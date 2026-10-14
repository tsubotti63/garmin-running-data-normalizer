from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.identity import IDENTIFIER, MISSING, garmin_activity_key, identifier_value, read_identifier
from ..common.values import read_value
from ..common.time import (
    DEFAULT_TIMEZONE,
    unix_ms_to_local_datetime,
)
from ..intake.discovery import DiscoveredAsset, load_json_assets
from .records import (
    IDENTITY_INVALID,
    IDENTITY_MISSING,
    VALUE_PROBLEMS,
    count_left_out,
    count_mark,
    row_snapshot_marks,
)
from .source_records import activity_items


def _start(row: dict[str, Any]) -> Any:
    start_gmt = row.get("startTimeGmt")
    return row.get("beginTimestamp") if start_gmt is None else start_gmt


def _fallback_parts(row: dict[str, Any]) -> tuple[Any, ...]:
    """The fields that make the key of an Activity without an identifier."""
    return (_start(row), row.get("distance"), row.get("duration"), row.get("activityType"))


def activity_left_out_reason(row: dict[str, Any]) -> str | None:
    """Return why an Activities row is left out, or None when it is kept.

    An Activity is named by its identifier, or, when it has none, by the key
    made from its other fields. An identifier of 0 or of a form that cannot
    name a record leaves the row out, also when those fields are there
    (stage A3d-1b).
    """
    state, token = read_identifier(row.get("activityId"))
    if state == IDENTIFIER and token != "0":
        return None
    if state == MISSING:
        if any(part not in (None, "") for part in _fallback_parts(row)):
            return None
        return IDENTITY_MISSING
    return IDENTITY_INVALID


def activity_key(row: dict[str, Any]) -> str:
    """Return the stable key of an Activities row that is kept: made from its
    identifier, as the source wrote it, or else from its other fields."""
    activity_id = identifier_value(row.get("activityId"))
    named = read_identifier(activity_id)[0] == IDENTIFIER
    return garmin_activity_key(activity_id if named else None, *_fallback_parts(row))


def _normalize(
    row: dict[str, Any],
    asset: DiscoveredAsset,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict[str, Any]:
    start_gmt = _start(row)
    distance = row.get("distance")
    duration = row.get("duration")
    description = row.get("description")
    # Values are made from numbers only; a value of another form is left
    # empty by Run-All, which keeps it (stage A3d-2a). A start time that is a
    # number but out of range keeps its value, and its local date and time are
    # empty; it is kept here, since Run-All cannot tell it from no time.
    distance_value = read_value(distance, "number")[1]
    duration_value = read_value(duration, "number")[1]
    start_value = read_value(start_gmt, "number")[1]
    local_datetime = unix_ms_to_local_datetime(start_value, timezone_name)
    problems = (
        [("start_time_gmt_ms", start_gmt)]
        if start_value is not None and local_datetime is None
        else []
    )
    return {
        "garmin_activity_key": activity_key(row),
        "activity_id": identifier_value(row.get("activityId")),
        "name": row.get("name"),
        "memo_text_raw": description,
        "memo_present": isinstance(description, str) and bool(description.strip()),
        "activity_type": row.get("activityType"),
        "sport_type": row.get("sportType"),
        "start_time_gmt_ms": start_gmt,
        "start_time_local_raw": row.get("startTimeLocal"),
        "activity_datetime_local": local_datetime,
        "activity_date_local": local_datetime[:10] if local_datetime else None,
        "distance_raw_centimeters": distance,
        "distance_m": None if distance_value is None else distance_value / 100.0,
        "duration_ms": duration,
        "duration_sec": None if duration_value is None else duration_value / 1000.0,
        "elapsed_duration_ms": row.get("elapsedDuration"),
        "moving_duration_ms": row.get("movingDuration"),
        "avg_hr": row.get("avgHr"),
        "max_hr": row.get("maxHr"),
        "avg_power": row.get("avgPower"),
        "max_power": row.get("maxPower"),
        "avg_run_cadence": row.get("avgRunCadence"),
        "training_effect_label": row.get("trainingEffectLabel"),
        "activity_training_load": row.get("activityTrainingLoad"),
        "lap_count": row.get("lapCount"),
        "source_path": asset.provenance_path,
        "source_sha256": asset.sha256,
        "source_confidence": "high",
        **row_snapshot_marks(row),
        **({VALUE_PROBLEMS: problems} if problems else {}),
    }


def normalize_activities(
    root: str,
    timezone_name: str = DEFAULT_TIMEZONE,
    *,
    assets: Iterable[DiscoveredAsset] | None = None,
    left_out: Counter[str] | None = None,
) -> list[dict[str, Any]]:
    """Normalize the Activities; ``assets`` are the Export's files from an open reading.

    A row without a usable identifier is counted in ``left_out`` by reason
    (stage A3d-1b), and so are an item that is not a record and a list of
    records that cannot be read (stage A3d-2c-2); without a counter, they
    stop the normalization.
    """
    records: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(
        root, filename_suffix="summarizedActivities.json", assets=assets
    ):
        for row in activity_items(payload):
            if count_mark(
                left_out, row, "activity item is not an object or its list has an unsupported type"
            ):
                continue
            reason = activity_left_out_reason(row)
            if reason is not None:
                count_left_out(
                    left_out,
                    row,
                    reason,
                    "activity_id or at least one fallback part is required"
                    if reason == IDENTITY_MISSING
                    else "activity_id has an unsupported type",
                )
                continue
            records.append(_normalize(row, asset, timezone_name))
    return sorted(records, key=lambda row: (str(row["garmin_activity_key"]), str(row["source_path"])))
