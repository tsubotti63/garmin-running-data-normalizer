"""A Snapshot Store that version 1.7.1 wrote keeps working without migration."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from garmin_running_data_normalizer.snapshot import (
    register_snapshot,
    run_snapshot_all,
    snapshot_status,
    verify_store,
)
from garmin_running_data_normalizer.snapshot.store import load_manifests


FIXTURE = Path(__file__).resolve().parent / "fixtures/snapshot_store_v1_7_1/store_files.json"
# The fixture is kept as version 1.7.1 wrote it; see its README.
FIXTURE_SHA256 = "f49df7c9cfeaf51b087f7f464337ebb262fa20ad7ccc0ef110c5753bd7dc426e"


def extract_store(target: Path) -> Path:
    """Write the fixture's store with the file modes that version 1.7.1 set."""
    entries = json.loads(FIXTURE.read_text(encoding="utf-8"))["entries"]
    target.mkdir()
    for entry in entries:
        path = target / entry["path"]
        if "text" in entry:
            path.write_bytes(entry["text"].encode("utf-8"))
        elif "base64" in entry:
            path.write_bytes(base64.b64decode(entry["base64"]))
        else:
            path.mkdir()
    if os.name == "posix":
        # Files first, so that no folder is read-only while it is written.
        for entry in sorted(entries, key=lambda item: "text" in item or "base64" in item, reverse=True):
            (target / entry["path"]).chmod(int(entry["mode"], 8))
    return target


def tree_state(root: Path) -> list[tuple[str, str]]:
    return [
        (
            path.relative_to(root).as_posix(),
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "folder",
        )
        for path in sorted(root.rglob("*"))
    ]


class SnapshotStoreV171Test(unittest.TestCase):
    def test_fixture_is_the_store_that_version_1_7_1_wrote(self) -> None:
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA256)

    def test_store_loads_and_verifies_without_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = extract_store(Path(directory) / "store")
            before = tree_state(store)
            verification = verify_store(store)
            self.assertEqual(verification["status"], "PASS", verification)
            self.assertEqual(verification["snapshot_count"], 2)
            status = snapshot_status(store)
            self.assertEqual(status["snapshot_count"], 2)
            self.assertEqual(
                [item["snapshot_label"] for item in load_manifests(store)],
                ["S1", "S2"],
            )
            self.assertEqual(tree_state(store), before)

    def test_every_snapshot_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = extract_store(root / "store")
            before = tree_state(store)
            output = root / "output"
            result = run_snapshot_all(store, output)
            self.assertEqual(result["snapshot_count"], 2)
            self.assertEqual(result["store_verification"], "PASS")
            self.assertEqual(result["processing_sequence"], ["S1", "S2"])
            self.assertIn(result["status"], {"PASS", "PASS_WITH_WARNINGS"})
            normalized = output / "normalized"
            activities = {
                row["activity_id"]: row
                for row in json.loads((normalized / "activities.json").read_text(encoding="utf-8"))
            }
            # SYNTHETIC-A1 is only in the first Snapshot and SYNTHETIC-A3 only in
            # the second; SYNTHETIC-A2 takes its name from the second.
            self.assertEqual(
                sorted(activities),
                ["SYNTHETIC-A1", "SYNTHETIC-A2", "SYNTHETIC-A3"],
            )
            self.assertEqual(activities["SYNTHETIC-A2"]["name"], "Synthetic A2 after")
            links = json.loads((normalized / "activity_gear.json").read_text(encoding="utf-8"))
            self.assertEqual(
                sorted(row["activity_id"] for row in links),
                ["SYNTHETIC-A1", "SYNTHETIC-A3"],
            )
            for dataset, field in (
                ("hill_score_daily.json", "calendar_date"),
                ("sleep_daily.json", "sleep_day"),
            ):
                rows = json.loads((normalized / dataset).read_text(encoding="utf-8"))
                self.assertEqual(
                    sorted(row[field] for row in rows),
                    ["2030-01-02", "2030-01-03"],
                    dataset,
                )
            fit_sessions = json.loads((normalized / "fit_sessions.json").read_text(encoding="utf-8"))
            self.assertEqual(len(fit_sessions), 1)
            self.assertEqual(tree_state(store), before)

    def test_new_snapshot_registers_into_the_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = extract_store(root / "store")
            export = root / "export-3.zip"
            payload = json.dumps(
                [
                    {
                        "summarizedActivitiesExport": [
                            {
                                "activityId": "SYNTHETIC-A4",
                                "activityType": "running",
                                "sportType": "running",
                                "distance": 500000,
                                "duration": 1800000,
                                "startTimeGmt": 1893715200000,
                                "startTimeLocal": "2030-01-04T09:00:00",
                                "name": "Synthetic A4",
                                "synthetic": True,
                            }
                        ]
                    }
                ]
            )
            with zipfile.ZipFile(export, "w") as archive:
                archive.writestr(
                    "DI_CONNECT/DI-Connect-Fitness/synthetic_summarizedActivities.json",
                    payload,
                )
            result = register_snapshot(
                store,
                export,
                snapshot_label="S3",
                export_requested_at="2030-01-04T00:00:00+00:00",
                export_downloaded_at="2030-01-04T01:00:00+00:00",
                export_observed_at="2030-01-04T02:00:00+00:00",
                confirm_complete=True,
            )
            self.assertEqual(result["snapshot_count"], 3)
            self.assertEqual(verify_store(store)["status"], "PASS")
            output = root / "output"
            run = run_snapshot_all(store, output)
            self.assertEqual(run["processing_sequence"], ["S1", "S2", "S3"])
            activities = json.loads(
                (output / "normalized/activities.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                sorted(row["activity_id"] for row in activities),
                ["SYNTHETIC-A1", "SYNTHETIC-A2", "SYNTHETIC-A3", "SYNTHETIC-A4"],
            )


if __name__ == "__main__":
    unittest.main()
