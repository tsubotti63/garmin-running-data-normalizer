from __future__ import annotations

import hashlib
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.performance_metrics import (
    normalize_endurance_score,
)
from garmin_running_data_normalizer.normalizers.uds import normalize_uds
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from garmin_running_data_normalizer.snapshot.merge import _merge_dataset
from tests.test_snapshot_lifecycle import _activity, _write_snapshot


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


class OneExportDisagreementTest(unittest.TestCase):
    """Within one Export, values that disagree are left empty and kept in the audit."""

    def test_endurance_values_that_disagree_have_no_winner(self) -> None:
        rows = [
            {"calendarDate": "2030-01-01", "overallScore": 70},
            {"calendarDate": "2030-01-01", "overallScore": 71},
        ]
        result = normalize_endurance_score([_asset("EnduranceScore_same_export.json", rows)])
        self.assertEqual(len(result.records), 1)
        self.assertIsNone(result.records[0]["overall_score"])
        self.assertEqual(result.records[0]["disagreeing_fields"], ["overall_score"])
        self.assertEqual(
            [item["value"] for item in result.audit["disagreements"][0]["fields"][0]["values"]],
            [70, 71],
        )

    def test_uds_values_that_disagree_are_empty_and_agreeing_values_stay(self) -> None:
        rows = [_uds_row("2030-01-01", 100), _uds_row("2030-01-01", 100), _uds_row("2030-01-01", 110)]
        result = normalize_uds([_asset("UDSFile_same_export.json", rows)])
        [row] = result.records
        self.assertEqual(
            row["disagreeing_fields"], ["steps", "distance_meters", "active_calories"]
        )
        self.assertIsNone(row["steps"])
        self.assertEqual(row["bmr_calories"], 1500)
        self.assertEqual(result.audit["disagreement_key_count"], 1)
        self.assertEqual(result.audit["same_value_duplicate_count"], 1)
        self.assertEqual(
            result.audit["disagreements"][0]["fields"][0],
            {
                "field": "steps",
                "values": [
                    {"value": 100, "observation_count": 2},
                    {"value": 110, "observation_count": 1},
                ],
            },
        )

    def test_missing_and_null_are_absent_and_zero_is_a_value(self) -> None:
        null_row = _uds_row("2030-01-01", 100)
        null_row["totalSteps"] = None
        missing_row = _uds_row("2030-01-01", 100)
        del missing_row["totalSteps"]
        zero_row = _uds_row("2030-01-01", 0)
        result = normalize_uds(
            [_asset("UDSFile_presence.json", [null_row, missing_row, zero_row])]
        )
        [row] = result.records
        # Only one observation has a step count, so it is used; the other two
        # observations have none and are counted.
        self.assertEqual(row["steps"], 0)
        self.assertEqual(result.audit["absent_value_counts"]["steps"], 2)
        self.assertEqual(row["disagreeing_fields"], ["distance_meters", "active_calories"])
        self.assertIsNone(row["distance_meters"])

    def test_presence_flags_are_true_when_any_observation_has_the_group(self) -> None:
        with_battery = _uds_row("2030-01-01", 100)
        with_battery["bodyBattery"] = {"chargedValue": 40}
        without_battery = _uds_row("2030-01-01", 100)
        result = normalize_uds(
            [_asset("UDSFile_presence_flags.json", [with_battery, without_battery])]
        )
        [row] = result.records
        self.assertTrue(row["raw_has_body_battery"])
        self.assertEqual(row["bb_charged_value"], 40)
        self.assertEqual(row["disagreeing_fields"], [])
        self.assertEqual(result.audit["absent_value_counts"], {"bb_charged_value": 1})

    def test_malformed_key_is_excluded_and_never_promoted(self) -> None:
        result = normalize_uds([_asset("UDSFile_malformed.json", [{"totalSteps": 100}])])
        self.assertEqual(result.records, [])
        self.assertEqual(result.audit["excluded_record_count"], 1)
        self.assertEqual(result.audit["disagreement_key_count"], 0)


class SnapshotDailyMergeTest(unittest.TestCase):
    """Across Snapshots, every distinct daily record is kept with its Snapshots."""

    def test_single_snapshot_and_reappearing_value_have_no_winner(self) -> None:
        single = _merge_dataset(
            "endurance_score_daily",
            _snapshot_observations("endurance_score_daily", [70]),
            1,
        )
        self.assertEqual(single[0][0]["raw_record"]["overallScore"], 70)
        self.assertEqual(single[0][0]["snapshot_numbers"], [1])
        self.assertEqual(single[5]["distinct_record_count"], 1)

        rows = _snapshot_observations("endurance_score_daily", [70, 71, 70])
        canonical, _, _, _, conflicts, summary = _merge_dataset("endurance_score_daily", rows, 3)
        self.assertEqual(conflicts, [])
        self.assertEqual(
            sorted(
                (item["raw_record"]["overallScore"], item["snapshot_numbers"])
                for item in canonical
            ),
            [(70, [1, 3]), (71, [2])],
        )
        self.assertEqual(summary["canonical_record_count"], 1)
        self.assertEqual(summary["distinct_record_count"], 2)
        self.assertEqual(summary["exact_repeat_count"], 1)
        self.assertFalse(summary["automatic_winner"])

    def test_four_snapshot_24_orders_give_the_same_records(self) -> None:
        for dataset, values in (
            ("endurance_score_daily", [70, 71, 72, 70]),
            ("uds_daily", [100, 100, 110, 120]),
        ):
            digests = set()
            for order in itertools.permutations(range(4)):
                observations = [_snapshot_observations(dataset, values)[index] for index in order]
                canonical, _, _, _, conflicts, summary = _merge_dataset(dataset, observations, 4)
                self.assertEqual(conflicts, [])
                semantic = {"canonical": canonical, "summary": summary}
                digests.add(hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest())
            self.assertEqual(len(digests), 1, dataset)

    def test_merge_summary_holds_counts_and_no_values(self) -> None:
        _, _, _, _, _, summary = _merge_dataset(
            "endurance_score_daily", _snapshot_observations("endurance_score_daily", [70, 71, 72, 73]), 4
        )
        serialized = json.dumps(summary)
        for private in ("overallScore", "private-", "synthetic.json", "object-"):
            self.assertNotIn(private, serialized)
        self.assertNotIn("observed_variants", summary)

    def test_snapshot_run_all_keeps_endurance_and_uds_days(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            for day, (score, steps) in enumerate(((70, 100), (71, 100), (70, 110)), start=1):
                source = root / f"source-{day}"
                _write_snapshot(source, [_activity(f"A{day}")])
                metrics = source / "DI-Connect-Metrics"
                metrics.mkdir()
                (metrics / "EnduranceScore_synthetic.json").write_text(
                    json.dumps([{"calendarDate": "2030-01-01", "overallScore": score}]),
                    encoding="utf-8",
                )
                aggregator = source / "DI-Connect-Aggregator"
                aggregator.mkdir()
                (aggregator / "UDSFile_synthetic.json").write_text(
                    json.dumps([_uds_row("2030-01-01", steps)]),
                    encoding="utf-8",
                )
                register_snapshot(
                    store,
                    source,
                    snapshot_label=f"S{day}",
                    export_requested_at=f"2030-01-0{day}T00:00:00+00:00",
                    export_downloaded_at=f"2030-01-0{day}T01:00:00+00:00",
                    export_observed_at=f"2030-01-0{day}T02:00:00+00:00",
                    confirm_complete=True,
                )
            output = root / "output"
            result = run_snapshot_all(store, output)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
            [endurance] = json.loads((output / "normalized/endurance_score_daily.json").read_text())
            self.assertIsNone(endurance["overall_score"])
            [uds] = json.loads((output / "normalized/uds_daily.json").read_text())
            self.assertEqual(uds["disagreeing_fields"], ["steps", "distance_meters", "active_calories"])
            self.assertEqual(uds["bmr_calories"], 1500)
            uds_audit = json.loads((output / "audit/uds_daily.json").read_text())
            self.assertEqual(
                [
                    (item["value"], item["observation_count"], item["snapshots"])
                    for item in uds_audit["disagreements"][0]["fields"][0]["values"]
                ],
                [(100, 2, [1, 2]), (110, 1, [3])],
            )
            summary = json.loads((output / "run_summary.json").read_text())
            self.assertEqual(
                sorted(
                    item["family"]
                    for item in summary["warnings"]
                    if item["code"] == "VALUES_DISAGREE"
                ),
                ["endurance_score", "uds"],
            )
            self.assertNotIn(
                "DAILY_METRICS_REVIEW_REQUIRED", {item["code"] for item in summary["warnings"]}
            )
            self.assertNotIn("observed variants", (output / "START_HERE.md").read_text())
            self.assertNotIn("observed_variants", (output / "run_summary.json").read_text())
