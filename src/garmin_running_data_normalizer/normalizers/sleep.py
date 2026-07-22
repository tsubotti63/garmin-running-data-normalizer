from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset, load_json_assets

MAX_SAFE_INTEGER = (1 << 53) - 1


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("sleepData", "data", "records", "items"):
        wrapped = value.get(key)
        if isinstance(wrapped, list):
            return [item for item in wrapped if isinstance(item, dict)]
    return [value]


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, int):
        return value if abs(value) <= MAX_SAFE_INTEGER else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:
        parsed = float(str(value))
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed) if parsed.is_integer() else parsed


def _first_number(row: dict[str, Any], *names: str) -> int | float | None:
    for name in names:
        value = _number(row.get(name))
        if value is not None:
            return value
    return None


def _timestamps(value: Any, timezone_name: str) -> tuple[str | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        utc_value = parsed.astimezone(timezone.utc)
        local_value = utc_value.astimezone(ZoneInfo(timezone_name))
    except (TypeError, ValueError):
        return None, None
    return utc_value.isoformat(), local_value.isoformat()


def _sleep_score(row: dict[str, Any]) -> int | float | None:
    scores = row.get("sleepScores")
    if isinstance(scores, dict):
        direct = _number(scores.get("overallScore"))
        if direct is not None:
            return direct
        overall = scores.get("overall")
        if isinstance(overall, dict):
            nested = _number(overall.get("value"))
            if nested is not None:
                return nested
    return _first_number(row, "overallScore", "sleepScore")


def _normalize_record(
    row: dict[str, Any],
    asset: DiscoveredAsset,
    record_index: int,
    timezone_name: str,
) -> dict[str, Any]:
    start_gmt, start_local = _timestamps(row.get("sleepStartTimestampGMT"), timezone_name)
    end_gmt, end_local = _timestamps(row.get("sleepEndTimestampGMT"), timezone_name)
    sleep_day = end_local[:10] if end_local else None
    score = _sleep_score(row)

    deep_seconds = _first_number(row, "deepSleepSeconds", "deep_sleep_seconds")
    light_seconds = _first_number(row, "lightSleepSeconds", "light_sleep_seconds")
    rem_seconds = _first_number(row, "remSleepSeconds", "rem_sleep_seconds")
    awake_seconds = _first_number(row, "awakeSleepSeconds", "awake_sleep_seconds")
    stages = [deep_seconds, light_seconds, rem_seconds]
    stage_sum = sum(value for value in stages if value is not None) if any(
        value is not None for value in stages
    ) else None
    total_seconds = stage_sum
    if total_seconds is None:
        total_seconds = _first_number(row, "totalSleepSeconds", "durationInSeconds", "sleepDuration")

    window_minutes = None
    if start_gmt and end_gmt:
        start = datetime.fromisoformat(start_gmt)
        end = datetime.fromisoformat(end_gmt)
        window_minutes = (end - start).total_seconds() / 60.0

    empty_retro_only = (
        daily_calendar_date(row.get("calendarDate")) is None
        and start_local is None
        and end_local is None
        and score is None
        and ("retro" in row or len(row) == 1)
    )
    valid_interval = window_minutes is not None and window_minutes > 0

    status = "available"
    limitation = "none"
    reason = "sleep_json_daily_available"
    available = True
    if empty_retro_only:
        status = "excluded_empty_record"
        limitation = "empty_record"
        reason = "sleep_json_empty_retro_only_record"
        available = False
    elif sleep_day is None:
        status = "needs_review"
        limitation = "data_quality_limitation"
        reason = "sleep_json_missing_sleep_end_date_jst"
        available = False
    elif start_local is None or end_local is None:
        status = "needs_review"
        limitation = "data_quality_limitation"
        reason = "sleep_json_missing_start_or_end"
        available = False
    elif not valid_interval:
        status = "needs_review"
        limitation = "data_quality_limitation"
        reason = "sleep_json_invalid_sleep_interval"
        available = False

    return {
        "sleep_record_key": f"sleep_record:{asset.sha256[:24]}:{record_index}",
        "sleep_day": sleep_day,
        "sleep_calendar_date_source": daily_calendar_date(row.get("calendarDate")),
        "sleep_attribution_rule": "sleep_period_ending_on_sleep_end_date_jst",
        "sleep_start_gmt": start_gmt,
        "sleep_end_gmt": end_gmt,
        "sleep_start_local": start_local,
        "sleep_end_local": end_local,
        "sleep_duration_minutes_ex_awake": None if total_seconds is None else total_seconds / 60.0,
        "sleep_window_minutes_including_awake": window_minutes,
        "sleep_score": score,
        "sleep_score_available_flag": score is not None,
        "sleep_stage_deep_minutes": None if deep_seconds is None else deep_seconds / 60.0,
        "sleep_stage_light_minutes": None if light_seconds is None else light_seconds / 60.0,
        "sleep_stage_rem_minutes": None if rem_seconds is None else rem_seconds / 60.0,
        "sleep_awake_minutes": None if awake_seconds is None else awake_seconds / 60.0,
        "sleep_stage_available_flag": any(value is not None for value in stages),
        "sleep_window_confirmation_type": row.get("sleepWindowConfirmationType"),
        "sleep_retro_flag": row.get("retro"),
        "sleep_normalization_status": status,
        "sleep_limitation_type": limitation,
        "sleep_reason_code": reason,
        "sleep_source_available_for_analysis_flag": available,
        "source_path": asset.provenance_path,
        "source_sha256": asset.sha256,
        "source_confidence": "high",
    }


def normalize_sleep(root: str, timezone_name: str = "Asia/Tokyo") -> list[dict[str, Any]]:
    """Normalize Garmin sleepData JSON without filling, inference, or activity joins."""
    normalized: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, filename_suffix="sleepData.json"):
        for record_index, row in enumerate(_records(payload)):
            normalized.append(_normalize_record(row, asset, record_index, timezone_name))

    duplicate_days: dict[str, list[dict[str, Any]]] = {}
    for record in normalized:
        sleep_day = record.get("sleep_day")
        if sleep_day is not None and record["sleep_normalization_status"] != "excluded_empty_record":
            duplicate_days.setdefault(str(sleep_day), []).append(record)
    for records in duplicate_days.values():
        if len(records) < 2:
            continue
        for record in records:
            record["sleep_normalization_status"] = "needs_review"
            record["sleep_limitation_type"] = "data_quality_limitation"
            record["sleep_reason_code"] = "sleep_json_duplicate_sleep_day"
            record["sleep_source_available_for_analysis_flag"] = False

    return sorted(normalized, key=lambda record: str(record["sleep_record_key"]))
