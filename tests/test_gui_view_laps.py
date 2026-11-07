"""The laps of one activity through the server of the view page (stage X9c-2
of v2.3.0): /api/view/laps reads the FIT file of the activity from the
Snapshot Store that the GUI remembers (gui.fit_reading); the list of a period
gives the number of its reading and the place of each row among the
activities of that reading, by which the page names the activity. From
stage X10, the list also gives why the laps of a row cannot be shown where
the output alone tells it (laps_unavailable), the same as pressing tells,
and the laps give their maximum heart rate.

The output and the store are made as the CLI and the GUI make them
(tests.test_gui_fit_reading.build: a synthetic Export registered in a store
and normalized from it with run_snapshot_all), and the store is remembered as
a Snapshot run of the GUI remembers it (settings.remember_run), in the
settings of each test (tests/conftest.py). Every test has its own server.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer.gui import places
from garmin_running_data_normalizer.gui import server as gui_server
from garmin_running_data_normalizer.gui import settings as gui_settings
from garmin_running_data_normalizer.gui import views as gui_views
from garmin_running_data_normalizer.gui.fit_reading import LAP_FILES, LAPS, LINKS, REASONS, SESSIONS, read_laps
from garmin_running_data_normalizer.gui.views import load_view, output_stamp
from garmin_running_data_normalizer.output_check import OutputActionError
from garmin_running_data_normalizer.view import data as view_data
from garmin_running_data_normalizer.view import series as view_series
from garmin_running_data_normalizer.view.data import load_view_data
from garmin_running_data_normalizer.view.items import ACTIVITIES
from garmin_running_data_normalizer.view.series_file import SERIES_COLUMNS, write_series
from tests.test_gui_fit_reading import NAMES, build, entries, load, remove_folder
from tests.test_gui_server import GuiServerTestCase
from tests.test_view_series import keyed
from tests.test_view_series import view_data as made_view_data

_MADE: dict[str, Any] = {}
# The facts of a reading of an output that the answers give, as the answer
# of opening gives them (stage W1 of v2.2.1).
OUTPUT_FACTS = ("first_day", "last_day", "types", "partial")
# The fields of a lap that the answer gives, and no other.
LAP_FIELDS = {"kind", "elapsed_s", "timer_s", "distance_m", "avg_heart_rate", "max_heart_rate", "avg_cadence", "avg_speed"}
# Why the laps of a row of the list cannot be shown, where the output alone
# tells it before a file is read (stage X10 of v2.3.0).
KNOWN_FROM_THE_OUTPUT = (None, "key_shared", "not_from_store")
NOT_A_TICKET = "not-a-ticket-of-this-server"


def setUpModule() -> None:
    directory = tempfile.TemporaryDirectory()
    root = Path(directory.name).resolve()
    # One running activity whose FIT file records the kinds of its laps,
    # normalized from a store; and the same activity normalized without one.
    build(root / "kinds")
    build(root / "plain", store=False)
    # An activity whose FIT file records no kind of its laps.
    build(root / "no_kinds", None)
    _MADE.update(directory=directory, root=root)


def tearDownModule() -> None:
    _MADE["directory"].cleanup()


def as_json(value: Any) -> Any:
    """A value as an answer of the server reads after JSON."""
    return json.loads(json.dumps(value))


def day_of(output: Path) -> str:
    """The day of the one activity of a made output."""
    [row] = load_view_data(output).rows[ACTIVITIES]
    return date.fromordinal(row.day).isoformat()


@contextlib.contextmanager
def holding(lock: threading.Lock) -> Iterator[None]:
    """The lock of the laps held by the test, as a reading of laps holds it.
    A lock that an answer did not let go fails the test, not waited for
    without end."""
    if not lock.acquire(timeout=10):
        raise AssertionError("an answer did not let the lock of the laps go")
    try:
        yield
    finally:
        lock.release()


def unblock(pipe: Path) -> None:
    """Open a pipe for writing once, where a reading waits for it, so that
    the reading ends (after a test whose reading waited)."""
    try:
        descriptor = os.open(pipe, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        return
    os.close(descriptor)


class LapsApiTest(GuiServerTestCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.place = Path(directory.name).resolve()

    def copy(self, name: str = "kinds") -> tuple[Path, Path]:
        """The output and the store of a copy of ``name``."""
        root = self.place / f"{name}-{len(list(self.place.iterdir()))}"
        shutil.copytree(_MADE["root"] / name, root, symlinks=True)
        return root / "out", root / "store"

    def call(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def open(self, output: Path) -> dict[str, Any]:
        status, answer = self.call("/api/view/open", {"output": "chosen", "path": str(output)})
        self.assertEqual(status, 200, answer)
        return answer

    def listed(self, ticket: str, start: str, end: str | None = None) -> dict[str, Any]:
        payload = {"view": ticket, "item": "dist", "period": {"from": start, "to": end or start}, "types": None}
        status, answer = self.call("/api/view/activities", payload)
        self.assertEqual(status, 200, answer)
        return answer

    def remembered(self, name: str = "kinds") -> tuple[Path, Path, dict[str, Any]]:
        """A copy whose store the settings remember, as a Snapshot run of the
        GUI leaves them, and the answer of opening its output."""
        output, store = self.copy(name)
        self.assertIsNone(gui_settings.remember_run(output, store))
        return output, store, self.open(output)

    def facts(self, opened: dict[str, Any]) -> dict[str, Any]:
        return {name: opened[name] for name in OUTPUT_FACTS}

    def assert_the_list_tells_as_pressing(self, opened: dict[str, Any], listed: dict[str, Any]) -> None:
        """Every row of the list gives why its laps cannot be shown where the
        output alone tells it, as pressing it answers (stage X10 of v2.3.0);
        a row of none is one whose laps the server reads, or tells another
        reason of."""
        self.assertTrue(listed["rows"])
        for row in listed["rows"]:
            with self.subTest(ref=row["ref"]):
                self.assertIn(row["laps_unavailable"], KNOWN_FROM_THE_OUTPUT)
                status, answer = self.call("/api/view/laps", {"view": opened["view"], "read": listed["read"], "ref": row["ref"]})
                self.assertEqual(status, 200, answer)
                if row["laps_unavailable"] is None:
                    self.assertTrue(answer["status"] == "laps" or answer["reason"] not in KNOWN_FROM_THE_OUTPUT, answer)
                else:
                    self.assertEqual((answer["status"], answer["reason"]), ("unavailable", row["laps_unavailable"]))

    def test_the_reasons_are_thirteen_in_their_order(self) -> None:
        # Those of gui.fit_reading, then the two of the server, which the page
        # tells apart by these names from stage X10 (the words of the page).
        self.assertEqual(
            gui_server.LAP_REASONS,
            (
                "not_from_store",
                "no_store",
                "other_store",
                "store_unreadable",
                "no_link",
                "key_shared",
                "fit_missing",
                "fit_too_large",
                "fit_changed",
                "fit_not_activity",
                "laps_differ",
                "read_stale",
                "busy",
            ),
        )
        self.assertEqual(gui_server.LAP_REASONS[: len(REASONS)], REASONS)

    def test_the_laps_of_an_activity_with_the_kinds_of_its_fit_file(self) -> None:
        output, store, opened = self.remembered()
        self.assertEqual(gui_settings.remembered_store(), store)
        listed = self.listed(opened["view"], day_of(output))
        # The list gives the number of its reading, that of the opening here,
        # and the place of its row among the activities of that reading.
        self.assertEqual(listed["read"], opened["read"])
        [row] = listed["rows"]
        self.assertEqual(row["ref"], 0)
        self.assertIsNone(row["laps_unavailable"])
        status, answer = self.call("/api/view/laps", {"view": opened["view"], "read": listed["read"], "ref": row["ref"]})
        self.assertEqual(status, 200, answer)
        self.assertEqual(set(answer), {"status", "laps", "counts", "read", "output"})
        self.assertEqual(answer["status"], "laps")
        self.assertEqual([lap["kind"] for lap in answer["laps"]], NAMES)
        self.assertEqual(answer["counts"], {"laps": len(NAMES), "unknown_kind": 0})
        for lap in answer["laps"]:
            self.assertEqual(set(lap), LAP_FIELDS)
        # The values are those of gui.fit_reading, by the key of the row.
        key = load(output / LINKS)[0]["garmin_activity_key"]
        laps = read_laps(output, entries(output), key, store)
        self.assertEqual(answer["laps"], as_json([dataclasses.asdict(lap) for lap in laps.laps]))
        # The maximum heart rate of each lap is the output's (stage X10).
        rows = sorted(load(output / LAPS), key=lambda lap: lap["lap_ordinal_within_session"])
        self.assertEqual([lap["max_heart_rate"] for lap in answer["laps"]], [lap["max_heart_rate"] for lap in rows])
        self.assertTrue(all(lap["max_heart_rate"] is not None for lap in answer["laps"]))
        self.assert_the_list_tells_as_pressing(opened, listed)
        self.assertEqual((answer["read"], answer["output"]), (listed["read"], self.facts(opened)))
        # No place, SHA-256, or key reaches the page, in the list or the laps.
        text = json.dumps([listed, answer])
        secrets = [str(output.parent), output.parent.name, key, load(output / SESSIONS)[0]["source_sha256"]]
        secrets.extend(digest for _size, digest in entries(output).values())
        for secret in secrets:
            self.assertNotIn(secret, text)

    def test_laps_of_no_known_kind_are_counted(self) -> None:
        output, store, opened = self.remembered("no_kinds")
        listed = self.listed(opened["view"], day_of(output))
        status, answer = self.call("/api/view/laps", {"view": opened["view"], "read": listed["read"], "ref": 0})
        self.assertEqual(status, 200, answer)
        laps = read_laps(output, entries(output), load(output / LINKS)[0]["garmin_activity_key"], store)
        self.assertGreater(laps.unknown_kind, 0)
        self.assertEqual(answer["counts"], {"laps": len(laps.laps), "unknown_kind": laps.unknown_kind})
        self.assertEqual({lap["kind"] for lap in answer["laps"]}, {"unknown"})

    def test_an_output_made_without_a_store(self) -> None:
        output, _none = self.copy("plain")
        _other, store = self.copy()
        self.assertIsNone(gui_settings.remember_run(output, store))
        opened = self.open(output)
        listed = self.listed(opened["view"], day_of(output))
        self.assertEqual(
            self.call("/api/view/laps", {"view": opened["view"], "read": listed["read"], "ref": listed["rows"][0]["ref"]}),
            (200, {"status": "unavailable", "reason": "not_from_store", "read": listed["read"], "output": self.facts(opened)}),
        )
        # The list tells it before the button is pressed (stage X10).
        self.assertEqual([row["laps_unavailable"] for row in listed["rows"]], ["not_from_store"])
        self.assert_the_list_tells_as_pressing(opened, listed)

    def test_the_store_is_the_one_that_the_settings_remember_at_each_request(self) -> None:
        output, store = self.copy()
        opened = self.open(output)
        payload = {"view": opened["view"], "read": opened["read"], "ref": 0}
        no_store = (200, {"status": "unavailable", "reason": "no_store", "read": opened["read"], "output": self.facts(opened)})
        settings = places.settings_file()
        # No settings: no store.
        self.assertFalse(settings.exists())
        self.assertIsNone(gui_settings.remembered_store())
        self.assertEqual(self.call("/api/view/laps", payload), no_store)
        # The settings of a run without a store.
        self.assertIsNone(gui_settings.remember_run(output, None))
        self.assertIsNone(gui_settings.remembered_store())
        self.assertEqual(self.call("/api/view/laps", payload), no_store)
        # The store of a Snapshot run, from the next request on.
        self.assertIsNone(gui_settings.remember_run(output, store))
        self.assertEqual(self.call("/api/view/laps", payload)[1]["status"], "laps")
        # Settings that cannot be read, of another form, or of a newer
        # version are not used: no store.
        newer = f"{gui_settings._FORMAT_PREFIX}{gui_settings._FORMAT_VERSION + 1}"
        for content in (
            b"{",
            json.dumps({"format": gui_settings.SETTINGS_FORMAT, "store": "a/relative/store"}).encode("utf-8"),
            json.dumps({"format": newer, "store": str(store)}).encode("utf-8"),
        ):
            with self.subTest(content=content):
                settings.write_bytes(content)
                self.assertIsNone(gui_settings.remembered_store())
                self.assertEqual(self.call("/api/view/laps", payload), no_store)
        # A remembered store that is no longer there.
        settings.unlink()
        self.assertIsNone(gui_settings.remember_run(output, store))
        remove_folder(store)
        self.assertEqual(gui_settings.remembered_store(), store)
        self.assertEqual(self.call("/api/view/laps", payload), no_store)

    def test_requests_of_another_form_are_refused(self) -> None:
        _output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        self.assertEqual(self.call("/api/view/laps", good)[1]["status"], "laps")
        for change in (
            {"view": None},
            {"view": 3},
            {"read": None},
            {"read": "1"},
            {"read": True},
            {"read": -1},
            {"read": 1.0},
            {"read": [1]},
            {"ref": None},
            {"ref": "0"},
            {"ref": False},
            {"ref": -1},
            {"ref": 0.0},
            {"ref": {}},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.call("/api/view/laps", {**good, **change}), (422, {"error": "REQUEST_INVALID"}))
        for name in good:
            with self.subTest(left_out=name):
                kept = {key: value for key, value in good.items() if key != name}
                self.assertEqual(self.call("/api/view/laps", kept), (422, {"error": "REQUEST_INVALID"}))
        # A place beyond the activities of the reading.
        for ref in (1, 10**40):
            with self.subTest(ref=ref):
                self.assertEqual(self.call("/api/view/laps", {**good, "ref": ref}), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(self.call("/api/view/laps", {**good, "view": NOT_A_TICKET}), (409, {"error": "VIEW_NOT_OPEN"}))

    def test_another_reading_of_a_store_is_told_busy_at_once(self) -> None:
        _output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        busy = (200, {"status": "unavailable", "reason": "busy", "read": opened["read"], "output": self.facts(opened)})
        # While a reading of a store holds the lock: told at once, with the
        # facts of the reading. The lock is taken once the output is read and
        # the activity found, so that a request of another form, a ticket
        # that is not open, and a place of another reading are told as such.
        with holding(self.server.laps_lock):
            self.assertEqual(self.call("/api/view/laps", good), busy)
            self.assertEqual(self.call("/api/view/laps", {**good, "ref": -1}), (422, {"error": "REQUEST_INVALID"}))
            self.assertEqual(self.call("/api/view/laps", {**good, "view": NOT_A_TICKET}), (409, {"error": "VIEW_NOT_OPEN"}))
            self.assertEqual(self.call("/api/view/laps", {**good, "read": opened["read"] + 1})[1]["reason"], "read_stale")
        # A reading under way, while it reads the store: the other is told
        # busy, and the first gives its laps.
        started, go = threading.Event(), threading.Event()
        real = gui_server.read_laps

        def slow(*args: Any) -> Any:
            started.set()
            go.wait(10)
            return real(*args)

        answers: list[tuple[int, dict[str, Any]]] = []
        with patch.object(gui_server, "read_laps", side_effect=slow):
            first = threading.Thread(target=lambda: answers.append(self.call("/api/view/laps", good)))
            first.start()
            try:
                self.assertTrue(started.wait(10))
                self.assertEqual(self.call("/api/view/laps", good), busy)
            finally:
                go.set()
                first.join(10)
        self.assertFalse(first.is_alive())
        self.assertEqual([answer[1]["status"] for answer in answers], ["laps"])
        self.assertEqual(self.call("/api/view/laps", good)[1]["status"], "laps")

    def test_the_lock_is_not_held_while_the_output_is_read(self) -> None:
        # A reading of the output that waits keeps the lock of the store free
        # (Codex's read of the diff of X9c-2), so that the laps of the other
        # outputs are not told busy meanwhile.
        _output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        started, go = threading.Event(), threading.Event()
        real = self.server.views.lap_reading

        def waiting(ticket: str) -> Any:
            started.set()
            go.wait(10)
            return real(ticket)

        answers: list[tuple[int, dict[str, Any]]] = []
        with patch.object(self.server.views, "lap_reading", side_effect=waiting):
            first = threading.Thread(target=lambda: answers.append(self.call("/api/view/laps", good)))
            first.start()
            try:
                self.assertTrue(started.wait(10))
                self.assertFalse(self.server.laps_lock.locked())
            finally:
                go.set()
                first.join(10)
        self.assertFalse(first.is_alive())
        self.assertEqual([answer[1]["status"] for answer in answers], ["laps"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "pipes in folders are of macOS and Linux")
    def test_a_pipe_put_in_place_of_the_settings_is_not_waited_for(self) -> None:
        # The settings are read while the lock of the store is held: a pipe
        # put in their place between their look and their opening is refused,
        # not waited for (Codex's read of the diff of X9c-2), and no store is
        # remembered then.
        _output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        settings = places.settings_file()
        real_open = os.open
        swapped: list[bool] = []

        def opening(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
            if not swapped and os.fspath(path) == os.fspath(settings):
                swapped.append(True)
                pipe = settings.with_name("pipe")
                os.mkfifo(pipe)
                os.replace(pipe, settings)
            return real_open(path, flags, *args, **kwargs)

        self.addCleanup(unblock, settings)
        started = time.monotonic()
        with patch.object(os, "open", side_effect=opening):
            answer = self.call("/api/view/laps", good)
        self.assertLess(time.monotonic() - started, 5.0)
        self.assertEqual(swapped, [True])
        self.assertEqual(answer, (200, {"status": "unavailable", "reason": "no_store", "read": opened["read"], "output": self.facts(opened)}))
        self.assertFalse(self.server.laps_lock.locked())

    def test_the_lock_is_let_go_after_every_answer(self) -> None:
        _output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        for payload, expected in (
            (good, (200, "laps")),
            ({**good, "read": opened["read"] + 1}, (200, "unavailable")),
            ({**good, "ref": 1}, (422, None)),
            ({**good, "view": NOT_A_TICKET}, (409, None)),
        ):
            with self.subTest(payload=payload):
                status, answer = self.call("/api/view/laps", payload)
                self.assertEqual((status, answer.get("status")), expected)
                self.assertFalse(self.server.laps_lock.locked())
        # An error that no code describes answers as an unexpected error of
        # the reading of the output does (COMMAND_FAILED), without its words;
        # the codes of the output are given.
        body = json.dumps(good).encode("utf-8")
        for name in ("read_laps", "remembered_store"):
            with self.subTest(failing=name), patch.object(gui_server, name, side_effect=RuntimeError("unexpected words")):
                status, _, answer = self.post_api("/api/view/laps", self.api_headers(body), body)
                self.assertEqual((status, json.loads(answer)), (500, {"error": "COMMAND_FAILED"}))
                self.assertNotIn(b"unexpected words", answer)
                self.assertFalse(self.server.laps_lock.locked())
        with patch.object(gui_server, "read_laps", side_effect=OutputActionError("OUTPUT_CHANGED")):
            self.assertEqual(self.call("/api/view/laps", good), (422, {"error": "OUTPUT_CHANGED"}))
        self.assertFalse(self.server.laps_lock.locked())
        with patch.object(self.server.views, "lap_reading", side_effect=RuntimeError("unexpected words")):
            self.assertEqual(self.call("/api/view/laps", good), (500, {"error": "COMMAND_FAILED"}))
        self.assertFalse(self.server.laps_lock.locked())
        self.assertEqual(self.call("/api/view/laps", good)[1]["status"], "laps")

    def test_a_place_of_another_reading_is_stale(self) -> None:
        output, _store, opened = self.remembered()
        first = opened["read"]
        good = {"view": opened["view"], "read": first, "ref": 0}

        def stale(read: int) -> tuple[int, dict[str, Any]]:
            return 200, {"status": "unavailable", "reason": "read_stale", "read": read, "output": self.facts(opened)}

        # A number that is not that of the reading now, also 0, is told with
        # the number now, by which the page asks for the list again.
        for read in (first + 1, 0):
            with self.subTest(read=read):
                self.assertEqual(self.call("/api/view/laps", {**good, "read": read}), stale(first))
        # A file of the laps alone whose time of change moved: the output is
        # read again, with a new number.
        lineage = output / LAP_FILES[0]
        later = lineage.stat().st_mtime_ns + 2_000_000_000
        os.utime(lineage, ns=(later, later))
        status, answer = self.call("/api/view/laps", good)
        second = answer.get("read")
        self.assertIsInstance(second, int)
        self.assertGreater(second, first)
        self.assertEqual((status, answer), stale(second))
        self.assertEqual(self.listed(opened["view"], day_of(output))["read"], second)
        self.assertEqual(self.call("/api/view/laps", {**good, "read": second})[1]["status"], "laps")
        # A new day reads the output again too (stage U1 of v2.2.0): the day
        # of the server and that of the reading, as on a new day.
        real_today = view_data.local_today

        def tomorrow(zone: str) -> date:
            return real_today(zone) + timedelta(days=1)

        with patch.object(self.server.views, "_today", tomorrow), patch.object(view_data, "local_today", tomorrow):
            status, answer = self.call("/api/view/laps", {**good, "read": second})
            third = answer.get("read")
            self.assertIsInstance(third, int)
            self.assertGreater(third, second)
            self.assertEqual((status, answer), stale(third))
            self.assertEqual(self.call("/api/view/laps", {**good, "read": third})[1]["status"], "laps")

    def test_a_file_of_the_laps_changed_under_the_same_stamp(self) -> None:
        # The reading of the page stays (the same size, time, and identity),
        # but the bytes are not those of its manifest: the code of the check
        # of the output, as the reading of the page gives it.
        output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        path = output / LAPS
        before = os.stat(path)
        stamp = output_stamp(output)
        content = path.read_bytes()
        place = next(index for index, byte in enumerate(content) if chr(byte).isdigit())
        digit = b"2" if content[place:place + 1] == b"1" else b"1"
        os.chmod(path, 0o600)
        with path.open("r+b") as handle:
            handle.seek(place)
            handle.write(digit)
        os.chmod(path, before.st_mode & 0o7777)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(output_stamp(output), stamp)
        self.assertEqual(self.call("/api/view/laps", good), (422, {"error": "OUTPUT_CHANGED"}))
        self.assertFalse(self.server.laps_lock.locked())

    def test_an_output_that_fails_its_check_when_read_again(self) -> None:
        # A file whose contents changed fails the check of the output, which
        # compares it with the manifest: the code of the check, and the
        # ticket is forgotten, as for the numbers.
        output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        with (output / "analysis" / "activities.csv").open("a", encoding="utf-8") as handle:
            handle.write("\n")
        self.assertEqual(self.call("/api/view/laps", good), (422, {"error": "HANDOFF_INVALID"}))
        self.assertEqual(self.call("/api/view/laps", good), (409, {"error": "VIEW_NOT_OPEN"}))
        self.assertFalse(self.server.laps_lock.locked())

    def made(self, rows: list[Any]) -> tuple[Any, dict[str, Any]]:
        """A reading of rows made by hand, opened under a ticket (the place
        is that of a copy, whose store the settings remember)."""
        data = made_view_data(rows)
        views = gui_views.Views(load=lambda place: data, today=lambda zone: date.fromordinal(data.today))
        patcher = patch.object(self.server, "views", views)
        patcher.start()
        self.addCleanup(patcher.stop)
        _output, _store, opened = self.remembered()
        return data, opened

    def test_an_activity_whose_key_another_has_too_or_that_has_none(self) -> None:
        # A reading made by hand has no file of its lineage, as an output made
        # without a store: the key is looked at first, as pressing does, so
        # that the list tells key_shared where both hold (stage X10).
        data, opened = self.made(
            [
                keyed("2024-03-05", "k1", distance_m=1000.0),
                keyed("2024-03-06", "k1", distance_m=2000.0),
                keyed("2024-03-07", "", distance_m=3000.0),
                keyed("2024-03-08", "k2", distance_m=4000.0),
            ]
        )
        self.assertNotIn("snapshot/snapshot_lineage.json", data.files)
        listed = self.listed(opened["view"], "2024-03-01", "2024-03-31")
        self.assertEqual(sorted(row["ref"] for row in listed["rows"]), [0, 1, 2, 3])
        self.assertEqual(
            {row["ref"]: row["laps_unavailable"] for row in listed["rows"]},
            {0: "key_shared", 1: "key_shared", 2: "key_shared", 3: "not_from_store"},
        )
        self.assert_the_list_tells_as_pressing(opened, listed)
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 10):
            self.assertEqual(
                self.call("/api/view/laps", {"view": opened["view"], "read": listed["read"], "ref": 0}), (422, {"error": "VIEW_ANSWER_TOO_LARGE"})
            )
        for ref in (0, 1, 2):
            with self.subTest(ref=ref):
                self.assertEqual(
                    self.call("/api/view/laps", {"view": opened["view"], "read": listed["read"], "ref": ref}),
                    (200, {"status": "unavailable", "reason": "key_shared", "read": listed["read"], "output": self.facts(opened)}),
                )

    def test_rows_of_the_same_values_have_their_own_places(self) -> None:
        data, opened = self.made([keyed("2024-03-05", "k1", distance_m=1000.0), keyed("2024-03-05", "k1", distance_m=1000.0)])
        first, second = data.rows[ACTIVITIES]
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        listed = self.listed(opened["view"], "2024-03-05")
        self.assertEqual(sorted(row["ref"] for row in listed["rows"]), [0, 1])

    def test_each_place_is_that_of_its_row_among_the_activities_of_the_reading(self) -> None:
        rows = [
            keyed(f"2024-03-{1 + index:02d}", f"k{index}", "running" if index % 3 else "trail_running", distance_m=1000.0 * (1 + index % 4))
            for index in range(28)
        ]
        rows.append(keyed("2024-03-10", "k-ride", "road_biking", distance_m=20000.0))
        data, opened = self.made(rows)
        for types in (None, ["trail_running"], ["running", "road_biking"]):
            with self.subTest(types=types):
                payload = {"view": opened["view"], "item": "dist", "period": {"from": "2024-03-05", "to": "2024-03-25"}, "types": types}
                status, listed = self.call("/api/view/activities", payload)
                self.assertEqual(status, 200, listed)
                refs = [row["ref"] for row in listed["rows"]]
                self.assertEqual(len(set(refs)), len(refs))
                self.assertGreater(len(refs), 0)
                for row in listed["rows"]:
                    found = data.rows[ACTIVITIES][row["ref"]]
                    self.assertEqual(
                        (date.fromordinal(found.day).isoformat(), found.marks["type"], found.values["distance_m"]),
                        (row["day"], row["type"], row["values"]["dist"]),
                    )

    def test_the_answer_is_no_larger_than_the_limit(self) -> None:
        _output, _store, opened = self.remembered()
        good = {"view": opened["view"], "read": opened["read"], "ref": 0}
        status, answer = self.call("/api/view/laps", good)
        self.assertEqual(status, 200)
        size = len(gui_server.json_body(answer))
        with patch.object(gui_server, "MAX_ANSWER_BYTES", size - 1):
            self.assertEqual(self.call("/api/view/laps", good), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))
        with patch.object(gui_server, "MAX_ANSWER_BYTES", size):
            self.assertEqual(self.call("/api/view/laps", good), (200, answer))
        self.assertEqual(gui_server.MAX_ANSWER_BYTES, 4 * 1024 * 1024)
        # Every answer, of every status: the facts of the output in it have
        # no limit of their own (Codex's read of the diff of X9c-2).
        too_large = (422, {"error": "VIEW_ANSWER_TOO_LARGE"})
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 10):
            self.assertEqual(self.call("/api/view/laps", {**good, "read": opened["read"] + 1}), too_large)
            with holding(self.server.laps_lock):
                self.assertEqual(self.call("/api/view/laps", good), too_large)
        self.assertFalse(self.server.laps_lock.locked())

    def test_nothing_is_written_or_printed(self) -> None:
        output, store, opened = self.remembered()
        listed = self.listed(opened["view"], day_of(output))
        settings = places.settings_file()

        def looked() -> dict[str, tuple[int, int, int]]:
            found = {}
            for folder in (output, store, settings.parent):
                for path in (folder, *folder.rglob("*")):
                    status = os.lstat(path)
                    found[str(path)] = (status.st_mode, status.st_size, status.st_mtime_ns)
            return found

        before = looked()
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            good = {"view": opened["view"], "read": listed["read"], "ref": 0}
            self.assertEqual(self.call("/api/view/laps", good)[1]["status"], "laps")
            self.assertEqual(self.call("/api/view/laps", {**good, "read": 0})[1]["reason"], "read_stale")
            with holding(self.server.laps_lock):
                self.assertEqual(self.call("/api/view/laps", good)[1]["reason"], "busy")
        self.assertEqual(looked(), before)
        self.assertEqual(printed.getvalue(), "")

    def test_the_stamp_follows_the_files_of_the_laps(self) -> None:
        self.assertEqual(
            LAP_FILES,
            ("snapshot/snapshot_lineage.json", "normalized/activity_fit_links.json", "normalized/fit_sessions.json", "normalized/fit_laps.json"),
        )
        output, _store = self.copy()
        for name in LAP_FILES:
            with self.subTest(name=name):
                stamp = output_stamp(output)
                path = output / name
                later = path.stat().st_mtime_ns + 2_000_000_000
                os.utime(path, ns=(later, later))
                self.assertNotEqual(output_stamp(output), stamp)

    def test_the_series_command_and_the_list_of_the_numbers_give_no_place(self) -> None:
        # The places and the number of the reading are the server's (stage
        # X9c-2 of v2.3.0): the list of view.series and the CSV file of the
        # series command are as before.
        output, _store = self.copy()
        day = date.fromisoformat(day_of(output))
        answer = view_series.activity_list(load_view(output), "dist", (day, day))
        self.assertNotIn("read", answer)
        self.assertEqual(len(answer["rows"]), 1)
        self.assertNotIn("ref", answer["rows"][0])
        # Nor why laps cannot be shown, which is the server's too (stage X10).
        self.assertNotIn("laps_unavailable", answer["rows"][0])
        written = self.place / "series.csv"
        write_series(output, written)
        header = written.read_text(encoding="utf-8").splitlines()[0].split(",")
        self.assertEqual(header, list(SERIES_COLUMNS))
        self.assertFalse({"ref", "read", "laps_unavailable"} & set(header))
