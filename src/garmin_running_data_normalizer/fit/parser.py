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

BASE_TYPES = {
    0x00: ("enum", 1, None), 0x01: ("sint8", 1, "b"), 0x02: ("uint8", 1, "B"),
    0x83: ("sint16", 2, "h"), 0x84: ("uint16", 2, "H"), 0x85: ("sint32", 4, "i"),
    0x86: ("uint32", 4, "I"), 0x07: ("string", 1, None), 0x88: ("float32", 4, "f"),
    0x89: ("float64", 8, "d"), 0x0A: ("uint8z", 1, "B"), 0x8B: ("uint16z", 2, "H"),
    0x8C: ("uint32z", 4, "I"), 0x0D: ("byte", 1, "B"), 0x8E: ("sint64", 8, "q"),
    0x8F: ("uint64", 8, "Q"), 0x90: ("uint64z", 8, "Q"),
}

FIELDS = {
    12: {0: ("sport", None), 1: ("sub_sport", None), 3: ("name", None)},
    18: {
        2: ("start_time", "date_time"), 5: ("sport", None), 6: ("sub_sport", None),
        7: ("total_elapsed_time", "sec1000"), 8: ("total_timer_time", "sec1000"),
        9: ("total_distance", "m100"), 14: ("total_calories", None),
        16: ("avg_speed", "speed"), 17: ("max_speed", "speed"),
        20: ("avg_heart_rate", None), 21: ("max_heart_rate", None),
        22: ("avg_cadence", None), 23: ("max_cadence", None),
        24: ("avg_power", None), 25: ("max_power", None),
        26: ("total_ascent", None), 27: ("total_descent", None),
        34: ("num_laps", None), 253: ("timestamp", "date_time"),
    },
    19: {
        2: ("start_time", "date_time"), 7: ("total_elapsed_time", "sec1000"),
        8: ("total_timer_time", "sec1000"), 9: ("total_distance", "m100"),
        16: ("avg_speed", "speed"), 17: ("max_speed", "speed"),
        20: ("avg_heart_rate", None), 21: ("max_heart_rate", None),
        22: ("avg_cadence", None), 23: ("max_cadence", None),
        24: ("avg_power", None), 25: ("max_power", None),
        26: ("total_ascent", None), 27: ("total_descent", None),
        253: ("timestamp", "date_time"),
    },
    # Record message values are deliberately not emitted: precise coordinates
    # and raw telemetry are outside this bounded session/lap implementation.
    20: {},
}

SPORT_ENUM = {1: "running", 2: "cycling", 17: "walking", 31: "hiking", 37: "swimming"}
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


def parse_fit_bytes(
    data: bytes,
    *,
    file_id: str,
    source_path: str,
    timezone_name: str = "Asia/Tokyo",
) -> dict[str, Any]:
    """Parse bounded FIT session/lap fields without exposing record coordinates."""
    if len(data) > MAX_FIT_BYTES:
        return {"status": "too_large", "file_id": file_id, "source_path": source_path}
    if len(data) < 12:
        return {"status": "too_small", "file_id": file_id, "source_path": source_path}
    header_size = data[0]
    if header_size not in (12, 14) or len(data) < header_size or data[8:12] != b".FIT":
        return {"status": "bad_header", "file_id": file_id, "source_path": source_path}
    data_size = struct.unpack_from("<I", data, 4)[0]
    if header_size + data_size > len(data):
        return {"status": "truncated", "file_id": file_id, "source_path": source_path}

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
                return {"status": "truncated", "file_id": file_id, "source_path": source_path}
            position += 1  # reserved byte
            architecture = data[position]
            position += 1
            endian = ">" if architecture == 1 else "<"
            global_message = struct.unpack_from(endian + "H", data, position)[0]
            position += 2
            field_count = data[position]
            position += 1
            if position + field_count * 3 > data_end:
                return {"status": "truncated", "file_id": file_id, "source_path": source_path}
            fields = tuple(
                FieldDef(data[position + index * 3], data[position + index * 3 + 1], data[position + index * 3 + 2])
                for index in range(field_count)
            )
            position += field_count * 3
            developer_sizes: tuple[int, ...] = ()
            if record_header & 0x20:
                if position + 1 > data_end:
                    return {"status": "truncated", "file_id": file_id, "source_path": source_path}
                developer_count = data[position]
                position += 1
                if position + developer_count * 3 > data_end:
                    return {"status": "truncated", "file_id": file_id, "source_path": source_path}
                developer_sizes = tuple(data[position + index * 3 + 1] for index in range(developer_count))
                position += developer_count * 3
            definitions[local_message] = Definition(endian, global_message, fields, developer_sizes)
            continue

        definition = definitions.get(local_message)
        if definition is None:
            unknown_records += 1
            break
        total_field_size = sum(field.size for field in definition.fields) + sum(definition.developer_field_sizes)
        if position + total_field_size > data_end:
            return {"status": "truncated", "file_id": file_id, "source_path": source_path}
        selected_fields = FIELDS.get(definition.global_message)
        record: dict[str, Any] = {}
        for field in definition.fields:
            value = _read_value(data, position, field, definition.endian)
            position += field.size
            if selected_fields is not None and field.number in selected_fields:
                name, scale = selected_fields[field.number]
                record[name] = _scale(value, scale, timezone_name)
        position += sum(definition.developer_field_sizes)
        if definition.global_message in messages:
            messages[definition.global_message].append(record)

    session = messages[18][0] if messages[18] else None
    sport_message = messages[12][0] if messages[12] else {}
    return {
        "status": "parsed_activity" if session else "parsed_non_activity",
        "file_id": file_id,
        "source_path": source_path,
        "session": session,
        "sport": sport_message,
        "laps": messages[19],
        "record_count": len(messages[20]),
        "lap_count": len(messages[19]),
        "unknown_records": unknown_records,
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
        })
        if parsed["status"] != "parsed_activity":
            continue
        session = parsed.get("session") or {}
        sport = parsed.get("sport") or {}
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
            "avg_power": session.get("avg_power"),
            "max_power": session.get("max_power"),
            "record_count": parsed.get("record_count"),
            "lap_count": parsed.get("lap_count"),
        })
        for lap_index, lap in enumerate(parsed.get("laps") or []):
            laps.append({
                "fit_file_id": file_id,
                "lap_index": lap_index,
                "source_path": asset.provenance_path,
                "source_sha256": asset.sha256,
                **lap,
            })
    return activities, laps, audit
