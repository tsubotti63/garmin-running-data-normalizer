"""Rows that lack a required value are left out and announced, or only counted
when they hold no value, alike in one-shot and Snapshot runs (stage A3d-1)."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.normalizers.daily_metrics import value_source_names
from garmin_running_data_normalizer.normalizers.performance_metrics import (
    ENDURANCE_FIELDS_WITHOUT_VALUES,
    ENDURANCE_VALUE_SOURCES,
    HILL_FIELDS_WITHOUT_VALUES,
    HILL_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.race_prediction import (
    RACE_PREDICTION_FIELDS_WITHOUT_VALUES,
    RACE_PREDICTION_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.sleep import (
    SLEEP_FIELDS_WITHOUT_VALUES,
    SLEEP_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.training_history import (
    TRAINING_HISTORY_FIELDS_WITHOUT_VALUES,
    TRAINING_HISTORY_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.training_load import (
    ACUTE_TRAINING_LOAD_FIELDS_WITHOUT_VALUES,
    ACUTE_TRAINING_LOAD_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.training_readiness import (
    TRAINING_READINESS_FIELDS_WITHOUT_VALUES,
    TRAINING_READINESS_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.uds import (
    UDS_FIELDS_WITHOUT_VALUES,
    UDS_VALUE_SOURCES,
)
from garmin_running_data_normalizer.normalizers.vo2max import (
    VO2MAX_FIELDS_WITHOUT_VALUES,
    VO2MAX_VALUE_SOURCES,
)
from garmin_running_data_normalizer.output_experience import DATASET_FIELDS
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    run_snapshot_all,
)
from garmin_running_data_normalizer.snapshot.merge import _daily_definition, _metric_row
from garmin_running_data_normalizer.snapshot.policies import MERGE_RULES_VERSION
from tests.test_repeated_records import audit, table
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, load, write_export
from tests.test_snapshot_unreadable_files import one_snapshot, register

DAILY = {
    "hill_score_daily": (HILL_VALUE_SOURCES, HILL_FIELDS_WITHOUT_VALUES),
    "endurance_score_daily": (ENDURANCE_VALUE_SOURCES, ENDURANCE_FIELDS_WITHOUT_VALUES),
    "race_prediction_daily": (RACE_PREDICTION_VALUE_SOURCES, RACE_PREDICTION_FIELDS_WITHOUT_VALUES),
    "sleep_daily": (SLEEP_VALUE_SOURCES, SLEEP_FIELDS_WITHOUT_VALUES),
    "uds_daily": (UDS_VALUE_SOURCES, UDS_FIELDS_WITHOUT_VALUES),
    "acute_training_load_daily": (
        ACUTE_TRAINING_LOAD_VALUE_SOURCES,
        ACUTE_TRAINING_LOAD_FIELDS_WITHOUT_VALUES,
    ),
    "training_readiness_daily": (
        TRAINING_READINESS_VALUE_SOURCES,
        TRAINING_READINESS_FIELDS_WITHOUT_VALUES,
    ),
    "vo2max_daily": (VO2MAX_VALUE_SOURCES, VO2MAX_FIELDS_WITHOUT_VALUES),
    "training_history_daily": (
        TRAINING_HISTORY_VALUE_SOURCES,
        TRAINING_HISTORY_FIELDS_WITHOUT_VALUES,
    ),
}
FAMILIES = {
    "hill_score_daily": "hill_score",
    "endurance_score_daily": "endurance_score",
    "race_prediction_daily": "race_prediction",
    "sleep_daily": "sleep",
    "uds_daily": "uds",
    "acute_training_load_daily": "acute_training_load",
    "training_readiness_daily": "training_readiness",
    "vo2max_daily": "vo2max",
    "training_history_daily": "training_history",
}
# The file of each daily dataset in an Export, and a record of it with a date.
FILES = {
    "hill_score_daily": "DI-Connect-Metrics/HillScore_synthetic.json",
    "endurance_score_daily": "DI-Connect-Metrics/EnduranceScore_synthetic.json",
    "race_prediction_daily": "DI-Connect-Metrics/RunRacePredictions_synthetic.json",
    "sleep_daily": "DI-Connect-Wellness/synthetic_sleepData.json",
    "uds_daily": "DI-Connect-Aggregator/UDSFile_synthetic.json",
    "acute_training_load_daily": "DI-Connect-Metrics/MetricsAcuteTrainingLoad_synthetic.json",
    "training_readiness_daily": "DI-Connect-Metrics/TrainingReadinessDTO_synthetic.json",
    "vo2max_daily": "DI-Connect-Metrics/MetricsMaxMetData_synthetic.json",
    "training_history_daily": "DI-Connect-Metrics/TrainingHistory_synthetic.json",
}
DATE = "2030-02-01"
STAMP = "2030-02-01T06:00:00"
KEPT = {
    "hill_score_daily": {"calendarDate": DATE, "overallScore": 70},
    "endurance_score_daily": {"calendarDate": DATE, "overallScore": 6000},
    "race_prediction_daily": {
        "calendarDate": DATE,
        "timestamp": STAMP,
        "raceTime5K": 1000,
        "raceTime10K": 2100,
        "raceTimeHalf": 4700,
        "raceTimeMarathon": 9900,
    },
    "sleep_daily": {
        "calendarDate": DATE,
        "sleepStartTimestampGMT": "2030-01-31T14:00:00Z",
        "sleepEndTimestampGMT": "2030-01-31T21:00:00Z",
        "sleepTimeSeconds": 25200,
    },
    "uds_daily": {"calendarDate": DATE, "totalSteps": 1},
    "acute_training_load_daily": {"calendarDate": DATE, "timestamp": STAMP, "dailyTrainingLoadAcute": 1},
    "training_readiness_daily": {"calendarDate": DATE, "timestamp": STAMP, "score": 1},
    "vo2max_daily": {"calendarDate": DATE, "updateTimestamp": STAMP, "vo2MaxValue": 50, "sport": "RUNNING"},
    "training_history_daily": {
        "calendarDate": DATE,
        "timestamp": STAMP,
        "trainingStatus": "PRODUCTIVE",
        "sport": "RUNNING",
    },
}
# A record of each daily dataset without its date that holds a value.
WITHOUT_DATE = {
    "hill_score_daily": {"overallScore": 71},
    "endurance_score_daily": {"overallScore": 6001},
    "race_prediction_daily": {"timestamp": STAMP, "raceTime5K": 1001},
    "sleep_daily": {"sleepTimeSeconds": 25000},
    "uds_daily": {"totalSteps": 2},
    "acute_training_load_daily": {"timestamp": STAMP, "dailyTrainingLoadAcute": 2},
    "training_readiness_daily": {"timestamp": STAMP, "score": 2},
    "vo2max_daily": {"updateTimestamp": STAMP, "vo2MaxValue": 51, "sport": "RUNNING"},
    "training_history_daily": {"timestamp": STAMP, "trainingStatus": "PEAKING"},
}
TABLES = tuple(DAILY)


def export_with(root: Path, name: str, files: dict[str, Any]) -> Path:
    """An Export with one Activity and these daily files."""
    source = write_export(root, name, [_activity("A1")])
    for relative, value in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    return source


def summary_of(output: Path) -> dict[str, Any]:
    return load(output / "run_summary.json")


def outcome(output: Path) -> dict[str, Any]:
    """What a run of one Export gives, whatever the form of the run."""
    summary = summary_of(output)
    quality = load(output / "diagnostics/run_quality.json")
    completeness = load(output / "diagnostics/source_completeness.json")
    return {
        "status": summary["status"],
        "warnings": sorted(
            (item["code"], item.get("family", ""), item.get("dataset", ""), item.get("count", 1))
            for item in summary["warnings"]
        ),
        "families": {
            family: (result["status"], result["record_count"], result.get("left_out_row_count", 0))
            for family, result in summary["family_results"].items()
        },
        "audits": {
            dataset: {
                field: audit(output, dataset).get(field)
                for field in (
                    "source_record_count",
                    "accepted_record_count",
                    "excluded_record_count",
                    "excluded_reason_counts",
                    "empty_record_count",
                    "same_value_duplicate_count",
                )
            }
            for dataset in TABLES
        },
        "run_quality": {
            "excluded": {key: value for key, value in quality["excluded"].items() if key != "authority_references"},
            "warnings": quality["warnings"],
        },
        # The state of a family also counts its source observations, which a
        # Snapshot counts before the records are merged (stage A3d-4).
        "content_validity": sorted(
            (item["source_family_id"], item["content_validity"]) for item in completeness["families"]
        ),
        "tables": {dataset: table(output, dataset) for dataset in TABLES},
    }


def both_forms(test: unittest.TestCase, root: Path, source: Path, name: str) -> Path:
    """Run one Export once and as one Snapshot; check that they agree, and
    return the output of the one-shot run."""
    one_shot = root / f"{name}-one-shot"
    run_all(source, one_shot)
    snapshot = one_snapshot(root, source, f"{name}-snapshot")
    test.assertEqual(outcome(snapshot), outcome(one_shot))
    return one_shot


def warnings_of(output: Path, code: str) -> dict[str, int]:
    return {
        str(item["dataset"]): int(item["count"])
        for item in summary_of(output)["warnings"]
        if item["code"] == code
    }


class ValueFieldsTest(unittest.TestCase):
    def test_every_field_of_a_daily_dataset_is_a_value_or_not(self) -> None:
        # A field added to a dataset without its source fields would let a row
        # with a value pass for an empty record.
        for dataset, (value_sources, without_values) in DAILY.items():
            with self.subTest(dataset=dataset):
                fields = set(DATASET_FIELDS[dataset]) - {"disagreeing_fields"}
                self.assertEqual(set(value_sources) | set(without_values), fields)
                self.assertFalse(set(value_sources) & set(without_values))
                self.assertTrue(all(value_sources.values()))

    def test_the_snapshot_build_keeps_every_source_field_of_a_value(self) -> None:
        names = {
            "race_prediction_daily": ("RunRacePredictions_1.json",),
            "sleep_daily": ("synthetic_sleepData.json",),
            "uds_daily": ("UDSFile_1.json",),
            "acute_training_load_daily": ("MetricsAcuteTrainingLoad_1.json",),
            "training_readiness_daily": ("TrainingReadinessDTO_1.json",),
            "vo2max_daily": (
                "ActivityVo2Max_1.json",
                "MetricsMaxMetData_1.json",
                "snapshot_vo2max.json",
            ),
            "training_history_daily": ("TrainingHistory_1.json",),
        }
        for dataset, (value_sources, _without_values) in DAILY.items():
            sources = set(value_source_names(value_sources))
            with self.subTest(dataset=dataset):
                if dataset in ("hill_score_daily", "endurance_score_daily"):
                    kept = set(_metric_row(dataset, {name: 1 for name in sources}))
                    self.assertLessEqual(sources, kept)
                    continue
                for name in names[dataset]:
                    definition = _daily_definition(f"DI-Connect-Metrics/{name}")
                    self.assertIsNotNone(definition)
                    self.assertEqual(definition[0], dataset)
                    self.assertLessEqual(sources, set(definition[1]))


class RowsLeftOutTest(unittest.TestCase):
    def test_a_row_without_its_date_that_holds_a_value_is_left_out_and_announced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {FILES[dataset]: [KEPT[dataset], WITHOUT_DATE[dataset]] for dataset in TABLES},
            )
            output = both_forms(self, root, source, "values")
            summary = summary_of(output)
            self.assertEqual(summary["status"], "PARTIAL_SUCCESS")
            self.assertEqual(warnings_of(output, "DATA_ROW_LEFT_OUT"), {dataset: 1 for dataset in TABLES})
            for dataset in TABLES:
                with self.subTest(dataset=dataset):
                    record = audit(output, dataset)
                    self.assertEqual(record["excluded_record_count"], 1)
                    self.assertNotIn("empty_record_count", record)
                    self.assertEqual(len(table(output, dataset)), 1)
                    self.assertEqual(
                        summary["family_results"][FAMILIES[dataset]]["left_out_row_count"], 1
                    )
            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("- Rows left out: 9 (`hill_score_daily` 1, ", start_here)

    def test_a_row_that_holds_no_value_is_only_counted(self) -> None:
        # A Sleep record with only its retro flag, a UDS record that is an
        # empty object, a Hill record with a date that cannot be read, and a
        # VO2max record with its key and no value hold no value.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {
                    FILES["sleep_daily"]: [KEPT["sleep_daily"], {"retro": False}, {"retro": True}],
                    FILES["uds_daily"]: [KEPT["uds_daily"], {}, {"totalSteps": None, "steps": ""}],
                    FILES["hill_score_daily"]: [KEPT["hill_score_daily"], {"calendarDate": "2030-13-45"}],
                    FILES["vo2max_daily"]: [
                        KEPT["vo2max_daily"],
                        {"calendarDate": DATE, "updateTimestamp": STAMP, "sport": "RUNNING", "maxMet": []},
                    ],
                },
            )
            output = both_forms(self, root, source, "empty")
            summary = summary_of(output)
            self.assertNotEqual(summary["status"], "PARTIAL_SUCCESS")
            self.assertEqual(warnings_of(output, "DATA_ROW_LEFT_OUT"), {})
            expected = {"sleep_daily": 2, "uds_daily": 2, "hill_score_daily": 1, "vo2max_daily": 1}
            for dataset, count in expected.items():
                with self.subTest(dataset=dataset):
                    record = audit(output, dataset)
                    self.assertEqual(record["empty_record_count"], count)
                    self.assertEqual(record["excluded_record_count"], 0)
                    self.assertEqual(record["excluded_reason_counts"], {})
                    self.assertNotIn("left_out_row_count", summary["family_results"][FAMILIES[dataset]])
            quality = load(output / "diagnostics/run_quality.json")
            self.assertEqual(quality["excluded"]["total_count"], 0)
            completeness = load(output / "diagnostics/source_completeness.json")
            self.assertNotIn(
                "MALFORMED", {item["content_validity"] for item in completeness["families"]}
            )
            self.assertNotIn("Rows left out", (output / "START_HERE.md").read_text(encoding="utf-8"))

    def test_a_value_of_an_unexpected_type_is_a_value(self) -> None:
        # Zero and false are values, and so is a value that the dataset would
        # leave empty, such as text for a number.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {
                    FILES["uds_daily"]: [
                        KEPT["uds_daily"],
                        {"totalSteps": "abc"},
                        {"restingHeartRate": 0},
                    ],
                    FILES["training_readiness_daily"]: [
                        KEPT["training_readiness_daily"],
                        {"timestamp": STAMP, "validSleep": False},
                    ],
                },
            )
            output = both_forms(self, root, source, "unexpected")
            self.assertEqual(
                warnings_of(output, "DATA_ROW_LEFT_OUT"),
                {"uds_daily": 2, "training_readiness_daily": 1},
            )
            self.assertEqual(summary_of(output)["status"], "PARTIAL_SUCCESS")

    def test_a_race_prediction_keeps_the_distances_that_it_gives(self) -> None:
        missing_marathon = {key: value for key, value in KEPT["race_prediction_daily"].items() if key != "raceTimeMarathon"}
        missing_marathon["calendarDate"] = "2030-02-02"
        without_distances = {"calendarDate": "2030-02-03", "timestamp": "2030-02-03T06:00:00", "raceTime5K": None}
        zero_distance = {**KEPT["race_prediction_daily"], "calendarDate": "2030-02-04", "raceTimeHalf": 0}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {
                    FILES["race_prediction_daily"]: [
                        KEPT["race_prediction_daily"],
                        missing_marathon,
                        without_distances,
                        zero_distance,
                    ]
                },
            )
            output = both_forms(self, root, source, "race")
            rows = {row["calendar_date"]: row for row in table(output, "race_prediction_daily")}
            self.assertEqual(sorted(rows), [DATE, "2030-02-02"])
            self.assertIsNone(rows["2030-02-02"]["race_time_marathon_sec"])
            self.assertEqual(rows["2030-02-02"]["race_time_half_sec"], 4700)
            record = audit(output, "race_prediction_daily")
            # The record without distances holds no value; the one with a
            # distance of zero is left out until stage A3d-2.
            self.assertEqual(record["empty_record_count"], 1)
            self.assertEqual(record["excluded_reason_counts"], {"missing_or_invalid_race_prediction": 1})
            self.assertEqual(warnings_of(output, "DATA_ROW_LEFT_OUT"), {"race_prediction_daily": 1})

    def test_a_family_whose_rows_all_lack_their_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {FILES["uds_daily"]: [WITHOUT_DATE["uds_daily"]], FILES["sleep_daily"]: [{"retro": False}]},
            )
            output = both_forms(self, root, source, "only")
            families = summary_of(output)["family_results"]
            self.assertEqual(families["uds"]["status"], "PROCESSED_EMPTY")
            self.assertEqual(families["sleep"]["status"], "PROCESSED_EMPTY")
            codes = {(item["code"], item.get("family")) for item in summary_of(output)["warnings"]}
            self.assertIn(("OPTIONAL_FAMILY_EMPTY", "uds"), codes)
            self.assertIn(("DATA_ROW_LEFT_OUT", "uds"), codes)
            self.assertIn(("OPTIONAL_FAMILY_EMPTY", "sleep"), codes)
            self.assertNotIn(("DATA_ROW_LEFT_OUT", "sleep"), codes)

    def test_copies_within_one_export_are_counted(self) -> None:
        # Copies of a row left out, and of a row that holds no value, count as
        # rows, also when a Snapshot writes the row once with its numbers.
        without_value = {"calendarDate": DATE, "updateTimestamp": STAMP, "sport": "RUNNING"}
        with_other_value = {**without_value, "maxMet": 3}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {
                    FILES["uds_daily"]: [KEPT["uds_daily"], WITHOUT_DATE["uds_daily"], WITHOUT_DATE["uds_daily"]],
                    FILES["sleep_daily"]: [KEPT["sleep_daily"], {"retro": False}, {"retro": False}],
                    FILES["vo2max_daily"]: [KEPT["vo2max_daily"], with_other_value, with_other_value, without_value],
                },
            )
            output = both_forms(self, root, source, "copies")
            self.assertEqual(audit(output, "uds_daily")["excluded_record_count"], 2)
            self.assertEqual(audit(output, "sleep_daily")["empty_record_count"], 2)
            self.assertEqual(
                audit(output, "vo2max_daily")["excluded_reason_counts"], {"missing_or_invalid_vo2max": 2}
            )
            self.assertEqual(audit(output, "vo2max_daily")["empty_record_count"], 1)
            self.assertEqual(audit(output, "uds_daily")["source_record_count"], 3)

    def test_hill_and_endurance_records_under_data_are_read_alike(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {
                    FILES["hill_score_daily"]: {
                        "data": [KEPT["hill_score_daily"], {**KEPT["hill_score_daily"], "calendarDate": "2030-02-02"}]
                    },
                    FILES["endurance_score_daily"]: {"records": [KEPT["endurance_score_daily"]]},
                },
            )
            output = both_forms(self, root, source, "wrapped")
            self.assertEqual(len(table(output, "hill_score_daily")), 2)
            self.assertEqual(len(table(output, "endurance_score_daily")), 1)


class SnapshotRowsTest(unittest.TestCase):
    def test_rows_without_a_key_are_written_for_run_all_and_never_held(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = export_with(
                root,
                "first",
                {
                    FILES["uds_daily"]: [KEPT["uds_daily"], WITHOUT_DATE["uds_daily"], WITHOUT_DATE["uds_daily"]],
                    FILES["sleep_daily"]: [KEPT["sleep_daily"], {"retro": False}],
                },
            )
            second = export_with(
                root,
                "second",
                {FILES["uds_daily"]: [KEPT["uds_daily"], WITHOUT_DATE["uds_daily"], {"totalSteps": 3}]},
            )
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            output = root / "output"
            run_snapshot_all(store, output)
            # The same row in both Snapshots is one row, and its copy within
            # the first is a further row; the row only in the second, and the
            # empty Sleep record only in the first, count as well.
            self.assertEqual(audit(output, "uds_daily")["excluded_record_count"], 3)
            self.assertEqual(audit(output, "sleep_daily")["empty_record_count"], 1)
            merge = load(output / "snapshot/canonical_merge_summary.json")
            self.assertEqual(merge["merge_rules_version"], MERGE_RULES_VERSION)
            self.assertEqual(MERGE_RULES_VERSION, "garmin_snapshot_merge_rules:v2.5")
            self.assertEqual(merge["review_hold_count"], 0)
            uds = merge["datasets"]["uds_daily"]
            self.assertEqual(uds["keyless_observation_count"], 4)
            self.assertEqual(uds["keyless_record_count"], 2)
            self.assertEqual(uds["null_key_hold_count"], 0)
            self.assertEqual(uds["canonical_record_count"], 1)

    def test_the_order_of_processing_does_not_change_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for number, rows in enumerate(
                (
                    [KEPT["uds_daily"], {"totalSteps": 4}, {}],
                    [KEPT["uds_daily"], {"totalSteps": 5}, {"totalSteps": 4}],
                    [KEPT["uds_daily"], {}, {"steps": 6}],
                ),
                start=1,
            ):
                source = export_with(root, f"source-{number}", {FILES["uds_daily"]: rows})
                register(store, source, f"S{number}", number)
            builds = [
                build_approved_input(store, root / f"build-{index}", processing_sequence=sequence)
                for index, sequence in enumerate((["S1", "S2", "S3"], ["S3", "S1", "S2"], ["S2", "S3", "S1"]))
            ]
            self.assertEqual(len({build["canonical_build_sha256"] for build in builds}), 1)
            self.assertEqual(len({build["approved_input_content_sha256"] for build in builds}), 1)

    def test_the_support_bundle_carries_counts_and_reasons_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(
                root,
                "export",
                {FILES["uds_daily"]: [KEPT["uds_daily"], {"totalSteps": 987654321, "date": "Private-date"}]},
            )
            output = one_snapshot(root, source)
            report = doctor_run_output(output)
            self.assertIn("DATA_ROW_LEFT_OUT", {item["code"] for item in report["findings"]})
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            with zipfile.ZipFile(bundle) as archive:
                content = b"".join(archive.read(name) for name in archive.namelist())
            self.assertIn(b"DATA_ROW_LEFT_OUT", content)
            self.assertNotIn(b"987654321", content)
            self.assertNotIn(b"Private-date", content)


if __name__ == "__main__":
    unittest.main()
