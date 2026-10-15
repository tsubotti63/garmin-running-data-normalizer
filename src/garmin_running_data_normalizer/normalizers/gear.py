from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.identity import (
    IDENTIFIER,
    INVALID,
    MISSING,
    identifier_value,
    is_ascii_digits,
    read_identifier,
    stable_hash,
)
from ..common.values import is_empty
from ..intake.discovery import DiscoveredAsset, load_json_assets
from .records import (
    IDENTITY_INVALID,
    IDENTITY_MISSING,
    count_left_out,
    count_mark,
    row_snapshot_marks,
)
from .source_records import RECORDS_NOT_READABLE, container_items, list_items, mark
from .unread_fields import UnreadFields, count_unread

GEAR_ITEM_MESSAGE = "gear item is not an object or its list has an unsupported type"
LINK_ITEM_MESSAGE = "activity-gear link is not an object or its list has an unsupported type"
# The source fields that Gear and its links read; the audit records count
# the others by name (stage A4c-1).
GEAR_SOURCE_FIELDS = frozenset(
    {
        "gearPk", "uuid", "displayName", "customMakeModel", "gearTypeName",
        "gearType", "dateBegin", "dateEnd", "maximumMeters",
    }
)
GEAR_LINK_SOURCE_FIELDS = frozenset({"activityId"})


def gear_links(container: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the Gear links of a container, by Gear key, and a mark for a
    ``gearActivityDTOs`` of another form than an object (stage A3d-2c-2): its
    links cannot be read. An empty value holds no links."""
    links = container.get("gearActivityDTOs")
    if isinstance(links, dict):
        return links, []
    if is_empty(links):
        return {}, []
    return {}, [mark(RECORDS_NOT_READABLE, links)]


def _fallback(row: dict[str, Any]) -> list[Any]:
    """The fields that make the key of a Gear record without an identifier."""
    return [row.get("uuid"), row.get("displayName"), row.get("dateBegin")]


def gear_left_out_reason(row: dict[str, Any]) -> str | None:
    """Return why a Gear row is left out, or None when it is kept.

    A Gear record is named by its identifier (``gearPk``), or, when it has
    none, by the key made from its other fields. An identifier of 0 or of a
    form that cannot name a record leaves the row out (stage A3d-1b).
    """
    state, token = read_identifier(row.get("gearPk"))
    if state == IDENTIFIER and token != "0":
        return None
    if state == MISSING:
        if not all(value in (None, "") for value in _fallback(row)):
            return None
        return IDENTITY_MISSING
    return IDENTITY_INVALID


def link_left_out_reason(gear_key: Any, row: dict[str, Any]) -> str | None:
    """Return why an activity_gear link is left out, or None when it is kept.

    A link is named by its Gear key and its Activity identifier; it is left
    out when either has a form that cannot name a record or is 0, or else
    when either is missing (stage A3d-1b).
    """
    readings = (read_identifier(gear_key), read_identifier(row.get("activityId")))
    if any(state == INVALID or token == "0" for state, token in readings):
        return IDENTITY_INVALID
    if any(state == MISSING for state, _token in readings):
        return IDENTITY_MISSING
    return None


def gear_record_key(row: dict[str, Any]) -> Any:
    """Return the stable key of a Gear row that is kept: its identifier, as
    the source wrote it, or else the key made from its other fields."""
    gear_key = identifier_value(row.get("gearPk"))
    if read_identifier(gear_key)[0] == IDENTIFIER:
        return gear_key
    return stable_hash(_fallback(row), prefix="garmin_gear_hash:")


def normalize_gear(
    root: str,
    *,
    assets: Iterable[DiscoveredAsset] | None = None,
    left_out: dict[str, Counter[str]] | None = None,
    unread: dict[str, UnreadFields] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize Gear and its links; ``assets`` are the Export's files from an open reading.

    A row without a usable identifier is counted by reason in
    ``left_out["gear"]`` or ``left_out["activity_gear"]`` (stage A3d-1b), and
    so are an item that is not a record and a list of records that cannot be
    read (stage A3d-2c-2); an item of the file's top list counts as Gear.
    Without counters, they stop the normalization. The fields of the rows read
    that no field takes are counted in ``unread["gear"]`` and
    ``unread["activity_gear"]`` (stage A4c-1).
    """
    gear_left_out = None if left_out is None else left_out.setdefault("gear", Counter())
    link_left_out = (
        None if left_out is None else left_out.setdefault("activity_gear", Counter())
    )
    gear_unread = None if unread is None else unread.get("gear")
    link_unread = None if unread is None else unread.get("activity_gear")
    gear: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for payload, asset in load_json_assets(root, family="gear", assets=assets):
        for container in container_items(payload):
            if count_mark(gear_left_out, container, GEAR_ITEM_MESSAGE):
                continue
            for row in list_items(container.get("gearDTOS")):
                if count_mark(gear_left_out, row, GEAR_ITEM_MESSAGE):
                    continue
                reason = gear_left_out_reason(row)
                if reason is not None:
                    count_left_out(
                        gear_left_out,
                        row,
                        reason,
                        "gear record lacks gearPk and deterministic fallback fields"
                        if reason == IDENTITY_MISSING
                        else "gear record identifier has an unsupported type",
                    )
                    continue
                count_unread(gear_unread, row)
                gear.append({
                    "gear_key": gear_record_key(row),
                    "uuid": row.get("uuid"),
                    "display_name": row.get("displayName"),
                    "custom_make_model": row.get("customMakeModel"),
                    "gear_type": row.get("gearTypeName") or row.get("gearType"),
                    "date_begin": row.get("dateBegin"),
                    "date_end": row.get("dateEnd"),
                    "maximum_meters": row.get("maximumMeters"),
                    "source_path": asset.provenance_path,
                    "source_sha256": asset.sha256,
                    **row_snapshot_marks(row),
                })
            activity_links, unreadable = gear_links(container)
            for row in unreadable:
                count_mark(link_left_out, row, LINK_ITEM_MESSAGE)
            for gear_key, values in activity_links.items():
                for row in list_items(values):
                    if count_mark(link_left_out, row, LINK_ITEM_MESSAGE):
                        continue
                    reason = link_left_out_reason(gear_key, row)
                    if reason is not None:
                        count_left_out(
                            link_left_out,
                            row,
                            reason,
                            "activity-gear link lacks gear key or activityId"
                            if reason == IDENTITY_MISSING
                            else "activity-gear link identifier has an unsupported type",
                        )
                        continue
                    count_unread(link_unread, row)
                    links.append({
                        # Digits are written as an integer, as in v1.7.1;
                        # other digits, such as "²", stay text.
                        "gear_key": (
                            int(gear_key)
                            if isinstance(gear_key, str) and is_ascii_digits(gear_key)
                            else gear_key
                        ),
                        "activity_id": identifier_value(row.get("activityId")),
                        "source_path": asset.provenance_path,
                        "source_sha256": asset.sha256,
                        **row_snapshot_marks(row),
                    })
    gear.sort(key=lambda row: (str(row["gear_key"]), str(row["source_path"])))
    links.sort(key=lambda row: (str(row["gear_key"]), str(row["activity_id"])))
    return gear, links
