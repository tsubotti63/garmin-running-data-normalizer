"""The kinds of the laps that a FIT file records, for the view page (stage X9b of v2.3.0): fit/lap_kinds.py.

Synthetic FIT files only, built here from the parts of tests/fit_fixture_factory.py."""

from __future__ import annotations

import dataclasses
import struct
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer.fit import lap_kinds
from garmin_running_data_normalizer.fit.lap_kinds import (
    INTENSITY_NAMES,
    MAX_LAPS,
    MAX_SESSIONS,
    intensity_name,
    read_lap_kinds,
)
from garmin_running_data_normalizer.fit.parser import FIT_EPOCH_OFFSET, fit_crc16, parse_fit_bytes
from tests.fit_fixture_factory import _definition, _record, definition_with_developer_fields

ROOT = Path(__file__).resolve().parents[1]
# A session: its start, sport (not read), elapsed, timer, distance, average heart rate (not read), number of laps.
SESSION_FIELDS = [(2, 4, 0x86), (5, 1, 0x00), (7, 4, 0x86), (8, 4, 0x86), (9, 4, 0x86), (16, 1, 0x02), (26, 2, 0x84)]
# A lap: its start, elapsed, timer, distance, average heart rate (not read), intensity, workout step index.
LAP_FIELDS = [(2, 4, 0x86), (7, 4, 0x86), (8, 4, 0x86), (9, 4, 0x86), (15, 1, 0x02), (23, 1, 0x00), (71, 2, 0x84)]
# A record with a position: its time, latitude and longitude (semicircles), and distance.
RECORD_FIELDS = [(253, 4, 0x86), (0, 4, 0x85), (1, 4, 0x85), (5, 4, 0x86)]
WARMUP, INTERVAL, RECOVERY, COOLDOWN = 2, 5, 4, 3
START = 1_000_000_000


def fit_bytes(body: bytes) -> bytes:
    """A FIT file of the body given, its header and file CRCs right."""
    header = bytes([14, 0x20]) + struct.pack("<H", 0) + struct.pack("<I", len(body)) + b".FIT"
    header += struct.pack("<H", fit_crc16(header))
    payload = header + body
    return payload + struct.pack("<H", fit_crc16(payload))


def session_values(start: int = START, num_laps: int = 1) -> bytes:
    return struct.pack("<IBIIIBH", start, 1, 3_600_000, 3_500_000, 1_000_000, 150, num_laps)


def lap_values(index: int, intensity: int = 0, step: int | None = None) -> bytes:
    return struct.pack(
        "<IIIIBBH",
        START + 300 * index,
        300_000 + index,
        290_000 + index,
        100_000 + 10 * index,
        150,
        intensity,
        index if step is None else step,
    )


def run_fit(
    kinds_by_session: list[list[int]],
    *,
    num_laps: list[int] | None = None,
    extra: bytes = b"",
    steps: list[int] | None = None,
) -> bytes:
    """A run whose laps come first and its sessions last, as a watch writes them: the laps of each session have
    the kinds given; the numbers of laps that the sessions say are those given, or their true counts."""
    body = bytearray(_definition(1, 19, LAP_FIELDS))
    index = 0
    for kinds in kinds_by_session:
        for kind in kinds:
            body.extend(_record(1, lap_values(index, kind, None if steps is None else steps[index])))
            index += 1
    body.extend(extra)
    body.extend(_definition(0, 18, SESSION_FIELDS))
    counts = num_laps if num_laps is not None else [len(kinds) for kinds in kinds_by_session]
    for ordinal, count in enumerate(counts):
        body.extend(_record(0, session_values(START + 10_000 * ordinal, count)))
    return fit_bytes(bytes(body))


def records(latitude: int) -> bytes:
    """A definition and three records with a position, at the local message 3."""
    body = bytearray(_definition(3, 20, RECORD_FIELDS))
    for second in range(3):
        body.extend(_record(3, struct.pack("<IiiI", START + second, latitude + second, -latitude, 100 * second)))
    return bytes(body)


def instant(fit_seconds: int | None) -> str | None:
    if fit_seconds is None:
        return None
    return datetime.fromtimestamp(fit_seconds + FIT_EPOCH_OFFSET, timezone.utc).isoformat()


INTERVAL_RUN = [WARMUP, INTERVAL, RECOVERY, INTERVAL, RECOVERY, INTERVAL, RECOVERY, INTERVAL, RECOVERY, INTERVAL, COOLDOWN]


class LapKindsTest(unittest.TestCase):
    def assert_as_the_parser(self, data: bytes) -> None:
        """The sessions, the laps, and their order, times, and distances are those of parse_fit_bytes."""
        ours = read_lap_kinds(data)
        theirs = parse_fit_bytes(data, file_id="fit_file:synthetic", source_path="synthetic.fit", timezone_name="UTC")
        self.assertEqual(ours.status, theirs["status"])
        if ours.status != "parsed_activity":
            return
        self.assertEqual(
            [len(session.laps) for session in ours.sessions], [len(laps) for laps in theirs["laps_by_session"]]
        )
        for session, their_session, their_laps in zip(ours.sessions, theirs["sessions"], theirs["laps_by_session"]):
            self.assertEqual(instant(session.start_time), their_session.get("start_time"))
            self.assertEqual(
                (session.elapsed_s, session.timer_s, session.distance_m),
                (their_session.get("total_elapsed_time"), their_session.get("total_timer_time"), their_session.get("total_distance")),
            )
            for lap, their_lap in zip(session.laps, their_laps):
                self.assertEqual(instant(lap.start_time), their_lap.get("start_time"))
                self.assertEqual(
                    (lap.elapsed_s, lap.timer_s, lap.distance_m),
                    (their_lap.get("total_elapsed_time"), their_lap.get("total_timer_time"), their_lap.get("total_distance")),
                )

    def test_an_interval_run_gives_the_kinds_of_its_laps_in_order(self) -> None:
        data = run_fit([INTERVAL_RUN])
        reading = read_lap_kinds(data)
        self.assertEqual(reading.status, "parsed_activity")
        self.assertEqual(reading.lap_count, 11)
        (session,) = reading.sessions
        self.assertEqual([lap.intensity for lap in session.laps], INTERVAL_RUN)
        self.assertEqual(
            [intensity_name(lap.intensity) for lap in session.laps],
            ["warmup"] + ["interval", "recovery"] * 4 + ["interval", "cooldown"],
        )
        self.assertEqual([lap.workout_step_index for lap in session.laps], list(range(11)))
        first = session.laps[0]
        self.assertEqual(
            (first.start_time, first.elapsed_s, first.timer_s, first.distance_m), (START, 300.0, 290.0, 1000.0)
        )
        self.assertEqual(
            (session.start_time, session.elapsed_s, session.timer_s, session.distance_m, session.num_laps),
            (START, 3600.0, 3500.0, 10000.0, 11),
        )
        self.assert_as_the_parser(data)

    def test_every_kind_of_the_profile_and_the_numbers_it_does_not_know(self) -> None:
        self.assertEqual(
            INTENSITY_NAMES,
            {0: "active", 1: "rest", 2: "warmup", 3: "cooldown", 4: "recovery", 5: "interval", 6: "other"},
        )
        kinds = [0, 1, 2, 3, 4, 5, 6, 0xFF, 7, 200]
        reading = read_lap_kinds(run_fit([kinds]))
        codes = [lap.intensity for lap in reading.sessions[0].laps]
        # 0xFF is the FIT's mark of no value.
        self.assertEqual(codes, [0, 1, 2, 3, 4, 5, 6, None, 7, 200])
        self.assertEqual(
            [intensity_name(code) for code in codes],
            ["active", "rest", "warmup", "cooldown", "recovery", "interval", "other", None, None, None],
        )
        self.assertIsNone(intensity_name(True))
        self.assertIsNone(intensity_name(2.0))

    def test_a_value_that_the_file_does_not_give_is_none(self) -> None:
        body = bytearray(_definition(1, 19, LAP_FIELDS))
        body.extend(_record(1, struct.pack("<IIIIBBH", 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFF, 0xFF, 0xFFFF)))
        body.extend(_definition(0, 18, SESSION_FIELDS))
        body.extend(_record(0, struct.pack("<IBIIIBH", 0xFFFFFFFF, 1, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFF, 0xFFFF)))
        reading = read_lap_kinds(fit_bytes(bytes(body)))
        self.assertEqual(reading.status, "parsed_activity")
        (session,) = reading.sessions
        self.assertEqual(
            (session.start_time, session.elapsed_s, session.timer_s, session.distance_m, session.num_laps),
            (None, None, None, None, None),
        )
        self.assertEqual(session.laps, (lap_kinds.Lap(None, None, None, None, None, None),))
        self.assert_as_the_parser(fit_bytes(bytes(body)))

    def test_the_laps_go_to_their_sessions_as_parse_fit_bytes_gives_them(self) -> None:
        cases = {
            "two sessions, their numbers of laps": (run_fit([[WARMUP, INTERVAL, COOLDOWN], [0, 0]]), "parsed_activity", [3, 2]),
            "the only session takes every lap, whatever it says": (run_fit([[0, 0, 0, 0, 0]], num_laps=[2]), "parsed_activity", [5]),
            "numbers of laps that do not add up": (run_fit([[0, 0, 0], [0, 0]], num_laps=[3, 3]), "session_lap_allocation_conflict", None),
            "a number of laps that is not there": (run_fit([[0, 0, 0], [0, 0]], num_laps=[3, 0xFFFF]), "session_lap_allocation_conflict", None),
            "fewer laps than said": (run_fit([[0], [0]], num_laps=[1, 2]), "session_lap_allocation_conflict", None),
        }
        for name, (data, status, counts) in cases.items():
            with self.subTest(name):
                reading = read_lap_kinds(data)
                self.assertEqual(reading.status, status)
                if counts is not None:
                    self.assertEqual([len(session.laps) for session in reading.sessions], counts)
                else:
                    self.assertEqual(reading.sessions, ())
                self.assert_as_the_parser(data)

    def test_a_file_without_a_session(self) -> None:
        laps_only = bytearray(_definition(1, 19, LAP_FIELDS))
        laps_only.extend(_record(1, lap_values(0)))
        nothing = bytearray(_definition(3, 20, RECORD_FIELDS))
        nothing.extend(_record(3, struct.pack("<IiiI", START, 1, 2, 3)))
        for name, body, status in (
            ("laps without a session", laps_only, "session_lap_allocation_conflict"),
            ("no session and no lap", nothing, "parsed_non_activity"),
        ):
            with self.subTest(name):
                data = fit_bytes(bytes(body))
                self.assertEqual(read_lap_kinds(data).status, status)
                self.assert_as_the_parser(data)

    def test_a_first_session_without_the_fields_that_parse_fit_bytes_reads(self) -> None:
        # The one difference that the module describes: a session message is a session here whatever fields it
        # holds, where parse_fit_bytes counts a file as an activity only if its first session holds one of the
        # fields that it reads (here the session holds its event only).
        body = bytearray(_definition(1, 19, LAP_FIELDS))
        body.extend(_record(1, lap_values(0, INTERVAL)))
        body.extend(_definition(0, 18, [(0, 1, 0x00)]))
        body.extend(_record(0, bytes([9])))
        data = fit_bytes(bytes(body))
        self.assertEqual(parse_fit_bytes(data, file_id="f", source_path="s")["status"], "parsed_non_activity")
        reading = read_lap_kinds(data)
        self.assertEqual(reading.status, "parsed_activity")
        (session,) = reading.sessions
        self.assertEqual(
            (session.start_time, session.elapsed_s, session.timer_s, session.distance_m, session.num_laps),
            (None, None, None, None, None),
        )
        self.assertEqual([lap.intensity for lap in session.laps], [INTERVAL])

    def test_the_other_messages_are_skipped_and_positions_are_not_read(self) -> None:
        # Records with positions, the readings of heart rate variability (370), a workout and its steps (26, 27),
        # and developer fields, between the laps and the sessions.
        others = bytearray(records(latitude=400_000_000))
        others.extend(_definition(2, 370, [(1, 2, 0x84)]))
        others.extend(_record(2, struct.pack("<H", 800)))
        others.extend(_definition(4, 26, [(4, 1, 0x00), (6, 2, 0x84)]))
        others.extend(_record(4, struct.pack("<BH", 1, 11)))
        others.extend(_definition(5, 27, [(254, 2, 0x84), (1, 1, 0x00)]))
        others.extend(_record(5, struct.pack("<HB", 0, 1)))
        others.extend(_definition(7, 21, [(2, 4, 0x86), (23, 1, 0x00), (26, 2, 0x84), (71, 2, 0x84)]))
        others.extend(_record(7, struct.pack("<IBHH", START, 3, 4, 5)))
        others.extend(definition_with_developer_fields(6, 19, LAP_FIELDS, [(0, 4, 0)]))
        others.extend(_record(6, lap_values(11, INTERVAL) + struct.pack("<I", 123456)))
        # Eleven laps, then the others with a twelfth lap of developer fields.
        with_others = run_fit([INTERVAL_RUN], extra=bytes(others), num_laps=[12])
        reading = read_lap_kinds(with_others)
        self.assertEqual(reading.status, "parsed_activity")
        self.assertEqual([lap.intensity for lap in reading.sessions[0].laps], INTERVAL_RUN + [INTERVAL])
        self.assertEqual(reading.sessions[0].laps[11].distance_m, 1001.1)
        self.assert_as_the_parser(with_others)
        # Only the positions differ: the answer is the same.
        elsewhere = bytearray(others)
        elsewhere[: len(records(400_000_000))] = records(latitude=-300_000_000)
        self.assertNotEqual(bytes(elsewhere), bytes(others))
        self.assertEqual(read_lap_kinds(run_fit([INTERVAL_RUN], extra=bytes(elsewhere), num_laps=[12])), reading)
        # The values read are those of the fields that it reads, of the sessions and the laps only.
        read = []
        original = lap_kinds._read_value

        def counted(data: bytes, offset: int, field, endian: str):
            read.append(field.number)
            return original(data, offset, field, endian)

        with mock.patch.object(lap_kinds, "_read_value", counted):
            read_lap_kinds(with_others)
        self.assertEqual(sorted(read), sorted([2, 7, 8, 9, 23, 71] * 12 + [2, 7, 8, 9, 26]))

    def test_a_big_endian_definition_and_a_compressed_time(self) -> None:
        big_lap = (
            bytes([0x41, 0x00, 0x01])
            + struct.pack(">H", 19)
            + bytes([len(LAP_FIELDS)])
            + b"".join(bytes(field) for field in LAP_FIELDS)
        )
        body = bytearray(big_lap)
        body.extend(bytes([0x01]) + struct.pack(">IIIIBBH", START, 300_000, 290_000, 100_000, 150, INTERVAL, 7))
        # A record header with a compressed time: the local message 1 and an offset of 3 seconds.
        body.extend(bytes([0x80 | (1 << 5) | 3]) + struct.pack(">IIIIBBH", START + 300, 300_001, 290_001, 100_010, 150, RECOVERY, 8))
        body.extend(_definition(0, 18, SESSION_FIELDS))
        body.extend(_record(0, session_values(num_laps=2)))
        data = fit_bytes(bytes(body))
        reading = read_lap_kinds(data)
        self.assertEqual(reading.status, "parsed_activity")
        laps = reading.sessions[0].laps
        self.assertEqual([(lap.intensity, lap.workout_step_index, lap.timer_s) for lap in laps], [(INTERVAL, 7, 290.0), (RECOVERY, 8, 290.001)])
        self.assert_as_the_parser(data)

    def test_a_file_that_cannot_be_read(self) -> None:
        good = run_fit([INTERVAL_RUN])
        broken_crc = good[:-2] + bytes([good[-2] ^ 0xFF, good[-1]])
        cut_record = bytearray(_definition(1, 19, LAP_FIELDS))
        cut_record.extend(bytes([0x01]) + b"\x00" * 5)
        undefined = bytes([0x05]) + b"\x00" * 4
        cut_definition = bytes([0x41, 0x00, 0x00])
        developer_head = bytes([0x61, 0x00, 0x00]) + struct.pack("<H", 19) + bytes([1]) + bytes((2, 4, 0x86))
        for name, data, status in (
            ("a wrong CRC of the file", broken_crc, "bad_file_crc"),
            ("a file that is cut", good[:-3], "truncated"),
            ("two files one after the other", good + good, "unsupported_chained"),
            ("a record cut short", fit_bytes(bytes(cut_record)), "truncated"),
            ("a definition cut short", fit_bytes(cut_definition), "truncated"),
            ("a definition cut before the count of its developer fields", fit_bytes(developer_head), "truncated"),
            ("developer fields cut short", fit_bytes(developer_head + bytes([2]) + bytes((0, 4, 0))), "truncated"),
            ("a record without its definition", fit_bytes(undefined), "undefined_local_message"),
        ):
            with self.subTest(name):
                reading = read_lap_kinds(data)
                self.assertEqual((reading.status, reading.sessions, reading.lap_count), (status, (), 0))
                self.assertEqual(parse_fit_bytes(data, file_id="f", source_path="s")["status"], status)

    def test_the_scan_stops_past_its_most_laps_and_sessions(self) -> None:
        self.assertEqual((MAX_LAPS, MAX_SESSIONS), (10_000, 1_000))
        with mock.patch.object(lap_kinds, "MAX_LAPS", 3):
            at_most = read_lap_kinds(run_fit([[0, 0, 0]]))
            self.assertEqual((at_most.status, at_most.lap_count, len(at_most.sessions[0].laps)), ("parsed_activity", 3, 3))
            # Past it, only the status: none of the laps read, so that a part is not shown as the whole.
            self.assertEqual(read_lap_kinds(run_fit([[0, 0, 0, 0]])), lap_kinds.LapKinds("too_many_laps"))
        with mock.patch.object(lap_kinds, "MAX_SESSIONS", 2):
            self.assertEqual(read_lap_kinds(run_fit([[0], [0]])).status, "parsed_activity")
            self.assertEqual(read_lap_kinds(run_fit([[0], [0], [0]])), lap_kinds.LapKinds("too_many_sessions"))
        self.assertEqual(read_lap_kinds(run_fit([[0, 0, 0, 0]])).sessions[0].laps[3].intensity, 0)
        empty = bytearray(_definition(1, 19, []))
        empty.extend(_record(1, b"") * 4)
        empty.extend(_definition(0, 18, SESSION_FIELDS) + _record(0, session_values(num_laps=4)))
        self.assertEqual(read_lap_kinds(fit_bytes(bytes(empty))).sessions[0].laps, (lap_kinds.Lap(None, None, None, None, None, None),) * 4)
        with mock.patch.object(lap_kinds, "MAX_LAPS", 3):
            self.assertEqual(read_lap_kinds(fit_bytes(bytes(empty))), lap_kinds.LapKinds("too_many_laps"))

    def test_values_of_another_form_than_their_fields(self) -> None:
        # A lap whose fields have other types or sizes than the profile's: an array (a field twice the size of its
        # type), a text, a float, a negative number, and a float that is not a number.
        fields = [(2, 8, 0x86), (7, 4, 0x07), (8, 4, 0x88), (9, 4, 0x85), (23, 2, 0x02), (71, 4, 0x07)]
        values = struct.pack("<II", START, START + 1) + b"abc\x00" + struct.pack("<f", 290.5) + struct.pack("<i", -150)
        values += bytes([5, 4]) + b"x\x00\x00\x00"
        body = bytearray(_definition(1, 19, fields))
        body.extend(_record(1, values))
        body.extend(_definition(2, 19, [(2, 4, 0x85), (8, 4, 0x88), (23, 1, 0x01), (71, 2, 0x83)]))
        body.extend(_record(2, struct.pack("<ifbh", -5, float("nan"), -1, -2)))
        # One value of its type, but of another form: a float for the start and the intensity, a letter for the
        # workout step index.
        body.extend(_definition(3, 19, [(2, 4, 0x88), (23, 4, 0x88), (71, 1, 0x07)]))
        body.extend(_record(3, struct.pack("<ff", 1.5, 5.0) + b"x"))
        body.extend(_definition(0, 18, SESSION_FIELDS))
        body.extend(_record(0, session_values(num_laps=3)))
        laps = read_lap_kinds(fit_bytes(bytes(body))).sessions[0].laps
        self.assertEqual(laps[0], lap_kinds.Lap(None, None, 290.5 / 1000.0, -1.5, None, None))
        self.assertEqual(laps[1], lap_kinds.Lap(-5, None, None, None, -1, -2))
        self.assertEqual(laps[2], lap_kinds.Lap(None, None, None, None, None, None))
        self.assertIsNone(intensity_name(laps[1].intensity))
        # The numbers of laps of two sessions that are not whole numbers of 0 or more: a conflict, as for
        # parse_fit_bytes.
        for name, session_fields, count in (
            ("a float", [(26, 4, 0x88)], struct.pack("<f", 1.0)),
            ("a negative number", [(26, 2, 0x83)], struct.pack("<h", -1)),
            ("an array", [(26, 4, 0x84)], struct.pack("<HH", 1, 1)),
        ):
            with self.subTest(name):
                body = bytearray(_definition(1, 19, LAP_FIELDS))
                body.extend(_record(1, lap_values(0)) + _record(1, lap_values(1)))
                body.extend(_definition(0, 18, session_fields))
                body.extend(_record(0, count) + _record(0, count))
                data = fit_bytes(bytes(body))
                self.assertEqual(read_lap_kinds(data).status, "session_lap_allocation_conflict")
                self.assertEqual(parse_fit_bytes(data, file_id="f", source_path="s")["status"], "session_lap_allocation_conflict")
        # A negative number with which the counts would add up (3 and -1 for two laps): still a conflict.
        body = bytearray(_definition(1, 19, LAP_FIELDS))
        body.extend(_record(1, lap_values(0)) + _record(1, lap_values(1)))
        body.extend(_definition(0, 18, [(26, 2, 0x83)]))
        body.extend(_record(0, struct.pack("<h", 3)) + _record(0, struct.pack("<h", -1)))
        data = fit_bytes(bytes(body))
        self.assertEqual(read_lap_kinds(data).status, "session_lap_allocation_conflict")
        self.assertEqual(parse_fit_bytes(data, file_id="f", source_path="s")["status"], "session_lap_allocation_conflict")

    def test_a_number_of_laps_that_is_true_is_a_conflict(self) -> None:
        # No FIT gives True, but the rule of parse_fit_bytes, which is also this one, takes a number of laps that is
        # a bool for none: the reading of the field is made True here.
        original = lap_kinds._read_value

        def reading(data: bytes, offset: int, field, endian: str):
            value = original(data, offset, field, endian)
            return True if field.number == 26 else value

        with mock.patch.object(lap_kinds, "_read_value", reading):
            self.assertEqual(read_lap_kinds(run_fit([[0], [0]])).status, "session_lap_allocation_conflict")
            self.assertIsNone(read_lap_kinds(run_fit([[0, 0]])).sessions[0].num_laps)

    def test_an_array_of_an_enum_a_byte_and_a_type_that_is_not_known(self) -> None:
        # Codex's review of the diff: the parser reads an enum of two bytes as its first value, and keeps 0xFF of the
        # type byte, which its table of the marks of no value does not have; here both are None, as is a field of a
        # type that is not known.
        cases = (
            ("an enum of two bytes and the mark of a byte", [(23, 2, 0x00), (71, 1, 0x0D)], bytes([5, 4, 0xFF]), (None, None)),
            ("a byte", [(23, 1, 0x0D), (71, 1, 0x0D)], bytes([5, 7]), (5, 7)),
            ("the mark of no value of a byte", [(23, 1, 0x0D)], bytes([0xFF]), (None, None)),
            ("a type that is not known", [(23, 1, 0x0F), (71, 1, 0x0F)], bytes([5, 7]), (None, None)),
        )
        for name, fields, values, expected in cases:
            with self.subTest(name):
                body = bytearray(_definition(1, 19, fields))
                body.extend(_record(1, values))
                body.extend(_definition(0, 18, SESSION_FIELDS) + _record(0, session_values()))
                (lap,) = read_lap_kinds(fit_bytes(bytes(body))).sessions[0].laps
                self.assertEqual((lap.intensity, lap.workout_step_index), expected)
        # The numbers of laps of two sessions as enums of two bytes: no number, a conflict, where the parser takes
        # their first bytes for the numbers (a value of another form, which the module describes).
        body = bytearray(_definition(1, 19, LAP_FIELDS))
        body.extend(_record(1, lap_values(0)) + _record(1, lap_values(1)))
        body.extend(_definition(0, 18, [(26, 2, 0x00)]))
        body.extend(_record(0, bytes([1, 0])) * 2)
        data = fit_bytes(bytes(body))
        self.assertEqual(read_lap_kinds(data).status, "session_lap_allocation_conflict")
        self.assertEqual(parse_fit_bytes(data, file_id="f", source_path="s")["status"], "parsed_activity")

    def test_a_field_twice_in_a_definition_keeps_its_later_value(self) -> None:
        fields = [(9, 4, 0x86), (23, 1, 0x00), (9, 4, 0x86), (23, 1, 0x00)]
        body = bytearray(_definition(1, 19, fields))
        body.extend(_record(1, struct.pack("<IBIB", 100, INTERVAL, 200, RECOVERY)))
        body.extend(_definition(0, 18, SESSION_FIELDS))
        body.extend(_record(0, session_values()))
        data = fit_bytes(bytes(body))
        (lap,) = read_lap_kinds(data).sessions[0].laps
        self.assertEqual((lap.distance_m, lap.intensity), (2.0, RECOVERY))
        self.assertEqual(parse_fit_bytes(data, file_id="f", source_path="s")["laps"][0]["total_distance"], 2.0)

    def test_a_time_out_of_the_range_of_a_date_stays_seconds(self) -> None:
        # A start as a number of 64 bits: parse_fit_bytes cannot turn it into a date and leaves it empty; here it
        # stays the number of seconds that the file gives.
        body = bytearray(_definition(1, 19, [(2, 8, 0x8F), (23, 1, 0x00)]))
        body.extend(_record(1, struct.pack("<QB", 2**62, INTERVAL)))
        body.extend(_definition(0, 18, SESSION_FIELDS))
        body.extend(_record(0, session_values()))
        data = fit_bytes(bytes(body))
        (lap,) = read_lap_kinds(data).sessions[0].laps
        self.assertEqual(lap.start_time, 2**62)
        self.assertIsNone(parse_fit_bytes(data, file_id="f", source_path="s")["laps"][0]["start_time"])

    def test_the_readings_of_heart_rate_variability_are_not_read(self) -> None:
        def with_readings(value: int) -> bytes:
            readings = bytearray(_definition(2, 370, [(1, 2, 0x84), (253, 4, 0x86)]))
            readings.extend(_record(2, struct.pack("<HI", value, START)))
            return run_fit([INTERVAL_RUN], extra=bytes(readings))

        self.assertNotEqual(with_readings(800), with_readings(1200))
        self.assertEqual(read_lap_kinds(with_readings(800)), read_lap_kinds(with_readings(1200)))

    def test_the_answer_holds_no_position_device_or_second_by_second_value(self) -> None:
        names = lambda kind: [field.name for field in dataclasses.fields(kind)]  # noqa: E731
        self.assertEqual(names(lap_kinds.Lap), ["start_time", "elapsed_s", "timer_s", "distance_m", "intensity", "workout_step_index"])
        self.assertEqual(names(lap_kinds.Session), ["start_time", "elapsed_s", "timer_s", "distance_m", "num_laps", "laps"])
        self.assertEqual(names(lap_kinds.LapKinds), ["status", "sessions", "lap_count"])

    def test_the_normalizer_does_not_use_it(self) -> None:
        # Only the module itself and the view page's reading of the laps of one activity (stage X9c-1) name it in
        # the source: the normalizer's reading and its outputs are as before.
        users = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "src").rglob("*.py")
            if "lap_kinds" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(
            users,
            ["src/garmin_running_data_normalizer/fit/lap_kinds.py", "src/garmin_running_data_normalizer/gui/fit_reading.py"],
        )
        # The commands of the normalizer, imported by a new Python, do not load either.
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "import garmin_running_data_normalizer.runner, garmin_running_data_normalizer.run_all; "
            "print(sorted(name for name in sys.modules if name.endswith(('.lap_kinds', '.fit_reading'))))"
        )
        found = subprocess.run(
            [sys.executable, "-I", "-B", "-c", code, str(ROOT / "src")],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        self.assertEqual(found.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
