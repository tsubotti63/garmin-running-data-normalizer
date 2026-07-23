from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..intake.discovery import discover_export

FIT_EPOCH_OFFSET = 631065600
MAX_FIT_BYTES = 128 * 1024 * 1024
FIT_CRC_TABLE = (
    0x0000, 0xCC01, 0xD801, 0x1400,
    0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401,
    0x5000, 0x9C01, 0x8801, 0x4400,
)

BASE_TYPES = {
    0x00: ("enum", 1, None), 0x01: ("sint8", 1, "b"), 0x02: ("uint8", 1, "B"),
    0x83: ("sint16", 2, "h"), 0x84: ("uint16", 2, "H"), 0x85: ("sint32", 4, "i"),
    0x86: ("uint32", 4, "I"), 0x07: ("string", 1, None), 0x88: ("float32", 4, "f"),
    0x89: ("float64", 8, "d"), 0x0A: ("uint8z", 1, "B"), 0x8B: ("uint16z", 2, "H"),
    0x8C: ("uint32z", 4, "I"), 0x0D: ("byte", 1, "B"), 0x8E: ("sint64", 8, "q"),
    0x8F: ("uint64", 8, "Q"), 0x90: ("uint64z", 8, "Q"),
}

INVALID_VALUES = {
    "enum": 0xFF, "sint8": 0x7F, "uint8": 0xFF, "sint16": 0x7FFF,
    "uint16": 0xFFFF, "sint32": 0x7FFFFFFF, "uint32": 0xFFFFFFFF,
    "uint8z": 0, "uint16z": 0, "uint32z": 0,
    "sint64": 0x7FFFFFFFFFFFFFFF, "uint64": 0xFFFFFFFFFFFFFFFF, "uint64z": 0,
}

INVALID_BEFORE_SCALE_FIELDS = {
    18: {11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 26},
    19: {13, 14, 15, 16, 17, 18, 19, 20, 21, 22},
}

FIELDS = {
    12: {0: ("sport", None), 1: ("sub_sport", None), 3: ("name", None)},
    18: {
        2: ("start_time", "date_time"), 5: ("sport", None), 6: ("sub_sport", None),
        7: ("total_elapsed_time", "sec1000"), 8: ("total_timer_time", "sec1000"),
        9: ("total_distance", "m100"), 11: ("total_calories", None),
        14: ("avg_speed", "speed"), 15: ("max_speed", "speed"),
        16: ("avg_heart_rate", None), 17: ("max_heart_rate", None),
        18: ("avg_cadence", None), 19: ("max_cadence", None),
        20: ("avg_power", None), 21: ("max_power", None),
        22: ("total_ascent", None), 23: ("total_descent", None),
        26: ("num_laps", None), 253: ("timestamp", "date_time"),
    },
    19: {
        2: ("start_time", "date_time"), 7: ("total_elapsed_time", "sec1000"),
        8: ("total_timer_time", "sec1000"), 9: ("total_distance", "m100"),
        13: ("avg_speed", "speed"), 14: ("max_speed", "speed"),
        15: ("avg_heart_rate", None), 16: ("max_heart_rate", None),
        17: ("avg_cadence", None), 18: ("max_cadence", None),
        19: ("avg_power", None), 20: ("max_power", None),
        21: ("total_ascent", None), 22: ("total_descent", None),
        253: ("timestamp", "date_time"),
    },
    # Record message values are deliberately not emitted: precise coordinates
    # and raw telemetry are outside this bounded session/lap implementation.
    20: {},
}

SPORT_ENUM = {
    1: "running",
    2: "cycling",
    10: "strength_training",
    11: "walking",
    17: "hiking",
    31: "swimming",
}
SUB_SPORT_ENUM = {6: "treadmill_running", 7: "street", 8: "trail"}


@dataclass(frozen=True)
class FieldDef:
    number: int
    size: int
    base_type: int


@dataclass(frozen=True)
class Definition:
    endian: str
    global_message: int
    fields: tuple[FieldDef, ...]
    developer_field_sizes: tuple[int, ...] = ()


def fit_crc16(data: bytes, initial: int = 0) -> int:
    """Return the FIT protocol CRC-16 for *data*."""
    crc = initial & 0xFFFF
    for byte in data:
        temporary = FIT_CRC_TABLE[crc & 0x0F]
        crc = ((crc >> 4) & 0x0FFF) ^ temporary ^ FIT_CRC_TABLE[byte & 0x0F]
        temporary = FIT_CRC_TABLE[crc & 0x0F]
        crc = (
            ((crc >> 4) & 0x0FFF)
            ^ temporary
            ^ FIT_CRC_TABLE[(byte >> 4) & 0x0F]
        )
    return crc & 0xFFFF


def _base_result(
    status: str,
    *,
    file_id: str,
    source_path: str,
    header_crc_status: str = "not_checked",
    file_crc_status: str = "not_checked",
) -> dict[str, Any]:
    return {
        "status": status,
        "file_id": file_id,
        "source_path": source_path,
        "header_crc_status": header_crc_status,
        "file_crc_status": file_crc_status,
    }


def _fit_datetime(value: Any, timezone_name: str) -> str | None:
    if value is None:
        return None
    try:
        unix_seconds = int(value) + FIT_EPOCH_OFFSET
        return datetime.fromtimestamp(unix_seconds, timezone.utc).astimezone(
            ZoneInfo(timezone_name)
        ).isoformat()
    except (OverflowError, TypeError, ValueError):
        return None


def _scale(value: Any, scale: str | None, timezone_name: str) -> Any:
    if value is None:
        return None
    try:
        if scale == "date_time":
            return _fit_datetime(value, timezone_name)
        if scale == "sec1000":
            return float(value) / 1000.0
        if scale == "m100":
            return float(value) / 100.0
        if scale == "speed":
            return float(value) / 1000.0
    except (TypeError, ValueError):
        return value
    return value


def _read_value(data: bytes, offset: int, field: FieldDef, endian: str) -> Any:
    descriptor = BASE_TYPES.get(field.base_type)
    if descriptor is None:
        normalized_type = (field.base_type & 0x1F) | (0x80 if field.base_type & 0x80 else 0)
        descriptor = BASE_TYPES.get(normalized_type)
    if descriptor is None or offset + field.size > len(data):
        return None
    name, type_size, format_code = descriptor
    raw = data[offset : offset + field.size]
    if name == "string":
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    if format_code is None:
        return raw[0] if raw else None
    count = field.size // type_size
    if count <= 0:
        return None
    try:
        values = struct.unpack(endian + format_code * count, raw[: count * type_size])
    except struct.error:
        return None
    return values[0] if count == 1 else list(values)


def _null_invalid(value: Any, field: FieldDef) -> Any:
    descriptor = BASE_TYPES.get(field.base_type)
    if descriptor is None:
        normalized_type = (field.base_type & 0x1F) | (0x80 if field.base_type & 0x80 else 0)
        descriptor = BASE_TYPES.get(normalized_type)
    invalid = INVALID_VALUES.get(descriptor[0]) if descriptor else None
    if invalid is None:
        return value
    if isinstance(value, list):
        return [None if item == invalid else item for item in value]
    return None if value == invalid else value


def parse_fit_bytes(
    data: bytes,
    *,
    file_id: str,
    source_path: str,
    timezone_name: str = "Asia/Tokyo",
) -> dict[str, Any]:
    """Parse bounded FIT session/lap fields without exposing record coordinates."""
    if len(data) > MAX_FIT_BYTES:
        return _base_result("too_large", file_id=file_id, source_path=source_path)
    if len(data) < 12:
        return _base_result("too_small", file_id=file_id, source_path=source_path)
    header_size = data[0]
    if header_size not in (12, 14) or len(data) < header_size or data[8:12] != b".FIT":
        return _base_result("bad_header", file_id=file_id, source_path=source_path)
    data_size = struct.unpack_from("<I", data, 4)[0]
    expected_size = header_size + data_size + 2
    if len(data) < expected_size:
        return _base_result("truncated", file_id=file_id, source_path=source_path)
    if len(data) > expected_size:
        return _base_result(
            "unsupported_chained",
            file_id=file_id,
            source_path=source_path,
        )

    header_crc_status = "not_present"
    if header_size == 14:
        expected_header_crc = struct.unpack_from("<H", data, 12)[0]
        if expected_header_crc:
            actual_header_crc = fit_crc16(data[:12])
            if actual_header_crc != expected_header_crc:
                return _base_result(
                    "bad_header_crc",
                    file_id=file_id,
                    source_path=source_path,
                    header_crc_status="invalid",
                )
            header_crc_status = "valid"

    expected_file_crc = struct.unpack_from("<H", data, header_size + data_size)[0]
    actual_file_crc = fit_crc16(data[: header_size + data_size])
    if actual_file_crc != expected_file_crc:
        return _base_result(
            "bad_file_crc",
            file_id=file_id,
            source_path=source_path,
            header_crc_status=header_crc_status,
            file_crc_status="invalid",
        )

    position = header_size
    data_end = header_size + data_size
    definitions: dict[int, Definition] = {}
    messages: dict[int, list[dict[str, Any]]] = {12: [], 18: [], 19: [], 20: []}
    unknown_records = 0

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
                return _base_result(
                    "truncated",
                    file_id=file_id,
                    source_path=source_path,
                    header_crc_status=header_crc_status,
                    file_crc_status="valid",
                )
            position += 1  # reserved byte
            architecture = data[position]
            position += 1
            endian = ">" if architecture == 1 else "<"
            global_message = struct.unpack_from(endian + "H", data, position)[0]
            position += 2
            field_count = data[position]
            position += 1
            if position + field_count * 3 > data_end:
                return _base_result(
                    "truncated",
                    file_id=file_id,
                    source_path=source_path,
                    header_crc_status=header_crc_status,
                    file_crc_status="valid",
                )
            fields = tuple(
                FieldDef(data[position + index * 3], data[position + index * 3 + 1], data[position + index * 3 + 2])
                for index in range(field_count)
            )
            position += field_count * 3
            developer_sizes: tuple[int, ...] = ()
            if record_header & 0x20:
                if position + 1 > data_end:
                    return _base_result(
                        "truncated",
                        file_id=file_id,
                        source_path=source_path,
                        header_crc_status=header_crc_status,
                        file_crc_status="valid",
                    )
                developer_count = data[position]
                position += 1
                if position + developer_count * 3 > data_end:
                    return _base_result(
                        "truncated",
                        file_id=file_id,
                        source_path=source_path,
                        header_crc_status=header_crc_status,
                        file_crc_status="valid",
                    )
                developer_sizes = tuple(data[position + index * 3 + 1] for index in range(developer_count))
                position += developer_count * 3
            definitions[local_message] = Definition(endian, global_message, fields, developer_sizes)
            continue

        definition = definitions.get(local_message)
        if definition is None:
            return _base_result(
                "undefined_local_message",
                file_id=file_id,
                source_path=source_path,
                header_crc_status=header_crc_status,
                file_crc_status="valid",
            )
        total_field_size = sum(field.size for field in definition.fields) + sum(definition.developer_field_sizes)
        if position + total_field_size > data_end:
            return _base_result(
                "truncated",
                file_id=file_id,
                source_path=source_path,
                header_crc_status=header_crc_status,
                file_crc_status="valid",
            )
        selected_fields = FIELDS.get(definition.global_message)
        record: dict[str, Any] = {}
        for field in definition.fields:
            value = _read_value(data, position, field, definition.endian)
            position += field.size
            if selected_fields is not None and field.number in selected_fields:
                name, scale = selected_fields[field.number]
                if field.number in INVALID_BEFORE_SCALE_FIELDS.get(definition.global_message, set()):
                    value = _null_invalid(value, field)
                record[name] = _scale(value, scale, timezone_name)
        position += sum(definition.developer_field_sizes)
        if definition.global_message in messages:
            messages[definition.global_message].append(record)

    sessions = messages[18]
    session = sessions[0] if sessions else None
    sport_message = messages[12][0] if messages[12] else {}
    all_laps = messages[19]
    laps_by_session: list[list[dict[str, Any]]] = []
    lap_cursor = 0
    allocation_conflict = False
    for item in sessions:
        raw_count = item.get("num_laps")
        if len(sessions) == 1:
            count = len(all_laps)
        elif not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 0:
            allocation_conflict = True
            count = 0
        else:
            count = raw_count
        laps_by_session.append(all_laps[lap_cursor : lap_cursor + count])
        lap_cursor += count
    if sessions and lap_cursor != len(all_laps):
        allocation_conflict = True
    if not sessions and all_laps:
        allocation_conflict = True
    status = (
        "session_lap_allocation_conflict"
        if allocation_conflict
        else "parsed_activity"
        if session
        else "parsed_non_activity"
    )
    return {
        "status": status,
        "file_id": file_id,
        "source_path": source_path,
        "session": session,
        "sessions": sessions,
        "sport": sport_message,
        "laps": all_laps,
        "laps_by_session": laps_by_session,
        "record_count": len(messages[20]),
        "lap_count": len(all_laps),
        "session_count": len(sessions),
        "unallocated_lap_count": max(len(all_laps) - lap_cursor, 0),
        "unknown_records": unknown_records,
        "header_crc_status": header_crc_status,
        "file_crc_status": "valid",
    }


def parse_fit_export(root: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    activities: list[dict[str, Any]] = []
    laps: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    fit_assets = [asset for asset in discover_export(root) if asset.kind == "fit"]
    for asset in fit_assets:
        file_id = f"fit_file:{asset.sha256[:24]}"
        parsed = parse_fit_bytes(asset.data, file_id=file_id, source_path=asset.provenance_path)
        audit.append({
            "fit_file_id": file_id,
            "source_path": asset.provenance_path,
            "source_sha256": asset.sha256,
            "parse_status": parsed["status"],
            "record_count": parsed.get("record_count", 0),
            "lap_count": parsed.get("lap_count", 0),
            "session_count": parsed.get("session_count", 0),
            "header_crc_status": parsed.get("header_crc_status", "not_checked"),
            "file_crc_status": parsed.get("file_crc_status", "not_checked"),
            "unallocated_lap_count": parsed.get("unallocated_lap_count", 0),
        })
        if parsed["status"] != "parsed_activity":
            continue
        sport = parsed.get("sport") or {}
        for session_ordinal, session in enumerate(parsed.get("sessions") or []):
            fit_session_key = f"fit_session:{asset.sha256}:{session_ordinal}"
            sport_code = session.get("sport", sport.get("sport"))
            sub_code = session.get("sub_sport", sport.get("sub_sport"))
            fit_sport = SPORT_ENUM.get(sport_code, str(sport_code or "unknown"))
            fit_sub_sport = SUB_SPORT_ENUM.get(sub_code)
            if fit_sub_sport == "trail":
                fit_sport = "trail_running"
            elif fit_sub_sport == "treadmill_running":
                fit_sport = "treadmill_running"
            activities.append({
                "fit_file_id": file_id,
                "fit_session_key": fit_session_key,
                "session_ordinal": session_ordinal,
                "source_path": asset.provenance_path,
                "source_sha256": asset.sha256,
                "start_datetime_local": session.get("start_time"),
                "sport": fit_sport,
                "sub_sport": fit_sub_sport,
                "distance_m": session.get("total_distance"),
                "elapsed_time_sec": session.get("total_elapsed_time"),
                "timer_time_sec": session.get("total_timer_time"),
                "avg_heart_rate": session.get("avg_heart_rate"),
                "max_heart_rate": session.get("max_heart_rate"),
                "avg_cadence": session.get("avg_cadence"),
                "max_cadence": session.get("max_cadence"),
                "avg_power": session.get("avg_power"),
                "max_power": session.get("max_power"),
                "total_ascent": session.get("total_ascent"),
                "total_descent": session.get("total_descent"),
                "record_count": parsed.get("record_count"),
                "lap_count": len((parsed.get("laps_by_session") or [])[session_ordinal]),
            })
            for lap_ordinal, lap in enumerate(
                (parsed.get("laps_by_session") or [])[session_ordinal]
            ):
                laps.append({
                    "fit_file_id": file_id,
                    "fit_session_key": fit_session_key,
                    "fit_lap_key": f"{fit_session_key}:lap:{lap_ordinal}",
                    "session_ordinal": session_ordinal,
                    "lap_ordinal_within_session": lap_ordinal,
                    "lap_index": lap_ordinal,
                    "source_path": asset.provenance_path,
                    "source_sha256": asset.sha256,
                    **lap,
                })
    return activities, laps, audit
