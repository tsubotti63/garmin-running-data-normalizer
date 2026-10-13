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


ACUTE_TRAINING_LOAD_FIELDS = (
    "calendar_date",
    "observation_timestamp",
    "acwr_percent",
    "acwr_status",
    "daily_training_load_acute",
    "daily_training_load_chronic",
    "daily_acute_chronic_workload_ratio",
)
# The source field of each value field (stage A3d-1); the other fields are the
# record's key. A row left out that holds nothing in them is an empty record.
ACUTE_TRAINING_LOAD_VALUE_SOURCES = {
    "acwr_percent": ("acwrPercent",),
    "acwr_status": ("acwrStatus",),
    "daily_training_load_acute": ("dailyTrainingLoadAcute",),
    "daily_training_load_chronic": ("dailyTrainingLoadChronic",),
    "daily_acute_chronic_workload_ratio": ("dailyAcuteChronicWorkloadRatio",),
}
ACUTE_TRAINING_LOAD_FIELDS_WITHOUT_VALUES = ("calendar_date", "observation_timestamp")


def acute_training_load_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why an Acute Training Load record is left out, or None when it is kept."""
    if daily_calendar_date(raw.get("calendarDate")) is None:
        return "missing_or_invalid_calendar_date"
    if normalize_observation_timestamp(raw.get("timestamp"))[0] is None:
        return "missing_or_invalid_observation_timestamp"
    return None


def normalize_acute_training_load(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("metricsacutetrainingload")
    )
    accepted = []
    left_out = RowsLeftOut(value_source_names(ACUTE_TRAINING_LOAD_VALUE_SOURCES))
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        timestamp_semantics[semantics] += 1 + copies_within_snapshots(snapshot_numbers(raw))
        reason = acute_training_load_left_out_reason(raw)
        if reason is not None:
            left_out.add(raw, reason)
            continue
        values = ValueReader()
        accepted.append(
            {
                "_snapshot_numbers": snapshot_numbers(raw),
                "calendar_date": date,
                "observation_timestamp": timestamp,
                "acwr_percent": values.number(raw.get("acwrPercent"), "acwr_percent"),
                "acwr_status": values.text(raw.get("acwrStatus"), "acwr_status"),
                "daily_training_load_acute": values.number(raw.get("dailyTrainingLoadAcute"), "daily_training_load_acute"),
                "daily_training_load_chronic": values.number(raw.get("dailyTrainingLoadChronic"), "daily_training_load_chronic"),
                "daily_acute_chronic_workload_ratio": values.number(raw.get("dailyAcuteChronicWorkloadRatio"), "daily_acute_chronic_workload_ratio"),
                "_value_problems": values.problems,
            }
        )
    result = finalize_daily(
        dataset="acute_training_load_daily",
        key_fields=("calendar_date", "observation_timestamp"),
        selected_assets=selected,
        source_record_count=len(rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=ACUTE_TRAINING_LOAD_FIELDS,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    return result


__all__ = [
    "ACUTE_TRAINING_LOAD_FIELDS",
    "ACUTE_TRAINING_LOAD_FIELDS_WITHOUT_VALUES",
    "ACUTE_TRAINING_LOAD_VALUE_SOURCES",
    "acute_training_load_left_out_reason",
    "normalize_acute_training_load",
]
