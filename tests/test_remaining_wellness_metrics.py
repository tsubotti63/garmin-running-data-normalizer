from __future__ import annotations

import hashlib
import json
import shutil
import struct
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from garmin_running_data_normalizer.fit.parser import FIT_EPOCH_OFFSET
from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.daily_metrics import DailyMetricConflictError
from garmin_running_data_normalizer.normalizers.hrv import HRV_DAILY_FIELDS, normalize_hrv_daily_assets
from garmin_running_data_normalizer.normalizers.race_prediction import RACE_PREDICTION_FIELDS, normalize_race_prediction
from garmin_running_data_normalizer.normalizers.sleep import SLEEP_DAILY_FIELDS, normalize_sleep_daily_assets
from garmin_running_data_normalizer.normalizers.training_history import TRAINING_HISTORY_FIELDS, normalize_training_history
from garmin_running_data_normalizer.normalizers.training_load import ACUTE_TRAINING_LOAD_FIELDS, normalize_acute_training_load
from garmin_running_data_normalizer.normalizers.training_readiness import TRAINING_READINESS_FIELDS, normalize_training_readiness
from garmin_running_data_normalizer.normalizers.uds import UDS_FIELDS, normalize_uds
from garmin_running_data_normalizer.normalizers.vo2max import VO2MAX_FIELDS, normalize_vo2max
from garmin_running_data_normalizer.run_all import run_all


def json_asset(name: str, value: object) -> DiscoveredAsset:
    data = json.dumps(value, sort_keys=True).encode()
    return DiscoveredAsset("json", name, None, len(data), hashlib.sha256(data).hexdigest(), data)


def fit_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()) - FIT_EPOCH_OFFSET


def hrv_fit(*records: tuple[int, int]) -> bytes:
    definition = bytes([0x40, 0x00, 0x00]) + struct.pack("<H", 370) + bytes([2, 1, 2, 0x84, 253, 4, 0x86])
    body = definition + b"".join(bytes([0x00]) + struct.pack("<HI", raw, timestamp) for raw, timestamp in records)
    return bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT" + body


def fit_asset(name: str, data: bytes) -> DiscoveredAsset:
    return DiscoveredAsset("fit", name, None, len(data), hashlib.sha256(data).hexdigest(), data)


class RemainingWellnessMetricsTest(unittest.TestCase):
    def test_race_prediction_allowlist_and_conflict(self) -> None:
        row = {"calendarDate": "2026-01-01", "timestamp": "2026-01-01T06:00:00", "raceTime5K": 1000, "raceTime10K": 2100, "raceTimeHalf": 4700, "raceTimeMarathon": 9900, "deviceId": "private"}
        result = normalize_race_prediction([json_asset("RunRacePredictions_test.json", [row])])
        self.assertEqual(set(result.records[0]), set(RACE_PREDICTION_FIELDS))
        self.assertEqual(result.records[0]["observation_timestamp"], "2026-01-01T06:00:00")
        with self.assertRaises(DailyMetricConflictError):
            normalize_race_prediction([json_asset("RunRacePredictions_conflict.json", [row, {**row, "raceTime5K": 1001}])])

    def test_same_day_distinct_observations_are_preserved_and_exact_keys_dedupe(self) -> None:
        first = {"calendarDate": "2026-01-01", "timestamp": "2026-01-01T06:00:00", "raceTime5K": 1000, "raceTime10K": 2100, "raceTimeHalf": 4700, "raceTimeMarathon": 9900}
        second = {**first, "timestamp": "2026-01-01T18:00:00", "raceTime5K": 1001}
        result = normalize_race_prediction(
            [json_asset("RunRacePredictions_observations.json", [first, second, first])]
        )
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.audit["same_value_duplicate_count"], 1)
        self.assertEqual(
            result.audit["stable_key"],
            ["calendar_date", "observation_timestamp"],
        )

    def test_sleep_public_contract_and_exact_duplicate_dedupe(self) -> None:
        row = {"calendarDate": "2026-01-02", "sleepStartTimestampGMT": "2026-01-01T14:00:00Z", "sleepEndTimestampGMT": "2026-01-01T22:00:00Z", "sleepTimeSeconds": 27000, "deepSleepSeconds": 3600, "lightSleepSeconds": 18000, "remSleepSeconds": 5400, "awakeSleepSeconds": None, "sleepScores": {"overall": {"value": 80}}, "userProfilePK": "private"}
        result = normalize_sleep_daily_assets([json_asset("synthetic_sleepData.json", [row])])
        self.assertEqual(set(result.records[0]), set(SLEEP_DAILY_FIELDS))
        self.assertIsNone(result.records[0]["sleep_awake_minutes"])
        duplicate = normalize_sleep_daily_assets([json_asset("synthetic_sleepData.json", [row, row])])
        self.assertEqual(len(duplicate.records), 1)
        self.assertEqual(duplicate.records[0]["sleep_normalization_status"], "available")
        self.assertTrue(duplicate.records[0]["sleep_source_available_for_analysis_flag"])
        self.assertEqual(duplicate.audit["duplicate_group_count"], 1)
        self.assertEqual(duplicate.audit["duplicate_row_count"], 1)
        self.assertEqual(duplicate.audit["dedupe_method"], "exact_canonical_duplicate_collapsed")
        self.assertEqual(duplicate.audit["review_required_count"], 0)
        self.assertEqual(duplicate.audit["divergent_duplicate_count"], 0)

    def test_uds_generation_flags_and_no_private_fields(self) -> None:
        row = {"calendarDate": "2026-01-03", "totalSteps": 0, "totalDistanceMeters": 0, "activeKilocalories": 100, "bmrKilocalories": 1500, "bodyBattery": {"chargedValue": 20, "drainedValue": 10}, "allDayStress": {"aggregatorList": [{"type": "TOTAL", "averageStressLevel": 22, "maxStressLevel": 70, "stressDuration": 100, "restDuration": 200}]}, "bodyBatteryFeedback": {}, "hydration": {"valueInML": 2000}, "userProfilePK": "private"}
        result = normalize_uds([json_asset("UDSFile_test.json", [row])])
        self.assertEqual(set(result.records[0]), set(UDS_FIELDS))
        self.assertEqual(result.records[0]["steps"], 0)
        self.assertNotIn("hydration_ml", result.records[0])

    def test_acute_load_preserves_source_values_without_recalculation(self) -> None:
        row = {"calendarDate": 1767225600000, "timestamp": 1767229200000, "acwrPercent": 90, "acwrStatus": "SYNTHETIC", "dailyTrainingLoadAcute": 9, "dailyTrainingLoadChronic": 10, "dailyAcuteChronicWorkloadRatio": None}
        result = normalize_acute_training_load([json_asset("MetricsAcuteTrainingLoad_test.json", [row])])
        self.assertEqual(set(result.records[0]), set(ACUTE_TRAINING_LOAD_FIELDS))
        self.assertEqual(result.records[0]["observation_timestamp"], "2026-01-01T01:00:00Z")
        self.assertIsNone(result.records[0]["daily_acute_chronic_workload_ratio"])

    def test_training_readiness_hrv_derived_fields_are_source_values(self) -> None:
        row = {"calendarDate": "2026-01-04", "timestamp": "2026-01-04T07:30:00", "score": 50, "level": "SYNTHETIC", "recoveryTime": 2, "acwrFactorPercent": 3, "stressHistoryFactorPercent": 4, "hrvFactorPercent": 5, "sleepHistoryFactorPercent": 6, "acuteLoad": 7, "hrvWeeklyAverage": 8, "validSleep": True, "sleepScore": 9, "inputContext": "excluded"}
        result = normalize_training_readiness([json_asset("TrainingReadinessDTO_test.json", [row])])
        self.assertEqual(set(result.records[0]), set(TRAINING_READINESS_FIELDS))
        self.assertNotIn("input_context", result.records[0])

    def test_observation_grain_duplicate_contracts_for_remaining_families(self) -> None:
        cases = (
            (
                normalize_acute_training_load,
                "MetricsAcuteTrainingLoad_observations.json",
                {"calendarDate": "2026-01-04", "timestamp": 1767502800000, "dailyTrainingLoadAcute": 9},
                {"timestamp": 1767506400000, "dailyTrainingLoadAcute": 10},
                {"dailyTrainingLoadAcute": 11},
            ),
            (
                normalize_training_readiness,
                "TrainingReadinessDTO_observations.json",
                {"calendarDate": "2026-01-05", "timestamp": "2026-01-05T06:00:00", "score": 50},
                {"timestamp": "2026-01-05T18:00:00", "score": 51},
                {"score": 52},
            ),
            (
                normalize_training_history,
                "TrainingHistory_observations.json",
                {"calendarDate": "2026-01-06", "timestamp": "2026-01-06T06:00:00", "trainingStatus": "PRODUCTIVE", "sport": "RUNNING"},
                {"timestamp": "2026-01-06T18:00:00", "trainingStatus": "MAINTAINING"},
                {"trainingStatus": "RECOVERY"},
            ),
        )
        for normalizer, name, first, distinct_changes, conflict_changes in cases:
            with self.subTest(dataset=name):
                distinct = {**first, **distinct_changes}
                result = normalizer([json_asset(name, [first, distinct, first])])
                self.assertEqual(len(result.records), 2)
                self.assertEqual(result.audit["same_value_duplicate_count"], 1)
                with self.assertRaises(DailyMetricConflictError):
                    normalizer([json_asset(name, [first, {**first, **conflict_changes}])])

    def test_vo2max_preserves_series_observations_and_stops_same_key_conflict(self) -> None:
        old = {"calendarDate": "2022-01-22", "timestampGmt": "2022-01-22T05:00:00", "activityId": 123, "vo2MaxValue": 60, "sport": "RUNNING", "deviceId": "private"}
        new = {"calendarDate": "2022-01-22", "updateTimestamp": "2022-01-22T06:00:00", "vo2MaxValue": 61, "sport": "RUNNING", "maxMet": 17, "maxMetCategory": "SYNTHETIC", "calibratedData": 1}
        result = normalize_vo2max([json_asset("ActivityVo2Max_test.json", [old]), json_asset("MetricsMaxMetData_test.json", [new])])
        self.assertEqual([row["vo2max_source_series"] for row in result.records], ["activity_vo2max_daily", "performance_metrics_daily"])
        self.assertTrue(all(set(row) == set(VO2MAX_FIELDS) for row in result.records))
        self.assertEqual(result.records[0]["source_activity_id"], 123)
        self.assertEqual(result.records[0]["observation_timestamp"], "2022-01-22T05:00:00Z")
        with self.assertRaises(DailyMetricConflictError):
            normalize_vo2max([json_asset("ActivityVo2Max_test.json", [old, {**old, "vo2MaxValue": 62}])])

    def test_vo2max_stable_key_dimensions_preserve_observations(self) -> None:
        base = {"calendarDate": "2022-01-22", "updateTimestamp": "2022-01-22T06:00:00", "vo2MaxValue": 60, "sport": "RUNNING"}
        rows = [
            base,
            {**base, "sport": "CYCLING", "vo2MaxValue": 55},
            {**base, "updateTimestamp": "2022-01-22T18:00:00", "vo2MaxValue": 61},
            base,
        ]
        result = normalize_vo2max([json_asset("MetricsMaxMetData_dimensions.json", rows)])
        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.audit["same_value_duplicate_count"], 1)
        self.assertEqual(
            result.audit["stable_key"],
            ["calendar_date", "vo2max_source_series", "sport", "observation_timestamp"],
        )

    def test_hrv_analysis_reference_conflict_has_no_selected_value(self) -> None:
        timestamp = fit_timestamp("2026-01-05T12:00:00Z")
        result = normalize_hrv_daily_assets([fit_asset("synthetic.fit", hrv_fit((70 * 128, timestamp), (75 * 128, timestamp)))])
        row = result["records"][0]
        self.assertEqual(set(row), set(HRV_DAILY_FIELDS))
        self.assertIsNone(row["hrv_value"])
        self.assertEqual(row["analysis_role"], "analysis_reference_only")
        self.assertEqual(result["audit"]["same_day_conflict_count"], 1)
        self.assertEqual(
            result["audit"]["date_basis"],
            "fit_end_jst_date_from_message_370_field_253_timestamp",
        )

    def test_training_history_is_limited_to_approved_observation_fields(self) -> None:
        row = {"calendarDate": "2026-01-06", "timestamp": "2026-01-06T08:00:00", "trainingStatus": "PRODUCTIVE", "sport": "RUNNING", "fitnessLevelTrend": "excluded", "weeklyTrainingLoadSum": 100}
        result = normalize_training_history([json_asset("TrainingHistory_test.json", [row])])
        self.assertEqual(set(result.records[0]), set(TRAINING_HISTORY_FIELDS))

    def test_optional_absence_is_empty_without_error(self) -> None:
        self.assertEqual(normalize_race_prediction([]).records, [])
        self.assertEqual(normalize_sleep_daily_assets([]).records, [])
        self.assertEqual(normalize_uds([]).records, [])
        self.assertEqual(normalize_acute_training_load([]).records, [])
        self.assertEqual(normalize_training_readiness([]).records, [])
        self.assertEqual(normalize_vo2max([]).records, [])
        self.assertEqual(normalize_hrv_daily_assets([])["records"], [])
        self.assertEqual(normalize_training_history([]).records, [])

    def test_run_all_publishes_all_daily_metric_contracts(self) -> None:
        source = Path("examples/synthetic/garmin_export")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_root = root / "input"
            shutil.copytree(source, input_root)
            metrics = input_root / "DI_CONNECT" / "DI-Connect-Metrics"
            metrics.mkdir(parents=True, exist_ok=True)
            fixtures = {
                "RunRacePredictions_synthetic.json": [{"calendarDate": "2026-01-01", "timestamp": "2026-01-01T06:00:00", "raceTime5K": 1000, "raceTime10K": 2100, "raceTimeHalf": 4700, "raceTimeMarathon": 9900}],
                "sleepData.json": [{"calendarDate": "2026-01-02", "sleepStartTimestampGMT": "2026-01-01T14:00:00Z", "sleepEndTimestampGMT": "2026-01-01T22:00:00Z", "sleepTimeSeconds": 27000}],
                "UDSFile_synthetic.json": [{"calendarDate": "2026-01-03", "totalSteps": 0}],
                "MetricsAcuteTrainingLoad_synthetic.json": [{"calendarDate": "2026-01-04", "timestamp": 1767502800000, "dailyTrainingLoadAcute": 9}],
                "TrainingReadinessDTO_synthetic.json": [{"calendarDate": "2026-01-05", "timestamp": "2026-01-05T06:00:00", "score": 50}],
                "MetricsMaxMetData_synthetic.json": [{"calendarDate": "2026-01-06", "updateTimestamp": "2026-01-06T06:00:00", "vo2MaxValue": 60, "sport": "RUNNING"}],
                "TrainingHistory_synthetic.json": [{"calendarDate": "2026-01-07", "timestamp": "2026-01-07T06:00:00", "trainingStatus": "PRODUCTIVE", "sport": "RUNNING"}],
            }
            for name, value in fixtures.items():
                (metrics / name).write_text(json.dumps(value), encoding="utf-8")
            output = root / "output"
            result = run_all(input_root, output)
            self.assertEqual(result["exit_code"], 0)
            expected_fields = {
                "race_prediction_daily": RACE_PREDICTION_FIELDS,
                "sleep_daily": SLEEP_DAILY_FIELDS,
                "uds_daily": UDS_FIELDS,
                "acute_training_load_daily": ACUTE_TRAINING_LOAD_FIELDS,
                "training_readiness_daily": TRAINING_READINESS_FIELDS,
                "vo2max_daily": VO2MAX_FIELDS,
                "training_history_daily": TRAINING_HISTORY_FIELDS,
            }
            for name, fields in expected_fields.items():
                rows = json.loads(
                    (output / "normalized" / f"{name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(set(rows[0]), set(fields))
            hrv_rows = json.loads(
                (output / "normalized" / "hrv_daily.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(hrv_rows, [])
            summary = json.loads(
                (output / "qa" / "daily_metrics_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(summary["health_status"]["status"], "DEFERRED_PENDING_SEMANTICS")
            race_summary = summary["datasets"]["race_prediction_daily"]
            self.assertEqual(race_summary["record_grain"], "source_observation")
            self.assertIsNone(race_summary["daily_projection"]["selection_rule"])


if __name__ == "__main__":
    unittest.main()
