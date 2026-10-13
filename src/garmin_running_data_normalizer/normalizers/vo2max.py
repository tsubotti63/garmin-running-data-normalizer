from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..common.values import ValueReader
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import (
    DailyMetricResult,
    RowsLeftOut,
    copies_within_snapshots,
    finalize_daily,
    load_rows,
    number,
    selected_rows,
    snapshot_numbers,
    text,
    value_source_names,
)


VO2MAX_FIELDS = (
    "calendar_date",
    "observation_timestamp",
    "vo2max",
    "vo2max_source_series",
    "sport",
    "source_activity_id",
    "source_confidence",
    "max_met",
    "max_met_category",
    "calibrated_data",
)
# The source field of each value field (stage A3d-1). The other fields are the
# record's key, the Activity that it came from, and a confidence that is always
# empty. A row left out that holds nothing in them is an empty record.
VO2MAX_VALUE_SOURCES = {
    "vo2max": ("vo2MaxValue",),
    "max_met": ("maxMet",),
    "max_met_category": ("maxMetCategory",),
    "calibrated_data": ("calibratedData",),
}
VO2MAX_FIELDS_WITHOUT_VALUES = (
    "calendar_date",
    "observation_timestamp",
    "vo2max_source_series",
    "sport",
    "source_activity_id",
    "source_confidence",
)


def vo2max_series(raw: dict[str, Any], file_name: str) -> str:
    """Return the series of a VO2max record: its own, or that of its file."""
    series = text(raw.get("vo2MaxSourceSeries"))
    if series is None:
        series = (
            "performance_metrics_daily"
            if file_name.startswith("metricsmaxmetdata")
            else "activity_vo2max_daily"
        )
    return series


def _observation_timestamp(raw: dict[str, Any], series: str) -> tuple[str | None, str]:
    timestamp_source = (
        raw.get("timestampGmt")
        if series == "activity_vo2max_daily"
        else raw.get("updateTimestamp")
    )
    if timestamp_source in (None, ""):
        timestamp_source = raw.get("observationTimestamp")
    return normalize_observation_timestamp(
        timestamp_source,
        naive_timezone_semantics=(
            "UTC_SOURCE_FIELD"
            if series == "activity_vo2max_daily" and raw.get("timestampGmt") not in (None, "")
            else "UNCONFIRMED"
        ),
    )


def vo2max_left_out_reason(raw: dict[str, Any], file_name: str) -> str | None:
    """Return why a VO2max record is left out, or None when it is kept.

    ``file_name`` is the lower-case name of the record's file, which gives
    the series of a record without its own.
    """
    if daily_calendar_date(raw.get("calendarDate")) is None:
        return "missing_or_invalid_calendar_date"
    if _observation_timestamp(raw, vo2max_series(raw, file_name))[0] is None:
        return "missing_or_invalid_observation_timestamp"
    if number(raw.get("vo2MaxValue")) is None:
        return "missing_or_invalid_vo2max"
    if text(raw.get("sport")) is None:
        return "missing_sport_for_stable_key"
    return None


def normalize_vo2max(assets: Iterable[DiscoveredAsset]) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets,
        lambda name: name.startswith(("activityvo2max", "metricsmaxmetdata", "snapshot_vo2max")),
    )
    accepted = []
    left_out = RowsLeftOut(value_source_names(VO2MAX_VALUE_SOURCES))
    timestamp_semantics: Counter[str] = Counter()
    for asset in selected:
        name = (asset.member_path or asset.source_path).split("/")[-1].lower()
        for raw in load_rows(asset):
            series = vo2max_series(raw, name)
            date = daily_calendar_date(raw.get("calendarDate"))
            value = number(raw.get("vo2MaxValue"))
            timestamp, semantics = _observation_timestamp(raw, series)
            # Copies within one Snapshot count as in a one-shot run (stage A3b).
            timestamp_semantics[semantics] += 1 + copies_within_snapshots(snapshot_numbers(raw))
            sport = text(raw.get("sport"))
            reason = vo2max_left_out_reason(raw, name)
            if reason is not None:
                left_out.add(raw, reason)
                continue
            values = ValueReader()
            source_activity_id = values.integer(raw.get("activityId"), "source_activity_id")
            accepted.append(
                {
                    "_snapshot_numbers": snapshot_numbers(raw),
                    "calendar_date": date,
                    "observation_timestamp": timestamp,
                    "vo2max": value,
                    "vo2max_source_series": series,
                    "sport": sport,
                    "source_activity_id": source_activity_id,
                    "source_confidence": None,
                    "max_met": values.number(raw.get("maxMet"), "max_met"),
                    "max_met_category": values.text(raw.get("maxMetCategory"), "max_met_category"),
                    "calibrated_data": values.number(raw.get("calibratedData"), "calibrated_data"),
                    "_value_problems": values.problems,
                }
            )
    result = finalize_daily(
        dataset="vo2max_daily",
        key_fields=(
            "calendar_date",
            "vo2max_source_series",
            "sport",
            "observation_timestamp",
        ),
        selected_assets=selected,
        source_record_count=len(rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=VO2MAX_FIELDS,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    result.audit["source_activity_id_role"] = "supplemental_provenance_not_stable_key"
    return result


__all__ = [
    "VO2MAX_FIELDS",
    "VO2MAX_FIELDS_WITHOUT_VALUES",
    "VO2MAX_VALUE_SOURCES",
    "normalize_vo2max",
    "vo2max_left_out_reason",
    "vo2max_series",
]
