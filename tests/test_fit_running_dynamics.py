from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from garmin_running_data_normalizer.fit.parser import parse_fit_export
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from tests.fit_fixture_factory import synthetic_fit

RUNNING_DYNAMICS_FIELDS = (
    "avg_vertical_oscillation_mm",
    "avg_stance_time_ms",
    "avg_stance_time_percent",
    "avg_stance_time_balance_percent",
    "avg_vertical_ratio_percent",
    "avg_step_length_mm",
)
# Raw uint16 values in factory order: vertical oscillation (mm, scale 10),
# stance time percent (scale 100), stance time (ms, scale 10), vertical ratio
# (scale 100), stance time balance (scale 100), step length (mm, scale 10).
SESSION_RAW = (843, 3698, 2421, 789, 4884, 10656)
LAP_RAW = (812, 3650, 2400, 770, 5005, 10500)
SESSION_VALUES = {
    "avg_vertical_oscillation_mm": 84.3,
    "avg_stance_time_ms": 242.1,
    "avg_stance_time_percent": 36.98,
    "avg_stance_time_balance_percent": 48.84,
    "avg_vertical_ratio_percent": 7.89,
    "avg_step_length_mm": 1065.6,
}
LAP_VALUES = {
    "avg_vertical_oscillation_mm": 81.2,
    "avg_stance_time_ms": 240.0,
    "avg_stance_time_percent": 36.5,
    "avg_stance_time_balance_percent": 50.05,
    "avg_vertical_ratio_percent": 7.7,
    "avg_step_length_mm": 1050.0,
}
INVALID = (0xFFFF,) * 6
# The synthetic FIT session starts at FIT time 1_000_000 (1990-01-11T13:46:40Z).
FIT_SESSION_START_MS = int(
    datetime(1990, 1, 11, 13, 46, 40, tzinfo=timezone.utc).timestamp() * 1000
)


def write_export(root: Path, fit_bytes: bytes) -> Path:
    fitness = root / "DI-Connect-Fitness"
    fitness.mkdir(parents=True)
    activity = {
        "activityId": 1,
        "activityType": "running",
        "sportType": "RUNNING",
        "startTimeGmt": FIT_SESSION_START_MS + 30_000,
        "distance": 1_000_000,
        "duration": 3_500_000,
        "name": "Synthetic 1",
    }
    (fitness / "synthetic_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": [activity]}]), encoding="utf-8"
    )
    uploaded = root / "DI-Connect-Uploaded-Files"
    uploaded.mkdir()
    (uploaded / "synthetic_activity.fit").write_bytes(fit_bytes)
    return root


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


class FitRunningDynamicsTest(unittest.TestCase):
    def test_values_follow_the_fit_profile_scales(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export = write_export(
                Path(directory) / "export",
                synthetic_fit(
                    session_running_dynamics=SESSION_RAW,
                    lap_running_dynamics=LAP_RAW,
                ),
            )
            sessions, laps, audit = parse_fit_export(export)

        session = sessions[0]
        lap = laps[0]
        for field, expected in SESSION_VALUES.items():
            self.assertEqual(session[field], expected, field)
        for field, expected in LAP_VALUES.items():
            self.assertEqual(lap[field], expected, field)
        # JSON keeps the same plain decimal form as the existing FIT scales.
        self.assertEqual(
            json.dumps([session[field] for field in RUNNING_DYNAMICS_FIELDS]),
            "[84.3, 242.1, 36.98, 48.84, 7.89, 1065.6]",
        )
        self.assertEqual(
            json.dumps([lap[field] for field in RUNNING_DYNAMICS_FIELDS]),
            "[81.2, 240.0, 36.5, 50.05, 7.7, 1050.0]",
        )
        self.assertEqual(audit[0]["invalid_sentinel_count"], 0)

    def test_files_without_running_dynamics_keep_session_nulls_and_omit_lap_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export = write_export(Path(directory) / "export", synthetic_fit())
            sessions, laps, _audit = parse_fit_export(export)

        for field in RUNNING_DYNAMICS_FIELDS:
            self.assertIn(field, sessions[0])
            self.assertIsNone(sessions[0][field])
            self.assertNotIn(field, laps[0])

    def test_invalid_values_are_null_counted_and_do_not_change_the_run_status(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = write_export(root / "plain", synthetic_fit())
            invalid = write_export(
                root / "invalid",
                synthetic_fit(
                    session_running_dynamics=INVALID,
                    lap_running_dynamics=INVALID,
                ),
            )
            run_all(plain, root / "plain-output")
            run_all(invalid, root / "invalid-output")

            plain_summary = load(root / "plain-output/run_summary.json")
            invalid_summary = load(root / "invalid-output/run_summary.json")
            self.assertEqual(invalid_summary["status"], plain_summary["status"])
            self.assertEqual(
                invalid_summary["warning_count"], plain_summary["warning_count"]
            )
            self.assertEqual(
                invalid_summary["error_count"], plain_summary["error_count"]
            )

            session = load(root / "invalid-output/normalized/fit_sessions.json")[0]
            lap = load(root / "invalid-output/normalized/fit_laps.json")[0]
            for field in RUNNING_DYNAMICS_FIELDS:
                self.assertIsNone(session[field])
                self.assertIn(field, lap)
                self.assertIsNone(lap[field])

            plain_audit = load(root / "plain-output/audit/fit_audit.json")[0]
            invalid_audit = load(root / "invalid-output/audit/fit_audit.json")[0]
            added = {
                key: count
                for key, count in invalid_audit["invalid_sentinel_counts"].items()
                if plain_audit["invalid_sentinel_counts"].get(key) != count
            }
            self.assertEqual(
                added,
                {
                    **{f"session.{field}": 1 for field in RUNNING_DYNAMICS_FIELDS},
                    **{f"lap.{field}": 1 for field in RUNNING_DYNAMICS_FIELDS},
                },
            )
            self.assertEqual(
                invalid_audit["invalid_sentinel_count"],
                plain_audit["invalid_sentinel_count"] + 12,
            )

    def test_run_all_and_snapshot_run_all_report_the_same_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(
                root / "export",
                synthetic_fit(
                    session_running_dynamics=SESSION_RAW,
                    lap_running_dynamics=LAP_RAW,
                ),
            )
            run_all(export, root / "run-all")
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            register_snapshot(
                store,
                export,
                snapshot_label="S1",
                export_requested_at="2030-01-01T00:00:00+00:00",
                export_downloaded_at="2030-01-01T01:00:00+00:00",
                export_observed_at="2030-01-01T02:00:00+00:00",
                confirm_complete=True,
            )
            run_snapshot_all(store, root / "snapshot-run-all")

            for name in ("run-all", "snapshot-run-all"):
                session = load(root / name / "normalized/fit_sessions.json")[0]
                lap = load(root / name / "normalized/fit_laps.json")[0]
                self.assertEqual(
                    {field: session[field] for field in RUNNING_DYNAMICS_FIELDS},
                    SESSION_VALUES,
                    name,
                )
                self.assertEqual(
                    {field: lap[field] for field in RUNNING_DYNAMICS_FIELDS},
                    LAP_VALUES,
                    name,
                )

            catalog = load(root / "run-all/SCHEMA_CATALOG.json")
            datasets = {item["dataset"]: item for item in catalog["datasets"]}
            units = {
                "avg_vertical_oscillation_mm": "millimetre",
                "avg_stance_time_ms": "millisecond",
                "avg_stance_time_percent": "percent",
                "avg_stance_time_balance_percent": "percent",
                "avg_vertical_ratio_percent": "percent",
                "avg_step_length_mm": "millimetre",
            }
            for dataset, required in (("fit_sessions", True), ("fit_laps", False)):
                fields = {item["field"]: item for item in datasets[dataset]["fields"]}
                for field, unit in units.items():
                    self.assertEqual(fields[field]["logical_type"], "number")
                    self.assertEqual(fields[field]["unit_or_domain"], unit)
                    self.assertEqual(fields[field]["required"], required)
                    self.assertTrue(fields[field]["nullable"])
            self.assertIn(
                "not converted to a left or right side",
                datasets["fit_laps"]["fields"][
                    [item["field"] for item in datasets["fit_laps"]["fields"]].index(
                        "avg_stance_time_balance_percent"
                    )
                ]["notes"],
            )


if __name__ == "__main__":
    unittest.main()
