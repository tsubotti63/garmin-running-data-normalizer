"""Values that several source names give (stage A4d-1).

UDS has two names for its date, its steps, and its distance; Sleep has four
for its score and two for each stage and for the time awake; Gear has two for
its type. When the names hold values that differ, the field disagrees: the
row leaves it empty and lists it in ``disagreeing_fields``, and the audit
record keeps the values and counts the rows in ``aliases_disagree_counts``.
When they agree, or only one name holds a value, that value is the field's.
A null or empty value is no value, and so is a value of another form, which
the audit record keeps as before. A UDS record whose names of the date give
different days is left out, as its key is not known. Across the time points
of a Snapshot store, a Gear record that uses both names of its type has them
as one field: the last time point that holds either gives the value, and a
change is listed once, under both names (merge rules v2.16).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.run_all import run_all
from tests.test_daily_unread_fields import write
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_parity import differences, runs
from tests.test_snapshot_record_updates import load, write_export

UDS_ROWS = [
    # The same steps in two forms; distances that differ.
    {"calendarDate": "2030-03-01", "totalSteps": 5, "steps": 5.0, "totalDistanceMeters": 100, "distanceMeters": 101},
    # A null first name, and an absent one: the other name gives the steps.
    {"calendarDate": "2030-03-02", "totalSteps": None, "steps": 9},
    {"calendarDate": "2030-03-03", "steps": 7},
    # A first name of another form: kept in the audit, and the other name gives the steps.
    {"calendarDate": "2030-03-04", "totalSteps": "x", "steps": 8},
    # Steps that differ.
    {"calendarDate": "2030-03-05", "totalSteps": 5, "steps": 6},
    # The same day in two forms is one day.
    {"calendarDate": "2030-03-06", "date": "2030-03-06T00:00:00", "totalSteps": 1},
    # A first name that is not a date: the other name gives the day.
    {"calendarDate": "x", "date": "2030-03-09", "totalSteps": 3},
]
DAYS_THAT_DISAGREE = {"calendarDate": "2030-03-07", "date": "2030-03-08", "totalSteps": 2}
SLEEP_ROWS = [
    {"calendarDate": "2030-03-01", "sleepScores": {"overallScore": 80}, "overallScore": 81},
    {"calendarDate": "2030-03-02", "sleepScores": {"overall": {"value": 70}}},
    {"calendarDate": "2030-03-03", "sleepScores": {"overallScore": 80}, "sleepScore": 80.0},
    # A stage whose names disagree: the stages give no duration.
    {"calendarDate": "2030-03-04", "deepSleepSeconds": 600, "deep_sleep_seconds": 660, "lightSleepSeconds": 1200},
    {"calendarDate": "2030-03-05", "deepSleepSeconds": 600, "lightSleepSeconds": None, "light_sleep_seconds": 1200},
    {"calendarDate": "2030-03-06", "awakeSleepSeconds": 60, "awake_sleep_seconds": 120},
]
GEAR_ROWS = [
    {"gearPk": 1, "displayName": "Shoe A", "gearTypeName": "running_shoes", "gearType": "running_shoes"},
    {"gearPk": 2, "displayName": "Shoe B", "gearTypeName": "Shoes", "gearType": "Bike"},
    {"gearPk": 3, "displayName": "Shoe C", "gearTypeName": "", "gearType": "Shoes"},
]


def alias_export(root: Path, name: str = "export", *, days_that_disagree: bool = False) -> Path:
    """An Export whose UDS, Sleep, and Gear rows hold values under several names."""
    source = write_export(root, name, [_activity("1001")], gear_rows=GEAR_ROWS)
    uds = [*UDS_ROWS, *([DAYS_THAT_DISAGREE] if days_that_disagree else [])]
    write(source / "DI-Connect-Aggregator" / "UDSFile_1.json", uds)
    write(source / "DI-Connect-Wellness" / "synthetic_sleepData.json", SLEEP_ROWS)
    return source


def by_key(output: Path, dataset: str, key: str) -> dict[str, dict[str, Any]]:
    return {str(row[key]): row for row in load(output / f"normalized/{dataset}.json")}


def disagreement_values(audit: dict[str, Any]) -> dict[str, list[Any]]:
    """The values of each field that disagrees, by the key of its record."""
    found: dict[str, list[Any]] = {}
    for entry in audit.get("disagreements", []):
        key = json.dumps(entry["key"], sort_keys=True)
        for item in entry["fields"]:
            found[f"{key} {item['field']}"] = sorted(
                (value["value"] for value in item["values"]), key=lambda value: json.dumps(value)
            )
    return found


def warning_codes(output: Path) -> set[tuple[str, str]]:
    return {(item["code"], item.get("family", "")) for item in load(output / "run_summary.json")["warnings"]}


class AliasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        root = Path(cls._directory.name)
        cls.output = root / "output"
        cls.result = run_all(alias_export(root), cls.output)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_uds(self) -> None:
        rows = by_key(self.output, "uds_daily", "calendar_date")
        self.assertEqual(
            {day: (row["steps"], row["distance_meters"], row["disagreeing_fields"]) for day, row in rows.items()},
            {
                "2030-03-01": (5, None, ["distance_meters"]),
                "2030-03-02": (9, None, []),
                "2030-03-03": (7, None, []),
                "2030-03-04": (8, None, []),
                "2030-03-05": (None, None, ["steps"]),
                "2030-03-06": (1, None, []),
                "2030-03-09": (3, None, []),
            },
        )
        audit = load(self.output / "audit/uds_daily.json")
        self.assertEqual(audit["aliases_disagree_counts"], {"distance_meters": 1, "steps": 1})
        self.assertEqual(
            disagreement_values(audit),
            {
                '{"calendar_date": "2030-03-01"} distance_meters': [100, 101],
                '{"calendar_date": "2030-03-05"} steps': [5, 6],
            },
        )
        # The value of another form is kept, though the field has a value.
        self.assertEqual(audit["invalid_value_counts"], {"steps": 1})
        self.assertEqual(audit["excluded_record_count"], 0)

    def test_sleep(self) -> None:
        rows = by_key(self.output, "sleep_daily", "sleep_day")
        self.assertEqual(
            {
                day: (
                    row["sleep_score"],
                    row["sleep_stage_deep_minutes"],
                    row["sleep_stage_light_minutes"],
                    row["sleep_awake_minutes"],
                    row["sleep_duration_minutes_ex_awake"],
                    row["disagreeing_fields"],
                )
                for day, row in rows.items()
            },
            {
                "2030-03-01": (None, None, None, None, None, ["sleep_score"]),
                "2030-03-02": (70, None, None, None, None, []),
                "2030-03-03": (80, None, None, None, None, []),
                # The duration is empty, but it is not a field that disagrees.
                "2030-03-04": (None, None, 20.0, None, None, ["sleep_stage_deep_minutes"]),
                "2030-03-05": (None, 10.0, 20.0, None, 30.0, []),
                "2030-03-06": (None, None, None, None, None, ["sleep_awake_minutes"]),
            },
        )
        audit = load(self.output / "audit/sleep_daily.json")
        self.assertEqual(
            audit["aliases_disagree_counts"],
            {"sleep_awake_minutes": 1, "sleep_score": 1, "sleep_stage_deep_minutes": 1},
        )
        self.assertEqual(
            audit["sleep_duration_source_counts"],
            {"null_fallback": 4, "stage_aliases_disagree": 1, "stage_derived": 1},
        )
        self.assertEqual(
            disagreement_values(audit),
            {
                '{"sleep_day": "2030-03-01"} sleep_score': [80, 81],
                '{"sleep_day": "2030-03-04"} sleep_stage_deep_minutes': [10.0, 11.0],
                '{"sleep_day": "2030-03-06"} sleep_awake_minutes': [1.0, 2.0],
            },
        )

    def test_gear(self) -> None:
        rows = by_key(self.output, "gear", "display_name")
        self.assertEqual(
            {name: (row["gear_type"], row["disagreeing_fields"]) for name, row in rows.items()},
            {
                "Shoe A": ("running_shoes", []),
                "Shoe B": (None, ["gear_type"]),
                "Shoe C": ("Shoes", []),
            },
        )
        audit = load(self.output / "audit/gear.json")
        self.assertEqual(audit["aliases_disagree_counts"], {"gear_type": 1})
        self.assertEqual(audit["disagreement_key_count"], 1)
        [entry] = audit["disagreements"]
        self.assertEqual(
            sorted(value["value"] for value in entry["fields"][0]["values"]), ["Bike", "Shoes"]
        )

    def test_warnings_and_exit_code(self) -> None:
        codes = warning_codes(self.output)
        for family in ("uds", "sleep", "gear"):
            with self.subTest(family=family):
                self.assertIn(("VALUES_DISAGREE", family), codes)
        self.assertNotIn("DATA_ROW_LEFT_OUT", {code for code, _family in codes})
        self.assertEqual(self.result["exit_code"], 0)


class DaysThatDisagreeTest(unittest.TestCase):
    def test_a_record_whose_names_give_different_days_is_left_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            result = run_all(alias_export(root, days_that_disagree=True), output)
            rows = by_key(output, "uds_daily", "calendar_date")
            self.assertNotIn("2030-03-07", rows)
            self.assertNotIn("2030-03-08", rows)
            audit = load(output / "audit/uds_daily.json")
            self.assertEqual(audit["excluded_reason_counts"], {"calendar_date_aliases_disagree": 1})
            self.assertIn(("DATA_ROW_LEFT_OUT", "uds"), warning_codes(output))
            self.assertEqual(result["exit_code"], 3)


class SnapshotTest(unittest.TestCase):
    def test_a_snapshot_run_reads_the_names_as_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = alias_export(root, days_that_disagree=True)
            # Copies within one Snapshot count as in a one-shot run.
            write(source / "DI-Connect-Aggregator" / "UDSFile_2.json", [UDS_ROWS[4]])
            one_shot, snapshot = runs(root / "runs", source)
            self.assertEqual(differences(one_shot, snapshot), [])
            self.assertEqual(
                load(snapshot / "audit/uds_daily.json")["aliases_disagree_counts"],
                {"distance_meters": 1, "steps": 2},
            )

    def test_two_snapshots_whose_records_use_different_names(self) -> None:
        # The steps of one day under one name in the first Snapshot and under
        # the other in the second: the same value is one value, and different
        # values disagree, as between any two Snapshots.
        for later, expected in ((5, (5, [])), (6, (None, ["steps"]))):
            with self.subTest(later=later), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                first = write_export(root, "first", [_activity("1001")])
                write(first / "DI-Connect-Aggregator" / "UDSFile_1.json", [{"calendarDate": "2030-03-01", "totalSteps": 5}])
                second = write_export(root, "second", [_activity("1001")])
                write(second / "DI-Connect-Aggregator" / "UDSFile_1.json", [{"calendarDate": "2030-03-01", "steps": later}])
                _one_shot, snapshot = runs(root / "runs", first, second)
                [row] = load(snapshot / "normalized/uds_daily.json")
                self.assertEqual((row["steps"], row["disagreeing_fields"]), expected)
                self.assertNotIn("aliases_disagree_counts", load(snapshot / "audit/uds_daily.json"))


def gear(**fields: object) -> list[dict[str, object]]:
    return [{"gearPk": 1, "displayName": "Shoe", **fields}]


class GearAcrossSnapshotsTest(unittest.TestCase):
    """A Gear record whose type is written under one name in one Snapshot and
    under the other in a later one: the names are one field across time
    points, so the later value is the record's, and the change is an update,
    as for any field (merge rules v2.16)."""

    def run_snapshots(self, *gear_lists: list[dict[str, object]]) -> tuple[dict[str, Any], dict[str, Any], set[str]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [
                write_export(root, f"export-{index}", [_activity("1001")], gear_rows=rows)
                for index, rows in enumerate(gear_lists, start=1)
            ]
            _one_shot, snapshot = runs(root / "runs", *sources)
            [row] = load(snapshot / "normalized/gear.json")
            codes = {code for code, family in warning_codes(snapshot) if family == "gear"}
            return row, load(snapshot / "audit/gear.json"), codes

    def updates(self, audit: dict[str, Any]) -> list[dict[str, Any]]:
        return [field for entry in audit.get("updates", []) for field in entry["fields"]]

    def test_the_names_switch(self) -> None:
        row, audit, codes = self.run_snapshots(gear(gearTypeName="Shoes"), gear(gearType="Bike"))
        self.assertEqual((row["gear_type"], row["disagreeing_fields"]), ("Bike", []))
        self.assertNotIn("aliases_disagree_counts", audit)
        self.assertEqual(
            self.updates(audit),
            [{"field": "gearTypeName|gearType",
              "values": [{"snapshots": [1], "value": "Shoes"}, {"snapshots": [2], "value": "Bike"}]}],
        )
        self.assertEqual(codes, {"VALUES_UPDATED"})

    def test_the_names_of_the_last_time_point_that_holds_either_go_on(self) -> None:
        # The third Snapshot holds no type: the second gives it, and the first
        # name, which only the first Snapshot holds, is not carried.
        row, audit, _codes = self.run_snapshots(gear(gearTypeName="Shoes"), gear(gearType="Bike"), gear())
        self.assertEqual((row["gear_type"], row["disagreeing_fields"]), ("Bike", []))
        self.assertEqual([item["field"] for item in self.updates(audit)], ["gearTypeName|gearType"])

    def test_the_same_value_under_the_other_name_is_no_change(self) -> None:
        row, audit, codes = self.run_snapshots(gear(gearTypeName="Shoes"), gear(gearType="Shoes"))
        self.assertEqual((row["gear_type"], row["disagreeing_fields"]), ("Shoes", []))
        self.assertEqual(self.updates(audit), [])
        self.assertEqual(codes, set())

    def test_a_record_that_uses_one_name_is_merged_as_before(self) -> None:
        row, audit, _codes = self.run_snapshots(gear(gearTypeName="Shoes"), gear(gearTypeName="Bike"))
        self.assertEqual(row["gear_type"], "Bike")
        self.assertEqual([item["field"] for item in self.updates(audit)], ["gearTypeName"])

    def test_names_that_disagree_within_the_last_row(self) -> None:
        row, audit, codes = self.run_snapshots(gear(gearTypeName="Shoes"), gear(gearTypeName="Shoes", gearType="Bike"))
        self.assertEqual((row["gear_type"], row["disagreeing_fields"]), (None, ["gear_type"]))
        self.assertEqual(audit["aliases_disagree_counts"], {"gear_type": 1})
        self.assertEqual(codes, {"VALUES_DISAGREE", "VALUES_UPDATED"})

    def test_the_names_are_those_of_the_merge_rules(self) -> None:
        from garmin_running_data_normalizer.normalizers.aliases import ENTITY_FIELD_NAMES
        from garmin_running_data_normalizer.snapshot.policies import MERGE_RULES

        self.assertEqual(
            {dataset: [list(names) for names in groups] for dataset, groups in ENTITY_FIELD_NAMES.items()},
            {"gear": MERGE_RULES["names_of_one_field"]["gear"]},
        )


if __name__ == "__main__":
    unittest.main()
