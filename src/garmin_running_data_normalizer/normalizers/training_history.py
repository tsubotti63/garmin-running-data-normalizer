from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, selected_rows, text


TRAINING_HISTORY_FIELDS = ("calendar_date", "training_status")


def normalize_training_history(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("traininghistory")
    )
    accepted = []
    excluded: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        status = text(raw.get("trainingStatus"))
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
        elif status is None:
            excluded["missing_training_status"] += 1
        else:
            accepted.append({"calendar_date": date, "training_status": status})
    return finalize_daily(
        dataset="training_history_daily",
        key_field="calendar_date",
        selected_assets=selected,
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
    )


__all__ = ["TRAINING_HISTORY_FIELDS", "normalize_training_history"]
