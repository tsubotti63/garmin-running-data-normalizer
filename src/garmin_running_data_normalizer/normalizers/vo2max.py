from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, load_rows, number, selected_rows, text


VO2MAX_FIELDS = (
    "calendar_date",
    "vo2max",
    "vo2max_source_series",
    "sport",
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
            if date is None:
                excluded["missing_or_invalid_calendar_date"] += 1
                continue
            if value is None:
                excluded["missing_or_invalid_vo2max"] += 1
                continue
            accepted.append(
                {
                    "calendar_date": date,
                    "vo2max": value,
                    "vo2max_source_series": series,
                    "sport": text(raw.get("sport")),
                    "source_confidence": None,
                    "max_met": number(raw.get("maxMet")),
                    "max_met_category": text(raw.get("maxMetCategory")),
                    "calibrated_data": number(raw.get("calibratedData")),
                }
            )
    return finalize_daily(
        dataset="vo2max_daily",
        key_field="calendar_date",
        selected_assets=selected,
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
    )


__all__ = ["VO2MAX_FIELDS", "normalize_vo2max"]
