"""Stage A5a: the CLI and the GUI check the name and the place of an output
alike, report the total of the warnings and those that belong to no family
alike, and the pre-run check reads the Activities files as a run reads them
(synthetic data only)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input
from garmin_running_data_normalizer.gui import runs
from garmin_running_data_normalizer.gui.runs import RunManager, RunRequestError, validate_output_name
# The names that stage A5a adds are read where they are used, so that each
# test fails on its own on a version without them.
from garmin_running_data_normalizer import output_location
from garmin_running_data_normalizer import run_all as run_all_module
from garmin_running_data_normalizer.run_all import ACTIVITIES_NOT_READABLE_MESSAGE, RunAllError, run_all
from garmin_running_data_normalizer.runner import GoldenPathError, run_activities
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from garmin_running_data_normalizer.snapshot.merge import SnapshotBuildOutputError
from tests.test_gui_runs import child_environment

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
PAGE = ROOT / "src/garmin_running_data_normalizer/gui/static/app.mjs"
STAMP = "2030-01-01T02:00:00+00:00"

# Names that the GUI refused before stage A5a, and the CLI took. Each can be
# written in a path on every system, so the checks meet them before the system
# does.
REFUSED_NAMES = {
    "a dot at the start": ".hidden",
    "a dot at the end": "name.",
    "a space at the end": "name ",
    "a colon": "na:me",
    "a character that Windows does not take": "a<b",
    "a control character": "a\x01b",
    "a Windows device": "CON",
    "a Windows device with an extension": "nul.txt",
    "201 bytes": "a" * 201,
    "201 bytes of kana": "あ" * 67,
}
ACCEPTED_NAMES = {
    "a plain name": "output",
    "200 bytes": "a" * 200,
    "198 bytes of kana": "あ" * 66,
    "a space at the start": " name",
    "an ideographic space at the end": "name　",
}
# Names that the CLI is given in a command line on every system.
COMMAND_LINE_NAMES = (".hidden", "name.", "CON")


def cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "garmin_running_data_normalizer", *map(str, args)],
        capture_output=True,
        text=True,
        env=child_environment(),
        timeout=300,
    )


def entries(folder: Path) -> list[str]:
    return sorted(path.name for path in folder.iterdir())


def store_with_one_snapshot(root: Path, source: Path = SYNTHETIC_EXPORT) -> Path:
    store = root / "store"
    initialize_store(store, "synthetic-account")
    register_snapshot(
        store,
        source,
        snapshot_label="S1",
        export_requested_at=STAMP,
        export_downloaded_at=STAMP,
        export_observed_at=STAMP,
        confirm_complete=True,
    )
    return store


def gui_request(parent: Path, name: str) -> dict[str, Any]:
    return {
        "input": str(SYNTHETIC_EXPORT),
        "output_parent": str(parent),
        "output_name": name,
        "timezone": "Asia/Tokyo",
    }


def stops(function: Any, *args: Any) -> str | None:
    """The code with which a command stops, or None when it finishes."""
    try:
        function(*args)
    except (RunAllError, GoldenPathError, SnapshotBuildOutputError, RunRequestError) as exc:
        return exc.code
    return None


class OutputNameTest(unittest.TestCase):
    def test_the_cli_and_the_gui_take_the_same_names(self) -> None:
        for label, name in ACCEPTED_NAMES.items():
            with self.subTest(label):
                self.assertTrue(output_location.valid_output_name(name))
                self.assertEqual(validate_output_name(name), name)
        for label, name in REFUSED_NAMES.items():
            with self.subTest(label):
                self.assertFalse(output_location.valid_output_name(name))
                with self.assertRaises(RunRequestError) as raised:
                    validate_output_name(name)
                self.assertEqual(raised.exception.code, "OUTPUT_NAME_INVALID")

    def test_every_command_refuses_a_name_before_it_reads_its_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = store_with_one_snapshot(root)
            parent = root / "outputs"
            parent.mkdir()
            commands = {
                "run-all": lambda output: run_all(SYNTHETIC_EXPORT, output),
                "normalize-activities": lambda output: run_activities(SYNTHETIC_EXPORT, output),
                "snapshot build-input": lambda output: build_approved_input(store, output),
                "snapshot run-all": lambda output: run_snapshot_all(store, output),
                "gui": lambda output: RunManager().start(gui_request(output.parent, output.name)),
            }
            for label, name in REFUSED_NAMES.items():
                for command, function in commands.items():
                    with self.subTest(label, command=command):
                        self.assertEqual(stops(function, parent / name), "OUTPUT_NAME_INVALID")
                        # Nothing is written, not even a hidden folder.
                        self.assertEqual(entries(parent), [])

    def test_the_cli_prints_the_code_and_exits_with_2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "outputs"
            parent.mkdir()
            for name in COMMAND_LINE_NAMES:
                for command in ("run-all", "normalize-activities"):
                    with self.subTest(name=name, command=command):
                        completed = cli(command, "--input", SYNTHETIC_EXPORT, "--output", parent / name)
                        self.assertEqual(completed.returncode, 2, completed.stderr)
                        self.assertTrue(
                            completed.stderr.startswith("ERROR [OUTPUT_NAME_INVALID]: "),
                            completed.stderr,
                        )
                        self.assertEqual(entries(parent), [])

    def test_an_empty_output_folder_of_the_golden_path_is_written_in(self) -> None:
        # The Golden Path writes in an empty output folder that is there
        # already; it does not make that folder, so its name is not checked.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / ".hidden"
            output.mkdir()
            result = run_activities(SYNTHETIC_EXPORT, output)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                entries(output), ["normalized_activities.json", "qa_summary.json", "run_manifest.json"]
            )


class OutputParentTest(unittest.TestCase):
    def test_every_command_refuses_a_folder_for_the_output_that_is_not_there(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = store_with_one_snapshot(root)
            (root / "a-file").write_text("synthetic", encoding="utf-8")
            commands = {
                "run-all": lambda output: run_all(SYNTHETIC_EXPORT, output),
                "normalize-activities": lambda output: run_activities(SYNTHETIC_EXPORT, output),
                "snapshot build-input": lambda output: build_approved_input(store, output),
                "snapshot run-all": lambda output: run_snapshot_all(store, output),
                "gui": lambda output: RunManager().start(gui_request(output.parent, output.name)),
            }
            before = entries(root)
            for label, parent in (
                ("a folder that is not there", root / "missing" / "deeper"),
                ("a file", root / "a-file"),
            ):
                for command, function in commands.items():
                    with self.subTest(label, command=command):
                        self.assertEqual(
                            stops(function, parent / "output"), "OUTPUT_PARENT_NOT_FOUND"
                        )
                        # Until stage A5a, the CLI made the missing folders.
                        self.assertEqual(entries(root), before)

    def test_the_cli_prints_the_code_and_the_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for command in ("run-all", "normalize-activities"):
                with self.subTest(command=command):
                    completed = cli(
                        command, "--input", SYNTHETIC_EXPORT, "--output", root / "missing" / "output"
                    )
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertEqual(
                        completed.stderr.strip(),
                        "ERROR [OUTPUT_PARENT_NOT_FOUND]: the folder for the output does not "
                        "exist or is not a folder; choose an existing folder for the output, "
                        "or create it first",
                    )
                    self.assertEqual(entries(root), [])


def warned_input(root: Path) -> Path:
    """An input with warnings of every kind: of the families, of the Lactate
    Threshold candidates, of a link to an Activity that the Export does not
    hold, and of the same Export given twice."""
    export = root / "input" / "one"
    shutil.copytree(SYNTHETIC_EXPORT, export)
    wellness = export / "DI-Connect-Wellness"
    wellness.mkdir()
    (wellness / "synthetic_userBioMetricProfileData.json").write_text(
        json.dumps([{"functionalThresholdPower": 100}, {"functionalThresholdPower": 110}]),
        encoding="utf-8",
    )
    (export / "synthetic_gear.json").write_text(
        json.dumps(
            {
                "gearDTOS": [{"gearPk": "SYNTHETIC-GEAR-1", "displayName": "Synthetic Shoe"}],
                "gearActivityDTOs": {"SYNTHETIC-GEAR-1": [{"activityId": "MISSING-ACTIVITY"}]},
            }
        ),
        encoding="utf-8",
    )
    shutil.copytree(export, root / "input" / "two")
    return root / "input"


def summary_of(output: Path) -> dict[str, Any]:
    return json.loads((output / "run_summary.json").read_text(encoding="utf-8"))


def printed_warnings(stdout: str) -> tuple[str, str]:
    """The line of the total, which follows the exit code, and the line of
    the warnings that belong to no family, which comes before the files."""
    lines = stdout.splitlines()
    total = lines[lines.index(next(line for line in lines if line.startswith("exit: "))) + 1]
    other = lines[lines.index(next(line for line in lines if line.startswith("generated: "))) - 1]
    return total, other


class WarningTotalsTest(unittest.TestCase):
    def test_the_total_is_the_families_and_the_warnings_of_no_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            result = run_all(warned_input(root), output)
            summary = summary_of(output)
            totals = result["warning_totals"]
            self.assertEqual(totals, run_all_module.warning_totals(summary))
            self.assertEqual(totals["total"], len(summary["warnings"]))
            self.assertEqual(
                totals["total"], sum(totals["families"].values()) + sum(totals["other"].values())
            )
            # Every kind of the warnings that belong to no family is there.
            self.assertEqual(totals["other"], {"candidate": 1, "relationship": 1, "input": 1})
            self.assertEqual(
                [name for name, _field in run_all_module.OTHER_WARNING_FIELDS],
                ["candidate", "relationship", "input"],
            )
            self.assertGreater(sum(totals["families"].values()), 0)

    def test_the_cli_prints_the_total_and_the_warnings_of_no_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = warned_input(root)
            completed = cli("run-all", "--input", source, "--output", root / "output")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = summary_of(root / "output")
            self.assertEqual(
                printed_warnings(completed.stdout),
                (
                    f"warnings: {summary['warning_count']}",
                    "other warnings: candidate=1 relationship=1 input=1",
                ),
            )
            handoff = cli("validate-handoff", "--input", root / "output")
            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            self.assertIn(f"\nwarnings: {summary['warning_count']}\n", handoff.stdout)

    def test_the_lines_are_printed_when_there_is_no_warning_of_no_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = store_with_one_snapshot(root)
            for label, args, output in (
                ("run-all", ("run-all", "--input", SYNTHETIC_EXPORT), root / "one-shot"),
                ("snapshot run-all", ("snapshot", "run-all", "--store", store), root / "snapshot"),
            ):
                with self.subTest(label):
                    completed = cli(*args, "--output", output)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(
                        printed_warnings(completed.stdout),
                        (
                            f"warnings: {summary_of(output)['warning_count']}",
                            "other warnings: candidate=0 relationship=0 input=0",
                        ),
                    )

    def test_the_gui_child_reports_the_same_totals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-P",
                    "-m",
                    "garmin_running_data_normalizer.gui.run_worker",
                    f"--input={warned_input(root)}",
                    f"--output={output}",
                ],
                capture_output=True,
                text=True,
                env=child_environment(),
                timeout=300,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            event = json.loads(completed.stdout.splitlines()[-1])
            totals = run_all_module.warning_totals(summary_of(output))
            self.assertEqual(event["warning_count"], totals["total"])
            self.assertEqual(event["other_warning_counts"], totals["other"])
            result = runs._valid_result(event)
            assert result is not None
            self.assertEqual(
                (result["warning_count"], result["other_warning_counts"]),
                (totals["total"], totals["other"]),
            )

    def test_the_run_manager_takes_only_counts(self) -> None:
        event = {
            "event": "finished",
            "status": "PASS",
            "exit_code": 0,
            "generated_file_count": 1,
            "families": {},
            "warning_count": 0,
            "other_warning_counts": {"candidate": 0, "relationship": 0, "input": 0},
        }
        self.assertIsNotNone(runs._valid_result(event))
        for label, change in (
            ("no total", {"warning_count": None}),
            ("a total below 0", {"warning_count": -1}),
            ("a total that is true", {"warning_count": True}),
            ("no warnings of no family", {"other_warning_counts": None}),
            ("a name missing", {"other_warning_counts": {"candidate": 0, "relationship": 0}}),
            (
                "another name",
                {"other_warning_counts": {"candidate": 0, "relationship": 0, "input": 0, "x": 0}},
            ),
            ("a count that is text", {"other_warning_counts": {"candidate": "0", "relationship": 0, "input": 0}}),
        ):
            with self.subTest(label):
                self.assertIsNone(runs._valid_result({**event, **change}))

    def test_the_page_has_no_timezone_of_its_own(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        self.assertFalse("Asia/Tokyo" in page, "the page has a timezone of its own")
        self.assertTrue("status.default_timezone" in page, "the page does not read the default")


ACTIVITIES = "DI-Connect-Fitness"
NO_RECORDS = json.dumps([{"summarizedActivitiesExport": []}])
# An identifier of a form that no identifier takes; an Activity without
# one is kept, with a key made from its fields.
NO_IDENTIFIER = json.dumps([{"summarizedActivitiesExport": [{"activityId": 12.5, "activityType": "running"}]}])


def activities_export(root: Path, *contents: str) -> Path:
    """The synthetic Export with its Activities files replaced by ``contents``;
    the synthetic Activities themselves for the content ``None``."""
    export = root / "export"
    shutil.copytree(SYNTHETIC_EXPORT, export)
    original = next((export / ACTIVITIES).glob("*summarizedActivities.json"))
    readable = original.read_text(encoding="utf-8")
    original.unlink()
    for index, content in enumerate(contents):
        (export / ACTIVITIES / f"synthetic_{index}_summarizedActivities.json").write_text(
            readable if content is None else content, encoding="utf-8"
        )
    return export


def findings(source: Path) -> list[tuple[str, str, str, str]]:
    return [
        (item["code"], item["severity"], item["safe_message_id"], item["next_action_id"])
        for item in doctor_input(source)["findings"]
    ]


LEFT_OUT = ("DATA_FILE_LEFT_OUT", "WARNING", "INPUT_FILES_CANNOT_BE_READ_AND_WILL_BE_LEFT_OUT", "RUN_ALL")
READY = ("RUN_ALL_NOT_EVALUATED", "INFO", "INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT", "RUN_ALL")
CANNOT_BE_READ = ("ACTIVITIES_EMPTY", "ERROR", "ACTIVITIES_FILES_CANNOT_BE_READ", "OBTAIN_COMPLETE_READABLE_EXPORT")
NO_RECORD = ("ACTIVITIES_EMPTY", "ERROR", "ACTIVITIES_FILES_HOLD_NO_RECORDS", "SELECT_EXPORT_WITH_ACTIVITIES")


class PreRunActivitiesTest(unittest.TestCase):
    """The pre-run check and the run give the same answer (stage A5a)."""

    CASES = {
        "every Activities file is not JSON": (("{",), [LEFT_OUT, CANNOT_BE_READ], ACTIVITIES_NOT_READABLE_MESSAGE),
        "one of two Activities files is not JSON": (("{", None), [LEFT_OUT, READY], None),
        "the Activities files hold no record": ((NO_RECORDS,), [NO_RECORD], "Activities input produced no valid records"),
        "the Activities rows have no usable identifier": (
            (NO_IDENTIFIER,),
            [NO_RECORD],
            "Activities input produced no valid records",
        ),
        "one file is not JSON, and the other holds no record": (
            ("{", NO_RECORDS),
            [LEFT_OUT, CANNOT_BE_READ],
            ACTIVITIES_NOT_READABLE_MESSAGE,
        ),
    }

    def test_the_check_tells_what_the_run_does(self) -> None:
        for label, (contents, expected, stop) in self.CASES.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = activities_export(root, *contents)
                archive = root / "export.zip"
                with zipfile.ZipFile(archive, "w") as handle:
                    for path in sorted(source.rglob("*")):
                        if path.is_file():
                            handle.write(path, path.relative_to(source).as_posix())
                self.assertEqual(findings(source), expected)
                self.assertEqual(findings(archive), expected)
                # The report holds codes only: no name of a file, and no
                # identifier or name of an Activity that the check read.
                report = json.dumps(doctor_input(source))
                for private in (
                    "summarizedActivities",
                    "SYNTHETIC-RUN-0001",
                    "Synthetic Five Kilometre Run",
                    "12.5",
                    str(root),
                ):
                    self.assertNotIn(private, report)
                if stop is None:
                    result = run_all(source, root / "output")
                    self.assertEqual((result["status"], result["exit_code"]), ("PARTIAL_SUCCESS", 3))
                else:
                    with self.assertRaises(RunAllError) as raised:
                        run_all(source, root / "output")
                    self.assertEqual(
                        (raised.exception.code, raised.exception.safe_message),
                        ("ACTIVITIES_EMPTY", stop),
                    )

    def test_the_check_does_not_read_activities_for_mixed_exports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mixed = root / "mixed"
            for name, activity_id in (("export-a", "SYNTHETIC-A1"), ("export-b", "SYNTHETIC-B1")):
                fitness = mixed / name / "DI_CONNECT" / ACTIVITIES
                fitness.mkdir(parents=True)
                (fitness / "synthetic_summarizedActivities.json").write_text(
                    json.dumps(
                        [
                            {
                                "summarizedActivitiesExport": [
                                    {
                                        "activityId": activity_id,
                                        "activityType": "running",
                                        "startTimeGmt": 1893456000000,
                                    }
                                ]
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
            self.assertEqual(
                [item[0] for item in findings(mixed)], ["INPUT_MULTIPLE_EXPORTS"]
            )


if __name__ == "__main__":
    unittest.main()
