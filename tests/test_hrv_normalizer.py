from __future__ import annotations

import json
import struct
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from garmin_running_data_normalizer.fit.hrv import parse_fit_hrv_bytes
from garmin_running_data_normalizer.fit.parser import FIT_EPOCH_OFFSET
from garmin_running_data_normalizer.normalizers.hrv import normalize_hrv


def fit_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()) - FIT_EPOCH_OFFSET


def synthetic_hrv_fit(*records: tuple[int, int]) -> bytes:
    definition = bytes([0x40, 0x00, 0x00]) + struct.pack("<H", 370) + bytes(
        [2, 1, 2, 0x84, 253, 4, 0x86]
    )
    body = definition + b"".join(
        bytes([0x00]) + struct.pack("<HI", raw_value, timestamp)
        for raw_value, timestamp in records
    )
    return bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT" + body


def synthetic_float_hrv_fit(raw_value: float, timestamp: float) -> bytes:
    definition = bytes([0x40, 0x00, 0x00]) + struct.pack("<H", 370) + bytes(
        [2, 1, 4, 0x88, 253, 4, 0x88]
    )
    body = definition + bytes([0x00]) + struct.pack("<ff", raw_value, timestamp)
    return bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT" + body


def health_status_record(date: str, value: object) -> dict[str, object]:
    return {
        "calendarDate": date,
        "metrics": [
            {
                "type": "HRV",
                "value": value,
                "baselineLowerLimit": 60,
                "baselineUpperLimit": 85,
                "status": "SYNTHETIC_BALANCED",
                "percentage": 80,
                "feedbackKey": "SYNTHETIC_ONLY",
            }
        ],
    }


class HrvNormalizerTest(unittest.TestCase):
    def test_fit_hrv_extraction_invalid_sentinel_and_daily_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timestamp = fit_timestamp("2026-07-21T22:00:00Z")
            (root / "synthetic.fit").write_bytes(
                synthetic_hrv_fit((73 * 128, timestamp), (65535, timestamp))
            )
            result = normalize_hrv(root)
            daily = result["fit_daily"][0]
            self.assertEqual(daily["date"], "2026-07-22")
            self.assertEqual(daily["fit_hrv_value"], 73.0)
            self.assertEqual(daily["invalid_raw_value_count_for_date"], 1)
            self.assertEqual(daily["dedupe_method"], "same_date_valid_value_after_invalid_excluded")
            self.assertNotIn(str(root), daily["source_path"])

    def test_different_same_date_values_are_not_averaged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timestamp = fit_timestamp("2026-07-21T22:00:00Z")
            (root / "synthetic.fit").write_bytes(
                synthetic_hrv_fit((70 * 128, timestamp), (75 * 128, timestamp))
            )
            daily = normalize_hrv(root)["fit_daily"][0]
            self.assertIsNone(daily["fit_hrv_value"])
            self.assertEqual(daily["valid_values_for_review"], [70.0, 75.0])
            self.assertEqual(daily["dedupe_method"], "same_date_different_valid_values_not_averaged")

    def test_fit_json_consistency_is_validation_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timestamp = fit_timestamp("2026-07-21T22:00:00Z")
            (root / "synthetic.fit").write_bytes(synthetic_hrv_fit((73 * 128, timestamp)))
            (root / "synthetic_healthStatusData.json").write_text(
                json.dumps([health_status_record("2026-07-22", 73)]), encoding="utf-8"
            )
            result = normalize_hrv(root)
            comparison = result["fit_json_consistency"][0]
            self.assertEqual(comparison["consistency_status"], "same_date_value_match")
            self.assertIn("equivalence is not asserted", comparison["comparison_semantics"])
            reference = result["health_status_json_reference"][0]
            self.assertEqual(reference["health_status_hrv_value"], 73)
            self.assertIn("not proven equivalent", reference["semantics_note"])

    def test_json_difference_duplicate_and_unsafe_numbers_remain_reviewable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timestamp = fit_timestamp("2026-07-21T22:00:00Z")
            (root / "synthetic.fit").write_bytes(synthetic_hrv_fit((73 * 128, timestamp)))
            payload = [
                health_status_record("2026-07-22", 75),
                health_status_record("2026-07-22", 10**1000),
            ]
            (root / "synthetic_healthStatusData.json").write_text(json.dumps(payload), encoding="utf-8")
            result = normalize_hrv(root)
            self.assertEqual(
                result["fit_json_consistency"][0]["consistency_status"],
                "needs_review_duplicate_health_status_date",
            )
            self.assertTrue(
                all(row["reference_status"] == "needs_review" for row in result["health_status_json_reference"])
            )
            self.assertIsNone(result["health_status_json_reference"][1]["health_status_hrv_value"])
            json.dumps(result, allow_nan=False)

    def test_safe_zip_and_content_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timestamp = fit_timestamp("2026-07-21T22:00:00Z")
            with zipfile.ZipFile(root / "synthetic-export.zip", "w") as archive:
                archive.writestr("DI-Connect-Metrics/synthetic.fit", synthetic_hrv_fit((73 * 128, timestamp)))
                archive.writestr(
                    "DI-Connect-Wellness/synthetic_healthStatusData.json",
                    json.dumps({"healthStatusData": [health_status_record("2026-07-22", 73)]}),
                )
            first = normalize_hrv(root)
            (root / "unrelated.json").write_text("{}", encoding="utf-8")
            second = normalize_hrv(root)
            self.assertEqual(first["fit_daily"][0]["fit_file_id"], second["fit_daily"][0]["fit_file_id"])
            self.assertIn("!DI-Connect-Metrics/", first["fit_daily"][0]["source_path"])
            self.assertIn("!DI-Connect-Wellness/", first["health_status_json_reference"][0]["source_path"])

    def test_bad_fit_is_audited_without_false_hrv(self) -> None:
        parsed = parse_fit_hrv_bytes(b"not-fit", file_id="fit_file:synthetic", source_path="bad.fit")
        self.assertEqual(parsed["status"], "too_small")
        self.assertEqual(parsed["records"], [])

    def test_non_finite_and_unexpected_fit_fields_are_json_safe_holds(self) -> None:
        parsed = parse_fit_hrv_bytes(
            synthetic_float_hrv_fit(float("inf"), float("nan")),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        record = parsed["records"][0]
        self.assertIsNone(record["fit_hrv_raw_value"])
        self.assertIsNone(record["record_timestamp_raw"])
        self.assertTrue(record["raw_required_hold_flag"])
        json.dumps(parsed, allow_nan=False)

    def test_invalid_fit_timestamp_sentinel_is_missing_date_hold(self) -> None:
        parsed = parse_fit_hrv_bytes(
            synthetic_hrv_fit((73 * 128, 0xFFFFFFFF)),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        record = parsed["records"][0]
        self.assertIsNone(record["date"])
        self.assertIsNone(record["record_timestamp_raw"])
        self.assertTrue(record["raw_required_hold_flag"])
        json.dumps(parsed, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
