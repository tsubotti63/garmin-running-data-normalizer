from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.common.identity import garmin_activity_key, stable_hash
from garmin_running_data_normalizer.common.time import daily_calendar_date, unix_ms_to_local_date
from garmin_running_data_normalizer.policies.datasets import inspect_records, load_registry, validate_registry
from garmin_running_data_normalizer.qa import deterministic_records_digest, summarize_records


class CommonAndPolicyTest(unittest.TestCase):
    def test_stable_identity_prefers_activity_id(self) -> None:
        self.assertEqual(garmin_activity_key(123), "garmin_activity:123")
        self.assertEqual(stable_hash(["a", 1]), stable_hash(["a", 1]))

    def test_identity_requires_real_fallback(self) -> None:
        with self.assertRaises(ValueError):
            garmin_activity_key(None)

    def test_time_normalization(self) -> None:
        self.assertEqual(daily_calendar_date("2026-07-17T12:00:00"), "2026-07-17")
        self.assertEqual(unix_ms_to_local_date(0, "Asia/Tokyo"), "1970-01-01")

    def test_registry_and_record_policy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        registry, digest = load_registry(root / "config/dataset_registry.example.json")
        self.assertEqual(validate_registry(registry)["status"], "PASS")
        self.assertEqual(len(digest), 64)
        report = inspect_records(
            [{"id": 1, "sequence": 1, "value": 10}, {"id": 1, "sequence": 2, "value": 11}],
            stable_key=["id"],
            update_order=["sequence"],
        )
        self.assertEqual(report["status"], "PASS_ORDERED_UPDATES")

    def test_conflict_and_null_key_are_not_silently_canonicalized(self) -> None:
        conflict = inspect_records([{"id": 1, "v": 1}, {"id": 1, "v": 2}], stable_key=["id"])
        null_key = inspect_records([{"id": None, "v": 1}], stable_key=["id"])
        self.assertEqual(conflict["status"], "REVIEW_REQUIRED_UNRESOLVED_KEY_CONFLICT")
        self.assertEqual(null_key["status"], "WARNING_NULL_KEY_PRESERVED")

    def test_qa_digest_is_order_independent(self) -> None:
        first = [{"id": "b"}, {"id": "a"}]
        second = list(reversed(first))
        self.assertEqual(deterministic_records_digest(first), deterministic_records_digest(second))
        self.assertEqual(summarize_records(first, key_field="id")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
