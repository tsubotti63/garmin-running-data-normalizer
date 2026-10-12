from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.normalizers.daily_metrics import SNAPSHOT_NUMBERS_FIELD
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from tests.test_snapshot_lifecycle import _activity, _write_snapshot

ACCOUNT = "synthetic-account-boundary"
SNAPSHOT_SLEEP_INPUT = "approved_input/DI-Connect-Wellness/snapshot_sleepData.json"
V1_4_SNAPSHOT_SLEEP_FIELDS = (
    "calendarDate",
    "sleepStartTimestampGMT",
    "sleepEndTimestampGMT",
    "sleepTimeSeconds",
    "totalSleepSeconds",
    "deepSleepSeconds",
    "lightSleepSeconds",
    "remSleepSeconds",
    "awakeSleepSeconds",
    "sleepScores",
)


def register(store: Path, source: Path, label: str, day: int) -> dict[str, object]:
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
        confirm_complete=True,
    )


def sleep_row(day: int, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "calendarDate": f"2030-01-{day:02d}",
        "sleepStartTimestampGMT": f"2030-01-{day - 1:02d}T14:00:00Z",
        "sleepEndTimestampGMT": f"2030-01-{day - 1:02d}T22:00:00Z",
    }
    row.update(fields)
    return row


def write_sleep_export(root: Path, name: str, rows: list[dict[str, object]]) -> Path:
    source = root / name
    _write_snapshot(source, [_activity("A1")])
    wellness = source / "DI-Connect-Wellness"
    wellness.mkdir()
    (wellness / "synthetic_sleepData.json").write_text(json.dumps(rows), encoding="utf-8")
    return source


def by_calendar_date(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(rows, key=lambda row: str(row["calendarDate"]))


class SnapshotSleepFieldTest(unittest.TestCase):
    def test_sleep_rows_without_added_fields_build_the_v1_4_records(self) -> None:
        first_day = sleep_row(
            2,
            sleepTimeSeconds=27000,
            deepSleepSeconds=3600,
            lightSleepSeconds=18000,
            remSleepSeconds=5400,
            awakeSleepSeconds=600,
            sleepScores={"overall": {"value": 80}},
            retro=False,
            sleepWindowConfirmationType="ENHANCED_CONFIRMED_FINAL",
            userProfilePK="PRIVATE-ACCOUNT",
        )
        second_day = sleep_row(3, totalSleepSeconds=26000, awakeSleepSeconds=None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, write_sleep_export(root, "source-1", [first_day]), "S1", 1)
            register(
                store,
                write_sleep_export(root, "source-2", [first_day, second_day]),
                "S2",
                2,
            )

            build_approved_input(store, root / "build")

            rows = json.loads((root / "build" / SNAPSHOT_SLEEP_INPUT).read_text(encoding="utf-8"))
            # Each record carries the import numbers of the Snapshots that gave it.
            expected = [
                {
                    **{field: row[field] for field in V1_4_SNAPSHOT_SLEEP_FIELDS if field in row},
                    SNAPSHOT_NUMBERS_FIELD: numbers,
                }
                for row, numbers in ((first_day, [1, 2]), (second_day, [2]))
            ]
            self.assertEqual(by_calendar_date(rows), expected)

    def test_sleep_values_that_differ_across_snapshots_are_kept_with_their_snapshots(self) -> None:
        cases = {
            "value differs": (
                {"overallScore": 80},
                {"overallScore": 81},
                {"sleep_score": [(80, [1]), (81, [2])]},
            ),
            "field appears": ({}, {"overallScore": 80}, {}),
            "snake_case stage differs": (
                {"deep_sleep_seconds": 3600},
                {"deep_sleep_seconds": 3660},
                {
                    "sleep_duration_minutes_ex_awake": [(60.0, [1]), (61.0, [2])],
                    "sleep_stage_deep_minutes": [(60.0, [1]), (61.0, [2])],
                },
            ),
        }
        for name, (first_fields, second_fields, expected) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = root / "store"
                initialize_store(store, ACCOUNT)
                for day, fields in ((1, first_fields), (2, second_fields)):
                    rows = [sleep_row(2, sleepTimeSeconds=27000, **fields)]
                    register(store, write_sleep_export(root, f"source-{day}", rows), f"S{day}", day)

                result = run_snapshot_all(store, root / "output")

                self.assertEqual(result["exit_code"], 0)
                [row] = json.loads(
                    (root / "output/normalized/sleep_daily.json").read_text(encoding="utf-8")
                )
                self.assertEqual(row["disagreeing_fields"], sorted(expected))
                for field in expected:
                    self.assertIsNone(row[field])
                audit = json.loads(
                    (root / "output/audit/sleep_daily.json").read_text(encoding="utf-8")
                )
                fields = {
                    item["field"]: [
                        (value["value"], value["snapshots"]) for value in item["values"]
                    ]
                    for entry in audit["disagreements"]
                    for item in entry["fields"]
                }
                self.assertEqual(fields, expected)
                if not expected:
                    # The Snapshot without a score does not disagree.
                    self.assertEqual(row["sleep_score"], 80)
                    self.assertEqual(audit["absent_value_counts"], {"sleep_score": 1})

    def test_snapshot_sleep_matches_single_export_run_all(self) -> None:
        rows = [
            sleep_row(
                2,
                deep_sleep_seconds=3600,
                light_sleep_seconds=18000,
                rem_sleep_seconds=5400,
                awake_sleep_seconds=600,
                overallScore=82,
            ),
            sleep_row(3, durationInSeconds=27000, sleepScore=75),
            sleep_row(4, sleepDuration=26400),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_sleep_export(root, "source", rows)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source, "S1", 1)

            run_all(source, root / "direct")
            run_snapshot_all(store, root / "snapshot")

            direct = json.loads(
                (root / "direct/normalized/sleep_daily.json").read_text(encoding="utf-8")
            )
            snapshot = json.loads(
                (root / "snapshot/normalized/sleep_daily.json").read_text(encoding="utf-8")
            )
            self.assertEqual(snapshot, direct)
            observed = {
                row["sleep_day"]: (
                    row["sleep_duration_minutes_ex_awake"],
                    row["sleep_stage_deep_minutes"],
                    row["sleep_awake_minutes"],
                    row["sleep_score"],
                )
                for row in snapshot
            }
            self.assertEqual(
                observed,
                {
                    "2030-01-02": (450.0, 60.0, 10.0, 82),
                    "2030-01-03": (450.0, None, None, 75),
                    "2030-01-04": (440.0, None, None, None),
                },
            )


if __name__ == "__main__":
    unittest.main()
