"""The numbers of the view page (stage G1).

The same rows, period, grouping, and activity types give the same numbers.
Every panel of a page shares one list of periods: the days, the weeks from
Monday, the months, or the years of a period of the output, the first and the
last cut by the period and marked as partial.

- A total (sum, count) is that of the recorded activities. A period without a
  recorded activity is 0 between the first and the last activity of the
  activity types counted, and empty before and after them: 0 means no record,
  not that there was no run.
- The pace is the total time divided by the total distance of the activities
  with both; a mean of activities is weighted by their durations.
- A daily item is the mean of the days with a value; a sleep counts only on
  the days that it may be used.
- An item with several records a day shows every record at the grain of a
  day, and otherwise their mean; the two series of VO2max, and its sports,
  stay in separate lines.

Values that are missing are never filled, carried, or made 0, and what is
left out is counted. The numbers are not rounded: the page and the CLI round
them as they show them.

From stage T1 of v2.2.0, the view page may give conditions on the activities
(Conditions): words of the name, a distance, and a time. They choose the rows
of the activities where the activity types counted do, after them, so that
every view takes them the same way; the CLI gives none.
"""

from __future__ import annotations

import math
import re
import unicodedata
from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from functools import cached_property
from typing import Any

from ..common.names import unsafe_character
from ..common.sport import sport_group
from .data import Names, Row, ViewData, fold
from .items import (
    ACTIVITIES,
    COUNT,
    DATASETS_BY_NAME,
    DISTANCE,
    DURATION,
    FIRST_ITEMS,
    ITEMS,
    ITEMS_BY_KEY,
    MAXIMUM,
    OBSERVED,
    PACE,
    SUM,
    TIME_WEIGHTED,
    Item,
)

GRAINS = ("day", "week", "month", "year")
# The whole period as one period (stage M2 of v2.2.0): the value of a span
# that the calendar does not give, such as the weeks before a race. Only the
# requests of the view page take it (gui/views.py); the CLI and the settings
# keep GRAINS.
RANGE_GRAIN = "range"
# A page shows up to six panels, and its answer of six panels at the grain of
# a day over 15 years stays within this size (a test of stage G1).
MAX_PANELS = 6
MAX_ANSWER_BYTES = 4 * 1024 * 1024
# The periods that end on the last day of the output, by their years.
LAST_YEARS = {"10y": 10, "5y": 5, "3y": 3, "1y": 1}
# The list of the activities of one period of a panel (stage M3 of v2.2.0):
# up to this many rows; a period of more says how many, without them. Its
# columns are the values of these items, as the panels count them, and of
# the item of the panel when it is none of them.
MAX_LIST_ROWS = 500
LIST_ITEMS = ("dist", "time", "pace", "hr", "mx", "cad", "asc")
# Two items of the activities plotted against each other (stage O1 of
# v2.2.0): a point an activity with a value of both, the newest up to this
# many.
MAX_POINTS = 5000
# The distribution of one item of the activities (stage P1 of v2.2.0): how
# many activities fall in each range of the width of the item, up to this
# many ranges; the width times the first of 2, 5, 10, 20, 50, ... that is
# enough where more would be needed.
MAX_RANGES = 200
# The ranges of each item that one activity has a value of: its value in the
# units of the output times the first number, cut in ranges of the second,
# each with its left end and without its right one: 1 km in metres, 10
# minutes in seconds, 10 seconds a kilometre, 0.5 cm in millimetres, 1 % in
# tenths of a percent, and so on (OP0 of v2.2.0). The page writes the ends of
# the ranges from these two numbers of an answer only (the checker's review
# of the plan of P1).
SPREAD_RANGES = {
    "dist": (1, 1000),
    "time": (1, 600),
    "pace": (1000, 10),
    "hr": (1, 5),
    "mx": (1, 5),
    "cad": (1, 5),
    "pow": (1, 10),
    "load": (1, 10),
    "asc": (1, 10),
    "vo": (1, 5),
    "gct": (1, 10),
    "gctp": (10, 10),
    "bal": (10, 5),
    "vr": (10, 5),
    "sl": (1, 50),
}
# The local date and time of an activity as the output writes it
# (common/time.py): the date, and the time of the day before its offset, as
# the page orders them (view_flow.mjs LOCAL_MOMENT).
LOCAL_MOMENT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?")
# The type of an activity without activity_type.
NO_TYPE = ""
# The activity types that the settings remember (stage K1 of v2.2.0): a choice
# of up to 64 names, each of up to 128 characters without a control or
# direction character. A request of the numbers takes any names, as 2.1.0 did.
MAX_TYPES = 64
MAX_TYPE_LENGTH = 128
# The conditions on the activities (stage T1 of v2.2.0): the words of a name,
# of up to MAX_CONDITION_TEXT code points, split at 、 and "," after NFKC (so
# that the half-width ､ and the full-width ， split too), up to
# MAX_CONDITION_WORDS different words; a distance in whole metres and a time
# in whole minutes, from and to, up to their limits.
MAX_CONDITION_TEXT = 60
MAX_CONDITION_WORDS = 10
MAX_DISTANCE_METRES = 1_000_000
MAX_TIME_MINUTES = 6_000
CONDITION_SEPARATORS = re.compile("[、,]")


@dataclass(frozen=True)
class Periods:
    """The periods of a page: from ``start`` to ``end`` (ordinals of dates),
    by ``grain``, each as its first and last day and whether it is cut."""

    start: int
    end: int
    grain: str
    spans: tuple[tuple[int, int, bool], ...]

    def index(self, day: int) -> int | None:
        """The period of a day, or None outside the periods."""
        if not self.start <= day <= self.end:
            return None
        return bisect_right(self._starts, day) - 1

    @cached_property
    def _starts(self) -> list[int]:
        return [first for first, _last, _partial in self.spans]


def _add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        # 29 February, in a year without it.
        return day.replace(year=day.year + years, day=28)


def _years_before(end: int, years: int) -> int:
    """The day number of the first day of the ``years`` years that end on the
    day number ``end``, as LAST_YEARS counts them (the day after the same day
    ``years`` years before, 28 February for 29 February), or 0 where that day
    is before 1 January of the year 1, which no date writes (stage Q1 of
    v2.2.0: _add_years would raise there, for the periods of an output of the
    first years too). The day after 31 December of the year 0 is 1 January of
    the year 1 (Codex's review of the diff of Q1)."""
    day = date.fromordinal(end)
    if day.year - years < 1:
        return 1 if day.year - years == 0 and (day.month, day.day) == (12, 31) else 0
    return _add_years(day, -years).toordinal() + 1


def auto_grain(start: int, end: int) -> str:
    """The grouping of "Auto": by month for more than 3 years, by week for
    more than 1 year, and by day otherwise."""
    first = date.fromordinal(start)
    if end >= _add_years(first, 3).toordinal():
        return "month"
    if end >= _add_years(first, 1).toordinal():
        return "week"
    return "day"


def _natural(day: date, grain: str) -> tuple[date, date]:
    """The day, the week from Monday, the month, or the year of ``day``."""
    if grain == "day":
        return day, day
    if grain == "week":
        first = day - timedelta(days=day.weekday())
        return first, first + timedelta(days=6)
    if grain == "month":
        first = day.replace(day=1)
        following = first.replace(year=first.year + 1, month=1) if first.month == 12 else first.replace(month=first.month + 1)
        return first, following - timedelta(days=1)
    if grain == "year":
        return day.replace(month=1, day=1), day.replace(month=12, day=31)
    raise ValueError(f"unknown grouping: {grain}")


def period_bounds(
    data: ViewData,
    period: str | tuple[date, date] = "all",
    grain: str = "auto",
) -> Periods | None:
    """The periods of ``period``: "all", one of LAST_YEARS, which count back
    from the last day of the output, or a range of two dates, which is cut to
    the days of the output. None when the output has no rows, or the range is
    outside them. With RANGE_GRAIN, the period is one period, without the
    mark of a cut one: it is the span asked for, and the page tells where the
    output cuts it."""
    if grain != "auto" and grain not in GRAINS and grain != RANGE_GRAIN:
        raise ValueError(f"unknown grouping: {grain}")
    if isinstance(period, tuple) and period[0] > period[1]:
        raise ValueError("the range ends before it starts")
    if data.first_day is None or data.last_day is None:
        return None
    if isinstance(period, tuple):
        start, end = max(period[0].toordinal(), data.first_day), min(period[1].toordinal(), data.last_day)
        if start > end:
            return None
    elif period == "all":
        start, end = data.first_day, data.last_day
    elif period in LAST_YEARS:
        end = data.last_day
        start = max(_years_before(end, LAST_YEARS[period]), data.first_day)
    else:
        raise ValueError(f"unknown period: {period}")
    if grain == "auto":
        grain = auto_grain(start, end)
    if grain == RANGE_GRAIN:
        return Periods(start, end, grain, ((start, end, False),))
    spans = []
    day = date.fromordinal(start)
    while day.toordinal() <= end:
        first, last = _natural(day, grain)
        spans.append(
            (
                max(first.toordinal(), start),
                min(last.toordinal(), end),
                first.toordinal() < start or last.toordinal() > end,
            )
        )
        day = last + timedelta(days=1)
    return Periods(start, end, grain, tuple(spans))


def activity_types(data: ViewData) -> list[dict[str, Any]]:
    """The activity types of the output, with the number of their activities,
    most first, and whether the page counts them at first: the types whose
    sport group is running, as for the link of an activity and a FIT session."""
    counts = Counter(row.marks["type"] for row in data.rows[ACTIVITIES])
    return [
        {"name": name, "count": count, "running": _is_running(name)}
        for name, count in sorted(counts.items(), key=lambda entry: (-entry[1], entry[0]))
    ]


def _is_running(name: str) -> bool:
    return name != NO_TYPE and sport_group(name) == "running"


def type_name_ok(name: Any) -> bool:
    """Whether the settings may keep ``name`` among the activity types that
    they remember: NO_TYPE or a name of up to MAX_TYPE_LENGTH characters
    without a control or direction character."""
    return isinstance(name, str) and len(name) <= MAX_TYPE_LENGTH and not unsafe_character(name)


def default_types(data: ViewData) -> frozenset[str]:
    """The activity types that the page counts at first."""
    return frozenset(entry["name"] for entry in activity_types(data) if entry["running"])


@dataclass(frozen=True)
class Conditions:
    """The conditions on the activities that a request gives (stage T1 of
    v2.2.0): ``text``, the words of the name as the person wrote them (None
    without); ``words``, the same words as they are compared
    (condition_words); ``distance``, the least and the most metres, and
    ``time``, the least and the most minutes, each None where it has no
    bound."""

    text: str | None
    words: tuple[str, ...]
    distance: tuple[int | None, int | None] = (None, None)
    time: tuple[int | None, int | None] = (None, None)

    def asked(self) -> dict[str, Any]:
        """The conditions in the form of a request, as an answer gives them
        back: the page says and saves what the numbers were made of."""
        answer: dict[str, Any] = {}
        if self.text is not None:
            answer["name"] = self.text
        if self.distance != (None, None):
            answer["distance"] = list(self.distance)
        if self.time != (None, None):
            answer["time"] = list(self.time)
        return answer


def condition_words(text: str) -> tuple[str, ...]:
    """The words of the name of conditions as they are compared (stage T1 of
    v2.2.0): the text in NFKC, split at 、 and ",", each word without the
    spaces at its ends and case folded (data.fold), without the empty words
    and the words that are the same as one before. Only the server compares
    them; the page says the words as they were written."""
    words: list[str] = []
    for part in CONDITION_SEPARATORS.split(unicodedata.normalize("NFKC", text)):
        word = fold(part.strip())
        if word and word not in words:
            words.append(word)
    return tuple(words)


def _name_state(data: ViewData, conditions: Conditions) -> str | None:
    """Whether the words of the name were used ("used"), or not, as the
    names of the output could not be read ("unread"); None without words."""
    if not conditions.words:
        return None
    return "unread" if data.names is None or data.names.too_large else "used"


def _meets(row: Row, conditions: Conditions, names: Names | None) -> bool:
    """Whether an activity meets the conditions (stage T1 of v2.2.0): its
    name holds one of the words, where the names were read (an activity
    without a name does not; without the names, the words are not used);
    and its distance in metres and its time in seconds are within the
    bounds, both ends included, compared as the output writes them (an
    activity without the value does not, where the condition is given)."""
    if conditions.words and names is not None and not names.too_large:
        folded = names.folded.get(row.marks.get("key") or "")
        if folded is None or not any(word in folded for word in conditions.words):
            return False
    for value, (low, high), unit in (
        (row.values[DISTANCE], conditions.distance, 1),
        (row.values[DURATION], conditions.time, 60),
    ):
        if low is None and high is None:
            continue
        if value is None or (low is not None and value < low * unit) or (high is not None and value > high * unit):
            return False
    return True


def _activity_rows(data: ViewData, types: Collection[str] | None, conditions: Conditions | None = None) -> list[Row]:
    counted = default_types(data) if types is None else frozenset(types)
    rows = [row for row in data.rows[ACTIVITIES] if row.marks["type"] in counted]
    # The conditions choose after the types (stage T1 of v2.2.0).
    return rows if conditions is None else [row for row in rows if _meets(row, conditions, data.names)]


def condition_counts(
    data: ViewData,
    span: tuple[int, int] | None,
    types: Collection[str] | None,
    conditions: Conditions,
) -> dict[str, Any]:
    """What the line of the conditions says of an answer (stage T1 of
    v2.2.0): the conditions as they were asked, the activities of the
    activity types counted in the days of ``span`` (those of the answer),
    those of them that meet the conditions, and _name_state."""
    rows = [] if span is None else [row for row in _activity_rows(data, types) if span[0] <= row.day <= span[1]]
    return {
        "asked": conditions.asked(),
        "counted": len(rows),
        "met": sum(1 for row in rows if _meets(row, conditions, data.names)),
        "name": _name_state(data, conditions),
    }


def _row_name(data: ViewData, row: Row) -> str | None:
    """The name of an activity of the list of a period (stage T1 of
    v2.2.0), where the names were read."""
    names = data.names
    if names is None or names.too_large:
        return None
    return names.names.get(row.marks.get("key") or "")


def _has_value(item: Item, row: Row) -> bool:
    if item.kind == COUNT:
        return True
    if item.kind == PACE:
        return _positive(row.values[DISTANCE]) and _positive(row.values[DURATION])
    if item.sleep and not row.marks["used"]:
        return False
    return row.values[item.field] is not None


def _positive(value: float | None) -> bool:
    return value is not None and value > 0


def _missing(item: Item, row: Row) -> str:
    """Why an activity or a day without a value has none: its value was
    emptied because the values disagreed, or it has no value."""
    fields = (DISTANCE, DURATION) if item.kind == PACE else (item.field,)
    if any(row.values[name] is None and name in row.disagree for name in fields):
        return "disagree"
    return "no_value"


def item_series(
    data: ViewData,
    key: str,
    periods: Periods,
    types: Collection[str] | None = None,
    conditions: Conditions | None = None,
) -> dict[str, Any]:
    """The numbers of one panel: for each line, the value and the count of
    each period, and what was left out. ``types`` are the activity types
    counted by the training and running-form items, the running types when
    None, and ``conditions`` choose among them (stage T1 of v2.2.0); the
    other items use neither."""
    if key not in ITEMS_BY_KEY:
        raise ValueError(f"unknown item: {key}")
    item = ITEMS_BY_KEY[key]
    dataset = DATASETS_BY_NAME[item.dataset]
    left_out: Counter[str] = Counter()
    if item.dataset == ACTIVITIES:
        rows = _activity_rows(data, types, conditions)
        lines = [_activity_line(item, rows, periods, left_out)]
    else:
        rows = list(data.rows[item.dataset])
        groups: dict[tuple[str, ...], list[Row]] = defaultdict(list)
        for row in rows:
            groups[row.marks.get("series", ())].append(row)
        lines = [
            _daily_line(item, group, periods, left_out, series=dict(zip(dataset.series, name)) if name else None)
            for name, group in sorted(groups.items(), key=lambda entry: (entry[1][0].day, entry[0]))
        ]
        # A line of a series without a value in the periods draws nothing.
        lines = [line for line in lines if any(line["counts"])] or [
            _daily_line(item, [], periods, Counter(), series=None)
        ]
    left_out["no_date"] = data.no_date[item.dataset]
    left_out["after_today"] = data.after_today[item.dataset]
    for line in lines:
        line["summary"] = _summary(item, line)
    return {
        "item": item.key,
        "kind": item.kind,
        "lines": lines,
        "left_out": dict(sorted(left_out.items())),
        "periods_with_value": sum(
            1 for index in range(len(periods.spans)) if any(line["values"][index] is not None for line in lines)
        ),
    }


def _activity_line(item: Item, rows: list[Row], periods: Periods, left_out: Counter[str]) -> dict[str, Any]:
    size = len(periods.spans)
    totals = [0.0] * size
    weights = [0.0] * size
    counts = [0] * size
    recorded = [False] * size
    highest: list[float | None] = [None] * size
    for row in rows:
        index = periods.index(row.day)
        if index is None:
            continue
        recorded[index] = True
        if not _has_value(item, row):
            left_out[_missing(item, row)] += 1
            continue
        if item.kind == COUNT:
            counts[index] += 1
        elif item.kind == PACE:
            totals[index] += row.values[DURATION]
            weights[index] += row.values[DISTANCE]
            counts[index] += 1
        elif item.kind == SUM:
            totals[index] += row.values[item.field]
            counts[index] += 1
        elif item.kind == MAXIMUM:
            value = row.values[item.field]
            highest[index] = value if highest[index] is None else max(highest[index], value)
            counts[index] += 1
        elif item.kind == TIME_WEIGHTED:
            duration = row.values[DURATION]
            if not _positive(duration):
                left_out["no_duration"] += 1
                continue
            totals[index] += row.values[item.field] * duration
            weights[index] += duration
            counts[index] += 1
    # The first and the last activity of the types counted, in the output.
    first = rows[0].day if rows else None
    last = rows[-1].day if rows else None
    values: list[float | None] = []
    for index, (start, end, _partial) in enumerate(periods.spans):
        if item.kind in (SUM, COUNT):
            if counts[index]:
                values.append(totals[index] if item.kind == SUM else float(counts[index]))
            elif not recorded[index] and first is not None and start <= last and end >= first:
                values.append(0.0)
                left_out["zero_periods"] += 1
            else:
                values.append(None)
        elif item.kind == MAXIMUM:
            values.append(highest[index])
        else:
            values.append(totals[index] / weights[index] if counts[index] else None)
    return {"series": None, "values": values, "counts": counts}


def _daily_line(
    item: Item,
    rows: list[Row],
    periods: Periods,
    left_out: Counter[str],
    *,
    series: dict[str, str] | None,
) -> dict[str, Any]:
    size = len(periods.spans)
    totals = [0.0] * size
    counts = [0] * size
    records_by_day: Counter[int] = Counter()
    unused_sleep: dict[str, set[int]] = {"review": set(), "other": set()}
    points: list[list[Any]] = []
    for row in rows:
        index = periods.index(row.day)
        if index is None:
            continue
        if item.sleep and not row.marks["used"]:
            unused_sleep["review" if row.marks["review"] else "other"].add(row.day)
            continue
        if not _has_value(item, row):
            left_out[_missing(item, row)] += 1
            continue
        value = row.values[item.field]
        totals[index] += value
        counts[index] += 1
        records_by_day[row.day] += 1
        if item.kind == OBSERVED and periods.grain == "day":
            points.append([index, value])
    if item.sleep:
        left_out["sleep_review_days"] += len(unused_sleep["review"])
        left_out["sleep_other_days"] += len(unused_sleep["other"] - unused_sleep["review"])
    if item.kind == OBSERVED:
        left_out["days_with_several_records"] += sum(1 for count in records_by_day.values() if count > 1)
    line: dict[str, Any] = {
        "series": series,
        "values": [totals[index] / counts[index] if counts[index] else None for index in range(size)],
        "counts": counts,
    }
    if item.kind == OBSERVED and periods.grain == "day":
        line["points"] = points
    if series is not None:
        days = [row.day for row in rows]
        line["first_day"] = date.fromordinal(min(days)).isoformat()
        line["last_day"] = date.fromordinal(max(days)).isoformat()
    return line


def _summary(item: Item, line: dict[str, Any]) -> dict[str, Any]:
    """What the second line of a panel says of a line: the periods with
    records, without records (0), and with a value, and the lowest, the
    highest, and the latest value, with their periods. A total takes them from
    the periods with records, so that a period of 0 is not its lowest."""
    totals = item.kind in (SUM, COUNT)
    with_records = with_value = without_records = 0
    candidates: list[tuple[float, int]] = []
    for index, (value, count) in enumerate(zip(line["values"], line["counts"])):
        if value is None:
            continue
        with_value += 1
        if count:
            with_records += 1
        elif totals:
            without_records += 1
        if count or not totals:
            candidates.append((value, index))
    return {
        "periods_with_records": with_records,
        "periods_without_records": without_records,
        "periods_with_value": with_value,
        "lowest": _at(min(candidates, key=lambda entry: (entry[0], entry[1])) if candidates else None),
        "highest": _at(min(candidates, key=lambda entry: (-entry[0], entry[1])) if candidates else None),
        "latest": _at(max(candidates, key=lambda entry: entry[1]) if candidates else None),
    }


def _at(entry: tuple[float, int] | None) -> dict[str, Any] | None:
    return None if entry is None else {"value": entry[0], "period": entry[1]}


def coverage(
    data: ViewData,
    types: Collection[str] | None = None,
    conditions: Conditions | None = None,
) -> dict[str, dict[str, Any]]:
    """For each item, the months with a value on at least one day, and its
    first and last day with a value: the bars of the item shelf. The training
    and running-form items follow ``types``, and ``conditions`` (stage T1 of
    v2.2.0)."""
    activity_rows = _activity_rows(data, types, conditions)
    answer: dict[str, dict[str, Any]] = {}
    for item in ITEMS:
        rows = activity_rows if item.dataset == ACTIVITIES else data.rows[item.dataset]
        days = sorted({row.day for row in rows if _has_value(item, row)})
        months = sorted({date.fromordinal(day).strftime("%Y-%m") for day in days})
        answer[item.key] = {
            "months": months,
            "first_day": date.fromordinal(days[0]).isoformat() if days else None,
            "last_day": date.fromordinal(days[-1]).isoformat() if days else None,
        }
    return answer


def default_items(data: ViewData, shelf: dict[str, dict[str, Any]] | None = None) -> list[str]:
    """The items of the first time, without those that the output has no
    value of; ``shelf`` is ``coverage(data)`` when the caller has it."""
    shelf = coverage(data) if shelf is None else shelf
    return [key for key in FIRST_ITEMS if shelf[key]["months"]]


def chosen_span(data: ViewData, period: str | tuple[date, date]) -> tuple[int, int] | None:
    """The days of ``period`` as chosen, before the output cuts them, as day
    numbers (stage Q1 of v2.2.0): a range as it is, the years of LAST_YEARS
    back from the last day of the output (0 where their first day is before
    the calendar), and "all" from the first day of the output to its last;
    None for an output without rows."""
    if data.first_day is None or data.last_day is None:
        return None
    if isinstance(period, tuple):
        return period[0].toordinal(), period[1].toordinal()
    if period == "all":
        return data.first_day, data.last_day
    if period in LAST_YEARS:
        return _years_before(data.last_day, LAST_YEARS[period]), data.last_day
    raise ValueError(f"unknown period: {period}")


def previous_span(data: ViewData, period: str | tuple[date, date]) -> tuple[int, int] | None:
    """The days just before the period chosen, of the same length, as day
    numbers (stage Q1 of v2.2.0): the years of LAST_YEARS back from the day
    before its first day, counted as LAST_YEARS counts them, and the same
    number of days for a range; None for "all" and for an output without
    rows. A number below 1 is a day before 1 January of the year 1."""
    chosen = chosen_span(data, period)
    if chosen is None or period == "all":
        return None
    first, last = chosen
    end = first - 1
    if isinstance(period, str):
        return (_years_before(end, LAST_YEARS[period]) if end >= 1 else 0), end
    return first - (last - first + 1), end


def _day_or_none(number: int) -> str | None:
    """A day number as a date, or None before the calendar."""
    return date.fromordinal(number).isoformat() if number >= 1 else None


def _span_answer(data: ViewData, span: tuple[int, int]) -> tuple[dict[str, Any], tuple[int, int] | None, bool]:
    """The days of a span chosen as an answer writes them, each end None
    before the calendar; the days of the output in it (None where it is wholly
    outside); and whether the output holds all of it."""
    first, last = span
    cut_first, cut_last = max(first, data.first_day), min(last, data.last_day)
    cut = (cut_first, cut_last) if cut_first <= cut_last else None
    whole = first >= data.first_day and last <= data.last_day
    return {"start": _day_or_none(first), "end": _day_or_none(last)}, cut, whole


def view_answer(
    data: ViewData,
    keys: Collection[str],
    period: str | tuple[date, date] = "all",
    grain: str = "auto",
    types: Collection[str] | None = None,
    previous: bool = False,
    conditions: Conditions | None = None,
) -> dict[str, Any]:
    """The numbers of a page: its periods, once, and a panel for each item.
    With ``previous`` (the whole period only, stage Q1 of v2.2.0), also the
    days chosen and whether the output holds all of them, and the numbers of
    the period of the same length just before, counted from the same reading
    of the output in the same way: None for "all" and where the period is
    outside the output. With ``conditions`` (stage T1 of v2.2.0), they choose
    the activities of the panels and of the period before, and the answer
    says how many of the activities of its days meet them (condition_counts)."""
    if previous and grain != RANGE_GRAIN:
        raise ValueError("the period before is for the whole period only")
    periods = period_bounds(data, period, grain)
    if periods is None:
        answer: dict[str, Any] = {"start": None, "end": None, "grain": None, "periods": [], "panels": []}
        if previous:
            answer["previous"] = None
        if conditions is not None:
            answer["conditions"] = condition_counts(data, None, types, conditions)
        return answer
    answer = {
        "start": date.fromordinal(periods.start).isoformat(),
        "end": date.fromordinal(periods.end).isoformat(),
        "grain": periods.grain,
        "periods": [
            {"start": date.fromordinal(first).isoformat(), "end": date.fromordinal(last).isoformat(), "partial": partial}
            for first, last, partial in periods.spans
        ],
        "panels": [item_series(data, key, periods, types, conditions) for key in keys],
    }
    if conditions is not None:
        answer["conditions"] = condition_counts(data, (periods.start, periods.end), types, conditions)
    if previous:
        chosen = chosen_span(data, period)
        if chosen is None:
            raise RuntimeError("an output with periods has days")
        answer["chosen"], _cut, answer["whole"] = _span_answer(data, chosen)
        before = previous_span(data, period)
        if before is None:
            answer["previous"] = None
        else:
            days, cut, whole = _span_answer(data, before)
            answer["previous"] = {
                "chosen": days,
                "start": None if cut is None else date.fromordinal(cut[0]).isoformat(),
                "end": None if cut is None else date.fromordinal(cut[1]).isoformat(),
                "whole": whole,
                "panels": None
                if cut is None
                else [
                    item_series(data, key, Periods(cut[0], cut[1], RANGE_GRAIN, ((cut[0], cut[1], False),)), types, conditions)
                    for key in keys
                ],
            }
    return answer


def activity_list(
    data: ViewData,
    key: str,
    period: tuple[date, date],
    types: Collection[str] | None = None,
    conditions: Conditions | None = None,
) -> dict[str, Any]:
    """The activities of one period of the panel of an item of the activities
    (stage M3 of v2.2.0): those of the activity types counted in the days of
    ``period``, cut to the output, chosen as the panel chooses them, with the
    value of the panel there and the count of the activities that have it. A
    period of more than MAX_LIST_ROWS activities gives their number only.
    From stage T1 of v2.2.0, ``conditions`` choose among them as among those
    of the panel, and each row has its name where the names were read."""
    if key not in ITEMS_BY_KEY or ITEMS_BY_KEY[key].dataset != ACTIVITIES:
        raise ValueError(f"not an item of the activities: {key}")
    periods, chosen = _period_rows(data, period, types, conditions)
    if periods is None:
        return {"start": None, "end": None, "total": 0, "rows": [], "limit": MAX_LIST_ROWS, "value": None}
    [line] = item_series(data, key, periods, types, conditions)["lines"]
    columns = LIST_ITEMS if key in LIST_ITEMS or ITEMS_BY_KEY[key].kind == COUNT else (*LIST_ITEMS, key)
    rows = None
    if len(chosen) <= MAX_LIST_ROWS:
        rows = [
            {
                "day": date.fromordinal(row.day).isoformat(),
                "datetime": row.marks.get("datetime"),
                "type": row.marks["type"],
                "name": _row_name(data, row),
                "values": {name: _list_value(ITEMS_BY_KEY[name], row) for name in columns},
            }
            for row in chosen
        ]
    return {
        "start": date.fromordinal(periods.start).isoformat(),
        "end": date.fromordinal(periods.end).isoformat(),
        "total": len(chosen),
        "rows": rows,
        "limit": MAX_LIST_ROWS,
        "value": {"value": line["values"][0], "count": line["counts"][0]},
    }


def _period_rows(
    data: ViewData,
    period: str | tuple[date, date],
    types: Collection[str] | None,
    conditions: Conditions | None = None,
) -> tuple[Periods | None, list[Row]]:
    """The days of ``period`` cut to the output as one period, and the
    activities of the activity types counted in them, chosen as the panels
    choose them: those of the list of a period (stage M3 of v2.2.0) and of
    the points of two items (stage O1)."""
    periods = period_bounds(data, period, RANGE_GRAIN)
    if periods is None:
        return None, []
    return periods, [row for row in _activity_rows(data, types, conditions) if periods.index(row.day) is not None]


def _conditions_part(
    data: ViewData,
    periods: Periods | None,
    types: Collection[str] | None,
    conditions: Conditions | None,
) -> dict[str, Any]:
    """The line of the conditions of an answer of the days of ``periods``,
    where conditions were given (stage T1 of v2.2.0)."""
    if conditions is None:
        return {}
    return {"conditions": condition_counts(data, None if periods is None else (periods.start, periods.end), types, conditions)}


def _list_value(item: Item, row: Row) -> float | None:
    """The value of an activity in a column of the list, as the panel of
    ``item`` counts it: the pace by its time over its distance, and none
    where that is not a finite number (Codex's review of the plan of O1)."""
    if item.kind == PACE:
        distance, duration = row.values[DISTANCE], row.values[DURATION]
        if not (_positive(distance) and _positive(duration)):
            return None
        pace = duration / distance
        return pace if math.isfinite(pace) else None
    return row.values[item.field]


def point_item(key: Any) -> bool:
    """Whether ``key`` is an item that two items plotted against each other
    can take (stage O1 of v2.2.0): an item of the activities that one
    activity has a value of, which the count is not."""
    return (
        isinstance(key, str)
        and key in ITEMS_BY_KEY
        and ITEMS_BY_KEY[key].dataset == ACTIVITIES
        and ITEMS_BY_KEY[key].kind != COUNT
    )


def _moment_key(row: Row) -> str:
    """What the points are ordered by: the date and the time of the day of
    an activity as they show, before the offset, and its day where its time
    cannot be read (view_flow.mjs listMomentKey)."""
    moment = row.marks.get("datetime")
    found = LOCAL_MOMENT.match(moment) if isinstance(moment, str) else None
    return found.group(0) if found is not None else date.fromordinal(row.day).isoformat()


def activity_points(
    data: ViewData,
    x: str,
    y: str,
    period: str | tuple[date, date] = "all",
    types: Collection[str] | None = None,
    conditions: Conditions | None = None,
) -> dict[str, Any]:
    """Two items of the activities plotted against each other (stage O1 of
    v2.2.0): the activities of the activity types counted in the days of
    ``period``, chosen as the list of a period chooses them, each a point
    where it has a value of both items, as the list writes them. The newest
    MAX_POINTS points are given, oldest first, by the date and the time of
    the day as they show, then in the order of the output; ``total`` counts
    the activities of the period, ``with_values`` those with both values,
    and ``missing`` the others."""
    if not point_item(x) or not point_item(y) or x == y:
        raise ValueError(f"not two items of the activities: {x}, {y}")
    periods, chosen = _period_rows(data, period, types, conditions)
    with_values = []
    for index, row in enumerate(chosen):
        values = {key: _list_value(ITEMS_BY_KEY[key], row) for key in (x, y)}
        if values[x] is not None and values[y] is not None:
            with_values.append((_moment_key(row), index, row, values))
    with_values.sort(key=lambda entry: (entry[0], entry[1]))
    return {
        "start": None if periods is None else date.fromordinal(periods.start).isoformat(),
        "end": None if periods is None else date.fromordinal(periods.end).isoformat(),
        "total": len(chosen),
        "with_values": len(with_values),
        "missing": len(chosen) - len(with_values),
        "limit": MAX_POINTS,
        "points": [
            {
                "day": date.fromordinal(row.day).isoformat(),
                "datetime": row.marks.get("datetime"),
                "type": row.marks["type"],
                "values": values,
            }
            for _key, _index, row, values in with_values[-MAX_POINTS:]
        ],
        **_conditions_part(data, periods, types, conditions),
    }


def _exact(value: float) -> Fraction:
    """A value of the output as the decimal number that it writes, so that
    no division of floating numbers moves it over the end of a range: 342.38
    seconds over 1007 metres are 340 seconds a kilometre, and not 339.99...
    (the checker's and Codex's reviews of the plan of P1)."""
    return Fraction(Decimal(repr(value)))


def _range_number(item: Item, row: Row, scale: int, width: int) -> int:
    """The number of the range of ``width`` that an activity with a value of
    ``item`` (as _list_value gives it) is in: its value times ``scale``, the
    pace by its time times 1000 over its distance, not rounded, and cut
    toward the smaller number, as a Python integer, which a value as large as
    1e300 has at once (the checker's review of the plan of P1)."""
    if item.kind == PACE:
        value = _exact(row.values[DURATION]) * scale / _exact(row.values[DISTANCE])
    else:
        value = _exact(row.values[item.field]) * scale
    return math.floor(value / width)


def _wider() -> Iterator[int]:
    """The steps of a wider range: 1, 2, 5, 10, 20, 50, ..."""
    power = 1
    while True:
        for lead in (1, 2, 5):
            yield lead * power
        power *= 10


def activity_spread(
    data: ViewData,
    key: str,
    period: str | tuple[date, date] = "all",
    types: Collection[str] | None = None,
    conditions: Conditions | None = None,
) -> dict[str, Any]:
    """The distribution of one item of the activities (stage P1 of v2.2.0):
    the activities of the activity types counted in the days of ``period``,
    chosen as the points are, that have a value of the item as the list
    writes it, counted in the ranges of the width of the item from the first
    range with an activity to the last, at most MAX_RANGES of them, with the
    width times the first step of _wider that is enough. A value is not
    rounded: 10999.6 metres are in the range of 10 to 11 km (the Human
    maintainer, 2026-10-30). The range ``first + i`` holds ``counts[i]``
    activities, from ``(first + i) * width / scale`` in the units of the
    output to the next; ``total`` counts the activities of the period,
    ``with_values`` those with a value, and ``missing`` the others."""
    if not point_item(key):
        raise ValueError(f"not an item of the activities: {key}")
    item = ITEMS_BY_KEY[key]
    scale, width = SPREAD_RANGES[key]
    periods, chosen = _period_rows(data, period, types, conditions)
    # Each value once in a range of the width of the item; a wider range only
    # takes those together (Codex's review of the plan of P1).
    counted = Counter(
        _range_number(item, row, scale, width) for row in chosen if _list_value(item, row) is not None
    )
    factor = 1
    if counted:
        low, high = min(counted), max(counted)
        factor = next(step for step in _wider() if high // step - low // step + 1 <= MAX_RANGES)
    ranges: Counter[int] = Counter()
    for number, count in counted.items():
        ranges[number // factor] += count
    first = min(ranges) if ranges else None
    last = max(ranges) if ranges else None
    # The step keeps the ranges to MAX_RANGES; their list is never made over a
    # wider span, which values as large as 1e300 would make endless (the
    # partial guard of P1).
    if first is not None and last - first >= MAX_RANGES:
        raise RuntimeError(f"more than {MAX_RANGES} ranges")
    with_values = sum(counted.values())
    return {
        "start": None if periods is None else date.fromordinal(periods.start).isoformat(),
        "end": None if periods is None else date.fromordinal(periods.end).isoformat(),
        "total": len(chosen),
        "with_values": with_values,
        "missing": len(chosen) - with_values,
        "limit": MAX_RANGES,
        "scale": scale,
        "width": width * factor,
        "widened": factor > 1,
        "first": first,
        "counts": [] if first is None else [ranges.get(number, 0) for number in range(first, last + 1)],
        **_conditions_part(data, periods, types, conditions),
    }


def shoe_count(data: ViewData) -> dict[str, Any]:
    """What the page needs to know of the shoes of an output before it shows
    them (stage S1 of v2.2.0): how many pairs link to an activity of the
    output up to today, of any type, and whether the files of the shoes were
    left out for their size. An output read without its shoes has none."""
    gear = data.gear
    if gear is None:
        return {"count": 0, "too_large": False}
    keys = {row.marks.get("key") for row in data.rows[ACTIVITIES] if row.marks.get("key")}
    linked = {shoe for activity, shoes in gear.links.items() if activity in keys for shoe in shoes}
    return {"count": len(linked), "too_large": gear.too_large}


def shoe_answer(
    data: ViewData,
    period: str | tuple[date, date] = "all",
    types: Collection[str] | None = None,
    conditions: Conditions | None = None,
) -> dict[str, Any]:
    """The view by shoes (stage S1 of v2.2.0): the months of ``period``,
    once; the activities of the activity types counted in it, chosen as the
    list of a period chooses them, by whether they link to shoes (to one or
    more, of which to two or more; not known: a link that tells no shoe, or
    no key; the rest without); and for each pair of shoes with an activity in
    it, in the order of its last one, newest first (then of gear.json): its
    distance by month, as the panel of the distance counts it (0 in the
    months between its first and last activities without one), and in the
    whole period, from its activities, never added up from the months; the
    activities of each month; the number of its activities and of those
    without a distance; the days of the first and the last; what Garmin sets
    of it; and what tells it from the shoes of the same name. An activity
    with two shoes counts for each. The pairs without an activity in the
    period are counted only."""
    item = ITEMS_BY_KEY["dist"]
    gear = data.gear
    shoes = () if gear is None else gear.shoes
    months = period_bounds(data, period, "month")
    whole, rows = _period_rows(data, period, types, conditions)
    answer: dict[str, Any] = {
        "start": None,
        "end": None,
        "grain": "month",
        "periods": [],
        "shoes": [],
        "activities": len(rows),
        "with_shoes": 0,
        "two_or_more": 0,
        "not_known": 0,
        "without_shoes": 0,
        "without_distance": 0,
        "left_out": len(shoes),
        "available": shoe_count(data),
    }
    # With conditions, the activities above are those that meet them (M); the
    # line counts the others before them (Codex's review of the plan of T1).
    answer.update(_conditions_part(data, whole, types, conditions))
    if months is None or whole is None:
        return answer
    linked: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        key = row.marks.get("key") or ""
        found = gear.links.get(key, frozenset()) if gear is not None and key else frozenset()
        if found:
            answer["with_shoes"] += 1
            if len(found) > 1:
                answer["two_or_more"] += 1
            if not _has_value(item, row):
                answer["without_distance"] += 1
            for shoe in found:
                linked[shoe].append(row)
        elif not key or (gear is not None and key in gear.unknown):
            answer["not_known"] += 1
    answer["without_shoes"] = len(rows) - answer["with_shoes"] - answer["not_known"]
    chosen = []
    for shoe in shoes:
        own = linked.get(shoe.key)
        if not own:
            continue
        line = _activity_line(item, own, months, Counter())
        [distance] = _activity_line(item, own, whole, Counter())["values"]
        activities = [0] * len(months.spans)
        for row in own:
            index = months.index(row.day)
            if index is not None:
                activities[index] += 1
        entry = {
            "name": shoe.name,
            "day": shoe.day,
            "number": shoe.number,
            "begin": shoe.begin,
            "end": shoe.end,
            "maximum": shoe.maximum,
            "values": line["values"],
            "activities_by_month": activities,
            "distance": distance,
            "activities": len(own),
            "without_distance": sum(1 for row in own if not _has_value(item, row)),
            "first": date.fromordinal(own[0].day).isoformat(),
            "last": date.fromordinal(own[-1].day).isoformat(),
        }
        chosen.append((own[-1].day, shoe.place, entry))
    chosen.sort(key=lambda found: (-found[0], found[1]))
    answer.update(
        {
            "start": date.fromordinal(months.start).isoformat(),
            "end": date.fromordinal(months.end).isoformat(),
            "periods": [
                {"start": date.fromordinal(first).isoformat(), "end": date.fromordinal(last).isoformat(), "partial": partial}
                for first, last, partial in months.spans
            ],
            "shoes": [entry for _last, _place, entry in chosen],
            "left_out": len(shoes) - len(chosen),
        }
    )
    return answer


__all__ = [
    "GRAINS",
    "LAST_YEARS",
    "CONDITION_SEPARATORS",
    "Conditions",
    "LIST_ITEMS",
    "MAX_ANSWER_BYTES",
    "MAX_CONDITION_TEXT",
    "MAX_CONDITION_WORDS",
    "MAX_DISTANCE_METRES",
    "MAX_LIST_ROWS",
    "MAX_PANELS",
    "MAX_POINTS",
    "MAX_RANGES",
    "MAX_TIME_MINUTES",
    "MAX_TYPES",
    "MAX_TYPE_LENGTH",
    "NO_TYPE",
    "Periods",
    "RANGE_GRAIN",
    "SPREAD_RANGES",
    "activity_list",
    "activity_points",
    "activity_spread",
    "activity_types",
    "auto_grain",
    "chosen_span",
    "condition_counts",
    "condition_words",
    "coverage",
    "default_items",
    "default_types",
    "item_series",
    "period_bounds",
    "point_item",
    "previous_span",
    "shoe_answer",
    "shoe_count",
    "type_name_ok",
    "view_answer",
]
