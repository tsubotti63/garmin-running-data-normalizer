"""Saving the panels of the view page as an image (stage R1 of v2.2.0).

The page makes one SVG file from its own charts and hands it to the browser
as a download: nothing is sent anywhere, the Content-Security-Policy of the
server stays as it is, and the colors and the letters of the page are written
into the file. These tests hold the page, its styles, and its script to the
plan of R1; the file itself is checked on the real page.
"""
from __future__ import annotations

import json
import re
import unittest

from tests.test_gui_accessibility import STATIC_ROOT, by_id, page

SERVER = STATIC_ROOT.parents[0] / "server.py"
# The classes of the words of a picture, which take their colors as the
# charts do.
SAVE_WORDS = {"save-surface", "save-name", "save-unit", "save-kind", "save-key", "save-footer", "save-empty"}


def function_body(script: str, name: str) -> str:
    found = re.search(rf"function {name}\(.*?\) \{{(.*?)\n\}}", script, re.DOTALL)
    assert found is not None, name
    return found.group(1)


def catalog(language: str) -> dict[str, str]:
    return json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))


class GuiViewSaveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.elements = page("view.html")
        self.script = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        self.css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")

    def test_the_button_follows_the_summary_and_opens_a_window_of_its_choices(self) -> None:
        # The order of the row that OP0 decided: other views, the summary, and
        # saving as an image.
        row = by_id(self.elements, "caveat")
        children = [element.get("id") or element.get("class") for element in self.elements if element.parent is row]
        self.assertEqual(children[children.index("recap-open") + 1], "save-open")
        button = by_id(self.elements, "save-open")
        self.assertEqual(
            (button.get("type"), button.get("aria-controls"), button.get("aria-expanded"), button.get("data-i18n")),
            ("button", "save-pop", "false", "view.save.button"),
        )
        window = by_id(self.elements, "save-pop")
        self.assertIs(window.parent, row)
        self.assertEqual((window.get("role"), window.get("aria-labelledby")), ("dialog", "save-pop-title"))
        self.assertIn("hidden", window.attributes)
        self.assertEqual(by_id(self.elements, "save-pop-title").get("tabindex"), "-1")
        # The choices in their groups; the first ones checked: all the panels,
        # the light colors, and no marks.
        legends = [element.get("data-i18n") for element in self.elements if element.tag == "legend" and window in element.ancestors()]
        self.assertEqual(legends, ["view.save.scope", "view.save.colors", "view.save.marks"])
        for name, group, checked in (
            ("save-all", "save-scope", True),
            ("save-one", "save-scope", False),
            ("save-light", "save-colors", True),
            ("save-screen", "save-colors", False),
        ):
            with self.subTest(field=name):
                field = by_id(self.elements, name)
                self.assertEqual((field.get("type"), field.get("name"), "checked" in field.attributes), ("radio", group, checked))
        marks = by_id(self.elements, "save-marks")
        self.assertEqual(marks.get("type"), "checkbox")
        self.assertNotIn("checked", marks.attributes)
        # The line before a saving in the band of a warning, with its icon;
        # why a saving cannot be done, in a live region of the window; then
        # cancel and save.
        self.assertIn("part-note", by_id(self.elements, "save-warn").parent.get("class"))
        problem = by_id(self.elements, "save-problem")
        self.assertEqual((problem.get("role"), problem.get("aria-live")), ("status", "polite"))
        buttons = [element.get("id") for element in self.elements if element.tag == "button" and window in element.ancestors()]
        self.assertEqual(buttons, ["save-pop-close", "save-cancel", "save-go"])
        self.assertEqual(by_id(self.elements, "save-go").get("class"), "primary")
        # The line after a saving is in the bar at the bottom, beside the line
        # of the settings, not in the line of the loading (the checker's R1-3).
        status = by_id(self.elements, "save-status")
        self.assertEqual((status.get("role"), status.get("aria-live")), ("status", "polite"))
        settings = by_id(self.elements, "settings-status")
        bar = [element.get("id") for element in self.elements if element.parent is settings.parent]
        self.assertEqual(bar[bar.index("settings-status") + 1], "save-status")

    def test_the_words_before_and_after_a_saving_are_those_of_the_sample(self) -> None:
        # The line before a saving as the sample of R0 showed it, and the
        # names of the marks where they go in.
        ja, en = catalog("ja"), catalog("en")
        self.assertEqual(ja["view.save.warn"], "画像には日付と値（個人のデータ）が写ります。このパソコンのダウンロードの場所に保存し、どこへも送りません。")
        self.assertEqual(ja["view.save.warn_marks"], "印の名前も写ります。")
        self.assertEqual(en["view.save.warn"], "The image shows dates and values (your personal data). It is saved in the downloads place of this computer and sent nowhere.")
        self.assertEqual(en["view.save.warn_marks"], "The names of the marks show too.")
        # The page cannot know that the browser saved the file: the line
        # after a saving says that it was handed to the browser.
        self.assertEqual(ja["view.save.notice"], "画像のファイルをブラウザーに渡しました。ダウンロードの場所を見てください。")
        self.assertNotIn("saved", en["view.save.notice"].lower())
        body = function_body(self.script, "renderSave")
        self.assertIn('setText(ui.saveWarn, ui.saveMarks.checked ? `${warn}${state.language === "ja" ? "" : " "}${t("view.save.warn_marks")}` : warn);', body)

    def test_the_window_opens_with_the_first_choices_one_window_at_a_time(self) -> None:
        held = {
            # Nothing remembers the choices, so that the names of the marks do
            # not go in as chosen before (the plan of R1).
            "openSave": (
                'state.saveScope = "all";',
                "state.savePanel = null;",
                'state.saveColors = "light";',
                "state.saveMarks = false;",
                "state.saveNotice = null;",
                "state.recapOpen = false;",
                "  if (state.marksOpen) {\n      state.marksOpen = false;",
                "(open ? ui.saveTitle : ui.saveOpen).focus();",
            ),
            "openRecap": ("    state.saveOpen = false;",),
            "openMarks": ("    state.saveOpen = false;",),
            # The window shows where that of the summary can; the button of
            # saving waits for an answer not on its way (Codex's review of
            # the plan of R1).
            "renderSave": (
                "const showable = recapShowable(viewing);",
                "ui.saveOpen.disabled = !viewing || !state.items.length;",
                "ui.savePop.hidden = !state.saveOpen || !showable;",
                "const { plan, ready } = saveReady(viewing);",
                "ui.saveGo.disabled = !ready;",
                # No marks chosen where the page draws none, so that their
                # names never go in as chosen before (Codex's review of the
                # diff of R1).
                "  if (!plan.marksDrawn) {\n    // Chosen again where marks show again, so that their names never go in\n    // as chosen before (Codex's review of the diff of R1).\n    state.saveMarks = false;\n  }",
                "ui.saveMarks.disabled = !plan.marksDrawn;",
                "ui.saveMarks.checked = plan.marksDrawn && state.saveMarks;",
                'setText(ui.saveName, plan.name ?? "—");',
                'const gone = state.saveScope === "one" && plan.chosen !== null && !plan.charts.includes(plan.chosen);',
                "ui.savePanel.selectedIndex = -1;",
                'const problem = state.saveProblem ?? (gone ? "view.save.gone" : null);',
                "fitSaveWindow();",
            ),
            "saveReady": (
                "plan.keys.every((key) => savedChart(key) !== null)",
                "loading: state.loading,",
                "stopped: state.seriesStop !== null,",
                "answer: state.answer,",
            ),
            # The panels in the order shown, the one made big first, without
            # the tables; the days of the answer (Codex's review of the plan).
            "savePlan": (
                "const shown = shownPanels().map((entry) => entry.key);",
                'const tables = shown.filter((key) => state.tables.has(key) && panelMode(key) !== "mini");',
                "const keys = savedPanels(shown, tables, state.saveScope, chosen);",
                "const days = saveDays(state.answer);",
                "name: days === null ? null : saveFileName(days.start, days.end, keys),",
                # The panel chosen stays chosen where it no longer shows, so
                # that a picture never takes another panel unseen.
                "const chosen = state.savePanel ?? charts[0] ?? null;",
            ),
        }
        for name, lines in held.items():
            body = function_body(self.script, name)
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body)
        # The window after the panels, as it reads their charts (Codex's
        # review of the diff of R1).
        stage = function_body(self.script, "renderStage")
        self.assertLess(stage.index("    renderPanels();"), stage.index("  renderSave(viewing);\n  renderSaveNotice();"))
        self.assertEqual(stage.count("renderSave("), 1)
        # One panel is the panel the list shows when it is chosen, which
        # stays chosen (Codex's review of the diff of R1).
        self.assertIn('ui.saveOne.addEventListener("change", () => changeSave({ saveScope: "one", savePanel: state.savePanel ?? (ui.savePanel.value || null) }));', self.script)
        self.assertRegex(
            self.script,
            r'ui\.savePop\.addEventListener\("keydown", \(event\) => \{\s*if \(event\.key === "Escape"\) \{\s*event\.preventDefault\(\);\s*openSave\(false\);',
        )

    def test_the_line_after_a_saving_stays_until_what_it_is_said_of_changes(self) -> None:
        # Not in the line of the loading, which every drawing writes again
        # (the checker's R1-3).
        notice = function_body(self.script, "renderSaveNotice")
        self.assertIn("state.saveNotice !== saveNoticeNow()", notice)
        self.assertIn('setText(ui.saveStatus, state.saveNotice === null ? "" : t("view.save.notice"));', notice)
        self.assertNotIn("ui.loading", notice)
        stage = function_body(self.script, "renderStage")
        self.assertIn('setText(ui.loading, state.loading && viewing ? t("view.loading") : "");', stage)
        self.assertNotIn("save", re.search(r"setText\(ui\.loading.*", stage).group(0))
        now = function_body(self.script, "saveNoticeNow")
        for part in ("ticket: state.view?.view ?? null,", "period: periodRequest(state.period, state.range),", "types: typesRequest(state.counted, state.view?.types),", "items: state.items,", "language: state.language,"):
            with self.subTest(part=part):
                self.assertIn(part, now)

    def test_a_saving_is_done_in_the_press_of_the_button_and_sends_nothing(self) -> None:
        self.assertNotIn("async function saveImage", self.script)
        body = function_body(self.script, "saveImage")
        # Nothing between the press and the download (the checker's R1-4).
        before = body[: body.index("link.click();")]
        for word in ("await", "requestAnimationFrame", "setTimeout", "queueMicrotask", ".then("):
            with self.subTest(word=word):
                self.assertNotIn(word, before)
        for line in (
            'new Blob([file], { type: "image/svg+xml;charset=utf-8" })',
            "link.download = plan.name;",
            "} finally {\n      stage?.remove();",
            "setTimeout(() => URL.revokeObjectURL(taken), 10000);",
            # Checked again as the window names it; where it cannot be done,
            # the window stays with the reason and the focus on its button
            # (Codex's review of the plan of R1).
            "plan.name !== ui.saveName.textContent",
            'problem = "view.save.gone";',
            'problem = "view.save.changed";',
            'problem = "view.save.failed";',
            "(problem === null ? ui.saveOpen : ui.saveGo).focus();",
            "state.saveNotice = saveNoticeNow();",
        ):
            with self.subTest(line=line):
                self.assertIn(line, body)
        for name in ("saveImage", "saveFile", "savePart", "saveWords", "writeSaveStyles", "saveStage", "savePlan", "saveReady", "renderSave", "renderSaveNotice", "openSave", "changeSave"):
            part = function_body(self.script, name)
            for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "callApi", "callWithKey", "innerHTML", "insertAdjacentHTML", "outerHTML", "applyTheme", "rememberTheme", "changeTheme", "writeStorage"):
                with self.subTest(function=name, word=word):
                    self.assertNotIn(word, part)

    def test_a_picture_holds_everything_before_its_styles_are_written_once(self) -> None:
        body = function_body(self.script, "saveFile")
        # The names of the marks written again on its top chart, then the
        # styles once (Codex's review of the plan of R1).
        self.assertIn("const marks = state.saveMarks && plan.marksDrawn;", body)
        self.assertIn("marks && index === 0 && key !== namedKey", body)
        self.assertLess(body.index("appendMarkNames("), body.index("writeSaveStyles(svg);"))
        self.assertEqual(body.count("writeSaveStyles("), 1)
        self.assertIn("const drop = [...SAVE_LEFT_OUT, ...(marks ? [] : SAVE_MARKS)].join(\", \");", body)
        self.assertIn('return `<?xml version="1.0" encoding="UTF-8"?>\\n${new XMLSerializer().serializeToString(svg)}`;', body)
        self.assertIn("const heading = panelHeading(key, entry.item, entry.panel, answer.grain, entry.mode);", body)
        self.assertIn("answerTypes: state.answerTypes,", body)
        self.assertIn("grain: answer.grain,", body)
        # The words of the heading are those of the page (the checker's
        # answer 2 of the plan of R1).
        self.assertIn("const words = panelHeading(key, item, panel, grain, mode);", function_body(self.script, "buildPanel"))
        heading = function_body(self.script, "panelHeading")
        self.assertIn('kind: full ? t(kindKey(item, grain)) : null,', heading)
        # A part keeps what the page shows outside its view box (the
        # checker's R1-2).
        self.assertIn('overflow: "visible"', function_body(self.script, "savePart"))
        # The frame of the picture grows to what its parts show out of their
        # frames, before its styles are written (Codex's review of the diff).
        for line in (
            "const frame = saveFrame(boxes, SAVE_WIDTH, Math.ceil(y));",
            'svg.setAttribute("viewBox", `${frame.x} ${frame.y} ${frame.width} ${frame.height}`);',
            "ground.setAttribute(name, String(value));",
        ):
            with self.subTest(line=line):
                self.assertIn(line, body)
        self.assertLess(body.index("saveFrame("), body.index("writeSaveStyles(svg);"))
        styles = function_body(self.script, "writeSaveStyles")
        for line in (
            "for (const [attribute, value] of savedAttributes(values, around)) {",
            'node.removeAttribute("class");',
            'node.removeAttribute("style");',
            'svg.setAttribute("font-family", font);',
        ):
            with self.subTest(line=line):
                self.assertIn(line, styles)

    def test_every_property_of_the_charts_is_written_into_a_picture(self) -> None:
        # Those of the shapes and the words of the charts, the time axis, the
        # keys, and the words of a picture, so that none is missed where a
        # style is added (the checker's R1-1).
        block = re.search(r"export const SAVE_ATTRIBUTES = \[(.*?)\];", self.flow, re.DOTALL)
        assert block is not None
        written = set(re.findall(r'\["([a-z-]+)", "[a-z-]+"\]', block.group(1)))
        rules = re.sub(r"/\*.*?\*/", "", self.css, flags=re.DOTALL)
        used: set[str] = set()
        for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", rules):
            classes = re.findall(r"\.([a-z][a-z0-9-]*)", selectors)
            if any(name.startswith(("chart-", "day-", "axis-", "key-")) or name in SAVE_WORDS for name in classes):
                used.update(re.findall(r"(?:^|;)\s*([a-z-]+)\s*:", declarations))
        self.assertEqual(sorted(used - written - {"display"}), [])
        self.assertLessEqual({"fill", "stroke", "paint-order", "font-variant-numeric", "font-weight"}, used)

    def test_the_words_of_a_picture_take_the_colors_of_the_system_after_their_own(self) -> None:
        # Where the system forces its colors, the ground and the words of a
        # picture take them as its charts do; the rule comes after the
        # colors of the page, as it wins only so (Codex's review of the plan).
        last = self.css.rindex("@media (forced-colors: active) {")
        self.assertLess(self.css.index(".save-surface {\n  fill: var(--surface);\n}"), last)
        forced = self.css[last:]
        self.assertIn(".save-surface {\n    fill: Canvas;\n  }", forced)
        self.assertRegex(forced, r"\.save-name,\s*\.save-unit,\s*\.save-kind,\s*\.save-key,\s*\.save-footer,\s*\.save-empty \{\s*fill: CanvasText;")
        self.assertRegex(self.css, r"\.save-stage \{\s*position: fixed;\s*top: 0;\s*left: -100000px;\s*width: 1200px;\s*pointer-events: none;\s*\}")

    def test_only_the_root_of_the_page_and_the_box_of_a_picture_have_data_theme(self) -> None:
        # Another element with data-theme would take the light colors inside
        # it (the checker's answer 5 of the plan of R1).
        writes = []
        for path in sorted([*STATIC_ROOT.glob("*.mjs"), *STATIC_ROOT.glob("*.js")]):
            for line in path.read_text(encoding="utf-8").splitlines():
                if re.search(r'dataset\.theme\s*=|delete [^;]*dataset\.theme|setAttribute\("data-theme"|removeAttribute\("data-theme"', line):
                    writes.append((path.name, line.strip()))
        self.assertEqual(
            sorted(writes),
            sorted(
                [
                    ("theme.js", "document.documentElement.dataset.theme = choice;"),
                    ("app.mjs", "delete document.documentElement.dataset.theme;"),
                    ("app.mjs", "document.documentElement.dataset.theme = attribute;"),
                    ("view.mjs", "delete document.documentElement.dataset.theme;"),
                    ("view.mjs", "document.documentElement.dataset.theme = attribute;"),
                    ("view.mjs", 'stage.dataset.theme = "light";'),
                ]
            ),
        )
        self.assertIn('stage.dataset.theme = "light";', function_body(self.script, "saveStage"))

    def test_the_server_keeps_its_content_security_policy(self) -> None:
        # The download needs no change of it (the plan of R1).
        self.assertIn(
            '        "default-src \'none\'; script-src \'self\'; style-src \'self\'; "\n'
            '        "connect-src \'self\'; img-src \'self\'; frame-ancestors \'none\'; "\n'
            '        "base-uri \'none\'; form-action \'none\'",\n',
            SERVER.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
