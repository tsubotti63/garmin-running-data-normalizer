from __future__ import annotations

from typing import Any

from ..common.identity import garmin_activity_key
from ..common.time import unix_ms_to_local_date, unix_ms_to_local_datetime
from ..intake.discovery import DiscoveredAsset, load_json_assets


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


def _normalize(row: dict[str, Any], asset: DiscoveredAsset) -> dict[str, Any]:
    activity_id = row.get("activityId")
    start_gmt = row.get("startTimeGmt")
    if start_gmt is None:
        start_gmt = row.get("beginTimestamp")
    distance = row.get("distance")
    duration = row.get("duration")
    description = row.get("description")
    return {
        "garmin_activity_key": garmin_activity_key(activity_id, start_gmt, distance, duration, row.get("activityType")),
        "activity_id": activity_id,
        "name": row.get("name"),
        "memo_text_raw": description,
        "memo_present": isinstance(description, str) and bool(description.strip()),
        "activity_type": row.get("activityType"),
        "sport_type": row.get("sportType"),
        "start_time_gmt_ms": start_gmt,
        "start_time_local_raw": row.get("startTimeLocal"),
        "activity_datetime_local": unix_ms_to_local_datetime(start_gmt),
        "activity_date_local": unix_ms_to_local_date(start_gmt),
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
    }


def normalize_activities(root: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, filename_suffix="summarizedActivities.json"):
        records.extend(_normalize(row, asset) for row in _unwrap(payload))
    return sorted(records, key=lambda row: (str(row["garmin_activity_key"]), str(row["source_path"])))
