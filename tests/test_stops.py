"""Stage A5b-1: every stop of the CLI says what happened and the next step of
its code, from one table. Stage A5b-2: the snapshot commands, the Support
Bundle, and the GUI's checks give the codes of the same problems in a run,
and the documents give the table (synthetic data only)."""

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
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input, render_doctor_human
from garmin_running_data_normalizer.intake.archive import ArchiveLimits
from garmin_running_data_normalizer.intake.discovery import read_export
from garmin_running_data_normalizer.intake.roots import open_export
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.snapshot import store as store_module
from garmin_running_data_normalizer.snapshot.store import (
    SnapshotStoreError,
    initialize_store,
    register_snapshot,
)

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
                # The stops and, from stage A5c, the cancellations that the
                # CLI prints.
                if name in ("_stop", "_cancel") and node.args and isinstance(node.args[0], ast.Constant):
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


def register_args(store: Path, source: Path, label: str = "S1") -> tuple[object, ...]:
    return (
        "snapshot", "register", "--store", store, "--input", source, "--label", label,
        "--requested-at", STAMP, "--downloaded-at", STAMP, "--observed-at", STAMP, "--confirm-complete",
    )


def registered(store: Path, source: Path, label: str = "S1") -> str:
    """Register one Export into a new store; return the Snapshot's identity."""
    if not store.exists():
        initialize_store(store, "synthetic")
    result = register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=STAMP,
        export_downloaded_at=STAMP,
        export_observed_at=STAMP,
        confirm_complete=True,
    )
    return str(result["snapshot_id"])


def can_symlink(directory: Path) -> bool:
    probe = directory / "symlink-probe"
    try:
        probe.symlink_to(directory, target_is_directory=True)
    except OSError:
        return False
    probe.unlink()
    return True


def cell(text: str) -> str:
    """A text as a cell of a Markdown table."""
    return text.replace("\\", "\\\\").replace("|", "\\|")


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

        # A name that could change the line or read otherwise is not written
        # (stage B3c).
        for function in (input_not_readable_message, store_not_readable_message):
            for name in ("a\nb", "a\u2028b", "a\u202eb", "x" * 5000):
                with self.subTest(function=function.__name__, name=name[:8]):
                    message = function([name, "c"])
                    self.assertTrue(message.endswith(": (a name that cannot be shown) and 1 more"), message)
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


class StopLines:
    """The check of the line of a stop, for the tests below."""

    def assert_stop(self: Any, code: str, args: tuple[object, ...], root: Path) -> str:
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


class StopLineTest(StopLines, unittest.TestCase):
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
                ("SUPPORT_BUNDLE_EXISTS", ("support-bundle", "--run-output", done, "--output", existing)),
                ("SUPPORT_BUNDLE_PATH_UNSAFE", ("support-bundle", "--run-output", empty / "missing", "--output", root / "b.zip")),
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

    def test_a_finding_whose_code_is_a_stop_gives_the_next_step_of_the_stop(self) -> None:
        # Stage B2b: the check and the run say the same about the same
        # problem; the JSON report keeps the identifier of the next action.
        # The words change for two findings only: an input that could not be
        # read safely, and Activities files that hold no record that can be
        # used.
        stops = stops_module()
        source = (PACKAGE / "diagnostics/doctor.py").read_text(encoding="utf-8")
        start = source.index("def doctor_input(")
        body = source[start : source.index("\ndef ", start)]
        pairs = re.findall(r'_finding\(\s*"([A-Z_]+)",.*?next_action_id="([A-Z_]+)"', body, re.DOTALL)
        self.assertEqual(len(pairs), body.count("_finding("))
        with tempfile.TemporaryDirectory() as directory:
            report = doctor_input(Path(directory))
        report["findings"] = [{"code": code, "next_action_id": action} for code, action in pairs]
        human = render_doctor_human(report)
        changed = set()
        for code, action in pairs:
            step = stops.STOPS[code].next_step if code in stops.STOPS else stops.NEXT_ACTIONS[action]
            with self.subTest(code=code, action=action):
                self.assertEqual(stops.finding_next_step(code, action), step)
                self.assertIn(f"Finding: {code} (next: {step})", human)
            if step != stops.NEXT_ACTIONS[action]:
                changed.add((code, action))
        self.assertEqual(
            changed,
            {
                ("INPUT_DISCOVERY_FAILED", "OBTAIN_COMPLETE_READABLE_EXPORT"),
                ("ACTIVITIES_EMPTY", "SELECT_EXPORT_WITH_ACTIVITIES"),
            },
        )

    def test_every_next_action_of_the_reports_has_words(self) -> None:
        source = (PACKAGE / "diagnostics/doctor.py").read_text(encoding="utf-8")
        used = set(re.findall(r'next_action_id="([A-Z_]+)"', source))
        used |= set(re.findall(r'doctor_next_action_id = "([A-Z_]+)"', source))
        used |= set(re.findall(r'"(CORRECT_PRE_RUN_CONDITION|RUN_ALL)"', source))
        self.assertEqual(sorted(used), sorted(stops_module().NEXT_ACTIONS))
        for action, text in stops_module().NEXT_ACTIONS.items():
            self.assertNotIn("{", text, action)
            self.assertFalse(text.endswith("."), action)



class SameProblemTest(StopLines, unittest.TestCase):
    """Stage A5b-2: the snapshot commands and the Support Bundle stop with the
    code of the same problem in a run, and with the same message."""

    def test_the_place_of_the_build_and_the_input_of_a_registration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            registered(store, SYNTHETIC_EXPORT)
            existing = root / "existing"
            existing.mkdir()
            plain = root / "plain.txt"
            plain.write_text("synthetic", encoding="utf-8")
            pairs = [
                (
                    "OUTPUT_EXISTS",
                    ("snapshot", "build-input", "--store", store, "--output", existing),
                    ("run-all", "--input", SYNTHETIC_EXPORT, "--output", existing),
                ),
                (
                    "INPUT_NOT_DIRECTORY",
                    register_args(store, plain, "S2"),
                    ("run-all", "--input", plain, "--output", root / "o1"),
                ),
            ]
            if can_symlink(root):
                elsewhere = root / "elsewhere"
                elsewhere.mkdir()
                link = root / "link"
                link.symlink_to(elsewhere, target_is_directory=True)
                export_link = root / "export-link"
                export_link.symlink_to(SYNTHETIC_EXPORT.resolve(), target_is_directory=True)
                inside = root / "with-a-link"
                shutil.copytree(SYNTHETIC_EXPORT, inside)
                (inside / "synthetic-link.json").symlink_to(plain)
                pairs += [
                    (
                        "OUTPUT_SYMLINK",
                        ("snapshot", "build-input", "--store", store, "--output", link),
                        ("run-all", "--input", SYNTHETIC_EXPORT, "--output", link),
                    ),
                    (
                        "INPUT_SYMLINK",
                        register_args(store, export_link, "S2"),
                        ("run-all", "--input", export_link, "--output", root / "o2"),
                    ),
                    (
                        "INPUT_DISCOVERY_FAILED",
                        register_args(store, inside, "S2"),
                        ("run-all", "--input", inside, "--output", root / "o3"),
                    ),
                ]
            for code, snapshot_args, run_args in pairs:
                with self.subTest(code=code):
                    self.assertEqual(
                        self.assert_stop(code, snapshot_args, root),
                        self.assert_stop(code, run_args, root),
                    )
            # An input that cannot be looked at, as a run says it.
            real = Path.is_symlink
            for error, code in (
                (PermissionError(errno.EACCES, "synthetic"), "INPUT_NOT_READABLE"),
                (OSError(errno.ENAMETOOLONG, "synthetic"), "INPUT_NOT_DIRECTORY"),
            ):

                def is_symlink(self: Path, error: OSError = error) -> bool:
                    if self == plain:
                        raise error
                    return real(self)

                with self.subTest(code=code), mock.patch.object(Path, "is_symlink", is_symlink):
                    self.assertEqual(
                        self.assert_stop(code, register_args(store, plain, "S2"), root),
                        self.assert_stop(code, ("run-all", "--input", plain, "--output", root / "o4"), root),
                    )
            # No output was made, and nothing was written through the link.
            self.assertEqual(sorted(path.name for path in root.iterdir() if path.name.startswith("o")), [])
            if (root / "elsewhere").exists():
                self.assertEqual(list((root / "elsewhere").iterdir()), [])

    def test_a_build_without_activities_stops_as_a_run_does(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export"
            shutil.copytree(SYNTHETIC_EXPORT, source)
            for path in source.rglob("*summarizedActivities.json"):
                path.write_text(json.dumps([{"summarizedActivitiesExport": []}]), encoding="utf-8")
            store = root / "store"
            registered(store, source)
            run = self.assert_stop("ACTIVITIES_EMPTY", ("run-all", "--input", source, "--output", root / "o1"), root)
            for args in (
                ("snapshot", "build-input", "--store", store, "--output", root / "o2"),
                ("snapshot", "run-all", "--store", store, "--output", root / "o3"),
            ):
                with self.subTest(command=args[1]):
                    self.assertEqual(self.assert_stop("ACTIVITIES_EMPTY", args, root), run)
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["export", "store"])

    def test_a_folder_without_a_store_and_a_store_without_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # A folder that holds files, but none that a store writes.
            folder = root / "folder"
            folder.mkdir()
            (folder / "notes.txt").write_text("synthetic", encoding="utf-8")
            for store in (root / "missing", folder):
                for args in (
                    ("snapshot", "status", "--store", store),
                    ("snapshot", "verify", "--store", store),
                    register_args(store, SYNTHETIC_EXPORT),
                    ("snapshot", "build-input", "--store", store, "--output", root / "o1"),
                    ("snapshot", "run-all", "--store", store, "--output", root / "o2"),
                ):
                    with self.subTest(store=store.name, command=args[1]):
                        self.assert_stop("SNAPSHOT_STORE_NOT_FOUND", args, root)
            store = root / "store"
            initialize_store(store, "synthetic")
            for args in (
                ("snapshot", "build-input", "--store", store, "--output", root / "o1"),
                ("snapshot", "run-all", "--store", store, "--output", root / "o2"),
            ):
                with self.subTest(command=args[1]):
                    self.assert_stop("SNAPSHOT_STORE_EMPTY", args, root)
            # A store without a Snapshot is not a stop for the commands that
            # look at it.
            for args in (("snapshot", "status", "--store", store), ("snapshot", "verify", "--store", store)):
                with self.subTest(command=args[1]):
                    self.assertEqual(cli(*args), (0, ""))
            # A store that lost store.json, but holds what a store writes, is
            # damaged, not a folder without a store.
            damaged = root / "damaged"
            registered(damaged, SYNTHETIC_EXPORT)
            (damaged / "store.json").chmod(0o600)
            (damaged / "store.json").unlink()
            for args in (
                ("snapshot", "status", "--store", damaged),
                ("snapshot", "verify", "--store", damaged),
                register_args(damaged, SYNTHETIC_EXPORT, "S2"),
                ("snapshot", "build-input", "--store", damaged, "--output", root / "o1"),
                ("snapshot", "run-all", "--store", damaged, "--output", root / "o2"),
            ):
                with self.subTest(store="damaged", command=args[1]):
                    what = self.assert_stop("SNAPSHOT_STORE_INVALID", args, root)
                    self.assertLessEqual(what.count("damaged:"), 1, what)
                    if args[1] in ("status", "register"):
                        self.assertEqual(what, "the Snapshot Store is damaged: store.json is missing")
            # No store and no output were made.
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["damaged", "folder", "store"])
            self.assertEqual([path.name for path in folder.iterdir()], ["notes.txt"])

    def test_the_stops_of_a_registration_have_their_own_codes(self) -> None:
        # Until stage B4b-1 these four stopped with SNAPSHOT_LIFECYCLE_FAILED;
        # the GUI checks the same with the same functions before a run.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            registered(store, SYNTHETIC_EXPORT)
            other = root / "other"
            shutil.copytree(SYNTHETIC_EXPORT, other)
            (other / "DI-Connect-Fitness" / "synthetic_gear.json").write_text("[]", encoding="utf-8")
            late = "2030-01-01T03:00:00+00:00"
            cases = [
                ("SNAPSHOT_LABEL_INVALID", register_args(store, other, "S 2")),
                ("SNAPSHOT_LABEL_EXISTS", register_args(store, other, "S1")),
                ("SNAPSHOT_TIME_INVALID", (*register_args(store, other, "S2")[:-1], "--observed-at", "2030-01-01 02:00", "--confirm-complete")),
                ("SNAPSHOT_TIME_INVALID", (*register_args(store, other, "S2")[:-1], "--requested-at", late, "--confirm-complete")),
                ("SNAPSHOT_INPUT_INSIDE_STORE", register_args(store, store, "S2")),
                ("SNAPSHOT_INPUT_INSIDE_STORE", register_args(store, store / "snapshots", "S2")),
            ]
            for code, args in cases:
                with self.subTest(code=code, args=args[-4:]):
                    self.assert_stop(code, args, root)
            # The same Export again is not a new Snapshot under any label,
            # one that the store has included (stage A3a).
            self.assertEqual(cli(*register_args(store, SYNTHETIC_EXPORT, "S1"))[0], 0)

    def test_a_registration_that_meets_a_damaged_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # A Snapshot whose identity is that of another content: the
            # identity is made from the content, so the store is damaged.
            other = root / "other"
            shutil.copytree(SYNTHETIC_EXPORT, other)
            (other / "DI-Connect-Fitness" / "synthetic_gear.json").write_text("[]", encoding="utf-8")
            other_id = registered(root / "scratch", other)
            store = root / "store"
            first_id = registered(store, SYNTHETIC_EXPORT)
            folder = store / "snapshots" / first_id
            manifest_path = folder / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["snapshot_id"] = other_id
            manifest_path.chmod(0o600)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            folder.rename(store / "snapshots" / other_id)
            (store / "registry.json").unlink()
            what = self.assert_stop("SNAPSHOT_STORE_INVALID", register_args(store, other, "S2"), root)
            self.assertEqual(
                what, "the Snapshot Store is damaged: the identity of a registered Snapshot does not match its content"
            )
            # A damaged record of a Snapshot, which the store names since stage
            # A3d-3b, says "damaged:" once; the build stops with the failures
            # of verification.
            records = root / "records"
            record_id = registered(records, SYNTHETIC_EXPORT)
            record_path = records / "snapshots" / record_id / "manifest.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            del record["registered_at"]
            record_path.chmod(0o600)
            record_path.write_text(json.dumps(record), encoding="utf-8")
            for args in (
                register_args(records, other, "S2"),
                ("snapshot", "status", "--store", records),
                ("snapshot", "build-input", "--store", records, "--output", root / "o1"),
            ):
                with self.subTest(command=args[1]):
                    what = self.assert_stop("SNAPSHOT_STORE_INVALID", args, root)
                    self.assertLessEqual(what.count("damaged:"), 1, what)
                    if args[1] != "build-input":
                        self.assertEqual(
                            what, "the Snapshot Store is damaged: snapshot manifest is missing required metadata"
                        )
            if can_symlink(root):
                linked = root / "linked-store"
                initialize_store(linked, "synthetic")
                blobs = linked / "blobs" / "sha256"
                shutil.rmtree(blobs)
                outside = root / "outside"
                outside.mkdir()
                blobs.symlink_to(outside, target_is_directory=True)
                what = self.assert_stop("SNAPSHOT_STORE_INVALID", register_args(linked, SYNTHETIC_EXPORT), root)
                self.assertEqual(what, "the Snapshot Store is damaged: it holds a symbolic link")
                self.assertEqual(list(outside.iterdir()), [])

    def test_a_registration_reads_the_input_as_a_run_does(self) -> None:
        # A ZIP file inside the Export that cannot be copied out or whose
        # members cannot be read stops as a run stops for an input that
        # cannot be read: INPUT_CHANGED for one that went away, and
        # INPUT_DISCOVERY_FAILED otherwise.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export"
            shutil.copytree(SYNTHETIC_EXPORT, source)
            uploaded = source / "DI-Connect-Uploaded-Files"
            uploaded.mkdir()
            with zipfile.ZipFile(uploaded / "UploadedFiles_0-_Part1.zip", "w") as archive:
                archive.writestr("synthetic-session-1.fit", b"synthetic")
            store = root / "store"
            initialize_store(store, "synthetic")
            for target in (
                "garmin_running_data_normalizer.intake.source.ExportSource.local_path",
                "garmin_running_data_normalizer.snapshot.store.digest_member",
            ):
                for error, code in (
                    (OSError(errno.EIO, "synthetic"), "INPUT_DISCOVERY_FAILED"),
                    (FileNotFoundError(errno.ENOENT, "synthetic"), "INPUT_CHANGED"),
                ):
                    with self.subTest(target=target.rsplit(".", 1)[1], code=code):
                        with mock.patch(target, side_effect=error):
                            self.assert_stop(code, register_args(store, source), root)
            self.assertEqual(cli(*register_args(store, source))[0], 0)
        # A member that cannot be read when it is copied was read whole when
        # the input was listed: the input changed.
        archive = mock.Mock()
        archive.open.side_effect = zipfile.BadZipFile("synthetic")
        with self.assertRaises(SnapshotStoreError) as raised:
            with store_module._open_member(archive, mock.Mock()):
                pass
        self.assertEqual(raised.exception.code, "INPUT_CHANGED")

    def test_an_export_zip_file_that_is_too_large_stops_a_registration_as_a_run(self) -> None:
        # The same Export twice in an Export ZIP file: its two roots are read
        # to compare them, which counts against the totals for one reading
        # of the ZIP file. INPUT_TOO_LARGE is an UnsafeArchiveError too, and
        # keeps its code (stage A5b-2).
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activities = next(SYNTHETIC_EXPORT.rglob("*summarizedActivities.json"))
            twice = root / "twice.zip"
            with zipfile.ZipFile(twice, "w") as archive:
                for name in ("export-a", "export-b"):
                    archive.write(activities, f"{name}/DI_CONNECT/DI-Connect-Fitness/{activities.name}")
            store = root / "store"
            initialize_store(store, "synthetic")
            limits = ArchiveLimits(max_export_read_bytes=1)
            with mock.patch(
                "garmin_running_data_normalizer.snapshot.store.open_export",
                side_effect=lambda path: open_export(path, limits),
            ), mock.patch(
                "garmin_running_data_normalizer.run_all.read_export",
                side_effect=lambda path: read_export(path, limits),
            ):
                self.assertEqual(
                    self.assert_stop("INPUT_TOO_LARGE", register_args(store, twice), root),
                    self.assert_stop("INPUT_TOO_LARGE", ("run-all", "--input", twice, "--output", root / "o1"), root),
                )
            self.assertEqual(cli("snapshot", "status", "--store", store)[0], 0)

    def test_the_support_bundle_never_replaces_a_file_or_a_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            done = root / "done"
            self.assertEqual(cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", done)[0], 0)
            existing = root / "existing.zip"
            existing.write_bytes(b"synthetic")
            places = [existing]
            if can_symlink(root):
                link = root / "link.zip"
                link.symlink_to(existing)
                broken = root / "broken.zip"
                broken.symlink_to(root / "missing.zip")
                places += [link, broken]
            for place in places:
                with self.subTest(place=place.name):
                    self.assert_stop(
                        "SUPPORT_BUNDLE_EXISTS", ("support-bundle", "--run-output", done, "--output", place), root
                    )
            self.assertEqual(existing.read_bytes(), b"synthetic")
            self.assertFalse((root / "missing.zip").exists())
            self.assert_stop(
                "SUPPORT_BUNDLE_PATH_UNSAFE",
                ("support-bundle", "--run-output", root / "missing", "--output", root / "new.zip"),
                root,
            )

    def test_dot_and_dot_dot_name_a_folder_that_is_there(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            store = root / "store"
            registered(store, SYNTHETIC_EXPORT)
            work = root / "work"
            work.mkdir()
            with contextlib.chdir(work):
                for output in (".", "..", "missing/.."):
                    for args in (
                        ("run-all", "--input", SYNTHETIC_EXPORT, "--output", output),
                        ("snapshot", "run-all", "--store", store, "--output", output),
                        ("snapshot", "build-input", "--store", store, "--output", output),
                    ):
                        with self.subTest(output=output, command=" ".join(map(str, args[:2]))):
                            self.assert_stop("OUTPUT_EXISTS", args, root)
                self.assertEqual(list(work.iterdir()), [])
            # normalize-activities writes in an empty folder that is there, as
            # before, also when the path names it from a folder that is not.
            for name, output in (("golden-dot", "."), ("golden-up", "missing/..")):
                folder = root / name
                folder.mkdir()
                with self.subTest(output=output), contextlib.chdir(folder):
                    self.assertEqual(cli("normalize-activities", "--input", SYNTHETIC_EXPORT, "--output", output)[0], 0)
                self.assertEqual(
                    sorted(path.name for path in folder.iterdir()),
                    ["normalized_activities.json", "qa_summary.json", "run_manifest.json"],
                )


class DocumentTableTest(unittest.TestCase):
    def test_the_documents_give_the_table_of_stops(self) -> None:
        # The table of the documents is made from stops.STOPS (stage
        # A5b-2); when they differ, the message gives the rows to paste.
        text = (ROOT / "docs" / "v2_data_handling.md").read_text(encoding="utf-8")
        heading = "\n#### Stops and next steps\n"
        self.assertTrue(heading in text, "the documents have no table of the stops")
        section = text.split(heading, 1)[1].split("\n#", 1)[0]
        rows = [line for line in section.splitlines() if line.startswith("| `")]
        expected = [
            f"| `{code}` | {cell(stop.what)} | {cell(stop.next_step)} |"
            for code, stop in stops_module().STOPS.items()
        ]
        self.assertEqual(rows, expected, "\n" + "\n".join(expected))

    def test_the_gui_design_gives_the_table_of_the_codes_of_the_gui(self) -> None:
        # The codes that only the GUI gives are not in the CLI's table; the
        # GUI design lists them, made from stops.PAGE_STOPS (stage B2a).
        text = (ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8")
        heading = "\n### Codes that only the GUI gives\n"
        self.assertTrue(heading in text, "the GUI design has no table of the codes of the GUI")
        section = text.split(heading, 1)[1].split("\n#", 1)[0]
        rows = [line for line in section.splitlines() if line.startswith("| `")]
        expected = [
            f"| `{code}` | {cell(stop.what)} | {cell(stop.next_step)} |"
            for code, stop in stops_module().PAGE_STOPS.items()
        ]
        self.assertEqual(rows, expected, "\n" + "\n".join(expected))


if __name__ == "__main__":
    unittest.main()
