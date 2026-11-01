"""The API of the view page (stage G3b): an output opened under a ticket that
holds no place, and its numbers, which are those of the functions of stage
G1, read once and again when the output changes; and the list of the
activities of one period of a panel (stage M3 of v2.2.0), from the same
reading.

Synthetic data only: one output of about two and a half years, made once and
copied by the tests that change it. Every test has its own server, and the
settings are each test's own (``tests/conftest.py``).
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Import the diagnostics package before modules that import standalone: the
# other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import __version__, diagnostics  # noqa: F401
from garmin_running_data_normalizer.gui import server as gui_server
from garmin_running_data_normalizer.gui import views as gui_views
from garmin_running_data_normalizer.gui.layouts import built_in_answer
from garmin_running_data_normalizer.gui.views import (
    MAX_SHELVES,
    load_view,
    MAX_VIEWS,
    ConditionsRequestError,
    ViewRequestError,
    Views,
    conditions_from,
    conditions_request,
    item_table,
    list_request,
    output_stamp,
    previous_request,
    series_request,
)
from garmin_running_data_normalizer.output_check import OutputActionError
from garmin_running_data_normalizer.run_all import RUN_ALL_VERSION, run_all
from garmin_running_data_normalizer.view import data as view_data
from garmin_running_data_normalizer.view import series as view_series
from garmin_running_data_normalizer.view.data import load_view_data
from garmin_running_data_normalizer.view.items import ITEMS
from garmin_running_data_normalizer.view.series import (
    MAX_TYPE_LENGTH,
    MAX_TYPES,
    Conditions,
    activity_types,
    coverage,
    default_items,
    shoe_answer,
    shoe_count,
    view_answer,
)
from tests.test_gui_server import GuiServerTestCase
from tests.v1_3_outputs import as_release, as_v1_3
from tests.view_export import MEMO_MARK, write_view_export

TIMEOUT_SECONDS = 10.0
_MADE: dict[str, Any] = {}


def setUpModule() -> None:
    directory = tempfile.TemporaryDirectory()
    root = Path(directory.name).resolve()
    run_all(write_view_export(root / "export"), root / "output")
    # With the synthetic shoes (stage S1 of v2.2.0).
    run_all(write_view_export(root / "shoes-export", gear=True), root / "shoes-output")
    # With made-up names of training too (stage T1).
    run_all(write_view_export(root / "names-export", gear=True, names=True), root / "names-output")
    _MADE.update(directory=directory, output=root / "output", shoes=root / "shoes-output", names=root / "names-output")


def tearDownModule() -> None:
    _MADE["directory"].cleanup()


def made_output() -> Path:
    return _MADE["output"]


def shoe_output() -> Path:
    return _MADE["shoes"]


def names_output() -> Path:
    return _MADE["names"]


def as_json(value: Any) -> Any:
    """A value as an answer of the server reads after JSON."""
    return json.loads(json.dumps(value))


class ViewApiTest(GuiServerTestCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.place = Path(directory.name).resolve()

    def call(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def copied(self, name: str = "output") -> Path:
        output = self.place / name
        shutil.copytree(made_output(), output)
        return output

    def open(self, output: Path) -> str:
        status, answer = self.call("/api/view/open", {"output": "chosen", "path": str(output)})
        self.assertEqual(status, 200, answer)
        return answer["view"]

    def test_an_output_opens_under_a_ticket_that_holds_no_place(self) -> None:
        output = made_output()
        status, answer = self.call("/api/view/open", {"output": "chosen", "path": str(output)})
        self.assertEqual(status, 200)
        data = load_view_data(output)
        self.assertEqual(
            set(answer),
            {"view", "name", "version", "partial", "first_day", "last_day", "items", "types", "first_items", "layouts", "coverage", "shoes", "names"},
        )
        # The names of the activities were read (stage T1 of v2.2.0).
        self.assertEqual(answer["names"], "read")
        self.assertRegex(answer["view"], r"^[A-Za-z0-9_-]{16,}$")
        self.assertEqual(
            {key: answer[key] for key in ("name", "version", "partial", "first_day", "last_day")},
            {
                "name": "output",
                "version": __version__,
                "partial": False,
                "first_day": date.fromordinal(data.first_day).isoformat(),
                "last_day": date.fromordinal(data.last_day).isoformat(),
            },
        )
        # The table of items is the server's: the page has none of its own.
        self.assertEqual(answer["items"], as_json(item_table()))
        self.assertEqual([entry["key"] for entry in answer["items"]], [item.key for item in ITEMS])
        self.assertEqual(answer["types"], as_json(activity_types(data)))
        self.assertEqual(answer["first_items"], default_items(data))
        # The built-in layouts, by their ids and items (stage K1 of v2.2.0).
        self.assertEqual(answer["layouts"], built_in_answer())
        self.assertEqual(answer["coverage"], as_json(coverage(data)))
        # Whether the view by shoes has shoes (stage S1 of v2.2.0): none here.
        self.assertEqual(answer["shoes"], shoe_count(load_view(output)))
        # No place reaches the page, not even a part of one.
        text = json.dumps(answer)
        for place in (output, output.parent):
            self.assertNotIn(str(place), text)

    def test_an_output_with_part_of_the_input_left_out_says_so(self) -> None:
        # Exit code 3: the check of the output answers PARTIAL_SUCCESS.
        real = view_data.checked_output

        def partial(output: Path) -> tuple[dict[str, Any], dict[str, Any], bool]:
            handoff, report, legacy = real(output)
            return {**handoff, "run_status": "PARTIAL_SUCCESS"}, report, legacy

        with patch.object(view_data, "checked_output", partial):
            status, answer = self.call("/api/view/open", {"output": "chosen", "path": str(made_output())})
        self.assertEqual((status, answer["partial"]), (200, True))

    def test_the_view_by_shoes_is_that_of_what_the_view_page_read(self) -> None:
        # Stage S1 of v2.2.0, with the synthetic shoes: the view page reads
        # them by default (Codex's review of the plan of S1), and every answer
        # of its numbers says how many it has.
        self.assertIs(Views()._load, load_view)
        output = shoe_output()
        status, opened = self.call("/api/view/open", {"output": "chosen", "path": str(output)})
        self.assertEqual((status, opened["shoes"]), (200, {"count": 6, "too_large": False}))
        data = load_view(output)
        names = [entry["name"] for entry in activity_types(data)]
        for period, types, chosen in (
            ("all", None, "all"),
            ("1y", names, "1y"),
            ({"from": "2024-02-01", "to": "2024-05-31"}, ["treadmill_running"], (date(2024, 2, 1), date(2024, 5, 31))),
        ):
            with self.subTest(period=period, types=types):
                status, answer = self.call("/api/view/shoes", {"view": opened["view"], "period": period, "types": types})
                self.assertEqual(status, 200)
                self.assertEqual(answer, as_json({**shoe_answer(data, chosen, types), "names": "read"}))
        status, numbers = self.call("/api/view/series", {"view": opened["view"], "items": ["dist"], "period": "all", "grain": "auto", "types": None})
        self.assertEqual((status, numbers["shoes"]), (200, {"count": 6, "too_large": False}))

    def test_a_request_of_the_view_by_shoes_is_checked_as_the_numbers_are(self) -> None:
        ticket = self.open(shoe_output())
        names = ("ロード用 A", "ロード用 B", "トレイル用 C", "レース用 D", "Synthetic model X")
        for payload, expected in (
            ({"period": "all"}, (422, "REQUEST_INVALID")),
            ({"view": 1, "period": "all"}, (422, "REQUEST_INVALID")),
            ({"view": ticket, "period": "5w"}, (422, "REQUEST_INVALID")),
            ({"view": ticket, "period": {"from": "2024-03-01", "to": "2024-02-01"}}, (422, "REQUEST_INVALID")),
            ({"view": ticket, "period": "all", "types": "running"}, (422, "REQUEST_INVALID")),
            ({"view": ticket, "period": "all", "types": ["running", "running"]}, (422, "REQUEST_INVALID")),
            ({"view": ticket, "period": "all", "types": ["no such type"]}, (422, "REQUEST_INVALID")),
            ({"view": "not-a-ticket", "period": "all"}, (409, "VIEW_NOT_OPEN")),
        ):
            with self.subTest(payload=payload):
                status, answer = self.call("/api/view/shoes", payload)
                self.assertEqual((status, answer), (expected[0], {"error": expected[1]}))
                # No name of a shoe is in an answer of an error.
                self.assertFalse(any(name in json.dumps(answer, ensure_ascii=False) for name in names))
        # The answer has the limit of the others (the partial guard of S1).
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 100):
            self.assertEqual(self.call("/api/view/shoes", {"view": ticket, "period": "all"}), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))


    def test_the_numbers_are_those_of_the_view_page(self) -> None:
        output = made_output()
        ticket = self.open(output)
        data = load_view_data(output)
        names = [entry["name"] for entry in activity_types(data)]
        cases = (
            (["dist"], "all", "auto", None, "all"),
            (["dist", "rhr", "vo2"], "1y", "week", None, "1y"),
            (["pace", "hr"], {"from": "2024-01-01", "to": "2024-03-31"}, "day", names[:1], (date(2024, 1, 1), date(2024, 3, 31))),
            (["count", "p5k", "sleep", "acwr", "steps", "gct"], "3y", "month", names, "3y"),
            # The whole period as one period (stage M2 of v2.2.0).
            (["dist", "pace", "rhr"], {"from": "2024-01-01", "to": "2024-03-31"}, "range", None, (date(2024, 1, 1), date(2024, 3, 31))),
        )
        for items, period, grain, types, chosen in cases:
            with self.subTest(items=items, period=period, grain=grain):
                status, answer = self.call(
                    "/api/view/series", {"view": ticket, "items": items, "period": period, "grain": grain, "types": types}
                )
                self.assertEqual(status, 200)
                expected = view_answer(data, items, chosen, grain, types)
                expected["coverage"] = coverage(data, types)
                expected["shoes"] = shoe_count(load_view(output))
                expected["names"] = "read"
                self.assertEqual(answer, as_json(expected))

    def test_the_summary_has_the_period_before(self) -> None:
        # Stage Q1 of v2.2.0: the whole period with the period of the same
        # length just before it, as the server makes them, from one reading.
        output = made_output()
        ticket = self.open(output)
        data = load_view_data(output)
        for items, period, chosen in (
            (["dist", "pace", "rhr"], "1y", "1y"),
            (["count", "vo2"], {"from": "2024-01-01", "to": "2024-03-31"}, (date(2024, 1, 1), date(2024, 3, 31))),
            (["dist"], "all", "all"),
        ):
            with self.subTest(items=items, period=period):
                status, answer = self.call(
                    "/api/view/series", {"view": ticket, "items": items, "period": period, "grain": "range", "types": None, "previous": True}
                )
                self.assertEqual(status, 200)
                expected = view_answer(data, items, chosen, "range", None, True)
                expected["coverage"] = coverage(data, None)
                expected["shoes"] = shoe_count(load_view(output))
                expected["names"] = "read"
                self.assertEqual(answer, as_json(expected))
                self.assertIn("previous", answer)
        # Without it, the answer is that of the whole period as before.
        status, answer = self.call("/api/view/series", {"view": ticket, "items": ["dist"], "period": "1y", "grain": "range", "previous": False})
        self.assertEqual(status, 200)
        self.assertNotIn("previous", answer)
        self.assertNotIn("chosen", answer)

    def test_requests_of_another_form_are_refused(self) -> None:
        ticket = self.open(made_output())
        good = {"view": ticket, "items": ["dist"], "period": "all", "grain": "auto", "types": None}
        for change in (
            {"view": None},
            {"view": 3},
            {"items": []},
            {"items": "dist"},
            {"items": ["dist", "dist"]},
            {"items": ["nope"]},
            {"items": [item.key for item in ITEMS[:7]]},
            {"period": "2y"},
            {"period": {"from": "2024-01-01"}},
            {"period": {"from": "2024-02-01", "to": "2024-01-01"}},
            {"period": {"from": "2024-1-1", "to": "2024-01-31"}},
            {"period": {"from": "2024-02-30", "to": "2024-03-01"}},
            {"grain": "quarter"},
            {"types": "running"},
            {"types": ["running", "running"]},
            {"types": [1]},
            {"types": ["no such type"]},
            # Stage Q1 of v2.2.0: the period before, as a truth value, with the whole period.
            {"previous": 1},
            {"previous": "true"},
            {"previous": None},
            {"previous": True},
            {"previous": True, "grain": "week"},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.call("/api/view/series", {**good, **change}), (422, {"error": "REQUEST_INVALID"}))

    def test_every_type_of_an_output_is_counted_whatever_their_number(self) -> None:
        # An output may have more activity types, or other names, than the
        # settings keep; the numbers take them all, as 2.1.0 did (stage K1 of
        # v2.2.0, the checker).
        output = made_output()
        ticket = self.open(output)
        data = load_view_data(output)
        extra = [f"type {number}" for number in range(MAX_TYPES + 1)] + ["a\u202eb", "x" * (MAX_TYPE_LENGTH + 1)]
        many = activity_types(data) + [{"name": name, "count": 1, "running": False} for name in extra]
        names = [entry["name"] for entry in many]
        payload = {"view": ticket, "items": ["dist"], "period": "all", "grain": "auto", "types": names}
        with patch.object(gui_server, "activity_types", return_value=many):
            status, answer = self.call("/api/view/series", payload)
        self.assertEqual(status, 200, answer)
        expected = view_answer(data, ["dist"], "all", "auto", names)
        expected["coverage"] = coverage(data, names)
        expected["shoes"] = shoe_count(load_view(output))
        expected["names"] = "read"
        self.assertEqual(answer, as_json(expected))

    def test_a_ticket_that_the_server_does_not_keep_is_refused(self) -> None:
        payload = {"view": "not-a-ticket-of-this-server", "items": ["dist"], "period": "all", "grain": "auto", "types": None}
        self.assertEqual(self.call("/api/view/series", payload), (409, {"error": "VIEW_NOT_OPEN"}))

    def test_outputs_that_cannot_be_viewed_are_refused_with_their_codes(self) -> None:
        legacy = self.copied("legacy")
        as_v1_3(legacy)
        other = self.copied("other")
        written = json.loads((other / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
        # A version that is not this one: an earlier stable release.
        as_release(other, "2.0.0", tuple(written), RUN_ALL_VERSION)
        for payload, expected in (
            ({"output": "chosen", "path": str(legacy)}, (422, {"error": "SERIES_OUTPUT_OTHER_VERSION", "version": "1.3.3"})),
            ({"output": "chosen", "path": str(other)}, (422, {"error": "OUTPUT_OTHER_VERSION", "version": "2.0.0"})),
            ({"output": "chosen", "path": str(self.place)}, (422, {"error": "HANDOFF_INVALID"})),
            ({"output": "chosen", "path": "relative"}, (422, {"error": "PATH_NOT_ABSOLUTE"})),
            ({}, (409, {"error": "NO_FINISHED_OUTPUT"})),
            ({"output": "earlier", "index": 0, "list": 7}, (409, {"error": "OUTPUT_LIST_CHANGED"})),
            ({"output": "another"}, (422, {"error": "REQUEST_INVALID"})),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/view/open", payload), expected)

    def test_an_answer_over_the_limit_of_its_size_is_refused(self) -> None:
        ticket = self.open(made_output())
        payload = {"view": ticket, "items": ["dist"], "period": "all", "grain": "day", "types": None}
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 1000):
            self.assertEqual(self.call("/api/view/series", payload), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))
        self.assertEqual(self.call("/api/view/series", payload)[0], 200)

    def test_an_unexpected_error_of_the_numbers_answers_as_the_server_does(self) -> None:
        # The checker's review of stage G3b-1: an error that no code
        # describes, in the numbers or in the bars of the shelf, answers as
        # any unexpected error of the server, without its words; the page
        # then says that something went wrong, and the server goes on. The
        # bars are made in gui/views.py and kept with the output (stage M2 of
        # v2.2.0); the opening made those of the first types, so the request
        # asks for one type, whose bars are made anew.
        output = made_output()
        ticket = self.open(output)
        names = [entry["name"] for entry in activity_types(load_view_data(output))]
        payload = {"view": ticket, "items": ["dist"], "period": "all", "grain": "auto", "types": names[:1]}
        body = json.dumps(payload).encode("utf-8")
        for module, name in ((gui_server, "view_answer"), (gui_views, "coverage")):
            with self.subTest(function=name), patch.object(module, name, side_effect=RuntimeError("unexpected words")):
                status, _, answer = self.post_api("/api/view/series", self.api_headers(body), body)
                self.assertEqual(status, 500)
                self.assertNotIn(b"unexpected words", answer)
        self.assertEqual(self.call("/api/view/series", payload)[0], 200)

    def test_the_bars_of_the_shelf_are_made_once_for_an_output_and_its_types(self) -> None:
        # Stage M2 of v2.2.0: a comparison by race day asks up to 13 times
        # in a row, and the bars of the shelf are made from every row of the
        # output; they are kept with the output by the activity types, in
        # any order, and made again when the output is read again. The bars
        # are counted wherever they are made (the first items of the opening
        # take them from view/series.py).
        output = self.copied()
        real = view_series.coverage
        made: list[Any] = []

        def counted(data: Any, types: Any = None, conditions: Any = None) -> Any:
            made.append(None if types is None else sorted(types))
            return real(data, types, conditions)

        data = load_view_data(output)
        names = [entry["name"] for entry in activity_types(data)]
        self.assertGreaterEqual(len(names), 2)
        with patch.object(gui_views, "coverage", counted), patch.object(view_series, "coverage", counted):
            ticket = self.open(output)
            # The opening makes them once, for its first items too.
            self.assertEqual(made, [None])
            for types in (None, None, names, list(reversed(names)), names[:1], names[:1]):
                with self.subTest(types=types):
                    status, answer = self.call(
                        "/api/view/series", {"view": ticket, "items": ["dist"], "period": "all", "grain": "range", "types": types}
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(answer["coverage"], as_json(real(data, types)))
            self.assertEqual(made, [None, sorted(names), sorted(names[:1])])
            activities = output / "analysis" / "activities.csv"
            later = activities.stat().st_mtime_ns + 2_000_000_000
            os.utime(activities, ns=(later, later))
            # Every shelf of the reading before is dropped (the checker's
            # review of M2): those of the other types are made again too.
            for types in (None, None, names[:1], names[:1]):
                status, answer = self.call("/api/view/series", {"view": ticket, "items": ["dist"], "period": "all", "grain": "range", "types": types})
                self.assertEqual((status, answer["coverage"]), (200, as_json(real(data, types))))
            self.assertEqual(made, [None, sorted(names), sorted(names[:1]), None, sorted(names[:1])])

    def test_the_numbers_are_read_once_and_again_when_the_output_changes(self) -> None:
        output = self.copied()
        loads: list[Path] = []

        def counted(place: Path) -> Any:
            loads.append(place)
            return load_view_data(place)

        payload = {"items": ["dist", "rhr"], "period": "all", "grain": "month", "types": None}
        with patch.object(self.server.views, "_load", counted):
            ticket = self.open(output)
            payload["view"] = ticket
            first = self.call("/api/view/series", payload)
            self.assertEqual(self.call("/api/view/series", payload), first)
            self.assertEqual(len(loads), 1)
            # A file whose time of change moved is read again, and checked.
            activities = output / "analysis" / "activities.csv"
            later = activities.stat().st_mtime_ns + 2_000_000_000
            os.utime(activities, ns=(later, later))
            self.assertEqual(self.call("/api/view/series", payload), first)
            self.assertEqual(len(loads), 2)
            # A file whose contents changed fails the check of the output,
            # which compares it with the manifest: the code of the check, and
            # the ticket is forgotten.
            with activities.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            self.assertEqual(self.call("/api/view/series", payload), (422, {"error": "HANDOFF_INVALID"}))
            self.assertEqual(self.call("/api/view/series", payload), (409, {"error": "VIEW_NOT_OPEN"}))

    def test_a_new_day_reads_the_output_again(self) -> None:
        loads: list[Path] = []

        def counted(place: Path) -> Any:
            loads.append(place)
            return load_view_data(place)

        with patch.object(self.server.views, "_load", counted):
            ticket = self.open(made_output())
            payload = {"view": ticket, "items": ["dist"], "period": "all", "grain": "auto", "types": None}
            self.assertEqual(self.call("/api/view/series", payload)[0], 200)
            self.assertEqual(len(loads), 1)
            tomorrow = view_data.local_today("Asia/Tokyo") + timedelta(days=1)
            with patch.object(self.server.views, "_today", lambda _timezone: tomorrow):
                self.assertEqual(self.call("/api/view/series", payload)[0], 200)
            self.assertEqual(len(loads), 2)

    def test_at_most_four_outputs_are_kept(self) -> None:
        # The number of the plan, written as it is, so that a changed
        # constant does not change the test.
        self.assertEqual(MAX_VIEWS, 4)
        tickets = [self.open(made_output()) for _ in range(MAX_VIEWS + 1)]
        self.assertEqual(len(set(tickets)), MAX_VIEWS + 1)
        payload = {"items": ["dist"], "period": "all", "grain": "auto", "types": None}
        self.assertEqual(self.call("/api/view/series", {**payload, "view": tickets[0]}), (409, {"error": "VIEW_NOT_OPEN"}))
        for ticket in tickets[1:]:
            with self.subTest(ticket=ticket):
                self.assertEqual(self.call("/api/view/series", {**payload, "view": ticket})[0], 200)

    def test_the_activities_of_a_period_are_those_of_the_view_page(self) -> None:
        # Stage M3 of v2.2.0: the list of the activities of one period of a
        # panel is that of the function of the view page, for a week, a
        # month, a year, and every day of the output (more activities than
        # the list shows: their number only).
        output = made_output()
        ticket = self.open(output)
        data = load_view_data(output)
        names = [entry["name"] for entry in activity_types(data)]
        for key, period, types, total in (
            ("dist", {"from": "2024-03-04", "to": "2024-03-10"}, None, True),
            ("pace", {"from": "2024-01-01", "to": "2024-01-31"}, names[:1], True),
            ("count", {"from": "2023-01-01", "to": "2023-12-31"}, names, True),
            ("gct", {"from": "2024-05-01", "to": "2024-05-31"}, None, True),
            ("dist", {"from": "2022-01-01", "to": "2026-12-31"}, names, False),
        ):
            with self.subTest(item=key, period=period, types=types):
                status, answer = self.call("/api/view/activities", {"view": ticket, "item": key, "period": period, "types": types})
                self.assertEqual(status, 200, answer)
                chosen = (date.fromisoformat(period["from"]), date.fromisoformat(period["to"]))
                self.assertEqual(answer, as_json({**view_series.activity_list(load_view(output), key, chosen, types), "names": "read"}))
                self.assertGreater(answer["total"], 0)
                self.assertEqual(answer["rows"] is not None, total)
        # The item of the panel, when it is none of the columns of the list,
        # is one more column.
        status, answer = self.call(
            "/api/view/activities", {"view": ticket, "item": "gct", "period": {"from": "2024-05-01", "to": "2024-05-31"}, "types": None}
        )
        self.assertEqual(status, 200)
        self.assertEqual(set(answer["rows"][0]["values"]), {*view_series.LIST_ITEMS, "gct"})

    def test_requests_for_the_activities_of_another_form_are_refused(self) -> None:
        ticket = self.open(made_output())
        good = {"view": ticket, "item": "dist", "period": {"from": "2024-03-04", "to": "2024-03-10"}, "types": None}
        for change in (
            {"view": None},
            {"view": 3},
            {"item": None},
            {"item": ["dist"]},
            {"item": "nope"},
            # An item of the days has no activities.
            {"item": "rhr"},
            {"period": None},
            {"period": "all"},
            {"period": {"from": "2024-03-04"}},
            {"period": {"from": "2024-03-10", "to": "2024-03-04"}},
            {"period": {"from": "2024-3-4", "to": "2024-03-10"}},
            {"types": "running"},
            {"types": ["running", "running"]},
            {"types": [1]},
            {"types": ["no such type"]},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.call("/api/view/activities", {**good, **change}), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(
            self.call("/api/view/activities", {**good, "view": "not-a-ticket-of-this-server"}), (409, {"error": "VIEW_NOT_OPEN"})
        )
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 100):
            self.assertEqual(self.call("/api/view/activities", good), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))
        # An error that no code describes answers as any unexpected error of
        # the server, without its words.
        body = json.dumps(good).encode("utf-8")
        with patch.object(gui_server, "activity_list", side_effect=RuntimeError("unexpected words")):
            status, _, answer = self.post_api("/api/view/activities", self.api_headers(body), body)
        self.assertEqual(status, 500)
        self.assertNotIn(b"unexpected words", answer)
        self.assertEqual(self.call("/api/view/activities", good)[0], 200)

    def test_the_activities_are_read_as_the_numbers_are(self) -> None:
        # The list takes the reading of the numbers: no reading of its own
        # while the output does not change, and the codes of the check of
        # the output when it does (the same ticket may be read again between
        # the numbers and the list, as for the numbers of stages L and M2).
        output = self.copied()
        loads: list[Path] = []

        def counted(place: Path) -> Any:
            loads.append(place)
            return load_view_data(place)

        listed = {"item": "dist", "period": {"from": "2024-03-04", "to": "2024-03-10"}, "types": None}
        with patch.object(self.server.views, "_load", counted):
            ticket = self.open(output)
            self.assertEqual(self.call("/api/view/series", {"view": ticket, "items": ["dist"], "period": "all", "grain": "week", "types": None})[0], 200)
            first = self.call("/api/view/activities", {**listed, "view": ticket})
            self.assertEqual(first[0], 200)
            self.assertEqual(self.call("/api/view/activities", {**listed, "view": ticket}), first)
            self.assertEqual(len(loads), 1)
            activities = output / "analysis" / "activities.csv"
            with activities.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            self.assertEqual(self.call("/api/view/activities", {**listed, "view": ticket}), (422, {"error": "HANDOFF_INVALID"}))
            self.assertEqual(self.call("/api/view/activities", {**listed, "view": ticket}), (409, {"error": "VIEW_NOT_OPEN"}))

    def test_two_items_plotted_are_those_of_the_view_page(self) -> None:
        # Stage O1 of v2.2.0: the points of two items of the activities are
        # those of the function of the view page, for a period of its names,
        # a range, and the activity types counted.
        output = made_output()
        ticket = self.open(output)
        data = load_view_data(output)
        names = [entry["name"] for entry in activity_types(data)]
        for x, y, period, types in (
            ("pace", "hr", "all", None),
            ("dist", "time", "1y", names[:1]),
            ("gct", "cad", {"from": "2024-01-01", "to": "2024-12-31"}, names),
        ):
            with self.subTest(x=x, y=y, period=period, types=types):
                status, answer = self.call("/api/view/points", {"view": ticket, "x": x, "y": y, "period": period, "types": types})
                self.assertEqual(status, 200, answer)
                chosen = period if isinstance(period, str) else (date.fromisoformat(period["from"]), date.fromisoformat(period["to"]))
                self.assertEqual(answer, as_json({**view_series.activity_points(data, x, y, chosen, types), "names": "read"}))
                self.assertGreater(answer["total"], 0)
                self.assertEqual(answer["total"], answer["with_values"] + answer["missing"])
                self.assertEqual(len(answer["points"]), min(answer["with_values"], answer["limit"]))

    def test_requests_for_points_of_another_form_are_refused(self) -> None:
        ticket = self.open(made_output())
        good = {"view": ticket, "x": "pace", "y": "hr", "period": "all", "types": None}
        for change in (
            {"view": None},
            {"view": 3},
            {"x": None},
            {"x": ["pace"]},
            {"x": "nope"},
            # The count and an item of the days are not values of one
            # activity, and the two items are two different ones.
            {"x": "count"},
            {"y": "rhr"},
            {"y": "vo2"},
            {"y": "pace"},
            {"period": None},
            {"period": "custom"},
            {"period": {"from": "2024-03-04"}},
            {"period": {"from": "2024-03-10", "to": "2024-03-04"}},
            {"types": "running"},
            {"types": ["running", "running"]},
            {"types": [1]},
            {"types": ["no such type"]},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.call("/api/view/points", {**good, **change}), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(self.call("/api/view/points", {**good, "view": "not-a-ticket-of-this-server"}), (409, {"error": "VIEW_NOT_OPEN"}))
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 100):
            self.assertEqual(self.call("/api/view/points", good), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))
        body = json.dumps(good).encode("utf-8")
        with patch.object(gui_server, "activity_points", side_effect=RuntimeError("unexpected words")):
            status, _, answer = self.post_api("/api/view/points", self.api_headers(body), body)
        self.assertEqual(status, 500)
        self.assertNotIn(b"unexpected words", answer)
        self.assertEqual(self.call("/api/view/points", good)[0], 200)

    def test_the_points_are_read_as_the_numbers_are(self) -> None:
        # As the list: no reading of their own while the output does not
        # change, and the codes of the check of the output when it does.
        output = self.copied()
        loads: list[Path] = []

        def counted(place: Path) -> Any:
            loads.append(place)
            return load_view_data(place)

        plotted = {"x": "pace", "y": "hr", "period": "all", "types": None}
        with patch.object(self.server.views, "_load", counted):
            ticket = self.open(output)
            first = self.call("/api/view/points", {**plotted, "view": ticket})
            self.assertEqual(first[0], 200)
            self.assertEqual(self.call("/api/view/points", {**plotted, "view": ticket}), first)
            self.assertEqual(len(loads), 1)
            activities = output / "analysis" / "activities.csv"
            with activities.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            self.assertEqual(self.call("/api/view/points", {**plotted, "view": ticket}), (422, {"error": "HANDOFF_INVALID"}))
            self.assertEqual(self.call("/api/view/points", {**plotted, "view": ticket}), (409, {"error": "VIEW_NOT_OPEN"}))

    def test_the_distribution_is_that_of_the_view_page(self) -> None:
        # Stage P1 of v2.2.0: the ranges of one item of the activities are
        # those of the function of the view page, for a period of its names,
        # a range, and the activity types counted.
        output = made_output()
        ticket = self.open(output)
        data = load_view_data(output)
        names = [entry["name"] for entry in activity_types(data)]
        for key, period, types in (
            ("dist", "all", None),
            ("pace", "1y", names[:1]),
            ("gct", {"from": "2024-01-01", "to": "2024-12-31"}, names),
        ):
            with self.subTest(item=key, period=period, types=types):
                status, answer = self.call("/api/view/spread", {"view": ticket, "item": key, "period": period, "types": types})
                self.assertEqual(status, 200, answer)
                chosen = period if isinstance(period, str) else (date.fromisoformat(period["from"]), date.fromisoformat(period["to"]))
                self.assertEqual(answer, as_json({**view_series.activity_spread(data, key, chosen, types), "names": "read"}))
                self.assertGreater(answer["total"], 0)
                self.assertEqual(answer["total"], answer["with_values"] + answer["missing"])
                self.assertEqual(sum(answer["counts"]), answer["with_values"])
                self.assertLessEqual(len(answer["counts"]), answer["limit"])

    def test_requests_for_a_distribution_of_another_form_are_refused(self) -> None:
        ticket = self.open(made_output())
        good = {"view": ticket, "item": "dist", "period": "all", "types": None}
        for change in (
            {"view": None},
            {"view": 3},
            {"item": None},
            {"item": ["dist"]},
            {"item": "nope"},
            # The count and an item of the days are not values of one
            # activity, as for the points.
            {"item": "count"},
            {"item": "rhr"},
            {"item": "vo2"},
            {"period": None},
            {"period": "custom"},
            {"period": {"from": "2024-03-04"}},
            {"period": {"from": "2024-03-10", "to": "2024-03-04"}},
            {"types": "running"},
            {"types": ["running", "running"]},
            {"types": [1]},
            {"types": ["no such type"]},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.call("/api/view/spread", {**good, **change}), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(self.call("/api/view/spread", {**good, "view": "not-a-ticket-of-this-server"}), (409, {"error": "VIEW_NOT_OPEN"}))
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 100):
            self.assertEqual(self.call("/api/view/spread", good), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))
        body = json.dumps(good).encode("utf-8")
        with patch.object(gui_server, "activity_spread", side_effect=RuntimeError("unexpected words")):
            status, _, answer = self.post_api("/api/view/spread", self.api_headers(body), body)
        self.assertEqual(status, 500)
        self.assertNotIn(b"unexpected words", answer)
        self.assertEqual(self.call("/api/view/spread", good)[0], 200)

    def test_the_distribution_is_read_as_the_numbers_are(self) -> None:
        # As the points: no reading of its own while the output does not
        # change, and the codes of the check of the output when it does.
        output = self.copied()
        loads: list[Path] = []

        def counted(place: Path) -> Any:
            loads.append(place)
            return load_view_data(place)

        spread = {"item": "pace", "period": "all", "types": None}
        with patch.object(self.server.views, "_load", counted):
            ticket = self.open(output)
            first = self.call("/api/view/spread", {**spread, "view": ticket})
            self.assertEqual(first[0], 200)
            self.assertEqual(self.call("/api/view/spread", {**spread, "view": ticket}), first)
            self.assertEqual(len(loads), 1)
            activities = output / "analysis" / "activities.csv"
            with activities.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            self.assertEqual(self.call("/api/view/spread", {**spread, "view": ticket}), (422, {"error": "HANDOFF_INVALID"}))
            self.assertEqual(self.call("/api/view/spread", {**spread, "view": ticket}), (409, {"error": "VIEW_NOT_OPEN"}))

    def payloads(self, ticket: str) -> dict[str, dict[str, Any]]:
        """A request of each view that takes conditions (stage T1 of v2.2.0)."""
        return {
            "/api/view/series": {"view": ticket, "items": ["dist", "pace"], "period": "all", "grain": "auto", "types": None},
            "/api/view/activities": {"view": ticket, "item": "dist", "period": {"from": "2024-03-01", "to": "2024-03-31"}, "types": None},
            "/api/view/points": {"view": ticket, "x": "dist", "y": "pace", "period": "all", "types": None},
            "/api/view/spread": {"view": ticket, "item": "pace", "period": "all", "types": None},
            "/api/view/shoes": {"view": ticket, "period": "all", "types": None},
        }

    def test_the_conditions_choose_in_every_view_and_say_their_counts(self) -> None:
        # Stage T1 of v2.2.0, with made-up names of training: every view is
        # that of the functions of the view page with the same conditions,
        # from one reading, and says how many activities were counted and how
        # many of them meet; the list counts those that meet, with their names.
        output = names_output()
        ticket = self.open(output)
        data = load_view(output)
        asked = {"name": " ペース走、tempo ", "distance": [5_000, None], "time": [None, 120]}
        conditions = conditions_from(asked)
        year = (date(2024, 1, 1), date(2024, 12, 31))
        span = {"from": "2024-01-01", "to": "2024-12-31"}
        for path, payload, expected in (
            (
                "/api/view/series",
                {"items": ["dist", "pace", "rhr"], "period": "all", "grain": "auto", "types": None},
                {
                    **view_answer(data, ["dist", "pace", "rhr"], "all", "auto", None, False, conditions),
                    "coverage": coverage(data, None, conditions),
                    "shoes": shoe_count(data),
                },
            ),
            (
                "/api/view/series",
                {"items": ["dist", "count"], "period": "1y", "grain": "range", "types": None, "previous": True},
                {
                    **view_answer(data, ["dist", "count"], "1y", "range", None, True, conditions),
                    "coverage": coverage(data, None, conditions),
                    "shoes": shoe_count(data),
                },
            ),
            (
                "/api/view/activities",
                {"item": "dist", "period": {"from": "2024-03-01", "to": "2024-03-31"}, "types": None},
                view_series.activity_list(data, "dist", (date(2024, 3, 1), date(2024, 3, 31)), None, conditions),
            ),
            ("/api/view/points", {"x": "dist", "y": "pace", "period": span, "types": None}, view_series.activity_points(data, "dist", "pace", year, None, conditions)),
            ("/api/view/spread", {"item": "pace", "period": span, "types": None}, view_series.activity_spread(data, "pace", year, None, conditions)),
            ("/api/view/shoes", {"period": span, "types": None}, shoe_answer(data, year, None, conditions)),
        ):
            with self.subTest(path=path, payload=payload):
                status, answer = self.call(path, {"view": ticket, **payload, "conditions": asked})
                self.assertEqual(status, 200, answer)
                self.assertEqual(answer, as_json({**expected, "names": "read"}))
                if path == "/api/view/activities":
                    self.assertTrue(answer["rows"] and all(row["name"] for row in answer["rows"]))
                    continue
                self.assertEqual(answer["conditions"]["asked"], {"name": "ペース走、tempo", "distance": [5_000, None], "time": [None, 120]})
                self.assertEqual(answer["conditions"]["name"], "used")
                self.assertTrue(0 < answer["conditions"]["met"] < answer["conditions"]["counted"], answer["conditions"])
        # No conditions, or null, are the answer as before, without the line.
        for extra in ({}, {"conditions": None}):
            with self.subTest(extra=extra):
                status, answer = self.call("/api/view/series", {"view": ticket, "items": ["dist"], "period": "all", "grain": "auto", "types": None, **extra})
                self.assertEqual(status, 200)
                self.assertEqual(answer, as_json({**view_answer(data, ["dist"], "all", "auto", None), "coverage": coverage(data, None), "shoes": shoe_count(data), "names": "read"}))

    def test_conditions_of_another_form_are_refused_in_every_view(self) -> None:
        # Stage T1 of v2.2.0: CONDITIONS_INVALID, which the page shows as a
        # stop of the numbers (it checks the conditions before it sends them),
        # with no word of them in the answer (and, as every test of the
        # server, nothing on its standard error).
        ticket = self.open(names_output())
        bad = (
            {}, [], "ペース走", 1, True,
            {"name": ""}, {"name": "   "}, {"name": 1}, {"name": None}, {"name": "、,"},
            {"name": "x" * 61}, {"name": "\U0001F600" * 61},
            {"name": "a\u202eb"}, {"name": "a\nb"}, {"name": "a\u2028b"}, {"name": "a\u061cb"},
            {"name": "、".join(f"w{number}" for number in range(11))},
            # Ten words and one of U+FEFF only, which str.strip keeps (the
            # checker's review of the diff of T1).
            {"name": ",".join(f"w{number}" for number in range(10)) + "," + chr(0xFEFF)},
            {"distance": [1]}, {"distance": [1, 2, 3]}, {"distance": [None, None]}, {"distance": [2, 1]}, {"distance": [-1, None]},
            {"distance": [1.5, None]}, {"distance": [10.0, None]}, {"distance": [True, None]}, {"distance": ["1", None]},
            {"distance": [None, 1_000_001]}, {"distance": {"from": 1}}, {"distance": None},
            {"time": [None, 6_001]}, {"time": [False, 1]}, {"time": "1"}, {"time": [90, 60]},
            {"other": 1}, {"name": "x", "other": 1},
        )
        for path, payload in self.payloads(ticket).items():
            for conditions in bad:
                with self.subTest(path=path, conditions=conditions):
                    self.assertEqual(self.call(path, {**payload, "conditions": conditions}), (422, {"error": "CONDITIONS_INVALID"}))
        # The bounds themselves are of the form; the words are counted after
        # those that are the same are left out.
        for conditions in (
            {"name": "x" * 60},
            {"name": "\U0001F600" * 60},
            {"name": "、".join(f"w{number}" for number in range(10))},
            {"name": "、".join("w" for _ in range(11))},
            {"distance": [0, 0]},
            {"distance": [None, 1_000_000]},
            {"time": [6_000, None]},
            {"name": " ペース走 ", "distance": [5_000, 10_000], "time": [20, 90]},
        ):
            for path, payload in self.payloads(ticket).items():
                with self.subTest(path=path, conditions=conditions):
                    self.assertEqual(self.call(path, {**payload, "conditions": conditions})[0], 200)

    def test_every_answer_says_whether_the_names_were_read(self) -> None:
        # Codex 5 of the plan of T1: any request may read the output again, so
        # the opening and every answer of a view say it. With the names left
        # out for the limits, the words choose nothing (the checker's A-3):
        # conditions of a name only count every activity, the list has no
        # names, and the other conditions choose alone.
        output = names_output()
        for state, names in (("read", None), ("too_large", view_data.Names({}, {}, too_large=True))):
            with self.subTest(state=state), patch.object(view_data, "_names", wraps=view_data._names) as read:
                if names is not None:
                    read.side_effect = None
                    read.return_value = names
                status, opened = self.call("/api/view/open", {"output": "chosen", "path": str(output)})
                self.assertEqual((status, opened["names"]), (200, state))
                for path, payload in self.payloads(opened["view"]).items():
                    status, answer = self.call(path, {**payload, "conditions": {"name": "ペース走", "distance": [5_000, None]}})
                    self.assertEqual((status, answer["names"]), (200, state), path)
                    if path == "/api/view/activities":
                        self.assertEqual({row["name"] is None for row in answer["rows"]}, {state == "too_large"})
                    else:
                        self.assertEqual(answer["conditions"]["name"], "used" if state == "read" else "unread")
                status, answer = self.call("/api/view/series", {**self.payloads(opened["view"])["/api/view/series"], "conditions": {"name": "ペース走"}})
                counts = answer["conditions"]
                self.assertEqual(counts["met"] == counts["counted"], state == "too_large", counts)

    def test_no_answer_holds_the_memo_the_place_or_the_hash_of_the_names(self) -> None:
        # Codex 19 of the plan of T1: of activities.json, only the names may
        # show, and the words of the conditions as they were given.
        output = names_output()
        written = json.loads((output / view_data.NAMES).read_text(encoding="utf-8"))
        hidden = {MEMO_MARK} | {record["source_path"] for record in written} | {record["source_sha256"] for record in written}
        status, opened = self.call("/api/view/open", {"output": "chosen", "path": str(output)})
        answers: list[Any] = [opened]
        for path, payload in self.payloads(opened["view"]).items():
            for conditions in (None, {"name": "ペース走"}):
                status, answer = self.call(path, {**payload, "conditions": conditions})
                self.assertEqual(status, 200, answer)
                answers.append(answer)
        shown = json.dumps(answers, ensure_ascii=False)
        self.assertIn("ﾍﾟｰｽ走 朝", shown)
        for value in hidden:
            self.assertNotIn(value, shown)

    def test_the_view_page_needs_the_launch_key(self) -> None:
        body = json.dumps({"output": "chosen", "path": str(made_output())}).encode("utf-8")
        headers = [header for header in self.api_headers(body) if header[0] != gui_server.LAUNCH_KEY_HEADER]
        for path in ("/api/view/open", "/api/view/series", "/api/view/activities", "/api/view/points", "/api/view/spread", "/api/settings/view"):
            with self.subTest(path=path):
                status, _, answer = self.post_api(path, headers, body)
                self.assertEqual((status, json.loads(answer)), (403, {"error": "FORBIDDEN"}))


class ViewsTest(unittest.TestCase):
    """The outputs that the view page opened, without a server."""

    def test_reading_takes_no_lock_of_the_server(self) -> None:
        # The reading can take seconds; the other requests are answered
        # meanwhile, so the lock of the outputs is free while it reads.
        reading, release = threading.Event(), threading.Event()

        def slow(place: Path) -> Any:
            reading.set()
            if not release.wait(TIMEOUT_SECONDS):
                raise AssertionError("the test did not let the reading go on")
            return load_view_data(place)

        views = Views(load=slow)
        answers: list[Any] = []
        thread = threading.Thread(target=lambda: answers.append(views.open(made_output())))
        thread.start()
        self.assertTrue(reading.wait(TIMEOUT_SECONDS))
        acquired = views._lock.acquire(blocking=False)
        if acquired:
            views._lock.release()
        release.set()
        thread.join(TIMEOUT_SECONDS)
        self.assertTrue(acquired, "the lock of the outputs was held while an output was read")
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(answers), 1)

    def test_an_output_that_changes_while_it_is_read_is_not_kept(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name).resolve() / "output"
        shutil.copytree(made_output(), output)

        def touched(place: Path) -> Any:
            data = load_view_data(place)
            manifest = place / "run_manifest.json"
            later = manifest.stat().st_mtime_ns + 2_000_000_000
            os.utime(manifest, ns=(later, later))
            return data

        views = Views(load=touched)
        with self.assertRaises(OutputActionError) as raised:
            views.open(output)
        self.assertEqual(raised.exception.code, "OUTPUT_CHANGED")
        self.assertEqual(len(views._views), 0)

    def test_the_stamp_follows_the_files_that_the_view_page_reads(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name).resolve() / "output"
        shutil.copytree(made_output(), output)
        stamp = output_stamp(output)
        self.assertEqual(output_stamp(output), stamp)
        # A file that the view page does not read leaves the stamp as it is.
        (output / "START_HERE.md").write_text("changed\n", encoding="utf-8")
        self.assertEqual(output_stamp(output), stamp)
        vo2max = output / "normalized" / "vo2max_daily.json"
        later = vo2max.stat().st_mtime_ns + 2_000_000_000
        os.utime(vo2max, ns=(later, later))
        self.assertNotEqual(output_stamp(output), stamp)
        # The files of the shoes too, each alone (stage S1 of v2.2.0).
        for name in ("gear.json", "activity_gear.json"):
            stamp = output_stamp(output)
            shoes = output / "normalized" / name
            later = shoes.stat().st_mtime_ns + 2_000_000_000
            os.utime(shoes, ns=(later, later))
            self.assertNotEqual(output_stamp(output), stamp, name)
        # The file of the names alone too (stage T1).
        stamp = output_stamp(output)
        names = output / "normalized" / "activities.json"
        later = names.stat().st_mtime_ns + 2_000_000_000
        os.utime(names, ns=(later, later))
        self.assertNotEqual(output_stamp(output), stamp)


    def test_the_bars_of_the_shelf_are_kept_for_the_reading_of_the_ticket_only(self) -> None:
        # Stage M2 of v2.2.0. The number of the plan, written as it is.
        self.assertEqual(MAX_SHELVES, 8)
        real = gui_views.coverage
        made: list[Any] = []

        def counted(data: Any, types: Any = None, conditions: Any = None) -> Any:
            made.append(types)
            return real(data, types, conditions)

        views = Views()
        ticket, data = views.open(made_output())
        with patch.object(gui_views, "coverage", counted):
            # At most eight sets of types; the one used longest ago leaves
            # first.
            kinds = [[f"type {number}"] for number in range(MAX_SHELVES + 1)]
            for types in kinds:
                self.assertEqual(views.coverage(ticket, data, types), real(data, types))
            self.assertEqual(len(made), MAX_SHELVES + 1)
            views.coverage(ticket, data, kinds[-1])
            self.assertEqual(len(made), MAX_SHELVES + 1)
            views.coverage(ticket, data, kinds[0])
            self.assertEqual(len(made), MAX_SHELVES + 2)
            # Another reading of the output, and a ticket that is gone: the
            # bars are made and not kept.
            other = load_view_data(made_output())
            for _ in range(2):
                self.assertEqual(views.coverage(ticket, other), real(other))
                self.assertEqual(views.coverage("gone", data), real(data))
            self.assertEqual(len(made), MAX_SHELVES + 6)

    def test_the_bars_of_the_shelf_are_kept_by_their_conditions_too(self) -> None:
        # The checker's A-2 of the plan of T1: other conditions with the same
        # types make other bars; the same conditions, written again, are made
        # once.
        real = gui_views.coverage
        made: list[Any] = []

        def counted(data: Any, types: Any = None, conditions: Any = None) -> Any:
            made.append((types, conditions))
            return real(data, types, conditions)

        views = Views()
        ticket, data = views.open(names_output())
        bounds = conditions_from({"name": "境目"})
        far = conditions_from({"distance": [10_000, None]})
        with patch.object(gui_views, "coverage", counted):
            plain = views.coverage(ticket, data)
            chosen = views.coverage(ticket, data, None, bounds)
            self.assertEqual((chosen["dist"]["months"], chosen, plain), (["2024-06"], real(data, None, bounds), real(data)))
            self.assertEqual(views.coverage(ticket, data, None, far), real(data, None, far))
            self.assertEqual(len(made), 3)
            views.coverage(ticket, data, None, conditions_from({"name": "境目"}))
            views.coverage(ticket, data)
            self.assertEqual(len(made), 3)
            views.coverage(ticket, data, ["running"], bounds)
            self.assertEqual(len(made), 4)
            # Another reading of the output, and a ticket that is gone: the
            # bars are made with the conditions, and not kept.
            other = load_view(names_output())
            self.assertEqual(views.coverage(ticket, other, None, bounds), real(other, None, bounds))
            self.assertEqual(views.coverage("gone", data, None, bounds), real(data, None, bounds))
            self.assertEqual(made[-2:], [(None, bounds), (None, bounds)])

    def test_conditions_have_their_form(self) -> None:
        # Stage T1 of v2.2.0: the words as written without the spaces at the
        # ends, and as compared; null or no conditions are none.
        self.assertEqual(
            conditions_from({"name": " ペース走、ﾍﾟｰｽ走 ", "time": [None, 60]}),
            Conditions("ペース走、ﾍﾟｰｽ走", ("ペース走",), (None, None), (None, 60)),
        )
        self.assertEqual(conditions_from({"distance": [None, 5]}).asked(), {"distance": [None, 5]})
        self.assertIsNone(conditions_request({}))
        self.assertIsNone(conditions_request({"conditions": None}))
        with self.assertRaises(ConditionsRequestError):
            conditions_request({"conditions": {}})
        self.assertTrue(issubclass(ConditionsRequestError, ViewRequestError))

    def test_a_request_for_numbers_has_its_form(self) -> None:
        self.assertEqual(
            series_request({"items": ["dist", "rhr"], "period": "5y", "grain": "week", "types": ["running"]}),
            (["dist", "rhr"], "5y", "week", ["running"]),
        )
        self.assertEqual(
            series_request({"items": ["vo2"], "period": {"from": "2024-01-01", "to": "2024-01-01"}}),
            (["vo2"], (date(2024, 1, 1), date(2024, 1, 1)), "auto", None),
        )
        for payload in ({}, {"items": ["dist"], "period": None}, {"items": ["dist"], "grain": None}, {"items": ["dist"], "types": [None]}):
            with self.subTest(payload=payload):
                with self.assertRaises(ViewRequestError):
                    series_request(payload)
        # Stage Q1 of v2.2.0: the period before, a truth value only (as the
        # month of a comparison is an integer only), true with the whole
        # period only, and false where the request leaves it out.
        self.assertIs(previous_request({}, "auto"), False)
        self.assertIs(previous_request({"previous": False}, "week"), False)
        self.assertIs(previous_request({"previous": True}, "range"), True)
        for previous, grain in ((1, "range"), ("true", "range"), (None, "range"), (0, "range"), (True, "auto"), (True, "month")):
            with self.subTest(previous=previous, grain=grain):
                with self.assertRaises(ViewRequestError):
                    previous_request({"previous": previous}, grain)

    def test_a_request_for_the_activities_of_a_period_has_its_form(self) -> None:
        # Stage M3 of v2.2.0: an item of the activities, the days of one
        # period, and the activity types or None.
        self.assertEqual(
            list_request({"item": "pace", "period": {"from": "2024-03-04", "to": "2024-03-10"}, "types": ["running"]}),
            ("pace", (date(2024, 3, 4), date(2024, 3, 10)), ["running"]),
        )
        self.assertEqual(
            list_request({"item": "pow", "period": {"from": "2024-03-04", "to": "2024-03-04"}}),
            ("pow", (date(2024, 3, 4), date(2024, 3, 4)), None),
        )
        for payload in (
            {},
            {"item": "dist"},
            {"item": "dist", "period": "1y"},
            {"item": "sleep", "period": {"from": "2024-03-04", "to": "2024-03-10"}},
            {"item": "dist", "period": {"from": "2024-03-04", "to": "2024-03-10"}, "types": [None]},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ViewRequestError):
                    list_request(payload)


if __name__ == "__main__":
    unittest.main()
