from __future__ import annotations

from typing import Any

from ..common.identity import stable_hash
from ..intake.discovery import load_json_assets


def normalize_personal_records(root: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, filename_suffix="personalRecord.json"):
        containers = payload if isinstance(payload, list) else [payload]
        for container in containers:
            if not isinstance(container, dict):
                continue
            for index, row in enumerate(container.get("personalRecords", []) or []):
                if not isinstance(row, dict):
                    continue
                raw_record_id = row.get("personalRecordId")
                fallback = [row.get("activityId"), row.get("personalRecordType"), row.get("value"), row.get("prStartTimeGMT")]
                if raw_record_id in (None, "") and all(value in (None, "") for value in fallback):
                    raise ValueError("personal record lacks identifier and deterministic fallback fields")
                record_key = raw_record_id if raw_record_id not in (None, "") else stable_hash(
                    fallback,
                    prefix="garmin_personal_record_hash:",
                )
                records.append({
                    "personal_record_id": record_key,
                    "activity_id": row.get("activityId"),
                    "personal_record_type": row.get("personalRecordType"),
                    "value": row.get("value"),
                    "start_time_gmt": row.get("prStartTimeGMT"),
                    "created_date": row.get("createdDate"),
                    "current": row.get("current"),
                    "confirmed": row.get("confirmed"),
                    "source_record_index": index,
                    "source_path": asset.provenance_path,
                    "source_sha256": asset.sha256,
                    "source_confidence": "high",
                })
    return sorted(records, key=lambda row: (str(row["personal_record_id"]), str(row["source_path"])))
