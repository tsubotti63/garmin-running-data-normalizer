from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..common.time import daily_calendar_date
from ..fit.hrv import parse_fit_hrv_export
from ..intake.discovery import DiscoveredAsset, load_json_assets

MAX_SAFE_INTEGER = (1 << 53) - 1


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
        return value if math.isfinite(value) else None
    try:
        parsed = float(str(value))
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed) if parsed.is_integer() else parsed


def _json_hrv_record(
    row: dict[str, Any], asset: DiscoveredAsset, record_index: int
) -> dict[str, Any]:
    hrv_metrics = [
        metric
        for metric in row.get("metrics", []) or []
        if isinstance(metric, dict) and str(metric.get("type") or "").lower() == "hrv"
    ]
    metric = hrv_metrics[-1] if hrv_metrics else {}
    date = daily_calendar_date(row.get("calendarDate") or row.get("date"))
    value = _number(metric.get("value"))
    status = "reference_available"
    reason = "health_status_hrv_reference_available"
    if date is None:
        status = "needs_review"
        reason = "health_status_hrv_missing_calendar_date"
    elif not hrv_metrics:
        status = "reference_missing"
        reason = "health_status_hrv_metric_not_present"
    elif value is None:
        status = "needs_review"
        reason = "health_status_hrv_value_invalid_or_missing"
    return {
        "health_status_hrv_record_key": f"health_status_hrv:{asset.sha256[:24]}:{record_index}",
        "date": date,
        "health_status_hrv_value": value,
        "health_status_hrv_baseline_lower": _number(metric.get("baselineLowerLimit")),
        "health_status_hrv_baseline_upper": _number(metric.get("baselineUpperLimit")),
        "health_status_hrv_status": metric.get("status"),
        "health_status_hrv_percentage": _number(metric.get("percentage")),
        "health_status_hrv_feedback_key": metric.get("feedbackKey"),
        "reference_status": status,
        "reference_reason_code": reason,
        "semantics_note": "health-status scoped HRV; not proven equivalent to nightly FIT HRV",
        "source_path": asset.provenance_path,
        "source_sha256": asset.sha256,
    }


def _load_json_hrv(root: str | Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, filename_suffix="healthStatusData.json"):
        for index, row in enumerate(_records(payload)):
            output.append(_json_hrv_record(row, asset, index))
    counts: dict[str, int] = {}
    for record in output:
        if record["date"] is not None:
            counts[str(record["date"])] = counts.get(str(record["date"]), 0) + 1
    for record in output:
        if record["date"] is not None and counts[str(record["date"])] > 1:
            record["reference_status"] = "needs_review"
            record["reference_reason_code"] = "health_status_hrv_duplicate_calendar_date"
    return sorted(output, key=lambda row: row["health_status_hrv_record_key"])


def _consistency(
    fit_daily: list[dict[str, Any]], json_reference: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    fit_by_date = {str(row["date"]): row for row in fit_daily if row.get("date") is not None}
    json_by_date: dict[str, list[dict[str, Any]]] = {}
    for row in json_reference:
        if row.get("date") is not None:
            json_by_date.setdefault(str(row["date"]), []).append(row)
    output: list[dict[str, Any]] = []
    for date in sorted(set(fit_by_date) | set(json_by_date)):
        fit = fit_by_date.get(date)
        references = json_by_date.get(date, [])
        fit_value = fit.get("fit_hrv_value") if fit else None
        json_value = references[0].get("health_status_hrv_value") if len(references) == 1 else None
        if len(references) > 1:
            status = "needs_review_duplicate_health_status_date"
        elif fit is None:
            status = "health_status_only"
        elif not references:
            status = "fit_only"
        elif fit_value is None or json_value is None:
            status = "needs_review_missing_value"
        elif math.isclose(float(fit_value), float(json_value), rel_tol=0.0, abs_tol=1e-9):
            status = "same_date_value_match"
        else:
            status = "same_date_value_difference"
        output.append(
            {
                "date": date,
                "fit_hrv_value": fit_value,
                "health_status_hrv_value": json_value,
                "consistency_status": status,
                "comparison_semantics": "same-date validation evidence only; measurement equivalence is not asserted",
            }
        )
    return output


def normalize_hrv(root: str | Path, timezone_name: str = "Asia/Tokyo") -> dict[str, Any]:
    """Normalize FIT HRV and compare health-status JSON without merging sources."""
    fit_daily, fit_audit = parse_fit_hrv_export(root, timezone_name=timezone_name)
    json_reference = _load_json_hrv(root)
    return {
        "fit_daily": fit_daily,
        "health_status_json_reference": json_reference,
        "fit_json_consistency": _consistency(fit_daily, json_reference),
        "fit_audit": fit_audit,
    }
