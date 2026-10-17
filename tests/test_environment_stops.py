"""Stops for problems of the environment, not of the data, have a code and a
next step (stage A3d-3a): the place of the output, a folder or file of the
input that this app may not open, which stops a run instead of being passed
over, an input that changes during a run, and every stop of the Golden Path."""

from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_input
from garmin_running_data_normalizer.gui.runs import RunManager
from garmin_running_data_normalizer.intake.discovery import InputChangedError
from garmin_running_data_normalizer.intake.source import (
    ExportSource,
    InputNotReadableError,
    walk_paths,
)
from garmin_running_data_normalizer.output_location import MESSAGES
from garmin_running_data_normalizer.run_all import RunAllError, run_all
def stop(code: str):
    """The entry of a code in the table of stops (stage A5b), read where it is
    used, so that each test fails on its own on a version without the table."""
    from garmin_running_data_normalizer.stops import STOPS

    return STOPS[code]
from garmin_running_data_normalizer.runner import GoldenPathError, main, run_activities
from garmin_running_data_normalizer.snapshot import (
    SnapshotLifecycleError,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    snapshot_status,
)
from tests.test_items_and_containers import (
    ACTIVITIES,
    GEAR,
    UDS,
    UDS_ROW,
    activities,
    export,
)
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, gear
from tests.test_snapshot_unreadable_files import register

UDS_FOLDER = "DI-Connect-Aggregator"
# A folder name that no output, log, or report may hold.
PRIVATE_FOLDER = "synthetic-private-folder"
REAL_PERMISSIONS = unittest.skipIf(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    "permission bits do not stop this user here",
)
REAL_SYMLINKS = unittest.skipIf(os.name == "nt", "symbolic links need privileges on Windows")


def files() -> dict[str, Any]:
    return {
        ACTIVITIES: activities(_activity("A1"), _activity("A2")),
        GEAR: [{"gearDTOS": [gear(1, "Shoe")]}],
        UDS: [UDS_ROW],
    }


@contextlib.contextmanager
def closed_folders(*names: str, error: type[OSError] = PermissionError) -> Iterator[None]:
    """Make the folders of these names fail to open, as the operating system's
    privacy settings make them, on any system."""
    real = os.scandir

    def scandir(path: Any = ".") -> Any:
        if Path(path).name in names:
            raise error(errno.EACCES if error is PermissionError else errno.ENOENT, "denied", str(path))
        return real(path)

    with mock.patch("garmin_running_data_normalizer.intake.source.os.scandir", side_effect=scandir):
        yield


@contextlib.contextmanager
def closed_files(suffix: str, error: type[OSError] = PermissionError) -> Iterator[None]:
    real = ExportSource.digest

    def digest(self: ExportSource, item: Any) -> tuple[str, int]:
        if item.relative_path.endswith(suffix):
            raise error(errno.EACCES if error is PermissionError else errno.ENOENT, "denied")
        return real(self, item)

    with mock.patch.object(ExportSource, "digest", digest):
        yield


@contextlib.contextmanager
def permissions(path: Path, mode: int) -> Iterator[None]:
    old = path.stat().st_mode & 0o777
    path.chmod(mode)
    try:
        yield
    finally:
        path.chmod(old)


def cli(*args: object) -> tuple[int, str]:
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
        code = main([str(arg) for arg in args])
    return code, stderr.getvalue().strip()


class WalkTest(unittest.TestCase):
    def test_the_walk_lists_what_rglob_lists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "a" / "b").mkdir(parents=True)
            (base / "a" / "b" / "c.json").write_text("{}")
            (base / "a" / "d.fit").write_bytes(b"x")
            (base / "e.txt").write_text("e")
            if os.name != "nt":
                (base / "link-to-a").symlink_to(base / "a", target_is_directory=True)
                (base / "link-to-e").symlink_to(base / "e.txt")
            paths, not_opened = walk_paths(base)
            self.assertEqual(sorted(paths), sorted(base.rglob("*")))
            self.assertEqual(not_opened, [])

    def test_a_folder_that_cannot_be_opened_is_named_where_rglob_passes_over_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "open" / "closed").mkdir(parents=True)
            (base / "open" / "closed" / "inside.json").write_text("{}")
            with closed_folders("closed"):
                paths, not_opened = walk_paths(base)
                # rglob passes over it without a word, which is why the
                # input is not read with it.
                self.assertNotIn(base / "open" / "closed" / "inside.json", list(base.rglob("*")))
            self.assertEqual(not_opened, [base / "open" / "closed"])
            self.assertNotIn(base / "open" / "closed" / "inside.json", paths)

    def test_system_and_os_metadata_folders_that_cannot_be_opened_are_passed_over(self) -> None:
        names = ("System Volume Information", "$RECYCLE.BIN", ".Spotlight-V100", ".Trashes", "__MACOSX")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name in names:
                (base / name).mkdir()
            # Finder's metadata at any depth; a system folder's name deeper
            # in the input is like any other folder.
            (base / "deeper" / "__MACOSX").mkdir(parents=True)
            (base / "deeper" / ".Trashes").mkdir()
            with closed_folders(*names):
                self.assertEqual(walk_paths(base)[1], [base / "deeper" / ".Trashes"])

    def test_a_folder_that_went_away_while_it_was_listed_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "gone").mkdir()
            with closed_folders("gone", error=FileNotFoundError):
                with self.assertRaises(FileNotFoundError):
                    walk_paths(base)


class InputNotReadableTest(unittest.TestCase):
    def run_stops(self, source: Path, output: Path) -> RunAllError:
        with self.assertRaises(RunAllError) as raised:
            run_all(source, output)
        self.assertFalse(output.exists())
        return raised.exception

    def test_a_folder_that_cannot_be_opened_stops_the_run_and_is_named(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            with closed_folders(UDS_FOLDER):
                error = self.run_stops(source, root / "output")
            self.assertEqual(error.code, "INPUT_NOT_READABLE")
            self.assertEqual(error.places, [UDS_FOLDER])
            # The message names no place; only where the run starts does.
            self.assertNotIn(UDS_FOLDER, error.safe_message)
            # It says what happened; the CLI adds the next step (stage A5b).
            self.assertEqual(error.safe_message, stop("INPUT_NOT_READABLE").what)
            with closed_folders(UDS_FOLDER):
                code, message = cli("run-all", "--input", source, "--output", root / "cli-output")
            self.assertEqual(code, 2)
            self.assertEqual(
                message,
                "ERROR [INPUT_NOT_READABLE]: this app is not allowed to open a folder or file of the "
                f"input: {UDS_FOLDER}; {stop('INPUT_NOT_READABLE').next_step}",
            )

    def test_a_file_that_cannot_be_opened_stops_the_run_and_is_named(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            with closed_files("UDSFile_1.json"):
                error = self.run_stops(source, root / "output")
            self.assertEqual(error.code, "INPUT_NOT_READABLE")
            self.assertEqual(error.places, [UDS])

    def test_the_input_itself_and_several_places(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            with closed_folders("export"):
                self.assertEqual(self.run_stops(source, root / "output").places, [""])
                code, message = cli("run-all", "--input", source, "--output", root / "cli-output")
            self.assertIn("of the input: the input folder or ZIP file itself;", message)
            with closed_folders(UDS_FOLDER, "DI-Connect-Fitness"):
                error = self.run_stops(source, root / "output")
                code, message = cli("run-all", "--input", source, "--output", root / "cli-output")
            self.assertEqual(error.places, ["DI-Connect-Aggregator", "DI-Connect-Fitness"])
            self.assertIn("of the input: DI-Connect-Aggregator and 1 more;", message)

    def test_an_activities_folder_that_cannot_be_opened_is_not_a_missing_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            with closed_folders("DI-Connect-Fitness"):
                self.assertEqual(self.run_stops(source, root / "output").code, "INPUT_NOT_READABLE")

    def test_a_drive_with_a_system_folder_that_cannot_be_opened_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            drive = root / "drive"
            export(drive, "export", files())
            (drive / "System Volume Information").mkdir()
            with closed_folders("System Volume Information"):
                result = run_all(drive, root / "output")
            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")

    @REAL_PERMISSIONS
    def test_real_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            folder = source / UDS_FOLDER
            with permissions(folder, 0o000):
                error = self.run_stops(source, root / "output")
            self.assertEqual((error.code, error.places), ("INPUT_NOT_READABLE", [UDS_FOLDER]))
            with permissions(source / UDS, 0o000):
                self.assertEqual(self.run_stops(source, root / "output").places, [UDS])

    def test_the_check_before_a_run_tells_it_without_the_place(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            (source / UDS_FOLDER / PRIVATE_FOLDER).mkdir()
            with closed_folders(PRIVATE_FOLDER):
                report = doctor_input(source)
            codes = [item["code"] for item in report["findings"]]
            self.assertIn("INPUT_NOT_READABLE", codes)
            [finding] = [item for item in report["findings"] if item["code"] == "INPUT_NOT_READABLE"]
            self.assertEqual(finding["safe_message_id"], "INPUT_FOLDER_OR_FILE_CANNOT_BE_OPENED")
            self.assertEqual(finding["next_action_id"], "ALLOW_INPUT_ACCESS_OR_SELECT_EXPORT_FOLDER")
            self.assertNotIn(PRIVATE_FOLDER, json.dumps(report))

    def test_a_registration_stops_on_a_folder_that_cannot_be_opened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            store = root / "store"
            initialize_store(store, ACCOUNT)
            with closed_folders(UDS_FOLDER):
                with self.assertRaises(InputNotReadableError) as raised:
                    register(store, source)
                code, message = cli(
                    "snapshot", "register", "--store", store, "--input", source, "--label", "S1",
                    "--requested-at", "2030-01-01T02:00:00+00:00",
                    "--downloaded-at", "2030-01-01T02:00:00+00:00",
                    "--observed-at", "2030-01-01T02:00:00+00:00", "--confirm-complete",
                )
            self.assertEqual(raised.exception.places, [UDS_FOLDER])
            self.assertEqual(code, 2)
            self.assertTrue(message.startswith("ERROR [INPUT_NOT_READABLE]: "), message)
            self.assertEqual(snapshot_status(store)["snapshot_count"], 0)


class InputChangedTest(unittest.TestCase):
    def test_every_family_stops_with_input_changed(self) -> None:
        targets = (
            "garmin_running_data_normalizer.run_all.normalize_uds",
            "garmin_running_data_normalizer.run_all.normalize_hill_score",
            "garmin_running_data_normalizer.run_all.normalize_sleep_daily_assets",
            "garmin_running_data_normalizer.run_all._repaired_text_files",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            for index, target in enumerate(targets):
                with self.subTest(target=target.rsplit(".", 1)[-1]):
                    with mock.patch(target, side_effect=InputChangedError("changed")):
                        with self.assertRaises(RunAllError) as raised:
                            run_all(source, root / f"output-{index}")
                    self.assertEqual(raised.exception.code, "INPUT_CHANGED")

    def test_a_file_that_went_away_is_a_changed_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            with closed_files("UDSFile_1.json", error=FileNotFoundError):
                with self.assertRaises(RunAllError) as raised:
                    run_all(source, root / "output")
            self.assertEqual(raised.exception.code, "INPUT_CHANGED")
            with closed_folders(UDS_FOLDER, error=FileNotFoundError):
                with self.assertRaises(RunAllError) as raised:
                    run_all(source, root / "output")
            self.assertEqual(raised.exception.code, "INPUT_CHANGED")


class OutputPlaceTest(unittest.TestCase):
    def test_a_place_that_cannot_be_written_stops_before_the_input_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            for error, code in (
                (PermissionError(errno.EACCES, "denied"), "OUTPUT_PARENT_NOT_WRITABLE"),
                (OSError(errno.ENOSPC, "full"), "OUTPUT_SPACE_INSUFFICIENT"),
                (OSError(errno.ENAMETOOLONG, "long"), "OUTPUT_NAME_INVALID"),
            ):
                with self.subTest(code=code):
                    with (
                        mock.patch("garmin_running_data_normalizer.output_location.tempfile.mkdtemp", side_effect=error),
                        mock.patch(
                            "garmin_running_data_normalizer.run_all.read_export",
                            side_effect=AssertionError("the input was read"),
                        ),
                    ):
                        with self.assertRaises(RunAllError) as raised:
                            run_all(source, root / "output")
                    self.assertEqual(raised.exception.code, code)
                    self.assertEqual(raised.exception.safe_message, MESSAGES[code])

    @REAL_PERMISSIONS
    def test_real_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            parent = root / "parent"
            parent.mkdir()
            with permissions(parent, 0o555):
                code, message = cli("run-all", "--input", source, "--output", parent / "output")
                self.assertEqual(list(parent.iterdir()), [])
            self.assertEqual(code, 2)
            self.assertTrue(message.startswith("ERROR [OUTPUT_PARENT_NOT_WRITABLE]: "), message)

    def test_a_folder_for_the_output_that_does_not_exist_is_not_made(self) -> None:
        # Until stage A5a, Run-All made the missing folders above the output
        # when it wrote; the folder for the output must exist now, as in the
        # GUI, so that a mistyped path makes no folders.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            with self.assertRaises(RunAllError) as raised:
                run_all(source, root / "new" / "deeper" / "output")
            self.assertEqual(raised.exception.code, "OUTPUT_PARENT_NOT_FOUND")
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["export"])

    @unittest.skipIf(os.name == "nt", "Windows refuses such a name in other ways, which the GUI tests cover")
    def test_a_name_too_long_for_the_system(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            for command in ("run-all", "normalize-activities"):
                with self.subTest(command=command):
                    code, message = cli(command, "--input", source, "--output", root / ("x" * 300))
                    self.assertEqual(code, 2)
                    self.assertTrue(message.startswith("ERROR [OUTPUT_NAME_INVALID]: "), message)

    def test_writing_the_output_fails_with_its_cause(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            for index, (error, code) in enumerate(
                (
                    (OSError(errno.ENOSPC, "full"), "OUTPUT_SPACE_INSUFFICIENT"),
                    (PermissionError(errno.EACCES, "denied"), "OUTPUT_PARENT_NOT_WRITABLE"),
                    (OSError(errno.ENAMETOOLONG, "long"), "OUTPUT_PATH_TOO_LONG"),
                    (OSError(errno.EIO, "broken"), "OUTPUT_PUBLISH_FAILED"),
                )
            ):
                with self.subTest(code=code):
                    with mock.patch(
                        "garmin_running_data_normalizer.run_all._write_exclusive", side_effect=error
                    ):
                        with self.assertRaises(RunAllError) as raised:
                            run_all(source, root / f"output-{index}")
                    self.assertEqual(raised.exception.code, code)
                    self.assertFalse((root / f"output-{index}").exists())
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["export"])

    def test_a_snapshot_run_checks_its_output_before_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, export(root, "export", files()))
            with (
                mock.patch(
                    "garmin_running_data_normalizer.output_location.tempfile.mkdtemp",
                    side_effect=PermissionError(errno.EACCES, "denied"),
                ),
                mock.patch(
                    "garmin_running_data_normalizer.snapshot.lifecycle.build_approved_input",
                    side_effect=AssertionError("the Snapshots were built"),
                ),
            ):
                with self.assertRaises(RunAllError) as raised:
                    run_snapshot_all(store, root / "output")
            self.assertEqual(raised.exception.code, "OUTPUT_PARENT_NOT_WRITABLE")
            (root / "taken").mkdir()
            with self.assertRaises(RunAllError) as raised:
                run_snapshot_all(store, root / "taken")
            self.assertEqual(raised.exception.code, "OUTPUT_EXISTS")


class GoldenPathTest(unittest.TestCase):
    def stops(self, source: Path, output: Path) -> str:
        with self.assertRaises(GoldenPathError) as raised:
            run_activities(source, output)
        return raised.exception.code

    def test_every_stop_has_a_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            occupied = root / "occupied"
            occupied.mkdir()
            (occupied / "note.txt").write_text("x")
            cases = {
                "a missing input": (root / "missing", root / "o1", "INPUT_NOT_DIRECTORY"),
                "an output inside the input": (source, source / "out", "OUTPUT_INSIDE_INPUT"),
                "an output that holds files": (source, occupied, "OUTPUT_EXISTS"),
                "no Activities": (export(root, "no-activities", {UDS: [UDS_ROW]}), root / "o2", "ACTIVITIES_NOT_FOUND"),
                "no Activities records": (export(root, "empty", {ACTIVITIES: activities()}), root / "o3", "ACTIVITIES_EMPTY"),
            }
            data = {
                "a row without a usable identifier": activities(_activity("A1"), _activity("X", activityId=[1])),
                "an item that is not a record": activities(_activity("A1"), 5),
                "a value of another form": activities(_activity("A1", distance="far")),
                "text with a broken character": '[{"summarizedActivitiesExport": [{"activityId": "A1", "name": "\\ud83d", "startTimeGmt": 1893456000000}]}]',
                "an Activities file that cannot be read": "{not json",
            }
            for index, (name, value) in enumerate(data.items()):
                cases[name] = (export(root, f"data-{index}", {ACTIVITIES: value}), root / f"d{index}", "GOLDEN_PATH_DATA_NEEDS_RUN_ALL")
            for name, (source_path, output, code) in cases.items():
                with self.subTest(case=name):
                    self.assertEqual(self.stops(source_path, output), code)
            with closed_folders("DI-Connect-Fitness"):
                self.assertEqual(self.stops(source, root / "o4"), "INPUT_NOT_READABLE")
            code, message = cli("normalize-activities", "--input", root / "missing", "--output", root / "o5")
            self.assertEqual(code, 2)
            self.assertEqual(
                message,
                "ERROR [INPUT_NOT_DIRECTORY]: input must be an existing folder or ZIP file; "
                f"{stop('INPUT_NOT_DIRECTORY').next_step}",
            )

    @REAL_SYMLINKS
    def test_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            (root / "link").symlink_to(source, target_is_directory=True)
            (root / "out").mkdir()
            (root / "out-link").symlink_to(root / "out", target_is_directory=True)
            self.assertEqual(self.stops(root / "link", root / "o1"), "INPUT_SYMLINK")
            self.assertEqual(self.stops(source, root / "out-link"), "OUTPUT_SYMLINK")

    def test_a_stop_while_writing_leaves_no_part_of_the_output(self) -> None:
        from garmin_running_data_normalizer import runner

        real = runner.open_private_file

        def second_fails(path: Path, *args: Any, **kwargs: Any) -> Any:
            if path.name != "normalized_activities.json":
                raise OSError(errno.ENOSPC, "No space left on device")
            return real(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files())
            existing = root / "existing"
            existing.mkdir()
            existing.chmod(0o755)
            for output in (root / "new", existing):
                with self.subTest(output=output.name):
                    with mock.patch.object(runner, "open_private_file", side_effect=second_fails):
                        self.assertEqual(self.stops(source, output), "OUTPUT_SPACE_INSUFFICIENT")
            self.assertFalse((root / "new").exists())
            self.assertEqual(list(existing.iterdir()), [])
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["existing", "export"])
            # Both can be written afterwards; the folder that was there keeps
            # its permissions.
            for output in (root / "new", existing):
                self.assertEqual(run_activities(source, output)["status"], "PASS")
                self.assertEqual(len(list(output.iterdir())), 3)
            if os.name != "nt":
                self.assertEqual(existing.stat().st_mode & 0o777, 0o755)
                self.assertEqual((root / "new").stat().st_mode & 0o777, 0o700)


class GuiDetailTest(unittest.TestCase):
    def test_the_worker_names_the_place_and_the_manager_keeps_only_a_valid_one(self) -> None:
        run = mock.Mock()
        for message, detail in (
            ({"event": "failed", "code": "INPUT_NOT_READABLE", "place": "DI_CONNECT/x", "more": 2}, {"place": "DI_CONNECT/x", "more": 2}),
            ({"event": "failed", "code": "INPUT_NOT_READABLE", "place": "", "more": 0}, {"place": "", "more": 0}),
            ({"event": "failed", "code": "INPUT_NOT_READABLE", "place": "a\nb", "more": 0}, None),
            ({"event": "failed", "code": "INPUT_NOT_READABLE", "place": "x" * 5000, "more": 0}, None),
            ({"event": "failed", "code": "INPUT_NOT_READABLE", "place": "x", "more": True}, None),
            ({"event": "failed", "code": "INPUT_CHANGED"}, None),
        ):
            with self.subTest(message=str(message)[:60]):
                RunManager._apply(run, message)
                self.assertEqual(run.error_detail, detail)
                self.assertEqual(run.error_code, message["code"])


if __name__ == "__main__":
    unittest.main()
