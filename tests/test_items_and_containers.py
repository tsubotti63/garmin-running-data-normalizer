"""Items of a list of records that are not objects, and values of another form
in the place of a list of records, are left out and counted, alike in one-shot
and Snapshot runs (stage A3d-2c-2); an item that is an empty value is an empty
record, which a run only counts."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.intake.accounts import payload_accounts
from garmin_running_data_normalizer.intake.discovery import read_export
from garmin_running_data_normalizer.normalizers.activities import normalize_activities
from garmin_running_data_normalizer.normalizers.gear import normalize_gear
from garmin_running_data_normalizer.normalizers.personal_records import (
    normalize_personal_records,
)
from garmin_running_data_normalizer.normalizers.records import EMPTY_RECORD
from garmin_running_data_normalizer.normalizers.source_records import (
    DAILY_WRAPPERS,
    MARK_FIELD,
    MARK_VALUE_FIELD,
    METRIC_WRAPPERS,
    NOT_AN_OBJECT,
    RECORDS_NOT_READABLE,
    activity_items,
    container_items,
    file_items,
    list_items,
    mark,
    mark_holds_a_value,
)
from garmin_running_data_normalizer.run_all import (
    CANDIDATE_ITEMS_LEFT_OUT_MESSAGE,
    DAILY_ROWS_LEFT_OUT_MESSAGE,
    ITEMS_LEFT_OUT_MESSAGE,
    RECORD_ROWS_LEFT_OUT_MESSAGE,
    RunAllError,
    run_all,
)
from garmin_running_data_normalizer.runner import GoldenPathError, run_activities
from garmin_running_data_normalizer.snapshot import initialize_store, run_snapshot_all
from garmin_running_data_normalizer.snapshot.policies import MERGE_RULES_VERSION
from tests.test_repeated_records import audit, table
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, gear, load, personal_record
from tests.test_snapshot_unreadable_files import one_snapshot, register

DAY = "2030-02-01"
ACTIVITIES = "DI-Connect-Fitness/synthetic_summarizedActivities.json"
MORE_ACTIVITIES = "DI-Connect-Fitness/synthetic_more_summarizedActivities.json"
GEAR = "DI-Connect-Fitness/synthetic_gear.json"
RECORDS = "DI-Connect-Fitness/synthetic_personalRecord.json"
UDS = "DI-Connect-Aggregator/UDSFile_1.json"
HILL = "DI-Connect-Metrics/HillScore_1.json"
SLEEP = "DI-Connect-Wellness/synthetic_sleepData.json"
LACTATE = "DI-Connect-Wellness/synthetic_userBioMetrics.json"
RECORD_TABLES = ("activities", "gear", "activity_gear", "personal_records")
DAILY_TABLES = ("uds_daily", "hill_score_daily", "sleep_daily")
LACTATE_AUDIT = "lactate_threshold_candidates"
UDS_ROW = {"calendarDate": DAY, "totalSteps": 5}
HILL_ROW = {"calendarDate": DAY, "overallScore": 50}
SLEEP_ROW = {
    "calendarDate": DAY,
    "sleepStartTimestampGMT": "2030-01-31T22:00:00.0",
    "sleepEndTimestampGMT": "2030-02-01T05:00:00.0",
    "deepSleepSeconds": 3600,
}
LACTATE_ROW = {"lactateThresholdHeartRate": 166, "metaData": {"calendarDate": DAY, "sequence": 1}}
# A text of an item that no output may hold.
PRIVATE_ITEM = "synthetic-private-item-text"


def activities(*rows: Any, **wrapper: Any) -> list[dict[str, Any]]:
    return [{"summarizedActivitiesExport": list(rows), **wrapper}]


BASE = {ACTIVITIES: activities(_activity("A1"), _activity("A2"))}


def export(root: Path, name: str, files: dict[str, Any]) -> Path:
    """An Export of these files; a text is written as it is, as the text of
    a JSON file, and any other value as JSON."""
    source = root / name
    for relative, value in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
    return source


def summary_of(output: Path) -> dict[str, Any]:
    return load(output / "run_summary.json")


def rows_left_out_lines(output: Path) -> list[str]:
    text = (output / "START_HERE.md").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.startswith("- Rows left out")]


def outcome(output: Path) -> dict[str, Any]:
    """What a run of one Export gives, whatever the form of the run."""
    summary = summary_of(output)
    quality = load(output / "diagnostics/run_quality.json")
    completeness = load(output / "diagnostics/source_completeness.json")
    lactate = audit(output, LACTATE_AUDIT)
    return {
        "status": summary["status"],
        "warnings": sorted(
            (
                item["code"],
                item.get("family", ""),
                item.get("dataset", ""),
                item.get("count", 1),
                item.get("message", ""),
            )
            for item in summary["warnings"]
        ),
        "candidate_warning_count": summary.get("candidate_warning_count", 0),
        "families": {
            family: (result["status"], result["record_count"], result.get("left_out_row_count", 0))
            for family, result in summary["family_results"].items()
        },
        "audits": {
            dataset: {
                field: audit(output, dataset).get(field)
                for field in (
                    "record_count",
                    "source_record_count",
                    "accepted_record_count",
                    "excluded_record_count",
                    "excluded_reason_counts",
                    "empty_record_count",
                )
            }
            for dataset in (*RECORD_TABLES, *DAILY_TABLES)
        },
        "lactate": {
            field: lactate.get(field)
            for field in (
                "candidate_count",
                "family_source_record_counts",
                "excluded_record_count",
                "excluded_reason_counts",
                "empty_record_count",
            )
        },
        "run_quality": {
            "excluded": {
                key: value
                for key, value in quality["excluded"].items()
                if key != "authority_references"
            },
            "warnings": quality["warnings"],
        },
        "content_validity": sorted(
            (item["source_family_id"], item["content_validity"])
            for item in completeness["families"]
        ),
        "tables": {dataset: table(output, dataset) for dataset in (*RECORD_TABLES, *DAILY_TABLES)},
        "rows_left_out": rows_left_out_lines(output),
    }


def both_forms(test: unittest.TestCase, root: Path, source: Path, name: str) -> Path:
    """Run one Export once and as one Snapshot; check that they agree, and
    return the output of the one-shot run."""
    one_shot = root / f"{name}-one-shot"
    run_all(source, one_shot)
    snapshot = one_snapshot(root, source, f"{name}-snapshot")
    test.assertEqual(outcome(snapshot), outcome(one_shot))
    return one_shot


def left_out_by_dataset(output: Path) -> dict[str, dict[str, int]]:
    """The reasons for which rows were left out, by dataset, from the audit
    records; the Lactate Threshold candidates by their own audit."""
    found: dict[str, dict[str, int]] = {}
    for dataset in (*RECORD_TABLES, *DAILY_TABLES, LACTATE_AUDIT):
        reasons = audit(output, dataset).get("excluded_reason_counts") or {}
        if reasons:
            found[dataset] = dict(reasons)
    return found


def empty_by_dataset(output: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    for dataset in (*RECORD_TABLES, *DAILY_TABLES, LACTATE_AUDIT):
        count = audit(output, dataset).get("empty_record_count")
        if count:
            found[dataset] = count
    return found


def row_warnings(output: Path) -> dict[str, tuple[int, str]]:
    return {
        str(item.get("dataset") or item["family"]): (item["count"], item["message"])
        for item in summary_of(output)["warnings"]
        if item["code"] == "DATA_ROW_LEFT_OUT"
    }


class ExtractionTest(unittest.TestCase):
    def test_a_list_of_records(self) -> None:
        record = {"calendarDate": DAY}
        self.assertEqual(
            list_items([record, 5, "x", None, True, [], [1], ""]),
            [
                record,
                mark(NOT_AN_OBJECT, 5),
                mark(NOT_AN_OBJECT, "x"),
                mark(NOT_AN_OBJECT, None),
                mark(NOT_AN_OBJECT, True),
                mark(NOT_AN_OBJECT, []),
                mark(NOT_AN_OBJECT, [1]),
                mark(NOT_AN_OBJECT, ""),
            ],
        )
        # An empty value holds no records; any other value in the place of
        # the list is one mark, since its records cannot be read.
        for value in (None, "", [], {}):
            with self.subTest(value=value):
                self.assertEqual(list_items(value), [])
        for value in (5, 0, False, "abc", {"a": 1}):
            with self.subTest(value=value):
                self.assertEqual(list_items(value), [mark(RECORDS_NOT_READABLE, value)])

    def test_a_mark_holds_a_value_unless_its_item_is_an_empty_value(self) -> None:
        for value, holds in ((None, False), ("", False), ([], False), (0, True), (False, True), ("x", True)):
            with self.subTest(value=value):
                self.assertEqual(mark_holds_a_value(mark(NOT_AN_OBJECT, value)), holds)
        self.assertTrue(mark_holds_a_value(mark(RECORDS_NOT_READABLE, 5)))
        self.assertEqual(set(mark(NOT_AN_OBJECT, 1)), {MARK_FIELD, MARK_VALUE_FIELD})

    def test_a_daily_or_performance_metric_file(self) -> None:
        record = {"calendarDate": DAY}
        self.assertEqual(file_items([record, 7], DAILY_WRAPPERS), [record, mark(NOT_AN_OBJECT, 7)])
        self.assertEqual(
            file_items({"values": [record, None]}, DAILY_WRAPPERS),
            [record, mark(NOT_AN_OBJECT, None)],
        )
        # The first wrapper that holds a list, in the order of the wrappers.
        self.assertEqual(
            file_items({"sleepData": [7], "data": [record]}, DAILY_WRAPPERS), [record]
        )
        self.assertEqual(file_items({"data": [record]}, METRIC_WRAPPERS), [record])
        self.assertEqual(file_items({"values": [record]}, METRIC_WRAPPERS), [{"values": [record]}])
        # A wrapper of another form is not a list of records: the top object
        # is the record, as before.
        self.assertEqual(file_items({"data": 5, **record}, DAILY_WRAPPERS), [{"data": 5, **record}])
        self.assertEqual(file_items(5, DAILY_WRAPPERS), [mark(RECORDS_NOT_READABLE, 5)])
        self.assertEqual(file_items(None, DAILY_WRAPPERS), [])
        # A mark written by a Snapshot build in the place of a file's value.
        self.assertEqual(file_items(mark(NOT_AN_OBJECT, 5), DAILY_WRAPPERS), [mark(NOT_AN_OBJECT, 5)])

    def test_a_gear_or_personal_records_file(self) -> None:
        container = {"gearDTOS": []}
        self.assertEqual(container_items(container), [container])
        self.assertEqual(container_items([container, 5]), [container, mark(NOT_AN_OBJECT, 5)])
        self.assertEqual(container_items(5), [mark(RECORDS_NOT_READABLE, 5)])
        self.assertEqual(container_items(None), [])

    def test_an_activities_file(self) -> None:
        one, two = _activity("A1"), _activity("A2")
        self.assertEqual(
            activity_items([7, {"summarizedActivitiesExport": [one, "x", None]}]),
            [mark(NOT_AN_OBJECT, 7), one, mark(NOT_AN_OBJECT, "x"), mark(NOT_AN_OBJECT, None)],
        )
        self.assertEqual(
            activity_items([{"summarizedActivitiesExport": 5}, {"summarizedActivitiesExport": [one]}]),
            [mark(RECORDS_NOT_READABLE, 5), one],
        )
        self.assertEqual(activity_items({"summarizedActivitiesExport": None}), [])
        self.assertEqual(activity_items(5), [mark(RECORDS_NOT_READABLE, 5)])
        self.assertEqual(activity_items(None), [])
        # The other lists inside the objects are searched for records as
        # before, and their other items are not records.
        self.assertEqual(
            activity_items([{"wrapper": [{"summarizedActivitiesExport": [one]}, 7], "other": two}]),
            [one, two],
        )
        self.assertEqual(activity_items([one, [two, 7]]), [one, two])

    def test_without_a_counter_an_item_that_holds_a_value_stops_the_normalization(self) -> None:
        cases = (
            ({ACTIVITIES: activities(_activity("A1"), 5)}, lambda root, assets: normalize_activities(root, assets=assets)),
            ({GEAR: [{"gearDTOS": 5}]}, lambda root, assets: normalize_gear(root, assets=assets)),
            ({RECORDS: [{"personalRecords": [5]}]}, lambda root, assets: normalize_personal_records(root, assets=assets)),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (files, normalize) in enumerate(cases):
                source = export(root, f"export-{index}", files)
                with self.subTest(case=index), read_export(source) as reading:
                    with self.assertRaisesRegex(ValueError, "not an object"):
                        normalize(str(source), reading.assets)
            # An item that is an empty value holds nothing; it is passed over.
            source = export(root, "empty", {ACTIVITIES: activities(_activity("A1"), None, "")})
            with read_export(source) as reading:
                self.assertEqual(len(normalize_activities(str(source), assets=reading.assets)), 1)
                left_out: Counter[str] = Counter()
                normalize_activities(str(source), assets=reading.assets, left_out=left_out)
                self.assertEqual(left_out, Counter({EMPTY_RECORD: 2}))


# What each case leaves out, by dataset and reason, and how many empty records
# it counts, by dataset.
CASES: dict[str, tuple[dict[str, Any], dict[str, dict[str, int]], dict[str, int]]] = {
    # Values of another form in the place of a list of records.
    "gearDTOS is a number": ({**BASE, GEAR: [{"gearDTOS": 5}]}, {"gear": {RECORDS_NOT_READABLE: 1}}, {}),
    "gearDTOS is text": ({**BASE, GEAR: [{"gearDTOS": "abc"}]}, {"gear": {RECORDS_NOT_READABLE: 1}}, {}),
    "gearDTOS is an object": ({**BASE, GEAR: [{"gearDTOS": {"a": 1}}]}, {"gear": {RECORDS_NOT_READABLE: 1}}, {}),
    "the links of Gear are a number": (
        {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": 7}]},
        {"activity_gear": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "the links of Gear are a list": (
        {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": [{"activityId": "A1"}]}]},
        {"activity_gear": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "the links of one Gear are a number": (
        {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": {"1": 7}}]},
        {"activity_gear": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "the links of one Gear are text": (
        {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": {"1": "abc"}}]},
        {"activity_gear": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "personalRecords is a number": (
        {**BASE, RECORDS: [{"personalRecords": 5}]},
        {"personal_records": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "personalRecords is text": (
        {**BASE, RECORDS: [{"personalRecords": "abc"}]},
        {"personal_records": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "summarizedActivitiesExport is a number": (
        {**BASE, MORE_ACTIVITIES: [{"summarizedActivitiesExport": 5}]},
        {"activities": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "summarizedActivitiesExport is text": (
        {**BASE, MORE_ACTIVITIES: [{"summarizedActivitiesExport": "abc"}]},
        {"activities": {RECORDS_NOT_READABLE: 1}},
        {},
    ),
    "a daily file is a number": ({**BASE, UDS: "5"}, {"uds_daily": {RECORDS_NOT_READABLE: 1}}, {}),
    "a daily file is text": ({**BASE, UDS: '"abc"'}, {"uds_daily": {RECORDS_NOT_READABLE: 1}}, {}),
    "a Hill Score file is a number": ({**BASE, HILL: "5"}, {"hill_score_daily": {RECORDS_NOT_READABLE: 1}}, {}),
    # Items of a file's top list that are not objects.
    "an item of an Activities file": (
        {ACTIVITIES: [5, {"summarizedActivitiesExport": [_activity("A1"), _activity("A2")]}]},
        {"activities": {NOT_AN_OBJECT: 1}},
        {},
    ),
    "an item of a Gear file": (
        {**BASE, GEAR: [5, {"gearDTOS": [gear(1, "Shoe")]}]},
        {"gear": {NOT_AN_OBJECT: 1}},
        {},
    ),
    "an item of a Personal Records file": (
        {**BASE, RECORDS: [5, {"personalRecords": [personal_record(1, "A1", 1.0)]}]},
        {"personal_records": {NOT_AN_OBJECT: 1}},
        {},
    ),
    # Items of a list of records that are not objects.
    "items of the Activities": (
        {ACTIVITIES: activities(1, "x", None, True, [], _activity("A1"))},
        {"activities": {NOT_AN_OBJECT: 3}},
        {"activities": 2},
    ),
    "items of the Gear": (
        {**BASE, GEAR: [{"gearDTOS": [1, None, gear(1, "Shoe")]}]},
        {"gear": {NOT_AN_OBJECT: 1}},
        {"gear": 1},
    ),
    "items of the links of one Gear": (
        {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": {"1": [5, None, {"activityId": "A1"}]}}]},
        {"activity_gear": {NOT_AN_OBJECT: 1}},
        {"activity_gear": 1},
    ),
    "items of the Personal Records": (
        {**BASE, RECORDS: [{"personalRecords": [None, 5, personal_record(1, "A1", 1.0)]}]},
        {"personal_records": {NOT_AN_OBJECT: 1}},
        {"personal_records": 1},
    ),
    "items of a daily file": (
        {**BASE, UDS: [1, None, "x", UDS_ROW]},
        {"uds_daily": {NOT_AN_OBJECT: 2}},
        {"uds_daily": 1},
    ),
    "items of a Sleep file in its wrapper": (
        {**BASE, SLEEP: {"sleepData": [None, 5, SLEEP_ROW]}},
        {"sleep_daily": {NOT_AN_OBJECT: 1}},
        {"sleep_daily": 1},
    ),
    "items of a Hill Score file": (
        {**BASE, HILL: [1, None, HILL_ROW]},
        {"hill_score_daily": {NOT_AN_OBJECT: 1}},
        {"hill_score_daily": 1},
    ),
    "items of a Lactate Threshold file": (
        {**BASE, LACTATE: [1, None, LACTATE_ROW]},
        {LACTATE_AUDIT: {NOT_AN_OBJECT: 1}},
        {LACTATE_AUDIT: 1},
    ),
    # Nothing is left out.
    # With a record in another container: a Gear file without records is
    # read as an empty family by a one-shot run and as no family by a
    # Snapshot run, as before (stage A3d-4).
    "gearDTOS is null": ({**BASE, GEAR: [{"gearDTOS": None}, {"gearDTOS": [gear(1, "Shoe")]}]}, {}, {}),
    "the links of Gear are empty": (
        {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": ""}]},
        {},
        {},
    ),
    "items of the Activities that are empty values": (
        {ACTIVITIES: activities(_activity("A1"), None, "", [])},
        {},
        {"activities": 3},
    ),
    "a Sleep file in the values wrapper": ({**BASE, SLEEP: {"values": [SLEEP_ROW]}}, {}, {}),
    "Lactate Threshold candidates in the data wrapper": ({**BASE, LACTATE: {"data": [LACTATE_ROW]}}, {}, {}),
}


class ItemsAndContainersRunTest(unittest.TestCase):
    def test_each_case_alike_in_both_forms_of_run(self) -> None:
        for name, (files, left_out, empty) in CASES.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = both_forms(self, root, export(root, "export", files), "run")
                self.assertEqual(left_out_by_dataset(output), left_out)
                self.assertEqual(empty_by_dataset(output), empty)
                summary = summary_of(output)
                self.assertEqual(summary["status"] == "PARTIAL_SUCCESS", bool(left_out))
                expected_warnings = {
                    ("lactate_threshold" if dataset == LACTATE_AUDIT else dataset): (
                        sum(reasons.values()),
                        CANDIDATE_ITEMS_LEFT_OUT_MESSAGE if dataset == LACTATE_AUDIT else ITEMS_LEFT_OUT_MESSAGE,
                    )
                    for dataset, reasons in left_out.items()
                }
                self.assertEqual(row_warnings(output), expected_warnings)
                if left_out:
                    [line] = rows_left_out_lines(output)
                    self.assertIn("or are items that are not records", line)
                else:
                    self.assertEqual(rows_left_out_lines(output), [])
                for path in output.rglob("*"):
                    if path.is_file():
                        data = path.read_bytes()
                        self.assertNotIn(MARK_FIELD.encode(), data, path.name)
                        self.assertNotIn(MARK_VALUE_FIELD.encode(), data, path.name)

    def test_the_wrappers_that_a_snapshot_reads_are_those_of_a_run(self) -> None:
        # The candidates under "data" were not read by the build until stage
        # A3d-2c-2; the Sleep records under "values" are read by both.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {**BASE, LACTATE: {"data": [LACTATE_ROW]}, SLEEP: {"values": [SLEEP_ROW]}}
            output = both_forms(self, root, export(root, "export", files), "run")
            self.assertEqual(audit(output, LACTATE_AUDIT)["candidate_count"], 1)
            self.assertEqual(len(table(output, "sleep_daily")), 1)

    def test_only_items_that_are_not_records_stop_both_forms_of_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", {ACTIVITIES: activities(1, "x", None)})
            with self.assertRaises(RunAllError) as one_shot:
                run_all(source, root / "one-shot")
            self.assertEqual(one_shot.exception.code, "ACTIVITIES_EMPTY")
            with self.assertRaises(RunAllError) as snapshot:
                one_snapshot(root, source)
            self.assertEqual(snapshot.exception.code, "ACTIVITIES_EMPTY")

    def test_rows_left_out_for_other_reasons_keep_their_messages(self) -> None:
        files = {
            ACTIVITIES: activities(_activity("A1"), _activity("X", activityId=[1])),
            UDS: [UDS_ROW, {"totalSteps": 7}],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export(root, "export", files), "run")
            self.assertEqual(
                row_warnings(output),
                {
                    "activities": (1, RECORD_ROWS_LEFT_OUT_MESSAGE),
                    "uds_daily": (1, DAILY_ROWS_LEFT_OUT_MESSAGE),
                },
            )
            [line] = rows_left_out_lines(output)
            self.assertNotIn("items that are not records", line)
            # With an item that is not a record, the dataset's warning names both.
            files[ACTIVITIES] = activities(_activity("A1"), _activity("X", activityId=[1]), 5)
            output = both_forms(self, root, export(root, "export-2", files), "run-2")
            self.assertEqual(row_warnings(output)["activities"], (2, ITEMS_LEFT_OUT_MESSAGE))
            self.assertEqual(row_warnings(output)["uds_daily"], (1, DAILY_ROWS_LEFT_OUT_MESSAGE))
            self.assertEqual(
                audit(output, "activities")["excluded_reason_counts"],
                {"identity_invalid": 1, NOT_AN_OBJECT: 1},
            )

    def test_copies_within_one_export_and_two_snapshots(self) -> None:
        files = {
            ACTIVITIES: activities(_activity("A1"), _activity("A2"), 5, 5, None),
            "DI-Connect-Fitness/copy/synthetic_summarizedActivities.json": activities(
                _activity("A1"), _activity("A2"), 5
            ),
            UDS: [UDS_ROW, "x", "x"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files)
            output = both_forms(self, root, source, "copies")
            self.assertEqual(
                left_out_by_dataset(output),
                {"activities": {NOT_AN_OBJECT: 3}, "uds_daily": {NOT_AN_OBJECT: 2}},
            )
            self.assertEqual(empty_by_dataset(output), {"activities": 1})
            # A later Export with the same files and one more; the same Export
            # registered again would be no new Snapshot.
            later = export(root, "later", {**files, GEAR: [{"gearDTOS": [gear(1, "Shoe")]}]})
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source, "S1", 1)
            register(store, later, "S2", 2)
            snapshots = root / "snapshots"
            run_snapshot_all(store, snapshots)
            # The same item in both Snapshots is one item, and its copies
            # within each Snapshot are further items, as for the rows without
            # a stable key (stage A3d-1).
            self.assertEqual(
                left_out_by_dataset(snapshots),
                {"activities": {NOT_AN_OBJECT: 5}, "uds_daily": {NOT_AN_OBJECT: 3}},
            )
            self.assertEqual(empty_by_dataset(snapshots), {"activities": 1})
            merge = load(snapshots / "snapshot/canonical_merge_summary.json")
            self.assertEqual(merge["merge_rules_version"], MERGE_RULES_VERSION)
            # Each distinct item is passed once, as a record without a key.
            for dataset, observations, records in (("activities", 8, 2), ("uds_daily", 4, 1)):
                summary = merge["datasets"][dataset]
                self.assertEqual(summary["keyless_observation_count"], observations, dataset)
                self.assertEqual(summary["keyless_record_count"], records, dataset)

    def test_marks_take_no_part_in_the_other_judgments_of_a_snapshot_run(self) -> None:
        links = {"1": [{"activityId": "A1"}]}
        plain = {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")], "gearActivityDTOs": links}]}
        with_items = {
            ACTIVITIES: activities(_activity("A1"), _activity("A2"), 5),
            GEAR: [{"gearDTOS": [gear(1, "Shoe"), "x"], "gearActivityDTOs": {"1": [{"activityId": "A1"}, 7]}}],
        }
        for first, second, expected in (
            (plain, with_items, 1),
            # The items of an earlier Snapshot are counted as well, as the
            # rows without a stable key are (stage A3d-1).
            (with_items, plain, 1),
        ):
            with self.subTest(latest_has_items=second is with_items), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = root / "store"
                initialize_store(store, ACCOUNT)
                register(store, export(root, "first", first), "S1", 1)
                register(store, export(root, "second", second), "S2", 2)
                output = root / "snapshots"
                run_snapshot_all(store, output)
                self.assertEqual(
                    left_out_by_dataset(output),
                    {dataset: {NOT_AN_OBJECT: expected} for dataset in RECORD_TABLES[:3]},
                )
                for dataset in RECORD_TABLES:
                    record_audit = audit(output, dataset)
                    self.assertEqual(record_audit["updated_record_count"], 0, dataset)
                    self.assertEqual(record_audit["not_in_latest_snapshot_count"], 0, dataset)
                self.assertEqual(audit(output, "activity_gear")["removed_link_count"], 0)
                self.assertEqual(len(table(output, "activity_gear")), 1)
                codes = {item["code"] for item in summary_of(output)["warnings"]}
                self.assertFalse({"VALUES_UPDATED", "RECORDS_NOT_IN_LATEST_SNAPSHOT"} & codes)

    def test_the_value_of_an_item_names_no_account(self) -> None:
        # A one-shot run reads no account inside an item that is not a
        # record, and the mark that a Snapshot build writes in its place is
        # no record either: the Snapshot run does not see a second account.
        other = [{"userProfilePk": 99999}]
        files = {
            ACTIVITIES: activities(
                _activity("A1", userProfileId=12345), _activity("A2", userProfileId=12345)
            ),
            UDS: [UDS_ROW, other],
        }
        self.assertEqual(payload_accounts(files[UDS]), set())
        self.assertEqual(payload_accounts([UDS_ROW, mark(NOT_AN_OBJECT, other)]), set())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export(root, "export", files), "run")
            self.assertEqual(left_out_by_dataset(output), {"uds_daily": {NOT_AN_OBJECT: 1}})

    def test_lactate_threshold_items_bound_the_run_as_a_candidate_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", {**BASE, LACTATE: [5, LACTATE_ROW]})
            output = both_forms(self, root, source, "run")
            summary = summary_of(output)
            self.assertEqual(summary["status"], "PARTIAL_SUCCESS")
            [warning] = [item for item in summary["warnings"] if item["code"] == "DATA_ROW_LEFT_OUT"]
            self.assertEqual(
                warning,
                {
                    "code": "DATA_ROW_LEFT_OUT",
                    "family": "lactate_threshold",
                    "count": 1,
                    "message": CANDIDATE_ITEMS_LEFT_OUT_MESSAGE,
                },
            )
            self.assertEqual(summary["candidate_warning_count"], 1)
            self.assertEqual(
                rows_left_out_lines(output)[0].split(", which")[0],
                "- Rows left out: 1 (`lactate_threshold` 1)",
            )
            self.assertEqual(audit(output, LACTATE_AUDIT)["candidate_count"], 1)
            self.assertIn("DATA_ROW_LEFT_OUT", {item["code"] for item in doctor_run_output(output)["findings"]})

    def test_the_support_bundle_and_the_safe_pack_carry_counts_only(self) -> None:
        files = {
            ACTIVITIES: activities(_activity("A1"), _activity("A2"), PRIVATE_ITEM),
            UDS: [UDS_ROW, [PRIVATE_ITEM]],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files)
            for name, output in (
                ("one-shot", root / "one-shot"),
                ("snapshot", None),
            ):
                if output is None:
                    store = root / "store"
                    initialize_store(store, ACCOUNT)
                    register(store, source)
                    output = root / "snapshot"
                    run_snapshot_all(store, output, external_safe_pack=True)
                else:
                    run_all(source, output, external_safe_pack=True)
                bundle = root / f"{name}-support.zip"
                build_support_bundle(output, bundle)
                self.assertIn("DATA_ROW_LEFT_OUT", {item["code"] for item in doctor_run_output(output)["findings"]})
                for path in output.rglob("*"):
                    if path.is_file():
                        with self.subTest(run=name, file=path.name):
                            self.assertNotIn(PRIVATE_ITEM.encode(), path.read_bytes())
                for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                    with zipfile.ZipFile(path) as archive:
                        content = b"".join(archive.read(member) for member in archive.namelist())
                    with self.subTest(run=name, archive=path.name):
                        self.assertIn(b"DATA_ROW_LEFT_OUT", content)
                        self.assertNotIn(PRIVATE_ITEM.encode(), content)
                        self.assertNotIn(MARK_FIELD.encode(), content)

    def test_without_such_items_the_outputs_have_nothing_new(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe")]}], LACTATE: [LACTATE_ROW]}
            output = both_forms(self, root, export(root, "export", files), "plain")
            for dataset in RECORD_TABLES:
                self.assertNotIn("empty_record_count", audit(output, dataset))
                self.assertNotIn("excluded_reason_counts", audit(output, dataset))
            lactate = audit(output, LACTATE_AUDIT)
            for field in ("excluded_record_count", "excluded_reason_counts", "empty_record_count"):
                self.assertNotIn(field, lactate)
            self.assertNotIn("DATA_ROW_LEFT_OUT", {item["code"] for item in summary_of(output)["warnings"]})


class GoldenPathTest(unittest.TestCase):
    def test_the_golden_path_stops_on_an_item_that_is_not_a_record(self) -> None:
        cases = {
            "an item of the list": {ACTIVITIES: activities(_activity("A1"), 5)},
            "a list of another form": {**BASE, MORE_ACTIVITIES: [{"summarizedActivitiesExport": 5}]},
            "an item of the file's top list": {ACTIVITIES: [7, *activities(_activity("A1"))]},
        }
        for name, files in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaisesRegex(GoldenPathError, "not a record"):
                    run_activities(export(root, "export", files), root / "golden")
                self.assertFalse((root / "golden").exists())

    def test_the_golden_path_passes_over_items_that_are_empty_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", {ACTIVITIES: activities(_activity("A1"), None, "")})
            run_activities(source, root / "golden")
            self.assertEqual(len(load(root / "golden/normalized_activities.json")), 1)


if __name__ == "__main__":
    unittest.main()
