from __future__ import annotations

from collections import Counter
from typing import Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import (
    DailyMetricResult,
    copies_within_snapshots,
    finalize_daily,
    number,
    selected_rows,
    snapshot_numbers,
)


RACE_PREDICTION_FIELDS = (
    "calendar_date",
    "observation_timestamp",
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
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate"))
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        timestamp_semantics[semantics] += 1 + copies_within_snapshots(snapshot_numbers(raw))
        values = {
            "race_time_5k_sec": number(raw.get("raceTime5K")),
            "race_time_10k_sec": number(raw.get("raceTime10K")),
            "race_time_half_sec": number(raw.get("raceTimeHalf")),
            "race_time_marathon_sec": number(raw.get("raceTimeMarathon")),
        }
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
        elif timestamp is None:
            excluded["missing_or_invalid_observation_timestamp"] += 1
        elif any(value is None or value <= 0 for value in values.values()):
            excluded["missing_or_invalid_race_prediction"] += 1
        else:
            accepted.append(
                {
                    "_snapshot_numbers": snapshot_numbers(raw),
                    "calendar_date": date,
                    "observation_timestamp": timestamp,
                    **values,
                }
            )
    result = finalize_daily(
        dataset="race_prediction_daily",
        key_fields=("calendar_date", "observation_timestamp"),
        selected_assets=selected,
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
        fields=RACE_PREDICTION_FIELDS,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    return result


__all__ = ["RACE_PREDICTION_FIELDS", "normalize_race_prediction"]
