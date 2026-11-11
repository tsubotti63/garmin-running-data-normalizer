"""Accessibility rules that can be checked without a browser.

The page's labels, button names, heading order, live regions, and colors are
read from the packaged files. Keyboard-only use and screen readers are checked
by hand before a release.
"""
from __future__ import annotations

import itertools
import json
import math
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
    ("text", "warn-soft"),  # the note of an output with part of its input left out (stage G3b)
    # The words of the years in the keys of a panel of comparing years, in
    # the colors of their lines (stage U3 of v2.2.0): all six, as words.
    ("year1-ink", "surface"),
    ("year2-ink", "surface"),
    ("year3-ink", "surface"),
    ("year4-ink", "surface"),
    ("year5-ink", "surface"),
    ("year6-ink", "surface"),
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
# The marks of the charts of the view page (stage G3b), always drawn on the
# surface: the two series, the hollow dots of 0, and the cross line, as
# graphical objects that carry meaning (3:1). The grid and the baseline are
# recessive, and the light bars of a period cut by the period are also said in
# words and in the table.
CHART_PAIRS = (
    ("d1", "surface"),
    ("d2", "surface"),
    ("zero", "surface"),
    ("cross", "surface"),
    # The six steps of the years compared (stage L1 of v2.2.0, the checker's
    # L0-1): each a line that carries meaning.
    ("y1", "surface"),
    ("y2", "surface"),
    ("y3", "surface"),
    ("y4", "surface"),
    ("y5", "surface"),
    ("y6", "surface"),
    # From stage L3, the lines of the years on one panel have colors of their
    # own; the calendar keeps the six steps above.
    ("year1", "surface"),
    ("year2", "surface"),
    ("year3", "surface"),
    ("year4", "surface"),
    ("year5", "surface"),
    ("year6", "surface"),
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


def page(name: str = "index.html") -> list[Element]:
    parser = _PageParser()
    parser.feed((STATIC_ROOT / name).read_text(encoding="utf-8"))
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
# The light colors, which are also those of the box that a picture of the
# view page is made in (stage R1 of v2.2.0), and Light chosen.
LIGHT_COLORS = r'^:root,\n\.save-stage\[data-theme="light"\] \{(.*?)^\}'
LIGHT_CHOSEN = r'^:root\[data-theme="light"\],\n\.save-stage\[data-theme="light"\] \{(.*?)^\}'


def declarations(block: str) -> dict[str, str]:
    """The colors and the color scheme that a block of styles.css sets."""
    return dict(re.findall(r"(--[a-z0-9-]+|color-scheme):\s*([^;]+);", block))


def theme_colors() -> dict[str, dict[str, str]]:
    """Return the color variables of the light theme and the dark theme."""
    source = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
    light_block = re.search(LIGHT_COLORS, source, re.MULTILINE | re.DOTALL)
    dark_block = re.search(DARK_FOR_THE_CHOICE, source, re.MULTILINE | re.DOTALL)
    if light_block is None or dark_block is None:
        raise AssertionError("styles.css has no light or dark color variables")

    def colors(block: str) -> dict[str, str]:
        return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6});", block))

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


# The colors of the years compared on one panel told apart (stage L3 of v2.2.0):
# in OKLab, under normal vision and under the three kinds of color blindness
# simulated with the matrices of Machado, Oliveira, and Fernandes (2009) at
# severity 1 in linear sRGB, clipped to 0 to 1.
COLOR_BLINDNESS = {
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def seen(color: str, kind: str = "normal") -> tuple[float, float, float]:
    def linear(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    rgb = [linear(int(color[index : index + 2], 16)) for index in (1, 3, 5)]
    if kind != "normal":
        rgb = [min(max(sum(weight * value for weight, value in zip(row, rgb)), 0.0), 1.0) for row in COLOR_BLINDNESS[kind]]
    red, green, blue = rgb
    cones = (
        0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue,
        0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue,
        0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue,
    )
    long_, middle, short = (max(value, 0.0) ** (1 / 3) for value in cones)
    return (
        0.2104542553 * long_ + 0.7936177850 * middle - 0.0040720468 * short,
        1.9779984951 * long_ - 2.4285922050 * middle + 0.4505937099 * short,
        0.0259040371 * long_ + 0.7827717662 * middle - 0.8086757660 * short,
    )


def apart(first: str, second: str, kind: str = "normal") -> float:
    return 100 * math.dist(seen(first, kind), seen(second, kind))


def faded(color: str, surface: str, opacity: float) -> str:
    # A color drawn at an opacity over the surface, as the browser blends it.
    mixed = (round(opacity * int(color[index : index + 2], 16) + (1 - opacity) * int(surface[index : index + 2], 16)) for index in (1, 3, 5))
    return "#" + "".join(f"{value:02x}" for value in mixed)


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
        # From stage X1 of v2.3.0, Escape keeps the app wherever the focus is
        # (test_escape_closes_a_question_wherever_the_focus_is).
        self.assertIn("    quit: { region: ui.quitConfirm, keep: keepApp },", script)
        stop = re.search(r"async function quit\(\) \{(.*?)\n\}", script, re.DOTALL)
        assert stop is not None
        self.assertIn('state.connectionKey = "status.quitting";', stop.group(1))
        self.assertIn("state.quitting = false;", stop.group(1).split("finally")[1])
        # v2.2.0 K2: before the server stops, the view page is asked to write
        # what waits to be remembered, and the page waits for it (flow.mjs,
        # which the node tests check).
        self.assertIn('await quitAfterWriting(() => askFlush(quitChannel), () => callApi("/api/shutdown"));', stop.group(1))
        self.assertNotIn('await callApi("/api/shutdown");', stop.group(1))
        opened = re.search(r'if \(target === "start_here"\) \{\s*output\.startHereOpened = true;', script)
        self.assertIsNotNone(opened)

    def test_escape_closes_a_question_wherever_the_focus_is(self) -> None:
        # Stage X1 of v2.3.0 (the person's finding in W6d, and the checker's
        # review of the plan of X1, A1 and A2), in the page scripts, which no
        # test runs: while a question shows, Escape closes it wherever the
        # focus is, as its safe answer does, in one handler of the document
        # that asks flow.mjs which one (the node tests check questionToClose);
        # the questions have no handlers of their own any more, which would
        # take one Escape twice; the parts of the page that close by Escape
        # take it first, so that it closes no question as well; and on the
        # view page a drag is cancelled first, and graphs only, which hide the
        # bar, are left after the question.
        script = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        for name, question in (("askQuit", "quit"), ("askForget", "forget"), ("askCancel", "cancel")):
            with self.subTest(asks=name):
                body = re.search(r"function " + name + r"\(\) \{(.*?)\n\}", script, re.DOTALL)
                assert body is not None
                self.assertIn(f'  questionsAsked = askedLast(questionsAsked, "{question}");\n', body.group(1))
        handler = re.search(
            r"  const questions = \{\n(.*?)\n  \};\n  document\.addEventListener\(\"keydown\", \(event\) => \{\n(.*?)\n  \}\);\n\}\n",
            script,
            re.DOTALL,
        )
        assert handler is not None
        self.assertEqual(
            handler.group(1),
            "    quit: { region: ui.quitConfirm, keep: keepApp },\n"
            "    forget: { region: ui.forgetConfirm, keep: keepSettings },\n"
            "    cancel: { region: ui.cancelConfirm, keep: keepRunning },",
        )
        self.assertEqual(
            handler.group(2),
            "    const open = questionsAsked.filter((name) => !questions[name].region.hidden);\n"
            "    const focused = open.find((name) => questions[name].region.contains(document.activeElement)) ?? null;\n"
            "    const name = questionToClose(event, open, focused);\n"
            "    if (name !== null) {\n"
            "      event.preventDefault();\n"
            "      questions[name].keep();\n"
            "    }",
        )
        for region in ("quitConfirm", "forgetConfirm", "cancelConfirm"):
            with self.subTest(gone=region):
                self.assertNotIn(f'ui.{region}.addEventListener("keydown"', script)
        for taken in (
            'ui.browser.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {\n      event.preventDefault();\n      closeBrowser();\n',
            'ui.helpPanel.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {\n      event.preventDefault();\n      closeHelp();\n',
            '      element.addEventListener("keydown", (event) => {\n        if (event.key === "Escape" && state.infos.has(name)) {\n          event.preventDefault();\n          closeInfo(name);\n',
        ):
            with self.subTest(taken=taken[:30]):
                self.assertEqual(script.count(taken), 1)
        # Every Escape of the page is one of these: no part closes by Escape
        # without taking it.
        escapes = re.findall(r'if \(event\.key === "Escape"[^\n]*\) \{\n *([^\n]*)', script)
        self.assertEqual(escapes, ["event.preventDefault();"] * 3)
        view = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.assertNotIn('ui.quitConfirm.addEventListener("keydown"', view)
        order = re.search(
            r'  document\.addEventListener\("keydown", \(event\) => \{\n    if \(event\.key !== "Escape" \|\| event\.defaultPrevented\) \{\n      return;\n    \}\n(.*?)\n  \}\);\n',
            view,
            re.DOTALL,
        )
        assert order is not None
        self.assertEqual(
            order.group(1),
            "    if (drag !== null) {\n"
            "      event.preventDefault();\n"
            "      cancelDrag();\n"
            "      return;\n"
            "    }\n"
            "    // Graphs only hide the bar, and with it a question left open.\n"
            '    const open = ui.quitConfirm.hidden || state.full ? [] : ["quit"];\n'
            '    const focused = ui.quitConfirm.contains(document.activeElement) ? "quit" : null;\n'
            "    if (questionToClose(event, open, focused) !== null) {\n"
            "      event.preventDefault();\n"
            "      keepApp();\n"
            "    } else if (state.full) {\n"
            "      leaveFull();\n"
            "    }",
        )
        # Every part of the view page that closes by Escape takes it, as the
        # help panel does (Codex's review of the diff: the windows of the
        # activity types and of the items to add did not, so that one Escape
        # closed the question of quitting as well); the list of a panel takes
        # it at the end of plotKey.
        self.assertIn('ui.helpPanel.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {\n      event.preventDefault();\n      closeHelp();\n', view)
        for window in ("typesPop", "picker"):
            with self.subTest(window=window):
                self.assertIn(f'ui.{window}.addEventListener("keydown", (event) => {{\n    if (event.key === "Escape") {{\n      event.preventDefault();\n', view)
        taken = re.findall(r'if \(event\.key === "Escape"[^\n]*\) \{\n(?: *//[^\n]*\n)* *([^\n]*)', view)
        self.assertEqual(taken.count("closeList(true);"), 1)
        self.assertEqual(set(taken), {"event.preventDefault();", "closeList(true);"})
        self.assertGreaterEqual(len(taken), 15)
        plot_key = re.search(r"\nfunction plotKey\(event\) \{\n(.*?)\n\}\n", view, re.DOTALL)
        assert plot_key is not None
        self.assertTrue(plot_key.group(1).endswith("  } else {\n    return false;\n  }\n  event.preventDefault();\n  return true;"))

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


class GuiViewPageStructureTest(unittest.TestCase):
    """The view page (stage G3b), with the rules of the normalization page.
    Its panels, which the script draws, are checked in the script."""

    def setUp(self) -> None:
        self.elements = page("view.html")
        self.catalogs = {
            language: json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            for language in LANGUAGES
        }
        self.script = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")

    def named(self, key: str | None) -> bool:
        return all(self.catalogs[language].get(str(key), "").strip() for language in LANGUAGES)

    def test_every_field_has_a_label(self) -> None:
        labelled = {element.get("for") for element in self.elements if element.tag == "label"}
        fields = [element for element in self.elements if element.tag in {"input", "select", "textarea"}]
        # From v2.2.0 L1, the item, the month, and the line of a comparison;
        # from M1, whether the marks show, and the date, the last day, the
        # kind, and the name of a mark; from M2, the weeks before a race day;
        # from O1, the two items plotted against each other; from P1, the
        # item of a distribution; from R1, the panels of a picture (all, or one
        # and which), its colors (two), and its marks; from T1, the words of the
        # name of the conditions, and their distance and duration, from and to;
        # from v2.3.0 X5, the format of a picture (two) and the size of a PNG
        # (three).
        self.assertEqual(len(fields), 39)
        for field in fields:
            with self.subTest(field=field.get("id")):
                self.assertTrue(field.get("id") in labelled or field.get("aria-label") or field.get("aria-labelledby"))

    def test_the_window_of_the_conditions_and_its_line(self) -> None:
        # Stage T1 of v2.2.0: a button in the heading row of the activity
        # types opens a window of the conditions under it; the line under the
        # filters says them in every view.
        head = by_id(self.elements, "conditions-button").parent
        self.assertEqual(head.get("class"), "filter-head")
        self.assertIs(by_id(self.elements, "types-label").parent, head)
        button = by_id(self.elements, "conditions-button")
        self.assertEqual((button.get("aria-expanded"), button.get("aria-controls")), ("false", "conditions-pop"))
        self.assertIn("disabled", button.attributes)
        window = by_id(self.elements, "conditions-pop")
        self.assertEqual((window.get("role"), window.get("aria-labelledby")), ("dialog", "conditions-title"))
        self.assertIn("hidden", window.attributes)
        problem = by_id(self.elements, "conditions-problem")
        self.assertEqual(problem.get("aria-live"), "polite")
        for name in ("conditions-name", "conditions-distance-from", "conditions-distance-to", "conditions-time-from", "conditions-time-to"):
            with self.subTest(box=name):
                box = by_id(self.elements, name)
                self.assertIn(window, box.ancestors())
                self.assertEqual(box.get("type"), "text")
                self.assertIn("conditions-problem", str(box.get("aria-describedby")).split())
        self.assertIn("hidden", by_id(self.elements, "conditions-line").attributes)
        self.assertEqual(by_id(self.elements, "conditions-line-clear").get("data-i18n"), "view.conditions.clear")
        held = {
            # The focus goes to the first box that can be used, and back to
            # the button; one window under the types at a time.
            "openConditions": (
                "fillConditionBoxes(state.conditions);",
                "state.typesOpen = false;",
                "(namesReadable() ? ui.conditionsName : ui.conditionsDistanceFrom).focus();",
                "ui.conditionsButton.focus();",
            ),
            # The same conditions ask nothing again; others are remembered
            # and asked in every view.
            "setConditions": (
                "if (conditionsKey(conditions) === conditionsKey(state.conditions)) {",
                "rememberItems(true);",
                "requestShown();",
                "requestCompare();",
            ),
            # A name that cannot be used, as the names were not read, stays.
            "applyConditions": (
                'name: ui.conditionsName.disabled ? (state.conditions?.name ?? "") : ui.conditionsName.value,',
                "state.conditionsProblem = problem;",
            ),
            # The window stays inside the window of the browser (the real
            # page in English at 1366x650).
            "fitConditionsWindow": (
                'pop.style.right = "";',
                "if (box.left < FILTER_POP_MARGIN) {",
                "pop.style.right = `${Math.floor(box.left - FILTER_POP_MARGIN)}px`;",
                "pop.style.maxHeight = `${Math.max(0, Math.floor(window.innerHeight - box.top - FILTER_POP_MARGIN))}px`;",
            ),
            # And that of the types, at the right edge (before T1 too).
            "fitTypesWindow": (
                'pop.style.left = "";',
                "const over = box.right - (window.innerWidth - FILTER_POP_MARGIN);",
                "  if (over > 0) {",
                "pop.style.left = `${-Math.ceil(Math.min(over, box.left - FILTER_POP_MARGIN))}px`;",
            ),
            "renderConditions": (
                'ui.conditionsButton.setAttribute("aria-expanded", String(viewing && state.conditionsOpen));',
                "ui.conditionsPop.hidden = !viewing || !state.conditionsOpen;\n  fitConditionsWindow();",
                "ui.conditionsName.disabled = !readable;",
                "ui.conditionsNamesWhy.hidden = readable;",
                # The counts of an answer of other conditions are never put to
                # these.
                "const current = counts !== null && conditionsKey(counts.asked ?? null) === conditionsKey(state.conditions);",
                'element("bdi", "", conditionsText(state.conditions))',
            ),
        }
        for name, lines in held.items():
            found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, found.group(1))
        for line in (
            # Esc closes; Enter applies, never while an IME composes.
            '  ui.conditionsPop.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {\n      event.preventDefault();\n      openConditions(false);\n    } else if (event.key === "Enter" && !event.isComposing && event.target instanceof HTMLInputElement) {\n      event.preventDefault();\n      applyConditions();\n    }\n  });',
            "  for (const box of [ui.conditionsName, ui.conditionsDistanceFrom, ui.conditionsDistanceTo, ui.conditionsTimeFrom, ui.conditionsTimeTo]) {\n    box.addEventListener(\"change\", applyConditions);\n  }",
            # The line hides with its button; the focus goes to the button
            # of the conditions (the checker's review of the diff of T1).
            '  ui.conditionsLineClear.addEventListener("click", () => {\n    clearConditions();\n    ui.conditionsButton.focus();\n  });',
            "    state.typesOpen = !state.typesOpen;\n    state.conditionsOpen = false;",
            'window.addEventListener("resize", fitConditionsWindow);',
            'window.addEventListener("resize", fitTypesWindow);',
            "  if (!ui.typesPop.hidden) {\n    renderTypes(types);\n  }\n  fitTypesWindow();",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # The window of the conditions closes where that of the types does:
        # another output, another view, and the full screen (the checker's
        # review of the diff of T1).
        for name in ("openOutput", "enterCompare", "enterPlot", "enterSpread", "enterShoes", "enterFull"):
            body = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert body is not None, name
            with self.subTest(function=name):
                # An opening by itself keeps them (stage W1 of v2.2.1).
                closed = "  if (auto === null) {\n    state.typesOpen = false;\n    state.conditionsOpen = false;" if name == "openOutput" else "  state.typesOpen = false;\n  state.conditionsOpen = false;"
                self.assertIn(closed, body.group(1))
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        rule = re.search(r"\n\.conditions-pop \{(.*?)\n\}", style, re.DOTALL)
        assert rule is not None
        self.assertIn("overflow-y: auto;", rule.group(1))
        # A name box that cannot be used is grey on the white of the window.
        disabled = re.search(r"\n\.conditions-pop \.conditions-text:disabled \{(.*?)\n\}", style, re.DOTALL)
        assert disabled is not None
        self.assertIn("background: var(--none-soft);", disabled.group(1))

    def test_the_names_of_the_list_are_isolated_and_wrap(self) -> None:
        # Stage T1 of v2.2.0: the column of the names where the answer of the
        # list read them; each name in <bdi>, so that characters of direction
        # in a name of the output never turn the text around it (Codex 19 of
        # the plan of T1); a long name wraps in its column (Codex 10).
        found = re.search(r"function buildListTable\(.*?\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert found is not None
        for line in (
            'const columns = listColumns(list.key, list.answer?.names === "read");',
            ': column === "name"\n              ? typeof row.name === "string" && row.name !== "" ? row.name : null',
            'column === "name" ? "list-name" : "n"',
            '      } else if (column === "name") {\n        // A name of the output may change the direction of the text around\n        // it (Codex\'s review of the plan of T1).\n        cell.append(element("bdi", "", text));',
        ):
            with self.subTest(line=line):
                self.assertIn(line, found.group(1))
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        rule = re.search(r"\n\.list-table \.t td\.list-name \{(.*?)\n\}", style, re.DOTALL)
        assert rule is not None
        for declaration in ("max-width: 16em;", "overflow-wrap: anywhere;", "white-space: normal;", "text-align: left;"):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, rule.group(1))

    def test_the_notes_of_a_panel_open_in_place_and_cover_nothing(self) -> None:
        # Stage X12d3 of v2.3.0, the person's choice B of the samples: the
        # notes of a panel ("About this panel (n)") open in place, under the
        # row of numbers and above the chart, and their button, which stays
        # where it is, closes them again. As a window over the chart (until
        # 2.3.0rc2) they covered their own button and the end of the row, and
        # could not be closed in Safari, where a pressed button does not take
        # the focus.
        from tests.test_gui_view_save import function_body

        build = function_body(self.script, "buildPanel")
        for line in (
            '      notesBox = element("div", "panel-notes");\n      notesBox.id = notesId;\n      notesBox.hidden = state.notesOpen !== key;\n      notesBox.dataset.key = key;',
            '      notesBox.append(element("p", "panel-notes-title", t("view.panel.about", { name })));',
            '      button.setAttribute("aria-controls", notesId);',
            '    section.append(summary);\n    if (notesBox !== null) {\n      section.append(notesBox);\n    }\n  }\n  let body;',
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, build)
        # The row of numbers, then the notes, then the chart; nothing after it.
        self.assertLess(build.index("section.append(summary);"), build.index("section.append(notesBox);"))
        self.assertLess(build.index("section.append(notesBox);"), build.index("section.append(body);"))
        self.assertEqual(build.count("section.append(notesBox);"), 1)
        toggle = function_body(self.script, "toggleNotes")
        self.assertIn('for (const box of ui.panels.querySelectorAll(".panel-notes")) {\n    box.hidden = box.dataset.key !== state.notesOpen;', toggle)
        # The chart of the panel gets lower or higher: the charts are drawn
        # again at the next frame.
        self.assertEqual(toggle.count("\n  scheduleRedraw();"), 1)
        # Escape in the panels closes them, also where the focus stayed on a
        # chart (Safari keeps it there after the press at their button): the
        # keys that the chart does not take go on to the notes.
        self.assertIn(
            '  ui.panels.addEventListener("keydown", (event) => {\n'
            '    // The keys of a chart first. An Escape that its chart leaves (no list of\n'
            '    // its own open) closes the notes, also where the focus stayed on a chart\n'
            '    // after the press at their button, as Safari keeps it there (Codex\'s\n'
            '    // read of the diff of stage X12d3 of v2.3.0).\n'
            '    if (event.target.classList?.contains("plot") && plotKey(event)) {\n'
            '      return;\n'
            '    }\n'
            '    if (event.key === "Escape" && listBox?.contains(event.target)) {\n',
            self.script,
        )
        self.assertIn('    } else if (event.key === "Escape" && state.notesOpen !== null) {\n      event.preventDefault();\n      const key = state.notesOpen;\n      toggleNotes(key, false);\n', self.script)
        # An SVG copies the charts of the page: it copies them as they are with
        # the notes closed (the QA audit's findings 11, G1); a PNG draws its
        # charts again from the answers, and the notes do not change it.
        self.assertIn('      const made = state.saveFormat === "png" ? savePng(stage, target) : withNotesClosed(() => saveSvg(stage, target));\n', self.script)
        closed = function_body(self.script, "withNotesClosed")
        # The box is shown again whatever fails, the first redraw too; the
        # panels are put back where they were, read before the box is hidden
        # (stage X12d4 of v2.3.0: WebKit kept them at the bottom that the
        # hidden notes left).
        self.assertIn("  if (box === null || box.hidden) {\n    return copy();\n  }\n", closed)
        self.assertIn(
            "  const top = ui.panels.scrollTop;\n  box.hidden = true;\n  try {\n    renderCharts();\n    return copy();\n"
            "  } finally {\n    box.hidden = false;\n    renderCharts();\n    ui.panels.scrollTop = top;\n  }",
            closed,
        )
        self.assertIn('ui.panels.querySelector(`.panel-notes[data-key="${state.notesOpen}"]`)', closed)
        # Not a window: no class of a window, no place over the chart.
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        for source in (self.script, style):
            self.assertNotIn("notes-pop", source)
        rule = re.search(r"\n\.panel-notes \{(.*?)\n\}", style, re.DOTALL)
        self.assertIsNotNone(rule)
        for word in ("position", "top:", "right:", "bottom:", "z-index"):
            with self.subTest(word=word):
                self.assertNotIn(word, rule.group(1))
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        self.assertIn(
            "and notes of what is left out, which open in place under that line and above the chart and cover nothing "
            "(stage X12d3 of v2.3.0, the person's choice B: as a window over the chart they covered their own button "
            "and could not be closed in Safari; a picture saved while they are open is as with them closed; since "
            "stage X12d4 of v2.3.0, where they open below what the panels show, the panels scroll to show as much of "
            "them as fits with their button still in view, and scroll back when they close unless they moved "
            "meanwhile, scrolled by the person or laid out again),",
            design,
        )

    def test_the_reading_of_a_panel_is_as_wide_as_its_widest(self) -> None:
        # Stage X12d4 of v2.3.0 (the QA audit's findings 15): a reading too
        # wide for the line of the name in some periods went to a line of its
        # own in those only, so that the heading got higher or lower as the
        # cross line moved (VO2 Max at 1415x970 too), the panels moved under
        # the pointer, and the first press at a chart could miss it. The
        # reading is as wide as its widest over the periods shown, of its
        # first line and of the number left out on its second, measured out of
        # the layout before the readings are written: every period, each digit
        # as the widest digit of its size, each shape once (Codex's fourth
        # read of the diff: the longest in characters is not always the
        # widest, the number left out can be wider than the first line, and
        # the grounds of each period look through the counts of all), the
        # letters not kerned (its fifth read).
        from tests.test_gui_view_save import function_body

        fit = function_body(self.script, "fitReadings")
        for line in (
            '    if (!entry.read?.classList.contains("two-lines")) {\n      continue;\n    }',
            '    entry.read.style.minWidth = "";',
            '    const probe = element("span", "read-probe");\n    entry.read.append(probe);\n    const digits = widestDigits(probe);',
            "    answer.periods.forEach((_, index) => {\n"
            "      const words = shapeWords(readingWords(readingLine(entry.item, entry.panel, answer.periods, index, answer.grain, state.language)), digits);\n"
            "      shapes.set(JSON.stringify(words), words);\n    });",
            "    for (const lead of groundsLeads(entry.item, entry.panel, answer.periods, state.language)) {\n"
            "      if (lead !== null) {\n        leads.add(describe(lead).replace(DIGIT, digits.lead));\n      }\n    }",
            "    for (const words of shapes.values()) {\n"
            '      const line = element("span", "read-line");\n'
            "      line.append(...readingNodes(entry, words));\n      probe.append(line);\n      measured.push(line);\n    }",
            "    for (const lead of leads) {\n"
            '      const line = element("span", "read-grounds");\n'
            '      const part = element("span", "read-grounds-lead", lead);\n'
            "      line.append(part);\n      probe.append(line);\n      measured.push(part);\n    }",
            "    const widest = measured.reduce((most, node) => Math.max(most, node.getBoundingClientRect().width), 0);\n    probe.remove();",
            "    if (widest > 0) {\n      entry.read.style.minWidth = `${Math.ceil(widest) + READING_SLACK}px`;\n    }",
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, fit)
        self.assertIn("\nconst DIGIT = /[0-9]/gu;\nconst READING_SLACK = 1;\n", self.script)
        self.assertNotIn("readout(", fit)
        # The widest digit of each size: of the period and the counts, of the
        # values, and of the number left out, in the elements that show them.
        digits = function_body(self.script, "widestDigits")
        for line in (
            '  const rows = [..."0123456789"].map((digit) => {',
            '    const words = element("span", "read-line", digit);',
            '    const valueLine = element("span", "read-line");\n    const value = element("strong", "", digit);\n    valueLine.append(value);',
            '    const leadLine = element("span", "read-grounds");\n    const lead = element("span", "read-grounds-lead", digit);\n    leadLine.append(lead);',
            "    probe.append(words, valueLine, leadLine);",
            "      const width = row[part].getBoundingClientRect().width;\n"
            "      if (width > found.width) {\n        found = { digit: row.digit, width };\n      }",
            '  const digits = { words: widest("words"), value: widest("value"), lead: widest("lead") };\n  probe.replaceChildren();\n  return digits;',
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, digits)
        shape = function_body(self.script, "shapeWords")
        for line in (
            "    period: words.period.replace(DIGIT, digits.words),",
            "      value: value.value.replace(DIGIT, digits.value),",
            "      count: value.count === null ? null : value.count.replace(DIGIT, digits.words),",
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, shape)
        # Fitted before the readings are written, each time the panels are
        # built again (the answer, the language, the marks).
        build = function_body(self.script, "renderPanels")
        self.assertIn("  fitReadings(answer);\n  moveCross(state.cursor ?? periods.length - 1, false);", build)
        for name, count in (("fitReadings(", 2), ("widestDigits(", 2), ("shapeWords(", 2), ("readingWords(", 3), ("readingNodes(", 3)):
            with self.subTest(name=name):
                self.assertEqual(self.script.count(name), count)
        # The reading written at the cross line and the ones measured are made
        # by the same functions.
        self.assertIn("      nodes.push(...readingNodes(entry, readingWords(reading)));", function_body(self.script, "moveCross"))
        words = function_body(self.script, "readingWords")
        for line in (
            "    period: describe(reading.period),",
            "    values: reading.values.map((value) => ({ line: value.line, value: describe(value.value), count: value.count === null ? null : describe(value.count) })),",
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, words)
        nodes = function_body(self.script, "readingNodes")
        for line in (
            "  const nodes = [words.period];",
            "        nodes.push(lineSwatch(entry.styles[value.line], showsPoints(entry.panel)));",
            '      nodes.push(element("strong", "", value.value));',
            "        nodes.push(value.count);",
            '    nodes.push(element("span", "no-value", t("view.no_value")));',
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, nodes)
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        # Clipped to nothing, so that the lines measured never widen what the
        # box of the panels scrolls (Codex's fifth read of the diff).
        rule = re.search(r"\n\.read-probe \{(.*?)\n\}", style, re.DOTALL)
        assert rule is not None
        for declaration in (
            "position: absolute;",
            "display: flex;",
            "flex-direction: column;",
            "align-items: flex-start;",
            "width: 0;",
            "height: 0;",
            "overflow: hidden;",
            "visibility: hidden;",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, rule.group(1))
        # The letters of a reading are not kerned, so that a shape with each
        # digit as the widest is never narrower than a reading it stands for.
        rule = re.search(r"\n\.panel-read\.two-lines \{(.*?)\n\}", style, re.DOTALL)
        assert rule is not None
        self.assertIn("font-kerning: none;", rule.group(1))
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        self.assertIn(
            "From stage X12d4 of v2.3.0 the reading is as wide as its widest reading over the periods shown (its first "
            "line and the number left out on its second, each digit as the widest, its letters not kerned), so that it "
            "stands beside the name only where even that one fits, and on a line of its own otherwise",
            design,
        )

    def test_notes_that_open_below_the_panels_come_into_view(self) -> None:
        # Stage X12d4 of v2.3.0, the QA audit's findings 12, J1: pressed as a
        # person presses it, where it shows, the button of notes low in the
        # box of the panels opened them mostly below it in a small window, and
        # the person saw little of them. The panels scroll down by as much as
        # shows them whole, never so far that their button leaves the top,
        # where a second press closes them. Closing them scrolls the panels
        # back where they were, unless the person scrolled them meanwhile: left
        # at their bottom, the panels moved under the pointer as soon as the
        # cross line shortened a panel, and the first press at a chart missed.
        from tests.test_gui_view_save import function_body

        toggle = function_body(self.script, "toggleNotes")
        # Where the panels were is read before a box is hidden.
        self.assertIn("  const before = state.notesOpen;\n  const at = ui.panels.scrollTop;\n  state.notesOpen = open ? key : null;\n", toggle)
        self.assertIn("  if (open) {\n    showNotes(key, before, at);\n  } else {\n    unscrollNotes(key, at);\n  }\n  scheduleRedraw();", toggle)
        show = function_body(self.script, "showNotes")
        for line in (
            '  const notes = ui.panels.querySelector(`.panel-notes[data-key="${key}"]`);',
            '  const button = ui.panels.querySelector(`button[data-action="notes"][data-key="${key}"]`);',
            "  if (notes === null || button === null) {\n    return;\n  }",
            "  const box = ui.panels.getBoundingClientRect();",
            "  const below = notes.getBoundingClientRect().bottom + NOTES_MARGIN - box.bottom;",
            "  const room = button.getBoundingClientRect().top - NOTES_MARGIN - box.top;",
            "  const down = Math.min(below, room);",
            "  if (down > 0) {\n    ui.panels.scrollTop += down;\n  }",
            "  const kept = notesScroll !== null && notesScroll.key === before && Math.abs(at - notesScroll.to) <= 1;",
            "  const from = kept ? notesScroll.from : at;",
            "  notesScroll = { key, from, to: ui.panels.scrollTop };",
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, show)
        back = function_body(self.script, "unscrollNotes")
        self.assertIn(
            "  if (notesScroll !== null && notesScroll.key === key && Math.abs(at - notesScroll.to) <= 1) {\n"
            "    ui.panels.scrollTop = notesScroll.from;\n  }\n  notesScroll = null;",
            back,
        )
        self.assertIn("\nlet notesScroll = null;\n", self.script)
        # Only the box of the panels scrolls: scrollIntoView would move the
        # page too, and would not keep the button in view.
        self.assertNotIn("scrollIntoView", show)
        self.assertIn("\nconst NOTES_MARGIN = 8;\n", self.script)
        # Each defined once and called once, where the notes open or close.
        self.assertEqual(self.script.count("showNotes("), 2)
        self.assertEqual(self.script.count("unscrollNotes("), 2)

    def test_a_panel_is_never_lower_than_what_it_holds(self) -> None:
        # Stage X12d3 of v2.3.0: with a least height of 150 pixels, the
        # heading, the reading of two lines and the row of numbers of a narrow
        # window left the chart less than its own least height, and it ran
        # over the next panel (900 by 1000 pixels). A panel is at least 150
        # pixels and never lower than what it holds; the panels scroll.
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        rule = re.search(r"\n\.panel-view \{(.*?)\n\}", style, re.DOTALL)
        self.assertIsNotNone(rule)
        self.assertIn("flex: 1 0 150px;", rule.group(1))
        self.assertIn("min-height: auto;", rule.group(1))
        self.assertNotRegex(rule.group(1), r"min-height: \d")
        panels = re.search(r"\n\.panels \{(.*?)\n\}", style, re.DOTALL)
        self.assertIn("overflow-y: auto;", panels.group(1))
        chart = re.search(r"\n\.panel-chart \{(.*?)\n\}", style, re.DOTALL)
        self.assertIn("min-height: 40px;", chart.group(1))
        # The low strip and the table: at least 76 and 240 pixels, and never
        # lower than what they hold either (in a narrow window the heading of a
        # strip takes two or three lines, and the notes left a table no room).
        for selector, basis in ((r"\.panel-view\.mini", "flex: 0 0 76px;"), (r"\.panel-view\.table", "flex: 1 0 240px;")):
            with self.subTest(selector=selector):
                variant = re.search(r"\n" + selector + r" \{(.*?)\n\}", style, re.DOTALL)
                self.assertIn(basis, variant.group(1))
                self.assertIn("min-height: auto;", variant.group(1))
                self.assertNotRegex(variant.group(1), r"min-height: \d")
        # The table of a panel keeps its heads and two rows or so, and what it
        # holds is not counted where its panel measures what it holds (or the
        # panel would take the height of the whole table).
        wrap = re.search(r"\n\.panel-view\.table:not\(\.compare-table\) > \.panel-table \{(.*?)\n\}", style, re.DOTALL)
        self.assertIsNotNone(wrap)
        self.assertIn("contain: size;", wrap.group(1))
        self.assertIn("min-height: 7rem;", wrap.group(1))
        # The one panel of the views of the points and of the spread, whose
        # chart is drawn in its flow, keeps its least height of 150 pixels.
        plot_view = re.search(r"\n\.plot-body \.plot-view \{(.*?)\n\}", style, re.DOTALL)
        self.assertIn("min-height: 150px;", plot_view.group(1))
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        self.assertIn(
            "Panels of at least 150 pixels, and never lower than what they hold (stage X12d3 of v2.3.0: in a narrow "
            "window a chart ran over the heading of the next panel), stand on one time axis; when they do not fit, only "
            "the panels scroll.",
            design,
        )
        self.assertIn(
            "and can be shown as a table (newest first, 400 rows at a time; the table keeps its heads and two rows or "
            "so, and its panel grows for them), enlarged, moved, or removed; one panel enlarged makes the others low "
            "strips on the same axis, which are never lower than what they hold either.",
            design,
        )

    def test_the_reading_holds_the_grounds_of_its_period_on_a_second_line(self) -> None:
        # Stage X6 of v2.3.0, the person's choice (a): the reading of a panel
        # always holds two lines, the reading (or an empty line while no
        # period is chosen) and the grounds of its period (or an empty line),
        # so that the heading keeps its height as the pointer moves; the
        # number left out first and kept whole, the reasons cut at their end,
        # the whole on the pointer. The reading stays hidden from a screen
        # reader, which hears the grounds whole and in parentheses after the
        # values of the panel.
        from tests.test_gui_view_save import function_body

        self.assertIn('  const read = element("span", "panel-read two-lines");\n  read.setAttribute("aria-hidden", "true");\n  read.append(element("span", "read-line", "\\u00a0"), groundsLine(null));\n  head.append(read);', self.script)
        self.assertEqual(self.script.count('"panel-read two-lines"'), 1)
        # A low strip shows neither the summary nor the notes of a panel, so
        # its reading keeps one line too (view.css below).
        build = function_body(self.script, "buildPanel")
        self.assertIn('  let notesBox = null;\n  if (mode !== "mini") {\n    const summary = element("div", "panel-summary");', build)
        cross = function_body(self.script, "moveCross")
        for line in (
            'const grounds = reading.grounds === null ? "" : t("view.spoken_grounds", { grounds: describe(reading.grounds.full).replace(/[。.]$/u, "") });',
            'value: (reading.values.length ? reading.values.map(spokenValue).join(t("view.spoken_separator")) : t("view.no_value")) + grounds,',
            '    const first = element("span", "read-line");\n    first.append(...(nodes.length ? nodes : ["\\u00a0"]));\n    entry.read.replaceChildren(first, groundsLine(reading?.grounds ?? null));',
        ):
            with self.subTest(line=line[:70]):
                self.assertIn(line, cross)
        line = function_body(self.script, "groundsLine")
        for part in (
            '  const line = element("span", "read-grounds");\n  if (grounds === null) {\n    line.append("\\u00a0");\n    return line;\n  }',
            '  if (grounds.lead !== null) {\n    line.append(element("span", "read-grounds-lead", describe(grounds.lead)));\n  }',
            'line.append(element("span", "read-grounds-reasons", describe(grounds.reasons)));',
            "line.title = describe(grounds.full);",
        ):
            with self.subTest(part=part[:70]):
                self.assertIn(part, line)
        self.assertEqual(self.catalogs["ja"]["view.spoken_grounds"], "（{grounds}）")
        # In English after a semicolon, as the whole has parentheses of its
        # own (the checker's review of X6).
        self.assertEqual(self.catalogs["en"]["view.spoken_grounds"], "; {grounds}")
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        for selector, wanted in (
            (".panel-read.two-lines", {"display": "flex", "flex": "1 1 auto", "flex-direction": "column", "align-items": "flex-end"}),
            (".read-line", {"white-space": "nowrap"}),
            # As high with no value as with one, of the size of a value.
            (".read-line::before", {"content": '"\\200b"', "font-size": "0.96rem"}),
            (".panel-read strong", {"font-size": "0.96rem"}),
            # The second line across the reading, its number counted in its
            # width and never cut (Codex's review of the diff of X6), its
            # reasons not.
            (".read-grounds", {"display": "flex", "align-self": "stretch", "overflow": "hidden", "white-space": "nowrap"}),
            (".read-grounds > :first-child", {"margin-left": "auto"}),
            (".read-grounds-lead", {"flex": "none"}),
            (".read-grounds-reasons", {"flex": "1 1 auto", "width": "0", "min-width": "0", "max-width": "max-content", "overflow": "hidden", "text-overflow": "ellipsis"}),
            # A low strip keeps one line, as it shows no summary and no notes.
            (".panel-view.mini .read-grounds", {"display": "none"}),
        ):
            rule = re.search(rf"\n{re.escape(selector)} \{{(.*?)\n\}}", style, re.DOTALL)
            assert rule is not None, selector
            found = dict(re.findall(r"^\s*([a-z-]+):\s*([^;]+);", rule.group(1), re.M))
            for name, value in wanted.items():
                with self.subTest(selector=selector, name=name):
                    self.assertEqual(found.get(name), value)
        # The second line has no width of its own that would cut its number.
        rule = re.search(r"\n\.read-grounds \{(.*?)\n\}", style, re.DOTALL)
        assert rule is not None
        self.assertNotRegex(rule.group(1), r"(^|\n)\s*(width|max-width):")

    def test_the_list_marks_each_row_left_out_and_says_the_grounds_under_its_value(self) -> None:
        # Stage X6 of v2.3.0: the cell of the item of a row that its panel
        # left out says why, after its value or its dash; a value missing is
        # said once to a screen reader; the line under the value of the list
        # says what the panel left out of the period, the whole on the
        # pointer.
        from tests.test_gui_view_save import function_body

        listing = function_body(self.script, "renderList")
        for line in (
            "parts.push(buildListTable(list, answer.rows, titleText, entry.item));",
            # The block whole, with its condition and its push (the partial
            # guard of X6: PV9).
            '    const grounds = listGrounds(entry.item, answer.value?.grounds, state.language);\n    if (grounds !== null) {\n      const under = element("p", "list-value list-grounds", `${describe(grounds.lead)}${describe(grounds.reasons)}`);\n      under.title = describe(grounds.full);\n      parts.push(under);\n    }\n',
        ):
            with self.subTest(line=line[:70]):
                self.assertIn(line, listing)
        table = function_body(self.script, "buildListTable")
        for line in (
            'const reasonKey = column === list.key && typeof row.left_out === "string" ? groundsWordKey(item, row.left_out, "short") : null;',
            'const reason = reasonKey === null ? null : element("span", "list-reason", t(reasonKey));',
            '        cell.append(dash, element("span", "visually-hidden", t("view.no_value")));\n        if (reason !== null) {\n          // A value missing is said once (stage X6 of v2.3.0).\n          if (reasonKey === "view.grounds.short.no_value") {\n            reason.setAttribute("aria-hidden", "true");\n          }\n          cell.append(reason);\n        }',
            "      } else if (reason !== null) {\n        cell.append(text, reason);",
        ):
            with self.subTest(line=line[:70]):
                self.assertIn(line, table)
        self.assertEqual(self.catalogs["ja"]["view.grounds.short.no_value"], self.catalogs["ja"]["view.no_value"])
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        for selector, wanted in ((".list-reason", {"margin-left": "0.35em", "color": "var(--sub)"}), (".list-value.list-grounds", {"margin-top": "0", "color": "var(--sub)"})):
            rule = re.search(rf"\n{re.escape(selector)} \{{(.*?)\n\}}", style, re.DOTALL)
            assert rule is not None, selector
            found = dict(re.findall(r"^\s*([a-z-]+):\s*([^;]+);", rule.group(1), re.M))
            for name, value in wanted.items():
                with self.subTest(selector=selector, name=name):
                    self.assertEqual(found.get(name), value)

    def test_every_view_asks_with_its_conditions(self) -> None:
        # Stage T1 of v2.2.0: the panels, the two items plotted, the
        # distribution, and the shoes ask with the conditions in force, which
        # the page remembers with the view; the list of a period asks with
        # those of the answer drawn, as with its types; the overview asks
        # again for other conditions (Codex 2 of the plan of T1).
        asked = "    types: typesRequest(state.counted, state.view.types),\n    conditions: state.conditions,\n  };"
        held = {
            "seriesPayload": (asked,),
            "plotPayload": (asked,),
            "spreadPayload": (asked,),
            "shoesPayload": (asked,),
            "viewValues": ("    spread: state.spreadItem,\n    conditions: state.conditions,",),
            "openList": ("    types: state.answerTypes,\n    conditions: state.answerConditions,",),
            "requestList": ("      types: list.types,\n      conditions: list.conditions,",),
            "requestOverview": (
                "const parts = [state.view.view, key, typesRequest(state.counted, state.view.types), conditionsKey(state.conditions)];",
                # With the number of its reading (stage W1 of v2.2.1).
                "const signature = JSON.stringify([...parts, state.viewRead]);",
                # An answer on its way for other conditions is dropped when the
                # overview drawn is that of these (Codex's review of the diff).
                "  if (state.overview?.signature === signature) {\n    // The overview drawn is that of these: an answer on its way for others,\n    // such as conditions changed and changed back, is dropped (Codex's\n    // review of the diff of T1).\n    state.overviewSeq += 1;\n    return;\n  }",
            ),
        }
        for name, lines in held.items():
            found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, found.group(1))

    def test_every_button_has_a_name_in_both_languages(self) -> None:
        # Its words, its name for an icon (data-i18n-label), the words of its
        # parts, or the words that label it.
        buttons = [element for element in self.elements if element.tag == "button"]
        self.assertTrue(buttons)
        for button in buttons:
            with self.subTest(button=button.get("id") or button.get("data-period") or button.get("data-grain")):
                self.assertEqual(button.get("type"), "button")
                parts = [element.get("data-i18n") for element in self.elements if button in element.ancestors() and element.get("data-i18n")]
                labels = str(button.get("aria-labelledby") or "").split()
                if button.get("data-i18n"):
                    self.assertTrue(self.named(button.get("data-i18n")))
                elif button.get("data-i18n-label"):
                    self.assertTrue(self.named(button.get("data-i18n-label")))
                elif labels:
                    self.assertTrue(self.named(by_id(self.elements, labels[0]).get("data-i18n")))
                elif button.get("id") in ("open-latest", "empty-primary"):
                    # The script gives them the words of what they do.
                    self.assertIn(f'ui.{"openLatest" if button.get("id") == "open-latest" else "emptyPrimary"}', self.script)
                else:
                    self.assertTrue(parts and all(self.named(key) for key in parts))
        # An icon button says what it does to screen readers only.
        for identifier, key in (
            ("period-back", "view.period.back"),
            ("period-next", "view.period.next"),
            ("shelf-fold", "view.shelf.fold"),
            ("shelf-open", "view.shelf.open"),
        ):
            with self.subTest(icon=identifier):
                self.assertEqual(by_id(self.elements, identifier).get("data-i18n-label"), key)

    def test_the_view_is_written_before_the_app_quits_and_when_the_page_hides(self) -> None:
        # v2.2.0 K2, in the page script, which no test runs: the view is
        # written 0.8 seconds after the last change (laterSender, which the
        # node tests check), at once before this page quits the app and when
        # the normalization page asks before it does, and in a keepalive
        # request when the page hides; once the app stopped, what waits is
        # not written.
        for line in (
            "const REMEMBER_WAIT_MS = 800;",
            "const viewLater = laterSender(writeView, REMEMBER_WAIT_MS);",
            'window.addEventListener("pagehide", rememberOnHide);',
            'callWithKey(state.launchKey, "/api/settings/view", { ...value.view, generation }, { keepalive: true })',
            "if (answerFlush(event.data, rememberNow, quitChannel)) {",
            # What the page takes of the settings when it starts, and of an
            # output that opens (view_flow.mjs, which the node tests check),
            # and the types as the person chose them.
            "takeLayouts(state.settings.view_layouts, state.settings.view_layouts_hidden, state.settings.view_layout);",
            "const period = periodToOpen(state.settings.view_period, null, null);",
            "state.grain = grainToOpen(state.settings.view_grain);",
            "state.wantedTypes = Array.isArray(state.settings.view_types) ? [...state.settings.view_types] : null;",
            "state.counted = typesToOpen(state.wantedTypes, answer.types) ?? defaultTypes(answer.types);",
            'const period = periodToOpen(periodRequest(state.period, state.range), answer.first_day, answer.last_day) ?? { choice: "all", range: null };',
            "state.wantedTypes = typesRequest(state.counted, state.view?.types);",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        now = re.search(r"function rememberNow\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert now is not None
        self.assertEqual([line.strip() for line in now.group(1).strip().splitlines()], ["viewLater.flush();", "return viewWriting;"])
        stopped = re.search(r"function markStopped\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert stopped is not None
        self.assertIn("viewLater.take();", stopped.group(1))
        stop = re.search(r"async function quit\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert stop is not None
        self.assertIn('await quitAfterWriting(rememberNow, () => callApi("/api/shutdown"));', stop.group(1))

    def test_the_layouts_are_chosen_changed_and_moved_from_the_page(self) -> None:
        # v2.2.0 K2, in the page script, which no test runs: a card shows its
        # items that the output knows, in its order; a removal is asked with
        # keeping the layout as the button that has the focus; a layout that
        # another tab removed reads the layouts again; a drag of a grip is one
        # change with its place, and the arrow keys on a grip move it by one;
        # Escape puts a dragged row back before it closes the window.
        for line in (
            "changeItems(card.items.filter((key) => known.has(key)));",
            "ui.layoutsPopBody.querySelector('[data-op=\"keep\"]')?.focus();",
            'if (error.code === "LAYOUT_NOT_FOUND") {\n        await readLayouts();',
            'ui.layoutsPopBody.addEventListener("pointerdown", layoutGripDown);',
            'ui.layoutsPopBody.addEventListener("pointermove", layoutGripMove);',
            'ui.layoutsPopBody.addEventListener("pointerup", layoutGripUp);',
            'ui.layoutsPopBody.addEventListener("pointercancel", cancelLayoutDrag);',
            'ui.layoutsPopBody.addEventListener("lostpointercapture", cancelLayoutDrag);',
            "ui.layoutsPopBody.setPointerCapture(event.pointerId);",
            'changeLayouts({ op: "move", id, to });',
            'changeLayouts({ op: "move", id: event.target.dataset.id, direction: event.key === "ArrowUp" ? "up" : "down" });',
            "const to = dropPlace(middles, event.clientY);",
            'layoutDrag.row.querySelector(".layout-grip")?.focus();',
            "if (layoutDrag !== null) {\n        cancelLayoutDrag();\n      } else {\n        openLayouts(false);",
            'grip.setAttribute("aria-label", t("view.layouts.grip", { name: layout.name }));',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # A name of the person is text, never markup.
        self.assertIn('button.append(element("span", "layout-name", card.builtIn ? t(card.nameKey) : card.name));', self.script)

    def test_headings_do_not_skip_levels(self) -> None:
        levels = [int(element.tag[1]) for element in self.elements if re.fullmatch(r"h[1-6]", element.tag)]
        self.assertEqual(levels[0], 1)
        self.assertEqual(levels.count(1), 1)
        for previous, current in zip(levels, levels[1:]):
            self.assertLessEqual(current, previous + 1, levels)
        # The panels are named by headings under the stage's.
        self.assertEqual(by_id(self.elements, "stage-heading").tag, "h2")
        self.assertIn('const heading = element("h3", "panel-name", name);', self.script)
        self.assertIn('section.setAttribute("aria-labelledby", headingId);', self.script)

    def test_live_regions_are_polite_apart_from_the_connection_alert(self) -> None:
        for element in self.elements:
            if element.get("aria-live") is not None:
                with self.subTest(element=element.get("id")):
                    self.assertEqual(element.get("aria-live"), "polite")
        alerts = [element.get("id") for element in self.elements if element.get("role") == "alert"]
        self.assertEqual(alerts, ["connection-problem"])
        # The values of the cross line are said by a hidden region, which the
        # page fills only when the keyboard moves the line.
        announcer = by_id(self.elements, "cross-announcer")
        self.assertEqual(announcer.get("aria-live"), "polite")
        self.assertIn("visually-hidden", str(announcer.get("class")).split())
        self.assertEqual(self.script.count("setText(ui.announcer,"), 1)
        self.assertIn("if (speak) {", self.script)
        speaking = [line.strip() for line in self.script.splitlines() if "moveCross(" in line and ", true)" in line]
        self.assertEqual(speaking, [
            "moveCross((state.cursor ?? 0) + CROSS_KEYS[event.key], true);",
            "moveCross(0, true);",
            "moveCross((state.answer?.periods.length ?? 1) - 1, true);",
        ])
        self.assertIn("moveCross(index, false);", self.script)
        # And that of the years compared (stage L1 of v2.2.0).
        compared = by_id(self.elements, "compare-announcer")
        self.assertEqual(compared.get("aria-live"), "polite")
        self.assertIn("visually-hidden", str(compared.get("class")).split())
        # From stage N1, a calendar says the day of its strip there too.
        self.assertEqual(self.script.count("setText(ui.compareAnnouncer,"), 2)
        self.assertIn('setText(ui.compareAnnouncer, t("view.compare.calendar_spoken", { day: describe(reading.day), value }));', self.script)
        speaking = [line.strip() for line in self.script.splitlines() if "moveCompareCross(" in line and ", true)" in line]
        self.assertEqual(speaking, [
            "moveCompareCross((state.compare.cursor ?? 0) + CROSS_KEYS[event.key], true);",
            "moveCompareCross(0, true);",
            "moveCompareCross(compareContext.span, true);",
        ])

    def test_focus_targets_after_actions_can_take_focus(self) -> None:
        for identifier in (
            "empty-heading",
            "stop-heading",
            "series-stop-heading",
            "compare-stop-heading",
            "help-heading",
            "help-zero-heading",
            "help-calculated-heading",
            "help-records-heading",
        ):
            with self.subTest(heading=identifier):
                self.assertEqual(by_id(self.elements, identifier).get("tabindex"), "-1")

    def test_the_controls_say_what_they_open(self) -> None:
        for button, region, expanded in (
            ("help-button", "help-panel", "false"),
            ("types-button", "types-pop", "false"),
            ("coverage-button", "coverage-text", "false"),
            ("add-items", "picker", "false"),
            ("quit-button", "quit-confirm", "false"),
            # The shelf is open at first; its rail opens it when it is folded.
            ("shelf-fold", "shelf", "true"),
            ("shelf-open", "shelf", "false"),
        ):
            with self.subTest(button=button):
                element = by_id(self.elements, button)
                self.assertEqual((element.get("aria-expanded"), element.get("aria-controls")), (expanded, region))
        for region in ("help-panel", "types-pop", "coverage-text", "picker", "quit-confirm", "shelf-rail", "range-row"):
            with self.subTest(region=region):
                self.assertIn("hidden", by_id(self.elements, region).attributes)
        # The choices of the period and the grouping are pressed buttons in a
        # group named by its words.
        for group, label, attribute in (
            ("period-choices", "period-label", "data-period"),
            ("grain-choices", "grain-label", "data-grain"),
            ("compare-modes", "compare-show-label", "data-compare-mode"),
            # What one item is compared by (stage M2 of v2.2.0).
            ("compare-bys", "compare-by-label", "data-compare-by"),
        ):
            with self.subTest(group=group):
                element = by_id(self.elements, group)
                self.assertEqual((element.get("role"), element.get("aria-labelledby")), ("group", label))
                members = [child for child in self.elements if child.parent is element]
                self.assertTrue(members)
                for member in members:
                    self.assertEqual((member.tag, member.get("aria-pressed")), ("button", "false"))
                    self.assertTrue(member.get(attribute))
        self.assertEqual(by_id(self.elements, "types-button").get("aria-labelledby"), "types-label types-summary")

    def test_years_are_compared_apart_from_the_panels(self) -> None:
        # v2.2.0 L1, in the page and its script, which no test runs: each panel
        # has a button that names its item; the comparison is a section named
        # by its heading, with the item in it, three ways in a group, the years
        # as pressed buttons (up to six, said under them), the words of running
        # totals that open under their button, its own stop, and the words of
        # what is not used, under the filters.
        section = by_id(self.elements, "compare")
        self.assertEqual((section.tag, section.get("aria-labelledby")), ("section", "compare-title"))
        self.assertIn("hidden", section.attributes)
        self.assertEqual(by_id(self.elements, "compare-title").tag, "h3")
        self.assertIs(by_id(self.elements, "compare-item").parent, by_id(self.elements, "compare-title"))
        self.assertEqual(by_id(self.elements, "compare-stop-heading").tag, "h4")
        years = by_id(self.elements, "compare-years")
        self.assertEqual((years.get("role"), years.get("aria-labelledby"), years.get("aria-describedby")), ("group", "compare-years-label", "compare-up-to"))
        about = by_id(self.elements, "compare-about")
        self.assertEqual((about.get("aria-expanded"), about.get("aria-controls")), ("false", "compare-about-text"))
        self.assertIn("hidden", by_id(self.elements, "compare-about-text").attributes)
        off = by_id(self.elements, "compare-off")
        self.assertEqual(off.get("data-i18n"), "view.compare.off")
        self.assertIn("hidden", off.attributes)
        self.assertEqual(by_id(self.elements, "compare-back").get("data-i18n"), "view.panel.unbig")
        for line in (
            'const compareButton = textButton(t("view.compare.button"), "compare", key);',
            'compareButton.setAttribute("aria-label", t("view.compare.title", { name }));',
            # From stage M2, a year or a race by its name.
            'const heading = element("h4", "panel-name compare-year");',
            "heading.append(...compareName(entry));",
            'button.setAttribute("aria-pressed", String(on));',
            "button.disabled = on ? chosen.length <= 1 : chosen.length >= MAX_COMPARE_YEARS;",
            ': t("view.compare.row_label", { year: describe(entry.label), name }),',
            # From stage M2, a race says its span too.
            '? t("view.compare.race_row_label", { race: describe(entry.label), name, span: t("view.compare.race_days", { n: context.weeks }) })',
            'wrap.setAttribute("aria-label", race ? t("view.compare.race_table_label", { name }) : t("view.compare.table_label", { name }));',
            'const caption = element("caption", "visually-hidden", race ? t("view.compare.race_table_caption", { name, kind }) : t("view.compare.table_caption", { name, kind }));',
            'frame.setAttribute("aria-hidden", "true");',
            "ui.compareItem.focus();",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)

    def test_a_comparison_by_race_day_has_its_own_parts_and_follows_the_marks(self) -> None:
        # v2.2.0 M2, in the page and its script, which no test runs: what it
        # compares by is a group of two pressed buttons in its title, the race
        # day greyed with its reason said in words beside it; the weeks in the
        # place of the month, with a label; the races as pressed buttons, up
        # to six, said under them; and its own words of what is not used. The
        # script asks for each race by week and by its whole span, follows the
        # marks, and remembers what it compares by and the weeks.
        title = by_id(self.elements, "compare-title")
        bys = by_id(self.elements, "compare-bys")
        self.assertIs(bys.parent, title)
        race = next(element for element in self.elements if element.get("data-compare-by") == "race")
        self.assertEqual(race.get("aria-describedby"), "compare-race-needed")
        needed = by_id(self.elements, "compare-race-needed")
        self.assertEqual(needed.get("data-i18n"), "view.compare.race_needed")
        self.assertIn("hidden", needed.attributes)
        self.assertIn("visually-hidden", str(by_id(self.elements, "compare-by-label").get("class")).split())
        weeks = by_id(self.elements, "compare-weeks-field")
        self.assertIn("hidden", weeks.attributes)
        self.assertIs(by_id(self.elements, "compare-weeks").parent, weeks)
        races = by_id(self.elements, "compare-races")
        self.assertEqual((races.get("role"), races.get("aria-labelledby"), races.get("aria-describedby")), ("group", "compare-races-label", "compare-races-up-to"))
        for hidden in ("compare-races", "compare-races-label", "compare-races-up-to", "compare-off-race"):
            with self.subTest(hidden=hidden):
                self.assertIn("hidden", by_id(self.elements, hidden).attributes)
        self.assertEqual(by_id(self.elements, "compare-off-race").get("data-i18n"), "view.compare.off_race")
        rows = by_id(self.elements, "compare-rows-race")
        self.assertEqual((rows.get("data-i18n"), rows.parent.get("data-compare-mode")), ("view.compare.mode.rows_race", "rows"))
        self.assertIn("hidden", rows.attributes)
        for line in (
            # The race day only with two races offered, and its reason.
            'button.disabled = button.dataset.compareBy === "race" && !offered;',
            "ui.compareRaceNeeded.hidden = offered;",
            'if (!comparing() || !COMPARE_BYS.includes(by) || (by === "race" && compareByFor(by, raceChoices()) !== "race")) {',
            # Each race by its grouping (a week, or a day from stage X3 of
            # v2.3.0) and by its whole span, in one generation.
            '? races.flatMap((race) => [seriesPayload([key], raceRange(race.day, weeks), grain), seriesPayload([key], raceRange(race.day, weeks), RANGE_GRAIN)])',
            "compare.races = racesKept(compare.races, choices);",
            # The races chosen, up to six, one at least.
            "button.disabled = on ? chosen.length <= 1 : chosen.length >= MAX_COMPARE_RACES;",
            # The marks that change follow into the comparison; another
            # output takes its races and its grouping.
            "    followMarks();\n",
            # Against the last request, also one whose answer is on its way
            # (Codex's review of the diff of M2).
            "  const asked = state.compare.asked ?? null;\n  const before = asked?.by ?? null;",
            "  compare.asked = { by, races: races.map((race) => ({ id: race.id, day: race.day, name: race.name })) };",
            "state.compare.races = firstCompareRaces(raceChoices());\n        settleCompareGrain(state.compareAnswer?.by ?? null);",
            # The grouping of a race day, whatever the way (from stage N1,
            # with the month that the way uses: none for a calendar; from
            # stage X3 of v2.3.0 the one chosen, by compareGrainAfter).
            "const grain = compareGrainAfter(compareModeNow());",
            "return compareGrainFor(by, mode, compareMonthNow());",
            "const grains = apart ? compareGrainsFor(compareByNow(), compareMonthNow(), compareModeNow()) : null;",
            "ui.compareOffRace.hidden = !byRace;",
            # One row per race, by race day; a grouping that does not fit
            # what it compares by is set again at every request.
            "ui.compareRowsRace.hidden = !race;",
            "  compare.races = racesKept(compare.races, choices);\n  // Its grouping, where what it compares by changed by another way (an\n  // output opened again for a new ticket).\n  settleCompareGrain(by);",
            # Remembered with the rest of the view.
            "compare_by: state.compareBy,",
            "compare_weeks: state.compareWeeks,",
            "const by = compareByToOpen(state.settings);",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # The short name to the eye, the whole name and the days to the ear
        # (Codex's review of the diff of M2), in the bar of the races: from
        # L3 the keys of the legend by race day say them so too, so these
        # lines are held to the function of the bar.
        from tests.test_gui_view_save import function_body

        bar = function_body(self.script, "renderCompareRaces")
        for line in ('shown.setAttribute("aria-hidden", "true");', 'button.append(shown, element("span", "visually-hidden", describe(chip.spoken)));'):
            with self.subTest(bar=line):
                self.assertIn(line, bar)

    def test_a_comparison_by_race_day_goes_by_day_too(self) -> None:
        # v2.3.0 X3, in the page and its script, which no test runs: by race
        # day, the day too (the person's choice B of the samples), kept when
        # the way or the item changes (the checker's review of the steps of the
        # samples, 2), the cross line set back as before (the checker's review
        # of the plan of its parts, 3: held apart); the answer by its grouping,
        # placed, named, and marked by day; a place before the span of a race
        # is not in its span in the readings and the table, with a note under
        # the table where a race by day has such places.
        from tests.test_gui_view_save import function_body

        held = {
            "compareGrainAfter": (
                'if (by === "race" && compareGrainsFor(by, compareMonthNow(), mode).includes(state.compare.grain)) {',
                "return state.compare.grain;",
                "return compareGrainFor(by, mode, compareMonthNow());",
            ),
            "chooseCompareItem": ("state.compare.grain = compareGrainAfter(mode);", "state.compare.cursor = null;"),
            "chooseCompareMode": ("const grain = compareGrainAfter(compareModeNow());", "state.compare.grain = grain;", "state.compare.cursor = null;"),
            "requestCompare": (
                "? races.flatMap((race) => [seriesPayload([key], raceRange(race.day, weeks), grain), seriesPayload([key], raceRange(race.day, weeks), RANGE_GRAIN)])",
                "            month: null,\n            grain,\n            years: [],",
            ),
            "renderCompareBody": (
                "raceData({ races: answer.races, weeks: answer.weeks, mode, series: compare.series, answers: answer.answers, wholes: answer.wholes, language: state.language, grain: answer.grain })",
                "const span = race ? raceSpan(answer.weeks, answer.grain) : compareSpan(answer.grain, answer.month, answer.years);",
                "slotName: (slot) => raceSlotName(slot, answer.weeks, answer.grain),",
            ),
            # From v2.3.0 X5, thinned for a PNG only.
            "drawCompareAxis": ("let ticks = race ? raceTicks(context.weeks, context.grain) : compareTicks(context.grain, context.month, newest, state.language);",),
            "renderCompareRead": ('nodes.push(compareSlotText(context, at), element("span", "no-value", t(compareMissingKey(year, at))));',),
            "buildCompareTable": ('const text = cell.notInSpan ? t("view.compare.not_in_span_cell") : cell.outside ? "—" :',),
            "renderCompare": (
                "const answered = state.compareAnswer;",
                'ui.compareSpanNote.hidden = !ready || !compare.table || answered.by !== "race" || !racesNotInSpan(answered.races, answered.weeks, answered.grain);',
            ),
        }
        for name, lines in held.items():
            body = function_body(self.script, name)
            for line in lines:
                with self.subTest(function=name, line=line[:60]):
                    self.assertIn(line, body)
        note = by_id(self.elements, "compare-span-note")
        self.assertEqual((note.get("data-i18n"), note.get("class")), ("view.compare.not_in_span_note", "compare-note"))
        self.assertIn("hidden", note.attributes)
        self.assertIs(note.parent, by_id(self.elements, "compare-note").parent)

    def test_the_highest_of_each_year_is_marked_heard_and_drawn(self) -> None:
        # v2.3.0 X4, in the page and its script, which no test runs (the
        # person's choice "1 C と案 2" of the samples): in the table, the value
        # of the highest in bold with a triangle for the eye only and its word
        # for the ear; in the heading of a row, one span of compare-whole (so
        # that a picture takes its words whole, saveComparePart), its words up
        # to the value apart from its period, which may shrink, while the
        # heading of a race stays as it was (Codex's third read of the diff of
        # X4, 3); in a chart of one row only, a triangle above the highest,
        # never on one panel or for a running total, apart from the cross line
        # and above it (the third read, 2), clear of what is drawn there by
        # its shape (the third read, 1); a note under the table with the other
        # notes, which the table fills.
        from tests.test_gui_view_save import function_body

        held = {
            "highestGlyph": ('const glyph = element("span", "compare-highest-glyph", text);', 'glyph.setAttribute("aria-hidden", "true");'),
            "buildCompareTable": (
                "if (cell.highest) {",
                'td.classList.add("compare-highest");',
                'td.append(" ", highestGlyph("▲"), element("span", "visually-hidden", t("view.compare.highest_cell")));',
            ),
            "buildCompareRow": (
                'const heading = element("h4", "panel-name compare-year");',
                "const highest = compareHighestWords(context.item, entry, context.grain, state.language, context.mode);",
                'const [before = "", after = ""] = t("view.summary.highest", { value: "\\u0001", period: describe(highest.period) }).split("\\u0001");',
                'const high = element("span", "compare-whole compare-highest-head");',
                'fixed.append(highestGlyph("▼"), before, element("strong", "", describe(highest.value)));',
                'high.append(fixed, element("span", "compare-highest-period", after));',
            ),
            "drawComparePlot": (
                'if (!one && context.mode !== "cumulative") {',
                "const at = year.highest ? year.slots[year.highest.index] : undefined;",
                # Above every mark of its period: its value and its points of
                # the records of a day (Codex's review of the diff of X4, 2).
                "const above = year.highest ? highestMarkValues(entry.lines[0], year.highest.index) : [];",
                # Clear of what is drawn there, also of the hollow dot of a 0
                # (Codex's fourth read of the diff of X4): highestMarkAt.
                'highestMark = svgElement("path", { class: "compare-highest-mark", d: highestMarkAt(first, at, above) });',
                "svg.append(cross);\n  if (highestMark !== null) {\n    svg.append(highestMark);\n  }",
            ),
            "renderCompare": ("if (!ready || !compare.table) {\n    ui.compareHighestNote.hidden = true;\n  }",),
            "renderCompareBody": (
                # Of the year, of the month chosen, or of the span of a race
                # (Codex's review of the diff of X4, 3).
                "const highestNote = compare.table ? compareHighestNoteKey(mode, data, answer.by, answer.month) : null;",
                "ui.compareHighestNote.hidden = highestNote === null;",
                'ui.compareHighestNote.replaceChildren(...(highestNote === null ? [] : [highestGlyph("▲"), " ", t(highestNote)]));',
            ),
            "saveComparePart": ('} else if (node.matches(".panel-unit, .compare-whole")) {',),
        }
        for name, lines in held.items():
            body = function_body(self.script, name)
            for line in lines:
                with self.subTest(function=name, line=line[:60]):
                    self.assertIn(line, body)
        # The triangle of the chart is apart from the cross line, which moves
        # without it.
        self.assertNotIn("compare-highest", function_body(self.script, "moveCompareCross"))
        # The note under the table: hidden at first, between the note of * and
        # — and the note of the days not in the span (the checker's review of
        # the plan of the parts of X4, 3).
        note = by_id(self.elements, "compare-highest-note")
        self.assertEqual((note.get("class"), note.get("data-i18n")), ("compare-note", None))
        self.assertIn("hidden", note.attributes)
        # The elements of the page are in its order.
        notes = [element.get("id") for element in self.elements if element.parent is note.parent and element.get("id") in ("compare-note", "compare-highest-note", "compare-span-note", "compare-count-note")]
        self.assertEqual(notes, ["compare-note", "compare-highest-note", "compare-span-note", "compare-count-note"])

    def test_the_heading_of_a_row_keeps_the_value_of_its_highest(self) -> None:
        # v2.3.0 X4 (the checker's review of the plan of its parts, 1): the
        # heading of a row is one line of 24 px whose overflow is hidden; its
        # highest never shrinks up to the value, its period shrinks first with
        # an ellipsis (its closing bracket with it; its leading space of
        # English kept), then the name of a race, whose flex shrink is tiny so
        # that it waits for the period; for the eye only. The triangles in the
        # colors of the words, and in those of the system in forced colors.
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        for rule in (
            r"\.compare-stack \.panel-view\.compare-row \.panel-head \{\s*flex: none;\s*flex-wrap: nowrap;\s*height: 24px;\s*padding-top: 3px;\s*overflow: hidden;\s*\}",
            # Its span gives no box of its own, so that its two parts are
            # items of the heading (the real-page check of X4: a box of its
            # own could not be smaller than all its words, so nothing shrank).
            r"\.compare-stack \.panel-view\.compare-row \.panel-head \.compare-highest-head \{\s*display: contents;\s*\}",
            r"\.compare-highest-fixed \{\s*white-space: nowrap;\s*\}",
            r"\.compare-highest-period \{\s*flex: 0 1 auto;\s*min-width: 0;\s*margin-left: -8px;\s*overflow: hidden;\s*text-overflow: ellipsis;\s*white-space: pre;\s*\}",
            r"\.compare-highest-head \.compare-highest-glyph \{\s*margin-right: 3px;\s*color: var\(--text\);\s*font-size: 0\.8em;\s*\}",
            r"\.years-table td\.compare-highest \{\s*font-weight: 700;\s*\}",
            r"\.compare-highest-mark \{\s*fill: var\(--text\);\s*stroke: var\(--surface\);\s*stroke-width: 1\.5;\s*paint-order: stroke;\s*\}",
        ):
            with self.subTest(rule=rule[:60]):
                self.assertRegex(css, rule)
        forced = css[css.index("@media (forced-colors: active)") :]
        self.assertRegex(forced[: forced.index("\n}\n")], r"\.compare-highest-mark \{\s*fill: CanvasText;\s*stroke: Canvas;\s*\}")

    def test_a_year_stands_out_on_one_panel(self) -> None:
        # v2.2.0 L3, in the page and its script, which no test runs: the keys of
        # the legend of one panel are buttons in a group named by what they do,
        # pressed or not; each year a group of its shapes, with what it draws
        # and the boxes of its name kept for the pointer; a press marks the
        # shapes and the keys and draws nothing again (Codex's review of the
        # plan, 3), so that a key keeps the focus; a press on the chart goes by
        # the place in the units of its view box (the checker's review of the
        # handling, 5); Esc puts it back only with one, on its chart or a key;
        # it lasts while one panel draws it, and is never remembered. After
        # Codex's review of the diff: a key only for a year that the chart
        # draws (1), a race to the ear by its whole name and its days, as its
        # button in the bar (5), the boxes of the names measured each time
        # they are marked, a name stood out bold (3), and the dots of the cross
        # line in their order again (4, and the checker's).
        from tests.test_gui_view_save import function_body

        for name, lines in (
            (
                "buildCompareOne",
                (
                    'keys.setAttribute("role", "group");',
                    'keys.setAttribute("aria-label", t(context.by === "race" ? "view.compare.lit_races" : "view.compare.lit_years"));',
                    "const drawn = yearDrawn(entry);",
                    'const key = element(drawn ? "button" : "span", `key y${entry.step}`);',
                    'key.type = "button";',
                    "key.dataset.lit = entry.id;",
                    'key.setAttribute("aria-pressed", String(lit !== null && lit.id === entry.id));',
                    "const chip = raceChip(entry.race, state.language);",
                    'shown.setAttribute("aria-hidden", "true");',
                    'key.append(shown, element("span", "visually-hidden", describe(chip.spoken)));',
                ),
            ),
            (
                "drawComparePlot",
                (
                    "entry.groups = null;",
                    "hits: one,",
                    'const group = one ? svgElement("g", { class: "compare-marks" }) : svg;',
                    "names[end.index] = text;",
                    "Object.assign(entry, { shapes, cross, crossLine, crossDots, groups: one ? groups : null, names });\n  markLit(entry);",
                ),
            ),
            (
                "markLit",
                (
                    "for (const index of topFirst(entry.groups.length, at).reverse()) {",
                    'node?.classList.toggle("lit", index === at);',
                    'node?.classList.toggle("dim", at >= 0 && index !== at);',
                    "entry.groups[index].parentNode.append(entry.groups[index]);",
                    "for (const dot of entry.crossDots) {\n    entry.cross.append(dot);\n  }\n  if (at >= 0) {\n    entry.cross.append(entry.crossDots[at]);\n  }",
                    "entry.boxes = entry.names.map((name) => name.getBBox());",
                ),
            ),
            (
                "standOut",
                (
                    "state.compare.lit = id === null ? null : litAfter(state.compare.lit, compareContext.by, id);",
                    'key.setAttribute("aria-pressed", String(state.compare.lit?.id === key.dataset.lit));',
                    "markLit(entry);",
                    "renderSaveNotice();",
                ),
            ),
            (
                "compareClick",
                (
                    "const place = plotPlace(event.clientX, event.clientY, svg.getBoundingClientRect(), width, height);",
                    "const order = topFirst(entry.data.length, lit === null ? -1 : entry.data.findIndex((year) => year.id === lit.id));",
                    "entry.shapes.map((shape) => shape.lines[0]?.hits ?? null),",
                    "place.reach,",
                    "standOut(entry.data[at].id);",
                ),
            ),
            (
                "renderCompareBody",
                (
                    "compare.lit = litKept(compare.lit, { by: answer.by, mode, table: compare.table, data });",
                    "const focusedKey = ui.comparePanels.contains(document.activeElement) ? (document.activeElement.dataset.lit ?? null) : null;",
                    'ui.comparePanels.querySelector(`button.key[data-lit="${CSS.escape(focusedKey)}"]`)?.focus({ preventScroll: true });',
                ),
            ),
            ("enterCompare", ("    lit: null,\n",)),
        ):
            body = function_body(self.script, name)
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body)
        stand = function_body(self.script, "standOut")
        for drawn in ("render()", "renderCompareBody(", "renderCompareCharts(", "drawComparePlot("):
            with self.subTest(drawn=drawn):
                self.assertNotIn(drawn, stand)
        for line in (
            '''    if (event.key === "Escape" && state.compare?.lit && event.target.matches?.('.plot[data-plot="one"], button.key[data-lit]')) {\n      event.preventDefault();\n      standOut(null);\n    } else if''',
            '''    const key = event.target.closest?.("button.key[data-lit]") ?? null;\n    if (key !== null) {\n      standOut(key.dataset.lit);\n    } else if (event.target.closest?.('.plot[data-plot="one"]')) {\n      compareClick(event);''',
        ):
            with self.subTest(listener=line):
                self.assertEqual(self.script.count(line), 1)
        # Never remembered.
        self.assertNotRegex(function_body(self.script, "viewValues"), r"\blit\b")
        for language, catalog in self.catalogs.items():
            for key in ("view.compare.lit_years", "view.compare.lit_races"):
                with self.subTest(language=language, key=key):
                    self.assertTrue(catalog[key])
        # The key pressed is bold in an edge of the color of the text, its name
        # at the end of its line too; where the system forces its colors, the
        # edge of the highlight, and the others without an edge.
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        normal, after = css.split("@media (forced-colors: active) {", 1)
        forced = after.split("\n}\n", 1)[0]
        self.assertRegex(normal, r"\.panel-keys button\.key \{[^}]*border: 1px solid transparent;[^}]*\}")
        self.assertRegex(normal, r'\.panel-keys button\.key\[aria-pressed="true"\] \{\s*border-color: var\(--text\);\s*font-weight: 600;\s*\}')
        # Stage U3 of v2.2.0: the words of each key in the color of its
        # line, stood out or not, by the step of the year in its class.
        for step in range(1, 7):
            with self.subTest(step=step):
                self.assertRegex(normal, rf"\.panel-keys \.key\.y{step} \{{\s*color: var\(--year{step}-ink\);\s*\}}")
        self.assertIn('const key = element(drawn ? "button" : "span", `key y${entry.step}`);', (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8"))
        self.assertRegex(normal, r"\.compare-label\.lit \{\s*fill: var\(--text\);\s*font-weight: 600;\s*\}")
        self.assertRegex(forced, r"\.compare-label,\s*\.compare-label\.newest,\s*\.compare-label\.lit \{\s*fill: CanvasText;\s*\}")
        self.assertRegex(forced, r"\.panel-keys button\.key \{\s*border-color: Canvas;\s*\}")
        self.assertRegex(forced, r'\.panel-keys button\.key\[aria-pressed="true"\] \{\s*border-color: Highlight;\s*\}')

    def test_the_years_of_a_table_of_comparing_years_are_apart(self) -> None:
        # v2.2.0 U3 (the person's hand check of the release candidate): in a
        # table of comparing years (or races), each year begins with a line on
        # its left, its value after the count of the one before, or each
        # column without counts (running totals), in the color of the edges
        # (3:1 on the surface, CONTROL_PAIRS); the tables by shoes, which share
        # the class compare-table, keep their form.
        from tests.test_gui_view_save import function_body

        script = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        table = function_body(script, "buildCompareTable")
        for line in (
            'const table = element("table", "t years-table");',
            "const starts = (index) => index > 0 && (!counts || index % 2 === 1);",
            'const ofRace = entry.key === "view.compare.race";',
            'const cell = element("th", index === 0 ? "" : starts(index) ? "n year-start" : "n", ofRace ? null : describe(entry));',
            "if (ofRace) {\n      cell.append(...raceHeadParts(entry));\n    }",
            # From stage X4 of v2.3.0 the cell is kept, for the triangle of
            # the highest, before it is appended.
            'const td = element("td", cell.value === null ? "n empty year-start" : "n year-start", text);',
            "tr.append(td);",
        ):
            with self.subTest(line=line):
                self.assertIn(line, table)
        self.assertRegex(css, r"\.years-table \.year-start \{\s*border-left: 2px solid var\(--edge\);\s*\}")
        shoes = function_body(script, "buildShoesTable")
        self.assertNotIn("year-start", shoes)
        self.assertNotIn("years-table", shoes)

    def test_a_table_of_comparing_years_fits_six_and_says_what_it_counts(self) -> None:
        # v2.2.1 W3 (the person's answer to the question of six years): a table
        # of comparing years (or races) wraps its places and its headings,
        # English at spaces, never inside a word, and Japanese between its
        # characters too, so that six years or races fit its box;
        # in English its headings of the counts are one short word ("Count"),
        # with the whole word for a screen reader, and a note under the table
        # says what was counted. The tables by shoes keep their form.
        from tests.test_gui_view_save import function_body

        script = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        page = (STATIC_ROOT / "view.html").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.compare-table \.t\.years-table tbody th,\s*\.compare-table \.t\.years-table thead th \{\s*white-space: normal;\s*\}")
        rule = css[css.index(".compare-table .t.years-table tbody th,") :]
        rule = rule[: rule.index("}")]
        self.assertNotIn("overflow-wrap", rule)
        # Japanese, which has no spaces, wraps between its characters too, so
        # that six years or six races fit: no keep-all (the person's choice
        # after Codex's review of the diff).
        self.assertNotIn("word-break", rule)
        # From v2.3.0 (stage X2): the name of a race in a heading is in a part
        # of its own that may wrap between any two characters where it does
        # not fit (six names of thirty letters with no space kept the table
        # out of its box); the words around it are those of its message, so
        # that the text of the heading stays as it was, and only the heading
        # of a race (the key of its message in view_flow.mjs) is made so.
        self.assertRegex(css, r"\n\.years-table \.years-race-name \{\n  overflow-wrap: anywhere;\n\}\n")
        parts = function_body(script, "raceHeadParts")
        self.assertIn('const [before = "", after = ""] = t(entry.key, { ...describedParams(entry), name: "\\u0001" }).split("\\u0001");', parts)
        self.assertIn('return [before, element("span", "years-race-name", entry.params.name), after];', parts)
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        self.assertEqual(flow.count('message("view.compare.race", '), 1)
        self.assertIn('label: message("view.compare.race", { name: race.name, date: dateText(race.day, language) }),', flow)
        self.assertNotIn("years-race-name", function_body(script, "buildShoesTable"))
        design = " ".join((STATIC_ROOT.parents[3] / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        self.assertEqual(design.count("From v2.3.0 (stage X2) the name of a race in a heading may wrap between any two characters where it does not fit (`raceHeadParts`), so that six names of thirty letters with no space fit too; the other words of the headings wrap as before."), 1)
        table = function_body(script, "buildCompareTable")
        self.assertIn('if (entry.spoken) {\n      cell.setAttribute("aria-label", describe(entry.spoken));\n    }', table)
        self.assertNotIn("spoken", function_body(script, "buildShoesTable"))
        self.assertIn('<p id="compare-count-note" class="compare-note" hidden></p>', page)
        self.assertLess(page.index('id="compare-note"'), page.index('id="compare-count-note"'))
        render = function_body(script, "renderCompare")
        for line in (
            "const countNote = ready && compare.table ? compareCountNoteKey(compareItem(), mode) : null;",
            "ui.compareCountNote.hidden = countNote === null;",
            'setText(ui.compareCountNote, countNote === null ? "" : t(countNote));',
        ):
            with self.subTest(line=line):
                self.assertIn(line, render)
        # The note is found by its id, and what the page needs of view_flow.mjs
        # is imported.
        self.assertIn('  compareCountNote: byId("compare-count-note"),\n', script)
        for name in ("compareCountNoteKey", "listEmptyMessage"):
            with self.subTest(imported=name):
                self.assertIn(f"\n  {name},\n", script.split('} from "./view_flow.mjs";')[0])
        # The list says its empty sentence by the grouping, the words of
        # view_flow.mjs (its tests), not the keys alone.
        self.assertIn('parts.push(element("p", "list-note", describe(listEmptyMessage(list.conditions, list.grain))));', function_body(script, "renderList"))
        # The design document says both rules.
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        for sentence in (
            'From v2.2.1 (stage W3) the table of a comparison names its first column by the grouping, heads the counts in English with one short word, "Count" (a screen reader hears the whole heading), says under the table what was counted, and wraps its places and headings, English at spaces and never inside a word, Japanese between its characters too (it has no spaces), so that six years or six races fit its box.',
            'From v2.2.1 (stage W3) the sentences of the list name its period by its grouping ("the week chosen"), with the same placeholders in both languages.',
        ):
            with self.subTest(sentence=sentence[:40]):
                self.assertEqual(design.count(sentence), 1)

    def test_a_calendar_compares_years_by_day_in_strips_of_its_own(self) -> None:
        # v2.2.0 N1, in the page and its script, which no test runs: the
        # calendar is the fourth way to compare years, greyed for an estimate
        # of several records a day (its reason behind an info button) and by
        # race day (in the words of what is not used); its legend stands above
        # its strips, and the table button goes back to it by its name. The
        # script uses no month for it, asks again where the month that it uses
        # changes, asks for the years by day and for their values as the years
        # do (never the one period of a race: the checker's N1-1), draws its
        # strips in their own size, and takes the keys, the pointer, a click,
        # and the focus of a strip.
        modes = by_id(self.elements, "compare-modes")
        calendar = next(element for element in self.elements if element.get("data-compare-mode") == "calendar")
        self.assertIs(calendar.parent, modes)
        self.assertEqual((calendar.get("data-i18n"), calendar.get("aria-pressed")), ("view.compare.mode.calendar", "false"))
        about = by_id(self.elements, "compare-calendar-about")
        self.assertEqual((about.get("aria-controls"), about.get("aria-expanded"), about.get("data-i18n")), ("compare-calendar-about-text", "false", "view.compare.calendar_about"))
        reason = next(element for element in self.elements if element.parent is by_id(self.elements, "compare-calendar-about-text"))
        self.assertEqual(reason.get("data-i18n"), "view.compare.calendar_only")
        for hidden in ("compare-calendar-about", "compare-calendar-about-text", "compare-off-calendar", "compare-legend", "compare-legend-line", "compare-legend-about-text", "compare-table-calendar"):
            with self.subTest(hidden=hidden):
                self.assertIn("hidden", by_id(self.elements, hidden).attributes)
        self.assertEqual(by_id(self.elements, "compare-off-calendar").get("data-i18n"), "view.compare.off_calendar")
        self.assertIs(by_id(self.elements, "compare-table-calendar").parent, by_id(self.elements, "compare-table"))
        stack = by_id(self.elements, "compare-stack")
        legend = by_id(self.elements, "compare-legend")
        panels = by_id(self.elements, "compare-panels")
        # Stage U3 of v2.2.0: the legend in a line with the button of its
        # notes at its end, and the notes under it, before the strips.
        line = by_id(self.elements, "compare-legend-line")
        notes = by_id(self.elements, "compare-legend-about-text")
        button = by_id(self.elements, "compare-legend-about")
        self.assertIs(line.parent, stack)
        self.assertIs(legend.parent, line)
        self.assertIs(button.parent, line)
        self.assertIs(notes.parent, stack)
        self.assertEqual((button.get("aria-controls"), button.get("aria-expanded"), button.get("data-i18n")), ("compare-legend-about-text", "false", "view.compare.legend_about"))
        self.assertLess(self.elements.index(legend), self.elements.index(panels))
        self.assertLess(self.elements.index(notes), self.elements.index(panels))
        for line in (
            # Greyed for an estimate and by race day; the month greyed, and kept.
            'button.disabled = (way === "cumulative" && !total) || (way === "calendar" && (!calendar || race));',
            "ui.compareCalendarAbout.hidden = calendar;",
            'ui.compareMonth.disabled = mode === "calendar";',
            'return mode === "calendar" && compareByNow() === "race" ? "rows" : mode;',
            "return compareMonthFor(compareModeNow(), state.compareMonth);",
            'if (mode === "calendar" && compareByNow() === "race") {',
            "if (!compareAsksAgain({ grain: state.compare.grain, month }, { grain, month: compareMonthNow() })) {",
            "ui.compareOffCalendar.hidden = !calendar;",
            'ui.compareTableCalendar.hidden = !compare.table || mode !== "calendar";',
            'ui.compareLegend.hidden = !ready || compare.table || mode !== "calendar";',
            # Stage U3 of v2.2.0: the notes of the legend under its info
            # button, with the legend, open as the person left them; the
            # button stays through a drawing, outside the legend.
            "ui.compareLegendLine.hidden = ui.compareLegend.hidden;",
            'ui.compareLegendAbout.setAttribute("aria-expanded", String(compare.legendAbout && !ui.compareLegend.hidden));',
            "ui.compareLegendAboutText.hidden = !compare.legendAbout || ui.compareLegend.hidden;",
            "state.compare.legendAbout = !state.compare.legendAbout;",
            "Object.assign(state.compare, { key, series: null, about: false, calendarAbout: false, legendAbout: false });",
            'ui.compareLegendAboutText.replaceChildren(...calendarNotes(steps, context.total, state.language).map((note) => element("p", "calendar-note", describe(note))));',
            # A strip a year, in its own size, its legend above them.
            "compared = data.map((entry, index) => buildCompareCalendar(compareContext, entry, lines[index], name));",
            'ui.compareAxis.hidden = compare.table || calendar;',
            "if (entry.size !== calendarSize(context)) {",
            'strip.setAttribute("aria-label", t("view.compare.calendar_label", { year: describe(entry.label), name }));',
            'ui.comparePanels.querySelector(`[data-plot="${focused}"]`)?.focus({ preventScroll: true });',
            # The keys, the pointer, a click, and the focus of a strip.
            "calendarKeyDown(event);",
            "calendarPointer(event);",
            "calendarClick(event);",
            "calendarFocus(event);",
            "moveCompareCross(slot, true, year);",
            # Drawn only from an answer of whole years by day, and the day that
            # the keys or a click chose kept in view (Codex's review of the
            # diff of N1).
            '&& (mode !== "calendar" || calendarAnswer(state.compareAnswer));',
            "renderCalendarCursor(entry, context, at, speak && entry.data[0].year === year);",
            'entry.cursor.scrollIntoView({ block: "nearest", inline: "nearest" });',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # No test runs the page (Codex's review of the diff of N1): what each
        # of its events does is held to the rules that the node tests run, by
        # the same room of a strip that its squares are drawn in; the real
        # page is checked by hand, and again for the release candidate.
        bodies = {
            name: re.search(rf"function {name}\((?:[^)]*)\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            for name in ("calendarSlotAt", "calendarPointer", "calendarClick", "calendarKeyDown", "calendarFocus", "drawCompareCalendar")
        }
        for name, lines in (
            ("calendarSlotAt", (
                "const day = calendarAt(entry.data[0].year, event.clientX - box.left - CALENDAR_LEFT, event.clientY - box.top - CALENDAR_TOP, entry.pitch);",
                "if (day === null || day < state.view.first_day || day > state.view.last_day) {",
                "return { year: entry.data[0].year, slot: daySlot(day) };",
            )),
            ("calendarPointer", ("const at = calendarSlotAt(event);", "moveCompareCross(at.slot, false);")),
            ("calendarClick", ("const at = calendarSlotAt(event);", "moveCompareCross(at.slot, true, at.year);")),
            ("calendarKeyDown", (
                "const slot = calendarMove(state.compare.cursor ?? 0, year, event.key, state.view.first_day, state.view.last_day);",
                "moveCompareCross(slot, true, year);",
                "event.preventDefault();",
            )),
            ("calendarFocus", ("speakCalendar(compareContext, state.compare.cursor, entry.data[0].year);",)),
            ("drawCompareCalendar", ("const x = CALENDAR_LEFT + place.week * pitch;", "const y = CALENDAR_TOP + place.day * pitch;")),
        ):
            body = bodies[name]
            assert body is not None, name
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body.group(1))
        request = re.search(r"async function requestCompare\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        body = request.group(1)
        self.assertIn("const month = compareMonthNow();", body)
        self.assertIn(": years.map((year) => seriesPayload([key], compareRange(year, month), grain));", body)
        self.assertIn('callApi("/api/view/series", seriesPayload([key], "all", by === "race" ? "year" : compareValueGrain(month))),', body)
        # The one period of a span only for a race.
        self.assertEqual(body.count("RANGE_GRAIN"), 1)
        self.assertIn("seriesPayload([key], raceRange(race.day, weeks), RANGE_GRAIN)", body)
        # The colors of its steps are the six steps of one hue (from stage L3,
        # apart from the colors of the lines of the years); a day without a
        # recorded activity an outline of var(--sub) (6.36 : 1 and 7.5 : 1);
        # in forced colors, one color by opacity; the strip takes the pointer.
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        for step in range(1, 7):
            with self.subTest(step=step):
                self.assertRegex(view_css, rf"\.calendar-cell\.s{step} \{{\s*fill: var\(--y{step}\);\s*\}}")
        self.assertRegex(view_css, r"\.calendar-cell\.zero \{\s*fill: none;\s*stroke: var\(--sub\);\s*stroke-width: 1\.5;\s*\}")
        self.assertRegex(view_css, r"\.calendar svg \{[^}]*pointer-events: none;")
        # v2.2.0 N2: the value of the day chosen stays in the column at the
        # left of its strip, whole where it fits (the English reading of a day
        # without a recorded activity ran over the days of the week): one block
        # no wider than the column that wraps whatever the reading of a panel
        # does, and no rule of a calendar makes it nowrap again (Codex's review
        # of the diff of N2).
        self.assertRegex(view_css, r"\.calendar-side \.calendar-read strong \{\s*display: inline-block;\s*max-width: 100%;\s*white-space: normal;\s*\}")
        for selector, body in re.findall(r"([^{}]*calendar[^{}]*)\{([^{}]*)\}", view_css):
            with self.subTest(rule=selector.strip()):
                self.assertNotIn("nowrap", body)
        forced = view_css[view_css.index("@media (forced-colors: active) {") :]
        self.assertRegex(forced, r"\.calendar-cell\.s6 \{\s*fill: CanvasText;\s*\}")
        for step, opacity in ((1, "0.15"), (2, "0.3"), (3, "0.45"), (4, "0.6"), (5, "0.8")):
            with self.subTest(forced=step):
                self.assertRegex(forced, rf"\.calendar-cell\.s{step} \{{\s*fill-opacity: {opacity};\s*\}}")
        self.assertRegex(forced, r"\.calendar-cell\.zero \{\s*stroke: CanvasText;\s*\}")

    def test_the_info_buttons_of_comparing_years_start_closed(self) -> None:
        # Each info button of comparing years (what a running total is, why a
        # calendar cannot be, and the legend of a calendar) says aria-expanded
        # from its state, which a comparison begins with as false; without it
        # the first drawing would say "undefined" (Codex's review of the diff
        # of U3). No test runs the page: the state is held to the function
        # that begins a comparison, and the real page was checked.
        from tests.test_gui_view_save import function_body

        script = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        begin = function_body(script, "enterCompare")
        for name in ("about", "calendarAbout", "legendAbout"):
            with self.subTest(name=name):
                self.assertIn(f"\n    {name}: false,\n", begin)

    def test_the_list_of_a_period_is_named_and_goes_back_to_its_chart(self) -> None:
        # Stage M3 of v2.2.0: a chart of the activities with values says by a
        # hidden description how Enter opens the list of a period; the list
        # is named by its heading, which takes the focus by the keyboard; its
        # table has a caption, heads that order it (aria-sort, the arrow
        # hidden), and rows named by their date and time, a value that an
        # activity does not have said in words; Esc and its button close it,
        # and the focus goes back to its chart. A polite region of its own
        # says what it has, apart from the region of the cross line.
        hint = by_id(self.elements, "list-hint")
        self.assertIn("visually-hidden", str(hint.get("class")).split())
        self.assertEqual(hint.get("data-i18n"), "view.list.hint")
        announcer = by_id(self.elements, "list-announcer")
        self.assertEqual(announcer.get("aria-live"), "polite")
        self.assertIn("visually-hidden", str(announcer.get("class")).split())
        for line in (
            'entry.plot.setAttribute("aria-describedby", "list-hint");',
            'entry.plot.removeAttribute("aria-describedby");',
            'listBox.setAttribute("aria-labelledby", "list-title");',
            "title.tabIndex = -1;",
            'const caption = element("caption", "visually-hidden", titleText);',
            'wrap.setAttribute("role", "region");\n  wrap.setAttribute("aria-labelledby", "list-title");',
            'cell.setAttribute("aria-sort", list.sort.descending ? "descending" : "ascending");',
            'arrow.setAttribute("aria-hidden", "true");',
            'cell.scope = "row";',
            'dash.setAttribute("aria-hidden", "true");\n        cell.append(dash, element("span", "visually-hidden", t("view.no_value")));',
            # The keys that a chart leaves come after it (stage X12d3 of v2.3.0).
            '    }\n    if (event.key === "Escape" && listBox?.contains(event.target)) {',
            '} else if (event.key === "Escape" && state.list !== null && event.target.dataset.key === state.list.key) {',
            '} else if ((event.key === "Enter" || event.key === " ") && event.target.classList.contains("listable")) {',
            "drawn.find((entry) => entry.key === list.key)?.plot?.focus();",
            # Its period first, so that another period of as many
            # activities is said too (Codex's review of the diff).
            'setText(ui.listAnnouncer, t("view.list.spoken", { title: describe(listTitle(state.answer.periods[list.index], list.grain, state.language)), text }));',
            "listSay(list, describe(listFrom(list.key, answer.total, state.language)));",
            # The table keeps where it was scrolled to, sideways too.
            "table.scrollLeft = scrolled.left;",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # The table of the list and that of the points (stage O1 of v2.2.0)
        # each hide the arrow of their order and name their rows: held to
        # the body of each, as one could keep the lines of the other (the
        # partial guard of O1).
        for name in ("buildListTable", "buildPlotTable"):
            body = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert body is not None
            for line in ('arrow.setAttribute("aria-hidden", "true");', 'cell.scope = "row";'):
                with self.subTest(table=name, line=line):
                    self.assertIn(line, body.group(1))
        # The heading takes the focus by the keyboard only: a click keeps it
        # on the chart, whose arrow keys move the cross line.
        self.assertIn("openList(event.target.dataset.key, state.cursor ?? (state.answer?.periods.length ?? 1) - 1, true);", self.script)
        self.assertIn("openList(entry.key, index, false);", self.script)
        # The chart takes the pointer itself, so that a drawing made again
        # during a click does not lose it (the real page in English at
        # 1366x650).
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertRegex(view_css, r"\.plot svg \{[^}]*pointer-events: none;")
        # A head of a column breaks between its words only.
        self.assertRegex(view_css, r"\.list-sort \{[^}]*overflow-wrap: normal;")

    def test_two_items_are_plotted_in_the_place_of_the_panels(self) -> None:
        # v2.2.0 O1, in the page and its script, which no test runs: the menu
        # of the other views in the row above the panels takes the keys of a
        # menu also with one item (the checker's review of the plan of O1);
        # the points take the place of the panels as a comparison does, with
        # the period and the activity types of the page, which then ask for
        # the points and leave the panels to ask again on the way back
        # (Codex's review of the plan of O1); the words that no relation is
        # shown always show under them; an item of one list is disabled in
        # the other, and says why; the answers are one generation, a ticket
        # opened again once, an output that stops closes them; the pointer,
        # the keys, and the table go by the rules that the node tests run.
        caveat = by_id(self.elements, "caveat")
        button = by_id(self.elements, "other-views")
        menu = by_id(self.elements, "other-views-menu")
        item = by_id(self.elements, "other-plot")
        self.assertIn(caveat, button.ancestors())
        self.assertEqual((button.get("aria-haspopup"), button.get("aria-expanded"), button.get("aria-controls")), ("menu", "false", "other-views-menu"))
        self.assertEqual((menu.get("role"), menu.get("aria-labelledby")), ("menu", "other-views"))
        self.assertIn("hidden", menu.attributes)
        self.assertIs(item.parent, menu)
        self.assertEqual((item.get("role"), item.get("tabindex"), item.get("data-i18n")), ("menuitem", "-1", "view.other.plot"))
        plot = by_id(self.elements, "plot")
        self.assertIn("hidden", plot.attributes)
        self.assertEqual(plot.get("aria-labelledby"), "plot-title")
        for name in ("plot-x", "plot-y", "plot-table", "plot-back", "plot-count", "plot-loading", "plot-stop", "plot-body", "plot-none", "plot-announcer", "plot-cut", "plot-caveat"):
            with self.subTest(element=name):
                self.assertIn(plot, by_id(self.elements, name).ancestors())
        self.assertEqual(by_id(self.elements, "plot-announcer").get("aria-live"), "polite")
        self.assertEqual(by_id(self.elements, "plot-off").get("data-i18n"), "view.plot.off")
        # The words of no relation are never hidden, nor touched by the script.
        words = by_id(self.elements, "plot-caveat")
        self.assertEqual(words.get("data-i18n"), "view.plot.caveat")
        self.assertNotIn("hidden", words.attributes)
        self.assertNotIn("plot-caveat", self.script)
        for line in (
            # The menu and its keys.
            'ui.otherViews.addEventListener("keydown", otherButtonKey);',
            'ui.otherMenu.addEventListener("keydown", otherMenuKey);',
            'if (event.key === "ArrowDown") {\n    event.preventDefault();\n    setOtherViews(true, "first");',
            'if (event.key === "Escape") {\n    event.preventDefault();\n    setOtherViews(false, "button");',
            'ui.otherViews.setAttribute("aria-expanded", String(state.otherOpen));',
            # In the place of the panels; the period and the types ask for what shows.
            "function apart() {\n  return comparing() || otherShown();\n}",
            "function shownAnswer() {\n  return plotting() ? state.plotAnswer : spreading() ? state.spreadAnswer : shoesShown() ? state.shoesAnswer : state.answer;\n}",
            # And the changes since the output before (stage X7 of v2.3.0).
            "function otherShown() {\n  return plotting() || spreading() || shoesShown() || changesShown();\n}",
            "function requestShown() {\n  if (otherShown()) {\n    state.panelsStale = true;\n    requestPlot();\n    requestSpread();\n    requestShoes();\n  } else {\n    requestSeries();\n  }\n}",
            "  const answer = shownAnswer();\n  const range = shiftedRange(answer?.start, answer?.end, direction, state.view?.first_day, state.view?.last_day);",
            "  rememberItems(true);\n  requestShown();\n  requestCompare();\n}",
            "button.disabled = !viewing || otherShown() || (grains !== null && !grains.includes(button.dataset.grain));",
            # One generation of answers, a ticket opened again once, an output that stops.
            'const answer = await callApi("/api/view/points", payload);\n    if (seq !== state.plotSeq) {\n      return;\n    }',
            "        state.plotLoading = false;\n        requestPlot(false);\n        return;",
            "    requestSeries();\n    requestCompare();\n    requestPlot();",
            "      if (plotPairOf(state.plotPair, answer.items) === null) {\n        state.plot = null;",
            # The lists, the settings, and the rules of the page.
            "option.disabled = item.key === other;",
            'const taken = axis === "x" ? "view.plot.taken_y" : "view.plot.taken_x";',
            "    plot: { x: state.plotPair.x, y: state.plotPair.y },",
            "    state.plotPair = plotPairToOpen(state.settings);",
            "return nearestPoint(context.shapes.places, event.clientX - box.left, event.clientY - box.top, PLOT_REACH);",
            "const next = plotMove(state.plot?.chosen ?? null, plotContext.answer.points.length, event.key);",
            "const rows = sortedListRows(drawn.points, state.plot.sort, typeName, state.language);",
            "const shapes = pointShapes(",
            # After the review of the diff by Codex: an output that opens drops
            # the answers of the points on their way; the order of the table
            # goes with an item changed; the focus stays, also on a head of
            # the table; the chart takes the room that its head leaves.
            "  const seq = ++state.openSeq;\n  state.compareSeq += 1;\n  // And those of the points, before they could open the output before\n  // again (Codex's review of the diff of O1).\n  state.plotSeq += 1;",
            'state.plot.sort = plotSortAfter(state.plot.sort, ["when", "type", pair.x, pair.y]);',
            "column !== null ? `button[data-action=\"plot-sort\"][data-column=\"${column}\"]` : focused?.closest(\".plot-points\") ? \".plot-points\"",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # Lines that other parts of the page have too, held to the body of
        # each function, as one could keep the lines of another (the
        # checker's review of the partial guard of O1): the rows of a table
        # added 400 at a time (those of a panel had no test before), the
        # reading of a point that the announcer says, the caption and the
        # heads of the table of the points, and its answers as those of the
        # list; from P1, the way back to the panels and the room of the
        # chart, which a distribution has too.
        held = {
            "buildTable": (
                "for (const row of rows.slice(shownRows, shownRows + TABLE_ROWS)) {",
                "shownRows = Math.min(rows.length, shownRows + TABLE_ROWS);",
            ),
            "buildPlotTable": (
                "for (const row of rows.slice(shownRows, shownRows + TABLE_ROWS)) {",
                "shownRows = Math.min(rows.length, shownRows + TABLE_ROWS);",
                'const caption = element("caption", "visually-hidden", t("view.plot.table_caption"));',
                'cell.scope = "col";',
            ),
            "buildPlotChart": ('read.setAttribute("aria-hidden", "true");',),
            "leavePlot": ("  if (state.panelsStale) {\n    state.panelsStale = false;\n    requestSeries();\n  }",),
            "renderPlotBody": (
                "const room = chart.chart.getBoundingClientRect();",
                # And of the same pair only (Codex's review of the diff of P1).
                "plotContext.answer !== null && plotContext.pair === `${state.plotPair.x} ${state.plotPair.y}`) {",
                "plotContext = { ...wanted, pair: drawn === null ? null : `${state.plotAsked.x} ${state.plotAsked.y}`, shapes: null };",
            ),
        }
        for name, lines in held.items():
            body = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert body is not None
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body.group(1))
        request = re.search(r"async function requestPlot\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        self.assertIn("const seq = ++state.plotSeq;", request.group(1))
        self.assertIn('error.code === "VIEW_NOT_OPEN" && again && state.target !== null', request.group(1))
        self.assertIn("requestPlot(false);", request.group(1))
        self.assertIn("OUTPUT_STOPS.includes(error.code)", request.group(1))
        self.assertEqual(request.group(1).count("if (seq !== state.plotSeq) {\n      return;\n    }"), 2)
        # An output that stops closes a distribution too (stage P1), also
        # where the summary asks (stage Q1).
        # With the view by shoes: the seven places, and its own request (stage
        # S1 of v2.2.0).
        # Each with the changes since the output before too, and their own
        # request one more (stage X7 of v2.3.0).
        self.assertEqual(self.script.count("      state.compare = null;\n      state.plot = null;\n      state.spread = null;\n      state.shoes = null;\n      state.changes = null;\n"), 9)
        self.assertRegex((STATIC_ROOT / "view.css").read_text(encoding="utf-8"), r"\.plot-head \.plot-read \{[^}]*white-space: normal;")
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertRegex(view_css, r"\.plot-dot \{\s*fill: var\(--d1\);\s*stroke: var\(--surface\);\s*stroke-width: 1;\s*\}")
        self.assertRegex(view_css, r"\.plot-dot\.plot-chosen \{\s*stroke: var\(--accent\);\s*stroke-width: 2\.5;\s*\}")
        self.assertRegex(view_css, r"\.plot-points svg \{[^}]*pointer-events: none;")
        forced = view_css[view_css.rindex("@media (forced-colors: active) {") :]
        self.assertRegex(forced, r"\.plot-dot \{\s*fill: CanvasText;\s*stroke: Canvas;\s*\}")
        self.assertRegex(forced, r"\.plot-dot\.plot-chosen \{\s*fill: Highlight;\s*stroke: CanvasText;\s*\}")

    def test_a_distribution_takes_the_place_of_the_panels(self) -> None:
        # v2.2.0 P1, in the page and its script, which no test runs: the
        # distribution is the second item of the menu of the other views; it
        # takes the place of the panels as the points do, with the period and
        # the activity types of the page, which then ask for it and leave the
        # panels to ask again on the way back (Codex's review of the plan of
        # P1); its answers are one generation; its ranges are placed by their
        # order, the ends written from the numbers of the answer, and no words
        # of a relation under them (the checker's review of the plan of P1).
        # The lines that the points have too are held to the body of each
        # function (the partial guard of O1).
        menu = by_id(self.elements, "other-views-menu")
        item = by_id(self.elements, "other-spread")
        self.assertEqual([element.get("id") for element in self.elements if element.parent is menu], ["other-plot", "other-spread", "other-shoes", "other-changes"])
        self.assertEqual((item.get("role"), item.get("tabindex"), item.get("data-i18n")), ("menuitem", "-1", "view.other.spread"))
        spread = by_id(self.elements, "spread")
        self.assertIn("hidden", spread.attributes)
        self.assertEqual(spread.get("aria-labelledby"), "spread-title")
        for name in ("spread-item", "spread-table", "spread-back", "spread-count", "spread-loading", "spread-stop", "spread-body", "spread-none", "spread-announcer", "spread-wide", "spread-faster"):
            with self.subTest(element=name):
                self.assertIn(spread, by_id(self.elements, name).ancestors())
        self.assertEqual(by_id(self.elements, "spread-announcer").get("aria-live"), "polite")
        self.assertEqual(by_id(self.elements, "spread-off").get("data-i18n"), "view.spread.off")
        faster = by_id(self.elements, "spread-faster")
        self.assertEqual(faster.get("data-i18n"), "view.spread.faster_left")
        self.assertIn("hidden", faster.attributes)
        self.assertEqual([element.get("data-i18n") for element in self.elements if spread in element.ancestors() and "caveat" in (element.get("data-i18n") or "")], [])
        held = {
            "enterSpread": ('listChanged("spread");', "state.spread = { table: false, chosen: null };", "ui.spreadItem.focus();", "requestSpread();"),
            "leaveSpread": ("state.spreadSeq += 1;", "ui.otherViews.focus();", "  if (state.panelsStale) {\n    state.panelsStale = false;\n    requestSeries();\n  }"),
            "chooseSpreadItem": ("if (spreadItemOf(key, state.view.items) !== key) {", "rememberItems(true);", "requestSpread();"),
            "spreadAnswerNow": ("asked.item === state.spreadItem",),
            "renderSpread": (
                "ui.spreadOff.hidden = spread === null;",
                "describe(spreadCount(drawn, state.language))",
                "spreadWide(state.spreadAsked.item, drawn, state.language)",
                'ui.spreadFaster.hidden = drawn === null || state.spreadAsked.item !== "pace";',
            ),
            "renderSpreadBody": (
                'ui.spreadBody.classList.toggle("waiting", state.spreadLoading);',
                'focused?.closest(".spread-bars") ? ".spread-bars"',
                "const room = chart.chart.getBoundingClientRect();",
                # Codex's review of the diff of P1: what stays while an answer
                # is on its way is of the same item only.
                "spreadContext.answer !== null && spreadContext.item === state.spreadItem) {",
                "spreadContext = { ...wanted, item: drawn === null ? null : state.spreadAsked.item, shapes: null };",
            ),
            "buildSpreadChart": ('read.setAttribute("aria-hidden", "true");', "chart.tabIndex = 0;", 'chart.setAttribute("role", "img");', 't("view.spread.label", { item: t(itemKey(key)) })'),
            "drawSpreadBars": ("spreadShapes(drawn.counts, drawn.first, { width, height })", "if (drawn.counts[index] > 0) {", "spreadEndWords(key, drawn, end, state.language)", 'upName.textContent = t("view.spread.head_count");'),
            "renderSpreadChosen": ("Math.max(SPREAD_CHOSEN_WIDTH, bar.x1 - bar.x0)", "setText(ui.spreadAnnouncer, describe(reading));"),
            "spreadKeyDown": ("spreadMove(state.spread?.chosen ?? null, spreadContext.answer.counts.length, event.key)",),
            "buildSpreadTable": ('const caption = element("caption", "visually-hidden", t("view.spread.table_caption"));', 'rangeHead.scope = "col";', 'countHead.scope = "col";', 'range.scope = "row";'),
            "renderOtherViews": ("ui.otherSpread.disabled = spreadItemOf(state.spreadItem, state.view?.items) === null;",),
            "scheduleRedraw": ("renderSpreadBody(spreadAnswerNow());",),
            "render": ("renderSpread(live);",),
        }
        for name, lines in held.items():
            body = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert body is not None
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body.group(1))
        request = re.search(r"async function requestSpread\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        for line in (
            "const seq = ++state.spreadSeq;",
            'const answer = await callApi("/api/view/spread", payload);',
            'error.code === "VIEW_NOT_OPEN" && again && state.target !== null',
            "requestSpread(false);",
            "OUTPUT_STOPS.includes(error.code)",
            "      state.spread = null;\n      state.shoes = null;\n      state.changes = null;\n      state.stop = { code: error.code, detail: error.detail };",
        ):
            with self.subTest(line=line):
                self.assertIn(line, request.group(1))
        self.assertEqual(request.group(1).count("if (seq !== state.spreadSeq) {\n      return;\n    }"), 2)
        opened = re.search(r"async function openOutput\(target, focus = false, auto = null\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert opened is not None
        for line in (
            "state.spreadSeq += 1;",
            "const key = spreadItemOf(state.spreadItem, answer.items);\n      if (key === null) {\n        state.spread = null;\n      } else {\n        state.spreadItem = key;\n        state.spread.chosen = null;\n      }",
            "requestSpread();",
        ):
            with self.subTest(line=line):
                self.assertIn(line, opened.group(1))
        for line in (
            "    spread: state.spreadItem,",
            "    state.spreadItem = spreadItemToOpen(state.settings);",
            "    watcher.observe(ui.spreadBody);",
            'ui.otherSpread.addEventListener("click", () => {\n    setOtherViews(false);\n    enterSpread();\n  });',
            'ui.spreadItem.addEventListener("change", () => chooseSpreadItem(ui.spreadItem.value));',
            'ui.spreadBack.addEventListener("click", leaveSpread);',
            'ui.spreadBody.addEventListener("keydown", spreadKeyDown);',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertRegex(view_css, r"\.spread-bar \{\s*fill: var\(--d1\);\s*\}")
        self.assertRegex(view_css, r"\.spread-chosen \{\s*fill: none;\s*stroke: var\(--accent\);\s*stroke-width: 2\.5;\s*\}")
        forced = view_css[view_css.rindex("@media (forced-colors: active) {") :]
        self.assertRegex(forced, r"\.spread-bar \{\s*fill: CanvasText;\s*\}")
        self.assertRegex(forced, r"\.spread-chosen \{\s*stroke: Highlight;\s*\}")

    def test_the_view_by_shoes_takes_the_place_of_the_panels(self) -> None:
        # v2.2.0 S1, in the page and its script, which no test runs: the third
        # item of the menu of the other views, which says under its name why
        # it cannot be chosen; a bar as that of the distribution; a row a pair
        # of shoes in a stack that scrolls, over one time axis across the
        # years (Codex's review of the plan of S1), the name cut before what
        # tells it apart; the keys and the pointer move one cross line; its
        # answers are one generation, which another output moves on; its
        # tables; the answers of the numbers say again whether it has shoes.
        menu = by_id(self.elements, "other-views-menu")
        item = by_id(self.elements, "other-shoes")
        self.assertIs(item.parent, menu)
        self.assertEqual((item.get("role"), item.get("tabindex"), item.get("class")), ("menuitem", "-1", "with-why"))
        name, why = [element for element in self.elements if element.parent is item]
        self.assertEqual((name.get("data-i18n"), why.get("id"), why.get("class")), ("view.other.shoes", "other-shoes-why", "menu-why"))
        self.assertIn("hidden", why.attributes)
        shoes = by_id(self.elements, "shoes")
        self.assertIn("hidden", shoes.attributes)
        self.assertEqual(shoes.get("aria-labelledby"), "shoes-title")
        title = by_id(self.elements, "shoes-title")
        self.assertEqual((title.get("tabindex"), title.get("data-i18n")), ("-1", "view.shoes.title"))
        for name in ("shoes-table", "shoes-save", "shoes-back", "shoes-count", "shoes-loading", "shoes-stop", "shoes-stack", "shoes-panels", "shoes-axis", "shoes-announcer", "shoes-none", "shoes-notes"):
            with self.subTest(element=name):
                self.assertIn(shoes, by_id(self.elements, name).ancestors())
        stack = by_id(self.elements, "shoes-stack")
        self.assertEqual(stack.get("class"), "stack compare-stack shoes-stack")
        self.assertEqual([element.get("id") for element in self.elements if element.parent is stack], ["shoes-panels", "shoes-axis", "shoes-announcer"])
        self.assertEqual(by_id(self.elements, "shoes-panels").get("class"), "panels")
        self.assertEqual(by_id(self.elements, "shoes-announcer").get("aria-live"), "polite")
        loading = by_id(self.elements, "shoes-loading")
        self.assertEqual((loading.get("role"), loading.get("aria-live")), ("status", "polite"))
        self.assertEqual(by_id(self.elements, "shoes-table").get("aria-pressed"), "false")
        self.assertEqual(by_id(self.elements, "shoes-off").get("data-i18n"), "view.shoes.off")
        held = {
            "enterShoes": ("if (state.view === null || comparing() || shoesWhy(state.shoesAvailable) !== null) {", 'listChanged("shoes");', "state.shoes = { table: false, cursor: null };", "ui.shoesTitle.focus();", "requestShoes();"),
            "leaveShoes": ("state.shoesSeq += 1;", "ui.otherViews.focus();", "  if (state.panelsStale) {\n    state.panelsStale = false;\n    requestSeries();\n  }"),
            "shoesPayload": ("period: periodRequest(state.period, state.range),", "types: typesRequest(state.counted, state.view.types),"),
            "shoesShown": ("return state.shoes !== null && state.view !== null;",),
            "renderShoes": (
                "ui.shoesOff.hidden = shoes === null;",
                "ui.shoesTable.disabled = drawn === null || !drawn.shoes.length;",
                'ui.shoesTable.setAttribute("aria-pressed", String(shoes.table));',
                'setText(ui.shoesLoading, state.shoesLoading ? t("view.loading") : "");',
                "ui.shoesStop.hidden = state.shoesStop === null;",
                "describe(shoesCount(drawn))",
                "ui.shoesNone.hidden = drawn === null || drawn.shoes.length > 0;",
                "shoesNotes(drawn).map(describe)",
                'ui.shoesNotes.replaceChildren(...notes.map((note) => element("p", "compare-note", note)));',
            ),
            "renderShoesBody": (
                "const periods = periodDays(drawn.periods);",
                'shown("dist", value)',
                "shared: extent(lines)",
                "ui.shoesPanels.replaceChildren(...buildShoesTables(drawn));",
                "plotWatcher?.observe(entry.plot);",
            ),
            "buildShoeRow": (
                'element("section", "panel-view compare-row shoe-row")',
                "const headingId = `shoe-${index}`;",
                'section.setAttribute("aria-labelledby", headingId);',
                'heading.append(element("span", "shoe-own", describe(name)));',
                'heading.append(element("span", "shoe-added", describe(added)));',
                "plot.tabIndex = 0;",
                'plot.setAttribute("role", "img");',
                't("view.shoes.row_label", { shoe: describe(shoeName(shoe, state.language)) })',
            ),
            "drawShoePlot": (
                "periods: context.periods, start: context.start, end: context.end, width, height, total: true, shared: context.shared",
                'appendScale(svg, "dist", shapes, width - PLOT_RIGHT);',
                'appendMarks(svg, shapes.lines[0], "c1", null, { outlined: true });',
            ),
            "renderShoesCharts": ("drawTimeAxis(shoesContext.start, shoesContext.end, width, ui.shoesAxis);",),
            "moveShoesCross": ("describe(shoesRead(answer.periods[at], answer.shoes[entry.index].values[at], state.language))", "if (entry.index === row) {", "setText(ui.shoesAnnouncer,"),
            "shoesKeyDown": ("const moves = { ArrowLeft: state.shoes.cursor - 1, ArrowRight: state.shoes.cursor + 1, Home: 0, End: last };", "event.preventDefault();", "moveShoesCross(moves[event.key], Number(plot.dataset.plot));"),
            "shoesPointer": ("nearestPeriod(shoesContext.periods, entry.shapes.scale, event.clientX - plot.getBoundingClientRect().left)",),
            "buildShoesTables": ('months, "shoes-months"),',),
            "buildShoesTable": ('kind === null ? "panel-view compare-table table" : `panel-view compare-table table ${kind}`', 'element("caption", "visually-hidden", caption)', 'cell.scope = "col";', 'first.scope = "row";', 'wrap.setAttribute("role", "region");'),
            "renderOtherViews": ("const why = shoesWhy(state.shoesAvailable);", 'ui.otherShoes.setAttribute("aria-disabled", String(why !== null));', "ui.otherShoesWhy.hidden = why === null;", 'setText(ui.otherShoesWhy, why === null ? "" : t(why));'),
            "saveButton": ("shoes: ui.shoesSave }[view];",),
            "saveShoesTarget": ("stopped: state.shoesStop !== null,", "loading: state.shoesLoading,", "answerTypes: state.shoesAsked?.types ?? null,"),
            "renderSave": ('  for (const each of ["panels", "compare", "plot", "spread", "shoes"]) {\n    saveButton(each).setAttribute("aria-expanded",',),
            "scheduleRedraw": ("renderShoesBody(state.shoesAnswer);",),
            "render": ("renderShoes(live);",),
            "drawTimeAxis": ("place.replaceChildren();", "place.append(svg);"),
        }
        for function, lines in held.items():
            body = re.search(rf"function {function}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert body is not None, function
            for line in lines:
                with self.subTest(function=function, line=line):
                    self.assertIn(line, body.group(1))
        request = re.search(r"async function requestShoes\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        for line in (
            "const seq = ++state.shoesSeq;",
            'const answer = await callApi("/api/view/shoes", payload);',
            "const asked = ++state.availableAsks;",
            "    if (answer.available && asked > state.availableFrom) {\n      state.shoesAvailable = answer.available;\n      state.availableFrom = asked;\n    }",
            'error.code === "VIEW_NOT_OPEN" && again && state.target !== null',
            "requestShoes(false);",
            "OUTPUT_STOPS.includes(error.code)",
        ):
            with self.subTest(line=line):
                self.assertIn(line, request.group(1))
        self.assertEqual(request.group(1).count("if (seq !== state.shoesSeq) {\n      return;\n    }"), 2)
        opened = re.search(r"async function openOutput\(target, focus = false, auto = null\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert opened is not None
        for line in (
            "state.shoesSeq += 1;",
            "    state.shoesAvailable = answer.shoes ?? null;\n    state.availableFrom = ++state.availableAsks;",
            "      state.shoesAnswer = null;\n      state.shoesAsked = null;\n      state.shoesStop = null;",
            "      if (shoesWhy(state.shoesAvailable) !== null) {\n        state.shoes = null;\n      } else {\n        state.shoes.cursor = null;\n      }",
            "requestShoes();",
        ):
            with self.subTest(line=line):
                self.assertIn(line, opened.group(1))
        # The answers of the numbers say again whether the output has shoes
        # (Codex's review of the plan of S1), unless an answer asked for after
        # them said it (Codex's review of the diff of S1).
        series = re.search(r"async function requestSeries\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert series is not None
        self.assertIn("const asked = ++state.availableAsks;", series.group(1))
        self.assertIn("    if (answer.shoes && asked > state.availableFrom) {\n      state.shoesAvailable = answer.shoes;\n      state.availableFrom = asked;\n    }", series.group(1))
        for line in (
            'ui.otherShoes.addEventListener("click", () => {\n    // An item that cannot be chosen does nothing, and the menu stays.\n    if (shoesWhy(state.shoesAvailable) !== null) {\n      return;\n    }\n    setOtherViews(false);\n    enterShoes();\n  });',
            'ui.shoesTable.addEventListener("click", () => {\n    if (state.shoes !== null) {\n      state.shoes.table = !state.shoes.table;\n      render();\n    }\n  });',
            'ui.shoesBack.addEventListener("click", leaveShoes);',
            'ui.shoesPanels.addEventListener("pointermove", shoesPointer);',
            'ui.shoesPanels.addEventListener("keydown", shoesKeyDown);',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        # A long name is cut, what tells it apart never (the checker's review
        # of the handling of Codex's review of the plan of S1).
        self.assertRegex(view_css, r"\.shoe-row \.panel-name\.shoe-name \{\s*display: flex;\s*min-width: 0;\s*overflow: hidden;\s*\}")
        self.assertRegex(view_css, r"\.shoe-own \{\s*min-width: 0;\s*overflow: hidden;\s*text-overflow: ellipsis;\s*white-space: nowrap;\s*\}")
        self.assertRegex(view_css, r"\.shoe-added \{\s*flex: none;\s*white-space: pre;\s*\}")
        self.assertRegex(view_css, r"\.other-menu button\.with-why \{\s*display: flex;\s*flex-direction: column;\s*align-items: flex-start;\s*\}")
        # Its reason stays on one line, never broken inside a word at the width
        # of the menu (S1's item 20, stage S2; measured on the real page).
        self.assertRegex(view_css, r"\.menu-why \{\s*font-size: 0\.8rem;\s*color: var\(--sub\);\s*white-space: nowrap;\s*\}")
        # An item that cannot be chosen stays in the way of the keys, and says
        # why (Codex's review of the diff of S1).
        self.assertNotIn("ui.otherShoes.disabled", self.script)
        self.assertRegex(view_css, r'\.other-menu button\[aria-disabled="true"\] \{\s*color: var\(--dis\);\s*cursor: not-allowed;\s*\}')
        self.assertRegex(view_css, r'@media \(forced-colors: active\) \{\s*\.other-menu button\[aria-disabled="true"\] \{\s*color: GrayText;\s*\}\s*\}')
        # The table by month keeps its months at the left (the checker's
        # review of the diff of S1).
        self.assertRegex(view_css, r"\.shoes-months \.panel-table \.t tbody th,\s*\.shoes-months \.panel-table \.t thead th:first-child \{\s*position: sticky;\s*left: 0;\s*\}")
        self.assertRegex(view_css, r"\.shoes-months \.panel-table \.t tbody th \{\s*background: var\(--surface\);\s*\}")
        self.assertRegex(view_css, r"\.shoes-months \.panel-table \.t thead th:first-child \{\s*z-index: 2;\s*\}")

    def test_the_summary_is_a_window_of_the_items_of_the_panels(self) -> None:
        # v2.2.0 Q1, in the page and its script, which no test runs: the
        # summary opens from the row above the panels, after the other views,
        # as the window of the marks does (its title takes the focus, the
        # close button and Escape go back to its button, a press outside does
        # not close it), and one of the two windows shows at a time; its
        # table is in a region of its own that the keys scroll (Codex's review
        # of the plan of Q1, 11). It shows and asks only with panels, outside
        # a comparison of years, another view, and the graphs only, and asks
        # once again where it shows again (Codex's 7, the checker's answer 5);
        # it asks again where the ticket, the period, the types, or the items
        # change, its answers are one generation, the table is empty while an
        # answer is on its way (the checker's answer 4), and a stop of its own
        # shows in it, the panels kept (Codex's 9).
        row = by_id(self.elements, "caveat")
        button = by_id(self.elements, "recap-open")
        children = [element.get("id") or element.get("class") for element in self.elements if element.parent is row]
        self.assertEqual(children[children.index("other-views") + 1], "recap-open")
        self.assertEqual(
            (button.tag, button.get("class"), button.get("aria-expanded"), button.get("aria-controls"), button.get("data-i18n")),
            ("button", "small", "false", "recap-pop", "view.recap.button"),
        )
        window = by_id(self.elements, "recap-pop")
        self.assertIs(window.parent, row)
        self.assertEqual((window.get("role"), window.get("aria-labelledby")), ("dialog", "recap-pop-title"))
        self.assertIn("hidden", window.attributes)
        self.assertEqual(by_id(self.elements, "recap-pop-title").get("tabindex"), "-1")
        self.assertEqual(by_id(self.elements, "recap-pop-title").get("data-i18n"), "view.recap.title")
        self.assertEqual(by_id(self.elements, "recap-pop-close").get("data-i18n"), "help.close")
        loading = by_id(self.elements, "recap-loading")
        self.assertEqual((loading.get("role"), loading.get("aria-live")), ("status", "polite"))
        body = by_id(self.elements, "recap-body")
        self.assertEqual((body.get("tabindex"), body.get("role"), body.get("aria-labelledby")), ("0", "region", "recap-pop-title"))
        self.assertIn("hidden", by_id(self.elements, "recap-stop").attributes)
        for name in ("recap-pop-title", "recap-pop-close", "recap-days", "recap-loading", "recap-stop", "recap-stop-heading", "recap-stop-lines", "recap-stop-code", "recap-body", "recap-difference-note", "recap-cut"):
            with self.subTest(element=name):
                self.assertIn(window, by_id(self.elements, name).ancestors())
        notes = [element.get("data-i18n") for element in self.elements if window in element.ancestors() and element.tag == "p" and element.get("data-i18n")]
        self.assertEqual(notes, ["view.recap.note", "view.recap.records_note"])
        held = {
            "recapShowable": ("return viewing && !apart() && state.items.length > 0 && !state.full;",),
            # From T1 of v2.2.0, the conditions on the activities too.
            "recapKey": ("JSON.stringify([state.view?.view ?? null, periodRequest(state.period, state.range), typesRequest(state.counted, state.view?.types), state.items, conditionsKey(state.conditions)])",),
            "openRecap": (
                "state.recapAsked = null;",
                "  if (open && state.marksOpen) {\n    state.marksOpen = false;\n    state.markAsk = null;\n    editMark(null, false);\n  }",
                "ui.recapTitle.focus();",
                "ui.recapOpen.focus();",
            ),
            # The window of the saving, at the same place, closes too (stage R1).
            # The window of the laps too (stage X10 of v2.3.0).
            "openMarks": ("  if (open) {\n    // One window opens under the right end of the row at a time (stage Q1).\n    state.recapOpen = false;\n    state.saveOpen = false;\n    dropLaps();\n  }",),
            # A low window keeps the heads and two rows or so of its table,
            # and scrolls as a whole (Codex's review of the diff of Q1).
            "fitRecapWindow": (
                'ui.recapBody.style.minHeight = "";',
                "ui.recapBody.style.minHeight = `${Math.min(ui.recapBody.scrollHeight, RECAP_KEPT)}px`;",
                "fitPop(ui.recapPop);",
            ),
            "fitMarksWindow": ("fitPop(ui.marksPop);",),
            # A window ends above the bar at the bottom of the page, which
            # stays on the screen above it (the real page of Q1).
            "fitPop": (
                "const bar = ui.viewBar.getBoundingClientRect();",
                "const bottom = bar.height > 0 ? Math.min(window.innerHeight, bar.top) : window.innerHeight;",
                # No more than the room above the bar (Codex's review of the
                # diff of Q1: 240 pixels at least went under it), from the
                # top of the window where it shows (stage X12d1 of v2.3.0:
                # popPlace, which keeps POP_GAP above the bar).
                "pop.style.maxHeight = `${place.maxHeight}px`;",
            ),
            "renderRecap": (
                "  if (state.view === null && state.stop !== null) {\n    state.recapOpen = false;\n  }",
                "ui.recapOpen.disabled = !viewing || !state.items.length;",
                'ui.recapOpen.setAttribute("aria-expanded", String(state.recapOpen && showable));',
                "const focused = ui.recapPop.contains(document.activeElement);",
                "ui.recapPop.hidden = !state.recapOpen || !showable;",
                # A window that hides drops its answers on their way and opens
                # no ticket again, and the focus inside it goes to the button
                # or to the heading of what shows instead (Codex's review of
                # the diff of Q1).
                "    if (state.recapShown) {",
                "      state.recapShown = false;\n      state.recapSeq += 1;\n      state.recapLoading = false;\n    }",
                "const target = !ui.recapOpen.disabled && shown(ui.recapOpen) ? ui.recapOpen : [ui.stopHeading, ui.emptyHeading].find(shown);",
                "      target?.focus();\n    }\n    return;",
                "  if (!state.recapShown) {\n    state.recapShown = true;\n    state.recapAsked = null;\n  }",
                "  if (live && state.recapAsked !== recapKey()) {",
                "queueMicrotask(() => requestRecap());",
                "recapColumns(periodRequest(state.period, state.range), state.language)",
                'setText(ui.recapLoading, state.recapLoading ? t("view.loading") : "");',
                "ui.recapStop.hidden = state.recapStop === null;",
                "renderStop(ui.recapStop, null, ui.recapStopLines, ui.recapStopCode, stopBox(state.recapStop.code, state.recapStop.detail, state.productVersion));",
                "describe(days)",
                "ui.recapDifferenceNote.hidden = columns.before === null;",
                # An answer for other items or another period is never drawn
                # under these (the real page of Q1).
                "const answer = state.recapAnswer?.key === recapKey() ? state.recapAnswer.answer : null;",
                "  renderRecapTable(answer, columns);\n  fitRecapWindow();",
            ),
            "renderRecapTable": (
                "  if (answer === null) {\n    ui.recapBody.replaceChildren();\n    return;\n  }",
                'cell.scope = "col";',
                'const name = element("th", "", itemName(key));',
                'name.scope = "row";',
                'name.append(" ", element("span", "recap-line", describe(row.name)));',
                "for (const row of recapRows(panel, before, state.language)) {",
                "const nowWhole = answer.whole === true;",
                "const beforeWhole = previous !== null && previous.whole === true;",
                'const beforeOutside = previous === null || typeof previous.start !== "string";',
                "const difference = nowWhole && beforeWhole ? recapDifference(key, row.now?.values?.[0], row.before?.values?.[0], state.language) : null;",
                # A period before wholly outside the output has dashes, not
                # "no value" (the partial guard of Q1).
                'tr.append(element("td", "", beforeOutside ? "\\u2014" : valueText(key, row.before, !beforeWhole)));',
                'tr.append(element("td", "", difference === null ? "\\u2014" : describe(difference)));',
                '`${describe(valueMessage(key, value, state.language))}${cut ? "*" : ""}`',
                't("view.recap.none")',
                "recapPartial(answer.chosen, answer.start, answer.end, state.language)",
                "recapPartial(previous.chosen, previous.start, previous.end, state.language)",
                't("view.recap.cut_note", { name: describe(columns.now), partial: describe(nowPartial) })',
            ),
            "renderStage": ("  renderMarks(viewing && !apart(), live);\n  renderRecap(viewing, live);",),
        }
        for name, lines in held.items():
            found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, found.group(1))
        request = re.search(r"async function requestRecap\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        for line in (
            # Not while the window does not show (Codex's review of the diff).
            "if (!state.recapShown || state.view === null || !state.items.length) {",
            "const seq = ++state.recapSeq;",
            "  const key = recapKey();\n  state.recapAsked = key;",
            "state.recapAnswer = { key, answer };",
            "  state.recapAnswer = null;\n  state.recapStop = null;\n  state.recapLoading = true;",
            "const payload = { ...seriesPayload(state.items, periodRequest(state.period, state.range), RANGE_GRAIN), previous: true };",
            'const answer = await callApi("/api/view/series", payload);',
            'error.code === "VIEW_NOT_OPEN" && again && state.target !== null',
            "requestRecap(false);",
            "OUTPUT_STOPS.includes(error.code)",
            "state.recapStop = { code: error.code, detail: error.detail };",
            "  if (seq === state.recapSeq) {\n    state.recapLoading = false;\n  }",
        ):
            with self.subTest(line=line):
                self.assertIn(line, request.group(1))
        self.assertEqual(request.group(1).count("if (seq !== state.recapSeq) {\n      return;\n    }"), 2)
        opened = re.search(r"async function openOutput\(target, focus = false, auto = null\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert opened is not None
        # The answers of the summary on their way are dropped as an output
        # starts opening, as those of the other views, before they could open
        # the output before again (Codex's review of the diff of Q1).
        self.assertIn("  state.spreadSeq += 1;\n  // And those of the summary (Codex's review of the diff of Q1).\n  state.recapSeq += 1;\n  state.recapLoading = false;\n  const current", opened.group(1))
        self.assertIn("    state.recapAnswer = null;\n    state.recapAsked = null;\n    state.recapStop = null;", opened.group(1))
        for line in (
            'window.addEventListener("resize", fitRecapWindow);',
            'ui.recapOpen.addEventListener("click", () => openRecap(!state.recapOpen));',
            'ui.recapClose.addEventListener("click", () => openRecap(false));',
            '  ui.recapPop.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {\n      event.preventDefault();\n      openRecap(false);\n    }\n  });',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        # Not remembered, and only the menu of the other views closes on a
        # press outside it.
        remembered = re.search(r"function viewValues\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        outside = re.search(r'document\.addEventListener\("pointerdown", \(event\) => \{(.*?)\n  \}\);', self.script, re.DOTALL)
        assert remembered is not None and outside is not None
        self.assertNotIn("recap", remembered.group(1))
        self.assertIn("state.otherOpen", outside.group(1))
        self.assertNotIn("recap", outside.group(1))
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertRegex(view_css, r"\.recap-pop \{[^}]*top: 100%;[^}]*right: 0;[^}]*max-width: calc\(100vw - 32px\);")
        self.assertRegex(view_css, r"\.recap-body \{\s*overflow: auto;")
        self.assertRegex(view_css, r"\.recap-pop \{[^}]*overflow: auto;")
        self.assertIn("const RECAP_KEPT = 112;", self.script)
        self.assertRegex(view_css, r"\.recap-body thead th \{\s*position: sticky;\s*top: 0;\s*z-index: 1;\s*background: var\(--surface\);")
        self.assertIn('viewBar: document.querySelector(".view-bar"),', self.script)

    def test_the_windows_of_the_right_column_stay_inside_it(self) -> None:
        # Stage X12d1 of v2.3.0: the right column hides what goes out of it,
        # and in a narrow window the windows under the row above the panels
        # (the summary, the laps, the marks, the menu of the other views, and
        # the picker of the items) went out of its left and were cut, or
        # were left too low to read; each now goes through fitPop, which
        # makes it no wider than the column, moves it back into the column,
        # and up inside it where little room is left under its row
        # (popPlace of view_flow.mjs, whose numbers the tests of node hold).
        fit = re.search(r"function fitPop\(pop, height = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert fit is not None
        for line in (
            "const stage = ui.stage.getBoundingClientRect();",
            "const style = getComputedStyle(ui.stage);",
            "left: stage.left + (parseFloat(style.paddingLeft) || 0),",
            "right: stage.right - (parseFloat(style.paddingRight) || 0),",
            "top: stage.top + (parseFloat(style.paddingTop) || 0),",
            # Measured as its rules place it, no wider than the column.
            '  pop.style.translate = "";\n  pop.style.maxWidth = `${Math.max(0, column.right - column.left)}px`;\n  const box = pop.getBoundingClientRect();',
            "const place = popPlace({ left: box.left, right: box.right, top: box.top }, column, bottom, height ? pop.scrollHeight : 0);",
            "const dy = height ? place.dy : 0;",
            'pop.style.translate = place.dx === 0 && dy === 0 ? "" : `${place.dx}px ${-dy}px`;',
            "  if (height) {\n    pop.style.maxHeight = `${place.maxHeight}px`;\n  }",
        ):
            with self.subTest(line=line):
                self.assertIn(line, fit.group(1))
        self.assertIn("  // Where a window of the right column goes (stage X12d1 of v2.3.0).\n  popPlace,\n} from \"./view_flow.mjs\";", self.script)
        for name, line in (
            ("fitRecapWindow", "fitPop(ui.recapPop);"),
            ("fitMarksWindow", "fitPop(ui.marksPop);"),
            ("fitSaveWindow", "fitPop(ui.savePop);"),
            ("renderLaps", "  renderLapsBody(laps, state.lapsAnswer);\n  fitLapsWindow();"),
            ("fitLapsWindow", "  if (!ui.lapsPop.hidden) {\n    ui.lapsBody.style.minHeight = \"\";\n    ui.lapsBody.style.minHeight = `${Math.min(ui.lapsBody.scrollHeight, RECAP_KEPT)}px`;\n  }\n  fitPop(ui.lapsPop);"),
            # The menu keeps its height; only into the column.
            ("renderOtherViews", "  fitPop(ui.otherMenu, false);"),
            ("renderPicker", "    fitPop(ui.picker);\n    return;\n  }"),
        ):
            found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            with self.subTest(function=name):
                self.assertIn(line, found.group(1))
        # Last, after what they hold is drawn.
        for name, last in (("renderOtherViews", "\n  fitPop(ui.otherMenu, false);"), ("renderPicker", "\n  fitPop(ui.picker);")):
            found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            with self.subTest(last=name):
                self.assertTrue(found.group(1).endswith(last))
        for line in (
            'window.addEventListener("resize", fitMarksWindow);',
            'window.addEventListener("resize", fitRecapWindow);',
            'window.addEventListener("resize", fitLapsWindow);',
            'window.addEventListener("resize", fitSaveWindow);',
            'window.addEventListener("resize", () => fitPop(ui.otherMenu, false));',
            'window.addEventListener("resize", () => fitPop(ui.picker));',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        view_css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        # The picker scrolls inside the height that fitPop gives it.
        self.assertRegex(view_css, r"\.picker \{\s*top: 100%;\s*left: 0;\s*width: 540px;\s*margin-top: 6px;\s*/\*[^*]*\*/\s*overflow: auto;\s*\}")
        # The kinds of the laps and their heads keep one line in a narrow
        # window, the tables scrolling sideways (in Japanese, a kind would
        # break after every letter where the window of the laps is as narrow
        # as the column).
        self.assertRegex(view_css, r"\.laps-body \.t th\.laps-kind,\s*\.laps-body \.t td\.laps-kind \{\s*white-space: nowrap;\s*\}")
        # The button of a window keeps one line, the title breaking before it.
        self.assertRegex(view_css, r"\.pop-head button \{\s*/\*[^*]*\*/\s*flex: none;\s*margin-left: auto;\s*white-space: nowrap;\s*\}")
        # The column hides what goes out of it, which is why the windows are kept inside it.
        self.assertRegex(view_css, r"\.stage \{[^}]*position: relative;[^}]*overflow: hidden;")
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        self.assertIn(
            "From stage X12d1 of v2.3.0, every window of the right column (the marks, the summary, saving, the laps, "
            "the menu of the other views, and the picker of the items) stays inside the column, which hides what goes "
            "out of it: no wider than the column inside its padding, moved back into it where its place goes out of its "
            "left or right, and, where less than 240 pixels (or what it holds, where less) are left under its row above "
            "the bar, moved up inside the column, no higher than its top (`fitPop`, `popPlace`); the menu keeps its height, "
            "and the tables of the laps keep their heads and two rows or so, as that of the summary (`fitLapsWindow`).",
            design,
        )
        self.assertIn(
            "Where the window is narrow, the kinds of the laps and the heads over them keep one line, and the tables "
            "scroll sideways.",
            design,
        )

    def test_the_laps_of_a_row_of_the_list_are_a_window(self) -> None:
        # Stage X10 of v2.3.0 (the person's answer 「2 C と最大心拍も」), in the
        # page and its script, which no test runs: each row of the list has a
        # button of its laps, which cannot be pressed (aria-disabled, tied to
        # the line under the list that says why) where the output alone tells
        # that they cannot be shown; the window opens at the place of the
        # summary as the summary does, without holding the focus (the checker's
        # review of the samples, 2), and one of the windows there shows at a
        # time; its title takes the focus, the close button and Escape go back
        # to the button of the row, and the heading of the list takes it where
        # the list was made anew; one request at a time, the last row pressed;
        # a list closed or changed closes it, and an answer of another reading
        # asks for the list again (the checker's review of the plan, 3 to 5).
        row = by_id(self.elements, "caveat")
        window = by_id(self.elements, "laps-pop")
        self.assertIs(window.parent, row)
        self.assertEqual((window.get("role"), window.get("aria-labelledby"), window.get("class")), ("dialog", "laps-pop-title", "pop recap-pop laps-pop"))
        self.assertIn("hidden", window.attributes)
        self.assertNotIn("aria-modal", window.attributes)
        self.assertEqual(by_id(self.elements, "laps-pop-title").get("tabindex"), "-1")
        self.assertEqual(by_id(self.elements, "laps-pop-close").get("data-i18n"), "help.close")
        loading = by_id(self.elements, "laps-loading")
        self.assertEqual((loading.get("role"), loading.get("aria-live")), ("status", "polite"))
        body = by_id(self.elements, "laps-body")
        self.assertEqual((body.get("tabindex"), body.get("role"), body.get("aria-labelledby")), ("0", "region", "laps-pop-title"))
        self.assertIn("hidden", by_id(self.elements, "laps-stop").attributes)
        self.assertIn("hidden", by_id(self.elements, "laps-note").attributes)
        self.assertEqual(by_id(self.elements, "laps-stop-heading").get("data-i18n"), "view.laps.stop_heading")
        for name in ("laps-pop-title", "laps-pop-close", "laps-loading", "laps-stop", "laps-stop-lines", "laps-stop-code", "laps-body", "laps-note"):
            with self.subTest(element=name):
                self.assertIn(window, by_id(self.elements, name).ancestors())
        held = {
            "dropLaps": ("  state.laps = null;\n  state.lapsAnswer = null;\n  state.lapsStop = null;\n  state.lapsLoading = false;",),
            # The running types as the page counts them at first.
            "runningType": ("return (state.view?.types ?? []).some((entry) => entry.name === name && entry.running === true);",),
            "lapsCell": (
                'button.dataset.action = "list-laps";',
                "button.dataset.listFocus = `laps-${row.ref}`;",
                'button.setAttribute("aria-haspopup", "dialog");',
                'button.setAttribute("aria-controls", "laps-pop");',
                "if (LIST_LAP_REASONS.includes(row.laps_unavailable)) {",
                'button.setAttribute("aria-disabled", "true");',
                'button.setAttribute("aria-describedby", `list-laps-${row.laps_unavailable}`);',
            ),
            "openLaps": (
                'if (row === undefined || button.getAttribute("aria-disabled") === "true") {',
                "  state.recapOpen = false;\n  state.saveOpen = false;\n  if (state.marksOpen) {",
                "state.laps = { ref, read: list.answer.read, key: list.key, when: row.datetime, type: row.type, running: runningType(row.type) };",
                "  ui.lapsTitle.focus();\n  requestLaps();",
                # Read from the press, also while another row's answer is on its way
                # (Codex's second read, 3).
                "  state.lapsLoading = true;\n  render();",
            ),
            "closeLaps": ('(listBox?.querySelector(`[data-list-focus="laps-${laps.ref}"]`) ?? listBox?.querySelector(".list-title"))?.focus();',),
            "requestLaps": (
                "if (laps === null || state.view === null || state.lapsAsking) {",
                'answer = await callApi("/api/view/laps", { view: state.view.view, read: laps.read, ref: laps.ref });',
                "  if (state.laps !== laps) {\n    // Closed, or another row pressed meanwhile.\n    requestLaps();\n    return;\n  }",
                '} else if (taken.reason === "read_stale") {\n      lapsStale();',
                # The output opened again, or not: still its row's, or it ends
                # (Codex's second read, 1).
                "    const reopened = await reopen();\n    if (state.laps !== laps) {\n      return;\n    }\n    if (reopened) {\n      lapsStale();\n      return;\n    }",
            ),
            # The rows of the reading before are not shown while the list is asked
            # for again (Codex's 3).
            "lapsStale": ("list.answer = null;", "list.lapsStale = true;", "requestList();", "  if (focused) {\n    focusList();\n  }"),
            "renderLaps": (
                "if (state.laps !== null && (!viewing || apart() || state.full || state.list === null || state.list.key !== state.laps.key)) {",
                "ui.lapsPop.hidden = state.laps === null;",
                "    if (focused) {\n      queueMicrotask(() => lapsFocusAway());\n    }",
            ),
            # The window hides at once where the list closes or changes, and the
            # focus goes away from it (Codex's read of the diff of X10, 1 and 2).
            # Once the page is drawn, which may close the list or stop the page
            # (Codex's second read of the diff of X10, 2).
            "hideLaps": ("  dropLaps();\n  ui.lapsPop.hidden = true;", "    queueMicrotask(() => lapsFocusAway(fallback));"),
            "lapsFocusAway": (
                # Not where the person's close sent it to the button already.
                "  if (active !== null && active !== document.body && !ui.lapsPop.contains(active)) {\n    return;\n  }",
                'const shown = (node) => node !== null && node !== undefined && node.isConnected && node.closest("[hidden]") === null;',
                '[listBox?.querySelector(".list-title"), fallback, ui.stopHeading, ui.emptyHeading].find(shown)?.focus();',
            ),
            "renderLapsBody": ("t(LAP_REASON_KEYS[answer.reason])", 'lapsTable(answer.laps, laps.running ? LAP_CADENCE_FACTOR : null),'),
            "lapsTable": ('const columns = ["number", "kind", "time", "distance", "pace", "heart", "max", ...(factor === null ? [] : ["cadence"])];',),
            "lapsSummaryTable": ('lapsHeads(["kind", "laps", "time", "distance", "avg_pace", "heart"])',),
            # The list closes the window, and another list too.
            "closeList": ("  listBox = null;\n  hideLaps(drawn.find((entry) => entry.key === list.key)?.plot ?? null);",),
            "openList": ("  hideLaps();\n  state.list = {",),
            "renderList": ("note.id = `list-laps-${reason}`;", "if (list.lapsStale && answer !== null) {"),
            # One window under the right end of the row at a time.
            "openRecap": ("    state.saveOpen = false;\n    dropLaps();",),
            "openSave": ("    state.recapOpen = false;\n    dropLaps();",),
            "panelAction": ('    case "list-laps":\n      openLaps(button);\n      return;',),
            "renderStage": ("  renderRecap(viewing, live);\n  renderLaps(viewing);",),
        }
        for name, lines in held.items():
            found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            for line in lines:
                with self.subTest(function=name, line=line[:60]):
                    self.assertIn(line, found.group(1))
        self.assertIn('ui.lapsClose.addEventListener("click", () => closeLaps(true));', self.script)
        # Its height follows the window of the browser (Codex's 4).
        # From stage X12d1 of v2.3.0, through fitLapsWindow, which keeps its
        # tables as those of the summary.
        self.assertIn('  window.addEventListener("resize", fitLapsWindow);', self.script)
        self.assertIn('  ui.lapsPop.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {\n      event.preventDefault();\n      closeLaps(true);', self.script)
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertIn('.list-table button.list-laps-button[aria-disabled="true"] {\n  opacity: 0.55;\n  cursor: not-allowed;\n}', style)
        self.assertIn(".laps-body th.laps-kind,\n.laps-body td.laps-kind {\n  text-align: left;\n}", style)

    def test_the_work_laps_of_the_shoes_are_counted_a_request_at_a_time(self) -> None:
        # Stage X11 of v2.3.0 (the person's answer 「1 C と案 1」), in the page
        # and its script, which no test runs (the real page was checked with
        # synthetic data): the button in the heading of the view by shoes,
        # also over the chart, which cannot be pressed (aria-disabled, its
        # words in the line) where the answer of the shoes tells that nothing
        # can be read; pressed, the tables and the line before reading, with
        # "Read"; read, a request at a time from the place of the answer
        # before, the line while reading, with "Stop"; an answer of a counting
        # dropped meanwhile is dropped, one told busy is asked once more after
        # a second, one told read_stale keeps its words while the shoes are
        # asked again, and the table of the work laps goes above the tables of
        # the shoes, its heading taking the focus (the checker's review of the
        # plan of X11, 9c 3; Codex's review of the plan of X11, 9).
        ids = [element.get("id") for element in self.elements]
        self.assertLess(ids.index("shoes-save"), ids.index("shoes-work"))
        self.assertLess(ids.index("shoes-work"), ids.index("shoes-back"))
        button = by_id(self.elements, "shoes-work")
        self.assertIs(button.parent, by_id(self.elements, "shoes-table").parent)
        self.assertEqual((button.get("class"), button.get("data-i18n")), ("small", "view.shoes.work.button"))
        line = by_id(self.elements, "shoes-work-line")
        self.assertIn("hidden", line.attributes)
        self.assertEqual(line.get("class"), "compare-line shoes-work-line")
        text = by_id(self.elements, "shoes-work-text")
        self.assertEqual((text.parent, text.get("role"), text.get("aria-live")), (line, "status", "polite"))
        for name, key in (("shoes-work-read", "view.shoes.work.read"), ("shoes-work-stop", "view.shoes.work.stop")):
            with self.subTest(element=name):
                self.assertIs(by_id(self.elements, name).parent, line)
                self.assertIn("hidden", by_id(self.elements, name).attributes)
                self.assertEqual(by_id(self.elements, name).get("data-i18n"), key)
        notes = by_id(self.elements, "shoes-work-notes")
        self.assertIn("hidden", notes.attributes)
        self.assertIs(notes.parent, by_id(self.elements, "shoes-notes").parent)
        self.assertLess(ids.index("shoes-work-notes"), ids.index("shoes-notes"))
        info = by_id(self.elements, "shoes-work-info")
        self.assertEqual((info.get("aria-expanded"), info.get("aria-controls"), info.get("data-i18n")), ("false", "shoes-work-more", "view.shoes.work.info"))
        self.assertIn("hidden", by_id(self.elements, "shoes-work-more").attributes)
        for name in ("shoes-work-shown", "shoes-work-info", "shoes-work-counted", "shoes-work-more"):
            with self.subTest(element=name):
                self.assertIn(notes, by_id(self.elements, name).ancestors())
        held = {
            "dropShoesWork": ("  state.shoesWork = null;\n  state.shoesWorkSeq += 1;",),
            "enterShoes": ('  listChanged("shoes");\n  dropShoesWork();',),
            "leaveShoes": ("  dropShoesWork();\n  state.shoes = null;",),
            # Another period, types, conditions, or reading drop it, but for
            # the words of a reading told stale.
            "requestShoes": (
                "  if (state.shoesWork?.keep) {\n    state.shoesWork.keep = false;\n  } else {\n    dropShoesWork();\n  }",
                # The shoes asked for again after the output opened again are
                # awaited (Codex's third read of the diff of X11, 2).
                "        state.shoesLoading = false;\n        // Awaited, so that a caller knows when the shoes are drawn (Codex's\n        // third read of the diff of X11, 2).\n        await requestShoes(false);\n        return;",
            ),
            "askShoesWork": (
                'if (state.shoes === null || drawn === null || state.shoesLoading || state.shoesWork?.phase === "reading" || !drawn.shoes.length) {',
                "  if (before.line === undefined) {\n    return;\n  }",
                # The stop of a counting before goes with it (Codex's seventh
                # read of the diff of X11).
                "  if (state.shoesStop?.work) {\n    state.shoesStop = null;\n  }\n  state.shoes.table = true;",
                # With the reading known when it is asked for (Codex's fourth
                # read of the diff of X11).
                'state.shoesWork = { seq: state.shoesWorkSeq, phase: "ask", before, read: drawn.read, known: state.viewRead, asked: { ...state.shoesAsked, read: drawn.read }, pairs: drawn.shoes.length };',
                "  render();\n  ui.shoesWorkRead.focus();",
            ),
            "readShoesWork": (
                '  if (work === null || work.phase !== "ask") {\n    return;\n  }',
                "  render();\n  ui.shoesWorkStop.focus();",
                # The sums of each pair (work.pairs is their number).
                "    sums: Array.from({ length: work.pairs }, () => workEmpty()),",
                # Of the shoes shown, of the output shown (Codex's read of the
                # diff of X11, 2); a counting whose view changed under it ends
                # (Codex's third read, 1), also before its first request.
                'const mine = () => state.shoesWork === work && work.seq === state.shoesWorkSeq && work.phase === "reading";',
                "    if (state.shoes !== null && state.view?.view === work.asked.view && state.viewRead === work.known) {\n      return true;\n    }\n    dropShoesWork();\n    render();\n    shoesWorkFocusAway();\n    return false;",
                "  for (;;) {\n    if (!current()) {\n      return;\n    }\n    while (shoesWorkAsking !== null) {",
                # A request of a counting dropped meanwhile is waited for
                # (Codex's read of the diff of X11, 3).
                "    while (shoesWorkAsking !== null) {\n      await shoesWorkAsking;\n      if (!current()) {\n        return;\n      }\n    }\n    const asking = callApi(\"/api/view/shoes/work\", { ...work.asked, from: start });",
                "    shoesWorkAsking = settled;\n    settled.then(() => {\n      if (shoesWorkAsking === settled) {\n        shoesWorkAsking = null;\n      }\n    });",
                # After the output opened again, the shoes asked for again
                # only where they were not meanwhile, as requestShoes does
                # (Codex's second and third reads of the diff of X11).
                '} else if (error.code === "VIEW_NOT_OPEN" && state.target !== null) {\n        const shoesSeq = state.shoesSeq;\n        if (await reopen()) {',
                '          if (state.shoesSeq === shoesSeq) {\n            await requestShoes(false);\n          }\n          shoesWorkFocusAway();\n          return;',
                "} else if (OUTPUT_STOPS.includes(error.code)) {",
                "state.shoesStop = { code: error.code, detail: error.detail, work: true };",
                "if (taken === null || (taken.reason === undefined && (taken.from !== start || taken.runs !== work.runs))) {",
                'state.shoesStop = { code: null, detail: null, work: true };',
                '      if (taken.reason === "busy" && !retried) {\n        retried = true;\n        await waitFor(1000);\n        if (!current()) {\n          return;\n        }\n        continue;\n      }',
                'keep: taken.reason === "read_stale",',
                # The focus away once the shoes asked again are drawn (Codex's
                # second read of the diff of X11, 3), and not from where the
                # person put it (its third read, 3).
                '      render();\n      // Not from where the person put it (Codex\'s third read of the diff\n      // of X11, 3).\n      shoesWorkFocusAway();\n      if (taken.reason === "read_stale") {',
                '        await requestShoes();\n        shoesWorkFocusAway();\n      }\n      return;',
                # Sums past the whole numbers that the page holds exactly end the
                # counting (Codex's ninth read of the diff of X11).
                "    retried = false;\n    const sums = work.sums.map((sum, index) => workAdd(sum, taken.pairs[index]));\n    const counts = workAdd(work.counts, taken.counts);\n    if (sums.includes(null) || counts === null) {",
                "      dropShoesWork();\n      state.shoesStop = { code: null, detail: null, work: true };\n      render();\n      shoesWorkFocusAway();\n      return;\n    }\n    work.sums = sums;\n    work.counts = counts;",
                # The table at the end, also after the chart was chosen while
                # reading (Codex's read of the diff of X11, 5).
                '      work.phase = "done";\n      // The table, also where the chart was chosen while reading (Codex\'s\n      // read of the diff of X11, 5), its heading to take the focus.\n      state.shoes.table = true;\n      render();\n      byId("shoes-work-name")?.focus();',
                "    work.done = taken.next;\n    start = taken.next;",
            ),
            "stopShoesWork": ('  if (state.shoesWork?.phase !== "reading") {\n    return;\n  }\n  dropShoesWork();\n  render();\n  ui.shoesWork.focus();',),
            # The focus after a stop or an error, which hid "Stop" (Codex's
            # read of the diff of X11, 4).
            "shoesWorkFocusAway": (
                "  if (active !== null && active !== document.body && shown(active)) {\n    return;\n  }",
                '[byId("shoes-stop-heading"), ui.stopHeading, ui.shoesWork, ui.shoesTitle, ui.emptyHeading].find(shown)?.focus();',
            ),
            # Opening another output drops a counting (Codex's read of the
            # diff of X11, 2).
            "openOutput": ("  state.seriesSeq += 1;\n  // And a counting of the work laps of the shoes, whose requests would go on\n  // for the output before (Codex's read of the diff of X11, 2).\n  dropShoesWork();",),
            # Not where a newer reading is known (Codex's fourth read of the
            # diff of X11).
            "shoesWorkDone": ('return work !== null && work.phase === "done" && drawn !== null && work.read === drawn.read && work.known === state.viewRead ? work : null;',),
            # The table from the sums of each pair that the counting keeps
            # (the real page of X11 found it drawn from the number of pairs).
            "buildShoesTables": ("shoesWorkTable(drawn, work.sums, state.language)", 'section.querySelector("#shoes-work-name").tabIndex = -1;', "    tables.unshift(section);"),
            # A focus in the view by shoes that the drawing hides or takes away
            # goes on (Codex's fifth and sixth reads of the diff of X11).
            "renderShoes": ("  renderShoesWork(drawn);", "  const inShoes = ui.shoes.contains(document.activeElement);", "  renderShoesBody(drawn);\n  if (inShoes) {\n    shoesWorkFocusAway();\n  }"),
            "renderShoesBody": ("shoesDrawn[2] === state.language && shoesDrawn[3] === shoesWorkDone(drawn)) {", "shoesDrawn = [drawn, shoes.table, state.language, shoesWorkDone(drawn)];"),
            "renderShoesWork": (
                "ui.shoesWork.hidden = !shown;",
                'ui.shoesWork.setAttribute("aria-disabled", String(grey || work?.phase === "reading" || state.shoesLoading));',
                'ui.shoesWorkRead.hidden = work?.phase !== "ask";',
                'ui.shoesWorkStop.hidden = work?.phase !== "reading";',
                "const done = state.shoes?.table ? shoesWorkDone(drawn) : null;",
                'ui.shoesWorkMore.hidden = ui.shoesWorkInfo.getAttribute("aria-expanded") !== "true";',
            ),
        }
        for name, lines in held.items():
            found = re.search(rf"(?:async )?function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            for line in lines:
                with self.subTest(function=name, line=line[:60]):
                    self.assertIn(line, found.group(1))
        read = re.search(r"async function readShoesWork\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert read is not None
        # The answer of a counting dropped meanwhile is dropped: before a
        # request, after an error, after an answer, after the wait of busy,
        # and after the wait of a request of a counting dropped before.
        self.assertEqual(read.group(1).count("if (!current()) {\n"), 5)
        # The focus away after an error and after an answer of another
        # form (the reopening has its own, held above).
        self.assertEqual(read.group(1).count("      render();\n      shoesWorkFocusAway();\n      return;\n"), 3)
        self.assertIn('  ui.shoesWork.addEventListener("click", () => {\n    if (ui.shoesWork.getAttribute("aria-disabled") !== "true") {\n      askShoesWork();', self.script)
        self.assertIn('  ui.shoesWorkRead.addEventListener("click", readShoesWork);\n  ui.shoesWorkStop.addEventListener("click", stopShoesWork);', self.script)
        self.assertIn('    const open = ui.shoesWorkInfo.getAttribute("aria-expanded") !== "true";\n    ui.shoesWorkInfo.setAttribute("aria-expanded", String(open));\n    ui.shoesWorkMore.hidden = !open;', self.script)
        # The charts drawn again for another size of the window keep a focus
        # in the view by shoes as renderShoes does (Codex's sixth read).
        redraw = re.search(r"function scheduleRedraw\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert redraw is not None
        self.assertIn("    if (!ui.shoes.hidden) {\n      // As renderShoes does (Codex's sixth read of the diff of X11).\n      const inShoes = ui.shoes.contains(document.activeElement);\n      renderShoesBody(state.shoesAnswer);\n      if (inShoes) {\n        shoesWorkFocusAway();\n      }\n    }", redraw.group(1))
        style = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertIn('#shoes-work[aria-disabled="true"] {\n  opacity: 0.55;\n  cursor: not-allowed;\n}', style)
        self.assertIn('.shoes-work-table th[scope="row"] {\n  white-space: normal;\n  overflow-wrap: anywhere;\n}', style)

    def test_the_words_of_an_info_button_have_no_mark_of_their_own(self) -> None:
        # The style puts ⓘ before the words of every info button (styles.css,
        # .info-button::before); words with a mark of their own showed it
        # twice (the real page of stage X11 of v2.3.0).
        catalogs = {language: json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8")) for language in ("ja", "en")}
        buttons = [element for element in self.elements if "info-button" in (element.get("class") or "").split() and element.get("data-i18n")]
        self.assertIn("shoes-work-info", [button.get("id") for button in buttons])
        for button in buttons:
            for language, words in catalogs.items():
                with self.subTest(button=button.get("id"), language=language):
                    self.assertNotIn("ⓘ", words[button.get("data-i18n")])

    def test_the_list_follows_the_panels_and_drops_old_answers(self) -> None:
        # Stage M3 of v2.2.0 (the checker's review of the plan, and Codex's):
        # the list closes when what the panels count or show changes, and
        # stays for the words, the scales, and the cross line
        # (view_flow.mjs listAfter, which the node tests check); it opens
        # from a chart of the answer now, not while numbers are on their way,
        # for the activity types of that answer; only the answer of its last
        # request is shown; a ticket that the server no longer keeps opens
        # the output again once; and it goes with its panel when the panels
        # are drawn again, the focus where it was.
        # From O1 of v2.2.0, the points of two items close it too, and from
        # P1 a distribution.
        for change, count in (("numbers", 1), ("items", 1), ("marks", 2), ("table", 1), ("big", 2), ("compare", 1), ("full", 2), ("plot", 1), ("spread", 1)):
            with self.subTest(change=change):
                self.assertEqual(self.script.count(f'listChanged("{change}");'), count)
        series = re.search(r"async function requestSeries\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert series is not None
        self.assertTrue(series.group(1).startswith('\n  // New numbers close the list of a period (stage M3 of v2.2.0).\n  listChanged("numbers");'))
        self.assertIn("state.answerTypes = payload.types;", series.group(1))
        request = re.search(r"async function requestList\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        body = request.group(1)
        self.assertIn("const seq = ++state.listSeq;", body)
        self.assertIn("types: list.types,", body)
        self.assertIn('error.code === "VIEW_NOT_OPEN" && again && state.target !== null && (await reopen())', body)
        self.assertIn("requestList(false);", body)
        self.assertIn("OUTPUT_STOPS.includes(error.code)", body)
        self.assertEqual(body.count("if (seq !== state.listSeq) {\n      return;\n    }"), 2)
        close = re.search(r"function closeList\(byPerson = false\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert close is not None
        self.assertIn("state.listSeq += 1;", close.group(1))
        for line in (
            "!listOpens({ item: entry.item, mode: entry.mode, table: entry.table, empty: entry.shapes === null || entry.shapes.empty, loading: state.loading })",
            "types: state.answerTypes,",
            "  // The list goes with its panel, drawn again (stage M3 of v2.2.0).\n  renderList();\n  drawnSignature = panelsSignature();\n  restoreFocus(focused);",
            "    // The list goes with the panels (stage M3 of v2.2.0).\n    closeList();\n    drawn = [];",
            "if (listBox?.contains(active)) {\n    return { list: active.dataset.listFocus ?? \"title\" };\n  }",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)

    def test_the_view_page_opens_the_output_again_for_a_newer_reading_of_other_facts(self) -> None:
        # Stage W1 of v2.2.1: every answer of the numbers goes through
        # takeReading after the check of its generation and before it is used
        # (a comparison of years once, by its answer of the newest reading); a
        # request refused for its form opens the output again once
        # (reopenOnce); an opening by itself opens the folder that the ticket
        # shown reads, and gives the focus back where it was.
        def body(name: str) -> str:
            found = re.search(rf"(?:async )?function {name}\(.*?\) \{{(.*?)\n\}}", self.script, re.DOTALL)
            assert found is not None, name
            return found.group(1)

        refused = '} else if (error.code === "REQUEST_INVALID" && reopenOnce(askedView)) {'
        refused_payload = '} else if (error.code === "REQUEST_INVALID" && reopenOnce(payload.view)) {'
        held = {
            "requestSeries": (
                "const askedView = state.view.view;",
                "    if (seq !== state.seriesSeq) {\n      return;\n    }\n    if (!takeReading(askedView, answer)) {\n      state.loading = false;\n      return;\n    }\n    setAnswer(answer);",
                refused,
            ),
            "requestOverview": (
                "const askedView = state.view.view;",
                '    if (seq === state.overviewSeq && error.code === "REQUEST_INVALID" && reopenOnce(askedView)) {\n      return;\n    }',
                "const parts = [state.view.view, key, typesRequest(state.counted, state.view.types), conditionsKey(state.conditions)];",
                "const signature = JSON.stringify([...parts, state.viewRead]);",
                "      if (!takeReading(askedView, answer)) {\n        return;\n      }\n      state.overview = { signature: JSON.stringify([...parts, Number.isInteger(answer.read) ? answer.read : null]), key, answer };",
            ),
            "requestRecap": (
                "const askedView = state.view.view;",
                "    if (!takeReading(askedView, answer)) {\n      state.recapLoading = false;\n      return;\n    }\n    state.recapAnswer = { key, answer };",
                refused,
            ),
            "requestCompare": (
                "const askedView = state.view.view;",
                "    if (seq !== state.compareSeq) {\n      return;\n    }\n    // Once for the generation, by its answer of the newest reading (stage W1\n    // of v2.2.1).\n    if (!takeReading(askedView, newestAnswer([whole, ...answers]))) {\n      state.compareLoading = false;\n      return;\n    }",
                refused,
            ),
            "requestPlot": (refused_payload,),
            "requestSpread": (refused_payload,),
            "requestShoes": (refused_payload,),
            "openOutput": (
                "  state.shoesSeq += 1;\n  // And that of the overview, whose answer of the output before could\n  // otherwise come after this one opened (stage W1 of v2.2.1).\n  state.overviewSeq += 1;",
                "  state.overviewSeq += 1;\n  // And that of the panels, whose answer of the output before could ask for\n  // its overview after this one opened (Codex's review of the diff of W1).\n  state.seriesSeq += 1;",
                "  if (auto === null) {\n    state.typesOpen = false;\n    state.conditionsOpen = false;\n    state.pickerOpen = false;\n  }",
                "    if (auto === null || (ui.rangeFrom.value === (rangeBefore?.from ?? \"\") && ui.rangeTo.value === (rangeBefore?.to ?? \"\"))) {",
                "    if (auto === null) {\n      rememberItems();\n    }",
                "const ticket = auto === null ? null : state.view?.view ?? null;",
                "const focused = auto === null ? null : document.activeElement;",
                "  if (auto === null) {\n    state.reopenedAt = null;\n  }",
                "const answer = await openAnswer(target, ticket);",
                "    state.opening = null;\n    // The answer of the panels that the opening dropped no longer puts their\n    // loading down (stage W1 of v2.2.1, the checker's review of its diff).\n    state.loading = false;",
                '    state.view = answer;\n    state.viewRead = Number.isInteger(answer.read) ? answer.read : null;\n    if (auto === "refused") {\n      state.reopenedAt = state.viewRead;\n    }',
                '    if (document.activeElement === document.body || document.activeElement?.closest("[hidden]")) {\n      if (focused !== null && focused !== document.body && focused.isConnected && !focused.closest("[hidden]") && !focused.disabled) {\n        focused.focus();\n      } else {\n        ui.outputSelect.focus();\n      }\n    }',
            ),
            "reopen": (
                "    state.view = answer;\n    state.viewRead = Number.isInteger(answer.read) ? answer.read : null;\n    state.names = answer.names ?? null;",
                "  const before = state.view;",
                '    if (before !== null && !sameFacts(before, answer)) {\n      if (state.opening === null) {\n        openOutput(state.target, false, "changed");\n      }\n      return false;\n    }\n    state.view = answer;',
            ),
            "openAnswer": (
                "  if (ticket !== null) {",
                'return await callApi("/api/view/open", { output: "view", view: ticket });',
                '      if (error.code !== "VIEW_NOT_OPEN") {\n        throw error;\n      }',
                'return callApi("/api/view/open", targetPayload(target));',
            ),
            "takeReading": (
                "const step = readingStep(readingOf(state.view, state.viewRead, asked, answer), state.opening !== null);",
                '  if (step === "reopen") {\n    if (state.target !== null) {\n      openOutput(state.target, false, "changed");\n    }\n    return false;\n  }',
                '  if (step === "drop") {\n    return false;\n  }',
                '  if (step === "newer") {\n    state.viewRead = answer.read;\n  }\n  return true;',
            ),
            "reopenOnce": (
                "const step = refusalStep({ asked, view: state.view, opening: state.opening !== null, reopenedAt: state.reopenedAt, known: state.viewRead });",
                '  if (step === "reopen" && state.target !== null) {\n    openOutput(state.target, false, "refused");\n    return true;\n  }\n  return step === "wait";',
            ),
        }
        for name, lines in held.items():
            text = body(name)
            for line in lines:
                with self.subTest(function=name, line=line[:60]):
                    self.assertIn(line, text)
        self.assertIn("  viewRead: null,\n  reopenedAt: null,\n", self.script)
        for name in ("readingOf", "readingStep", "refusalStep", "newestAnswer", "sameFacts"):
            with self.subTest(imported=name):
                self.assertIn(f"\n  {name},\n", self.script.split('} from "./view_flow.mjs";')[0])
        # The item of the design document, said once.
        design = re.sub(r"\s+", " ", (ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8"))
        for line in (
            "From v2.2.1 (stage W1), the answer of `/api/view/open` gives the number of its reading too, and those four answers give the facts of their reading of the output (`output`: its first and last days, its activity types with their counts, and whether it is partial).",
            "the page opens the output again by itself, as **Choose another output…** with the same folder does, by the ticket that reads it (`{\"output\": \"view\", \"view\": ticket}`,",
            "unless an output is being opened; a newer reading of the same facts only moves the reading known on, and the overview keeps the number of its reading in its signature.",
            "opens the output again by itself once, until a newer reading than the one that it opened is seen; the overview too.",
            "An opening by itself drops the answers of the output before (those of the panels too), writes no settings, keeps a date being typed and the windows of the activity types and the conditions, and gives the focus back where it was only where the focus was lost meanwhile.",
        ):
            with self.subTest(design=line[:60]):
                self.assertEqual(design.count(line), 1)

    def test_the_questions_of_the_bar_end_where_their_buttons_end(self) -> None:
        # Stage W2 of v2.2.1 (the person's choice of the samples): the
        # questions of Quit (both pages) and of forgetting the settings are each
        # in a row of their own, whose room right of the button the page
        # measures, and a way of Compare years chosen shows its chart again.
        normalize = page("index.html")
        for elements, pairs in ((self.elements, (("quit-row", "quit-confirm"),)), (normalize, (("quit-row", "quit-confirm"), ("forget-row", "forget-confirm")))):
            for row, question in pairs:
                with self.subTest(row=row):
                    box = by_id(elements, row)
                    self.assertEqual((box.get("class"), "hidden" in box.attributes), ("confirm-row", True))
                    self.assertIs(by_id(elements, question).parent, box)
                    self.assertIn("hidden", by_id(elements, question).attributes)
        style = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
        for rule in (
            ".statusbar .confirm-row {\n  display: flex;\n  flex: 1 1 100%;\n  justify-content: flex-end;\n}",
            ".statusbar .confirm-row .confirm {\n  flex: 0 1 34em;\n  min-width: 0;\n}",
            '.statusbar .confirm-row[data-fit="bar"] .confirm {\n  flex: 1 1 100%;\n}',
        ):
            with self.subTest(rule=rule[:40]):
                self.assertIn(rule, style)
        measure = (
            "function alignConfirmRow(row, button) {\n  if (row.hidden) {\n    return;\n  }\n  const bar = row.parentElement;\n"
            "  const style = getComputedStyle(bar);\n  const box = bar.getBoundingClientRect();\n  const end = button.getBoundingClientRect().right;\n"
            "  const room = end - box.left - parseFloat(style.paddingLeft);\n"
            "  const wide = room < 20 * parseFloat(getComputedStyle(document.documentElement).fontSize);\n"
            "  row.dataset.fit = wide ? \"bar\" : \"button\";\n"
            "  row.style.paddingRight = wide ? \"0px\" : `${Math.max(0, Math.round(box.right - parseFloat(style.paddingRight) - end))}px`;\n"
            "  row.firstElementChild.style.maxWidth = wide ? \"\" : `${Math.floor(room)}px`;\n}"
        )
        # The bar and each part of it but the rows of the questions (a part
        # that grows or wraps may move a button while the bar keeps its size).
        WATCH_PARTS = (
            "    const bar = ui.quitRow.parentElement;\n    watcher.observe(bar);\n    for (const part of bar.children) {\n"
            "      if (!part.classList.contains(\"confirm-row\")) {\n        watcher.observe(part);\n      }\n    }\n"
        )
        # What the observer asks for is measured in the next frame, so that
        # what the measuring changes does not come back to the observer in the
        # same frame (the errors of the window on the real pages of W2).
        SCHEDULE = (
            "let alignFrame = null;\n\nfunction scheduleAlign() {\n  if (alignFrame !== null) {\n    return;\n  }\n"
            "  alignFrame = window.requestAnimationFrame(() => {\n    alignFrame = null;\n    ALIGN\n  });\n}"
        )
        app = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        for name, script, lines in (
            ("view.mjs", self.script, (
                measure,
                '  quitRow: byId("quit-row"),',
                "  ui.quitRow.hidden = !state.quitAsked;\n  ui.quitConfirm.hidden = !state.quitAsked;\n  alignConfirmRow(ui.quitRow, ui.quit);",
                '  window.addEventListener("resize", () => alignConfirmRow(ui.quitRow, ui.quit));',
                "  if (compareModeNow() !== mode) {\n    state.compare.table = false;\n  }\n  state.compareMode = mode;\n  rememberItems(true);",
                "  renderHelp();\n  // The question of Quit, after every part of the bar is drawn (stage W2 of\n  // v2.2.1).\n  alignConfirmRow(ui.quitRow, ui.quit);\n}",
                "    const watcher = new ResizeObserver(scheduleAlign);\n" + WATCH_PARTS,
                SCHEDULE.replace("ALIGN", "alignConfirmRow(ui.quitRow, ui.quit);"),
            )),
            ("app.mjs", app, (
                measure,
                '  quitRow: byId("quit-row"),',
                '  forgetRow: byId("forget-row"),',
                "  ui.forgetRow.hidden = !state.forget.asked;\n  ui.forgetConfirm.hidden = !state.forget.asked;\n  alignConfirmRow(ui.forgetRow, ui.forgetButton);",
                "  ui.quitRow.hidden = !state.quitAsked;\n  ui.quitConfirm.hidden = !state.quitAsked;\n  alignConfirmRow(ui.quitRow, ui.quit);",
                "function alignConfirmRows() {\n  alignConfirmRow(ui.quitRow, ui.quit);\n  alignConfirmRow(ui.forgetRow, ui.forgetButton);\n}",
                '  window.addEventListener("resize", alignConfirmRows);',
                "  renderInfos();\n  // The questions of the bar, after every part of it is drawn (stage W2 of\n  // v2.2.1).\n  alignConfirmRows();\n}",
                "    const watcher = new ResizeObserver(scheduleAlign);\n" + WATCH_PARTS,
                SCHEDULE.replace("ALIGN", "alignConfirmRows();"),
            )),
        ):
            for line in lines:
                with self.subTest(script=name, line=line[:50]):
                    self.assertEqual(script.count(line), 1)
        # The table of Compare years goes down only where the way shown
        # changes, besides its own button, and each comparison starts with
        # the chart: the item, the years, the month, and the races keep it
        # (Codex's review of the diff of W2 of v2.2.1).
        self.assertEqual(re.findall(r"state\.compare\.table = [^;\n]*;", self.script), ["state.compare.table = false;", "state.compare.table = !state.compare.table;"])
        way = re.search(r"\nfunction chooseCompareMode\(mode\) \{\n(.*?)\n\}\n", self.script, re.DOTALL)
        assert way is not None
        self.assertIn("  if (compareModeNow() !== mode) {\n    state.compare.table = false;\n  }\n", way.group(1))
        opened = re.search(r"\n  state\.compare = \{\n(.*?)\n  \};\n", self.script, re.DOTALL)
        assert opened is not None
        self.assertIn("\n    table: false,\n", opened.group(1))
        self.assertIn('  ui.compareTable.addEventListener("click", () => {\n    state.compare.table = !state.compare.table;\n    render();\n  });', self.script)
        design = re.sub(r"\s+", " ", (ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8"))
        for line in (
            "From v2.2.1 (stage W2) each question is in a row of its own, its box ending where its button ends: CSS alone does not know where the button is,",
            "the box is at most as wide as the room left of the end of the button, and a room under 20rem leaves the box as wide as the bar.",
            "Both questions of the normalization page can show at once, each in its own row.",
            "and as the window, the bar, or any part of the bar changes size (a part that grows or wraps may move the button while the bar keeps its size; such a change is measured in the next frame, so that what the measuring changes does not come back to the observer of the bar in the same frame);",
        ):
            with self.subTest(design=line[:40]):
                self.assertEqual(design.count(line), 1)

    def test_a_comparison_never_changes_the_panels_and_drops_old_answers(self) -> None:
        # v2.2.0 L1 (plan v2, 5 and 6): the numbers of a comparison are one
        # generation, whose older answers are dropped when they come, and
        # whose stop shows under its bar; the period, the grouping, and the
        # panels of the page are never written while comparing, and the way
        # back shows them as they were; the shelf, the layouts, the period,
        # its range, and the groupings Auto and Year are not used.
        request = re.search(r"async function requestCompare\(again = true\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert request is not None
        body = request.group(1)
        self.assertIn("const seq = ++state.compareSeq;", body)
        self.assertEqual(body.count("if (seq !== state.compareSeq) {\n      return;\n    }"), 2)
        self.assertIn("if (seq !== state.compareSeq) {\n          return;\n        }", body)
        self.assertIn("state.compareStop = { code: error.code, detail: error.detail };", body)
        # Its stop says what a comparison can change (view_flow.mjs, which the
        # node tests check).
        self.assertIn("compareStopBox(state.compareStop.code, state.compareStop.detail, state.productVersion, compareMonthNow())", self.script)
        self.assertNotRegex(body, r"state\.(grain|period|range|items|answer) =")
        grain = re.search(r"function setGrain\(grain\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert grain is not None
        self.assertLess(grain.group(1).index("    return;\n  }"), grain.group(1).index("state.grain = grain;"))
        leave = re.search(r"function leaveCompare\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert leave is not None
        self.assertIn("state.compareSeq += 1;", leave.group(1))
        self.assertNotRegex(leave.group(1), r"state\.(grain|period|range|items) =")
        for line in (
            "state.compareSeq += 1;\n  // And those of the points, before they could open the output before\n  // again (Codex's review of the diff of O1).\n  state.plotSeq += 1;\n  // And those of a distribution (stage P1).\n  state.spreadSeq += 1;\n  // And those of the summary (Codex's review of the diff of Q1).\n  state.recapSeq += 1;\n  state.recapLoading = false;\n  const current",
            "const apart = viewing && comparing();",
            # The changes use no period either (stage X7 of v2.3.0).
            "const noPeriod = apart || (viewing && changesShown());",
            "button.disabled = !viewing || noPeriod;",
            "ui.rangeFrom.disabled = noPeriod;",
            "ui.rangeTo.disabled = noPeriod;",
            "ui.periodBack.disabled = !viewing || noPeriod ||",
            "button.disabled = !viewing || otherShown() || (grains !== null && !grains.includes(button.dataset.grain));",
            "ui.compareOff.hidden = !apart;",
            # From O1 of v2.2.0, the points of two items take the place of the
            # panels as a comparison does.
            "function apart() {\n  return comparing() || otherShown();\n}",
            "const viewing = live && state.view !== null && state.opening === null && !apart();",
            "ui.addItems.disabled = !viewing || apart() || state.items.length >= MAX_PANELS;",
            "const showPanels = viewing && state.items.length > 0 && state.answer !== null && state.seriesStop === null && !apart();",
            "ui.caveat.hidden = !viewing || apart();",
            "compare_mode: state.compareMode,",
            "compare_month: state.compareMonth,",
            "const compare = compareToOpen(state.settings);",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        self.assertEqual(self.script.count("const viewing = live && state.view !== null && state.opening === null && !apart();"), 2)
        # A ticket opened again for an output that is no longer the one chosen
        # is dropped (the review by Codex); an output without days has no
        # years to compare.
        again = re.search(r"async function reopen\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert again is not None
        self.assertIn("const seq = state.openSeq;", again.group(1))
        self.assertEqual(again.group(1).count("if (seq !== state.openSeq) {\n      return false;\n    }"), 2)
        self.assertLess(again.group(1).index("if (seq !== state.openSeq)"), again.group(1).index("state.view = answer;"))
        for line in (
            "compareButton.disabled = !compareYears(state.view?.first_day, state.view?.last_day).length;",
            "if (state.view === null || item === undefined || !compareYears(state.view.first_day, state.view.last_day).length) {",
            "if (itemsByKey(answer.items).has(state.compare.key) && compareYears(answer.first_day, answer.last_day).length) {",
            # What the keyboard says names each year's own period.
            ': t("view.compare.spoken_year", { year: describe(reading.label), period: describe(reading.period), value: describe(reading.value ?? reading.missing) }),',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)

    def test_quitting_asks_first_in_the_bar(self) -> None:
        # As on the normalization page, with words that say what it quits:
        # the view page is a tab of its own.
        self.assertEqual(by_id(self.elements, "quit-button").get("data-i18n"), "view.quit")
        for identifier, key in (("quit-yes", "quit.yes"), ("quit-no", "quit.no")):
            with self.subTest(button=identifier):
                answer = by_id(self.elements, identifier)
                self.assertEqual((answer.get("data-i18n"), answer.get("aria-describedby")), (key, "quit-question quit-text"))
        ask = re.search(r"function askQuit\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert ask is not None
        self.assertIn("ui.quitNo.focus();", ask.group(1))

    def test_the_colors_are_one_group_of_three_choices(self) -> None:
        group = [element for element in self.elements if element.tag == "fieldset" and element.get("aria-labelledby") == "theme-label"]
        self.assertEqual(len(group), 1)
        for identifier, value in (("theme-auto", "auto"), ("theme-light", "light"), ("theme-dark", "dark")):
            with self.subTest(choice=identifier):
                choice = by_id(self.elements, identifier)
                self.assertEqual((choice.get("type"), choice.get("name"), choice.get("value")), ("radio", "theme", value))
                self.assertIn("disabled", choice.attributes)

    def test_the_help_panel_is_a_closed_side_panel(self) -> None:
        panel = by_id(self.elements, "help-panel")
        self.assertEqual((panel.tag, panel.get("role"), panel.get("aria-labelledby")), ("aside", None, "help-heading"))
        sections = [element for element in self.elements if element.get("class") == "help-section"]
        # From v2.2.0 L2, an item of comparing years; from M4, the items of
        # comparing by race day, of the marks, and of the list of a period,
        # after comparing years; from OP2, an item of the other views, after
        # comparing by race day (the checker's answer 1 of the plan of OP2),
        # with a paragraph for each view. Q2: an item of the summary, after the
        # other views (the checker's answer 2 of the plan of Q2). R3: an item of
        # saving as an image, after the summary (the checker's answer 2 of the
        # plan of R3). T2: an item of the conditions on the activities, after
        # how to use, as the guides give them after the period, the grouping,
        # and the activity types (Codex's review of the plan of T2, 11).
        self.assertEqual(len(sections), 17)
        order = [str(section.get("aria-labelledby")) for section in sections]
        self.assertEqual(order[:3], ["help-use-heading", "help-conditions-heading", "help-shelf-heading"])
        self.assertEqual(order[order.index("help-compare-heading") : order.index("help-compare-heading") + 7], ["help-compare-heading", "help-race-heading", "help-other-heading", "help-recap-heading", "help-save-heading", "help-marks-heading", "help-list-heading"])
        other = [element.get("data-i18n") for element in self.elements if (element.get("data-i18n") or "").startswith("view.help.other")]
        # And the changes since the output before (stage X7 of v2.3.0).
        self.assertEqual(other, ["view.help.other", "view.help.other_plot", "view.help.other_spread", "view.help.other_shoes", "view.help.other_changes"])
        recap = [element.get("data-i18n") for element in self.elements if (element.get("data-i18n") or "").startswith("view.help.recap")]
        self.assertEqual(recap, ["view.help.recap", "view.help.recap_text"])
        conditions = [element.get("data-i18n") for element in self.elements if (element.get("data-i18n") or "").startswith("view.help.conditions")]
        self.assertEqual(conditions, ["view.help.conditions", "view.help.conditions_text"])
        save = [element.get("data-i18n") for element in self.elements if (element.get("data-i18n") or "").startswith("view.help.save")]
        self.assertEqual(save, ["view.help.save", "view.help.save_text"])
        for section in sections:
            with self.subTest(section=section.get("aria-labelledby")):
                self.assertEqual(by_id(self.elements, str(section.get("aria-labelledby"))).tag, "h3")

    def test_the_panels_drawn_by_the_script_are_named(self) -> None:
        # A chart is an image named by its item and period, which the keyboard
        # can reach; a table has a caption and heads of its columns and rows;
        # each tool of a panel names the item that it acts on.
        for line in (
            "plot.tabIndex = 0;",
            'plot.setAttribute("role", "img");',
            '"view.chart.label"',
            'const caption = element("caption", "visually-hidden",',
            'cell.scope = "col";',
            'period.scope = "row";',
            'wrap.setAttribute("aria-label", t("view.table.label", { name }));',
            'iconButton("expand", t("view.panel.big", { name }), "big", key)',
            'iconButton("up", t("view.panel.up", { name }), "up", key, index === 0)',
            'iconButton("down", t("view.panel.down", { name }), "down", key, index === count - 1)',
            'iconButton("close", t("view.panel.remove", { name }), "remove", key)',
            'tableButton.setAttribute("aria-pressed", String(table));',
            'button.setAttribute("aria-controls", notesId);',
            'read.setAttribute("aria-hidden", "true");',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
        self.assertRegex(self.script, r"const CROSS_KEYS = \{ ArrowLeft: -1, ArrowRight: 1, PageUp: -12, PageDown: 12 \};")

    def test_the_line_of_what_to_do_next_is_in_the_bar_of_the_app(self) -> None:
        # One row at the top, so that the panels keep the height, and the
        # filters in one row from a width of 1366 (the Human maintainer,
        # 2026-10-27).
        self.assertEqual(by_id(self.elements, "next-line").parent.get("class"), "view-title-row")
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertRegex(view, r"\.output-filter \{\s*flex: 1 1 320px;\s*min-width: 300px;\s*max-width: 430px;")

    def test_graphs_only_hides_the_rest_and_goes_back(self) -> None:
        # Graphs only (the Human maintainer, 2026-10-27): the parts around the
        # panels are hidden, and the panels, the time axis, and the overview
        # stay, under a line that says what they show; Esc, the button of that
        # line, and the browser's own end of its full screen go back, with the
        # focus on the button that went there.
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        rule = re.search(r"((?:\.view-app\.full \.[a-z-]+,\s*)+\.view-app\.full \.[a-z-]+) \{\s*display: none;", view)
        assert rule is not None
        hidden = re.findall(r"\.view-app\.full \.([a-z-]+)", rule.group(1))
        self.assertEqual(hidden, ["view-top", "filters", "filters-hint", "shelf", "rail", "caveat", "view-bar"])
        self.assertIn("hidden", by_id(self.elements, "full-bar").attributes)
        self.assertEqual(by_id(self.elements, "full-back").get("data-i18n"), "view.full.back")
        enter = re.search(r"function enterFull\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        leave = re.search(r"function leaveFull\(\) \{(.*?)\n\}", self.script, re.DOTALL)
        assert enter is not None and leave is not None
        self.assertIn("ui.fullBack.focus();", enter.group(1))
        # Back before the browser's full screen came leaves it again.
        self.assertIn("if (!state.full) {\n          leaveScreen();", enter.group(1))
        self.assertIn("ui.fullEnter.focus();", leave.group(1))
        # The browser takes the first Esc of its full screen: a drag of the
        # overview ends there, and does not choose a period afterwards.
        self.assertIn("  if (dragging) {\n    endDrag();\n  }", leave.group(1))
        # A stop hides the button that had the focus: the focus goes to the
        # heading of what shows instead.
        self.assertIn("[ui.seriesStopHeading, ui.stopHeading, ui.emptyHeading].find(", self.script)
        for line in (
            'document.addEventListener("fullscreenchange", () => {',
            "if (document.fullscreenElement === null && state.full) {",
            "} else if (state.full) {",
            "if (state.full && !showPanels) {",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)

    def test_the_pointer_says_what_a_drag_on_the_overview_does(self) -> None:
        # A new period where the pointer is a cross, an edge of the frame where
        # it is a double arrow, and the days in the label while it moves; a
        # drag selects no text of the page.
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        self.assertRegex(view, r"\.overview-plot \{[^}]*cursor: crosshair;")
        self.assertRegex(view, r"\.overview-plot\[data-grip\],\s*\.overview-plot\[data-drag\] \{\s*cursor: ew-resize;")
        self.assertRegex(view, r"\.overview \{[^}]*user-select: none;")
        for line in (
            'ui.overviewPlot.addEventListener("pointermove", overviewMove);',
            "ui.overviewPlot.dataset.grip = grip;",
            'ui.overviewPlot.dataset.drag = drag.grip ?? "new";',
            't("view.overview_range", {',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)


class GuiStyleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
        self.themes = theme_colors()

    def test_every_color_variable_is_defined_in_both_themes(self) -> None:
        # The view page uses the colors of styles.css only (stage G3b).
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        used = set(re.findall(r"var\(--([a-z0-9-]+)\)", self.source + view))
        light = theme_colors()["light"]
        self.assertEqual(sorted(used - set(light)), [])
        self.assertNotRegex(view, r"--[a-z0-9-]+:")
        self.assertLessEqual({"d1", "d2", "grid", "axis", "cross", "zero"}, set(light))
        # The dark theme sets every color, so none falls back to a light one,
        # where the browser reports dark and where the person chose Dark
        # (stage G3a).
        for pattern in (DARK_FOR_THE_BROWSER, DARK_FOR_THE_CHOICE):
            with self.subTest(pattern=pattern):
                block = re.search(pattern, self.source, re.MULTILINE | re.DOTALL)
                assert block is not None
                self.assertEqual(sorted(re.findall(r"--([a-z0-9-]+):", block.group(1))), sorted(light))

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
        light = re.search(LIGHT_CHOSEN, self.source, re.MULTILINE | re.DOTALL)
        assert light is not None
        self.assertEqual(declarations(light.group(1)), {"color-scheme": "light"})
        root = re.search(LIGHT_COLORS, self.source, re.MULTILINE | re.DOTALL)
        assert root is not None
        self.assertEqual(declarations(root.group(1))["color-scheme"], "light dark")

    def test_only_the_box_of_a_picture_takes_the_light_colors_beside_the_page(self) -> None:
        # Stage R1 of v2.2.0: the box out of the page that a picture of the
        # view page is made in takes the light colors and their color scheme
        # with data-theme="light" (Codex's simpler form of the plan); the
        # attribute on any other element changes no color.
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        rules = re.sub(r"/\*.*?\*/", "", self.source + view, flags=re.DOTALL)
        themed = {
            part.strip()
            for selectors in re.findall(r"([^{};]+)\{", rules)
            for part in selectors.split(",")
            if "data-theme" in part
        }
        self.assertEqual(
            themed,
            {
                ':root[data-theme="light"]',
                '.save-stage[data-theme="light"]',
                ':root:not([data-theme="light"])',
                ':root[data-theme="dark"]',
            },
        )
        for pattern in (LIGHT_COLORS, LIGHT_CHOSEN):
            with self.subTest(pattern=pattern):
                self.assertIsNotNone(re.search(pattern, self.source, re.MULTILINE | re.DOTALL))

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
            for pairs, minimum in ((TEXT_PAIRS, 4.5), (CONTROL_PAIRS, 3.0), (CHART_PAIRS, 3.0)):
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

    def test_the_charts_keep_their_marks_where_the_system_forces_its_colors(self) -> None:
        # Stage G3b: where the system forces its own colors, the marks take
        # the color of the text, the later series of VO2 Max that of links, and
        # the light marks that of gray text; the dashes of the sports are
        # attributes of the lines, which stay.
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        forced = view.split("@media (forced-colors: active) {", 1)
        self.assertEqual(len(forced), 2)
        block = forced[1]
        for rule in (
            r"\.chart-bar\.c1,[^{]*\{\s*fill: CanvasText;",
            r"\.chart-bar\.c2 \{\s*fill: LinkText;",
            r"\.chart-line\.c1,[^{]*\{\s*stroke: CanvasText;",
            r"\.chart-line\.c2,[^{]*\{\s*stroke: LinkText;",
            r"\.chart-bar\.partial \{\s*fill: GrayText;",
            r"\.chart-zero,[^{]*\{\s*stroke: GrayText;",
            r"\.chart-cross,[^{]*\{\s*stroke: Highlight;",
            r"\.overview-handle\.on \{\s*fill: Highlight;",
            # Stage L1 of v2.2.0: the years in the color of the text, the older
            # ones dashed, and a cut bar hollow with an edge; from stage L3, a
            # dash cut square, as long as its round end drew it.
            r"\.chart-line\.y6,[^{]*\{\s*stroke: CanvasText;",
            r"\.chart-line\.y5,\s*\.key-line\.y5 \{\s*stroke-dasharray: 10 1;\s*stroke-linecap: butt;",
            r"\.chart-bar\.partial\.outlined \{\s*fill: Canvas;\s*stroke: CanvasText;",
            # Stage M3 of v2.2.0: the frame of the period of the list keeps
            # its edge.
            r"\.list-frame \{\s*fill: none;\s*stroke: Highlight;",
        ):
            with self.subTest(rule=rule):
                self.assertRegex(block, rule)
        script = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.assertIn('"stroke-dasharray": dash', script)

    def test_the_lines_of_the_years_have_colors_of_their_own_told_apart(self) -> None:
        # Stage L3 of v2.2.0: the lines of the years on one panel take colors of
        # their own (--year1 to --year6), the calendar the six steps of one hue
        # (--y1 to --y6). As a guide for the design, not a promise that thin
        # lines are told apart (Codex's review of the plan, 10), the closest
        # pair of the first four, newest first (the 6th to the 3rd steps), is 15
        # or more apart under normal vision and 8 or more under protanopia and
        # deuteranopia; tritanopia is left out. The design gives the numbers
        # that this test computes.
        design = " ".join((ROOT / "docs/gui_design.md").read_text(encoding="utf-8").split())
        gaps = {}
        for theme, colors in self.themes.items():
            first = [colors[f"year{step}"] for step in (6, 5, 4, 3)]
            for kind, least in (("normal", 15), ("protan", 8), ("deutan", 8)):
                gap = min(apart(one, other, kind) for one, other in itertools.combinations(first, 2))
                gaps[theme, kind] = f"{gap:.1f}"
                with self.subTest(theme=theme, kind=kind):
                    self.assertGreaterEqual(gap, least)
        self.assertIn(
            f"{gaps['light', 'normal']}, {gaps['light', 'protan']}, and {gaps['light', 'deutan']} on light, and "
            f"{gaps['dark', 'normal']}, {gaps['dark', 'protan']}, and {gaps['dark', 'deutan']} on dark.",
            design,
        )
        self.assertIn("each day of the output in one of up to six steps of one hue. The steps are", design)
        self.assertIn("The 5th and 6th years are dashed too, as in forced colors, where every year but the newest is;", design)
        light = self.themes["light"]
        self.assertIn(f"on light, the purple and the teal are {apart(light['year6'], light['year4'], 'tritan'):.1f} apart", design)
        # The 5th and 6th years (the 2nd and the 1st steps) dashed too, cut square
        # as long as their round ends drew them, two dashes apart; the first
        # four full lines. Where the system forces its colors, every dash of a
        # year is cut square (Codex's review of the plan, 6).
        view = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        normal, after = view.split("@media (forced-colors: active) {", 1)
        forced = after.split("\n}\n", 1)[0]
        for step in range(1, 7):
            with self.subTest(step=step):
                self.assertRegex(normal, rf"\.chart-line\.y{step},\s*\.chart-dots\.y{step},\s*\.key-line\.y{step} \{{\s*stroke: var\(--year{step}\);\s*\}}")
                self.assertRegex(normal, rf"\.chart-cross-dot\.y{step} \{{\s*fill: var\(--year{step}\);\s*\}}")
        dash = r"\.chart-line\.y(\d),\s*\.key-line\.y\1 \{\s*stroke-dasharray: ([\d ]+);\s*stroke-linecap: butt;\s*\}"
        self.assertEqual(dict(re.findall(dash, normal)), {"2": "10 1 4 1", "1": "3 2"})
        for step in (3, 4, 5, 6):
            with self.subTest(full=step):
                self.assertNotRegex(normal, rf"\.chart-line\.y{step}[^{{}}]*\{{[^{{}}]*stroke-dasharray")
        self.assertEqual(dict(re.findall(dash, forced)), {"5": "10 1", "4": "6 1", "3": "4 1", "2": "10 1 4 1", "1": "3 2"})
        # A year stood out: its line 3.5 px wide; the other years faint only by
        # the class of a year stood out, never in forced colors (Codex's review
        # of the plan, 7, and the checker's review of its handling).
        self.assertRegex(normal, r"\.compare-marks\.lit \.chart-line \{\s*stroke-width: 3\.5;\s*\}")
        self.assertRegex(normal, r"\.compare-marks\.dim,\s*\.compare-label\.dim,\s*\.chart-cross-dot\.dim \{\s*opacity: 0\.28;\s*\}")
        self.assertRegex(forced, r"\.compare-marks\.dim,\s*\.compare-label\.dim,\s*\.chart-cross-dot\.dim \{\s*opacity: 1;\s*\}")
        rules = re.sub(r"/\*.*?\*/", "", view, flags=re.DOTALL)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", rules):
            if re.search(r"(?:^|;)\s*opacity:", body) and re.search(r"compare-marks|compare-label|chart-cross-dot|chart-line", selectors):
                with self.subTest(rule=selectors.strip()):
                    self.assertTrue(all(".dim" in part for part in selectors.split(",")))
        # While a year stands out, the others fall under 3:1, as the design
        # says with the lowest of each theme; and its numbers are those of the
        # page and of the pointer.
        lowest = {
            theme: min(contrast(faded(colors[f"year{step}"], colors["surface"], 0.28), colors["surface"]) for step in range(1, 7)) for theme, colors in self.themes.items()
        }
        self.assertLess(max(lowest.values()), 3)
        self.assertIn(f"the other lines fall under 3:1 on the surface ({lowest['light']:.2f} : 1 on light and {lowest['dark']:.2f} : 1 on dark for the lowest)", design)
        self.assertIn("its line 3.5 px wide and drawn last, and the other years at 0.28 opacity", design)
        self.assertIn("or on the chart within 8 px of what the line of a year draws", design)
        self.assertIn("export const HIT_REACH = 8;", (STATIC_ROOT / "view_chart.mjs").read_text(encoding="utf-8"))

    def test_motion_can_be_reduced(self) -> None:
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.source)

    def test_the_contrast_formula_matches_known_values(self) -> None:
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#ffffff", "#ffffff"), 1.0)
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), 4.54, places=2)


if __name__ == "__main__":
    unittest.main()
