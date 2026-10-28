"""The layouts of the view page and what the settings remember for it from
v2.2.0 (stage K1).

The built-in layouts and the rules of the person's layouts (gui/layouts.py);
the settings of format 2 with the layouts, the period, the grouping, the
activity types, and the timezone of the last run that made its output; the
check of the size of the file before it is written; and the requests of the
page (/api/settings/view and /api/settings/layouts). Every test keeps the
settings in its own folder (tests/conftest.py); synthetic data only.
"""
from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer.gui import layouts, places, settings
from garmin_running_data_normalizer.gui.layouts import (
    BUILT_IN_IDS,
    BUILT_IN_LAYOUTS,
    MAX_LAYOUT_NAME_LENGTH,
    MAX_LAYOUTS,
    LayoutChangeError,
    built_in_answer,
    built_in_name_keys,
    change_layouts,
    kept_hidden,
    kept_layouts,
    layout_name,
    name_key,
)
from garmin_running_data_normalizer.gui.server import LANGUAGES
from garmin_running_data_normalizer.gui.settings import (
    MAX_SETTINGS_BYTES,
    SETTINGS_FORMAT,
    SETTINGS_NEWER,
    SETTINGS_NOT_WRITTEN,
    change_layouts_at,
    launch_answer,
    read_settings,
    remember_hints_at,
    remember_run_at,
    remember_view_at,
    write_settings,
)
from garmin_running_data_normalizer.gui.views import ViewRequestError, series_request
from garmin_running_data_normalizer.view.items import ITEMS_BY_KEY
from garmin_running_data_normalizer.view.series import MAX_TYPE_LENGTH, MAX_TYPES
from tests.test_gui_server import GuiServerTestCase

APP = places.SETTINGS_FOLDER_NAME
NAME = places.SETTINGS_FILE_NAME
FORMAT_1 = "garmin-running-data-normalizer-gui-settings-v1"
NEWER_FORMAT = "garmin-running-data-normalizer-gui-settings-v3"
STATIC = Path(layouts.__file__).resolve().parent / "static"
# The characters that a name of the person cannot hold: control characters, the
# separators of lines and paragraphs, and those that change the direction of
# the text around them.
UNSAFE = ["\x00", "\x1f", "\x7f", "\x85", "\u2028", "\u2029", "\u061c", "\u200e", "\u200f",
          *(chr(code) for code in range(0x202A, 0x202F)), *(chr(code) for code in range(0x2066, 0x206A))]
# Words that would judge the numbers, which a layout's name never holds.
JUDGING_WORDS = ("良い", "悪い", "調子", "回復", "おすすめ", "改善", "good", "bad", "best", "worst", "better", "recover", "recommend", "improve",
                 "wellness", "ウェルネス", "coaching", "コーチング")


def catalog(language: str) -> dict[str, str]:
    return json.loads((STATIC / "i18n" / f"{language}.json").read_text(encoding="utf-8"))


def state(layouts_list: list[dict[str, Any]] | None = None, hidden: list[str] | None = None, current: str | None = None) -> dict[str, Any]:
    return {"layouts": layouts_list or [], "hidden": hidden or [], "current": current}


def added(state_before: dict[str, Any], name: str, items: list[str] | None = None) -> dict[str, Any]:
    return change_layouts(state_before, {"op": "add", "name": name, "items": items or ["dist", "pace"]})


class LimitTest(unittest.TestCase):
    def test_the_limits_are_those_of_the_plan(self) -> None:
        # Stage K1 of v2.2.0: 20 layouts of 1 to 30 characters, and up to 64
        # activity types of up to 128 characters each.
        self.assertEqual((MAX_LAYOUTS, MAX_LAYOUT_NAME_LENGTH, MAX_TYPES, MAX_TYPE_LENGTH), (20, 30, 64, 128))
        self.assertEqual(MAX_SETTINGS_BYTES, 64 * 1024)


class BuiltInLayoutTest(unittest.TestCase):
    def test_the_six_built_in_layouts_show_items_that_this_version_knows(self) -> None:
        self.assertEqual(BUILT_IN_IDS, ("run", "sleep_hr", "volume", "form", "load", "estimates"))
        for layout_id, items in BUILT_IN_LAYOUTS:
            with self.subTest(layout_id=layout_id):
                self.assertTrue(0 < len(items) <= 6)
                self.assertEqual(len(set(items)), len(items))
                self.assertLessEqual(set(items), set(ITEMS_BY_KEY))
        # As the person chose them on 2026-10-28 (K0).
        self.assertEqual(
            dict(BUILT_IN_LAYOUTS),
            {
                "run": ("dist", "pace", "hr"),
                "sleep_hr": ("sleep", "sscore", "hrv", "rhr"),
                "volume": ("dist", "time", "count", "asc"),
                "form": ("cad", "sl", "vo", "gct"),
                "load": ("load", "acute", "chronic", "acwr"),
                "estimates": ("vo2", "phalf", "pfull", "endu"),
            },
        )

    def test_each_built_in_layout_has_a_name_in_every_language_and_the_page_names_it(self) -> None:
        self.assertEqual(layouts.CATALOG_LANGUAGES, LANGUAGES)
        for language in LANGUAGES:
            words = catalog(language)
            for layout_id in BUILT_IN_IDS:
                with self.subTest(language=language, layout_id=layout_id):
                    name = words.get(f"view.layout.{layout_id}")
                    self.assertIsInstance(name, str)
                    self.assertEqual(layout_name(name), name)
        # The page's table of the names has the same layouts, in the same
        # order.
        source = (STATIC / "view_flow.mjs").read_text(encoding="utf-8")
        table = re.search(r"export const LAYOUT_NAME_KEYS = \{(.*?)\n\};", source, re.DOTALL)
        assert table is not None
        entries = re.findall(r'^\s+(\w+): "([^"]+)",$', table.group(1), re.MULTILINE)
        self.assertEqual(entries, [(layout_id, f"view.layout.{layout_id}") for layout_id in BUILT_IN_IDS])

    def test_the_names_of_the_built_in_layouts_do_not_judge(self) -> None:
        # The layouts choose what to show only (the rule of not interpreting).
        for language in LANGUAGES:
            words = catalog(language)
            for layout_id in BUILT_IN_IDS:
                name = words[f"view.layout.{layout_id}"].casefold()
                for word in JUDGING_WORDS:
                    with self.subTest(language=language, layout_id=layout_id, word=word):
                        self.assertNotIn(word.casefold(), name)

    def test_the_server_reads_the_built_in_names_from_the_page_files(self) -> None:
        keys = built_in_name_keys()
        self.assertEqual(len(keys), len(BUILT_IN_IDS) * len(LANGUAGES))
        for name in ("ランの指標", "Running", "Garmin の推定", "Garmin estimates", "走りの形", "Running form"):
            with self.subTest(name=name):
                self.assertIn(name_key(name), keys)

    def test_the_page_takes_the_built_in_layouts_by_their_ids_and_items(self) -> None:
        self.assertEqual(built_in_answer(), [{"id": layout_id, "items": list(items)} for layout_id, items in BUILT_IN_LAYOUTS])


class LayoutNameTest(unittest.TestCase):
    def test_a_name_is_kept_in_nfc_without_the_spaces_around_it(self) -> None:
        self.assertEqual(layout_name("朝ラン"), "朝ラン")
        self.assertEqual(layout_name("  朝ラン\t"), "朝ラン")
        self.assertEqual(layout_name("ガ"), "ガ")
        self.assertEqual(layout_name("😀" * MAX_LAYOUT_NAME_LENGTH), "😀" * MAX_LAYOUT_NAME_LENGTH)
        self.assertEqual(layout_name("a" * MAX_LAYOUT_NAME_LENGTH), "a" * MAX_LAYOUT_NAME_LENGTH)

    def test_a_name_of_another_form_is_not_kept(self) -> None:
        for value in (None, 3, ["朝"], "", "   ", "a" * (MAX_LAYOUT_NAME_LENGTH + 1), *(f"朝{character}ラン" for character in UNSAFE)):
            with self.subTest(value=value):
                self.assertIsNone(layout_name(value))

    def test_names_are_compared_in_nfkc_and_casefold(self) -> None:
        self.assertEqual(name_key("ＲＵＮ"), name_key("run"))
        self.assertEqual(name_key("ﾗﾝ"), name_key("ラン"))
        self.assertEqual(name_key("Straße"), name_key("STRASSE"))
        self.assertNotEqual(name_key("朝ラン"), name_key("夜ラン"))


class ChangeLayoutsTest(unittest.TestCase):
    def assert_refused(self, before: dict[str, Any], change: Any, code: str) -> None:
        with self.assertRaises(LayoutChangeError) as caught:
            change_layouts(before, change)
        self.assertEqual(caught.exception.code, code)

    def test_a_new_layout_goes_last_and_becomes_the_one_used_last(self) -> None:
        first = added(state(current="run"), " 朝ラン ", ["dist", "hr"])
        layout = first["layouts"][0]
        self.assertRegex(layout["id"], r"^u-[0-9a-f]{8}$")
        self.assertEqual((layout["name"], layout["items"], first["current"]), ("朝ラン", ["dist", "hr"], layout["id"]))
        second = added(first, "週末", ["time"])
        self.assertEqual([entry["name"] for entry in second["layouts"]], ["朝ラン", "週末"])
        self.assertNotEqual(second["layouts"][0]["id"], second["layouts"][1]["id"])
        # The state given is not changed.
        self.assertEqual(len(first["layouts"]), 1)

    def test_items_of_another_form_are_refused(self) -> None:
        for items in (None, "dist", [], ["dist"] * 2, ["dist", "nope"], [1], ["dist", "pace", "hr", "mx", "cad", "pow", "load"]):
            with self.subTest(items=items):
                self.assert_refused(state(), {"op": "add", "name": "朝", "items": items}, "REQUEST_INVALID")

    def test_a_name_of_another_form_or_one_that_is_taken_is_refused(self) -> None:
        for name in ("", " ", None, 7, "a" * 31, "朝\u202eラン", "朝\nラン"):
            with self.subTest(name=name):
                self.assert_refused(state(), {"op": "add", "name": name, "items": ["dist"]}, "LAYOUT_NAME_INVALID")
        # The names of the built-in layouts, in either language, as the person
        # may type them.
        for name in ("ランの指標", "Running", "running", "ＲＵＮＮＩＮＧ", " sleep AND heart rate ", "睡眠と心拍", "Garmin Estimates", "負荷"):
            with self.subTest(name=name):
                self.assert_refused(state(), {"op": "add", "name": name, "items": ["dist"]}, "LAYOUT_NAME_TAKEN")
        mine = added(state(), "Morning")
        for name in ("morning", "ＭＯＲＮＩＮＧ", " Morning "):
            with self.subTest(name=name):
                self.assert_refused(mine, {"op": "add", "name": name, "items": ["dist"]}, "LAYOUT_NAME_TAKEN")

    def test_the_twenty_first_layout_is_refused(self) -> None:
        current = state()
        for number in range(MAX_LAYOUTS):
            current = added(current, f"型{number}")
        self.assertEqual(len(current["layouts"]), MAX_LAYOUTS)
        self.assert_refused(current, {"op": "add", "name": "もう 1 つ", "items": ["dist"]}, "LAYOUTS_FULL")

    def test_a_layout_of_the_person_is_renamed_overwritten_moved_and_removed(self) -> None:
        current = added(added(added(state(), "A"), "B"), "C")
        ids = [entry["id"] for entry in current["layouts"]]
        renamed = change_layouts(current, {"op": "rename", "id": ids[0], "name": "Ａ２"})
        self.assertEqual(renamed["layouts"][0]["name"], "Ａ２")
        # Its own name in another case is its own.
        self.assertEqual(change_layouts(current, {"op": "rename", "id": ids[1], "name": "b"})["layouts"][1]["name"], "b")
        self.assert_refused(current, {"op": "rename", "id": ids[0], "name": "c"}, "LAYOUT_NAME_TAKEN")
        overwritten = change_layouts(current, {"op": "overwrite", "id": ids[1], "items": ["rhr", "hrv"]})
        self.assertEqual((overwritten["layouts"][1]["items"], overwritten["current"]), (["rhr", "hrv"], ids[1]))
        self.assert_refused(current, {"op": "overwrite", "id": ids[1], "items": []}, "REQUEST_INVALID")
        moved = change_layouts(current, {"op": "move", "id": ids[2], "direction": "up"})
        self.assertEqual([entry["id"] for entry in moved["layouts"]], [ids[0], ids[2], ids[1]])
        moved = change_layouts(current, {"op": "move", "id": ids[0], "direction": "down"})
        self.assertEqual([entry["id"] for entry in moved["layouts"]], [ids[1], ids[0], ids[2]])
        # At either end it stays.
        self.assertEqual(change_layouts(current, {"op": "move", "id": ids[0], "direction": "up"})["layouts"], current["layouts"])
        self.assertEqual(change_layouts(current, {"op": "move", "id": ids[2], "direction": "down"})["layouts"], current["layouts"])
        self.assert_refused(current, {"op": "move", "id": ids[0], "direction": "left"}, "REQUEST_INVALID")
        removed = change_layouts(current, {"op": "remove", "id": ids[2]})
        self.assertEqual(([entry["id"] for entry in removed["layouts"]], removed["current"]), (ids[:2], None))
        kept = change_layouts({**current, "current": ids[0]}, {"op": "remove", "id": ids[1]})
        self.assertEqual(kept["current"], ids[0])
        for operation in ("rename", "overwrite", "move", "remove"):
            for layout_id in ("u-00000000", "run", None):
                with self.subTest(operation=operation, layout_id=layout_id):
                    self.assert_refused(
                        current,
                        {"op": operation, "id": layout_id, "name": "Z", "items": ["dist"], "direction": "up"},
                        "LAYOUT_NOT_FOUND",
                    )

    def test_built_in_layouts_are_hidden_shown_and_all_shown_again(self) -> None:
        hidden = change_layouts(state(), {"op": "hide", "id": "load"})
        hidden = change_layouts(hidden, {"op": "hide", "id": "run"})
        hidden = change_layouts(hidden, {"op": "hide", "id": "run"})
        self.assertEqual(hidden["hidden"], ["run", "load"])
        self.assertEqual(change_layouts(hidden, {"op": "show", "id": "run"})["hidden"], ["load"])
        self.assertEqual(change_layouts(hidden, {"op": "show", "id": "form"})["hidden"], ["run", "load"])
        self.assertEqual(change_layouts(hidden, {"op": "reset"})["hidden"], [])
        for layout_id in ("u-00000000", "Run", None):
            with self.subTest(layout_id=layout_id):
                self.assert_refused(state(), {"op": "hide", "id": layout_id}, "LAYOUT_NOT_FOUND")
        # A layout hidden is no longer the one used last; hiding another one
        # keeps it (the checker, K1-2).
        self.assertIsNone(change_layouts(state(current="form"), {"op": "hide", "id": "form"})["current"])
        self.assertEqual(change_layouts(state(current="form"), {"op": "hide", "id": "load"})["current"], "form")

    def test_a_change_of_another_form_is_refused(self) -> None:
        for change in (None, [], "add", {}, {"op": "rename2"}, {"op": 1}):
            with self.subTest(change=change):
                self.assert_refused(state(), change, "REQUEST_INVALID")


class SettingsOfVersion220Test(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.base = self.root / "base"
        self.base.mkdir()
        self.path = self.base / APP / NAME
        self.store = str(self.root / "store")
        self.parent = str(self.root / "outputs")

    def write_raw(self, data: dict[str, Any]) -> bytes:
        self.path.parent.mkdir(exist_ok=True)
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.path.write_bytes(content)
        return content

    def written(self) -> dict[str, Any]:
        return json.loads(self.path.read_bytes().decode("utf-8"))

    def view_values(self) -> dict[str, Any]:
        return {
            "view_layouts": [{"id": "u-0123abcd", "name": "朝ラン", "items": ["dist", "hr"]}, {"id": "u-89abcdef", "name": "Weekend", "items": ["time"]}],
            "view_layouts_hidden": ["sleep_hr", "load"],
            "view_layout": "u-89abcdef",
            "view_period": {"from": "2024-01-01", "to": "2024-12-31"},
            "view_grain": "week",
            "view_types": ["running", "trail_running", ""],
            "timezone": "Europe/London",
        }

    def test_format_1_is_read_and_written_as_format_2_with_its_keys(self) -> None:
        older = {
            "format": FORMAT_1,
            "store": self.store,
            "output_parent": self.parent,
            "recent_outputs": [self.parent + "-1", self.parent + "-2"],
            "hints": False,
            "theme": "dark",
            "view_items": ["dist", "rhr"],
            "view_shelf": "closed",
        }
        self.write_raw(older)
        values = {key: value for key, value in older.items() if key != "format"}
        self.assertEqual(read_settings(self.path), (values, None))
        self.assertIsNone(remember_hints_at(self.path, True))
        self.assertEqual(SETTINGS_FORMAT, "garmin-running-data-normalizer-gui-settings-v2")
        self.assertEqual(self.written(), {"format": SETTINGS_FORMAT, **values, "hints": True})

    def test_a_newer_format_is_neither_used_nor_written_over_by_the_new_changes(self) -> None:
        newer = self.write_raw({"format": NEWER_FORMAT, "view_layouts": []})
        self.assertEqual(read_settings(self.path), ({}, SETTINGS_NEWER))
        self.assertEqual(remember_view_at(self.path, ["dist"], "open", {"grain": "week"}), SETTINGS_NEWER)
        self.assertEqual(change_layouts_at(self.path, {"op": "reset"}), (state(), SETTINGS_NEWER))
        self.assertEqual(remember_run_at(self.path, self.root / "outputs" / "o1", None, "Europe/London"), SETTINGS_NEWER)
        self.assertEqual(self.path.read_bytes(), newer)

    def test_the_values_of_the_view_page_are_read_and_written(self) -> None:
        values = {"store": self.store, **self.view_values()}
        self.assertIsNone(write_settings(self.path, values))
        self.assertEqual(read_settings(self.path), (values, None))
        answer = launch_answer(values, None, present=True)
        for key, value in self.view_values().items():
            with self.subTest(key=key):
                self.assertEqual(answer[key], value)

    def test_a_value_of_another_form_is_left_out_alone(self) -> None:
        good = {"store": self.store, "hints": True, **self.view_values()}
        bad = {
            "view_layouts": {"id": "u-0123abcd"},
            "view_layouts_hidden": "run",
            "view_layout": 3,
            "view_period": {"from": "2024-12-31", "to": "2024-01-01"},
            "view_grain": "hour",
            "view_types": "running",
            "timezone": "asia/tokyo",
        }
        for key, value in bad.items():
            with self.subTest(key=key):
                self.write_raw({"format": SETTINGS_FORMAT, **good, key: value})
                values, notice = read_settings(self.path)
                expected = {name: kept for name, kept in good.items() if name != key}
                if key == "view_layouts":
                    # The layout used last was one of the layouts left out.
                    expected.pop("view_layout")
                self.assertEqual((values, notice), (expected, None))

    def test_one_layout_of_another_form_is_left_out_alone(self) -> None:
        entries = [
            {"id": "u-00000001", "name": "A", "items": ["dist", "nope", "dist", "pace", "hr", "mx", "cad", "pow", "load"]},
            {"id": "u-00000001", "name": "Twice", "items": ["dist"]},
            {"id": "U-00000002", "name": "Capital id", "items": ["dist"]},
            {"id": "u-00000003", "name": "朝\u202eラン", "items": ["dist"]},
            {"id": "u-00000004", "name": "Nothing known", "items": ["nope"]},
            {"id": "u-00000005", "name": "ガ", "items": ["rhr"]},
            "not a layout",
            {"id": "u-00000006", "name": "No items"},
        ]
        self.assertEqual(
            kept_layouts(entries),
            [
                {"id": "u-00000001", "name": "A", "items": ["dist", "pace", "hr", "mx", "cad", "pow"]},
                {"id": "u-00000005", "name": "ガ", "items": ["rhr"]},
            ],
        )
        many = [{"id": f"u-{number:08x}", "name": f"L{number}", "items": ["dist"]} for number in range(MAX_LAYOUTS + 5)]
        self.assertEqual(len(kept_layouts(many)), MAX_LAYOUTS)
        self.assertIsNone(kept_layouts("u-00000001"))
        self.assertEqual(kept_hidden(["form", "run", "nope", "run", 3]), ["run", "form"])
        self.assertIsNone(kept_hidden("run"))

    def test_the_layout_used_last_is_a_built_in_one_or_one_that_is_kept(self) -> None:
        layouts_kept = self.view_values()["view_layouts"]
        for current, kept in (("run", True), ("u-0123abcd", True), ("u-deadbeef", False), ("RUN", False), (None, False)):
            with self.subTest(current=current):
                self.write_raw({"format": SETTINGS_FORMAT, "view_layouts": layouts_kept, "view_layout": current})
                self.assertEqual(read_settings(self.path)[0].get("view_layout"), current if kept else None)

    def test_the_period_the_grouping_and_the_types(self) -> None:
        for period, kept in (
            ("all", True), ("10y", True), ("1y", True), ("custom", False), ("2y", False),
            ({"from": "2024-02-29", "to": "2024-02-29"}, True), ({"from": "2023-02-29", "to": "2023-03-01"}, False),
            ({"from": "2024-01-01"}, False), ({"from": "2024-01-01", "to": "2024-12-31", "more": 1}, False), ({"from": "20240101", "to": "20241231"}, False),
        ):
            with self.subTest(period=period):
                self.write_raw({"format": SETTINGS_FORMAT, "view_period": period})
                self.assertEqual(read_settings(self.path)[0].get("view_period"), period if kept else None)
        for grain in ("auto", "day", "week", "month", "year", "hour", None, 1):
            with self.subTest(grain=grain):
                self.write_raw({"format": SETTINGS_FORMAT, "view_grain": grain})
                expected = grain if grain in ("auto", "day", "week", "month", "year") else None
                self.assertEqual(read_settings(self.path)[0].get("view_grain"), expected)
        # The activity types counted are kept whole or not at all, so that an
        # opening never counts other types than those chosen (the checker,
        # K1-2); the other values stay. No type counted is a choice of its own.
        for types, kept in (
            (["running", "", "Treadmill Running", "x" * MAX_TYPE_LENGTH], True),
            ([f"t{number}" for number in range(MAX_TYPES)], True),
            ([], True),
            ([f"t{number}" for number in range(MAX_TYPES + 1)], False),
            (["running", "running"], False),
            (["running", "a\x00b"], False),
            (["running", "c\u202ed"], False),
            (["running", 3], False),
            (["running", "x" * (MAX_TYPE_LENGTH + 1)], False),
            ("running", False),
        ):
            with self.subTest(types=types):
                self.write_raw({"format": SETTINGS_FORMAT, "view_types": types, "view_grain": "week"})
                values = read_settings(self.path)[0]
                self.assertEqual((values.get("view_types"), values["view_grain"]), (types if kept else None, "week"))

    def test_the_timezone_is_one_that_the_cli_takes(self) -> None:
        for timezone, kept in (
            ("Europe/London", True), ("America/Argentina/Buenos_Aires", True), ("UTC", True),
            ("asia/tokyo", False), ("Factory", False), ("Asia/Tokyo/", False), ("../Asia/Tokyo", False),
            ("Nowhere/Place", False), ("", False), (9, False), ("A" * 65, False),
        ):
            with self.subTest(timezone=timezone):
                self.write_raw({"format": SETTINGS_FORMAT, "timezone": timezone})
                self.assertEqual(read_settings(self.path)[0].get("timezone"), timezone if kept else None)

    def test_a_run_that_made_its_output_remembers_its_timezone(self) -> None:
        output = self.root / "outputs" / "o1"
        self.assertIsNone(remember_run_at(self.path, output, None, "Europe/London"))
        self.assertEqual(read_settings(self.path)[0]["timezone"], "Europe/London")
        # A name of another form is not remembered, and the one before stays;
        # without a timezone the one before stays too.
        self.assertIsNone(remember_run_at(self.path, output, None, "asia/tokyo"))
        self.assertIsNone(remember_run_at(self.path, output, None))
        self.assertEqual(read_settings(self.path)[0]["timezone"], "Europe/London")
        self.assertIsNone(remember_run_at(self.path, output, None, "America/New_York"))
        self.assertEqual(read_settings(self.path)[0]["timezone"], "America/New_York")

    def test_the_view_page_changes_only_the_values_that_it_gives(self) -> None:
        self.assertIsNone(write_settings(self.path, {"store": self.store, **self.view_values()}))
        self.assertIsNone(remember_view_at(self.path, ["dist"], "open", {"grain": "month", "period": "5y"}))
        values = read_settings(self.path)[0]
        self.assertEqual((values["view_grain"], values["view_period"], values["view_layout"]), ("month", "5y", "u-89abcdef"))
        self.assertEqual(values["view_types"], ["running", "trail_running", ""])
        # None takes the layout used last and the types away; the rest stays.
        self.assertIsNone(remember_view_at(self.path, ["dist"], "open", {"layout": None, "types": None}))
        values = read_settings(self.path)[0]
        self.assertNotIn("view_layout", values)
        self.assertNotIn("view_types", values)
        self.assertEqual((values["view_grain"], values["store"], values["view_layouts"]), ("month", self.store, self.view_values()["view_layouts"]))
        self.assertIsNone(remember_view_at(self.path, ["dist"], "open", {"layout": "run", "types": ["running"]}))
        values = read_settings(self.path)[0]
        self.assertEqual((values["view_layout"], values["view_types"]), ("run", ["running"]))

    def largest_values(self) -> dict[str, Any]:
        """The largest settings that a person can make on a system whose places
        are up to 1024 bytes, as macOS keeps them (stage K1 of v2.2.0)."""
        def place(mark: str) -> str:
            head = str(self.root / mark)
            return head + "p" * (1024 - len(head.encode("utf-8")))
        return {
            "store": place("s"),
            "output_parent": place("o"),
            "recent_outputs": [place(f"r{number}") for number in range(10)],
            "hints": True,
            "theme": "dark",
            "view_items": ["dist", "pace", "hr", "mx", "cad", "pow"],
            "view_shelf": "open",
            "view_layouts": [
                {"id": f"u-{number:08x}", "name": "😀" * MAX_LAYOUT_NAME_LENGTH, "items": ["dist", "pace", "hr", "mx", "cad", "pow"]}
                for number in range(MAX_LAYOUTS)
            ],
            "view_layouts_hidden": list(BUILT_IN_IDS),
            "view_layout": "u-00000000",
            "view_period": {"from": "2011-04-03", "to": "2026-10-21"},
            "view_grain": "week",
            "view_types": [f"{number:02d}" + "t" * (MAX_TYPE_LENGTH - 2) for number in range(MAX_TYPES)],
            # A long name that every system has (not a link of the backward file).
            "timezone": "America/Argentina/Buenos_Aires",
        }

    def test_the_largest_settings_of_a_person_are_written_and_read_back(self) -> None:
        values = self.largest_values()
        self.assertIsNone(write_settings(self.path, values))
        self.assertLessEqual(self.path.stat().st_size, MAX_SETTINGS_BYTES)
        self.assertEqual(read_settings(self.path), (values, None))

    def test_settings_over_the_limit_are_not_written_and_the_file_before_stays(self) -> None:
        values = self.largest_values()
        self.assertIsNone(write_settings(self.path, values))
        before = self.path.read_bytes()
        # Places of 4096 characters of three bytes each, as a system of long
        # places allows: the file would be over the limit, and not read again.
        longer = {**values, "recent_outputs": [str(self.root / f"{number}") + "語" * 3800 for number in range(10)]}
        self.assertEqual(write_settings(self.path, longer), SETTINGS_NOT_WRITTEN)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(read_settings(self.path), (values, None))

    def test_settings_of_the_size_of_the_limit_are_written(self) -> None:
        values = {"store": self.store, "hints": True}
        self.assertIsNone(write_settings(self.path, values))
        size = len(self.path.read_bytes())
        with patch.object(settings, "MAX_SETTINGS_BYTES", size):
            self.assertIsNone(write_settings(self.path, values))
        with patch.object(settings, "MAX_SETTINGS_BYTES", size - 1):
            self.assertEqual(write_settings(self.path, {"hints": True, "store": self.store}), SETTINGS_NOT_WRITTEN)

    def test_each_change_that_would_go_over_the_limit_says_so(self) -> None:
        # With the limit at the size of the file now, a change that makes the
        # file larger is not written; the file is still read.
        self.assertIsNone(write_settings(self.path, {"store": self.store, "hints": True}))
        before = self.path.read_bytes()
        with patch.object(settings, "MAX_SETTINGS_BYTES", len(before)):
            self.assertEqual(read_settings(self.path), ({"store": self.store, "hints": True}, None))
            self.assertEqual(remember_hints_at(self.path, False), SETTINGS_NOT_WRITTEN)
            self.assertEqual(remember_view_at(self.path, ["dist"], "open", {"grain": "week"}), SETTINGS_NOT_WRITTEN)
            self.assertEqual(remember_run_at(self.path, self.root / "outputs" / "o1", None, "Europe/London"), SETTINGS_NOT_WRITTEN)
            self.assertEqual(
                change_layouts_at(self.path, {"op": "add", "name": "朝ラン", "items": ["dist"]}),
                (state(), SETTINGS_NOT_WRITTEN),
            )
        self.assertEqual(self.path.read_bytes(), before)

    def test_a_change_of_the_layouts_is_written_or_the_layouts_before_are_answered(self) -> None:
        self.assertIsNone(write_settings(self.path, {"store": self.store}))
        after, notice = change_layouts_at(self.path, {"op": "add", "name": "朝ラン", "items": ["dist", "hr"]})
        self.assertIsNone(notice)
        values = read_settings(self.path)[0]
        self.assertEqual((values["view_layouts"], values["view_layout"], values["store"]), (after["layouts"], after["current"], self.store))
        before = self.path.read_bytes()
        with patch.object(settings, "write_settings", return_value=SETTINGS_NOT_WRITTEN):
            self.assertEqual(
                change_layouts_at(self.path, {"op": "remove", "id": after["current"]}),
                ({"layouts": after["layouts"], "hidden": [], "current": after["current"]}, SETTINGS_NOT_WRITTEN),
            )
        # A change that cannot be made writes nothing.
        with self.assertRaises(LayoutChangeError):
            change_layouts_at(self.path, {"op": "add", "name": "ランの指標", "items": ["dist"]})
        self.assertEqual(self.path.read_bytes(), before)
        # Removing the layout used last forgets that it was used.
        self.assertIsNone(change_layouts_at(self.path, {"op": "remove", "id": after["current"]})[1])
        self.assertNotIn("view_layout", read_settings(self.path)[0])

    def test_two_changes_at_once_keep_both(self) -> None:
        start = threading.Barrier(2)
        errors: list[BaseException] = []

        def add_many(mark: str) -> None:
            try:
                start.wait(timeout=10)
                for number in range(MAX_LAYOUTS // 2):
                    self.assertIsNone(change_layouts_at(self.path, {"op": "add", "name": f"{mark}{number}", "items": ["dist"]})[1])
            except BaseException as exc:  # pragma: no cover - reported below
                errors.append(exc)

        threads = [threading.Thread(target=add_many, args=(mark,)) for mark in ("A", "B")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(errors, [])
        kept = read_settings(self.path)[0]["view_layouts"]
        self.assertEqual(len(kept), MAX_LAYOUTS)
        self.assertEqual(len({entry["id"] for entry in kept}), MAX_LAYOUTS)
        self.assertEqual({entry["name"] for entry in kept}, {f"{mark}{number}" for mark in "AB" for number in range(MAX_LAYOUTS // 2)})


class ViewRequestTypesTest(unittest.TestCase):
    def test_the_numbers_take_the_types_as_2_1_0_did(self) -> None:
        # Names of any number, length, and characters, each once, which the
        # limit of the size of a request bounds (the checker, K1-2): an output
        # may have more types than the settings keep (types_kept).
        for types in (
            ["running", ""], [f"t{number}" for number in range(MAX_TYPES + 1)], ["x" * (MAX_TYPE_LENGTH + 1)],
            ["a\x00b"], ["c\u202ed"], [], None,
        ):
            with self.subTest(types=types):
                self.assertEqual(series_request({"items": ["dist"], "types": types})[3], types)
        for types in (["running", "running"], [3], "running", {"running": True}):
            with self.subTest(types=types):
                with self.assertRaises(ViewRequestError):
                    series_request({"items": ["dist"], "types": types})


class LayoutsApiTest(GuiServerTestCase):
    def post(self, path: str, payload: Any = None) -> tuple[int, dict[str, Any]]:
        body = json.dumps({} if payload is None else payload).encode("utf-8")
        status, _, answer = self.post_api(path, body=body)
        return status, json.loads(answer)

    def test_the_view_page_remembers_its_layout_period_grouping_and_types(self) -> None:
        path = places.settings_file()
        payload = {"items": ["dist"], "shelf": "open", "layout": "run", "period": {"from": "2024-01-01", "to": "2024-06-30"}, "grain": "week", "types": ["running", ""]}
        self.assertEqual(self.post("/api/settings/view", payload), (200, {"remembered": True, "notice": None}))
        values = read_settings(path)[0]
        self.assertEqual(
            {key: values[key] for key in ("view_layout", "view_period", "view_grain", "view_types")},
            {"view_layout": "run", "view_period": {"from": "2024-01-01", "to": "2024-06-30"}, "view_grain": "week", "view_types": ["running", ""]},
        )
        settings_answer = self.post("/api/status")[1]["settings"]
        self.assertEqual((settings_answer["view_layout"], settings_answer["view_grain"]), ("run", "week"))
        # The values not given stay; None takes the layout and the types away.
        self.assertEqual(self.post("/api/settings/view", {"items": ["rhr"], "shelf": "closed", "layout": None, "types": None})[0], 200)
        values = read_settings(path)[0]
        self.assertEqual((values.get("view_layout"), values.get("view_types"), values["view_grain"], values["view_items"]), (None, None, "week", ["rhr"]))

    def test_values_of_another_form_are_refused(self) -> None:
        base = {"items": ["dist"], "shelf": "open"}
        for extra in (
            {"layout": "RUN"}, {"layout": "u-XYZ"}, {"layout": 3}, {"period": "custom"}, {"period": None},
            {"period": {"from": "2024-12-31", "to": "2024-01-01"}}, {"grain": "hour"}, {"grain": None},
            {"types": ["running", "running"]}, {"types": "running"}, {"types": [3]},
        ):
            with self.subTest(extra=extra):
                self.assertEqual(self.post("/api/settings/view", {**base, **extra}), (422, {"error": "REQUEST_INVALID"}))
        self.assertFalse(places.settings_file().exists())

    def test_a_choice_of_types_that_cannot_be_kept_whole_is_not_remembered(self) -> None:
        # The page may count types that the settings cannot keep (the checker,
        # K1-2): the choice before is forgotten too, so that the next opening
        # counts those counted at first; the other values are remembered.
        path = places.settings_file()
        base = {"items": ["dist"], "shelf": "open"}
        for types in ([f"t{n}" for n in range(MAX_TYPES + 1)], ["running", "a\u202eb"], ["running", "x" * (MAX_TYPE_LENGTH + 1)]):
            with self.subTest(types=types):
                self.assertEqual(self.post("/api/settings/view", {**base, "types": ["running"]})[0], 200)
                self.assertEqual(read_settings(path)[0]["view_types"], ["running"])
                self.assertEqual(
                    self.post("/api/settings/view", {**base, "grain": "week", "types": types}),
                    (200, {"remembered": True, "notice": None}),
                )
                written = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotIn("view_types", written)
                self.assertEqual(written["view_grain"], "week")
        self.assertEqual(self.post("/api/settings/view", {**base, "types": []})[0], 200)
        self.assertEqual(read_settings(path)[0]["view_types"], [])

    def test_the_layouts_change_one_at_a_time(self) -> None:
        status, answer = self.post("/api/settings/layouts", {"op": "add", "name": "朝ラン", "items": ["dist", "hr"]})
        self.assertEqual((status, answer["remembered"], answer["notice"], answer["hidden"]), (200, True, None, []))
        mine = answer["layouts"][0]["id"]
        self.assertEqual((answer["layouts"], answer["layout"]), ([{"id": mine, "name": "朝ラン", "items": ["dist", "hr"]}], mine))
        answer = self.post("/api/settings/layouts", {"op": "rename", "id": mine, "name": "夜ラン"})[1]
        self.assertEqual(answer["layouts"][0]["name"], "夜ラン")
        answer = self.post("/api/settings/layouts", {"op": "hide", "id": "load"})[1]
        self.assertEqual(answer["hidden"], ["load"])
        settings_answer = self.post("/api/status")[1]["settings"]
        self.assertEqual(
            (settings_answer["view_layouts"], settings_answer["view_layouts_hidden"], settings_answer["view_layout"]),
            ([{"id": mine, "name": "夜ラン", "items": ["dist", "hr"]}], ["load"], mine),
        )
        answer = self.post("/api/settings/layouts", {"op": "remove", "id": mine})[1]
        self.assertEqual((answer["layouts"], answer["layout"]), ([], None))

    def test_a_change_that_cannot_be_made_answers_its_code(self) -> None:
        self.assertEqual(self.post("/api/settings/layouts", {"op": "add", "name": "朝ラン", "items": ["dist"]})[0], 200)
        for payload, code in (
            ({"op": "add", "name": "朝\u202eラン", "items": ["dist"]}, "LAYOUT_NAME_INVALID"),
            ({"op": "add", "name": "ＲＵＮＮＩＮＧ", "items": ["dist"]}, "LAYOUT_NAME_TAKEN"),
            ({"op": "add", "name": " 朝ラン ", "items": ["dist"]}, "LAYOUT_NAME_TAKEN"),
            ({"op": "rename", "id": "u-00000000", "name": "x"}, "LAYOUT_NOT_FOUND"),
            ({"op": "hide", "id": "u-00000000"}, "LAYOUT_NOT_FOUND"),
            ({"op": "add", "name": "x", "items": ["nope"]}, "REQUEST_INVALID"),
            ({"op": "drop"}, "REQUEST_INVALID"),
            ({"name": "x"}, "REQUEST_INVALID"),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.post("/api/settings/layouts", payload), (422, {"error": code}))
        for number in range(1, MAX_LAYOUTS):
            self.assertEqual(self.post("/api/settings/layouts", {"op": "add", "name": f"型{number}", "items": ["dist"]})[0], 200)
        self.assertEqual(
            self.post("/api/settings/layouts", {"op": "add", "name": "もう 1 つ", "items": ["dist"]}),
            (422, {"error": "LAYOUTS_FULL"}),
        )

    def test_layouts_that_are_not_written_say_so(self) -> None:
        path = places.settings_file()
        with patch.object(settings, "write_settings", return_value=SETTINGS_NOT_WRITTEN):
            self.assertEqual(
                self.post("/api/settings/layouts", {"op": "hide", "id": "run"}),
                (200, {"remembered": False, "notice": SETTINGS_NOT_WRITTEN, "layouts": [], "hidden": [], "layout": None}),
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        newer = json.dumps({"format": NEWER_FORMAT}).encode()
        path.write_bytes(newer)
        self.assertEqual(
            self.post("/api/settings/layouts", {"op": "hide", "id": "run"}),
            (200, {"remembered": False, "notice": SETTINGS_NEWER, "layouts": [], "hidden": [], "layout": None}),
        )
        self.assertEqual(path.read_bytes(), newer)


if __name__ == "__main__":
    unittest.main()
