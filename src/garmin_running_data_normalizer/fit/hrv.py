from __future__ import annotations

import math
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..intake.discovery import discover_export
from .parser import Definition, FieldDef, FIT_EPOCH_OFFSET, MAX_FIT_BYTES, _read_value

FIT_HRV_MESSAGE_NUM = 370
FIT_HRV_VALUE_FIELD_NUM = 1
FIT_TIMESTAMP_FIELD_NUM = 253
FIT_HRV_DIVISOR = 128.0
FIT_HRV_INVALID_RAW_VALUE = 65535
FIT_TIMESTAMP_INVALID_RAW_VALUE = 0xFFFFFFFF


def _fit_datetime(value: Any, timezone_name: str) -> str | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value == FIT_TIMESTAMP_INVALID_RAW_VALUE
    ):
        return None
    try:
        unix_seconds = int(value) + FIT_EPOCH_OFFSET
        return datetime.fromtimestamp(unix_seconds, timezone.utc).astimezone(
            ZoneInfo(timezone_name)
        ).isoformat()
    except (OverflowError, TypeError, ValueError):
        return None


def _empty_result(status: str, file_id: str, source_path: str) -> dict[str, Any]:
    return {
        "status": status,
        "fit_file_id": file_id,
        "source_path": source_path,
        "records": [],
        "message370_record_count": 0,
        "hrv_record_count": 0,
        "unknown_records": 0,
    }


def parse_fit_hrv_bytes(
    data: bytes,
    *,
    file_id: str,
    source_path: str,
    timezone_name: str = "Asia/Tokyo",
) -> dict[str, Any]:
    """Extract the bounded HRV PoC signal from FIT message 370 field 1."""
    if len(data) > MAX_FIT_BYTES:
        return _empty_result("too_large", file_id, source_path)
    if len(data) < 12:
        return _empty_result("too_small", file_id, source_path)
    header_size = data[0]
    if header_size not in (12, 14) or len(data) < header_size or data[8:12] != b".FIT":
        return _empty_result("bad_header", file_id, source_path)
    data_size = struct.unpack_from("<I", data, 4)[0]
    if header_size + data_size > len(data):
        return _empty_result("truncated", file_id, source_path)

    position = header_size
    data_end = header_size + data_size
    definitions: dict[int, Definition] = {}
    records: list[dict[str, Any]] = []
    unknown_records = 0
    message_count = 0

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
                return _empty_result("truncated", file_id, source_path)
            position += 1
            architecture = data[position]
            position += 1
            endian = ">" if architecture == 1 else "<"
            global_message = struct.unpack_from(endian + "H", data, position)[0]
            position += 2
            field_count = data[position]
            position += 1
            if position + field_count * 3 > data_end:
                return _empty_result("truncated", file_id, source_path)
            fields = tuple(
                FieldDef(
                    data[position + index * 3],
                    data[position + index * 3 + 1],
                    data[position + index * 3 + 2],
                )
                for index in range(field_count)
            )
            position += field_count * 3
            developer_sizes: tuple[int, ...] = ()
            if record_header & 0x20:
                if position >= data_end:
                    return _empty_result("truncated", file_id, source_path)
                developer_count = data[position]
                position += 1
                if position + developer_count * 3 > data_end:
                    return _empty_result("truncated", file_id, source_path)
                developer_sizes = tuple(
                    data[position + index * 3 + 1] for index in range(developer_count)
                )
                position += developer_count * 3
            definitions[local_message] = Definition(
                endian, global_message, fields, developer_sizes
            )
            continue

        definition = definitions.get(local_message)
        if definition is None:
            unknown_records += 1
            break
        total_size = sum(field.size for field in definition.fields) + sum(
            definition.developer_field_sizes
        )
        if position + total_size > data_end:
            return _empty_result("truncated", file_id, source_path)

        values: dict[int, Any] = {}
        for field in definition.fields:
            value = _read_value(data, position, field, definition.endian)
            position += field.size
            if definition.global_message == FIT_HRV_MESSAGE_NUM:
                values[field.number] = value
        position += sum(definition.developer_field_sizes)
        if definition.global_message != FIT_HRV_MESSAGE_NUM:
            continue

        message_count += 1
        raw_value = values.get(FIT_HRV_VALUE_FIELD_NUM)
        timestamp_raw = values.get(FIT_TIMESTAMP_FIELD_NUM)
        scalar_raw = (
            raw_value
            if isinstance(raw_value, int) and not isinstance(raw_value, bool)
            else None
        )
        invalid = scalar_raw == FIT_HRV_INVALID_RAW_VALUE
        hrv_value = None
        if scalar_raw is not None and not invalid:
            candidate = float(scalar_raw) / FIT_HRV_DIVISOR
            hrv_value = candidate if math.isfinite(candidate) else None
        timestamp_safe = (
            timestamp_raw
            if isinstance(timestamp_raw, int)
            and not isinstance(timestamp_raw, bool)
            and timestamp_raw != FIT_TIMESTAMP_INVALID_RAW_VALUE
            else None
        )
        timestamp_local = _fit_datetime(timestamp_safe, timezone_name)
        date = timestamp_local[:10] if timestamp_local else None
        raw_hold = date is None or (hrv_value is None and not invalid)

        if invalid:
            confidence = "invalid_raw_value"
            needs_inspection = False
            raw_hold = False
        elif raw_hold:
            confidence = "raw_required_hold"
            needs_inspection = False
        else:
            confidence = "needs_inspection"
            needs_inspection = True

        records.append(
            {
                "date": date,
                "fit_hrv_value": hrv_value,
                "fit_hrv_unit": "ms",
                "fit_hrv_raw_value": scalar_raw,
                "fit_hrv_invalid_raw_value_flag": invalid,
                "fit_message_name_or_num": "message370",
                "fit_field_name_or_num": "field_1",
                "fit_file_id": file_id,
                "source_path": source_path,
                "extraction_method": "fit_message370_field1_raw_div_128",
                "confidence_status": confidence,
                "needs_inspection_flag": needs_inspection,
                "raw_required_hold_flag": raw_hold,
                "record_timestamp_raw": timestamp_safe,
                "record_timestamp_local": timestamp_local,
                "date_semantics_note": "date derived from message370 field253 timestamp converted to local date",
                "date_semantics_confidence": "medium" if date else "needs_inspection",
                "dedupe_method": "not_deduped_record_level",
            }
        )

    return {
        "status": "parsed_fit_hrv" if records else "no_fit_hrv_records",
        "fit_file_id": file_id,
        "source_path": source_path,
        "records": records,
        "message370_record_count": message_count,
        "hrv_record_count": len(records),
        "unknown_records": unknown_records,
    }


def dedupe_fit_hrv_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build daily FIT HRV candidates without filling or averaging conflicts."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    hold_rows: list[dict[str, Any]] = []
    for row in rows:
        date = row.get("date")
        if date is None:
            hold_rows.append(row)
        else:
            grouped.setdefault(str(date), []).append(row)

    daily: list[dict[str, Any]] = []
    for date, items in sorted(grouped.items()):
        invalid_items = [item for item in items if item["fit_hrv_invalid_raw_value_flag"]]
        valid_items = [item for item in items if not item["fit_hrv_invalid_raw_value_flag"]]
        unique_values = sorted(
            {item["fit_hrv_value"] for item in valid_items if item["fit_hrv_value"] is not None}
        )
        base = dict(valid_items[0] if valid_items else items[0])
        base.update(
            {
                "date": date,
                "record_count_for_date": len(items),
                "source_file_count_for_date": len({item["fit_file_id"] for item in items}),
                "invalid_raw_value_count_for_date": len(invalid_items),
            }
        )
        if len(unique_values) == 1:
            base.update(
                {
                    "fit_hrv_value": unique_values[0],
                    "fit_hrv_invalid_raw_value_flag": False,
                    "confidence_status": "needs_inspection",
                    "needs_inspection_flag": True,
                    "raw_required_hold_flag": False,
                    "dedupe_method": "same_date_valid_value_after_invalid_excluded"
                    if invalid_items
                    else "same_date_same_value_deduped",
                }
            )
        elif len(unique_values) > 1:
            base.update(
                {
                    "fit_hrv_value": None,
                    "confidence_status": "needs_inspection",
                    "needs_inspection_flag": True,
                    "raw_required_hold_flag": False,
                    "dedupe_method": "same_date_different_valid_values_not_averaged",
                    "valid_values_for_review": unique_values,
                }
            )
        elif invalid_items:
            base.update(
                {
                    "fit_hrv_value": None,
                    "fit_hrv_invalid_raw_value_flag": True,
                    "confidence_status": "invalid_raw_value",
                    "needs_inspection_flag": False,
                    "raw_required_hold_flag": False,
                    "dedupe_method": "only_invalid_raw_values_excluded",
                }
            )
        else:
            base.update(
                {
                    "fit_hrv_value": None,
                    "confidence_status": "raw_required_hold",
                    "needs_inspection_flag": False,
                    "raw_required_hold_flag": True,
                    "dedupe_method": "no_valid_value_for_date",
                }
            )
        daily.append(base)

    for row in hold_rows:
        hold = dict(row)
        hold.update(
            {
                "record_count_for_date": 1,
                "source_file_count_for_date": 1,
                "invalid_raw_value_count_for_date": int(
                    bool(hold["fit_hrv_invalid_raw_value_flag"])
                ),
                "confidence_status": "raw_required_hold",
                "needs_inspection_flag": False,
                "raw_required_hold_flag": True,
                "dedupe_method": "missing_date_raw_required_hold",
            }
        )
        daily.append(hold)
    return sorted(daily, key=lambda row: (str(row.get("date")), row["fit_file_id"]))


def parse_fit_hrv_export(
    root: str | Path, timezone_name: str = "Asia/Tokyo"
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for asset in (item for item in discover_export(root) if item.kind == "fit"):
        file_id = f"fit_file:{asset.sha256[:24]}"
        parsed = parse_fit_hrv_bytes(
            asset.data,
            file_id=file_id,
            source_path=asset.provenance_path,
            timezone_name=timezone_name,
        )
        audit.append(
            {
                "fit_file_id": file_id,
                "source_path": asset.provenance_path,
                "source_sha256": asset.sha256,
                "parse_status": parsed["status"],
                "message370_record_count": parsed["message370_record_count"],
                "hrv_record_count": parsed["hrv_record_count"],
                "unknown_records": parsed["unknown_records"],
            }
        )
        for record in parsed["records"]:
            record["source_sha256"] = asset.sha256
            records.append(record)
    return dedupe_fit_hrv_daily(records), audit
