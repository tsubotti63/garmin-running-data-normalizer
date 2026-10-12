from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.diagnostics.detector import classify_source_name
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from tests.test_snapshot_lifecycle import (
    _activity,
    _write_performance_metrics,
    _write_remaining_daily_metrics,
    _write_snapshot,
)

ACCOUNT = "synthetic-account-boundary"
METRIC_FAMILIES = {
    "hill_score_daily": "hill_score",
    "endurance_score_daily": "endurance_score",
    "vo2max_daily": "vo2max",
}
MERGED_FILES = {
    "DI-Connect-Metrics/snapshot_HillScore.json": "hill_score",
    "DI-Connect-Metrics/snapshot_EnduranceScore.json": "endurance_score",
    "DI-Connect-Metrics/snapshot_vo2max.json": "vo2max",
}


def register(store: Path, source: Path, label: str, day: int) -> None:
    register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
        confirm_complete=True,
    )


def write_metric_export(root: Path, name: str, day: int) -> Path:
    """Write an Export with Hill, Endurance, and both VO2Max series for one day."""
    source = root / name
    _write_snapshot(source, [_activity(f"A{day}")])
    _write_performance_metrics(source, day)
    _write_remaining_daily_metrics(source, day)
    (source / "DI-Connect-Metrics" / f"ActivityVo2Max_{day}.json").write_text(
        json.dumps(
            [
                {
                    "calendarDate": f"2030-02-{day:02d}",
                    "timestampGmt": f"2030-02-{day:02d}T07:00:00",
                    "vo2MaxValue": 48 + day,
                    "sport": "RUNNING",
                    "activityId": 1000 + day,
                }
            ]
        ),
        encoding="utf-8",
    )
    return source


def read_rows(output: Path, dataset: str) -> list[dict[str, object]]:
    return json.loads(
        (output / "normalized" / f"{dataset}.json").read_text(encoding="utf-8")
    )


def family_statuses(output: Path) -> dict[str, str]:
    summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
    return {
        family: summary["family_results"][family]["status"]
        for family in METRIC_FAMILIES.values()
    }


class SnapshotMetricFamiliesTest(unittest.TestCase):
    def test_single_snapshot_matches_direct_run_all(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_metric_export(root, "source", 1)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source, "S1", 1)

            run_all(source, root / "direct")
            run_snapshot_all(store, root / "snapshot")

            for dataset in METRIC_FAMILIES:
                direct = read_rows(root / "direct", dataset)
                self.assertTrue(direct, dataset)
                self.assertEqual(read_rows(root / "snapshot", dataset), direct, dataset)
            self.assertEqual(
                sorted(
                    row["vo2max_source_series"]
                    for row in read_rows(root / "snapshot", "vo2max_daily")
                ),
                ["activity_vo2max_daily", "performance_metrics_daily"],
            )
            self.assertEqual(
                family_statuses(root / "snapshot"),
                {family: "PROCESSED" for family in METRIC_FAMILIES.values()},
            )
            manifest = json.loads(
                (root / "snapshot/run_manifest.json").read_text(encoding="utf-8")
            )
            detected = {
                item["source_path"]: item["detected_family"]
                for item in manifest["input_assets"]
            }
            for path, family in MERGED_FILES.items():
                self.assertEqual(detected[path], family, path)

    def test_rows_from_every_snapshot_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for day in (1, 2):
                source = write_metric_export(root, f"source-{day}", day)
                register(store, source, f"S{day}", day)

            run_snapshot_all(store, root / "snapshot")

            merge = json.loads(
                (root / "snapshot/snapshot/canonical_merge_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            for dataset in METRIC_FAMILIES:
                self.assertEqual(
                    len(read_rows(root / "snapshot", dataset)),
                    merge["datasets"][dataset]["canonical_record_count"],
                    dataset,
                )
            self.assertEqual(
                [row["calendar_date"] for row in read_rows(root / "snapshot", "hill_score_daily")],
                ["2030-01-01", "2030-01-02"],
            )
            self.assertEqual(len(read_rows(root / "snapshot", "vo2max_daily")), 4)

    def test_endurance_values_that_differ_keep_their_day_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_metric_export(root, "source-1", 1)
            second = write_metric_export(root, "source-2", 2)
            (second / "DI-Connect-Metrics" / "EnduranceScore_revised.json").write_text(
                json.dumps(
                    [
                        {
                            "calendarDate": "2030-01-01",
                            "overallScore": 5999,
                            "classification": 5,
                            "feedbackPhrase": 19,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)

            summary = run_snapshot_all(store, root / "snapshot")

            self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
            # The day whose values differ stays, with the differing field empty.
            rows = {
                row["calendar_date"]: row
                for row in read_rows(root / "snapshot", "endurance_score_daily")
            }
            self.assertEqual(sorted(rows), ["2030-01-01", "2030-01-02"])
            self.assertIsNone(rows["2030-01-01"]["overall_score"])
            self.assertEqual(rows["2030-01-01"]["disagreeing_fields"], ["overall_score"])
            self.assertEqual(rows["2030-01-01"]["classification"], 5)
            audit = json.loads(
                (root / "snapshot/audit/endurance_score_daily.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(audit["disagreement_key_count"], 1)
            self.assertEqual(
                [
                    (value["value"], value["snapshots"])
                    for value in audit["disagreements"][0]["fields"][0]["values"]
                ],
                [(5999, [2]), (6001, [1])],
            )
            self.assertNotIn("observed_variants", audit)
            merge_summary = json.loads(
                (root / "snapshot/snapshot/canonical_merge_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("observed_variants", merge_summary["datasets"]["endurance_score_daily"])

    def test_detector_matches_only_the_merged_names(self) -> None:
        cases = (
            ("DI-Connect-Metrics/snapshot_HillScore.json", "hill_score"),
            ("DI-Connect-Metrics/snapshot_EnduranceScore.json", "endurance_score"),
            ("DI-Connect-Metrics/snapshot_vo2max.json", "vo2max"),
            ("DI-Connect-Metrics\\SNAPSHOT_VO2MAX.JSON", "vo2max"),
            ("DI-Connect-Metrics/HillScore_2030.json", "hill_score"),
            ("DI-Connect-Metrics/EnduranceScore_2030.json", "endurance_score"),
            ("DI-Connect-Metrics/MetricsMaxMetData_2030.json", "vo2max"),
            ("DI-Connect-Metrics/snapshot_HillScore_extra.json", "unclassified"),
            ("DI-Connect-Metrics/my_snapshot_vo2max.json", "unclassified"),
        )
        for name, family in cases:
            with self.subTest(name=name):
                self.assertEqual(classify_source_name(name, "json"), family)
        self.assertEqual(
            classify_source_name("DI-Connect-Metrics/snapshot_HillScore.json", "fit"),
            "fit",
        )


if __name__ == "__main__":
    unittest.main()
