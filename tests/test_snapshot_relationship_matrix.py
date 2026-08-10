from __future__ import annotations

import hashlib
import itertools
import json
import unittest

from garmin_running_data_normalizer.relationships import validate_declared_relationships
from garmin_running_data_normalizer.snapshot.merge import _merge_dataset


def _observation(dataset: str, snapshot_id: str, logical_order: int, record: dict, raw_key: tuple):
    return {
        "dataset": dataset,
        "snapshot_id": snapshot_id,
        "logical_order": logical_order,
        "record": record,
        "raw_key": raw_key,
        "export_observed_at": f"2026-05-{logical_order:02d}T12:00:00+09:00",
        "source_relative_path": f"synthetic/{snapshot_id}/{dataset}.json",
        "source_record_index": 0,
        "source_object_sha256": "a" * 64,
    }


def _snapshot_observations(snapshot_id: str, logical_order: int) -> dict[str, list[dict]]:
    activity = {
        "activityId": 101,
        "startTimeGmt": "2030-01-01T00:00:00Z",
        "distance": 5000,
        "duration": 1800,
        "activityType": {"typeKey": "running"},
    }
    gear = {"gearPk": 7, "displayName": "Synthetic Shoe"}
    link = {"activityId": 101, "gearPk": 7}
    # S2 intentionally omits the Activity endpoint; S3 intentionally omits
    # the link. The cumulative union must still resolve the explicit link.
    values = {
        "activities": [] if snapshot_id == "S2" else [(activity, (101,))],
        "gear": [(gear, (7,))],
        "activity_gear": [] if snapshot_id == "S3" else [(link, (7, 101))],
    }
    return {
        dataset: [
            _observation(dataset, snapshot_id, logical_order, record, raw_key)
            for record, raw_key in rows
        ]
        for dataset, rows in values.items()
    }


def _normalized_digest(order: tuple[int, ...]) -> tuple[str, dict]:
    snapshots = [f"S{index}" for index in range(1, 5)]
    observations: dict[str, list[dict]] = {"activities": [], "gear": [], "activity_gear": []}
    for snapshot_index in order:
        # The snapshot registry canonicalizes logical order by acquisition
        # date; this matrix varies ingestion order while keeping that
        # authoritative order fixed.
        logical_order = snapshot_index + 1
        snapshot = _snapshot_observations(snapshots[snapshot_index], logical_order)
        for dataset, rows in snapshot.items():
            observations[dataset].extend(rows)
    merged: dict[str, list[dict]] = {}
    for dataset in observations:
        merged[dataset], *_ = _merge_dataset(dataset, observations[dataset], 4)
    raw_activities = merged["activities"][0]["raw_record"]
    raw_gear = merged["gear"][0]["raw_record"]
    raw_link = merged["activity_gear"][0]["raw_record"]
    records = {
        "activities": [{
            "garmin_activity_key": "garmin_activity:101",
            "activity_id": raw_activities["activityId"],
            "source_path": "synthetic/activities.json",
            "source_sha256": "a" * 64,
        }],
        "gear": [{
            "gear_key": raw_gear["gearPk"],
            "source_path": "synthetic/gear.json",
            "source_sha256": "a" * 64,
        }],
        "activity_gear": [{
            "gear_key": raw_link["gearPk"],
            "activity_id": raw_link["activityId"],
            "source_path": "synthetic/gear.json",
            "source_sha256": "a" * 64,
        }],
        "personal_records": [],
        "fit_sessions": [],
        "fit_laps": [],
    }
    latest_snapshot = snapshots[3]
    latest = _snapshot_observations(latest_snapshot, 4)
    current_activity_ids = {str(row["record"]["activityId"]) for row in latest["activities"]}
    current_gear_keys = {str(row["record"]["gearPk"]) for row in latest["gear"]}
    summary = validate_declared_relationships(
        records,
        current_activity_ids=current_activity_ids,
        current_gear_keys=current_gear_keys,
        current_fit_session_keys=set(),
    )
    payload = {
        "records": records,
        # Snapshot attribution is audit context and may legitimately identify
        # a different latest snapshot for a different permutation. The
        # normalized relationship result itself must remain byte-stable.
        "relationship": {
            "relationship_total": summary["relationship_total"],
            "relationship_resolved": summary["relationship_resolved"],
            "relationship_unresolved": summary["relationship_unresolved"],
            "unresolved_links": summary["unresolved_links"],
        },
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return digest, summary


class SnapshotRelationshipMatrixTest(unittest.TestCase):
    def test_all_24_snapshot_orders_have_same_explicit_result(self) -> None:
        results = [_normalized_digest(order) for order in itertools.permutations(range(4))]
        digests = {digest for digest, _summary in results}
        self.assertEqual(len(digests), 1)
        for _digest, summary in results:
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["relationship_total"], 1)
            self.assertEqual(summary["relationship_resolved"], 1)
            self.assertEqual(summary["relationship_snapshot_resolved"], 0)
            self.assertEqual(summary["relationship_unresolved"], 0)
            self.assertFalse(summary["relationships"]["activity_gear_to_activities"]["inference_performed"])
