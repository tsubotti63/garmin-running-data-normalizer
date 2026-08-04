from __future__ import annotations

import hashlib
import json
import unittest

from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.performance_metrics import (
    PerformanceMetricsConflictError,
    build_performance_metrics_daily_context,
    collect_lactate_threshold_candidates,
    normalize_endurance_score,
    normalize_hill_score,
)


def _asset(name: str, value: object) -> DiscoveredAsset:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return DiscoveredAsset(
        kind="json",
        source_path=name,
        member_path=None,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
    )


class HillScoreContractTest(unittest.TestCase):
    def test_h01_to_h11_normalization_matrix(self) -> None:
        cases = (
            ("minimal", {"calendarDate": "2026-01-01", "overallScore": 78}, 1, 0),
            ("full", {"calendarDate": "2026-01-02", "overallScore": 84, "strengthScore": 86, "enduranceScore": 82, "hillScoreClassificationId": 2, "hillScoreFeedbackPhraseId": 3}, 1, 0),
            ("nullable", {"calendarDate": "2026-01-03", "overallScore": 80, "strengthScore": None}, 1, 0),
            ("timestamp-date", {"calendarDate": "2026-01-04T12:00:00", "overallScore": 81}, 1, 0),
            ("invalid-date", {"calendarDate": "not-a-date", "overallScore": 81}, 0, 1),
            ("missing-date", {"overallScore": 81}, 0, 1),
            ("missing-overall", {"calendarDate": "2026-01-05"}, 0, 1),
            ("null-overall", {"calendarDate": "2026-01-06", "overallScore": None}, 0, 1),
            ("float-overall", {"calendarDate": "2026-01-07", "overallScore": 1.5}, 0, 1),
            ("unknown-field", {"calendarDate": "2026-01-08", "overallScore": 66, "unknown": "ignored"}, 1, 0),
            ("private-fields", {"calendarDate": "2026-01-09", "overallScore": 70, "deviceId": "private", "userProfilePk": "private", "timestamp": 1}, 1, 0),
        )
        for name, row, accepted, excluded in cases:
            with self.subTest(name=name):
                result = normalize_hill_score([_asset("DI-Connect-Metrics/HillScore_test.json", [row])])
                self.assertEqual(len(result.records), accepted)
                self.assertEqual(result.audit["excluded_record_count"], excluded)
                self.assertTrue(
                    all(set(item) == {"calendar_date", "overall_score", "strength_score", "endurance_score", "classification_id", "feedback_phrase_id"} for item in result.records)
                )

    def test_h12_same_value_duplicates_collapse_without_keep_last(self) -> None:
        rows = [
            {"calendarDate": "2026-02-01", "overallScore": 90, "timestamp": 1},
            {"calendarDate": "2026-02-01", "overallScore": 90, "timestamp": 2},
        ]
        result = normalize_hill_score([_asset("HillScore_duplicate.json", rows)])
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.audit["same_value_duplicate_count"], 1)
        self.assertFalse(result.audit["keep_last"])

    def test_h13_divergent_daily_value_fails_closed(self) -> None:
        rows = [
            {"calendarDate": "2026-02-02", "overallScore": 70},
            {"calendarDate": "2026-02-02", "overallScore": 71},
        ]
        with self.assertRaises(PerformanceMetricsConflictError):
            normalize_hill_score([_asset("HillScore_conflict.json", rows)])

    def test_h14_nonmatching_json_is_not_promoted(self) -> None:
        result = normalize_hill_score(
            [_asset("DI-Connect-Metrics/OtherScore.json", [{"calendarDate": "2026-02-03", "overallScore": 99}])]
        )
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["detected_asset_count"], 0)

    def test_h15_multiple_assets_are_calendar_sorted(self) -> None:
        result = normalize_hill_score(
            [
                _asset("HillScore_later.json", [{"calendarDate": "2026-02-05", "overallScore": 80}]),
                _asset("HillScore_earlier.json", [{"calendarDate": "2026-02-04", "overallScore": 79}]),
            ]
        )
        self.assertEqual(
            [item["calendar_date"] for item in result.records],
            ["2026-02-04", "2026-02-05"],
        )

    def test_h16_epoch_milliseconds_use_utc_daily_label(self) -> None:
        result = normalize_hill_score(
            [_asset("HillScore_epoch.json", [{"calendarDate": 1_767_225_600_000, "overallScore": 79}])]
        )
        self.assertEqual(result.records[0]["calendar_date"], "2026-01-01")


class EnduranceScoreContractTest(unittest.TestCase):
    def test_e01_to_e11_normalization_matrix(self) -> None:
        cases = (
            ("minimal", {"calendarDate": "2026-03-01", "overallScore": 70}, 1, 0),
            ("full", {"calendarDate": "2026-03-02", "overallScore": 71.5, "classification": 7, "feedbackPhrase": 100}, 1, 0),
            ("nullable", {"calendarDate": "2026-03-03", "overallScore": 72, "classification": None}, 1, 0),
            ("timestamp-date", {"calendarDate": "2026-03-04T00:00:00", "overallScore": 73}, 1, 0),
            ("invalid-date", {"calendarDate": "2026-99-99", "overallScore": 73}, 0, 1),
            ("missing-date", {"overallScore": 73}, 0, 1),
            ("missing-overall", {"calendarDate": "2026-03-05"}, 0, 1),
            ("null-overall", {"calendarDate": "2026-03-06", "overallScore": None}, 0, 1),
            ("boolean-overall", {"calendarDate": "2026-03-07", "overallScore": True}, 0, 1),
            ("contributors", {"calendarDate": "2026-03-08", "overallScore": 75, "enduranceScoreContributor": [{"group": 0}]}, 1, 0),
            ("private-fields", {"calendarDate": "2026-03-09", "overallScore": 76, "deviceId": "private", "userProfilePK": "private", "primaryTrainingDevice": True}, 1, 0),
        )
        for name, row, accepted, excluded in cases:
            with self.subTest(name=name):
                result = normalize_endurance_score([_asset("DI-Connect-Metrics/EnduranceScore_test.json", [row])])
                self.assertEqual(len(result.records), accepted)
                self.assertEqual(result.audit["excluded_record_count"], excluded)
                self.assertTrue(
                    all(set(item) == {"calendar_date", "overall_score", "classification", "feedback_phrase"} for item in result.records)
                )

    def test_e12_same_value_duplicates_collapse_without_keep_last(self) -> None:
        rows = [
            {"calendarDate": "2026-03-10", "overallScore": 80, "timestamp": 1},
            {"calendarDate": "2026-03-10", "overallScore": 80, "timestamp": 2},
        ]
        result = normalize_endurance_score([_asset("EnduranceScore_duplicate.json", rows)])
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.audit["same_value_duplicate_count"], 1)

    def test_e13_divergent_daily_value_fails_closed(self) -> None:
        rows = [
            {"calendarDate": "2026-03-11", "overallScore": 80},
            {"calendarDate": "2026-03-11", "overallScore": 81},
        ]
        with self.assertRaises(PerformanceMetricsConflictError):
            normalize_endurance_score([_asset("EnduranceScore_conflict.json", rows)])

    def test_e14_nonmatching_json_is_not_promoted(self) -> None:
        result = normalize_endurance_score(
            [_asset("DI-Connect-Metrics/OtherScore.json", [{"calendarDate": "2026-03-12", "overallScore": 99}])]
        )
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["detected_asset_count"], 0)

    def test_e15_multiple_assets_are_calendar_sorted(self) -> None:
        result = normalize_endurance_score(
            [
                _asset("EnduranceScore_later.json", [{"calendarDate": "2026-03-14", "overallScore": 80}]),
                _asset("EnduranceScore_earlier.json", [{"calendarDate": "2026-03-13", "overallScore": 79}]),
            ]
        )
        self.assertEqual(
            [item["calendar_date"] for item in result.records],
            ["2026-03-13", "2026-03-14"],
        )

    def test_e16_epoch_milliseconds_use_utc_daily_label(self) -> None:
        result = normalize_endurance_score(
            [_asset("EnduranceScore_epoch.json", [{"calendarDate": 1_767_225_600_000, "overallScore": 79}])]
        )
        self.assertEqual(result.records[0]["calendar_date"], "2026-01-01")


class LactateThresholdCandidateTest(unittest.TestCase):
    def _candidate_audit(self) -> dict:
        return collect_lactate_threshold_candidates(
            [
                _asset(
                    "DI-Connect-Wellness/synthetic_userBioMetrics.json",
                    [
                        {"metaData": {"calendarDate": "2026-07-12T00:00:00", "sequence": 2, "userProfilePK": "private"}, "lactateThresholdSpeed": 0.386, "functionalThresholdPower": 290},
                        {"metaData": {"calendarDate": "2026-07-11", "sequence": 1}, "lactateThresholdSpeed": None},
                        {"metaData": {"calendarDate": "bad", "sequence": 3}, "lactateThresholdSpeed": 0.4},
                    ],
                ),
                _asset("DI-Connect-Wellness/synthetic_bioMetrics_latest.json", [{"lactateThresholdSpeed": 0.395, "lactateThresholdHeartRate": 164, "functionalThresholdPower": 151}]),
                _asset("DI-Connect-Wellness/synthetic_userBioMetricProfileData.json", [{"lactateThresholdHeartRate": 165, "functionalThresholdPower": 290, "weight": 60}]),
                _asset("DI-Connect-Wellness/synthetic_heartRateZones.json", [{"trainingMethod": "LACTATE_THRESHOLD", "lactateThresholdHeartRateUsed": 163}]),
            ]
        )

    def test_l01_to_l15_candidate_boundary(self) -> None:
        audit = self._candidate_audit()
        checks = (
            ("status", audit["status"] == "REVIEW_REQUIRED_STABLE_PROMOTION_BLOCKED"),
            ("promotion", audit["public_promotion"] is False),
            ("stable-key", audit["machine_stable_key_status"] == "PRODUCT_DECISION_REQUIRED"),
            ("families", set(audit["observation_families"]) == {"history", "latest_snapshot", "profile_state", "derived_evidence"}),
            ("history-date", any(item["observation_family"] == "history" and item["observation_timestamp"] == "2026-07-12" for item in audit["candidates"])),
            ("latest-null-date", any(item["observation_family"] == "latest_snapshot" and item["observation_timestamp"] is None for item in audit["candidates"])),
            ("profile", any(item["observation_family"] == "profile_state" and item["lactate_threshold_heart_rate"] == 165 for item in audit["candidates"])),
            ("derived", any(item["observation_family"] == "derived_evidence" and item["lactate_threshold_type"] == "LACTATE_THRESHOLD" for item in audit["candidates"])),
            ("invalid-history", audit["review_condition_counts"]["history_timestamp_missing_or_invalid"] == 1),
            ("speed-unit", audit["units"]["lactate_threshold_speed"] == "UNCONFIRMED"),
            ("heart-unit", audit["units"]["lactate_threshold_heart_rate"] == "UNCONFIRMED"),
            ("power-unit", audit["units"]["functional_threshold_power"] == "UNCONFIRMED"),
            ("timezone", audit["timezone"] == "UNCONFIRMED"),
            ("no-private", all(set(item) == {"observation_timestamp", "observation_family", "lactate_threshold_speed", "lactate_threshold_heart_rate", "functional_threshold_power", "lactate_threshold_type"} for item in audit["candidates"])),
            ("no-latest-wins", audit["latest_wins"] is False and audit["inference_performed"] is False),
        )
        for name, passed in checks:
            with self.subTest(name=name):
                self.assertTrue(passed)

    def test_l16_sequence_orders_but_is_not_exposed_or_promoted(self) -> None:
        audit = collect_lactate_threshold_candidates(
            [
                _asset(
                    "synthetic_userBioMetrics.json",
                    [
                        {"metaData": {"calendarDate": "2026-07-10", "sequence": 2}, "lactateThresholdSpeed": 0.31},
                        {"metaData": {"calendarDate": "2026-07-10", "sequence": 1}, "lactateThresholdSpeed": 0.30},
                    ],
                )
            ]
        )
        self.assertEqual([row["lactate_threshold_speed"] for row in audit["candidates"]], [0.30, 0.31])
        self.assertTrue(all("sequence" not in row for row in audit["candidates"]))

    def test_l17_power_conflict_is_a_review_condition(self) -> None:
        audit = collect_lactate_threshold_candidates(
            [
                _asset(
                    "synthetic_bioMetrics_latest.json",
                    [{"functionalThresholdPower": 200}, {"functionalThresholdPower": 201}],
                )
            ]
        )
        self.assertEqual(
            audit["review_condition_counts"]["functional_threshold_power_conflict"],
            1,
        )

    def test_daily_context_uses_explicit_prefixes(self) -> None:
        rows = build_performance_metrics_daily_context(
            [{"calendar_date": "2026-01-01", "overall_score": 80}],
            [{"calendar_date": "2026-01-01", "overall_score": 70}],
        )
        self.assertEqual(rows[0]["hill_overall_score"], 80)
        self.assertEqual(rows[0]["endurance_overall_score"], 70)


if __name__ == "__main__":
    unittest.main()
