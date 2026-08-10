from __future__ import annotations

import hashlib
import itertools
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.performance_metrics import (
    PerformanceMetricsConflictError,
    normalize_endurance_score,
)
from garmin_running_data_normalizer.normalizers.uds import normalize_uds
from garmin_running_data_normalizer.normalizers.daily_metrics import DailyMetricConflictError
from garmin_running_data_normalizer.snapshot.merge import _merge_dataset
from garmin_running_data_normalizer.run_all import run_all


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


def _uds_row(date: str, steps: int) -> dict[str, object]:
    return {
        "calendarDate": date,
        "totalSteps": steps,
        "totalDistanceMeters": steps * 2,
        "activeKilocalories": steps + 10,
        "bmrKilocalories": 1500,
    }


def _snapshot_observations(dataset: str, values: list[int]) -> list[dict[str, object]]:
    rows = []
    for order, value in enumerate(values, start=1):
        record = (
            {"calendarDate": "2030-01-01", "overallScore": value}
            if dataset == "endurance_score_daily"
            else _uds_row("2030-01-01", value)
        )
        rows.append(
            {
                "dataset": dataset,
                "record": record,
                "raw_key": ("2030-01-01",),
                "snapshot_id": f"private-{order}",
                "logical_order": order,
                "export_observed_at": f"2030-01-0{order}T00:00:00Z",
                "source_relative_path": "synthetic.json",
                "source_record_index": 0,
                "source_object_sha256": f"object-{order}",
            }
        )
    return rows


class PreserveObservedVariantsTest(unittest.TestCase):
    def test_endurance_v2_preserves_values_without_a_winner(self) -> None:
        rows = [
            {"calendarDate": "2030-01-01", "overallScore": 70},
            {"calendarDate": "2030-01-01", "overallScore": 71},
        ]
        with self.assertRaises(PerformanceMetricsConflictError):
            normalize_endurance_score([_asset("EnduranceScore_same_export.json", rows)])
        result = normalize_endurance_score(
            [_asset("EnduranceScore_snapshot_variants.json", rows)],
            preserve_observed_variants=True,
        )
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["multi_variant_key_count"], 1)
        self.assertEqual(result.audit["observed_variant_count"], 2)
        self.assertEqual(result.audit["canonicalization_unresolved_count"], 1)
        self.assertFalse(result.audit["automatic_winner"])
        self.assertEqual(
            {item["observed_value"]["overall_score"] for item in result.audit["observed_variants"]},
            {70, 71},
        )

    def test_uds_v2_preserves_values_and_exact_repeats(self) -> None:
        rows = [_uds_row("2030-01-01", 100), _uds_row("2030-01-01", 100), _uds_row("2030-01-01", 110)]
        result = normalize_uds(
            [_asset("UDSFile_snapshot_variants.json", rows)],
            preserve_observed_variants=True,
        )
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["multi_variant_key_count"], 1)
        self.assertEqual(result.audit["observed_variant_count"], 2)
        self.assertEqual(result.audit["exact_repeat_count"], 1)
        self.assertFalse(result.audit["automatic_winner"])

    def test_uds_same_export_divergence_remains_malformed(self) -> None:
        rows = [_uds_row("2030-01-01", 100), _uds_row("2030-01-01", 110)]
        with self.assertRaises(DailyMetricConflictError):
            normalize_uds([_asset("UDSFile_same_export.json", rows)])

    def test_single_snapshot_and_reappearing_key_have_no_winner(self) -> None:
        single = _merge_dataset(
            "endurance_score_daily",
            _snapshot_observations("endurance_score_daily", [70]),
            1,
        )
        self.assertEqual(single[0][0]["raw_record"]["overallScore"], 70)
        self.assertEqual(single[5]["multi_variant_key_count"], 0)

        rows = _snapshot_observations("endurance_score_daily", [70, 71, 70])
        merged = _merge_dataset("endurance_score_daily", rows, 3)
        self.assertEqual(merged[0], [])
        self.assertEqual(merged[5]["multi_variant_key_count"], 1)
        self.assertEqual(merged[5]["exact_repeat_count"], 1)

    def test_missing_null_and_zero_are_observed_not_invented(self) -> None:
        null_row = _uds_row("2030-01-01", 100)
        null_row["totalSteps"] = None
        missing_row = _uds_row("2030-01-01", 100)
        del missing_row["totalSteps"]
        zero_row = _uds_row("2030-01-01", 0)
        result = normalize_uds(
            [_asset("UDSFile_presence_variants.json", [null_row, missing_row, zero_row])],
            preserve_observed_variants=True,
        )
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["multi_variant_key_count"], 1)
        self.assertEqual(result.audit["canonicalization_unresolved_count"], 1)
        self.assertFalse(result.audit["automatic_winner"])
        observed = result.audit["observed_variants"]
        # The UDS parser gives absent and explicit null the same public null
        # projection; the non-null zero remains a distinct observed variant.
        self.assertEqual(len(observed), 2)
        self.assertEqual(
            {item["observed_value"].get("steps") for item in observed},
            {None, 0},
        )

    def test_malformed_key_is_excluded_and_never_promoted(self) -> None:
        result = normalize_uds(
            [_asset("UDSFile_malformed.json", [{"totalSteps": 100}])],
            preserve_observed_variants=True,
        )
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["malformed_count"], 1)
        self.assertEqual(result.audit["canonicalization_unresolved_count"], 0)

    def test_four_snapshot_24_orders_have_identical_variant_semantics(self) -> None:
        for dataset, values in (
            ("endurance_score_daily", [70, 71, 72, 70]),
            ("uds_daily", [100, 100, 110, 120]),
        ):
            digests = set()
            for order in itertools.permutations(range(4)):
                observations = [_snapshot_observations(dataset, values)[index] for index in order]
                canonical, _, _, _, conflicts, summary = _merge_dataset(dataset, observations, 4)
                self.assertEqual(canonical, [])
                self.assertEqual(conflicts, [])
                semantic = {
                    "variants": summary["observed_variants"],
                    "multi_variant_key_count": summary["multi_variant_key_count"],
                    "observed_variant_count": summary["observed_variant_count"],
                    "exact_repeat_count": summary["exact_repeat_count"],
                    "canonicalization_unresolved_count": summary["canonicalization_unresolved_count"],
                }
                digests.add(hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest())
            self.assertEqual(len(digests), 1, dataset)

    def test_variant_lineage_is_snapshot_order_safe_and_public_safe(self) -> None:
        _, _, _, _, _, summary = _merge_dataset(
            "endurance_score_daily", _snapshot_observations("endurance_score_daily", [70, 71, 72, 73]), 4
        )
        for item in summary["observed_variants"]:
            self.assertEqual(item["snapshot_orders"], sorted(item["snapshot_orders"]))
            self.assertNotIn("snapshot_id", item)
            self.assertNotIn("source_relative_path", item)
            self.assertNotIn("source_object_sha256", item)
            self.assertNotIn("deviceId", item["observed_value"])

    def test_snapshot_run_all_is_non_fatal_and_handoff_explains_variants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_root = root / "input"
            shutil.copytree(Path("examples/synthetic/garmin_export"), input_root)
            context = {
                "lineage": {"snapshot_count": 4, "canonical_build_sha256": "synthetic-build"},
                "coverage": {"snapshot_count": 4},
                "merge_summary": {
                    "snapshot_count": 4,
                    "datasets": {
                        "endurance_score_daily": {
                            "canonical_record_count": 2,
                            "single_variant_key_count": 2,
                            "multi_variant_key_count": 1,
                            "observed_variant_count": 2,
                            "exact_repeat_count": 1,
                            "canonicalization_unresolved_count": 1,
                            "observed_variants": [
                                {
                                    "canonical_key": "synthetic-endurance",
                                    "variant_fingerprint": "a",
                                    "observed_value": {"calendarDate": "2030-01-01", "overallScore": 70},
                                    "observation_count": 1,
                                    "snapshot_orders": [1],
                                    "variant_status": "observed_variant",
                                    "canonical_status": "unresolved_multiple_observed_values",
                                },
                                {
                                    "canonical_key": "synthetic-endurance",
                                    "variant_fingerprint": "b",
                                    "observed_value": {"calendarDate": "2030-01-01", "overallScore": 71},
                                    "observation_count": 1,
                                    "snapshot_orders": [2],
                                    "variant_status": "observed_variant",
                                    "canonical_status": "unresolved_multiple_observed_values",
                                },
                            ],
                        },
                        "uds_daily": {
                            "canonical_record_count": 2,
                            "single_variant_key_count": 2,
                            "multi_variant_key_count": 1,
                            "observed_variant_count": 2,
                            "exact_repeat_count": 0,
                            "canonicalization_unresolved_count": 1,
                            "observed_variants": [],
                        },
                    },
                },
            }
            output = root / "output"
            result = run_all(input_root, output, snapshot_context=context)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
            audit = json.loads((output / "audit/endurance_score_daily.json").read_text())
            self.assertEqual(audit["canonicalization_unresolved_count"], 1)
            self.assertFalse(audit["automatic_winner"])
            self.assertIn("preserved observed variants", (output / "START_HERE.md").read_text())
