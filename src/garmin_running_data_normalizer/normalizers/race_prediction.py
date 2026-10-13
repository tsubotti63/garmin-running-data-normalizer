from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..common.values import ValueReader, is_empty
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


RACE_PREDICTION_FIELDS = (
    "calendar_date",
    "observation_timestamp",
    "race_time_5k_sec",
    "race_time_10k_sec",
    "race_time_half_sec",
    "race_time_marathon_sec",
)
# The source field of each value field (stage A3d-1); the other fields are the
# record's key. A row left out that holds nothing in them is an empty record.
RACE_PREDICTION_VALUE_SOURCES = {
    "race_time_5k_sec": ("raceTime5K",),
    "race_time_10k_sec": ("raceTime10K",),
    "race_time_half_sec": ("raceTimeHalf",),
    "race_time_marathon_sec": ("raceTimeMarathon",),
}
RACE_PREDICTION_FIELDS_WITHOUT_VALUES = ("calendar_date", "observation_timestamp")


def _race_times(raw: dict[str, Any], values: ValueReader) -> dict[str, int | float | None]:
    """The distances; one given in a form that is not a positive number is
    left empty and kept in ``values`` (stage A3d-2a)."""
    return {
        field: values.number(raw.get(name), field, positive=True)
        for field, (name,) in RACE_PREDICTION_VALUE_SOURCES.items()
    }


def race_prediction_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why a Race Prediction record is left out, or None when it is kept.

    A distance that the record does not give stays empty, and the record is
    kept with its other distances (stage A3d-1); so is a distance given in a
    form that is not a positive number, which the audit keeps (stage
    A3d-2a). A record without any distance is left out, as an empty record.
    """
    if daily_calendar_date(raw.get("calendarDate")) is None:
        return "missing_or_invalid_calendar_date"
    if normalize_observation_timestamp(raw.get("timestamp"))[0] is None:
        return "missing_or_invalid_observation_timestamp"
    if all(is_empty(raw.get(name)) for (name,) in RACE_PREDICTION_VALUE_SOURCES.values()):
        return "missing_or_invalid_race_prediction"
    return None


def normalize_race_prediction(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(
        assets, lambda name: name.startswith("runracepredictions")
    )
    accepted = []
    left_out = RowsLeftOut(value_source_names(RACE_PREDICTION_VALUE_SOURCES))
    timestamp_semantics: Counter[str] = Counter()
    for raw in rows:
        timestamp, semantics = normalize_observation_timestamp(raw.get("timestamp"))
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        timestamp_semantics[semantics] += 1 + copies_within_snapshots(snapshot_numbers(raw))
        reason = race_prediction_left_out_reason(raw)
        if reason is not None:
            left_out.add(raw, reason)
            continue
        values = ValueReader()
        accepted.append(
            {
                "_snapshot_numbers": snapshot_numbers(raw),
                "calendar_date": daily_calendar_date(raw.get("calendarDate")),
                "observation_timestamp": timestamp,
                **_race_times(raw, values),
                "_value_problems": values.problems,
            }
        )
    result = finalize_daily(
        dataset="race_prediction_daily",
        key_fields=("calendar_date", "observation_timestamp"),
        selected_assets=selected,
        source_record_count=len(rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=RACE_PREDICTION_FIELDS,
    )
    result.audit["observation_timestamp_semantics_counts"] = dict(
        sorted(timestamp_semantics.items())
    )
    result.audit["storage_grain"] = "source_observation"
    result.audit["daily_projection_selection_rule"] = None
    return result


__all__ = [
    "RACE_PREDICTION_FIELDS",
    "RACE_PREDICTION_FIELDS_WITHOUT_VALUES",
    "RACE_PREDICTION_VALUE_SOURCES",
    "normalize_race_prediction",
    "race_prediction_left_out_reason",
]
