from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from garmin_running_data_normalizer.normalizers.health_status import normalize_health_status


def metric(metric_type: str, value: object, *, status: str = "SYNTHETIC_NORMAL") -> dict[str, object]:
    return {
        "type": metric_type,
        "value": value,
        "baselineUpperLimit": 90,
        "baselineLowerLimit": 50,
        "status": status,
        "percentage": 75,
        "feedbackKey": "SYNTHETIC_ONLY",
    }


def record(date: object, metrics: list[dict[str, object]], update: str = "2026-07-22T02:00:00Z") -> dict[str, object]:
    return {
        "calendarDate": date,
        "createTimestampUTC": "2026-07-22T01:00:00Z",
        "updateTimestampUTC": update,
        "outliersCount": 2,
        "metrics": metrics,
    }


class HealthStatusNormalizerTest(unittest.TestCase):
    def test_complete_long_and_fixed_daily_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics = [
                metric("HRV", 72),
                metric("HR", 55),
                metric("SPO2", 98),
                metric("SKIN_TEMP_C", 36.4),
                metric("RESPIRATION", 14),
            ]
            (root / "synthetic_healthStatusData.json").write_text(
                json.dumps([record("2026-07-22", metrics)]), encoding="utf-8"
            )
            result = normalize_health_status(root)
            self.assertEqual(len(result["metrics"]), 5)
            daily = result["daily"][0]
            self.assertEqual(daily["health_status_hrv_value"], 72)
            self.assertEqual(daily["health_status_hr_status"], "SYNTHETIC_NORMAL")
            self.assertEqual(daily["health_status_spo2_baseline_lower"], 50)
            self.assertEqual(daily["health_status_skin_temp_c_percentage"], 75)
            self.assertEqual(daily["health_status_respiration_feedback_key"], "SYNTHETIC_ONLY")
            self.assertEqual(daily["source_metric_count"], 5)
            self.assertNotIn(str(root), daily["source_path"])

    def test_unknown_metric_is_retained_long_without_dynamic_daily_column(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic_healthStatusData.json").write_text(
                json.dumps([record("2026-07-22", [metric("SYNTHETIC_UNKNOWN", 1)])]),
                encoding="utf-8",
            )
            result = normalize_health_status(root)
            self.assertEqual(result["metrics"][0]["metric_type"], "SYNTHETIC_UNKNOWN")
            self.assertEqual(result["daily"][0]["unknown_metric_count"], 1)
            self.assertFalse(any("synthetic_unknown" in key for key in result["daily"][0]))

    def test_duplicate_calendar_date_selects_latest_and_retains_long_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = [
                record("2026-07-22", [metric("HR", 50)], "2026-07-22T02:00:00Z"),
                record("2026-07-22", [metric("HR", 60)], "2026-07-22T03:00:00Z"),
            ]
            (root / "synthetic_healthStatusData.json").write_text(json.dumps(payload), encoding="utf-8")
            result = normalize_health_status(root)
            self.assertEqual(len(result["daily"]), 1)
            self.assertEqual(result["daily"][0]["health_status_hr_value"], 60)
            self.assertEqual(result["daily"][0]["daily_duplicate_count_before_dedupe"], 2)
            self.assertEqual(result["daily"][0]["health_status_normalization_status"], "available_with_explicit_dedupe")
            self.assertEqual(
                {row["daily_selection_status"] for row in result["metrics"]},
                {"selected_for_daily", "superseded_for_daily"},
            )

    def test_duplicate_metric_type_is_not_silently_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = [record("2026-07-22", [metric("HR", 50), metric("hr", 60)])]
            (root / "synthetic_healthStatusData.json").write_text(json.dumps(payload), encoding="utf-8")
            result = normalize_health_status(root)
            self.assertEqual(len(result["metrics"]), 2)
            self.assertIsNone(result["daily"][0]["health_status_hr_value"])
            self.assertEqual(result["daily"][0]["health_status_reason_code"], "health_status_duplicate_metric_type")

    def test_missing_date_and_empty_metrics_are_explicit_review_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = [record(True, [metric("HR", 50)]), record("2026-07-22", [])]
            (root / "synthetic_healthStatusData.json").write_text(json.dumps(payload), encoding="utf-8")
            daily = normalize_health_status(root)["daily"]
            reasons = {row["health_status_reason_code"] for row in daily}
            self.assertEqual(reasons, {"health_status_missing_calendar_date", "health_status_no_metrics"})

    def test_unsafe_numbers_are_null_and_output_is_json_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = [record("2026-07-22", [metric("HR", 10**1000), metric("SPO2", "Infinity")])]
            payload[0]["outliersCount"] = 10**1000
            payload[0]["metrics"][0]["baselineUpperLimit"] = 10**1000
            (root / "synthetic_healthStatusData.json").write_text(json.dumps(payload), encoding="utf-8")
            result = normalize_health_status(root)
            self.assertIsNone(result["daily"][0]["outliers_count"])
            self.assertTrue(all(row["value"] is None for row in result["metrics"]))
            self.assertTrue(all(row["metric_normalization_status"] == "needs_review" for row in result["metrics"]))
            self.assertEqual(result["daily"][0]["health_status_reason_code"], "health_status_metric_requires_review")
            json.dumps(result, allow_nan=False)

    def test_exact_integer_boundary_applies_to_float_and_string_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            safe = (1 << 53) - 1
            payload = [
                record(
                    "2026-07-22",
                    [
                        metric("HR", float(safe)),
                        metric("SPO2", str(safe + 1)),
                        metric("RESPIRATION", float(safe + 1)),
                    ],
                )
            ]
            (root / "synthetic_healthStatusData.json").write_text(json.dumps(payload), encoding="utf-8")
            result = normalize_health_status(root)
            by_type = {row["metric_type"]: row for row in result["metrics"]}
            self.assertEqual(by_type["HR"]["value"], float(safe))
            self.assertIsNone(by_type["SPO2"]["value"])
            self.assertIsNone(by_type["RESPIRATION"]["value"])
            self.assertEqual(by_type["SPO2"]["metric_normalization_status"], "needs_review")
            json.dumps(result, allow_nan=False)

    def test_safe_zip_wrapper_exact_suffix_and_content_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root / "synthetic-export.zip", "w") as archive:
                archive.writestr(
                    "DI-Connect-Wellness/synthetic_healthStatusData.json",
                    json.dumps({"healthStatusData": [record("2026-07-22", [metric("HR", 55)])]}),
                )
                archive.writestr(
                    "DI-Connect-Wellness/not-health-status.json",
                    json.dumps([record("2026-07-23", [metric("HR", 65)])]),
                )
            first = normalize_health_status(root)
            (root / "unrelated.json").write_text("{}", encoding="utf-8")
            second = normalize_health_status(root)
            self.assertEqual(len(first["daily"]), 1)
            self.assertEqual(
                first["daily"][0]["health_status_daily_record_key"],
                second["daily"][0]["health_status_daily_record_key"],
            )
            self.assertIn("!DI-Connect-Wellness/", first["daily"][0]["source_path"])


if __name__ == "__main__":
    unittest.main()
