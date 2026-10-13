"""Values of a form that their field does not take are left empty, kept in the
audit records, and announced, alike in one-shot and Snapshot runs (stage
A3d-2a); an empty value is no value."""

from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.common.values import (
    ABSENT,
    INVALID,
    LARGEST_NUMBER,
    VALID,
    ValueReader,
    json_safe,
    read_value,
)
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.fit.parser import fit_crc16
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.runner import GoldenPathError, run_activities
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    run_snapshot_all,
)
from tests.fit_fixture_factory import _definition, _record
from tests.test_repeated_records import audit, table
from tests.test_rows_left_out import (
    DATE,
    FILES,
    KEPT,
    STAMP,
    both_forms,
    export_with,
    record_both_forms,
    records_export,
    summary_of,
)
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, gear, load, personal_record, write_export
from tests.test_snapshot_unreadable_files import one_snapshot, register

LACTATE_FILE = "DI-Connect-Wellness/synthetic_userBioMetrics.json"


def value_warnings(output: Path) -> dict[str, int]:
    """The warnings about values of another form, by dataset (or family)."""
    return {
        str(item.get("dataset") or item["family"]): int(item["count"])
        for item in summary_of(output)["warnings"]
        if item["code"] == "DATA_VALUE_INVALID"
    }


def kept_values(output: Path) -> dict[str, Any]:
    """Every value of another form that the audit records keep, without the
    Snapshot numbers, which only a Snapshot run gives."""
    found: dict[str, Any] = {}
    for path in sorted((output / "audit").glob("*.json")):
        value = load(path)
        entries = value if isinstance(value, list) else [value]
        for index, entry in enumerate(entries):
            if isinstance(entry, dict) and "invalid_values" in entry:
                found[f"{path.name}[{index}]"] = {
                    "counts": entry["invalid_value_counts"],
                    "values": [
                        {key: item[key] for key in item if key != "snapshots"}
                        for item in entry["invalid_values"]
                    ],
                }
    return found


def fit_file(messages: list[tuple[int, int, list[tuple[int, int, int]], list[bytes]]]) -> bytes:
    """A FIT file: for each (local, global, fields, records) a definition and its records."""
    body = bytearray()
    for local, global_message, fields, records in messages:
        body.extend(_definition(local, global_message, fields))
        for values in records:
            body.extend(_record(local, values))
    header = bytes([14, 0x20]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT"
    header += struct.pack("<H", fit_crc16(header))
    payload = header + bytes(body)
    return payload + struct.pack("<H", fit_crc16(payload))


SESSION_BASE = [(2, 4, 0x86), (7, 4, 0x86), (8, 4, 0x86), (9, 4, 0x86)]


def session_values(start: int = 1_000_000) -> bytes:
    return struct.pack("<IIII", start, 3_600_000, 3_500_000, 1_000_000)


class ValueRuleTest(unittest.TestCase):
    def test_how_a_value_fits_its_field(self) -> None:
        cases = (
            (5, "number", (VALID, 5)),
            (5.5, "number", (VALID, 5.5)),
            (LARGEST_NUMBER, "number", (VALID, LARGEST_NUMBER)),
            (LARGEST_NUMBER + 1, "number", (INVALID, None)),
            (10**400, "number", (INVALID, None)),
            (float("nan"), "number", (INVALID, None)),
            (float("inf"), "number", (INVALID, None)),
            ("5", "number", (INVALID, None)),
            (True, "number", (INVALID, None)),
            ([1], "number", (INVALID, None)),
            ({"v": 1}, "number", (INVALID, None)),
            # An empty value is no value, whatever the field.
            (None, "number", (ABSENT, None)),
            ("", "number", (ABSENT, None)),
            ([], "number", (ABSENT, None)),
            ({}, "number", (ABSENT, None)),
            # A whole number written with a decimal point is an integer.
            (3.0, "integer", (VALID, 3)),
            (3.5, "integer", (INVALID, None)),
            ("", "string", (VALID, "")),
            ("x", "string", (VALID, "x")),
            (5, "string", (INVALID, None)),
            ([], "string", (ABSENT, None)),
            (False, "boolean", (VALID, False)),
            ("true", "boolean", (INVALID, None)),
            (0, "boolean", (INVALID, None)),
            ("A1", "integer|string", (VALID, "A1")),
            (7.0, "integer|string", (VALID, 7)),
        )
        for value, logical_type, expected in cases:
            with self.subTest(value=repr(value)[:24], logical_type=logical_type):
                self.assertEqual(read_value(value, logical_type), expected)

    def test_the_reader_keeps_the_values_of_another_form(self) -> None:
        values = ValueReader()
        self.assertIsNone(values.number("5", "steps"))
        self.assertIsNone(values.number(0, "race_time_5k_sec", positive=True))
        self.assertIsNone(values.text("", "level"))
        self.assertIsNone(values.integer({}, "lap_count"))
        self.assertEqual(values.number(5, "steps"), 5)
        self.assertEqual(values.problems, [("steps", "5"), ("race_time_5k_sec", 0)])

    def test_a_number_that_is_not_finite_is_kept_as_strict_json(self) -> None:
        self.assertEqual(
            json_safe([float("nan"), {"a": float("-inf")}, 1.5]),
            [{"non_finite_number": "NaN"}, {"a": {"non_finite_number": "-Infinity"}}, 1.5],
        )


class DailyValuesTest(unittest.TestCase):
    def test_daily_values_of_another_form_are_left_empty_alike(self) -> None:
        files = {
            FILES["uds_daily"]: [
                {**KEPT["uds_daily"], "totalSteps": "5"},
                {"calendarDate": "2030-02-02", "totalSteps": 7, "restingHeartRate": 10**20},
                {"calendarDate": "2030-02-03", "totalSteps": float("nan")},
                # Empty values are no values, and give no warning.
                {"calendarDate": "2030-02-04", "totalSteps": "", "allDayStress": {}},
            ],
            FILES["hill_score_daily"]: [
                {"calendarDate": DATE, "overallScore": 70.0, "strengthScore": "61"},
            ],
            FILES["race_prediction_daily"]: [
                {**KEPT["race_prediction_daily"], "raceTime5K": "abc", "raceTime10K": 0},
            ],
            FILES["training_readiness_daily"]: [
                {**KEPT["training_readiness_daily"], "score": [1], "validSleep": "true"},
            ],
            FILES["vo2max_daily"]: [
                {**KEPT["vo2max_daily"], "maxMet": "abc"},
            ],
            FILES["training_history_daily"]: [{**KEPT["training_history_daily"], "sport": 5}],
            FILES["sleep_daily"]: [
                {**KEPT["sleep_daily"], "sleepTimeSeconds": "abc", "sleepStartTimestampGMT": "9999-12-31T23:59:59Z"},
            ],
            FILES["endurance_score_daily"]: [
                {"calendarDate": DATE, "overallScore": 6000, "classification": float("nan")},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(root, "export", files)
            output = both_forms(self, root, source, "daily")
            snapshot = root / "daily-snapshot"
            self.assertEqual(kept_values(snapshot), kept_values(output))
            summary = summary_of(output)
            self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
            self.assertEqual(
                value_warnings(output),
                {
                    "hill_score_daily": 1,
                    "endurance_score_daily": 1,
                    "race_prediction_daily": 2,
                    "sleep_daily": 2,
                    "uds_daily": 3,
                    "training_readiness_daily": 2,
                    "vo2max_daily": 1,
                    "training_history_daily": 1,
                },
            )
            self.assertEqual(
                audit(output, "uds_daily")["invalid_value_counts"],
                {"resting_heart_rate": 1, "steps": 2},
            )
            uds = {row["calendar_date"]: row for row in table(output, "uds_daily")}
            self.assertEqual(sorted(uds), [DATE, "2030-02-02", "2030-02-03", "2030-02-04"])
            self.assertIsNone(uds[DATE]["steps"])
            self.assertIsNone(uds["2030-02-02"]["resting_heart_rate"])
            self.assertIsNone(uds["2030-02-04"]["steps"])
            [hill] = table(output, "hill_score_daily")
            self.assertEqual((hill["overall_score"], hill["strength_score"]), (70, None))
            self.assertIsInstance(hill["overall_score"], int)
            [race] = table(output, "race_prediction_daily")
            self.assertEqual(
                (race["race_time_5k_sec"], race["race_time_10k_sec"], race["race_time_half_sec"]),
                (None, None, 4700),
            )
            [vo2max] = table(output, "vo2max_daily")
            self.assertIsNone(vo2max["max_met"])
            nan = [
                item
                for item in audit(output, "uds_daily")["invalid_values"]
                if item["key"] == {"calendar_date": "2030-02-03"}
            ]
            self.assertEqual(nan[0]["value"], {"non_finite_number": "NaN"})
            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("- Values left empty: 13 (", start_here)
            self.assertNotIn("DATA_ROW_LEFT_OUT", {item["code"] for item in summary["warnings"]})

    def test_a_value_of_another_form_is_no_value_when_rows_are_merged(self) -> None:
        # The check runs before the rows of one key are merged: "abc" is no
        # value there, so 5 stays and the values do not disagree.
        files = {FILES["uds_daily"]: [{"calendarDate": DATE, "totalSteps": 5}, {"calendarDate": DATE, "totalSteps": "abc"}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export_with(root, "export", files), "merge")
            [row] = table(output, "uds_daily")
            self.assertEqual((row["steps"], row["disagreeing_fields"]), (5, []))
            codes = {item["code"] for item in summary_of(output)["warnings"]}
            self.assertNotIn("VALUES_DISAGREE", codes)
            self.assertEqual(value_warnings(output), {"uds_daily": 1})

    def test_a_date_or_time_out_of_range_leaves_its_row_out(self) -> None:
        files = {
            FILES["uds_daily"]: [KEPT["uds_daily"], {"calendarDate": 10**20, "totalSteps": 2}],
            FILES["acute_training_load_daily"]: [
                KEPT["acute_training_load_daily"],
                {"calendarDate": DATE, "timestamp": "0001-01-01T00:00:00+01:00", "dailyTrainingLoadAcute": 2},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export_with(root, "export", files), "range")
            self.assertEqual(summary_of(output)["status"], "PARTIAL_SUCCESS")
            self.assertEqual(
                audit(output, "uds_daily")["excluded_reason_counts"],
                {"missing_or_invalid_calendar_date": 1},
            )
            self.assertEqual(
                audit(output, "acute_training_load_daily")["excluded_reason_counts"],
                {"missing_or_invalid_observation_timestamp": 1},
            )


class RecordValuesTest(unittest.TestCase):
    def test_record_values_of_another_form_are_left_empty_alike(self) -> None:
        activities = [
            _activity("A1", distance="abc", lapCount=3.0, name=123),
            _activity("A2", startTimeGmt=10**15, duration=float("nan")),
            _activity("A3", startTimeGmt=10**20),
        ]
        gear_rows = [{**gear(1, "Synthetic Shoe"), "maximumMeters": "800000"}]
        records = [{**personal_record(1, "A1", 1.0), "value": "1.0", "current": "true"}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = records_export(
                root, "export", activities, gear_rows=gear_rows, link_rows={"1": [{"activityId": "A1"}]}, records=records
            )
            output = record_both_forms(self, root, source, "records")
            self.assertEqual(kept_values(root / "records-snapshot"), kept_values(output))
            self.assertEqual(
                value_warnings(output),
                {"activities": 5, "gear": 1, "personal_records": 2},
            )
            rows = {row["activity_id"]: row for row in table(output, "activities")}
            self.assertEqual(
                (rows["A1"]["distance_raw_centimeters"], rows["A1"]["distance_m"], rows["A1"]["name"]),
                (None, None, None),
            )
            self.assertEqual(rows["A1"]["lap_count"], 3)
            self.assertIsInstance(rows["A1"]["lap_count"], int)
            # A time out of range keeps its value, and its local date is empty.
            self.assertEqual(rows["A2"]["start_time_gmt_ms"], 10**15)
            self.assertIsNone(rows["A2"]["activity_date_local"])
            self.assertIsNone(rows["A2"]["duration_ms"])
            # A number beyond 2**53 - 1 is of another form.
            self.assertIsNone(rows["A3"]["start_time_gmt_ms"])
            self.assertEqual(
                audit(output, "activities")["invalid_value_counts"],
                {"distance_raw_centimeters": 1, "duration_ms": 1, "name": 1, "start_time_gmt_ms": 2},
            )
            [record] = table(output, "personal_records")
            self.assertEqual((record["value"], record["current"]), (None, None))
            self.assertEqual(record["activity_relationship_status"], "explicit")
            self.assertEqual(summary_of(output)["status"], "PASS_WITH_WARNINGS")

    def test_fit_values_of_another_form_are_left_empty_alike(self) -> None:
        # A session whose sport is an array and whose average heart rate is
        # text, and one whose start time is out of range: the files are read.
        odd = fit_file([(0, 18, SESSION_BASE + [(5, 2, 0x02), (16, 3, 0x07)], [session_values() + bytes([1, 1]) + b"abc"])])
        late = fit_file(
            [(0, 18, [(2, 8, 0x8F), (5, 1, 0x00), (7, 4, 0x86), (9, 4, 0x86)], [struct.pack("<QBII", 10**17, 1, 3_600_000, 1_000_000)])]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("A1")])
            uploads = source / "DI-Connect-Uploaded-Files"
            uploads.mkdir(parents=True, exist_ok=True)
            (uploads / "synthetic_odd.fit").write_bytes(odd)
            (uploads / "synthetic_late.fit").write_bytes(late)
            output = both_forms(self, root, source, "fit")
            snapshot = root / "fit-snapshot"
            self.assertEqual(kept_values(snapshot), kept_values(output))
            self.assertEqual(table(snapshot, "fit_sessions"), table(output, "fit_sessions"))
            self.assertEqual(value_warnings(output), {"fit_sessions": 3})
            sessions = table(output, "fit_sessions")
            self.assertEqual(len(sessions), 2)
            self.assertTrue(all(row["avg_heart_rate"] is None for row in sessions))
            entries = [entry for entry in load(output / "audit/fit_audit.json") if "invalid_value_counts" in entry]
            self.assertEqual(
                sorted(field for entry in entries for field in entry["invalid_value_counts"]),
                ["fit_sessions.avg_heart_rate", "fit_sessions.sport", "fit_sessions.start_datetime_local"],
            )
            self.assertEqual(summary_of(output)["family_results"]["fit"]["invalid_value_count"], 3)

    def test_the_golden_path_stops_on_an_activities_value_of_another_form(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("A1", distance="abc")])
            with self.assertRaisesRegex(GoldenPathError, "form that its field does not take"):
                run_activities(source, root / "golden")
            self.assertFalse((root / "golden").exists())


class SnapshotValuesTest(unittest.TestCase):
    def test_a_later_value_of_another_form_leaves_the_field_empty(self) -> None:
        # The later Snapshot's value replaces the earlier one, and Run-All
        # leaves it empty; the audit keeps both (stage A3d-2a).
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_export(root, "first", [_activity("A1", distance=500000)])
            second = write_export(root, "second", [_activity("A1", distance="abc")])
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            output = root / "output"
            run_snapshot_all(store, output)
            [row] = table(output, "activities")
            self.assertIsNone(row["distance_raw_centimeters"])
            record = audit(output, "activities")
            self.assertEqual(record["invalid_value_counts"], {"distance_raw_centimeters": 1})
            [update] = record["updates"]
            self.assertIn("distance", [item["field"] for item in update["fields"]])
            self.assertEqual(value_warnings(output), {"activities": 1})

    def test_a_lactate_candidate_of_another_form_no_longer_stops_the_build(self) -> None:
        files = {
            LACTATE_FILE: [
                {"lactateThresholdHeartRate": "166", "metaData": {"calendarDate": DATE, "sequence": 1}},
                {"lactateThresholdHeartRate": 165, "metaData": {"calendarDate": "2030-02-02", "sequence": 1}},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export_with(root, "export", files), "lactate")
            self.assertEqual(kept_values(root / "lactate-snapshot"), kept_values(output))
            self.assertEqual(value_warnings(output), {"lactate_threshold": 1})
            candidates = load(output / "audit/lactate_threshold_candidates.json")
            self.assertEqual(candidates["invalid_value_counts"], {"lactate_threshold_heart_rate": 1})
            self.assertEqual(summary_of(output)["candidate_warning_count"], 1)

    def test_the_build_order_does_not_change_the_values_kept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = export_with(root, "first", {FILES["uds_daily"]: [{**KEPT["uds_daily"], "totalSteps": "5"}]})
            second = export_with(root, "second", {FILES["uds_daily"]: [{"calendarDate": "2030-02-02", "totalSteps": [1]}]})
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            builds = [
                build_approved_input(store, root / f"build-{index}", processing_sequence=sequence)
                for index, sequence in enumerate((["S1", "S2"], ["S2", "S1"]))
            ]
            self.assertEqual(len({build["canonical_build_sha256"] for build in builds}), 1)
            output = root / "output"
            run_snapshot_all(store, output)
            self.assertEqual(audit(output, "uds_daily")["invalid_value_counts"], {"steps": 2})


class OutputTest(unittest.TestCase):
    def test_every_output_file_is_strict_json(self) -> None:
        # NaN and Infinity are read from an Export, but never written.
        files = {FILES["uds_daily"]: [{**KEPT["uds_daily"], "totalSteps": float("nan"), "minHeartRate": float("inf")}]}

        def strict(name: str) -> Any:
            raise ValueError(f"not strict JSON: {name}")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export_with(root, "export", files)
            activities = source / "DI-Connect-Fitness" / "synthetic_summarizedActivities.json"
            value = json.loads(activities.read_text(encoding="utf-8"))
            value[0]["summarizedActivitiesExport"][0]["distance"] = float("nan")
            activities.write_text(json.dumps(value), encoding="utf-8")
            for output in (both_forms(self, root, source, "strict"), root / "strict-snapshot"):
                for path in sorted(output.rglob("*.json")):
                    with self.subTest(path=str(path.relative_to(output))):
                        json.loads(path.read_text(encoding="utf-8"), parse_constant=strict)
            self.assertTrue(math.isnan(float("nan")))

    def test_the_support_bundle_and_the_external_safe_pack_carry_counts_only(self) -> None:
        activities = [_activity("A1", name=["PRIVATE-NAME-VALUE"], distance="918273645")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", activities)
            output = root / "output"
            run_all(source, output, external_safe_pack=True)
            report = doctor_run_output(output)
            self.assertIn("DATA_VALUE_INVALID", {item["code"] for item in report["findings"]})
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with zipfile.ZipFile(path) as archive:
                    content = b"".join(archive.read(name) for name in archive.namelist())
                with self.subTest(path=path.name):
                    self.assertIn(b"DATA_VALUE_INVALID", content)
                    self.assertNotIn(b"PRIVATE-NAME-VALUE", content)
                    self.assertNotIn(b"918273645", content)
            # The local audit record keeps the values.
            kept = json.dumps(audit(output, "activities")["invalid_values"])
            self.assertIn("PRIVATE-NAME-VALUE", kept)


if __name__ == "__main__":
    unittest.main()
