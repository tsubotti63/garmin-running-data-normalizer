"""The marks of the values filled from another source field, and three small
defects (stage A4d-2).

Sleep marks the field that gives its day (``sleep_day_source``) and how its
duration was made (``sleep_duration_source``); Activities mark the field that
gives their start (``start_time_source``), and fill the start from
``beginTimestamp`` when ``startTimeGmt`` holds no number, keeping a value of
another form for the audit record, while the key of an Activity without an
identifier stays as it was. Merged copies take the best-ranked mark, the
source fields first, and no mark when the field whose source it names
disagrees; copies are compared without their marks, so they count as before.
Across the time points of a Snapshot store, the two names of the start are
one field (merge rules v2.17). The HRV audit names its timezone apart, a FIT
session keeps the number of its sub-sport, and the External-safe Pack leaves
the month of an Activity without a date empty.
"""

from __future__ import annotations

import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.common.identity import garmin_activity_key
from garmin_running_data_normalizer.run_all import run_all
from tests.test_daily_unread_fields import write
from tests.test_fit_sport_profile import parsed_session
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_parity import differences, runs
from tests.test_snapshot_record_updates import load, write_export

END = "2030-03-01T20:00:00Z"
START = 1893456000000


def sleep_row(day: str | None, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "sleepStartTimestampGMT": "2030-03-01T12:00:00Z", "sleepEndTimestampGMT": END, **fields,
    }
    if day is not None:
        row["calendarDate"] = day
    return row


def marks_export(root: Path, name: str = "marks") -> Path:
    """An Export whose Sleep and Activities rows fill values from other fields."""
    source = write_export(root, name, [
        _activity("1001"),
        _activity("1002", startTimeGmt=None, beginTimestamp=START + 86400000),
        _activity("1003", startTimeGmt="x", beginTimestamp=START + 2 * 86400000),
        _activity("1004", startTimeGmt=None),
    ])
    write(source / "DI-Connect-Wellness" / "synthetic_sleepData.json", [
        sleep_row("2030-02-01", deepSleepSeconds=600, lightSleepSeconds=1200),
        # A calendar date that cannot be read: the end time gives the day.
        sleep_row("x", sleepTimeSeconds=1800),
        sleep_row("2030-02-03"),
        sleep_row("2030-02-04", sleepTimeSeconds=1800, totalSleepSeconds=1860),
        sleep_row("2030-02-05", deepSleepSeconds=600, deep_sleep_seconds=660),
    ])
    return source


def rows_by(output: Path, dataset: str, key: str) -> dict[str, dict[str, Any]]:
    return {str(row[key]): row for row in load(output / f"normalized/{dataset}.json")}


class MarksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        root = Path(cls._directory.name)
        cls.output = root / "output"
        run_all(marks_export(root), cls.output, external_safe_pack=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_sleep(self) -> None:
        rows = rows_by(self.output, "sleep_daily", "sleep_day")
        self.assertEqual(
            {day: (row["sleep_day_source"], row["sleep_duration_source"]) for day, row in rows.items()},
            {
                "2030-02-01": ("calendarDate", "stage_derived"),
                "2030-03-02": ("sleepEndTimestampGMT", "direct_fallback"),
                "2030-02-03": ("calendarDate", "null_fallback"),
                "2030-02-04": ("calendarDate", "direct_aliases_disagree"),
                "2030-02-05": ("calendarDate", "stage_aliases_disagree"),
            },
        )

    def test_activities(self) -> None:
        rows = rows_by(self.output, "activities", "activity_id")
        self.assertEqual(
            {key: (row["start_time_gmt_ms"], row["start_time_source"]) for key, row in rows.items()},
            {
                "1001": (START, "startTimeGmt"),
                "1002": (START + 86400000, "beginTimestamp"),
                # A start of another form is passed over and kept in the audit.
                "1003": (START + 2 * 86400000, "beginTimestamp"),
                "1004": (None, None),
            },
        )
        self.assertEqual(rows["1003"]["activity_date_local"], "2030-01-03")
        audit = load(self.output / "audit/activities.json")
        self.assertEqual(audit["invalid_value_counts"], {"start_time_gmt_ms": 1})
        codes = {item["code"] for item in load(self.output / "run_summary.json")["warnings"]}
        self.assertIn("DATA_VALUE_INVALID", codes)

    def test_the_analysis_table_and_the_month_of_an_activity_without_a_date(self) -> None:
        table = list(csv.DictReader(io.StringIO((self.output / "analysis/activities.csv").read_text(encoding="utf-8"))))
        self.assertEqual(
            sorted(row["start_time_source"] for row in table), ["", "beginTimestamp", "beginTimestamp", "startTimeGmt"]
        )
        with zipfile.ZipFile(self.output / "analysis/external_safe_handoff.zip") as archive:
            monthly = archive.read("safe/activities_monthly.csv").decode("utf-8")
        months = [row["activity_month"] for row in csv.DictReader(io.StringIO(monthly))]
        # The Activity without a date comes last, with no month.
        self.assertEqual(months, ["2030-01", "2030-01", "2030-01", ""])
        self.assertNotIn("None", monthly)


class KeyTest(unittest.TestCase):
    def test_the_key_of_an_activity_without_an_identifier_does_not_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = _activity("1001", startTimeGmt="x", beginTimestamp=START)
            row.pop("activityId")
            source = write_export(root, "export", [_activity("1002"), row])
            output = root / "output"
            run_all(source, output)
            [record] = [item for item in load(output / "normalized/activities.json") if item["activity_id"] is None]
            # The start is filled, but the key is made from the fields as before.
            self.assertEqual((record["start_time_gmt_ms"], record["start_time_source"]), (START, "beginTimestamp"))
            self.assertEqual(
                record["garmin_activity_key"],
                garmin_activity_key(None, "x", row["distance"], row["duration"], row["activityType"]),
            )


class CopiesTest(unittest.TestCase):
    """Copies are compared without their marks, and the merged row takes the
    best-ranked mark, or none when the field whose source it names disagrees."""

    def run_export(self, activities: list[dict[str, object]], sleep: list[dict[str, object]]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        source = write_export(root, "export", activities)
        write(source / "DI-Connect-Wellness" / "synthetic_sleepData.json", sleep)
        output = root / "output"
        run_all(source, output)
        return output

    def test_sleep_copies(self) -> None:
        output = self.run_export([_activity("1001")], [
            # The same day from the end time (in Asia/Tokyo) and from the
            # calendar date, with the same duration from a direct field and
            # from the stages: the filled copy comes first, and the marks
            # still name the source fields themselves.
            sleep_row(None, sleepTimeSeconds=1800),
            sleep_row("2030-03-02", deepSleepSeconds=600, lightSleepSeconds=1200),
            # Durations that disagree.
            sleep_row("2030-02-02", deepSleepSeconds=600),
            sleep_row("2030-02-02", deepSleepSeconds=660),
        ])
        rows = rows_by(output, "sleep_daily", "sleep_day")
        self.assertEqual(sorted(rows), ["2030-02-02", "2030-03-02"])
        self.assertEqual(
            (rows["2030-03-02"]["sleep_day_source"], rows["2030-03-02"]["sleep_duration_source"]),
            ("calendarDate", "stage_derived"),
        )
        self.assertEqual(
            (rows["2030-03-02"]["sleep_duration_minutes_ex_awake"], rows["2030-03-02"]["disagreeing_fields"]), (30.0, [])
        )
        # The two copies of the day are one record, as they were.
        self.assertEqual(load(output / "audit/sleep_daily.json")["accepted_record_count"], 2)
        self.assertEqual(
            (rows["2030-02-02"]["sleep_duration_minutes_ex_awake"], rows["2030-02-02"]["sleep_duration_source"]),
            (None, None),
        )
        self.assertIn("sleep_duration_minutes_ex_awake", rows["2030-02-02"]["disagreeing_fields"])

    def test_activity_copies(self) -> None:
        output = self.run_export([
            # The filled copy comes first.
            _activity("1001", startTimeGmt=None, beginTimestamp=START),
            _activity("1001"),
            _activity("1002"),
            _activity("1002", startTimeGmt=START + 1000),
        ], [])
        rows = rows_by(output, "activities", "activity_id")
        self.assertEqual((rows["1001"]["start_time_source"], rows["1001"]["disagreeing_fields"]), ("startTimeGmt", []))
        self.assertEqual((rows["1002"]["start_time_gmt_ms"], rows["1002"]["start_time_source"]), (None, None))
        # The copies of 1001 differ only in their marks: they are copies, as before.
        self.assertEqual(load(output / "audit/activities.json")["same_value_duplicate_count"], 1)


class SnapshotTest(unittest.TestCase):
    def test_a_snapshot_run_marks_as_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root / "runs", marks_export(root))
            self.assertEqual(differences(one_shot, snapshot), [])

    def run_snapshots(self, *activities: dict[str, object]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [write_export(root, f"export-{index}", [row]) for index, row in enumerate(activities, start=1)]
            _one_shot, snapshot = runs(root / "runs", *sources)
            [row] = load(snapshot / "normalized/activities.json")
            summary = load(snapshot / "snapshot/canonical_merge_summary.json")["datasets"]["activities"]
            return row, load(snapshot / "audit/activities.json"), summary

    def test_the_names_of_the_start_across_time_points(self) -> None:
        # The second Snapshot gives the start under the other name: its value
        # is the record's, and its name the mark (merge rules v2.17).
        row, audit, summary = self.run_snapshots(
            _activity("1001"), _activity("1001", startTimeGmt=None, beginTimestamp=START + 1000)
        )
        self.assertEqual((row["start_time_gmt_ms"], row["start_time_source"]), (START + 1000, "beginTimestamp"))
        [update] = audit["updates"]
        self.assertEqual([item["field"] for item in update["fields"]], ["startTimeGmt|beginTimestamp"])
        self.assertEqual(summary["updated_field_count"], 1)

    def test_both_names_change_once(self) -> None:
        # Both Snapshots hold both names: a change of the start is one change,
        # where field by field it was two.
        row, audit, summary = self.run_snapshots(
            _activity("1001", beginTimestamp=START),
            _activity("1001", startTimeGmt=START + 1000, beginTimestamp=START + 1000),
        )
        self.assertEqual((row["start_time_gmt_ms"], row["start_time_source"]), (START + 1000, "startTimeGmt"))
        [update] = audit["updates"]
        self.assertEqual([item["field"] for item in update["fields"]], ["startTimeGmt|beginTimestamp"])
        self.assertEqual(summary["updated_field_count"], 1)

    def test_names_in_two_forms_of_one_value_are_one_value(self) -> None:
        # A whole number and the same number with a decimal point are one value.
        row, audit, summary = self.run_snapshots(
            _activity("1001", startTimeGmt=float(START), beginTimestamp=START),
            _activity("1001", startTimeGmt=float(START), beginTimestamp=START),
        )
        self.assertEqual((row["start_time_source"], row["disagreeing_fields"]), ("startTimeGmt", []))
        self.assertEqual((audit["updates"], summary["updated_field_count"]), ([], 0))


class SmallDefectsTest(unittest.TestCase):
    def test_the_hrv_audit_names_its_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(write_export(root, "export", [_activity("1001")]), output, timezone_name="UTC")
            audit = load(output / "audit/hrv_daily.json")
            self.assertEqual(
                (audit["date_basis"], audit["date_timezone"]),
                ("fit_end_local_date_from_message_370_field_253_timestamp", "UTC"),
            )

    def test_a_fit_session_keeps_the_number_of_its_sub_sport(self) -> None:
        cases = {(1, 2): ("street", 2), (60, 99): (None, 99), (1, 255): (None, None)}
        for (sport, sub_sport), expected in cases.items():
            with self.subTest(sport=sport, sub_sport=sub_sport):
                session = parsed_session(sport, sub_sport)
                self.assertEqual((session["sub_sport"], session["sub_sport_code"]), expected)


if __name__ == "__main__":
    unittest.main()
