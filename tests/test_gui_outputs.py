from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

# Import the diagnostics package before modules that import standalone:
# the other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.diagnostics.doctor import DoctorError, doctor_run_output
from garmin_running_data_normalizer.gui import outputs
from garmin_running_data_normalizer.gui.outputs import (
    MACOS_OPEN,
    OPEN_TARGETS,
    OutputActionError,
    check_output,
    make_support_bundle,
    open_command,
    open_output,
    support_bundle_path,
)
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.standalone import validate_standalone_handoff
from tests.test_gui_runs import SYNTHETIC_EXPORT, child_environment, wait_until
from tests.test_run_all_progress import tree_bytes


def can_symlink(directory: Path) -> bool:
    probe = directory / "symlink-probe"
    try:
        probe.symlink_to(directory, target_is_directory=True)
    except OSError:
        return False
    probe.unlink()
    return True


class OutputTestCase(unittest.TestCase):
    """Give each test its own copy of one synthetic Run-All output."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source_directory = tempfile.TemporaryDirectory()
        cls.source_output = Path(cls.source_directory.name) / "output"
        run_all(SYNTHETIC_EXPORT, cls.source_output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.source_directory.cleanup()

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "output"
        shutil.copytree(self.source_output, self.output)

    def assert_code(self, code: str, action: object, *args: object) -> None:
        with self.assertRaises(OutputActionError) as caught:
            action(*args)  # type: ignore[operator]
        self.assertEqual(caught.exception.code, code)


class OutputCheckTest(OutputTestCase):
    def test_a_finished_output_is_checked_as_the_cli_checks_it(self) -> None:
        answer = check_output(self.output)
        handoff = validate_standalone_handoff(self.output)
        report = doctor_run_output(self.output)
        self.assertEqual(
            answer,
            {
                "handoff": {
                    "status": "PASS",
                    "dataset_count": handoff["dataset_count"],
                    "relationship_count": handoff["explicit_relationship_count"],
                    "warning_count": handoff["warning_count"],
                },
                "doctor": {
                    "product_status": report["product_status"],
                    "usability_scope": report["usability_scope"],
                    "next_action_id": report["doctor_next_action_id"],
                    "support_bundle_suggested": True,
                    "warning_codes": ["OPTIONAL_FAMILY_NOT_PRESENT"],
                },
            },
        )
        # The synthetic example: 17 datasets, 6 relationships, 3 warnings.
        self.assertEqual(
            (handoff["dataset_count"], handoff["explicit_relationship_count"], handoff["warning_count"]),
            (17, 6, 3),
        )
        self.assertEqual(report["usability_scope"], "USABLE_WITH_DISCLOSED_WARNINGS")
        self.assertNotIn(str(self.root), json.dumps(answer))

    def test_the_warning_total_includes_warnings_outside_the_data_families(self) -> None:
        # A valid link to a missing activity is a relationship warning, which
        # no data family counts, so the sum over the families is one short.
        export = self.root / "export"
        shutil.copytree(SYNTHETIC_EXPORT, export)
        (export / "synthetic_gear.json").write_text(
            json.dumps(
                {
                    "gearDTOS": [{"gearPk": "SYNTHETIC-GEAR-1", "displayName": "Synthetic Shoe"}],
                    "gearActivityDTOs": {"SYNTHETIC-GEAR-1": [{"activityId": "MISSING-ACTIVITY"}]},
                }
            ),
            encoding="utf-8",
        )
        result = run_all(export, self.root / "linked")
        family_total = sum(details["warning_count"] for details in result["family_results"].values())
        answer = check_output(self.root / "linked")
        self.assertEqual(answer["handoff"]["warning_count"], family_total + 1)
        self.assertEqual(
            answer["doctor"]["warning_codes"],
            ["OPTIONAL_FAMILY_NOT_PRESENT", "RELATIONSHIP_UNRESOLVED_VALID_LINK"],
        )

    def test_an_output_that_changed_after_the_run_is_reported_by_code(self) -> None:
        with (self.output / "analysis/activities.csv").open("ab") as handle:
            handle.write(b"changed\n")
        self.assert_code("HANDOFF_INVALID", check_output, self.output)
        (self.output / "START_HERE.md").unlink()
        self.assert_code("HANDOFF_INVALID", check_output, self.output)
        self.assert_code("HANDOFF_INVALID", check_output, self.root / "missing")

    def test_a_link_in_place_of_the_output_is_not_checked(self) -> None:
        if not can_symlink(self.root):
            self.skipTest("this system does not allow creating symbolic links")
        link = self.root / "link"
        link.symlink_to(self.output, target_is_directory=True)
        self.assert_code("HANDOFF_INVALID", check_output, link)

    def test_doctor_answers_other_than_a_current_completed_run_are_refused(self) -> None:
        with patch.object(
            outputs,
            "doctor_run_output",
            return_value={"completion_state": "NOT_COMPLETED", "diagnostic_contract_availability": "NOT_EVALUATED"},
        ):
            self.assert_code("OUTPUT_CHANGED", check_output, self.output)
        with patch.object(
            outputs,
            "doctor_run_output",
            return_value={"completion_state": "COMPLETED", "diagnostic_contract_availability": "LEGACY_NOT_AVAILABLE"},
        ):
            self.assert_code("OUTPUT_CHANGED", check_output, self.output)
        with patch.object(
            outputs,
            "doctor_run_output",
            side_effect=DoctorError("DOCTOR_AUTHORITY_INVALID", "diagnostic authorities disagree"),
        ):
            self.assert_code("DOCTOR_AUTHORITY_INVALID", check_output, self.output)

    def test_an_output_that_cannot_be_read_is_reported_by_code(self) -> None:
        with patch.object(outputs, "validate_standalone_handoff", side_effect=PermissionError("denied")):
            self.assert_code("OUTPUT_NOT_AVAILABLE", check_output, self.output)


class SupportBundleTest(OutputTestCase):
    def test_the_bundle_is_saved_next_to_the_output_as_the_cli_makes_it(self) -> None:
        before = tree_bytes(self.output)
        answer = make_support_bundle(self.output)
        destination = self.root / "output-support-bundle.zip"
        self.assertEqual(support_bundle_path(self.output), destination)
        self.assertEqual(
            answer,
            {"path": str(destination), "member_count": 6, "human_review_required": True},
        )
        with zipfile.ZipFile(destination) as archive:
            self.assertEqual(len(archive.namelist()), 6)
        self.assertEqual(tree_bytes(self.output), before)
        cli_bundle = self.root / "cli-support-bundle.zip"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "garmin_running_data_normalizer",
                "support-bundle",
                "--run-output",
                str(self.output),
                "--output",
                str(cli_bundle),
            ],
            capture_output=True,
            text=True,
            env=child_environment(),
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(destination.read_bytes(), cli_bundle.read_bytes())

    def test_an_existing_bundle_is_never_replaced(self) -> None:
        make_support_bundle(self.output)
        destination = support_bundle_path(self.output)
        first = destination.read_bytes()
        self.assert_code("SUPPORT_BUNDLE_EXISTS", make_support_bundle, self.output)
        self.assertEqual(destination.read_bytes(), first)
        destination.unlink()
        if can_symlink(self.root):
            destination.symlink_to(self.root / "elsewhere.zip")
            self.assert_code("SUPPORT_BUNDLE_EXISTS", make_support_bundle, self.output)
            self.assertFalse((self.root / "elsewhere.zip").exists())

    def test_bundle_failures_are_reported_by_code(self) -> None:
        self.assert_code("SUPPORT_BUNDLE_PATH_UNSAFE", make_support_bundle, self.root / "missing")
        empty = self.root / "empty"
        empty.mkdir()
        self.assert_code("SUPPORT_BUNDLE_AUTHORITY_INVALID", make_support_bundle, empty)
        with patch(
            "garmin_running_data_normalizer.diagnostics.support_bundle.tempfile.mkstemp",
            side_effect=PermissionError("denied"),
        ):
            self.assert_code("SUPPORT_BUNDLE_NOT_WRITTEN", make_support_bundle, self.output)
        self.assertFalse(support_bundle_path(self.output).exists())


class OpenOutputTest(OutputTestCase):
    def test_open_commands_take_one_absolute_path_and_no_shell(self) -> None:
        folder = self.output
        start_here = self.output / "START_HERE.md"
        self.assertEqual(
            open_command(folder, folder=True, platform="darwin"),
            [MACOS_OPEN, "-R", str(folder)],
        )
        self.assertEqual(
            open_command(start_here, folder=False, platform="darwin"),
            [MACOS_OPEN, str(start_here)],
        )
        self.assertIsNone(open_command(folder, folder=True, platform="win32"))
        with patch.object(outputs.shutil, "which", return_value="/usr/bin/xdg-open"):
            self.assertEqual(
                open_command(folder, folder=True, platform="linux"),
                ["/usr/bin/xdg-open", str(folder)],
            )
        with patch.object(outputs.shutil, "which", return_value=None):
            self.assert_code(
                "OPEN_NOT_AVAILABLE",
                lambda: open_command(folder, folder=False, platform="linux"),
            )

    def test_only_the_folder_and_start_here_can_be_opened(self) -> None:
        self.assertEqual(OPEN_TARGETS, ("folder", "start_here"))
        with patch.object(outputs, "_launch") as launch:
            open_output(self.output, "folder")
            open_output(self.output, "start_here")
            self.assertEqual(
                launch.call_args_list,
                [
                    call(self.output, folder=True),
                    call(self.output / "START_HERE.md", folder=False),
                ],
            )
            for target in (None, "", "Folder", "START_HERE.md", "../folder", ["folder"], {"target": "folder"}, 1):
                with self.subTest(target=target):
                    self.assert_code("REQUEST_INVALID", open_output, self.output, target)
            self.assertEqual(launch.call_count, 2)

    def test_missing_or_replaced_targets_are_not_opened(self) -> None:
        with patch.object(outputs, "_launch") as launch:
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.root / "missing", "folder")
            (self.output / "START_HERE.md").unlink()
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "start_here")
            (self.output / "START_HERE.md").mkdir()
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "start_here")
            not_a_folder = self.root / "file"
            not_a_folder.write_text("synthetic", encoding="utf-8")
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, not_a_folder, "folder")
            if can_symlink(self.root):
                (self.output / "START_HERE.md").rmdir()
                (self.output / "START_HERE.md").symlink_to(self.output / "DATASET_INVENTORY.md")
                self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "start_here")
                link = self.root / "link"
                link.symlink_to(self.output, target_is_directory=True)
                self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, link, "folder")
            launch.assert_not_called()

    def test_a_folder_marked_as_a_reparse_point_is_not_opened(self) -> None:
        junction = SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o755,
            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
        )
        with (
            patch.object(outputs.os, "lstat", return_value=junction),
            patch.object(outputs, "_launch") as launch,
        ):
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "folder")
        launch.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "junctions are a Windows feature")
    def test_a_junction_in_place_of_the_output_is_not_opened(self) -> None:
        junction = self.root / "junction"
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(self.output)],
            check=True,
            capture_output=True,
        )
        with patch.object(outputs, "_launch") as launch:
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, junction, "folder")
        launch.assert_not_called()

    def test_a_relative_path_is_never_opened(self) -> None:
        directory = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, directory)
        with patch.object(outputs, "_launch") as launch:
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, Path("output"), "folder")
        launch.assert_not_called()

    def test_failures_to_open_are_reported_by_code(self) -> None:
        with patch.object(outputs, "_launch", side_effect=FileNotFoundError("no opener")):
            self.assert_code("OPEN_FAILED", open_output, self.output, "folder")
        with patch.object(outputs, "_launch", side_effect=OutputActionError("OPEN_NOT_AVAILABLE")):
            self.assert_code("OPEN_NOT_AVAILABLE", open_output, self.output, "start_here")

    def test_the_opener_is_started_from_an_argument_list(self) -> None:
        process = Mock()
        with (
            patch.object(outputs, "sys", SimpleNamespace(platform="darwin")),
            patch.object(outputs.subprocess, "Popen", return_value=process) as popen,
        ):
            outputs._launch(self.output, folder=True)
        args, options = popen.call_args
        self.assertEqual(args, ([MACOS_OPEN, "-R", str(self.output)],))
        self.assertNotIn("shell", options)
        self.assertTrue(options["start_new_session"])
        for stream in ("stdin", "stdout", "stderr"):
            self.assertEqual(options[stream], subprocess.DEVNULL)
        self.assertTrue(wait_until(lambda: process.wait.called, 5.0))

    def test_windows_shows_the_folder_and_opens_the_file_with_explicit_verbs(self) -> None:
        with (
            patch.object(outputs, "sys", SimpleNamespace(platform="win32")),
            patch.object(outputs.os, "startfile", create=True) as startfile,
            patch.object(outputs.subprocess, "Popen") as popen,
        ):
            outputs._launch(self.output, folder=True)
            outputs._launch(self.output / "START_HERE.md", folder=False)
        self.assertEqual(
            startfile.call_args_list,
            [
                call(str(self.output), "explore"),
                call(str(self.output / "START_HERE.md"), "open"),
            ],
        )
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
