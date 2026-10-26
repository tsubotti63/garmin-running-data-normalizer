"""The words of the view page for the numbers of the server (stage G3b): the
names and the units of the items, the first items, the groups, the choices of
the period and the grouping, and the codes that the page words itself, read
from view_flow.mjs and view.mjs and checked against the tables of the package.
The page holds no table of the items beyond its words; the node tests check
how it writes them.
"""
from __future__ import annotations

import re
import unittest
from fractions import Fraction
from pathlib import Path

# Import the diagnostics package before modules that import standalone: the
# other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.gui.settings import SHELF_STATES
from garmin_running_data_normalizer.view.items import FIRST_ITEMS, ITEMS
from garmin_running_data_normalizer.view.series import GRAINS, LAST_YEARS, MAX_PANELS


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/garmin_running_data_normalizer"
STATIC_ROOT = SOURCE / "gui/static"
FLOW = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
PAGE = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")

# The units of the server's table that the page writes in its own unit, and
# the factor from one to the other.
UNITS = {
    ("metre", "km"): Fraction(1, 1000),
    ("metre", "m"): Fraction(1),
    ("millimetre", "cm"): Fraction(1, 10),
    ("millimetre", "m"): Fraction(1, 1000),
    ("second", "hm"): Fraction(1, 60),
    ("second", "hms"): Fraction(1),
    ("minute", "hm"): Fraction(1),
    ("minute", "min"): Fraction(1),
    ("second_per_metre", "pace"): Fraction(1000),
    ("activity", "count"): Fraction(1),
    ("beats_per_minute", "bpm"): Fraction(1),
    ("millisecond", "ms"): Fraction(1),
    ("percent", "pct"): Fraction(1),
    ("percent", "pct_fit"): Fraction(1),
    (None, "raw"): Fraction(1),
}


def table(source: str, name: str) -> dict[str, str]:
    """A table of strings of a script, in its order."""
    match = re.search(rf"const {name} = \{{\n(.*?)\n\}};", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"no table {name}")
    return dict(re.findall(r'^  "?([\w]+)"?: "([^"]*)",$', match.group(1), re.MULTILINE))


def array(source: str, name: str) -> list[str]:
    match = re.search(rf"const {name} = \[([^\]]*)\];", source)
    if match is None:
        raise AssertionError(f"no list {name}")
    return re.findall(r'"([^"]+)"', match.group(1))


def factor(text: str) -> Fraction:
    parts = [part.strip() for part in text.split("/")]
    value = Fraction(parts[0])
    for part in parts[1:]:
        value /= Fraction(part)
    return value


def formats() -> dict[str, tuple[str, Fraction, int]]:
    match = re.search(r"export const ITEM_FORMATS = \{\n(.*?)\n\};", FLOW, re.DOTALL)
    assert match is not None
    entries = re.findall(r'^  (\w+): \{ unit: "(\w+)", factor: ([0-9./ ]+), digits: (\d) \},$', match.group(1), re.MULTILINE)
    return {key: (unit, factor(value), int(digits)) for key, unit, value, digits in entries}


class ViewPageWordsTest(unittest.TestCase):
    def test_the_page_names_and_writes_every_item_of_the_server(self) -> None:
        keys = [item.key for item in ITEMS]
        self.assertEqual(table(FLOW, "ITEM_KEYS"), {key: f"view.item.{key}" for key in keys})
        self.assertEqual(list(table(FLOW, "ITEM_KEYS")), keys)
        written = formats()
        self.assertEqual(list(written), keys)
        units = table(FLOW, "UNIT_KEYS")
        for item in ITEMS:
            unit, value, digits = written[item.key]
            with self.subTest(item=item.key):
                # A unit of the page is a unit of the server, converted.
                self.assertEqual(UNITS[(item.unit, unit)], value)
                self.assertIn(unit, units)
                self.assertLessEqual(digits, 2)

    def test_the_choices_of_the_page_are_those_of_the_server(self) -> None:
        self.assertEqual(array(FLOW, "FIRST_KEYS"), list(FIRST_ITEMS))
        self.assertEqual(array(FLOW, "GROUPS"), list(dict.fromkeys(item.group for item in ITEMS)))
        self.assertEqual(array(FLOW, "GRAINS"), ["auto", *GRAINS])
        self.assertEqual(array(FLOW, "PERIODS"), ["all", *LAST_YEARS, "custom"])
        self.assertEqual(array(FLOW, "SHELF_STATES"), list(SHELF_STATES))
        self.assertIn(f"export const MAX_PANELS = {MAX_PANELS};", FLOW)
        # The buttons of the page are those choices.
        page = (STATIC_ROOT / "view.html").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'data-period="(\w+)"', page), ["all", *LAST_YEARS, "custom"])
        self.assertEqual(re.findall(r'data-grain="(\w+)"', page), ["auto", *GRAINS])
        self.assertEqual(set(table(FLOW, "GRAIN_KEYS")), set(GRAINS))
        self.assertEqual(set(table(FLOW, "GRAIN_COUNT_KEYS")), set(GRAINS))

    def test_the_two_series_of_vo2max_are_those_of_the_normalization(self) -> None:
        # The page colors the series by their order, and names the two that
        # the normalization writes in its note.
        normalizer = (SOURCE / "normalizers/vo2max.py").read_text(encoding="utf-8")
        for name in ("VO2_ACTIVITY", "VO2_MAXMET"):
            with self.subTest(series=name):
                value = re.search(rf'const {name} = "([a-z0-9_]+)";', FLOW)
                assert value is not None
                self.assertIn(f'"{value.group(1)}"', normalizer)

    def test_the_stops_of_an_output_are_codes_of_its_checks(self) -> None:
        # The stops that close the output on the page, and the three that
        # the page words itself, are codes that opening or reading an output
        # gives.
        given = set()
        for name in ("output_check.py", "view/data.py"):
            given |= set(re.findall(r'OutputActionError\(\s*"([A-Z_]+)"', (SOURCE / name).read_text(encoding="utf-8")))
        given.add("TIMEZONE_DATA_UNAVAILABLE")
        stops = array(PAGE, "OUTPUT_STOPS")
        self.assertLessEqual(set(stops), given)
        # Exactly the stops of the output itself: another version, a change,
        # a file that cannot be read, a failed check, and the timezone data
        # (the checker's review of stage G3b-2).
        self.assertEqual(
            stops,
            [
                "OUTPUT_OTHER_VERSION",
                "SERIES_OUTPUT_OTHER_VERSION",
                "OUTPUT_CHANGED",
                "OUTPUT_NOT_AVAILABLE",
                "HANDOFF_INVALID",
                "TIMEZONE_DATA_UNAVAILABLE",
            ],
        )
        own = set(re.findall(r"^  ([A-Z_]+): \[", re.search(r"const VIEW_STOP_KEYS = \{(.*?)\n\};", FLOW, re.DOTALL).group(1), re.MULTILINE))
        self.assertEqual(own, {"OUTPUT_NOT_AVAILABLE", "OUTPUT_CHANGED", "HANDOFF_INVALID"})
        self.assertLessEqual(own, given)


if __name__ == "__main__":
    unittest.main()
