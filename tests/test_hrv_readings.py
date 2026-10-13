"""HRV readings follow the rules of the other daily datasets (stage A3d-2b).

A reading without a date, or with a value of another form, is left out and
announced; a reading without a value, such as one with FIT's invalid value
65535, is counted and not announced. One Export gives the same in a one-shot
run and as one Snapshot, and Run-All no longer gives
DAILY_METRICS_REVIEW_REQUIRED.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output  # noqa: F401
from garmin_running_data_normalizer.common.values import ABSENT, INVALID, VALID
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.fit.parser import fit_crc16
from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.normalizers.hrv import (
    READING_TIMESTAMP_LEFT_OUT,
    READING_VALUE_LEFT_OUT,
    _reading_date,
    _reading_value,
    normalize_hrv_daily_assets,
)
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import initialize_store, run_snapshot_all
from tests.test_hrv_normalizer import fit_timestamp
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, load, write_export
from tests.test_snapshot_unreadable_files import one_snapshot, register

VALUE_TIME = [(1, 2, 0x84), (253, 4, 0x86)]
NO_VALUE = 65535
NO_TIME = 0xFFFFFFFF


def hrv_fit(fields: list[tuple[int, int, int]], rows: list[bytes]) -> bytes:
    """A FIT file with one definition of message 370 and its records."""
    definition = bytes([0x40, 0x00, 0x00]) + struct.pack("<H", 370) + bytes([len(fields)])
    definition += b"".join(bytes(field) for field in fields)
    body = definition + b"".join(bytes([0x00]) + row for row in rows)
    payload = bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT" + body
    return payload + struct.pack("<H", fit_crc16(payload))


def reading(value: int, time: int) -> bytes:
    return struct.pack("<HI", value, time)


def day(number: int) -> int:
    """A FIT time at noon UTC of 2030-02-<number>, the same date in Tokyo."""
    return fit_timestamp(f"2030-02-{number:02d}T12:00:00Z")


# One FIT file for each kind of reading, each on its own date.
READINGS = {
    "valid": hrv_fit(VALUE_TIME, [reading(6400, day(1))]),
    "no_value_only": hrv_fit(VALUE_TIME, [reading(NO_VALUE, day(3))]),
    "no_value_and_value": hrv_fit(VALUE_TIME, [reading(NO_VALUE, day(4)), reading(6528, day(4))]),
    "no_date_with_value": hrv_fit(VALUE_TIME, [reading(6400, NO_TIME)]),
    "no_date_no_value": hrv_fit(VALUE_TIME, [reading(NO_VALUE, NO_TIME)]),
    "fraction": hrv_fit([(1, 4, 0x88), (253, 4, 0x86)], [struct.pack("<fI", 6400.5, day(5))]),
    "array": hrv_fit([(1, 4, 0x84), (253, 4, 0x86)], [struct.pack("<HHI", 6400, 6500, day(6))]),
    "time_too_large": hrv_fit([(1, 2, 0x84), (253, 8, 0x8F)], [struct.pack("<HQ", 6400, 10**18)]),
}
# The value of another form above, as it would be written and in milliseconds.
OTHER_FORM_TEXTS = ("6400.5", "50.00390625")
OLD_AUDIT_FIELDS = ("invalid_value_count", "missing_date_count", "review_required_count", "review_item_count")
AUDIT_FIELDS = (
    "status",
    "source_record_count",
    "accepted_record_count",
    "excluded_record_count",
    "excluded_reason_counts",
    "empty_record_count",
    "absent_value_counts",
    "same_value_duplicate_count",
    "disagreement_key_count",
)


def asset(name: str, data: bytes) -> DiscoveredAsset:
    return DiscoveredAsset("fit", name, None, len(data), hashlib.sha256(data).hexdigest(), data)


def hrv_export(root: Path, name: str, files: dict[str, bytes]) -> Path:
    """An Export with one Activity and these HRV FIT files."""
    source = write_export(root, name, [_activity("A1")])
    for relative, data in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return source


def metrics_files(readings: dict[str, bytes]) -> dict[str, bytes]:
    return {f"DI-Connect-Metrics/synthetic_{name}.fit": data for name, data in readings.items()}


def hrv_outcome(output: Path) -> dict[str, Any]:
    """What a run gives for HRV, whatever the form of the run."""
    summary = load(output / "run_summary.json")
    audit = load(output / "audit/hrv_daily.json")
    quality = load(output / "diagnostics/run_quality.json")
    daily = load(output / "qa/daily_metrics_summary.json")
    return {
        "status": summary["status"],
        "warnings": sorted(
            (item["code"], item.get("family", ""), item.get("dataset", ""), item.get("count", 1))
            for item in summary["warnings"]
        ),
        "hrv_result": {
            key: summary["family_results"]["hrv"].get(key)
            for key in ("status", "record_count", "left_out_row_count", "review_required_count", "warning_count")
        },
        "audit": {key: audit.get(key) for key in (*AUDIT_FIELDS, *OLD_AUDIT_FIELDS)},
        "rows": load(output / "normalized/hrv_daily.json"),
        "daily_summary": (daily["status"], daily["datasets"]["hrv_daily"]["audit_status"]),
        "run_quality": {
            "excluded": {key: value for key, value in quality["excluded"].items() if key != "authority_references"},
            "warnings": quality["warnings"],
        },
    }


def hrv_both_forms(test: unittest.TestCase, root: Path, source: Path, name: str) -> Path:
    """Run one Export once and as one Snapshot; check that they agree, and
    return the output of the one-shot run."""
    one_shot = root / f"{name}-one-shot"
    run_all(source, one_shot)
    snapshot = one_snapshot(root, source, f"{name}-snapshot")
    test.assertEqual(hrv_outcome(snapshot), hrv_outcome(one_shot))
    return one_shot


def day_values(output: Path) -> list[tuple[str, float | None]]:
    return [(row["calendar_date"], row["hrv_value"]) for row in load(output / "normalized/hrv_daily.json")]


class ReadingRuleTest(unittest.TestCase):
    def test_how_the_value_of_a_reading_is_read(self) -> None:
        cases = (
            (6400, (VALID, 50.0)),
            (6400.0, (VALID, 50.0)),
            (NO_VALUE, (ABSENT, None)),
            (float(NO_VALUE), (ABSENT, None)),
            (None, (ABSENT, None)),
            (6400.5, (INVALID, None)),
            (math.nan, (INVALID, None)),
            ([6400, 6500], (INVALID, None)),
            ("6400", (INVALID, None)),
            (2**53, (INVALID, None)),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(_reading_value(raw), expected)

    def test_how_the_date_of_a_reading_is_made(self) -> None:
        cases = (
            (day(1), "2030-02-01"),
            (float(day(1)), "2030-02-01"),
            (NO_TIME, None),
            (None, None),
            (10**18, None),
            (day(1) + 0.5, None),
            ([day(1)], None),
            ("2030-02-01", None),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(_reading_date(raw, "Asia/Tokyo"), expected)


class HrvReadingsTest(unittest.TestCase):
    def test_each_kind_of_reading(self) -> None:
        timestamp = READING_TIMESTAMP_LEFT_OUT
        value = READING_VALUE_LEFT_OUT
        cases = {
            # name: (day values, excluded reasons, empty records, absent values)
            "valid": ([("2030-02-01", 50.0)], {}, None, {}),
            "no_value_only": ([], {}, None, {"hrv_value": 1}),
            "no_value_and_value": ([("2030-02-04", 51.0)], {}, None, {"hrv_value": 1}),
            "no_date_with_value": ([], {timestamp: 1}, None, {}),
            "no_date_no_value": ([], {}, 1, {}),
            "fraction": ([], {value: 1}, None, {}),
            "array": ([], {value: 1}, None, {}),
            "time_too_large": ([], {timestamp: 1}, None, {}),
        }
        more = {
            "whole_number_written_with_a_point": (
                hrv_fit([(1, 4, 0x88), (253, 4, 0x86)], [struct.pack("<fI", 6400.0, day(7))]),
                ([("2030-02-07", 50.0)], {}, None, {}),
            ),
            "time_written_with_a_point": (
                hrv_fit([(1, 2, 0x84), (253, 8, 0x89)], [struct.pack("<Hd", 6400, float(day(8)))]),
                ([("2030-02-08", 50.0)], {}, None, {}),
            ),
            "no_time_field": (hrv_fit([(1, 2, 0x84)], [struct.pack("<H", 6400)]), ([], {timestamp: 1}, None, {})),
            "no_value_field": (hrv_fit([(253, 4, 0x86)], [struct.pack("<I", day(9))]), ([], {}, None, {"hrv_value": 1})),
            "not_a_number": (
                hrv_fit([(1, 4, 0x88), (253, 4, 0x86)], [struct.pack("<fI", math.nan, day(10))]),
                ([], {value: 1}, None, {}),
            ),
        }
        files = {name: (READINGS[name], expected) for name, expected in cases.items()} | more
        for name, (data, (rows, reasons, empty, absent)) in files.items():
            with self.subTest(name=name):
                result = normalize_hrv_daily_assets([asset(f"{name}.fit", data)])
                audit = result["audit"]
                self.assertEqual([(row["calendar_date"], row["hrv_value"]) for row in result["records"]], rows)
                self.assertEqual(audit["excluded_reason_counts"], reasons)
                self.assertEqual(audit["excluded_record_count"], sum(reasons.values()))
                self.assertEqual(audit.get("empty_record_count"), empty)
                self.assertEqual(audit["absent_value_counts"], absent)
                self.assertEqual(audit["status"], "PASS")
                for field in OLD_AUDIT_FIELDS:
                    self.assertNotIn(field, audit)

    def test_every_reading_is_counted_once(self) -> None:
        result = normalize_hrv_daily_assets([asset(f"{name}.fit", data) for name, data in READINGS.items()])
        audit = result["audit"]
        in_rows = sum(row["record_count_for_date"] for row in result["records"])
        self.assertEqual(
            audit["source_record_count"],
            in_rows
            + audit["absent_value_counts"]["hrv_value"]
            + audit["excluded_record_count"]
            + audit["empty_record_count"],
        )
        self.assertEqual(audit["source_record_count"], 9)


class HrvRunTest(unittest.TestCase):
    def test_readings_in_one_shot_and_snapshot_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = hrv_export(root, "export", metrics_files(READINGS))
            output = hrv_both_forms(self, root, source, "readings")
            summary = load(output / "run_summary.json")
            self.assertEqual(summary["status"], "PARTIAL_SUCCESS")
            codes = {item["code"] for item in summary["warnings"]}
            self.assertNotIn("DAILY_METRICS_REVIEW_REQUIRED", codes)
            self.assertNotIn("DATA_VALUE_INVALID", codes)
            [left_out] = [item for item in summary["warnings"] if item["code"] == "DATA_ROW_LEFT_OUT"]
            self.assertEqual(
                (left_out["family"], left_out["dataset"], left_out["count"]), ("hrv", "hrv_daily", 4)
            )
            self.assertEqual(day_values(output), [("2030-02-01", 50.0), ("2030-02-04", 51.0)])
            outcome = hrv_outcome(output)
            self.assertEqual(
                outcome["audit"],
                {
                    "status": "PASS",
                    "source_record_count": 9,
                    "accepted_record_count": 2,
                    "excluded_record_count": 4,
                    "excluded_reason_counts": {READING_VALUE_LEFT_OUT: 2, READING_TIMESTAMP_LEFT_OUT: 2},
                    "empty_record_count": 1,
                    "absent_value_counts": {"hrv_value": 2},
                    "same_value_duplicate_count": 0,
                    "disagreement_key_count": 0,
                    **{field: None for field in OLD_AUDIT_FIELDS},
                },
            )
            self.assertEqual(outcome["hrv_result"]["left_out_row_count"], 4)
            self.assertEqual(outcome["hrv_result"]["review_required_count"], 0)
            self.assertEqual(outcome["daily_summary"], ("PASS", "PASS"))
            self.assertIn(
                "- Rows left out: 4 (`hrv_daily` 4)", (output / "START_HERE.md").read_text(encoding="utf-8")
            )

    def test_readings_without_a_value_are_not_announced(self) -> None:
        readings = {name: READINGS[name] for name in ("valid", "no_value_only", "no_value_and_value", "no_date_no_value")}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = hrv_both_forms(self, root, hrv_export(root, "export", metrics_files(readings)), "no-value")
            summary = load(output / "run_summary.json")
            self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
            self.assertEqual([item for item in summary["warnings"] if item.get("family") == "hrv"], [])
            audit = load(output / "audit/hrv_daily.json")
            self.assertEqual(audit["absent_value_counts"], {"hrv_value": 2})
            self.assertEqual(audit["empty_record_count"], 1)
            self.assertEqual(audit["excluded_record_count"], 0)
            self.assertEqual(day_values(output), [("2030-02-01", 50.0), ("2030-02-04", 51.0)])

    def test_copies_within_one_export_or_snapshot_are_counted_alike(self) -> None:
        readings = {name: READINGS[name] for name in ("valid", "no_value_and_value", "no_date_with_value", "no_date_no_value")}
        files = metrics_files(readings) | {
            f"DI-Connect-Uploaded-Files/copy_{name}.fit": data for name, data in readings.items()
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = hrv_both_forms(self, root, hrv_export(root, "export", files), "copies")
            audit = load(output / "audit/hrv_daily.json")
            self.assertEqual(audit["source_record_count"], 10)
            self.assertEqual(audit["excluded_reason_counts"], {READING_TIMESTAMP_LEFT_OUT: 2})
            self.assertEqual(audit["empty_record_count"], 2)
            self.assertEqual(audit["absent_value_counts"], {"hrv_value": 2})
            self.assertEqual(audit["same_value_duplicate_count"], 2)

    def test_two_snapshots_of_one_export_count_as_one_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = hrv_export(root, "export", metrics_files(READINGS))
            one_shot = root / "one-shot"
            run_all(source, one_shot)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source, "S1", 1)
            register(store, source, "S2", 2)
            snapshots = root / "snapshots"
            run_snapshot_all(store, snapshots)
            for output in (one_shot, snapshots):
                with self.subTest(output=output.name):
                    outcome = hrv_outcome(output)
                    self.assertEqual(outcome["audit"], hrv_outcome(one_shot)["audit"])
                    self.assertEqual(outcome["rows"], hrv_outcome(one_shot)["rows"])
                    self.assertEqual(
                        [item for item in outcome["warnings"] if item[1] == "hrv"],
                        [("DATA_ROW_LEFT_OUT", "hrv", "hrv_daily", 4)],
                    )

    def test_values_of_another_form_reach_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = hrv_export(root, "export", metrics_files(READINGS))
            output = root / "output"
            run_all(source, output, external_safe_pack=True)
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)

            def refuse(name: str) -> Any:
                raise ValueError(name)

            for path in sorted(output.rglob("*")):
                if not path.is_file():
                    continue
                data = path.read_bytes()
                with self.subTest(path=path.relative_to(output).as_posix()):
                    for text in OTHER_FORM_TEXTS:
                        self.assertNotIn(text.encode(), data)
                    if path.suffix == ".json":
                        json.loads(data.decode("utf-8"), parse_constant=refuse)
            for archive_path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with zipfile.ZipFile(archive_path) as archive:
                    for name in archive.namelist():
                        with self.subTest(archive=archive_path.name, member=name):
                            for text in OTHER_FORM_TEXTS:
                                self.assertNotIn(text.encode(), archive.read(name))


if __name__ == "__main__":
    unittest.main()
