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
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cached_property
from typing import Any

from ..common.sport import sport_group
from .data import Row, ViewData
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
# A page shows up to six panels, and its answer of six panels at the grain of
# a day over 15 years stays within this size (a test of stage G1).
MAX_PANELS = 6
MAX_ANSWER_BYTES = 4 * 1024 * 1024
# The periods that end on the last day of the output, by their years.
LAST_YEARS = {"10y": 10, "5y": 5, "3y": 3, "1y": 1}
# The type of an activity without activity_type.
NO_TYPE = ""


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
    outside them."""
    if grain != "auto" and grain not in GRAINS:
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
        back = _add_years(date.fromordinal(end), -LAST_YEARS[period]) + timedelta(days=1)
        start = max(back.toordinal(), data.first_day)
    else:
        raise ValueError(f"unknown period: {period}")
    if grain == "auto":
        grain = auto_grain(start, end)
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


def default_types(data: ViewData) -> frozenset[str]:
    """The activity types that the page counts at first."""
    return frozenset(entry["name"] for entry in activity_types(data) if entry["running"])


def _activity_rows(data: ViewData, types: Collection[str] | None) -> list[Row]:
    counted = default_types(data) if types is None else frozenset(types)
    return [row for row in data.rows[ACTIVITIES] if row.marks["type"] in counted]


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
) -> dict[str, Any]:
    """The numbers of one panel: for each line, the value and the count of
    each period, and what was left out. ``types`` are the activity types
    counted by the training and running-form items, the running types when
    None; the other items do not use them."""
    if key not in ITEMS_BY_KEY:
        raise ValueError(f"unknown item: {key}")
    item = ITEMS_BY_KEY[key]
    dataset = DATASETS_BY_NAME[item.dataset]
    left_out: Counter[str] = Counter()
    if item.dataset == ACTIVITIES:
        rows = _activity_rows(data, types)
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


def coverage(data: ViewData, types: Collection[str] | None = None) -> dict[str, dict[str, Any]]:
    """For each item, the months with a value on at least one day, and its
    first and last day with a value: the bars of the item shelf. The training
    and running-form items follow ``types``."""
    activity_rows = _activity_rows(data, types)
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


def default_items(data: ViewData) -> list[str]:
    """The items of the first time, without those that the output has no
    value of."""
    shelf = coverage(data)
    return [key for key in FIRST_ITEMS if shelf[key]["months"]]


def view_answer(
    data: ViewData,
    keys: Collection[str],
    period: str | tuple[date, date] = "all",
    grain: str = "auto",
    types: Collection[str] | None = None,
) -> dict[str, Any]:
    """The numbers of a page: its periods, once, and a panel for each item."""
    periods = period_bounds(data, period, grain)
    if periods is None:
        return {"start": None, "end": None, "grain": None, "periods": [], "panels": []}
    return {
        "start": date.fromordinal(periods.start).isoformat(),
        "end": date.fromordinal(periods.end).isoformat(),
        "grain": periods.grain,
        "periods": [
            {"start": date.fromordinal(first).isoformat(), "end": date.fromordinal(last).isoformat(), "partial": partial}
            for first, last, partial in periods.spans
        ],
        "panels": [item_series(data, key, periods, types) for key in keys],
    }


__all__ = [
    "GRAINS",
    "LAST_YEARS",
    "MAX_ANSWER_BYTES",
    "MAX_PANELS",
    "NO_TYPE",
    "Periods",
    "activity_types",
    "auto_grain",
    "coverage",
    "default_items",
    "default_types",
    "item_series",
    "period_bounds",
    "view_answer",
]
