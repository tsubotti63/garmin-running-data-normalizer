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
    selected_rows,
    snapshot_numbers,
    value_source_names,
)


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
# The source field of each value field (stage A3d-1); the other fields are the
# record's key. A row left out that holds nothing in them is an empty record.
TRAINING_READINESS_VALUE_SOURCES = {
    "training_readiness_score": ("score",),
    "training_readiness_level": ("level",),
    "training_readiness_recovery_time": ("recoveryTime",),
    "acwr_factor_percent": ("acwrFactorPercent",),
    "stress_history_factor_percent": ("stressHistoryFactorPercent",),
    "hrv_factor_percent": ("hrvFactorPercent",),
    "sleep_history_factor_percent": ("sleepHistoryFactorPercent",),
    "training_readiness_acute_load": ("acuteLoad",),
    "training_readiness_hrv_weekly_average": ("hrvWeeklyAverage",),
    "training_readiness_valid_sleep": ("validSleep",),
    "training_readiness_sleep_score": ("sleepScore",),
}
TRAINING_READINESS_FIELDS_WITHOUT_VALUES = ("calendar_date", "observation_timestamp")


def training_readiness_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why a Training Readiness record is left out, or None when it is kept."""
    if daily_calendar_date(raw.get("calendarDate")) is None:
        return "missing_or_invalid_calendar_date"
    if normalize_observation_timestamp(raw.get("timestamp"))[0] is None:
        return "missing_or_invalid_observation_timestamp"
    return None


def normalize_training_readiness(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("trainingreadinessdto")
    )
    accepted = []
    left_out = RowsLeftOut(value_source_names(TRAINING_READINESS_VALUE_SOURCES))
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        timestamp_semantics[semantics] += 1 + copies_within_snapshots(snapshot_numbers(raw))
        reason = training_readiness_left_out_reason(raw)
        if reason is not None:
            left_out.add(raw, reason)
            continue
        values = ValueReader()
        accepted.append(
            {
                "_snapshot_numbers": snapshot_numbers(raw),
                "calendar_date": date,
                "observation_timestamp": timestamp,
                "training_readiness_score": values.number(raw.get("score"), "training_readiness_score"),
                "training_readiness_level": values.text(raw.get("level"), "training_readiness_level"),
                "training_readiness_recovery_time": values.number(raw.get("recoveryTime"), "training_readiness_recovery_time"),
                "acwr_factor_percent": values.number(raw.get("acwrFactorPercent"), "acwr_factor_percent"),
                "stress_history_factor_percent": values.number(raw.get("stressHistoryFactorPercent"), "stress_history_factor_percent"),
                "hrv_factor_percent": values.number(raw.get("hrvFactorPercent"), "hrv_factor_percent"),
                "sleep_history_factor_percent": values.number(raw.get("sleepHistoryFactorPercent"), "sleep_history_factor_percent"),
                "training_readiness_acute_load": values.number(raw.get("acuteLoad"), "training_readiness_acute_load"),
                "training_readiness_hrv_weekly_average": values.number(raw.get("hrvWeeklyAverage"), "training_readiness_hrv_weekly_average"),
                "training_readiness_valid_sleep": values.boolean(raw.get("validSleep"), "training_readiness_valid_sleep"),
                "training_readiness_sleep_score": values.number(raw.get("sleepScore"), "training_readiness_sleep_score"),
                "_value_problems": values.problems,
            }
        )
    result = finalize_daily(
        dataset="training_readiness_daily",
        key_fields=("calendar_date", "observation_timestamp"),
        selected_assets=selected,
        source_record_count=len(rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=TRAINING_READINESS_FIELDS,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    return result


__all__ = [
    "TRAINING_READINESS_FIELDS",
    "TRAINING_READINESS_FIELDS_WITHOUT_VALUES",
    "TRAINING_READINESS_VALUE_SOURCES",
    "normalize_training_readiness",
    "training_readiness_left_out_reason",
]
