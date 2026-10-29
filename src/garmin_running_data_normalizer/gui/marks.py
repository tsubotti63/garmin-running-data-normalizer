"""The marks of the view page (internal; stage M1 of v2.2.0): the days and
spans that the person marks on the panels, such as a race, an injury, or new
shoes.

A mark has an id that the server gives ("m-" and eight hexadecimal digits),
a kind (race, injury, shoes, or other), a name, its day, and for a span the
day it ends ("end"; None for one day). The name is kept by the rules of the
name of a layout (layouts.layout_name); two marks can have the same name, as
their days and ids tell them apart. A day is a date of the calendar from
1 January 1900, in the form that the period of the view page takes
(YYYY-MM-DD; the page counts its days from years of four digits), and a span
does not end before its day; a span that ends on its day is a mark of one day.

The marks are kept in a file of their own next to the settings
(gui-marks.json: the settings could not hold 200 marks within their limit),
never in an output. The support bundle and the report on GitHub never read
it, as the names are the person's own record. The file holds up to 200 marks
in the order of their days (those of one day keep their order, and a new one
comes last of its day). A mark of another form is left out alone, so that the
others are still used; only a file changed by hand holds one, as this version
writes no other form. A later version that adds a kind or a key writes the
file in format 2, which this version does not use and never writes over.

The changes are pure functions here; the settings read, change, and write
the file under the lock of the settings (settings.change_marks_at). A change
gives every value of a mark again, so that of two tabs that change one mark,
the change made last stays, as for the layouts."""

from __future__ import annotations

import re
import secrets
from datetime import date
from typing import Any

from .layouts import layout_name
from .views import DATE_FORM

MARKS_FORMAT_PREFIX = "garmin-running-data-normalizer-gui-marks-v"
MARKS_FORMAT_VERSION = 1
MARKS_FORMAT = f"{MARKS_FORMAT_PREFIX}{MARKS_FORMAT_VERSION}"
MAX_MARKS = 200
MARK_KINDS = ("race", "injury", "shoes", "other")
MARK_ID = re.compile(r"m-[0-9a-f]{8}")
MARK_OPERATIONS = ("add", "change", "remove")
# The page counts days with Date.UTC, which reads a year below 100 as one of
# the 1900s.
FIRST_MARK_DAY = date(1900, 1, 1)

# What a change of the marks tells the page, codes only.
MARK_DAY_INVALID = "MARK_DAY_INVALID"
MARK_NAME_INVALID = "MARK_NAME_INVALID"
MARK_NOT_FOUND = "MARK_NOT_FOUND"
MARKS_FULL = "MARKS_FULL"
REQUEST_INVALID = "REQUEST_INVALID"


class MarkChangeError(ValueError):
    """A change of the marks that cannot be made, with its code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def mark_day(value: Any) -> date | None:
    """The date of a day given as YYYY-MM-DD, as the period of the view page
    takes it (views.period_choice); None when it is of another form, not a
    date of the calendar, or before FIRST_MARK_DAY."""
    if not isinstance(value, str) or not DATE_FORM.fullmatch(value):
        return None
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    return day if day >= FIRST_MARK_DAY else None


def mark_days(day: Any, end: Any) -> tuple[str, str | None] | None:
    """The day and the end of a mark as they are kept, or None when either is
    of another form or the span ends before its day. A span that ends on its
    day is kept as a mark of one day."""
    first = mark_day(day)
    if first is None:
        return None
    if end is None:
        return day, None
    last = mark_day(end)
    if last is None or last < first:
        return None
    return (day, None) if last == first else (day, end)


def _in_order(marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # The sort is stable: the marks of one day keep their order.
    return sorted(marks, key=lambda mark: mark["day"])


def kept_marks(value: Any) -> list[dict[str, Any]] | None:
    """The marks as the file keeps them, in the order of their days, or None
    when the value is not a list. A mark of another form is left out alone: an
    id of another form or one given twice, a kind that this version does not
    know, a name that is not kept, or days of another form; so are the marks
    after the 200th."""
    if not isinstance(value, list):
        return None
    marks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in value:
        if len(marks) == MAX_MARKS:
            break
        if not isinstance(entry, dict):
            continue
        mark_id = entry.get("id")
        kind = entry.get("kind")
        name = layout_name(entry.get("name"))
        days = mark_days(entry.get("day"), entry.get("end"))
        if not isinstance(mark_id, str) or not MARK_ID.fullmatch(mark_id) or mark_id in seen:
            continue
        if not isinstance(kind, str) or kind not in MARK_KINDS or name is None or days is None:
            continue
        seen.add(mark_id)
        marks.append({"id": mark_id, "kind": kind, "name": name, "day": days[0], "end": days[1]})
    return _in_order(marks)


def new_mark_id(taken: set[str]) -> str:
    """An id for a new mark that no other mark has."""
    while True:
        mark_id = f"m-{secrets.token_hex(4)}"
        if mark_id not in taken:
            return mark_id


def change_marks(marks: list[dict[str, Any]], change: Any) -> list[dict[str, Any]]:
    """The marks after one change of the page, in the order of their days.
    MarkChangeError tells why a change cannot be made.

    - add (kind, name, day, and end for a span): a new mark.
    - change (id, and all of kind, name, day, and end again): a mark.
    - remove (id): a mark."""
    if not isinstance(change, dict) or change.get("op") not in MARK_OPERATIONS:
        raise MarkChangeError(REQUEST_INVALID)
    operation = change["op"]
    marks = [dict(mark) for mark in marks]

    def index_of() -> int:
        mark_id = change.get("id")
        for index, mark in enumerate(marks):
            if mark["id"] == mark_id:
                return index
        raise MarkChangeError(MARK_NOT_FOUND)

    def kind_given() -> str:
        kind = change.get("kind")
        if not isinstance(kind, str) or kind not in MARK_KINDS:
            raise MarkChangeError(REQUEST_INVALID)
        return kind

    def values_given(kind: str) -> dict[str, Any]:
        days = mark_days(change.get("day"), change.get("end"))
        if days is None:
            raise MarkChangeError(MARK_DAY_INVALID)
        name = layout_name(change.get("name"))
        if name is None:
            raise MarkChangeError(MARK_NAME_INVALID)
        return {"kind": kind, "name": name, "day": days[0], "end": days[1]}

    if operation == "add":
        kind = kind_given()
        if len(marks) >= MAX_MARKS:
            raise MarkChangeError(MARKS_FULL)
        values = values_given(kind)
        marks.append({"id": new_mark_id({mark["id"] for mark in marks}), **values})
    elif operation == "change":
        index = index_of()
        marks[index].update(values_given(kind_given()))
    else:
        marks.pop(index_of())
    return _in_order(marks)


__all__ = [
    "FIRST_MARK_DAY",
    "MARKS_FORMAT",
    "MARKS_FORMAT_PREFIX",
    "MARKS_FORMAT_VERSION",
    "MARKS_FULL",
    "MARK_DAY_INVALID",
    "MARK_ID",
    "MARK_KINDS",
    "MARK_NAME_INVALID",
    "MARK_NOT_FOUND",
    "MARK_OPERATIONS",
    "MAX_MARKS",
    "MarkChangeError",
    "change_marks",
    "kept_marks",
    "mark_day",
    "mark_days",
    "new_mark_id",
]
