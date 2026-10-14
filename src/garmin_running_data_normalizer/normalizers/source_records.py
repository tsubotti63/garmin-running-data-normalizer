"""The records of an Export file, as a run and the Snapshot build read them
(stage A3d-2c-2).

A list of records can hold an item that is not an object, and the place of a
list of records can hold a value of another form, such as a number. Each is
kept, in the place of a record, as a mark: an object that names what it is
and keeps the value. A run counts the marks; the Snapshot build passes them to
Run-All as records without a key, so that Run-All counts them as a one-shot
run of the same Export does.
"""

from __future__ import annotations

from typing import Any

from ..common.values import is_empty

# The fields of a mark, which no Garmin record has.
MARK_FIELD = "garminRunningDataNormalizerItem"
MARK_VALUE_FIELD = "garminRunningDataNormalizerItemValue"
# What a mark stands for. A mark that holds a value is left out with this
# reason; an item that is an empty value is an empty record.
NOT_AN_OBJECT = "not_an_object"
RECORDS_NOT_READABLE = "records_not_readable"
MARK_KINDS = frozenset({NOT_AN_OBJECT, RECORDS_NOT_READABLE})
# The wrappers that hold the list of records of a daily file and of a
# performance-metric file, in the order they are looked at.
DAILY_WRAPPERS = ("data", "items", "records", "values", "summaries", "sleepData")
METRIC_WRAPPERS = ("records", "items", "data")


def mark(kind: str, value: Any) -> dict[str, Any]:
    """Return the mark of an item that is not an object, or of a value of
    another form in the place of a list of records."""
    return {MARK_FIELD: kind, MARK_VALUE_FIELD: value}


def is_mark(value: Any) -> bool:
    return isinstance(value, dict) and value.get(MARK_FIELD) in MARK_KINDS


def mark_holds_a_value(raw: dict[str, Any]) -> bool:
    """Whether a run leaves the mark out with its reason. An item that is an
    empty value (null, "", or []) holds nothing: it is an empty record, which
    a run only counts. A value of another form in the place of a list is
    marked only when it is not empty, so its records cannot be read."""
    return raw[MARK_FIELD] == RECORDS_NOT_READABLE or not is_empty(raw.get(MARK_VALUE_FIELD))


def list_items(value: Any) -> list[dict[str, Any]]:
    """Return the records of a list of records: its objects as they are, a
    mark for each other item, and one mark for a value of another form in its
    place. An empty value holds no records."""
    if isinstance(value, list):
        return [item if isinstance(item, dict) else mark(NOT_AN_OBJECT, item) for item in value]
    if is_empty(value):
        return []
    return [mark(RECORDS_NOT_READABLE, value)]


def file_items(value: Any, wrappers: tuple[str, ...]) -> list[dict[str, Any]]:
    """Return the records of a daily or performance-metric file: the
    items of its top list, of the first list that its top object holds under
    one of the wrappers, or the top object itself. A file whose value is
    neither a list nor an object gives one mark, unless it is empty."""
    if isinstance(value, dict):
        if is_mark(value):
            return [value]
        for name in wrappers:
            nested = value.get(name)
            if isinstance(nested, list):
                return list_items(nested)
        return [value]
    return list_items(value)


def container_items(value: Any) -> list[dict[str, Any]]:
    """Return the objects of a Gear or Personal Records file that hold its
    lists of records: the top object, or the objects of the top list, with a
    mark for each other item of the top list. A file whose value is neither
    a list nor an object gives one mark, unless it is empty."""
    if isinstance(value, dict):
        return [value]
    return list_items(value)


def activity_items(value: Any, *, top: bool = True) -> list[dict[str, Any]]:
    """Return the Activities records of a file: the items of each
    ``summarizedActivitiesExport`` list, and the objects with an
    ``activityId`` among the objects around them.

    The items of a ``summarizedActivitiesExport`` list that are not objects
    are marked, and so are the items of the top list that are neither
    objects nor lists, a ``summarizedActivitiesExport`` that holds a value
    other than a list or an object, and a file whose value is neither. A
    list of the top list, a ``summarizedActivitiesExport`` object, and the
    other lists and objects inside the objects are searched for records as
    before, and the other items of those lists are not records.
    """
    rows: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, dict)):
                rows.extend(activity_items(item, top=False))
            elif top:
                rows.append(mark(NOT_AN_OBJECT, item))
    elif isinstance(value, dict):
        if is_mark(value):
            return [value]
        exported = value.get("summarizedActivitiesExport")
        if isinstance(exported, list):
            rows.extend(list_items(exported))
        elif "activityId" in value:
            rows.append(value)
        else:
            if not isinstance(exported, dict) and not is_empty(exported):
                rows.append(mark(RECORDS_NOT_READABLE, exported))
            for item in value.values():
                if isinstance(item, (list, dict)):
                    rows.extend(activity_items(item, top=False))
    elif top and not is_empty(value):
        rows.append(mark(RECORDS_NOT_READABLE, value))
    return rows


__all__ = [
    "DAILY_WRAPPERS",
    "MARK_FIELD",
    "MARK_KINDS",
    "MARK_VALUE_FIELD",
    "METRIC_WRAPPERS",
    "NOT_AN_OBJECT",
    "RECORDS_NOT_READABLE",
    "activity_items",
    "container_items",
    "file_items",
    "is_mark",
    "list_items",
    "mark",
    "mark_holds_a_value",
]
