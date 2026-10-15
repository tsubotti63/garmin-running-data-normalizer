"""Rows that lack a required value are left out and announced, or only counted
when they hold no value, alike in one-shot and Snapshot runs (stage A3d-1); rows
without a usable identifier are left out, and Personal Records whose activity
link cannot be followed are kept unresolved (stage A3d-1b)."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.common.identity import (
    IDENTIFIER,
    IDENTIFIER_MAX_DIGITS,
    INVALID,
    MISSING,
    identifier_value,
    read_identifier,
)
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.detector import classify_source_name
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
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.runner import GoldenPathError, run_activities
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    run_snapshot_all,
)
from garmin_running_data_normalizer.snapshot.merge import _daily_definition, _metric_row
from garmin_running_data_normalizer.snapshot.policies import MERGE_RULES_VERSION
from tests.test_repeated_records import audit, table
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, gear, load, personal_record, write_export
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
                    path = f"DI-Connect-Metrics/{name}"
                    definition = _daily_definition(classify_source_name(path, "json"), path)
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
            self.assertEqual(sorted(rows), [DATE, "2030-02-02", "2030-02-04"])
            self.assertIsNone(rows["2030-02-02"]["race_time_marathon_sec"])
            self.assertEqual(rows["2030-02-02"]["race_time_half_sec"], 4700)
            # A distance of zero is a value of another form: the row stays,
            # with that distance empty (stage A3d-2a).
            self.assertIsNone(rows["2030-02-04"]["race_time_half_sec"])
            record = audit(output, "race_prediction_daily")
            # The record without distances holds no value.
            self.assertEqual(record["empty_record_count"], 1)
            self.assertEqual(record["excluded_reason_counts"], {})
            self.assertEqual(record["invalid_value_counts"], {"race_time_half_sec": 1})
            self.assertEqual(warnings_of(output, "DATA_ROW_LEFT_OUT"), {})
            self.assertEqual(warnings_of(output, "DATA_VALUE_INVALID"), {"race_prediction_daily": 1})

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
            self.assertEqual(MERGE_RULES_VERSION, "garmin_snapshot_merge_rules:v2.15")
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


RECORD_TABLES = ("activities", "gear", "activity_gear", "personal_records")


def records_export(
    root: Path,
    name: str,
    activities: list[dict[str, Any]],
    *,
    gear_rows: list[dict[str, Any]] | None = None,
    link_rows: dict[str, list[dict[str, Any]]] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> Path:
    """An Export with these Activities, Gear, links (as Garmin keys them), and
    Personal Records, written as given."""
    source = write_export(root, name, activities)
    fitness = source / "DI-Connect-Fitness"
    if gear_rows is not None or link_rows is not None:
        container: dict[str, Any] = {"gearDTOS": gear_rows or []}
        if link_rows is not None:
            container["gearActivityDTOs"] = link_rows
        (fitness / "synthetic_gear.json").write_text(json.dumps([container]), encoding="utf-8")
    if records is not None:
        (fitness / "synthetic_personalRecord.json").write_text(
            json.dumps([{"personalRecords": records}]), encoding="utf-8"
        )
    return source


def record_outcome(output: Path) -> dict[str, Any]:
    """What a run gives for the record datasets, whatever the form of the run."""
    relationships = load(output / "qa/relationship_summary.json")
    links = relationships["relationships"]["personal_records_to_activities"]
    counts = ("relationship_unresolved", "relationship_malformed", "relationship_conflict")
    return {
        **outcome(output),
        "record_audits": {
            name: {
                field: audit(output, name).get(field)
                for field in ("record_count", "excluded_record_count", "excluded_reason_counts")
            }
            for name in RECORD_TABLES
        },
        "record_tables": {name: table(output, name) for name in RECORD_TABLES},
        "personal_records_to_activities": {
            **{
                field: links.get(field)
                for field in (
                    "link_count",
                    "eligible_count",
                    "unresolved_count",
                    "orphan_count",
                    "independent_count",
                    "primary_unresolved_reason",
                )
            },
            # A Snapshot run gives these counts also when they are 0.
            **{field: links.get(field, 0) for field in counts},
        },
        "relationship_counts": {field: relationships.get(field, 0) for field in counts},
    }


def record_both_forms(test: unittest.TestCase, root: Path, source: Path, name: str) -> Path:
    one_shot = root / f"{name}-one-shot"
    run_all(source, one_shot)
    snapshot = one_snapshot(root, source, f"{name}-snapshot")
    test.assertEqual(record_outcome(snapshot), record_outcome(one_shot))
    return one_shot


class IdentifierRuleTest(unittest.TestCase):
    def test_how_a_value_names_a_record(self) -> None:
        digits = "1" * IDENTIFIER_MAX_DIGITS
        cases = (
            (123, (IDENTIFIER, "123")),
            (123.0, (IDENTIFIER, "123")),
            (float(2**53 - 1), (IDENTIFIER, str(2**53 - 1))),
            (" 0123", (IDENTIFIER, "123")),
            ("0", (IDENTIFIER, "0")),
            (-5, (IDENTIFIER, "-5")),
            ("-5", (IDENTIFIER, "-5")),
            ("SYNTHETIC-RUN-1", (IDENTIFIER, "SYNTHETIC-RUN-1")),
            # Only the ASCII digits 0-9 are digits; other digits are text.
            ("²", (IDENTIFIER, "²")),
            ("１２３", (IDENTIFIER, "１２３")),
            ("٣", (IDENTIFIER, "٣")),
            (digits, (IDENTIFIER, digits)),
            (None, (MISSING, None)),
            ("", (MISSING, None)),
            ("  ", (MISSING, None)),
            (True, (INVALID, None)),
            (123.5, (INVALID, None)),
            (float("nan"), (INVALID, None)),
            (float("inf"), (INVALID, None)),
            (float(2**53), (INVALID, None)),
            ([3], (INVALID, None)),
            ({"id": 3}, (INVALID, None)),
            (digits + "1", (INVALID, None)),
        )
        for value, expected in cases:
            with self.subTest(value=repr(value)[:24]):
                self.assertEqual(read_identifier(value), expected)
        self.assertEqual(identifier_value(123.0), 123)
        self.assertIsInstance(identifier_value(123.0), int)
        self.assertEqual(identifier_value(" 0123"), " 0123")


class IdentityRowsTest(unittest.TestCase):
    def test_rows_without_a_usable_identifier_are_left_out_alike(self) -> None:
        activities = [
            _activity("A1"),
            _activity("A2", activityId=123.0),
            # No identifier, but the fields for a key in its place.
            _activity("A3", activityId="  "),
            {"name": "No identifier and no key fields"},
            _activity("X1", activityId=[3]),
            _activity("X2", activityId=0),
            _activity("X3", activityId=True),
            _activity("X4", activityId=1.5),
            _activity("X5", activityId="1" * (IDENTIFIER_MAX_DIGITS + 1)),
        ]
        gear_rows = [
            gear(1, "Synthetic Shoe"),
            {**gear(7, "Synthetic Shoe 7"), "gearPk": 7.0},
            {"gearTypeName": "Shoes"},
            {**gear(2, "Synthetic Shoe 2"), "gearPk": 0},
            {**gear(3, "Synthetic Shoe 3"), "gearPk": 2.5},
            {**gear(4, "Synthetic Shoe 4"), "gearPk": True},
        ]
        link_rows = {
            "1": [{"activityId": "A1"}, {}, {"activityId": 0}],
            "": [{"activityId": "A1"}],
            "0": [{"activityId": "A1"}],
            # Text that is not ASCII digits names Gear that is not there.
            "²": [{"activityId": "A1"}],
        }
        records = [
            personal_record(1, "A1", 1.0),
            {**personal_record(2, "A1", 2.0), "personalRecordId": True},
            {**personal_record(3, "A1", 3.0), "personalRecordId": 2.5},
            {"current": True},
            {**personal_record(4, "A1", 4.0), "personalRecordId": 0},
            {**personal_record(5, "A1", 5.0), "personalRecordId": 6.0},
            {**personal_record(7, "A1", 7.0), "activityId": None},
            {**personal_record(8, "A1", 8.0), "activityId": [1]},
            {**personal_record(9, "A1", 9.0), "activityId": 0},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(
                root, "export", activities, gear_rows=gear_rows, link_rows=link_rows, records=records
            )
            output = record_both_forms(self, root, source, "identity")
            summary = summary_of(output)
            self.assertEqual(summary["status"], "PARTIAL_SUCCESS")
            self.assertEqual(
                warnings_of(output, "DATA_ROW_LEFT_OUT"),
                {"activities": 6, "gear": 4, "activity_gear": 4, "personal_records": 3},
            )
            self.assertEqual(summary["family_results"]["gear"]["left_out_row_count"], 8)
            self.assertIn(
                "- Rows left out: 17 (`activities` 6, `gear` 4, `activity_gear` 4, "
                "`personal_records` 3), which lack a required value, such as a date "
                "or a usable identifier;",
                (output / "START_HERE.md").read_text(encoding="utf-8"),
            )
            expected_reasons = {
                "activities": {"identity_invalid": 5, "identity_missing": 1},
                "gear": {"identity_invalid": 3, "identity_missing": 1},
                "activity_gear": {"identity_invalid": 2, "identity_missing": 2},
                "personal_records": {"identity_invalid": 2, "identity_missing": 1},
            }
            for name, reasons in expected_reasons.items():
                with self.subTest(dataset=name):
                    self.assertEqual(audit(output, name)["excluded_reason_counts"], reasons)
            activities_table = {row["garmin_activity_key"]: row for row in table(output, "activities")}
            self.assertIn("garmin_activity:A1", activities_table)
            self.assertEqual(activities_table["garmin_activity:123"]["activity_id"], 123)
            self.assertEqual(len(activities_table), 3)
            self.assertEqual(sorted(row["gear_key"] for row in table(output, "gear")), [1, 7])
            records_table = {row["personal_record_id"]: row for row in table(output, "personal_records")}
            self.assertEqual(sorted(records_table, key=str), [0, 1, 6, 7, 8, 9])
            self.assertEqual(records_table[9]["activity_relationship_status"], "independent")
            self.assertEqual(records_table[7]["activity_relationship_reason"], "activity_link_missing")
            self.assertEqual(records_table[8]["activity_relationship_reason"], "activity_link_invalid")
            self.assertIsNone(records_table[8]["activity_id"])
            codes = {item["code"]: item.get("count") for item in summary["warnings"]}
            self.assertEqual(codes["RELATIONSHIP_UNRESOLVED_INVALID_LINK"], 2)
            self.assertEqual(codes["RELATIONSHIP_UNRESOLVED_VALID_LINK"], 1)
            self.assertEqual(summary["relationship_warning_count"], 2)
            completeness = {
                item["source_family_id"]: item["content_validity"]
                for item in load(output / "diagnostics/source_completeness.json")["families"]
            }
            self.assertEqual(completeness["activities"], "MALFORMED")
            self.assertEqual(completeness["gear"], "MALFORMED")
            self.assertIn("activities", load(output / "diagnostics/run_quality.json")["excluded"]["by_dataset"])

    def test_links_to_rows_left_out_have_an_absent_endpoint(self) -> None:
        # The Activity 1.5 and the Gear 2.5 are left out; links that name
        # them as text are valid links whose endpoint is absent, kept with
        # that endpoint unresolved from stage A4a.
        activities = [_activity("A1"), _activity("X", activityId=1.5)]
        gear_rows = [gear(1, "Synthetic Shoe"), {**gear(2, "Synthetic Shoe 2"), "gearPk": 2.5}]
        link_rows = {"1": [{"activityId": "A1"}, {"activityId": "1.5"}], "2.5": [{"activityId": "A1"}]}
        records = [personal_record(1, "A1", 1.0), personal_record(2, "1.5", 2.0)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(
                root, "export", activities, gear_rows=gear_rows, link_rows=link_rows, records=records
            )
            output = record_both_forms(self, root, source, "absent")
            self.assertEqual(warnings_of(output, "DATA_ROW_LEFT_OUT"), {"activities": 1, "gear": 1})
            codes = {item["code"]: item.get("count") for item in summary_of(output)["warnings"]}
            self.assertEqual(codes["RELATIONSHIP_UNRESOLVED_VALID_LINK"], 3)
            self.assertNotIn("RELATIONSHIP_UNRESOLVED_INVALID_LINK", codes)
            self.assertEqual(
                [
                    (row["gear_key"], row["activity_id"], row["activity_relationship_status"], row["gear_relationship_status"])
                    for row in table(output, "activity_gear")
                ],
                [(1, "A1", "explicit", "explicit"), (1, "1.5", "unresolved", "explicit"), ("2.5", "A1", "explicit", "unresolved")],
            )
            self.assertEqual(
                [
                    (row["personal_record_id"], row["activity_relationship_status"])
                    for row in table(output, "personal_records")
                ],
                [(1, "explicit"), (2, "unresolved")],
            )
            entry = load(output / "qa/relationship_summary.json")["relationships"][
                "personal_records_to_activities"
            ]
            self.assertEqual(
                (entry["orphan_count"], entry["relationship_malformed"], entry["relationship_conflict"]),
                (1, 0, 0),
            )

    def test_an_identifier_written_as_an_integral_number_is_one_record_in_one_export(self) -> None:
        activities = [_activity("A1"), _activity("A2", activityId=123), _activity("A2", activityId=123.0)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(root, "export", activities)
            output = record_both_forms(self, root, source, "integral")
            self.assertEqual(sorted(str(row["activity_id"]) for row in table(output, "activities")), ["123", "A1"])
            self.assertEqual(audit(output, "activities")["same_value_duplicate_count"], 1)
            codes = {item["code"] for item in summary_of(output)["warnings"]}
            self.assertFalse({"DATA_ROW_LEFT_OUT", "VALUES_DISAGREE"} & codes)

    def test_a_personal_record_whose_activity_disagrees_is_kept_unresolved(self) -> None:
        records = [personal_record(1, "A1", 1.0), personal_record(1, "A2", 1.0)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(root, "export", [_activity("A1"), _activity("A2")], records=records)
            output = record_both_forms(self, root, source, "disagree")
            [record] = table(output, "personal_records")
            self.assertEqual(record["activity_relationship_status"], "unresolved")
            self.assertEqual(record["activity_relationship_reason"], "activity_link_values_disagree")
            self.assertIn("activity_id", record["disagreeing_fields"])
            relationships = load(output / "qa/relationship_summary.json")
            self.assertEqual(relationships["relationship_conflict"], 1)
            codes = {item["code"] for item in summary_of(output)["warnings"]}
            self.assertLessEqual({"VALUES_DISAGREE", "RELATIONSHIP_UNRESOLVED_INVALID_LINK"}, codes)
            self.assertEqual(summary_of(output)["status"], "PASS_WITH_WARNINGS")

    def test_the_support_bundle_and_the_external_safe_pack_carry_counts_only(self) -> None:
        activities = [_activity("A1"), _activity("X", activityId=[918273645])]
        gear_rows = [gear(1, "Synthetic Shoe"), {**gear(2, "Synthetic Shoe 2"), "gearPk": 5647382.5}]
        link_rows = {"1": [{"activityId": "A1"}, {"activityId": 0}]}
        records = [{**personal_record(1, "A1", 1.0), "activityId": [192837465]}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(
                root, "export", activities, gear_rows=gear_rows, link_rows=link_rows, records=records
            )
            output = root / "output"
            run_all(source, output, external_safe_pack=True)
            report = doctor_run_output(output)
            self.assertLessEqual(
                {"DATA_ROW_LEFT_OUT", "RELATIONSHIP_UNRESOLVED_INVALID_LINK"},
                {item["code"] for item in report["findings"]},
            )
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            with zipfile.ZipFile(bundle) as archive:
                bundle_content = b"".join(archive.read(name) for name in archive.namelist())
            with zipfile.ZipFile(output / "analysis/external_safe_handoff.zip") as archive:
                pack_content = b"".join(archive.read(name) for name in archive.namelist())
                context = json.loads(archive.read("safe/ANALYSIS_CONTEXT.json"))
            # The pack keeps the form of its warnings, so Gear and its links
            # give two warnings of the Gear family.
            self.assertEqual(
                sorted(
                    (item["family"], item["count"])
                    for item in context["warnings"]
                    if item["code"] == "DATA_ROW_LEFT_OUT"
                ),
                [("activities", 1), ("gear", 1), ("gear", 1)],
            )
            for content in (bundle_content, pack_content):
                self.assertIn(b"DATA_ROW_LEFT_OUT", content)
                self.assertIn(b"RELATIONSHIP_UNRESOLVED_INVALID_LINK", content)
                for value in (b"918273645", b"5647382", b"192837465"):
                    self.assertNotIn(value, content)

    def test_every_activities_row_left_out_stops_both_forms_of_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(root, "export", [{"name": "No identifier"}, _activity("X", activityId=0)])
            with self.assertRaises(RunAllError) as one_shot:
                run_all(source, root / "one-shot")
            self.assertEqual(one_shot.exception.code, "ACTIVITIES_EMPTY")
            with self.assertRaises(RunAllError) as snapshot:
                one_snapshot(root, source)
            self.assertEqual(snapshot.exception.code, "ACTIVITIES_EMPTY")

    def test_the_golden_path_stops_on_an_activities_row_left_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(root, "export", [_activity("A1"), _activity("X", activityId=[1])])
            with self.assertRaisesRegex(GoldenPathError, "no usable identifier"):
                run_activities(source, root / "golden")


class SnapshotIdentityTest(unittest.TestCase):
    def test_rows_without_a_usable_identifier_are_counted_across_snapshots(self) -> None:
        without = {"name": "No identifier and no key fields"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = records_export(root, "first", [_activity("A1"), without, without])
            second = records_export(
                root, "second", [_activity("A1", activityId=123.0), without, _activity("X", activityId=0)]
            )
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            output = root / "output"
            run_snapshot_all(store, output)
            # The same row in both Snapshots is one row, and its copy within
            # the first is a further row; the row with 0 is only in the second.
            self.assertEqual(
                audit(output, "activities")["excluded_reason_counts"],
                {"identity_invalid": 1, "identity_missing": 2},
            )
            merge = load(output / "snapshot/canonical_merge_summary.json")["datasets"]["activities"]
            self.assertEqual(merge["keyless_observation_count"], 4)
            self.assertEqual(merge["keyless_record_count"], 2)
            self.assertEqual(merge["null_key_hold_count"], 0)
            builds = [
                build_approved_input(store, root / f"build-{index}", processing_sequence=sequence)
                for index, sequence in enumerate((["S1", "S2"], ["S2", "S1"]))
            ]
            self.assertEqual(len({build["canonical_build_sha256"] for build in builds}), 1)

    def test_an_identifier_written_as_an_integral_number_is_one_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = records_export(root, "first", [_activity("A0"), _activity("A1", activityId=123)])
            second = records_export(root, "second", [_activity("A0"), _activity("A1", activityId=123.0)])
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            output = root / "output"
            run_snapshot_all(store, output)
            rows = [row for row in table(output, "activities") if row["activity_id"] != "A0"]
            self.assertEqual([row["activity_id"] for row in rows], [123])
            self.assertEqual(audit(output, "activities")["updated_record_count"], 0)


if __name__ == "__main__":
    unittest.main()
