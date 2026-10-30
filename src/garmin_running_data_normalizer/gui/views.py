"""The outputs that the view page opened, and the requests for their numbers
(stage G3b).

The page opens an output once: the server checks it and reads it as the view
page reads it (``load_view_data``), and keeps what it read in memory under a
ticket of random characters, which holds no place. Every request for numbers
looks at the output again by the size, the time of change, and the inode of
its folder and of the files that the view page reads, and by the date of
today in the output's timezone. When one of them changed, the output is
checked and read again; the contents of the files (their sha256) are checked
when an output is opened and when it is read again, not at every request.

Nothing is written: no file of settings and no temporary file. At most four
outputs are kept; the one used longest ago leaves first. With each output,
the bars of its item shelf are kept by the activity types of the requests,
at most eight, until the output is read again (stage M2 of v2.2.0).
"""

from __future__ import annotations

import os
import re
import secrets
import threading
from collections import OrderedDict
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from ..output_check import OutputActionError
from ..view.data import MANIFEST, ViewData, load_view_data, local_today
from ..view.items import ACTIVITIES, DATASETS, ITEMS, ITEMS_BY_KEY, Item
from ..view.series import GRAINS, LAST_YEARS, MAX_PANELS, RANGE_GRAIN, coverage, point_item

MAX_VIEWS = 4
MAX_SHELVES = 8
PERIODS = ("all", *LAST_YEARS)
DATE_FORM = re.compile(r"\d{4}-\d{2}-\d{2}")


class ViewNotOpenError(Exception):
    """The ticket names no output that this server keeps."""


class ViewRequestError(ValueError):
    """A request for numbers that is not of its form."""


Stamp = tuple[tuple[Any, ...], ...]


def output_stamp(output: Path) -> Stamp:
    """The size, the time of change, and the inode of the output's folder and
    of the files that the view page reads; a file that cannot be looked at,
    or a link in its place, gives another stamp."""
    stamps = []
    for path in (output, output / MANIFEST, *(output / dataset.path for dataset in DATASETS)):
        try:
            status = os.lstat(path)
        except OSError:
            stamps.append(())
            continue
        stamps.append((status.st_mode, status.st_size, status.st_mtime_ns, status.st_ino, status.st_dev))
    return tuple(stamps)


@dataclass
class _View:
    output: Path
    stamp: Stamp
    data: ViewData
    lock: threading.Lock
    # The bars of the item shelf of ``data`` by the activity types (stage M2
    # of v2.2.0): every answer carries them, and they are made from every
    # row of the output, while a comparison by race day asks up to 13 times
    # in a row.
    shelves: OrderedDict[frozenset[str] | None, dict[str, dict[str, Any]]] = field(default_factory=OrderedDict)


class Views:
    """The outputs that the view page opened, by their tickets."""

    def __init__(
        self,
        load: Callable[[Path], ViewData] = load_view_data,
        today: Callable[[str], date] = local_today,
        max_views: int = MAX_VIEWS,
    ) -> None:
        self._load = load
        self._today = today
        self._max_views = max_views
        self._lock = threading.Lock()
        self._views: OrderedDict[str, _View] = OrderedDict()

    def _read(self, output: Path) -> tuple[ViewData, Stamp]:
        # The stamp before and after the reading: an output that changed
        # while it was read is not kept.
        before = output_stamp(output)
        data = self._load(output)
        if output_stamp(output) != before:
            raise OutputActionError("OUTPUT_CHANGED")
        return data, before

    def open(self, output: Path) -> tuple[str, ViewData]:
        """Check and read ``output``, and keep it under a new ticket. The
        reading takes no lock of the server, so that other requests are
        answered meanwhile."""
        data, stamp = self._read(output)
        ticket = secrets.token_urlsafe(16)
        with self._lock:
            self._views[ticket] = _View(output, stamp, data, threading.Lock())
            while len(self._views) > self._max_views:
                self._views.popitem(last=False)
        return ticket, data

    def data(self, ticket: str) -> ViewData:
        """What the output of ``ticket`` holds now: what was read, when its
        stamp and the date of today are the same; otherwise it is checked and
        read again, and a ticket whose output fails is forgotten."""
        with self._lock:
            view = self._views.get(ticket)
            if view is None:
                raise ViewNotOpenError(ticket)
            self._views.move_to_end(ticket)
        with view.lock:
            if output_stamp(view.output) == view.stamp and self._today(view.data.timezone).toordinal() == view.data.today:
                return view.data
            try:
                view.data, view.stamp = self._read(view.output)
            except Exception:
                with self._lock:
                    if self._views.get(ticket) is view:
                        del self._views[ticket]
                raise
            view.shelves = OrderedDict()
            return view.data

    def coverage(self, ticket: str, data: ViewData, types: Collection[str] | None = None) -> dict[str, dict[str, Any]]:
        """The bars of the item shelf of ``data`` for ``types`` (``coverage``),
        made once while the output of ``ticket`` holds ``data``; for a ticket
        that is gone, or an output read again meanwhile, they are made and
        not kept."""
        with self._lock:
            view = self._views.get(ticket)
        if view is None:
            return coverage(data, types)
        key = None if types is None else frozenset(types)
        with view.lock:
            if view.data is not data:
                return coverage(data, types)
            shelf = view.shelves.get(key)
            if shelf is None:
                shelf = view.shelves[key] = coverage(data, types)
                while len(view.shelves) > MAX_SHELVES:
                    view.shelves.popitem(last=False)
            else:
                view.shelves.move_to_end(key)
            return shelf


def item_answer(item: Item) -> dict[str, Any]:
    """What the page knows of an item: the table of items is the server's
    only, and the page takes it from here."""
    return {
        "key": item.key,
        "group": item.group,
        "kind": item.kind,
        "unit": item.unit,
        "unit_group": item.unit_group,
        "per_day": item.per_day,
        "sleep": item.sleep,
        "from_fit": item.from_fit,
    }


def item_table() -> list[dict[str, Any]]:
    return [item_answer(item) for item in ITEMS]


def series_request(payload: dict[str, Any]) -> tuple[list[str], str | tuple[date, date], str, list[str] | None]:
    """The items, the period, the grouping, and the activity types of a
    request for numbers: one to six items that this version knows, each once;
    a period of PERIODS, or a range of two dates; a grouping of GRAINS, auto,
    or from stage M2 of v2.2.0 the whole period (RANGE_GRAIN, which the
    settings do not keep); and the names of the activity types, or None for
    the running ones."""
    items = payload.get("items")
    if (
        not isinstance(items, list)
        or not 0 < len(items) <= MAX_PANELS
        or any(not isinstance(key, str) or key not in ITEMS_BY_KEY for key in items)
        or len(set(items)) != len(items)
    ):
        raise ViewRequestError("items")
    chosen = period_choice(payload.get("period", "all"))
    if chosen is None:
        raise ViewRequestError("period")
    grain = payload.get("grain", "auto")
    if not (grain_ok(grain) or grain == RANGE_GRAIN):
        raise ViewRequestError("grain")
    types = payload.get("types")
    if types is not None and not types_ok(types):
        raise ViewRequestError("types")
    return list(items), chosen, grain, types


def previous_request(payload: dict[str, Any], grain: str) -> bool:
    """Whether a request for numbers asks for the period of the same length
    just before (stage Q1 of v2.2.0): a truth value only, as the month of a
    comparison is an integer only (not 1 or "true"), and true with the whole
    period (RANGE_GRAIN) only; false where the request leaves it out."""
    previous = payload.get("previous", False)
    if type(previous) is not bool or (previous and grain != RANGE_GRAIN):
        raise ViewRequestError("previous")
    return previous


def list_request(payload: dict[str, Any]) -> tuple[str, tuple[date, date], list[str] | None]:
    """The item, the days, and the activity types of a request for the list
    of the activities of one period of a panel (stage M3 of v2.2.0): an item
    of the activities; the days of the period, as a range of two dates; and
    the names of the activity types, or None for the running ones."""
    key = payload.get("item")
    if not isinstance(key, str) or key not in ITEMS_BY_KEY or ITEMS_BY_KEY[key].dataset != ACTIVITIES:
        raise ViewRequestError("item")
    chosen = period_choice(payload.get("period"))
    if not isinstance(chosen, tuple):
        raise ViewRequestError("period")
    types = payload.get("types")
    if types is not None and not types_ok(types):
        raise ViewRequestError("types")
    return key, chosen, types


def points_request(payload: dict[str, Any]) -> tuple[str, str, str | tuple[date, date], list[str] | None]:
    """The two items, the period, and the activity types of a request for two
    items of the activities plotted against each other (stage O1 of v2.2.0):
    two different items that one activity has a value of (series.point_item);
    a period of PERIODS, or a range of two dates, as the numbers take it; and
    the names of the activity types, or None for the running ones."""
    x, y = payload.get("x"), payload.get("y")
    if not point_item(x):
        raise ViewRequestError("x")
    if not point_item(y) or y == x:
        raise ViewRequestError("y")
    chosen = period_choice(payload.get("period", "all"))
    if chosen is None:
        raise ViewRequestError("period")
    types = payload.get("types")
    if types is not None and not types_ok(types):
        raise ViewRequestError("types")
    return x, y, chosen, types


def spread_request(payload: dict[str, Any]) -> tuple[str, str | tuple[date, date], list[str] | None]:
    """The item, the period, and the activity types of a request for the
    distribution of one item of the activities (stage P1 of v2.2.0): an item
    that one activity has a value of (series.point_item, as for the points);
    a period of PERIODS, or a range of two dates, as the numbers take it; and
    the names of the activity types, or None for the running ones."""
    key = payload.get("item")
    if not point_item(key):
        raise ViewRequestError("item")
    chosen = period_choice(payload.get("period", "all"))
    if chosen is None:
        raise ViewRequestError("period")
    types = payload.get("types")
    if types is not None and not types_ok(types):
        raise ViewRequestError("types")
    return key, chosen, types


def period_choice(period: Any) -> str | tuple[date, date] | None:
    """The period that a request names: one of PERIODS, or a range of two
    dates, the first not after the second; None when it is of another form.
    The settings take the period that they remember by the same rule (stage
    K1 of v2.2.0)."""
    if isinstance(period, str) and period in PERIODS:
        return period
    if isinstance(period, dict) and set(period) == {"from", "to"}:
        start, end = period["from"], period["to"]
        if not (isinstance(start, str) and isinstance(end, str) and DATE_FORM.fullmatch(start) and DATE_FORM.fullmatch(end)):
            return None
        try:
            chosen = (date.fromisoformat(start), date.fromisoformat(end))
        except ValueError:
            return None
        return chosen if chosen[0] <= chosen[1] else None
    return None


def grain_ok(grain: Any) -> bool:
    """Whether a request names a grouping: "auto" or one of GRAINS."""
    return isinstance(grain, str) and grain in ("auto", *GRAINS)


# How the view page compares one item by year (stage L1 of v2.2.0): the
# years in rows, laid over one another, or added up from the first day; from
# stage N1, also as a calendar of the days of each year.
COMPARE_MODES = ("rows", "overlay", "cumulative", "calendar")


def compare_mode_ok(mode: Any) -> bool:
    """Whether a request names a way to compare by year: one of COMPARE_MODES."""
    return isinstance(mode, str) and mode in COMPARE_MODES


def compare_month_ok(month: Any) -> bool:
    """Whether a request names a month to compare by year: 1 to 12, an integer
    (never a truth value); none is the whole year."""
    return type(month) is int and 1 <= month <= 12


# What the view page compares one item by (stage M2 of v2.2.0): the years, or
# the race marks, each from some weeks before its day to the day.
COMPARE_BYS = ("year", "race")
COMPARE_WEEKS = (8, 12, 16, 20, 24)


def compare_by_ok(by: Any) -> bool:
    """Whether a request names what to compare by: one of COMPARE_BYS."""
    return isinstance(by, str) and by in COMPARE_BYS


def compare_weeks_ok(weeks: Any) -> bool:
    """Whether a request names the weeks before a race day to compare: one of
    COMPARE_WEEKS, an integer (never a truth value)."""
    return type(weeks) is int and weeks in COMPARE_WEEKS


def plot_pair_ok(pair: Any) -> bool:
    """Whether a request names the two items plotted against each other
    (stage O1 of v2.2.0): both of them, as one pair, two different items that
    one activity has a value of, so that the settings never keep one of them
    alone (Codex's review of the plan of O1)."""
    return (
        isinstance(pair, dict)
        and set(pair) == {"x", "y"}
        and point_item(pair["x"])
        and point_item(pair["y"])
        and pair["x"] != pair["y"]
    )


def types_ok(types: Any) -> bool:
    """Whether a request names the activity types that it counts: a list of
    names, each once, as 2.1.0 took them; the limit of the size of a request
    bounds them. The settings keep a choice only when they can keep the whole
    of it (settings.types_kept, stage K1 of v2.2.0)."""
    return isinstance(types, list) and all(isinstance(name, str) for name in types) and len(set(types)) == len(types)


__all__ = [
    "MAX_SHELVES",
    "MAX_VIEWS",
    "COMPARE_BYS",
    "COMPARE_MODES",
    "COMPARE_WEEKS",
    "PERIODS",
    "ViewNotOpenError",
    "ViewRequestError",
    "Views",
    "compare_by_ok",
    "compare_mode_ok",
    "compare_month_ok",
    "compare_weeks_ok",
    "grain_ok",
    "item_answer",
    "item_table",
    "list_request",
    "output_stamp",
    "period_choice",
    "plot_pair_ok",
    "points_request",
    "previous_request",
    "series_request",
    "spread_request",
    "types_ok",
]
