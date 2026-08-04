from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, selected_rows, text


TRAINING_HISTORY_FIELDS = (
    "calendar_date",
    "observation_timestamp",
    "training_status",
    "sport",
)


def normalize_training_history(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("traininghistory")
    )
    accepted = []
    excluded: Counter[str] = Counter()
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        timestamp_semantics[semantics] += 1
        status = text(raw.get("trainingStatus"))
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
        elif timestamp is None:
            excluded["missing_or_invalid_observation_timestamp"] += 1
        elif status is None:
            excluded["missing_training_status"] += 1
        else:
            accepted.append(
                {
                    "calendar_date": date,
                    "observation_timestamp": timestamp,
                    "training_status": status,
                    "sport": text(raw.get("sport")),
                }
            )
    result = finalize_daily(
        dataset="training_history_daily",
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


__all__ = ["TRAINING_HISTORY_FIELDS", "normalize_training_history"]
