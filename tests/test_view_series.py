"""The numbers of the view page, from rows written by hand (stage G1)."""

from __future__ import annotations

import json
import math
import re
import time
import unittest
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer.run_all import ACTIVITIES_CSV_COLUMNS
from garmin_running_data_normalizer.view.data import Row, ViewData
from garmin_running_data_normalizer.view.items import (
    ACTIVITIES,
    DATASETS,
    DATASETS_BY_NAME,
    FIRST_ITEMS,
    ITEMS,
    ITEMS_BY_KEY,
    COUNT,
    MAXIMUM,
    PACE,
    SUM,
    TIME_WEIGHTED,
    dataset_fields,
)
from garmin_running_data_normalizer.view import series as series_module
from garmin_running_data_normalizer.view.series import (
    LIST_ITEMS,
    MAX_ANSWER_BYTES,
    MAX_LIST_ROWS,
    MAX_PANELS,
    MAX_POINTS,
    MAX_RANGES,
    SPREAD_RANGES,
    activity_list,
    activity_points,
    activity_spread,
    activity_types,
    auto_grain,
    coverage,
    default_items,
    default_types,
    item_series,
    period_bounds,
    point_item,
    view_answer,
)

ROOT = Path(__file__).resolve().parents[1]


def day(text: str) -> int:
    return date.fromisoformat(text).toordinal()


def activity(
    when: str, kind: str = "running", disagree: tuple[str, ...] = (), moment: str | None = None, **values: float | None
) -> Row:
    fields = dataset_fields(ACTIVITIES)
    marks: dict[str, Any] = {"type": kind}
    if moment is not None:
        marks["datetime"] = moment
    return Row(day(when), {name: values.get(name) for name in fields}, frozenset(disagree), marks)


def daily(
    dataset: str,
    when: str,
    *,
    time: str = "",
    used: bool = True,
    review: bool = False,
    series: tuple[str, ...] | None = None,
    disagree: tuple[str, ...] = (),
    **values: float | None,
) -> Row:
    spec = DATASETS_BY_NAME[dataset]
    marks: dict[str, Any] = {}
    if dataset == "sleep_daily":
        marks.update(used=used, review=review)
    if spec.observed:
        marks["time"] = time
    if spec.series:
        marks["series"] = series or ("",) * len(spec.series)
    fields = dataset_fields(dataset)
    return Row(day(when), {name: values.get(name) for name in fields}, frozenset(disagree), marks)


def view_data(
    rows: list[tuple[str, Row]],
    *,
    no_date: dict[str, int] | None = None,
    after_today: dict[str, int] | None = None,
) -> ViewData:
    by_name: dict[str, list[Row]] = {spec.name: [] for spec in DATASETS}
    for name, row in rows:
        by_name[name].append(row)
    kept = {
        name: tuple(sorted(found, key=lambda row: (row.day, row.marks.get("time", ""))))
        for name, found in by_name.items()
    }
    days = [row.day for found in kept.values() for row in found]
    return ViewData(
        version="test",
        timezone="Asia/Tokyo",
        today=day("2030-01-01"),
        rows=kept,
        no_date={spec.name: (no_date or {}).get(spec.name, 0) for spec in DATASETS},
        after_today={spec.name: (after_today or {}).get(spec.name, 0) for spec in DATASETS},
        first_day=min(days) if days else None,
        last_day=max(days) if days else None,
    )


def uds(when: str, **values: float | None) -> tuple[str, Row]:
    return "uds_daily", daily("uds_daily", when, **values)


def act(
    when: str, kind: str = "running", disagree: tuple[str, ...] = (), moment: str | None = None, **values: float | None
) -> tuple[str, Row]:
    return ACTIVITIES, activity(when, kind, disagree, moment, **values)


def spans(data: ViewData, period: Any = "all", grain: str = "auto") -> list[tuple[str, str, bool]]:
    periods = period_bounds(data, period, grain)
    assert periods is not None
    return [
        (date.fromordinal(first).isoformat(), date.fromordinal(last).isoformat(), partial)
        for first, last, partial in periods.spans
    ]


def panel(data: ViewData, key: str, period: Any = "all", grain: str = "auto", types: Any = None) -> dict[str, Any]:
    periods = period_bounds(data, period, grain)
    assert periods is not None
    return item_series(data, key, periods, types)


class PeriodTest(unittest.TestCase):
    def test_weeks_start_on_monday_and_cut_periods_are_partial(self) -> None:
        # 7 January 2024 is a Sunday, and 24 January a Wednesday.
        data = view_data([uds("2024-01-07", resting_heart_rate=50), uds("2024-01-24", resting_heart_rate=51)])
        self.assertEqual(
            spans(data, grain="week"),
            [
                ("2024-01-07", "2024-01-07", True),
                ("2024-01-08", "2024-01-14", False),
                ("2024-01-15", "2024-01-21", False),
                ("2024-01-22", "2024-01-24", True),
            ],
        )

    def test_months_and_years_follow_the_calendar(self) -> None:
        data = view_data([uds("2023-12-31", steps=1), uds("2024-02-29", steps=2)])
        self.assertEqual(
            spans(data, grain="month"),
            [
                ("2023-12-31", "2023-12-31", True),
                ("2024-01-01", "2024-01-31", False),
                ("2024-02-01", "2024-02-29", False),
            ],
        )
        self.assertEqual(
            spans(data, grain="year"),
            [("2023-12-31", "2023-12-31", True), ("2024-01-01", "2024-02-29", True)],
        )
        self.assertEqual(spans(data, grain="day")[0], ("2023-12-31", "2023-12-31", False))
        self.assertEqual(len(spans(data, grain="day")), 61)

    def test_the_last_years_count_back_from_the_last_day_of_the_output(self) -> None:
        data = view_data([uds("2020-03-01", steps=1), uds("2024-02-29", steps=2)])
        bounds = {
            name: (date.fromordinal(periods.start).isoformat(), date.fromordinal(periods.end).isoformat(), periods.grain)
            for name in ("all", "10y", "5y", "3y", "1y")
            if (periods := period_bounds(data, name)) is not None
        }
        self.assertEqual(
            bounds,
            {
                "all": ("2020-03-01", "2024-02-29", "month"),
                # Cut to the first day of the output.
                "10y": ("2020-03-01", "2024-02-29", "month"),
                "5y": ("2020-03-01", "2024-02-29", "month"),
                # Three years before 29 February 2024 is 28 February 2021.
                "3y": ("2021-03-01", "2024-02-29", "week"),
                "1y": ("2023-03-01", "2024-02-29", "day"),
            },
        )

    def test_a_range_is_cut_to_the_days_of_the_output(self) -> None:
        data = view_data([uds("2020-03-01", steps=1), uds("2024-02-29", steps=2)])
        periods = period_bounds(data, (date(2019, 1, 1), date(2020, 3, 31)), "month")
        assert periods is not None
        self.assertEqual((date.fromordinal(periods.start), date.fromordinal(periods.end)), (date(2020, 3, 1), date(2020, 3, 31)))
        self.assertIsNone(period_bounds(data, (date(2010, 1, 1), date(2015, 1, 1))))
        with self.assertRaises(ValueError):
            period_bounds(data, (date(2021, 1, 2), date(2021, 1, 1)))
        self.assertIsNone(period_bounds(view_data([]), "all"))

    def test_auto_groups_by_the_length_of_the_period(self) -> None:
        start = day("2023-01-01")
        cases = {
            "2023-12-31": "day",
            "2024-01-01": "week",
            "2025-12-31": "week",
            "2026-01-01": "month",
        }
        for end, grain in cases.items():
            with self.subTest(end=end):
                self.assertEqual(auto_grain(start, day(end)), grain)

    def test_unknown_periods_groupings_and_items_are_refused(self) -> None:
        data = view_data([uds("2024-01-01", steps=1)])
        with self.assertRaises(ValueError):
            period_bounds(data, "2y")
        with self.assertRaises(ValueError):
            period_bounds(data, "all", "fortnight")
        with self.assertRaises(ValueError):
            period_bounds(data, "all", "ranges")
        periods = period_bounds(data)
        assert periods is not None
        with self.assertRaises(ValueError):
            item_series(data, "nothing", periods)


class RangeTest(unittest.TestCase):
    """The whole period as one period (stage M2 of v2.2.0): the value of a span
    that the calendar does not give, such as the weeks before a race."""

    def test_the_whole_range_is_one_period_cut_to_the_output(self) -> None:
        data = view_data([uds("2024-01-07", steps=10), uds("2024-01-24", steps=20)])
        # The days of the output, as one period, without the mark of a cut one.
        self.assertEqual(spans(data, (date(2024, 1, 1), date(2024, 2, 10)), "range"), [("2024-01-07", "2024-01-24", False)])
        self.assertEqual(spans(data, (date(2024, 1, 9), date(2024, 1, 16)), "range"), [("2024-01-09", "2024-01-16", False)])
        self.assertEqual(spans(data, "all", "range"), [("2024-01-07", "2024-01-24", False)])
        periods = period_bounds(data, (date(2024, 1, 9), date(2024, 1, 16)), "range")
        assert periods is not None
        self.assertEqual(periods.grain, "range")
        self.assertIsNone(period_bounds(data, (date(2010, 1, 1), date(2015, 1, 1)), "range"))

    def test_the_whole_range_is_counted_as_its_days_are(self) -> None:
        data = view_data(
            [
                act("2024-03-04", distance_m=10000, duration_sec=3000, avg_hr=150, max_hr=170),
                act("2024-03-06", distance_m=5000, duration_sec=1800, avg_hr=160, max_hr=180),
                act("2024-03-13", distance_m=8000, duration_sec=2400, avg_hr=155, max_hr=175),
                uds("2024-03-05", resting_heart_rate=50),
                uds("2024-03-12", resting_heart_rate=54),
            ]
        )
        span = (date(2024, 3, 4), date(2024, 3, 17))
        [total] = panel(data, "dist", span, "range")["lines"]
        self.assertEqual(total["values"], [23000.0])
        self.assertEqual(total["counts"], [3])
        self.assertEqual(sum(value for value in panel(data, "dist", span, "day")["lines"][0]["values"] if value), 23000.0)
        self.assertAlmostEqual(panel(data, "pace", span, "range")["lines"][0]["values"][0], 7200 / 23000)
        self.assertAlmostEqual(panel(data, "hr", span, "range")["lines"][0]["values"][0], (150 * 3000 + 160 * 1800 + 155 * 2400) / 7200)
        self.assertEqual(panel(data, "mx", span, "range")["lines"][0]["values"], [180.0])
        self.assertEqual(panel(data, "rhr", span, "range")["lines"][0]["values"], [52.0])
        # The same as by the week, where the two weeks add up.
        weeks = panel(data, "dist", span, "week")["lines"][0]["values"]
        self.assertEqual(sum(value for value in weeks if value), 23000.0)

    def test_the_whole_range_counts_each_row_by_its_own_weight_and_value(self) -> None:
        # Codex's review of the plan of M2: the right values come from the
        # rows, with distances, times, and records that differ, and with
        # activities and days without a value; the values and counts of the
        # weeks cannot give the value of an average.
        acute = "acute_training_load_daily"
        data = view_data(
            [
                act("2024-03-04", distance_m=12000, duration_sec=4000, avg_hr=150),
                # Without a heart rate: its distance and time count.
                act("2024-03-05", distance_m=3000, duration_sec=1200),
                # Without a distance: no pace, and its heart rate counts by its time.
                act("2024-03-07", duration_sec=600, avg_hr=120),
                act("2024-03-14", distance_m=6000, duration_sec=1800, avg_hr=160),
                uds("2024-03-06", resting_heart_rate=48),
                uds("2024-03-08"),
                uds("2024-03-13", resting_heart_rate=50),
                uds("2024-03-15", resting_heart_rate=55),
                # Two records on one day: each record counts.
                (acute, daily(acute, "2024-03-05", time="07:00", daily_training_load_acute=300)),
                (acute, daily(acute, "2024-03-05", time="19:00", daily_training_load_acute=330)),
                (acute, daily(acute, "2024-03-12", time="07:00", daily_training_load_acute=390)),
            ]
        )
        span = (date(2024, 3, 4), date(2024, 3, 17))
        [total] = panel(data, "dist", span, "range")["lines"]
        self.assertEqual((total["values"], total["counts"]), ([21000.0], [3]))
        [pace] = panel(data, "pace", span, "range")["lines"]
        self.assertEqual(pace["counts"], [3])
        self.assertAlmostEqual(pace["values"][0], (4000 + 1200 + 1800) / (12000 + 3000 + 6000))
        [hr] = panel(data, "hr", span, "range")["lines"]
        self.assertEqual(hr["counts"], [3])
        self.assertAlmostEqual(hr["values"][0], (150 * 4000 + 120 * 600 + 160 * 1800) / (4000 + 600 + 1800))
        [weeks] = panel(data, "hr", span, "week")["lines"]
        by_counts = sum(value * count for value, count in zip(weeks["values"], weeks["counts"])) / sum(weeks["counts"])
        self.assertNotAlmostEqual(by_counts, hr["values"][0])
        rhr = panel(data, "rhr", span, "range")
        self.assertEqual((rhr["lines"][0]["values"], rhr["lines"][0]["counts"]), ([51.0], [3]))
        self.assertEqual(rhr["left_out"]["no_value"], 1)
        observed = panel(data, "acute", span, "range")
        self.assertEqual((observed["lines"][0]["values"], observed["lines"][0]["counts"]), ([340.0], [3]))
        self.assertNotIn("points", observed["lines"][0])
        self.assertEqual(observed["left_out"]["days_with_several_records"], 1)
        # A range whose activities have no value is empty; one without
        # activities, between the first and the last, is 0.
        self.assertEqual(panel(data, "load", span, "range")["lines"][0]["values"], [None])
        self.assertEqual(panel(data, "dist", (date(2024, 3, 8), date(2024, 3, 13)), "range")["lines"][0]["values"], [0.0])


def value_of(item: Any, rows: list[dict[str, Any]]) -> tuple[float | None, int]:
    """The value of a panel and its count, made again from the rows of its list."""
    if item.kind == COUNT:
        return float(len(rows)), len(rows)
    values = [row["values"][item.key] for row in rows]
    times = [row["values"]["time"] for row in rows]
    if item.kind == PACE:
        pairs = [(time, distance) for time, distance in zip(times, (row["values"]["dist"] for row in rows)) if time and time > 0 and distance and distance > 0]
        return (sum(time for time, _ in pairs) / sum(distance for _, distance in pairs) if pairs else None), len(pairs)
    if item.kind == TIME_WEIGHTED:
        pairs = [(value, time) for value, time in zip(values, times) if value is not None and time is not None and time > 0]
        return (sum(value * time for value, time in pairs) / sum(time for _, time in pairs) if pairs else None), len(pairs)
    present = [value for value in values if value is not None]
    if item.kind == MAXIMUM:
        return (max(present) if present else None), len(present)
    return (sum(present) if present else None), len(present)


class ActivityListTest(unittest.TestCase):
    """The activities of one period of a panel (stage M3 of v2.2.0): chosen as
    the panel chooses them, with the value of the panel there."""

    def data(self) -> ViewData:
        return view_data(
            [
                # A week of a distance of 0, a time of 0, and a time below 0,
                # which no pace and no weight by time counts.
                act("2024-02-27", moment="2024-02-27T06:00:00+09:00", distance_m=0, duration_sec=900, avg_hr=140, max_hr=150),
                act("2024-02-28", moment="2024-02-28T06:00:00+09:00", distance_m=5000, duration_sec=0, avg_hr=145, max_hr=160),
                act("2024-02-29", moment="2024-02-29T06:00:00+08:00", distance_m=3000, duration_sec=-60, avg_hr=150),
                act("2024-03-04", moment="2024-03-04T06:30:00+09:00", distance_m=10000, duration_sec=3000, avg_hr=150, max_hr=170),
                act("2024-03-04", moment="2024-03-04T18:05:00+09:00", distance_m=4000, duration_sec=1500),
                act("2024-03-06", "cycling", moment="2024-03-06T07:00:00+09:00", distance_m=30000, duration_sec=4000, avg_hr=120),
                act("2024-03-07", moment="2024-03-07T06:40:00+09:00", duration_sec=600, avg_hr=125),
                act("2024-03-12", distance_m=8000, duration_sec=2400, avg_hr=155, max_hr=176, fit_total_ascent_m=40),
                uds("2024-03-05", resting_heart_rate=50),
            ]
        )

    def test_the_rows_of_a_period_give_the_value_of_its_panel(self) -> None:
        # Codex's review of the plan of M3: the value of the panel and its
        # count come again from the rows of the list, by the rules of the kind
        # of each item (the weights, the pace of a positive distance and time,
        # the maximum), for every week and every item of the activities.
        data = self.data()
        weeks = period_bounds(data, "all", "week")
        assert weeks is not None
        for first, last, _partial in weeks.spans:
            span = (date.fromordinal(first), date.fromordinal(last))
            for item in (entry for entry in ITEMS if entry.dataset == ACTIVITIES):
                with self.subTest(week=span[0].isoformat(), item=item.key):
                    answer = activity_list(data, item.key, span)
                    [line] = panel(data, item.key, span, "range")["lines"]
                    self.assertEqual(answer["value"], {"value": line["values"][0], "count": line["counts"][0]})
                    value, count = value_of(item, answer["rows"])
                    self.assertEqual(count, line["counts"][0])
                    if count:
                        self.assertAlmostEqual(value, line["values"][0])
                    else:
                        # None counted: 0 between the first and the last
                        # activity for a total, or no value.
                        self.assertIn(line["values"][0], (None, 0.0))
        # The week of 4 March: three running activities, the cycling left out.
        answer = activity_list(data, "dist", (date(2024, 3, 4), date(2024, 3, 10)))
        self.assertEqual(answer["total"], 3)
        self.assertEqual([row["datetime"] for row in answer["rows"]], ["2024-03-04T06:30:00+09:00", "2024-03-04T18:05:00+09:00", "2024-03-07T06:40:00+09:00"])
        self.assertEqual(answer["rows"][2]["values"], {"dist": None, "time": 600.0, "pace": None, "hr": 125.0, "mx": None, "cad": None, "asc": None})
        self.assertAlmostEqual(answer["rows"][0]["values"]["pace"], 0.3)
        self.assertEqual(answer["value"], {"value": 14000.0, "count": 2})
        # The week of 26 February: no pace of a distance or a time of 0 or
        # below; the weight by time counts the activity of 900 seconds only.
        week = activity_list(data, "pace", (date(2024, 2, 26), date(2024, 3, 3)))
        self.assertEqual([row["values"]["pace"] for row in week["rows"]], [None, None, None])
        self.assertEqual(week["value"], {"value": None, "count": 0})
        self.assertEqual(activity_list(data, "hr", (date(2024, 2, 26), date(2024, 3, 3)))["value"], {"value": 140.0, "count": 1})
        self.assertEqual(activity_list(data, "mx", (date(2024, 2, 26), date(2024, 3, 3)))["value"], {"value": 160.0, "count": 2})

    def test_the_page_opens_the_list_from_the_panels_of_these_items(self) -> None:
        # The page opens the list from the panels of the training and the
        # running form (view_flow.mjs listOpens), and writes the columns of
        # the server up to its limit: the same items, columns, and limit.
        for item in ITEMS:
            with self.subTest(item=item.key):
                self.assertEqual(item.group in ("act", "fit"), item.dataset == ACTIVITIES)
        script = (Path(series_module.__file__).parent.parent / "gui" / "static" / "view_flow.mjs").read_text(encoding="utf-8")
        found = re.search(r"export const LIST_ITEMS = \[([^\]]*)\];", script)
        assert found is not None
        self.assertEqual(tuple(json.loads(f"[{found.group(1)}]")), LIST_ITEMS)
        self.assertIn(f"export const MAX_LIST_ROWS = {MAX_LIST_ROWS};", script)

    def test_the_list_counts_the_types_counted(self) -> None:
        answer = activity_list(self.data(), "dist", (date(2024, 3, 4), date(2024, 3, 10)), ["cycling"])
        self.assertEqual([(row["type"], row["day"]) for row in answer["rows"]], [("cycling", "2024-03-06")])
        self.assertEqual(answer["value"], {"value": 30000.0, "count": 1})

    def test_a_period_is_cut_to_the_output_and_has_no_rows_outside_it(self) -> None:
        data = self.data()
        answer = activity_list(data, "dist", (date(2024, 3, 11), date(2024, 3, 17)))
        # The output ends on 12 March: the period ends there too.
        self.assertEqual((answer["start"], answer["end"], answer["total"]), ("2024-03-11", "2024-03-12", 1))
        self.assertIsNone(answer["rows"][0]["datetime"])
        outside = activity_list(data, "dist", (date(2020, 1, 1), date(2020, 1, 31)))
        self.assertEqual(outside, {"start": None, "end": None, "total": 0, "rows": [], "limit": MAX_LIST_ROWS, "value": None})
        # A week without activities between the first and the last: none, and 0.
        empty = view_data([act("2024-01-01", distance_m=1000, duration_sec=300), act("2024-01-20", distance_m=1000, duration_sec=300)])
        answer = activity_list(empty, "dist", (date(2024, 1, 8), date(2024, 1, 14)))
        self.assertEqual((answer["total"], answer["rows"], answer["value"]), (0, [], {"value": 0.0, "count": 0}))

    def test_a_period_of_more_rows_than_the_limit_gives_their_number(self) -> None:
        self.assertEqual(MAX_LIST_ROWS, 500)
        with patch.object(series_module, "MAX_LIST_ROWS", 2):
            answer = activity_list(self.data(), "time", (date(2024, 3, 4), date(2024, 3, 10)))
        self.assertEqual((answer["total"], answer["rows"], answer["limit"]), (3, None, 2))
        self.assertEqual(answer["value"], {"value": 5100.0, "count": 3})
        # As many rows as the limit are listed.
        with patch.object(series_module, "MAX_LIST_ROWS", 3):
            answer = activity_list(self.data(), "time", (date(2024, 3, 4), date(2024, 3, 10)))
        self.assertEqual((answer["total"], len(answer["rows"]), answer["limit"]), (3, 3, 3))

    def test_an_item_of_the_days_has_no_list(self) -> None:
        for key in ("rhr", "vo2", "sleep", "nope"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    activity_list(self.data(), key, (date(2024, 3, 4), date(2024, 3, 10)))


class ActivityPointsTest(unittest.TestCase):
    """Two items of the activities plotted against each other (stage O1 of
    v2.2.0): the activities of the list of a period with a value of both,
    the newest up to a limit, in the order of the time as it shows."""

    def data(self) -> ViewData:
        return ActivityListTest().data()

    def test_the_points_are_the_rows_of_the_list_with_both_values(self) -> None:
        # The numbers are made once (the checker's review of the plan of O1):
        # for every week and every two items, the points are the rows of the
        # list of the same days and types that have a value of both.
        data = self.data()
        keys = [item.key for item in ITEMS if point_item(item.key)]
        self.assertEqual(keys, [item.key for item in ITEMS if item.dataset == ACTIVITIES and item.kind != COUNT])
        weeks = period_bounds(data, "all", "week")
        assert weeks is not None
        for first, last, _partial in weeks.spans:
            span = (date.fromordinal(first), date.fromordinal(last))
            lists = {key: activity_list(data, key, span) for key in keys}
            for x in keys:
                for y in keys:
                    if x == y:
                        continue
                    with self.subTest(week=span[0].isoformat(), x=x, y=y):
                        answer = activity_points(data, x, y, span)
                        rows = [
                            {"day": a["day"], "datetime": a["datetime"], "type": a["type"], "values": {x: a["values"][x], y: b["values"][y]}}
                            for a, b in zip(lists[x]["rows"], lists[y]["rows"])
                        ]
                        expected = [row for row in rows if None not in row["values"].values()]
                        self.assertEqual(sorted(map(json.dumps, answer["points"])), sorted(map(json.dumps, expected)))
                        self.assertEqual(answer["total"], lists[x]["total"])
                        self.assertEqual(answer["with_values"], len(expected))
                        self.assertEqual(answer["total"], answer["with_values"] + answer["missing"])
                        self.assertEqual((answer["start"], answer["end"]), (lists[x]["start"], lists[x]["end"]))
        # The week of 4 March: the distance and the pace of two activities;
        # the third has no distance.
        answer = activity_points(data, "dist", "pace", (date(2024, 3, 4), date(2024, 3, 10)))
        self.assertEqual((answer["total"], answer["with_values"], answer["missing"], answer["limit"]), (3, 2, 1, MAX_POINTS))
        self.assertEqual([point["values"]["dist"] for point in answer["points"]], [10000.0, 4000.0])
        self.assertAlmostEqual(answer["points"][0]["values"]["pace"], 0.3)

    def test_the_points_are_in_the_order_of_the_time_as_it_shows(self) -> None:
        # As the list orders them (the checker's M3-1): the date and the time
        # of the day before the offset, the day where the time cannot be
        # read, and then the order of the output.
        data = view_data(
            [
                act("2024-03-04", moment="2024-03-04T07:00:00+09:00", distance_m=5000, duration_sec=1500),
                act("2024-03-04", moment="2024-03-04T06:30:00+08:00", distance_m=6000, duration_sec=1800),
                act("2024-03-04", distance_m=7000, duration_sec=2100),
                act("2024-03-04", moment="not a time", distance_m=8000, duration_sec=2400),
                act("2024-03-03", moment="2024-03-03T21:00:00+09:00", distance_m=9000, duration_sec=2700),
                act("2024-03-04", moment="2024-03-04T07:00:00+09:00", distance_m=4000, duration_sec=1200),
            ]
        )
        answer = activity_points(data, "dist", "time")
        self.assertEqual([point["values"]["dist"] for point in answer["points"]], [9000.0, 7000.0, 8000.0, 6000.0, 5000.0, 4000.0])

    def test_the_newest_points_up_to_the_limit(self) -> None:
        self.assertEqual(MAX_POINTS, 5000)
        data = self.data()
        everything = activity_points(data, "dist", "time")
        with patch.object(series_module, "MAX_POINTS", 2):
            answer = activity_points(data, "dist", "time")
        self.assertEqual(answer["points"], everything["points"][-2:])
        self.assertEqual((answer["total"], answer["with_values"], answer["missing"], answer["limit"]), (everything["total"], everything["with_values"], everything["missing"], 2))
        self.assertGreater(everything["with_values"], 2)

    def test_a_pace_that_is_not_a_finite_number_has_no_value(self) -> None:
        # Codex's review of the plan of O1: a positive time over a tiny
        # positive distance is not finite; the activity has no pace, in the
        # points and in the list, and the answer is JSON without NaN or
        # Infinity.
        data = view_data(
            [
                act("2024-03-04", moment="2024-03-04T06:00:00+09:00", distance_m=1e-300, duration_sec=1e300, avg_hr=150),
                act("2024-03-05", moment="2024-03-05T06:00:00+09:00", distance_m=10000, duration_sec=3000, avg_hr=140),
            ]
        )
        answer = activity_points(data, "pace", "hr")
        self.assertEqual((answer["total"], answer["with_values"], answer["missing"]), (2, 1, 1))
        self.assertEqual(answer["points"][0]["day"], "2024-03-05")
        json.dumps(answer, allow_nan=False)
        listed = activity_list(data, "pace", (date(2024, 3, 4), date(2024, 3, 10)))
        self.assertEqual([row["values"]["pace"] for row in listed["rows"]], [None, 0.3])
        # The list of a period is JSON without them too (the checker's review
        # of the decisions of O1).
        json.dumps(listed, allow_nan=False)

    def test_the_points_count_the_types_and_the_days_of_the_period(self) -> None:
        data = self.data()
        cycling = activity_points(data, "dist", "hr", "all", ["cycling"])
        self.assertEqual([(point["type"], point["day"]) for point in cycling["points"]], [("cycling", "2024-03-06")])
        # The last year of the output, which ends on 12 March 2024, cut to
        # its first day.
        year = activity_points(data, "dist", "time", "1y")
        self.assertEqual((year["start"], year["end"]), ("2024-02-27", "2024-03-12"))
        outside = activity_points(data, "dist", "time", (date(2020, 1, 1), date(2020, 1, 31)))
        self.assertEqual(outside, {"start": None, "end": None, "total": 0, "with_values": 0, "missing": 0, "limit": MAX_POINTS, "points": []})
        none = activity_points(data, "dist", "time", "all", [])
        self.assertEqual((none["total"], none["points"]), (0, []))

    def test_the_page_knows_the_limit_and_the_items_of_the_points(self) -> None:
        # The page says the limit of the server and takes its items, but the
        # count, as point_item does.
        script = (Path(series_module.__file__).parent.parent / "gui" / "static" / "view_flow.mjs").read_text(encoding="utf-8")
        self.assertIn(f"export const MAX_POINTS = {MAX_POINTS};", script)
        self.assertIn('return typeof item?.key === "string" && isActivityItem(item) && item.kind !== "count";', script)

    def test_only_two_different_items_of_one_activity_are_plotted(self) -> None:
        for x, y in (("dist", "dist"), ("count", "dist"), ("dist", "count"), ("rhr", "dist"), ("dist", "vo2"), ("nope", "dist"), (None, "dist")):
            with self.subTest(x=x, y=y):
                with self.assertRaises(ValueError):
                    activity_points(self.data(), x, y)  # type: ignore[arg-type]


class ActivitySpreadTest(unittest.TestCase):
    """The distribution of one item of the activities (stage P1 of v2.2.0):
    the activities of the points with a value of the item, counted in the
    ranges of its width from their values as the output writes them, not
    rounded, up to MAX_RANGES ranges."""

    def data(self) -> ViewData:
        return ActivityListTest().data()

    def ranges(self, key: str, *rows: dict[str, float]) -> dict[str, Any]:
        data = view_data([act("2024-03-04", moment="2024-03-04T06:00:00+09:00", **values) for values in rows])
        answer = activity_spread(data, key)
        json.dumps(answer, allow_nan=False)
        return answer

    def test_the_ranges_count_the_rows_of_the_list_with_a_value(self) -> None:
        # The same activities as the list and the points (the checker's review
        # of the plan of O1): for every week and every item, the ranges count
        # the rows of the list of the same days that have a value of the item,
        # each in the range of its value as the output writes it.
        data = self.data()
        keys = [item.key for item in ITEMS if point_item(item.key)]
        self.assertEqual(sorted(SPREAD_RANGES), sorted(keys))
        weeks = period_bounds(data, "all", "week")
        assert weeks is not None
        for first, last, _partial in weeks.spans:
            span = (date.fromordinal(first), date.fromordinal(last))
            for key in keys:
                with self.subTest(week=span[0].isoformat(), item=key):
                    listed = activity_list(data, key, span)
                    answer = activity_spread(data, key, span)
                    json.dumps(answer, allow_nan=False)
                    # The rows of the list are those of the output in its order.
                    rows = [row for row in data.rows[ACTIVITIES] if span[0].toordinal() <= row.day <= span[1].toordinal() and row.marks["type"] == "running"]
                    self.assertEqual(len(rows), len(listed["rows"]))
                    with_value = [row for row, entry in zip(rows, listed["rows"]) if entry["values"][key] is not None]
                    scale, width = SPREAD_RANGES[key]
                    expected: dict[int, int] = {}
                    for row in with_value:
                        if key == "pace":
                            exact = Fraction(Decimal(repr(row.values["duration_sec"]))) * scale / Fraction(Decimal(repr(row.values["distance_m"])))
                        else:
                            exact = Fraction(Decimal(repr(row.values[ITEMS_BY_KEY[key].field]))) * scale
                        number = math.floor(exact / width)
                        expected[number] = expected.get(number, 0) + 1
                    self.assertEqual((answer["total"], answer["with_values"]), (listed["total"], len(with_value)))
                    self.assertEqual(answer["total"], answer["with_values"] + answer["missing"])
                    self.assertEqual((answer["start"], answer["end"]), (listed["start"], listed["end"]))
                    self.assertEqual((answer["scale"], answer["width"], answer["widened"], answer["limit"]), (scale, width, False, MAX_RANGES))
                    if expected:
                        self.assertEqual(answer["first"], min(expected))
                        self.assertEqual(answer["counts"], [expected.get(number, 0) for number in range(min(expected), max(expected) + 1)])
                    else:
                        self.assertEqual((answer["first"], answer["counts"]), (None, []))
        # A time below 0 is counted as it is, as the list writes it (Codex's
        # review of the plan of P1): -60 seconds are in the range of -10 to 0
        # minutes, 0 in that of 0 to 10, and 900 in that of 10 to 20.
        answer = activity_spread(data, "time", (date(2024, 2, 26), date(2024, 3, 3)))
        self.assertEqual((answer["first"], answer["counts"]), (-1, [1, 1, 1]))

    def test_the_values_are_not_rounded_nor_moved_by_a_division_of_floating_numbers(self) -> None:
        # The Human maintainer, 2026-10-30: the values as they are, so that
        # "10 km or more and less than 11 km" says the truth of each; and the
        # pace by its time times 1000 over its distance, which a division of
        # floating numbers moves to the range below (the checker's and
        # Codex's reviews of the plan of P1).
        cases = (
            ("dist", {"distance_m": 10999.6}, 10),
            ("dist", {"distance_m": 11000.0}, 11),
            ("time", {"duration_sec": 600.0}, 1),
            ("pace", {"distance_m": 1007, "duration_sec": 342.38}, 34),
            ("pace", {"distance_m": 10000, "duration_sec": 5095}, 50),
            ("pace", {"distance_m": 10000, "duration_sec": 3100}, 31),
            ("cad", {"avg_run_cadence": 174.6}, 34),
            ("bal", {"fit_avg_stance_time_balance_percent": 49.95}, 99),
            ("sl", {"fit_avg_step_length_mm": 1249.9}, 24),
        )
        for key, values, number in cases:
            with self.subTest(item=key, values=values):
                answer = self.ranges(key, values)
                self.assertEqual((answer["first"], answer["counts"], answer["with_values"]), (number, [1], 1))
        # The case of the pace is one that a floating division moves: 342.38
        # seconds over 1007 metres are 340 seconds a kilometre exactly.
        self.assertEqual(math.floor(342.38 / 1007 * 1000 / 10), 33)

    def test_the_ranges_are_widened_by_steps_up_to_the_limit(self) -> None:
        self.assertEqual(MAX_RANGES, 200)
        # 200 ranges are not widened; 201 are, by the first step that is
        # enough, and the counts are those of the wider width.
        exact = self.ranges("dist", {"distance_m": 500}, {"distance_m": 199500})
        self.assertEqual((exact["width"], exact["widened"], exact["first"], len(exact["counts"])), (1000, False, 0, 200))
        self.assertEqual((exact["counts"][0], exact["counts"][-1], sum(exact["counts"])), (1, 1, 2))
        more = self.ranges("dist", {"distance_m": 500}, {"distance_m": 200500}, {"distance_m": 1999})
        self.assertEqual((more["width"], more["widened"], more["first"], len(more["counts"])), (2000, True, 0, 101))
        self.assertEqual((more["counts"][0], more["counts"][-1], sum(more["counts"])), (2, 1, 3))
        # The ranges from -1 m and 199,000 m are 201 (Codex's review of the
        # plan of P1): their number is that of the last range and the first,
        # not of the span of the values.
        below = self.ranges("dist", {"distance_m": -1}, {"distance_m": 199000})
        self.assertEqual((below["width"], below["first"], len(below["counts"])), (2000, -1, 101))
        # The ranges 1 and 400 take 5 times the width: 2 times would leave the
        # ranges 0 to 200, which are 201, though the values span 399 ranges.
        edge = self.ranges("dist", {"distance_m": 1000}, {"distance_m": 400000})
        self.assertEqual((edge["width"], edge["first"], len(edge["counts"])), (5000, 0, 81))
        # 601 ranges take 5 times the width: 2 times leave 301.
        five = self.ranges("dist", {"distance_m": 0}, {"distance_m": 600000})
        self.assertEqual((five["width"], five["first"], len(five["counts"])), (5000, 0, 121))
        # Taken together, the counts are those of the wider width counted again.
        values = [-7000, -1, 0, 999, 1000, 4999, 5000, 149999, 150000, 1000001]
        answer = self.ranges("dist", *({"distance_m": value} for value in values))
        wide = answer["width"]
        again: dict[int, int] = {}
        for value in values:
            again[value // wide] = again.get(value // wide, 0) + 1
        self.assertTrue(answer["widened"])
        self.assertEqual(answer["counts"], [again.get(number, 0) for number in range(min(again), max(again) + 1)])

    def test_very_large_values_have_their_ranges_at_once(self) -> None:
        # The checker's review of the plan of P1: a whole number of 298 digits
        # and more, at once, and widened until the ranges are 200 at most.
        started = time.perf_counter()
        distance = self.ranges("dist", {"distance_m": 1e300}, {"distance_m": 10000})
        pace = self.ranges("pace", {"distance_m": 0.001, "duration_sec": 1e300}, {"distance_m": 10000, "duration_sec": 3000})
        self.assertLess(time.perf_counter() - started, 2)
        for answer in (distance, pace):
            self.assertTrue(answer["widened"])
            self.assertLessEqual(len(answer["counts"]), MAX_RANGES)
            self.assertEqual(sum(answer["counts"]), 2)
        # The last range holds 1e300 m: its right end is past it.
        self.assertGreater((distance["first"] + len(distance["counts"])) * distance["width"], 10**300)

    def test_a_pace_that_is_not_a_finite_number_has_no_range(self) -> None:
        # As in the points and the list (Codex's review of the plan of P1):
        # whether an activity has a value is that of _list_value.
        data = view_data(
            [
                act("2024-03-04", moment="2024-03-04T06:00:00+09:00", distance_m=1e-300, duration_sec=1e300),
                act("2024-03-05", moment="2024-03-05T06:00:00+09:00", distance_m=10000, duration_sec=3000),
            ]
        )
        answer = activity_spread(data, "pace")
        self.assertEqual((answer["total"], answer["with_values"], answer["missing"], answer["first"], answer["counts"]), (2, 1, 1, 30, [1]))
        json.dumps(answer, allow_nan=False)

    def test_the_ranges_count_the_types_and_the_days_of_the_period(self) -> None:
        data = self.data()
        cycling = activity_spread(data, "dist", "all", ["cycling"])
        self.assertEqual((cycling["total"], cycling["first"], cycling["counts"]), (1, 30, [1]))
        year = activity_spread(data, "dist", "1y")
        self.assertEqual((year["start"], year["end"]), ("2024-02-27", "2024-03-12"))
        outside = activity_spread(data, "dist", (date(2020, 1, 1), date(2020, 1, 31)))
        self.assertEqual(
            outside,
            {"start": None, "end": None, "total": 0, "with_values": 0, "missing": 0, "limit": MAX_RANGES, "scale": 1, "width": 1000, "widened": False, "first": None, "counts": []},
        )
        none = activity_spread(data, "dist", "all", [])
        self.assertEqual((none["total"], none["counts"]), (0, []))

    def test_every_item_has_the_width_of_its_ranges(self) -> None:
        # OP0 of v2.2.0: 1 km, 10 minutes, 10 seconds a kilometre, 5 bpm, 5
        # steps, 10 W, 10 of the load, 10 m, 0.5 cm, 10 ms, 1 %, 0.5 %, 0.5 %,
        # and 5 cm, in the units of the output.
        widths = {key: Fraction(width, scale) for key, (scale, width) in SPREAD_RANGES.items()}
        self.assertEqual(
            widths,
            {
                "dist": 1000, "time": 600, "pace": Fraction(1, 100), "hr": 5, "mx": 5, "cad": 5, "pow": 10, "load": 10,
                "asc": 10, "vo": 5, "gct": 10, "gctp": 1, "bal": Fraction(1, 2), "vr": Fraction(1, 2), "sl": 50,
            },
        )
        for key, (scale, width) in SPREAD_RANGES.items():
            with self.subTest(item=key):
                self.assertTrue(type(scale) is int and type(width) is int and scale > 0 and width > 0)

    def test_only_an_item_of_one_activity_has_a_distribution(self) -> None:
        for key in ("count", "rhr", "vo2", "nope", None):
            with self.subTest(item=key):
                with self.assertRaises(ValueError):
                    activity_spread(self.data(), key)  # type: ignore[arg-type]


class TotalTest(unittest.TestCase):
    def data(self) -> ViewData:
        return view_data(
            [
                uds("2023-11-15", steps=1),
                act("2023-12-20", "cycling", distance_m=20000, duration_sec=3600),
                act("2024-01-05", distance_m=5000, duration_sec=1500),
                act("2024-03-10", distance_m=3000, duration_sec=900),
                act("2024-03-20", "treadmill_running", distance_m=1000, duration_sec=300),
                uds("2024-05-10", steps=1),
            ]
        )

    def test_a_period_without_records_is_zero_only_between_the_first_and_last_activity(self) -> None:
        answer = panel(self.data(), "dist", grain="month")
        [line] = answer["lines"]
        # November 2023 to May 2024.
        self.assertEqual(line["values"], [None, None, 5000.0, 0.0, 4000.0, None, None])
        self.assertEqual(line["counts"], [0, 0, 1, 0, 2, 0, 0])
        self.assertEqual(answer["left_out"]["zero_periods"], 1)
        self.assertEqual(
            line["summary"],
            {
                "periods_with_records": 2,
                "periods_without_records": 1,
                "periods_with_value": 3,
                # A period of 0 is not the lowest.
                "lowest": {"value": 4000.0, "period": 4},
                "highest": {"value": 5000.0, "period": 2},
                "latest": {"value": 4000.0, "period": 4},
            },
        )
        count = panel(self.data(), "count", grain="month")["lines"][0]
        self.assertEqual(count["values"], [None, None, 1.0, 0.0, 2.0, None, None])

    def test_the_activity_types_counted_change_the_totals_and_their_ends(self) -> None:
        [line] = panel(self.data(), "dist", grain="month", types=["running", "cycling"])["lines"]
        self.assertEqual(line["values"], [None, 20000.0, 5000.0, 0.0, 3000.0, None, None])
        [line] = panel(self.data(), "dist", grain="month", types=[])["lines"]
        self.assertEqual(line["values"], [None] * 7)

    def test_a_period_with_activities_but_no_value_is_empty(self) -> None:
        data = view_data(
            [
                act("2024-01-05", distance_m=5000, duration_sec=1500, activity_training_load=80),
                act("2024-02-05", distance_m=5000, duration_sec=1500),
                act("2024-03-05", distance_m=5000, duration_sec=1500, activity_training_load=60),
            ]
        )
        answer = panel(data, "load", grain="month")
        self.assertEqual(answer["lines"][0]["values"], [80.0, None, 60.0])
        self.assertEqual((answer["left_out"]["no_value"], answer["left_out"].get("zero_periods", 0)), (1, 0))


class MeanTest(unittest.TestCase):
    def test_the_pace_takes_the_activities_with_both_a_distance_and_a_time(self) -> None:
        data = view_data(
            [
                act("2024-01-02", distance_m=10000, duration_sec=3000),
                act("2024-01-02", distance_m=5000, duration_sec=1600),
                act("2024-01-02", distance_m=None, duration_sec=1000),
                act("2024-01-02", distance_m=0, duration_sec=1200),
                act("2024-01-02", disagree=("duration_sec",), distance_m=3000, duration_sec=None),
            ]
        )
        answer = panel(data, "pace")
        [line] = answer["lines"]
        self.assertAlmostEqual(line["values"][0], 4600 / 15000)
        self.assertEqual(line["counts"], [2])
        self.assertEqual((answer["left_out"]["no_value"], answer["left_out"]["disagree"]), (2, 1))

    def test_a_mean_of_activities_is_weighted_by_their_durations(self) -> None:
        data = view_data(
            [
                act("2024-01-02", avg_hr=150, duration_sec=3600),
                act("2024-01-03", avg_hr=170, duration_sec=1800),
                act("2024-01-04", avg_hr=160, duration_sec=None),
                act("2024-01-05", disagree=("avg_hr",), avg_hr=None, duration_sec=600),
                act("2024-01-06", avg_hr=None, duration_sec=600),
            ]
        )
        answer = panel(data, "hr", grain="month")
        self.assertAlmostEqual(answer["lines"][0]["values"][0], (150 * 3600 + 170 * 1800) / 5400)
        self.assertEqual(answer["lines"][0]["counts"], [2])
        self.assertEqual(
            {name: answer["left_out"][name] for name in ("no_duration", "disagree", "no_value")},
            {"no_duration": 1, "disagree": 1, "no_value": 1},
        )

    def test_the_maximum_of_a_period(self) -> None:
        data = view_data([act("2024-01-02", max_hr=180), act("2024-01-03", max_hr=175), act("2024-02-01", max_hr=170)])
        self.assertEqual(panel(data, "mx", grain="month")["lines"][0]["values"], [180.0, 170.0])

    def test_a_daily_item_is_the_mean_of_the_days_with_a_value(self) -> None:
        data = view_data(
            [
                uds("2024-01-01", resting_heart_rate=50, steps=8000),
                uds("2024-01-02", resting_heart_rate=None, steps=12000),
                uds("2024-01-03", resting_heart_rate=53, steps=None),
            ]
        )
        month = panel(data, "rhr", grain="month")
        self.assertEqual((month["lines"][0]["values"], month["lines"][0]["counts"]), ([51.5], [2]))
        self.assertEqual(month["left_out"]["no_value"], 1)
        self.assertEqual(panel(data, "rhr", grain="day")["lines"][0]["values"], [50.0, None, 53.0])
        # Steps are a mean per day of the days with a value.
        self.assertEqual(panel(data, "steps", grain="month")["lines"][0]["values"], [10000.0])

    def test_a_sleep_counts_only_on_the_days_that_it_may_be_used(self) -> None:
        def sleep(when: str, minutes: float, **marks: bool) -> tuple[str, Row]:
            return "sleep_daily", daily("sleep_daily", when, sleep_duration_minutes_ex_awake=minutes, **marks)

        data = view_data(
            [
                sleep("2024-01-01", 420),
                sleep("2024-01-02", 400, used=False, review=True),
                sleep("2024-01-03", 380, used=False),
                # Two rows of one day need review, and count as one day.
                sleep("2024-01-04", 360, used=False, review=True),
                sleep("2024-01-04", 361, used=False, review=True),
                sleep("2024-01-05", 440),
            ]
        )
        answer = panel(data, "sleep", grain="month")
        self.assertEqual(answer["lines"][0]["values"], [430.0])
        self.assertEqual((answer["left_out"]["sleep_review_days"], answer["left_out"]["sleep_other_days"]), (2, 1))

    def test_a_value_emptied_because_values_disagreed_is_counted(self) -> None:
        data = view_data(
            [
                ("hrv_daily", daily("hrv_daily", "2024-01-01", disagree=("hrv_value",), hrv_value=None)),
                ("hrv_daily", daily("hrv_daily", "2024-01-02", hrv_value=60)),
            ]
        )
        answer = panel(data, "hrv", grain="month")
        self.assertEqual((answer["lines"][0]["values"], answer["left_out"]["disagree"]), ([60.0], 1))


class RecordTest(unittest.TestCase):
    def test_every_record_is_a_point_by_day_and_otherwise_in_the_mean(self) -> None:
        def readiness(when: str, time: str, score: float) -> tuple[str, Row]:
            return "training_readiness_daily", daily(
                "training_readiness_daily", when, time=time, training_readiness_score=score
            )

        data = view_data(
            [
                readiness("2024-01-01", "2024-01-01T12:00:00Z", 60),
                readiness("2024-01-01", "2024-01-01T06:00:00Z", 50),
                readiness("2024-01-02", "2024-01-02T06:00:00Z", 70),
            ]
        )
        by_day = panel(data, "tr", grain="day")
        [line] = by_day["lines"]
        self.assertEqual(line["points"], [[0, 50.0], [0, 60.0], [1, 70.0]])
        self.assertEqual((line["values"], line["counts"]), ([55.0, 70.0], [2, 1]))
        self.assertEqual(by_day["left_out"]["days_with_several_records"], 1)
        by_week = panel(data, "tr", grain="week")["lines"][0]
        # The mean of every record, not of the means of the days.
        self.assertEqual((by_week["values"], "points" in by_week), ([60.0], False))

    def test_the_series_and_sports_of_vo2max_are_separate_lines(self) -> None:
        def vo2(when: str, series: str, sport: str, value: float) -> tuple[str, Row]:
            return "vo2max_daily", daily("vo2max_daily", when, series=(series, sport), vo2max=value)

        data = view_data(
            [
                vo2("2022-01-10", "activity_vo2max_daily", "RUNNING", 55),
                vo2("2022-01-20", "activity_vo2max_daily", "RUNNING", 56),
                vo2("2022-01-23", "performance_metrics_daily", "RUNNING", 58),
                vo2("2022-01-23", "performance_metrics_daily", "CYCLING", 50),
            ]
        )
        lines = panel(data, "vo2", grain="month")["lines"]
        self.assertEqual(
            [(line["series"], line["values"], line["first_day"], line["last_day"]) for line in lines],
            [
                ({"vo2max_source_series": "activity_vo2max_daily", "sport": "RUNNING"}, [55.5], "2022-01-10", "2022-01-20"),
                ({"vo2max_source_series": "performance_metrics_daily", "sport": "CYCLING"}, [50.0], "2022-01-23", "2022-01-23"),
                ({"vo2max_source_series": "performance_metrics_daily", "sport": "RUNNING"}, [58.0], "2022-01-23", "2022-01-23"),
            ],
        )
        later = panel(data, "vo2", period=(date(2022, 1, 21), date(2022, 1, 31)), grain="month")["lines"]
        self.assertEqual([line["series"]["vo2max_source_series"] for line in later], ["performance_metrics_daily"] * 2)

    def test_rows_without_a_date_or_after_today_are_counted_for_their_file(self) -> None:
        data = view_data([uds("2024-01-01", steps=1)], no_date={"uds_daily": 2}, after_today={"uds_daily": 1})
        left_out = panel(data, "steps")["left_out"]
        self.assertEqual((left_out["no_date"], left_out["after_today"]), (2, 1))
        self.assertEqual(panel(data, "vo2")["left_out"]["no_date"], 0)


class ShelfTest(unittest.TestCase):
    def test_the_running_types_are_counted_at_first(self) -> None:
        names = ["running"] * 3 + ["treadmill_running", "Trail Running", "virtual_run", "cycling", "cycling", "road_biking", "walking", ""]
        data = view_data([act("2024-01-01", name, distance_m=1000) for name in names])
        self.assertEqual(
            activity_types(data),
            [
                {"name": "running", "count": 3, "running": True},
                {"name": "cycling", "count": 2, "running": False},
                {"name": "", "count": 1, "running": False},
                {"name": "Trail Running", "count": 1, "running": True},
                {"name": "road_biking", "count": 1, "running": False},
                {"name": "treadmill_running", "count": 1, "running": True},
                {"name": "virtual_run", "count": 1, "running": True},
                {"name": "walking", "count": 1, "running": False},
            ],
        )
        self.assertEqual(default_types(data), {"running", "treadmill_running", "Trail Running", "virtual_run"})
        self.assertEqual(panel(data, "count")["lines"][0]["values"], [6.0])

    def test_the_bars_of_the_shelf_and_the_first_items(self) -> None:
        data = view_data(
            [
                uds("2023-12-31", resting_heart_rate=50),
                uds("2024-02-01", resting_heart_rate=None, steps=100),
                act("2024-03-01", "cycling", distance_m=1000),
                act("2024-04-01", distance_m=2000),
            ]
        )
        shelf = coverage(data)
        self.assertEqual(shelf["rhr"], {"months": ["2023-12"], "first_day": "2023-12-31", "last_day": "2023-12-31"})
        self.assertEqual(shelf["dist"]["months"], ["2024-04"])
        self.assertEqual(coverage(data, ["cycling"])["dist"]["months"], ["2024-03"])
        self.assertEqual(shelf["vo2"]["months"], [])
        # The output has no VO2max.
        self.assertEqual(default_items(data), ["dist", "rhr"])
        self.assertEqual(FIRST_ITEMS, ("dist", "rhr", "vo2"))


class ItemTableTest(unittest.TestCase):
    def test_the_items_read_fields_that_the_output_has(self) -> None:
        self.assertEqual(len(ITEMS), 38)
        self.assertEqual(len(ITEMS_BY_KEY), 38)
        for item in ITEMS:
            with self.subTest(item=item.key):
                if item.field is None:
                    continue
                if item.dataset == ACTIVITIES:
                    self.assertIn(item.field, ACTIVITIES_CSV_COLUMNS)
                else:
                    schema = json.loads((ROOT / "schemas" / f"{item.dataset}.schema.json").read_text(encoding="utf-8"))
                    self.assertIn(item.field, schema["items"]["properties"])
        for spec in DATASETS[1:]:
            schema = json.loads((ROOT / "schemas" / f"{spec.name}.schema.json").read_text(encoding="utf-8"))
            self.assertIn(spec.date_field, schema["items"]["properties"])
            for name in spec.series:
                self.assertIn(name, schema["items"]["properties"])


class AnswerSizeTest(unittest.TestCase):
    def test_six_panels_by_day_over_fifteen_years_stay_within_the_size(self) -> None:
        rows: list[tuple[str, Row]] = []
        first = date(2011, 1, 1)
        switch = date(2022, 1, 23)
        current = first
        while current <= date(2025, 12, 31):
            when = current.isoformat()
            # The records of the most a day: readiness three times a day.
            for hour in ("06", "12", "18"):
                rows.append(
                    (
                        "training_readiness_daily",
                        daily("training_readiness_daily", when, time=f"{when}T{hour}:00:00Z", training_readiness_score=55.123456789),
                    )
                )
            for hour in ("06", "18"):
                rows.append(
                    (
                        "acute_training_load_daily",
                        daily(
                            "acute_training_load_daily",
                            when,
                            time=f"{when}T{hour}:00:00Z",
                            daily_training_load_acute=412.123456789,
                            daily_training_load_chronic=388.987654321,
                        ),
                    )
                )
            rows.append(("race_prediction_daily", daily("race_prediction_daily", when, race_time_5k_sec=1234.56789)))
            if current < switch:
                rows.append(("vo2max_daily", daily("vo2max_daily", when, series=("activity_vo2max_daily", "RUNNING"), vo2max=55.5)))
            else:
                for sport in ("RUNNING", "CYCLING"):
                    rows.append(("vo2max_daily", daily("vo2max_daily", when, series=("performance_metrics_daily", sport), vo2max=54.25)))
            current += timedelta(days=1)
        data = view_data(rows)
        keys = ["tr", "acute", "chronic", "vo2", "p5k", "p10k"]
        self.assertEqual(len(keys), MAX_PANELS)
        answer = view_answer(data, keys, "all", "day")
        self.assertEqual(len(answer["periods"]), (date(2025, 12, 31) - first).days + 1)
        size = len(json.dumps(answer).encode("utf-8"))
        self.assertLessEqual(size, MAX_ANSWER_BYTES)
        self.assertEqual((MAX_ANSWER_BYTES, MAX_PANELS), (4 * 1024 * 1024, 6))


if __name__ == "__main__":
    unittest.main()
