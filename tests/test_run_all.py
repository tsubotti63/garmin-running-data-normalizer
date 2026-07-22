from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer.normalizers.activities import normalize_activities
from garmin_running_data_normalizer.run_all import OUTPUT_PATHS, RunAllError, run_all


ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_FIXTURE = ROOT / "examples/synthetic/garmin_export"


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def synthetic_fit_session() -> bytes:
    session_definition = bytes([0x40, 0x00, 0x00]) + struct.pack("<H", 18) + bytes([
        3,
        2, 4, 0x86,
        5, 1, 0x00,
        9, 4, 0x86,
    ])
    session_record = bytes([0x00]) + struct.pack("<I", 1_000_000) + bytes([1]) + struct.pack("<I", 100_000)
    lap_definition = bytes([0x41, 0x00, 0x00]) + struct.pack("<H", 19) + bytes([
        2,
        2, 4, 0x86,
        9, 4, 0x86,
    ])
    lap_record = bytes([0x01]) + struct.pack("<I", 1_000_000) + struct.pack("<I", 50_000)
    body = session_definition + session_record + lap_definition + lap_record
    return bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT" + body


class RunAllTest(unittest.TestCase):
    def run_command(self, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "garmin_running_data_normalizer",
                "run-all",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def add_optional_families(input_root: Path, *, include_bad_fit: bool = False) -> None:
        (input_root / "synthetic_gear.json").write_text(json.dumps({
            "gearDTOS": [{"gearPk": "SYNTHETIC-GEAR-1", "displayName": "Synthetic Shoe"}],
            "gearActivityDTOs": {"SYNTHETIC-GEAR-1": [{"activityId": "SYNTHETIC-RUN-0001"}]},
        }), encoding="utf-8")
        (input_root / "synthetic_personalRecord.json").write_text(json.dumps({
            "personalRecords": [{
                "personalRecordId": "SYNTHETIC-PR-1",
                "activityId": "SYNTHETIC-RUN-0001",
                "personalRecordType": "synthetic_best",
            }]
        }), encoding="utf-8")
        (input_root / "synthetic-session.fit").write_bytes(synthetic_fit_session())
        if include_bad_fit:
            (input_root / "synthetic-incomplete.fit").write_bytes(b"not-fit")

    def synthetic_input(self, parent: Path, *, optional: bool = False, bad_fit: bool = False) -> Path:
        parent.mkdir(parents=True, exist_ok=True)
        input_root = parent / "input"
        shutil.copytree(ACTIVITIES_FIXTURE, input_root)
        if optional:
            self.add_optional_families(input_root, include_bad_fit=bad_fit)
        return input_root

    def test_t1_full_synthetic_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_root = self.synthetic_input(temporary, optional=True)
            before = tree_hashes(input_root)
            output = temporary / "output"
            result = self.run_command(input_root, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("STATUS: PASS", result.stdout)
            self.assertEqual(before, tree_hashes(input_root))
            self.assertEqual(
                sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()),
                sorted(OUTPUT_PATHS),
            )
            summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
            qa = json.loads((output / "qa/dataset_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(qa["status"], "PASS")
            self.assertTrue(all(item["status"] == "PASS" for item in qa["datasets"]))
            self.assertEqual({summary["family_results"][name]["detected_asset_count"] for name in ("activities", "gear", "personal_records", "fit")}, {1})

    def test_t2_activities_only_passes_with_warnings_and_empty_optional_outputs(self) -> None:
        before = tree_hashes(ACTIVITIES_FIXTURE)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            result = self.run_command(ACTIVITIES_FIXTURE, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("STATUS: PASS_WITH_WARNINGS", result.stdout)
            summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
            for family in ("gear", "personal_records", "fit"):
                self.assertEqual(summary["family_results"][family]["status"], "SKIPPED_NOT_PRESENT")
            for relative in (
                "normalized/gear.json",
                "normalized/activity_gear.json",
                "normalized/personal_records.json",
                "normalized/fit_sessions.json",
                "normalized/fit_laps.json",
                "audit/fit_audit.json",
            ):
                self.assertEqual(json.loads((output / relative).read_text(encoding="utf-8")), [])
        self.assertEqual(before, tree_hashes(ACTIVITIES_FIXTURE))

    def test_t3_fatal_inputs_do_not_publish_completion_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)

            empty_input = temporary / "empty"
            empty_input.mkdir()
            missing_output = temporary / "missing-output"
            missing = self.run_command(empty_input, missing_output)
            self.assertEqual(missing.returncode, 2)
            self.assertFalse(missing_output.exists())

            unsafe_input = temporary / "unsafe"
            unsafe_input.mkdir()
            with zipfile.ZipFile(unsafe_input / "synthetic.zip", "w") as archive:
                archive.writestr("../synthetic_summarizedActivities.json", "{}")
            unsafe_output = temporary / "unsafe-output"
            unsafe = self.run_command(unsafe_input, unsafe_output)
            self.assertEqual(unsafe.returncode, 2)
            self.assertFalse(unsafe_output.exists())

            malformed_input = temporary / "malformed"
            malformed_input.mkdir()
            (malformed_input / "synthetic_summarizedActivities.json").write_text("{not-json", encoding="utf-8")
            malformed_output = temporary / "malformed-output"
            malformed = self.run_command(malformed_input, malformed_output)
            self.assertEqual(malformed.returncode, 2)
            self.assertFalse(malformed_output.exists())

            inside_input = self.synthetic_input(temporary / "inside-case")
            inside_output = inside_input / "generated"
            inside = self.run_command(inside_input, inside_output)
            self.assertEqual(inside.returncode, 2)
            self.assertFalse(inside_output.exists())

            existing_input = self.synthetic_input(temporary / "existing-case")
            existing_output = temporary / "existing-output"
            existing_output.mkdir()
            marker = existing_output / "keep.txt"
            marker.write_text("keep\n", encoding="utf-8")
            existing = self.run_command(existing_input, existing_output)
            self.assertEqual(existing.returncode, 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse((existing_output / "run_summary.json").exists())

            for result in (missing, unsafe, malformed, inside, existing):
                self.assertNotIn(str(temporary), result.stdout + result.stderr)

            changing_input = self.synthetic_input(temporary / "changing-case")
            changing_output = temporary / "changing-output"
            activity_file = next(changing_input.rglob("*summarizedActivities.json"))

            def normalize_then_change(root: str):
                records = normalize_activities(root)
                activity_file.write_bytes(activity_file.read_bytes() + b" ")
                return records

            with mock.patch(
                "garmin_running_data_normalizer.run_all.normalize_activities",
                side_effect=normalize_then_change,
            ):
                with self.assertRaises(RunAllError) as changed:
                    run_all(changing_input, changing_output)
            self.assertEqual(changed.exception.code, "INPUT_CHANGED")
            self.assertFalse(changing_output.exists())

    def test_t4_incomplete_fit_returns_partial_success_with_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_root = self.synthetic_input(temporary, optional=True, bad_fit=True)
            output = temporary / "output"
            result = self.run_command(input_root, output)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("STATUS: PARTIAL_SUCCESS", result.stdout)
            summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
            audit = json.loads((output / "audit/fit_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "PARTIAL_SUCCESS")
            self.assertEqual(summary["family_results"]["fit"]["detected_asset_count"], 2)
            self.assertEqual(summary["family_results"]["fit"]["incomplete_asset_count"], 1)
            self.assertEqual(summary["family_results"]["fit"]["skipped_asset_count"], 1)
            self.assertEqual(Counter(item["parse_status"] for item in audit), Counter({"parsed_activity": 1, "too_small": 1}))
            self.assertTrue((output / "run_summary.json").is_file())

    def test_t5_rerun_refuses_existing_output_and_new_output_is_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_root = self.synthetic_input(temporary, optional=True)
            first = temporary / "first"
            second = temporary / "second"
            first_run = self.run_command(input_root, first)
            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            first_hashes = tree_hashes(first)
            same_destination = self.run_command(input_root, first)
            self.assertEqual(same_destination.returncode, 2)
            self.assertEqual(first_hashes, tree_hashes(first))
            second_run = self.run_command(input_root, second)
            self.assertEqual(second_run.returncode, 0, second_run.stderr)
            self.assertEqual(first_hashes, tree_hashes(second))

    def test_t6_privacy_regression_and_no_ci_artifact_upload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_root = self.synthetic_input(temporary, optional=True)
            output = temporary / "output"
            result = self.run_command(input_root, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            console = result.stdout + result.stderr
            self.assertNotIn(str(temporary), console)
            self.assertNotIn("SYNTHETIC-RUN-0001", console)
            self.assertNotIn("Synthetic Shoe", console)
            self.assertNotRegex(console, re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I))

            combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(output.rglob("*")) if path.is_file())
            self.assertNotRegex(combined, re.compile(r"/(?:Users|home)/[^/\s]+"))
            self.assertNotIn("latitude", combined.lower())
            self.assertNotIn("longitude", combined.lower())
            csv_header = (output / "analysis/activities.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertNotIn("activity_id", csv_header)
            self.assertNotIn("memo", csv_header)
            self.assertNotIn("source", csv_header)
            self.assertNotIn("sha", csv_header)

        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("upload-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
