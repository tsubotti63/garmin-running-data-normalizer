from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, boolean, finalize_daily, number, selected_rows, text


TRAINING_READINESS_FIELDS = (
    "calendar_date",
    "observation_timestamp",
    "training_readiness_score",
    "training_readiness_level",
    "training_readiness_recovery_time",
    "acwr_factor_percent",
    "stress_history_factor_percent",
    "hrv_factor_percent",
    "sleep_history_factor_percent",
    "training_readiness_acute_load",
    "training_readiness_hrv_weekly_average",
    "training_readiness_valid_sleep",
    "training_readiness_sleep_score",
)


def normalize_training_readiness(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("trainingreadinessdto")
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
                "training_readiness_score": number(raw.get("score")),
                "training_readiness_level": text(raw.get("level")),
                "training_readiness_recovery_time": number(raw.get("recoveryTime")),
                "acwr_factor_percent": number(raw.get("acwrFactorPercent")),
                "stress_history_factor_percent": number(raw.get("stressHistoryFactorPercent")),
                "hrv_factor_percent": number(raw.get("hrvFactorPercent")),
                "sleep_history_factor_percent": number(raw.get("sleepHistoryFactorPercent")),
                "training_readiness_acute_load": number(raw.get("acuteLoad")),
                "training_readiness_hrv_weekly_average": number(raw.get("hrvWeeklyAverage")),
                "training_readiness_valid_sleep": boolean(raw.get("validSleep")),
                "training_readiness_sleep_score": number(raw.get("sleepScore")),
            }
        )
    result = finalize_daily(
        dataset="training_readiness_daily",
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


__all__ = ["TRAINING_READINESS_FIELDS", "normalize_training_readiness"]
