"""Daily values across Snapshots are compared as within one Export (stage A2b-1)."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from garmin_running_data_normalizer.snapshot.merge import DATASET_ORDER, DAILY_DATASETS
from garmin_running_data_normalizer.snapshot.policies import (
    CONTRACT_VERSION,
    MERGE_RULES_VERSION,
    REGISTRY_VERSION,
    merge_rules,
    public_registry,
)
from tests.test_remaining_wellness_metrics import fit_timestamp, hrv_fit
from tests.test_snapshot_lifecycle import _activity, _write_snapshot

ACCOUNT = "synthetic-account-boundary"
NEW_YORK = "America/New_York"


def register(
    store: Path,
    source: Path,
    label: str,
    day: int,
    *,
    observed_hour: int = 2,
) -> dict[str, object]:
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T{observed_hour:02d}:00:00+00:00",
        confirm_complete=True,
    )


def write_export(
    root: Path,
    name: str,
    files: dict[str, object],
    *,
    fit_payload: bytes | None = None,
) -> Path:
    """Write a synthetic Export with one Activity and the given JSON files."""
    source = root / name
    _write_snapshot(source, [_activity(f"A-{name}")], fit_payload=fit_payload)
    for relative, value in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    return source


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def uds(steps: object, day: str = "2030-02-01") -> dict[str, object]:
    return {"calendarDate": day, "totalSteps": steps, "bmrKilocalories": 1500}


class SnapshotDailyValuesTest(unittest.TestCase):
    def test_a_missing_value_in_a_later_snapshot_is_absent(self) -> None:
        # The example the maintainer approved: 8,000 steps, then no value.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for day, steps in ((1, 8000), (2, None)):
                source = write_export(
                    root, f"source-{day}", {"DI-Connect-Aggregator/UDSFile_1.json": [uds(steps)]}
                )
                register(store, source, f"S{day}", day)
            result = run_snapshot_all(store, root / "output")
            self.assertEqual(result["exit_code"], 0)
            [row] = load(root / "output/normalized/uds_daily.json")
            self.assertEqual(row["steps"], 8000)
            self.assertEqual(row["disagreeing_fields"], [])
            audit = load(root / "output/audit/uds_daily.json")
            self.assertEqual(audit["absent_value_counts"], {"steps": 1})
            self.assertEqual(audit["disagreement_key_count"], 0)

    def test_values_that_differ_within_one_snapshot_or_at_one_time_are_kept(self) -> None:
        cases = {
            # One Snapshot gives two different values for one day.
            "within one snapshot": [([uds(100), uds(110)], 1)],
            # Two Snapshots observed at the same time give different values.
            "same observation time": [([uds(100)], 2), ([uds(110)], 2)],
        }
        for name, exports in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = root / "store"
                initialize_store(store, ACCOUNT)
                for index, (rows, day) in enumerate(exports, start=1):
                    source = write_export(
                        root, f"source-{index}", {"DI-Connect-Aggregator/UDSFile_1.json": rows}
                    )
                    register(store, source, f"S{index}", day)
                result = run_snapshot_all(store, root / "output")
                self.assertEqual(result["exit_code"], 0)
                [row] = load(root / "output/normalized/uds_daily.json")
                self.assertIsNone(row["steps"])
                self.assertEqual(row["disagreeing_fields"], ["steps"])
                values = load(root / "output/audit/uds_daily.json")["disagreements"][0]["fields"][0][
                    "values"
                ]
                self.assertEqual([item["value"] for item in values], [100, 110])
                self.assertTrue(all(item["snapshots"] for item in values))

    def test_hrv_values_that_differ_name_their_snapshots(self) -> None:
        timestamp = fit_timestamp("2030-02-01T12:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            payloads = {
                1: hrv_fit((70 * 128, timestamp)),
                2: hrv_fit((75 * 128, timestamp)),
                3: hrv_fit((70 * 128, timestamp)),
            }
            for day, payload in payloads.items():
                source = write_export(root, f"source-{day}", {}, fit_payload=payload)
                register(store, source, f"S{day}", day)
            result = run_snapshot_all(store, root / "output")
            self.assertEqual(result["exit_code"], 0)
            [row] = load(root / "output/normalized/hrv_daily.json")
            self.assertIsNone(row["hrv_value"])
            self.assertEqual(row["disagreeing_fields"], ["hrv_value"])
            [entry] = load(root / "output/audit/hrv_daily.json")["disagreements"]
            self.assertEqual(entry["observation_count"], 3)
            self.assertEqual(
                entry["fields"][0]["values"],
                [
                    {"value": 70.0, "observation_count": 2, "snapshots": [1, 3]},
                    {"value": 75.0, "observation_count": 1, "snapshots": [2]},
                ],
            )

    def test_sleep_without_calendar_date_gets_the_one_shot_sleep_day(self) -> None:
        undated = {
            "sleepStartTimestampGMT": "2030-02-01T20:00:00Z",
            "sleepEndTimestampGMT": "2030-02-02T03:30:00Z",
            "sleepTimeSeconds": 20000,
        }
        files = {"DI-Connect-Wellness/synthetic_sleepData.json": [undated]}
        for timezone_name in ("Asia/Tokyo", NEW_YORK):
            with self.subTest(timezone=timezone_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = root / "store"
                initialize_store(store, ACCOUNT)
                for day in (1, 2):
                    register(store, write_export(root, f"source-{day}", files), f"S{day}", day)
                run_snapshot_all(store, root / "snapshot", timezone_name=timezone_name)
                run_all(write_export(root, "one-shot", files), root / "one-shot-output", timezone_name=timezone_name)
                snapshot_rows = load(root / "snapshot/normalized/sleep_daily.json")
                one_shot_rows = load(root / "one-shot-output/normalized/sleep_daily.json")
                self.assertEqual(len(snapshot_rows), 1)
                self.assertEqual(snapshot_rows, one_shot_rows)

    def test_processing_sequence_does_not_change_the_snapshot_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for day, steps in ((1, 100), (2, 110), (3, 100)):
                source = write_export(
                    root, f"source-{day}", {"DI-Connect-Aggregator/UDSFile_1.json": [uds(steps)]}
                )
                register(store, source, f"S{day}", day)
            first = build_approved_input(store, root / "build-a", processing_sequence=["S3", "S1", "S2"])
            second = build_approved_input(store, root / "build-b", processing_sequence=["S2", "S3", "S1"])
            self.assertEqual(first["canonical_build_sha256"], second["canonical_build_sha256"])
            relative = "approved_input/DI-Connect-Aggregator/UDSFile_snapshot.json"
            self.assertEqual(
                (root / "build-a" / relative).read_bytes(),
                (root / "build-b" / relative).read_bytes(),
            )

    def test_store_keeps_its_versions_and_builds_record_the_merge_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, write_export(root, "source-1", {}), "S1", 1)
            metadata = load(store / "store.json")
            self.assertEqual(metadata["policy_registry_version"], REGISTRY_VERSION)
            self.assertEqual(metadata["contract_version"], CONTRACT_VERSION)
            self.assertTrue(REGISTRY_VERSION.endswith(":v1.0"))
            for manifest in store.glob("snapshots/*/manifest.json"):
                self.assertEqual(load(manifest)["policy_registry_version"], REGISTRY_VERSION)
                self.assertNotIn("merge_rules_version", load(manifest))
            build = build_approved_input(store, root / "build")
            self.assertEqual(build["lineage"]["merge_rules_version"], MERGE_RULES_VERSION)
            self.assertEqual(build["merge_summary"]["merge_rules_version"], MERGE_RULES_VERSION)
            self.assertEqual(
                load(root / "build/approved_input/approved_input_manifest.json")["merge_rules_version"],
                MERGE_RULES_VERSION,
            )

    def test_merge_rules_are_published_apart_from_the_v1_registry(self) -> None:
        root = Path(__file__).resolve().parents[1]
        published = load(root / "config/garmin_snapshot_merge_rules_v2.json")
        self.assertEqual(published, merge_rules())
        self.assertEqual(published["merge_rules_version"], MERGE_RULES_VERSION)
        self.assertEqual(published["store_policy_registry_version"], REGISTRY_VERSION)
        self.assertEqual(set(published["daily_datasets"]["datasets"]), DAILY_DATASETS)
        self.assertTrue(DAILY_DATASETS <= set(DATASET_ORDER))
        # The v1.0 registry stays the record of the v1.0 rules.
        registry = public_registry()
        self.assertNotIn("merge_rules_version", registry)
        self.assertEqual(
            {
                item["dataset"]: item["conflict_policy"]
                for item in registry["policies"]
                if item["dataset"] in DAILY_DATASETS
            },
            {dataset: "review_fail_closed" for dataset in DAILY_DATASETS},
        )

    def test_shared_files_carry_counts_and_no_observed_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for day, steps in ((1, 3456789), (2, 3456790)):
                source = write_export(
                    root, f"source-{day}", {"DI-Connect-Aggregator/UDSFile_1.json": [uds(steps)]}
                )
                register(store, source, f"S{day}", day)
            output = root / "output"
            run_snapshot_all(store, output, external_safe_pack=True)
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with self.subTest(file=path.name), zipfile.ZipFile(path) as archive:
                    content = b"".join(archive.read(name) for name in archive.namelist())
                    for value in (b"3456789", b"3456790"):
                        self.assertNotIn(value, content)
            for relative in ("snapshot/canonical_merge_summary.json", "run_summary.json"):
                with self.subTest(file=relative):
                    self.assertNotIn(b"3456789", (output / relative).read_bytes())
            # The local audit keeps the values with their Snapshots.
            self.assertIn(b"3456789", (output / "audit/uds_daily.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
