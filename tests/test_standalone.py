from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.standalone import (
    OtherVersionError,
    StandaloneHandoffError,
    validate_standalone_handoff,
)
from tests.v1_3_outputs import V1_3_SHAPES, as_v1_3


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"


class StandaloneHandoffTest(unittest.TestCase):
    def _rehash_completed_output(self, output: Path) -> None:
        manifest_path = output / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["outputs"]:
            data = (output / item["path"]).read_bytes()
            item["bytes"] = len(data)
            item["sha256"] = hashlib.sha256(data).hexdigest()
        canonical = "\n".join(
            f"{item['path']}:{item['sha256']}"
            for item in sorted(manifest["outputs"], key=lambda value: value["path"])
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        manifest["deterministic_output_digest"] = digest
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary_path = output / "run_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["deterministic_output_digest"] = digest
        summary["manifest_sha256"] = hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest()
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    def test_completed_output_is_self_describing_without_repository_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            detached_input = temporary / "input"
            shutil.copytree(SYNTHETIC_EXPORT, detached_input)
            output = temporary / "detached-handoff"
            run_all(detached_input, output)
            result = validate_standalone_handoff(output)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["first_read"], "START_HERE.md")
            self.assertFalse(result["repository_required"])
            self.assertFalse(result["internet_required"])
            self.assertEqual(result["dataset_count"], result["schema_dataset_count"])
            self.assertEqual(result["explicit_relationship_count"], 6)
            manifest = json.loads(
                (output / "run_manifest.json").read_text(encoding="utf-8")
            )
            schema = json.loads(
                (output / "SCHEMA_CATALOG.json").read_text(encoding="utf-8")
            )
            schema_by_dataset = {
                item["dataset"]: {field["field"] for field in item["fields"]}
                for item in schema["datasets"]
            }
            for dataset in manifest["datasets"]:
                records = json.loads(
                    (
                        output
                        / "normalized"
                        / f"{dataset['name']}.json"
                    ).read_text(encoding="utf-8")
                )
                emitted_fields = {
                    field for record in records for field in record
                }
                self.assertTrue(
                    emitted_fields.issubset(schema_by_dataset[dataset["name"]]),
                    dataset["name"],
                )

    def test_warning_and_partial_state_are_preserved_and_tampering_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            output = temporary / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            result = validate_standalone_handoff(output)
            self.assertEqual(result["run_status"], "PASS_WITH_WARNINGS")
            self.assertEqual(result["warning_count"], 3)

            context_path = output / "ANALYSIS_CONTEXT.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["relationships"][0]["status"] = "not_yet_defined"
            context_path.write_text(
                json.dumps(context, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneHandoffError,
                "non-explicit join",
            ):
                validate_standalone_handoff(output)

    def test_manifest_detects_payload_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            start_here = output / "START_HERE.md"
            start_here.write_text(
                start_here.read_text(encoding="utf-8") + "tampered\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneHandoffError,
                "manifest payload",
            ):
                validate_standalone_handoff(output)

    def test_v133_completed_handoff_remains_valid_without_v14_diagnostics(self) -> None:
        # With the files that the 1.3 releases wrote (stage B5b).
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            self.assertEqual(as_v1_3(output), V1_3_SHAPES["plain"])
            result = validate_standalone_handoff(output)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["diagnostic_contract_availability"],
                "LEGACY_NOT_AVAILABLE",
            )

    def test_summary_binds_manifest_and_deterministic_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            start_here = output / "START_HERE.md"
            start_here.write_text(
                start_here.read_text(encoding="utf-8") + "tampered\n",
                encoding="utf-8",
            )
            manifest_path = output / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = next(
                item
                for item in manifest["outputs"]
                if item["path"] == "START_HERE.md"
            )
            payload = start_here.read_bytes()
            entry["bytes"] = len(payload)
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneHandoffError,
                "manifest hash",
            ):
                validate_standalone_handoff(output)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            summary_path = output / "run_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["deterministic_output_digest"] = "0" * 64
            summary_path.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneHandoffError,
                "deterministic output digest",
            ):
                validate_standalone_handoff(output)

    def test_rehashed_but_semantically_contradictory_diagnostics_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            quality_path = output / "diagnostics/run_quality.json"
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            quality["dataset_summary"][0]["record_count"] = 999
            quality_path.write_text(
                json.dumps(quality, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self._rehash_completed_output(output)
            with self.assertRaisesRegex(
                StandaloneHandoffError,
                "contradict Product evidence",
            ):
                validate_standalone_handoff(output)

    def test_unexpected_file_and_current_version_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            (output / "unexpected-private.txt").write_text(
                "SYNTHETIC_PRIVATE_ROW_VALUE",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneHandoffError,
                "undeclared",
            ):
                validate_standalone_handoff(output)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            summary_path = output / "run_summary.json"
            manifest_path = output / "run_manifest.json"
            context_path = output / "ANALYSIS_CONTEXT.json"
            completeness_path = output / "diagnostics/source_completeness.json"
            quality_path = output / "diagnostics/run_quality.json"
            for path in (
                summary_path,
                manifest_path,
                context_path,
                completeness_path,
                quality_path,
            ):
                value = json.loads(path.read_text(encoding="utf-8"))
                value["product_version"] = "1.4.2"
                path.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            self._rehash_completed_output(output)
            # Another version made the output (stage B5b); until then, a
            # version that did not match the installed Product.
            with self.assertRaisesRegex(OtherVersionError, "made by version 1.4.2 of this app") as caught:
                validate_standalone_handoff(output)
            self.assertEqual(caught.exception.version, "1.4.2")


# Each module of the package imported first, with no other module of the
# package loaded, in a new Python (stage W4b of v2.2.1): the names of the
# modules found under the source folder and the errors, as ASCII JSON.
FIRST_IMPORTS = """
import importlib, json, sys
from pathlib import Path

source = Path(sys.argv[1])
sys.path.insert(0, str(source))
package = "garmin_running_data_normalizer"
names = []
for path in sorted((source / package).rglob("*.py")):
    parts = path.relative_to(source).with_suffix("").parts
    if parts[-1] != "__main__":
        names.append(".".join(parts[:-1] if parts[-1] == "__init__" else parts))
failed = []
for name in names:
    for loaded in [key for key in sys.modules if key == package or key.startswith(package + ".")]:
        del sys.modules[loaded]
    try:
        importlib.import_module(name)
    except Exception as error:
        failed.append(f"{name}: {type(error).__name__}: {error}")
print(json.dumps({"file": getattr(sys.modules.get(package), "__file__", None), "names": names, "failed": failed}))
"""


class FirstImportTest(unittest.TestCase):
    def test_every_module_can_be_the_first_that_is_imported(self) -> None:
        # The diagnostics package imports standalone (its doctor checks a
        # handoff), and standalone reads the diagnostic checks where it uses
        # them, so that no module meets a circular import when it is the
        # first of the package that is imported, as in a script or a test
        # file run on its own (stage W4b of v2.2.1). A new Python, so that
        # the modules that this run has loaded play no part, with its home
        # folders in a folder of the test, where importing writes nothing.
        with tempfile.TemporaryDirectory() as folder:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", FIRST_IMPORTS, str(ROOT / "src")],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
                cwd=folder,
                env={
                    **os.environ,
                    **dict.fromkeys(("HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "XDG_STATE_HOME"), folder),
                },
            )
            written = sorted(path.name for path in Path(folder).iterdir())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(written, [])
        found = json.loads(completed.stdout)
        self.assertEqual(found["failed"], [])
        self.assertEqual(
            Path(found["file"]).resolve(), (ROOT / "src/garmin_running_data_normalizer/__init__.py").resolve()
        )
        # Not a few modules by mistake: those that import standalone, and
        # standalone and the diagnostics package themselves, are among them.
        self.assertGreaterEqual(len(found["names"]), 80)
        self.assertLessEqual(
            {
                "garmin_running_data_normalizer",
                "garmin_running_data_normalizer.diagnostics",
                "garmin_running_data_normalizer.diagnostics.doctor",
                "garmin_running_data_normalizer.gui.outputs",
                "garmin_running_data_normalizer.output_check",
                "garmin_running_data_normalizer.runner",
                "garmin_running_data_normalizer.standalone",
                "garmin_running_data_normalizer.view.data",
            },
            set(found["names"]),
        )


if __name__ == "__main__":
    unittest.main()
