"""Outputs that other versions of this app made (stage B5b).

An output of 1.3, which has no diagnostics, is checked against the files
that the 1.3 releases wrote, in each of their four shapes, as v1.4 through
v1.7.1 did: validate-handoff takes it, the Doctor says that it has none of
the diagnostics of v1.4 and that the result that it recorded is the one to
use, and support-bundle refuses it for the diagnostics that it lacks. Until
stage B5b, its files were compared with those of this version, which stage
A2b-2 made longer, so that every 1.3 output was refused.

An output of 1.0 to 1.2, or of 1.4 or later that another version made, stops
with OUTPUT_OTHER_VERSION in validate-handoff, doctor --run-output, and
support-bundle alike, by the version that its summary names, before its
files are compared, so that it is never taken for one whose files changed.
The 1.0 releases named no version, and their outputs stop as before.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer import __version__
from garmin_running_data_normalizer.diagnostics.doctor import DoctorError, doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import SupportBundleError, build_support_bundle
from garmin_running_data_normalizer.run_all import RUN_ALL_VERSION
from garmin_running_data_normalizer.standalone import (
    OtherVersionError,
    StandaloneHandoffError,
    validate_standalone_handoff,
)
from tests.test_stops import SYNTHETIC_EXPORT, StopLines, cli, register_args
from tests.v1_3_outputs import V1_3_FILES, V1_3_PACK, V1_3_SHAPES, V1_3_SNAPSHOT_FILES, as_release, as_v1_3

# The four shapes of a run of this version: a run, with the External-safe
# Pack, of Snapshots, and both.
SHAPES = ("plain", "pack", "snapshot", "both")


class EarlierOutputTest(StopLines, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_directory = tempfile.TemporaryDirectory()
        source = Path(cls.source_directory.name)
        cls.sources = {name: source / name for name in SHAPES}
        assert cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", cls.sources["plain"])[0] == 0
        assert cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", cls.sources["pack"], "--external-safe-pack")[0] == 0
        store = source / "store"
        assert cli("snapshot", "init", "--store", store, "--account", "synthetic-account-boundary")[0] == 0
        assert cli(*register_args(store, SYNTHETIC_EXPORT))[0] == 0
        assert cli("snapshot", "run-all", "--store", store, "--output", cls.sources["snapshot"])[0] == 0
        assert cli("snapshot", "run-all", "--store", store, "--output", cls.sources["both"], "--external-safe-pack")[0] == 0

    @classmethod
    def tearDownClass(cls) -> None:
        cls.source_directory.cleanup()

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def copy(self, shape: str) -> Path:
        output = self.root / shape
        shutil.copytree(self.sources[shape], output)
        return output

    def test_the_four_shapes_of_1_3_are_the_files_that_its_releases_wrote(self) -> None:
        # As the 1.3.0 to 1.3.3 releases wrote them, from their tags: 44
        # files, 45 with the External-safe Pack, 47 of Snapshots, 48 of both,
        # each with its files before the manifest and the summary.
        self.assertEqual([len(V1_3_SHAPES[name]) for name in SHAPES], [44, 45, 47, 48])
        self.assertEqual(V1_3_FILES[-2:], ("run_manifest.json", "run_summary.json"))
        self.assertEqual(V1_3_SHAPES["pack"][42], V1_3_PACK)
        self.assertEqual(V1_3_SHAPES["snapshot"][42:45], V1_3_SNAPSHOT_FILES)
        self.assertEqual(V1_3_SHAPES["both"][42:46], (V1_3_PACK, *V1_3_SNAPSHOT_FILES))
        self.assertFalse(any(path.startswith("diagnostics/") for path in V1_3_FILES))
        # This version writes more files than 1.3 did.
        for name in SHAPES:
            with self.subTest(shape=name):
                written = json.loads((self.sources[name] / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
                self.assertGreater(len(written), len(V1_3_SHAPES[name]))
                self.assertTrue(set(V1_3_SHAPES[name]) < set(written))

    def test_an_output_of_1_3_is_checked_as_v1_7_1_checked_it(self) -> None:
        for name in SHAPES:
            with self.subTest(shape=name):
                output = self.copy(name)
                self.assertEqual(as_v1_3(output), V1_3_SHAPES[name])
                result = validate_standalone_handoff(output)
                self.assertEqual((result["status"], result["diagnostic_contract_availability"]), ("PASS", "LEGACY_NOT_AVAILABLE"))
                self.assertEqual(cli("validate-handoff", "--input", output)[0], 0)
                report = doctor_run_output(output)
                self.assertEqual(report["diagnostic_contract_availability"], "LEGACY_NOT_AVAILABLE")
                self.assertEqual(report["product_version"], "1.3.3")
                self.assertEqual(
                    [(finding["code"], finding["next_action_id"]) for finding in report["findings"]],
                    [("V1_4_DIAGNOSTICS_NOT_AVAILABLE", "USE_RECORDED_LEGACY_RESULT")],
                )
                self.assertEqual(cli("doctor", "--run-output", output, "--format", "json")[0], 0)
                # The Support Bundle needs the diagnostics of v1.4, as before.
                with self.assertRaises(SupportBundleError) as caught:
                    build_support_bundle(output, self.root / f"{name}.zip")
                self.assertEqual(caught.exception.code, "SUPPORT_BUNDLE_AUTHORITY_INVALID")

    def test_an_output_of_1_3_with_the_files_of_this_version_is_refused(self) -> None:
        # The shape that the tests made until stage B5b: this version's files
        # without the diagnostics only, which no release wrote.
        output = self.copy("plain")
        written = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
        as_release(output, "1.3.3", tuple(path for path in written if not path.startswith("diagnostics/")))
        with self.assertRaisesRegex(StandaloneHandoffError, "version-aware exact set"):
            validate_standalone_handoff(output)
        self.assert_stop("HANDOFF_INVALID", ("validate-handoff", "--input", output), self.root)

    def test_an_output_of_another_version_stops_before_its_files_are_compared(self) -> None:
        cases = (
            # Versions before 1.3, which no version since 1.4 has taken.
            ("1.0.0", RUN_ALL_VERSION, "1.0.0"),
            ("1.1.1", 1, "1.1.1"),
            ("1.2.1", 1, "1.2.1"),
            # Versions of 1.4 and later that are not this one.
            ("1.4.2", 1, "1.4.2"),
            ("1.7.0", 1, "1.7.0"),
            ("2.0.0", RUN_ALL_VERSION, "2.0.0"),
            # This version's name with the checks of another, as the release
            # of 1.7.1 and this version in development until 2.0.0.
            (__version__, RUN_ALL_VERSION - 1, __version__),
            # A version of another form is not repeated.
            ("2.0.0rc1", RUN_ALL_VERSION, None),
        )
        for version, run_all_version, named in cases:
            with self.subTest(version=version, run_all_version=run_all_version):
                output = self.root / f"{version}-{run_all_version}"
                shutil.copytree(self.sources["plain"], output)
                written = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
                as_release(output, version, tuple(written), run_all_version)
                # The files do not matter: one more file changes nothing.
                (output / "unexpected.txt").write_text("synthetic", encoding="utf-8")
                with self.assertRaises(OtherVersionError) as caught:
                    validate_standalone_handoff(output)
                self.assertEqual(caught.exception.version, named)
                words = f"version {named}" if named else "another version"
                for command in (
                    ("validate-handoff", "--input", output),
                    ("doctor", "--run-output", output, "--format", "json"),
                    ("support-bundle", "--run-output", output, "--output", self.root / f"{version}.zip"),
                ):
                    line = self.assert_stop("OUTPUT_OTHER_VERSION", command, self.root)
                    self.assertIn(f"the output was made by {words} of this app", line)
                with self.assertRaises(DoctorError) as doctor:
                    doctor_run_output(output)
                self.assertEqual(doctor.exception.code, "OUTPUT_OTHER_VERSION")
                with self.assertRaises(SupportBundleError) as bundle:
                    build_support_bundle(output, self.root / f"{version}-bundle.zip")
                self.assertEqual(bundle.exception.code, "OUTPUT_OTHER_VERSION")
                self.assertFalse((self.root / f"{version}-bundle.zip").exists())

    def test_an_output_that_names_no_version_is_refused_as_before(self) -> None:
        # As the 1.0 releases wrote it, without product_version: no version
        # can be told, so it stops as it did in 1.7.1.
        output = self.copy("plain")
        summary_path = output / "run_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        del summary["product_version"]
        summary_path.write_text(json.dumps(summary), encoding="utf-8")
        with self.assertRaises(StandaloneHandoffError) as caught:
            validate_standalone_handoff(output)
        self.assertNotIsInstance(caught.exception, OtherVersionError)
        self.assert_stop("HANDOFF_INVALID", ("validate-handoff", "--input", output), self.root)
        self.assert_stop("DOCTOR_VERSION_UNSUPPORTED", ("doctor", "--run-output", output, "--format", "json"), self.root)
        self.assert_stop("SUPPORT_BUNDLE_AUTHORITY_INVALID", ("support-bundle", "--run-output", output, "--output", self.root / "b.zip"), self.root)

    def test_an_output_of_this_version_whose_files_changed_is_not_another_version(self) -> None:
        output = self.copy("plain")
        (output / "START_HERE.md").unlink()
        with self.assertRaises(StandaloneHandoffError) as caught:
            validate_standalone_handoff(output)
        self.assertNotIsInstance(caught.exception, OtherVersionError)
        self.assert_stop("HANDOFF_INVALID", ("validate-handoff", "--input", output), self.root)


if __name__ == "__main__":
    unittest.main()
