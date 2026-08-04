from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, load_rows, number, selected_rows, text


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


def normalize_vo2max(assets: Iterable[DiscoveredAsset]) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets,
        lambda name: name.startswith(("activityvo2max", "metricsmaxmetdata", "snapshot_vo2max")),
    )
    accepted = []
    excluded: Counter[str] = Counter()
    timestamp_semantics: Counter[str] = Counter()
    for asset in selected:
        name = (asset.member_path or asset.source_path).split("/")[-1].lower()
        for raw in load_rows(asset):
            series = text(raw.get("vo2MaxSourceSeries"))
            if series is None:
                series = (
                    "performance_metrics_daily"
                    if name.startswith("metricsmaxmetdata")
                    else "activity_vo2max_daily"
                )
            date = daily_calendar_date(raw.get("calendarDate"))
            value = number(raw.get("vo2MaxValue"))
            timestamp_source = (
                raw.get("timestampGmt")
                if series == "activity_vo2max_daily"
                else raw.get("updateTimestamp")
            )
            if timestamp_source in (None, ""):
                timestamp_source = raw.get("observationTimestamp")
            timestamp, semantics = normalize_observation_timestamp(
                timestamp_source,
                naive_timezone_semantics=(
                    "UTC_SOURCE_FIELD"
                    if series == "activity_vo2max_daily" and raw.get("timestampGmt") not in (None, "")
                    else "UNCONFIRMED"
                ),
            )
            timestamp_semantics[semantics] += 1
            sport = text(raw.get("sport"))
            source_activity_id = number(raw.get("activityId"))
            if not isinstance(source_activity_id, int):
                source_activity_id = None
            if date is None:
                excluded["missing_or_invalid_calendar_date"] += 1
                continue
            if timestamp is None:
                excluded["missing_or_invalid_observation_timestamp"] += 1
                continue
            if value is None:
                excluded["missing_or_invalid_vo2max"] += 1
                continue
            if sport is None:
                excluded["missing_sport_for_stable_key"] += 1
                continue
            accepted.append(
                {
                    "calendar_date": date,
                    "observation_timestamp": timestamp,
                    "vo2max": value,
                    "vo2max_source_series": series,
                    "sport": sport,
                    "source_activity_id": source_activity_id,
                    "source_confidence": None,
                    "max_met": number(raw.get("maxMet")),
                    "max_met_category": text(raw.get("maxMetCategory")),
                    "calibrated_data": number(raw.get("calibratedData")),
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
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    result.audit["source_activity_id_role"] = "supplemental_provenance_not_stable_key"
    return result


__all__ = ["VO2MAX_FIELDS", "normalize_vo2max"]
