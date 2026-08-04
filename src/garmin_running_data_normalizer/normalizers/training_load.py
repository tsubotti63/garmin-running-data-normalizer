from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, number, selected_rows, text


ACUTE_TRAINING_LOAD_FIELDS = (
    "calendar_date",
    "acwr_percent",
    "acwr_status",
    "daily_training_load_acute",
    "daily_training_load_chronic",
    "daily_acute_chronic_workload_ratio",
)


def normalize_acute_training_load(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("metricsacutetrainingload")
    )
    accepted = []
    excluded: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
            continue
        accepted.append(
            {
                "calendar_date": date,
                "acwr_percent": number(raw.get("acwrPercent")),
                "acwr_status": text(raw.get("acwrStatus")),
                "daily_training_load_acute": number(raw.get("dailyTrainingLoadAcute")),
                "daily_training_load_chronic": number(raw.get("dailyTrainingLoadChronic")),
                "daily_acute_chronic_workload_ratio": number(raw.get("dailyAcuteChronicWorkloadRatio")),
            }
        )
    return finalize_daily(
        dataset="acute_training_load_daily",
        key_field="calendar_date",
        selected_assets=selected,
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
    )


__all__ = ["ACUTE_TRAINING_LOAD_FIELDS", "normalize_acute_training_load"]
