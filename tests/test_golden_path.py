from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer import runner


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/synthetic/garmin_export"
EXPECTED = ROOT / "examples/synthetic/expected/golden_path"
OUTPUT_NAMES = (
    "normalized_activities.json",
    "qa_summary.json",
    "run_manifest.json",
)


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class GoldenPathTest(unittest.TestCase):
    def run_command(self, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "garmin_running_data_normalizer",
                "normalize-activities",
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

    def test_formal_command_matches_golden_result_and_is_deterministic(self) -> None:
        before = tree_hashes(FIXTURE)
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            first = temporary / "first"
            second = temporary / "second"
            first_run = self.run_command(FIXTURE, first)
            second_run = self.run_command(FIXTURE, second)
            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            self.assertEqual(second_run.returncode, 0, second_run.stderr)
            self.assertIn("PASS", first_run.stdout)
            self.assertEqual(sorted(path.name for path in first.iterdir()), sorted(OUTPUT_NAMES))

            for name in OUTPUT_NAMES:
                first_bytes = (first / name).read_bytes()
                self.assertEqual(first_bytes, (second / name).read_bytes())
                self.assertEqual(first_bytes, (EXPECTED / name).read_bytes())

            qa = json.loads((first / "qa_summary.json").read_text(encoding="utf-8"))
            manifest = json.loads((first / "run_manifest.json").read_text(encoding="utf-8"))
            records = json.loads((first / "normalized_activities.json").read_text(encoding="utf-8"))
            self.assertEqual(qa["status"], "PASS")
            self.assertEqual(qa["missing_key_count"], 0)
            self.assertEqual(qa["duplicate_key_count"], 0)
            self.assertEqual(qa["records_sha256"], manifest["deterministic_digest"])
            self.assertTrue(all(record["garmin_activity_key"] for record in records))

            combined = "\n".join((first / name).read_text(encoding="utf-8") for name in OUTPUT_NAMES)
            self.assertNotRegex(combined, re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I))
            self.assertNotRegex(combined, re.compile(r"/(?:Users|home)/[^/\s]+"))
            self.assertNotIn("latitude", combined.lower())
            self.assertNotIn("longitude", combined.lower())

        self.assertEqual(before, tree_hashes(FIXTURE))

    def test_missing_or_insufficient_input_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            missing = self.run_command(temporary / "missing", temporary / "output-missing")
            self.assertNotEqual(missing.returncode, 0)
            empty_input = temporary / "empty-input"
            empty_input.mkdir()
            insufficient = self.run_command(empty_input, temporary / "output-empty")
            self.assertNotEqual(insufficient.returncode, 0)

    def test_nonempty_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("do not replace\n", encoding="utf-8")
            result = self.run_command(FIXTURE, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "do not replace\n")
            self.assertEqual(sorted(path.name for path in output.iterdir()), ["keep.txt"])

    def test_output_inside_input_is_rejected(self) -> None:
        before = tree_hashes(FIXTURE)
        output = FIXTURE / "generated-output"
        result = self.run_command(FIXTURE, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertEqual(before, tree_hashes(FIXTURE))

    def test_unsafe_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_root = temporary / "input"
            input_root.mkdir()
            with zipfile.ZipFile(input_root / "unsafe.zip", "w") as archive:
                archive.writestr("../synthetic_summarizedActivities.json", "{}")
            output = temporary / "output"
            result = self.run_command(input_root, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_input_and_output_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_target = temporary / "input-target"
            input_target.mkdir()
            input_link = temporary / "input-link"
            input_link.symlink_to(input_target, target_is_directory=True)
            input_result = self.run_command(input_link, temporary / "input-output")
            self.assertNotEqual(input_result.returncode, 0)
            self.assertFalse((temporary / "input-output").exists())

            output_target = temporary / "output-target"
            output_target.mkdir()
            output_link = temporary / "output-link"
            output_link.symlink_to(output_target, target_is_directory=True)
            output_result = self.run_command(FIXTURE, output_link)
            self.assertNotEqual(output_result.returncode, 0)
            self.assertEqual(list(output_target.iterdir()), [])

    def test_empty_normalization_result_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with mock.patch.object(runner, "normalize_activities", return_value=[]):
                with self.assertRaisesRegex(runner.GoldenPathError, "no activity records"):
                    runner.run_activities(FIXTURE, output)
            self.assertFalse(output.exists())

    def test_provenance_divergence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            divergent = [
                {
                    "garmin_activity_key": "garmin_activity:synthetic",
                    "source_path": "changed_summarizedActivities.json",
                    "source_sha256": "0" * 64,
                }
            ]
            with mock.patch.object(runner, "normalize_activities", return_value=divergent):
                with self.assertRaisesRegex(runner.GoldenPathError, "provenance diverged"):
                    runner.run_activities(FIXTURE, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
