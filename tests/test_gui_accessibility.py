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


# The dark colors, where the browser reports dark and the person chose no
# colors, and where the person chose Dark (stage G3a).
DARK_FOR_THE_BROWSER = r'@media \(prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{(.*?)\}\s*\}'
DARK_FOR_THE_CHOICE = r'^:root\[data-theme="dark"\] \{(.*?)^\}'


def declarations(block: str) -> dict[str, str]:
    """The colors and the color scheme that a block of styles.css sets."""
    return dict(re.findall(r"(--[a-z-]+|color-scheme):\s*([^;]+);", block))


def theme_colors() -> dict[str, dict[str, str]]:
    """Return the color variables of the light theme and the dark theme."""
    source = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
    light_block = re.search(r"^:root \{(.*?)^\}", source, re.MULTILINE | re.DOTALL)
    dark_block = re.search(DARK_FOR_THE_CHOICE, source, re.MULTILINE | re.DOTALL)
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

    def test_an_explanation_that_opens_is_spoken_by_a_hidden_live_region(self) -> None:
        # Stage C1: focus stays on the information button, so a hidden polite
        # region, which the page fills only when an explanation opens, says
        # its text once.
        announcer = by_id(self.elements, "info-announcer")
        self.assertEqual((announcer.get("role"), announcer.get("aria-live")), ("status", "polite"))
        self.assertIn("visually-hidden", str(announcer.get("class")).split())

    def test_the_result_heading_is_named_with_its_visible_words(self) -> None:
        # Stage C1: a screen reader that lists headings alone reads hidden
        # words before the visible headline, such as "Normalization result:
        # Waiting"; the visible words stay in the name (WCAG 2.5.3).
        heading = by_id(self.elements, "result-heading")
        children = [element for element in self.elements if element.parent is heading]
        self.assertEqual([child.tag for child in children], ["span", "span"])
        prefix, headline = children
        self.assertIn("visually-hidden", str(prefix.get("class")).split())
        self.assertEqual(prefix.get("data-i18n"), "run.result_prefix")
        self.assertEqual(headline.get("id"), "result-headline")
        for language in ("en", "ja"):
            with self.subTest(language=language):
                self.assertTrue(self.catalogs[language].get("run.result_prefix", "").strip())

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
            "help-report-heading",
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

    def test_the_remembered_settings_are_forgotten_after_a_question(self) -> None:
        # Stage B4c: the button in the bar says whether its question is open,
        # the question is hidden until it is asked, and its two buttons are
        # described by the question and what it forgets.
        button = by_id(self.elements, "forget-button")
        self.assertEqual(
            (button.tag, button.get("aria-expanded"), button.get("aria-controls")),
            ("button", "false", "forget-confirm"),
        )
        self.assertIn("hidden", by_id(self.elements, "forget-confirm").attributes)
        for identifier in ("forget-yes", "forget-no"):
            with self.subTest(button=identifier):
                answer = by_id(self.elements, identifier)
                self.assertEqual(
                    (answer.tag, answer.get("aria-describedby")),
                    ("button", "forget-question forget-text forget-text-also"),
                )
        # Stage G3a: what 2.1.0 also forgets comes after the words of 2.0.x.
        self.assertEqual(by_id(self.elements, "forget-text-also").get("data-i18n"), "forget.text_also")
        self.assertEqual(by_id(self.elements, "settings-status").get("role"), "status")
        # Looking again for a remembered store or folder that is not found.
        for identifier in ("store-search", "output-search"):
            with self.subTest(button=identifier):
                search = by_id(self.elements, identifier)
                self.assertEqual((search.tag, search.get("data-i18n")), ("button", "remembered.search_again"))
                self.assertIn("hidden", search.attributes)

    def test_the_colors_are_one_group_of_three_choices(self) -> None:
        # Stage G3a: in the bar, named by the words beside it, as the choice
        # of the fourth box is named by its heading.
        group = [element for element in self.elements if element.tag == "fieldset" and element.get("aria-labelledby") == "theme-label"]
        self.assertEqual(len(group), 1)
        self.assertEqual(by_id(self.elements, "theme-label").get("data-i18n"), "theme.label")
        labels = {element.get("for"): element for element in self.elements if element.tag == "label"}
        for identifier, value in (("theme-auto", "auto"), ("theme-light", "light"), ("theme-dark", "dark")):
            with self.subTest(choice=identifier):
                choice = by_id(self.elements, identifier)
                self.assertEqual(
                    (choice.tag, choice.get("type"), choice.get("name"), choice.get("value")),
                    ("input", "radio", "theme", value),
                )
                # Nothing works before the page has the connection.
                self.assertIn("disabled", choice.attributes)
                self.assertIn(identifier, labels)
        self.assertEqual(labels["theme-light"].get("data-i18n"), "theme.light")
        self.assertEqual(labels["theme-dark"].get("data-i18n"), "theme.dark")

    def test_quitting_asks_first_in_the_bar(self) -> None:
        # v2.0.1 F2: Quit asks first, in the bar, as forgetting the settings
        # does: the button says whether its question is open, the question is
        # hidden until it is asked, and its two buttons are described by the
        # question and what quitting does, which focus reads once; no live
        # region repeats it.
        button = by_id(self.elements, "quit-button")
        self.assertEqual(
            (button.tag, button.get("aria-expanded"), button.get("aria-controls")),
            ("button", "false", "quit-confirm"),
        )
        question = by_id(self.elements, "quit-confirm")
        self.assertIn("hidden", question.attributes)
        self.assertIsNone(question.get("role"))
        self.assertIsNone(question.get("aria-live"))
        for identifier, key in (("quit-yes", "quit.yes"), ("quit-no", "quit.no")):
            with self.subTest(button=identifier):
                answer = by_id(self.elements, identifier)
                self.assertEqual(
                    (answer.tag, answer.get("type"), answer.get("data-i18n"), answer.get("aria-describedby")),
                    ("button", "button", key, "quit-question quit-text"),
                )
        # The line under Normalize after a run is plain help text.
        again = by_id(self.elements, "run-again")
        self.assertEqual((again.tag, again.get("class")), ("p", "help"))

    def test_the_script_asks_before_it_quits_and_remembers_start_here(self) -> None:
        # v2.0.1 F2, in the page script, which no test runs: Quit opens its
        # question, whose answers quit or keep the app, Escape keeps it, focus
        # goes to the safe answer; the state of quitting and the switch of the
        # tips follow the rules of flow.mjs; and opening START_HERE.md marks
        # reading the result done in the help panel.
        script = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        for line in (
            'ui.quit.addEventListener("click", askQuit);',
            'ui.quitYes.addEventListener("click", quit);',
            'ui.quitNo.addEventListener("click", keepApp);',
            "ui.quitConfirm.hidden = !state.quitAsked;",
            "ui.quitYes.disabled = !enabled.quit;",
            "ui.hintsToggle.disabled = !enabled.hints;",
            "replaceLines(ui.runAgain, againNote(current, enabled).map(describe));",
            "quitting: state.quitting,",
            'stopped: state.connectionKey === "status.stopped",',
            "helpSteps(states, current.runState, state.output?.startHereOpened === true)",
        ):
            with self.subTest(line=line):
                self.assertIn(line, script)
        ask = re.search(r"function askQuit\(\) \{(.*?)\n\}", script, re.DOTALL)
        assert ask is not None
        self.assertIn("ui.quitNo.focus();", ask.group(1))
        self.assertRegex(
            script,
            r'ui\.quitConfirm\.addEventListener\("keydown", \(event\) => \{\s*if \(event\.key === "Escape"\) \{\s*keepApp\(\);',
        )
        stop = re.search(r"async function quit\(\) \{(.*?)\n\}", script, re.DOTALL)
        assert stop is not None
        self.assertIn('state.connectionKey = "status.quitting";', stop.group(1))
        self.assertIn("state.quitting = false;", stop.group(1).split("finally")[1])
        opened = re.search(r'if \(target === "start_here"\) \{\s*output\.startHereOpened = true;', script)
        self.assertIsNotNone(opened)

    def test_the_name_and_the_place_of_the_support_bundle_say_what_they_are(self) -> None:
        # Stage B5a: the name of the output is described by its red lines,
        # the button that chooses the folder of the Support Bundle by its
        # label, and the buttons that show the files where they are saved
        # are hidden until there is a file.
        name = by_id(self.elements, "output-name")
        self.assertEqual(name.get("aria-describedby"), "output-name-help output-name-note")
        self.assertEqual(by_id(self.elements, "output-name-note").get("role"), "status")
        choose = by_id(self.elements, "bundle-choose")
        self.assertEqual((choose.tag, choose.get("aria-labelledby")), ("button", "bundle-choose bundle-place-label"))
        self.assertEqual(by_id(self.elements, "bundle-place-label").get("data-i18n"), "bundle.place_label")
        # Each one is named with what it shows: the Support Bundle, or the
        # file that the run made, and says under it what showing it said.
        for identifier, named, result in (
            ("bundle-reveal", "bundle-heading", "bundle-reveal-result"),
            ("pack-reveal", "pack-made", "pack-result"),
        ):
            with self.subTest(button=identifier):
                reveal = by_id(self.elements, identifier)
                self.assertEqual((reveal.tag, reveal.get("data-i18n")), ("button", "reveal.button"))
                self.assertIn("hidden", reveal.attributes)
                self.assertEqual(reveal.get("aria-labelledby"), f"{identifier} {named}")
                self.assertEqual(by_id(self.elements, result).get("role"), "status")

    def test_the_output_of_the_fourth_box_and_the_change_say_what_they_are(self) -> None:
        # Stage B5b: the choice of the output of the check and the Support
        # Bundle is named by its heading, the list of earlier outputs by its
        # choice, and what the check said is read out; the column of the
        # change is hidden until there is one.
        group = next(element for element in self.elements if element.tag == "fieldset" and element.get("aria-labelledby") == "target-heading")
        self.assertIsNotNone(group)
        self.assertEqual(by_id(self.elements, "target-heading").get("data-i18n"), "target.heading")
        for identifier in ("target-run", "target-earlier"):
            with self.subTest(choice=identifier):
                choice = by_id(self.elements, identifier)
                self.assertEqual((choice.tag, choice.get("type"), choice.get("name")), ("input", "radio", "target"))
        self.assertEqual(by_id(self.elements, "target-list").get("aria-labelledby"), "target-earlier-label")
        self.assertEqual(by_id(self.elements, "target-check").get("data-i18n"), "target.check")
        self.assertEqual(by_id(self.elements, "target-check-result").get("role"), "status")
        self.assertIn("hidden", by_id(self.elements, "target-chosen").attributes)
        column = by_id(self.elements, "column-change")
        self.assertEqual((column.tag, column.get("scope"), column.get("data-i18n")), ("th", "col", "result.column_change"))
        self.assertIn("hidden", column.attributes)
        self.assertIn("hidden", by_id(self.elements, "family-total-change").attributes)
        # The choice of the output comes before the Support Bundle, which is
        # made for it.
        order = [element.get("id") for element in self.elements if element.get("id") in {"target-heading", "bundle-heading"}]
        self.assertEqual(order, ["target-heading", "bundle-heading"])

    def test_folded_help_says_whether_it_is_open(self) -> None:
        toggle = by_id(self.elements, "tools-toggle")
        self.assertEqual(toggle.get("aria-expanded"), "false")
        self.assertEqual(toggle.get("aria-controls"), "tools-body")
        self.assertIn("hidden", by_id(self.elements, "tools-body").attributes)

    def test_the_help_panel_is_a_closed_side_panel_with_five_parts(self) -> None:
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
        for name in ("steps", "faq", "words", "ai", "report"):
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

    def test_the_report_and_the_links_open_in_a_new_tab_only_when_pressed(self) -> None:
        # Stage B5c: every link of the page opens in a new tab, gives the
        # opened page neither this page nor where it came from, and has no
        # address in the page itself: the script gives it one, of the
        # repository's documents, the private channel, the page of Garmin, or
        # the report's form.
        source = (STATIC_ROOT / "flow.mjs").read_text(encoding="utf-8")
        block = re.search(r"export const OUTSIDE_DOCUMENTS = \[(.*?)\];", source, re.DOTALL)
        assert block is not None
        documents = set(re.findall(r'"([^"]+)"', block.group(1)))
        for document in documents:
            with self.subTest(document=document):
                self.assertTrue((ROOT / document).is_file())
        links = [element for element in self.elements if element.tag == "a"]
        self.assertEqual(len(links), 9)
        for link in links:
            with self.subTest(link=link.get("data-link") or link.get("id")):
                self.assertEqual(link.get("target"), "_blank")
                self.assertEqual(link.get("rel"), "noopener noreferrer")
                self.assertNotIn("href", link.attributes)
                self.assertIsNotNone(link.get("data-i18n"))
                if link.get("id") == "report-open":
                    self.assertIsNone(link.get("data-link"))
                else:
                    self.assertIn(link.get("data-link"), documents | {"garmin", "security"})
                if link.get("data-link-ja") is not None:
                    self.assertIn(link.get("data-link-ja"), documents)
        report = by_id(self.elements, "report-open")
        self.assertEqual(by_id(self.elements, str(report.get("aria-describedby"))).get("data-i18n"), "report.new_tab")
        values = by_id(self.elements, "report-values")
        table = values.parent
        assert table is not None
        self.assertEqual(table.tag, "table")
        self.assertEqual(
            [element.get("data-i18n") for element in self.elements if element.tag == "caption" and element.parent is table],
            ["report.table_caption"],
        )
        button = by_id(self.elements, "tools-report")
        self.assertEqual(button.tag, "button")
        self.assertEqual(by_id(self.elements, str(button.get("aria-describedby"))).get("data-i18n"), "tools.report_note")
        self.assertIn(by_id(self.elements, "tools-body"), button.ancestors())
        # The page of Garmin shows its address as its words, in each language.
        page = re.search(r'export const GARMIN_DATA_PAGE = "([^"]+)";', source)
        assert page is not None
        for language in LANGUAGES:
            with self.subTest(language=language):
                catalog = json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
                self.assertEqual(catalog["help.garmin_page"], page.group(1))

    def test_the_report_of_a_stop_comes_after_the_buttons_that_fix_it(self) -> None:
        # Stage B6a: in the first box after the buttons that choose one of the
        # Exports of a mixed input, and in the second after the check and the
        # button that remove the lock file, so that the report does not come
        # between what happened and how to fix it.
        order = [element.get("id") for element in self.elements if element.get("id")]
        for before, report in (("check-choices", "check-report"), ("lock-area", "store-report")):
            with self.subTest(report=report):
                self.assertEqual(order.index(report), order.index(before) + 1 + sum(
                    1 for element in self.elements
                    if element.get("id") and by_id(self.elements, before) in element.ancestors()
                ))
                self.assertEqual(by_id(self.elements, report).get("class"), "messages")
        self.assertLess(order.index("check-result"), order.index("check-choices"))
        self.assertLess(order.index("store-result"), order.index("lock-area"))
        # The page puts the line there through the rule of flow.mjs, which
        # the tests of the page's rules check.
        script = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        for result, report in (("checkResult", "checkReport"), ("storeResult", "storeReport")):
            with self.subTest(result=result):
                found = re.search(
                    rf"const (\w+) = apartReport\(.*\);\n\s+replaceLines\(ui\.{result}, \1\.lines\);\n\s+replaceLines\(ui\.{report}, \1\.report\);",
                    script,
                )
                self.assertIsNotNone(found)
                assert found is not None
                # Elsewhere the areas are only emptied.
                given = {area: set(re.findall(rf"replaceLines\(ui\.{area}, ([^)]*)\)", script)) for area in (result, report)}
                self.assertEqual(given[result] - {"[]"}, {f"{found.group(1)}.lines"})
                self.assertEqual(given[report] - {"[]"}, {f"{found.group(1)}.report"})
        note = by_id(self.elements, "store-same-note")
        self.assertEqual(note.get("data-i18n"), "store.same_note")
        self.assertIn("hidden", note.attributes)
        self.assertIn(by_id(self.elements, "store-list"), note.ancestors())

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
        self.assertEqual(sorted(used - set(light)), [])
        # The dark theme sets every color, so none falls back to a light one,
        # where the browser reports dark and where the person chose Dark
        # (stage G3a).
        for pattern in (DARK_FOR_THE_BROWSER, DARK_FOR_THE_CHOICE):
            with self.subTest(pattern=pattern):
                block = re.search(pattern, self.source, re.MULTILINE | re.DOTALL)
                assert block is not None
                self.assertEqual(sorted(re.findall(r"--([a-z-]+):", block.group(1))), sorted(light))

    def test_the_dark_colors_of_the_browser_and_of_the_choice_are_the_same(self) -> None:
        # Stage G3a: CSS cannot join a media query and an attribute in one
        # rule, so the dark colors are written twice. Light keeps the light
        # colors also where the browser reports dark, and without a choice
        # the page follows the browser.
        browser = re.search(DARK_FOR_THE_BROWSER, self.source, re.MULTILINE | re.DOTALL)
        choice = re.search(DARK_FOR_THE_CHOICE, self.source, re.MULTILINE | re.DOTALL)
        assert browser is not None and choice is not None
        self.assertEqual(declarations(browser.group(1)), declarations(choice.group(1)))
        self.assertEqual(declarations(choice.group(1))["color-scheme"], "dark")
        light = re.search(r'^:root\[data-theme="light"\] \{(.*?)^\}', self.source, re.MULTILINE | re.DOTALL)
        assert light is not None
        self.assertEqual(declarations(light.group(1)), {"color-scheme": "light"})
        root = re.search(r"^:root \{(.*?)^\}", self.source, re.MULTILINE | re.DOTALL)
        assert root is not None
        self.assertEqual(declarations(root.group(1))["color-scheme"], "light dark")

    def test_the_chosen_colors_show_without_color_and_with_the_keyboard(self) -> None:
        # Stage G3a: the chosen part is filled and bold, the part that has
        # the keyboard has the ring of the page, and where the system forces
        # its own colors, the radio buttons show.
        self.assertRegex(self.source, r"\.theme-choice input:checked \+ label \{[^}]*font-weight: 600;")
        self.assertRegex(
            self.source,
            r"\.theme-choice input:focus-visible \+ label \{\s*outline: 3px solid var\(--accent\);\s*outline-offset: 2px;",
        )
        forced = re.search(r"@media \(forced-colors: active\) \{\s*\.theme-choice input \{(.*?)\}\s*\}", self.source, re.DOTALL)
        assert forced is not None
        self.assertIn("opacity: 1;", forced.group(1))

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

    def test_the_bar_at_the_bottom_stays_on_the_screen(self) -> None:
        # v2.0.1 F2: Quit and the language can be reached without scrolling to
        # the end of the page; the help panel, fixed at the right, lies above
        # the bar.
        bar = re.search(r"\n\.statusbar \{(.*?)\}", self.source, re.DOTALL)
        assert bar is not None
        self.assertIn("position: sticky;", bar.group(1))
        self.assertIn("bottom: 0;", bar.group(1))
        layer = re.search(r"z-index: (\d+);", bar.group(1))
        panel = re.search(r"\n\.help-panel \{(.*?)\}", self.source, re.DOTALL)
        assert layer is not None and panel is not None
        panel_layer = re.search(r"z-index: (\d+);", panel.group(1))
        assert panel_layer is not None
        self.assertLess(int(layer.group(1)), int(panel_layer.group(1)))

    def test_motion_can_be_reduced(self) -> None:
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.source)

    def test_the_contrast_formula_matches_known_values(self) -> None:
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#ffffff", "#ffffff"), 1.0)
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), 4.54, places=2)


if __name__ == "__main__":
    unittest.main()
