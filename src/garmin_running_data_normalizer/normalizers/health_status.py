from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset, load_json_assets

MAX_SAFE_INTEGER = (1 << 53) - 1
KNOWN_METRIC_TYPES = ("HRV", "HR", "SPO2", "SKIN_TEMP_C", "RESPIRATION")
METRIC_FIELDS = (
    "value",
    "status",
    "baseline_upper",
    "baseline_lower",
    "percentage",
    "feedback_key",
)


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("healthStatusData", "data", "records", "items", "values", "summaries"):
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
        return value if math.isfinite(value) and abs(value) <= MAX_SAFE_INTEGER else None
    try:
        parsed = float(str(value))
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(parsed) or abs(parsed) > MAX_SAFE_INTEGER:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _timestamp_utc(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (OverflowError, ValueError):
        return None


def _calendar_date(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and abs(value) > MAX_SAFE_INTEGER:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return daily_calendar_date(value)


def _metric_type(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text is not None else None


def _empty_wide_fields() -> dict[str, Any]:
    return {
        f"health_status_{metric_type.lower()}_{field}": None
        for metric_type in KNOWN_METRIC_TYPES
        for field in METRIC_FIELDS
    }


def _metric_record(
    metric: dict[str, Any],
    *,
    daily_key: str,
    metric_index: int,
    calendar_date: str | None,
    create_timestamp_utc: str | None,
    update_timestamp_utc: str | None,
    outliers_count: int | float | None,
    asset: DiscoveredAsset,
) -> dict[str, Any]:
    metric_type = _metric_type(metric.get("type"))
    value = _number(metric.get("value"))
    baseline_upper = _number(metric.get("baselineUpperLimit"))
    baseline_lower = _number(metric.get("baselineLowerLimit"))
    percentage = _number(metric.get("percentage"))
    status = "available"
    reason = "health_status_metric_available"
    if calendar_date is None:
        status = "needs_review"
        reason = "health_status_missing_calendar_date"
    elif metric_type is None:
        status = "needs_review"
        reason = "health_status_missing_metric_type"
    elif value is None and metric.get("value") not in (None, ""):
        status = "needs_review"
        reason = "health_status_metric_value_invalid"
    elif any(
        normalized is None and metric.get(source_name) not in (None, "")
        for source_name, normalized in (
            ("baselineUpperLimit", baseline_upper),
            ("baselineLowerLimit", baseline_lower),
            ("percentage", percentage),
        )
    ):
        status = "needs_review"
        reason = "health_status_metric_context_invalid"
    return {
        "health_status_metric_record_key": f"{daily_key}:metric:{metric_index}",
        "health_status_daily_record_key": daily_key,
        "calendar_date": calendar_date,
        "create_timestamp_utc": create_timestamp_utc,
        "update_timestamp_utc": update_timestamp_utc,
        "outliers_count": outliers_count,
        "metric_type": metric_type,
        "value": value,
        "baseline_upper_limit": baseline_upper,
        "baseline_lower_limit": baseline_lower,
        "status": _text(metric.get("status")),
        "percentage": percentage,
        "feedback_key": _text(metric.get("feedbackKey")),
        "metric_normalization_status": status,
        "metric_reason_code": reason,
        "daily_selection_status": "pending",
        "source_path": asset.provenance_path,
        "source_sha256": asset.sha256,
        "source_confidence": "high",
    }


def _normalize_source_record(
    row: dict[str, Any], asset: DiscoveredAsset, record_index: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    daily_key = f"health_status_daily:{asset.sha256[:24]}:{record_index}"
    calendar_date = _calendar_date(row.get("calendarDate") or row.get("date"))
    create_timestamp_utc = _timestamp_utc(row.get("createTimestampUTC"))
    update_timestamp_utc = _timestamp_utc(row.get("updateTimestampUTC"))
    outliers_count = _number(row.get("outliersCount"))
    raw_metrics = row.get("metrics")
    metrics = [item for item in raw_metrics if isinstance(item, dict)] if isinstance(raw_metrics, list) else []
    long_rows = [
        _metric_record(
            metric,
            daily_key=daily_key,
            metric_index=metric_index,
            calendar_date=calendar_date,
            create_timestamp_utc=create_timestamp_utc,
            update_timestamp_utc=update_timestamp_utc,
            outliers_count=outliers_count,
            asset=asset,
        )
        for metric_index, metric in enumerate(metrics)
    ]

    wide = {
        "health_status_daily_record_key": daily_key,
        "calendar_date": calendar_date,
        "create_timestamp_utc": create_timestamp_utc,
        "update_timestamp_utc": update_timestamp_utc,
        "outliers_count": outliers_count,
        "source_metric_count": len(metrics),
        "unknown_metric_count": sum(
            row["metric_type"] not in KNOWN_METRIC_TYPES for row in long_rows
        ),
        "daily_duplicate_count_before_dedupe": 1,
        "daily_dedupe_method": "not_needed_unique_calendar_date",
        "health_status_normalization_status": "available",
        "health_status_reason_code": "health_status_daily_available",
        "source_path": asset.provenance_path,
        "source_sha256": asset.sha256,
        "source_confidence": "high",
        **_empty_wide_fields(),
    }

    counts: dict[str, int] = {}
    for metric in long_rows:
        metric_type = metric["metric_type"]
        if metric_type is not None:
            counts[metric_type] = counts.get(metric_type, 0) + 1
    duplicate_known = {key for key, count in counts.items() if key in KNOWN_METRIC_TYPES and count > 1}
    for metric in long_rows:
        metric_type = metric["metric_type"]
        if metric_type not in KNOWN_METRIC_TYPES or metric_type in duplicate_known:
            continue
        prefix = f"health_status_{metric_type.lower()}"
        wide[f"{prefix}_value"] = metric["value"]
        wide[f"{prefix}_status"] = metric["status"]
        wide[f"{prefix}_baseline_upper"] = metric["baseline_upper_limit"]
        wide[f"{prefix}_baseline_lower"] = metric["baseline_lower_limit"]
        wide[f"{prefix}_percentage"] = metric["percentage"]
        wide[f"{prefix}_feedback_key"] = metric["feedback_key"]

    if calendar_date is None:
        wide["health_status_normalization_status"] = "needs_review"
        wide["health_status_reason_code"] = "health_status_missing_calendar_date"
    elif not metrics:
        wide["health_status_normalization_status"] = "needs_review"
        wide["health_status_reason_code"] = "health_status_no_metrics"
    elif duplicate_known:
        wide["health_status_normalization_status"] = "needs_review"
        wide["health_status_reason_code"] = "health_status_duplicate_metric_type"
    elif any(metric["metric_normalization_status"] == "needs_review" for metric in long_rows):
        wide["health_status_normalization_status"] = "needs_review"
        wide["health_status_reason_code"] = "health_status_metric_requires_review"
    return wide, long_rows


def _selection_sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("update_timestamp_utc") or ""),
        str(row.get("create_timestamp_utc") or ""),
        str(row["health_status_daily_record_key"]),
    )


def normalize_health_status(root: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Normalize healthStatusData to complete long and fixed daily schemas."""
    candidates: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, filename_suffix="healthStatusData.json"):
        for record_index, row in enumerate(_records(payload)):
            daily, long_rows = _normalize_source_record(row, asset, record_index)
            candidates.append(daily)
            metrics.extend(long_rows)

    grouped: dict[str, list[dict[str, Any]]] = {}
    missing_date: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate["calendar_date"] is None:
            missing_date.append(candidate)
        else:
            grouped.setdefault(str(candidate["calendar_date"]), []).append(candidate)

    selected: list[dict[str, Any]] = []
    selection_by_key: dict[str, str] = {}
    for rows in grouped.values():
        winner = max(rows, key=_selection_sort_key)
        winner["daily_duplicate_count_before_dedupe"] = len(rows)
        if len(rows) > 1:
            winner["daily_dedupe_method"] = "latest_update_then_create_then_stable_key"
            if winner["health_status_normalization_status"] == "available":
                winner["health_status_normalization_status"] = "available_with_explicit_dedupe"
                winner["health_status_reason_code"] = "health_status_duplicate_calendar_date_resolved"
        selected.append(winner)
        for row in rows:
            selection_by_key[row["health_status_daily_record_key"]] = (
                "selected_for_daily" if row is winner else "superseded_for_daily"
            )
    for row in missing_date:
        selected.append(row)
        selection_by_key[row["health_status_daily_record_key"]] = "missing_date_hold"
    for metric in metrics:
        metric["daily_selection_status"] = selection_by_key.get(
            metric["health_status_daily_record_key"], "not_selected"
        )

    return {
        "daily": sorted(
            selected,
            key=lambda row: (str(row.get("calendar_date")), row["health_status_daily_record_key"]),
        ),
        "metrics": sorted(metrics, key=lambda row: row["health_status_metric_record_key"]),
    }
