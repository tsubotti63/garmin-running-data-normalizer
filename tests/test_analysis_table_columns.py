from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from garmin_running_data_normalizer.run_all import (
    ACTIVITIES_CSV_COLUMNS,
    EXTERNAL_SAFE_CSV_COLUMNS,
    run_all,
)
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from tests.fit_fixture_factory import synthetic_fit
from tests.test_fit_running_dynamics import (
    FIT_SESSION_START_MS,
    LAP_RAW,
    SESSION_RAW,
)

BASE_COLUMNS = (
    "garmin_activity_key",
    "activity_date_local",
    "activity_datetime_local",
    "activity_type",
    "sport_type",
    "distance_m",
    "duration_sec",
    "avg_hr",
    "max_hr",
    "avg_power",
    "max_power",
    "avg_run_cadence",
    "training_effect_label",
    "activity_training_load",
    "lap_count",
)
DURATION_COLUMNS = {
    "elapsed_duration_sec": "elapsed_duration_ms",
    "moving_duration_sec": "moving_duration_ms",
}
FIT_COLUMNS = {
    "fit_avg_vertical_oscillation_mm": "avg_vertical_oscillation_mm",
    "fit_avg_stance_time_ms": "avg_stance_time_ms",
    "fit_avg_stance_time_percent": "avg_stance_time_percent",
    "fit_avg_stance_time_balance_percent": "avg_stance_time_balance_percent",
    "fit_avg_vertical_ratio_percent": "avg_vertical_ratio_percent",
    "fit_avg_step_length_mm": "avg_step_length_mm",
    "fit_total_ascent_m": "total_ascent",
    "fit_total_descent_m": "total_descent",
}


def write_export(root: Path) -> Path:
    fitness = root / "DI-Connect-Fitness"
    fitness.mkdir(parents=True)
    linked = {
        "activityId": 1,
        "activityType": "running",
        "sportType": "RUNNING",
        "startTimeGmt": FIT_SESSION_START_MS + 30_000,
        "distance": 1_000_000,
        "duration": 3_500_000,
        "elapsedDuration": 3_610_500,
        "movingDuration": 3_480_250,
        "name": "Synthetic linked",
    }
    unlinked = {
        "activityId": 2,
        "activityType": "running",
        "sportType": "RUNNING",
        "startTimeGmt": FIT_SESSION_START_MS + 30 * 86_400_000,
        "distance": 500_000,
        "duration": 1_800_000,
        "elapsedDuration": 1_860_000,
        "name": "Synthetic unlinked",
    }
    (fitness / "synthetic_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": [linked, unlinked]}]),
        encoding="utf-8",
    )
    uploaded = root / "DI-Connect-Uploaded-Files"
    uploaded.mkdir()
    (uploaded / "synthetic_activity.fit").write_bytes(
        synthetic_fit(
            session_running_dynamics=SESSION_RAW,
            lap_running_dynamics=LAP_RAW,
        )
    )
    return root


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = {row["garmin_activity_key"]: row for row in reader}
        return list(reader.fieldnames or []), rows


def cell(value: object) -> str:
    return "" if value is None else str(value)


class AnalysisTableColumnsTest(unittest.TestCase):
    def test_columns_are_appended_and_follow_explicit_fit_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export")
            output = root / "output"
            run_all(export, output, external_safe_pack=True)

            header, rows = read_rows(output / "analysis/activities.csv")
            self.assertEqual(
                header,
                [*BASE_COLUMNS, *DURATION_COLUMNS, *FIT_COLUMNS],
            )
            self.assertEqual(tuple(header), ACTIVITIES_CSV_COLUMNS)

            activities = {
                item["garmin_activity_key"]: item
                for item in load(output / "normalized/activities.json")
            }
            links = load(output / "normalized/activity_fit_links.json")
            sessions = {
                item["fit_session_key"]: item
                for item in load(output / "normalized/fit_sessions.json")
            }
            self.assertEqual(len(links), 1)
            linked_key = links[0]["garmin_activity_key"]
            session = sessions[links[0]["fit_session_key"]]
            unlinked_key = next(key for key in rows if key != linked_key)

            for key, row in rows.items():
                for column, source in DURATION_COLUMNS.items():
                    value = activities[key][source]
                    self.assertEqual(
                        row[column],
                        "" if value is None else str(float(value) / 1000.0),
                        column,
                    )
            self.assertEqual(rows[linked_key]["elapsed_duration_sec"], "3610.5")
            self.assertEqual(rows[linked_key]["moving_duration_sec"], "3480.25")
            self.assertEqual(rows[unlinked_key]["moving_duration_sec"], "")

            for column, source in FIT_COLUMNS.items():
                self.assertEqual(rows[linked_key][column], cell(session[source]), column)
                self.assertNotEqual(rows[linked_key][column], "", column)
                self.assertEqual(rows[unlinked_key][column], "", column)
            self.assertEqual(rows[linked_key]["fit_avg_vertical_oscillation_mm"], "84.3")
            self.assertEqual(rows[linked_key]["fit_avg_vertical_ratio_percent"], "7.89")

            with zipfile.ZipFile(output / "analysis/external_safe_handoff.zip") as archive:
                safe = archive.read("safe/activities_monthly.csv").decode("utf-8")
            safe_header = next(csv.reader(io.StringIO(safe)))
            self.assertEqual(tuple(safe_header), EXTERNAL_SAFE_CSV_COLUMNS)
            self.assertFalse(
                any(
                    name.startswith("fit_") or name in DURATION_COLUMNS
                    for name in safe_header
                )
            )

    def test_projection_declares_the_derived_and_joined_columns(self) -> None:
        expected = {
            "path": "analysis/activities.csv",
            "canonical": False,
            "projection_of": "activities",
            "selection_rule": None,
            "derived_columns": {
                "source_dataset": "activities",
                "rule": "milliseconds divided by 1000",
                "columns": [
                    {"column": column, "source_field": source}
                    for column, source in DURATION_COLUMNS.items()
                ],
            },
            "joined_columns": {
                "source_dataset": "fit_sessions",
                "join_via": "activity_fit_links",
                "join_rule": "explicit one-to-one links only; never timestamp proximity",
                "missing_value": (
                    "empty when the activity has no explicit link or the FIT "
                    "value is null"
                ),
                "columns": [
                    {"column": column, "source_field": source}
                    for column, source in FIT_COLUMNS.items()
                ],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(write_export(root / "export"), output)
            catalog = load(output / "SCHEMA_CATALOG.json")
            context = load(output / "ANALYSIS_CONTEXT.json")
            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            handoff = (output / "ANALYSIS_HANDOFF.md").read_text(encoding="utf-8")

        catalog_activities = next(
            item for item in catalog["datasets"] if item["dataset"] == "activities"
        )
        self.assertEqual(catalog_activities["derived_projection"], expected)
        context_activities = next(
            item
            for item in context["datasets"]
            if (item.get("dataset") or item.get("name")) == "activities"
        )
        self.assertEqual(context_activities["derived_projection"], expected)
        self.assertIn("Its `fit_*` columns come from the FIT session", start_here)
        self.assertIn("The `fit_*` columns in `analysis/activities.csv`", handoff)

    def test_snapshot_run_all_writes_the_same_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export")
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
            self.assertEqual(
                (root / "run-all/analysis/activities.csv").read_bytes(),
                (root / "snapshot-run-all/analysis/activities.csv").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
