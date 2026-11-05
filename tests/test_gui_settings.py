"""The settings of an earlier launch of the GUI (stage B4c).

The GUI remembers the store and the folder for the output of the last run that
made its output, the latest outputs, whether the tips show, and the colors of
the page that the person chose (stage G3a), in one owner-only file in the
place that the system keeps for each person's application data. The file is
written whole, read with care, never written over when a newer version wrote
it, and forgotten on request. Every test keeps it in its own folder
(``tests/conftest.py``); synthetic data only.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.gui import places, runs, settings
from garmin_running_data_normalizer.gui.places import makeable_settings_folders, settings_file_for
from garmin_running_data_normalizer.snapshot import initialize_store
from garmin_running_data_normalizer.gui.settings import (
    MAX_RECENT_OUTPUTS,
    SETTINGS_FORMAT,
    SETTINGS_INVALID,
    SETTINGS_NEWER,
    SETTINGS_NOT_REMOVED,
    SETTINGS_NOT_WRITTEN,
    launch_answer,
    launch_theme,
    read_settings,
    remember_hints_at,
    remember_run_at,
    remember_theme_at,
    remember_view_at,
    remove_settings,
    settings_present,
    write_settings,
)
from tests.test_environment_stops import REAL_SYMLINKS
from tests.test_gui_runs import SYNTHETIC_EXPORT, child_environment, request, stub_manager, wait_until
from tests.test_gui_server import GuiServerTestCase
from tests.test_gui_snapshot_runs import ACCOUNT, STAMP, register

APP = places.SETTINGS_FOLDER_NAME
NAME = places.SETTINGS_FILE_NAME
POSIX_MODES = unittest.skipIf(os.name == "nt", "Windows keeps no POSIX modes")
TIMEOUT_SECONDS = 10.0
# A format newer than this version's: format 2 is that of v2.2.0 (stage K1).
NEWER_FORMAT = "garmin-running-data-normalizer-gui-settings-v3"


class SettingsPlaceTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name).resolve() / "home"
        self.elsewhere = Path(directory.name).resolve() / "elsewhere"

    def test_each_system_keeps_the_settings_in_its_place_for_application_data(self) -> None:
        self.assertEqual(
            settings_file_for("darwin", {}, self.home),
            self.home / "Library" / "Application Support" / APP / NAME,
        )
        self.assertEqual(settings_file_for("win32", {"LOCALAPPDATA": str(self.elsewhere)}, self.home), self.elsewhere / APP / NAME)
        self.assertEqual(settings_file_for("linux", {"XDG_STATE_HOME": str(self.elsewhere)}, self.home), self.elsewhere / APP / NAME)
        # A variable that is missing, empty, or not absolute counts as not
        # given, as the XDG Base Directory Specification says.
        for value in (None, "", "relative/state"):
            environ = {} if value is None else {"LOCALAPPDATA": value, "XDG_STATE_HOME": value}
            with self.subTest(value=value):
                self.assertEqual(settings_file_for("win32", environ, self.home), self.home / "AppData" / "Local" / APP / NAME)
                self.assertEqual(settings_file_for("linux", environ, self.home), self.home / ".local" / "state" / APP / NAME)

    def test_only_the_folders_of_the_xdg_state_home_in_the_home_folder_may_be_made(self) -> None:
        with patch.object(places, "home", lambda: self.home):
            state = self.home / ".local" / "state"
            self.assertEqual(makeable_settings_folders(state / APP / NAME, "linux"), (self.home / ".local", state))
            self.assertEqual(makeable_settings_folders(self.elsewhere / APP / NAME, "linux"), ())
            for platform in ("darwin", "win32"):
                with self.subTest(platform=platform):
                    self.assertEqual(makeable_settings_folders(state / APP / NAME, platform), ())

    def test_every_test_has_its_own_settings(self) -> None:
        # The shared preparation replaces the function that names the file.
        path = places.settings_file()
        self.assertEqual(path.name, NAME)
        self.assertNotEqual(path, settings_file_for(sys.platform, os.environ, Path.home()))
        self.assertTrue(path.parent.parent.is_dir())


class SettingsFileTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.base = self.root / "base"
        self.base.mkdir()
        self.path = self.base / APP / NAME
        self.store = str(self.root / "store")
        self.parent = str(self.root / "outputs")

    def written(self) -> dict[str, Any]:
        return json.loads(self.path.read_bytes().decode("utf-8"))

    def test_the_settings_are_written_whole_and_read_back(self) -> None:
        self.assertEqual(read_settings(self.path), ({}, None))
        values = {"store": self.store, "output_parent": self.parent, "recent_outputs": [self.parent + "-1"], "hints": False}
        self.assertIsNone(write_settings(self.path, values))
        self.assertEqual(read_settings(self.path), (values, None))
        self.assertEqual(self.written(), {"format": SETTINGS_FORMAT, **values})
        # Nothing else is left in this app's folder.
        self.assertEqual([item.name for item in self.path.parent.iterdir()], [NAME])
        # The next settings replace the file whole.
        self.assertIsNone(write_settings(self.path, {"hints": True}))
        self.assertEqual(read_settings(self.path), ({"hints": True}, None))

    @POSIX_MODES
    def test_the_folder_and_the_file_are_the_persons_own(self) -> None:
        # The umask cannot widen them.
        previous = os.umask(0)
        try:
            self.assertIsNone(write_settings(self.path, {"hints": True}))
        finally:
            os.umask(previous)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_only_this_apps_folder_is_made(self) -> None:
        missing = self.root / "missing" / APP / NAME
        self.assertEqual(write_settings(missing, {"hints": True}), SETTINGS_NOT_WRITTEN)
        self.assertFalse((self.root / "missing").exists())

    @POSIX_MODES
    def test_the_xdg_state_home_is_made_when_it_is_missing_and_kept_as_it_is_when_it_is_there(self) -> None:
        home = self.root / "home"
        home.mkdir()
        state = home / ".local" / "state"
        path = state / APP / NAME
        self.assertIsNone(write_settings(path, {"hints": True}, (home / ".local", state)))
        for folder in (home / ".local", state, state / APP):
            with self.subTest(folder=folder.name):
                self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
        # Folders that are there keep their permissions; they are shared.
        other = self.root / "other-home"
        (other / ".local" / "state").mkdir(parents=True)
        for folder in (other / ".local", other / ".local" / "state"):
            folder.chmod(0o755)
        path = other / ".local" / "state" / APP / NAME
        self.assertIsNone(write_settings(path, {"hints": True}, (other / ".local", other / ".local" / "state")))
        for folder in (other / ".local", other / ".local" / "state"):
            with self.subTest(folder=str(folder)):
                self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o755)

    def test_files_that_are_not_of_this_form_are_not_used(self) -> None:
        good = {"format": SETTINGS_FORMAT, "store": self.store}
        cases = {
            "not JSON": b"{not json",
            "not UTF-8": b"\xff\xfe",
            "a list": b"[]",
            "no format": json.dumps({"store": self.store}).encode(),
            "another format": json.dumps({**good, "format": "another-format-v1"}).encode(),
            "an older format": json.dumps({**good, "format": "garmin-running-data-normalizer-gui-settings-v0"}).encode(),
            "a relative place": json.dumps({**good, "store": "relative/store"}).encode(),
            "a control character": json.dumps({**good, "store": self.store + "\x01"}).encode(),
            "a place that is not text": json.dumps({**good, "output_parent": 3}).encode(),
            "tips that are not true or false": json.dumps({**good, "hints": "yes"}).encode(),
            "outputs that are not a list": json.dumps({**good, "recent_outputs": self.parent}).encode(),
            "too many outputs": json.dumps(
                {**good, "recent_outputs": [f"{self.parent}-{number}" for number in range(MAX_RECENT_OUTPUTS + 1)]}
            ).encode(),
            "the same output twice": json.dumps({**good, "recent_outputs": [self.parent, self.parent]}).encode(),
            # 64 KiB at most, as the file promises.
            "too large": json.dumps({**good, "padding": "x" * 64 * 1024}).encode(),
            "deeply nested": b"[" * 30000 + b"]" * 30000,
            # Of this form but for a value more than 256 deep (stage E2d).
            "nested more than 256 deep": (json.dumps(good)[:-1] + ', "padding": ' + "[" * 300 + "]" * 300 + "}").encode(),
        }
        self.path.parent.mkdir()
        for name, content in cases.items():
            with self.subTest(name):
                self.path.write_bytes(content)
                self.assertEqual(read_settings(self.path), ({}, SETTINGS_INVALID))
        self.path.unlink()
        self.path.mkdir()
        self.assertEqual(read_settings(self.path), ({}, SETTINGS_INVALID))

    @REAL_SYMLINKS
    def test_a_link_is_not_followed(self) -> None:
        target = self.root / "target.json"
        target.write_bytes(json.dumps({"format": SETTINGS_FORMAT, "store": self.store}).encode())
        self.path.parent.mkdir()
        self.path.symlink_to(target)
        self.assertEqual(read_settings(self.path), ({}, SETTINGS_INVALID))
        # This app's folder may not be a link either.
        link = self.root / "linked" / APP
        link.parent.mkdir()
        link.symlink_to(self.root / "target-folder", target_is_directory=True)
        (self.root / "target-folder").mkdir()
        self.assertEqual(write_settings(link / NAME, {"hints": True}), SETTINGS_NOT_WRITTEN)
        self.assertEqual(list((self.root / "target-folder").iterdir()), [])

    def test_keys_that_this_version_does_not_know_are_left_out(self) -> None:
        self.path.parent.mkdir()
        self.path.write_bytes(json.dumps({"format": SETTINGS_FORMAT, "store": self.store, "later": [1, 2]}).encode())
        self.assertEqual(read_settings(self.path), ({"store": self.store}, None))
        self.assertIsNone(remember_hints_at(self.path, True))
        self.assertEqual(self.written(), {"format": SETTINGS_FORMAT, "store": self.store, "hints": True})

    def test_a_file_of_a_newer_version_is_neither_used_nor_written_over(self) -> None:
        self.path.parent.mkdir()
        newer = json.dumps({"format": NEWER_FORMAT, "store": 7}).encode()
        self.path.write_bytes(newer)
        self.assertEqual(read_settings(self.path), ({}, SETTINGS_NEWER))
        self.assertEqual(remember_hints_at(self.path, True), SETTINGS_NEWER)
        self.assertEqual(remember_run_at(self.path, self.root / "outputs" / "o1", Path(self.store)), SETTINGS_NEWER)
        self.assertEqual(remember_theme_at(self.path, "dark"), SETTINGS_NEWER)
        self.assertEqual(self.path.read_bytes(), newer)
        # Forgetting removes it.
        self.assertIsNone(remove_settings(self.path)[0])
        self.assertFalse(self.path.exists())

    def test_a_file_that_is_not_used_is_replaced_by_the_next_settings(self) -> None:
        self.path.parent.mkdir()
        self.path.write_bytes(b"{not json")
        self.assertIsNone(remember_run_at(self.path, self.root / "outputs" / "o1", None))
        self.assertEqual(read_settings(self.path)[1], None)

    def test_a_run_remembers_its_places_and_the_latest_outputs(self) -> None:
        outputs = self.root / "outputs"
        self.assertIsNone(remember_run_at(self.path, outputs / "o1", Path(self.store)))
        self.assertEqual(
            read_settings(self.path)[0],
            {"store": self.store, "output_parent": str(outputs), "recent_outputs": [str(outputs / "o1")]},
        )
        # A run of this Export alone keeps the store that was remembered.
        other = self.root / "other-outputs"
        self.assertIsNone(remember_run_at(self.path, other / "o2", None))
        values = read_settings(self.path)[0]
        self.assertEqual((values["store"], values["output_parent"]), (self.store, str(other)))
        self.assertEqual(values["recent_outputs"], [str(other / "o2"), str(outputs / "o1")])
        # The latest first, each once, ten at most; the tips stay.
        self.assertIsNone(remember_hints_at(self.path, False))
        for number in range(3, 15):
            remember_run_at(self.path, outputs / f"o{number}", None)
        remember_run_at(self.path, outputs / "o10", None)
        values = read_settings(self.path)[0]
        self.assertEqual(len(values["recent_outputs"]), MAX_RECENT_OUTPUTS)
        self.assertEqual(values["recent_outputs"][:3], [str(outputs / "o10"), str(outputs / "o14"), str(outputs / "o13")])
        self.assertEqual(len(set(values["recent_outputs"])), MAX_RECENT_OUTPUTS)
        self.assertIs(values["hints"], False)

    def test_the_colors_are_remembered_with_the_other_settings(self) -> None:
        # Stage G3a: Light or Dark, or none to follow the browser; the other
        # settings stay as they are, and the format stays the one of 2.0.x,
        # which leaves out a key that it does not know.
        self.assertIsNone(remember_run_at(self.path, self.root / "outputs" / "o1", Path(self.store)))
        self.assertIsNone(remember_hints_at(self.path, False))
        before = read_settings(self.path)[0]
        for theme in ("light", "dark"):
            with self.subTest(theme=theme):
                self.assertIsNone(remember_theme_at(self.path, theme))
                self.assertEqual(read_settings(self.path), ({**before, "theme": theme}, None))
                self.assertEqual(self.written(), {"format": SETTINGS_FORMAT, **before, "theme": theme})
                self.assertEqual(launch_answer(read_settings(self.path)[0], None, present=True)["theme"], theme)
        self.assertIsNone(remember_theme_at(self.path, None))
        self.assertEqual(read_settings(self.path), (before, None))
        self.assertEqual(self.written(), {"format": SETTINGS_FORMAT, **before})
        # A run and the tips keep the colors.
        self.assertIsNone(remember_theme_at(self.path, "dark"))
        self.assertIsNone(remember_run_at(self.path, self.root / "outputs" / "o2", None))
        self.assertIsNone(remember_hints_at(self.path, True))
        self.assertEqual(read_settings(self.path)[0]["theme"], "dark")

    def test_colors_of_another_form_are_left_out_alone(self) -> None:
        # Stage G3a: a key that 2.1.0 added is left out when it is of another
        # form, such as a color of a later version; the places, the outputs,
        # and the tips are still used.
        values = {"store": self.store, "output_parent": self.parent, "recent_outputs": [self.parent + "-1"], "hints": True}
        self.path.parent.mkdir()
        for theme in ("blue", "Dark", "", 1, True, ["dark"], {"dark": True}):
            with self.subTest(theme=theme):
                self.path.write_bytes(json.dumps({"format": SETTINGS_FORMAT, **values, "theme": theme}).encode())
                self.assertEqual(read_settings(self.path), (values, None))
        # The next change writes the settings without it.
        self.assertIsNone(remember_hints_at(self.path, False))
        self.assertEqual(self.written(), {"format": SETTINGS_FORMAT, **values, "hints": False})

    def test_settings_that_2_0_wrote_are_read_without_colors(self) -> None:
        # The file of 2.0.x, as it writes it, has no colors: the page follows
        # the browser.
        older = {
            "format": SETTINGS_FORMAT,
            "hints": False,
            "output_parent": self.parent,
            "recent_outputs": [self.parent + "-1"],
            "store": self.store,
        }
        self.path.parent.mkdir()
        self.path.write_bytes((json.dumps(older, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode())
        values, notice = read_settings(self.path)
        self.assertEqual((values, notice), ({key: value for key, value in older.items() if key != "format"}, None))
        self.assertIsNone(launch_answer(values, notice, present=True)["theme"])

    def test_the_view_page_remembers_its_items_and_shelf(self) -> None:
        # Stage G3b: the names of the items only, and whether the item shelf
        # is open; the other settings stay as they are.
        self.assertIsNone(remember_run_at(self.path, self.root / "outputs" / "o1", Path(self.store)))
        self.assertIsNone(remember_theme_at(self.path, "dark"))
        before = read_settings(self.path)[0]
        self.assertIsNone(remember_view_at(self.path, ["dist", "rhr", "vo2"], "closed"))
        values = read_settings(self.path)[0]
        self.assertEqual(values, {**before, "view_items": ["dist", "rhr", "vo2"], "view_shelf": "closed"})
        self.assertEqual(self.written()["format"], SETTINGS_FORMAT)
        answer = launch_answer(values, None, present=True)
        self.assertEqual((answer["view_items"], answer["view_shelf"]), (["dist", "rhr", "vo2"], "closed"))
        # No items is an answer of its own; a run, the tips, and the colors
        # keep them.
        self.assertIsNone(remember_view_at(self.path, [], "open"))
        self.assertIsNone(remember_run_at(self.path, self.root / "outputs" / "o2", None))
        self.assertIsNone(remember_hints_at(self.path, True))
        self.assertIsNone(remember_theme_at(self.path, None))
        values = read_settings(self.path)[0]
        self.assertEqual((values["view_items"], values["view_shelf"]), ([], "open"))
        # A file of a newer version is not written over.
        newer = json.dumps({"format": NEWER_FORMAT}).encode()
        self.path.write_bytes(newer)
        self.assertEqual(remember_view_at(self.path, ["dist"], "open"), SETTINGS_NEWER)
        self.assertEqual(self.path.read_bytes(), newer)

    def test_items_and_shelf_of_another_form_are_left_out_alone(self) -> None:
        # Stage G3b: of the items, the names that this version does not know,
        # the names given twice, and those after the sixth are left out; a
        # key of another form is left out alone, and the places, the outputs,
        # and the tips are still used.
        values = {"store": self.store, "output_parent": self.parent, "recent_outputs": [self.parent + "-1"], "hints": True}
        self.path.parent.mkdir()
        names = ["dist", "nope", "dist", 1, ["rhr"], "rhr", "vo2", "hr", "mx", "pace", "time", "count"]
        self.path.write_bytes(json.dumps({"format": SETTINGS_FORMAT, **values, "view_items": names, "view_shelf": "open"}).encode())
        self.assertEqual(
            read_settings(self.path),
            ({**values, "view_items": ["dist", "rhr", "vo2", "hr", "mx", "pace"], "view_shelf": "open"}, None),
        )
        for items in ("dist", {"dist": True}, 3, True):
            with self.subTest(items=items):
                self.path.write_bytes(json.dumps({"format": SETTINGS_FORMAT, **values, "view_items": items}).encode())
                self.assertEqual(read_settings(self.path), (values, None))
        for shelf in ("Open", "", 1, ["open"]):
            with self.subTest(shelf=shelf):
                self.path.write_bytes(json.dumps({"format": SETTINGS_FORMAT, **values, "view_shelf": shelf}).encode())
                self.assertEqual(read_settings(self.path), (values, None))

    def test_two_changes_at_once_keep_both(self) -> None:
        # Stage G3a: a change reads the file and writes it whole, so that two
        # at once could keep only one of them; the second waits for the first
        # now. A run that ends while the person chooses the colors keeps both.
        reading = threading.Event()
        release = threading.Event()
        real = settings.write_settings

        def held(path: Path, values: dict[str, Any], makeable: tuple[Path, ...] = ()) -> str | None:
            if values.get("theme") == "dark" and not release.is_set():
                # The first change holds after it read the file.
                reading.set()
                if not release.wait(TIMEOUT_SECONDS):
                    raise AssertionError("the test did not let the change go on")
            return real(path, values, makeable)

        with patch.object(settings, "write_settings", held):
            first = threading.Thread(target=remember_theme_at, args=(self.path, "dark"))
            first.start()
            self.assertTrue(reading.wait(TIMEOUT_SECONDS))
            second = threading.Thread(target=remember_run_at, args=(self.path, self.root / "outputs" / "o1", Path(self.store)))
            second.start()
            second.join(0.2)
            self.assertTrue(second.is_alive(), "the run's change did not wait")
            release.set()
            first.join(TIMEOUT_SECONDS)
            second.join(TIMEOUT_SECONDS)
        self.assertFalse(first.is_alive() or second.is_alive())
        values = read_settings(self.path)[0]
        self.assertEqual((values.get("theme"), values.get("store")), ("dark", self.store))

    def test_settings_that_cannot_be_written_leave_nothing_behind(self) -> None:
        with patch("os.replace", side_effect=PermissionError("denied")):
            self.assertEqual(write_settings(self.path, {"hints": True}), SETTINGS_NOT_WRITTEN)
        self.assertEqual(list(self.path.parent.iterdir()), [])
        # A place that cannot be kept in the file is not written, and raises
        # nothing.
        self.assertEqual(remember_run_at(self.path, Path(self.parent) / "\udcff", None), SETTINGS_NOT_WRITTEN)
        self.assertFalse(self.path.exists())
        self.assertEqual(write_settings(self.path, {"store": "relative"}), SETTINGS_NOT_WRITTEN)

    def test_forgetting_removes_the_file_and_the_empty_folder(self) -> None:
        self.assertFalse(settings_present(self.path))
        notice, present, generation = remove_settings(self.path)
        self.assertEqual((notice, present), (None, False))
        self.assertIsNone(write_settings(self.path, {"hints": True}))
        self.assertTrue(settings_present(self.path))
        # Each forgetting moves the generation of the settings on by one
        # (stage U2 of v2.2.0), with no file to forget too.
        self.assertEqual(remove_settings(self.path), (None, True, generation + 1))
        self.assertFalse(settings_present(self.path))
        self.assertFalse(self.path.parent.exists())
        self.assertTrue(self.base.is_dir())
        # A folder in its place is there to report (stage C1); the
        # generation moves on also when the file is left.
        self.path.mkdir(parents=True)
        self.assertTrue(settings_present(self.path))
        self.assertEqual(remove_settings(self.path), (SETTINGS_NOT_REMOVED, True, generation + 2))
        self.assertTrue(self.path.is_dir())

    def temporary(self, pid: int, *, path: Path | None = None, age: float = 0.0, hexes: str = "0123abcd") -> Path:
        # A temporary file of a write of ``path`` (the settings at first), as
        # _write_content names it, ``age`` seconds old (stage W4 of v2.2.1).
        place = path or self.path
        place.parent.mkdir(parents=True, exist_ok=True)
        temporary = place.parent / f".{place.name}.{pid}.{hexes}.tmp"
        temporary.write_bytes(b'{"store": "synthetic"}')
        if age:
            moment = time.time() - age
            os.utime(temporary, (moment, moment))
        return temporary

    @staticmethod
    def other_pid(offset: int) -> int:
        # A pid that is not this process's; whether it is alive is what the
        # test makes os.kill answer (Codex's review of the diff: never the
        # state of the machine).
        pid = 424240 + offset
        return pid + 100 if pid == os.getpid() else pid

    def test_forgetting_removes_the_abandoned_temporary_files(self) -> None:
        # Stage W4 of v2.2.1: a write that stopped in the middle leaves a copy
        # of the settings or the marks. Forgetting removes those of this
        # process, older than ten minutes, or of a process that is gone (by
        # its pid, not on Windows), and leaves a newer one of a process that is
        # alive, the names of other forms, and a folder; the folder of the
        # settings stays with what is left.
        self.assertEqual(settings.TEMPORARY_AGE_SECONDS, 10 * 60)
        marks = self.path.with_name(places.MARKS_FILE_NAME)
        alive = self.other_pid(1)
        gone_pid = self.other_pid(2)
        own = self.temporary(os.getpid())
        old = self.temporary(alive, age=settings.TEMPORARY_AGE_SECONDS + 60, hexes="89abcdef")
        younger = self.temporary(alive, age=settings.TEMPORARY_AGE_SECONDS - 60, hexes="0a0a0a0a")
        fresh = self.temporary(alive, hexes="00ff00ff")
        gone = self.temporary(gone_pid, hexes="deadbeef")
        marks_own = self.temporary(os.getpid(), path=marks)
        others = [
            self.path.parent / name
            for name in (
                f".{NAME}.0123.0123abcd.tmp",
                f".{NAME}.{alive}.0123ABCD.tmp",
                f".{NAME}.{alive}.0123abc.tmp",
                f".{NAME}.12345678901.0123abcd.tmp",
                f".{NAME.replace('.', '_')}.{os.getpid()}.0123abcd.tmp",
                f".other.json.{os.getpid()}.0123abcd.tmp",
                f"{NAME}.{os.getpid()}.0123abcd.tmp",
                f".{NAME}.{os.getpid()}.0123abcd.tmp.old",
            )
        ]
        # Old enough to be removed, were they of a name that a write makes
        # (the partial guard of W4: a name taken by mistake must show).
        moment = time.time() - settings.TEMPORARY_AGE_SECONDS - 60
        for other in others:
            other.write_bytes(b"{}")
            os.utime(other, (moment, moment))
        folder = self.path.parent / f".{NAME}.{os.getpid()}.feedbeef.tmp"
        folder.mkdir()

        def kill(pid: int, signal: int) -> None:
            if pid == gone_pid:
                raise ProcessLookupError("gone")

        with patch.object(settings, "_CHECK_PIDS", True), patch("os.kill", side_effect=kill):
            self.assertEqual(remove_settings(self.path, (marks,))[:2], (None, True))
        for removed in (own, old, marks_own, gone):
            with self.subTest(removed=removed.name):
                self.assertFalse(os.path.lexists(removed))
        for kept in (younger, fresh, *others):
            with self.subTest(kept=kept.name):
                self.assertTrue(kept.exists())
        self.assertTrue(folder.is_dir())
        self.assertTrue(self.path.parent.is_dir())

    def test_forgetting_temporary_files_alone_removes_the_folder(self) -> None:
        # Stage W4 of v2.2.1: a temporary file alone is something to forget,
        # and the folder goes after it.
        own = self.temporary(os.getpid())
        self.assertEqual(remove_settings(self.path)[:2], (None, True))
        self.assertFalse(os.path.lexists(own))
        self.assertFalse(self.path.parent.exists())
        self.assertTrue(self.base.is_dir())

    def test_a_temporary_file_left_is_told_as_its_file(self) -> None:
        # Stage W4 of v2.2.1: one that cannot be removed holds a copy, and is
        # told as the file of the settings or of the marks would be.
        marks = self.path.with_name(places.MARKS_FILE_NAME)
        real_unlink = os.unlink

        def unlink(place: Any, *args: Any, **kwargs: Any) -> None:
            if os.fspath(place).endswith(".tmp"):
                raise PermissionError("denied")
            real_unlink(place, *args, **kwargs)

        own = self.temporary(os.getpid())
        with patch("os.unlink", side_effect=unlink):
            self.assertEqual(remove_settings(self.path, (marks,))[:2], (SETTINGS_NOT_REMOVED, True))
        self.assertTrue(own.exists())
        own.unlink()
        marks_own = self.temporary(os.getpid(), path=marks)
        with patch("os.unlink", side_effect=unlink):
            self.assertEqual(remove_settings(self.path, (marks,))[:2], (settings.MARKS_NOT_REMOVED, True))
        self.assertTrue(marks_own.exists())

    def test_only_a_process_that_is_gone_makes_a_newer_file_abandoned(self) -> None:
        # Stage W4 of v2.2.1 (the checker's review of the plan, A): only
        # ProcessLookupError tells that the process is gone; any other answer
        # counts as alive, and the age decides. os.kill is never really called
        # here; where pids are not looked at (Windows), it is never called.
        pid = self.other_pid(2)
        for error in (PermissionError("another user"), OverflowError("too large"), ValueError("bad"), OSError("other")):
            with self.subTest(error=type(error).__name__):
                temporary = self.temporary(pid, hexes="0a0b0c0d")
                with patch.object(settings, "_CHECK_PIDS", True), patch("os.kill", side_effect=error):
                    remove_settings(self.path)
                self.assertTrue(temporary.exists())
                temporary.unlink()
        temporary = self.temporary(pid, hexes="0a0b0c0d")
        with patch.object(settings, "_CHECK_PIDS", True), patch("os.kill", side_effect=ProcessLookupError("gone")) as kill:
            remove_settings(self.path)
        self.assertFalse(os.path.lexists(temporary))
        kill.assert_called_once_with(pid, 0)
        temporary = self.temporary(pid, hexes="0a0b0c0d")
        with patch.object(settings, "_CHECK_PIDS", False), patch("os.kill", side_effect=AssertionError("os.kill")):
            remove_settings(self.path)
        self.assertTrue(temporary.exists())
        self.assertIs(settings._CHECK_PIDS, os.name != "nt")
        # The line itself, which the value on one system alone cannot tell
        # (the partial guard of W4).
        self.assertIn('_CHECK_PIDS = os.name != "nt"\n', Path(settings.__file__).read_text(encoding="utf-8"))

    @REAL_SYMLINKS
    def test_forgetting_removes_a_temporary_link_only(self) -> None:
        # Stage W4 of v2.2.1: a link of that name is removed, not what it
        # points to.
        target = self.root / "target.json"
        target.write_bytes(b"{}")
        self.path.parent.mkdir()
        link = self.path.parent / f".{NAME}.{os.getpid()}.0123abcd.tmp"
        link.symlink_to(target)
        self.assertEqual(remove_settings(self.path)[:2], (None, True))
        self.assertFalse(os.path.lexists(link))
        self.assertEqual(target.read_bytes(), b"{}")

    def test_a_folder_that_cannot_be_looked_at_is_something_to_forget(self) -> None:
        # Stage W4 of v2.2.1 (the checker's review of the plan, C): the page
        # lets the person try.
        self.path.parent.mkdir()
        # From Codex's review of the diff, what is in it is not known to be
        # gone, and is told as left.
        with patch("os.listdir", side_effect=PermissionError("denied")):
            # While the folder is there (forgetting removes it when empty).
            self.assertIs(settings._temporaries_present((self.path,)), True)
            self.assertEqual(remove_settings(self.path)[:2], (SETTINGS_NOT_REMOVED, True))
        # Where the folder is not there, there is none.
        self.assertIs(settings._temporaries_present((self.root / "missing" / NAME,)), False)

    def test_a_temporary_file_that_cannot_be_looked_at_is_told(self) -> None:
        # Codex's review of the diff: a name of a write that cannot be looked
        # at is not known to be gone; it is something to forget and is told.
        own = self.temporary(os.getpid())
        real_lstat = os.lstat

        def lstat(place: Any, *args: Any, **kwargs: Any) -> os.stat_result:
            if os.fspath(place).endswith(".tmp"):
                raise PermissionError("denied")
            return real_lstat(place, *args, **kwargs)

        with patch("os.lstat", side_effect=lstat):
            self.assertEqual(remove_settings(self.path)[:2], (SETTINGS_NOT_REMOVED, True))
            self.assertIs(settings._temporaries_present((self.path,)), True)
        self.assertTrue(own.exists())

    @REAL_SYMLINKS
    def test_a_folder_that_is_a_link_is_never_looked_into(self) -> None:
        # Codex's review of the diff: this app never writes into its folder
        # where that is a link (_make_folder), and forgetting never removes a
        # file of that name in the folder that the link points to.
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        temporary = elsewhere / f".{NAME}.{os.getpid()}.0123abcd.tmp"
        temporary.write_bytes(b"{}")
        self.path.parent.symlink_to(elsewhere, target_is_directory=True)
        self.assertEqual(remove_settings(self.path)[:2], (None, False))
        self.assertTrue(temporary.exists())

    def test_a_temporary_file_changed_since_it_was_looked_at_stays(self) -> None:
        # Codex's review of the diff: a file is removed only while it is still
        # the one looked at; one written again since (another launch going on
        # with its write) or put in its place is left to its writer, and is
        # not told as left.
        own = self.temporary(os.getpid())
        seen = os.lstat(own)
        moment = seen.st_mtime + 5
        os.utime(own, (moment, moment))
        self.assertIs(settings._remove_temporary(own, seen), True)
        self.assertTrue(own.exists())
        with patch.object(settings, "_abandoned_temporaries", return_value=([(0, own, seen)], set())):
            self.assertEqual(remove_settings(self.path)[:2], (None, True))
        self.assertTrue(own.exists())
        self.assertIs(settings._remove_temporary(own, os.lstat(own)), True)
        self.assertFalse(own.exists())
        self.assertIs(settings._remove_temporary(own, seen), True)

    def test_a_place_that_cannot_be_looked_at_counts_as_present(self) -> None:
        # Stage C1: the page lets the person try, and forgetting tells what
        # it could not do.
        with patch("os.lstat", side_effect=PermissionError("denied")):
            self.assertTrue(settings_present(self.path))

    @REAL_SYMLINKS
    def test_forgetting_a_link_removes_the_link_only(self) -> None:
        target = self.root / "target.json"
        target.write_bytes(b"{}")
        self.path.parent.mkdir()
        self.path.symlink_to(target)
        self.assertTrue(settings_present(self.path))
        self.assertIsNone(remove_settings(self.path)[0])
        self.assertFalse(os.path.lexists(self.path))
        self.assertEqual(target.read_bytes(), b"{}")

    def test_a_later_launch_needs_a_remembered_place(self) -> None:
        self.assertEqual(
            launch_answer({}, None, present=False),
            {
                "launch": "first",
                "store": None,
                "output_parent": None,
                "hints": None,
                "theme": None,
                "view_items": None,
                "view_shelf": None,
                "view_layouts": [],
                "view_layouts_hidden": [],
                "view_layout": None,
                "view_period": None,
                "view_grain": None,
                "view_types": None,
                "view_compare_mode": None,
                "view_compare_month": None,
                "view_compare_by": None,
                "view_compare_weeks": None,
                "view_marks_shown": None,
                "view_plot": None,
                "view_spread": None,
                "view_conditions": None,
                "view_marks": [],
                "marks_notice": None,
                "timezone": None,
                "notice": None,
                "present": False,
                # The generation of the settings (stage U2 of v2.2.0).
                "generation": 0,
            },
        )
        self.assertEqual(launch_answer({}, None, present=False, generation=3)["generation"], 3)
        self.assertEqual(launch_answer({"hints": False}, None, present=True)["launch"], "first")
        self.assertEqual(launch_answer({"store": self.store}, None, present=True)["launch"], "later")
        self.assertEqual(launch_answer({"output_parent": self.parent}, None, present=True)["launch"], "later")
        self.assertEqual(launch_answer({}, SETTINGS_INVALID, present=True)["notice"], SETTINGS_INVALID)
        # Whether there is a file to forget goes to the page as it is (stage C1).
        self.assertIs(launch_answer({"hints": False}, None, present=True)["present"], True)


class SettingsApiTest(GuiServerTestCase):
    def post(self, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        body = json.dumps(self.at_generation(path, payload or {})).encode("utf-8")
        status, _, answer = self.post_api(path, body=body)
        return status, json.loads(answer)

    def test_the_page_reads_the_settings_when_it_starts(self) -> None:
        path = places.settings_file()
        store = str(path.parent.parent / "store")
        self.assertIsNone(remember_run_at(path, path.parent.parent / "outputs" / "o1", Path(store)))
        status, answer = self.post("/api/status")
        self.assertEqual(
            (status, answer["settings"]),
            (
                200,
                {
                    "launch": "later",
                    "store": store,
                    "output_parent": str(path.parent.parent / "outputs"),
                    "hints": None,
                    "theme": None,
                    "view_items": None,
                    "view_shelf": None,
                    "view_layouts": [],
                    "view_layouts_hidden": [],
                    "view_layout": None,
                    "view_period": None,
                    "view_grain": None,
                    "view_types": None,
                    "view_compare_mode": None,
                    "view_compare_month": None,
                    "view_compare_by": None,
                    "view_compare_weeks": None,
                    "view_marks_shown": None,
                    "view_plot": None,
                    "view_spread": None,
                    "view_conditions": None,
                    "view_marks": [],
                    "marks_notice": None,
                    "timezone": None,
                    "notice": None,
                    "present": True,
                    "generation": self.settings_generation(),
                },
            ),
        )
        path.write_bytes(b"{not json")
        self.assertEqual(self.post("/api/status")[1]["settings"]["notice"], SETTINGS_INVALID)
        self.assertIs(self.post("/api/status")[1]["settings"]["present"], True)

    def test_the_tips_are_remembered_as_they_are_switched(self) -> None:
        for on in (False, True):
            with self.subTest(on=on):
                self.assertEqual(self.post("/api/settings/hints", {"on": on}), (200, {"remembered": True, "notice": None}))
                self.assertIs(read_settings(places.settings_file())[0]["hints"], on)
        for payload in ({}, {"on": "yes"}, {"on": 1}):
            with self.subTest(payload=payload):
                self.assertEqual(self.post("/api/settings/hints", payload), (422, {"error": "REQUEST_INVALID"}))
        with patch.object(settings, "write_settings", return_value=SETTINGS_NOT_WRITTEN):
            self.assertEqual(
                self.post("/api/settings/hints", {"on": True}),
                (200, {"remembered": False, "notice": SETTINGS_NOT_WRITTEN}),
            )

    def test_the_colors_are_remembered_as_they_are_chosen(self) -> None:
        # Stage G3a: "auto" follows the browser, and is remembered as no
        # choice.
        path = places.settings_file()
        for theme, kept in (("dark", "dark"), ("light", "light"), ("auto", None)):
            with self.subTest(theme=theme):
                self.assertEqual(self.post("/api/settings/theme", {"theme": theme}), (200, {"remembered": True, "notice": None}))
                self.assertEqual(read_settings(path)[0].get("theme"), kept)
                self.assertEqual(self.post("/api/status")[1]["settings"]["theme"], kept)
        for payload in ({}, {"theme": "Dark"}, {"theme": "system"}, {"theme": 1}, {"theme": None}, {"theme": ["dark"]}):
            with self.subTest(payload=payload):
                self.assertEqual(self.post("/api/settings/theme", payload), (422, {"error": "REQUEST_INVALID"}))
        with patch.object(settings, "write_settings", return_value=SETTINGS_NOT_WRITTEN):
            self.assertEqual(
                self.post("/api/settings/theme", {"theme": "dark"}),
                (200, {"remembered": False, "notice": SETTINGS_NOT_WRITTEN}),
            )
        newer = json.dumps({"format": NEWER_FORMAT}).encode()
        path.write_bytes(newer)
        self.assertEqual(
            self.post("/api/settings/theme", {"theme": "dark"}),
            (200, {"remembered": False, "notice": SETTINGS_NEWER}),
        )
        self.assertEqual(path.read_bytes(), newer)

    def test_the_items_and_the_shelf_of_the_view_page_are_remembered(self) -> None:
        # Stage G3b: up to six names of items that this version knows, each
        # once, and the shelf open or closed.
        path = places.settings_file()
        self.assertEqual(
            self.post("/api/settings/view", {"items": ["dist", "rhr"], "shelf": "closed"}),
            (200, {"remembered": True, "notice": None}),
        )
        settings_answer = self.post("/api/status")[1]["settings"]
        self.assertEqual((settings_answer["view_items"], settings_answer["view_shelf"]), (["dist", "rhr"], "closed"))
        self.assertEqual(self.post("/api/settings/view", {"items": [], "shelf": "open"})[0], 200)
        self.assertEqual(read_settings(path)[0]["view_items"], [])
        for payload in (
            {},
            {"items": ["dist"]},
            {"items": ["dist"], "shelf": "Open"},
            {"items": "dist", "shelf": "open"},
            {"items": ["nope"], "shelf": "open"},
            {"items": ["dist", "dist"], "shelf": "open"},
            {"items": ["dist", "time", "count", "pace", "hr", "mx", "cad"], "shelf": "open"},
            {"items": [1], "shelf": "open"},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.post("/api/settings/view", payload), (422, {"error": "REQUEST_INVALID"}))
        with patch.object(settings, "write_settings", return_value=SETTINGS_NOT_WRITTEN):
            self.assertEqual(
                self.post("/api/settings/view", {"items": ["dist"], "shelf": "open"}),
                (200, {"remembered": False, "notice": SETTINGS_NOT_WRITTEN}),
            )

    def test_the_settings_are_forgotten_on_request_and_never_while_a_run_is_active(self) -> None:
        path = places.settings_file()
        generation = self.settings_generation()
        # Nothing to forget: no file is left, and the answer says that there
        # was none (stage C1); and from stage U2 of v2.2.0 the generation of
        # the settings after it, one more.
        self.assertIs(self.post("/api/status")[1]["settings"]["present"], False)
        self.assertEqual(
            self.post("/api/settings/forget"),
            (200, {"forgotten": True, "had_settings": False, "notice": None, "generation": generation + 1}),
        )
        self.assertIsNone(remember_hints_at(path, False))
        self.assertIs(self.post("/api/status")[1]["settings"]["present"], True)
        # A run that is active (a child that waits until it is cancelled):
        # the settings stay, and so does their generation.
        parent = path.parent.parent / "outputs"
        parent.mkdir()
        manager = stub_manager("wait", cancel_grace=60.0)
        self.addCleanup(manager.stop)
        with patch.object(self.server, "runs", manager):
            self.assertEqual(self.post("/api/run/start", request(SYNTHETIC_EXPORT, parent, "o1"))[0], 200)
            self.assertEqual(self.post("/api/settings/forget"), (409, {"error": "RUN_ACTIVE"}))
            self.assertTrue(path.exists())
            self.assertEqual(self.settings_generation(), generation + 1)
            self.assertTrue(wait_until(lambda: bool(manager.status()["progress"])))
            manager.cancel()
            self.assertTrue(wait_until(lambda: not manager.active(), 120))
        self.assertEqual(
            self.post("/api/settings/forget"),
            (200, {"forgotten": True, "had_settings": True, "notice": None, "generation": generation + 2}),
        )
        self.assertFalse(path.exists())
        self.assertEqual(self.post("/api/status")[1]["settings"]["launch"], "first")
        self.assertIs(self.post("/api/status")[1]["settings"]["present"], False)
        path.mkdir(parents=True)
        self.assertEqual(
            self.post("/api/settings/forget"),
            (200, {"forgotten": False, "had_settings": True, "notice": SETTINGS_NOT_REMOVED, "generation": generation + 3}),
        )


# A change of each of the five requests that change the settings (stage U2
# of v2.2.0).
CHANGES = {
    "/api/settings/hints": {"on": True},
    "/api/settings/theme": {"theme": "dark"},
    "/api/settings/view": {"items": ["dist"], "shelf": "open"},
    "/api/settings/layouts": {"op": "add", "name": "Mine", "items": ["dist", "pace"]},
    "/api/settings/marks": {"op": "add", "kind": "race", "name": "Race U", "day": "2030-04-01"},
}


class SettingsGenerationTest(GuiServerTestCase):
    """The generation of the settings (stage U2 of v2.2.0): forgetting moves
    it on, and a change asked at another one is stale and writes nothing, in
    whichever order the two take the lock of the settings."""

    def post(self, path: str, payload: Any = None) -> tuple[int, dict[str, Any]]:
        # The generation as each test names it.
        body = json.dumps({} if payload is None else payload).encode("utf-8")
        status, _, answer = self.post_api(path, body=body)
        return status, json.loads(answer)

    def in_thread(self, path: str, payload: Any = None) -> tuple[threading.Thread, list[tuple[int, dict[str, Any]]]]:
        answers: list[tuple[int, dict[str, Any]]] = []
        thread = threading.Thread(target=lambda: answers.append(self.post(path, payload)), daemon=True)
        thread.start()
        return thread, answers

    def held(self, name: str, inside: Any = None) -> tuple[Any, threading.Event, threading.Event]:
        """settings.<name>, which is called under the lock of the settings,
        stopped there until ``release`` is set: the patcher, ``entered``, and
        ``release``."""
        entered, release = threading.Event(), threading.Event()
        # A request that a broken test leaves stopped goes on at its end.
        self.addCleanup(release.set)
        real = getattr(settings, name)

        def stopping(*args: Any, **kwargs: Any) -> Any:
            if inside is not None:
                inside()
            entered.set()
            release.wait(10)
            return real(*args, **kwargs)

        return patch.object(settings, name, stopping), entered, release

    def files(self) -> tuple[bool, bool]:
        return os.path.lexists(places.settings_file()), os.path.lexists(places.marks_file())

    def test_a_change_names_a_generation_of_its_form(self) -> None:
        generation = self.settings_generation()
        for path, change in CHANGES.items():
            for value in (None, True, False, 1.0, -1, "0", [generation]):
                with self.subTest(path=path, value=value):
                    payload = {**change, "generation": value}
                    self.assertEqual(self.post(path, payload), (422, {"error": "REQUEST_INVALID"}))
            with self.subTest(path=path, value="none"):
                self.assertEqual(self.post(path, change), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(self.files(), (False, False))
        for path, change in CHANGES.items():
            with self.subTest(path=path):
                status, answer = self.post(path, {**change, "generation": generation})
                self.assertEqual((status, answer["remembered"]), (200, True))
        self.assertEqual(self.files(), (True, True))

    def test_a_change_of_another_generation_is_stale_and_writes_nothing(self) -> None:
        before = self.settings_generation()
        self.assertEqual(self.post("/api/settings/forget")[1]["generation"], before + 1)
        for path, change in CHANGES.items():
            for asked in (before, before + 2):
                with self.subTest(path=path, asked=asked):
                    self.assertEqual(
                        self.post(path, {**change, "generation": asked}),
                        (200, {"stale": True, "generation": before + 1}),
                    )
        self.assertEqual(self.files(), (False, False))
        # The generation now writes again.
        for path, change in CHANGES.items():
            with self.subTest(path=path):
                self.assertIs(self.post(path, {**change, "generation": before + 1})[1]["remembered"], True)
        self.assertEqual(self.files(), (True, True))
        self.assertEqual(self.settings_generation(), before + 1)

    def test_a_stale_change_is_told_before_a_mark_or_a_layout_that_it_names_is_looked_for(self) -> None:
        before = self.settings_generation()
        self.post("/api/settings/forget")
        stale = (200, {"stale": True, "generation": before + 1})
        self.assertEqual(self.post("/api/settings/marks", {"op": "remove", "id": "m-0000000a", "generation": before}), stale)
        self.assertEqual(self.post("/api/settings/layouts", {"op": "rename", "id": "u-0000000a", "name": "B", "generation": before}), stale)
        self.assertEqual(self.post("/api/settings/layouts", {"op": "nothing", "generation": before}), stale)
        # And before a file of the marks that is not used.
        places.marks_file().parent.mkdir(parents=True, exist_ok=True)
        places.marks_file().write_bytes(b"{not json")
        self.assertEqual(self.post("/api/settings/marks", {**CHANGES["/api/settings/marks"], "generation": before}), stale)
        self.assertEqual(
            self.post("/api/settings/marks", {"op": "remove", "id": "m-0000000a", "generation": before + 1}),
            (200, {"remembered": False, "notice": "MARKS_UNREADABLE", "marks": None}),
        )
        self.assertEqual(places.marks_file().read_bytes(), b"{not json")

    def test_a_change_that_holds_the_lock_first_is_written_and_then_forgotten(self) -> None:
        for path, change in CHANGES.items():
            with self.subTest(path=path):
                generation = self.settings_generation()
                patcher, entered, release = self.held("read_marks" if path.endswith("marks") else "read_settings")
                with patcher:
                    writing, written = self.in_thread(path, {**change, "generation": generation})
                    self.assertTrue(entered.wait(10))
                    forgetting, forgotten = self.in_thread("/api/settings/forget")
                    forgetting.join(0.3)
                    self.assertTrue(forgetting.is_alive(), "forgetting waits for the change")
                    release.set()
                    writing.join(10)
                    forgetting.join(10)
                self.assertEqual((written[0][0], written[0][1]["remembered"]), (200, True))
                self.assertEqual(forgotten[0], (200, {"forgotten": True, "had_settings": True, "notice": None, "generation": generation + 1}))
                self.assertEqual(self.files(), (False, False))

    def test_a_change_after_a_forgetting_that_holds_the_lock_first_is_stale(self) -> None:
        for path, change in CHANGES.items():
            with self.subTest(path=path):
                generation = self.settings_generation()
                self.assertIs(self.post(path, {**change, "generation": generation})[1]["remembered"], True)
                patcher, entered, release = self.held("_remove_file")
                with patcher:
                    forgetting, forgotten = self.in_thread("/api/settings/forget")
                    self.assertTrue(entered.wait(10))
                    writing, written = self.in_thread(path, {**change, "generation": generation})
                    writing.join(0.3)
                    self.assertTrue(writing.is_alive(), "the change waits for the forgetting")
                    release.set()
                    forgetting.join(10)
                    writing.join(10)
                self.assertEqual(forgotten[0][1]["generation"], generation + 1)
                self.assertEqual(written[0], (200, {"stale": True, "generation": generation + 1}))
                self.assertEqual(self.files(), (False, False))

    def test_the_status_tells_the_settings_and_their_generation_of_one_reading(self) -> None:
        generation = self.settings_generation()
        self.assertIs(self.post("/api/settings/hints", {"on": False, "generation": generation})[1]["remembered"], True)
        # A forgetting that holds the lock first: the status waits for it,
        # and tells no settings of before with the generation after.
        patcher, entered, release = self.held("_remove_file")
        with patcher:
            forgetting, _forgotten = self.in_thread("/api/settings/forget")
            self.assertTrue(entered.wait(10))
            reading, read = self.in_thread("/api/status")
            reading.join(0.3)
            self.assertTrue(reading.is_alive(), "the status waits for the forgetting")
            release.set()
            forgetting.join(10)
            reading.join(10)
        settings_now = read[0][1]["settings"]
        self.assertEqual((settings_now["generation"], settings_now["present"], settings_now["hints"]), (generation + 1, False, None))
        # A status that holds the lock first: the settings of before, with the
        # generation of before.
        self.assertIs(self.post("/api/settings/hints", {"on": False, "generation": generation + 1})[1]["remembered"], True)
        patcher, entered, release = self.held("read_marks")
        with patcher:
            reading, read = self.in_thread("/api/status")
            self.assertTrue(entered.wait(10))
            forgetting, _forgotten = self.in_thread("/api/settings/forget")
            forgetting.join(0.3)
            self.assertTrue(forgetting.is_alive(), "forgetting waits for the status")
            release.set()
            reading.join(10)
            forgetting.join(10)
        settings_now = read[0][1]["settings"]
        self.assertEqual((settings_now["generation"], settings_now["present"], settings_now["hints"]), (generation + 1, True, False))
        self.assertEqual(self.settings_generation(), generation + 2)

    def test_no_run_starts_while_the_settings_are_forgotten(self) -> None:
        parent = places.settings_file().parent.parent / "outputs"
        parent.mkdir()
        manager = stub_manager("wait", cancel_grace=60.0)
        self.addCleanup(manager.stop)
        held_runs: list[bool] = []
        patcher, entered, release = self.held("_remove_file", inside=lambda: held_runs.append(manager._lock.locked()))
        with patch.object(self.server, "runs", manager), patcher:
            forgetting, forgotten = self.in_thread("/api/settings/forget")
            self.assertTrue(entered.wait(10))
            starting, started = self.in_thread("/api/run/start", request(SYNTHETIC_EXPORT, parent, "o1"))
            starting.join(0.3)
            self.assertTrue(starting.is_alive(), "the run waits for the forgetting")
            release.set()
            forgetting.join(10)
            starting.join(30)
            self.assertEqual((forgotten[0][0], started[0][0]), (200, 200))
            # The settings and the marks were removed under the lock of the
            # runs.
            self.assertEqual(held_runs, [True, True])
            self.assertTrue(wait_until(lambda: bool(manager.status()["progress"])))
            manager.cancel()
            self.assertTrue(wait_until(lambda: not manager.active(), 120))
        # A run that is active refuses the forgetting before the lock of the
        # settings is taken: the generation stays.
        generation = self.settings_generation()
        with patch.object(self.server, "runs", manager):
            self.assertEqual(self.post("/api/run/start", request(SYNTHETIC_EXPORT, parent, "o2"))[0], 200)
            self.assertEqual(self.post("/api/settings/forget"), (409, {"error": "RUN_ACTIVE"}))
            self.assertEqual(self.settings_generation(), generation)
            self.assertTrue(wait_until(lambda: bool(manager.status()["progress"])))
            manager.cancel()
            self.assertTrue(wait_until(lambda: not manager.active(), 120))


class LaunchThemeTest(unittest.TestCase):
    def test_a_launch_opens_in_the_remembered_colors(self) -> None:
        # Stage G3a: the address of a launch carries them; none without a
        # choice, or with a file that is not used.
        path = places.settings_file()
        self.assertIsNone(launch_theme())
        self.assertIsNone(remember_theme_at(path, "light"))
        self.assertEqual(launch_theme(), "light")
        path.write_bytes(b"{not json")
        self.assertIsNone(launch_theme())


class RunRemembersTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.dict(os.environ, child_environment())
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.parent = self.root / "outputs"
        self.parent.mkdir()
        self.path = places.settings_file()

    def end(self, manager: runs.RunManager, cancel: bool = False) -> dict[str, Any]:
        if cancel:
            self.assertTrue(wait_until(lambda: bool(manager.status()["progress"])))
            manager.cancel()
        self.assertTrue(wait_until(lambda: not manager.active(), 120))
        return manager.status()

    def test_a_finished_run_remembers_its_places(self) -> None:
        manager = runs.RunManager()
        self.addCleanup(manager.stop)
        manager.start(request(SYNTHETIC_EXPORT, self.parent, "o1"))
        status = self.end(manager)
        self.assertEqual((status["state"], status["settings_notice"]), ("finished", None))
        # From v2.2.0 the timezone of the run too (stage K1).
        self.assertEqual(
            read_settings(self.path)[0],
            {"output_parent": str(self.parent), "recent_outputs": [str(self.parent / "o1")], "timezone": "Asia/Tokyo"},
        )

    def test_the_store_of_a_snapshot_run_is_remembered_with_an_output_that_a_late_cancellation_left(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        register(store, SYNTHETIC_EXPORT, "S1", STAMP)
        manager = stub_manager("publish-then-wait", cancel_grace=60.0)
        self.addCleanup(manager.stop)
        rerun = {**request(SYNTHETIC_EXPORT, self.parent, "o2"), "how": "rerun", "store": str(store)}
        del rerun["input"]
        manager.start(rerun)
        status = self.end(manager, cancel=True)
        self.assertEqual(status["state"], "finished_after_cancel")
        values = read_settings(self.path)[0]
        self.assertEqual((values["store"], values["recent_outputs"]), (str(store), [str(self.parent / "o2")]))

    def test_a_run_without_its_output_remembers_nothing(self) -> None:
        for mode, cancel, state in (("wait", True, "cancelled"), ("fail-then-wait", True, "failed")):
            with self.subTest(mode=mode):
                manager = stub_manager(mode, cancel_grace=60.0)
                self.addCleanup(manager.stop)
                manager.start(request(SYNTHETIC_EXPORT, self.parent, mode))
                status = self.end(manager, cancel=cancel)
                self.assertEqual((status["state"], status["settings_notice"]), (state, None))
                self.assertFalse(self.path.exists())

    def test_settings_that_cannot_be_remembered_are_told_and_never_hold_the_end_of_a_run(self) -> None:
        cases = (
            patch.object(runs, "remember_run", return_value=SETTINGS_NOT_WRITTEN),
            patch.object(runs, "remember_run", return_value=SETTINGS_NEWER),
            patch.object(runs, "remember_run", side_effect=RuntimeError("unexpected")),
        )
        for number, (patcher, notice) in enumerate(zip(cases, (SETTINGS_NOT_WRITTEN, SETTINGS_NEWER, SETTINGS_NOT_WRITTEN))):
            with self.subTest(notice=notice, number=number):
                with patcher:
                    manager = stub_manager("publish-then-wait", cancel_grace=60.0)
                    self.addCleanup(manager.stop)
                    manager.start(request(SYNTHETIC_EXPORT, self.parent, f"o{number}"))
                    status = self.end(manager, cancel=True)
                self.assertEqual((status["state"], status["settings_notice"]), ("finished_after_cancel", notice))


if __name__ == "__main__":
    unittest.main()
