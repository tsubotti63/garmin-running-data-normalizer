from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import (
    DailyMetricResult,
    RowsLeftOut,
    copies_within_snapshots,
    finalize_daily,
    selected_rows,
    snapshot_numbers,
    text,
    value_source_names,
)


TRAINING_HISTORY_FIELDS = (
    "calendar_date",
    "observation_timestamp",
    "training_status",
    "sport",
)
# The source field of each value field (stage A3d-1); the other fields are the
# record's key. A row left out that holds nothing in them is an empty record.
TRAINING_HISTORY_VALUE_SOURCES = {
    "training_status": ("trainingStatus",),
    "sport": ("sport",),
}
TRAINING_HISTORY_FIELDS_WITHOUT_VALUES = ("calendar_date", "observation_timestamp")


def training_history_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why a Training History record is left out, or None when it is kept."""
    if daily_calendar_date(raw.get("calendarDate")) is None:
        return "missing_or_invalid_calendar_date"
    if normalize_observation_timestamp(raw.get("timestamp"))[0] is None:
        return "missing_or_invalid_observation_timestamp"
    if text(raw.get("trainingStatus")) is None:
        return "missing_training_status"
    return None


def normalize_training_history(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("traininghistory")
    )
    accepted = []
    left_out = RowsLeftOut(value_source_names(TRAINING_HISTORY_VALUE_SOURCES))
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        timestamp_semantics[semantics] += 1 + copies_within_snapshots(snapshot_numbers(raw))
        reason = training_history_left_out_reason(raw)
        if reason is not None:
            left_out.add(raw, reason)
            continue
        accepted.append(
            {
                "_snapshot_numbers": snapshot_numbers(raw),
                "calendar_date": date,
                "observation_timestamp": timestamp,
                "training_status": text(raw.get("trainingStatus")),
                "sport": text(raw.get("sport")),
            }
        )
    result = finalize_daily(
        dataset="training_history_daily",
        key_fields=("calendar_date", "observation_timestamp"),
        selected_assets=selected,
        source_record_count=len(rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=TRAINING_HISTORY_FIELDS,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    return result


__all__ = [
    "TRAINING_HISTORY_FIELDS",
    "TRAINING_HISTORY_FIELDS_WITHOUT_VALUES",
    "TRAINING_HISTORY_VALUE_SOURCES",
    "normalize_training_history",
    "training_history_left_out_reason",
]
