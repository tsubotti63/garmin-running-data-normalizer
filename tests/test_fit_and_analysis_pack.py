from __future__ import annotations

import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from garmin_running_data_normalizer.export.analysis_pack import build_analysis_pack
from garmin_running_data_normalizer.fit.parser import fit_crc16, parse_fit_bytes, parse_fit_export

from tests.fit_fixture_factory import synthetic_fit, truncated_fit, unsupported_chained_fit


def synthetic_fit_session(*, invalid_metrics: bool = False) -> bytes:
    session_definition = bytes([0x40, 0x00, 0x00]) + struct.pack("<H", 18) + bytes([
        18,
        2, 4, 0x86,
        5, 1, 0x00,
        6, 1, 0x00,
        7, 4, 0x86,
        8, 4, 0x86,
        9, 4, 0x86,
        11, 2, 0x84,
        14, 4, 0x86,
        15, 4, 0x86,
        16, 1, 0x02,
        17, 1, 0x02,
        18, 1, 0x02,
        19, 1, 0x02,
        20, 2, 0x84,
        21, 2, 0x84,
        22, 2, 0x84,
        23, 2, 0x84,
        26, 2, 0x84,
    ])
    u32_metric = 0xFFFFFFFF if invalid_metrics else 3_000
    u16_metric = 0xFFFF if invalid_metrics else 250
    u8_metric = 0xFF if invalid_metrics else 150
    session_record = bytes([0x00]) + b"".join([
        struct.pack("<I", 1_000_000), bytes([1, 7]),
        struct.pack("<II", 3_600_000, 3_500_000), struct.pack("<I", 1_000_000),
        struct.pack("<H", 0xFFFF if invalid_metrics else 600),
        struct.pack("<II", u32_metric, 5_000 if not invalid_metrics else 0xFFFFFFFF),
        bytes([u8_metric, 180 if not invalid_metrics else 0xFF, 82 if not invalid_metrics else 0xFF, 95 if not invalid_metrics else 0xFF]),
        struct.pack("<HHHHH", u16_metric, 400 if not invalid_metrics else 0xFFFF,
                    100 if not invalid_metrics else 0xFFFF, 80 if not invalid_metrics else 0xFFFF,
                    1),
    ])
    lap_definition = bytes([0x41, 0x00, 0x00]) + struct.pack("<H", 19) + bytes([
        14,
        2, 4, 0x86,
        7, 4, 0x86,
        8, 4, 0x86,
        9, 4, 0x86,
        13, 4, 0x86,
        14, 4, 0x86,
        15, 1, 0x02,
        16, 1, 0x02,
        17, 1, 0x02,
        18, 1, 0x02,
        19, 2, 0x84,
        20, 2, 0x84,
        21, 2, 0x84,
        22, 2, 0x84,
    ])
    lap_record = bytes([0x01]) + b"".join([
        struct.pack("<IIIIII", 1_000_000, 3_600_000, 3_500_000, 1_000_000,
                    u32_metric, 5_000 if not invalid_metrics else 0xFFFFFFFF),
        bytes([u8_metric, 180 if not invalid_metrics else 0xFF, 82 if not invalid_metrics else 0xFF, 95 if not invalid_metrics else 0xFF]),
        struct.pack("<HHHH", u16_metric, 400 if not invalid_metrics else 0xFFFF,
                    100 if not invalid_metrics else 0xFFFF, 80 if not invalid_metrics else 0xFFFF),
    ])
    body = session_definition + session_record + lap_definition + lap_record
    payload = bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT" + body
    return payload + struct.pack("<H", fit_crc16(payload))


class FitAndPackTest(unittest.TestCase):
    def test_fit_session_parses_without_record_coordinates(self) -> None:
        parsed = parse_fit_bytes(synthetic_fit_session(), file_id="fit_file:000000", source_path="synthetic.fit")
        self.assertEqual(parsed["status"], "parsed_activity")
        self.assertEqual(parsed["session"]["total_distance"], 10_000.0)
        self.assertEqual(parsed["session"]["sport"], 1)
        self.assertEqual(parsed["session"]["avg_speed"], 3.0)
        self.assertEqual(parsed["session"]["avg_heart_rate"], 150)
        self.assertEqual(parsed["session"]["avg_cadence"], 82)
        self.assertEqual(parsed["session"]["avg_power"], 250)
        self.assertEqual(parsed["session"]["total_ascent"], 100)
        self.assertEqual(parsed["laps"][0]["total_distance"], 10_000.0)
        self.assertEqual(parsed["laps"][0]["avg_speed"], 3.0)
        self.assertEqual(parsed["laps"][0]["avg_heart_rate"], 150)

    def test_fit_invalid_sentinels_are_null_before_scaling(self) -> None:
        parsed = parse_fit_bytes(
            synthetic_fit_session(invalid_metrics=True),
            file_id="fit_file:invalid-synthetic",
            source_path="synthetic-invalid.fit",
        )
        for name in ("avg_speed", "max_speed", "avg_heart_rate", "max_heart_rate",
                     "avg_cadence", "max_cadence", "avg_power", "max_power",
                     "total_ascent", "total_descent"):
            self.assertIsNone(parsed["session"][name], name)
            self.assertIsNone(parsed["laps"][0][name], name)

    def test_fit_negative_statuses_are_auditable(self) -> None:
        bad_header = b"\x0c\x10\x00\x00\x00\x00\x00\x00NOPE"
        truncated = bytes([12, 0x10]) + struct.pack("<H", 0) + struct.pack("<I", 10) + b".FIT"
        unknown_body = b"\x00"
        unknown_payload = (
            bytes([12, 0x10])
            + struct.pack("<H", 0)
            + struct.pack("<I", 1)
            + b".FIT"
            + unknown_body
        )
        unknown = unknown_payload + struct.pack("<H", fit_crc16(unknown_payload))
        self.assertEqual(parse_fit_bytes(bad_header, file_id="x", source_path="x.fit")["status"], "bad_header")
        self.assertEqual(parse_fit_bytes(truncated, file_id="x", source_path="x.fit")["status"], "truncated")
        unknown_result = parse_fit_bytes(unknown, file_id="x", source_path="x.fit")
        self.assertEqual(unknown_result["status"], "undefined_local_message")
        self.assertEqual(unknown_result["file_crc_status"], "valid")
        with patch("garmin_running_data_normalizer.fit.parser.MAX_FIT_BYTES", 1):
            self.assertEqual(parse_fit_bytes(b"12", file_id="x", source_path="x.fit")["status"], "too_large")

    def test_fit_crc_statuses_are_explicit_and_fail_closed(self) -> None:
        valid = parse_fit_bytes(
            synthetic_fit(),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        self.assertEqual(valid["status"], "parsed_activity")
        self.assertEqual(valid["header_crc_status"], "valid")
        self.assertEqual(valid["file_crc_status"], "valid")

        header_crc_omitted = parse_fit_bytes(
            synthetic_fit(header_crc_present=False),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        self.assertEqual(header_crc_omitted["status"], "parsed_activity")
        self.assertEqual(header_crc_omitted["header_crc_status"], "not_present")
        self.assertEqual(header_crc_omitted["file_crc_status"], "valid")

        short_header = parse_fit_bytes(
            synthetic_fit(header_size=12),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        self.assertEqual(short_header["status"], "parsed_activity")
        self.assertEqual(short_header["header_crc_status"], "not_present")
        self.assertEqual(short_header["file_crc_status"], "valid")

        bad_header = parse_fit_bytes(
            synthetic_fit(invalid_header_crc=True),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        self.assertEqual(bad_header["status"], "bad_header_crc")
        self.assertEqual(bad_header["header_crc_status"], "invalid")

        bad_file = parse_fit_bytes(
            synthetic_fit(invalid_file_crc=True),
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        self.assertEqual(bad_file["status"], "bad_file_crc")
        self.assertEqual(bad_file["file_crc_status"], "invalid")
        self.assertEqual(
            parse_fit_bytes(
                truncated_fit(),
                file_id="fit_file:synthetic",
                source_path="synthetic.fit",
            )["status"],
            "truncated",
        )
        self.assertEqual(
            parse_fit_bytes(
                unsupported_chained_fit(),
                file_id="fit_file:synthetic",
                source_path="synthetic.fit",
            )["status"],
            "unsupported_chained",
        )

    def test_multi_session_identity_and_lap_conservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic-multi.fit").write_bytes(synthetic_fit(sessions=2))
            sessions, laps, audit = parse_fit_export(root)
            self.assertEqual(len(sessions), 2)
            self.assertEqual(len(laps), 2)
            self.assertEqual(audit[0]["session_count"], 2)
            self.assertEqual(audit[0]["lap_count"], 2)
            self.assertEqual(audit[0]["unallocated_lap_count"], 0)
            self.assertEqual([item["session_ordinal"] for item in sessions], [0, 1])
            self.assertEqual(
                [item["lap_ordinal_within_session"] for item in laps],
                [0, 0],
            )
            self.assertEqual(
                {item["fit_session_key"] for item in sessions},
                {item["fit_session_key"] for item in laps},
            )
            self.assertEqual(len({item["fit_lap_key"] for item in laps}), 2)

    def test_multi_session_lap_allocation_conflict_is_not_normalized(self) -> None:
        payload = synthetic_fit(sessions=2, declared_laps_per_session=2)
        parsed = parse_fit_bytes(
            payload,
            file_id="fit_file:synthetic",
            source_path="synthetic.fit",
        )
        self.assertEqual(parsed["status"], "session_lap_allocation_conflict")
        self.assertEqual(parsed["session_count"], 2)
        self.assertEqual(parsed["lap_count"], 2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic-conflict.fit").write_bytes(payload)
            sessions, laps, audit = parse_fit_export(root)
            self.assertEqual((sessions, laps), ([], []))
            self.assertEqual(
                audit[0]["parse_status"],
                "session_lap_allocation_conflict",
            )

    def test_fit_file_id_is_stable_when_an_earlier_file_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.fit").write_bytes(synthetic_fit_session())
            first_id = parse_fit_export(root)[0][0]["fit_file_id"]
            (root / "a.fit").write_bytes(b"not-fit")
            activities, laps, _ = parse_fit_export(root)
            self.assertEqual(activities[0]["fit_file_id"], first_id)
            self.assertEqual(laps[0]["fit_file_id"], first_id)
            self.assertIn("source_sha256", laps[0])
            self.assertEqual(activities[0]["avg_cadence"], 82)
            self.assertEqual(activities[0]["total_ascent"], 100)

    def test_fit_export_reports_bad_input_in_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.fit").write_bytes(b"not-fit")
            activities, laps, audit = parse_fit_export(root)
            self.assertEqual((activities, laps), ([], []))
            self.assertEqual(audit[0]["parse_status"], "too_small")
            self.assertNotIn(str(root), audit[0]["source_path"])

    def test_analysis_pack_is_allowlist_only_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "normalized").mkdir()
            (root / "normalized/data.json").write_text(json.dumps({"synthetic": True}), encoding="utf-8")
            first = root / "first.zip"
            second = root / "second.zip"
            result_one = build_analysis_pack(root, ["normalized/data.json"], first)
            result_two = build_analysis_pack(root, ["normalized/data.json"], second)
            self.assertEqual(result_one["pack_sha256"], result_two["pack_sha256"])
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(sorted(archive.namelist()), ["manifest.json", "normalized/data.json"])
            with self.assertRaises(ValueError):
                build_analysis_pack(root, ["../outside.json"], root / "unsafe.zip")


if __name__ == "__main__":
    unittest.main()
