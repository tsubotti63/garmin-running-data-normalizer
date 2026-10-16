"""Stage A5b-1: every stop of the CLI says what happened and the next step of
its code, from one table (synthetic data only)."""

from __future__ import annotations

import ast
import contextlib
import errno
import importlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input, render_doctor_human
from garmin_running_data_normalizer.run_all import RunAllError, run_all

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/garmin_running_data_normalizer"
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
CODE = re.compile(r"[A-Z][A-Z0-9_]{3,}")
STAMP = "2030-01-01T02:00:00+00:00"

# The error classes and where their code is: the position of the argument,
# with the default code of the class when there is one.
ARGUMENT_CODES = {
    "RunAllError": (0, None),
    "GoldenPathError": (1, None),
    "DoctorError": (0, None),
    "SupportBundleError": (0, None),
    "SnapshotStoreError": (1, "SNAPSHOT_LIFECYCLE_FAILED"),
    "SnapshotMergeError": (1, "SNAPSHOT_LIFECYCLE_FAILED"),
    "SnapshotBuildOutputError": (0, None),
    "OutputLocationError": (0, None),
    # The class of a store error that verification_error is given.
    "error_class": (1, "SNAPSHOT_LIFECYCLE_FAILED"),
}
# The position of the message in the arguments.
MESSAGE_ARGUMENTS = {
    "RunAllError": 1,
    "GoldenPathError": 0,
    "DoctorError": 1,
    "SupportBundleError": 1,
    "SnapshotStoreError": 0,
    "SnapshotMergeError": 0,
    "error_class": 0,
    "StandaloneHandoffError": 0,
    "MixedExportsError": 0,
    "CorruptArchiveError": 0,
    "ExportTooLargeError": 0,
    "ActivitiesNotReadableError": 0,
}
FIXED_CODES = {
    "ActivitiesNotReadableError": "ACTIVITIES_EMPTY",
    "StandaloneHandoffError": "HANDOFF_INVALID",
    "MixedExportsError": "INPUT_MULTIPLE_EXPORTS",
    "CorruptArchiveError": "INPUT_ZIP_CORRUPT",
    "ExportTooLargeError": "INPUT_TOO_LARGE",
    "TempSpaceError": "TEMP_SPACE_INSUFFICIENT",
    "InputNotReadableError": "INPUT_NOT_READABLE",
    "TimezoneDataUnavailableError": "TIMEZONE_DATA_UNAVAILABLE",
    "TimezoneNameInvalidError": "TIMEZONE_INVALID",
}


def stops_module() -> Any:
    # The table is read where it is used, so that each test fails on its own
    # on a version without it.
    return importlib.import_module("garmin_running_data_normalizer.stops")


def sources() -> list[tuple[str, ast.Module]]:
    """The modules of the package that the CLI runs: all but the GUI."""
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        if not relative.startswith("gui/"):
            found.append((relative, ast.parse(path.read_text(encoding="utf-8"))))
    return found


def module_name(relative: str) -> str:
    return "garmin_running_data_normalizer." + relative.removesuffix(".py").replace("/", ".")


def called(node: ast.Call) -> str:
    return node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")


def codes_in_the_package() -> set[str]:
    """Every code with which a command of the CLI can stop."""
    codes: set[str] = set()
    for relative, tree in sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = called(node)
                if name in FIXED_CODES:
                    codes.add(FIXED_CODES[name])
                if name in ARGUMENT_CODES:
                    index, default = ARGUMENT_CODES[name]
                    keyword = next((item.value for item in node.keywords if item.arg == "code"), None)
                    value = keyword or (node.args[index] if len(node.args) > index else None)
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        codes.add(value.value)
                    elif value is None and default is not None:
                        codes.add(default)
                if name == "_stop" and node.args and isinstance(node.args[0], ast.Constant):
                    codes.add(node.args[0].value)
            # The codes that the functions of the place of an output return.
            if isinstance(node, ast.FunctionDef) and node.name in ("write_error_code", "path_error_code"):
                for item in ast.walk(node):
                    if isinstance(item, ast.Constant) and isinstance(item.value, str) and CODE.fullmatch(item.value):
                        codes.add(item.value)
            # Codes kept in constants.
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                target = node.targets[0]
                if (
                    isinstance(target, ast.Name)
                    and (target.id.endswith("_ERROR_CODE") or target.id == "DATA_NEEDS_RUN_ALL")
                    and isinstance(node.value.value, str)
                ):
                    codes.add(node.value.value)
    return codes


def messages_in_the_package() -> list[tuple[str, str]]:
    """The fixed texts that the stops of the package give as their message:
    literals, the literal parts of f-strings and sums, and module constants."""
    found: list[tuple[str, str]] = []
    for relative, tree in sources():
        module = importlib.import_module(module_name(relative))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or called(node) not in MESSAGE_ARGUMENTS:
                continue
            index = MESSAGE_ARGUMENTS[called(node)]
            if len(node.args) <= index:
                continue
            value = node.args[index]
            where = f"{relative}:{node.lineno}"
            parts: list[ast.AST] = [value]
            while parts:
                part = parts.pop()
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    found.append((where, part.value))
                elif isinstance(part, ast.JoinedStr):
                    parts.extend(part.values)
                elif isinstance(part, ast.BinOp):
                    parts.extend((part.left, part.right))
                elif isinstance(part, ast.Name) and isinstance(getattr(module, part.id, None), str):
                    found.append((where, getattr(module, part.id)))
    return found


def cli(*args: object) -> tuple[int, str]:
    stderr = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
        code = runner.main([str(arg) for arg in args])
    return code, stderr.getvalue()


class TableTest(unittest.TestCase):
    def test_every_code_of_a_stop_is_in_the_table_and_every_entry_is_used(self) -> None:
        table = stops_module().STOPS
        codes = codes_in_the_package()
        self.assertEqual(sorted(codes - set(table)), [], "codes without an entry")
        self.assertEqual(sorted(set(table) - codes), [], "entries that no stop uses")

    def test_the_texts_are_fixed_and_say_what_happened_and_what_to_do(self) -> None:
        for code, stop in stops_module().STOPS.items():
            with self.subTest(code=code):
                self.assertTrue(CODE.fullmatch(code))
                self.assertTrue(stop.what and stop.next_step)
                # The meaning has no ";", which separates the next step.
                self.assertNotIn(";", stop.what)
                for text in stop:
                    self.assertNotIn("{", text)
                    self.assertNotIn("}", text)
                    self.assertFalse(text.endswith((".", ";", " ")), text)
                    # No place of the computer: no path from a root or a drive.
                    self.assertIsNone(re.search(r"(^|\s)(/[A-Za-z]|[A-Za-z]:\\)", text), text)

    def test_messages_say_what_happened_without_a_next_step(self) -> None:
        stops = stops_module()
        found = messages_in_the_package()
        self.assertGreater(len(found), 100)
        next_steps = {stop.next_step for stop in stops.STOPS.values()}
        for where, message in found:
            with self.subTest(where=where):
                self.assertNotIn(";", message)
                for step in next_steps:
                    self.assertNotIn(step, message)
        from garmin_running_data_normalizer.output_location import MESSAGES
        from garmin_running_data_normalizer.run_all import input_not_readable_message
        from garmin_running_data_normalizer.snapshot.store import NOTICE_MESSAGES, store_not_readable_message

        for message in (
            *MESSAGES.values(),
            input_not_readable_message(),
            input_not_readable_message(["a", "b"]),
            store_not_readable_message(),
            store_not_readable_message([""]),
        ):
            with self.subTest(message=message):
                self.assertNotIn(";", message)
        # The place of an output says what the table says it means.
        for code, message in MESSAGES.items():
            self.assertEqual(message, stops.STOPS[code].what, code)
        # A notice of the same problem gives the same meaning and next step.
        self.assertEqual(NOTICE_MESSAGES, {code: stops.stop_text(code) for code in NOTICE_MESSAGES})


class StopLineTest(unittest.TestCase):
    def assert_stop(self, code: str, args: tuple[object, ...], root: Path) -> str:
        exit_code, stderr = cli(*args)
        self.assertEqual(exit_code, 2, stderr)
        lines = stderr.splitlines()
        self.assertEqual(len(lines), 1, stderr)
        line = lines[0]
        prefix, suffix = f"ERROR [{code}]: ", f"; {stops_module().STOPS[code].next_step}"
        self.assertTrue(line.startswith(prefix), line)
        self.assertTrue(line.endswith(suffix), line)
        what = line[len(prefix):-len(suffix)]
        self.assertTrue(what)
        self.assertNotIn(";", what)
        # No path of the computer is named: not the synthetic input, the
        # output, or the store.
        self.assertNotIn(str(root), line)
        self.assertNotIn(root.name, line)
        return what

    def test_the_stops_of_every_kind_of_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            done = root / "done"
            self.assertEqual(cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", done)[0], 0)
            plain = root / "plain.txt"
            plain.write_text("synthetic", encoding="utf-8")
            broken = root / "broken.zip"
            broken.write_bytes(b"not a ZIP file")
            empty = root / "empty"
            empty.mkdir()
            mixed = root / "mixed"
            for name, activity_id in (("export-a", "SYNTHETIC-A1"), ("export-b", "SYNTHETIC-B1")):
                fitness = mixed / name / "DI_CONNECT" / "DI-Connect-Fitness"
                fitness.mkdir(parents=True)
                (fitness / "synthetic_summarizedActivities.json").write_text(
                    json.dumps([{"summarizedActivitiesExport": [{"activityId": activity_id, "startTimeGmt": 1893456000000}]}]),
                    encoding="utf-8",
                )
            activities = root / "activities"
            shutil.copytree(SYNTHETIC_EXPORT, activities)
            next(activities.rglob("*summarizedActivities.json")).write_text("{", encoding="utf-8")
            store = root / "store"
            self.assertEqual(cli("snapshot", "init", "--store", store, "--account", "synthetic")[0], 0)
            register = (
                "snapshot", "register", "--store", store, "--input", SYNTHETIC_EXPORT, "--label", "S1",
                "--requested-at", STAMP, "--downloaded-at", STAMP, "--observed-at", STAMP,
            )
            existing = root / "existing.zip"
            existing.write_bytes(b"x")
            cases = [
                ("OUTPUT_EXISTS", ("run-all", "--input", SYNTHETIC_EXPORT, "--output", done)),
                ("INPUT_NOT_DIRECTORY", ("run-all", "--input", plain, "--output", root / "o1")),
                ("OUTPUT_INSIDE_INPUT", ("run-all", "--input", activities, "--output", activities / "o2")),
                ("OUTPUT_NAME_INVALID", ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / ".hidden")),
                ("OUTPUT_PARENT_NOT_FOUND", ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "missing" / "o3")),
                ("INPUT_ZIP_CORRUPT", ("run-all", "--input", broken, "--output", root / "o4")),
                ("INPUT_MULTIPLE_EXPORTS", ("run-all", "--input", mixed, "--output", root / "o5")),
                ("TIMEZONE_INVALID", ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o6", "--timezone", "Mars")),
                ("ACTIVITIES_NOT_FOUND", ("run-all", "--input", empty, "--output", root / "o7")),
                ("GOLDEN_PATH_DATA_NEEDS_RUN_ALL", ("normalize-activities", "--input", activities, "--output", root / "o8")),
                ("SNAPSHOT_LIFECYCLE_FAILED", register),
                ("HANDOFF_INVALID", ("validate-handoff", "--input", empty)),
                ("SUPPORT_BUNDLE_PATH_UNSAFE", ("support-bundle", "--run-output", done, "--output", existing)),
            ]
            for code, args in cases:
                with self.subTest(code=code):
                    self.assert_stop(code, args, root)
            (store / ".single-writer.lock").write_text("424242\n", encoding="ascii")
            what = self.assert_stop("SNAPSHOT_STORE_LOCKED", (*register, "--confirm-complete"), root)
            self.assertIn("pid 424242", what)

    def test_a_stop_that_no_code_describes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(runner, "run_all", side_effect=RuntimeError(str(root))):
                what = self.assert_stop("RUN_ALL_FAILED", ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o"), root)
            # Until stage A5b, the next step was to verify the input and
            # output contract.
            self.assertEqual(what, "Run-All stopped unexpectedly")
            with mock.patch.object(runner, "run_activities", side_effect=RuntimeError(str(root))):
                self.assert_stop("GOLDEN_PATH_FAILED", ("normalize-activities", "--input", SYNTHETIC_EXPORT, "--output", root / "o"), root)
            with mock.patch.object(runner, "validate_standalone_handoff", side_effect=RuntimeError(str(root))):
                what = self.assert_stop("COMMAND_FAILED", ("validate-handoff", "--input", root), root)
            self.assertEqual(what, "validate-handoff stopped unexpectedly")


class NoOutputTest(unittest.TestCase):
    def test_every_stop_of_run_all_comes_before_its_output_is_published(self) -> None:
        source = (PACKAGE / "run_all.py").read_text(encoding="utf-8")
        function = next(
            node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name == "run_all"
        )
        publish = next(
            node.lineno for node in ast.walk(function) if isinstance(node, ast.Call) and called(node) == "_publish_outputs"
        )
        raises = [node.lineno for node in ast.walk(function) if isinstance(node, ast.Raise)]
        self.assertTrue(raises)
        self.assertLess(max(raises), publish)

    def test_internal_stops_leave_no_output(self) -> None:
        cases = {
            # The last stop before the output is published.
            "OUTPUT_EXPERIENCE_FAILED": "garmin_running_data_normalizer.output_experience.render_output_experience_artifacts",
            "ACTIVITIES_NORMALIZATION_FAILED": "garmin_running_data_normalizer.run_all.normalize_activities",
        }
        for code, function in cases.items():
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                with mock.patch(function, side_effect=ValueError("synthetic")):
                    with self.assertRaises(RunAllError) as raised:
                        run_all(SYNTHETIC_EXPORT, parent / "output")
                self.assertEqual(raised.exception.code, code)
                self.assertTrue(stops_module().STOPS[code].next_step.startswith("no output was written"))
                # No output, and no hidden staging folder.
                self.assertEqual(list(parent.iterdir()), [])

    def test_the_golden_path_takes_back_what_it_moved_into_an_empty_folder(self) -> None:
        # The three files are moved one at a time; stop at the second and at
        # the third.
        for stop_at in (2, 3):
            with self.subTest(stop_at=stop_at), tempfile.TemporaryDirectory() as directory:
                output = Path(directory).resolve() / "output"
                output.mkdir()
                real = Path.rename
                moved: list[str] = []

                def rename(self: Path, target: Any) -> Any:
                    if Path(target).parent == output:
                        if len(moved) + 1 == stop_at:
                            raise OSError(errno.EIO, "synthetic")
                        moved.append(Path(target).name)
                    return real(self, target)

                with mock.patch.object(Path, "rename", rename):
                    with self.assertRaises(runner.GoldenPathError) as raised:
                        runner.run_activities(SYNTHETIC_EXPORT, output)
                self.assertEqual(raised.exception.code, "OUTPUT_PUBLISH_FAILED")
                self.assertEqual(len(moved), stop_at - 1)
                # The folder that was there stays, empty again: no part of an
                # output, and no hidden staging folder.
                self.assertTrue(output.is_dir())
                self.assertEqual(list(output.iterdir()), [])


class DoctorNextStepTest(unittest.TestCase):
    def test_the_report_of_a_person_gives_the_next_steps_in_words(self) -> None:
        stops = stops_module()
        with tempfile.TemporaryDirectory() as directory:
            report = doctor_input(Path(directory))
        human = render_doctor_human(report)
        self.assertIn(
            f"Finding: ACTIVITIES_NOT_FOUND (next: {stops.NEXT_ACTIONS['SELECT_EXPORT_WITH_ACTIVITIES']})", human
        )
        self.assertIn(f"Next: CORRECT_PRE_RUN_CONDITION ({stops.NEXT_ACTIONS['CORRECT_PRE_RUN_CONDITION']})", human)

    def test_every_next_action_of_the_reports_has_words(self) -> None:
        source = (PACKAGE / "diagnostics/doctor.py").read_text(encoding="utf-8")
        used = set(re.findall(r'next_action_id="([A-Z_]+)"', source))
        used |= set(re.findall(r'doctor_next_action_id = "([A-Z_]+)"', source))
        used |= set(re.findall(r'"(CORRECT_PRE_RUN_CONDITION|RUN_ALL)"', source))
        self.assertEqual(sorted(used), sorted(stops_module().NEXT_ACTIONS))
        for action, text in stops_module().NEXT_ACTIONS.items():
            self.assertNotIn("{", text, action)
            self.assertFalse(text.endswith("."), action)


if __name__ == "__main__":
    unittest.main()
