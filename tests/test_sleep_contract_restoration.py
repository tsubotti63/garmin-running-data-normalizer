from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.daily_metrics import (
    DailyMetricConflictError,
    finalize_daily,
)
from garmin_running_data_normalizer.normalizers.sleep import (
    SLEEP_DAILY_FIELDS,
    normalize_sleep,
    normalize_sleep_daily_assets,
)
from garmin_running_data_normalizer.output_experience import DATASET_FIELDS, _field_descriptor
from garmin_running_data_normalizer.run_all import DATASET_TABLE


def asset(name: str, rows: list[dict]) -> DiscoveredAsset:
    data = json.dumps(rows, sort_keys=True).encode()
    return DiscoveredAsset(
        "json", name, None, len(data), hashlib.sha256(data).hexdigest(), data
    )


def sleep_row(**changes: object) -> dict:
    row = {
        "calendarDate": "2026-01-02",
        "sleepStartTimestampGMT": "2026-01-01T14:00:00Z",
        "sleepEndTimestampGMT": "2026-01-01T22:00:00Z",
        "deepSleepSeconds": 3_600,
        "lightSleepSeconds": 18_000,
        "remSleepSeconds": 5_400,
        "awakeSleepSeconds": 3_600,
        "sleepScores": {"overall": {"value": 80}},
    }
    row.update(changes)
    return row


class SleepContractRestorationTest(unittest.TestCase):
    def test_issue_a_excluded_only_is_not_review_required(self) -> None:
        result = finalize_daily(
            dataset="synthetic_sleep_daily",
            key_fields=("day",),
            selected_assets=[],
            source_record_count=2,
            accepted=[{"day": "2026-01-02", "value": 1}],
            excluded_reasons=Counter({"missing_day": 1}),
            strip_internal_fields=lambda row: dict(row),
        )
        self.assertEqual(result.audit["excluded_record_count"], 1)
        self.assertEqual(result.audit.get("review_required_count", 0), 0)
        self.assertEqual(result.audit["review_item_count"], 0)
        self.assertEqual(result.audit["status"], "PASS")

    def test_issue_a_review_only_and_mixed_are_separate(self) -> None:
        def run(excluded: Counter[str]) -> dict:
            result = finalize_daily(
                dataset="synthetic_sleep_daily",
                key_fields=("day",),
                selected_assets=[],
                source_record_count=2,
                accepted=[
                    {"day": "2026-01-02", "value": 1},
                    {"day": "2026-01-02", "value": 2},
                ],
                excluded_reasons=excluded,
                review_on_any_duplicate=True,
                duplicate_review_factory=lambda key, _rows: {"day": key, "value": None},
                signature_factory=lambda row: json.dumps(row, sort_keys=True),
                strip_internal_fields=lambda row: dict(row),
            )
            return result.audit

        review = run(Counter())
        self.assertEqual(review["review_required_count"], 1)
        self.assertEqual(review["review_item_count"], 1)
        self.assertEqual(review["excluded_record_count"], 0)
        self.assertEqual(review["status"], "PASS_WITH_REVIEW_ITEMS")
        mixed = run(Counter({"missing_day": 2}))
        self.assertEqual(mixed["review_required_count"], 1)
        self.assertEqual(mixed["review_item_count"], 1)
        self.assertEqual(mixed["excluded_record_count"], 2)

    def test_issue_a_neither_is_clean(self) -> None:
        result = finalize_daily(
            dataset="synthetic_sleep_daily",
            key_fields=("day",),
            selected_assets=[],
            source_record_count=1,
            accepted=[{"day": "2026-01-02", "value": 1}],
            excluded_reasons=Counter(),
            strip_internal_fields=lambda row: dict(row),
        )
        self.assertEqual(result.audit["status"], "PASS")
        self.assertEqual(result.audit.get("review_required_count", 0), 0)

    def _duration(self, **changes: object) -> float | None:
        result = normalize_sleep_daily_assets([asset("sleepData.json", [sleep_row(**changes)])])
        return result.records[0]["sleep_duration_minutes_ex_awake"]

    def test_issue_b_stage_matrix_and_precedence(self) -> None:
        self.assertEqual(self._duration(deepSleepSeconds=3_600, lightSleepSeconds=7_200, remSleepSeconds=1_800), 210.0)
        self.assertEqual(self._duration(deepSleepSeconds=3_600, lightSleepSeconds=None, remSleepSeconds=None), 60.0)
        self.assertEqual(self._duration(deepSleepSeconds=None, lightSleepSeconds=7_200, remSleepSeconds=None), 120.0)
        self.assertEqual(self._duration(deepSleepSeconds=None, lightSleepSeconds=None, remSleepSeconds=1_800), 30.0)
        self.assertEqual(self._duration(deepSleepSeconds=3_600, lightSleepSeconds=7_200, remSleepSeconds=None), 180.0)
        self.assertEqual(self._duration(deepSleepSeconds=3_600, lightSleepSeconds=None, remSleepSeconds=1_800), 90.0)
        self.assertEqual(self._duration(deepSleepSeconds=None, lightSleepSeconds=7_200, remSleepSeconds=1_800), 150.0)
        self.assertEqual(self._duration(deepSleepSeconds=3_600, lightSleepSeconds=None, remSleepSeconds=None, sleepTimeSeconds=99_999), 60.0)
        self.assertEqual(self._duration(deepSleepSeconds=None, lightSleepSeconds=None, remSleepSeconds=None, sleepTimeSeconds=7_200), 120.0)
        self.assertIsNone(self._duration(deepSleepSeconds=None, lightSleepSeconds=None, remSleepSeconds=None))

    def test_issue_b_awake_and_window_are_never_used(self) -> None:
        value = self._duration(
            deepSleepSeconds=3_600,
            lightSleepSeconds=3_600,
            remSleepSeconds=None,
            awakeSleepSeconds=36_000,
        )
        self.assertEqual(value, 120.0)

    def test_issue_b_zero_is_observed_and_not_missing(self) -> None:
        self.assertEqual(self._duration(deepSleepSeconds=0, lightSleepSeconds=None, remSleepSeconds=None), 0.0)
        self.assertEqual(self._duration(deepSleepSeconds=0, lightSleepSeconds=3_600, remSleepSeconds=None), 60.0)
        zero = sleep_row(deepSleepSeconds=0, lightSleepSeconds=None, remSleepSeconds=None)
        missing = {key: value for key, value in zero.items() if key != "deepSleepSeconds"}
        with self.assertRaises(DailyMetricConflictError):
            normalize_sleep_daily_assets([asset("sleepData.json", [zero, missing])])

    def test_issue_b_direct_alias_equal_and_conflicting(self) -> None:
        equal = sleep_row(
            deepSleepSeconds=None,
            lightSleepSeconds=None,
            remSleepSeconds=None,
            sleepTimeSeconds=7_200,
            totalSleepSeconds=7_200,
            durationInSeconds=7_200,
            sleepDuration=7_200,
        )
        result = normalize_sleep_daily_assets([asset("sleepData.json", [equal])])
        self.assertEqual(result.records[0]["sleep_duration_minutes_ex_awake"], 120.0)
        conflict = dict(equal, durationInSeconds=7_201)
        with self.assertRaises(DailyMetricConflictError):
            normalize_sleep_daily_assets([asset("sleepData.json", [conflict])])

    def test_issue_b_alias_presence_is_duplicate_sensitive(self) -> None:
        base = sleep_row(
            deepSleepSeconds=None,
            lightSleepSeconds=None,
            remSleepSeconds=None,
        )
        for alias in ("sleepTimeSeconds", "totalSleepSeconds", "durationInSeconds", "sleepDuration"):
            with self.subTest(alias=alias):
                absent = {key: value for key, value in base.items() if key != alias}
                explicit_null = dict(absent, **{alias: None})
                with self.assertRaises(DailyMetricConflictError):
                    normalize_sleep_daily_assets([asset("sleepData.json", [absent, explicit_null])])
                equal = dict(explicit_null, **{alias: 7_200})
                duplicate = normalize_sleep_daily_assets([asset("sleepData.json", [equal, equal])])
                self.assertEqual(duplicate.audit["review_required_count"], 0)

    def test_issue_b_nonfinite_values_are_not_numeric_evidence(self) -> None:
        self.assertIsNone(
            self._duration(
                deepSleepSeconds="NaN",
                lightSleepSeconds="Infinity",
                remSleepSeconds=None,
                sleepTimeSeconds="NaN",
            )
        )

    def test_public_helper_and_run_all_producer_have_same_contract(self) -> None:
        row = sleep_row(
            deepSleepSeconds=3_600,
            lightSleepSeconds=7_200,
            remSleepSeconds=None,
            sleepTimeSeconds=99_999,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic_sleepData.json").write_text(json.dumps([row]), encoding="utf-8")
            helper = normalize_sleep(str(root))[0]
        producer = normalize_sleep_daily_assets([asset("sleepData.json", [row])]).records[0]
        self.assertEqual(helper["sleep_duration_minutes_ex_awake"], producer["sleep_duration_minutes_ex_awake"])

    def test_schema_and_dataset_invariants_are_unchanged(self) -> None:
        self.assertEqual(len(DATASET_TABLE), 17)
        self.assertEqual(sum(len(fields) for fields in DATASET_FIELDS.values()), 212)
        self.assertEqual(SLEEP_DAILY_FIELDS[0], "sleep_day")
        descriptor = _field_descriptor("sleep_daily", "sleep_duration_minutes_ex_awake")
        self.assertEqual(descriptor["origin"], "derived")
        self.assertEqual(descriptor["logical_type"], "number")
        self.assertTrue(descriptor["nullable"])


if __name__ == "__main__":
    unittest.main()
