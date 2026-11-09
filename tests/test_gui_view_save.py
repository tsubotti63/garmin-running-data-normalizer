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
SAVE_WORDS = {"save-surface", "save-name", "save-title", "save-unit", "save-kind", "save-key", "save-footer", "save-caption", "save-empty"}


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
        # The window is out of that row, in the stage right after it, so that
        # the bars of the other views open it too (stage R2; the checker's
        # R2-1).
        window = by_id(self.elements, "save-pop")
        stage = by_id(self.elements, "stage")
        self.assertIs(window.parent, stage)
        order = [element.get("id") or element.get("class") for element in self.elements if element.parent is stage]
        self.assertEqual(order[order.index("caveat") + 1], "save-pop")
        self.assertEqual((window.get("role"), window.get("aria-labelledby")), ("dialog", "save-pop-title"))
        self.assertIn("hidden", window.attributes)
        self.assertEqual(by_id(self.elements, "save-pop-title").get("tabindex"), "-1")
        # The choices in their groups; the first ones checked: all the panels,
        # the light colors, and no marks.
        legends = [element.get("data-i18n") for element in self.elements if element.tag == "legend" and window in element.ancestors()]
        # From v2.3.0 (stage X5), the format, and the size of a PNG: SVG and
        # 4:5 first.
        self.assertEqual(legends, ["view.save.scope", "view.save.colors", "view.save.marks", "view.save.format_choice", "view.save.size"])
        for name, group, checked in (
            ("save-all", "save-scope", True),
            ("save-one", "save-scope", False),
            ("save-light", "save-colors", True),
            ("save-screen", "save-colors", False),
            ("save-svg", "save-format", True),
            ("save-png", "save-format", False),
            ("save-size-4x5", "save-size", True),
            ("save-size-1x1", "save-size", False),
            ("save-size-9x16", "save-size", False),
        ):
            with self.subTest(field=name):
                field = by_id(self.elements, name)
                self.assertEqual((field.get("type"), field.get("name"), "checked" in field.attributes), ("radio", group, checked))
        marks = by_id(self.elements, "save-marks")
        self.assertEqual(marks.get("type"), "checkbox")
        self.assertNotIn("checked", marks.attributes)
        # The sizes and the note of a PNG show only with PNG chosen, after the
        # marks and before the name of the file (stage X5 of v2.3.0).
        self.assertIn("hidden", by_id(self.elements, "save-size-field").attributes)
        self.assertEqual(by_id(self.elements, "save-format-note").get("data-i18n"), "view.save.format")
        note = by_id(self.elements, "save-png-note")
        self.assertEqual((note.get("class"), note.get("data-i18n"), "hidden" in note.attributes), ("note save-note", "view.save.png_note", True))
        sizes = by_id(self.elements, "save-size-field")
        self.assertEqual(
            [element.get("data-i18n") for element in self.elements if element.tag == "label" and sizes in element.ancestors()],
            ["view.save.size_4x5", "view.save.size_1x1", "view.save.size_9x16"],
        )
        # The line before a saving in the band of a warning, with its icon;
        # why a saving cannot be done, in a live region of the window; then
        # cancel and save.
        self.assertIn("part-note", by_id(self.elements, "save-warn").parent.get("class"))
        problem = by_id(self.elements, "save-problem")
        self.assertEqual((problem.get("role"), problem.get("aria-live")), ("status", "polite"))
        # From v2.3.0 (stage X2, G1 and H1 of the checker's reviews of its
        # plan): the line before a saving comes right under what the window
        # saves, above the choices; the marks that the choice of the panels
        # puts in are said under that choice; and the end of the window, why
        # it cannot save and the buttons, is a part of its own, the last one.
        parts = [element.get("id") or element.get("class") for element in self.elements if element.parent is window]
        self.assertEqual(parts[parts.index("save-what") + 1], "part-note save-warn")
        self.assertLess(parts.index("part-note save-warn"), parts.index("save-scope-field"))
        self.assertEqual(parts[-1], "save-end")
        self.assertEqual(
            parts[parts.index("save-marks-field") : parts.index("save-marks-field") + 6],
            ["save-marks-field", "save-format-field", "save-size-field", "save-file", "save-format-note", "save-png-note"],
        )
        end = next(element for element in self.elements if element.parent is window and element.get("class") == "save-end")
        self.assertEqual([element.get("id") or element.get("class") for element in self.elements if element.parent is end], ["save-problem", "button-row"])
        field = by_id(self.elements, "save-marks-field")
        self.assertEqual([element.get("id") for element in self.elements if element.parent is field and element.tag == "p"], ["save-marks-none", "save-marks-warn"])
        said = by_id(self.elements, "save-marks-warn")
        self.assertEqual((said.get("class"), "hidden" in said.attributes), ("note save-note", True))
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

    def test_the_end_of_the_save_window_stays_at_its_bottom(self) -> None:
        # v2.3.0 X2 (F3, with G1 of the checker's review of its plan): at
        # 1366x650 the buttons of the window were hidden in it until it was
        # scrolled. Its end, why it cannot save and the buttons, stays at the
        # bottom of the window while it scrolls, on the ground of the window,
        # with a padding above the buttons in place of the margin that they
        # have elsewhere (through which the choices showed); a field that
        # takes the focus scrolls above that end at its tallest.
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        window = re.search(r"\n\.save-pop \{\n(.*?)\n\}\n", css, re.DOTALL)
        assert window is not None
        self.assertIn("  overflow: auto;\n", window.group(1))
        # The end holds the room under its buttons, in place of the padding
        # of the window, where what scrolls showed under the end (it stays
        # inside the padding of the window); the scroll padding is the height
        # of the end at its tallest, that room in it.
        self.assertIn("  padding-bottom: 0;\n", window.group(1))
        self.assertIn("  scroll-padding-bottom: 95px;\n", window.group(1))
        end = re.search(r"\n\.save-pop > \.save-end \{\n(.*?)\n\}\n", css, re.DOTALL)
        assert end is not None
        self.assertEqual(
            end.group(1).split("\n"),
            [
                "  position: sticky;",
                "  bottom: 0;",
                "  display: flex;",
                "  flex-direction: column;",
                "  gap: 8px;",
                "  padding-top: 8px;",
                "  padding-bottom: 10px;",
                "  background: var(--surface);",
            ],
        )
        self.assertRegex(css, r"\n\.save-pop > \.save-end > \.button-row \{\n  margin-top: 0;\n\}\n")
        # A note of a choice goes under it, on a line of its own, as the
        # design says (Codex's review of the diff of X2: the names of the
        # marks that a press puts in sat beside the choice where they fit).
        self.assertRegex(css, r"\n\.save-field > \.save-note \{\n  flex-basis: 100%;\n\}\n")
        # The design document says the order of the window and its end.
        design = " ".join((STATIC_ROOT.parents[3] / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        sentence = (
            "From v2.3.0 (stage X2) the window says what it saves and then the line before a saving, above its choices; "
            "the names of the marks that the choice of the panels puts in are said under that choice, so that a press does not move it; "
            "its end, why it cannot save and the buttons (`.save-end`), stays at the bottom of the window while it scrolls, "
            "where at 1366 × 650 the buttons were hidden in it; "
            "and the window opens at its top each time, also where it was scrolled before it closed."
        )
        self.assertEqual(design.count(sentence), 1)

    def test_the_words_before_and_after_a_saving_are_those_of_the_sample(self) -> None:
        # The line before a saving as the sample of R0 showed it, and the
        # names of the marks where they go in.
        ja, en = catalog("ja"), catalog("en")
        # v2.2.1 W3: the file goes to the browser, which saves it where its
        # settings say, as the guides say it.
        self.assertEqual(ja["view.save.warn"], "画像には日付と値（個人のデータ）が写ります。画像のファイルはブラウザーに渡し（保存する場所は、ブラウザーの設定のとおりです）、どこへも送りません。")
        self.assertEqual(ja["view.save.warn_marks"], "印の名前も写ります。")
        # v2.2.0 R3: the English words of the downloads, as the guides say
        # them (the checker's review (c) of R1).
        self.assertEqual(en["view.save.warn"], "The image shows dates and values (your personal data). Its file goes to the browser, which saves it where its settings say; it is sent nowhere.")
        self.assertEqual(en["view.save.warn_marks"], "The names of the marks show too.")
        # The page cannot know that the browser saved the file: the line
        # after a saving says that it was handed to the browser.
        self.assertEqual(ja["view.save.notice"], "画像のファイルをブラウザーに渡しました。ダウンロードの場所を見てください。")
        self.assertNotIn("saved", en["view.save.notice"].lower())
        self.assertEqual(en["view.save.notice"], "The image file was handed to the browser. Look in your downloads.")
        # What the window says where the picture to save is no longer the one
        # that it showed at the press, in the words of every view (the
        # checker's answer 3 of the plan of R3).
        self.assertEqual(ja["view.save.changed"], "保存する図が変わりました。ファイルの名前を見直して、もう一度「保存」を押してください。")
        self.assertEqual(en["view.save.changed"], "The picture to save changed. Check the file name and press Save again.")
        body = function_body(self.script, "renderSave")
        # And the view by shoes: the names of all its shoes (stage S1 of
        # v2.2.0, Codex's review of its plan).
        self.assertIn('const named = target.view === "shoes" ? t("view.save.warn_shoes") : !panels && target.marks ? t("view.save.warn_marks") : null;', body)
        # From v2.3.0 (stage X2, H1): the marks that the choice of the panels
        # puts in are said under that choice, so that a press does not move it.
        for line in (
            "const marked = panels && ui.saveMarks.checked;",
            "ui.saveMarksWarn.hidden = !marked;",
            'setText(ui.saveMarksWarn, marked ? t("view.save.warn_marks") : "");',
        ):
            with self.subTest(line=line):
                self.assertIn(line, body)
        self.assertIn('  saveMarksWarn: byId("save-marks-warn"),\n', self.script)
        # From T1, the words of the conditions of the answer drawn add to them
        # (Codex's review of the plan of T1).
        self.assertIn('const words = typeof drawnConditions(target.view)?.asked?.name === "string" ? t("view.save.warn_conditions") : null;', body)
        self.assertIn('setText(ui.saveWarn, [warn, named, words].filter((part) => part !== null).join(state.language === "ja" ? "" : " "));', body)
        # By race, always: the names of the races are those of the marks
        # (the checker's answer 5 of the plan of R2).
        self.assertIn("marks: race,", function_body(self.script, "saveCompareTarget"))

    def test_the_window_opens_with_the_first_choices_one_window_at_a_time(self) -> None:
        held = {
            # Nothing remembers the choices, so that the names of the marks do
            # not go in as chosen before (the plan of R1).
            "openSave": (
                'state.saveScope = "all";',
                "state.savePanel = null;",
                'state.saveColors = "light";',
                "state.saveMarks = false;",
                # SVG and 4:5 each time (stage X5 of v2.3.0).
                'state.saveFormat = "svg";',
                'state.saveSize = "4x5";',
                "state.saveNotice = null;",
                "state.recapOpen = false;",
                "  if (state.marksOpen) {\n      state.marksOpen = false;",
                "state.saveFrom = from;",
                "(open ? ui.saveTitle : saveButton(state.saveFrom)).focus();",
                # It opens at its top each time, also where it was scrolled
                # before it closed (stage X2 of v2.3.0: at 1366 x 650 a part
                # of the scrolling stayed), before the focus goes to its title.
                "  render();\n  // It opens at its top each time, also where it was scrolled before it\n  // closed (stage X2 of v2.3.0).\n"
                "  if (open) {\n    ui.savePop.scrollTop = 0;\n  }\n  (open ? ui.saveTitle : saveButton(state.saveFrom)).focus();",
            ),
            "openRecap": ("    state.saveOpen = false;",),
            "openMarks": ("    state.saveOpen = false;",),
            # The window shows where that of the summary can; the button of
            # saving waits for an answer not on its way (Codex's review of
            # the plan of R1).
            "renderSave": (
                # The window shows by the view of the button that opened it
                # (stage R2; for the panels as in R1: the node test of
                # saveWindowShows).
                "const showable = saveWindowShows({ viewing, from: state.saveFrom, view, items: state.items.length, full: state.full });",
                "if (state.saveOpen && state.saveFrom !== view) {\n    state.saveOpen = false;\n  }",
                "ui.saveOpen.disabled = !viewing || !state.items.length;",
                "ui.savePop.hidden = !state.saveOpen || !showable;",
                "const target = saveTarget(viewing);",
                "ui.saveGo.disabled = !target.ready;",
                # Save that had the focus and can no longer be pressed, after a
                # drawing again, gives it to the title of the window (Codex's
                # review of the diff of U1, 2).
                "const pressed = document.activeElement === ui.saveGo;",
                "if (pressed && ui.saveGo.disabled) {\n    ui.saveTitle.focus();\n  }",
                'setText(ui.saveName, target.name ?? "—");',
                # The format, the sizes of a PNG, and the note of each (stage
                # X5 of v2.3.0).
                'const png = state.saveFormat === "png";',
                "ui.saveSvg.checked = !png;",
                "ui.savePng.checked = png;",
                "ui.saveSizeField.hidden = !png;",
                "input.checked = input.value === state.saveSize;",
                "ui.saveFormatNote.hidden = png;",
                "ui.savePngNote.hidden = !png;",
                "const gone = panels ? renderSavePanels(target.plan) : false;",
                # A reason that a press kept, or what the window says by itself,
                # which a press goes by too (stage U1 of v2.2.0).
                "const problem = state.saveProblem ?? saveSaysNow(target, gone).line;",
                'setText(ui.saveProblem, problem !== null ? saveProblemText(problem) : "");',
                "fitSaveWindow();",
            ),
            "saveSaysNow": (
                "gone,",
                "problem: target.problem,",
                "loading: target.loading,",
                # Every panel shown a table, which their own line says (Codex's
                # review of the plan of U1, 1).
                "allTables: panels && !target.plan.charts.length && target.plan.tables.length > 0,",
            ),
            "renderSavePanels": (
                # No marks chosen where the page draws none, so that their
                # names never go in as chosen before (Codex's review of the
                # diff of R1).
                "  if (!plan.marksDrawn) {\n    // Chosen again where marks show again, so that their names never go in\n    // as chosen before (Codex's review of the diff of R1).\n    state.saveMarks = false;\n  }",
                "ui.saveMarks.disabled = !plan.marksDrawn;",
                "ui.saveMarks.checked = plan.marksDrawn && state.saveMarks;",
                "const gone = savePanelGone(plan);",
                "ui.savePanel.selectedIndex = -1;",
                "return gone;",
            ),
            "saveTarget": (
                "const { plan, ready } = saveReady(viewing);",
                # The name of a PNG has its size and .png (stage X5).
                "return { view, plan, ready, name: savePictureName(plan.name, state.saveFormat, state.saveSize), problem, loading: state.loading, marks: false };",
                "target.name = savePictureName(target.name, state.saveFormat, state.saveSize);",
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
        # The window after every view, as it reads their charts (Codex's
        # reviews of the diff of R1 and of the plan of R2).
        stage = function_body(self.script, "renderStage")
        self.assertIn("    renderPanels();", stage)
        self.assertNotIn("renderSave(", stage)
        drawing = function_body(self.script, "render")
        for before in ("  renderStage(live);", "  renderCompare(live);", "  renderPlot(live);", "  renderSpread(live);"):
            with self.subTest(before=before):
                self.assertLess(drawing.index(before), drawing.index("  renderSave(live && state.view !== null && state.opening === null);\n  renderSaveNotice();"))
        self.assertEqual(drawing.count("renderSave("), 1)
        # One panel is the panel the list shows when it is chosen, which
        # stays chosen (Codex's review of the diff of R1).
        self.assertIn('ui.saveOne.addEventListener("change", () => changeSave({ saveScope: "one", savePanel: state.savePanel ?? (ui.savePanel.value || null) }));', self.script)
        for line in (
            'ui.saveSvg.addEventListener("change", () => changeSave({ saveFormat: "svg" }));',
            'ui.savePng.addEventListener("change", () => changeSave({ saveFormat: "png" }));',
            'input.addEventListener("change", () => changeSave({ saveSize: input.value }));',
            'saveSizes: [byId("save-size-4x5"), byId("save-size-1x1"), byId("save-size-9x16")],',
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.script)
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
            # The SVG, or a PNG of the size chosen, which may not fit (stage X5
            # of v2.3.0): then nothing is saved, and the window says why.
            'const made = state.saveFormat === "png" ? savePng(stage, target) : saveSvg(stage, target);',
            "if (made.problem !== null) {\n        problem = made.problem;\n      } else {\n        address = URL.createObjectURL(made.blob);",
            "link.download = target.name;",
            "} finally {\n      stage?.remove();",
            "setTimeout(() => URL.revokeObjectURL(taken), 10000);",
            # Checked again as the window names it; where it cannot be done,
            # the window stays with the reason (Codex's review of the plan of
            # R1), none kept that the window says by itself, and the focus on
            # its button, or on its title where the button cannot be pressed,
            # while the window shows (stage U1 of v2.2.0, savePress).
            "const press = savePress({",
            'gone: panels && state.saveScope === "one" && !target.plan.keys.length,',
            "ready: target.ready,",
            "said: saveSaysNow(target, panels && savePanelGone(target.plan)).said,",
            "shown: ui.saveName.textContent,",
            "let problem = press.keep;",
            "if (press.save) {",
            'problem = "view.save.failed";',
            "const saved = press.save && problem === null;",
            "state.saveNotice = saveNoticeNow();",
            "if (saved) {\n    saveButton(state.saveFrom).focus();\n  } else if (!ui.savePop.hidden) {",
            "(ui.saveGo.disabled ? ui.saveTitle : ui.saveGo).focus();",
        ):
            with self.subTest(line=line):
                self.assertIn(line, body)
        self.assertIn('return { blob: new Blob([pictureXml(svg)], { type: "image/svg+xml;charset=utf-8" }), problem: null };', function_body(self.script, "saveSvg"))
        for name in (
            "saveImage", "saveFile", "savePart", "saveWords", "writeSaveStyles", "saveStage", "savePlan", "saveReady", "renderSave", "renderSaveNotice", "openSave", "changeSave",
            # Stage X5 of v2.3.0.
            "saveSvg", "savePng", "pictureLayout", "pictureFrame", "pictureXml", "redrawBox", "redrawn", "redrawPanel", "redrawCompare", "redrawCalendar", "redrawShoe",
            "redrawPlot", "redrawSpread", "redrawTimeAxis", "redrawCompareAxis", "axisMeasure", "paintItems", "paintShape", "paintPath", "paintColor", "paintAlpha", "pngBlob",
            # Stage R2.
            "saveTarget", "saveCompareTarget", "compareSaveTitle", "saveComparePart", "saveCalendarLegend", "savePlotTarget", "saveSpreadTarget", "saveNotesOf",
            "saveContent", "fitSaveWindow", "renderSavePanels", "saveProblemText", "saveViewFile", "saveNotes", "saveBegin", "saveEnd",
        ):
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
        self.assertLess(body.index("appendMarkNames("), body.index("return saveEnd(svg, ground, probe, y, footer, measure, layout);"))
        # The end that the panels and the other views share writes the
        # styles once (stage R2).
        end = function_body(self.script, "saveEnd")
        self.assertEqual(end.count("writeSaveStyles("), 1)
        for name in ("saveFile", "saveViewFile"):
            with self.subTest(function=name):
                self.assertEqual(function_body(self.script, name).count("writeSaveStyles("), 0)
                self.assertEqual(function_body(self.script, name).count("return saveEnd(svg, ground, probe, y"), 1)
        self.assertIn("const drop = [...SAVE_LEFT_OUT, ...(marks ? [] : SAVE_MARKS)].join(\", \");", body)
        # The file of an SVG made of the picture, a PNG painted from it (stage
        # X5 of v2.3.0).
        self.assertIn('return `<?xml version="1.0" encoding="UTF-8"?>\\n${new XMLSerializer().serializeToString(svg)}`;', function_body(self.script, "pictureXml"))
        self.assertIn("  writeSaveStyles(svg);\n  // The file of an SVG is made of it (pictureXml), a PNG painted from it\n  // (stage X5 of v2.3.0).\n  return svg;", end)
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
            "const frame = saveFrame(boxes, layout.width, Math.ceil(y));",
            'svg.setAttribute("viewBox", `${frame.x} ${frame.y} ${frame.width} ${frame.height}`);',
            "ground.setAttribute(name, String(value));",
        ):
            with self.subTest(line=line):
                self.assertIn(line, end)
        self.assertLess(end.index("saveFrame("), end.index("writeSaveStyles(svg);"))
        styles = function_body(self.script, "writeSaveStyles")
        for line in (
            "const own = SAVE_ATTRIBUTES.map(([, attribute]) => attribute).filter((attribute) => node.hasAttribute(attribute));",
            "for (const [attribute, value] of savedAttributes(values, around, own)) {",
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
        # And those of every class that the script gives a shape of SVG (the
        # attributes of svgElement), as those of the other views (Codex's
        # review of the plan of R2); of a class made in a template, the words
        # before it is made, as a class made of a number, as y1, goes with one
        # of them.
        shapes: set[str] = set()
        for match in re.finditer(r'\bclass: (?:"([^"]*)"|`([^`]*)`)', self.script):
            words = match.group(1) if match.group(1) is not None else match.group(2).split("${")[0]
            parts = words.split()
            if match.group(2) is not None and "${" in match.group(2) and words and not words[-1].isspace():
                parts = parts[:-1]
            shapes.update(parts)
        # The coverage of the shelf and the overview are never in a picture.
        shapes -= {name for name in shapes if name.startswith(("coverage", "overview-"))}
        self.assertLessEqual({"calendar-cell", "calendar-name", "compare-label", "plot-dot", "plot-axis", "key-line"}, shapes)
        used: set[str] = set()
        for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", rules):
            classes = re.findall(r"\.([a-z][a-z0-9-]*)", selectors)
            if any(name.startswith(("chart-", "day-", "axis-", "key-")) or name in SAVE_WORDS or name in shapes for name in classes):
                used.update(re.findall(r"(?:^|;)\s*([a-z-]+)\s*:", declarations))
        self.assertEqual(sorted(used - written - {"display"}), [])
        self.assertLessEqual({"fill", "stroke", "paint-order", "font-variant-numeric", "font-weight"}, used)

    def test_a_picture_keeps_a_year_stood_out(self) -> None:
        # Stage L3 of v2.2.0: a year stood out goes in as it shows, its marks on
        # the shapes themselves, which the box keeps (Codex's review of the
        # plan, 8), and its key bold, in the colors of the system where they
        # are forced; the line after a saving goes when another year stands
        # out (saveContent, above), but the window does not say that the
        # picture changed (Codex's review of the plan, 2).
        part = function_body(self.script, "saveComparePart")
        self.assertIn('const className = key.getAttribute("aria-pressed") === "true" ? "save-key lit" : "save-key";', part)
        # Stage U3 of v2.2.0: the words of a year in the color of its line,
        # stood out too, and in the colors of the system where they are forced.
        self.assertIn('const step = [...key.classList].find((name) => /^y[1-6]$/.test(name));', part)
        self.assertIn('pieces.push({ text: keyWords(key), className: step ? `${className} ${step}` : className, swatch: () => key.querySelector("svg").cloneNode(true) });', part)
        self.assertIn('.filter((node) => !node.classList?.contains("visually-hidden"))', function_body(self.script, "keyWords"))
        self.assertIn('const group = one ? svgElement("g", { class: "compare-marks" }) : svg;', function_body(self.script, "drawComparePlot"))
        self.assertRegex(self.css, r"\.save-key\.lit \{\s*fill: var\(--text\);\s*font-weight: 600;\s*\}")
        last = self.css.rindex("@media (forced-colors: active) {")
        self.assertIn(".save-key.lit,\n" + "".join(f"  .save-key.y{step},\n" for step in range(1, 6)) + "  .save-key.y6 {\n    fill: CanvasText;\n  }", self.css[last:])
        lit = self.css.index(".save-key.lit {")
        for step in range(1, 7):
            with self.subTest(step=step):
                rule = f".save-key.y{step} {{\n  fill: var(--year{step}-ink);\n}}"
                self.assertGreater(self.css.index(rule), lit)
        self.assertNotRegex(function_body(self.script, "saveImage"), r"\blit\b")

    def test_the_words_of_a_picture_take_the_colors_of_the_system_after_their_own(self) -> None:
        # Where the system forces its colors, the ground and the words of a
        # picture take them as its charts do; the rule comes after the
        # colors of the page, as it wins only so (Codex's review of the plan).
        last = self.css.rindex("@media (forced-colors: active) {")
        self.assertLess(self.css.index(".save-surface {\n  fill: var(--surface);\n}"), last)
        forced = self.css[last:]
        self.assertIn(".save-surface {\n    fill: Canvas;\n  }", forced)
        self.assertRegex(forced, r"\.save-name,\s*\.save-title,\s*\.save-unit,\s*\.save-kind,\s*\.save-key,\s*\.save-footer,\s*\.save-caption,\s*\.save-empty \{\s*fill: CanvasText;")
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


    # --- Saving the other views (stage R2 of v2.2.0) -----------------------

    def test_the_bars_of_the_other_views_open_the_one_window_right_after_their_table_buttons(self) -> None:
        # The place that the person chose from the sample (A, 2026-10-31):
        # right after "表で見る" in the first line of each bar.
        for view in ("compare", "plot", "spread", "shoes"):
            with self.subTest(view=view):
                button = by_id(self.elements, f"{view}-save")
                line = button.parent
                self.assertIn("compare-line", line.get("class"))
                self.assertIn(by_id(self.elements, view), line.ancestors())
                order = [element.get("id") or element.get("class") for element in self.elements if element.parent is line]
                self.assertEqual(order[order.index(f"{view}-table") + 1], f"{view}-save")
                self.assertEqual(
                    (button.get("type"), button.get("class"), button.get("aria-controls"), button.get("aria-expanded"), button.get("data-i18n")),
                    ("button", "small", "save-pop", "false", "view.save.button"),
                )
        self.assertIn(
            '  for (const each of ["compare", "plot", "spread", "shoes"]) {\n    saveButton(each).addEventListener("click", () => openSave(!(state.saveOpen && state.saveFrom === each), each));\n  }',
            self.script,
        )
        self.assertIn('ui.saveOpen.addEventListener("click", () => openSave(!(state.saveOpen && state.saveFrom === "panels"), "panels"));', self.script)
        # The window says what another view saves in one line, and hides the
        # choices that the panels only have (the plan of R2).
        window = by_id(self.elements, "save-pop")
        what = by_id(self.elements, "save-what")
        self.assertIs(what.parent, window)
        self.assertIn("hidden", what.attributes)
        for name in ("save-scope-field", "save-marks-field"):
            with self.subTest(field=name):
                self.assertEqual((by_id(self.elements, name).tag, by_id(self.elements, name).parent), ("fieldset", window))
        body = function_body(self.script, "renderSave")
        for line in (
            "ui.saveScopeField.hidden = !panels;",
            "ui.saveMarksField.hidden = !panels;",
            "ui.saveWhat.hidden = panels;",
            'setText(ui.saveWhat, panels ? "" : t("view.save.what", { name: target.title }));',
            "  for (const each of [\"compare\", \"plot\", \"spread\", \"shoes\"]) {\n    saveButton(each).disabled = !viewing;\n  }",
            'saveButton(each).setAttribute("aria-expanded", String(state.saveOpen && showable && state.saveFrom === each));',
            "const button = saveButton(state.saveFrom);",
        ):
            with self.subTest(line=line):
                self.assertIn(line, body)

    def test_the_window_is_placed_under_the_row_of_its_button_and_follows_it(self) -> None:
        # Under the row of its button at its right end, as under the row above
        # the panels in R1, placed again as the page draws, the window
        # changes its size, or a chart is drawn again; the width of R1
        # (Codex's review of the plan of R2, 7; the checker).
        self.assertIn('return view === "panels" ? ui.caveat : saveButton(view).closest(".compare-line");', function_body(self.script, "saveRow"))
        fit = function_body(self.script, "fitSaveWindow")
        for line in (
            "const row = saveRow(state.saveFrom).getBoundingClientRect();",
            "ui.savePop.style.top = `${row.bottom - stage.top + ui.stage.scrollTop}px`;",
            "ui.savePop.style.right = `${Math.max(0, right)}px`;",
            "if (stage.width - right - width < pad) {",
            # Not wider than the stage, which hides what goes out of it
            # (Codex's review of the diff of R2).
            "ui.savePop.style.maxWidth = `${Math.max(0, stage.width - 2 * pad)}px`;",
            "fitPop(ui.savePop);",
        ):
            with self.subTest(line=line):
                self.assertIn(line, fit)
        self.assertLess(fit.index("ui.savePop.style.maxWidth"), fit.index("const width = ui.savePop.getBoundingClientRect().width;"))
        self.assertIn("fitSaveWindow();", function_body(self.script, "renderSave"))
        self.assertIn('window.addEventListener("resize", fitSaveWindow);', self.script)
        self.assertRegex(self.css, r"\.save-pop \{\s*top: 0;\s*right: 0;\s*display: flex;\s*flex-direction: column;\s*gap: 8px;\s*width: 540px;\s*max-width: calc\(100vw - 32px\);")

    def test_the_window_reads_the_charts_after_they_are_drawn_and_never_draws_itself(self) -> None:
        # After the bodies of every view are drawn again, while it shows only,
        # so that the focus stays (Codex's review of the plan of R2, 1; the
        # checker's (i) and (ii)).
        redraw = function_body(self.script, "scheduleRedraw")
        self.assertIn("    if (state.saveOpen) {\n      renderSave(viewingNow());\n    }", redraw)
        for before in ("renderPanels();", "renderCompareBody();", "renderPlotBody(plotAnswerNow());", "renderSpreadBody(spreadAnswerNow());", "renderShoesBody(state.shoesAnswer);"):
            with self.subTest(before=before):
                self.assertLess(redraw.index(before), redraw.index("renderSave(viewingNow());"))
        for name in ("renderSave", "renderSavePanels", "saveTarget", "saveCompareTarget", "savePlotTarget", "saveSpreadTarget", "saveShoesTarget", "fitSaveWindow", "saveProblemText"):
            body = function_body(self.script, name)
            for word in ("render()", "scheduleRedraw(", "requestAnimationFrame"):
                with self.subTest(function=name, word=word):
                    self.assertNotIn(word, body)
            # Nothing in the window is made again where it does not change,
            # so that a drawing again keeps the focus in it (the checker's
            # (iii)): the list of the panels only where they change (R1).
            if name != "renderSavePanels":
                self.assertNotIn("replaceChildren(", body)
        panels = function_body(self.script, "renderSavePanels")
        self.assertEqual(panels.count("replaceChildren("), 1)
        self.assertLess(panels.index("if (ui.savePanel.dataset.signature !== signature) {"), panels.index("ui.savePanel.replaceChildren("))
        # The window goes with the view of its button.
        self.assertIn('return comparing() ? "compare" : plotting() ? "plot" : spreading() ? "spread" : shoesShown() ? "shoes" : "panels";', function_body(self.script, "saveViewNow"))

    def test_another_view_saves_its_answer_drawn_as_a_chart_or_says_why_not(self) -> None:
        target = function_body(self.script, "saveTarget")
        for line in (
            "const charts = target.parts.filter((part) => part.source !== null).length;",
            "saveViewNow() === view &&",
            "target.name !== null &&",
            "charts === target.parts.length &&",
            "saveViewReady({ answer: target.answer, loading: target.loading, stopped: target.stopped, table: target.table, charts });",
            # Why it cannot save, also for a stop, an answer without values,
            # and a chart without room (Codex's review of the diff of R2), and
            # so for the panels.
            "  target.problem = saveProblem({\n    table: target.table,\n    stopped: target.stopped,\n    loading: target.loading,\n    answer: target.answer,\n    empty: target.empty,\n    drawn: charts,\n    parts: target.parts.length,\n  });",
            "const drawn = plan.keys.filter((key) => savedChart(key) !== null).length;",
            "const problem = saveProblem({ stopped: state.seriesStop !== null, loading: state.loading, answer: state.answer, drawn, parts: plan.keys.length });",
        ):
            with self.subTest(line=line):
                self.assertIn(line, target)
        self.assertIn("empty: answer !== null && !answer.points.length,", function_body(self.script, "savePlotTarget"))
        self.assertIn("empty: answer !== null && !answer.counts.length,", function_body(self.script, "saveSpreadTarget"))
        # What a picture leaves out is taken out of the copy of a chart
        # (Codex's review of the diff of R2, 4; on the real page too).
        self.assertIn('  if (drop !== "") {\n    for (const node of copy.querySelectorAll(drop)) {\n      node.remove();\n    }\n  }', function_body(self.script, "savePart"))
        # The chart of the answer shown, not of one on its way or of another
        # pair or item (Codex's review of the plan of R2, 2).
        self.assertIn("const answer = compare !== null && state.compareAnswer !== null && state.compareAnswer.key === compare.key ? state.compareAnswer : null;", function_body(self.script, "saveCompareTarget"))
        self.assertIn('parts: shown ? compared.map((entry) => saveComparePart(entry, entry.kind === "calendar" ? redrawCalendar : redrawCompare)) : [],', function_body(self.script, "saveCompareTarget"))
        self.assertIn("const drawnNow = answer !== null && plotContext !== null && plotContext.answer === answer;", function_body(self.script, "savePlotTarget"))
        self.assertIn('source: drawnNow ? ui.plotBody.querySelector(".plot-points > svg") : null', function_body(self.script, "savePlotTarget"))
        self.assertIn("const drawnNow = answer !== null && spreadContext !== null && spreadContext.answer === answer;", function_body(self.script, "saveSpreadTarget"))
        self.assertIn('source: drawnNow ? ui.spreadBody.querySelector(".spread-bars > svg") : null', function_body(self.script, "saveSpreadTarget"))
        # The table says how to show the chart again, with the name of its
        # button.
        problem = function_body(self.script, "saveProblemText")
        self.assertIn('const calendar = state.saveFrom === "compare" && compareModeNow() === "calendar";', problem)
        self.assertIn('return t(problem, { button: t(calendar ? "view.compare.table_calendar" : "view.panel.chart") });', problem)
        image = function_body(self.script, "saveImage")
        self.assertIn('const svg = target.view === "panels" ? saveFile(stage, target.plan) : saveViewFile(stage, target);', function_body(self.script, "saveSvg"))
        self.assertIn('const made = state.saveFormat === "png" ? savePng(stage, target) : saveSvg(stage, target);', image)
        self.assertIn("const target = saveTarget(viewingNow());", image)

    def test_a_picture_of_the_view_by_shoes_holds_all_its_rows_and_notes_and_no_name_in_its_file(self) -> None:
        # Stage S1 of v2.2.0 (Codex's review of its plan): every row of the
        # answer drawn, also those scrolled out of the screen; its axis; its
        # notes as the page shows them; the file named by its period and the
        # key of the distance, never by the shoes.
        target = function_body(self.script, "saveShoesTarget")
        for line in (
            "const shown = drawn !== null && !state.shoes.table && shoesDrawn !== null && shoesDrawn[0] === drawn;",
            "parts: shown ? shoeRows.map((entry) => saveComparePart(entry, redrawShoe)) : [],",
            'axis: shown && !ui.shoesAxis.hidden ? ui.shoesAxis.querySelector(":scope > svg") : null,',
            "notes: drawn === null ? [] : saveNotesOf([...ui.shoesNotes.children]),",
            'drop: SAVE_LEFT_OUT_VIEWS.shoes.join(", "),',
            'name: drawn === null ? null : saveViewFileName("shoes", { key: "dist", start: drawn.start, end: drawn.end }),',
            "empty: drawn !== null && !drawn.shoes.length,",
        ):
            with self.subTest(line=line):
                self.assertIn(line, target)
        self.assertIn('view === "spread" ? saveSpreadTarget() : saveShoesTarget();', function_body(self.script, "saveTarget"))
        ja, en = catalog("ja"), catalog("en")
        self.assertEqual(ja["view.save.warn_shoes"], "画面に出ていない段も含めて、すべての靴の名前が写ります。")
        self.assertEqual(en["view.save.warn_shoes"], "The names of all the shoes show too, also of the rows not on the screen.")

    def test_a_picture_of_another_view_holds_the_words_of_the_page(self) -> None:
        # The heads of the rows, the strips, and the one chart as the page
        # shows them, without the reading of the day chosen; the words of an
        # empty chart (Codex's review of the plan of R2, 4).
        part = function_body(self.script, "saveComparePart")
        for line in (
            'const head = entry.section.querySelector(entry.kind === "calendar" ? ".calendar-side" : ".panel-head");',
            'node.matches(".panel-unit, .compare-whole")',
            'swatch: () => key.querySelector("svg").cloneNode(true)',
            'source: entry.plot.querySelector(":scope > svg"),',
            'empty: entry.plot.querySelector(".panel-empty")?.textContent ?? null,',
        ):
            with self.subTest(line=line):
                self.assertIn(line, part)
        self.assertNotIn("read", part)
        # The legend of a calendar without where the page reads the values
        # (Codex's review of the plan of R2, 5).
        legend = function_body(self.script, "saveCalendarLegend")
        # Stage U3 of v2.2.0: its unit and its keys by name, never the button
        # of the notes or what it opens (the notes are under an info button
        # on the page), and the notes from what the calendar shows, under the
        # conditions of the page (calendarNotes, tested in gui_js).
        self.assertIn('} else if (node.matches(".calendar-unit")) {', legend)
        self.assertNotIn("} else {", legend)
        self.assertNotIn("calendar-note", legend)
        self.assertIn("const notes = steps === null ? [] : calendarNotes(steps, compareContext.total, state.language, true).map((note) => describe(note));", legend)
        self.assertIn("swatchSize: [12, 12]", legend)
        # The title in the words of the page (the checker's answer 3).
        title = function_body(self.script, "compareSaveTitle")
        for line in (
            't("view.compare.title_by", { item: itemName(answer.key), by: t(race ? "view.compare.by.race" : "view.compare.by.year") }),',
            'mode === "rows" && race ? t("view.compare.mode.rows_race") : t(`view.compare.mode.${mode}`),',
            'race ? t("view.compare.weeks_option", { n: answer.weeks }) : answer.month === null ? t("view.compare.month_all") : describe(compareSlotName(answer.month - 1, "month", null, state.language)),',
            "if (!ui.compareSeriesField.hidden && ui.compareSeries.selectedIndex >= 0) {",
            'return words.join(t("view.save.separator"));',
        ):
            with self.subTest(line=line):
                self.assertIn(line, title)
        compare = function_body(self.script, "saveCompareTarget")
        for line in (
            "const years = answer === null || race ? [] : answer.years;",
            "const days = answer === null || !race ? [] : answer.races.map((each) => each.day);",
            'name: answer === null ? null : saveViewFileName("compare", { key: answer.key, years, days }),',
            "answerTypes: answer.types,",
            'separator: t("view.spoken_separator"),',
            'daysSeparator: t("view.save.days_separator"),',
            'drop: SAVE_LEFT_OUT_VIEWS.compare.join(", "),',
            'axis: shown && !ui.compareAxis.hidden ? ui.compareAxis.querySelector(":scope > svg") : null,',
            "marks: race,",
        ):
            with self.subTest(line=line):
                self.assertIn(line, compare)
        plot = function_body(self.script, "savePlotTarget")
        self.assertIn('notes: [...saveNotesOf([ui.plotCount, ui.plotCut]), t("view.plot.caveat")],', plot)
        self.assertIn("answerTypes: asked.types,", plot)
        self.assertIn('drop: SAVE_LEFT_OUT_VIEWS.plot.join(", "),', plot)
        spread = function_body(self.script, "saveSpreadTarget")
        self.assertIn("notes: saveNotesOf([ui.spreadCount, ui.spreadWide, ui.spreadFaster]),", spread)
        self.assertIn("answerTypes: asked.types,", spread)
        self.assertIn('drop: SAVE_LEFT_OUT_VIEWS.spread.join(", "),', spread)
        self.assertIn('return nodes.filter((node) => node.closest("[hidden]") === null && node.textContent !== "").map((node) => node.textContent);', function_body(self.script, "saveNotesOf"))
        # The activity types that a comparison asked for go with its answer
        # (Codex's review of the plan of R2, 6).
        request = function_body(self.script, "requestCompare")
        self.assertIn("const types = typesRequest(state.counted, state.view.types);", request)
        self.assertIn("            wholes: new Map(races.map((race, index) => [race.id, answers[2 * index + 1]])),\n            types,\n          }", request)
        self.assertIn("wholes: null, types };", request)
        # The words of a picture: its title, its parts, the lines under it.
        file = function_body(self.script, "saveViewFile")
        for line in (
            'saveLines([{ text: target.title, className: "save-title" }], layout.room, SAVE_GAP, measure), SAVE_MARGIN, SAVE_TITLE_LINE, measure) + 8;',
            "y += savePart(svg, stage, layout.chart === null ? part.source : part.redraw(stage, layout), top, target.drop, null, layout);",
            'const empty = svgElement("text", { class: "save-empty", x: layout.width / 2, y: ((top + y) / 2).toFixed(1), "text-anchor": "middle" });',
            "y = saveNotes(svg, target.notes, y, measure, layout);",
            # The axis of a comparison under its charts.
            '  if (target.axis !== null) {\n    y += savePart(svg, stage, layout.chart === null ? target.axis : target.redrawAxis(stage, layout), y, "", null, layout);\n  }',
        ):
            with self.subTest(line=line):
                self.assertIn(line, file)
        # The line after a saving goes with what another view shows (the
        # checker's review of the handling of Codex's review of the plan of R2).
        self.assertIn("content: saveContent(view),", function_body(self.script, "saveNoticeNow"))
        content = function_body(self.script, "saveContent")
        for line in (
            'return [state.compare.key, by, by === "race" ? state.compare.races : state.compare.years, compareModeNow(), compareMonthNow(), state.compareWeeks, state.compare.series, state.compare.grain, state.compare.lit?.id ?? null];',
            "return [state.plotPair.x, state.plotPair.y];",
            'return view === "spread" ? [state.spreadItem] : null;',
        ):
            with self.subTest(line=line):
                self.assertIn(line, content)
        self.assertIn('className: "save-caption"', function_body(self.script, "saveNotes"))
        # Each piece makes its own swatch, as the page does (Codex 3).
        words = function_body(self.script, "saveWords")
        self.assertIn("const swatch = piece.swatch();", words)
        self.assertIn("const [width, height] = piece.swatchSize ?? [22, 8];", words)
        self.assertIn('swatch: () => lineSwatch(line.style, heading.points)', function_body(self.script, "saveFile"))

    def test_the_words_of_saving_the_other_views(self) -> None:
        ja, en = catalog("ja"), catalog("en")
        for key, ja_words, en_words in (
            ("view.save.what", "保存する図：{name}", "Picture to save: {name}"),
            ("view.save.table", "表で見ているあいだは保存できません。「{button}」を押すと保存できます。", "No image can be saved while the table shows. Press “{button}” to save it."),
            ("view.save.compare_years", "くらべた年 {years}", "Years compared: {years}"),
            ("view.save.compare_races", "くらべた大会の日 {days}", "Race days compared: {days}"),
            ("view.save.width", "区間の幅 {width}", "Width of a range: {width}"),
            # The days of the races in English have commas of their own.
            ("view.save.days_separator", "、", "; "),
            # Why it cannot save (Codex's review of the diff of R2).
            ("view.save.stopped", "読み込みが止まったので、保存できません。止まった理由と次にすることは、図の上に出ています。", "The numbers stopped loading, so no image can be saved. Why, and what to do next, show above the chart."),
            ("view.save.empty", "この期間には図にする値がないので、保存できません。", "This period has no values to draw, so no image can be saved."),
            ("view.save.undrawn", "図を描く広さがないので、保存できません。ウィンドウを広げると保存できます。", "There is no room to draw the chart, so no image can be saved. Make the window larger to save it."),
        ):
            with self.subTest(key=key):
                self.assertEqual((ja[key], en[key]), (ja_words, en_words))
        # The rule of the steps of a calendar is the words of the page before
        # where it reads the values, which a picture cannot do (Codex 5; the
        # checker: in English one space before the next sentence).
        for catalog_, rest in ((ja, "値は、"), (en, " The values ")):
            with self.subTest(rest=rest):
                note, steps = catalog_["view.compare.calendar_note"], catalog_["view.compare.calendar_steps"]
                self.assertTrue(note.startswith(steps))
                self.assertTrue(note[len(steps):].startswith(rest))
        self.assertEqual(en["view.compare.calendar_note"][len(en["view.compare.calendar_steps"]) + 1], "T")
        self.assertNotIn("表で見る", ja["view.compare.calendar_steps"])
        self.assertNotIn("table", en["view.compare.calendar_steps"].lower())


    # --- A PNG of the size of a post (stage X5 of v2.3.0) -----------------

    def test_a_png_is_laid_out_in_its_frame_its_charts_drawn_again_from_the_answers_of_the_page(self) -> None:
        png = function_body(self.script, "savePng")
        for line in (
            "const frame = SAVE_SIZES[state.saveSize];",
            # Two layouts: the charts first SAVE_FIRST_CHART high, then as
            # high as fills the frame (the node test of saveFrameHeights).
            "const layout = pictureLayout(frame.width, chart);",
            'const svg = target.view === "panels" ? saveFile(stage, target.plan, layout) : saveViewFile(stage, target, layout);',
            # A plot and a distribution are drawn first as high as the least
            # they are drawn at, as they are never drawn lower (Codex's review
            # of the diff of X5).
            "const firstChart = Math.max(SAVE_FIRST_CHART, target.low ?? SAVE_PNG_LOW);",
            "let made = make(firstChart);",
            "const heights = saveFrameHeights({ frame: frame.height, first: made.box.height, chart: firstChart, count: made.layout.grows, low: target.low ?? SAVE_PNG_LOW });",
            '    return { problem: state.saveSize === "9x16" ? "view.save.png_tight_tall" : "view.save.png_tight" };',
            "  if (made.layout.grows > 0) {\n    made = make(heights.chart);\n  }",
            # In the middle of the frame, 2.5 times as large, smaller where it
            # is wider or higher than its frame.
            "const scale = SAVE_PNG_SCALE * Math.min(1, frame.width / box.width, frame.height / box.height);",
            "const plan = paintPlan(made.svg, [scale, 0, 0, scale, (width - box.width * scale) / 2, (height - box.height * scale) / 2]);",
            '  if (plan.left > 0) {\n    return { problem: "view.save.failed" };\n  }',
            'context.fillStyle = made.svg.querySelector(":scope > rect")?.getAttribute("fill") ?? "#ffffff";',
            "paintItems(context, plan.items);",
            "return { blob: pngBlob(canvas), problem: null };",
        ):
            with self.subTest(line=line):
                self.assertIn(line, png)
        # Each chart drawn again by the function that draws it on the page,
        # given a copy of its panel or row with a box in place of its plot,
        # or the box and a size: the page keeps its own.
        for name, line in (
            ("redrawPanel", "drawChart({ ...entry, plot });"),
            ("redrawCompare", "const copy = { ...entry, plot };\n  drawComparePlot(copy, compareContext);"),
            ("redrawCalendar", "drawCompareCalendar({ ...entry, plot }, compareContext, Math.min(calendarPitch(compareContext.data.length), fit));"),
            ("redrawShoe", "drawShoePlot({ ...entry, plot });"),
            ("redrawPlot", "drawPlotPoints({ chart }, answer, asked, [layout.room, layout.chart]);"),
            ("redrawSpread", "drawSpreadBars({ chart }, answer, key, [layout.room, layout.chart]);"),
            ("redrawTimeAxis", "drawTimeAxis(start, end, layout.room, place, true);"),
            ("redrawCompareAxis", "drawCompareAxis(compareContext, layout.room, layout.right ?? PLOT_RIGHT, place, true);"),
        ):
            with self.subTest(function=name):
                self.assertIn(line, function_body(self.script, name))
        for name in ("redrawPanel", "redrawCompare", "redrawShoe", "redrawPlot", "redrawSpread"):
            with self.subTest(grows=name):
                self.assertIn("layout.grows += 1;", function_body(self.script, name))
        self.assertNotIn("layout.grows", function_body(self.script, "redrawCalendar"))
        # The parts of each view know how to draw again; a plot and a
        # distribution never lower than they are drawn.
        for name, line in (
            ("saveFile", "layout.chart === null ? savedChart(key) : redrawPanel(stage, entry, layout)"),
            ("saveFile", "const axis = layout.chart === null ? ui.timeAxis.querySelector(\":scope > svg\") : periods?.length ? redrawTimeAxis(stage, periods[0].start, periods[periods.length - 1].end, layout) : null;"),
            ("saveCompareTarget", "redrawAxis: redrawCompareAxis,"),
            ("saveShoesTarget", "redrawAxis: (stage, layout) => redrawTimeAxis(stage, shoesContext.start, shoesContext.end, layout),"),
            ("savePlotTarget", "redraw: (stage, layout) => redrawPlot(stage, answer, asked, layout)"),
            ("savePlotTarget", "low: SAVE_DRAWN_LOW,"),
            ("saveSpreadTarget", "redraw: (stage, layout) => redrawSpread(stage, answer, asked.item, layout)"),
            ("saveSpreadTarget", "low: SAVE_DRAWN_LOW,"),
            ("saveComparePart", "redraw: (stage, layout) => redraw(stage, entry, layout),"),
        ):
            with self.subTest(function=name, line=line):
                self.assertIn(line, function_body(self.script, name))
        self.assertIn("const SAVE_DRAWN_LOW = 120;", self.script)
        self.assertIn("const SVG_LAYOUT = Object.freeze(pictureLayout());", self.script)
        # The squares of a calendar as large as given, or as the page has them.
        self.assertIn("const pitch = size ?? calendarPitch(context.data.length);", function_body(self.script, "drawCompareCalendar"))

    def test_the_window_never_draws_again_and_the_page_keeps_its_axes(self) -> None:
        # Showing the window draws nothing again (the checker's review of the
        # plan of X5): the window, the choices, and what it saves call no
        # function that draws, and no picture is laid out but by a press.
        import re

        drawing = re.compile(r"(?<![A-Za-z])(?:draw[A-Z]\w*|saveFile|saveViewFile|savePng|saveSvg|redraw[A-Z]\w*)\(")
        for name in ("renderSave", "renderSavePanels", "saveTarget", "saveCompareTarget", "savePlotTarget", "saveSpreadTarget", "saveShoesTarget", "fitSaveWindow", "saveProblemText", "openSave", "changeSave", "saveComparePart"):
            body = function_body(self.script, name)
            # The parts of a view hold the function that draws them again, run
            # by a press only.
            body = re.sub(r"\(stage, layout\) => [^,\n]*", "", body)
            with self.subTest(function=name):
                self.assertIsNone(drawing.search(body), drawing.search(body))
        # A PNG is laid out by a press only, once there.
        self.assertEqual(len(re.findall(r"(?<![A-Za-z])(?<!function )savePng\(", self.script)), 1)
        self.assertIn("savePng(stage, target)", function_body(self.script, "saveImage"))
        for call in ("part.redraw(stage, layout)", "target.redrawAxis(stage, layout)"):
            with self.subTest(call=call):
                self.assertEqual(self.script.count(call), 1)
                self.assertIn(call, function_body(self.script, "saveViewFile"))
        # The page draws its own axes as before: the marks are thinned only
        # where a PNG asks for it.
        self.assertIn("drawTimeAxis(periods[0].start, periods[periods.length - 1].end, chartWidth);", function_body(self.script, "renderCharts"))
        self.assertIn("drawCompareAxis(context, width, first.right);", function_body(self.script, "renderCompareCharts"))
        self.assertIn("drawTimeAxis(shoesContext.start, shoesContext.end, width, ui.shoesAxis);", function_body(self.script, "renderShoesCharts"))
        for name in ("drawTimeAxis", "drawCompareAxis"):
            body = function_body(self.script, name)
            with self.subTest(axis=name):
                self.assertEqual(body.count("thinTicks("), 1)
                self.assertLess(body.index("if (thin) {"), body.index("thinTicks("))
        self.assertIn("{ years: true },", function_body(self.script, "drawTimeAxis"))
        self.assertIn("{ last: race },", function_body(self.script, "drawCompareAxis"))

    def test_a_png_is_made_at_once_and_loads_no_image(self) -> None:
        blob = function_body(self.script, "pngBlob")
        self.assertIn('const data = canvas.toDataURL("image/png");', blob)
        self.assertIn('return new Blob([array], { type: "image/png" });', blob)
        for name in ("savePng", "paintItems", "paintShape", "paintPath", "pngBlob"):
            body = function_body(self.script, name)
            # Nothing waits (the checker's R1-4 and the plan of X5), and no
            # image is loaded, so the policy of the page stays as it is.
            for word in ("toBlob", "await", "requestAnimationFrame", "setTimeout", "queueMicrotask", ".then(", "new Image", "createImageBitmap", ".src", "onload", "decode("):
                with self.subTest(function=name, word=word):
                    self.assertNotIn(word, body)
        # A layer is a canvas of its own, laid on with its opacity.
        items = function_body(self.script, "paintItems")
        self.assertIn('const layer = document.createElement("canvas");', items)
        self.assertIn("context.globalAlpha = item.opacity;\n      context.drawImage(layer, 0, 0);", items)
        shape = function_body(self.script, "paintShape")
        for line in (
            "context.setTransform(...shape.matrix);",
            'const strokeFirst = /^stroke\\b/.test(String(styles["paint-order"]).trim());',
            'context.textAlign = { middle: "center", end: "right" }[styles["text-anchor"]] ?? "left";',
            'context.textBaseline = "alphabetic";',
            "context.setLineDash(",
        ):
            with self.subTest(line=line):
                self.assertIn(line, shape)
        # The round corners of the squares of a calendar.
        self.assertIn("} else if (shape.rx > 0 && shape.ry > 0) {", function_body(self.script, "paintPath"))
        # The line under a picture keeps the space after its separator.
        self.assertIn("const footPieces = saveFooterPieces(", function_body(self.script, "saveEnd"))

    def test_the_words_of_a_png(self) -> None:
        ja, en = catalog("ja"), catalog("en")
        for key, ja_words, en_words in (
            ("view.save.format_choice", "形式", "Format"),
            ("view.save.format_svg", "SVG", "SVG"),
            ("view.save.format_png", "PNG", "PNG"),
            ("view.save.size", "大きさ", "Size"),
            ("view.save.size_4x5", "4:5 縦長（1080×1350）", "4:5 portrait (1080×1350)"),
            ("view.save.size_1x1", "1:1 正方形（1080×1080）", "1:1 square (1080×1080)"),
            ("view.save.size_9x16", "9:16 縦長（1080×1920）", "9:16 portrait (1080×1920)"),
            # Only the sizes of posts; nothing is sent or joined to a service
            # (the checker's review of the plan of X5).
            ("view.save.png_note", "PNG 形式。スマホで見る SNS の投稿の大きさです。", "PNG, in the sizes of social media posts seen on a phone."),
            ("view.save.png_tight", "この大きさには段が収まりません。段を減らすか、縦に長い大きさを選んでください。", "The panels do not fit this size. Show fewer panels, or choose a taller size."),
            ("view.save.png_tight_tall", "この大きさには段が収まりません。段を減らしてください。", "The panels do not fit this size. Show fewer panels."),
        ):
            with self.subTest(key=key):
                self.assertEqual((ja[key], en[key]), (ja_words, en_words))
        for words in (ja["view.save.png_note"], en["view.save.png_note"]):
            for word in ("送", "つな", "連携", "send", "share", "upload", "connect"):
                with self.subTest(words=words, word=word):
                    self.assertNotIn(word, words)


if __name__ == "__main__":
    unittest.main()
