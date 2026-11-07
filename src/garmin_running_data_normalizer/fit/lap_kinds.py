"""The kinds of the laps that a FIT file records, for the view page (stage X9b of v2.3.0).

A small scan of its own, apart from the normalizer's ``parse_fit_bytes``, which it does not change and which does not
use it. It reads, of each session (message 18), its start, its elapsed and timer times, its distance, and its number
of laps; and of each lap (message 19), its start, its elapsed and timer times, its distance, its intensity (the kind of
the lap that the FIT records, FIT SDK Profile 21.221.0), and the index of its workout step, kept as a number only (the
steps of a workout, messages 26 and 27, are not read). Every other message, such as the records with their positions,
every other field, and every developer field is skipped by its size: its value is not read, kept, or counted.

The laps go to their sessions by the rule of ``parse_fit_bytes``: all the laps to the only session; with two sessions
or more, as many laps as each session's number of laps says, in order; a number of laps that is not a number, a count
that does not add up, or laps without a session make the file a ``session_lap_allocation_conflict``. One difference: a
session message is a session here whatever fields it holds, where ``parse_fit_bytes`` counts a file as an activity only
if its first session holds one of the fields that it reads.

A time is the number of seconds of the FIT (from 1989-12-31 00:00 UTC), as the file gives it, with no time zone; to
compare it with a time of an output, it is turned into one as ``parse_fit_bytes`` does. A time, a number of laps, an
intensity, and a workout step index are whole numbers; the times and distances, whole numbers or finite numbers,
scaled as ``parse_fit_bytes`` scales them; a value of another form, such as a text, a field whose size is not that
of its type (an array, also of an enum, which ``parse_fit_bytes`` reads as its first value), a type that is not known,
and the FIT's mark of no value (also 0xFF of the type byte, which ``parse_fit_bytes`` keeps) are None. Where a
definition holds a field twice, the later value stays, as in ``parse_fit_bytes``. Past ``MAX_LAPS`` laps or
``MAX_SESSIONS`` sessions the scan stops and gives its status only, none of the laps read.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Any

from .parser import BASE_TYPES, Definition, FieldDef, _null_invalid_with_count, _read_value, check_fit_container

SESSION_MESSAGE = 18
LAP_MESSAGE = 19
# The fields read, by message: the number of the field and the name of its value.
SESSION_FIELDS = {2: "start_time", 7: "elapsed", 8: "timer", 9: "distance", 26: "num_laps"}
LAP_FIELDS = {2: "start_time", 7: "elapsed", 8: "timer", 9: "distance", 23: "intensity", 71: "workout_step_index"}
READ_FIELDS = {SESSION_MESSAGE: SESSION_FIELDS, LAP_MESSAGE: LAP_FIELDS}
# The kinds of a lap (the FIT type intensity, FIT SDK Profile 21.221.0). Another number, or none, is not known.
INTENSITY_NAMES = {0: "active", 1: "rest", 2: "warmup", 3: "cooldown", 4: "recovery", 5: "interval", 6: "other"}
# The most laps and sessions that a file may hold: past them the scan stops, so that a file of 128 MiB with
# millions of laps does not fill the memory of the server of the view page.
MAX_LAPS = 10_000
MAX_SESSIONS = 1_000


@dataclass(frozen=True)
class Lap:
    """A lap: its start (seconds of the FIT), its elapsed and timer times (seconds), its distance (metres), its
    intensity, and the index of its workout step; a value that the file does not give is None."""

    start_time: int | None
    elapsed_s: float | None
    timer_s: float | None
    distance_m: float | None
    intensity: int | None
    workout_step_index: int | None


@dataclass(frozen=True)
class Session:
    """A session: its start, its elapsed and timer times, its distance, its number of laps as the file gives it
    (None where it is not a whole number), and its laps."""

    start_time: int | None
    elapsed_s: float | None
    timer_s: float | None
    distance_m: float | None
    num_laps: int | None
    laps: tuple[Lap, ...]


@dataclass(frozen=True)
class LapKinds:
    """What a FIT file says of its laps.

    ``status`` is ``parsed_activity`` (a session or more), ``parsed_non_activity`` (no session and no lap),
    ``session_lap_allocation_conflict``, ``too_many_laps``, ``too_many_sessions``, ``truncated``,
    ``undefined_local_message``, or a status of ``check_fit_container``. The sessions and their laps are given only
    for ``parsed_activity``; ``lap_count`` is every lap of the file that was read.
    """

    status: str
    sessions: tuple[Session, ...] = ()
    lap_count: int = 0


def intensity_name(code: int | None) -> str | None:
    """The name of the kind of a lap, or None where the number is not known."""
    return INTENSITY_NAMES.get(code) if _whole(code) else None


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _code(value: Any) -> int | None:
    """A whole number as it is; anything else, such as an array, is None."""
    return value if _whole(value) else None


def _measure(value: Any, divisor: float) -> float | None:
    """A number divided, as parse_fit_bytes scales it; anything else, and a number that is not finite, is None."""
    if _whole(value) or (isinstance(value, float) and math.isfinite(value)):
        return value / divisor
    return None


def _field_value(data: bytes, offset: int, field: FieldDef, endian: str) -> Any:
    """The value of a field that is read: None where the field is not one value of its type (its size is not that of
    its type, as in an array), where its type is not known, or where it holds the FIT's mark of no value, also 0xFF of
    the type byte, which the parser's table of the marks does not have (Codex's review of the diff of X9b)."""
    base = BASE_TYPES.get(field.base_type) or BASE_TYPES.get(
        (field.base_type & 0x1F) | (0x80 if field.base_type & 0x80 else 0)
    )
    if base is None or field.size != base[1]:
        return None
    value, _ = _null_invalid_with_count(_read_value(data, offset, field, endian), field)
    if base[0] == "byte" and value == 0xFF:
        return None
    return value


def read_lap_kinds(data: bytes) -> LapKinds:
    """Read the sessions and the laps of a FIT file (see the module)."""
    container = check_fit_container(data)
    if container.status is not None:
        return LapKinds(container.status)
    position = container.header_size
    data_end = container.header_size + container.data_size
    definitions: dict[int, Definition] = {}
    sessions: list[dict[str, Any]] = []
    laps: list[Lap] = []

    while position < data_end:
        record_header = data[position]
        position += 1
        if record_header & 0x80:
            local_message = (record_header >> 5) & 0x03
            is_definition = False
        else:
            local_message = record_header & 0x0F
            is_definition = bool(record_header & 0x40)

        if is_definition:
            if position + 5 > data_end:
                return LapKinds("truncated")
            position += 1  # reserved byte
            architecture = data[position]
            position += 1
            endian = ">" if architecture == 1 else "<"
            global_message = struct.unpack_from(endian + "H", data, position)[0]
            position += 2
            field_count = data[position]
            position += 1
            if position + field_count * 3 > data_end:
                return LapKinds("truncated")
            fields = tuple(
                FieldDef(data[position + index * 3], data[position + index * 3 + 1], data[position + index * 3 + 2])
                for index in range(field_count)
            )
            position += field_count * 3
            developer_sizes: tuple[int, ...] = ()
            if record_header & 0x20:
                if position + 1 > data_end:
                    return LapKinds("truncated")
                developer_count = data[position]
                position += 1
                if position + developer_count * 3 > data_end:
                    return LapKinds("truncated")
                developer_sizes = tuple(data[position + index * 3 + 1] for index in range(developer_count))
                position += developer_count * 3
            definitions[local_message] = Definition(endian, global_message, fields, developer_sizes)
            continue

        definition = definitions.get(local_message)
        if definition is None:
            return LapKinds("undefined_local_message")
        total_size = sum(field.size for field in definition.fields) + sum(definition.developer_field_sizes)
        if position + total_size > data_end:
            return LapKinds("truncated")
        wanted = READ_FIELDS.get(definition.global_message)
        if wanted is None:
            # Another message: its values are not read.
            position += total_size
            continue
        values: dict[str, Any] = {}
        for field in definition.fields:
            if field.number in wanted:
                values[wanted[field.number]] = _field_value(data, position, field, definition.endian)
            position += field.size
        position += sum(definition.developer_field_sizes)
        if definition.global_message == SESSION_MESSAGE:
            if len(sessions) >= MAX_SESSIONS:
                return LapKinds("too_many_sessions")
            sessions.append(values)
        else:
            if len(laps) >= MAX_LAPS:
                return LapKinds("too_many_laps")
            laps.append(
                Lap(
                    start_time=_code(values.get("start_time")),
                    elapsed_s=_measure(values.get("elapsed"), 1000.0),
                    timer_s=_measure(values.get("timer"), 1000.0),
                    distance_m=_measure(values.get("distance"), 100.0),
                    intensity=_code(values.get("intensity")),
                    workout_step_index=_code(values.get("workout_step_index")),
                )
            )

    # The rule of parse_fit_bytes, which gives the laps to their sessions.
    laps_by_session: list[tuple[Lap, ...]] = []
    cursor = 0
    conflict = False
    for session in sessions:
        raw_count = session.get("num_laps")
        if len(sessions) == 1:
            count = len(laps)
        elif not _whole(raw_count) or raw_count < 0:
            conflict = True
            count = 0
        else:
            count = raw_count
        laps_by_session.append(tuple(laps[cursor : cursor + count]))
        cursor += count
    if sessions and cursor != len(laps):
        conflict = True
    if not sessions and laps:
        conflict = True
    if conflict:
        return LapKinds("session_lap_allocation_conflict", lap_count=len(laps))
    if not sessions:
        return LapKinds("parsed_non_activity")
    return LapKinds(
        "parsed_activity",
        sessions=tuple(
            Session(
                start_time=_code(session.get("start_time")),
                elapsed_s=_measure(session.get("elapsed"), 1000.0),
                timer_s=_measure(session.get("timer"), 1000.0),
                distance_m=_measure(session.get("distance"), 100.0),
                num_laps=_code(session.get("num_laps")),
                laps=session_laps,
            )
            for session, session_laps in zip(sessions, laps_by_session)
        ),
        lap_count=len(laps),
    )
