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
    ("text", "background"),  # body text and fields
    ("text", "surface"),  # notices and buttons
    ("muted", "background"),  # help, paths, and the version
    ("muted", "surface"),
    ("accent-text", "accent"),  # the primary button
)
CONTROL_PAIRS = (
    ("border", "background"),  # the edges of fields and buttons
    ("accent", "background"),  # the focus outline and the primary button
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
        # The page moves focus to these headings at the end of a run, or when
        # the button that had focus stays disabled.
        for identifier in (
            "input-heading",
            "run-heading",
            "result-heading",
            "output-check-heading",
            "bundle-heading",
            "browser-heading",
        ):
            with self.subTest(heading=identifier):
                self.assertEqual(by_id(self.elements, identifier).get("tabindex"), "-1")


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
