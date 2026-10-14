from __future__ import annotations

from datetime import datetime, timezone
from collections import Counter
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from ..common.time import TIME_OUT_OF_RANGE, daily_calendar_date
from ..common.values import ValueReader, is_empty
from ..intake.discovery import DiscoveredAsset, load_json_assets
from .daily_metrics import (
    DailyMetricResult,
    RowsLeftOut,
    copies_within_snapshots,
    finalize_daily,
    load_rows,
    logical_basename,
    snapshot_numbers,
    value_source_names,
)

SLEEP_STAGE_ALIASES = (
    ("deepSleepSeconds", "deep_sleep_seconds"),
    ("lightSleepSeconds", "light_sleep_seconds"),
    ("remSleepSeconds", "rem_sleep_seconds"),
)
SLEEP_DIRECT_DURATION_ALIASES = (
    "sleepTimeSeconds",
    "totalSleepSeconds",
    "durationInSeconds",
    "sleepDuration",
)


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


def _number(
    value: Any,
    values: ValueReader | None = None,
    field: str = "",
) -> int | float | None:
    """A number, as a number field takes it (stage A3d-2a: text such as "5" is
    not a number); a value of another form is kept in ``values``."""
    return (values or ValueReader()).number(value, field)


def _first_number(
    row: dict[str, Any],
    *names: str,
    values: ValueReader | None = None,
    field: str = "",
) -> int | float | None:
    """The first of the source fields that holds a number. A value of another
    form in a source field read before it is kept in ``values``."""
    for name in names:
        value = _number(row.get(name), values, field)
        if value is not None:
            return value
    return None


def _sleep_duration_seconds(
    row: dict[str, Any],
    values: ValueReader | None = None,
) -> tuple[int | float | None, str, list[int | float]]:
    """Return the observed-stage/direct-fallback duration, its source, and
    the direct values when they disagree.

    Stage values have precedence whenever at least one finite stage is present.
    Missing stages are not replaced with zero.  Direct aliases are considered as
    an allowlist: equal finite candidates collapse deterministically, while
    differing candidates leave the duration empty and are returned, so that
    the duration is reported as a disagreement instead of using first-wins.
    """
    stages = [
        _first_number(row, *aliases)
        for aliases in SLEEP_STAGE_ALIASES
    ]
    observed_stages = [value for value in stages if value is not None]
    if observed_stages:
        return sum(observed_stages), "stage_derived", []

    # The stage values are kept in ``values`` with the stage fields; a direct
    # value of another form is kept with the duration.
    direct_candidates = [
        (name, _number(row.get(name), values, "sleep_duration_minutes_ex_awake"))
        for name in SLEEP_DIRECT_DURATION_ALIASES
    ]
    finite_candidates = [
        (name, value) for name, value in direct_candidates if value is not None
    ]
    distinct_values = {value for _name, value in finite_candidates}
    if len(distinct_values) > 1:
        return None, "direct_aliases_disagree", [value for _name, value in finite_candidates]
    if finite_candidates:
        return finite_candidates[0][1], "direct_fallback", []
    return None, "null_fallback", []


def _timestamps(value: Any, timezone_name: str) -> tuple[str | None, str | None]:
    if value in (None, ""):
        return None, None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        utc_value = parsed.astimezone(timezone.utc)
        local_value = utc_value.astimezone(ZoneInfo(timezone_name))
    except TIME_OUT_OF_RANGE:
        return None, None
    return utc_value.isoformat(), local_value.isoformat()


def _sleep_score(row: dict[str, Any], values: ValueReader | None = None) -> int | float | None:
    scores = row.get("sleepScores")
    if isinstance(scores, dict):
        direct = _number(scores.get("overallScore"), values, "sleep_score")
        if direct is not None:
            return direct
        overall = scores.get("overall")
        if isinstance(overall, dict):
            nested = _number(overall.get("value"), values, "sleep_score")
            if nested is not None:
                return nested
    return _first_number(row, "overallScore", "sleepScore", values=values, field="sleep_score")


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
    total_seconds, _duration_source, _disagreeing = _sleep_duration_seconds(row)

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


SLEEP_DAILY_FIELDS = (
    "sleep_day",
    "sleep_start_local",
    "sleep_end_local",
    "sleep_window_minutes_including_awake",
    "sleep_duration_minutes_ex_awake",
    "sleep_stage_deep_minutes",
    "sleep_stage_light_minutes",
    "sleep_stage_rem_minutes",
    "sleep_score",
    "sleep_awake_minutes",
    "sleep_stage_available_flag",
    "sleep_score_available_flag",
    "sleep_normalization_status",
    "sleep_limitation_type",
    "sleep_reason_code",
    "sleep_source_available_for_analysis_flag",
)

# The source fields of each value field (stage A3d-1); the other fields are the
# sleep day and the states set from the values. A row left out that holds
# nothing in them is an empty record, such as a record with only its ``retro``
# flag. The end time also gives the sleep day, but it is a value as well.
SLEEP_VALUE_SOURCES = {
    "sleep_start_local": ("sleepStartTimestampGMT",),
    "sleep_end_local": ("sleepEndTimestampGMT",),
    "sleep_window_minutes_including_awake": (
        "sleepStartTimestampGMT",
        "sleepEndTimestampGMT",
    ),
    "sleep_duration_minutes_ex_awake": (
        *(name for aliases in SLEEP_STAGE_ALIASES for name in aliases),
        *SLEEP_DIRECT_DURATION_ALIASES,
    ),
    "sleep_stage_deep_minutes": ("deepSleepSeconds", "deep_sleep_seconds"),
    "sleep_stage_light_minutes": ("lightSleepSeconds", "light_sleep_seconds"),
    "sleep_stage_rem_minutes": ("remSleepSeconds", "rem_sleep_seconds"),
    "sleep_score": ("sleepScores", "overallScore", "sleepScore"),
    "sleep_awake_minutes": ("awakeSleepSeconds", "awake_sleep_seconds"),
}
SLEEP_FIELDS_WITHOUT_VALUES = (
    "sleep_day",
    "sleep_stage_available_flag",
    "sleep_score_available_flag",
    "sleep_normalization_status",
    "sleep_limitation_type",
    "sleep_reason_code",
    "sleep_source_available_for_analysis_flag",
)

_SLEEP_STAGE_FIELDS = (
    "sleep_stage_deep_minutes",
    "sleep_stage_light_minutes",
    "sleep_stage_rem_minutes",
)
_SLEEP_INTERVAL_FIELDS = (
    "sleep_start_local",
    "sleep_end_local",
    "sleep_window_minutes_including_awake",
)
# Set from the merged row, not compared: the flags say whether the merged row
# has the values, and the status describes its sleep interval.
_SLEEP_RECOMPUTED_FIELDS = frozenset(
    {
        "sleep_stage_available_flag",
        "sleep_score_available_flag",
        "sleep_normalization_status",
        "sleep_limitation_type",
        "sleep_reason_code",
        "sleep_source_available_for_analysis_flag",
    }
)


def _sleep_status(
    start_local: str | None,
    end_local: str | None,
    window_minutes: int | float | None,
) -> tuple[str, str, str, bool]:
    if start_local is None or end_local is None:
        return "needs_review", "missing_start_or_end", "missing_start_or_end_no_inference", False
    if window_minutes is None or window_minutes <= 0:
        return "needs_review", "invalid_sleep_window", "invalid_sleep_window_no_inference", False
    return "available", "none", "sleep_source_available", True


def _finalize_merged_sleep(row: dict[str, Any], disagreeing: list[str]) -> None:
    row["sleep_stage_available_flag"] = any(row[field] is not None for field in _SLEEP_STAGE_FIELDS)
    row["sleep_score_available_flag"] = row["sleep_score"] is not None
    if any(field in disagreeing for field in _SLEEP_INTERVAL_FIELDS):
        status = ("needs_review", "values_disagree", "sleep_interval_values_disagree_no_selection", False)
    else:
        status = _sleep_status(
            row["sleep_start_local"],
            row["sleep_end_local"],
            row["sleep_window_minutes_including_awake"],
        )
    (
        row["sleep_normalization_status"],
        row["sleep_limitation_type"],
        row["sleep_reason_code"],
        row["sleep_source_available_for_analysis_flag"],
    ) = status


def _sleep_alternatives(row: dict[str, Any]) -> dict[str, list[Any]]:
    disagreeing = row.get("_sleep_duration_alternatives") or []
    return {"sleep_duration_minutes_ex_awake": disagreeing} if disagreeing else {}


def _strip_sleep_internal_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in SLEEP_DAILY_FIELDS}


def _public_sleep_review_row(
    sleep_day: str, _rows: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "sleep_day": sleep_day,
        "sleep_start_local": None,
        "sleep_end_local": None,
        "sleep_window_minutes_including_awake": None,
        "sleep_duration_minutes_ex_awake": None,
        "sleep_stage_deep_minutes": None,
        "sleep_stage_light_minutes": None,
        "sleep_stage_rem_minutes": None,
        "sleep_score": None,
        "sleep_awake_minutes": None,
        "sleep_stage_available_flag": False,
        "sleep_score_available_flag": False,
        "sleep_normalization_status": "needs_review",
        "sleep_limitation_type": "duplicate_sleep_day",
        "sleep_reason_code": "duplicate_sleep_day_no_automatic_selection",
        "sleep_source_available_for_analysis_flag": False,
    }


def sleep_left_out_reason(raw: dict[str, Any], timezone_name: str = "UTC") -> str | None:
    """Return why a Sleep record is left out, or None when it is kept.

    A record is kept when it has a sleep day: its calendar date, or else the
    local date of its end time. Whether the end time can be read does not
    depend on the timezone.
    """
    if (
        daily_calendar_date(raw.get("calendarDate")) is None
        and _timestamps(raw.get("sleepEndTimestampGMT"), timezone_name)[1] is None
    ):
        return "missing_or_invalid_sleep_day"
    return None


def normalize_sleep_daily_assets(
    assets: Iterable[DiscoveredAsset],
    timezone_name: str = "Asia/Tokyo",
) -> DailyMetricResult:
    selected = [
        asset
        for asset in assets
        if asset.kind == "json" and logical_basename(asset).endswith("sleepdata.json")
    ]
    source_rows = [row for asset in selected for row in load_rows(asset)]
    accepted: list[dict[str, Any]] = []
    left_out = RowsLeftOut(value_source_names(SLEEP_VALUE_SOURCES))
    duration_source_counts: Counter[str] = Counter()
    for raw in source_rows:
        if left_out.add_mark(raw):
            continue
        _start_gmt, start_local = _timestamps(
            raw.get("sleepStartTimestampGMT"), timezone_name
        )
        _end_gmt, end_local = _timestamps(
            raw.get("sleepEndTimestampGMT"), timezone_name
        )
        sleep_day = daily_calendar_date(raw.get("calendarDate"))
        if sleep_day is None and end_local is not None:
            sleep_day = end_local[:10]
        reason = sleep_left_out_reason(raw, timezone_name)
        if reason is not None:
            left_out.add(raw, reason)
            continue
        window_minutes = None
        if start_local is not None and end_local is not None:
            window_minutes = (
                datetime.fromisoformat(end_local) - datetime.fromisoformat(start_local)
            ).total_seconds() / 60.0
        status, limitation, reason, available = _sleep_status(
            start_local, end_local, window_minutes
        )
        values = ValueReader()
        # A start or end time that is given but cannot be read, such as one
        # out of range, is a value of another form (stage A3d-2a).
        for name, local, field in (
            ("sleepStartTimestampGMT", start_local, "sleep_start_local"),
            ("sleepEndTimestampGMT", end_local, "sleep_end_local"),
        ):
            if local is None and not is_empty(raw.get(name)):
                values.problems.append((field, raw.get(name)))
        deep = _first_number(raw, "deepSleepSeconds", "deep_sleep_seconds", values=values, field="sleep_stage_deep_minutes")
        light = _first_number(raw, "lightSleepSeconds", "light_sleep_seconds", values=values, field="sleep_stage_light_minutes")
        rem = _first_number(raw, "remSleepSeconds", "rem_sleep_seconds", values=values, field="sleep_stage_rem_minutes")
        awake = _first_number(raw, "awakeSleepSeconds", "awake_sleep_seconds", values=values, field="sleep_awake_minutes")
        duration, duration_source, disagreeing = _sleep_duration_seconds(raw, values)
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        duration_source_counts[duration_source] += 1 + copies_within_snapshots(
            snapshot_numbers(raw)
        )
        score = _sleep_score(raw, values)
        accepted.append(
            {
                "_snapshot_numbers": snapshot_numbers(raw),
                "sleep_day": sleep_day,
                "sleep_start_local": start_local,
                "sleep_end_local": end_local,
                "sleep_window_minutes_including_awake": window_minutes,
                "sleep_duration_minutes_ex_awake": None if duration is None else duration / 60.0,
                "sleep_stage_deep_minutes": None if deep is None else deep / 60.0,
                "sleep_stage_light_minutes": None if light is None else light / 60.0,
                "sleep_stage_rem_minutes": None if rem is None else rem / 60.0,
                "sleep_score": score,
                "sleep_awake_minutes": None if awake is None else awake / 60.0,
                "sleep_stage_available_flag": any(value is not None for value in (deep, light, rem)),
                "sleep_score_available_flag": score is not None,
                "sleep_normalization_status": status,
                "sleep_limitation_type": limitation,
                "sleep_reason_code": reason,
                "sleep_source_available_for_analysis_flag": available,
                "_sleep_duration_source": duration_source,
                "_sleep_duration_alternatives": [value / 60.0 for value in disagreeing],
                "_value_problems": values.problems,
            }
        )
    result = finalize_daily(
        dataset="sleep_daily",
        key_fields=("sleep_day",),
        selected_assets=selected,
        source_record_count=len(source_rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=SLEEP_DAILY_FIELDS,
        review_on_any_duplicate=False,
        duplicate_review_factory=_public_sleep_review_row,
        strip_internal_fields=_strip_sleep_internal_fields,
        dedupe_exact_duplicates=True,
        recomputed_fields=_SLEEP_RECOMPUTED_FIELDS,
        finalize_merged=_finalize_merged_sleep,
        alternatives=_sleep_alternatives,
    )
    result.audit["sleep_duration_source_counts"] = dict(
        sorted(duration_source_counts.items())
    )
    result.audit["stage_derived_count"] = duration_source_counts["stage_derived"]
    result.audit["direct_fallback_count"] = duration_source_counts["direct_fallback"]
    result.audit["null_fallback_count"] = duration_source_counts["null_fallback"]
    result.audit["direct_aliases_disagree_count"] = duration_source_counts["direct_aliases_disagree"]
    return result


__all__ = [
    "SLEEP_DAILY_FIELDS",
    "SLEEP_DIRECT_DURATION_ALIASES",
    "SLEEP_FIELDS_WITHOUT_VALUES",
    "SLEEP_VALUE_SOURCES",
    "normalize_sleep",
    "normalize_sleep_daily_assets",
    "sleep_left_out_reason",
]
