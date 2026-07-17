from __future__ import annotations

from typing import Any

from ..common.identity import stable_hash
from ..intake.discovery import DiscoveredAsset, load_json_assets


def _containers(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def normalize_gear(root: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gear: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, filename_suffix="gear.json"):
        for container in _containers(payload):
            for row in container.get("gearDTOS", []) or []:
                if not isinstance(row, dict):
                    continue
                raw_gear_key = row.get("gearPk")
                fallback = [row.get("uuid"), row.get("displayName"), row.get("dateBegin")]
                if raw_gear_key in (None, "") and all(value in (None, "") for value in fallback):
                    raise ValueError("gear record lacks gearPk and deterministic fallback fields")
                gear_key = raw_gear_key if raw_gear_key not in (None, "") else stable_hash(
                    fallback, prefix="garmin_gear_hash:"
                )
                gear.append({
                    "gear_key": gear_key,
                    "uuid": row.get("uuid"),
                    "display_name": row.get("displayName"),
                    "custom_make_model": row.get("customMakeModel"),
                    "gear_type": row.get("gearTypeName") or row.get("gearType"),
                    "date_begin": row.get("dateBegin"),
                    "date_end": row.get("dateEnd"),
                    "maximum_meters": row.get("maximumMeters"),
                    "source_path": asset.provenance_path,
                    "source_sha256": asset.sha256,
                })
            activity_links = container.get("gearActivityDTOs") or {}
            if isinstance(activity_links, dict):
                for gear_key, values in activity_links.items():
                    if gear_key in (None, ""):
                        raise ValueError("activity-gear link lacks gear key")
                    for row in values or []:
                        if isinstance(row, dict):
                            activity_id = row.get("activityId")
                            if activity_id in (None, ""):
                                raise ValueError("activity-gear link lacks activityId")
                            links.append({
                                "gear_key": int(gear_key) if str(gear_key).isdigit() else gear_key,
                                "activity_id": activity_id,
                                "source_path": asset.provenance_path,
                                "source_sha256": asset.sha256,
                            })
    gear.sort(key=lambda row: (str(row["gear_key"]), str(row["source_path"])))
    links.sort(key=lambda row: (str(row["gear_key"]), str(row["activity_id"])))
    return gear, links
