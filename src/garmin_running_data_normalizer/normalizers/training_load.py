from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, number, selected_rows, text


ACUTE_TRAINING_LOAD_FIELDS = (
    "calendar_date",
    "observation_timestamp",
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
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        timestamp_semantics[semantics] += 1
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
            continue
        if timestamp is None:
            excluded["missing_or_invalid_observation_timestamp"] += 1
            continue
        accepted.append(
            {
                "calendar_date": date,
                "observation_timestamp": timestamp,
                "acwr_percent": number(raw.get("acwrPercent")),
                "acwr_status": text(raw.get("acwrStatus")),
                "daily_training_load_acute": number(raw.get("dailyTrainingLoadAcute")),
                "daily_training_load_chronic": number(raw.get("dailyTrainingLoadChronic")),
                "daily_acute_chronic_workload_ratio": number(raw.get("dailyAcuteChronicWorkloadRatio")),
            }
        )
    result = finalize_daily(
        dataset="acute_training_load_daily",
        key_fields=("calendar_date", "observation_timestamp"),
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
    return result


__all__ = ["ACUTE_TRAINING_LOAD_FIELDS", "normalize_acute_training_load"]
