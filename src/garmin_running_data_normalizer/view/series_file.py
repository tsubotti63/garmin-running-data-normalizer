"""The numbers of the view page in a new CSV file: the series command (stage G2).

The command reads an output as the page reads it (``load_view_data``) and
writes the numbers of the same functions, so that the page and the CLI give
the same numbers. One row is one period of one line of one item, for every
period, with an empty value where there is none; the values are not rounded,
and keep the units of SCHEMA_CATALOG.json. What is left out of the numbers is
not in the file: the command prints it, by item.

The file holds the values of the output: on macOS and Linux only its owner
may read it (Windows gives it the permissions of its folder), it is never
inside the output, and it never replaces a file (common/new_file). A name
of a sport, which comes from Garmin, is written only when it is made of
capitals, digits, and ``_``, so that a spreadsheet never reads it as a
formula; otherwise it is left empty and counted.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Collection
from datetime import date
from pathlib import Path
from typing import Any

from ..common.new_file import NewFileError, check_new_file_place, write_new_file
from .data import load_view_data
from .items import ITEMS, ITEMS_BY_KEY
from .series import LAST_YEARS, activity_types, view_answer

SERIES_COLUMNS = (
    "item",
    "line",
    "kind",
    "unit",
    "vo2max_source_series",
    "sport",
    "period_start",
    "period_end",
    "partial",
    "value",
    "count",
)
PERIODS = ("all", *LAST_YEARS)
# The names that a cell of a spreadsheet never reads as a formula.
SPORT_NAME = re.compile(r"[A-Z0-9_]+")
SERIES_NAME = re.compile(r"[a-z0-9_]+")
DATE_FORM = re.compile(r"\d{4}-\d{2}-\d{2}")


class SeriesError(ValueError):
    """A stop of the series command, with its code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


def _period(period: str | None, start: str | None, end: str | None) -> str | tuple[date, date]:
    """The period of the numbers: one of PERIODS, or a range of two dates."""
    if start is None and end is None:
        return period or "all"
    if start is None or end is None or period is not None:
        raise SeriesError("SERIES_RANGE_INVALID", "the range of dates was not given as one range")
    try:
        if not (DATE_FORM.fullmatch(start) and DATE_FORM.fullmatch(end)):
            raise ValueError(start)
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise SeriesError("SERIES_RANGE_INVALID", "a date of the range is not a date") from exc
    if first > last:
        raise SeriesError("SERIES_RANGE_INVALID", "the range ends before it starts")
    return first, last


def series_csv(answer: dict[str, Any]) -> tuple[bytes, int, dict[str, int]]:
    """The CSV file of an answer of the view page, the number of its rows,
    and, by item, the lines whose name of a sport was not written."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(SERIES_COLUMNS)
    rows = 0
    hidden: dict[str, int] = {}
    for panel in answer["panels"]:
        item = ITEMS_BY_KEY[panel["item"]]
        for number, line in enumerate(panel["lines"], 1):
            series = line["series"] or {}
            source = series.get("vo2max_source_series", "")
            sport = series.get("sport", "")
            if source and not SERIES_NAME.fullmatch(source):
                source = ""
            if sport and not SPORT_NAME.fullmatch(sport):
                hidden[item.key] = hidden.get(item.key, 0) + 1
                sport = ""
            for period, value, count in zip(answer["periods"], line["values"], line["counts"]):
                writer.writerow(
                    (
                        item.key,
                        number,
                        item.kind,
                        item.unit or "",
                        source,
                        sport,
                        period["start"],
                        period["end"],
                        "true" if period["partial"] else "false",
                        "" if value is None else repr(value),
                        count,
                    )
                )
                rows += 1
    return stream.getvalue().encode("utf-8"), rows, hidden


def write_series(
    run_output: str | Path,
    output: str | Path,
    *,
    items: Collection[str] | None = None,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
    grain: str = "auto",
    types: Collection[str] | None = None,
    all_types: bool = False,
    today: date | None = None,
) -> dict[str, Any]:
    """Write the numbers of the view page of ``run_output`` to the new CSV
    file ``output``. ``items`` are the keys of the items, all of them in the
    order of the table unless given; ``types`` are the activity types
    counted, the running types unless given or ``all_types``."""
    run_output, destination = Path(run_output), Path(output)
    keys = list(dict.fromkeys(items)) if items else [item.key for item in ITEMS]
    if any(key not in ITEMS_BY_KEY for key in keys):
        raise SeriesError("SERIES_ITEM_UNKNOWN", "an item key that this app does not know was given")
    chosen = _period(period, start, end)
    try:
        check_new_file_place(run_output, destination)
    except NewFileError as exc:
        if exc.reason == "parent":
            raise SeriesError("SERIES_PARENT_NOT_FOUND", "the folder for the CSV file does not exist or is not a folder") from None
        if exc.reason == "inside":
            raise SeriesError("SERIES_INSIDE_OUTPUT", "the place of the CSV file is inside the run output") from None
        raise SeriesError("SERIES_EXISTS", "a file or a link is there already in the place of the CSV file") from None
    data = load_view_data(run_output, today=today)
    names = {entry["name"] for entry in activity_types(data)}
    counted: Collection[str] | None = None
    if all_types:
        counted = names
    elif types:
        # The names as the output writes them: another case or another
        # separator is another name.
        if any(name not in names for name in types):
            raise SeriesError("SERIES_TYPE_UNKNOWN", "an activity type that the output does not have was given")
        counted = list(types)
    answer = view_answer(data, keys, chosen, grain, counted)
    body, rows, hidden = series_csv(answer)
    try:
        write_new_file(destination, body)
    except NewFileError as exc:
        if exc.reason == "exists":
            raise SeriesError("SERIES_EXISTS", "a file or a link is there already in the place of the CSV file") from exc
        raise SeriesError("SERIES_NOT_WRITTEN", "the CSV file could not be written") from exc
    about: dict[str, dict[str, int]] = {}
    for panel in answer["panels"]:
        counts = {name: count for name, count in panel["left_out"].items() if count}
        if hidden.get(panel["item"]):
            counts["sport_name_not_written"] = hidden[panel["item"]]
        if counts:
            about[panel["item"]] = dict(sorted(counts.items()))
    return {
        "status": "PASS",
        "path": destination.name,
        "rows": rows,
        "items": len(keys),
        "start": answer["start"],
        "end": answer["end"],
        "grain": answer["grain"],
        "about": about,
    }


__all__ = ["PERIODS", "SERIES_COLUMNS", "SeriesError", "series_csv", "write_series"]
