"""Repeated records and disagreements within one Export or one time point (stage A3b)."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from tests.test_hrv_normalizer import fit_timestamp, synthetic_hrv_fit
from tests.test_snapshot_lifecycle import _activity, _write_snapshot
from tests.test_snapshot_record_updates import ACCOUNT, gear, load, personal_record, write_export

RECORD_DATASETS = ("activities", "gear", "activity_gear", "personal_records")
# The audit keys of stage A2b-2, which an Export without repeated records keeps.
A2B2_AUDIT_KEYS = {
    "format",
    "dataset",
    "observation_scope",
    "record_count",
    "updated_record_count",
    "updates",
    "not_in_latest_snapshot_count",
    "not_in_latest_snapshot",
}


def add_json(source: Path, relative: str, value: object) -> None:
    path = source / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def add_activities(source: Path, name: str, rows: list[dict[str, object]]) -> None:
    add_json(source, f"DI-Connect-Fitness/{name}", [{"summarizedActivitiesExport": rows}])


def one_shot(root: Path, source: Path, name: str = "one-shot") -> Path:
    output = root / name
    run_all(source, output)
    return output


def snapshot_run(
    root: Path,
    sources: list[tuple[Path, str, str]],
    name: str = "snapshot",
) -> Path:
    """Register (source, label, observed time) in the given order and run."""
    store = root / f"{name}-store"
    initialize_store(store, ACCOUNT)
    for source, label, observed in sources:
        register_snapshot(
            store,
            source,
            snapshot_label=label,
            export_requested_at=observed,
            export_downloaded_at=observed,
            export_observed_at=observed,
            confirm_complete=True,
        )
    output = root / name
    run_snapshot_all(store, output)
    return output


def day(number: int) -> str:
    return f"2030-01-{number:02d}T02:00:00+00:00"


def rows(output: Path, dataset: str) -> list[dict[str, object]]:
    return load(output / f"normalized/{dataset}.json")


def table(output: Path, dataset: str) -> list[dict[str, object]]:
    """The normalized rows without their provenance fields."""
    return [
        {field: value for field, value in row.items() if not field.startswith("source_")}
        for row in rows(output, dataset)
    ]


def audit(output: Path, dataset: str) -> dict[str, object]:
    return load(output / f"audit/{dataset}.json")


def merge_counts(output: Path, dataset: str) -> dict[str, object]:
    """The stage A3b part of a record audit, without Snapshot numbers."""

    def strip(value: object) -> object:
        if isinstance(value, dict):
            return {key: strip(item) for key, item in value.items() if key != "snapshots"}
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value

    record = audit(output, dataset)
    return strip(
        {
            key: record[key]
            for key in (
                "same_value_duplicate_count",
                "absent_value_counts",
                "disagreement_key_count",
                "disagreements",
            )
            if key in record
        }
    )


def warnings(output: Path) -> dict[tuple[str, str], int]:
    return {
        (item["code"], item.get("family", "")): item.get("count", 1)
        for item in load(output / "run_summary.json")["warnings"]
        if not item["code"].startswith("OPTIONAL_FAMILY")
    }


class OneShotRepeatedRecordsTest(unittest.TestCase):
    def test_records_with_the_same_values_become_one_row_and_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activity = _activity("A1")
            record = personal_record(1, "A1", 100.0)
            source = write_export(
                root,
                "export",
                [activity, dict(activity)],
                gear_rows=[gear(1, "Shoe"), gear(1, "Shoe")],
                links={"1": ["A1", "A1"]},
                records=[record, dict(record)],
            )
            add_activities(source, "second_summarizedActivities.json", [dict(activity)])
            add_json(
                source,
                "DI-Connect-Fitness/second_personalRecord.json",
                [{"personalRecords": [dict(record)]}, {"personalRecords": [dict(record)]}],
            )
            output = one_shot(root, source)

            for dataset, copies in (
                ("activities", 2),
                ("gear", 1),
                ("activity_gear", 1),
                ("personal_records", 3),
            ):
                with self.subTest(dataset=dataset):
                    self.assertEqual(len(rows(output, dataset)), 1)
                    self.assertEqual(rows(output, dataset)[0]["disagreeing_fields"], [])
                    self.assertEqual(merge_counts(output, dataset), {"same_value_duplicate_count": copies})
            # Copies are counted without a warning.
            self.assertEqual(warnings(output), {})
            qa = {item["dataset"]: item for item in load(output / "qa/dataset_summary.json")["datasets"]}
            for dataset in RECORD_DATASETS:
                self.assertEqual(qa[dataset]["duplicate_extra_rows"], 0)
            self.assertEqual(doctor_run_output(output)["product_exit_code"], 0)

    def test_values_that_disagree_are_left_empty_and_every_value_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(
                root,
                "export",
                [_activity("A1", name="Morning run")],
                gear_rows=[gear(1, "Shoe")],
                records=[personal_record(1, "A1", 100.0)],
            )
            add_activities(
                source,
                "second_summarizedActivities.json",
                [_activity("A1", name="Morning run 10k", distance=600000)],
            )
            add_json(
                source,
                "DI-Connect-Fitness/second_gear.json",
                [{"gearDTOS": [gear(1, "Renamed shoe")]}],
            )
            add_json(
                source,
                "DI-Connect-Fitness/second_personalRecord.json",
                [{"personalRecords": [personal_record(1, "A1", 99.0)]}],
            )
            output = one_shot(root, source)

            activity = rows(output, "activities")[0]
            self.assertEqual(
                activity["disagreeing_fields"],
                ["name", "distance_raw_centimeters", "distance_m"],
            )
            for field in ("name", "distance_raw_centimeters", "distance_m"):
                self.assertIsNone(activity[field])
            # Fields that agree keep their value.
            self.assertEqual(activity["duration_sec"], 1800.0)
            self.assertEqual(rows(output, "gear")[0]["display_name"], None)
            self.assertEqual(rows(output, "personal_records")[0]["disagreeing_fields"], ["value"])
            entry = audit(output, "activities")["disagreements"][0]
            self.assertEqual(entry["key"], {"garmin_activity_key": "garmin_activity:A1"})
            self.assertEqual(entry["observation_count"], 2)
            self.assertEqual(
                entry["fields"][0],
                {
                    "field": "name",
                    # Values other than numbers in the order of their JSON text.
                    "values": [
                        {"value": "Morning run 10k", "observation_count": 1},
                        {"value": "Morning run", "observation_count": 1},
                    ],
                },
            )
            self.assertEqual(
                warnings(output),
                {
                    ("VALUES_DISAGREE", "activities"): 1,
                    ("VALUES_DISAGREE", "gear"): 1,
                    ("VALUES_DISAGREE", "personal_records"): 1,
                },
            )
            summary = load(output / "run_summary.json")
            self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
            self.assertEqual(summary["family_results"]["activities"]["disagreement_key_count"], 1)
            quality = load(output / "diagnostics/run_quality.json")["conflict_summary"]
            self.assertEqual(
                quality["by_dataset"],
                {"activities": 1, "gear": 1, "personal_records": 1},
            )
            self.assertEqual(doctor_run_output(output)["product_exit_code"], 0)

    def test_identifiers_written_in_two_ways_name_one_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity(" 123", name="Same")])
            add_activities(
                source,
                "second_summarizedActivities.json",
                [_activity(123, name="Same"), _activity("0123", name="Same")],
            )
            output = one_shot(root, source)
            (activity,) = rows(output, "activities")
            self.assertEqual(activity["disagreeing_fields"], [])
            self.assertEqual(merge_counts(output, "activities"), {"same_value_duplicate_count": 2})

    def test_null_and_missing_are_no_value_and_forms_alike_are_one_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(
                root,
                "export",
                [_activity("A1", avgHr=150, description="memo")],
            )
            add_activities(
                source,
                "second_summarizedActivities.json",
                [_activity("A1", avgHr=150.0), _activity("A1", avgHr=None, description=None)],
            )
            output = one_shot(root, source)
            (activity,) = rows(output, "activities")
            self.assertEqual(activity["disagreeing_fields"], [])
            self.assertEqual(activity["avg_hr"], 150.0)
            self.assertEqual(activity["memo_text_raw"], "memo")
            self.assertTrue(activity["memo_present"])
            counts = merge_counts(output, "activities")
            # memo_present is a presence flag, which is never empty.
            self.assertEqual(counts["absent_value_counts"], {"avg_hr": 1, "memo_text_raw": 2})
            self.assertNotIn("disagreements", counts)
            self.assertEqual(warnings(output), {})

    def test_provenance_comes_from_the_first_file_in_path_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("A1")])
            add_activities(source, "a_first_summarizedActivities.json", [_activity("A1")])
            output = one_shot(root, source)
            self.assertEqual(
                rows(output, "activities")[0]["source_path"],
                "DI-Connect-Fitness/a_first_summarizedActivities.json",
            )

    def test_an_export_without_repeated_records_keeps_its_audits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(
                root,
                "export",
                [_activity("A1"), _activity("A2")],
                gear_rows=[gear(1, "Shoe")],
                links={"1": ["A1"]},
                records=[personal_record(1, "A1", 100.0)],
            )
            output = one_shot(root, source)
            for dataset in RECORD_DATASETS:
                with self.subTest(dataset=dataset):
                    keys = set(audit(output, dataset))
                    expected = A2B2_AUDIT_KEYS | (
                        {"removed_link_count", "removed_links"} if dataset == "activity_gear" else set()
                    )
                    self.assertEqual(keys, expected)


# The memos of two observations of one Activity, and what the merged row holds:
# an empty value is no value, as a missing one is (stage A3b).
MISSING = object()
MEMO_CASES = (
    ("", "x", "x", False),
    (None, "x", "x", False),
    (MISSING, "x", "x", False),
    ("x", "y", None, True),
    ("", None, "empty", False),
)


def memo_activity(memo: object) -> dict[str, object]:
    row = _activity("A1")
    if memo is not MISSING:
        row["description"] = memo
    return row


class EmptyValuesTest(unittest.TestCase):
    """An empty memo next to a memo is no value, in each kind of run."""

    def check(self, output: Path, expected: object, disagrees: bool) -> None:
        (activity,) = rows(output, "activities")
        if expected == "empty":
            self.assertIn(activity["memo_text_raw"], (None, ""))
        else:
            self.assertEqual(activity["memo_text_raw"], expected)
        # The flag is never empty: it says whether any observation has a memo.
        self.assertIs(activity["memo_present"], expected not in ("empty",))
        self.assertEqual(activity["disagreeing_fields"], ["memo_text_raw"] if disagrees else [])
        self.assertEqual(
            warnings(output).get(("VALUES_DISAGREE", "activities"), 0),
            1 if disagrees else 0,
        )

    def test_one_shot_runs(self) -> None:
        for first, second, expected, disagrees in MEMO_CASES:
            with self.subTest(first=first, second=second), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = write_export(root, "export", [memo_activity(first)])
                add_activities(source, "second_summarizedActivities.json", [memo_activity(second)])
                self.check(one_shot(root, source), expected, disagrees)

    def test_one_snapshot(self) -> None:
        for first, second, expected, disagrees in MEMO_CASES:
            with self.subTest(first=first, second=second), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = write_export(root, "export", [memo_activity(first)])
                add_activities(source, "second_summarizedActivities.json", [memo_activity(second)])
                self.check(snapshot_run(root, [(source, "S1", day(1))]), expected, disagrees)

    def test_a_later_snapshot_without_the_memo(self) -> None:
        for first, second, expected, disagrees in MEMO_CASES:
            with self.subTest(first=first, second=second), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                earlier = write_export(root, "earlier", [memo_activity(first)])
                add_activities(earlier, "second_summarizedActivities.json", [memo_activity(second)])
                later = write_export(root, "later", [memo_activity(MISSING)])
                output = snapshot_run(root, [(earlier, "S1", day(1)), (later, "S2", day(2))])
                self.check(output, expected, disagrees)

    def test_no_field_that_must_have_a_value_stops_a_disagreement(self) -> None:
        # Every value field of each dataset differs between two observations,
        # the activity of a Personal Record too, which leaves its link
        # unresolved (stage A3d-1b).
        first_activity = _activity("A1", description="one", startTimeLocal="2030-01-01T09:00:00",
                                   elapsedDuration=1, movingDuration=1, avgHr=1, maxHr=1, avgPower=1,
                                   maxPower=1, avgRunCadence=1, trainingEffectLabel="one",
                                   activityTrainingLoad=1, lapCount=1)
        second_activity = _activity("A1", name="other", activityType="cycling", sportType="cycling",
                                    distance=1, duration=1, startTimeGmt=1893459600000,
                                    description="two", startTimeLocal="2030-01-01T10:00:00",
                                    elapsedDuration=2, movingDuration=2, avgHr=2, maxHr=2, avgPower=2,
                                    maxPower=2, avgRunCadence=2, trainingEffectLabel="two",
                                    activityTrainingLoad=2, lapCount=2)
        first_gear = gear(1, "Shoe")
        second_gear = {
            "gearPk": 1,
            "uuid": "other-uuid",
            "displayName": "Other",
            "customMakeModel": "Other model",
            "gearTypeName": "Bike",
            "dateBegin": "2031-01-01T00:00:00.0",
            "dateEnd": "2032-01-01T00:00:00.0",
            "maximumMeters": 1,
        }
        first_record = {**personal_record(1, "A1", 100.0), "prStartTimeGMT": "2030-01-01T08:00:00.0"}
        second_record = {
            **first_record,
            "activityId": "A2",
            "personalRecordType": "other_best",
            "value": 99.0,
            "prStartTimeGMT": "2030-01-01T09:00:00.0",
            "createdDate": "2030-01-02",
            "current": False,
            "confirmed": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(
                root,
                "export",
                [first_activity],
                gear_rows=[first_gear],
                links={"1": ["A1"]},
                records=[first_record],
            )
            add_activities(source, "second_summarizedActivities.json", [second_activity])
            add_json(source, "DI-Connect-Fitness/second_gear.json", [{"gearDTOS": [second_gear]}])
            add_json(
                source,
                "DI-Connect-Fitness/second_personalRecord.json",
                [{"personalRecords": [second_record]}],
            )
            for output in (one_shot(root, source), snapshot_run(root, [(source, "S1", day(1))])):
                with self.subTest(output=output.name):
                    activity = rows(output, "activities")[0]
                    self.assertTrue(activity["memo_present"])
                    self.assertIn("name", activity["disagreeing_fields"])
                    self.assertIn("display_name", rows(output, "gear")[0]["disagreeing_fields"])
                    record = rows(output, "personal_records")[0]
                    self.assertLessEqual({"value", "activity_id"}, set(record["disagreeing_fields"]))
                    self.assertEqual(
                        record["activity_relationship_reason"], "activity_link_values_disagree"
                    )
                    self.assertEqual(doctor_run_output(output)["product_exit_code"], 0)


class SnapshotRepeatedRecordsTest(unittest.TestCase):
    def test_one_snapshot_gives_the_tables_and_counts_of_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activity = _activity("A2")
            record = personal_record(1, "A1", 100.0)
            source = write_export(
                root,
                "export",
                [_activity("A1", name="first", avgHr=150), activity, dict(activity)],
                gear_rows=[gear(1, "Shoe"), gear(1, "Shoe")],
                links={"1": ["A1", "A1"]},
                records=[record],
            )
            add_activities(
                source,
                "second_summarizedActivities.json",
                [_activity("A1", name="second"), dict(activity)],
            )
            add_json(
                source,
                "DI-Connect-Fitness/second_personalRecord.json",
                [{"personalRecords": [personal_record(1, "A1", 99.0)]}],
            )
            first = one_shot(root, source)
            second = snapshot_run(root, [(source, "S1", day(1))])
            for dataset in RECORD_DATASETS:
                with self.subTest(dataset=dataset):
                    self.assertEqual(table(first, dataset), table(second, dataset))
                    self.assertEqual(merge_counts(first, dataset), merge_counts(second, dataset))
            self.assertEqual(warnings(first), warnings(second))
            values = audit(second, "activities")["disagreements"][0]["fields"][0]["values"]
            self.assertEqual([item["snapshots"] for item in values], [[1], [1]])
            self.assertEqual(doctor_run_output(second)["product_exit_code"], 0)

    def test_snapshots_observed_at_the_same_time_are_one_time_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            older = write_export(root, "older", [_activity("A1", name="before"), _activity("A3")])
            left = write_export(root, "left", [_activity("A1", name="left"), _activity("A2")])
            right = write_export(root, "right", [_activity("A1", name="right")])
            results = []
            for order, name in ((("left", "right"), "one"), (("right", "left"), "two")):
                sources = {"left": left, "right": right}
                output = snapshot_run(
                    root,
                    [(older, "OLDER", day(1))]
                    + [(sources[label], label.upper(), day(2)) for label in order],
                    name=name,
                )
                results.append(output)
                with self.subTest(order=order):
                    activities = {row["activity_id"]: row for row in rows(output, "activities")}
                    self.assertIsNone(activities["A1"]["name"])
                    self.assertEqual(activities["A1"]["disagreeing_fields"], ["name"])
                    record = audit(output, "activities")
                    # A2 is in one Snapshot of the latest time point, so it is in
                    # the latest Snapshot; A3 is not.
                    self.assertEqual(
                        [item["key"] for item in record["not_in_latest_snapshot"]],
                        [{"garmin_activity_key": "garmin_activity:A3"}],
                    )
                    self.assertEqual(
                        warnings(output),
                        {
                            ("VALUES_DISAGREE", "activities"): 1,
                            ("VALUES_UPDATED", "activities"): 1,
                            ("RECORDS_NOT_IN_LATEST_SNAPSHOT", "activities"): 1,
                        },
                    )
                    names = audit(output, "activities")["disagreements"][0]["fields"][0]["values"]
                    self.assertEqual(sorted(item["value"] for item in names), ["left", "right"])
            # The order of the Snapshots of one time point changes nothing but
            # their numbers.
            self.assertEqual(table(results[0], "activities"), table(results[1], "activities"))

    def test_removed_links_are_judged_by_time_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_export(
                root, "first", [_activity("A1")], gear_rows=[gear(1, "Shoe")], links={"1": ["A1"]}
            )
            # At the latest time point, one Snapshot has the Gear links object
            # without the link, and the other has the Activity and the Gear.
            links_only = write_export(root, "links-only", [_activity("A2")], links={})
            endpoints = write_export(root, "endpoints", [_activity("A1")], gear_rows=[gear(1, "Shoe")])
            kept_link = write_export(root, "kept-link", [_activity("A1")], links={"1": ["A1"]})
            removed = snapshot_run(
                root,
                [(first, "S1", day(1)), (links_only, "S2", day(2)), (endpoints, "S3", day(2))],
                name="removed",
            )
            self.assertEqual(rows(removed, "activity_gear"), [])
            self.assertEqual(audit(removed, "activity_gear")["removed_link_count"], 1)
            kept = snapshot_run(
                root,
                [(first, "S1", day(1)), (links_only, "S2", day(2)), (kept_link, "S3", day(2))],
                name="kept",
            )
            self.assertEqual(len(rows(kept, "activity_gear")), 1)
            self.assertEqual(audit(kept, "activity_gear")["removed_link_count"], 0)

    def test_fields_the_last_time_point_lacks_keep_their_earlier_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            earlier = write_export(root, "earlier", [_activity("A1", description="memo")])
            later = write_export(root, "later", [_activity("A1", name="one")])
            add_activities(later, "second_summarizedActivities.json", [_activity("A1", name="two")])
            output = snapshot_run(root, [(earlier, "S1", day(1)), (later, "S2", day(2))])
            (activity,) = rows(output, "activities")
            self.assertEqual(activity["memo_text_raw"], "memo")
            self.assertTrue(activity["memo_present"])
            self.assertEqual(activity["disagreeing_fields"], ["name"])

    def test_changes_are_counted_between_time_points_only(self) -> None:
        cases = (
            # (names at time point 1, names at time point 2, the updates'
            # values with their time points, VALUES_UPDATED, VALUES_DISAGREE).
            # The Snapshots of one time point are numbered in an order that
            # means nothing, so only their time point is checked.
            (("A", "B"), ("B",), [("A", 1), ("B", 1), ("B", 2)], 1, 0),
            (("A", "B"), ("A",), [("A", 1), ("B", 1), ("A", 2)], 1, 0),
            (("A",), ("A", "B"), [("A", 1), ("A", 2), ("B", 2)], 1, 1),
            (("A", "B"), ("A", "B"), None, 0, 1),
        )
        for first, second, values, updated, disagree in cases:
            with self.subTest(first=first, second=second), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                sources = []
                number = 0
                for observed, names in ((day(1), first), (day(2), second)):
                    for name in names:
                        number += 1
                        # Each Export has a record of its own, so that no two
                        # have the same content (stage A3a counts those once).
                        source = write_export(
                            root,
                            f"s{number}",
                            [_activity("A1", name=name), _activity(f"F{number}")],
                        )
                        sources.append((source, f"S{number}", observed))
                output = snapshot_run(root, sources)
                found = warnings(output)
                self.assertEqual(found.get(("VALUES_UPDATED", "activities"), 0), updated)
                self.assertEqual(found.get(("VALUES_DISAGREE", "activities"), 0), disagree)
                updates = audit(output, "activities")["updates"]
                if values is None:
                    self.assertEqual(updates, [])
                else:
                    (field,) = updates[0]["fields"]
                    self.assertEqual(field["field"], "name")
                    self.assertEqual(
                        [
                            (item["value"], 1 if max(item["snapshots"]) <= len(first) else 2)
                            for item in field["values"]
                        ],
                        values,
                    )
                    self.assertTrue(all(len(item["snapshots"]) == 1 for item in field["values"]))

    def test_an_earlier_disagreement_stays_when_the_last_time_point_lacks_the_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            earlier = write_export(root, "earlier", [_activity("A1", description="first memo")])
            add_activities(
                earlier,
                "second_summarizedActivities.json",
                [_activity("A1", description="second memo")],
            )
            later = write_export(root, "later", [_activity("A1")])
            output = snapshot_run(root, [(earlier, "S1", day(1)), (later, "S2", day(2))])
            (activity,) = rows(output, "activities")
            self.assertIsNone(activity["memo_text_raw"])
            self.assertEqual(activity["disagreeing_fields"], ["memo_text_raw"])
            # Both memos are present, so the flag stays.
            self.assertTrue(activity["memo_present"])
            entry = audit(output, "activities")["disagreements"][0]
            self.assertEqual(
                entry["fields"],
                [
                    {
                        "field": "memo_text_raw",
                        "values": [
                            {"value": "first memo", "observation_count": 1, "snapshots": [1]},
                            {"value": "second memo", "observation_count": 1, "snapshots": [1]},
                        ],
                    }
                ],
            )
            self.assertEqual(warnings(output).get(("VALUES_DISAGREE", "activities")), 1)

    def test_the_same_record_in_two_snapshots_is_not_a_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_export(root, "first", [_activity("A1"), _activity("A2", name="one")])
            second = write_export(root, "second", [_activity("A1"), _activity("A2", name="two")])
            for name, times in (("apart", (day(1), day(2))), ("together", (day(1), day(1)))):
                with self.subTest(times=name):
                    output = snapshot_run(
                        root,
                        [(first, "S1", times[0]), (second, "S2", times[1])],
                        name=name,
                    )
                    self.assertNotIn("same_value_duplicate_count", audit(output, "activities"))

    def test_copies_within_an_earlier_snapshot_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            earlier = write_export(root, "earlier", [_activity("A1"), _activity("A1"), _activity("A2")])
            later = write_export(root, "later", [_activity("A1"), _activity("A3")])
            output = snapshot_run(root, [(earlier, "S1", day(1)), (later, "S2", day(2))])
            self.assertEqual(audit(output, "activities")["same_value_duplicate_count"], 1)
            self.assertEqual(len(rows(output, "activities")), 3)

    def test_copies_written_in_other_forms_count_as_in_a_one_shot_run(self) -> None:
        # Copies whose values differ only in form, or in an empty value next
        # to a missing one, are copies in the build as in Run-All.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = _activity("A1", avgHr=100, description="")
            second = _activity("A1", avgHr=100.0)
            earlier = write_export(root, "earlier", [first, second, _activity("A2")])
            later = write_export(root, "later", [_activity("A1"), _activity("A3")])
            alone = one_shot(root, earlier)
            output = snapshot_run(root, [(earlier, "S1", day(1)), (later, "S2", day(2))])
            self.assertEqual(audit(alone, "activities")["same_value_duplicate_count"], 1)
            self.assertEqual(audit(output, "activities")["same_value_duplicate_count"], 1)

    def test_counts_of_repeated_files_and_records_match_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export"
            _write_snapshot(
                source,
                [_activity("A1")],
                fit_payload=synthetic_hrv_fit((73 * 128, fit_timestamp("2030-02-01T12:00:00Z"))),
            )
            uploaded = source / "DI-Connect-Uploaded-Files"
            (uploaded / "nested").mkdir()
            shutil.copyfile(uploaded / "synthetic.fit", uploaded / "nested/synthetic_copy.fit")
            uds = {"calendarDate": "2030-02-01", "totalSteps": 100, "bmrKilocalories": 1500}
            add_json(source, "DI-Connect-Aggregator/UDSFile_1.json", [uds, {"calendarDate": "2030-02-02", "totalSteps": 5}])
            add_json(source, "DI-Connect-Aggregator/UDSFile_2.json", [dict(uds)])
            readiness = {"calendarDate": "2030-02-01", "timestamp": "2030-02-01T07:00:00.0", "score": 80}
            add_json(
                source,
                "DI-Connect-Metrics/TrainingReadinessDTO_1.json",
                [readiness, {**readiness, "calendarDate": "2030-02-02", "timestamp": "2030-02-02T07:00:00.0"}],
            )
            add_json(source, "DI-Connect-Metrics/TrainingReadinessDTO_2.json", [dict(readiness)])
            hill = {"calendarDate": "2030-02-01", "overallScore": 80}
            add_json(
                source,
                "DI-Connect-Metrics/HillScore_1.json",
                [hill, {"calendarDate": "2030-02-02", "overallScore": 81}],
            )
            add_json(source, "DI-Connect-Metrics/HillScore_2.json", [dict(hill)])
            first = one_shot(root, source)
            second = snapshot_run(root, [(source, "S1", day(1))])
            fields = ("calendar_date", "hrv_value", "record_count_for_date", "source_file_count_for_date", "dedupe_status")
            for output in (first, second):
                with self.subTest(output=output.name):
                    (hrv,) = rows(output, "hrv_daily")
                    self.assertEqual(
                        {field: hrv[field] for field in fields},
                        {
                            "calendar_date": "2030-02-01",
                            "hrv_value": 73.0,
                            "record_count_for_date": 2,
                            "source_file_count_for_date": 1,
                            "dedupe_status": "same_date_same_value_deduped",
                        },
                    )
                    hrv_audit = audit(output, "hrv_daily")
                    self.assertEqual(
                        (hrv_audit["detected_asset_count"], hrv_audit["source_record_count"], hrv_audit["same_value_duplicate_count"]),
                        (2, 2, 1),
                    )
                    uds_audit = audit(output, "uds_daily")
                    self.assertEqual(
                        (uds_audit["source_record_count"], uds_audit["same_value_duplicate_count"]),
                        (3, 1),
                    )
                    readiness_audit = audit(output, "training_readiness_daily")
                    self.assertEqual(
                        (
                            readiness_audit["source_record_count"],
                            readiness_audit["same_value_duplicate_count"],
                            sum(readiness_audit["observation_timestamp_semantics_counts"].values()),
                        ),
                        (3, 1, 3),
                    )
                    hill_audit = audit(output, "hill_score_daily")
                    self.assertEqual(
                        (hill_audit["source_record_count"], hill_audit["same_value_duplicate_count"]),
                        (3, 1),
                    )

    def test_the_support_bundle_and_the_safe_pack_carry_counts_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("A1", name="PRIVATE-NAME-ONE")])
            add_activities(
                source,
                "second_summarizedActivities.json",
                [_activity("A1", name="PRIVATE-NAME-TWO")],
            )
            output = root / "with-pack"
            run_all(source, output, external_safe_pack=True)
            self.assertIn("PRIVATE-NAME-ONE", (output / "audit/activities.json").read_text(encoding="utf-8"))
            bundle = root / "bundle.zip"
            build_support_bundle(output, bundle)
            for archive in (bundle, output / "analysis/external_safe_handoff.zip"):
                with self.subTest(archive=archive.name), zipfile.ZipFile(archive) as opened:
                    for name in opened.namelist():
                        self.assertNotIn(b"PRIVATE-NAME", opened.read(name))


if __name__ == "__main__":
    unittest.main()
