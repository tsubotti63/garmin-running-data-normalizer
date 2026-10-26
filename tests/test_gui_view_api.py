"""The API of the view page (stage G3b): an output opened under a ticket that
holds no place, and its numbers, which are those of the functions of stage
G1, read once and again when the output changes.

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
from garmin_running_data_normalizer.gui.views import (
    MAX_VIEWS,
    ViewRequestError,
    Views,
    item_table,
    output_stamp,
    series_request,
)
from garmin_running_data_normalizer.output_check import OutputActionError
from garmin_running_data_normalizer.run_all import RUN_ALL_VERSION, run_all
from garmin_running_data_normalizer.view import data as view_data
from garmin_running_data_normalizer.view.data import load_view_data
from garmin_running_data_normalizer.view.items import ITEMS
from garmin_running_data_normalizer.view.series import activity_types, coverage, default_items, view_answer
from tests.test_gui_server import GuiServerTestCase
from tests.v1_3_outputs import as_release, as_v1_3
from tests.view_export import write_view_export

TIMEOUT_SECONDS = 10.0
_MADE: dict[str, Any] = {}


def setUpModule() -> None:
    directory = tempfile.TemporaryDirectory()
    root = Path(directory.name).resolve()
    run_all(write_view_export(root / "export"), root / "output")
    _MADE.update(directory=directory, output=root / "output")


def tearDownModule() -> None:
    _MADE["directory"].cleanup()


def made_output() -> Path:
    return _MADE["output"]


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
            {"view", "name", "version", "partial", "first_day", "last_day", "items", "types", "first_items", "coverage"},
        )
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
        self.assertEqual(answer["coverage"], as_json(coverage(data)))
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
        )
        for items, period, grain, types, chosen in cases:
            with self.subTest(items=items, period=period, grain=grain):
                status, answer = self.call(
                    "/api/view/series", {"view": ticket, "items": items, "period": period, "grain": grain, "types": types}
                )
                self.assertEqual(status, 200)
                expected = view_answer(data, items, chosen, grain, types)
                expected["coverage"] = coverage(data, types)
                self.assertEqual(answer, as_json(expected))

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
        ):
            with self.subTest(change=change):
                self.assertEqual(self.call("/api/view/series", {**good, **change}), (422, {"error": "REQUEST_INVALID"}))

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
        # then says that something went wrong, and the server goes on.
        ticket = self.open(made_output())
        payload = {"view": ticket, "items": ["dist"], "period": "all", "grain": "auto", "types": None}
        body = json.dumps(payload).encode("utf-8")
        for name in ("view_answer", "coverage"):
            with self.subTest(function=name), patch.object(gui_server, name, side_effect=RuntimeError("unexpected words")):
                status, _, answer = self.post_api("/api/view/series", self.api_headers(body), body)
                self.assertEqual(status, 500)
                self.assertNotIn(b"unexpected words", answer)
        self.assertEqual(self.call("/api/view/series", payload)[0], 200)

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

    def test_the_view_page_needs_the_launch_key(self) -> None:
        body = json.dumps({"output": "chosen", "path": str(made_output())}).encode("utf-8")
        headers = [header for header in self.api_headers(body) if header[0] != gui_server.LAUNCH_KEY_HEADER]
        for path in ("/api/view/open", "/api/view/series", "/api/settings/view"):
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


if __name__ == "__main__":
    unittest.main()
