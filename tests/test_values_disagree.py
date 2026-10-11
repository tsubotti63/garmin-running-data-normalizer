"""Values that disagree within one Export are left empty and kept, not stopped."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics.doctor import DoctorError, doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import (
    SupportBundleError,
    build_support_bundle,
)
from garmin_running_data_normalizer import output_experience
from garmin_running_data_normalizer import run_all as run_all_module
from garmin_running_data_normalizer.normalizers.sleep import normalize_sleep_daily_assets
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.standalone import (
    StandaloneHandoffError,
    validate_standalone_handoff,
)
from tests.test_remaining_wellness_metrics import fit_timestamp, hrv_fit, json_asset


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
DAY = "2030-02-01"
MORNING = "2030-02-01T06:00:00"
MORNING_MS = int(datetime(2030, 2, 1, 6, tzinfo=timezone.utc).timestamp() * 1000)

# For each daily dataset: its file, one observation, the change in a second
# observation of the same stable key, the field that then disagrees, and the
# two normalized values. The values are distinctive so that the privacy
# checks can look for them.
DISAGREEING = {
    "hill_score_daily": (
        "HillScore_synthetic.json",
        {"calendarDate": DAY, "overallScore": 9876543, "strengthScore": 50},
        {"overallScore": 9876544},
        "overall_score",
        (9876543, 9876544),
    ),
    "endurance_score_daily": (
        "EnduranceScore_synthetic.json",
        {"calendarDate": DAY, "overallScore": 5432109.5, "classification": 3},
        {"overallScore": 5432110.5},
        "overall_score",
        (5432109.5, 5432110.5),
    ),
    "race_prediction_daily": (
        "RunRacePredictions_synthetic.json",
        {
            "calendarDate": DAY,
            "timestamp": MORNING,
            "raceTime5K": 1234567,
            "raceTime10K": 2100,
            "raceTimeHalf": 4700,
            "raceTimeMarathon": 9900,
        },
        {"raceTime5K": 7654321},
        "race_time_5k_sec",
        (1234567, 7654321),
    ),
    "sleep_daily": (
        "sleepData.json",
        {
            "calendarDate": "2030-02-02",
            "sleepStartTimestampGMT": "2030-02-01T14:00:00Z",
            "sleepEndTimestampGMT": "2030-02-01T22:00:00Z",
            "deepSleepSeconds": 3600,
            "lightSleepSeconds": 18000,
            "remSleepSeconds": 5400,
            "sleepScores": {"overall": {"value": 91}},
        },
        {"sleepScores": {"overall": {"value": 92}}},
        "sleep_score",
        (91, 92),
    ),
    "uds_daily": (
        "UDSFile_synthetic.json",
        {"calendarDate": DAY, "totalSteps": 3456789, "bmrKilocalories": 1500},
        {"totalSteps": 3456790},
        "steps",
        (3456789, 3456790),
    ),
    "acute_training_load_daily": (
        "MetricsAcuteTrainingLoad_synthetic.json",
        {"calendarDate": DAY, "timestamp": MORNING_MS, "dailyTrainingLoadAcute": 911},
        {"dailyTrainingLoadAcute": 912},
        "daily_training_load_acute",
        (911, 912),
    ),
    "training_readiness_daily": (
        "TrainingReadinessDTO_synthetic.json",
        {"calendarDate": DAY, "timestamp": MORNING, "score": 77},
        {"score": 78},
        "training_readiness_score",
        (77, 78),
    ),
    "vo2max_daily": (
        "MetricsMaxMetData_synthetic.json",
        {"calendarDate": DAY, "updateTimestamp": MORNING, "vo2MaxValue": 61, "sport": "RUNNING"},
        {"vo2MaxValue": 62},
        "vo2max",
        (61, 62),
    ),
    "training_history_daily": (
        "TrainingHistory_synthetic.json",
        {"calendarDate": DAY, "timestamp": MORNING, "trainingStatus": "MAINTAINING", "sport": "RUNNING"},
        {"trainingStatus": "PRODUCTIVE"},
        "training_status",
        ("MAINTAINING", "PRODUCTIVE"),
    ),
}
FAMILY = {
    "hill_score_daily": "hill_score",
    "endurance_score_daily": "endurance_score",
    "race_prediction_daily": "race_prediction",
    "sleep_daily": "sleep",
    "uds_daily": "uds",
    "acute_training_load_daily": "acute_training_load",
    "training_readiness_daily": "training_readiness",
    "vo2max_daily": "vo2max",
    "training_history_daily": "training_history",
    "hrv_daily": "hrv",
}
PRIVATE_VALUES = ("9876543", "9876544", "5432109", "5432110", "1234567", "7654321", "3456789", "3456790")

# The normalized values of the agreeing Export below, without
# disagreeing_fields, and its analysis tables without the new columns, as
# v1.7.1 (main at 728d4f5, before stage A2a) writes them.
V1_7_1_AGREEING_VALUES_SHA256 = "71c8f37ee7d88f1898e423cbe23fc35a9c0e9cff75eae220a9f3cb6288c3a11f"


def _metrics_folder(root: Path) -> Path:
    folder = root / "DI_CONNECT" / "DI-Connect-Metrics"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_disagreeing_export(root: Path) -> Path:
    shutil.copytree(SYNTHETIC_EXPORT, root)
    metrics = _metrics_folder(root)
    for name, row, change, _field, _values in DISAGREEING.values():
        (metrics / name).write_text(json.dumps([row, {**row, **change}]), encoding="utf-8")
    timestamp = fit_timestamp("2030-02-01T12:00:00Z")
    (metrics / "synthetic_hrv.fit").write_bytes(
        hrv_fit((70 * 128, timestamp), (75 * 128, timestamp))
    )
    return root


def write_agreeing_export(root: Path) -> Path:
    """Every daily family, with exact repeats and a missing stage, and no disagreement."""
    shutil.copytree(SYNTHETIC_EXPORT, root)
    metrics = _metrics_folder(root)
    for name, row, _change, _field, _values in DISAGREEING.values():
        (metrics / name).write_text(json.dumps([row, row]), encoding="utf-8")
    later_sleep = {
        **DISAGREEING["sleep_daily"][1],
        "calendarDate": "2030-02-03",
        "sleepStartTimestampGMT": "2030-02-02T14:00:00Z",
        "sleepEndTimestampGMT": "2030-02-02T21:00:00Z",
        "deepSleepSeconds": None,
    }
    (metrics / "later_sleepData.json").write_text(json.dumps([later_sleep]), encoding="utf-8")
    timestamp = fit_timestamp("2030-02-01T12:00:00Z")
    (metrics / "synthetic_hrv.fit").write_bytes(
        hrv_fit((70 * 128, timestamp), (70 * 128, timestamp))
    )
    return root


def values_digest(output: Path) -> str:
    """Digest the normalized values and analysis tables without the stage A2a additions."""
    new_columns = {"disagreeing_fields", "hill_disagreeing_fields", "endurance_disagreeing_fields"}
    digest = hashlib.sha256()
    for path in sorted((output / "normalized").glob("*.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))
        values = [{key: value for key, value in row.items() if key != "disagreeing_fields"} for row in rows]
        digest.update(path.name.encode() + b"\n" + json.dumps(values, sort_keys=True).encode() + b"\n")
    for path in sorted((output / "analysis").glob("*.csv")):
        reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
        columns = [name for name in reader.fieldnames or [] if name not in new_columns]
        table = [columns, *([row[name] for name in columns] for row in reader)]
        digest.update(path.name.encode() + b"\n" + json.dumps(table).encode() + b"\n")
    return digest.hexdigest()


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _key_rows(rows: list[dict], dataset: str) -> list[dict]:
    if dataset == "sleep_daily":
        return [row for row in rows if row["sleep_day"] == "2030-02-02"]
    return [row for row in rows if row["calendar_date"] == DAY]


class DisagreeingExportRunAllTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        root = Path(cls._directory.name)
        cls.output = root / "output"
        cls.result = run_all(
            write_disagreeing_export(root / "export"), cls.output, external_safe_pack=True
        )
        cls.bundle = root / "support.zip"
        build_support_bundle(cls.output, cls.bundle)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_every_daily_family_keeps_one_row_with_the_field_empty(self) -> None:
        for dataset, (_name, _row, _change, field, values) in DISAGREEING.items():
            with self.subTest(dataset=dataset):
                rows = _key_rows(_load(self.output / f"normalized/{dataset}.json"), dataset)
                self.assertEqual(len(rows), 1)
                self.assertIsNone(rows[0][field])
                self.assertEqual(rows[0]["disagreeing_fields"], [field])
                audit = _load(self.output / f"audit/{dataset}.json")
                self.assertEqual(audit["disagreement_key_count"], 1)
                [entry] = audit["disagreements"]
                self.assertEqual(entry["observation_count"], 2)
                self.assertEqual(
                    entry["fields"],
                    [
                        {
                            "field": field,
                            "values": [
                                {"value": value, "observation_count": 1} for value in values
                            ],
                        }
                    ],
                )
        [hrv] = _key_rows(_load(self.output / "normalized/hrv_daily.json"), "hrv_daily")
        self.assertIsNone(hrv["hrv_value"])
        self.assertEqual(hrv["disagreeing_fields"], ["hrv_value"])
        self.assertEqual(
            _load(self.output / "audit/hrv_daily.json")["disagreements"][0]["fields"][0]["values"],
            [{"value": 70.0, "observation_count": 1}, {"value": 75.0, "observation_count": 1}],
        )

    def test_fields_that_agree_keep_their_values(self) -> None:
        [hill] = _key_rows(_load(self.output / "normalized/hill_score_daily.json"), "hill_score_daily")
        self.assertEqual(hill["strength_score"], 50)
        [race] = _key_rows(
            _load(self.output / "normalized/race_prediction_daily.json"), "race_prediction_daily"
        )
        self.assertEqual(race["race_time_10k_sec"], 2100)
        [sleep] = _key_rows(_load(self.output / "normalized/sleep_daily.json"), "sleep_daily")
        self.assertEqual(sleep["sleep_duration_minutes_ex_awake"], 450.0)
        self.assertEqual(sleep["sleep_normalization_status"], "available")

    def test_the_run_finishes_with_one_warning_per_family(self) -> None:
        self.assertEqual(self.result["exit_code"], 0)
        summary = _load(self.output / "run_summary.json")
        self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(summary["run_all_version"], 2)
        warnings = [item for item in summary["warnings"] if item["code"] == "VALUES_DISAGREE"]
        self.assertEqual(
            sorted((item["family"], item["count"]) for item in warnings),
            sorted((family, 1) for family in FAMILY.values()),
        )
        self.assertNotIn(
            "DAILY_METRICS_REVIEW_REQUIRED", {item["code"] for item in summary["warnings"]}
        )
        for family, result in summary["family_results"].items():
            with self.subTest(family=family):
                self.assertEqual(
                    result["disagreement_key_count"], int(family in FAMILY.values())
                )

    def test_run_quality_names_the_reason_after_the_rule(self) -> None:
        quality = _load(self.output / "diagnostics/run_quality.json")
        self.assertEqual(quality["format"], "garmin-running-data-normalizer-run-quality-v2")
        self.assertEqual(quality["schema_version"], "garmin-run-quality:v2")
        self.assertEqual(quality["conflict_summary"]["reason_code_counts"], {"VALUES_DISAGREE": 10})
        self.assertEqual(
            quality["conflict_summary"]["by_dataset"], {dataset: 1 for dataset in FAMILY}
        )

    def test_analysis_tables_name_the_fields_that_disagree(self) -> None:
        with (self.output / "analysis/performance_metrics_daily.csv").open(encoding="utf-8") as handle:
            rows = {row["calendar_date"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows[DAY]["hill_overall_score"], "")
        self.assertEqual(rows[DAY]["hill_strength_score"], "50")
        self.assertEqual(rows[DAY]["hill_disagreeing_fields"], "overall_score")
        self.assertEqual(rows[DAY]["endurance_disagreeing_fields"], "overall_score")

    def test_checks_accept_the_output(self) -> None:
        self.assertEqual(validate_standalone_handoff(self.output)["dataset_count"], 17)
        self.assertEqual(doctor_run_output(self.output)["completion_state"], "COMPLETED")
        with zipfile.ZipFile(self.bundle) as archive:
            quality = json.loads(archive.read("run_quality.json"))
        self.assertEqual(quality["conflict_summary"]["reason_code_counts"], {"VALUES_DISAGREE": 10})
        self.assertIn("VALUES_DISAGREE", {item["code"] for item in quality["warnings"]})

    def test_shared_files_carry_counts_and_no_observed_values(self) -> None:
        for path in (self.bundle, self.output / "analysis/external_safe_handoff.zip"):
            with self.subTest(file=path.name), zipfile.ZipFile(path) as archive:
                content = b"".join(archive.read(name) for name in archive.namelist())
                for value in PRIVATE_VALUES:
                    self.assertNotIn(value.encode(), content)
        # The local audit keeps the observed values.
        self.assertIn(b"7654321", (self.output / "audit/race_prediction_daily.json").read_bytes())


class AgreeingExportTest(unittest.TestCase):
    def test_values_without_disagreements_are_those_of_v1_7_1(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(write_agreeing_export(root / "export"), output)
            summary = _load(output / "run_summary.json")
            self.assertNotIn("VALUES_DISAGREE", {item["code"] for item in summary["warnings"]})
            for path in sorted((output / "normalized").glob("*.json")):
                with self.subTest(dataset=path.stem):
                    self.assertTrue(all(row["disagreeing_fields"] == [] for row in _load(path)))
            self.assertEqual(values_digest(output), V1_7_1_AGREEING_VALUES_SHA256)


class DerivedFieldTest(unittest.TestCase):
    def _sleep(self, *observations: dict) -> dict:
        base = {
            "calendarDate": "2030-02-02",
            "sleepStartTimestampGMT": "2030-02-01T14:00:00Z",
            "sleepEndTimestampGMT": "2030-02-01T22:00:00Z",
        }
        rows = [{**base, **observation} for observation in observations]
        [row] = normalize_sleep_daily_assets([json_asset("sleepData.json", rows)]).records
        return row

    def test_a_value_computed_alike_from_disagreeing_values_is_kept(self) -> None:
        # Deep 60 + light 120 minutes and deep 90 + light 90 minutes: the stages
        # disagree, and both observations give a duration of 180 minutes.
        row = self._sleep(
            {"deepSleepSeconds": 3600, "lightSleepSeconds": 7200},
            {"deepSleepSeconds": 5400, "lightSleepSeconds": 5400},
        )
        self.assertEqual(
            row["disagreeing_fields"], ["sleep_stage_deep_minutes", "sleep_stage_light_minutes"]
        )
        self.assertIsNone(row["sleep_stage_deep_minutes"])
        self.assertIsNone(row["sleep_stage_light_minutes"])
        self.assertEqual(row["sleep_duration_minutes_ex_awake"], 180.0)
        # The flags describe the merged row, which has no stage minutes left.
        self.assertFalse(row["sleep_stage_available_flag"])
        self.assertEqual(row["sleep_normalization_status"], "available")

    def test_a_value_computed_differently_is_empty_too(self) -> None:
        row = self._sleep(
            {"deepSleepSeconds": 3600, "lightSleepSeconds": 7200},
            {"deepSleepSeconds": 5400, "lightSleepSeconds": 7200},
        )
        self.assertEqual(
            row["disagreeing_fields"],
            ["sleep_duration_minutes_ex_awake", "sleep_stage_deep_minutes"],
        )
        self.assertIsNone(row["sleep_duration_minutes_ex_awake"])
        self.assertEqual(row["sleep_stage_light_minutes"], 120.0)


class RemovedStopsTest(unittest.TestCase):
    def test_nothing_in_the_product_stops_for_values_that_disagree(self) -> None:
        removed = (
            "DAILY_METRICS_CONFLICT",
            "PERFORMANCE_METRICS_CONFLICT",
            "DailyMetricConflictError",
            "PerformanceMetricsConflictError",
            "CONFLICT_PRESERVED_NO_WINNER",
        )
        source = ROOT / "src/garmin_running_data_normalizer"
        for path in sorted(source.rglob("*")):
            if path.suffix not in {".py", ".mjs", ".json", ".html"}:
                continue
            text = path.read_text(encoding="utf-8")
            for name in removed:
                with self.subTest(file=path.relative_to(source).as_posix(), name=name):
                    self.assertNotIn(name, text)


class EarlierContractVersionTest(unittest.TestCase):
    def test_an_output_with_another_contract_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            with patch.object(run_all_module, "RUN_ALL_VERSION", 1), patch.object(
                output_experience, "RUN_ALL_VERSION", 1
            ):
                run_all(SYNTHETIC_EXPORT, output)
            self.assertEqual(_load(output / "run_summary.json")["run_all_version"], 1)
            with self.assertRaisesRegex(StandaloneHandoffError, "contract version"):
                validate_standalone_handoff(output)
            with self.assertRaises(DoctorError) as caught:
                doctor_run_output(output)
            self.assertEqual(caught.exception.code, "DOCTOR_AUTHORITY_INVALID")
            with self.assertRaises(SupportBundleError) as caught_bundle:
                build_support_bundle(output, root / "support.zip")
            self.assertEqual(caught_bundle.exception.code, "SUPPORT_BUNDLE_AUTHORITY_INVALID")


if __name__ == "__main__":
    unittest.main()
