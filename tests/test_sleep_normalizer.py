from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from garmin_running_data_normalizer.normalizers.sleep import normalize_sleep


def synthetic_sleep_record(**overrides):
    record = {
        "calendarDate": "2026-07-21",
        "sleepStartTimestampGMT": "2026-07-21T14:00:00Z",
        "sleepEndTimestampGMT": "2026-07-21T22:00:00Z",
        "deepSleepSeconds": 7_200,
        "lightSleepSeconds": 14_400,
        "remSleepSeconds": 3_600,
        "awakeSleepSeconds": 3_600,
        "sleepScores": {"overallScore": 88},
        "sleepWindowConfirmationType": "SYNTHETIC_CONFIRMED",
        "retro": False,
    }
    record.update(overrides)
    return record


class SleepNormalizerTest(unittest.TestCase):
    def test_sleep_day_metrics_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic_sleepData.json").write_text(
                json.dumps([synthetic_sleep_record()]), encoding="utf-8"
            )
            record = normalize_sleep(str(root))[0]
            self.assertEqual(record["sleep_day"], "2026-07-22")
            self.assertEqual(record["sleep_calendar_date_source"], "2026-07-21")
            self.assertEqual(record["sleep_duration_minutes_ex_awake"], 420.0)
            self.assertEqual(record["sleep_window_minutes_including_awake"], 480.0)
            self.assertEqual(record["sleep_score"], 88)
            self.assertTrue(record["sleep_score_available_flag"])
            self.assertEqual(record["sleep_normalization_status"], "available")
            self.assertNotIn(str(root), record["source_path"])
            self.assertEqual(len(record["source_sha256"]), 64)
            self.assertTrue(record["sleep_record_key"].startswith("sleep_record:"))

    def test_missing_score_is_available_but_duplicate_day_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = synthetic_sleep_record(sleepScores=None)
            second = synthetic_sleep_record(calendarDate="2026-07-22", sleepScores={"overall": {"value": 75}})
            (root / "synthetic_sleepData.json").write_text(json.dumps([first, second]), encoding="utf-8")
            records = normalize_sleep(str(root))
            self.assertEqual(len({record["sleep_record_key"] for record in records}), 2)
            self.assertEqual({record["sleep_normalization_status"] for record in records}, {"needs_review"})
            self.assertEqual({record["sleep_reason_code"] for record in records}, {"sleep_json_duplicate_sleep_day"})
            self.assertEqual([record["sleep_score_available_flag"] for record in records], [False, True])

    def test_empty_missing_and_invalid_records_are_not_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = [
                {"retro": True},
                synthetic_sleep_record(sleepStartTimestampGMT=None),
                synthetic_sleep_record(
                    sleepStartTimestampGMT="2026-07-21T22:00:00Z",
                    sleepEndTimestampGMT="2026-07-21T14:00:00Z",
                ),
            ]
            (root / "synthetic_sleepData.json").write_text(json.dumps(payload), encoding="utf-8")
            records = normalize_sleep(str(root))
            by_reason = {record["sleep_reason_code"]: record for record in records}
            self.assertEqual(
                by_reason["sleep_json_empty_retro_only_record"]["sleep_normalization_status"],
                "excluded_empty_record",
            )
            self.assertEqual(
                by_reason["sleep_json_missing_start_or_end"]["sleep_normalization_status"],
                "needs_review",
            )
            self.assertEqual(
                by_reason["sleep_json_invalid_sleep_interval"]["sleep_normalization_status"],
                "needs_review",
            )

    def test_non_finite_metrics_are_null_and_json_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = synthetic_sleep_record(
                deepSleepSeconds="Infinity",
                lightSleepSeconds=None,
                remSleepSeconds=None,
                totalSleepSeconds="NaN",
                sleepScores={"overallScore": "NaN"},
            )
            (root / "synthetic_sleepData.json").write_text(json.dumps([record]), encoding="utf-8")
            normalized = normalize_sleep(str(root))[0]
            self.assertIsNone(normalized["sleep_duration_minutes_ex_awake"])
            self.assertIsNone(normalized["sleep_score"])
            self.assertFalse(normalized["sleep_score_available_flag"])
            json.dumps(normalized, allow_nan=False)

    def test_arbitrary_precision_metrics_are_null_instead_of_raising(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = synthetic_sleep_record(
                deepSleepSeconds=10**1000,
                lightSleepSeconds=None,
                remSleepSeconds=None,
                totalSleepSeconds=10**1000,
                sleepScores={"overallScore": 10**1000},
            )
            (root / "synthetic_sleepData.json").write_text(json.dumps([record]), encoding="utf-8")
            normalized = normalize_sleep(str(root))[0]
            self.assertIsNone(normalized["sleep_duration_minutes_ex_awake"])
            self.assertIsNone(normalized["sleep_score"])
            json.dumps(normalized, allow_nan=False)

    def test_safe_zip_wrapper_and_content_identity_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {"sleepData": [synthetic_sleep_record()]}
            with zipfile.ZipFile(root / "synthetic-export.zip", "w") as archive:
                archive.writestr("DI-Connect-Wellness/synthetic_sleepData.json", json.dumps(payload))
            original = normalize_sleep(str(root))[0]
            (root / "a_unclassified.json").write_text("{}", encoding="utf-8")
            repeated = normalize_sleep(str(root))[0]
            self.assertEqual(original["sleep_record_key"], repeated["sleep_record_key"])
            self.assertIn("!DI-Connect-Wellness/", original["source_path"])


if __name__ == "__main__":
    unittest.main()
