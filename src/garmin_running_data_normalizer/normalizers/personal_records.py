from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.identity import IDENTIFIER, MISSING, identifier_value, read_identifier, stable_hash
from ..intake.discovery import DiscoveredAsset, load_json_assets
from .records import (
    IDENTITY_INVALID,
    IDENTITY_MISSING,
    count_left_out,
    count_mark,
    row_snapshot_marks,
)
from .source_records import container_items, list_items
from .unread_fields import UnreadFields, count_unread

PERSONAL_RECORD_ITEM_MESSAGE = (
    "personal record item is not an object or its list has an unsupported type"
)
# The source fields that Personal Records read; the audit record counts the
# others by name (stage A4c-1).
PERSONAL_RECORD_SOURCE_FIELDS = frozenset(
    {
        "personalRecordId", "activityId", "personalRecordType", "value",
        "prStartTimeGMT", "createdDate", "current", "confirmed",
    }
)


def _fallback(row: dict[str, Any]) -> list[Any]:
    """The fields that make the key of a Personal Record without an identifier."""
    return [
        identifier_value(row.get("activityId")),
        row.get("personalRecordType"),
        row.get("value"),
        row.get("prStartTimeGMT"),
    ]


def personal_record_left_out_reason(row: dict[str, Any]) -> str | None:
    """Return why a Personal Records row is left out, or None when it is kept.

    A Personal Record is named by its identifier, also 0, or, when it has
    none, by the key made from its other fields. An identifier of a form that
    cannot name a record leaves the row out (stage A3d-1b).
    """
    state, _token = read_identifier(row.get("personalRecordId"))
    if state == IDENTIFIER:
        return None
    if state == MISSING:
        if not all(value in (None, "") for value in _fallback(row)):
            return None
        return IDENTITY_MISSING
    return IDENTITY_INVALID


def personal_record_key(row: dict[str, Any]) -> Any:
    """Return the stable key of a Personal Records row that is kept: its
    identifier, as the source wrote it, or else the key made from its other
    fields."""
    record_id = identifier_value(row.get("personalRecordId"))
    if read_identifier(record_id)[0] == IDENTIFIER:
        return record_id
    return stable_hash(_fallback(row), prefix="garmin_personal_record_hash:")


def normalize_personal_records(
    root: str,
    *,
    assets: Iterable[DiscoveredAsset] | None = None,
    left_out: Counter[str] | None = None,
    unread: UnreadFields | None = None,
) -> list[dict[str, Any]]:
    """Normalize Personal Records; ``assets`` are the Export's files from an open reading.

    A row without a usable identifier is counted in ``left_out`` by reason
    (stage A3d-1b), and so are an item that is not a record and a list of
    records that cannot be read (stage A3d-2c-2); without a counter, they
    stop the normalization. The fields of the rows read that no field takes
    are counted in ``unread`` (stage A4c-1).
    """
    records: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, family="personal_records", assets=assets):
        for container in container_items(payload):
            if count_mark(left_out, container, PERSONAL_RECORD_ITEM_MESSAGE):
                continue
            for index, row in enumerate(list_items(container.get("personalRecords"))):
                if count_mark(left_out, row, PERSONAL_RECORD_ITEM_MESSAGE):
                    continue
                reason = personal_record_left_out_reason(row)
                if reason is not None:
                    count_left_out(
                        left_out,
                        row,
                        reason,
                        "personal record lacks identifier and deterministic fallback fields"
                        if reason == IDENTITY_MISSING
                        else "personal record identifier has an unsupported type",
                    )
                    continue
                count_unread(unread, row)
                records.append({
                    "personal_record_id": personal_record_key(row),
                    "activity_id": identifier_value(row.get("activityId")),
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
                    **row_snapshot_marks(row),
                })
    return sorted(records, key=lambda row: (str(row["personal_record_id"]), str(row["source_path"])))
