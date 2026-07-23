from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.standalone import (
    StandaloneHandoffError,
    validate_standalone_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"


class StandaloneHandoffTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
