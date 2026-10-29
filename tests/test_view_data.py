"""The view page reads an output that this version made, and only that
(stage G1): the numbers against counts of the files, and the outputs that it
refuses."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Import the diagnostics package before modules that import standalone:
# the other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.output_check import OutputActionError
from garmin_running_data_normalizer.run_all import ACTIVITIES_CSV_FIT_SESSION_COLUMNS, run_all
from garmin_running_data_normalizer.view import data as data_module
from garmin_running_data_normalizer.view.data import load_view_data
from garmin_running_data_normalizer.view.items import ACTIVITIES, DATASETS, ITEMS, dataset_fields
from garmin_running_data_normalizer.view.series import activity_types, coverage, item_series, period_bounds
from tests.test_gui_runs import SYNTHETIC_EXPORT
from tests.test_local_timezone import EVENING_IN_NEW_YORK, NEW_YORK, activity_row, write_export
from tests.v1_3_outputs import as_release, as_v1_3
from tests.view_export import write_view_export

TODAY = date(2026, 10, 26)
RUNNING_TYPES = {"running", "treadmill_running", "trail_running"}
# The units of SCHEMA_CATALOG.json that the page converts; any other is a
# value as Garmin gives it.
UNITS = {"metre", "second", "minute", "millisecond", "millimetre", "percent", "beats_per_minute"}


def can_symlink(directory: Path) -> bool:
    probe = directory / "symlink-probe"
    try:
        probe.symlink_to(directory, target_is_directory=True)
    except OSError:
        return False
    probe.unlink()
    return True


def month(text: str) -> str:
    return text[:7]


def by_month(pairs: list[tuple[str, float]]) -> dict[str, list[float]]:
    found: dict[str, list[float]] = defaultdict(list)
    for when, value in pairs:
        found[month(when)].append(value)
    return found


def panel_by_month(data: Any, key: str, types: Any = None) -> dict[str, list[dict[str, Any]]]:
    periods = period_bounds(data, "all", "month")
    assert periods is not None
    answer = item_series(data, key, periods, types)
    starts = [date.fromordinal(first).isoformat() for first, _last, _partial in periods.spans]
    return {
        "lines": [
            {
                "series": line["series"],
                "values": {month(start): value for start, value in zip(starts, line["values"]) if value is not None},
                "counts": {month(start): count for start, count in zip(starts, line["counts"]) if count},
            }
            for line in answer["lines"]
        ],
        "left_out": answer["left_out"],
    }


class ViewOutputTest(unittest.TestCase):
    """One output of about two and a half years of synthetic data."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        cls.output = root / "output"
        run_all(write_view_export(root / "export"), cls.output)
        cls.data = load_view_data(cls.output, today=TODAY)
        with (cls.output / "analysis" / "activities.csv").open(encoding="utf-8", newline="") as handle:
            cls.activities = list(csv.DictReader(handle))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def rows(self, name: str) -> list[dict[str, Any]]:
        return json.loads((self.output / "normalized" / f"{name}.json").read_text(encoding="utf-8"))

    def assert_means(self, found: dict[str, Any], pairs: list[tuple[str, float]]) -> None:
        expected = by_month(pairs)
        self.assertEqual(set(found["values"]), set(expected))
        for key, values in expected.items():
            self.assertAlmostEqual(found["values"][key], sum(values) / len(values))
            self.assertEqual(found["counts"][key], len(values))

    def test_the_rows_are_those_of_the_files(self) -> None:
        self.assertEqual(self.data.version, json.loads((self.output / "run_summary.json").read_text())["product_version"])
        self.assertEqual(self.data.timezone, "Asia/Tokyo")
        self.assertEqual(len(self.data.rows[ACTIVITIES]), len(self.activities))
        for spec in DATASETS[1:]:
            with self.subTest(dataset=spec.name):
                self.assertEqual(len(self.data.rows[spec.name]), len(self.rows(spec.name)))
        self.assertEqual(self.data.no_date, {spec.name: 0 for spec in DATASETS})
        self.assertEqual(self.data.after_today, {spec.name: 0 for spec in DATASETS})
        days = [row["activity_date_local"] for row in self.activities] + [
            row[spec.date_field] for spec in DATASETS[1:] for row in self.rows(spec.name)
        ]
        self.assertEqual(
            (date.fromordinal(self.data.first_day).isoformat(), date.fromordinal(self.data.last_day).isoformat()),
            (min(days), max(days)),
        )
        # An activity at 21:00 UTC is on the next day in Tokyo.
        self.assertEqual(max(days), "2025-07-01")

    def test_each_activity_keeps_its_local_date_and_time_as_written(self) -> None:
        # Stage M3 of v2.2.0: the list of the activities of a period shows the
        # date and time of each activity as the output writes it.
        written = sorted((row["activity_date_local"], row["activity_datetime_local"]) for row in self.activities if row["activity_datetime_local"])
        kept = sorted(
            (date.fromordinal(row.day).isoformat(), row.marks["datetime"]) for row in self.data.rows[ACTIVITIES] if row.marks["datetime"] is not None
        )
        self.assertTrue(kept)
        self.assertEqual(kept, [pair for pair in written if pair[0] <= TODAY.isoformat()])
        for day, moment in kept:
            self.assertTrue(moment.startswith(day), (day, moment))

    def test_an_activity_without_the_column_of_its_date_and_time_has_none(self) -> None:
        # The column is not needed: a file without it is read, and its
        # activities have no date and time.
        dataset = next(entry for entry in DATASETS if entry.name == ACTIVITIES)
        names = sorted({"activity_date_local", "activity_type", "disagreeing_fields", *dataset_fields(ACTIVITIES)})
        cells = {"activity_date_local": "2024-01-05", "activity_type": "running"}
        # An empty cell of the column is no date and time either.
        for header, moment, expected in (
            (names, "2024-01-05T06:30:00+09:00", None),
            ([*names, "activity_datetime_local"], "2024-01-05T06:30:00+09:00", "2024-01-05T06:30:00+09:00"),
            ([*names, "activity_datetime_local"], "", None),
        ):
            with self.subTest(columns=len(header), moment=moment):
                values = {**cells, "activity_datetime_local": moment}
                text = ",".join(header) + "\n" + ",".join(values.get(name, "") for name in header) + "\n"
                records = data_module._activity_records(text.encode("utf-8"))
                rows, no_date, after_today = data_module._rows(dataset, records, date(2030, 1, 1).toordinal())
                self.assertEqual((len(rows), no_date, after_today), (1, 0, 0))
                self.assertEqual(rows[0].marks["datetime"], expected)

    def test_the_activity_types_and_the_running_types(self) -> None:
        counts: dict[str, int] = defaultdict(int)
        for row in self.activities:
            counts[row["activity_type"]] += 1
        self.assertEqual({entry["name"]: entry["count"] for entry in activity_types(self.data)}, counts)
        self.assertEqual({entry["name"] for entry in activity_types(self.data) if entry["running"]}, RUNNING_TYPES)

    def test_the_totals_of_the_running_activities(self) -> None:
        running = [row for row in self.activities if row["activity_type"] in RUNNING_TYPES]
        distances = by_month([(row["activity_date_local"], float(row["distance_m"])) for row in running])
        [line] = panel_by_month(self.data, "dist")["lines"]
        self.assertEqual(set(line["values"]), set(distances))
        for key, values in distances.items():
            self.assertAlmostEqual(line["values"][key], sum(values))
            self.assertEqual(line["counts"][key], len(values))
        # With the cycling counted too.
        everything = by_month([(row["activity_date_local"], 1.0) for row in self.activities])
        [line] = panel_by_month(self.data, "count", types=counts_of(self.activities))["lines"]
        self.assertEqual(line["values"], {key: float(len(values)) for key, values in everything.items()})

    def test_a_mean_of_activities_is_weighted_by_their_durations(self) -> None:
        running = [row for row in self.activities if row["activity_type"] in RUNNING_TYPES]
        weighted: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        without = 0
        for row in running:
            if not row["avg_hr"]:
                without += 1
                continue
            weighted[month(row["activity_date_local"])][0] += float(row["avg_hr"]) * float(row["duration_sec"])
            weighted[month(row["activity_date_local"])][1] += float(row["duration_sec"])
        found = panel_by_month(self.data, "hr")
        for key, (total, weight) in weighted.items():
            self.assertAlmostEqual(found["lines"][0]["values"][key], total / weight)
        self.assertEqual(found["left_out"]["no_value"], without)

    def test_the_running_form_comes_from_the_linked_fit_sessions(self) -> None:
        linked = [row for row in self.activities if row["fit_avg_vertical_oscillation_mm"]]
        self.assertEqual(len(linked), 3)
        found = panel_by_month(self.data, "vo")
        self.assertEqual(sum(found["lines"][0]["counts"].values()), 3)
        self.assertEqual(
            found["left_out"]["no_value"],
            sum(1 for row in self.activities if row["activity_type"] in RUNNING_TYPES) - 3,
        )
        for row in linked:
            self.assertAlmostEqual(
                found["lines"][0]["values"][month(row["activity_date_local"])],
                float(row["fit_avg_vertical_oscillation_mm"]),
            )

    def test_the_daily_items_are_means_of_the_days_with_a_value(self) -> None:
        cases = {
            "rhr": ("uds_daily", "resting_heart_rate"),
            "steps": ("uds_daily", "steps"),
            "hrv": ("hrv_daily", "hrv_value"),
            "endu": ("endurance_score_daily", "overall_score"),
            "hill": ("hill_score_daily", "overall_score"),
        }
        for key, (name, field) in cases.items():
            with self.subTest(item=key):
                pairs = [(row["calendar_date"], row[field]) for row in self.rows(name) if row[field] is not None]
                self.assertTrue(pairs)
                [line] = panel_by_month(self.data, key)["lines"]
                self.assert_means(line, pairs)

    def test_a_sleep_counts_only_on_the_days_that_it_may_be_used(self) -> None:
        rows = self.rows("sleep_daily")
        used = [
            (row["sleep_day"], row["sleep_duration_minutes_ex_awake"])
            for row in rows
            if row["sleep_normalization_status"] == "available"
            and row["sleep_source_available_for_analysis_flag"] is True
            and row["sleep_duration_minutes_ex_awake"] is not None
        ]
        review = {row["sleep_day"] for row in rows if row["sleep_normalization_status"] == "needs_review"}
        self.assertTrue(review)
        found = panel_by_month(self.data, "sleep")
        self.assert_means(found["lines"][0], used)
        self.assertEqual(found["left_out"]["sleep_review_days"], len(review))

    def test_the_sleep_score_is_a_mean_of_the_sleeps_that_may_be_used(self) -> None:
        rows = self.rows("sleep_daily")
        used = [
            (row["sleep_day"], row["sleep_score"])
            for row in rows
            if row["sleep_normalization_status"] == "available"
            and row["sleep_source_available_for_analysis_flag"] is True
            and row["sleep_score"] is not None
        ]
        self.assertTrue(used)
        found = panel_by_month(self.data, "sscore")
        self.assert_means(found["lines"][0], used)

    def test_every_item_has_values_in_the_synthetic_export(self) -> None:
        # The synthetic Export gives values of every item, so that a shape of
        # the test data that the normalization does not read is noticed, as
        # that of the sleep scores was (the checker's review, 2026-10-26).
        shelf = coverage(self.data)
        self.assertEqual([item.key for item in ITEMS if not shelf[item.key]["months"]], [])

    def test_the_records_of_a_day_are_all_points(self) -> None:
        rows = [row for row in self.rows("training_readiness_daily") if row["calendar_date"].startswith("2024-03")]
        periods = period_bounds(self.data, (date(2024, 3, 1), date(2024, 3, 31)), "day")
        assert periods is not None
        answer = item_series(self.data, "tr", periods)
        [line] = answer["lines"]
        self.assertEqual(len(line["points"]), len(rows))
        per_day: dict[str, int] = defaultdict(int)
        for row in rows:
            per_day[row["calendar_date"]] += 1
        self.assertEqual(answer["left_out"]["days_with_several_records"], sum(1 for count in per_day.values() if count > 1))
        self.assertEqual(sorted(value for _index, value in line["points"]), sorted(float(row["training_readiness_score"]) for row in rows))

    def test_the_series_and_sports_of_vo2max_stay_apart(self) -> None:
        rows = self.rows("vo2max_daily")
        expected: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
        for row in rows:
            expected[(row["vo2max_source_series"], row["sport"])].append((row["calendar_date"], row["vo2max"]))
        lines = panel_by_month(self.data, "vo2")["lines"]
        self.assertEqual(
            [(line["series"]["vo2max_source_series"], line["series"]["sport"]) for line in lines],
            [("activity_vo2max_daily", "RUNNING"), ("performance_metrics_daily", "CYCLING"), ("performance_metrics_daily", "RUNNING")],
        )
        for line in lines:
            self.assert_means(line, expected[(line["series"]["vo2max_source_series"], line["series"]["sport"])])

    def test_the_race_predictions_are_means_of_their_records(self) -> None:
        for key, field in (("p5k", "race_time_5k_sec"), ("pfull", "race_time_marathon_sec")):
            with self.subTest(item=key):
                pairs = [(row["calendar_date"], row[field]) for row in self.rows("race_prediction_daily")]
                self.assert_means(panel_by_month(self.data, key)["lines"][0], pairs)

    def test_rows_after_today_are_left_out_and_counted(self) -> None:
        cut = date(2024, 12, 31)
        data = load_view_data(self.output, today=cut)
        self.assertEqual(date.fromordinal(data.last_day), cut)
        later = sum(1 for row in self.activities if row["activity_date_local"] > cut.isoformat())
        self.assertEqual(data.after_today[ACTIVITIES], later)
        self.assertEqual(len(data.rows[ACTIVITIES]), len(self.activities) - later)
        for spec in DATASETS[1:]:
            with self.subTest(dataset=spec.name):
                later = sum(1 for row in self.rows(spec.name) if row[spec.date_field] > cut.isoformat())
                self.assertEqual(data.after_today[spec.name], later)

    def test_the_units_are_those_of_the_schema_catalog(self) -> None:
        catalog = json.loads((self.output / "SCHEMA_CATALOG.json").read_text(encoding="utf-8"))
        units = {
            (entry["dataset"], field["field"]): field["unit_or_domain"]
            for entry in catalog["datasets"]
            for field in entry["fields"]
        }
        fit_fields = dict(ACTIVITIES_CSV_FIT_SESSION_COLUMNS)
        for item in ITEMS:
            if item.field is None:
                continue
            with self.subTest(item=item.key):
                if item.dataset != ACTIVITIES:
                    unit = units[(item.dataset, item.field)]
                elif item.field in fit_fields:
                    unit = units[("fit_sessions", fit_fields[item.field])]
                else:
                    unit = units[("activities", item.field)]
                self.assertEqual(item.unit, unit if unit in UNITS else None)


def counts_of(rows: list[dict[str, str]]) -> set[str]:
    return {row["activity_type"] for row in rows}


class ViewOutputRefusalTest(unittest.TestCase):
    """The outputs that the view page does not read, from copies of one
    output of the synthetic example."""

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
        self.csv = self.output / "analysis" / "activities.csv"

    def assert_code(self, code: str, version: str | None = None, **options: Any) -> None:
        with self.assertRaises(OutputActionError) as caught:
            load_view_data(self.output, today=TODAY, **options)
        self.assertEqual((caught.exception.code, caught.exception.version), (code, version))

    def after_the_checks(self, change: Any) -> Any:
        """Change the output after the checks have passed, before the reading."""
        checked = data_module.checked_output

        def checked_and_changed(output: Path) -> Any:
            answer = checked(output)
            change()
            return answer

        return patch.object(data_module, "checked_output", checked_and_changed)

    def test_an_output_of_this_version_is_read(self) -> None:
        data = load_view_data(self.output, today=date(2030, 6, 1))
        self.assertEqual(len(data.rows[ACTIVITIES]), 1)

    def test_an_output_of_1_3_is_refused_with_its_version(self) -> None:
        # It passes its checks, but its numbers are not given (stage G2).
        as_v1_3(self.output)
        self.assert_code("SERIES_OUTPUT_OTHER_VERSION", "1.3.3")

    def test_an_output_of_another_version_is_refused_with_its_version(self) -> None:
        written = json.loads((self.output / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
        as_release(self.output, "1.2.1", tuple(written))
        self.assert_code("OUTPUT_OTHER_VERSION", "1.2.1")

    def test_an_output_changed_before_the_checks_stops_in_the_checks(self) -> None:
        with self.csv.open("ab") as handle:
            handle.write(b"changed\n")
        self.assert_code("HANDOFF_INVALID")

    def test_a_file_changed_after_the_checks_is_not_read_as_checked(self) -> None:
        before = self.csv.read_bytes()
        after = before.replace(b"5000.0", b"6000.0")
        # The same size: only the hash tells the change.
        self.assertEqual((len(after), after != before), (len(before), True))
        with self.after_the_checks(lambda: self.csv.write_bytes(after)):
            self.assert_code("OUTPUT_CHANGED")

    def test_a_file_and_the_manifest_changed_together_after_the_checks(self) -> None:
        manifest_path = self.output / "run_manifest.json"

        def change() -> None:
            data = self.csv.read_bytes() + b"x,2030-01-02,,running,running,1.0" + b"," * 21 + b"\n"
            self.csv.write_bytes(data)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest["outputs"]:
                if entry["path"] == "analysis/activities.csv":
                    entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        with self.after_the_checks(change):
            self.assert_code("OUTPUT_CHANGED")

    def test_a_manifest_that_could_not_be_read_before_the_checks(self) -> None:
        read = data_module._plain_bytes
        calls: list[Path] = []

        def first_unread(path: Path, limit: int) -> bytes | None:
            calls.append(path)
            return None if len(calls) == 1 else read(path, limit)

        with patch.object(data_module, "_plain_bytes", first_unread):
            self.assert_code("OUTPUT_CHANGED")

    def test_the_limits_are_those_of_the_plan(self) -> None:
        # One file as one FIT file or one file in a ZIP file, all the files
        # together, and the manifest, which lists every file of the Export.
        self.assertEqual(
            (data_module.MAX_FILE_BYTES, data_module.MAX_TOTAL_BYTES, data_module.MAX_MANIFEST_BYTES),
            (128 * 1024 * 1024, 512 * 1024 * 1024, 256 * 1024 * 1024),
        )

    def test_a_manifest_over_its_limit_is_not_read(self) -> None:
        with patch.object(data_module, "MAX_MANIFEST_BYTES", 10):
            self.assert_code("OUTPUT_NOT_AVAILABLE")

    def test_files_over_the_limits_are_not_read(self) -> None:
        manifest = json.loads((self.output / "run_manifest.json").read_text(encoding="utf-8"))
        sizes = {entry["path"]: entry["bytes"] for entry in manifest["outputs"]}
        total = sum(sizes[spec.path] for spec in DATASETS)
        largest = max(sizes[spec.path] for spec in DATASETS)
        with patch.object(data_module, "_checked_bytes") as read:
            self.assert_code("OUTPUT_NOT_AVAILABLE", max_file_bytes=largest - 1)
            self.assert_code("OUTPUT_NOT_AVAILABLE", max_file_bytes=largest, max_total_bytes=total - 1)
            read.assert_not_called()
        load_view_data(self.output, today=TODAY, max_file_bytes=largest, max_total_bytes=total)

    def test_a_file_replaced_by_a_link_after_the_checks(self) -> None:
        if not can_symlink(self.root):
            self.skipTest("symbolic links are not available")
        copy = self.root / "activities.csv"
        shutil.copyfile(self.csv, copy)

        def change() -> None:
            self.csv.unlink()
            self.csv.symlink_to(copy)

        with self.after_the_checks(change):
            self.assert_code("OUTPUT_NOT_AVAILABLE")


class ViewTimezoneTest(unittest.TestCase):
    def test_the_dates_and_today_are_those_of_the_output_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export", [activity_row(1, EVENING_IN_NEW_YORK)])
            run_all(export, root / "output", timezone_name=NEW_YORK)
            zones: list[str] = []

            class Clock:
                @staticmethod
                def now(zone: Any) -> datetime:
                    zones.append(zone.key)
                    return datetime(2024, 1, 1, 21, 0, tzinfo=zone)

            with patch.object(data_module, "datetime", Clock):
                data = load_view_data(root / "output")
        self.assertEqual(zones, [NEW_YORK])
        self.assertEqual((data.timezone, data.today), (NEW_YORK, date(2024, 1, 1).toordinal()))
        # 20:00 in New York on 1 January is 2 January in UTC.
        self.assertEqual([date.fromordinal(row.day) for row in data.rows[ACTIVITIES]], [date(2024, 1, 1)])


class ViewImportTest(unittest.TestCase):
    def test_each_module_can_be_the_first_imported(self) -> None:
        # A new Python, which imports the package of this tree first.
        source = str(Path(__file__).resolve().parents[1] / "src")
        for module in (
            "garmin_running_data_normalizer.output_check",
            "garmin_running_data_normalizer.view.data",
            "garmin_running_data_normalizer.view.series",
        ):
            with self.subTest(module=module):
                completed = subprocess.run(
                    [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {source!r}); import {module}"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
