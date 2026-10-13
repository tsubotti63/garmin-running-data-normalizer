from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.identity import IDENTIFIER, MISSING, garmin_activity_key, identifier_value, read_identifier
from ..common.time import (
    DEFAULT_TIMEZONE,
    unix_ms_to_local_date,
    unix_ms_to_local_datetime,
)
from ..intake.discovery import DiscoveredAsset, load_json_assets
from .records import IDENTITY_INVALID, IDENTITY_MISSING, count_left_out, row_snapshot_marks


def _unwrap(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            rows.extend(_unwrap(item))
    elif isinstance(value, dict):
        exported = value.get("summarizedActivitiesExport")
        if isinstance(exported, list):
            rows.extend(item for item in exported if isinstance(item, dict))
        elif "activityId" in value:
            rows.append(value)
        else:
            for item in value.values():
                if isinstance(item, (list, dict)):
                    rows.extend(_unwrap(item))
    return rows


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
        "activity_datetime_local": unix_ms_to_local_datetime(start_gmt, timezone_name),
        "activity_date_local": unix_ms_to_local_date(start_gmt, timezone_name),
        "distance_raw_centimeters": distance,
        "distance_m": float(distance) / 100.0 if isinstance(distance, (int, float)) else None,
        "duration_ms": duration,
        "duration_sec": float(duration) / 1000.0 if isinstance(duration, (int, float)) else None,
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
    (stage A3d-1b); without a counter, it stops the normalization.
    """
    records: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(
        root, filename_suffix="summarizedActivities.json", assets=assets
    ):
        for row in _unwrap(payload):
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
