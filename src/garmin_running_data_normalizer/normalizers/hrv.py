from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..common.time import daily_calendar_date
from ..common.values import ABSENT, INVALID, VALID, read_value
from ..fit.hrv import (
    FIT_HRV_DIVISOR,
    FIT_HRV_INVALID_RAW_VALUE,
    FIT_TIMESTAMP_INVALID_RAW_VALUE,
    _fit_datetime,
    parse_fit_hrv_export,
    read_fit_hrv_messages,
)
from ..intake.discovery import DiscoveredAsset, load_json_assets
from .daily_metrics import copies_within_snapshots

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


# Why an HRV reading is left out, named as the daily datasets name theirs
# (stage A3d-2b).
READING_TIMESTAMP_LEFT_OUT = "missing_or_invalid_reading_timestamp"
READING_VALUE_LEFT_OUT = "missing_or_invalid_hrv_value"


def _reading_value(raw: Any) -> tuple[str, float | None]:
    """Read the value of an HRV reading as an integer field takes it.

    A whole number, also one written with a decimal point, gives the value in
    milliseconds. FIT's invalid value 65535, which marks that nothing was
    measured, and a missing field give no value; any other value is of
    another form (stage A3d-2b).
    """
    state, value = read_value(raw, "integer")
    if state == ABSENT or (state == VALID and value == FIT_HRV_INVALID_RAW_VALUE):
        return ABSENT, None
    if state == INVALID:
        return INVALID, None
    return VALID, value / FIT_HRV_DIVISOR


def _reading_date(raw: Any, timezone_name: str) -> str | None:
    """Return the local date of an HRV reading's time, or None when the time
    is missing, FIT's invalid value, of another form, or out of range."""
    state, seconds = read_value(raw, "integer")
    if state != VALID or seconds == FIT_TIMESTAMP_INVALID_RAW_VALUE:
        return None
    local = _fit_datetime(seconds, timezone_name)
    return local[:10] if local else None


HRV_DAILY_FIELDS = (
    "calendar_date",
    "hrv_value",
    "semantics_status",
    "analysis_role",
    "record_count_for_date",
    "source_file_count_for_date",
    "dedupe_status",
)


def normalize_hrv_daily_assets(
    assets: list[DiscoveredAsset],
    timezone_name: str = "Asia/Tokyo",
    *,
    snapshot_numbers: Mapping[str, list[int]] | None = None,
) -> dict[str, Any]:
    """Normalize FIT-derived HRV by date; values that disagree are left empty.

    Each FIT reading (message 370) is an observation of its local date. A
    reading without a date is left out as a daily row without one is (stage
    A3d-1): one that holds a value is counted by reason, and one that holds
    none is an empty record. A reading whose value is of another form is left
    out too, because the value is what the reading is for, as a VO2max row
    without its value is. A reading without a value, such as one with FIT's
    invalid value, which marks that nothing was measured, is counted in
    ``absent_value_counts`` and not announced; a date has a row only when one
    of its readings has a value (stage A3d-2b).

    ``snapshot_numbers``, in a Snapshot run, maps the SHA-256 digest of each FIT
    file to the import numbers of the Snapshots that contained it. The audit
    record then counts each Snapshot occurrence and names the Snapshots that
    gave each value. A file's copies within one Snapshot count as files, as
    a one-shot run of that Export counts them (stage A3b).
    """
    fit_assets = [asset for asset in assets if asset.kind == "fit"]

    def copies(asset: DiscoveredAsset) -> int:
        return 1 + copies_within_snapshots((snapshot_numbers or {}).get(asset.sha256))

    by_date: dict[str, list[tuple[int | float, str]]] = defaultdict(list)
    parse_status_counts: Counter[str] = Counter()
    left_out: Counter[str] = Counter()
    empty_record_count = 0
    absent_value_count = 0
    source_record_count = 0
    for asset in fit_assets:
        status, readings, _unknown_records = read_fit_hrv_messages(asset.data)
        weight = copies(asset)
        parse_status_counts[
            status or ("parsed_fit_hrv" if readings else "no_fit_hrv_records")
        ] += weight
        for raw_value, raw_time in readings:
            source_record_count += weight
            state, value = _reading_value(raw_value)
            date = _reading_date(raw_time, timezone_name)
            if date is None:
                if state == ABSENT:
                    empty_record_count += weight
                else:
                    left_out[READING_TIMESTAMP_LEFT_OUT] += weight
            elif state == INVALID:
                left_out[READING_VALUE_LEFT_OUT] += weight
            elif state == ABSENT:
                absent_value_count += weight
            else:
                by_date[date].extend([(value, asset.sha256)] * weight)

    records: list[dict[str, Any]] = []
    disagreement_key_count = 0
    duplicate_count = 0
    disagreements: list[dict[str, Any]] = []
    for date in sorted(by_date):
        observations = by_date[date]
        value_counts = Counter(value for value, _source in observations)
        duplicate_count += len(observations) - len(value_counts)
        conflict = len(value_counts) > 1
        if conflict:
            # Every value is kept in the audit; the day's value is left empty.
            disagreement_key_count += 1
            weighted: dict[int | float, list[Any]] = {}
            # In a Snapshot run, each file counts once for each Snapshot
            # occurrence, its copies included.
            for value, source in (
                observations
                if snapshot_numbers is None
                else list(dict.fromkeys(observations))
            ):
                numbers = (snapshot_numbers or {}).get(source) or []
                entry = weighted.setdefault(value, [0, set()])
                entry[0] += len(numbers) or 1
                entry[1].update(numbers)
            disagreements.append(
                {
                    "key": {"calendar_date": date},
                    "observation_count": sum(count for count, _numbers in weighted.values()),
                    "fields": [
                        {
                            "field": "hrv_value",
                            "values": [
                                {
                                    "value": value,
                                    "observation_count": count,
                                    **(
                                        {"snapshots": sorted(numbers)}
                                        if snapshot_numbers is not None
                                        else {}
                                    ),
                                }
                                for value, (count, numbers) in sorted(weighted.items())
                            ],
                        }
                    ],
                }
            )
        records.append(
            {
                "calendar_date": date,
                "hrv_value": None if conflict else next(iter(value_counts)),
                "semantics_status": "semantics_approved_analysis_reference",
                "analysis_role": "analysis_reference_only",
                "record_count_for_date": len(observations),
                "source_file_count_for_date": len({source for _value, source in observations}),
                "dedupe_status": (
                    "same_day_values_disagree"
                    if conflict
                    else "same_date_same_value_deduped"
                    if len(observations) > 1
                    else "single_observation"
                ),
                "disagreeing_fields": ["hrv_value"] if conflict else [],
            }
        )
    # Values that disagree are reported as disagreements; readings left out
    # and readings without a value are counted (stage A3d-2b).
    return {
        "records": records,
        "audit": {
            "format": "garmin-running-data-normalizer-hrv-daily-audit-v2",
            "dataset": "hrv_daily",
            "status": "PASS",
            "detected_asset_count": sum(copies(asset) for asset in fit_assets),
            "source_record_count": source_record_count,
            "accepted_record_count": len(records),
            "excluded_record_count": sum(left_out.values()),
            "excluded_reason_counts": dict(sorted(left_out.items())),
            # Readings left out that hold no value: counted apart, and not
            # announced.
            **({"empty_record_count": empty_record_count} if empty_record_count else {}),
            "same_value_duplicate_count": duplicate_count,
            "disagreement_key_count": disagreement_key_count,
            "disagreements": disagreements,
            "absent_value_counts": (
                {"hrv_value": absent_value_count} if absent_value_count else {}
            ),
            "parse_status_counts": dict(sorted(parse_status_counts.items())),
            "source_definition": "non-running FIT message 370 field 1 raw divided by 128",
            "date_basis": "fit_end_jst_date_from_message_370_field_253_timestamp",
            "analysis_role": "analysis_reference_only",
            "source_of_truth": False,
            "daily_coach_use": False,
            "latest_wins": False,
            "source_paths_exposed": False,
            "source_hashes_exposed": False,
        },
    }


__all__ = ["HRV_DAILY_FIELDS", "normalize_hrv", "normalize_hrv_daily_assets"]
