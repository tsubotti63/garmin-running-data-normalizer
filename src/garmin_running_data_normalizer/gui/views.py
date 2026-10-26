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
outputs are kept; the one used longest ago leaves first.
"""

from __future__ import annotations

import os
import re
import secrets
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ..output_check import OutputActionError
from ..view.data import MANIFEST, ViewData, load_view_data, local_today
from ..view.items import DATASETS, ITEMS, ITEMS_BY_KEY, Item
from ..view.series import GRAINS, LAST_YEARS, MAX_PANELS

MAX_VIEWS = 4
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
            return view.data


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
    a period of PERIODS, or a range of two dates; a grouping of GRAINS or
    auto; and the names of the activity types, or None for the running ones."""
    items = payload.get("items")
    if (
        not isinstance(items, list)
        or not 0 < len(items) <= MAX_PANELS
        or any(not isinstance(key, str) or key not in ITEMS_BY_KEY for key in items)
        or len(set(items)) != len(items)
    ):
        raise ViewRequestError("items")
    period = payload.get("period", "all")
    chosen: str | tuple[date, date]
    if isinstance(period, str) and period in PERIODS:
        chosen = period
    elif isinstance(period, dict) and set(period) == {"from", "to"}:
        start, end = period["from"], period["to"]
        try:
            if not (isinstance(start, str) and isinstance(end, str) and DATE_FORM.fullmatch(start) and DATE_FORM.fullmatch(end)):
                raise ValueError(start)
            chosen = (date.fromisoformat(start), date.fromisoformat(end))
        except ValueError as exc:
            raise ViewRequestError("period") from exc
        if chosen[0] > chosen[1]:
            raise ViewRequestError("period")
    else:
        raise ViewRequestError("period")
    grain = payload.get("grain", "auto")
    if not isinstance(grain, str) or grain not in ("auto", *GRAINS):
        raise ViewRequestError("grain")
    types = payload.get("types")
    if types is not None and (
        not isinstance(types, list) or any(not isinstance(name, str) for name in types) or len(set(types)) != len(types)
    ):
        raise ViewRequestError("types")
    return list(items), chosen, grain, types


__all__ = [
    "MAX_VIEWS",
    "PERIODS",
    "ViewNotOpenError",
    "ViewRequestError",
    "Views",
    "item_answer",
    "item_table",
    "output_stamp",
    "series_request",
]
