from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.daily_metrics import (
    DailyMetricConflictError,
    finalize_daily,
)
from garmin_running_data_normalizer.normalizers.sleep import normalize_sleep_daily_assets
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot.merge import _merge_dataset


def asset(name: str, rows: list[dict]) -> DiscoveredAsset:
    data = json.dumps(rows, sort_keys=True).encode()
    return DiscoveredAsset("json", name, None, len(data), hashlib.sha256(data).hexdigest(), data)


def sleep_row(**changes: object) -> dict:
    row = {
        "calendarDate": "2026-01-02",
        "sleepStartTimestampGMT": "2026-01-01T14:00:00Z",
        "sleepEndTimestampGMT": "2026-01-01T22:00:00Z",
        "sleepTimeSeconds": 27000,
        "deepSleepSeconds": 3600,
        "lightSleepSeconds": 18000,
        "remSleepSeconds": 5400,
        "awakeSleepSeconds": None,
        "sleepScores": {"overall": {"value": 80}},
    }
    row.update(changes)
    return row


class SleepDuplicatePolicyTest(unittest.TestCase):
    def test_single_row_and_two_three_exact_duplicates(self) -> None:
        for count in (1, 2, 3):
            with self.subTest(count=count):
                result = normalize_sleep_daily_assets([asset("sleepData.json", [sleep_row()] * count)])
                self.assertEqual(len(result.records), 1)
                self.assertEqual(result.audit.get("duplicate_group_count", 0), int(count > 1))
                self.assertEqual(result.audit.get("duplicate_row_count", 0), max(count - 1, 0))
                self.assertEqual(result.audit.get("review_required_count", 0), 0)

    def test_filename_and_input_order_are_not_equality_fields(self) -> None:
        first = sleep_row()
        second = {
            **first,
            "sourceFileName": "another-export.json",
            "sleepWindowConfirmationType": "DIFFERENT_SOURCE_METADATA",
            "retro": True,
        }
        result = normalize_sleep_daily_assets([asset("a_sleepData.json", [first]), asset("b_sleepData.json", [second])])
        self.assertEqual(len(result.records), 1)
        permuted = normalize_sleep_daily_assets([asset("a_sleepData.json", [second, first])])
        self.assertEqual(permuted.records, result.records)
        self.assertEqual(permuted.audit["dedupe_method"], "exact_canonical_duplicate_collapsed")

    def test_divergent_score_stage_null_value_and_absent_null_fail_closed(self) -> None:
        cases = (
            {"sleepScores": {"overall": {"value": 81}}},
            {"deepSleepSeconds": 3660},
            {"sleepScores": None},
            {"sleepScores": None},
        )
        for index, change in enumerate(cases):
            with self.subTest(index=index):
                base = sleep_row()
                if index == 3:
                    other = {key: value for key, value in base.items() if key != "sleepScores"}
                else:
                    other = {**base, **change}
                with self.assertRaises(DailyMetricConflictError):
                    normalize_sleep_daily_assets([asset("sleepData.json", [base, other])])

    def test_zero_is_not_missing_and_missing_endpoints_are_not_inferred(self) -> None:
        zero = sleep_row(deepSleepSeconds=0)
        missing = {key: value for key, value in sleep_row().items() if key != "deepSleepSeconds"}
        with self.assertRaises(DailyMetricConflictError):
            normalize_sleep_daily_assets([asset("sleepData.json", [zero, missing])])
        missing_endpoints = sleep_row(sleepStartTimestampGMT=None, sleepEndTimestampGMT=None)
        result = normalize_sleep_daily_assets([asset("sleepData.json", [missing_endpoints])])
        self.assertEqual(result.records[0]["sleep_normalization_status"], "needs_review")
        self.assertFalse(result.records[0]["sleep_source_available_for_analysis_flag"])

    def test_provenance_conflict_is_review_required_without_a_winner(self) -> None:
        row = {"day": "2026-01-02", "value": 1, "_provenance": "authoritative-a"}
        review = {"day": "2026-01-02", "value": None, "status": "needs_review"}
        result = finalize_daily(
            dataset="synthetic_sleep_daily",
            key_fields=("day",),
            selected_assets=[],
            source_record_count=2,
            accepted=[row, {**row, "_provenance": "authoritative-b"}],
            excluded_reasons=Counter(),
            duplicate_review_factory=lambda _key, _rows: review,
            provenance_conflict_predicate=lambda rows: len({r["_provenance"] for r in rows}) > 1,
            signature_factory=lambda value: json.dumps({"day": value["day"], "value": value["value"]}, sort_keys=True),
            strip_internal_fields=lambda value: {"day": value["day"], "value": value["value"]},
            dedupe_exact_duplicates=True,
        )
        self.assertEqual(result.records, [review])
        self.assertEqual(result.audit["dedupe_method"], "review_required")
        self.assertEqual(result.audit["review_required_count"], 1)

    def test_replay_and_existing_review_case_remain_deterministic(self) -> None:
        row = sleep_row()
        result = normalize_sleep_daily_assets([asset("sleepData.json", [row, row, row, row])])
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.audit["duplicate_row_count"], 3)
        self.assertEqual(result.audit["same_value_duplicate_count"], 3)

    def test_existing_review_row_is_not_promoted_by_dedupe(self) -> None:
        row = {"day": "2026-01-02", "value": None, "status": "needs_review"}
        result = finalize_daily(
            dataset="synthetic_sleep_daily",
            key_fields=("day",),
            selected_assets=[],
            source_record_count=2,
            accepted=[row, dict(row)],
            excluded_reasons=Counter(),
            signature_factory=lambda value: json.dumps(value, sort_keys=True),
            strip_internal_fields=lambda value: dict(value),
            dedupe_exact_duplicates=True,
        )
        self.assertEqual(result.records, [row])
        self.assertEqual(result.records[0]["status"], "needs_review")
        self.assertEqual(result.audit["review_required_count"], 0)

    @staticmethod
    def _snapshot_observation(
        snapshot_id: str,
        logical_order: int,
        record: dict[str, object],
    ) -> dict[str, object]:
        return {
            "snapshot_id": snapshot_id,
            "logical_order": logical_order,
            "export_observed_at": f"2026-01-0{logical_order}T12:00:00+09:00",
            "source_relative_path": f"{snapshot_id}/sleepData.json",
            "source_record_index": 0,
            "source_object_sha256": hashlib.sha256(snapshot_id.encode()).hexdigest(),
            "raw_key": ("2026-01-02",),
            "record": record,
        }

    def test_snapshot_exact_omission_reappearance_and_permutation_are_deterministic(self) -> None:
        record = {"calendarDate": "2026-01-02", "sleepTimeSeconds": 27000}
        observations = [
            self._snapshot_observation("s1", 1, record),
            self._snapshot_observation("s2", 2, record),
            self._snapshot_observation("s4", 4, record),
        ]
        first = _merge_dataset("sleep_daily", observations, 4)
        second = _merge_dataset("sleep_daily", list(reversed(observations)), 4)
        self.assertFalse(first[4])
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[0][0]["presence_pattern"], "1101")
        self.assertEqual(first[0][0]["raw_record"], record)
        self.assertEqual(first[5]["presence_pattern_counts"], second[5]["presence_pattern_counts"])

    def test_snapshot_divergent_value_fails_closed(self) -> None:
        observations = [
            self._snapshot_observation("s1", 1, {"calendarDate": "2026-01-02", "sleepTimeSeconds": 27000}),
            self._snapshot_observation("s2", 2, {"calendarDate": "2026-01-02", "sleepTimeSeconds": 27060}),
        ]
        result = _merge_dataset("sleep_daily", observations, 4)
        self.assertTrue(any(item["conflict_type"] == "same_stable_key_different_public_value" for item in result[4]))
        self.assertEqual(result[0], [])

    def test_run_all_exact_sleep_duplicates_do_not_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_root = root / "input"
            shutil.copytree(Path("examples/synthetic/garmin_export"), input_root)
            metrics = input_root / "DI_CONNECT" / "DI-Connect-Metrics"
            metrics.mkdir(parents=True, exist_ok=True)
            row = sleep_row()
            (metrics / "sleepData.json").write_text(json.dumps([row, row]), encoding="utf-8")
            output = root / "output"
            result = run_all(input_root, output)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["family_results"]["sleep"]["status"], "PROCESSED")
            normalized = json.loads((output / "normalized/sleep_daily.json").read_text(encoding="utf-8"))
            audit = json.loads((output / "audit/sleep_daily.json").read_text(encoding="utf-8"))
            self.assertEqual(len(normalized), 1)
            self.assertEqual(audit["review_required_count"], 0)
            self.assertEqual(audit["dedupe_method"], "exact_canonical_duplicate_collapsed")


if __name__ == "__main__":
    unittest.main()
