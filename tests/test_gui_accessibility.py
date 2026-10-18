"""Accessibility rules that can be checked without a browser.

The page's labels, button names, heading order, live regions, and colors are
read from the packaged files. Keyboard-only use and screen readers are checked
by hand before a release.
"""
from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "src/garmin_running_data_normalizer/gui/static"
LANGUAGES = ("en", "ja")

# Colors that the stylesheet puts together, with the WCAG 2.1 AA minimum:
# 4.5:1 for text, and 3:1 for the parts that identify a control or its focus.
TEXT_PAIRS = (
    ("text", "surface"),  # the boxes, fields, buttons, and tables
    ("text", "page"),  # the title area
    ("text", "group"),  # table heads and the bar at the bottom
    ("text", "ng-tint"),  # a box that needs a fix
    ("sub", "surface"),  # help, notes, and labels
    ("sub", "page"),
    ("sub", "group"),
    ("sub", "ng-tint"),
    ("muted", "surface"),  # steps that are not run yet, absent data
    ("muted", "group"),
    ("on-accent", "accent"),  # the primary button and the current number
    ("accent", "surface"),  # links and the current badge
    ("accent", "accent-soft"),
    ("accent", "group"),  # "Now" in the steps of the help panel
    ("accent", "ng-tint"),  # an information button in a box that needs a fix
    ("ok", "surface"),  # the summary of a confirmed box
    ("ok", "ok-soft"),  # a done badge or pill
    ("ok", "group"),  # "Done" in the steps of the help panel
    ("warn", "warn-soft"),  # a warning pill
    ("ng", "surface"),  # the heading of a stop
    ("ng", "ng-soft"),
    ("ng", "ng-tint"),
    ("none", "none-soft"),  # an absent or not-yet pill
    ("surface", "ok"),  # the mark in a confirmed box's number
    ("surface", "ng"),  # the mark in a red box's number
    ("surface", "text"),  # the open part of the help panel, and Help while it is open
)
# The bar beside a warning row is decoration: the icon and the words carry
# the meaning, so it is not a pair here.
CONTROL_PAIRS = (
    ("edge", "surface"),  # the edges of fields and buttons
    ("edge", "page"),
    ("edge", "ng-tint"),
    ("edge", "group"),  # the buttons on the gray parts of the help panel
    ("accent", "surface"),  # the focus outline, the current box, and the primary button
    ("accent", "page"),
    ("accent", "ng-tint"),
    ("ng", "surface"),  # the edge of a box that needs a fix, and of a stop
    ("ok", "surface"),  # the edge of a confirmed box
)


class Element:
    def __init__(self, tag: str, attributes: dict[str, str | None], parent: Element | None) -> None:
        self.tag = tag
        self.attributes = attributes
        self.parent = parent

    def get(self, name: str) -> str | None:
        return self.attributes.get(name)

    def ancestors(self) -> list[Element]:
        found = []
        node = self.parent
        while node is not None:
            found.append(node)
            node = node.parent
        return found


class _PageParser(HTMLParser):
    VOID = {"meta", "link", "input", "br", "img", "hr"}

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[Element] = []
        self._open: list[Element] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, dict(attrs), self._open[-1] if self._open else None)
        self.elements.append(element)
        if tag not in self.VOID:
            self._open.append(element)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index].tag == tag:
                del self._open[index:]
                return


def page() -> list[Element]:
    parser = _PageParser()
    parser.feed((STATIC_ROOT / "index.html").read_text(encoding="utf-8"))
    parser.close()
    return parser.elements


def by_id(elements: list[Element], identifier: str) -> Element:
    matches = [element for element in elements if element.get("id") == identifier]
    if len(matches) != 1:
        raise AssertionError(f"expected one element with id {identifier}")
    return matches[0]


def is_live(element: Element) -> bool:
    return element.get("aria-live") is not None or element.get("role") in {"status", "alert"}


def theme_colors() -> dict[str, dict[str, str]]:
    """Return the color variables of the light theme and the dark theme."""
    source = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
    light_block = re.search(r"^:root \{(.*?)^\}", source, re.MULTILINE | re.DOTALL)
    dark_block = re.search(
        r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}\s*\}", source, re.DOTALL
    )
    if light_block is None or dark_block is None:
        raise AssertionError("styles.css has no light or dark color variables")

    def colors(block: str) -> dict[str, str]:
        return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6});", block))

    light = colors(light_block.group(1))
    return {"light": light, "dark": {**light, **colors(dark_block.group(1))}}


def relative_luminance(color: str) -> float:
    def linear(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(int(color[index : index + 2], 16)) for index in (1, 3, 5))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class GuiPageStructureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.elements = page()
        self.catalogs = {
            language: json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            for language in LANGUAGES
        }

    def test_every_field_has_a_label(self) -> None:
        labelled = {element.get("for") for element in self.elements if element.tag == "label"}
        fields = [
            element
            for element in self.elements
            if element.tag in {"input", "select", "textarea"} and element.get("type") != "hidden"
        ]
        self.assertTrue(fields)
        for field in fields:
            with self.subTest(field=field.get("id")):
                self.assertTrue(
                    field.get("id") in labelled
                    or field.get("aria-label")
                    or field.get("aria-labelledby"),
                )

    def test_every_button_has_a_name_in_both_languages(self) -> None:
        buttons = [element for element in self.elements if element.tag == "button"]
        self.assertTrue(buttons)
        for button in buttons:
            with self.subTest(button=button.get("id")):
                self.assertEqual(button.get("type"), "button")
                key = button.get("data-i18n")
                self.assertIsNotNone(key)
                for language in LANGUAGES:
                    self.assertTrue(self.catalogs[language].get(str(key), "").strip(), language)

    def test_headings_do_not_skip_levels(self) -> None:
        levels = [
            int(element.tag[1])
            for element in self.elements
            if re.fullmatch(r"h[1-6]", element.tag)
        ]
        self.assertEqual(levels[0], 1)
        self.assertEqual(levels.count(1), 1)
        for previous, current in zip(levels, levels[1:]):
            self.assertLessEqual(current, previous + 1, levels)

    def test_progress_counts_stay_out_of_live_regions(self) -> None:
        # Counts and seconds change every second; only the hidden announcer,
        # which speaks when the stage changes, is live in the run area.
        progress = by_id(self.elements, "run-progress")
        self.assertFalse(is_live(progress))
        self.assertFalse(any(is_live(ancestor) for ancestor in progress.ancestors()))
        self.assertFalse(is_live(by_id(self.elements, "run-result")))
        announcer = by_id(self.elements, "run-announcer")
        self.assertEqual(announcer.get("aria-live"), "polite")
        self.assertIn("visually-hidden", str(announcer.get("class")).split())

    def test_live_regions_are_polite_apart_from_the_connection_alert(self) -> None:
        for element in self.elements:
            if element.get("aria-live") is not None:
                with self.subTest(element=element.get("id")):
                    self.assertEqual(element.get("aria-live"), "polite")
        alerts = [element.get("id") for element in self.elements if element.get("role") == "alert"]
        self.assertEqual(alerts, ["connection-problem"])

    def test_focus_targets_after_actions_can_take_focus(self) -> None:
        # The page moves focus to these headings at the end of a run, to the
        # stop in the box that it concerns, to the next box when one is
        # confirmed, or when the button that had focus stays disabled.
        for identifier in (
            "input-heading",
            "output-heading",
            "run-heading",
            "result-heading",
            "export-error-heading",
            "output-error-heading",
            "run-error-heading",
            "output-check-heading",
            "bundle-heading",
            "browser-heading",
            "help-heading",
            "help-steps-heading",
            "help-faq-heading",
            "help-words-heading",
            "help-ai-heading",
        ):
            with self.subTest(heading=identifier):
                self.assertEqual(by_id(self.elements, identifier).get("tabindex"), "-1")


    def test_the_ways_to_normalize_and_the_fields_of_an_import(self) -> None:
        # From stage B4b-1 both ways to normalize can be chosen, the Snapshots
        # first; the note that the other way does not use the store is shown
        # when that way is chosen. The parts of the Snapshot Store wait for
        # the server, as every button does, and point at no reason.
        snapshots = by_id(self.elements, "how-snapshots")
        single = by_id(self.elements, "how-single")
        self.assertEqual(("disabled" in snapshots.attributes, "disabled" in single.attributes), (False, False))
        self.assertEqual(("checked" in snapshots.attributes, "checked" in single.attributes), (True, False))
        self.assertIn("hidden", by_id(self.elements, "how-note").attributes)
        for identifier in ("store-create", "store-open", "store-open-other", "store-create-new", "store-check"):
            with self.subTest(part=identifier):
                button = by_id(self.elements, identifier)
                self.assertEqual(button.tag, "button")
                self.assertIsNone(button.get("aria-describedby"))
        # The fields of an import have a label each and say what they take.
        for identifier in ("snapshot-label", "downloaded-at"):
            with self.subTest(field=identifier):
                field = by_id(self.elements, identifier)
                self.assertEqual(field.get("aria-describedby"), f"{identifier}-help")
                labels = [element for element in self.elements if element.tag == "label" and element.get("for") == identifier]
                self.assertEqual(len(labels), 1)
        # The lines of the store and of an import are spoken when they change.
        for identifier in ("store-result", "import-result"):
            with self.subTest(lines=identifier):
                result = by_id(self.elements, identifier)
                self.assertEqual((result.get("role"), result.get("aria-live")), ("status", "polite"))

    def test_the_lock_file_is_removed_only_after_a_labelled_check(self) -> None:
        # Stage B4b-2: the check has its label and is described by the age of
        # the lock file; the part is hidden until a store has a lock file.
        self.assertIn("hidden", by_id(self.elements, "lock-area").attributes)
        check = by_id(self.elements, "lock-confirm")
        self.assertEqual((check.get("type"), check.get("aria-describedby")), ("checkbox", "lock-time"))
        labels = [element for element in self.elements if element.tag == "label" and element.get("for") == "lock-confirm"]
        self.assertEqual(len(labels), 1)
        self.assertEqual(by_id(self.elements, "lock-remove").tag, "button")

    def test_folded_help_says_whether_it_is_open(self) -> None:
        toggle = by_id(self.elements, "tools-toggle")
        self.assertEqual(toggle.get("aria-expanded"), "false")
        self.assertEqual(toggle.get("aria-controls"), "tools-body")
        self.assertIn("hidden", by_id(self.elements, "tools-body").attributes)

    def test_the_help_panel_is_a_closed_side_panel_with_four_parts(self) -> None:
        # Stage B1b: the panel pushes the page aside instead of covering it,
        # so it is a complementary landmark, not a dialog.
        button = by_id(self.elements, "help-button")
        self.assertEqual(button.get("aria-expanded"), "false")
        self.assertEqual(button.get("aria-controls"), "help-panel")
        panel = by_id(self.elements, "help-panel")
        self.assertEqual(panel.tag, "aside")
        self.assertIsNone(panel.get("role"))
        self.assertEqual(panel.get("aria-labelledby"), "help-heading")
        self.assertIn("hidden", panel.attributes)
        nav = [element for element in self.elements if element.tag == "nav"]
        self.assertEqual(len(nav), 1)
        self.assertEqual(by_id(self.elements, nav[0].get("aria-labelledby")).get("data-i18n"), "help.nav")
        for name in ("steps", "faq", "words", "ai"):
            with self.subTest(part=name):
                self.assertEqual(by_id(self.elements, f"help-nav-{name}").get("data-section"), name)
                section = by_id(self.elements, f"help-{name}")
                self.assertEqual(section.get("aria-labelledby"), f"help-{name}-heading")
                self.assertEqual("hidden" in section.attributes, name != "steps")
        for element in self.elements:
            if element.get("class") == "copy-button":
                with self.subTest(copy=element.get("id")):
                    described = by_id(self.elements, str(element.get("aria-describedby")))
                    self.assertEqual(described.get("id"), element.get("data-copy"))

    def test_information_buttons_open_a_part_under_them(self) -> None:
        # Stage B1b: an information button is a disclosure, named by its own
        # word first and then by what it explains (WCAG 2.5.3).
        buttons = [element for element in self.elements if element.get("class") == "info-button"]
        self.assertEqual(
            [button.get("id") for button in buttons],
            [
                "how-info-button",
                # The Snapshot Store and the default place (stage B4a).
                "store-info-button",
                "place-info-button",
                "timezone-info-button",
                "pack-info-button",
                "exit-info-button",
                "tools-info-button",
            ],
        )
        for button in buttons:
            with self.subTest(button=button.get("id")):
                self.assertEqual(button.get("aria-expanded"), "false")
                region = by_id(self.elements, str(button.get("aria-controls")))
                self.assertIn("hidden", region.attributes)
                self.assertIsNone(region.get("role"))
                own, named = str(button.get("aria-labelledby")).split()
                self.assertEqual(own, button.get("id"))
                # The exit code is written by the page; the others are labels.
                self.assertTrue(by_id(self.elements, named).get("data-i18n") or named == "run-exit")

    def test_tips_show_under_every_box_heading_with_a_switch(self) -> None:
        switch = by_id(self.elements, "hints-toggle")
        self.assertEqual(switch.get("type"), "checkbox")
        self.assertEqual(switch.get("role"), "switch")
        self.assertIn("checked", switch.attributes)
        hints = [element.get("data-i18n") for element in self.elements if element.get("class") == "hint"]
        self.assertEqual(hints, ["hint.export", "hint.snapshot", "hint.output", "hint.run"])


class GuiStyleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
        self.themes = theme_colors()

    def test_every_color_variable_is_defined_in_both_themes(self) -> None:
        used = set(re.findall(r"var\(--([a-z-]+)\)", self.source))
        light = theme_colors()["light"]
        dark_only = re.search(
            r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}\s*\}", self.source, re.DOTALL
        )
        assert dark_only is not None
        dark = set(re.findall(r"--([a-z-]+):", dark_only.group(1)))
        self.assertEqual(sorted(used - set(light)), [])
        # The dark theme sets every color, so none falls back to a light one.
        self.assertEqual(sorted(dark), sorted(light))

    def test_colors_meet_wcag_aa_contrast_in_both_themes(self) -> None:
        for theme, colors in self.themes.items():
            for pairs, minimum in ((TEXT_PAIRS, 4.5), (CONTROL_PAIRS, 3.0)):
                for foreground, background in pairs:
                    with self.subTest(theme=theme, foreground=foreground, background=background):
                        ratio = contrast(colors[foreground], colors[background])
                        self.assertGreaterEqual(ratio, minimum, f"{ratio:.2f}:1")

    def test_focus_stays_visible(self) -> None:
        self.assertRegex(self.source, r":focus-visible \{\s*outline: 3px solid var\(--accent\);")
        self.assertNotRegex(self.source, r"outline:\s*(none|0)\b")

    def test_motion_can_be_reduced(self) -> None:
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.source)

    def test_the_contrast_formula_matches_known_values(self) -> None:
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#ffffff", "#ffffff"), 1.0)
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), 4.54, places=2)


if __name__ == "__main__":
    unittest.main()
