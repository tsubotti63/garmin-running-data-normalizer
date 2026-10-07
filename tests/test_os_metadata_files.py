from __future__ import annotations

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from garmin_running_data_normalizer.common.os_metadata import is_os_metadata_path
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input, doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.intake.archive import is_real_export_file
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.standalone import (
    StandaloneHandoffError,
    validate_standalone_handoff,
)

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
APPLEDOUBLE_BYTES = b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X        "
FINDER_BYTES = b"\x00\x00\x00\x01Bud1"
THUMBNAIL_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def add_input_metadata(root: Path) -> None:
    (root / "DI-Connect-Fitness/._synthetic_summarizedActivities.json").write_bytes(
        APPLEDOUBLE_BYTES
    )
    (root / "._ride.fit").write_bytes(APPLEDOUBLE_BYTES)
    (root / "._export.zip").write_bytes(APPLEDOUBLE_BYTES)
    macosx = root / "__MACOSX/DI-Connect-Fitness"
    macosx.mkdir(parents=True)
    (macosx / "._synthetic_summarizedActivities.json").write_bytes(APPLEDOUBLE_BYTES)
    (root / ".DS_Store").write_bytes(FINDER_BYTES)
    (root / "Thumbs.db").write_bytes(THUMBNAIL_BYTES)


def add_output_metadata(root: Path) -> None:
    (root / ".DS_Store").write_bytes(FINDER_BYTES)
    (root / "normalized/.DS_Store").write_bytes(FINDER_BYTES)
    (root / "._START_HERE.md").write_bytes(APPLEDOUBLE_BYTES)
    (root / "Thumbs.db").write_bytes(THUMBNAIL_BYTES)
    (root / "__MACOSX").mkdir()
    (root / "__MACOSX/._run_summary.json").write_bytes(APPLEDOUBLE_BYTES)


class OsMetadataFilesTest(unittest.TestCase):
    def test_metadata_rule_matches_only_os_metadata(self) -> None:
        for path in (
            ".DS_Store",
            "normalized/.DS_Store",
            "Thumbs.db",
            "._ride.fit",
            "DI-Connect-Fitness/._synthetic_summarizedActivities.json",
            "__MACOSX/synthetic_summarizedActivities.json",
            "export/__MACOSX/DI-Connect-Fitness/ride.fit",
            "export\\._ride.fit",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_os_metadata_path(path))
        for path in (
            "DI-Connect-Fitness/synthetic_summarizedActivities.json",
            "ride.fit",
            "_ride.fit",
            "notes.DS_Store",
            "Thumbs.db.json",
            "MACOSX/ride.fit",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_os_metadata_path(path))

    def test_zip_member_rule_keeps_the_v1_4_0_snapshot_identity(self) -> None:
        self.assertTrue(is_real_export_file("Thumbs.db"))
        for name in (
            ".DS_Store",
            "DI-Connect-Fitness/._synthetic_summarizedActivities.json",
            "__MACOSX/DI-Connect-Fitness/synthetic_summarizedActivities.json",
        ):
            with self.subTest(name=name):
                self.assertFalse(is_real_export_file(name))

    def test_folder_input_ignores_os_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clean_input = root / "clean"
            noisy_input = root / "noisy"
            shutil.copytree(SYNTHETIC_EXPORT, clean_input)
            shutil.copytree(SYNTHETIC_EXPORT, noisy_input)
            add_input_metadata(noisy_input)

            clean = run_all(clean_input, root / "clean-output")
            noisy = run_all(noisy_input, root / "noisy-output")

            self.assertEqual(noisy["status"], "PASS_WITH_WARNINGS")
            self.assertEqual(noisy["exit_code"], 0)
            self.assertEqual(noisy["deterministic_digest"], clean["deterministic_digest"])
            self.assertEqual(doctor_input(noisy_input), doctor_input(clean_input))

    def test_handoff_commands_ignore_os_metadata_but_not_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(SYNTHETIC_EXPORT, output)
            add_output_metadata(output)

            validate_standalone_handoff(output)
            report = doctor_run_output(output)
            self.assertEqual(report["product_status"], "PASS_WITH_WARNINGS")
            self.assertEqual(report["diagnostic_contract_availability"], "CURRENT")
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    [
                        "README.md",
                        "doctor.json",
                        "manifest.json",
                        "privacy_scan.json",
                        "run_quality.json",
                        "source_completeness.json",
                    ],
                )

            (output / "notes.txt").write_text("not declared\n", encoding="utf-8")
            with self.assertRaisesRegex(StandaloneHandoffError, "undeclared or missing file"):
                validate_standalone_handoff(output)


if __name__ == "__main__":
    unittest.main()
