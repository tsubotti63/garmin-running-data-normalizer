"""The marks of the view page from v2.2.0 (stage M1).

The rules of a mark (gui/marks.py); the file of the marks next to the
settings (gui-marks.json), read and written as the settings are, and never
written over when it cannot be read or is of a newer version; forgetting the
settings, which removes both files; the requests of the page
(/api/settings/marks, and whether the marks show in /api/settings/view); and
the report on GitHub, which never holds a mark. Every test keeps the
settings in its own folder (tests/conftest.py); the names and days of the
marks are made up.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer.gui import places, settings
from garmin_running_data_normalizer.gui.marks import (
    MARK_KINDS,
    MARKS_FORMAT,
    MAX_MARKS,
    MarkChangeError,
    change_marks,
    kept_marks,
)
from garmin_running_data_normalizer.gui.report import report_values
from garmin_running_data_normalizer.gui.settings import (
    MARKS_NEWER,
    MARKS_NOT_REMOVED,
    MARKS_NOT_WRITTEN,
    MARKS_UNREADABLE,
    MAX_SETTINGS_BYTES,
    SETTINGS_NOT_REMOVED,
    change_marks_at,
    forget_settings,
    launch_settings,
    read_marks,
    read_settings,
    remember_view_at,
    write_marks,
    write_settings,
)
from tests.test_environment_stops import REAL_SYMLINKS
from tests.test_gui_layouts import UNSAFE
from tests.test_gui_server import GuiServerTestCase

POSIX_MODES = unittest.skipIf(os.name == "nt", "Windows keeps no POSIX modes")
# A format newer than this version's.
NEWER_FORMAT = "garmin-running-data-normalizer-gui-marks-v2"


def added(before: list[dict[str, Any]], name: str, day: str, kind: str = "race", end: str | None = None) -> list[dict[str, Any]]:
    change = {"op": "add", "kind": kind, "name": name, "day": day}
    if end is not None:
        change["end"] = end
    return change_marks(before, change)


def code_of(before: list[dict[str, Any]], change: Any) -> str | None:
    """The code of a change that cannot be made; None when it is made."""
    try:
        change_marks(before, change)
    except MarkChangeError as exc:
        return exc.code
    return None


def biggest_marks() -> list[dict[str, Any]]:
    """The largest file of marks: 200 spans whose names are 30 characters of
    four bytes each."""
    every: list[dict[str, Any]] = []
    for number in range(MAX_MARKS):
        every = added(every, "\U0001F3C3" * 29 + chr(0x1F600 + number % 64), f"2030-{1 + number % 12:02d}-01", "injury", f"2030-{1 + number % 12:02d}-28")
    return every


class MarkRulesTest(unittest.TestCase):
    def test_a_mark_keeps_its_kind_name_and_days(self) -> None:
        kept = added([], "  Spring race A  ", "2030-04-14")
        self.assertEqual(len(kept), 1)
        self.assertRegex(kept[0]["id"], r"^m-[0-9a-f]{8}$")
        self.assertEqual({key: kept[0][key] for key in ("kind", "name", "day", "end")}, {"kind": "race", "name": "Spring race A", "day": "2030-04-14", "end": None})
        span = added(kept, "Sore knee B", "2030-05-02", "injury", "2030-05-20")
        self.assertEqual((span[1]["kind"], span[1]["day"], span[1]["end"]), ("injury", "2030-05-02", "2030-05-20"))
        self.assertEqual(MARK_KINDS, ("race", "injury", "shoes", "other"))
        self.assertEqual(MARKS_FORMAT, "garmin-running-data-normalizer-gui-marks-v1")

    def test_a_name_follows_the_rules_of_the_name_of_a_layout(self) -> None:
        self.assertEqual(added([], "Café run", "2030-01-01")[0]["name"], "Café run")
        self.assertEqual(added([], "x" * 30, "2030-01-01")[0]["name"], "x" * 30)
        for name in ("", "   ", "x" * 31, 3, None, *(f"a{character}b" for character in UNSAFE)):
            with self.subTest(name=name):
                self.assertEqual(code_of([], {"op": "add", "kind": "other", "name": name, "day": "2030-01-01"}), "MARK_NAME_INVALID")
        # Two marks can have the same name: their days and ids tell them apart.
        same = added(added([], "New shoes C", "2030-02-01", "shoes"), "New shoes C", "2030-09-01", "shoes")
        self.assertEqual([mark["name"] for mark in same], ["New shoes C", "New shoes C"])
        self.assertNotEqual(same[0]["id"], same[1]["id"])

    def test_a_day_is_a_date_of_the_calendar_from_1900(self) -> None:
        self.assertEqual(added([], "First", "1900-01-01")[0]["day"], "1900-01-01")
        self.assertEqual(added([], "Leap", "2032-02-29")[0]["day"], "2032-02-29")
        # The last day is that of years of four digits, as on the page.
        self.assertEqual(added([], "Last", "9999-12-31")[0]["day"], "9999-12-31")
        for day in ("1899-12-31", "0099-01-01", "2030-02-30", "2031-02-29", "2030-13-01", "2030-1-01", "20300101", " 2030-01-01", "2030-01-01T00:00", "10000-01-01", 20300101, None):
            with self.subTest(day=day):
                self.assertEqual(code_of([], {"op": "add", "kind": "race", "name": "A", "day": day}), "MARK_DAY_INVALID")
        for end in ("2030-03-09", "2030-02-30", 5, "", "1899-12-31"):
            with self.subTest(end=end):
                self.assertEqual(code_of([], {"op": "add", "kind": "injury", "name": "A", "day": "2030-03-10", "end": end}), "MARK_DAY_INVALID")
        # A span that ends on its day is a mark of one day.
        self.assertIsNone(added([], "One day", "2030-03-10", "injury", "2030-03-10")[0]["end"])

    def test_a_kind_is_one_of_the_four(self) -> None:
        for kind in ("trip", "Race", "", None, 1, ["race"]):
            with self.subTest(kind=kind):
                self.assertEqual(code_of([], {"op": "add", "kind": kind, "name": "A", "day": "2030-01-01"}), "REQUEST_INVALID")

    def test_a_mark_is_changed_or_removed_by_its_id(self) -> None:
        before = added(added([], "Race D", "2030-06-01"), "Camp E", "2030-07-01", "other")
        mark_id = before[0]["id"]
        changed = change_marks(before, {"op": "change", "id": mark_id, "kind": "other", "name": "Trip D", "day": "2030-08-01", "end": "2030-08-03"})
        self.assertEqual([(mark["name"], mark["day"], mark["end"]) for mark in changed], [("Camp E", "2030-07-01", None), ("Trip D", "2030-08-01", "2030-08-03")])
        self.assertEqual(changed[1]["id"], mark_id)
        # The change gives every value again: a span that loses its end is one day.
        self.assertIsNone(change_marks(changed, {"op": "change", "id": mark_id, "kind": "other", "name": "Trip D", "day": "2030-08-01"})[1]["end"])
        self.assertEqual([mark["name"] for mark in change_marks(changed, {"op": "remove", "id": mark_id})], ["Camp E"])
        # The list given is not changed.
        self.assertEqual(before[0]["name"], "Race D")
        for change in ({"op": "remove", "id": "m-00000000"}, {"op": "change", "id": "m-00000000", "kind": "race", "name": "A", "day": "2030-01-01"}, {"op": "remove"}):
            with self.subTest(change=change):
                self.assertEqual(code_of(before, change), "MARK_NOT_FOUND")
        for change in (None, [], "add", {}, {"op": "rename", "id": mark_id, "name": "A"}, {"op": "change", "id": mark_id, "name": "A", "day": "2030-01-01"}):
            with self.subTest(change=change):
                self.assertEqual(code_of(before, change), "REQUEST_INVALID")

    def test_the_marks_keep_the_order_of_their_days(self) -> None:
        kept = added(added(added([], "Later", "2030-10-10"), "Earlier", "2030-05-05"), "Same day 1", "2030-05-05")
        self.assertEqual([mark["name"] for mark in kept], ["Earlier", "Same day 1", "Later"])
        # A new mark comes last of its day; a mark moved to another day keeps
        # its place in the list among the marks of that day.
        kept = added(kept, "Same day 2", "2030-05-05")
        self.assertEqual([mark["name"] for mark in kept], ["Earlier", "Same day 1", "Same day 2", "Later"])
        later = kept[3]
        moved = change_marks(kept, {"op": "change", "id": later["id"], "kind": "race", "name": "Later", "day": "2030-05-05"})
        self.assertEqual([mark["name"] for mark in moved], ["Earlier", "Same day 1", "Same day 2", "Later"])
        first = moved[0]
        moved = change_marks(moved, {"op": "change", "id": first["id"], "kind": "race", "name": "Earlier", "day": "2030-12-24"})
        self.assertEqual([mark["name"] for mark in moved], ["Same day 1", "Same day 2", "Later", "Earlier"])

    def test_at_most_200_marks(self) -> None:
        full = biggest_marks()
        self.assertEqual(len(full), MAX_MARKS)
        self.assertEqual(len({mark["id"] for mark in full}), MAX_MARKS)
        self.assertEqual(code_of(full, {"op": "add", "kind": "race", "name": "One more", "day": "2030-01-01"}), "MARKS_FULL")
        # A full list still changes and removes.
        self.assertEqual(len(change_marks(full, {"op": "remove", "id": full[0]["id"]})), MAX_MARKS - 1)

    def test_a_mark_of_another_form_is_left_out_alone(self) -> None:
        good = {"id": "m-0000000a", "kind": "race", "name": "Kept", "day": "2030-01-01", "end": None}
        entries = [
            good,
            {**good, "name": "Same id"},
            {**good, "id": "u-0000000b"},
            {**good, "id": "m-0000000C"},
            {**good, "id": "m-0000000c", "kind": "trip"},
            {**good, "id": "m-0000000d", "name": ""},
            {**good, "id": "m-0000000e", "day": "2030-02-30"},
            {**good, "id": "m-0000000f", "end": "2029-12-31"},
            "not a mark",
            {"id": "m-00000010", "kind": "shoes", "name": "No end key", "day": "2030-03-01"},
        ]
        self.assertEqual([mark["name"] for mark in kept_marks(entries)], ["Kept", "No end key"])
        self.assertIsNone(kept_marks({"marks": []}))
        self.assertEqual(kept_marks([]), [])
        many = [{"id": f"m-{number:08x}", "kind": "other", "name": f"M{number}", "day": "2030-01-01"} for number in range(MAX_MARKS + 5)]
        self.assertEqual(len(kept_marks(many)), MAX_MARKS)


class MarksFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = places.marks_file()
        self.settings_path = places.settings_file()

    def test_the_marks_are_a_file_of_their_own_next_to_the_settings(self) -> None:
        self.assertEqual(self.path, self.settings_path.with_name("gui-marks.json"))
        self.assertEqual(read_marks(self.path), ([], None))
        self.assertEqual(change_marks_at(self.path, {"op": "add", "kind": "race", "name": "Race F", "day": "2030-04-01"})[1], None)
        self.assertFalse(self.settings_path.exists())
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["format"], MARKS_FORMAT)
        self.assertEqual([mark["name"] for mark in data["marks"]], ["Race F"])
        self.assertEqual([path.name for path in self.path.parent.iterdir()], ["gui-marks.json"])

    @POSIX_MODES
    def test_the_file_is_the_persons_own(self) -> None:
        self.assertIsNone(write_marks(self.path, added([], "Race G", "2030-04-01")))
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_the_largest_file_is_written_and_read_again(self) -> None:
        full = biggest_marks()
        self.assertIsNone(write_marks(self.path, full))
        self.assertLess(self.path.stat().st_size, MAX_SETTINGS_BYTES)
        self.assertEqual(read_marks(self.path), (full, None))

    def test_marks_whose_file_would_be_too_large_are_not_written(self) -> None:
        self.assertIsNone(write_marks(self.path, added([], "Before", "2030-01-01")))
        before = self.path.read_bytes()
        with patch.object(settings, "MAX_SETTINGS_BYTES", 300):
            marks_now, notice = change_marks_at(self.path, {"op": "add", "kind": "other", "name": "x" * 30, "day": "2030-02-01"})
        self.assertEqual(notice, MARKS_NOT_WRITTEN)
        self.assertEqual([mark["name"] for mark in marks_now], ["Before"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_a_change_that_is_not_written_keeps_the_marks_as_they_were(self) -> None:
        self.assertIsNone(write_marks(self.path, added([], "Before", "2030-01-01")))
        before = self.path.read_bytes()
        with patch.object(settings, "_write_content", return_value=False):
            marks_now, notice = change_marks_at(self.path, {"op": "add", "kind": "other", "name": "After", "day": "2030-02-01"})
        self.assertEqual((notice, [mark["name"] for mark in marks_now]), (MARKS_NOT_WRITTEN, ["Before"]))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual([path.name for path in self.path.parent.iterdir()], ["gui-marks.json"])

    def test_a_file_that_cannot_be_read_is_never_written_over(self) -> None:
        # A mark is the person's own record: a file read later may still hold it.
        for content in (b"{not json", b"[]", json.dumps({"format": MARKS_FORMAT, "marks": {}}).encode(), json.dumps({"format": "other", "marks": []}).encode(), json.dumps({"marks": []}).encode(), b"\xff\xfe", b"[" * 500 + b"]" * 500):
            with self.subTest(content=content[:30]):
                self.path.parent.mkdir(exist_ok=True)
                self.path.write_bytes(content)
                self.assertEqual(read_marks(self.path), ([], MARKS_UNREADABLE))
                # Adding, changing, and removing are refused alike, and the
                # file does not change by one byte.
                for change in (
                    {"op": "add", "kind": "race", "name": "A", "day": "2030-01-01"},
                    {"op": "change", "id": "m-0000000a", "kind": "race", "name": "A", "day": "2030-01-01"},
                    {"op": "remove", "id": "m-0000000a"},
                    "not a change",
                ):
                    self.assertEqual(change_marks_at(self.path, change), (None, MARKS_UNREADABLE))
                self.assertEqual(self.path.read_bytes(), content)
        self.path.write_bytes(b"x" * (MAX_SETTINGS_BYTES + 1))
        self.assertEqual(read_marks(self.path), ([], MARKS_UNREADABLE))
        self.path.unlink()
        self.path.mkdir()
        self.assertEqual(change_marks_at(self.path, {"op": "add", "kind": "race", "name": "A", "day": "2030-01-01"}), (None, MARKS_UNREADABLE))
        self.assertTrue(self.path.is_dir())

    def test_forgetting_removes_a_file_of_the_marks_that_is_not_used(self) -> None:
        # A file that cannot be read, or of a newer version, is never written
        # over, but forgetting the settings removes it.
        for content in (b"{not json", json.dumps({"format": NEWER_FORMAT, "marks": []}).encode()):
            with self.subTest(content=content[:20]):
                self.path.parent.mkdir(exist_ok=True)
                self.path.write_bytes(content)
                self.assertIs(launch_settings()["present"], True)
                self.assertEqual(forget_settings(), (None, True))
                self.assertFalse(os.path.lexists(self.path))

    @REAL_SYMLINKS
    def test_a_link_at_the_place_of_the_marks_is_not_followed(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / "elsewhere.json"
        target.write_text(json.dumps({"format": MARKS_FORMAT, "marks": []}), encoding="utf-8")
        self.path.parent.mkdir()
        self.path.symlink_to(target)
        self.assertEqual(read_marks(self.path), ([], MARKS_UNREADABLE))
        self.assertEqual(change_marks_at(self.path, {"op": "add", "kind": "race", "name": "A", "day": "2030-01-01"})[1], MARKS_UNREADABLE)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["marks"], [])

    def test_a_file_of_a_newer_version_is_never_written_over(self) -> None:
        self.path.parent.mkdir()
        content = json.dumps({"format": NEWER_FORMAT, "marks": [{"id": "m-0000000a", "kind": "trip"}]}).encode()
        self.path.write_bytes(content)
        self.assertEqual(read_marks(self.path), ([], MARKS_NEWER))
        self.assertEqual(change_marks_at(self.path, {"op": "add", "kind": "race", "name": "A", "day": "2030-01-01"}), (None, MARKS_NEWER))
        self.assertEqual(self.path.read_bytes(), content)

    def test_a_broken_mark_is_left_out_alone(self) -> None:
        self.path.parent.mkdir()
        good = {"id": "m-0000000a", "kind": "race", "name": "Kept", "day": "2030-01-01", "end": None}
        self.path.write_text(json.dumps({"format": MARKS_FORMAT, "marks": [good, {**good, "id": "m-0000000b", "day": "never"}]}), encoding="utf-8")
        self.assertEqual(read_marks(self.path), ([good], None))

    def test_two_changes_at_once_keep_both(self) -> None:
        start = threading.Barrier(2)
        errors: list[BaseException] = []

        def add_many(letter: str) -> None:
            try:
                start.wait(timeout=10)
                for number in range(20):
                    self.assertIsNone(change_marks_at(self.path, {"op": "add", "kind": "other", "name": f"{letter}{number}", "day": "2030-01-01"})[1])
            except BaseException as exc:  # pragma: no cover - reported below
                errors.append(exc)

        threads = [threading.Thread(target=add_many, args=(letter,)) for letter in ("A", "B")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(errors, [])
        self.assertEqual({mark["name"] for mark in read_marks(self.path)[0]}, {f"{letter}{number}" for letter in "AB" for number in range(20)})

    def test_forgetting_removes_both_files_and_the_folder(self) -> None:
        self.assertIsNone(write_settings(self.settings_path, {"hints": True}))
        self.assertIsNone(write_marks(self.path, added([], "Race H", "2030-04-01")))
        self.assertEqual(forget_settings(), (None, True))
        self.assertFalse(os.path.lexists(self.path))
        self.assertFalse(os.path.lexists(self.settings_path))
        self.assertFalse(self.path.parent.exists())
        self.assertEqual(forget_settings(), (None, False))

    def test_the_marks_alone_are_settings_to_forget(self) -> None:
        self.assertIsNone(write_marks(self.path, added([], "Race I", "2030-04-01")))
        self.assertIs(launch_settings()["present"], True)
        self.assertEqual(forget_settings(), (None, True))
        self.assertFalse(self.path.parent.exists())
        self.assertIs(launch_settings()["present"], False)

    def test_forgetting_tries_both_files(self) -> None:
        # The marks cannot be removed (a folder is at their place): the
        # settings are removed all the same, and the page is told that the
        # marks are left.
        self.assertIsNone(write_settings(self.settings_path, {"hints": True}))
        self.path.mkdir()
        self.assertEqual(forget_settings(), (MARKS_NOT_REMOVED, True))
        self.assertFalse(os.path.lexists(self.settings_path))
        self.assertTrue(self.path.is_dir())
        self.assertIs(launch_settings()["present"], True)

    def test_forgetting_removes_the_marks_when_the_settings_stay(self) -> None:
        # The other way round: the settings cannot be removed (a folder is at
        # their place), and the marks are removed all the same.
        self.settings_path.parent.mkdir()
        self.settings_path.mkdir()
        self.assertIsNone(write_marks(self.path, added([], "Race N", "2030-04-01")))
        self.assertEqual(forget_settings(), (SETTINGS_NOT_REMOVED, True))
        self.assertFalse(os.path.lexists(self.path))
        self.assertTrue(self.settings_path.is_dir())

    def test_the_launch_answer_holds_the_marks_and_what_to_tell(self) -> None:
        kept = added([], "Race J", "2030-04-01")
        self.assertIsNone(write_marks(self.path, kept))
        answer = launch_settings()
        self.assertEqual((answer["view_marks"], answer["marks_notice"], answer["view_marks_shown"]), (kept, None, None))
        self.path.write_bytes(b"{not json")
        answer = launch_settings()
        self.assertEqual((answer["view_marks"], answer["marks_notice"], answer["notice"]), ([], MARKS_UNREADABLE, None))

    def test_whether_the_marks_show_is_remembered_alone(self) -> None:
        self.assertIsNone(remember_view_at(self.settings_path, ["dist"], "open", {"marks_shown": False}))
        self.assertIs(read_settings(self.settings_path)[0]["view_marks_shown"], False)
        self.assertIs(launch_settings()["view_marks_shown"], False)
        # A value of another form is left out alone (as the other values of
        # the view page, stage K1).
        data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        for value in ("no", 0, None, [False]):
            with self.subTest(value=value):
                self.settings_path.write_text(json.dumps({**data, "view_marks_shown": value}), encoding="utf-8")
                values, notice = read_settings(self.settings_path)
                self.assertIsNone(notice)
                self.assertNotIn("view_marks_shown", values)
                self.assertEqual(values["view_items"], ["dist"])

    def test_the_report_on_github_holds_no_mark(self) -> None:
        self.assertIsNone(write_marks(self.path, added([], "Made-up mark K", "2030-04-01")))
        text = json.dumps(report_values(), ensure_ascii=False)
        self.assertNotIn("Made-up mark K", text)
        self.assertNotIn("gui-marks", text)


class MarksApiTest(GuiServerTestCase):
    def post(self, path: str, payload: Any = None) -> tuple[int, dict[str, Any]]:
        body = json.dumps({} if payload is None else payload).encode("utf-8")
        status, _, answer = self.post_api(path, body=body)
        return status, json.loads(answer)

    def test_the_page_adds_changes_and_removes_marks(self) -> None:
        status, answer = self.post("/api/settings/marks", {"op": "add", "kind": "race", "name": "Race L", "day": "2030-04-01"})
        self.assertEqual((status, answer["remembered"], answer["notice"]), (200, True, None))
        [mark] = answer["marks"]
        self.assertEqual({key: mark[key] for key in ("kind", "name", "day", "end")}, {"kind": "race", "name": "Race L", "day": "2030-04-01", "end": None})
        status, answer = self.post("/api/settings/marks", {"op": "change", "id": mark["id"], "kind": "injury", "name": "Calf M", "day": "2030-04-01", "end": "2030-04-09"})
        self.assertEqual((status, [(item["name"], item["end"]) for item in answer["marks"]]), (200, [("Calf M", "2030-04-09")]))
        self.assertEqual(self.post("/api/status")[1]["settings"]["view_marks"], answer["marks"])
        self.assertEqual(self.post("/api/settings/marks", {"op": "remove", "id": mark["id"]}), (200, {"remembered": True, "notice": None, "marks": []}))

    def test_a_change_that_cannot_be_made_answers_its_code(self) -> None:
        cases = {
            "MARK_NAME_INVALID": {"op": "add", "kind": "race", "name": " ", "day": "2030-04-01"},
            "MARK_DAY_INVALID": {"op": "add", "kind": "race", "name": "A", "day": "2030-02-30"},
            "MARK_NOT_FOUND": {"op": "remove", "id": "m-00000000"},
            "REQUEST_INVALID": {"op": "add", "kind": "trip", "name": "A", "day": "2030-04-01"},
        }
        for code, change in cases.items():
            with self.subTest(code=code):
                self.assertEqual(self.post("/api/settings/marks", change), (422, {"error": code}))
        self.assertFalse(places.marks_file().exists())
        self.assertIsNone(write_marks(places.marks_file(), biggest_marks()))
        self.assertEqual(self.post("/api/settings/marks", {"op": "add", "kind": "race", "name": "A", "day": "2030-04-01"}), (422, {"error": "MARKS_FULL"}))

    def test_a_file_that_is_not_used_is_told_and_kept(self) -> None:
        path = places.marks_file()
        path.parent.mkdir()
        path.write_bytes(b"{not json")
        self.assertEqual(self.post("/api/status")[1]["settings"]["marks_notice"], MARKS_UNREADABLE)
        change = {"op": "add", "kind": "race", "name": "A", "day": "2030-04-01"}
        self.assertEqual(self.post("/api/settings/marks", change), (200, {"remembered": False, "notice": MARKS_UNREADABLE, "marks": None}))
        self.assertEqual(path.read_bytes(), b"{not json")

    def test_the_view_page_remembers_whether_the_marks_show(self) -> None:
        base = {"items": ["dist"], "shelf": "open"}
        self.assertEqual(self.post("/api/settings/view", {**base, "marks_shown": False}), (200, {"remembered": True, "notice": None}))
        self.assertIs(self.post("/api/status")[1]["settings"]["view_marks_shown"], False)
        for value in (None, "false", 0):
            with self.subTest(value=value):
                self.assertEqual(self.post("/api/settings/view", {**base, "marks_shown": value})[0], 422)
        # The value not given stays.
        self.assertEqual(self.post("/api/settings/view", base)[0], 200)
        self.assertIs(self.post("/api/status")[1]["settings"]["view_marks_shown"], False)

    def test_forgetting_removes_the_marks(self) -> None:
        self.assertEqual(self.post("/api/settings/marks", {"op": "add", "kind": "race", "name": "A", "day": "2030-04-01"})[0], 200)
        self.assertEqual(self.post("/api/settings/forget"), (200, {"forgotten": True, "had_settings": True, "notice": None}))
        self.assertFalse(os.path.lexists(places.marks_file()))
        self.assertEqual(self.post("/api/status")[1]["settings"]["view_marks"], [])
        # A file of the marks that cannot be removed is told apart from the
        # settings, which are removed.
        self.assertIsNone(write_settings(places.settings_file(), {"hints": True}))
        places.marks_file().mkdir()
        self.assertEqual(self.post("/api/settings/forget"), (200, {"forgotten": False, "had_settings": True, "notice": MARKS_NOT_REMOVED}))
        self.assertFalse(os.path.lexists(places.settings_file()))



class MarksPageScriptTest(unittest.TestCase):
    """What the page does with the answers of the marks, from the review by
    Codex of the diff of M1: a scripted page is checked by its words, as the
    other scripts of the page are (test_gui_server)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(places.__file__).resolve().parent / "static" / "view.mjs").read_text(encoding="utf-8")

    def body(self, name: str) -> str:
        found = re.search(rf"\n(?:async )?function {name}\([^)]*\) \{{(.*?)\n\}}", self.source, re.DOTALL)
        assert found is not None, name
        return found.group(1)

    def test_an_answer_asked_before_the_other_tab_forgot_is_dropped(self) -> None:
        heard = self.body("themeHeard")
        self.assertLess(heard.index("state.marksGen += 1;"), heard.index("takeMarks([]);"))
        for name in ("changeMarks", "readMarks"):
            with self.subTest(name=name):
                body = self.body(name)
                self.assertIn("const gen = state.marksGen;", body)
                self.assertIn("if (gen !== state.marksGen) {", body)

    def test_a_file_that_is_not_used_shows_no_marks(self) -> None:
        self.assertIn("    } else if (marksLocked()) {\n      // The file is not used now: no mark shows, as at a launch.\n      takeMarks([]);", self.body("changeMarks"))

    def test_what_was_typed_after_a_change_was_sent_stays(self) -> None:
        body = self.body("saveMark")
        self.assertIn("const sent = JSON.stringify(markFields());", body)
        self.assertIn("if (JSON.stringify(markFields()) === sent) {\n      editMark(null, false);\n    }", body)

    def test_the_window_takes_the_focus_while_its_form_cannot_be_used(self) -> None:
        self.assertIn("(ui.markDay.disabled ? ui.marksPopClose : ui.markDay).focus();", self.body("focusMarkForm"))
        self.assertIn("    focusMarkForm();\n    await readMarks();", self.body("openMarks"))
        self.assertNotIn("ui.markDay.focus();", self.body("editMark"))

    def test_the_question_before_a_removal_names_its_buttons(self) -> None:
        body = self.body("renderMarksList")
        self.assertIn('ask.setAttribute("role", "group");', body)
        self.assertIn('ask.setAttribute("aria-labelledby", question.id);', body)
        self.assertIn('button.setAttribute("aria-describedby", question.id);', body)


if __name__ == "__main__":
    unittest.main()
