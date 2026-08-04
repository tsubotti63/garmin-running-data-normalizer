from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, number, selected_rows


RACE_PREDICTION_FIELDS = (
    "calendar_date",
    "race_time_5k_sec",
    "race_time_10k_sec",
    "race_time_half_sec",
    "race_time_marathon_sec",
)


def normalize_race_prediction(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("runracepredictions")
    )
    accepted = []
    excluded: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        values = {
            "race_time_5k_sec": number(raw.get("raceTime5K")),
            "race_time_10k_sec": number(raw.get("raceTime10K")),
            "race_time_half_sec": number(raw.get("raceTimeHalf")),
            "race_time_marathon_sec": number(raw.get("raceTimeMarathon")),
        }
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
        elif any(value is None or value <= 0 for value in values.values()):
            excluded["missing_or_invalid_race_prediction"] += 1
        else:
            accepted.append({"calendar_date": date, **values})
    return finalize_daily(
        dataset="race_prediction_daily",
        key_field="calendar_date",
        selected_assets=selected,
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
    )


__all__ = ["RACE_PREDICTION_FIELDS", "normalize_race_prediction"]
