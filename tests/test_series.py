"""The series command: the numbers of the view page in a new CSV file (stage G2)."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import re
import shutil
import stat
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before modules that import standalone:
# the other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.stops import STOPS
from garmin_running_data_normalizer.view import series_file
from garmin_running_data_normalizer.view.data import load_view_data
from garmin_running_data_normalizer.view.items import ITEMS, ITEMS_BY_KEY
from garmin_running_data_normalizer.view.series import view_answer
from garmin_running_data_normalizer.view.series_file import SERIES_COLUMNS, series_csv
from tests.test_gui_runs import SYNTHETIC_EXPORT
from tests.v1_3_outputs import as_release, as_v1_3
from tests.view_export import write_view_export

HEADER = "item,line,kind,unit,vo2max_source_series,sport,period_start,period_end,partial,value,count"


def cli(*args: object) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = runner.main([str(arg) for arg in args])
    return code, stdout.getvalue(), stderr.getvalue()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def expected_rows(answer: dict[str, Any]) -> list[dict[str, str]]:
    """The rows of an answer of the view page, as the contract writes them."""
    rows = []
    for panel in answer["panels"]:
        item = ITEMS_BY_KEY[panel["item"]]
        for number, line in enumerate(panel["lines"], 1):
            series = line["series"] or {}
            for period, value, count in zip(answer["periods"], line["values"], line["counts"]):
                rows.append(
                    {
                        "item": item.key,
                        "line": str(number),
                        "kind": item.kind,
                        "unit": item.unit or "",
                        "vo2max_source_series": series.get("vo2max_source_series", ""),
                        "sport": series.get("sport", ""),
                        "period_start": period["start"],
                        "period_end": period["end"],
                        "partial": "true" if period["partial"] else "false",
                        "value": "" if value is None else repr(value),
                        "count": str(count),
                    }
                )
    return rows


class SeriesTestCase(unittest.TestCase):
    def assert_same_rows(self, rows: list[dict[str, str]], expected: list[dict[str, str]]) -> None:
        """The rows of a CSV file against the rows that they must be: the
        count, then the first row that differs. The diff of assertEqual takes
        hours for tens of thousands of rows, as a partial guard found."""
        self.assertEqual(len(rows), len(expected))
        for index, (row, want) in enumerate(zip(rows, expected)):
            if row != want:
                self.fail(f"row {index + 2} of the file differs: {row} != {want}")

    def assert_stop(self, code: str, args: tuple[object, ...], root: Path) -> str:
        exit_code, stdout, stderr = cli(*args)
        self.assertEqual((exit_code, stdout), (2, ""), stderr)
        lines = stderr.splitlines()
        self.assertEqual(len(lines), 1, stderr)
        prefix, suffix = f"ERROR [{code}]: ", f"; {STOPS[code].next_step}"
        self.assertTrue(lines[0].startswith(prefix), lines[0])
        self.assertTrue(lines[0].endswith(suffix), lines[0])
        self.assertNotIn(str(root), lines[0])
        return lines[0][len(prefix) : -len(suffix)]


class SeriesFileTest(SeriesTestCase):
    """One output of about two and a half years of synthetic data."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name).resolve()
        cls.output = cls.root / "output"
        run_all(write_view_export(cls.root / "export"), cls.output)
        cls.data = load_view_data(cls.output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.place = Path(directory.name)

    def series(self, *options: object, name: str = "series.csv") -> tuple[Path, list[str]]:
        target = self.place / name
        exit_code, stdout, stderr = cli("series", "--run-output", self.output, "--output", target, *options)
        self.assertEqual((exit_code, stderr), (0, ""))
        return target, stdout.splitlines()

    def test_the_columns_are_those_of_the_contract(self) -> None:
        self.assertEqual(",".join(SERIES_COLUMNS), HEADER)
        target, _lines = self.series("--item", "dist")
        self.assertEqual(target.read_text(encoding="utf-8").splitlines()[0], HEADER)

    def test_every_row_is_a_number_of_the_view_page(self) -> None:
        for grain in ("day", "week", "month", "year", "auto"):
            with self.subTest(grain=grain):
                target, _lines = self.series("--grain", grain, name=f"{grain}.csv")
                answer = view_answer(self.data, [item.key for item in ITEMS], "all", grain)
                rows = read_rows(target)
                self.assert_same_rows(rows, expected_rows(answer))
                self.assertEqual({row["item"] for row in rows}, {item.key for item in ITEMS})

    def test_the_options_choose_the_items_the_period_and_the_types(self) -> None:
        cases = {
            "items, last year, weeks": (("--item", "rhr", "--item", "dist", "--period", "1y", "--grain", "week"), (["rhr", "dist"], "1y", "week", None)),
            "a range": (("--item", "dist", "--from", "2024-02-10", "--to", "2024-05-20", "--grain", "month"), (["dist"], (date(2024, 2, 10), date(2024, 5, 20)), "month", None)),
            "a type": (("--item", "count", "--type", "road_biking", "--grain", "month"), (["count"], "all", "month", ["road_biking"])),
            "every type": (("--item", "count", "--all-types", "--grain", "month"), (["count"], "all", "month", ["running", "treadmill_running", "trail_running", "road_biking"])),
            "repeated items": (("--item", "dist", "--item", "dist"), (["dist"], "all", "auto", None)),
        }
        for name, (options, (keys, period, grain, types)) in cases.items():
            with self.subTest(case=name):
                target, _lines = self.series(*options, name=f"{len(name)}.csv")
                self.assert_same_rows(read_rows(target), expected_rows(view_answer(self.data, keys, period, grain, types)))

    def test_the_names_of_the_types_are_those_that_the_output_writes(self) -> None:
        # Another case or another separator is another name; the output has
        # running and trail_running.
        for names in (("Running",), ("running", "trail-running"), ("RUNNING",)):
            with self.subTest(names=names):
                options = [part for name in names for part in ("--type", name)]
                self.assert_stop("SERIES_TYPE_UNKNOWN", ("series", "--run-output", self.output, "--output", self.place / "s.csv", *options), self.root)
                self.assertFalse((self.place / "s.csv").exists())
        target, _lines = self.series("--item", "count", "--type", "running", "--type", "trail_running", "--grain", "year")
        self.assert_same_rows(read_rows(target), expected_rows(view_answer(self.data, ["count"], "all", "year", ["running", "trail_running"])))

    def test_the_lines_of_vo2max_name_their_series_and_sport(self) -> None:
        target, _lines = self.series("--item", "vo2", "--grain", "year")
        lines = {(row["line"], row["vo2max_source_series"], row["sport"]) for row in read_rows(target)}
        self.assertEqual(
            lines,
            {
                ("1", "activity_vo2max_daily", "RUNNING"),
                ("2", "performance_metrics_daily", "CYCLING"),
                ("3", "performance_metrics_daily", "RUNNING"),
            },
        )

    def test_a_name_that_a_spreadsheet_could_read_as_a_formula_is_not_written(self) -> None:
        def line(sport: str) -> dict[str, Any]:
            return {"series": {"vo2max_source_series": "performance_metrics_daily", "sport": sport}, "values": [1.5], "counts": [1]}

        answer = {
            "periods": [{"start": "2024-01-01", "end": "2024-01-31", "partial": False}],
            "panels": [{"item": "vo2", "lines": [line("=SUM(1)"), line("-1"), line("Running"), line("RUNNING"), line("@A1")]}],
        }
        body, rows, hidden = series_csv(answer)
        sports = [row["sport"] for row in csv.DictReader(io.StringIO(body.decode("utf-8")))]
        self.assertEqual((sports, rows, hidden), (["", "", "", "RUNNING", ""], 5, {"vo2": 4}))

    def test_the_file_is_the_same_for_the_same_input_and_only_its_owner_reads_it(self) -> None:
        first, _lines = self.series("--item", "tr", "--grain", "day", name="first.csv")
        second, _lines = self.series("--item", "tr", "--grain", "day", name="second.csv")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertTrue(first.read_bytes().isascii())
        self.assertNotIn(b"\r", first.read_bytes())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)

    def test_the_lines_that_the_command_prints(self) -> None:
        target, lines = self.series("--item", "dist", "--item", "tr", "--item", "sleep", "--grain", "month")
        rows = read_rows(target)
        self.assertEqual(lines[:4], ["PASS", "generated: series.csv", f"rows: {len(rows)}", "items: 3"])
        answer = view_answer(self.data, ["dist", "tr", "sleep"], "all", "month")
        self.assertEqual(lines[4:6], [f"period: {answer['start']} to {answer['end']}", "grain: month"])
        about = [line for line in lines if line.startswith("about ")]
        expected = []
        for panel in answer["panels"]:
            counts = {name: count for name, count in panel["left_out"].items() if count}
            if counts:
                expected.append(f"about {panel['item']}: " + " ".join(f"{name}={count}" for name, count in sorted(counts.items())))
        self.assertEqual(about, expected)
        self.assertTrue(any(line.startswith("about tr: ") and "days_with_several_records=" in line for line in about))
        self.assertEqual(lines[-1], "The CSV file holds the values of the output: share it as you would share the output")
        # Counts, names, and dates only: no value and no place.
        output = "\n".join(lines)
        self.assertIsNone(re.search(r"\d\.\d", output))
        self.assertNotIn(str(self.root), output)
        self.assertNotIn(str(self.place), output)


class SeriesRefusalTest(SeriesTestCase):
    """What the series command refuses, with copies of one output of the
    synthetic example."""

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
        self.root = Path(directory.name).resolve()
        self.output = self.root / "output"
        shutil.copytree(self.source_output, self.output)
        self.target = self.root / "series.csv"
        self.args = ("series", "--run-output", self.output, "--output", self.target)

    def assert_nothing_written(self) -> None:
        self.assertEqual(sorted(path.name for path in self.root.iterdir() if path.name != "link"), ["output"])

    def test_an_output_without_rows_gives_the_header_only(self) -> None:
        # The only activity of the example is in 2030, after today.
        exit_code, stdout, _stderr = cli(*self.args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.target.read_text(encoding="utf-8"), HEADER + "\n")
        self.assertEqual(stdout.splitlines()[2:4], ["rows: 0", f"items: {len(ITEMS)}"])
        self.assertIn("period: none", stdout.splitlines())

    def test_outputs_of_other_versions_are_refused_with_their_versions(self) -> None:
        as_v1_3(self.output)
        what = self.assert_stop("SERIES_OUTPUT_OTHER_VERSION", self.args, self.root)
        self.assertIn("version 1.3.3", what)
        self.assert_nothing_written()
        shutil.rmtree(self.output)
        shutil.copytree(self.source_output, self.output)
        written = (self.output / "run_summary.json").read_text(encoding="utf-8")
        as_release(self.output, "1.2.1", tuple(json.loads(written)["generated_paths"]))
        what = self.assert_stop("OUTPUT_OTHER_VERSION", self.args, self.root)
        self.assertIn("version 1.2.1", what)
        self.assert_nothing_written()

    def test_a_changed_output_stops_in_its_checks(self) -> None:
        with (self.output / "analysis" / "activities.csv").open("ab") as handle:
            handle.write(b"changed\n")
        self.assert_stop("HANDOFF_INVALID", self.args, self.root)
        self.assert_nothing_written()

    def test_an_output_changed_after_its_checks_and_a_file_over_its_limit(self) -> None:
        csv_file = self.output / "analysis" / "activities.csv"
        changed = csv_file.read_bytes().replace(b"5000.0", b"6000.0")
        checked = series_file.load_view_data.__globals__["checked_output"]

        def checked_and_changed(output: Path) -> Any:
            answer = checked(output)
            csv_file.write_bytes(changed)
            return answer

        with mock.patch("garmin_running_data_normalizer.view.data.checked_output", checked_and_changed):
            self.assert_stop("OUTPUT_CHANGED", self.args, self.root)
        self.assert_nothing_written()
        shutil.rmtree(self.output)
        shutil.copytree(self.source_output, self.output)
        real = series_file.load_view_data

        def read_with_a_small_limit(output: Path, **options: Any) -> Any:
            return real(output, max_file_bytes=10, **options)

        with mock.patch.object(series_file, "load_view_data", read_with_a_small_limit):
            self.assert_stop("OUTPUT_NOT_AVAILABLE", self.args, self.root)
        self.assert_nothing_written()

    def test_the_place_of_the_csv_file(self) -> None:
        self.assert_stop("SERIES_PARENT_NOT_FOUND", ("series", "--run-output", self.output, "--output", self.root / "missing" / "s.csv"), self.root)
        places = [self.output / "s.csv", self.output / "analysis" / "s.csv"]
        if can_symlink(self.root):
            link = self.root / "link"
            link.symlink_to(self.output, target_is_directory=True)
            places.append(link / "s.csv")
        for place in places:
            with self.subTest(place=place.relative_to(self.root).as_posix()):
                self.assert_stop("SERIES_INSIDE_OUTPUT", ("series", "--run-output", self.output, "--output", place), self.root)
        # The output still passes its checks.
        self.assertEqual(cli("validate-handoff", "--input", self.output)[0], 0)
        with mock.patch("garmin_running_data_normalizer.common.new_file.tempfile.mkstemp", side_effect=PermissionError("denied")):
            self.assert_stop("SERIES_NOT_WRITTEN", self.args, self.root)
        self.assert_nothing_written()

    def test_a_file_or_a_link_in_the_place_is_never_replaced(self) -> None:
        existing = self.root / "existing.csv"
        existing.write_bytes(b"synthetic")
        places = [existing]
        if can_symlink(self.root):
            link = self.root / "link.csv"
            link.symlink_to(existing)
            broken = self.root / "broken.csv"
            broken.symlink_to(self.root / "nothing.csv")
            places += [link, broken]
        for place in places:
            with self.subTest(place=place.name):
                self.assert_stop("SERIES_EXISTS", ("series", "--run-output", self.output, "--output", place), self.root)
                self.assertEqual(existing.read_bytes(), b"synthetic")
        # A file put in the place after it was checked stays as it is.
        real = series_file.load_view_data

        def read_and_put(output: Path, **options: Any) -> Any:
            data = real(output, **options)
            self.target.write_bytes(b"put there")
            return data

        with mock.patch.object(series_file, "load_view_data", read_and_put):
            self.assert_stop("SERIES_EXISTS", self.args, self.root)
        self.assertEqual(self.target.read_bytes(), b"put there")
        self.assertEqual(sorted(path.name for path in self.root.iterdir() if path.name.startswith(".")), [])

    def test_the_arguments(self) -> None:
        cases = {
            "SERIES_ITEM_UNKNOWN": [("--item", "distance")],
            # The only activity of the example is after today: the output has no type.
            "SERIES_TYPE_UNKNOWN": [("--type", "running")],
            "SERIES_RANGE_INVALID": [
                ("--from", "2024-01-01"),
                ("--from", "2024-02-01", "--to", "2024-01-01"),
                ("--from", "2024-13-01", "--to", "2024-12-31"),
                ("--from", "20240101", "--to", "20241231"),
                ("--period", "1y", "--from", "2024-01-01", "--to", "2024-12-31"),
            ],
        }
        for code, options in cases.items():
            for option in options:
                with self.subTest(code=code, options=option):
                    self.assert_stop(code, (*self.args, *option), self.root)
                    self.assert_nothing_written()
        for option in (("--period", "2y"), ("--grain", "fortnight"), ("--type", "running", "--all-types")):
            with self.subTest(options=option):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    runner.main([str(arg) for arg in (*self.args, *option)])
                self.assertEqual(caught.exception.code, 2)

    def test_ctrl_c_leaves_no_part_of_the_file(self) -> None:
        with mock.patch("garmin_running_data_normalizer.common.new_file.os.link", side_effect=KeyboardInterrupt):
            exit_code, _stdout, stderr = cli(*self.args)
        self.assertEqual(exit_code, 130)
        self.assertEqual(stderr.splitlines()[0], f"ERROR [RUN_CANCELLED]: series was cancelled with Ctrl+C; {STOPS['RUN_CANCELLED'].next_step}")
        self.assert_nothing_written()
        real = series_file.write_new_file

        def written_then_cancelled(*args: Any, **kwargs: Any) -> None:
            real(*args, **kwargs)
            raise KeyboardInterrupt

        with mock.patch.object(series_file, "write_new_file", written_then_cancelled):
            exit_code, _stdout, stderr = cli(*self.args)
        self.assertEqual(exit_code, 130)
        self.assertTrue(stderr.startswith("ERROR [RUN_CANCELLED_AFTER_OUTPUT]: series was cancelled with Ctrl+C after it wrote its output"))
        self.assertEqual(self.target.read_text(encoding="utf-8"), HEADER + "\n")


def can_symlink(directory: Path) -> bool:
    probe = directory / "symlink-probe"
    try:
        probe.symlink_to(directory, target_is_directory=True)
    except OSError:
        return False
    probe.unlink()
    return True


if __name__ == "__main__":
    unittest.main()
