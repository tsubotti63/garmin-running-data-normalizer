from __future__ import annotations

import errno
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

# Import the diagnostics package before modules that import standalone:
# the other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.diagnostics.doctor import DoctorError, doctor_run_output
from garmin_running_data_normalizer.gui import outputs, places
from garmin_running_data_normalizer.gui.outputs import (
    MACOS_OPEN,
    OPEN_TARGETS,
    OutputActionError,
    check_output,
    earlier_outputs,
    make_support_bundle,
    open_command,
    open_output,
    output_summary,
    support_bundle_path,
)
from garmin_running_data_normalizer.gui.settings import remember_run_at
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.standalone import validate_standalone_handoff
from tests.v1_3_outputs import as_release, as_v1_3
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
                    # An output of 1.3 is told by its version (stage B5b).
                    "legacy": False,
                    "product_version": report["product_version"],
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
            return_value={"completion_state": "NOT_COMPLETED", "diagnostic_contract_availability": "LEGACY_NOT_AVAILABLE"},
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

    def test_the_bundle_holds_no_settings_of_the_gui(self) -> None:
        # Stage B4c: the settings remember places on this computer, which the
        # bundle never holds; it is made from the output alone.
        settings_path = places.settings_file()
        store = self.root / "remembered-store-of-this-test"
        self.assertIsNone(remember_run_at(settings_path, self.output, store))
        make_support_bundle(self.output)
        with zipfile.ZipFile(self.root / "output-support-bundle.zip") as archive:
            for name in archive.namelist():
                with self.subTest(member=name):
                    content = archive.read(name)
                    self.assertNotIn(places.SETTINGS_FILE_NAME, name)
                    self.assertNotIn(store.name.encode("utf-8"), content)
                    self.assertNotIn(str(settings_path.parent).encode("utf-8"), content)

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

    def test_the_bundle_goes_in_a_chosen_folder(self) -> None:
        # Stage B5a: next to the output by default, or in the folder that the
        # person chose, with the same name and the same bytes.
        chosen = self.root / "chosen"
        chosen.mkdir()
        answer = make_support_bundle(self.output, chosen)
        destination = chosen / "output-support-bundle.zip"
        self.assertEqual(answer, {"path": str(destination), "member_count": 6, "human_review_required": True})
        self.assertEqual(support_bundle_path(self.output, chosen), destination)
        make_support_bundle(self.output)
        self.assertEqual(destination.read_bytes(), support_bundle_path(self.output).read_bytes())

    def test_the_place_of_the_bundle_follows_the_rules_of_the_cli(self) -> None:
        # A folder that is there, outside the output, as for the output
        # (decision 20261016-13); no folder is made.
        missing = self.root / "missing"
        self.assert_code("SUPPORT_BUNDLE_PARENT_NOT_FOUND", make_support_bundle, self.output, missing)
        self.assertFalse(missing.exists())
        a_file = self.root / "a-file"
        a_file.write_bytes(b"synthetic")
        self.assert_code("SUPPORT_BUNDLE_PARENT_NOT_FOUND", make_support_bundle, self.output, a_file)
        before = tree_bytes(self.output)
        for folder in (self.output, self.output / "analysis"):
            with self.subTest(folder=folder.name):
                self.assert_code("SUPPORT_BUNDLE_INSIDE_OUTPUT", make_support_bundle, self.output, folder)
        if can_symlink(self.root):
            link = self.root / "link-to-output"
            link.symlink_to(self.output, target_is_directory=True)
            self.assert_code("SUPPORT_BUNDLE_INSIDE_OUTPUT", make_support_bundle, self.output, link)
        # The case of the names too, on a disk that does not tell it apart.
        if (self.root / "OUTPUT").exists():
            self.assert_code("SUPPORT_BUNDLE_INSIDE_OUTPUT", make_support_bundle, self.output, self.root / "OUTPUT")
        self.assertEqual(tree_bytes(self.output), before)
        self.assertEqual(validate_standalone_handoff(self.output)["status"], "PASS")

    def test_a_file_put_in_the_place_while_the_bundle_is_written_stays(self) -> None:
        # The bundle is given its name in one step that never replaces a file
        # (stage B5a): a file that another program put there meanwhile stays.
        destination = support_bundle_path(self.output)
        real_link = os.link

        def link(source: object, target: object) -> None:
            Path(str(target)).write_bytes(b"put there meanwhile")
            real_link(source, target)

        with patch("garmin_running_data_normalizer.diagnostics.support_bundle.os.link", side_effect=link):
            self.assert_code("SUPPORT_BUNDLE_EXISTS", make_support_bundle, self.output)
        self.assertEqual(destination.read_bytes(), b"put there meanwhile")
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["output", destination.name])

    def test_a_disk_without_hard_links_gets_a_copy_that_never_replaces_a_file(self) -> None:
        # Where the disk makes no hard links, the bundle is copied into a new
        # file; a name that is taken is never written over.
        destination = support_bundle_path(self.output)
        for number in (errno.EPERM, errno.EXDEV, errno.ENOTSUP):
            with self.subTest(errno=number):
                with patch(
                    "garmin_running_data_normalizer.diagnostics.support_bundle.os.link",
                    side_effect=OSError(number, "no hard links here"),
                ):
                    answer = make_support_bundle(self.output)
                self.assertEqual(answer["member_count"], 6)
                with zipfile.ZipFile(destination) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(len(archive.namelist()), 6)
                copied = destination.read_bytes()
                destination.unlink()
                make_support_bundle(self.output)
                self.assertEqual(destination.read_bytes(), copied)
                destination.unlink()
        real_open = os.open

        def taken(place: object, flags: int, *args: object) -> int:
            # Something takes the name between the link and the copy.
            if Path(str(place)) == destination:
                destination.write_bytes(b"put there meanwhile")
            return real_open(place, flags, *args)

        with (
            patch("garmin_running_data_normalizer.diagnostics.support_bundle.os.link", side_effect=OSError(errno.EXDEV, "no hard links here")),
            patch("garmin_running_data_normalizer.diagnostics.support_bundle.os.open", side_effect=taken),
        ):
            self.assert_code("SUPPORT_BUNDLE_EXISTS", make_support_bundle, self.output)
        self.assertEqual(destination.read_bytes(), b"put there meanwhile")
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["output", destination.name])

    def test_a_bundle_that_cannot_be_written_leaves_nothing(self) -> None:
        # A folder that cannot be written, or a copy that fails half-way,
        # gives SUPPORT_BUNDLE_NOT_WRITTEN, as the CLI does (stage B5a), and
        # leaves neither the temporary file nor a part of the bundle.
        destination = support_bundle_path(self.output)
        real_read, real_open = Path.read_bytes, os.open

        def read_bytes(path: Path) -> bytes:
            if path.name.startswith(f".{destination.name}."):
                raise OSError(errno.EIO, "synthetic read error")
            return real_read(path)

        def refused(place: object, flags: int, *args: object) -> int:
            if Path(str(place)) == destination:
                raise PermissionError(errno.EACCES, "denied")
            return real_open(place, flags, *args)

        module = "garmin_running_data_normalizer.diagnostics.support_bundle"
        cases = {
            "the folder": patch(f"{module}.tempfile.mkstemp", side_effect=PermissionError("denied")),
            "the new file": patch(f"{module}.os.open", side_effect=refused),
            "the copy": patch.object(Path, "read_bytes", read_bytes),
        }
        for label, broken in cases.items():
            with self.subTest(case=label):
                with patch(f"{module}.os.link", side_effect=OSError(errno.EXDEV, "no hard links here")), broken:
                    self.assert_code("SUPPORT_BUNDLE_NOT_WRITTEN", make_support_bundle, self.output)
                self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["output"])

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


class EarlierOutputTest(OutputTestCase):
    """Outputs of earlier runs and of other versions (stage B5b)."""

    def test_the_earlier_outputs_are_those_that_are_there(self) -> None:
        other = self.root / "other"
        shutil.copytree(self.output, other)
        (self.root / "a-file").write_bytes(b"synthetic")
        remembered = [str(other), str(self.root / "gone"), str(self.root / "a-file"), str(self.output)]
        if can_symlink(self.root):
            link = self.root / "link"
            link.symlink_to(self.output, target_is_directory=True)
            remembered.insert(1, str(link))
        # Newest first; not found, not a folder, a link, and this launch's
        # output are left out.
        self.assertEqual(earlier_outputs(remembered, None), [other, self.output])
        self.assertEqual(earlier_outputs(remembered, self.output), [other])
        self.assertEqual(earlier_outputs([], None), [])

    def test_the_summary_of_an_output_gives_what_a_run_is_compared_with(self) -> None:
        summary = json.loads((self.output / "run_summary.json").read_text(encoding="utf-8"))
        answer = output_summary(self.output)
        self.assertEqual(
            answer,
            {
                "name": "output",
                "families": {family: details["record_count"] for family, details in summary["family_results"].items()},
                "snapshots": False,
                "version": summary["product_version"],
                "run_all_version": summary["run_all_version"],
                "timezone": "Asia/Tokyo",
            },
        )
        self.assertEqual(answer["families"]["activities"], 1)
        path = self.output / "run_summary.json"
        # Words in the place of a version or a timezone are not passed on.
        for key, value in (("product_version", "1.7.1\nsynthetic"), ("local_timezone", "../synthetic"), ("run_all_version", True)):
            with self.subTest(key=key):
                path.write_text(json.dumps({**summary, key: value}), encoding="utf-8")
                answer = output_summary(self.output)
                self.assertIsNone(answer[{"product_version": "version", "local_timezone": "timezone", "run_all_version": "run_all_version"}[key]])
        path.write_text(json.dumps({**summary, "snapshot_lifecycle": {}}), encoding="utf-8")
        self.assertTrue(output_summary(self.output)["snapshots"])
        # A summary that is not of this form gives nothing.
        broken = (
            b"not json",
            json.dumps([summary]).encode("utf-8"),
            json.dumps({**summary, "family_results": []}).encode("utf-8"),
            json.dumps({**summary, "family_results": {"Activities": {"record_count": 1}}}).encode("utf-8"),
            json.dumps({**summary, "family_results": {"activities": {"record_count": -1}}}).encode("utf-8"),
            json.dumps({**summary, "family_results": {"activities": {"record_count": "1"}}}).encode("utf-8"),
            # A value more than 256 deep, and JSON that Python 3.11 cannot read
            # by recursion, as every version reads them (stage E2d).
            (json.dumps(summary)[:-1] + ', "padding": ' + "[" * 300 + "]" * 300 + "}").encode("utf-8"),
            b"[" * 30_000 + b"]" * 30_000,
        )
        for data in broken:
            with self.subTest(data=data[:30]):
                path.write_bytes(data)
                self.assertIsNone(output_summary(self.output))
        path.unlink()
        self.assertIsNone(output_summary(self.output))
        with patch.object(outputs, "MAX_SUMMARY_BYTES", 10):
            path.write_text(json.dumps(summary), encoding="utf-8")
            self.assertIsNone(output_summary(self.output))

    def test_an_output_of_1_3_is_checked_and_told_by_its_version(self) -> None:
        as_v1_3(self.output)
        # As the output before a run, it names its version and the version of
        # its checks, so that the page never compares a run with it.
        summary = output_summary(self.output)
        self.assertEqual((summary["version"], summary["run_all_version"]), ("1.3.3", 1))
        answer = check_output(self.output)
        self.assertEqual(answer["handoff"]["status"], "PASS")
        self.assertEqual((answer["doctor"]["legacy"], answer["doctor"]["product_version"]), (True, "1.3.3"))
        self.assert_code("SUPPORT_BUNDLE_AUTHORITY_INVALID", make_support_bundle, self.output)

    def test_an_output_of_another_version_is_told_with_that_version(self) -> None:
        written = json.loads((self.output / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
        as_release(self.output, "1.2.1", tuple(written))
        for action in (check_output, make_support_bundle):
            with self.subTest(action=action.__name__):
                with self.assertRaises(OutputActionError) as caught:
                    action(self.output)
                self.assertEqual((caught.exception.code, caught.exception.version), ("OUTPUT_OTHER_VERSION", "1.2.1"))
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
        # A file shown where it is saved (stage B5a): selected in Finder, in
        # File Explorer, and elsewhere its folder.
        bundle = self.root / "output-support-bundle.zip"
        self.assertEqual(open_command(bundle, folder=False, platform="darwin", reveal=True), [MACOS_OPEN, "-R", str(bundle)])
        # File Explorer takes /select only with the place alone in quotes,
        # also for a place with a space, which a list would quote whole.
        spaced = PureWindowsPath(r"D:\Running Data\GarminRunningData\out-support-bundle.zip")
        explorer = str(self.root / "Windows" / "explorer.exe")
        with patch.dict(os.environ, {"SystemRoot": str(self.root / "Windows")}):
            command = open_command(spaced, folder=False, platform="win32", reveal=True)
            self.assertEqual(command, f'"{explorer}" /select,"{spaced}"')
            self.assertNotEqual(command, subprocess.list2cmdline([explorer, f"/select,{spaced}"]))
            # A place with quotes, which Windows never names, is not put in it.
            self.assert_code(
                "OPEN_FAILED",
                lambda: open_command(PureWindowsPath('C:\\a"b\\x.zip'), folder=False, platform="win32", reveal=True),
            )
        with patch.object(outputs.shutil, "which", return_value="/usr/bin/xdg-open"):
            self.assertEqual(open_command(bundle, folder=False, platform="linux", reveal=True), ["/usr/bin/xdg-open", str(self.root)])
        with patch.object(outputs.shutil, "which", return_value=None):
            self.assert_code(
                "OPEN_NOT_AVAILABLE",
                lambda: open_command(folder, folder=False, platform="linux"),
            )

    def test_only_the_known_targets_can_be_opened(self) -> None:
        # The output folder, its START_HERE.md, and from stage B5a the Support
        # Bundle that the server made and the External-safe Pack of the output.
        self.assertEqual(OPEN_TARGETS, ("folder", "start_here", "bundle", "safe_pack"))
        bundle = Path(make_support_bundle(self.output)["path"])
        pack = self.output / "analysis" / "external_safe_handoff.zip"
        with patch.object(outputs, "_launch") as launch:
            open_output(self.output, "folder")
            open_output(self.output, "start_here")
            # No bundle made by the server, and no pack made by the run.
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "bundle")
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "safe_pack")
            open_output(self.output, "bundle", bundle)
            pack.write_bytes(b"synthetic pack")
            open_output(self.output, "safe_pack")
            self.assertEqual(
                launch.call_args_list,
                [
                    call(self.output, folder=True, reveal=False),
                    call(self.output / "START_HERE.md", folder=False, reveal=False),
                    call(bundle, folder=False, reveal=True),
                    call(pack, folder=False, reveal=True),
                ],
            )
            for target in (None, "", "Folder", "START_HERE.md", "../folder", ["folder"], {"target": "folder"}, 1, str(bundle)):
                with self.subTest(target=target):
                    self.assert_code("REQUEST_INVALID", open_output, self.output, target, bundle)
            # A link or a folder in the place of a file to show is not shown.
            pack.unlink()
            pack.mkdir()
            self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "safe_pack")
            if can_symlink(self.root):
                bundle.unlink()
                bundle.symlink_to(self.output / "START_HERE.md")
                self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "bundle", bundle)
                # Nor a pack in a folder that a link put in the place of
                # analysis.
                elsewhere = self.root / "elsewhere"
                elsewhere.mkdir()
                (elsewhere / "external_safe_handoff.zip").write_bytes(b"synthetic pack")
                shutil.rmtree(self.output / "analysis")
                (self.output / "analysis").symlink_to(elsewhere, target_is_directory=True)
                self.assert_code("OUTPUT_NOT_AVAILABLE", open_output, self.output, "safe_pack")
            self.assertEqual(launch.call_count, 4)

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
