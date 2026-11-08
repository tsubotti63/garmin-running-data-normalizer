from __future__ import annotations

import itertools
import json
import re
import struct
import unittest
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

from garmin_running_data_normalizer.gui.layouts import BUILT_IN_LAYOUTS
from garmin_running_data_normalizer.view.data import ViewData
from garmin_running_data_normalizer.view import series as series_module
from garmin_running_data_normalizer.view.items import ITEMS, ITEMS_BY_KEY, OBSERVED
from garmin_running_data_normalizer.view.series import (
    MAX_POINTS,
    MAX_RANGES,
    SPREAD_RANGES,
    activity_spread,
    chosen_span,
    period_bounds,
    point_item,
    previous_span,
)

# The guides of main are read by the users of the stable release, through the
# README, so they name and install the release that is published, which the
# product state knows, also while the source is a release candidate, whose
# procedure gives its own line (v2.0.1 F4; decision 20261024-4).
from scripts.validate_public_product_state import CURRENT_STABLE_VERSION
from tests import test_gui_i18n
from tests.test_gui_view_save import function_body
from tests.test_view_series import act, view_data


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "src/garmin_running_data_normalizer/gui/static"
GUIDES = {"en": ROOT / "docs/gui_guide.md", "ja": ROOT / "docs/gui_guide.ja.md"}
# The labels that the guides quote: bold in English, 「」 in Japanese, in the
# order of the page (stage B6b: the guides follow the boxes of the page).
QUOTED_LABELS = (
    "language.label",
    "export.heading",
    "snapshot.heading",
    "output.heading",
    "run.heading",
    "next_line.label",
    "badge.current",
    "badge.done",
    "decide.button",
    "legend.title",
    "steps.heading",
    "result.caption",
    "choose.zip",
    "choose.folder",
    "browser.choose",
    "extract.label",
    "input.label",
    "check.button",
    "import.label",
    "import.time",
    "rerun.button",
    "rerun.back",
    "how.legend",
    "how.snapshots",
    "how.single",
    "store.label",
    "store.open",
    "store.create",
    "store.open_other",
    "store.create_new",
    "store.check",
    "store.row_pending",
    "store.row_added",
    "store.row_kept",
    "lock.confirm",
    "lock.remove",
    "browse.button",
    "output.parent",
    "output.name",
    "timezone.label",
    "pack.label",
    "info.contents",
    "reveal.button",
    "run.start",
    "run.cancel",
    "run.cancel_yes",
    "run.cancel_no",
    "info.meaning",
    "result.headline_done",
    "result.headline_partial",
    "result.headline_failed",
    "output_check.heading",
    "next_actions.heading",
    "open.folder",
    "open.start_here",
    "next_actions.ai",
    "result.column_change",
    "hints.toggle",
    # v2.0.1 F5: the question before Quit, and the step of the help that
    # reading the result marks done (stage F2).
    "quit.question",
    "quit.yes",
    "quit.no",
    "status.quitting",
    "help.step_results",
    "step_state.done",
    "remembered.search_again",
    "forget.button",
    "tools.heading",
    "target.heading",
    "target.run",
    "target.earlier",
    "target.other",
    "target.check",
    "bundle.button",
    "bundle.place_label",
    "report.line_button",
    "tools.report",
    "help.report",
    "report.open",
    "help.button",
    "help.steps",
    "help.faq",
    "help.words",
    "help.ai",
    "ai.copy",
    "help.close",
    "info.explain",
    "quit.button",
    # v2.1.0 G6a: the colors of the page and the view page (stages G3a
    # and G3b), which the guides describe from 2.1.0.
    "theme.label",
    "theme.auto",
    "theme.light",
    "theme.dark",
    "view.open_output",
    "view.open_page",
    "view.to_normalize",
    "view.output.label",
    "view.output.open_remembered",
    "view.output.open_latest",
    "view.stop.normalize_again",
    "view.period.label",
    "view.period.all",
    "view.period.years10",
    "view.period.years5",
    "view.period.years3",
    "view.period.years1",
    "view.period.custom",
    "view.range.from",
    "view.range.to",
    "view.period.back",
    "view.period.next",
    "view.grain.label",
    "view.grain.auto",
    "view.grain.day",
    "view.grain.week",
    "view.grain.month",
    "view.grain.year",
    "view.types.label",
    "view.shelf.search_label",
    "view.shelf.fold",
    "view.shelf.open",
    "view.add.button",
    "view.panel.table",
    "view.panel.chart",
    "view.panel.unbig",
    "view.align",
    "view.full.enter",
    "view.full.back",
    "view.quit",
    # v2.2.0 K3: the layouts, their buttons, and the six built-in layouts.
    "view.layouts.heading",
    "view.layouts.save_as",
    "view.layouts.overwrite",
    "view.layouts.manage",
    "view.layouts.rename",
    "view.layouts.up",
    "view.layouts.down",
    "view.layouts.remove",
    "view.layouts.keep",
    "view.layouts.hide",
    "view.layouts.show",
    "view.layouts.show_all",
    "view.layouts.close",
    "view.layouts.rail",
    "view.layout.run",
    "view.layout.sleep_hr",
    "view.layout.volume",
    "view.layout.form",
    "view.layout.load",
    "view.layout.estimates",
)


def section(text: str, heading: str) -> str:
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


# The one line of each system that installs this version and makes the icon
# (stage E1e): the code blocks inside the list of what you need, which are
# indented by two spaces in a list item, or by three in a numbered step (the
# steps of v2.0.1 F1).
ONE_LINE = re.compile(r"^( {2,3})```(bash|powershell)\n\1(.*)\n\1```$", re.M)
WHAT_YOU_NEED = {"en": "What you need", "ja": "用意するもの"}


def one_lines(language: str) -> list[tuple[str, str]]:
    text = section(GUIDES[language].read_text(encoding="utf-8"), WHAT_YOU_NEED[language])
    return [(kind, line) for _indent, kind, line in ONE_LINE.findall(text)]


def flowing(language: str, heading: str) -> str:
    """A section as it reads: an English line break is a space, and a
    Japanese one is nothing."""
    text = section(GUIDES[language].read_text(encoding="utf-8"), heading)
    return " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)


def catalog(language: str) -> dict[str, str]:
    return json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))


class GuiGuideTest(unittest.TestCase):
    def test_guides_quote_the_labels_on_the_page(self) -> None:
        # A changed label fails here until both guides follow it.
        quote = {"en": "**{}**", "ja": "「{}」"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            messages = catalog(language)
            for key in QUOTED_LABELS:
                with self.subTest(language=language, key=key):
                    self.assertIn(quote[language].format(messages[key]), text)

    def test_guides_quote_the_lines_of_the_page_that_v2_0_1_changed(self) -> None:
        # v2.0.1 F5, from the checker: the lines of the page that stage F2
        # changed, quoted from the catalog, so that a changed line fails here
        # until both guides follow it.
        quote = {"en": '"{}"', "ja": "「{}」"}
        sections = {
            "en": {
                "how.single_note": "Box 2: Snapshots",
                "run.again_note": "Box 4: Normalize",
                "run.again_same_export": "Box 4: Normalize",
                # v2.1.0 H1: a remembered item that another output does not have.
                "view.summary.none": "The view page (from 2.1.0)",
            },
            "ja": {
                "how.single_note": "2 の箱：スナップショット",
                "run.again_note": "4 の箱：正規化",
                "run.again_same_export": "4 の箱：正規化",
                "view.summary.none": "見るページ（2.1.0 から）",
            },
        }
        for language, keys in sections.items():
            messages = catalog(language)
            for key, heading in keys.items():
                with self.subTest(language=language, key=key):
                    self.assertIn(quote[language].format(messages[key]), flowing(language, heading))

    def test_guides_name_the_lines_of_the_line_for_macos_in_powershell_5_1(self) -> None:
        # v2.0.1 F5, from the check of v2.0.1rc1 on a physical Windows machine
        # (stage F4d): the line for macOS, pasted in Windows PowerShell 5.1,
        # stops before any part of it runs, since 5.1 has no "&&". The red
        # lines are in the language of Windows: "The token '&&' is not a valid
        # statement separator in this version." in English.
        for language, row, action in (
            ("en", "| `'&&'` and `is not a valid statement separator` (Windows) | The line for macOS was pasted in "
                   "Windows PowerShell 5.1, which has no `&&`. PowerShell ran no part of it, and nothing changed. |",
             "Run the line for Windows PowerShell in [Install Python and this app](#install-python-and-this-app) "
             "instead. There is nothing to move to the Recycle Bin."),
            ("ja", "| `'&&'` と、`有効なステートメント区切りではありません` か `is not a valid statement separator`（Windows） | "
                   "macOS の 1 行を Windows PowerShell 5.1 に貼りました。",
             "[Python とこのアプリを入れる](#python-とこのアプリを入れる)の Windows PowerShell の 1 行を、代わりに動かしてください。ごみ箱へ入れる物はありません。"),
        ):
            with self.subTest(language=language):
                text = flowing(language, WHAT_YOU_NEED[language])
                self.assertIn(row, text)
                self.assertIn(action, text)

    def test_guides_say_that_the_gui_is_in_this_release(self) -> None:
        # The stable release has the gui command, and v1.7.1 does not
        # (stage E2b; the release candidates said so for themselves from
        # stage D2).
        english = GUIDES["en"].read_text(encoding="utf-8")
        japanese = GUIDES["ja"].read_text(encoding="utf-8")
        self.assertTrue(english.startswith(f"# GUI Guide\n\n> **This guide is for v{CURRENT_STABLE_VERSION}.**"))
        self.assertTrue(japanese.startswith(f"# GUI の手引き\n\n> **v{CURRENT_STABLE_VERSION} の手引きです。**"))
        # The note at the top names this release and v1.7.1, and no
        # pre-release (stage D7).
        for language, text in (("en", english), ("ja", japanese)):
            with self.subTest(language=language):
                note = text.split("\n\n", 2)[1]
                self.assertEqual(set(re.findall(r"v\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", note)), {f"v{CURRENT_STABLE_VERSION}", "v1.7.1"})
                self.assertIsNone(re.search(r"v\d+\.\d+\.\d+(?:a|b|rc)\d+", note))
        self.assertIn("[日本語](gui_guide.ja.md)", english)
        self.assertIn("[English](gui_guide.md)", japanese)
        # The index of the documents leads users to the guides first.
        index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
        start = index.split("\n## Start here\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("[GUI Guide](gui_guide.md) ([日本語](gui_guide.ja.md))", start)
        self.assertNotIn("release candidate", index)

    def test_the_exit_3_result_reads_the_same_on_the_page_and_in_the_guides(self) -> None:
        # PARTIAL_SUCCESS is a finished run that left out part of the input,
        # not only FIT files (stage B1a), and its output can be used.
        phrases = {"en": ("left out", "output can be used"), "ja": ("除いたもの", "出力は使えます")}
        for language, path in GUIDES.items():
            row = next(
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith("| `PARTIAL_SUCCESS` |")
            )
            message = catalog(language)["result.sub_partial"]
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, row)
                    self.assertIn(phrase, message)

    def test_the_stops_in_the_guides_say_what_the_page_says(self) -> None:
        # A row of a stop quotes the page: what happened, and the next step
        # (stage B2a). Code spans of the guides are plain text on the page.
        whats = test_gui_i18n.flow_table("STOP_KEYS")
        next_steps = test_gui_i18n.flow_table("STOP_NEXT_KEYS")
        row = re.compile(r"^\| `([A-Z_]+)` \| (.+?) \| (.+?) \|$", re.M)
        for language, path in GUIDES.items():
            messages = catalog(language)
            rows = [match for match in row.finditer(path.read_text(encoding="utf-8")) if match[1] in whats]
            self.assertTrue(rows, language)
            for match in rows:
                with self.subTest(language=language, code=match[1]):
                    # A table cell escapes its backslashes and "|".
                    cells = [re.sub(r"\\(.)", r"\1", cell) for cell in (match[2], match[3])]
                    self.assertEqual(cells[0], messages[whats[match[1]]])
                    self.assertEqual(cells[1], messages[next_steps[match[1]]])

    def test_guides_describe_the_same_sections_and_codes(self) -> None:
        english = GUIDES["en"].read_text(encoding="utf-8")
        japanese = GUIDES["ja"].read_text(encoding="utf-8")
        self.assertEqual(english.count("\n## "), japanese.count("\n## "))
        codes = re.compile(r"^\| `([A-Z_]+)` \|", re.M)
        english_codes = codes.findall(section(english, "When something goes wrong"))
        self.assertEqual(english_codes, codes.findall(section(japanese, "うまくいかないとき")))
        # Only codes that the page can show.
        self.assertTrue(english_codes)
        self.assertLessEqual(set(english_codes), set(test_gui_i18n.flow_table("STOP_KEYS")))
        commands = re.compile(r"^garmin-running-data-normalizer .*$", re.M)
        self.assertEqual(commands.findall(english), commands.findall(japanese))

    def test_guides_give_one_line_that_installs_this_version_and_makes_the_icon(self) -> None:
        # One line for each system makes a virtual environment whose name has
        # no version, so that a later version goes into the same one and the
        # icon stays; installs this version in it; and makes the icon with its
        # Python. Each part runs only after the one before it succeeded: "&&"
        # on macOS (stage E1e), and in Windows PowerShell 5.1, which has no
        # "&&", "if ($?) { … }" one inside the other (stage E1i;
        # WindowsPowerShellLineTest in tests/test_shortcut.py runs the line).
        # The places are quoted for a home folder with spaces.
        found = {language: one_lines(language) for language in GUIDES}
        self.assertEqual(found["en"], found["ja"])
        (mac_language, mac), (windows_language, windows) = found["en"]
        self.assertEqual((mac_language, windows_language), ("bash", "powershell"))
        # The stable release is installed from Production PyPI only (stage
        # E2b); the release candidates were installed from TestPyPI.
        install = f"-m pip install garmin-running-data-normalizer=={CURRENT_STABLE_VERSION}"
        for language, path in GUIDES.items():
            with self.subTest(language=language):
                self.assertNotIn("test.pypi.org", path.read_text(encoding="utf-8"))
        icon = "-m garmin_running_data_normalizer gui --create-shortcut"
        venv = "~/garmin-normalizer"
        self.assertEqual(
            mac.split(" && "),
            [f"python3 -m venv {venv}", f"{venv}/bin/python {install}", f"{venv}/bin/python {icon}"],
        )
        venv = "$HOME\\garmin-normalizer"
        python = f'& "{venv}\\Scripts\\python.exe"'
        self.assertEqual(windows, f'py -m venv "{venv}"; if ($?) {{ {python} {install}; if ($?) {{ {python} {icon} }} }}')
        self.assertNotIn("&&", windows)
        # After the line, the GUI starts with the Python of the virtual
        # environment, as the icon starts it, and not with the program that
        # pip makes, which Windows may refuse, since it has no signature
        # (stage E1d). The sections that start the GUI and make the icon give
        # these commands first, as a person who installed with the line has
        # no other (stage E1i).
        for language, headings in (
            ("en", ("Start the GUI", "Start the GUI from an icon")),
            ("ja", ("GUI を起動する", "アイコンから起動する")),
        ):
            for heading, option in zip(headings, ("", " --create-shortcut")):
                text = section(GUIDES[language].read_text(encoding="utf-8"), heading)
                with self.subTest(language=language, heading=heading):
                    self.assertEqual(
                        re.findall(r"^```(bash|powershell)\n(.*)\n```$", text, re.M),
                        [
                            ("bash", f"~/garmin-normalizer/bin/python -m garmin_running_data_normalizer gui{option}"),
                            ("powershell", f"{python} -m garmin_running_data_normalizer gui{option}"),
                            ("bash", f"garmin-running-data-normalizer gui{option}"),
                        ],
                    )
                    self.assertNotIn("garmin-running-data-normalizer.exe", text)

    def test_guides_answer_what_a_first_reader_asked(self) -> None:
        # Stage E1i, from a new AI session that read the guides of v2.0.0rc3
        # as a first-time user, and from the checks of v2.0.0rc3 on a Mac: how
        # to see the version of Python, what the end of the line looks like,
        # what to do when it stops, how to update, how to undo Don't Allow,
        # why the terminal seems to stand still, and how to remove this app.
        phrases = {
            "en": {
                "What you need": (
                    "`python3 --version`", "`py --version`", "open the Terminal again",
                    "a new release of pip is available", "run the same line again",
                    "move the folder `garmin-normalizer`", "the line of the guide of that version",
                    "stop the GUI first", "request it early", "Nothing else needs to be installed",
                ),
                "Start the GUI from an icon": ("**Desktop Folder**", "**Files & Folders**", "OneDrive"),
                "When something goes wrong": ("double-click the icon again", "60 minutes"),
                "Stop the GUI": ("seems to stand still", '"GUI stopped."'),
                "Remove this app": (
                    "`shell:programs`", "`GarminRunningData`", "personal data",
                    "`pip uninstall garmin-running-data-normalizer`",
                    # v2.1.0 G6a: Windows said once that the folder was in use
                    # (stage G5d); a wait and Try Again went on.
                    "wait a little, and choose **Try Again**",
                ),
            },
            "ja": {
                "用意するもの": (
                    "`python3 --version`", "`py --version`", "ターミナルを開き直して",
                    "A new release of pip is available", "同じ 1 行をもう一度動かして",
                    "`garmin-normalizer` をごみ箱へ", "そのバージョンの手引きにある 1 行",
                    "先に GUI を終えて", "先にリクエストして", "ほかに入れるものはありません",
                ),
                "アイコンから起動する": ("「デスクトップフォルダ」", "「ファイルとフォルダ」", "OneDrive"),
                "うまくいかないとき": ("アイコンをもう一度ダブルクリック", "60 分間"),
                "GUI を終える": ("止まって見えます", "「GUI stopped.」"),
                "このアプリを片付ける": (
                    "`shell:programs`", "`GarminRunningData`", "個人のデータ",
                    "`pip uninstall garmin-running-data-normalizer`",
                    "少し待ってから「再試行」を押してください",
                ),
            },
        }
        for language, sections in phrases.items():
            for heading, wanted in sections.items():
                text = flowing(language, heading)
                for phrase in wanted:
                    with self.subTest(language=language, heading=heading, phrase=phrase):
                        self.assertIn(phrase, text)
        # The page says the same when the GUI no longer answers.
        for language, phrase in (("en", "double-click the icon again"), ("ja", "アイコンをもう一度ダブルクリック")):
            with self.subTest(language=language):
                self.assertIn(phrase, catalog(language)["next.restart_gui"])

    def test_guides_say_how_to_install_python_on_windows(self) -> None:
        # Stage E2b, from the second reading of stage E2a: on Windows,
        # python.org gives the Python install manager first (its page and
        # https://docs.python.org/3/using/windows.html, read on 2026-10-23).
        # Starting Python with py installs the latest Python when none is
        # installed, and the first one may ask to add a folder to PATH, which
        # the line, which uses py, does not need. When an older Python is
        # installed, py starts it, and pymanager install default installs the
        # latest one; when py still starts the older one, as the legacy Python
        # Launcher can make it, the Launcher is removed in Installed apps, and
        # the older Python too when py still starts it (the documentation,
        # sections 4.1.5, 4.1.9 and 4.1.15, and the source of the Python
        # install manager 26.4, read on 2026-10-23; from the new AI session
        # that read the guides of v2.0.0). v2.0.1 F1 removes the Launcher
        # first, since the legacy launcher's py overrides the one of the
        # install manager (sections 4.1.9 and 4.1.15, read again on
        # 2026-10-24) and other apps may use the older Python.
        phrases = {
            "en": (
                "**Download Python install manager**", "choose **Install**",
                "as `py --version` does, installs the latest Python by itself",
                "add a folder to `PATH`", "The line of step 4 uses `py`",
                "When an older Python is installed already, `py` starts that one",
                "run `pymanager install default` in PowerShell",
                "uninstall the Python Launcher in **Installed apps**",
                "[python.org describes](https://docs.python.org/3/using/windows.html)",
                "Keep the Python install manager and Python 3.11 and later.",
                "When it still shows the older Python, uninstall Python 3.10 and earlier too",
            ),
            "ja": (
                "「Download Python install manager」", "「Install」を押して",
                "いちばん新しい Python が自動で入ります", "`PATH` にフォルダーを足すか", "4 の 1 行は `py` を",
                "`py` はその古い Python を起動する", "`pymanager install default` を動かして",
                "「インストールされているアプリ」で Python Launcher をアンインストールし",
                "[python.org の説明](https://docs.python.org/3/using/windows.html)",
                "Python install manager と 3.11 以降の Python は残します",
                "それでも古い Python が出るときは、3.10 以前の Python もアンインストールして",
            ),
        }
        for language, wanted in phrases.items():
            text = flowing(language, WHAT_YOU_NEED[language])
            for phrase in wanted:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_guides_answer_what_a_second_reader_asked(self) -> None:
        # Stage E2a, from a new AI session that read the guides of v2.0.0rc4
        # as a first-time user, from the checks of v2.0.0rc4 on Windows and on
        # a Mac, and from a second new AI session that read the guides that
        # these answers changed: how to read the version of Python, the lines
        # of a line that stopped (an old pip, such as the one of Python 3.9,
        # shows no line of Requires-Python) and where to ask, how to open the
        # home folder, how to update, how to go back to the GUI that is open,
        # and the name with ".command" that the Finder shows when it shows
        # every extension. An update stops the GUI first on every system: a
        # GUI that is still open keeps the page of its version (gui/server.py
        # reads the page at its start), while each run is a new Python process
        # that takes the code on the disk (gui/runs.py). An open page keeps
        # the GUI awake with its heartbeat (gui/server.py).
        phrases = {
            "en": {
                "What you need": (
                    'the number after "3." is 11 or more', "can be too old for this app", "`%USERPROFILE%`",
                    "**Go** > **Home**",
                    # The rows of the table, which the words of a row also name.
                    "| `command not found` (macOS), or `is not recognized` (Windows) |", "| `xcode-select` (macOS) |",
                    "| `Requires-Python` |", "| `Retrying` and `connection` |",
                    "| `No matching distribution found`, without `Requires-Python` and `Retrying` |",
                    "| A line that starts with `ERROR [SHORTCUT_` |",
                    "On macOS as on Windows, stop the GUI first", '"Unable to copy"', "the versions are mixed",
                    "stay as they are", "open a new PowerShell window", "the terminal is the window of PowerShell",
                    "a line that ends with %", "there is nothing to move",
                    "an old pip does not show the line of `Requires-Python`",
                    "[Report a problem on GitHub](#report-a-problem-on-github)",
                    "see the version again with `python3 --version` (on Windows, `py --version`)",
                    "follow its steps in [Install Python and this app](#install-python-and-this-app) until `py --version` shows 3.11 or later",
                ),
                "Start the GUI from an icon": ("**Show all filename extensions**", "the icon starts the new version"),
                "Go back to the GUI that is open": (
                    "A bookmark does not open the GUI", "one more GUI opens", "60 minutes",
                    "When no normalization runs, you may instead double-click the icon again", "the command key and C",
                    "right-click to copy it", "stops the GUI of that page only", "puts the tab to sleep",
                    # v2.1.0 G6a: Safari stops asking from a window hidden with
                    # Command-H (stage G5p).
                    "or hides its window, as Safari does with Command-H",
                    "The earlier GUI has no page, and stops by itself after 60 minutes when no run is active",
                    "A GUI whose page you closed stops by itself after 60 minutes when no run is active",
                ),
                "Stop the GUI": ("the control key and C, on macOS too", "When no page is open for 60 minutes"),
                "When something goes wrong": ("because no page was open for 60 minutes",),
            },
            "ja": {
                "用意するもの": (
                    "「3.」のあとの数が 11 以上", "このアプリには古いことがあります", "`%USERPROFILE%`",
                    "「移動」→「ホーム」",
                    "| `command not found`（macOS）、`認識されません` か `is not recognized`（Windows） |",
                    "| `xcode-select`（macOS） |", "| `Requires-Python` |", "| `Retrying` と `connection` |",
                    "| `No matching distribution found`（`Requires-Python` と `Retrying` が無いとき） |",
                    "| `ERROR [SHORTCUT_` で始まる行 |",
                    "macOS でも Windows でも、先に GUI を終えて", "「Unable to copy」",
                    "バージョンが混ざります", "そのまま残ります", "PowerShell の窓を開き直して",
                    "Windows では PowerShell の窓のことです", "% で終わる行", "そのフォルダーが無ければ",
                    "古い pip は `Requires-Python` の行を出しません", "[GitHub で報告する](#github-で報告する)",
                    "もう一度 `python3 --version`（Windows では `py --version`）で", "パス（ファイルやフォルダーの場所）",
                    "[Python とこのアプリを入れる](#python-とこのアプリを入れる)の Windows の手順で、`py --version` が 3.11 以降と出るまで",
                ),
                "アイコンから起動する": ("「すべてのファイル名拡張子を表示」", "アイコンから新しいバージョンが起動します"),
                "開いている GUI に戻る": (
                    "ブックマークからは開けません", "GUI がもう 1 つ開きます", "60 分たつと",
                    "実行中の正規化が無いときは、代わりにアイコンをもう一度ダブルクリック", "command キーと C", "右クリックで写します",
                    "そのページの GUI だけが終わります", "タブを眠らせた", "窓を隠したとき（Safari の ⌘H など）",
                    "前の GUI は、ページが無いので、実行中でなければ、60 分たつと",
                    "閉じた GUI は、実行中でなければ、60 分たつと",
                ),
                "GUI を終える": ("macOS でも control キーと C", "どのページも開いていないまま 60 分たつと"),
                "うまくいかないとき": ("どのページも 60 分間開いていなかった",),
            },
        }
        for language, sections in phrases.items():
            for heading, wanted in sections.items():
                text = flowing(language, heading)
                for phrase in wanted:
                    with self.subTest(language=language, heading=heading, phrase=phrase):
                        self.assertIn(phrase, text)
        # The guides quote the lines that the gui command prints at the end of
        # a line that succeeded.
        command = (ROOT / "src/garmin_running_data_normalizer/gui/command.py").read_text(encoding="utf-8")
        for line in (
            "GUI address (it contains the launch key; do not share it):",
            "Stop with Ctrl+C or the Quit button on the page.",
        ):
            self.assertIn(f'print("{line}"', command)
            for language in GUIDES:
                with self.subTest(language=language, line=line):
                    self.assertIn(line, flowing(language, WHAT_YOU_NEED[language]))
        # The Export comes first among what you need, since Garmin takes time
        # to make it; and the remembered settings are forgotten before the
        # GUI stops, since only the page forgets them. v2.1.0 H1: the places
        # are written down before the settings are forgotten, since the page
        # no longer shows them then (the reading of G6a).
        for language, export, write, forget, stop in (
            ("en", "- A Garmin Account Data Export", "1. When you changed the places",
             "**Forget the remembered settings…**", "3. Stop the GUI"),
            ("ja", "- Garmin のエクスポート", "1. 保管場所や出力を作る場所を変えていたときは",
             "「覚えた設定を消す…」", "3. GUI を終えます"),
        ):
            with self.subTest(language=language):
                text = GUIDES[language].read_text(encoding="utf-8")
                need = section(text, WHAT_YOU_NEED[language])
                self.assertTrue(need.split("\n\n", 2)[1].startswith(export))
                remove = flowing(language, {"en": "Remove this app", "ja": "このアプリを片付ける"}[language])
                self.assertLess(remove.index(write), remove.index(forget))
                self.assertLess(remove.index(forget), remove.index(stop))

    def test_guides_show_pictures_of_this_repository(self) -> None:
        # v2.1.0 G6a, from the checker: the pictures of each guide are files
        # of this repository, given by paths relative to the guide, so that
        # the guide that the help panel opens at a tag shows the pictures of
        # the same tag, with words in place of each picture. They are PNGs
        # made from synthetic data, without the chunks that can hold text or a
        # time. v2.1.0 H1: the whole flow and the ways to use it add four
        # pictures; the two guides give the same pictures in the same order,
        # each guide those of its own language, with the words in its
        # language.
        # v2.2.0 K3: the view page shows the layouts above the item shelf, in
        # two pictures more, cut to the layouts and to their window. L2: May of
        # every year in its scene, and the years in rows and laid over one
        # another in the section of comparing years. M4: the list of a period
        # and the marks, after the overview, and comparing by race day, after
        # the years laid over one another. N2: the calendar, before comparing
        # by race day. OP2: the points and a distribution, after comparing by
        # race day. Q2: the summary, after a distribution. R3: saving as an
        # image, after the summary: its window, and a picture saved, cut above
        # its line at the bottom (the checker's answer 4 of the plan of R3).
        # T2: the conditions on the activities, after the view page; the list
        # of a period is taken again with its column of the names.
        names = (
            "normalized-page",
            "next-steps",
            "second-launch",
            "view-last-year",
            "view-compare-may",
            "view-page",
            "view-conditions",
            "view-layouts",
            "view-layouts-manage",
            "view-list",
            "view-marks",
            "view-compare-rows",
            "view-compare-overlay",
            "view-compare-calendar",
            "view-compare-race",
            "view-plot",
            "view-spread",
            "view-shoes",
            "view-recap",
            "view-save",
            "view-save-picture",
        )
        sizes = {"next-steps": (315, 213), "view-layouts": (371, 193), "view-layouts-manage": (440, 438)}
        # The picture saved is cut above its line at the bottom, under the
        # chart of each language (R3); taken again with 2.2.0, the English one
        # is cut lower, under its taller chart (K6a).
        sizes |= {("view-save-picture", "en"): (1200, 564), ("view-save-picture", "ja"): (1200, 598)}
        # S2: the view by shoes, 860 px high so that the two rows of one name show.
        sizes |= {("view-shoes", "en"): (1470, 860), ("view-shoes", "ja"): (1470, 860)}
        japanese = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
        for language, path in GUIDES.items():
            with self.subTest(language=language):
                pictures = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", path.read_text(encoding="utf-8"))
                self.assertEqual([link for _words, link in pictures], [f"assets/gui-guide/{name}.{language}.png" for name in names])
                for (words, link), name in zip(pictures, names):
                    with self.subTest(language=language, picture=name):
                        self.assertTrue(words.strip())
                        self.assertEqual(bool(japanese.search(words)), language == "ja")
                        data = (path.parent / link).read_bytes()
                        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                        self.assertEqual(struct.unpack(">II", data[16:24]), sizes.get((name, language), sizes.get(name, (1470, 830))))
                        self.assertLess(len(data), 1_000_000)
                        kinds = set()
                        place = 8
                        while place < len(data):
                            size, kind = struct.unpack(">I4s", data[place : place + 8])
                            kinds.add(kind)
                            place += 12 + size
                        self.assertEqual(place, len(data))
                        self.assertFalse({b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"} & kinds)

    def test_guides_give_the_whole_flow_and_the_ways_to_use_it(self) -> None:
        # v2.1.0 H1, as the Human maintainer chose on 2026-10-28 (the ways to
        # use it at the center, the whole flow at the top): the whole flow
        # comes before what you need, in four steps that each lead to a
        # section; the ways to use it come after what you need, the same six
        # scenes in both guides, each with links to the sections that give
        # the details, and the first two start the GUI by a link, not by its
        # steps (the checker). From v2.2.0 (stage L2), a seventh scene compares
        # May of every year, after the past year on the view page; from M4, an
        # eighth compares the 16 weeks before races, after it; from OP2, a ninth
        # gives the distances of the last year as a distribution, after it (the
        # checker's answer 3 of the plan of OP2). From R3, a scene keeps a
        # comparison of years as an image, after the summary, the tenth of
        # eleven (the checker's answer 2 of the plan of R3); from S2, a scene
        # sees the distance of each pair of shoes by month, after it, the
        # eleventh of twelve (answer 2 of the plan of S2); from T2, a scene
        # counts only the tempo runs by name, after the last year compared with
        # the year before, the tenth of thirteen (the checker's answer 2 of the
        # plan of T2); the CSV file stays last.
        parts = {
            "en": ("How it goes", "Ways to use it", "More: [", "(#start-the-gui)"),
            "ja": ("全体の流れ", "場面ごとの使い方", "くわしくは：[", "(#gui-を起動する)"),
        }
        scenes = {}
        for language, path in GUIDES.items():
            flow, ways, more, start = parts[language]
            text = path.read_text(encoding="utf-8")
            need = f"\n## {WHAT_YOU_NEED[language]}\n"
            with self.subTest(language=language):
                self.assertLess(text.index(f"\n## {flow}\n"), text.index(need))
                self.assertLess(text.index(need), text.index(f"\n## {ways}\n"))
                steps = re.findall(r"^(\d)\. \[[^\]]+\]\(#[^)]+\)", section(text, flow), re.M)
                self.assertEqual(steps, ["1", "2", "3", "4"])
                scenes[language] = re.split(r"^### ", section(text, ways), flags=re.M)[1:]
                for number, scene in enumerate(scenes[language], 1):
                    with self.subTest(language=language, scene=number):
                        self.assertIn(more, scene)
                        if number <= 2:
                            first = re.search(r"^1\. (.*)$", scene, re.M).group(1)
                            self.assertIn(start, first)
                        reads = " ".join(scene.split()) if language == "en" else re.sub(r"\n *", "", scene)
                        for phrase in self.READING_OF_H1[language].get(number, ()):
                            self.assertIn(phrase, reads)
                        if scene.startswith(("Give the numbers to an AI", "数字を CSV にして")):
                            care = {"en": "personal data", "ja": "個人のデータ"}[language]
                            self.assertLess(reads.index(care), reads.index("`about`"))
        self.assertEqual(len(scenes["en"]), 13)
        self.assertEqual(len(scenes["ja"]), 13)
        for language, title, race, spread, recap in (
            ("en", "Compare May of every year", "Compare the 16 weeks before races", "See how often you ran each distance in the last year", "Compare the last year with the year before"),
            ("ja", "毎年の 5 月をくらべる", "大会の前の 16 週をくらべる", "直近 1 年に、どの距離を何回走ったかを見る", "この 1 年と前の 1 年をくらべる"),
        ):
            with self.subTest(language=language, scene="compare"):
                self.assertTrue(scenes[language][5].startswith(title))
                self.assertTrue(scenes[language][6].startswith(race))
                self.assertTrue(scenes[language][7].startswith(spread))
                self.assertTrue(scenes[language][8].startswith(recap))
                self.assertTrue(scenes[language][9].startswith(("Count only the tempo runs, by name", "名前でペース走だけを数える")))
                self.assertTrue(scenes[language][10].startswith(("Keep a comparison of years as an image", "年でくらべた図を画像にして残す")))
                self.assertTrue(scenes[language][11].startswith(("See the distance of each pair of shoes by month", "靴ごとに、月ごとの距離を見る")))
                self.assertTrue(scenes[language][12].startswith(("Give the numbers to an AI", "数字を CSV にして")))
        intro = {"en": "The steps of thirteen common cases.", "ja": "よくある 13 の場面の手順です。"}
        for language, path in GUIDES.items():
            with self.subTest(language=language, part="intro"):
                self.assertIn(intro[language], path.read_text(encoding="utf-8"))

    # From the two new AI sessions that read the sections of H1: the first
    # two scenes name the timezone, which is Asia/Tokyo by default and, from
    # v2.2.0 (stage K1), that of the last run that made an output, which box 3
    # set by itself keeps at a later launch; the
    # scenes that do not import say that the way to normalize is not
    # remembered; and the CSV file is given only after the care for the
    # personal data in it (checked in the test above).
    READING_OF_H1 = {
        "en": {
            1: ("**Timezone for local dates and times** (`Asia/Tokyo` by default)",),
            2: ("The timezone of the last run that made an output is remembered",),
            3: ("The way to normalize is not remembered",),
            4: ("choose **Normalize this export only (no import)** in box 2 again",),
        },
        "ja": {
            1: ("「日時に使うタイムゾーン」を確かめてから（既定は `Asia/Tokyo`）",),
            2: ("タイムゾーンは、前に出力を作った正規化のものを覚えています",),
            3: ("正規化のしかたは覚えません",),
            4: ("2 の箱で「今回のエクスポートだけで正規化する（取り込まない）」をもう一度選びます",),
        },
    }

    def test_guides_say_what_2_2_0_remembers_and_what_going_back_does(self) -> None:
        # v2.2.0 K1: the timezone of the last run that made an output is
        # remembered, and a later launch sets box 3 with it; an earlier
        # version does not use the settings of 2.2.0 and starts as a first
        # launch, and its forgetting forgets them too (the checker).
        phrases = {
            "en": (
                "The timezone of the last run that made its output (from 2.2.0). At later launches, box 3 is set with it (**(as last time)**).",
                "The place of an Export, **Name of the new folder** in box 3, the language, and the way to normalize are not remembered.",
                "it does not use the settings that 2.2.0 remembered, and starts as a first launch. It does not write over their file, so it does not remember what you choose while you use it; back in 2.2.0, what 2.2.0 remembered is used as before.",
                "**Forget the remembered settings…** of the earlier version removes that file, so that it forgets what 2.2.0 remembered too, such as the timezone of Box 3",
                # v2.2.1 W6e: 2.2.1 keeps the settings and the marks in the
                # form of 2.2.0, so that going back to 2.2.0 keeps them.
                "When you go back from 2.2.1 to 2.2.0, 2.2.0 uses the settings and the marks that 2.2.1 remembered as they are, as both versions keep them in the same form; what follows of 2.2.0 holds for 2.2.1 too.",
            ),
            "ja": (
                "前に出力を作った正規化のタイムゾーン（2.2.0 から）。2 回目からは、3 の箱がこのタイムゾーンで決まります（「（前回のまま）」）。",
                "エクスポートの場所、3 の箱の「新しく作るフォルダーの名前」、言語、正規化のしかたは覚えません。",
                "2.2.0 が覚えた設定は使われず、初めての起動として始まります。戻したバージョンは、2.2.0 の設定のファイルを書き換えないので、戻している間に選んだことは覚えません。2.2.0 にまた戻すと、2.2.0 が覚えていたものが、そのまま使われます。",
                "「覚えた設定を消す…」を押すと、そのファイルを消すので、2.2.0 が覚えたもの（3 の箱のタイムゾーンや、見るページで覚えたものなど）も消えます。",
                "2.2.1 から 2.2.0 に戻したときは、2.2.1 が覚えた設定と印が、そのまま使われます（2 つのバージョンは、設定と印を同じ形で残します）。下の 2.2.0 のことは、2.2.1 にも当てはまります。",
            ),
        }
        before = {"en": "The timezone is not remembered", "ja": "タイムゾーンは覚えません"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, reads)
            self.assertNotIn(before[language], reads)

    def test_guides_answer_the_reading_after_the_stable_version(self) -> None:
        # v2.2.0 V1, after the stable version: what the third new reader of
        # K6a asked of the chapter that installs this app and of the 2.2.0
        # sections of the view page, and the two things found before the
        # publication (what stays as the output opened until it opens again,
        # and the mark of 2.2.0 on the parts of the section of an output that
        # changes, not on its heading). Each sentence is said once, in the
        # words of the page as the catalogs write them, and the words that V1
        # takes away do not come back.
        names = {language: [catalog(language)[f"view.layout.{layout}"] for layout, _ in BUILT_IN_LAYOUTS] for language in GUIDES}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            messages = catalog(language)
            mark = "**{}**" if language == "en" else "「{}」"

            def word(key: str) -> str:
                return mark.format(messages[key])

            if language == "en":
                phrases = (
                    "The output is one folder: files that hold the Activities, Gear, Personal Records, FIT Sessions and Laps, and daily records of the Export in fixed forms, the records of its checks and sources, and context for analysis that people and AI tools can read ([Box 3: Output](#box-3-output)).",
                    "Request a complete Account Data Export on Garmin's official [Data Management page](https://www.garmin.com/account/datamanagement/): Garmin prepares the download later, so follow the instructions that Garmin shows then, and keep its notification until you have downloaded the archive. This app does not sign in to Garmin or request the Export for you.",
                    "the Python install manager is the app of python.org that installs Python on Windows, and it brings the commands `py` and `pymanager` of these steps; before it, `py` was the command of the Python Launcher that came with Python.",
                    "when such a Python is installed already, or you do not know whether it is, you may still install the install manager and go on",
                    "its steps are `pymanager install default`, uninstalling the Python Launcher, and uninstalling Python 3.10 and earlier, in this order, and **Installed apps** shows whether something is still installed.",
                    "makes the icon that starts the GUI (on the desktop on macOS, and on the desktop and in the Start menu on Windows; [Start the GUI from an icon](#start-the-gui-from-an-icon)), and opens the GUI.",
                    'which runs the Python of the virtual environment: `~/garmin-normalizer/bin/python -m garmin_running_data_normalizer gui` on macOS, or `& "$HOME\\garmin-normalizer\\Scripts\\python.exe" -m garmin_running_data_normalizer gui` on Windows.',
                    "**Exit code**: the number that the command that stopped returned (its exit code); on macOS, `echo $?` right after it stopped shows it.",
                    f"When the GUI does not open, so that you cannot use {word('tools.report')} on its page, fill in the fields in this way:",
                    "You need an account of GitHub, which you can make for free; GitHub is the only place to tell us. The fields of the form are in English, and you may write in English or in Japanese.",
                    "Write what happened yourself (in English or in Japanese), choose whether the synthetic data shows the problem, and tick the four checks that no personal data is in it.",
                    "The line installs the new version into the same virtual environment `garmin-normalizer`, and makes the icon again.",
                    f"stop the GUI first: choose {word('quit.button')} at the bottom of the page ([Stop the GUI](#stop-the-gui)).",
                    "as [Remove this app](#remove-this-app) says ([Later launches](#later-launches) says where the folder is).",
                    "[Later launches](#later-launches) says where it is): the marks in it are gone then.",
                    f"The training and running-form items are those of the groups {word('view.group.act')} and {word('view.group.fit')} of the item shelf; the daily items and the estimates are those of {word('view.group.body')} and {word('view.group.est')}.",
                    "(The time of the panels is the duration in the record of Garmin: the time of the activity as recorded, which is neither the whole time with the pauses nor the moving time alone.)",
                    "Press Enter in a field, or change its value and then press elsewhere or move on with Tab, and the conditions apply",
                    "Tab moves from field to field, and Enter, or a value changed in a field before Tab moves on, applies them",
                    f"{word('view.conditions.clear')} clears the filter in use, and that is remembered too (the next time, there are no conditions)",
                    "Where the data of the names is too large, the page goes on in this way, without the names only.",
                    f"A file of the names that is broken stops the output, as any broken file does, and {word('view.stop.heading')} shows.",
                    f"it gives the numbers of the whole output (the days of {word('view.period.all')}), not of the period chosen",
                    f"{word('view.item.hrv')}, and {word('view.item.rhr')} (the HRV is a reference value read from FIT files, which can differ from Garmin's HRV status)",
                    "(the Japanese names are " + ", ".join(names["ja"][:-1]) + ", and " + names["ja"][-1] + "), nor the name of another of your layouts; names that differ only in case or in full or half width are the same name.",
                    "the panels, the period, and the grouping are then as they were before (the grouping while comparing is chosen apart from that of the panels).",
                    f"December (not the grouping {word('view.grain.month')}).",
                    "such as VO2 Max (it has a line for each activity type, and its lines also split on the day when the records of Garmin that its values come from change from the activity records to the MaxMet records, as the note of its panel says), by the names of the key of its panel.",
                    "the days, weeks, or months in rows (the first column named by the grouping) and the years in columns,",
                    f"each year with a column of values and one of counts ({word('view.compare.count.activities')}: the activities, the days with a value, or the records, by the item, as a note under the table says)",
                    f"The years chosen are not remembered: each time, the newest four. {word('view.compare.show')} and {word('view.compare.month')} are remembered for the next time",
                    f"({word('view.grain.day')} or {word('view.grain.week')} with one month chosen in {word('view.compare.month')} of the bar).",
                    f"the item shelf, and the layouts are not used, and are grayed; so are the groupings {word('view.grain.auto')} and {word('view.grain.year')}, and the grouping {word('view.grain.month')} too where one month is chosen in {word('view.compare.month')} of the bar.",
                    f"Where the numbers cannot be shown, {word('view.stop.series_heading')} shows under the bar above the panels, with the reason and its code, in the words of a stop of the panels.",
                    "For another reason that shows again when you try again, tell us the reason and the code ([Report a problem on GitHub](#report-a-problem-on-github)).",
                    f"Where the output can no longer be read (where it is broken, for example), {word('view.compare.button')} closes too, and {word('view.stop.heading')} shows.",
                    "(for a race mark with an end day, the race day is its first day, and the days after it are left out).",
                    "The races show as cards in the place of the years, newest first",
                    "The card of a race shows the head of its name and its date",
                    "In the table, 0:10 is hours and minutes for the time (10 minutes), and minutes and seconds for the average pace (10 seconds a kilometer).",
                    f"numbers being read (the window says {word('view.loading')})",
                    "open a comparison of years, a list, or the summary (all from 2.2.0) again as below",
                    # Stage W1 of v2.2.1: the page opens the output again by itself.
                    f"From 2.2.1, where the page finds, as it gives numbers (when you press the button of the period again, for example), that the days, the activity types, or the like of the output have changed, it opens the output again by itself, as choosing the same output folder with {word('target.other')} does:",
                    f"the overview under the panels, the years that {word('view.compare.button')} can choose, the days that {word('view.period.custom')} can choose, and the list of the activity types are then of the output as it is now.",
                    f"An enlarged panel and {word('view.panel.table')} on a panel are undone, and the years and the races chosen in {word('view.compare.button')} are the first ones again. Where the output",
                    "Where the output is read again with the same days and activity types (where only the date changed, for example), it is not opened again.",
                    "The list of the activities of a day, week, month, or year does not notice that the output changed: open it again after the panels show new numbers.",
                    f"In 2.2.0, pressing the button of the period again does not renew the overview under the panels and the like: choose the same output folder with {word('target.other')} to open the output again (choosing the same output again in {word('view.output.label')} does not open it again).",
                    f"An enlarged panel and {word('view.panel.table')} on a panel are then undone, and the years and the races chosen in {word('view.compare.button')} are the first ones again.",
                    # Stage W2 of v2.2.1: where the question of Quit shows.
                    "Its question, **Quit this app?**, shows from 2.2.1 right above **Quit the app…**, ending where the button ends (across the bar where a narrow window leaves too little room left of the button; in 2.2.0, at the left end of the bar at the bottom).",
                )
                gone = (
                    "Without the GUI, fill in",
                    "shows at the left end of the bar at the bottom (**Quit the app…** is at the right end).",
                    # Stage W1 of v2.2.1: the bullet of 2.2.0 before it.
                    "Pressing the button of the period again does not renew the overview under the panels, the years that",
                    "The line installs into the same virtual environment",
                    "change its value and leave it",
                    "field that is left",
                    "[What is remembered for the next time](#what-is-remembered-for-the-next-time) says where it is",
                    "The races show as buttons",
                    "The button of a race",
                    "an answer on its way",
                    "numbers on their way",
                )
            else:
                phrases = (
                    "出力は 1 つのフォルダーで、Garmin のアクティビティ・ギア・自己ベスト・FIT のセッションとラップ・毎日の記録を決まった形にそろえたファイルと、確かめと出どころの記録、人と AI が読む分析の手がかりが入ります（[3 の箱：出力](#3-の箱出力)）。",
                    "Garmin の公式の [Data Management のページ](https://www.garmin.com/account/datamanagement/)で、Account Data Export をまるごとリクエストします。Garmin はダウンロードをあとで用意するので、Garmin がそのときに出す手順に従い、ダウンロードし終えるまで、Garmin からの知らせを残しておいてください。このアプリは、Garmin にサインインしたり、代わりにリクエストしたりはしません。",
                    "（python.org の、Windows に Python を入れるためのアプリです。この手順の `py` と `pymanager` のコマンドは、これが入れます。前は、Python と一緒に入る Python Launcher が、`py` のコマンドでした）。",
                    "それがもう入っているときや、入っているかどうか分からないときも、そのまま install manager を入れて進めてかまいません",
                    "（その手は、`pymanager install default`、Python Launcher のアンインストール、3.10 以前の Python のアンインストールの順です。アンインストールしたかは、「インストールされているアプリ」に残っているかで分かります）。",
                    "（macOS ではデスクトップに、Windows ではデスクトップとスタートメニューにできます。[アイコンから起動する](#アイコンから起動する)）、GUI を開きます。",
                    'アイコンなしで起動してください（macOS は `~/garmin-normalizer/bin/python -m garmin_running_data_normalizer gui`、Windows は `& "$HOME\\garmin-normalizer\\Scripts\\python.exe" -m garmin_running_data_normalizer gui`）。',
                    "Exit code：止まったコマンドが返した数（終了コード）です。macOS では、止まったすぐあとに `echo $?` を動かすと出ます。",
                    f"GUI を開けないとき（画面の{word('tools.report')}を使えないとき）は、書式の欄に次のように書きます。",
                    "知らせる所は GitHub だけです。書式の欄の名前は英語ですが、日本語で書いてかまいません。",
                    "何が起きたかは自分で書き（日本語でかまいません）、合成データで起きるかを選び、",
                    "1 行は、新しいバージョンを同じ仮想環境 `garmin-normalizer` に入れ、アイコンも作り直します。",
                    f"先に GUI を終えてください（画面の下の{word('quit.button')}を押します。[GUI を終える](#gui-を終える)）。",
                    "設定のフォルダーごとごみ箱へ入れてください（設定のフォルダーの場所は、[2 回目からの起動](#2-回目からの起動)にあります）。",
                    "（ファイルの場所は[2 回目からの起動](#2-回目からの起動)にあります。その中の印は無くなります）。",
                    f"練習と走りの形の項目は、項目の棚の{word('view.group.act')}と{word('view.group.fit')}の組の項目で、毎日の項目と推定値は、{word('view.group.body')}と{word('view.group.est')}の組の項目です。",
                    "（段の「時間」は、Garmin の記録の duration で、記録した活動の時間です。一時停止を含む全体の時間でも、動いていた時間だけでもありません）。",
                    "欄で Enter キーを押すか、欄の値を変えてから、ほかの所を押すか Tab キーで移ると効きます",
                    "Tab キーで欄を移り、Enter キーを押すか、欄の値を変えてから Tab キーで移ると効きます",
                    f"{word('view.conditions.clear')}は今の絞りを外し、外したことも覚えます（次に開いたときも、条件はありません）。",
                    "名前のデータが大きすぎるときは、このように名前だけを使わずに続けます。",
                    f"名前のファイルが壊れているときは、ほかのファイルが壊れているときと同じく、出力を開けずに止まり、{word('view.stop.heading')}と出ます。",
                    f"のように、選んだ期間によらず、出力の全体（期間の{word('view.period.all')}と同じ）の数です。",
                    f"{word('view.item.hrv')}{word('view.item.rhr')}（HRV は、FIT から読んだ参考の値で、Garmin の HRV ステータスと同じとは限りません）",
                    "（英語の名前は " + "、".join(names["en"]) + " です）。自分のほかのレイアウトと同じ名前も使えません。大文字と小文字、全角と半角の違いだけの名前は、同じ名前です。",
                    "戻ると、段・期間・まとめ方は、くらべる前のとおりです（くらべる間のまとめ方は、段のまとめ方とは別に選びます）。",
                    f"並びます（まとめ方の{word('view.grain.month')}とは別のものです）。",
                    "（VO2 Max は種目ごとに線があり、値の元の Garmin の記録が、活動の記録から MaxMet の記録に変わった日でも、線が分かれます。段の注にも出ます）。",
                    f"（1 列めの見出しはまとめ方の名前。年ごとに、値の列と件数の列。件数は、項目によって{word('view.compare.count.activities')}{word('view.compare.count.days')}{word('view.compare.count.records')}で、表の下に何の数かが出ます）。",
                    "選んだ年は覚えず、開くたびに新しい 4 年です。見せ方と月は、次に開いたときも覚えています（[次に開いたときに覚えるもの](#次に開いたときに覚えるもの)）。",
                    f"から選びます（くらべる帯の{word('view.compare.month')}で月を選んだときは{word('view.grain.day')}か{word('view.grain.week')}）。",
                    f"数字を出せなかったとき：くらべる帯の下に{word('view.stop.series_heading')}と出て、段と同じ言葉で、そのわけとコードが出ます。",
                    "ほかのわけで、もう一度してもまた出るときは、そのわけとコードを書いて知らせてください（[GitHub で報告する](#github-で報告する)）。",
                    f"出力が読めなくなったとき（壊れたときなど）は、年でくらべるも閉じて、{word('view.stop.heading')}と出ます。",
                    "（終わりの日もある大会の印では、始まりの日が大会の日で、そのあとの日は入りません）。",
                    "表の 0:10 は、時間では時と分（10 分）、平均ペースでは分と秒（1 km あたり 10 秒）です。",
                    f"・数字を読んでいる間（窓に{word('view.loading')}と出ます）・",
                    "2.2.0 からの年でくらべる・区切りの一覧・まとめの窓は、下のとおり開き直します（年でくらべる間は、期間のボタンは灰色です）。",
                    # Stage W1 of v2.2.1: the page opens the output again by itself.
                    "（2.2.1 から）数字を出すとき（期間のボタンを押し直したときなど）に、見ている出力の日付や種目などが変わったと分かると、見るページは出力を自分で開き直します。",
                    f"{word('target.other')}で同じ出力のフォルダーを選んだときと同じで、段の下の全体図、年でくらべるで選べる年、{word('view.period.custom')}で選べる日付、数える種目の一覧なども、今の出力になります。",
                    f"開き直すと、大きくした段と、段の{word('view.panel.table')}は元に戻り、年でくらべるで選んだ年や大会は、初めのものに戻ります。日付や種目などが同じままの読み直し",
                    "日付や種目などが同じままの読み直し（日付が変わっただけのときなど）では、開き直しません。",
                    "区切りの一覧は、出力が変わったことに気づきません（段の数が新しくなってから、一覧を開き直してください）。",
                    f"2.2.0 では、期間のボタンを押し直しても、段の下の全体図などは新しくなりません。{word('target.other')}で同じ出力のフォルダーを選び、出力を開き直してください（{word('view.output.label')}の欄で同じ出力を選び直しても、開き直しません）。開き直すと、大きくした段と、段の{word('view.panel.table')}は元に戻り、年でくらべるで選んだ年や大会は、初めのものに戻ります。",
                    # Stage W2 of v2.2.1: where the question of Quit shows.
                    "問い「このアプリを終了しますか？」は、（2.2.1 から）「このアプリを終了…」のすぐ上に、その右の端にそろえて出ます（ボタンの左に場所が足りない狭い窓では、下の帯の幅いっぱいに出ます。2.2.0 では、下の帯の左の端に出ます）。",
                )
                gone = (
                    "GUI が無いときは",
                    "下の帯の左の端に出ます（「このアプリを終了…」は右の端にあります）。",
                    # Stage W1 of v2.2.1: the bullet of 2.2.0 before it.
                    "期間のボタンを押し直しても、段の下の全体図、年でくらべるで選べる年、",
                    "同じ仮想環境 `garmin-normalizer` に入り、",
                    "欄の値を変えて離れると",
                    "[次に開いたときに覚えるもの](#次に開いたときに覚えるもの)にあります。その中の",
                    "読み込み中",
                )
            for phrase in phrases:
                with self.subTest(language=language, phrase=phrase):
                    self.assertEqual(reads.count(phrase), 1)
            for phrase in gone:
                with self.subTest(language=language, gone=phrase):
                    self.assertNotIn(phrase, reads)

    def test_guides_say_that_forgetting_removes_the_marks_too(self) -> None:
        # v2.2.0 M1: forgetting the settings also removes the file of the
        # marks of the view page, which cannot be brought back, and forgets
        # what the view page remembers from 2.2.0, as the page's question
        # says; an earlier version keeps that file (the checker, M0 and M1).
        phrases = {
            "en": (
                "The marks of the view page (from 2.2.0), in a file of their own.",
                "from 2.2.0, the marks of the view page are in `gui-marks.json` in the same folder",
                "then removes the file of the settings, never while a run is active; from 2.2.0, it also removes the file of the marks of the view page, `gui-marks.json` in the same folder (the marks cannot be brought back).",
                "The file of the marks of the view page, `gui-marks.json`, stays in the folder of the settings: **Forget the remembered settings…** of 2.2.0 removes it",
            ),
            "ja": (
                "見るページの印（2.2.0 から）。印だけのファイルに残します。",
                "2.2.0 からは、見るページの印を、同じフォルダーの `gui-marks.json` に残します。",
                "先に聞いてから、設定のファイルを消します。2.2.0 からは、同じフォルダーの見るページの印のファイル `gui-marks.json` も消します（印は戻せません）。",
                "見るページの印のファイル `gui-marks.json` は消えずに、設定のフォルダーに残ります。2.2.0 の「覚えた設定を消す…」で消えます。",
            ),
        }
        # What is forgotten, in the words of the page's question; from M4,
        # also the month, what a comparison compares by, the weeks of a span,
        # and whether marks show (the question of 2.2.0 had left them out); from
        # OP2, the two items plotted and the item of a distribution (stages O1
        # and P1 remember them).
        forgotten = {
            "en": "It also forgets the appearance, the items and the item shelf of the view page, your layouts, the period, the grouping, the activity types counted, how years are compared (the way, the month, by year or race day, and the weeks of a span), whether marks show, the two items plotted and the item of a distribution, and the timezone of the last run that made its output.",
            "ja": "画面の色と、見るページで並べた項目と棚の開け閉め、自分のレイアウト、期間とまとめ方と数える種目、年でくらべるのしかた（見せ方・月・くらべ方・範囲の週の数）、「印を出す」かどうか、点で並べる 2 つの項目と分かれ方の項目、前に出力を作った正規化のタイムゾーンも忘れます。",
        }
        removed = {"en": "The marks of the view page are removed too, and cannot be brought back.", "ja": "見るページの印も消えます（戻せません）。"}
        gone = {"en": "removes the file of the settings only", "ja": "設定のファイルだけを消します"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            for phrase in (*phrases[language], forgotten[language]):
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, reads)
            self.assertNotIn(gone[language], reads)
            words = catalog(language)["forget.text_also"]
            self.assertIn(forgotten[language], words)
            self.assertIn(removed[language], words)

    def test_guides_say_what_the_view_page_remembers_from_2_2_0(self) -> None:
        # v2.2.0 K2: the view page remembers the period, the grouping, the
        # activity types counted, and the layouts, and the guides say how they
        # apply to another output; the lines that said that they were not
        # remembered are gone (the checker's opinion 3 of K1), and the names
        # of the layouts saved, the days of a custom range (which can be days
        # of the person's life), the types, and the timezone are among what
        # the settings hold (the checker's K2-3). From K3, each of them says
        # that it is from 2.2.0, as the guides are those of the release that
        # is published (a finding of the review of the diff by Codex). From L2,
        # the way and the month of a comparison by year are remembered too, and
        # whether years were compared and the years chosen are not. From M4,
        # what a comparison compares by and the weeks of a span (stage M2) and
        # whether marks show (stage M1) are remembered, the marks themselves in
        # their file, and the races chosen and a list of a period (stage M3)
        # are not. From OP2, the two items plotted and the item of a
        # distribution (stages O1 and P1) are remembered, and another view shown
        # and what is chosen in it are not; nothing of the view is remembered
        # while no panel is left, which is said once, for all of it (the
        # checker's review of the plan of OP2). From L3, the year highlighted
        # on one panel is not remembered.
        phrases = {
            "en": (
                "At first, the period is **All time**, and the grouping **Auto**; from 2.2.0, those chosen last stay for the next time",
                "or **Dark** is chosen); from 2.2.0, also the period, the grouping, the activity types counted, the layouts (those saved, and the one used last), the way and the month of [Compare years](#compare-years-from-220), what it compares by (the years or the race days) and the weeks of a span, whether **Show marks** is on, the two items plotted and the item of a distribution of [Other views](#other-views-from-220), and the [conditions](#conditions-from-220). The [marks](#marks-from-220) themselves are kept in the file of the marks.",
                "While no panel is left, neither that nor the period, the conditions, or another choice changed meanwhile is remembered: what was remembered before stays (the appearance, the layouts saved, and the marks are kept as ever).",
                "When another output opens (from 2.2.0), a period such as **1 year** stays as it is.",
                # From stage U2 of v2.2.0, as the design and the code have it: the
                # days chosen stay, and the values count the days of the output.
                "A period chosen with **Custom range…** keeps its days when it overlaps those of the output in part: the values and the charts count only the days of the output in it, and in **Summary…** the period before has as many days as the range chosen, and the values of a period that the output cuts are marked *, with a dash (—) for the difference.",
                "It becomes **All time** when it does not overlap them at all.",
                "A range that overlaps them in part keeps the days chosen, and the values and the charts count only the days of the output in it.",
                "The activity types counted are those remembered that the output has; when it has none of them, every running type in the output.",
                "Not remembered: the output shown, the same scale, a panel enlarged, a table shown, full screen, whether years were compared, with the years or races chosen and the year highlighted, whether a list of activities was open, whether another view was shown, with the point, the range, or the month of the shoes chosen, whether the summary was open, and whether the window of saving as an image was open, with its choices.",
                "the names of places and of the items of the view page, and from 2.2.0 also the names of the layouts you saved, the days of a period chosen with **Custom range…**, the activity types counted, the words of the conditions of the view page, and the timezone. They stay on this computer",
            ),
            "ja": (
                "期間とまとめ方は、はじめは「全期間」と「自動」です。2.2.0 からは、選んだものを覚えていて、次に開いたときもそのままです",
                "画面の色（「ライト」か「ダーク」を選んだとき）。2.2.0 からは、期間、まとめ方、数える種目、レイアウト（保存したレイアウトと、最後に使ったレイアウト）、[年でくらべる](#年でくらべる220-から)の見せ方と月、くらべ方（年か大会の日か）と範囲の週の数、「印を出す」かどうか、[ほかの見方](#ほかの見方220-から)の点で並べる 2 つの項目と分かれ方の項目と、[条件](#条件で絞る220-から)も覚えます。[印](#印220-から)そのものは、印のファイルに残ります。",
                "段を全部外して 1 つも無い間は、そのことも、その間に変えた期間・条件などのしかたも覚えず、前に覚えたもののままです（画面の色、保存したレイアウト、印は覚えます）。",
                "ほかの出力を開いたとき（2.2.0 から）：「1 年」などの期間は、そのままです。",
                # The words of the button of an enlarged panel changed in 2.2.0 (the
                # checker's K3-2); the English words are those of 2.1.0.
                "⤢ の所が「段を並べて見る」（2.1.0 では「元に戻す」）になり、",
                "「範囲を選ぶ…」で選んだ期間は、その出力の日の範囲と一部だけ重なるときは選んだ日付のままで、値とグラフは、その中の出力の日だけで数えます。「まとめ…」の前の期間は選んだ範囲と同じ日数で、出力で切れた期間の値には「*」が付き、差は「—」です。まったく重ならないときは「全期間」になります。",
                "出力の日の範囲と一部だけ重なる範囲は、選んだ日付のままで、値とグラフは、その中の出力の日だけで数えます。",
                "数える種目は、覚えた種目のうち、その出力にある種目です。1 つも無いときは、その出力のランニングの種目すべてです。",
                "覚えないもの：見ていた出力、目盛りをそろえるか、段を大きくしたか、表で見ていたか、全画面、年でくらべるを開いていたかと、選んだ年や大会、強調した年、区切りの一覧を開いていたか、ほかの見方を開いていたかと、選んだ点や分かれ方の区間、靴ごとで選んだ月、まとめの窓を開いていたか、画像で保存の窓を開いていたかと、その選び。",
                "2.2.0 からは、保存したレイアウトの名前、「範囲を選ぶ…」で選んだ期間の日付、数える種目、見るページの条件の言葉、タイムゾーンも入ります。",
            ),
        }
        before = {
            "en": ("Each time the view page opens, the period is **All time**", "Not remembered: the output shown, the period"),
            "ja": ("見るページを開くたびに、期間は「全期間」", "覚えないもの：見ていた出力、期間"),
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, reads)
            for phrase in before[language]:
                with self.subTest(language=language, before=phrase):
                    self.assertNotIn(phrase, reads)

    def test_guides_give_the_colors_of_the_years_and_a_year_highlighted(self) -> None:
        # v2.2.0 L3: the years laid over one another and their running totals
        # have colors of their own, newest first, the 5th and 6th dashed too;
        # a press on a key, a line, a point, or the name at the end of a line
        # highlights a year, and a press again or Esc on the chart or a key
        # puts it back; not remembered, the same by race day, without fading
        # in forced colors, and in a picture as it shows. The help says it in
        # a sentence, and each says what the page does.
        phrases = {
            "en": (
                "With **Overlay** and **Running total**, each year has a color of its own: of the years chosen, newest first, the purple of the page, orange, teal, navy, dark blue, and light blue (on a dark screen, navy becomes a light gray, dark blue a brick red, and light blue a yellow), and the 5th and 6th years are dashed too. Taking a year out colors the years left again, newest first.",
                "With **Overlay** and **Running total**, press a year in the legend, a line, a point, or the year at the end of a line to highlight that year: its line gets thicker and goes on top, and the other years fade. Press it again, or press Esc on the chart or on a year in the legend, to go back. A press away from the lines and the points changes nothing. The year highlighted is not remembered. Comparing by race day works the same way. In forced colors (a contrast theme of Windows, for example), the other years do not fade; the year highlighted only gets thicker.",
                "The years in the legend of **Overlay** and **Running total** (from 2.2.0) are reached with Tab; Enter or Space highlights one, and pressing it again, or Esc on the chart or on a year in the legend, goes back",
                "A year highlighted when comparing years goes in as it shows: the other years faint, and its name bold in the legend.",
            ),
            "ja": (
                "「重ねる」と「累積」では、年ごとに色がちがいます。選んだ年のうち新しい順に、ページの紫・オレンジ・青緑・紺・濃い青・水色（暗い画面では、紺が白に近い灰、濃い青が赤茶、水色が黄）で、5 年めと 6 年めは破線にもなります。年を外すと、残った年を新しい順に塗り直します。",
                "「重ねる」と「累積」で、凡例の年・線・点・線の端の年を押すと、その年を強調します（線が太くなっていちばん上になり、ほかの年は薄くなります）。もう一度押すか、グラフか凡例の年で Esc キーを押すと戻ります。線や点から離れた所を押しても変わりません。強調した年は覚えません。大会の日でくらべるときも同じです。強制カラーの画面（Windows のコントラスト テーマなど）では、ほかの年は薄くならず、強調した年が太くなるだけです。",
                "「重ねる」と「累積」の凡例の年（2.2.0 から）は、Tab キーで移り、Enter キーか Space キーで強調します。もう一度押すか、グラフか凡例の年で Esc キーを押すと戻ります",
                "年でくらべるで強調した年は、そのまま写ります（ほかの年は薄く、凡例ではその年の名前が太字になります）。",
            ),
        }
        help_text = {
            "en": " In “Overlay” and “Running total”, each year has a color of its own, and pressing a year in the legend or its line highlights it (press it again, or Esc on the chart or on a year in the legend, to go back).",
            "ja": "「重ねる」と「累積」では年ごとに色がちがい、凡例の年や線を押すと、その年を強調します（もう一度押すか、グラフか凡例の年で Esc キーを押すと戻ります）。",
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, reads)
            catalog = json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            with self.subTest(language=language, help=True):
                self.assertTrue(catalog["view.help.compare_text"].endswith(help_text[language]))
        # What the page does: the colors by the order among the years chosen
        # (the newest the 6th step), on the lines of one panel only; a press on
        # a key, on the names first, then on what the lines draw; Esc on the
        # chart or a key; nothing remembered; no fading in forced colors (the
        # test of the styles); the marks on the shapes of a picture.
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        chart = (STATIC_ROOT / "view_chart.mjs").read_text(encoding="utf-8")
        self.assertIn("return new Map(sorted.map((year, index) => [year, MAX_COMPARE_YEARS - index]));", function_body(flow, "yearSteps"))
        self.assertIn('const color = one ? `y${entry.data[index].step}` : "c1";', function_body(page, "drawComparePlot"))
        self.assertIn("if (box && x >= box.x && x <= box.x + box.width && y >= box.y && y <= box.y + box.height) {", function_body(chart, "shapeAt"))
        self.assertIn("event.target.matches?.('.plot[data-plot=\"one\"], button.key[data-lit]')", page)
        self.assertNotRegex(function_body(page, "viewValues"), r"\blit\b")
        self.assertIn('const className = key.getAttribute("aria-pressed") === "true" ? "save-key lit" : "save-key";', function_body(page, "saveComparePart"))

    def test_guides_say_where_the_item_compared_is_chosen(self) -> None:
        # v2.2.0 U3 (a new AI looked for a field of the name of the label of
        # that list, which is only for the ear): the guides say the list of
        # items in the title, as the page does.
        sentences = {
            "en": "The list of items in the title (where the item compared is named): to compare another item.",
            "ja": "題の中の項目の一覧（いまの項目の名前が出ている所）：ほかの項目に替えられます。",
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            with self.subTest(language=language):
                self.assertEqual(reads.count(sentences[language]), 1)
                self.assertNotIn("**Item**:" if language == "en" else "「項目」：", reads)

    def test_guides_say_that_forgetting_removes_the_half_written_files(self) -> None:
        # v2.2.1 W4: forgetting the settings also removes the half-written
        # files that a write leaves where this app stops in the middle of it,
        # and the privacy section says that they hold a copy; the design
        # document gives the rules. From W7 (Codex's whole review before
        # W6f, and the checker's review of the plan): what to do on Windows
        # for ten minutes after this app stopped in the middle of a write;
        # from stage X1 of v2.3.0 the bar tells that it stayed, and the button
        # can be pressed again, with a line of 2.2.1 (the checker's review of
        # the plan of X1). The sentences of W7 are gone.
        said = {
            "ja": (
                "（2.2.1 から）書く途中でこのアプリが落ちたときに残る書きかけのファイル（設定や印の写しが入ります）も消し、それだけが残っているときも押せます。消すのは、書いたこのアプリがもう終わっているものか、10 分より古いものです（Windows では、10 分より古いものだけ）。ほかに開いているこのアプリが書いている途中のものは残します。",
                "（2.2.1 から）書く途中でこのアプリが落ちたときに残る書きかけのファイルにも、設定や印の写しが入ります。「覚えた設定を消す…」で一緒に消えます（Windows では、落ちてから 10 分たったあとに）。",
                "Windows では、落ちてから 10 分たたないうちは、書きかけのファイルは消えません。（2.3.0 から）そのときは、残したことを下の帯に出し、ボタンは押せるままなので、10 分たってから、もう一度押してください（2.2.1 では、ボタンが押せなくなり、ページを読み込み直すと押せました）。",
            ),
            "en": (
                "From 2.2.1, it also removes the half-written files that a write leaves when this app stops in the middle of it (they hold a copy of the settings or the marks), and it can be pressed while only such a file is there: one whose launch has ended, or one older than ten minutes (on Windows, only one older than ten minutes). One that another open launch of this app is writing at that moment stays.",
                "A half-written file that a write leaves when this app stops in the middle of it holds a copy of them too; from 2.2.1, **Forget the remembered settings…** removes it with them (on Windows, once it is ten minutes old).",
                "On Windows, for ten minutes after this app stopped in the middle of a write, the half-written file stays. From 2.3.0, the bar then says so, and the button can still be pressed: once ten minutes have passed, press it again (in 2.2.1, the button could not be pressed until the page was loaded again).",
            ),
        }
        gone = {
            "ja": ("ボタンも押せないことがあります。", "10 分たってからページを読み込み直し、押してください。"),
            "en": ("you may not be able to press the button", "load the page again, and press it."),
        }
        # What the bar says, as the guides tell it (stage X1 of v2.3.0).
        tells = {
            "ja": "覚えた設定を消しました。書きかけのファイルは、書いている途中かもしれないので残しました。10 分ほどたってから、もう一度押してください。",
            "en": "The remembered settings are forgotten. A half-written file stays, as a write may still be using it; press the button again in about ten minutes.",
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            for sentence in said[language]:
                with self.subTest(language=language, sentence=sentence[:30]):
                    self.assertEqual(reads.count(sentence), 1)
            for old in gone[language]:
                with self.subTest(language=language, gone=old[:30]):
                    self.assertNotIn(old, reads)
            with self.subTest(language=language, bar="settings.temporary_left"):
                self.assertEqual(catalog(language)["settings.temporary_left"], tells[language])
        flow = (STATIC_ROOT / "flow.mjs").read_text(encoding="utf-8")
        self.assertIn('  TEMPORARY_LEFT: "settings.temporary_left",\n', flow)
        outcome = re.search(r"export function forgetOutcome\(answer\) \{(.*?)\n\}", flow, re.DOTALL)
        assert outcome is not None
        self.assertIn('  if (answer?.notice === "TEMPORARY_LEFT") {\n    return { key: null, notice: "TEMPORARY_LEFT", present: true, forgotten: true };\n  }', outcome.group(1))
        code = (ROOT / "src" / "garmin_running_data_normalizer" / "gui" / "settings.py").read_text(encoding="utf-8")
        remove = re.search(r"\ndef remove_settings\(.*?\n\n\n", code, re.DOTALL)
        assert remove is not None
        self.assertIn("        return (TEMPORARY_LEFT if newer else None), present, _generation\n", remove.group(0))
        self.assertIn("        if not removed[0] or 0 in left:\n            return SETTINGS_NOT_REMOVED, present, _generation\n        if not all(removed) or left:\n            return MARKS_NOT_REMOVED, present, _generation\n", remove.group(0))
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        for sentence in (
            "From v2.2.1 (stage W4) forgetting also removes the temporary files that a write leaves where this app stops in the middle of it",
            "and any older than ten minutes.",
            "A newer one of another process that is alive, another launch in the middle of its write, stays, and so does the folder with it.",
            "One that cannot be removed is told as its file would be, and the button can be pressed while one is there.",
            "A folder that is a link is never looked into, as the settings are never written into one;",
            "a file is removed only while it is still the one looked at (a newer write or another file in its place stays);",
            "and one that cannot be looked at, or a folder that cannot be listed, is told as left.",
            # Stage X1 of v2.3.0.
            "From v2.3.0 (stage X1) a newer one that stays counts as something to forget too, so that the button can still be pressed (on Windows, one that a stop left stays until it is ten minutes old): forgetting tells that it stayed (`TEMPORARY_LEFT`, where the settings and the marks are gone, so the page drops the colors remembered in the tab as well), and pressing again once it is ten minutes old removes it.",
            "The status of a launch and forgetting count what there is to forget alike.",
        ):
            with self.subTest(design=sentence[:30]):
                self.assertEqual(design.count(sentence), 1)
        # The colors are remembered in the tab (sessionStorage), not in the
        # browser: the words of X1 were put right in stage X2 (the checker's
        # review of the diff of X1, B2).
        self.assertNotIn("the colors remembered in the browser", design)

    def test_guides_say_that_escape_closes_a_question_wherever_the_focus_is(self) -> None:
        # Stage X1 of v2.3.0 (the person's finding in W6d, and the checker's
        # review of the plan of X1): the section on the keyboard says, once in
        # each language, that the questions close by Escape wherever the focus
        # is, one at a time, with a line of 2.2.1; with the names of the
        # questions and of their safe answers as the page gives them; and the
        # design gives the rule.
        said = {
            "ja": "（2.3.0 から）「このアプリを終了しますか？」「覚えた設定を消しますか？」と、正規化を取り消すかの問いは、開いているあいだ、フォーカスがどこにあっても、Esc キーで閉じます（「やめる」「続ける」を押したのと同じです）。2 つ以上開いているときは、フォーカスのある問いを、無ければあとから開いた問いを、1 回に 1 つ閉じます。2.2.1 までは、問いの中にフォーカスがあるときだけでした。",
            "en": "From 2.3.0, the questions **Quit this app?** and **Forget the remembered settings?**, and the question of cancelling a normalization, close by Escape wherever the focus is while they show, as **Keep using it**, **Keep them**, and **Continue** do. Where two or more show, each Escape closes one: the one that holds the focus, else the one that opened last. Until 2.2.1, Escape closed one only while the focus was in it.",
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            section = text.split("\n## キーボードとスクリーンリーダー\n" if language == "ja" else "\n## Keyboard and screen readers\n")[1].split("\n## ")[0]
            keyboard = " ".join(section.split()) if language == "en" else re.sub(r"\n *", "", section)
            messages = catalog(language)
            with self.subTest(language=language):
                self.assertEqual(reads.count(said[language]), 1)
                self.assertIn(said[language], keyboard)
                if language == "ja":
                    names = (f"「{messages['quit.question']}」", f"「{messages['forget.question']}」", f"「{messages['quit.no']}」", f"「{messages['run.cancel_no']}」")
                    self.assertEqual(messages["forget.no"], messages["quit.no"])
                else:
                    names = tuple(f"**{messages[key]}**" for key in ("quit.question", "forget.question", "quit.no", "forget.no", "run.cancel_no"))
                for name in names:
                    self.assertIn(name, said[language])
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        self.assertEqual(
            design.count(
                "From v2.3.0 (stage X1) a question of a page (quitting, forgetting the settings, and cancelling a run) closes by Escape wherever the focus is while it shows, as its safe answer does: one for each Escape, the one that holds the focus, else the one that opened last. A part of the page that closes by Escape takes it first, and an Escape while a text is composed (an IME) closes no question (a window closes by it as before). On the view page Escape cancels a drag first, and graphs only, which hide the bar and a question left open in it, are left by it."
            ),
            1,
        )
        flow = (STATIC_ROOT / "flow.mjs").read_text(encoding="utf-8")
        choose = re.search(r"export function questionToClose\(event, open, focused\) \{(.*?)\n\}", flow, re.DOTALL)
        assert choose is not None
        self.assertIn('  if (event?.key !== "Escape" || event.defaultPrevented === true || event.isComposing === true) {\n    return null;\n  }', choose.group(1))
        self.assertIn("  return open.length > 0 ? open[open.length - 1] : null;", choose.group(1))

    def test_guides_say_the_cadence_in_steps_a_minute(self) -> None:
        # Stage X10 of v2.3.0 (the person's answer 「1 歩数にそろえる」): the page
        # writes the cadence in steps a minute, twice the value of one foot
        # that Garmin's files record (checked with the running types), and the
        # guides say so once, with the width of its ranges in those steps, and
        # that the output and the CSV file of series keep the values as
        # recorded (the checker's review of the plan, 1 and 2).
        said = {
            "ja": (
                "ピッチは 1 分の歩数（両足）です。",
                "Garmin のファイルは片足の数で記録しているので、このアプリが 2 倍して出します（2.3.0 から。2.2 までは記録の値のままで、時計の画面の半分でした）。",
                "2 倍で時計と同じになることは、走る種目で確かめました。",
                "ほかの種目に値があるときも、同じく 2 倍して出します。",
                "正規化の出力の値は変わりません。",
                "ピッチだけは、CSV では記録の値のまま（片足の数）で、見るページの値（1 分の歩数）の半分です。",
                "| ピッチ | 10 歩/分 |",
            ),
            "en": (
                "The cadence is in steps per minute (both feet).",
                "Garmin's files record it of one foot, so this app doubles it (from 2.3.0; up to 2.2, it was the value as recorded, half of what the watch shows).",
                "That the doubled value is the watch's was checked with the running types; a value of another type is doubled too.",
                "The values of the output do not change.",
                "Only the cadence differs from the view page: the CSV file keeps it as recorded (of one foot), half of the steps per minute that the page shows.",
                "| Cadence | 10 spm |",
            ),
        }
        gone = {"ja": "| ピッチ | 5（Garmin と同じ単位、記載なし） |", "en": "| Cadence | 5 (same unit as Garmin, not named) |"}
        for language, sentences in said.items():
            raw = GUIDES[language].read_text(encoding="utf-8")
            text = " ".join(raw.split()) if language == "en" else re.sub(r"\n *", "", raw)
            self.assertNotIn(gone[language], raw)
            for sentence in sentences:
                with self.subTest(language=language, sentence=sentence[:40]):
                    self.assertEqual(text.count(sentence), 1)

    def test_guides_say_the_words_of_the_page_of_v221(self) -> None:
        # v2.2.1 W3 (the person's answer 「おすすめのとおり」): the guides name the
        # bars, the buttons, the steps of the colors, and the ranges of a
        # distribution as the page does; say what the panels and the plot do
        # not show as the page does; and name the list of a period by its
        # grouping. The old words are gone; the texts of the pictures wait for
        # the pictures (W6).
        def reads_of(language: str) -> str:
            text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", GUIDES[language].read_text(encoding="utf-8"))
            return " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)

        gone = {
            "ja": ("色の区切り", "年の札", "大会の札", "区切りの幅", "Garmin の値のまま", "このパソコン", "見せ方を選び直すと", "段の上の帯", "あいだの関係（どちらが原因か）", "範囲と回数", "回数の無い区切り", "どの帯でも", "平年の帯", "分かれ方の区切り", "ごとの区切りに何回", "その区切りと回数"),
            "en": ("Garmin value as is", "The activities of a period", "the activities of a period", "up to 500 a period", "a period cut short", "choose a period with"),
        }
        said = {
            "ja": (
                "並べた項目のあいだに関係があるか、どちらが原因か、何をすればよいかは示しません。",
                "数字の決まり（段の名前の横に出る「合計」などの表示が、その段の値の作り方です）：",
                "グラフの区切り（まとめ方で決まる 1 つぶん。週でまとめていれば 1 週）を押すと、",
                "期間の印は、その期間を薄く塗った所で、",
                "段の上のくらべる帯で選びます。",
                "「年」：出力にある年のボタンです。",
                "年のボタンの代わりに、大会のボタンが新しい順に出ます。",
                "大会の日でくらべるときの大会のボタンは、名前の全部と日付を読み上げます。",
                "値のある最初の区間から最後の区間までの数（回数の無い区間も入れて）が 200 を超えるときは、",
                "| パワー | 10（Garmin と同じ単位、記載なし） |",
                "くらべる帯（年でくらべる）と見方の帯（点で並べる・分かれ方・靴ごと）の",
                "下の帯に「このアプリを終了しています…」と出て",
                "1 km ごとの区間に何回あったかが棒で出ます。",
                "棒を押すと、右上にその区間と回数が出ます。",
            ),
            "en": (
                "### The activities of a day, week, month, or year (from 2.2.0)",
                "press a bar or a point of the chart (one day, week, month, or year, by the grouping), and the list of its activities opens just under the panel.",
                "(where none does, it says so by the grouping, such as **No activity of the week chosen meets the conditions.**), up to 500 at a time.",
                "the days, weeks, or months in rows (the first column named by the grouping) and the years in columns,",
                "* marks one cut short (by an end of the output, of the year or month, or by the race day), and — one not in the year (outside the output,",
                "- **Race week (to the race day)**, a week of the readings and the table,",
                "| Power | 10 (same unit as Garmin, not named) |",
                "Where there would be more than 200 ranges from the first with a value to the last (those of no activity too),",
            ),
        }
        for language in GUIDES:
            text = reads_of(language)
            for words in gone[language]:
                with self.subTest(language=language, gone=words):
                    self.assertNotIn(words, text)
            for words in said[language]:
                with self.subTest(language=language, said=words):
                    self.assertEqual(text.count(words), 1)
        # The links to the section of the list follow its heading.
        english = GUIDES["en"].read_text(encoding="utf-8")
        self.assertEqual(english.count("(#the-activities-of-a-day-week-month-or-year-from-220)"), 2)
        self.assertNotIn("#the-activities-of-a-period-from-220", english)

    def test_guides_say_where_the_notes_of_a_calendar_open(self) -> None:
        # v2.2.0 U3 (the person's hand check of the release candidate): the
        # notes of the legend of a calendar open under its info button,
        # named as the page names it.
        sentences = {
            "en": "**About the legend**, at the right of the legend, opens the rule of the steps and, for a total or a count with days without a recorded activity (0), their number.",
            "ja": "色の段階の説明と、記録の無い日（0）の数（合計や回数の項目で、その日があるとき）は、凡例の右の「凡例の見方」を押すと開きます。",
        }
        quote = {"en": "**{}**", "ja": "「{}」"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            with self.subTest(language=language):
                self.assertEqual(reads.count(sentences[language]), 1)
                self.assertIn(quote[language].format(catalog(language)["view.compare.legend_about"]), sentences[language])

    def test_guides_give_the_layouts_of_the_view_page(self) -> None:
        # v2.2.0 K3: the section of the layouts comes before the item shelf
        # and gives the rules of the page: the items of each built-in layout
        # in the words of the shelf, an item without a value stays a panel
        # (the checker's K3-1), the rules of a name and the number of
        # layouts, the grip and its keys, the question before a removal, and
        # that a click outside the window does not close it (the checker's
        # opinion 2 of K2).
        catalogs = {language: catalog(language) for language in GUIDES}
        heading = {"en": "Layouts (from 2.2.0)", "ja": "レイアウト（2.2.0 から）"}
        shelf = {"en": "The item shelf and the panels", "ja": "項目の棚と段"}
        phrases = {
            "en": (
                "The period, the grouping, the activity types, and the conditions are not part of a layout",
                "An item without a value in the output is a panel too",
                "A name has 1 to 30 characters, without line breaks or invisible characters",
                "You can keep up to 20 layouts of your own (the built-in layouts are not counted).",
                "A drag of the grip (⋮⋮) at the left moves a layout too, and so do ↑ and ↓ on the grip. Escape during a drag puts it back.",
                "**Remove** asks first, with **Keep it** chosen.",
                "A click outside it does not close it",
                "Here, **Overwrite the layout** puts the panels shown into that layout, also when it is not the one in use.",
            ),
            "ja": (
                "期間・まとめ方・数える種目・条件は、レイアウトに入りません",
                "その出力に値の無い項目も、段として出ます",
                "名前は 1〜30 字で、改行や見えない文字は使えません。",
                "自分のレイアウトは 20 までです。",
                "左のつまみ（⋮⋮）をなぞっても並べ替えられ、つまみを選んで ↑ ↓ キーでも動かせます。",
                "選ばれているのは「消さない」です。",
                "窓の外を押しても閉じません",
                "ここの「レイアウトを上書き」は、使っているレイアウトでなくても、いまの段でそのレイアウトを書き換えます。",
            ),
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            with self.subTest(language=language, part="order"):
                self.assertLess(text.index(f"\n### {heading[language]}\n"), text.index(f"\n### {shelf[language]}\n"))
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, reads)
            # The words under the name of a card, as the page writes them
            # (a finding of the review of the diff by Codex).
            messages = catalogs[language]
            mark = '"{}"' if language == "en" else "「{}」"
            for words in (messages["view.layouts.changed"], messages["view.layouts.valued"].format(n=2, m=4)):
                with self.subTest(language=language, words=words):
                    self.assertIn(mark.format(words), reads)
            # Each built-in layout with its items, in the words of the page.
            for layout, keys in BUILT_IN_LAYOUTS:
                with self.subTest(language=language, layout=layout):
                    if language == "en":
                        names = [f"**{messages[f'view.item.{key}']}**" for key in keys]
                        line = f"**{messages[f'view.layout.{layout}']}**: " + ", ".join(names[:-1]) + ", and " + names[-1]
                    else:
                        line = f"「{messages[f'view.layout.{layout}']}」：" + "".join(f"「{messages[f'view.item.{key}']}」" for key in keys)
                    self.assertIn(line, reads)

    def test_guides_give_the_comparison_of_years(self) -> None:
        # v2.2.0 L2: the section of comparing years comes after full screen
        # and before what is remembered, and gives the rules of the page (stage
        # L1): the places of weeks, days, and one month on one axis, the value
        # of a year counted as on the panels and partial at both ends of the
        # output (the checker's opinion 2 of L1), a running total of the five
        # totals and counts that goes on after a period without a value, what
        # is not used while comparing and the activity types that still apply
        # (the checker's opinion 1 of L1), the keys of the cross line as the
        # page takes them, and the next step of a stop; it quotes the words of
        # the page as the catalogs write them.
        catalogs = {language: catalog(language) for language in GUIDES}
        heading = {"en": "Compare years (from 2.2.0)", "ja": "年でくらべる（2.2.0 から）"}
        before = {"en": "Full screen", "ja": "全画面で見る"}
        after = {"en": "What is remembered for the next time", "ja": "次に開いたときに覚えるもの"}
        phrases = {
            "en": (
                "a year may have 54",
                # With one month chosen, the weeks count from its first day,
                # and a value is partial only where the output cuts it (the
                # review of the diff by Codex).
                "A week is placed by its order from the week of 1 January (with one month chosen, of the first day of that month)",
                "Where the output starts or ends within a year (or within the month chosen), its value is partial",
                "29 February has a value only in a leap year.",
                "With one month chosen, the days go to the last day of that month in the years chosen.",
                "A period without a record (0) adds nothing, and a period without a value breaks the line; the total goes on from what it was, so that the running total at the end of a year is its",
                "Its table has no columns of counts, which the tables of the other ways have.",
                "**Activity types counted** and **Conditions…** still apply: a change of them also applies to the panels after the way back, and is remembered.",
                "press ← or → to move by one period, Page Up or Page Down by 12, and Home or End to an end",
                # v2.2.0 K6a: where the readings stand at first (the first new
                # reader of 2.2.0rc1, k5f 1, which the Human maintainer took
                # for the stable release on 2026-11-03).
                "At first, and after a change of the grouping or of the month, they are of the last period of the newest year, where the cross line stands too.",
                "group by **Week** or **Month** (by **Week** with one month chosen).",
                # v2.2.0 K6a: the table stays while the same comparison is
                # open, whatever the way to show (the hand checks of rc2);
                # from v2.2.1 (stage W2) a way changed shows the chart again.
                "From 2.2.1, choosing another way in **Show as** brings back the chart, with its legend; changing the item, the years, the month, or the races keeps the table. In 2.2.0, while **Compare years** is open, the table stays when you change **Show as**: to bring back the chart, press **Show as a chart** or **Show as a calendar**.",
            ),
            "ja": (
                "54 週まである年もあります",
                "週は、月曜からの週を、1 月 1 日（月を選んだときは、その月の 1 日）の週から数えた順番でそろえます。",
                "出力がその年（月を選んだときはその月）の途中で始まるか終わるときは、途中の値で",
                "2 月 29 日は、うるう年にだけ値があります。",
                "月を選んだときの日は、選んだ年のその月の日数までです。",
                "記録の無い区切り（0）はそのまま足し、値の無い区切りでは線が切れます。合計はそれまでから続くので、年の終わりの累積は、その年の",
                "表には件数の列がありません（ほかの見せ方の表にはあります）。",
                "「数える種目」と「条件…」は使えます。変えると、戻ったあとの段にも効き、次に開いたときにも覚えています。",
                "← → キーで 1 つずつ、Page Up と Page Down で 12 ずつ、Home と End で端へ動かすと",
                "開いた直後と、まとめ方か月を変えたあとは、いちばん新しい年の最後の区切りの値で、十字線もそこに立ちます。",
                # The days of a custom range, told from the Span of a race day,
                # which the Japanese page also names 範囲 (the second reader of
                # K6a).
                "くらべる間は、期間・‹ ›・「範囲を選ぶ…」の日付の欄・項目の棚・レイアウトは使わず、灰色になります。まとめ方の「自動」と「年」も灰色で、くらべる帯の「月」で月を選んだときは、まとめ方の「月」も灰色です。",
                "まとめ方を「週」か「月」に（くらべる帯の「月」で月を選んだときは「週」に）してください。",
                "（2.2.1 から）ほかの見せ方を選ぶと、図（凡例を含む）に戻ります。項目・年・月・大会を替えても、表のままです。2.2.0 では、年でくらべるを開いている間は、見せ方を替えても「表で見る」のままで、図に戻すには「グラフで見る」か「カレンダーで見る」を押します。",
            ),
        }
        quoted = (
            "view.compare.button",
            "view.panel.unbig",
            "view.compare.show",
            "view.compare.mode.rows",
            "view.compare.mode.overlay",
            "view.compare.mode.cumulative",
            "view.compare.month",
            "view.compare.month_all",
            "view.compare.series",
            "view.panel.table",
            "view.compare.years",
            "view.compare.up_to",
            "view.compare.cumulative_about",
        )
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            with self.subTest(language=language, part="order"):
                self.assertLess(text.index(f"\n### {before[language]}\n"), text.index(f"\n### {heading[language]}\n"))
                self.assertLess(text.index(f"\n### {heading[language]}\n"), text.index(f"\n### {after[language]}\n"))
            start = text.index(f"\n### {heading[language]}\n")
            part = text[start : text.index("\n### ", start + 1)]
            part_reads = " ".join(part.split()) if language == "en" else re.sub(r"\n *", "", part)
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertIn(phrase, part_reads)
            messages = catalogs[language]
            mark = "**{}**" if language == "en" else "「{}」"
            for key in quoted:
                with self.subTest(language=language, words=key):
                    self.assertIn(mark.format(messages[key]), part_reads)
            # The partial year, in the words of the heading of a row.
            date = "October 21" if language == "en" else "10月21日"
            with self.subTest(language=language, part="partial year"):
                self.assertIn(messages["view.compare.until"].format(date=date), part_reads)
            # Every word quoted in the section is a word of the page: a word of
            # the catalogs, the value of a year as a row says it, or the day
            # that the output cuts it (a case of the partial guard).
            words = set(messages.values())
            # The value of a year, and from M4 that of the span of a race as the
            # heading of its row and the last row of its table say it.
            periods = (messages["view.compare.whole_year"], messages["view.compare.this_span"], messages["view.compare.race_days"].format(n=16))
            words |= {messages[key].format(period=period) for key in messages if key.startswith("view.compare.value.") for period in periods}
            words.add(messages["view.compare.until"].format(date=date))
            pattern = r"\*\*([^*]+)\*\*|\"([^\"]+)\"" if language == "en" else r"「([^」]+)」()"
            for word in (bold or plain for bold, plain in re.findall(pattern, part_reads)):
                with self.subTest(language=language, quoted=word):
                    self.assertIn(word, words)
            # The scene of May of every year leads to the section.
            with self.subTest(language=language, part="scene"):
                title = "\n### Compare May of every year\n" if language == "en" else "\n### 毎年の 5 月をくらべる\n"
                begin = text.index(title)
                scene = text[begin : text.index("\n### ", begin + 1)]
                link = "(#compare-years-from-220)" if language == "en" else "(#年でくらべる220-から)"
                self.assertIn(link, scene)
                # The way chosen last is remembered: the scene chooses one row
                # per year (a finding of the review of the diff by Codex).
                self.assertIn(mark.format(messages["view.compare.mode.rows"]), scene)
        # The keys of the cross line, as the page takes them.
        script = (ROOT / "src/garmin_running_data_normalizer/gui/static/view.mjs").read_text(encoding="utf-8")
        self.assertIn("const CROSS_KEYS = { ArrowLeft: -1, ArrowRight: 1, PageUp: -12, PageDown: 12 };", script)
        self.assertIn('} else if (event.key === "Home") {\n    moveCompareCross(0, true);', script)
        self.assertIn('} else if (event.key === "End") {\n    moveCompareCross(compareContext.span, true);', script)

    def test_guides_give_the_list_the_marks_and_the_race_day(self) -> None:
        # v2.2.0 M4: the list of the activities of a period (stage M3) and the
        # marks (stage M1) come after the overview and before full screen;
        # comparing by race day (stage M2) is a part of comparing years; and
        # what happens when the output changes while one looks (the same
        # generation of the checker's reviews of M2 and M3) is said once, in
        # its own section, which the others link to. Each section gives the
        # rules of the page, quotes its words as the catalogs write them, and
        # quotes no other word; the lines of the marks are those of view.css
        # (the checker's M4-1).
        catalogs = {language: catalog(language) for language in GUIDES}
        headings = {
            "en": ("The overview", "The activities of a day, week, month, or year (from 2.2.0)", "Marks (from 2.2.0)", "Full screen", "Compare years (from 2.2.0)", "When the output changes while you look", "What is remembered for the next time"),
            "ja": ("全体図", "区切りのアクティビティの一覧（2.2.0 から）", "印（2.2.0 から）", "全画面で見る", "年でくらべる（2.2.0 から）", "見ている間に出力が変わったとき", "次に開いたときに覚えるもの"),
        }
        race = {"en": "\n#### Compare by race day\n", "ja": "\n#### 大会の日でくらべる\n"}
        phrases = {
            "en": {
                1: (
                    "With the keys only, select the chart (Tab), choose one with ← or →, and press Enter (or Space).",
                    "press a bar or a point of the chart (one day, week, month, or year, by the grouping), and the list of its activities opens just under the panel.",
                    "(where none does, it says so by the grouping, such as **No activity of the week chosen meets the conditions.**), up to 500 at a time.",
                    "A click keeps the chart selected, so that ← and → still move the cross line (the period of the list stays). Enter takes you to the heading of the list.",
                    "(their timezone is not changed)",
                    "each press switches between smallest first and largest first, and rows without a value go last either way. The date and time are ordered as they show.",
                    "\"Value of the panel: 108.1 km (activities counted: 11)\"",
                    "up to 500 at a time. For more, it says how many, and the finer grouping that lists them (**Month** for a year, **Week** for a month, **Day** for a week).",
                    "The list is not remembered and never written to a file.",
                ),
                2: (
                    "a race a full line (in the color of the text), shoes a dotted line, another mark a dashed line, and an injury a dash-dot line (long dashes and dots in turn). A span is a light band whose edges, its first and last day, are the line of its kind.",
                    "Marks never change the numbers.",
                    "They are your own words, so they never go into an output, the Support Bundle, or the text of a report on GitHub.",
                    "the marks do not show and the file is never written over",
                ),
                5: (
                    "So right after you normalize again, or right after the date changes, the numbers of the panels and those of the years or the races in **Compare years** (also by race day), of the activities of a day, week, month, or year, and of the table of **Summary…** may not agree: one of them was counted before the output changed.",
                ),
            },
            "ja": {
                1: (
                    "キーだけで開くときは、グラフを選んで（Tab キー）← → キーで区切りを選び、Enter キー（か Space キー）を押します。",
                    "グラフの区切り（まとめ方で決まる 1 つぶん。週でまとめていれば 1 週）を押すと、",
                    "（条件に合うものが無い区切りでは「この週に、条件に合うアクティビティはありません。」のように、まとめ方の言葉で出ます）。",
                    "押して開いたときは、グラフが選ばれたままなので、← → キーで十字線を動かせます（一覧の区切りは変わりません）。Enter キーで開いたときは、一覧の見出しへ移ります。",
                    "（タイムゾーンは直しません）",
                    "押すたびに小さい順と大きい順が入れ替わり、値の無い行はどちらでも最後です。日時は、見えている日付と時刻の順です。",
                    "「段の値：108.1 km（この値に数えた 11 件）」",
                    "1 つの区切りで 500 件までで、それより多いときは件数と、細かいまとめ方（年なら「月」、月なら「週」、週なら「日」）を案内します。",
                    "一覧は覚えず、ファイルにも書きません。",
                ),
                2: (
                    "大会は実線（文字の色）、靴は点線、ほかは破線、けがは一点鎖線（長い線と点のくり返し）です。期間の印は、その期間を薄く塗った所で、最初と最後の日のふちが、その種類の線です。",
                    "印は数字を変えません。",
                    "自分の言葉なので、出力・問い合わせ用ファイル・GitHub への報告の文には入りません。",
                    "印を出さず、ファイルも書き換えません",
                ),
                5: (
                    "そのため、正規化し直した直後や日付が変わった直後は、並んでいる段の数と、年でくらべる（大会の日でくらべるも）の年ごと・大会ごとの値、区切りのアクティビティの一覧、まとめの表の数が、合わないことがあります。どちらかが、出力が変わる前の数だからです。",
                ),
            },
        }
        race_phrases = {
            "en": (
                "It counts back from the Monday of the week of the race, so that every race has as many weeks.",
                "The grouping is **Week** only, also for a running total.",
                "The way to compare (by year or by race day) and the weeks of the span are remembered for the next time; the races chosen are not.",
            ),
            "ja": (
                "大会の週の月曜からさかのぼるので、どの大会も週の数がそろいます。",
                "まとめ方は「週」だけです（累積でも）。",
                "次に開いたときも、くらべ方（年か大会の日か）と範囲の週の数を覚えています。選んだ大会は覚えません。",
            ),
        }
        quoted = {
            1: ("view.group.act", "view.group.fit", "view.panel.table", "view.list.close", "view.types.label", "view.align", "view.grain.month", "view.grain.week", "view.grain.day"),
            2: ("view.marks.button", "view.marks.kind.race", "view.marks.kind.injury", "view.marks.kind.shoes", "view.marks.kind.other", "view.marks.add", "view.marks.end", "view.marks.change", "view.marks.remove", "view.marks.keep", "view.marks.show"),
        }
        race_quoted = ("view.compare.by.year", "view.compare.by.race", "view.compare.weeks", "view.compare.mode.rows_race", "view.compare.race_week", "view.marks.kind.race")
        links = {
            "en": "(#when-the-output-changes-while-you-look)",
            "ja": "(#見ている間に出力が変わったとき)",
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            messages = catalogs[language]
            mark = "**{}**" if language == "en" else "「{}」"
            pattern = r"\*\*([^*]+)\*\*|\"([^\"]+)\"" if language == "en" else r"「([^」]+)」()"
            places = [text.index(f"\n### {heading}\n") for heading in headings[language]]
            with self.subTest(language=language, part="order"):
                self.assertEqual(places, sorted(places))
                self.assertLess(places[4], text.index(race[language]))
                self.assertLess(text.index(race[language]), places[5])
            parts = {}
            for number in range(len(headings[language]) - 1):
                part = text[places[number] : places[number + 1]] if number in (1, 2, 5) else ""
                parts[number] = " ".join(part.split()) if language == "en" else re.sub(r"\n *", "", part)
            begin = text.index(race[language])
            race_part = text[begin : places[5]]
            race_reads = " ".join(race_part.split()) if language == "en" else re.sub(r"\n *", "", race_part)
            for number, expected in phrases[language].items():
                for phrase in expected:
                    with self.subTest(language=language, section=number, phrase=phrase):
                        self.assertIn(phrase, parts[number])
            for phrase in race_phrases[language]:
                with self.subTest(language=language, section="race", phrase=phrase):
                    self.assertIn(phrase, race_reads)
            for number, keys in quoted.items():
                for key in keys:
                    with self.subTest(language=language, section=number, words=key):
                        self.assertIn(mark.format(messages[key]), parts[number])
            for key in race_quoted:
                with self.subTest(language=language, section="race", words=key):
                    self.assertIn(mark.format(messages[key]), race_reads)
            # Every word quoted in the list and the marks is a word of the page,
            # or the line under the list, a date and time, and the number of
            # marks that meet as the page writes them.
            words = set(messages.values())
            words.add(messages["view.list.value"].format(value="108.1 km", n="11"))
            words.add(messages["view.list.moment"].format(date="10/2", weekday="Fri" if language == "en" else "金", time="6:30"))
            words.add(messages["view.marks.crowded"].format(n="3"))
            # The sentence of a list without an activity, as the page says it
            # of a week (stage W3 of v2.2.1).
            words.add(messages["view.list.none_met"].replace("{grain}", messages["view.grain_word.week"]))
            # The dash of the list for a value that an activity does not have.
            words.add("\u2014")
            for number in (1, 2, 5):
                for word in (bold or plain for bold, plain in re.findall(pattern, parts[number])):
                    with self.subTest(language=language, section=number, quoted=word):
                        self.assertIn(word, words)
            # What happens when the output changes is said in its own section
            # only, which the list and comparing years (and by race day) link to.
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            with self.subTest(language=language, part="said once"):
                self.assertEqual(reads.count(phrases[language][5][0]), 1)
                self.assertIn(links[language], parts[1])
                compare = text[places[4] : text.index(race[language])]
                self.assertIn(links[language], compare)
            # The scene of the 16 weeks before races leads to the race day and to
            # the marks; its marks are made up.
            with self.subTest(language=language, part="scene"):
                title = "\n### Compare the 16 weeks before races\n" if language == "en" else "\n### 大会の前の 16 週をくらべる\n"
                start = text.index(title)
                scene = text[start : text.index("\n### ", start + 1)]
                self.assertIn("(#compare-by-race-day)" if language == "en" else "(#大会の日でくらべる)", scene)
                self.assertIn("(#marks-from-220)" if language == "en" else "(#印220-から)", scene)
                self.assertIn("2026-03-15", scene)
        # The lines of the marks, as view.css draws them (the checker's M4-1).
        css = (ROOT / "src/garmin_running_data_normalizer/gui/static/view.css").read_text(encoding="utf-8")
        for rule in (
            r"\.day-mark\.race \{\s*stroke: var\(--text\);\s*\}",
            r"\.day-mark\.shoes \{[^}]*stroke-dasharray: 0\.1 4;[^}]*stroke-linecap: round;",
            r"\.day-mark\.other \{\s*stroke-dasharray: 6 3;\s*\}",
            r"\.day-mark\.injury \{\s*stroke-dasharray: 8 3 1\.5 3;\s*\}",
        ):
            with self.subTest(rule=rule):
                self.assertRegex(css, rule)

    def test_guides_give_the_races_and_the_overview_as_the_page_does(self) -> None:
        # v2.2.0 M4 (Codex's review of the diff of M4): what the guides and the
        # help say of the races that can be compared, of the week of a race,
        # and of the marks on the overview is what the page and the server do,
        # so that a change of either fails here. The races are those whose
        # longest span meets the days of the output (view_flow.mjs, whose
        # rules its own tests give); the week of a race on a Sunday inside the
        # output is a whole week; and the overview draws one short plain line
        # a mark. The scene of the races chooses the way and the span, which
        # are remembered, and what the GUI remembers names what forgetting
        # removes. The line beside race day where it is grayed and the note of
        # the table of a comparison say what the guides say (the checker's
        # M4-3).
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        weeks = [int(n) for n in re.search(r"export const COMPARE_WEEKS = \[([\d, ]+)\];", flow).group(1).split(",")]
        longest = weeks[-1]
        for line in (
            "const LONGEST_WEEKS = COMPARE_WEEKS[COMPARE_WEEKS.length - 1];",
            "return { from: isoOf(mondayOf(day) - weeks * 7), to: day };",
            ".filter(({ mark }) => mark.day >= firstDay && raceRange(mark.day, LONGEST_WEEKS).from <= lastDay)",
        ):
            with self.subTest(code=line):
                self.assertIn(line, flow)
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        start = page.index("\nfunction drawOverview(")
        overview = page[start : page.index("\nfunction ", start + 1)]
        self.assertIn('svgElement("line", { class: "overview-day-mark", x1: x, x2: x, y1: 0, y2: 10 })', overview)
        for drawn in ("appendMarkBands", "appendMarkLines", "day-band", "day-mark "):
            with self.subTest(overview=drawn):
                self.assertNotIn(drawn, overview)
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        rules = re.findall(r"([^{}]*overview-day-mark[^{}]*)\{([^}]*)\}", css)
        self.assertTrue(rules)
        for selector, body in rules:
            with self.subTest(rule=selector.strip()):
                self.assertNotIn("stroke-dasharray", body)

        # The week of a race as the server cuts it: whole for a race on a
        # Sunday inside the output, cut for a race on another day and where
        # the output ends within the week.
        def race_week(race: date, last: date) -> bool:
            monday = race - timedelta(days=race.weekday())
            data = ViewData(
                version="test",
                timezone="Asia/Tokyo",
                today=date(2030, 1, 1).toordinal(),
                rows={},
                no_date={},
                after_today={},
                first_day=date(2025, 6, 2).toordinal(),
                last_day=last.toordinal(),
            )
            first, end, cut = period_bounds(data, (monday - timedelta(weeks=16), race), "week").spans[-1]
            self.assertEqual((first, end), (monday.toordinal(), min(race, last).toordinal()))
            return cut

        sunday = date(2026, 3, 15)
        self.assertEqual(sunday.weekday(), 6)
        self.assertFalse(race_week(sunday, date(2026, 4, 30)))
        self.assertTrue(race_week(sunday - timedelta(days=1), date(2026, 4, 30)))
        self.assertTrue(race_week(sunday, date(2026, 3, 12)))
        phrases = {
            "en": (
                f"[**Race**](#marks-from-220)) whose days from the Monday {longest} weeks before the week of the race to the race day overlap the days of the output, from its first to its last (always {longest} weeks, whatever **Span** is, and whether or not those days have activities);",
                "Where the race is not on a Sunday (or the output ends within that week), it is a week cut short,",
                "The overview gives each mark only a short line at its top, whatever its kind (a span at its first day).",
                "The newest races, up to four, are in rows.",
            ),
            "ja": (
                f"大会の週の {longest} 週前の月曜から大会の日までが、出力の最初の日から最後の日までと少しでも重なるものが 2 つ以上あるときに押せます（「範囲」の週の数によらず {longest} 週で数え、記録のある日かどうかは見ません）。",
                "大会が日曜でないとき（や、出力がその週の途中で終わるとき）は、年の端の週と同じく途中の区切りです",
                "全体図には、種類にかかわらず、印ごとに上の端の短い線だけが出ます（期間の印は最初の日に）。",
                "新しい大会が 4 つまで、大会ごとに並びます。",
            ),
        }
        # The rule of the races offered, as the help and the guides say it,
        # in its four parts: from the Monday of the week some weeks before,
        # the days of the output from the first to the last, always the
        # longest span whatever the span chosen, and whether or not the days
        # have records; the note beside the title is short and leads to the
        # help by the names of the page (stage U3, the checker's answer to
        # the plan of U3).
        rules = {
            "en": (
                f"from the Monday {longest} weeks before the week of the race to the race day overlap the days of the output",
                "from its first to its last",
                f"always {longest} weeks, whatever",
                "whether or not those days have activities",
            ),
            "ja": (
                f"大会の週の {longest} 週前の月曜から大会の日までが",
                "出力の最初の日から最後の日までと少しでも重なる",
                f"週の数によらず {longest} 週で数え",
                "記録のある日かどうかは見ません",
            ),
        }
        page_quote = {"en": "“{}”", "ja": "「{}」"}
        remembered = {
            "en": ("how years are compared (the way, the month, by year or race day, and the weeks of a span)", "whether marks show"),
            "ja": ("年でくらべるのしかた（見せ方・月・くらべ方・範囲の週の数）", "「印を出す」かどうか"),
        }
        lists = {"en": ("The GUI remembers only these:", "The place of an Export,"), "ja": ("GUI が覚えるのは、次のものだけです。", "エクスポートの場所、")}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            messages = catalog(language)
            for phrase in phrases[language]:
                with self.subTest(language=language, phrase=phrase):
                    self.assertEqual(reads.count(phrase), 1)
            for rule in rules[language]:
                with self.subTest(language=language, part="help", rule=rule):
                    self.assertIn(rule, messages["view.help.race_text"])
                    self.assertEqual(reads.count(rule), 1)
                    self.assertNotIn(rule, messages["view.compare.race_needed"])
            with self.subTest(language=language, part="race needed"):
                self.assertIn(messages["help.button"], messages["view.compare.race_needed"])
                self.assertIn(page_quote[language].format(messages["view.help.race"]), messages["view.compare.race_needed"])
            # Where the weeks of a span are chosen, the help names the span in
            # the words of the page, with the weeks that the page offers; the
            # rule above names the span too, which would hide a name of it not
            # quoted here (the partial guard of U3).
            chosen = ("Choose {} to {} weeks in {}." if language == "en" else "{2}で {0}〜{1} 週を選びます。").format(
                weeks[0], longest, page_quote[language].format(messages["view.compare.weeks"])
            )
            with self.subTest(language=language, part="weeks chosen"):
                self.assertEqual(messages["view.help.race_text"].count(chosen), 1)
            # The note of the table is in the note of the guides as a whole,
            # not as words that the guides also have elsewhere ("outside the
            # output"; the partial guard of M4).
            note = messages["view.compare.partial_note"]
            if language == "en":
                parts = re.fullmatch(r"\* (.+); — (.+)\.", note)
                self.assertIsNotNone(parts)
                note = "* marks one {}, and — one {}.".format(*parts.groups())
            with self.subTest(language=language, part="note"):
                self.assertIn(note, reads)
            # The overview is never said to draw the forms of the kinds.
            with self.subTest(language=language, part="overview"):
                self.assertNotIn("on every panel and on the overview" if language == "en" else "全部の段と全体図に", reads)
            # The scene chooses the way to show and the span, in the words of
            # the page, as they are remembered from before.
            words = [messages[key] for key in ("view.compare.mode.rows_race", "view.compare.show")]
            words += [messages["view.compare.weeks_option"].format(n=16), messages["view.compare.weeks"]]
            choose = (
                "Choose **{}** in **{}**, and **{}** in **{}**" if language == "en" else "「{1}」で「{0}」を、「{3}」で「{2}」を選びます"
            ).format(*words)
            with self.subTest(language=language, part="scene"):
                self.assertEqual(reads.count(choose), 1)
            # What the GUI remembers names what forgetting removes.
            begin = reads.index(lists[language][0])
            remembers = reads[begin : reads.index(lists[language][1], begin)]
            for phrase in remembered[language]:
                with self.subTest(language=language, remembered=phrase):
                    self.assertIn(phrase, remembers)
                    self.assertIn(phrase, messages["forget.text_also"])

    def test_guides_give_the_calendar_as_the_page_does(self) -> None:
        # v2.2.0 N2: the calendar of comparing years (stage N1) is the fourth
        # way of **Show as**, with a heading of its own in the section of
        # comparing years, before comparing by race day (the checker's review
        # of the plan of N2), which the line of the ways and the keyboard link
        # to. What the guides say of it is what the page does, so that a change
        # of either fails here: the ways of the page in their order, the keys
        # of a strip (a week and a day, unlike the one period of the cross
        # line), the steps of its colors at most, the outline of a day without
        # a recorded activity, the same day of a common year for 29 February,
        # and the estimates that it is not for, the items of the kind obs, in
        # the words of their reason on the page (the checker's answer 5). After
        # the review of the diff by Codex: a day without a record is never
        # called a rest, the reason is for those items only, Home and End stop
        # at the output, and race day has the ways of the years but the
        # calendar.
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        modes = [mode.strip().strip('"') for mode in re.search(r"export const COMPARE_MODES = \[([^\]]*)\];", flow).group(1).split(",")]
        self.assertEqual(modes[-1], "calendar")
        keys = re.search(r"const CALENDAR_KEYS = \{([^}]*)\};", flow).group(1)
        self.assertEqual({key: int(n) for key, n in re.findall(r"(\w+): (-?\d+)", keys)}, {"ArrowLeft": -7, "ArrowRight": 7, "ArrowUp": -1, "ArrowDown": 1})
        self.assertIn("export const CALENDAR_STEPS = 6;", flow)
        for line in (
            'return typeof item?.kind === "string" && item.kind !== "obs";',
            'return isTotal(item ?? {}) && value === 0 && count === 0 ? "zero" : "value";',
            "const day = slotDay(slot, year) ?? `${year}-02-28`;",
            'if (key === "Home") {\n    next = span.from;\n  } else if (key === "End") {\n    next = span.to;',
        ):
            with self.subTest(code=line):
                self.assertIn(line, flow)
        self.assertEqual([item.key for item in ITEMS if item.kind == OBSERVED], ["vo2", "p5k", "p10k", "phalf", "pfull", "tr", "acute", "chronic", "acwr"])
        heading = {"en": "Compare years (from 2.2.0)", "ja": "年でくらべる（2.2.0 から）"}
        own = {"en": "Calendar", "ja": "カレンダー"}
        race = {"en": "Compare by race day", "ja": "大会の日でくらべる"}
        link = {"en": "[Calendar](#calendar)", "ja": "[カレンダー](#カレンダー)"}
        estimates = {"en": r"Of the Garmin estimates, (.+?) can have several records a day", "ja": r"Garmin の推定値のうち (.+?)は、1 日に記録がいくつもある"}
        example = {"en": "(10–20: 10 or more, under 20)", "ja": "（10–20 は 10 以上 20 未満）"}
        right = {"en": "A color further right in the legend only means a higher value.", "ja": "凡例の右の色ほど値が大きいことだけを表します。"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            messages = catalog(language)
            mark = "**{}**" if language == "en" else "「{}」"
            words = {key.rsplit(".", 1)[-1]: mark.format(messages[key]) for key in ("view.compare.show", "view.grain.day", "view.compare.month", "view.compare.calendar_about", "view.panel.table", "view.compare.table_calendar")}
            rows, calendar = (mark.format(messages[f"view.compare.mode.{mode}"]) for mode in ("rows", "calendar"))
            start = text.index(f"\n### {heading[language]}\n")
            part = text[start : text.index("\n### ", start + 1)]
            with self.subTest(language=language, part="order"):
                self.assertLess(part.index(f"\n#### {own[language]}\n"), part.index(f"\n#### {race[language]}\n"))
            begin = part.index(f"\n#### {own[language]}\n")
            own_part = part[begin : part.index(f"\n#### {race[language]}\n")]
            own_reads = " ".join(own_part.split()) if language == "en" else re.sub(r"\n *", "", own_part)
            # The line of the ways names the ways of the page in their order,
            # and leads to the calendar.
            ways = re.sub(r"\n *", " " if language == "en" else "", part)
            ways = ways[ways.index(words["show"] + (": " if language == "en" else "：")) :]
            ways = ways[: ways.index("At first," if language == "en" else "初めは")]
            places = [ways.index(mark.format(messages[f"view.compare.mode.{mode}"])) for mode in modes]
            with self.subTest(language=language, part="ways"):
                self.assertEqual(places, sorted(places))
                self.assertIn(link[language], ways)
            names = re.search(estimates[language], messages["view.compare.calendar_only"]).group(1)
            zero = messages["view.compare.calendar_zero_key"]
            for words_of_the_page in (example, right):
                with self.subTest(language=language, note=words_of_the_page[language]):
                    self.assertIn(words_of_the_page[language], messages["view.compare.calendar_note"])
            if language == "en":
                phrases = (
                    f"To compare amounts, use {rows}; to see the days in their order (when you ran, and where days without a recorded activity ran on), use {calendar}.",
                    f"{calendar} in {words['show']} makes a strip of each year: the weeks across (from the week of 1 January) and the days of the week down, Monday to Sunday,",
                    f"It goes by {words['day']} only, and the choice of the {words['month']} is not used and grayed (the month chosen stays, and comes back with the other ways).",
                    f"It cannot be used while comparing by race day. Nor can it be used for an item that can have several records a day ({names}); for such an item, {words['calendar_about']} says why.",
                    "The legend above the strips gives up to six steps.",
                    f"Each holds its left value and not its right one {example[language]}. {right[language]}",
                    f"For a total or a count, a {zero[0].lower()}{zero[1:]} is an outline; a day without a value and a day outside the output are not drawn.",
                    "A recorded 0 (activities of 0 km) takes the first step.",
                    "The day chosen is the same day of the year in every strip where it can be: 28 February for 29 February in a common year, and, for a day outside the output in that year, the nearest day of the output in that year.",
                    f"use ← and → (a week), ↑ and ↓ (a day), and Home and End (the first and last day of the year in the output). The arrows move otherwise than with {rows}, where ← and → move one period.",
                    f"{words['table']} gives the days in rows and the years in columns; {words['table_calendar']} goes back.",
                    "In forced colors (a contrast theme of Windows, for example) the steps can be hard to tell apart; the values are at the left of a strip and in the table.",
                )
                keyboard = "In a calendar (from 2.2.0), Tab goes from strip to strip, and ← → (a week), ↑ ↓ (a day), and Home and End (the first and last day of the year in the output) read out the date, the day of the week, and the value; so does a strip that the focus comes to ([Calendar](#calendar))."
                race_ways = f"The ways to show are those of the years without {calendar}; {rows} becomes {mark.format(messages['view.compare.mode.rows_race'])}, which is the way at first."
                shades = ("dark", "light", "pale", "deep")
                rest = re.search(r"\brest\b", own_reads)
            else:
                phrases = (
                    f"量をくらべるときは{rows}、日の並び（いつ走ったか・記録の無い日が続いた所）を見るときは{calendar}です。",
                    f"{words['show']}の{calendar}で、1 年を 1 本の横長の帯（年の帯）にします。横に週（1 月 1 日の週から）、縦に曜日（月〜日）で、",
                    f"まとめ方は{words['day']}だけです。月の選び（{words['month']}）は使わず、灰色になります（選んでいた月は覚えていて、ほかの見せ方に戻すとその月で出ます）。",
                    f"大会の日でくらべる間は使えません。1 日に記録がいくつもある項目（{names}）でも使えず、そのわけは{words['calendar_about']}で開きます。",
                    "色は 6 つの段階までで、年の帯の上の凡例に、色の段階が出ます。",
                    f"色の段階は左の値を含み、右の値を含みません{example[language]}。{right[language]}",
                    f"合計や回数の項目で{zero}は枠だけ、値の無い日と出力の外の日は何も描きません。",
                    "記録された 0（距離 0 km のアクティビティの日など）は、凡例のいちばん左の色です。",
                    "選んだ日は、どの年の帯でも、できるだけ同じ月日です。平年では 2 月 29 日の代わりに 2 月 28 日、その年の出力の外の日なら、その年の出力の中でいちばん近い日です。",
                    f"← → キー（1 週）、↑ ↓ キー（1 日）、Home と End（その年の出力の最初と最後の日）で日を選びます。{rows}の ← →（1 区切り）とは動き方が違います。",
                    f"{words['table']}で日ごとの表（月日 × 年）になり、{words['table_calendar']}で戻ります。",
                    "強制カラーの画面（Windows のコントラスト テーマなど）では色の段階が見分けにくいことがあるので、値は年の帯の左と表で読めます。",
                )
                keyboard = "カレンダー（2.2.0 から）では、年の帯ごとに Tab キーで移り、← → キーで 1 週、↑ ↓ キーで 1 日、Home と End でその年の出力の最初と最後の日へ動かすと、日付・曜日・値を読み上げます。年の帯に移ったときも読み上げます（[カレンダー](#カレンダー)）。"
                race_ways = f"見せ方は、年の見せ方から{calendar}を除いた {len(modes) - 1} つで、{rows}は{mark.format(messages['view.compare.mode.rows_race'])}になります（初めは{mark.format(messages['view.compare.mode.rows_race'])}）。"
                shades = ("濃い", "淡い", "明るい", "暗い", "薄い")
                rest = re.search("休み", own_reads)
            for phrase in phrases:
                with self.subTest(language=language, phrase=phrase):
                    self.assertEqual(own_reads.count(phrase), 1)
            with self.subTest(language=language, part="keyboard"):
                self.assertEqual(reads.count(keyboard), 1)
            with self.subTest(language=language, part="race day"):
                self.assertEqual(reads.count(race_ways), 1)
            # A day without a recorded activity is not a rest: the watch may
            # not have been worn (view.note.zero; Codex's review of the diff).
            with self.subTest(language=language, part="rest"):
                self.assertIsNone(rest)
            # The steps go the other way in the dark appearance, so the guides
            # never name them by their shade (the checker's N0-1).
            for shade in shades:
                with self.subTest(language=language, shade=shade):
                    self.assertNotIn(shade, own_reads.lower())

    def test_guides_give_the_other_views_as_the_page_does(self) -> None:
        # v2.2.0 OP2: the other views of stages O1 and P1 have a section of
        # their own after comparing years, with a heading for each view under
        # it, as the calendar and the race day are under comparing years (the
        # checker's answer 2 of the plan of OP2). What the guides say of them
        # is what the page and the server do, so that a change of either fails
        # here: the first pair and the first item, the limit of the points, the
        # items of the views (those of one activity but the count, in the
        # groups of the shelf), the limit of the ranges and the steps of a
        # wider width, the width of each item as a table in the units of the
        # page (the checker's OP2-1 and answer 4), the way the pace goes in each
        # view (OP2-2), a value counted before it is rounded (the promise of
        # P1: 10,999.6 m, shown as 11.0 km, is in the range of 10 to 11 km), the
        # reading of a range, the keys, what is remembered, and the scene of
        # the distances of the last year (answer 3), which chooses the distance
        # and keeps the running types, as a distribution opens with the item
        # and the types chosen last (Codex's review of the diff). Every word
        # quoted is a word of the page or a value as the page writes it.
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        self.assertEqual(MAX_POINTS, 5000)
        self.assertIn(f"export const MAX_POINTS = {MAX_POINTS};", flow)
        self.assertIn('export const PLOT_FIRST = Object.freeze({ x: "pace", y: "hr" });', flow)
        self.assertIn('export const SPREAD_FIRST = "dist";', flow)
        self.assertEqual(MAX_RANGES, 200)
        self.assertEqual(list(itertools.islice(series_module._wider(), 4)), [1, 2, 5, 10])
        # The items in the order of the page (ITEMS), which the table
        # follows; SPREAD_RANGES has a width for each, in any order (Codex's
        # review of the diff of OP2).
        keys = [item.key for item in ITEMS if point_item(item.key)]
        self.assertEqual(set(keys), set(SPREAD_RANGES))
        self.assertEqual(len(keys), 15)
        self.assertEqual({ITEMS_BY_KEY[key].group for key in keys}, {"act", "fit"})
        self.assertEqual([item.key for item in ITEMS if item.group in ("act", "fit") and not point_item(item.key)], ["count"])
        self.assertEqual({item.group for item in ITEMS}, {"act", "fit", "body", "est"})
        block = re.search(r"export const ITEM_FORMATS = \{\n(.*?)\n\};", flow, re.S).group(1)
        formats = {
            key: (unit, Fraction(factor.replace(" ", "")), int(digits))
            for key, unit, factor, digits in re.findall(r'^  (\w+): \{ unit: "(\w+)", factor: ([0-9./ ]+), digits: (\d+) \},$', block, re.M)
        }
        # The example of the guides, as the server counts it and the page
        # writes it.
        answer = activity_spread(view_data([act("2026-03-01", distance_m=10999.6)]), "dist")
        self.assertEqual((answer["first"], answer["counts"]), (10, [1]))
        unit, factor, digits = formats["dist"]
        self.assertEqual(unit, "km")
        self.assertEqual(f"{float(Fraction('10999.6') * factor):.{digits}f}", "11.0")

        def width_words(key: str, language: str, messages: dict[str, str]) -> str:
            # The width of the ranges of an item, as the page writes a width:
            # the scale and the width of the server, in the unit of the page.
            scale, width = SPREAD_RANGES[key]
            unit, factor, _digits = formats[key]
            shown = Fraction(width, scale) * factor
            number = format(float(shown), "g")
            if unit in ("hm", "pace"):
                self.assertEqual(shown.denominator, 1)
                clock = f"{int(shown) // 60}:{int(shown) % 60:02d}"
                if unit == "hm":
                    return f"{int(shown)} minutes ({clock})" if language == "en" else f"{int(shown)} 分（{clock}）"
                clock = messages["view.value.pace"].format(value=clock)
                return f"{int(shown)} seconds ({clock})" if language == "en" else f"{int(shown)} 秒（{clock}）"
            if unit == "raw":
                # The words of the page in the parentheses of the guide (stage
                # W3 of v2.2.1): "Same unit as Garmin (not named)" is written
                # "(same unit as Garmin, not named)", without parentheses in
                # parentheses.
                raw = re.fullmatch(r"(.+) \((.+)\)", messages["view.unit.raw"]) if language == "en" else re.fullmatch(r"(.+)（(.+)）", messages["view.unit.raw"])
                self.assertIsNotNone(raw)
                if language == "en":
                    return f"{number} ({raw[1][0].lower()}{raw[1][1:]}, {raw[2]})"
                return f"{number}（{raw[1]}、{raw[2]}）"
            return messages[f"view.value.{'pct' if unit == 'pct_fit' else unit}"].format(value=number)

        heading = {"en": "Other views (from 2.2.0)", "ja": "ほかの見方（2.2.0 から）"}
        before = {"en": "Compare years (from 2.2.0)", "ja": "年でくらべる（2.2.0 から）"}
        # Q2: the summary follows the other views.
        after = {"en": "Summary (from 2.2.0)", "ja": "まとめ（2.2.0 から）"}
        # S2: the view by shoes has its heading after the distribution, and is
        # read apart from it (its words in test_guides_give_the_shoes_as_the_page_does).
        own = {"en": ("Plot two items", "Distribution", "By shoes"), "ja": ("点で並べる", "分かれ方", "靴ごと")}
        heads = {"en": ("Item", "Width of a range"), "ja": ("項目", "区間の幅")}
        scene = {"en": "See how often you ran each distance in the last year", "ja": "直近 1 年に、どの距離を何回走ったかを見る"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            messages = catalog(language)
            mark = "**{}**" if language == "en" else "「{}」"
            name = {key: messages[f"view.item.{key}"] for key in ("pace", "hr", "dist")}
            places = [text.index(f"\n### {title}\n") for title in (before[language], heading[language], after[language])]
            with self.subTest(language=language, part="order"):
                self.assertEqual(places, sorted(places))
            part = text[places[1] : places[2]]
            plot_at, spread_at, shoes_at = (part.index(f"\n#### {title}\n") for title in own[language])
            with self.subTest(language=language, part="headings"):
                self.assertLess(plot_at, spread_at)
                self.assertLess(spread_at, shoes_at)
            parts = {
                "menu": part[:plot_at],
                "plot": part[plot_at:spread_at],
                "spread": part[spread_at:shoes_at],
                "shoes": part[shoes_at:],
            }
            joined = {key: " ".join(value.split()) if language == "en" else re.sub(r"\n *", "", value) for key, value in parts.items()}
            # The widths, as a table of two columns in the order of the page.
            rows = re.findall(r"^\| (.+?) \| (.+?) \|$", parts["spread"], re.M)
            with self.subTest(language=language, part="widths"):
                self.assertEqual(rows[:2], [heads[language], ("---", "---")])
                self.assertEqual(rows[2:], [(messages[f"view.item.{key}"], width_words(key, language, messages)) for key in keys])
            reading = messages["view.spread.reading"].format(**{"from": messages["view.value.km"].format(value="10"), "to": messages["view.value.km"].format(value="11"), "n": messages["view.value.count"].format(value="42")})
            shown_value = messages["view.value.km"].format(value="11.0")
            range_words = messages["view.spread.range"].format(**{"from": "10", "to": messages["view.value.km"].format(value="11")})
            if language == "en":
                phrases = {
                    "menu": (
                        f"{mark.format(messages['view.other.button'])} above the panels shows {mark.format(messages['view.other.plot'])}, {mark.format(messages['view.other.spread'])}, or {mark.format(messages['view.other.shoes'])} in the place of the panels.",
                        "Enter, Space, or ↓ opens its menu on the first item; ↑, ↓, Home, and End move in it, and Esc closes it, back to its button. Tab or a click elsewhere closes it too.",
                        f"While one shows, the {mark.format(messages['view.shelf.heading'])}, {mark.format(messages['view.layouts.heading'])}, and {mark.format(messages['view.grain.label'])} are not used; a line under the filters says so.",
                        "a period, activity types, or conditions changed here stay for the panels when you go back.",
                        f"{mark.format(messages['view.panel.unbig'])} goes back, the focus (where the keys act) on {mark.format(messages['view.other.button'])}. To go from one of these views to another, go back to the panels first with {mark.format(messages['view.panel.unbig'])}, and then choose it in {mark.format(messages['view.other.button'])}. While comparing years, {mark.format(messages['view.other.button'])} is not shown.",
                    ),
                    "plot": (
                        f"Each activity is one point, one item across and another up, chosen in the lists of the title, {mark.format(messages['view.plot.x'])} and {mark.format(messages['view.plot.y'])}; at first the {name['pace'].lower()} across and the {name['hr'].lower()} up, and later the two chosen last. An item chosen in one list cannot be chosen in the other, and the list says why.",
                        "A line under the title gives the numbers only: the points, the activities of the period, those with both values, and those without (with conditions, all of them of the activities that meet them).",
                        "Press a point, or select the chart and use ← and → (one point in the order of the dates and times) and Home and End (the first and the last): its date and time with the year, its type, its two values,",
                        f"{mark.format(messages['view.panel.table'])} gives one row an activity (the date and time, the type, and the two values), ordered by the buttons of its heads (newest first at first); {mark.format(messages['view.panel.chart'])} goes back.",
                        f"The items are the {len(keys)} of {mark.format(messages['view.group.act'])} (without {mark.format(messages['view.item.count'])}) and {mark.format(messages['view.group.fit'])}; those of {mark.format(messages['view.group.body'])} and {mark.format(messages['view.group.est'])} cannot be chosen.",
                        f"Only the newest {MAX_POINTS:,} are plotted; where there are more, a line says so (a shorter period shows them all).",
                        f"{mark.format(messages['view.plot.caveat'])} is always under the points.",
                        "Each scale goes over the values of its item, not from 0. A smaller value of the average pace is faster: further down as the item up, and further left as the item across.",
                        "how many more have the same values, if any, are at the top right, and are read out too.",
                        "Where an item changes, the points before are not shown until the new ones come; where the period, the activity types, or the conditions change, the points stay, dimmed, until then.",
                    ),
                    "spread": (
                        f"How many activities fall in each range of one item, as bars. Choose the item in the list of the title: the {name['dist'].lower()} at first, and later the item chosen last, among the {len(keys)} items of {mark.format(messages['view.other.plot'])}.",
                        "A range of no activity has no bar (0 in the table).",
                        "A line under the title gives the numbers only: the activities counted, those of the period, and those without a value.",
                        "Press a bar, or select the chart and use ← and → (one range at a time, those of no activity among them) and Home and End (the first and the last):",
                        f"{mark.format(messages['view.panel.table'])} gives the number of activities of each range; {mark.format(messages['view.panel.chart'])} goes back.",
                        f"A range holds its left value and not its right one ({range_words}: 10 km or more, under 11 km).",
                        f"The ranges count the values before they are rounded. The list and the points show rounded values, so an activity near the end of a range can look as if it were in the next one: 10,999.6 m shows as {shown_value}, and is in the range {range_words}.",
                        f"Where there would be more than {MAX_RANGES} ranges from the first with a value to the last (those of no activity too), each range is the first of 2, 5, 10, ... times as wide that is enough, and a line says so.",
                        f"For the average pace, {mark.format(messages['view.spread.faster_left'])} is there too.",
                        f"the range and its activities are at the top right, as {mark.format(reading)}, and are read out too.",
                        "An end of a range (its left or its right value) that is too large to write, as a record of an error can make it, is a dash (—).",
                    ),
                }
                keyboard = "In **Other views** (from 2.2.0), Enter, Space, or ↓ opens the menu on its first item, ↑, ↓, Home, and End move in it, and Esc closes it, back to its button. In **Plot two items**, select the chart: ← and → (one point in the order of the dates and times) and Home and End choose a point and read out its date and time, its type, and its two values (and how many more have the same values). In **Distribution**, ← and → (those of no activity among them) and Home and End choose a range and read out the range and its activities. In **By shoes**, select a panel: ← and → (a month) and Home and End choose a month and read out the name of the shoes and the distance of the month. Where **By shoes** cannot be chosen, ↑ and ↓ stop on it and its reason is read out too; Enter and Space do nothing. Tab goes into the box of each table of **Show as a table**, which the arrow keys scroll ([Other views](#other-views-from-220))."
                remembered = ("whether **Show marks** is on, the two items plotted and the item of a distribution of [Other views](#other-views-from-220), and the [conditions](#conditions-from-220).", "whether marks show, the two items plotted and the item of a distribution, and the conditions (the words of the name, the distance, and the duration).")
                forgets = "the two items plotted and the item of a distribution"
                steps = (f"2. Press {mark.format(messages['view.period.years1'])} in {mark.format(messages['view.period.label'])} above. Keep {mark.format(messages['view.types.label'])} to running types", f"3. Choose {mark.format(messages['view.other.spread'])} in {mark.format(messages['view.other.button'])} above the panels, and {mark.format(name['dist'])} in the list of its title")
            else:
                phrases = {
                    "menu": (
                        f"段の上の{mark.format(messages['view.other.button'])}で、段の代わりに{mark.format(messages['view.other.plot'])}{mark.format(messages['view.other.spread'])}か{mark.format(messages['view.other.shoes'])}を出します。",
                        "メニューは、Enter・Space・↓ キーで開いて最初の項目に移り、↑ ↓・Home・End キーで動き、Esc キーでボタンに戻って閉じます。Tab キーか、ほかの所を押しても閉じます。",
                        f"出ている間は{mark.format(messages['view.shelf.heading'])}{mark.format(messages['view.layouts.heading'])}{mark.format(messages['view.grain.label'])}を使いません。フィルターの下に、そのことが 1 行で出ます。",
                        "ここで変えた期間と数える種目と条件は、段に戻ってもそのまま段に効きます。",
                        f"戻るときは{mark.format(messages['view.panel.unbig'])}を押します。フォーカス（キーで操作する先）は{mark.format(messages['view.other.button'])}に戻ります。ほかの見方どうしを行き来するときは、{mark.format(messages['view.panel.unbig'])}でいったん段に戻ってから、{mark.format(messages['view.other.button'])}で選びます。年でくらべる間は、{mark.format(messages['view.other.button'])}は出ません。",
                    ),
                    "plot": (
                        f"1 回のアクティビティを 1 つの点にして、2 つの項目を横と縦に並べます。項目は、題の中の{mark.format(messages['view.plot.x'])}と{mark.format(messages['view.plot.y'])}の一覧で選びます。初めは{name['pace']}（横）と{name['hr']}（縦）で、次に開いたときは前に選んだ 2 つです。もう一方で選んでいる項目は選べず、一覧にそのわけが出ます。",
                        "題の下に、数だけの行が出ます（点の数、この期間の回、両方の値がある回、値の無い回。条件があるときは、どれも条件に合う回で数えます）。",
                        "点を押すか、グラフを選んで ← → キー（日時の順に 1 つずつ）、Home と End（最初と最後）で点を選ぶと、右上に日時（年つき）・種目・2 つの値と、",
                        f"{mark.format(messages['view.panel.table'])}で 1 回ごとの表（日時・種目・2 つの値）になり、列の見出しのボタンで並べ替えられます（初めは新しい順）。{mark.format(messages['view.panel.chart'])}で戻ります。",
                        f"選べるのは{mark.format(messages['view.group.act'])}（{mark.format(messages['view.item.count'])}を除く）と{mark.format(messages['view.group.fit'])}の {len(keys)} の項目で、{mark.format(messages['view.group.body'])}と{mark.format(messages['view.group.est'])}の項目は選べません。",
                        f"点にするのは新しい {MAX_POINTS:,} 回までで、それより多いときは、そのことが 1 文で出ます（期間をしぼると、全部を出せます）。",
                        f"点の下には、いつも{mark.format(messages['view.plot.caveat'])}が出ます。",
                        "目盛りは、それぞれの項目の値に合わせて決まります（0 からではありません）。平均ペースは、値が小さいほど速い回です。縦の項目なら下ほど、横の項目なら左ほど速くなります。",
                        "同じ値の回がほかにあればその数が出ます。読み上げでも聞けます。",
                        "項目を替えると、新しい点が届くまで、前の点は出しません。期間や数える種目・条件を変えたときは、届くまで今の点を薄く残します。",
                    ),
                    "spread": (
                        f"1 つの項目の 1 回ごとの値が、どの区間に何回あるかを、棒で見ます。項目は題の中の一覧で選びます。初めは{name['dist']}で、次に開いたときは前に選んだ項目です。選べる項目は、点で並べるのと同じ {len(keys)} です。",
                        "回数の無い区間は、棒を描きません（表では 0）。",
                        "題の下に、数だけの行（数えた回・この期間の回・値の無い回）が出ます。",
                        "棒を押すか、グラフを選んで ← → キー（1 つずつ。回数の無い区間も通ります）、Home と End（最初と最後）で区間を選ぶと、",
                        f"{mark.format(messages['view.panel.table'])}で区間ごとの回数の表になり、{mark.format(messages['view.panel.chart'])}で戻ります。",
                        f"区間は左の値を含み、右の値を含みません（{range_words} は 10 km 以上 11 km 未満）。",
                        f"区間には、丸める前の値で入れます。一覧や点の値は丸めて出すので、区間の境目のすぐ近くの回は、表示と区間が違って見えることがあります（10,999.6 m の回は{mark.format(shown_value)}と出て、{range_words} に入ります）。",
                        f"値のある最初の区間から最後の区間までの数（回数の無い区間も入れて）が {MAX_RANGES} を超えるときは、幅を 2 倍・5 倍・10 倍…のうち足りるいちばん小さい幅に広げ、そのことを 1 行で言います。",
                        f"平均ペースのときは{mark.format(messages['view.spread.faster_left'])}も出ます。",
                        f"右上に{mark.format(reading)}のように、区間と回数が出ます。読み上げでも聞けます。",
                        "区間の端（左の値か右の値）が、記録の誤りのように書き表せないほど大きいときは、その端を「—」で書きます。",
                    ),
                }
                keyboard = "ほかの見方（2.2.0 から）では、メニューを Enter・Space・↓ キーで開くと最初の項目に移り、↑ ↓・Home・End キーで動き、Esc キーでボタンに戻って閉じます。点で並べるでは、グラフを選んで ← → キー（日時の順に 1 つずつ）と Home・End で点を選ぶと、日時・種目・2 つの値（同じ値の回があればその数も）を読み上げます。分かれ方では、← → キー（回数の無い区間も通ります）と Home・End で区間を選ぶと、区間と回数を読み上げます。靴ごとでは、段を選んで ← → キー（1 か月ずつ）と Home・End で月を選ぶと、靴の名前とその月の距離を読み上げます。メニューの「靴ごと」が選べないときは、↑ ↓ キーでそこに止まり、わけも読み上げます。Enter・Space キーでは何もしません。「表で見る」の 2 つの表は、Tab キーで表の枠に入ると、矢印キーで送れます（[ほかの見方](#ほかの見方220-から)）。"
                remembered = ("「印を出す」かどうか、[ほかの見方](#ほかの見方220-から)の点で並べる 2 つの項目と分かれ方の項目と、[条件](#条件で絞る220-から)も覚えます。", "「印を出す」かどうか、点で並べる 2 つの項目と分かれ方の項目、条件（名前の言葉・距離・時間）も。")
                forgets = "点で並べる 2 つの項目と分かれ方の項目"
                steps = (f"2. 上の{mark.format(messages['view.period.label'])}で{mark.format(messages['view.period.years1'])}を押します。{mark.format(messages['view.types.label'])}は、ランニングの種目だけにします", f"3. 段の上の{mark.format(messages['view.other.button'])}で{mark.format(messages['view.other.spread'])}を選び、題の一覧で{mark.format(name['dist'])}を選びます")
            for key, expected in phrases.items():
                for phrase in expected:
                    with self.subTest(language=language, part=key, phrase=phrase):
                        self.assertEqual(joined[key].count(phrase), 1)
            with self.subTest(language=language, part="keyboard"):
                self.assertEqual(reads.count(keyboard), 1)
            for phrase in remembered:
                with self.subTest(language=language, remembered=phrase):
                    self.assertEqual(reads.count(phrase), 1)
            with self.subTest(language=language, part="forget"):
                self.assertIn(forgets, messages["forget.text_also"])
            # The scene of the distances of the last year leads to the
            # distribution, in the words of the page.
            start = text.index(f"\n### {scene[language]}\n")
            scene_text = text[start : text.index("\n### ", start + 1)]
            scene_reads = " ".join(scene_text.split()) if language == "en" else re.sub(r"\n *", "", scene_text)
            with self.subTest(language=language, part="scene"):
                for step in steps:
                    self.assertIn(step, scene_reads)
                self.assertIn("(#distribution)" if language == "en" else "(#分かれ方)", scene_text)
            # Every word quoted is a word of the page, or the reading of a range
            # and a value as the page writes them, or the dash of an end.
            words = set(messages.values()) | {reading, shown_value, "—"}
            pattern = r"\*\*([^*]+)\*\*|\"([^\"]+)\"" if language == "en" else r"「([^」]+)」()"
            for key, value in joined.items():
                for word in (bold or plain for bold, plain in re.findall(pattern, value)):
                    with self.subTest(language=language, part=key, quoted=word):
                        self.assertIn(word, words)
            # The width of the distance in the help is that of the table.
            with self.subTest(language=language, part="help"):
                self.assertIn(width_words("dist", language, messages), messages["view.help.other_spread"])

    def test_guides_give_the_summary_as_the_page_does(self) -> None:
        # v2.2.0 Q2: the summary of the panels of stage Q1 has a section of its
        # own after the other views, before the readings (the checker's answer
        # 1 of the plan of Q2). What the guides say of it is what the page and
        # the server do, so that a change of either fails here: the way each
        # item is counted, as a table tied to the kinds of the items and to the
        # words of the page (the checker's Q2-1), the headings after ‹ and ›
        # (Q2-2), 0 and no value (Q2-3), the types counted (Q2-4), a year of the
        # calendar before (Q2-5), the difference, the keys, and the tenth scene
        # (answer 3). Every word quoted is a word of the page or a heading as
        # the page writes it.
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        # The words of a kind as the summary counts it: those of kindKey with a
        # grouping that is not a day, which the summary never asks for.
        block = re.search(r"const KIND_KEYS = \{\n(.*?)\n\};", flow, re.S).group(1)
        kind_keys = dict(re.findall(r'^  (\w+): "(view\.kind\.\w+)",$', block, re.M))
        self.assertEqual(set(kind_keys), {"sum", "count", "pace", "tw", "max"})
        self.assertIn('return grain === "day" ? "view.kind.day" : item.per_day ? "view.kind.day_mean_per_day" : "view.kind.day_mean";', flow)
        self.assertIn('return grain === "day" ? "view.kind.obs_points" : "view.kind.obs_mean";', flow)
        self.assertIn("{ ...seriesPayload(state.items, periodRequest(state.period, state.range), RANGE_GRAIN), previous: true }", page)
        # Codex's review of the diff of Q2: a total is 0 between the first and
        # the last activity of the types counted; the heading of the days
        # before counts the days of the range; Escape closes the window where
        # the focus is in it.
        server = (ROOT / "src/garmin_running_data_normalizer/view/series.py").read_text(encoding="utf-8")
        self.assertIn("        rows = _activity_rows(data, types, conditions)\n        lines = [_activity_line(item, rows, periods, left_out)]", server)
        self.assertIn("    # The first and the last activity of the types counted, in the output.\n    first = rows[0].day if rows else None", server)
        self.assertIn("    const days = daysBetween(period.from, period.to) + 1;", flow)
        self.assertIn('  ui.recapPop.addEventListener("keydown", (event) => {\n    if (event.key === "Escape") {', page)
        self.assertEqual({item.kind for item in ITEMS}, {"sum", "count", "pace", "tw", "max", "day", "obs"})

        def kind_word(item: object) -> str:
            kind = getattr(item, "kind")
            if kind in kind_keys:
                return kind_keys[kind]
            if kind == "day":
                return "view.kind.day_mean_per_day" if getattr(item, "per_day") else "view.kind.day_mean"
            return "view.kind.obs_mean"

        groups: dict[str, list[str]] = {}
        for item in ITEMS:
            groups.setdefault(kind_word(item), []).append(item.key)
        # ‹ and › make the period a range (the checker's Q2-2).
        shift = re.search(r"function shiftPeriod\(direction\) \{(.*?)\n\}", page, re.S).group(1)
        self.assertIn('state.period = "custom";', shift)
        # The year before a year with 29 February is a year of the calendar, a
        # day shorter than the days that ‹ moves by (the checker's Q1-2 and
        # Q2-5).
        data = view_data([act("2023-01-10", distance_m=1000), act("2024-02-29", distance_m=1000)])
        now, before = chosen_span(data, "1y"), previous_span(data, "1y")
        self.assertEqual((now[1] - now[0] + 1, before[1] - before[0] + 1), (366, 365))
        self.assertEqual(date.fromordinal(before[1]) + timedelta(days=1), date.fromordinal(now[0]))
        heading = {"en": "Summary (from 2.2.0)", "ja": "まとめ（2.2.0 から）"}
        before_heading = {"en": "Other views (from 2.2.0)", "ja": "ほかの見方（2.2.0 から）"}
        after = {"en": "When the output changes while you look", "ja": "見ている間に出力が変わったとき"}
        heads = {"en": ("How it is counted", "Items"), "ja": ("数え方", "項目")}
        joiner = {"en": "; ", "ja": "・"}
        scene = {"en": "Compare the last year with the year before", "ja": "この 1 年と前の 1 年をくらべる"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            messages = catalog(language)
            mark = "**{}**" if language == "en" else "「{}」"
            days = {n: messages["view.recap.before.days"].format(n=n) for n in (31, 365)}
            places = [text.index(f"\n### {title}\n") for title in (before_heading[language], heading[language], after[language])]
            with self.subTest(language=language, part="order"):
                self.assertEqual(places, sorted(places))
            # v2.2.0 R3: saving as an image comes between, so that the summary
            # is read up to the next heading, as before R3 (Codex's review of
            # the plan of R3).
            part = text[places[1] : text.index("\n### ", places[1] + 1)]
            joined = " ".join(part.split()) if language == "en" else re.sub(r"\n *", "", part)
            # The way each item is counted, as a table of two columns: the
            # words of the page for its kind, and its items in the order of
            # the page.
            rows = re.findall(r"^\| (.+?) \| (.+?) \|$", part, re.M)
            with self.subTest(language=language, part="kinds"):
                self.assertEqual(rows[:2], [heads[language], ("---", "---")])
                self.assertEqual(rows[2:], [(messages[word], joiner[language].join(messages[f"view.item.{key}"] for key in keys)) for word, keys in groups.items()])
                self.assertEqual(sorted(key for keys in groups.values() for key in keys), sorted(item.key for item in ITEMS))
            if language == "en":
                phrases = (
                    f"{mark.format(messages['view.recap.button'])} above the panels opens a window with a table of the items of the panels: the value of each in the period shown and in the period of the same length just before it (for {mark.format(messages['view.period.years1'])} and the like, years counted by the dates, so that the days can differ by one; see below), and their difference.",
                    f"It opens where the window of {mark.format(messages['view.marks.button'])} opens; only one of the windows of {mark.format(messages['view.marks.button'])}, {mark.format(messages['view.recap.button'])}, saving, and the laps opens at a time. {mark.format(messages['help.close'])}, or the Esc key in the window, closes it (a press outside it does not). Whether it was open is not remembered.",
                    "It can be used with panels, while years are not compared, no other view shows, and the page is not in **Full screen**.",
                    f"Its columns are {mark.format(messages['view.recap.item'])}, the period shown ({mark.format(messages['view.recap.now.years1'])}, {mark.format(messages['view.recap.now.custom'])}, and so on), the period before ({mark.format(messages['view.recap.before.years1'])}, {mark.format(days[31])}, and so on), and {mark.format(messages['view.recap.difference'])}.",
                    f"counted with the same {mark.format(messages['view.types.label'])} and conditions as the panels",
                    f"A period without a value says {mark.format(messages['view.recap.none'])}. An item that is a total or a number of recorded activities is 0 for a period without an activity of the types counted (that meets the conditions, where there are some) where the period reaches between the first and the last such activity in the output, and then has a difference",
                    f"The period before is, for {mark.format(messages['view.period.years1'])}, {mark.format(messages['view.period.years3'])}, and so on, as many years, counted by the dates, up to the day before the period shown; for a range of {mark.format(messages['view.period.custom'])}, the same number of days just before it, and the column gives the days, such as {mark.format(messages['view.recap.before.days'].format(n=31))}.",
                    "‹ moves by the same number of days, so where the year shown has 29 February, the period it moves to and the year before differ by a day",
                    f"‹ and › make the period a range, and the columns then say {mark.format(messages['view.recap.now.custom'])} and the days of the range moved ({mark.format(days[365])} from {mark.format(messages['view.period.years1'])}, or 366 for a year with 29 February).",
                    "A difference is the value now minus the value before, as a sign and a number only, that of the two values as the table writes them",
                    f"the line under the title says {mark.format(messages['view.recap.outside'])}.",
                    f"The window takes the focus on its title. Tab goes to {mark.format(messages['help.close'])} and to the table, which ↑ and ↓ scroll (its row of headings stays in place).",
                )
                keyboard = f"In {mark.format(messages['view.recap.button'])} (from 2.2.0), the window takes the focus on its title; Tab goes to {mark.format(messages['help.close'])} and to the table, which ↑ and ↓ scroll, and Esc closes it, back to its button ([Summary](#summary-from-220))."
                steps = (f"2. Press {mark.format(messages['view.period.years1'])} in {mark.format(messages['view.period.label'])} above.", f"3. Press {mark.format(messages['view.recap.button'])} above the panels", f"5. ‹ and › make the period a range: the columns then say {mark.format(messages['view.recap.now.custom'])} and {mark.format(days[365])} (366 for a year with 29 February).")
                link = "(#summary-from-220)"
            else:
                phrases = (
                    f"段の上の行の{mark.format(messages['view.recap.button'])}で、並べた段の項目を表にした窓を開きます。今の期間と、その前の同じ長さの期間（「1 年」などは日付で数えた年なので、日数が 1 日違うことがあります。下を見てください）の値と、その差が並びます。",
                    f"窓は{mark.format(messages['view.marks.button'])}の窓と同じ所に開きます。{mark.format(messages['view.marks.button'])}{mark.format(messages['view.recap.button'])}と画像で保存とラップの窓は、どれか 1 つだけが開きます。閉じるときは{mark.format(messages['help.close'])}を押すか、窓の中で Esc キーを押します（窓の外を押しても閉じません）。開いていたかは覚えません。",
                    "段が 1 つ以上あり、年でくらべる・ほかの見方・全画面でないときに使えます。",
                    f"列は{mark.format(messages['view.recap.item'])}、今の期間（{mark.format(messages['view.recap.now.years1'])}{mark.format(messages['view.recap.now.custom'])}など）、前の期間（{mark.format(messages['view.recap.before.years1'])}{mark.format(days[31])}など）、{mark.format(messages['view.recap.difference'])}です。",
                    f"段と同じ{mark.format(messages['view.types.label'])}と条件で数えます。",
                    f"値が無いときは{mark.format(messages['view.recap.none'])}です。記録されたアクティビティの合計と数の項目は、その期間に数える種目のアクティビティ（条件があるときは、条件に合うもの）が 1 回も無くても、期間が、出力の中のそのアクティビティの最初と最後のあいだにかかるなら 0 で、差も出ます。",
                    f"前の期間は、{mark.format(messages['view.period.years1'])}{mark.format(messages['view.period.years3'])}などなら、今の期間の始まりの前の日までの、日付で数えた同じ年数です。{mark.format(messages['view.period.custom'])}の範囲なら、同じ日数のすぐ前で、列は{mark.format(messages['view.recap.before.days'].format(n=31))}のように日数で出ます。",
                    "‹ は同じ日数だけ動かすので、今の 1 年に 2 月 29 日があると、‹ で動かした先の期間と、前の 1 年が 1 日違います。",
                    f"‹ › を押すと期間は範囲になり、列の見出しは{mark.format(messages['view.recap.now.custom'])}と、動かした範囲の日数の見出しに変わります（{mark.format(messages['view.period.years1'])}からなら{mark.format(days[365])}、2 月 29 日を含む 1 年なら 366 日）。",
                    "差は、表に書いた今の値から前の値を引いた数で、符号と数だけです",
                    f"題の下の行は{mark.format(messages['view.recap.outside'])}です。",
                    f"窓を開くと、窓の題にフォーカスが移ります。Tab キーで{mark.format(messages['help.close'])}と表へ進み、表は ↑ ↓ キーで送れます（見出しの行は動かずに残ります）。",
                )
                keyboard = f"まとめ（2.2.0 から）は、窓を開くと窓の題にフォーカスが移り、Tab キーで{mark.format(messages['help.close'])}と表へ進みます。表は ↑ ↓ キーで送れ、Esc キーで{mark.format(messages['view.recap.button'])}に戻って閉じます（[まとめ](#まとめ220-から)）。"
                steps = (f"2. 上の{mark.format(messages['view.period.label'])}で{mark.format(messages['view.period.years1'])}を押します。", f"3. 段の上の{mark.format(messages['view.recap.button'])}を押します。", f"5. ‹ › を押すと期間は範囲になり、列の見出しは{mark.format(messages['view.recap.now.custom'])}と{mark.format(days[365])}（2 月 29 日を含む 1 年なら 366 日）に変わります。")
                link = "(#まとめ220-から)"
            for phrase in phrases:
                with self.subTest(language=language, phrase=phrase):
                    self.assertEqual(joined.count(phrase), 1)
            with self.subTest(language=language, part="keyboard"):
                self.assertEqual(reads.count(keyboard), 1)
            # The tenth scene leads to the summary, in the words of the page.
            start = text.index(f"\n### {scene[language]}\n")
            scene_text = text[start : text.index("\n### ", start + 1)]
            scene_reads = " ".join(scene_text.split()) if language == "en" else re.sub(r"\n *", "", scene_text)
            with self.subTest(language=language, part="scene"):
                for step in steps:
                    self.assertIn(step, scene_reads)
                self.assertIn(link, scene_text)
            # Every word quoted is a word of the page, a heading as the page
            # writes it, or the dash and the star of the table.
            words = set(messages.values()) | set(days.values()) | {"—", "*"}
            pattern = r"\*\*([^*]+)\*\*" if language == "en" else r"「([^」]+)」"
            for value in (joined, scene_reads):
                for word in re.findall(pattern, value):
                    with self.subTest(language=language, quoted=word):
                        self.assertIn(word, words)

    def test_guides_give_the_saving_as_the_page_does(self) -> None:
        # v2.2.0 R3: saving as an image (stages R1 and R2) has a section of
        # its own after the summary, before the readings of an output that
        # changes (the checker's answer 1 of the plan of R3), and a scene, the
        # tenth (answer 2). What the guides say of it is what the page does,
        # so that a change of either fails here (Codex's review of the plan of
        # R3): the first choices of the window, the row above the panels that
        # hides, what a picture leaves out, the views that cannot save without
        # values, the browser that saves the file, the reasons at the press,
        # and where the focus goes. The names of the files are those that
        # saveFileName and saveViewFileName give (tests/gui_js/view_flow.test.mjs).
        # Every word quoted is a word of the page, whole: a label, or in
        # English a line in quotes (the checker's review of the handling).
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")
        held = {
            "openSave": ('state.saveScope = "all";', 'state.saveColors = "light";', "state.saveMarks = false;", "(open ? ui.saveTitle : saveButton(state.saveFrom)).focus();"),
            "renderSave": ("if (state.saveOpen && state.saveFrom !== view) {\n    state.saveOpen = false;", "ui.saveOpen.disabled = !viewing || !state.items.length;", "ui.saveGo.disabled = !target.ready;"),
            "saveImage": (
                # Stage U1 of v2.2.0: none kept that the window says by itself,
                # and the focus on the title where the button cannot be pressed.
                "said: saveSaysNow(target, panels && savePanelGone(target.plan)).said,",
                'problem = "view.save.failed";',
                "link.download = target.name;",
                "(ui.saveGo.disabled ? ui.saveTitle : ui.saveGo).focus();",
            ),
            "saveTarget": ("const problem = saveProblem({ stopped: state.seriesStop !== null, loading: state.loading, answer: state.answer, drawn, parts: plan.keys.length });",),
        }
        for name, lines in held.items():
            body = function_body(page, name)
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body)
        self.assertIn("ui.caveat.hidden = !viewing || apart();", page)
        # Close and Cancel close the window back to its button, as Escape does
        # (the checker's review of the diff of R3).
        self.assertIn('ui.saveClose.addEventListener("click", () => openSave(false));\n  ui.saveCancel.addEventListener("click", () => openSave(false));', page)
        self.assertIn(".view-app.full .caveat,", css)
        self.assertIn('export const SAVE_LEFT_OUT_VIEWS = {\n  compare: [".cross", ".calendar-cursor"],\n  plot: [".plot-chosen"],\n  spread: [".spread-chosen"],\n  // The cross lines of the rows of the shoes (stage S1 of v2.2.0).\n  shoes: [".cross"],\n};', flow)
        # A period without values stops two items plotted and a distribution
        # only; the panels and comparing years save the words of an empty
        # chart (Codex's review of the plan of R3).
        self.assertEqual(
            re.findall(r"^    empty: (.*),$", page, re.M),
            # And the view by shoes, which a period without shoes stops too
            # (stage S1 of v2.2.0).
            ["target.empty", "false", "drawn !== null && !drawn.shoes.length", 'entry.plot.querySelector(".panel-empty")?.textContent ?? null', "answer !== null && !answer.points.length", "answer !== null && !answer.counts.length"],
        )
        heading = {"en": "Saving as an image (from 2.2.0)", "ja": "画像で保存（2.2.0 から）"}
        before = {"en": "Summary (from 2.2.0)", "ja": "まとめ（2.2.0 から）"}
        after = {"en": "When the output changes while you look", "ja": "見ている間に出力が変わったとき"}
        says = {
            "en": (
                "**Save as image…** is right after **Summary…** in the row above the panels, and right after **Show as a table** in the bars of **Compare years**, **Plot two items**, **Distribution**, and **By shoes**.",
                "The row above the panels does not show while years are compared, another view is shown, or in full screen. Without panels, its **Save as image…** cannot be pressed.",
                "The window closes when you go from the view it opened in (the panels, **Compare years**, or another view) to another view. In full screen it does not close but hides, and shows again after it (the window of **Summary…** hides while years are compared, another view is shown, or in full screen, and shows again after them).",
                "its choices are the first ones again: all the panels, the light colors, and no marks (nothing is remembered).",
                "the cross line (the vertical line at the period whose values are read), and the frames that show the day, point, or range chosen, with the readings of its values, never go in; the points, the bars, and the days themselves do, and the lines of the marks do where **Marks** puts them in.",
                "for two items plotted or a distribution, a period without values to draw;",
                "A panel or a year without values goes in with the words that the page shows for it.",
                "**Save** hands the file to the browser as a download, which the browser saves where its settings say (usually your downloads, or where you choose if it asks each time). This app cannot know that it was saved,",
                "the window says so. Where it can no longer save at the press, it says the reason that it would show by itself, such as **Reading…**; those words go when the reason does. The focus stays on **Save** where it can still be pressed, and goes to the title of the window where it cannot; check the window, and press **Save** again when it can save.",
                "In forced colors (a contrast theme of Windows, for example), the picture takes the colors of the screen, whichever **Colors** gives.",
                "Once **Save** hands the file to the browser, the window closes (where it cannot, the window stays open and says why). Esc, **Close**, or **Cancel** closes it without saving (**Close** and **Cancel** do the same). The focus then goes back to its **Save as image…**.",
            ),
            "ja": (
                "段の上の行の「まとめ…」の右と、くらべる帯（年でくらべる）と見方の帯（点で並べる・分かれ方・靴ごと）の「表で見る」の右に、「画像で保存…」があります。",
                "年でくらべる・ほかの見方・全画面の間は、段の上の行が隠れます。段が無いときは、段の上の「画像で保存…」は押せません。",
                "窓は、開いたときの見方（段を並べて見る・年でくらべる・ほかの見方）から別の見方に移ると閉じます。全画面の間は閉じずに隠れ、戻ると出ます（「まとめ…」の窓は、年でくらべる・ほかの見方・全画面の間は隠れ、戻ると出ます）。",
                "窓を開くたびに、選びは初めの形（並べた段すべて・明るい色・印は入れない）に戻ります（覚えません）。",
                "全体図・一覧・ボタン・出力のフォルダーの名前と、十字線（値を読む区切りに立つ縦の線）、選んだ日・点・区間を示す枠、その値を読む所は入りません（点や棒、カレンダーの日そのものは入ります。印の線は、「印」で選んだときに入ります）。",
                "点で並べると分かれ方で期間に図にする値が無いとき",
                "値の無い段や年も、ページに出ている言葉のまま入ります。",
                "窓の「保存」を押すと、画像のファイルをブラウザーにダウンロードとして渡します。保存する場所は、ブラウザーの設定のとおりです（ふつうはダウンロードの場所。毎回聞く設定なら、そのとき選んだ場所）。このアプリは、保存できたかを知らないので、",
                "押したときに、保存する図が窓に出ていたものから変わっていたときと、画像を作れなかったときも、窓がわけを言います。押したときに保存できなくなっていたときは、窓は、そのときの保存できないわけ（「読んでいます…」など）を出します。この言葉は、そのわけが無くなると消えます。「保存」が押せるときは、フォーカスは「保存」に残り、押せないときは窓の題に移ります。窓を見直して、保存できるようになったら、もう一度「保存」を押してください。",
                "強制カラーの画面（Windows のコントラスト テーマなど）では、どちらの「色」を選んでも、画像はその画面の色になります。",
                "「保存」でファイルをブラウザーに渡すと、窓は閉じます（渡せなかったときは、窓は開いたままで、わけを言います）。Esc キー・「閉じる」・「やめる」は、どれも保存せずに窓を閉じます（「閉じる」と「やめる」は同じ働きです）。閉じたあとは、フォーカスは押した「画像で保存…」に戻ります。",
            ),
        }
        scene = {"en": "Keep a comparison of years as an image", "ja": "年でくらべた図を画像にして残す"}
        # S2: the scene of the shoes follows (before that of the CSV file).
        scenes = {"en": ("Compare the last year with the year before", "See the distance of each pair of shoes by month"), "ja": ("この 1 年と前の 1 年をくらべる", "靴ごとに、月ごとの距離を見る")}
        steps = {
            "en": ("Press **Compare years** in the heading of a panel", "Press **Save as image…** in its bar.", "Choose the colors under **Colors**, and press **Save**.", "look in your downloads.", "More: [Saving as an image](#saving-as-an-image-from-220)"),
            "ja": ("段の見出しの「年でくらべる」を押し", "帯の「画像で保存…」を押します。", "「色」を選び、「保存」を押します。", "ブラウザーのダウンロードの場所を見ます。", "くわしくは：[画像で保存](#画像で保存220-から)"),
        }
        # The marks, privacy, and the keys elsewhere in the guides (the plan of
        # R3, and Codex's review of it: an image you save can show the names
        # of the marks, and forgetting the settings does not remove it).
        elsewhere = {
            "en": (
                "This app keeps the marks only in `gui-marks.json`",
                "An image you save shows them where you choose **Put in the lines and names of the marks** in [Saving as an image](#saving-as-an-image-from-220) while the page shows the marks, and when you save a comparison by race day.",
                "so this app keeps them only in the file of the marks, `gui-marks.json`, never in an output, the Support Bundle, or the text of a report on GitHub (an image you save with [Saving as an image](#saving-as-an-image-from-220) shows them where you put them in, and by race day).",
                "hands it to the browser as a download; this app sends nothing anywhere. With the marks put in, and by race day, the names of the marks show too.",
                "The images you saved are your own files: **Forget the remembered settings…** does not remove them.",
                "In **Save as image…** (from 2.2.0), the window takes the focus on its title; Esc, **Close**, or **Cancel** closes it, back to its button, as does handing the file to the browser; where it could not save, the window says why, and the focus stays on **Save** where it can still be pressed, or goes to the title of the window where it cannot",
            ),
            "ja": (
                "印は、このアプリが、このコンピューターの GUI の設定のフォルダーの `gui-marks.json` にだけ残します",
                "[画像で保存](#画像で保存220-から)で「印の線と名前を入れる」を選んだとき（ページで印を出しているとき）と、大会の日でくらべた図を保存したときは、保存した画像に写ります。",
                "このアプリは、印のファイル `gui-marks.json` にだけ残します。出力・問い合わせ用ファイル・GitHub への報告の文には入りません（[画像で保存](#画像で保存220-から)で印を入れたときと、大会の日でくらべた図は、あなたが保存する画像に写ります）。",
                "ブラウザーにダウンロードとして渡すだけで、このアプリはどこへも送りません。印を入れたときと、大会の日でくらべた図は、印の名前も写ります。",
                "保存した画像はあなたのファイルなので、「覚えた設定を消す…」では消えません。",
                "画像で保存（2.2.0 から）は、窓を開くと窓の題にフォーカスが移ります。Esc キー・「閉じる」・「やめる」で閉じたときと、ファイルをブラウザーに渡したあとは、押した「画像で保存…」に戻ります。保存できなかったときは、窓がわけを言い、「保存」が押せるときは、フォーカスは「保存」に残り、押せないときは窓の題に移ります",
            ),
        }
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            messages = catalog(language)
            read = (lambda part: " ".join(part.split())) if language == "en" else (lambda part: re.sub(r"\n *", "", part))
            places = [text.index(f"\n### {title}\n") for title in (before[language], heading[language], after[language])]
            with self.subTest(language=language, part="order"):
                self.assertEqual(places, sorted(places))
                self.assertEqual(text.index("\n### ", places[1] + 1), places[2])
            joined = read(text[places[1] : places[2]])
            with self.subTest(language=language, part="section"):
                for phrase in says[language]:
                    self.assertIn(phrase, joined)
                # The line after a saving, whole, as the page writes it.
                notice = messages["view.save.notice"]
                self.assertIn(f'"{notice}"' if language == "en" else f"「{notice}」", joined)
            start = text.index(f"\n### {scene[language]}\n")
            scene_reads = read(text[start : text.index("\n### ", start + 1)])
            with self.subTest(language=language, part="scene"):
                self.assertLess(text.index(f"\n### {scenes[language][0]}\n"), start)
                self.assertEqual(text.index("\n### ", start + 1), text.index(f"\n### {scenes[language][1]}\n"))
                for step in steps[language]:
                    self.assertIn(step, scene_reads)
            with self.subTest(language=language, part="elsewhere"):
                whole = read(text)
                for phrase in elsewhere[language]:
                    self.assertIn(phrase, whole)
            # Every word quoted is a word of the page, whole.
            words = set(messages.values())
            patterns = (r"\*\*([^*]+)\*\*", r'"([^"]+)"') if language == "en" else (r"「([^」]+)」",)
            for value in (joined, scene_reads):
                for pattern in patterns:
                    for word in re.findall(pattern, value):
                        with self.subTest(language=language, quoted=word):
                            self.assertIn(word, words)
            # The help of the page says it in short (the checker's answer 2).
            with self.subTest(language=language, part="help"):
                help_text = messages["view.help.save_text"]
                self.assertIn(messages["view.save.button"], help_text)
                for phrase in {"en": ("hands what you see to the browser as one SVG file to download", "dates (or years) and the keys of the items only", "nothing is sent anywhere"), "ja": ("ブラウザーにダウンロードとして渡します", "日付（または年）と項目の鍵だけ", "どこへも送りません")}[language]:
                    self.assertIn(phrase, help_text)

    def test_guides_give_the_shoes_as_the_page_does(self) -> None:
        # v2.2.0 S2: the view by shoes of stage S1 has a heading of its own
        # under the other views, after the distribution and before the summary
        # (the checker's answer 1 of the plan of S2), and the eleventh of the
        # twelve scenes (answer 2). What the guides, the help, and the design
        # say of it is what the page and the server do, so that a change of
        # either fails here (Codex's review of the plan of S2): bars up to
        # MAX_BARS months and a line above (1), the picture that cannot be
        # saved without a pair of shoes in the period (2), the panels asked
        # again on the way back only after a change in another view (3), the
        # item that cannot be chosen for the activities of the output of any
        # type (8), the axis over the period chosen (9), the names, the order,
        # the notes, the keys, the tables, the name of a file, and what is not
        # remembered. Each sentence is held whole; every word quoted is a word
        # of the page, whole (4).
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        chart = (STATIC_ROOT / "view_chart.mjs").read_text(encoding="utf-8")
        server = (ROOT / "src/garmin_running_data_normalizer/view/series.py").read_text(encoding="utf-8")
        reader = (ROOT / "src/garmin_running_data_normalizer/view/data.py").read_text(encoding="utf-8")
        settings = (ROOT / "src/garmin_running_data_normalizer/gui/settings.py").read_text(encoding="utf-8")
        bars = int(re.search(r"^export const MAX_BARS = (\d+);$", chart, re.M).group(1))
        self.assertEqual(bars, 220)
        self.assertIn("const bars = zeros && !lineOnly && periods.length <= MAX_BARS;", chart)
        held = {
            (flow, "shoeWords"): ('message("view.shoes.unnamed")', 'message("view.shoes.started", { day: dateText(shoe.day, language) })', 'message("view.shoes.number", { n: shoe.number })'),
            (flow, "shoesNotes"): ('const notes = [message("view.shoes.note_garmin")];', "if (Number.isInteger(answer[name]) && answer[name] > 0) {"),
            (flow, "shoesWhy"): ('return "view.other.shoes_too_large";', 'return known && Number.isInteger(shoes.count) && shoes.count > 0 ? null : "view.other.shoes_none";'),
            (flow, "saveViewFileName"): ("return `garmin-shoes_${start}_${end}_${key}.svg`;",),
            (page, "drawShoePlot"): ("width, height, total: true, shared: context.shared });", 'appendMarks(svg, shapes.lines[0], "c1", null, { outlined: true });'),
            (page, "renderShoesBody"): ("shoes.cursor = periods.length - 1;",),
            (page, "shoesKeyDown"): ("const moves = { ArrowLeft: state.shoes.cursor - 1, ArrowRight: state.shoes.cursor + 1, Home: 0, End: last };",),
            (page, "moveShoesCross"): ("setText(ui.shoesAnnouncer, `${describe(shoeName(answer.shoes[entry.index], state.language))} ${words}`);",),
            (page, "saveShoesTarget"): ("empty: drawn !== null && !drawn.shoes.length,", 'name: drawn === null ? null : saveViewFileName("shoes", { key: "dist", start: drawn.start, end: drawn.end }),'),
            (page, "requestShown"): ("state.panelsStale = true;",),
            (page, "leaveShoes"): ("if (state.panelsStale) {",),
            # Stage U1 of v2.2.0: another view of another reading than the
            # panels marks them too, only after the check of its generation.
            (page, "otherReading"): ("if (!sameReading(state.answer, answer)) {\n    state.panelsStale = true;",),
            # From stage W1 of v2.2.1, the reading of the answer is taken
            # between the check and its use (takeReading).
            (page, "requestPlot"): ("if (seq !== state.plotSeq) {\n      return;\n    }\n    if (!takeReading(payload.view, answer)) {\n      state.plotLoading = false;\n      return;\n    }\n    state.plotAnswer = answer;\n    otherReading(answer);",),
            (page, "requestSpread"): ("if (seq !== state.spreadSeq) {\n      return;\n    }\n    if (!takeReading(payload.view, answer)) {\n      state.spreadLoading = false;\n      return;\n    }\n    state.spreadAnswer = answer;\n    otherReading(answer);",),
            (page, "requestShoes"): ("if (seq !== state.shoesSeq) {\n      return;\n    }\n    if (!takeReading(payload.view, answer)) {\n      state.shoesLoading = false;\n      return;\n    }\n    state.shoesAnswer = answer;\n    otherReading(answer);",),
        }
        for (script, name), lines in held.items():
            body = function_body(script, name)
            for line in lines:
                with self.subTest(function=name, line=line):
                    self.assertIn(line, body)
        # The panels are asked again on the way back only where requestShown
        # set it, while another view showed (Codex's review of the plan of S2, 3),
        # or where another view took an answer of another reading (stage U1 of
        # v2.2.0): the two places that set it are those two functions.
        self.assertEqual(page.count("state.panelsStale = true;"), 2)
        self.assertEqual(sum(function_body(page, name).count("state.panelsStale = true;") for name in ("requestShown", "otherReading")), 2)
        self.assertEqual(page.count("otherReading(answer);"), 3)
        self.assertIn('ui.shoesPanels.addEventListener("pointermove", shoesPointer);', page)
        self.assertIn('ui.shoesPanels.addEventListener("keydown", shoesKeyDown);', page)
        self.assertIn('name=_shoe_text(record.get("display_name")) or _shoe_text(record.get("custom_make_model")),', reader)
        self.assertIn('keys = {row.marks.get("key") for row in data.rows[ACTIVITIES] if row.marks.get("key")}', server)
        self.assertIn("chosen.append((own[-1].day, shoe.place, entry))", server)
        self.assertIn("chosen.sort(key=lambda found: (-found[0], found[1]))", server)
        # A total of 0 that was recorded is a 0 too, and the dots of 0 are of
        # any 0; the counts of the shoes: two or more and no distance among
        # those with shoes, not known only without a link to shoes (Codex's
        # review of the diff of S2, 1, 3, and 4).
        self.assertIn("            if counts[index]:\n                values.append(totals[index] if item.kind == SUM else float(counts[index]))", server)
        self.assertIn("if (value !== 0) {", function_body(chart, "zeroDots"))
        self.assertIn('        if found:\n            answer["with_shoes"] += 1\n            if len(found) > 1:\n                answer["two_or_more"] += 1\n            if not _has_value(item, row):\n                answer["without_distance"] += 1\n', server)
        self.assertIn('        elif not key or (gear is not None and key in gear.unknown):\n            answer["not_known"] += 1\n', server)
        # Nothing of the view by shoes is remembered.
        self.assertNotIn("view_shoes", settings)
        shoes_heading = {"en": "By shoes", "ja": "靴ごと"}
        spread_heading = {"en": "Distribution", "ja": "分かれ方"}
        summary = {"en": "Summary (from 2.2.0)", "ja": "まとめ（2.2.0 から）"}
        changes = {"en": "When the output changes while you look", "ja": "見ている間に出力が変わったとき"}
        saving = {"en": "Saving as an image (from 2.2.0)", "ja": "画像で保存（2.2.0 から）"}
        scene_title = {"en": "See the distance of each pair of shoes by month", "ja": "靴ごとに、月ごとの距離を見る"}
        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            messages = catalog(language)
            read = (lambda part: " ".join(part.split())) if language == "en" else (lambda part: re.sub(r"\n *", "", part))
            mark = "**{}**" if language == "en" else "「{}」"
            places = [text.index(f"\n#### {spread_heading[language]}\n"), text.index(f"\n#### {shoes_heading[language]}\n"), text.index(f"\n### {summary[language]}\n")]
            with self.subTest(language=language, part="order"):
                self.assertEqual(places, sorted(places))
                self.assertEqual(text.index("\n### ", places[0]), places[2])
            shoes = read(text[places[1] : places[2]])
            if language == "en":
                says = (
                    f"Each pair of shoes is a panel, with its distance by month as bars (as a line over a period of more than {bars} months). Every panel has the same time axis, across the period chosen, and the same scale (one color). As bars, a month that the period cuts is drawn lighter, with an edge.",
                    "A month without an activity with the pair, between the first and the last month that it was used in the output (by an activity of the types counted that meets the conditions, where there are some, also outside the period chosen), is 0, a hollow dot on the base line, as is a month whose activities with the pair add up to 0; before the first and after the last, it is empty. A month of 0 does not always mean that the pair was not used (it may not have been set in Garmin).",
                    "those with shoes but without a distance (in the counts, not in the distances)",
                    f"A name is the one in Garmin; without one, the make and model; without either, {mark.format(messages['view.shoes.unnamed'])}. A long name is cut short with an ellipsis. Shoes of one name are told apart by their start date after the name (the day set in Garmin, where it is theirs alone) or by a number, which are never cut.",
                    "The panels go by the day each pair was last used in the period, the newest first (on the same day, in the order of Garmin's gear). Shoes not used in the period have no panel.",
                    f"Under the panels, {mark.format(messages['view.shoes.note_garmin'])} is always shown, and a line for each count of 1 or more:",
                    f"Where no activity of the period and the types (and of the conditions, where there are some) has shoes, {mark.format(messages['view.shoes.none'])} shows in the place of the panels.",
                    "Move the pointer over a panel, or select a panel (Tab) and use ← and → (a month) and Home and End (the first and the last month), to choose a month: every panel gives its distance at the top right (at first, the last month). With the keys, the name of the shoes and the distance are read out.",
                    f"{mark.format(messages['view.panel.table'])} gives two tables:",
                    f"whose months stay at the left as it scrolls to the right. {mark.format(messages['view.panel.chart'])} goes back.",
                    f"Where no activity of the output (up to today, of any type, and without the conditions) has shoes, {mark.format(messages['view.other.shoes_none'])}, and where the data of the shoes is too large, {mark.format(messages['view.other.shoes_too_large'])} shows under {mark.format(messages['view.other.shoes'])} in the menu, which then cannot be chosen: ↑ and ↓ stop on it, and pressing it does nothing. Where only other periods or types have shoes, it can be chosen, and {mark.format(messages['view.shoes.none'])} shows in the place of the panels.",
                    "The start, the end, and the maximum distance are the values set in Garmin, as they are. This app says nothing from them, such as when to change shoes.",
                    "(assets/gui-guide/view-shoes.en.png)",
                    "(synthetic data)](assets/gui-guide/view-shoes.en.png)",
                )
                saves = (
                    f"By shoes, the window also says {mark.format(messages['view.save.warn_shoes'])}",
                    "or the period and the keys of two items plotted, of a distribution, or of the shoes (the key of the distance, as `garmin-shoes_2024-01-05_2024-12-31_dist.svg`, never the names of the shoes).",
                    "By shoes, every panel goes in, also those scrolled out of the screen, with the time axis and the notes.",
                    "by shoes, a period and types (and conditions) without an activity with shoes;",
                )
                again = "The other views from 2.2.0 (two items plotted, a distribution, and the shoes) may not agree with the panels in the same way. Back from another view, whether the panels are counted again goes as follows: - Where the period, the activity types, or the conditions were changed while it showed: they are counted again. - Where that view gave numbers of an output read again after the panels: they are counted again. - Otherwise: the panels keep their numbers, also where the output changed after the last numbers of that view. Where the numbers of the panels look old, press the button of the period again (the same period will do), and the panels count again from the output as it is now."
                privacy = "The names of the shoes of [By shoes](#by-shoes) (from 2.2.0) may be names you gave in Garmin. They show on the page and in a picture you save (the window says so before saving). This app writes them in no file name, log, or remembered setting."
                steps = (
                    f"In {mark.format(messages['view.other.button'])} above the panels, choose {mark.format(messages['view.other.shoes'])}.",
                    f"(with {mark.format(messages['view.period.all'])}, the panels go over the whole output)",
                    f"For the numbers, press {mark.format(messages['view.panel.table'])}",
                    "More: [By shoes](#by-shoes), [Other views](#other-views-from-220)",
                )
            else:
                says = (
                    f"靴 1 足を 1 段にして、月ごとの距離を棒で並べます（月が {bars} を超える長い期間では、線になります）。どの段も、選んだ期間全体の同じ時間の軸と、同じ目盛りです（色は 1 色）。棒のとき、期間で切れた月の棒は、薄く（縁取りをつけて）出ます。",
                    "出力の中でその靴を初めて使った月と最後に使った月（数える種目のアクティビティで、条件があるときは条件に合うもの。選んだ期間の外も含めます）のあいだで、その靴の付いた回が無い月は 0 で、底の線の上の白抜きの点です（付いた回の距離の合計が 0 の月も、同じ点です）。初めより前と最後より後は空です。0 の月も、その靴を使わなかったとは限りません（Garmin で付け忘れた回もありえます）。",
                    "靴の付いた回のうち距離の無い回（回数には入ります）",
                    f"名前は Garmin の道具の名前のままで、名前が無ければメーカーとモデル、どちらも無ければ{mark.format(messages['view.shoes.unnamed'])}と出ます。長い名前は、終わりを省略記号にして切ります。同じ名前の靴は、名前のあとの使い始めの日（Garmin で決めた日が、その靴だけのとき）か、番号で見分けます。そこは切りません。",
                    "段は、この期間に最後に使った日の新しい順です（同じ日なら、Garmin の道具の順）。この期間に使った回の無い靴は、段にしません。",
                    f"段の下には、いつも{mark.format(messages['view.shoes.note_garmin'])}が出て、次の数は 1 以上のときだけ、1 つずつ 1 行で出ます：",
                    f"その期間と種目に、靴の付いた回が無いとき（条件があるときは、条件に合う回のうち）は、段の代わりに{mark.format(messages['view.shoes.none'])}と出ます。",
                    "段の上でポインターを動かすか、段を選んで（Tab キー）← → キー（1 か月ずつ）と Home・End（最初と最後の月）で月を選ぶと、どの段も右上にその月の距離が出ます（初めは最後の月）。キーで選んだときは、靴の名前とその月の距離を読み上げます。",
                    f"{mark.format(messages['view.panel.table'])}で、2 つの表になります。",
                    f"右へ送っても、月の列は左に残ります）です。{mark.format(messages['view.panel.chart'])}で戻ります。",
                    f"出力のアクティビティ（今日までのもの。種目と条件は問いません）に付いた靴が 1 足も無い出力では{mark.format(messages['view.other.shoes_none'])}、靴のデータが大きすぎる出力では{mark.format(messages['view.other.shoes_too_large'])}が、メニューの{mark.format(messages['view.other.shoes'])}の下に出て、選べません（↑ ↓ キーではそこで止まり、押しても何もしません）。ほかの期間や種目にだけ靴の付いた回があるときは選べ、段の代わりに{mark.format(messages['view.shoes.none'])}が出ます。",
                    "使い始め・使い終わり・上限の距離は、Garmin で決めた値をそのまま出します。このアプリは、それをもとに、いつ替えるかなどを言いません。",
                    "(assets/gui-guide/view-shoes.ja.png)",
                    "（合成のデータ）](assets/gui-guide/view-shoes.ja.png)",
                )
                saves = (
                    f"靴ごとでは、窓に{mark.format(messages['view.save.warn_shoes'])}も出ます。",
                    "点で並べる・分かれ方・靴ごとは、期間と項目の鍵です（靴ごとは距離の鍵で、`garmin-shoes_2024-01-05_2024-12-31_dist.svg` のように。靴の名前は入れません）。",
                    "靴ごとでは、画面の外へ送った段も含めたすべての段と、時間の軸・注が入ります。",
                    "靴ごとでその期間と種目（と条件）に靴の付いた回が無いとき",
                )
                again = "2.2.0 からのほかの見方（点で並べる・分かれ方・靴ごと）でも、同じように段と数が合わないことがあります。ほかの見方から段に戻ったときに、段を数え直すかどうかは、次のとおりです。- ほかの見方の間に、期間か数える種目か条件を変えたとき：数え直します。- ほかの見方が、段よりあとに読み直した出力の数を出していたとき：数え直します。- それ以外のとき：段は前の数のままです（ほかの見方の最後の数のあとに出力が変わったときも）。段の数が古いと思ったら、期間のボタンを押し直すと（同じ期間でもかまいません）、段も今の出力で数え直します。"
                privacy = "[靴ごと](#靴ごと)（2.2.0 から）の靴の名前は、あなたが Garmin で付けた名前のことがあります。名前はページと、画像で保存した画像に写ります（保存の前に、窓がそのことを言います）。このアプリは、靴の名前を、ファイルの名前・ログ・覚えた設定に書きません。"
                steps = (
                    f"段の上の{mark.format(messages['view.other.button'])}で{mark.format(messages['view.other.shoes'])}を選びます。",
                    f"（{mark.format(messages['view.period.all'])}なら、出力全体の期間で並びます）",
                    f"数字で見るときは{mark.format(messages['view.panel.table'])}を押します",
                    "くわしくは：[靴ごと](#靴ごと)、[ほかの見方](#ほかの見方220-から)",
                )
            with self.subTest(language=language, part="shoes"):
                for phrase in says:
                    self.assertEqual(shoes.count(phrase), 1, phrase)
            start = text.index(f"\n### {saving[language]}\n")
            saving_reads = read(text[start : text.index("\n### ", start + 1)])
            with self.subTest(language=language, part="saving"):
                for phrase in saves:
                    self.assertEqual(saving_reads.count(phrase), 1, phrase)
            start = text.index(f"\n### {changes[language]}\n")
            with self.subTest(language=language, part="changes"):
                self.assertEqual(read(text[start : text.index("\n### ", start + 1)]).count(again), 1)
            with self.subTest(language=language, part="privacy"):
                self.assertEqual(read(text).count(privacy), 1)
            start = text.index(f"\n### {scene_title[language]}\n")
            scene_reads = read(text[start : text.index("\n### ", start + 1)])
            with self.subTest(language=language, part="scene"):
                for step in steps:
                    self.assertIn(step, scene_reads)
                for word in ("when to change", "替え時", "いつ替える"):
                    self.assertNotIn(word, scene_reads)
            # Every word quoted in the scene is a word of the page, whole.
            words = set(messages.values())
            patterns = (r"\*\*([^*]+)\*\*", r'"([^"]+)"') if language == "en" else (r"「([^」]+)」",)
            for pattern in patterns:
                for word in re.findall(pattern, scene_reads):
                    with self.subTest(language=language, quoted=word):
                        self.assertIn(word, words)
            # The help: the shoes after the distribution, which no longer goes
            # back; the shoes say the tables and end with the way back.
            back = f"“{messages['view.panel.unbig']}” goes back." if language == "en" else f"戻るときは{mark.format(messages['view.panel.unbig'])}を押します。"
            own = f"“{messages['view.other.shoes']}” shows" if language == "en" else f"{mark.format(messages['view.other.shoes'])}では、"
            table = f"“{messages['view.panel.table']}”" if language == "en" else mark.format(messages["view.panel.table"])
            with self.subTest(language=language, part="help"):
                self.assertNotIn(back, messages["view.help.other_spread"])
                self.assertTrue(messages["view.help.other_shoes"].startswith(own))
                self.assertTrue(messages["view.help.other_shoes"].endswith(back))
                self.assertIn(table, messages["view.help.other_shoes"])
        # The design: the third item of the other views, what is read, what
        # 2.1.0 left out that 2.2.0 adds, the panels on the way back, privacy.
        from garmin_running_data_normalizer.view.data import GEAR_FILES
        from garmin_running_data_normalizer.view.items import DATASETS

        numbers = {2: "two", 10: "ten"}
        design = " ".join((ROOT / "docs/gui_design.md").read_text(encoding="utf-8").split())
        for phrase in (
            "relating two items (v2.2.0 lays the years over each other, also by race day: see [The view page](#the-view-page-v210))",
            "moving averages (v2.2.0 adds the view by shoes: see [The view page](#the-view-page-v210))",
            "Saving a chart as a picture or a file (v2.2.0 saves a chart as an SVG picture: see [The view page](#the-view-page-v210))",
            f"reads only the dates and the values of the items, of {numbers[len(DATASETS)]} files at most,",
            f"From v2.2.0 the view page (never the series command) also reads the {numbers[len(GEAR_FILES)]} files of the shoes, `normalized/gear.json` and `normalized/activity_gear.json`, after those of the items and checked in the same way (one that the manifest leaves out, or that changed, stops the reading with `OUTPUT_CHANGED`), within what the items leave of those limits: where they do not fit, the shoes alone are left out and the page opens (see By shoes below).",
            "- Other views (stages O1, P1, and S1):",
            "An item that cannot be chosen (**By shoes**, where no activity of the output has shoes, or their files were too large to read) says why under its name, stays in the way of the arrow keys (`aria-disabled`), and does nothing when pressed.",
            "The items of two items plotted and of a distribution are the 15 of one activity (the kinds `act`, but the count, and `fit`);",
            "the view by shoes always shows the distance by month, and nothing of it is remembered.",
            "a comparison, a list, the summary, or another view asked right after a new normalization can come from another reading than the panels beside it; asking again uses the new reading. Back from another view, the panels ask again where the period, the activity types, or the conditions changed while it showed (`panelsStale`), and from v2.2.0 (stage U1) where an answer of that view was of another reading than the panels, so that otherwise they show the reading before.",
            "From v2.2.0 the names of the shoes, which may be the person's own words, show on the view page and in a picture saved from the view by shoes (its window says so before saving); they are written in no file name, log, or setting.",
            "an activity with no link to shoes is not known to have shoes where it has no key, or links to gear not in the output or of a type not known;",
            "how many have shoes (and of those, how many have two or more and how many have no distance), are not known, and are without;",
        ):
            with self.subTest(design=phrase):
                self.assertEqual(design.count(phrase), 1)
        start = design.index("- By shoes (stage S1):")
        self.assertLess(design.index("- The distribution of one item (stage P1):"), start)
        self.assertEqual(design.index("- ", start + 1), design.index("- The summary of the panels (stage Q1):"))
        part = design[start : design.index("- The summary of the panels (stage Q1):")]
        for name in ("(`MAX_BARS`)", "(`shoe_count`)", "(`shoe_answer`)", "`POST /api/view/shoes`", "`garmin_activity_key`", "`running_shoes`", "`display_name`", "`custom_make_model`"):
            with self.subTest(by_shoes=name):
                self.assertIn(name, part)

    def test_guides_give_the_conditions_as_the_page_does(self) -> None:
        # v2.2.0 T2: the conditions on the activities (stage T1) in a section
        # of their own after the period, the grouping, and the activity types
        # (the checker's answer 1 of the plan of T2), with the words of the page
        # whole and the numbers of the code. What follows the conditions and
        # what does not is said once (Codex's review of the plan, 9), each
        # list whole in a bullet of its own (Codex's review of the diff, 2); the
        # summary keeps its own words, never those of the second line of a
        # panel (Codex 1); the line on the full screen gives no numbers (the
        # checker's A); the CSV file of series takes no conditions (Codex 2);
        # the names are compared in their first 200 characters (Codex 5); the
        # help gives the conditions after how to use (Codex 11); and an
        # activity without a name, or without a value, fails only a condition
        # on it, in the guides and the design (Codex's review of the diff, 1).
        from garmin_running_data_normalizer.gui.settings import VIEW_KEYS
        from garmin_running_data_normalizer.view.data import MAX_NAME_LENGTH, NAMES
        from garmin_running_data_normalizer.view.series import CONDITION_SEPARATORS, MAX_CONDITION_TEXT, MAX_CONDITION_WORDS, MAX_DISTANCE_METRES, MAX_TIME_MINUTES

        self.assertEqual((MAX_CONDITION_TEXT, MAX_CONDITION_WORDS, MAX_DISTANCE_METRES, MAX_TIME_MINUTES, MAX_NAME_LENGTH), (60, 10, 1_000_000, 6_000, 200))
        self.assertEqual(CONDITION_SEPARATORS.pattern, "[、,]")
        self.assertEqual(NAMES, "normalized/activities.json")
        self.assertEqual(VIEW_KEYS["conditions"], "view_conditions")
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        self.assertIn('const CONDITION_KEYS = ["name", "distance", "time"];', flow)
        self.assertIn('const LIST_KEPT = ["language", "align", "cursor"];', flow)
        self.assertIn('listChanged("numbers");', function_body((STATIC_ROOT / "view.mjs").read_text(encoding="utf-8"), "requestSeries"))
        series_file = (ROOT / "src/garmin_running_data_normalizer/view/series_file.py").read_text(encoding="utf-8")
        self.assertNotIn("conditions", series_file)
        heads = {
            "en": ("### Period, grouping, and activity types", "### Conditions (from 2.2.0)", "### Layouts (from 2.2.0)"),
            "ja": ("### 期間・まとめ方・数える種目", "### 条件で絞る（2.2.0 から）", "### レイアウト（2.2.0 から）"),
        }
        samples = {"en": ("Tempo", "8", "12"), "ja": ("ペース走", "8", "12")}
        for language, path in GUIDES.items():
            messages = catalog(language)
            mark = "**{}**" if language == "en" else "「{}」"
            text = path.read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            before, own, after = heads[language]
            with self.subTest(language=language, part="place"):
                self.assertLess(text.index(f"\n{before}\n"), text.index(f"\n{own}\n"))
                self.assertLess(text.index(f"\n{own}\n"), text.index(f"\n{after}\n"))
            start = text.index(f"\n{own}\n")
            part = text[start : text.index(f"\n{after}\n")]
            joined = " ".join(part.split()) if language == "en" else re.sub(r"\n *", "", part)
            word, low, high = samples[language]
            conditions = messages["view.conditions.text.name"].format(words=word) + messages["view.conditions.text.separator"] + messages["view.conditions.text.distance_range"].format(**{"from": low, "to": high})
            head = messages["view.conditions.line.head"] + messages["view.conditions.line.after"].format(conditions=conditions)
            space = " " if language == "en" else ""
            quoted = [
                messages["view.conditions.button"],
                messages["view.conditions.name"],
                messages["view.conditions.distance"],
                messages["view.conditions.km_from"],
                messages["view.conditions.km_to"],
                messages["view.conditions.time"],
                messages["view.conditions.min_from"],
                messages["view.conditions.min_to"],
                messages["view.conditions.name_note"],
                messages["view.conditions.time_note"],
                messages["view.types.note"],
                messages["view.conditions.problem.distance_order"],
                messages["view.conditions.clear"],
                messages["help.close"],
                head + space + messages["view.conditions.line.period"].format(n="120", m="28"),
                messages["view.conditions.line.whole"].format(n="860", m="190"),
                messages["view.conditions.none_met"],
                messages["view.conditions.names_too_large"],
                messages["view.conditions.line.unread"],
            ]
            # The count of the button, in the sentence that says what it counts (the picture under it
            # names the button too: the guard of T2).
            button = {"en": "the button says {} and so on: how many of the name, the distance, and the duration were given", "ja": "ボタンは{}のように、名前・距離・時間のうち入れたものの数を言います"}[language]
            self.assertIn(button.format(mark.format(messages["view.conditions.button_some"].format(n=2))), joined)
            for words in quoted:
                with self.subTest(language=language, words=words):
                    self.assertIn(mark.format(words), joined)
            numbers = {
                "en": ("up to 60 characters in all, commas included, and 10 words (a word given twice counts once)", "up to 1000 km", "up to 6000", "cut at 200 characters", "`normalized/activities.json`", "(、 separates them too)", "with a comma", "(a least and a most count as one)"),
                "ja": ("言葉は、「、」も含めて全部で 60 字まで、10 個までです（同じ言葉は 1 つに数えます）", "1000 km まで", "6000 分までです", "200 字で切って", "`normalized/activities.json`", "（「,」でも区切れます）", "「、」で区切ると", "（下と上は合わせて 1 つです）"),
            }[language]
            for words in numbers:
                with self.subTest(language=language, number=words):
                    self.assertIn(words, joined)
            # Without a name, or without a value, an activity fails only a
            # condition on it.
            scoped = {
                "en": ("An activity without a name does not meet it.", "An activity without the value does not meet a condition on it."),
                "ja": ("名前の無いアクティビティは、名前の条件には合いません。", "その値の無いアクティビティは、その条件があるときは合いません。"),
            }[language]
            for words in scoped:
                with self.subTest(language=language, scoped=words):
                    self.assertIn(words, joined)
            # What follows the conditions and what does not, said once, each
            # list whole in a bullet of its own, with the words of the page;
            # the full screen gives their words, never their numbers.
            once = {
                "en": ("Following the conditions:", "Not following them:", "whether **By shoes** can be chosen", "the line at the top holds the words of the conditions, not their numbers"),
                "ja": ("条件に従うもの：", "条件に従わないもの：", "「靴ごと」を選べるかどうか", "上の 1 行に条件の言葉が入ります（件数は入りません）"),
            }[language]
            for words in once:
                with self.subTest(language=language, once=words):
                    self.assertEqual(reads.count(words), 1)
            bullets = [" ".join(piece.split()) if language == "en" else re.sub(r"\n *", "", piece).strip() for piece in part.split("\n- ")[1:]]
            page_words = {
                "valued": messages["view.layouts.valued"].split(" {n}")[0],
                "compare": messages["view.compare.button"],
                "summary": messages["view.recap.button"],
                "body": messages["view.group.body"],
                "estimates": messages["view.group.est"],
                "shoes": messages["view.other.shoes"],
            }
            lists = {
                "en": (
                    "Following the conditions: the training and running-form panels, the overview, the bars of the item shelf and the **{valued}** of the layouts, **{compare}** (also by race day and as a calendar), **{summary}** (also the period before), the activities of a day, week, month, or year, two items plotted, the distribution, and the panels, tables, and counts of the shoes.",
                    "Not following them: the panels of **{body}** and **{estimates}**, the first and the last day of the output and the buttons of the period, the years and the races to choose, the counts in the list of the activity types, whether **{shoes}** can be chosen, and the CSV file of `series`.",
                ),
                "ja": (
                    "条件に従うもの：練習と走りの形の段、全体図、項目の棚の横棒とレイアウトの「{valued}」、{compare}（大会の日でくらべる・カレンダーも）、まとめ（前の期間も）、区切りの一覧、点で並べる、分かれ方、{shoes}の段と表と数。",
                    "条件に従わないもの：{body}と {estimates}の段、出力の最初と最後の日と期間のボタン、年と大会の候補、数える種目の一覧の件数、「{shoes}」を選べるかどうか、`series` の CSV。",
                ),
            }[language]
            for whole in lists:
                with self.subTest(language=language, bullet=whole[:20]):
                    self.assertIn(whole.format(**page_words), bullets)
            self.assertNotIn("{n}", messages["view.full.text_conditions"])
            # The summary keeps its own words: the words of a panel with no
            # activity that meets the conditions are not said of it.
            summary = {"en": "### Summary (from 2.2.0)", "ja": "### まとめ（2.2.0 から）"}[language]
            recap = text[text.index(f"\n{summary}\n") : text.index("\n### ", text.index(f"\n{summary}\n") + 1)]
            self.assertNotIn(messages["view.conditions.none_met"], " ".join(recap.split()) if language == "en" else re.sub(r"\n *", "", recap))
            # The words of the page elsewhere: the list, saving, forgetting.
            # The sentence of a list, as the page says it of a week (stage W3 of
            # v2.2.1).
            for words in (messages["view.list.none_met"].replace("{grain}", messages["view.grain_word.week"]), messages["view.save.warn_conditions"]):
                with self.subTest(language=language, page=words):
                    self.assertIn(mark.format(words), reads)
            columns = {"en": "The columns are {}, {}, and {},", "ja": "列は{}{}{}と、"}[language].format(*(mark.format(messages[f"view.list.{key}"]) for key in ("when", "name", "type")))
            self.assertIn(columns, reads)
            forgets = messages["forget.text_also"]
            sentence = {"en": "It also forgets the conditions of the view page (the words of the name, the distance, and the duration).", "ja": "見るページの条件（名前の言葉・距離・時間）も忘れます。"}[language]
            self.assertIn(sentence, forgets)
            self.assertIn(sentence, reads)
            # The CSV file of series takes no conditions, at each of its doors.
            csv = {
                "en": ("of the view page do not apply to the CSV file: its numbers are those without conditions.", "(without the [conditions](#conditions-from-220) of the view page, which do not apply to it)", "Without conditions, the view page shows the numbers that this command writes to a CSV file"),
                "ja": ("は CSV に効かず、CSV の数字は条件の無いときのものです。", "（見るページの[条件](#条件で絞る220-から)は効かず、条件の無いときの数字です）", "見るページの数字は、条件で絞っていなければ、次のコマンドが CSV に書く数字と同じです"),
            }[language]
            for words in csv:
                with self.subTest(language=language, csv=words):
                    self.assertIn(words, reads)
        # The help: an item of the conditions after how to use, which quotes
        # the button and the activity types; three items say the conditions.
        page = (STATIC_ROOT / "view.html").read_text(encoding="utf-8")
        self.assertLess(page.index('aria-labelledby="help-use-heading"'), page.index('aria-labelledby="help-conditions-heading"'))
        self.assertLess(page.index('aria-labelledby="help-conditions-heading"'), page.index('aria-labelledby="help-shelf-heading"'))
        for language in GUIDES:
            messages = catalog(language)
            for key, words in (("view.help.use_text", ("条件", "conditions")), ("view.help.layouts_text", ("条件", "conditions")), ("view.help.zero_text", ("条件", "conditions")), ("view.hint.filters", ("条件", "conditions"))):
                with self.subTest(language=language, key=key):
                    self.assertIn(words[0] if language == "ja" else words[1], messages[key])
        # The design: an item of its own after that of L3, before an output
        # that changes, and the reading of an output gives the names.
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        own = design.index("- Conditions on the activities (stage T1):")
        self.assertLess(design.index("- The colors of the years compared and a year highlighted (stage L3):"), own)
        self.assertLess(own, design.index("- An output that changes while the view page is open is read again"))
        item = design[own : design.index("- An output that changes while the view page is open is read again")]
        for name in ("`view_conditions`", "`CONDITIONS_INVALID`", "`normalized/activities.json`", "`_activity_rows`", "`condition_words`", "`series` takes none"):
            with self.subTest(design=name):
                self.assertIn(name, item)
        # Without a name, an activity fails the words only where they are
        # used: where there are words and the names were read.
        for words in ("An activity meets them where its name holds one of the words, if there are words and the names were read, and its distance and duration", "; without a name where the words are used, or without the value of a bound given, it does not."):
            with self.subTest(design=words):
                self.assertIn(words, item)
        server = (ROOT / "src/garmin_running_data_normalizer/view/series.py").read_text(encoding="utf-8")
        meets = server[server.index("def _meets(") : server.index("\ndef ", server.index("def _meets("))]
        self.assertIn("    if conditions.words and names is not None and not names.too_large:\n", meets)
        reading = design[design.index("Reading an output:") : design.index("- Rows without a date")]
        self.assertIn("it reads the file of the names of the activities, `normalized/activities.json`", reading)
        self.assertIn("The series command parses neither the shoes nor the names", reading)

    def test_the_design_gives_the_summary(self) -> None:
        # v2.2.0 Q2: the design of the GUI gives the summary of stage Q1 after
        # the distribution, with the names of the code that it is made of, and
        # the readings of an output that changes name it with a comparison and
        # a list (the plan of Q2).
        flowing = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        spread = flowing.index("- The distribution of one item (stage P1):")
        summary = flowing.index("- The summary of the panels (stage Q1):")
        readings = flowing.index("- An output that changes while the view page is open is read again")
        self.assertLess(spread, summary)
        self.assertLess(summary, readings)
        # v2.2.0 R3: the item of saving comes between, so that the summary is
        # read up to it, as before R3 (Codex's review of the diff of R3).
        part = flowing[summary : flowing.index("- Saving as an image (stages R1 and R2):")]
        for name in ('`/api/view/series` with `"previous": true`', "`RANGE_GRAIN`", "`item_series`", "`LAST_YEARS`", "`period_bounds`", "**Summary…** after **Other views**"):
            with self.subTest(name=name):
                self.assertIn(name, part)
        self.assertIn("a comparison, a list, the summary, or another view asked right after a new normalization", flowing)
        server = (ROOT / "src/garmin_running_data_normalizer/view/series.py").read_text(encoding="utf-8")
        self.assertIn("def view_answer(\n    data: ViewData,\n    keys: Collection[str],\n    period: str | tuple[date, date] = \"all\",\n    grain: str = \"auto\",\n    types: Collection[str] | None = None,\n    previous: bool = False,\n    conditions: Conditions | None = None,\n)", server)
        self.assertIn('return grain === "day" ? "view.kind.obs_points" : "view.kind.obs_mean";', (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8"))

    def test_the_design_gives_the_saving(self) -> None:
        # v2.2.0 R3: the design of the GUI gives saving as an image (stages R1
        # and R2) after the summary, before an output that changes, with the
        # names of the code that it is made of, and what the page cannot know;
        # its privacy; and only SVG, PNG and the other formats out of scope
        # (the checker's answer of the plan of R3).
        design = (ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8")
        flowing = " ".join(design.split())
        summary = flowing.index("- The summary of the panels (stage Q1):")
        saving = flowing.index("- Saving as an image (stages R1 and R2):")
        readings = flowing.index("- An output that changes while the view page is open is read again")
        self.assertLess(summary, saving)
        self.assertLess(saving, readings)
        part = flowing[saving:readings]
        for name in ("`.save-stage`", "`writeSaveStyles`", "`SAVE_LEFT_OUT_VIEWS`", "`blob:`", "`download`", "`saveFileName`", "`saveViewFileName`"):
            with self.subTest(name=name):
                self.assertIn(name, part)
        for phrase in (
            "the page cannot know whether or where the browser saves it, so the bar at the bottom says that it was handed.",
            "Nothing is sent to the server or anywhere else, and the Content-Security-Policy stays as it is.",
            "Only SVG is made; PNG and the other formats are out of scope.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, part)
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        for code in ('element("div", "save-stage")', "function writeSaveStyles(", "export const SAVE_LEFT_OUT_VIEWS = {", "export function saveFileName(", "export function saveViewFileName("):
            with self.subTest(code=code):
                self.assertIn(code, page + flow)
        privacy = " ".join(section(design, "Privacy").split())
        self.assertIn("From v2.2.0 a picture saved from the view page shows the dates and values of its charts, and the names of the marks where they are put in and by race day;", privacy)
        self.assertIn("A picture saved is the person's own file, which \"Forget the remembered settings…\" does not remove.", privacy)

    def test_the_design_gives_the_generation_of_the_settings(self) -> None:
        # v2.2.0 U2: the design gives the generation of the settings, each part
        # tied to the code that does it (the plan of U2 and the checker's A and
        # B): forgetting moves it on, a stale change writes nothing, a run that
        # ends needs none, the order of the locks, the pages that follow it and
        # read the settings again as they come forward, and one GUI only; the
        # messages between the tabs carry it; and the months of 0 of the shoes.
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        for line in (
            "From stage U2 of v2.2.0 the settings have a generation: a whole number that the server keeps from 0 for its launch, never in a file, under the lock of the settings, and gives in `/api/status`, read at once with the settings and the marks.",
            "Forgetting the settings moves it on by one, also when a file is left, and its answer tells it;",
            "The server writes a change of the generation now only.",
            '`{"stale": true, "generation": n}` (200, which the page takes for no error), before a file is read or a layout or a mark that the change names is looked for, and one without a generation is refused (`REQUEST_INVALID`).',
            "A run that ends remembers its places without a generation: the settings are not forgotten while a run is active, and the server forgets them under the lock of the runs, so that no run starts meanwhile (that lock is taken before the lock of the settings, never after it).",
            "As a page comes forward (`visibilitychange` and `focus`), it reads `/api/status` again, so that a tab that did not hear the message moves on before the person changes anything there.",
            # Codex's review of the diff of U2: the stamp of a change, the
            # reading that gives no answer, and what the page keeps.
            "A change of the person takes a stamp as it is made: it goes with the generation that the reading on its way then reads, or else with that of its moment, and not at all where the page heard of a forgetting by a message since, as it was made before that forgetting; a reading that gives no answer in 10 seconds is one that could not read.",
            "it keeps the layout in use where the layouts still offer it, and whether the marks show",
            'So "only a change of the person writes them again" holds in every tab.',
            # The way that is left (the checker's review of the handling of
            # Codex's review of the diff).
            "One way is left: in a tab that did not hear the message, a change made right after the page came forward can be written with the generation after a forgetting done in another window while the reading of the page waits on the server for seconds; by hand, the reading ends first.",
            "The generation holds for one GUI, as the lock does: the page of another launch cannot ask this server (its key is another), and two GUIs of two processes are outside it.",
            "which carries the colors, and the generation of the settings after a forgetting (from stage U2 of v2.2.0; until then, the notice that they were forgotten), only; never the key.",
            "carry the colors, the generation of the settings after a forgetting (from stage U2 of v2.2.0; until then, the notice that they were forgotten), and the notice that the app stopped; never the key.",
            "its distance by month (0 between its first and last use in the output, of the types counted that meet the conditions, also outside the period, as on the panels: stage U2)",
            "its activities by month, its first and last days in the period,",
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, design)
        gui = ROOT / "src" / "garmin_running_data_normalizer" / "gui"
        settings = (gui / "settings.py").read_text(encoding="utf-8")
        # From stage W4 of v2.2.1 the abandoned temporary files are looked at
        # in the same lock, before the generation moves on; from stage X1 of
        # v2.3.0 by the one count of what there is to forget, which the status
        # takes as well (the checker's review of the plan of X1).
        self.assertIn("    with _CHANGE_LOCK:\n        present, temporaries, unknown, newer = _to_forget(places_to_forget)\n        _generation += 1\n", settings)
        self.assertIn("    with _CHANGE_LOCK:\n        values, notice = read_settings(path)\n        marks, marks_notice = read_marks(marks_path)\n        # What there is to forget, as forgetting counts it (stage X1 of\n        # v2.3.0; the temporary files from stage W4 of v2.2.1); the launch is\n        # told by the places remembered, not by this.\n        present = _to_forget((path, marks_path))[0]\n        generation = _generation\n", settings)
        count = re.search(r"\ndef _to_forget\(.*?\n\n\n", settings, re.DOTALL)
        assert count is not None
        self.assertIn("    present = any(settings_present(place) for place in places)\n    try:\n        temporaries, unknown, newer = _abandoned_temporaries(places)\n    except OSError:\n", count.group(0))
        self.assertIn("        temporaries, unknown, newer = [], {0}, set()\n    return present or bool(temporaries) or bool(unknown) or bool(newer), temporaries, unknown, newer\n", count.group(0))
        self.assertNotIn("_temporaries_present", settings)
        self.assertIn("        notice, present, generation = self.server.runs.when_idle(forget_settings)\n", (gui / "server.py").read_text(encoding="utf-8"))
        self.assertIn("        with self._lock:\n            if self._run is not None and self._run.active:\n                raise RunActiveError()\n            return action()\n", (gui / "runs.py").read_text(encoding="utf-8"))
        # The lock of the settings is never held while that of the runs is
        # taken: the settings, the marks, and the layouts know no runs.
        for name in ("settings.py", "marks.py", "layouts.py"):
            with self.subTest(name=name):
                code = (gui / name).read_text(encoding="utf-8")
                self.assertNotIn("from .runs", code)
                self.assertNotIn("from . import runs", code)
        flow = (STATIC_ROOT / "flow.mjs").read_text(encoding="utf-8")
        self.assertIn("export function settingsFollower(\n  read,\n  { moving = () => {}, moved = () => {}, wait = SETTINGS_READ_WAIT_MS, setTimer = setTimeout, clearTimer = clearTimeout } = {},\n) {", flow)
        self.assertIn("export const SETTINGS_READ_WAIT_MS = 10000;", flow)

    def test_readme_puts_the_gui_first(self) -> None:
        # v2.1.0 H1 (the whole flow): the README gives the GUI right after who
        # it is for, with links to the whole flow and the ways to use it of
        # the guide; the changes of each release come after the non-goals,
        # under the same headings, and Start here says where they are; the
        # story of the author stays under why this project (the checker).
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        order = (
            "### Who this is for\n", "### Use it with the GUI\n", "### What you get\n", "### Try it\n",
            "(#what-v221-fixes)", "## Why this project\n", "### Built from a runner's own workflow\n",
            "## Install\n", "## Non-goals\n", "## What v2.2.1 fixes\n", "## What v2.2.0 adds\n", "## What v2.1.0 adds\n",
            "## What v1.3.0 adds\n",
            "### Evidence-backed observation contracts\n", "## Community\n",
        )
        places = [readme.index(part) for part in order]
        self.assertEqual(places, sorted(places))
        for link in ("gui_guide.md#how-it-goes", "gui_guide.md#ways-to-use-it"):
            self.assertIn(link, readme)
        japanese = (ROOT / "README.ja.md").read_text(encoding="utf-8")
        for link in ("(docs/gui_guide.ja.md#全体の流れ)", "(docs/gui_guide.ja.md#場面ごとの使い方)"):
            self.assertIn(link, japanese)
        # The partial guard of H1 found that the order alone did not hold
        # these: Start here says where the changes of each release are, and
        # the steps of the GUI begin with the request of the Export, which
        # takes time.
        self.assertIn(
            "What each release added and changed is in [What v2.2.1 fixes](#what-v221-fixes)",
            section(readme, "Start here"),
        )
        steps = readme[readme.index("### Use it with the GUI\n") : readme.index("### What you get\n")]
        self.assertTrue(re.search(r"^1\. (.*)$", steps, re.M).group(1).startswith("Request your Account Data Export from Garmin"))
        steps = section(japanese, "GUI で使う")
        self.assertTrue(re.search(r"^1\. (.*)$", steps, re.M).group(1).startswith("Garmin にエクスポートをリクエストし"))

    def test_links_inside_the_guides_lead_to_their_headings(self) -> None:
        # GitHub makes the anchor of a heading from its text in lower case,
        # without the characters that are not letters, digits, "_", "-", or
        # spaces, and with each space made a "-".
        def anchor(heading: str) -> str:
            return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")

        for language, path in GUIDES.items():
            text = path.read_text(encoding="utf-8")
            anchors = {anchor(heading) for heading in re.findall(r"^#{1,6} (.+)$", text, re.M)}
            links = re.findall(r"\]\(#([^)]+)\)", text)
            self.assertTrue(links, language)
            for link in links:
                with self.subTest(language=language, link=link):
                    self.assertIn(link, anchors)


    def test_guides_answer_the_reading_of_v200(self) -> None:
        # v2.0.1 F1, from the new AI sessions that read the guides of v2.0.0
        # (stage E2b) and the points left for after it (decision
        # 20261022-15): numbered steps to install Python and this app, what
        # to do for each code of an icon that was not made (stops.py), how to
        # see the version and learn of a new one, how python.org finishes the
        # install on macOS and removes Python, what to leave out of a
        # report, the way back to a normalization that runs, and the window
        # of PowerShell. The guides stay true of the page of v2.0.0, which
        # links to the guides of main through the README.
        # The steps are items of a numbered list, each at the start of its
        # line, in this order ("go on to step 4." ends step 3, so the words
        # alone would not show a lost number).
        steps = {
            "en": (
                "1. See whether Python 3.11 or later is installed", "2. Install Python from the page of",
                "3. Open the terminal again", "4. Run the line below.",
            ),
            "ja": (
                "1. Python 3.11 以降が入っているかを確かめます。",
                "2. [python.org](https://www.python.org/downloads/) のページから",
                "3. ターミナルを開き直して", "4. 下の 1 行を動かします。",
            ),
        }
        for language, wanted in steps.items():
            text = section(GUIDES[language].read_text(encoding="utf-8"), WHAT_YOU_NEED[language])
            places = [match.start() if (match := re.search(rf"^{re.escape(step)}", text, re.M)) else -1 for step in wanted]
            with self.subTest(language=language, steps=wanted):
                self.assertNotIn(-1, places)
                self.assertEqual(places, sorted(places))
        mac_doc, windows_doc = "https://docs.python.org/3/using/mac.html", "https://docs.python.org/3/using/windows.html"
        releases = "https://github.com/tsubotti63/garmin-running-data-normalizer/releases"
        phrases = {
            "en": {
                "What you need": (
                    "the Command Prompt of Windows does not take them",
                    "double-click **Install Certificates.command**",
                    f"[python.org describes]({mac_doc})",
                    "`Ctrl+C` in either window can stop the GUI, and when it does, a normalization that runs is canceled too",
                    "| A line that starts with `ERROR [SHORTCUT_` | The icon could not be made; this app is installed. |",
                    "right after `/Users` on macOS or `C:\\Users` on Windows",
                    "write `USER` in its place",
                    "Do not paste the address of the GUI either",
                    "-m garmin_running_data_normalizer --version",
                    f"[Releases]({releases})",
                ),
                "Start the GUI from an icon": (
                    "This app is installed even then",
                    "`SHORTCUT_PLACE_TAKEN`: a file that this app did not make has the name of the icon",
                    "`SHORTCUT_NOT_CREATED`: the icon could not be written",
                    "do as the macOS item above says after **Don't Allow**",
                    "`SHORTCUT_NOT_SUPPORTED`: only macOS and Windows have the icon",
                ),
                "Go back to the GUI that is open": (
                    "a normalization that runs goes on to its end",
                    "the page shows the normalization that runs, if one runs",
                    "it does not show what the earlier GUI does",
                    "neither does the history of the browser",
                    "do not tick the box and press **Remove the lock file** until that normalization has ended",
                ),
                "Stop the GUI": ("130 is the code of a cancelled run, not an error of this app",),
                "Remove this app": (
                    # v2.1.0 H1: in other words, after the reading of H1.
                    "You do not need to remove Python itself for this app",
                    f"[macOS]({mac_doc})", f"[Windows]({windows_doc})",
                ),
            },
            "ja": {
                "用意するもの": (
                    "Windows のコマンドプロンプトでは動きません",
                    "「Install Certificates.command」をダブルクリックして、入れるのを終えます",
                    f"[python.org の説明]({mac_doc})",
                    "どちらの窓でも、Ctrl+C を押すと GUI が止まることがあり、そのときは実行中の正規化も取り消されます",
                    "| `ERROR [SHORTCUT_` で始まる行 | アイコンを作れませんでした。このアプリは入っています。 |",
                    "macOS では `/Users`、Windows では `C:\\Users` のすぐあと",
                    "`USER` に書き換えます",
                    "GUI のアドレスも貼らないでください",
                    "-m garmin_running_data_normalizer --version",
                    f"[Releases]({releases})",
                ),
                "アイコンから起動する": (
                    "そのときも、このアプリは入っています",
                    "`SHORTCUT_PLACE_TAKEN`：このアプリが作っていないファイルが、アイコンと同じ名前でデスクトップにあります",
                    "`SHORTCUT_NOT_CREATED`：アイコンを書けませんでした",
                    "上の macOS の項目の「許可しない」を押したあとのとおりにして",
                    "`SHORTCUT_NOT_SUPPORTED`：アイコンは macOS と Windows だけです",
                ),
                "開いている GUI に戻る": (
                    "実行中の正規化も、最後まで動きます",
                    "実行中の正規化があれば、そのページに出ます",
                    "前の GUI でしていることは出ません",
                    "ブラウザーの履歴からも開けません",
                    "その正規化が終わるまでは、✓ を入れて「目印のファイルを消す」を押さないでください",
                ),
                "GUI を終える": ("130 は取り消した実行のコードで、このアプリのエラーではありません",),
                "このアプリを片付ける": (
                    "このアプリのために Python そのものを消す要はありません",
                    f"[macOS]({mac_doc})", f"[Windows]({windows_doc})",
                ),
            },
        }
        for language, sections in phrases.items():
            for heading, wanted in sections.items():
                text = flowing(language, heading)
                for phrase in wanted:
                    with self.subTest(language=language, heading=heading, phrase=phrase):
                        self.assertIn(phrase, text)

    def test_guides_answer_the_reading_of_their_changes(self) -> None:
        # v2.0.1 F1, from two new AI sessions that read the changed guides: on
        # a Mac without Python, python3 --version opens the window of the
        # developer tools, which step 1 names; the cases of Windows one by
        # one, the Python Launcher before the older Python (which other apps
        # may use), and either answer to the question on PATH; where to go
        # when the version is still old, without a loop back; how to tell us
        # when the GUI does not open (the Bug report form of the repository,
        # whose fields are required), with the names to write over; the codes
        # of an icon that was not made in their own part; and the way back,
        # the end, and the removal. This app does not look for new versions:
        # it reaches no server by itself.
        for language in ("en", "ja"):
            text = section(GUIDES[language].read_text(encoding="utf-8"), WHAT_YOU_NEED[language])
            step_1 = text[re.search(r"^1\. ", text, re.M).start() : re.search(r"^2\. ", text, re.M).start()]
            with self.subTest(language=language):
                self.assertIn("`xcode-select`", step_1)
        issues = "https://github.com/tsubotti63/garmin-running-data-normalizer/issues"
        phrases = {
            "en": {
                "What you need": (
                    "You may also install this app first and read **How to use** before you request it",
                    "(on Windows, the line says that it is not recognized)",
                    "do not choose **Install** in that window, choose the button that closes it without doing anything, and go on to step 2",
                    "it installs the certificates that Python uses for secure connections",
                    "the folder named like **Python 3.14** in **Applications** of the Finder",
                    "open a new PowerShell window, and run `py --version`",
                    "**Installed apps** is under **Apps** in the Settings of Windows (**Apps & features** on Windows 10)",
                    "when you do not know whether you may uninstall it, leave it installed",
                    "close every window of the terminal (on macOS, quit the Terminal with **Terminal** > **Quit Terminal**"
                    " in its menu), open it again",
                    "copy it with the copy button at the top right of its box",
                    "Windows PowerShell, in any version",
                    "After `ERROR [SHORTCUT_`, you need not move the folder",
                    "| Install Python 3.11 or later, open the terminal again,",
                    "| Do what [When the icon could not be made](#when-the-icon-could-not-be-made) says for the code,",
                    f"choose **New issue** in [Issues]({issues})",
                    "You need an account of GitHub",
                    "do not attach a picture of the screen",
                    "write `COMPUTER` in its place", "write `FOLDER` in their place",
                    "This app does not tell you when a new version comes out",
                    "**Current stable release** names the latest version",
                    "When more than one GUI is open, stop them all",
                    "It opens a window of the Terminal, which shows lines in English and stops when it is done",
                    "either answer works",
                    "it is usually because the Python Launcher that came with the older Python takes the `py` command",
                    "from what you have not done yet",
                    "which you can make for free",
                    "**Does the tracked synthetic fixture reproduce the problem?**: choose **Not tested**",
                    f"the version that you were installing, {CURRENT_STABLE_VERSION}.",
                    "The line of this guide holds no name",
                    "paste what `python3 --version` or `py --version` showed, and write what you did",
                    "in a new window of the terminal, not the one where the GUI runs",
                ),
                "Start the GUI": ("the line of this guide alone does not make this command work",),
                "Start the GUI from an icon": (
                    "When you start the GUI from it, its window opens minimized",
                    "([When the icon could not be made](#when-the-icon-could-not-be-made))",
                    "the command of the Python of the virtual environment in [Start the GUI](#start-the-gui)",
                    "whose folder opens when you type `shell:programs`",
                    "When it stops again, tell us ([Tell us when the GUI does not open](#tell-us-when-the-gui-does-not-open))",
                    "The name of the icon is **Garmin Running Data Normalizer**",
                    "or move it to the Trash when you do not need it",
                ),
                "Go back to the GUI that is open": (
                    "when you do not know whether a normalization runs, use the address",
                    "the control key and C stops the GUI",
                    "so choose again from box 1",
                    "Once the earlier GUI has stopped, its address no longer opens it",
                    "the one with the normalization that runs if one runs",
                    "Quit the new GUI then, and go back to the earlier one with its address",
                    f'When the page says "{catalog("en")["status.unauthorized"]}", select all of the address again',
                    "Stop the GUI that you do not use with **Quit** on its page",
                ),
                "Stop the GUI": (
                    "when the icon started the GUI on Windows, the window closes by itself",
                    "a line that starts with `ERROR [RUN_CANCELLED`",
                ),
                "Remove this app": (
                    "write down the places that boxes 2 and 3 show: once the remembered settings are forgotten",
                    "The Exports that you downloaded",
                ),
                "If something is wrong": (
                    "When the GUI does not open, do as "
                    "[Tell us when the GUI does not open](#tell-us-when-the-gui-does-not-open) says",
                    "When you paste lines of the terminal in what happened, write other words in place of names",
                ),
            },
            "ja": {
                "用意するもの": (
                    "このアプリを先に入れて、画面の「使い方」を見てからリクエストしてもかまいません",
                    "（Windows では「認識されません」か「is not recognized」）",
                    "その窓では「インストール」を押さずに、何もしないで窓を閉じるボタンを押してから、2 に進みます",
                    "Python が安全なつながりに使う証明書を入れます",
                    "「Python 3.14」のような名前のフォルダーにあります",
                    "新しい PowerShell の窓を開いて、`py --version` を動かします",
                    "「インストールされているアプリ」は、Windows の設定の「アプリ」の中にあります（Windows 10 では「アプリと機能」）",
                    "アンインストールしてよいか分からないときは、そのままにして知らせてください",
                    "ターミナルの窓をすべて閉じてから（macOS では、メニューの「ターミナル」→「ターミナルを終了」で終えてから）開き直して",
                    "枠の右上のコピーのボタン（GitHub でこの手引きを見ているときに出ます。ほかで見ているときは、1 行を選んで写します）で写してから",
                    "どのバージョンでも、この 1 行を使えます",
                    "`ERROR [SHORTCUT_` で止まったときは、ごみ箱へ入れる要はありません",
                    "| Python 3.11 以降を入れてターミナルを開き直し、",
                    "| [アイコンを作れなかったとき](#アイコンを作れなかったとき)のコードごとのことをするか、",
                    f"[Issues]({issues}) で「New issue」を押し、「Bug report」の書式で知らせてください",
                    "GitHub のアカウントが要ります",
                    "画面の写しは添付しないでください",
                    "`COMPUTER` に書き換えます", "`FOLDER` に書き換えます",
                    "このアプリは、新しいバージョンが出ても知らせません",
                    "「Current stable release」に、いちばん新しいバージョンが書いてあります",
                    "GUI がいくつか開いているときは、すべて終えます",
                    "終わって止まったら、その窓は閉じてかまいません",
                    "どちらに答えてもかまいません",
                    "たいてい、古い Python と一緒に入った Python Launcher が `py` を受け持っています",
                    "まだしていない所から続けます",
                    "無料で作れます",
                    "「Not tested」を選びます",
                    f"入れようとしたバージョン（{CURRENT_STABLE_VERSION}）",
                    "手引きの 1 行には名前が入っていないので",
                    "`python3 --version`（Windows では `py --version`）が出した行と、したことを書きます",
                    "GUI を動かしている窓とは別の、新しい窓で",
                    "「GUI Guide」の横の「日本語」のリンク",
                ),
                "GUI を起動する": ("手引きの 1 行で入れただけでは、このコマンドは使えません",),
                "アイコンから起動する": (
                    "ショートカットから起動すると、窓は最小化されて",
                    "（[アイコンを作れなかったとき](#アイコンを作れなかったとき)）",
                    "仮想環境の Python のコマンド（`--create-shortcut` なし）で、GUI を開けます",
                    "`shell:programs` と入れて開くフォルダーの中にあります",
                    "もう一度動かしてまた止まるときは、知らせてください（[GUI を開けないときに知らせる](#gui-を開けないときに知らせる)）",
                    "アイコンの名前は「Garmin Running Data Normalizer」です",
                    "要らなければごみ箱へ入れてください",
                ),
                "開いている GUI に戻る": (
                    "実行中かどうか分からないときは、アドレスのほうにします",
                    "control キーと C を押すと、GUI が止まり、実行中の正規化も取り消されます",
                    "1 の箱から選び直します",
                    "前の GUI が止まったあとは、そのアドレスを貼っても開けません",
                    "実行中の正規化があるときは、その GUI を使います",
                    "新しい GUI を「終了」で終えて、前の GUI に、そのアドレスから戻ります",
                    f'「{catalog("ja")["status.unauthorized"]}」と出たときは、アドレスを端から端までもう一度写します',
                    "使わない GUI は、そのページの「終了」で終えます",
                ),
                "GUI を終える": (
                    "Windows でアイコンから起動したときは、窓が自分で閉じます",
                    "`ERROR [RUN_CANCELLED` で始まる行が出ます",
                ),
                "このアプリを片付ける": (
                    "2 と 3 の箱に出ている場所を書き留めます（覚えた設定を消すと、画面に出なくなるためです）",
                    "ダウンロードしたエクスポートの ZIP",
                ),
                "困ったとき": (
                    "GUI を開けないときは、[GUI を開けないときに知らせる](#gui-を開けないときに知らせる)のとおりにします",
                    "「何が起きたか」にターミナルの行を貼るときは",
                ),
            },
        }
        for language, sections in phrases.items():
            for heading, wanted in sections.items():
                text = flowing(language, heading)
                for phrase in wanted:
                    with self.subTest(language=language, heading=heading, phrase=phrase):
                        self.assertIn(phrase, text)

    def test_links_from_other_files_into_the_guides_find_their_headings(self) -> None:
        # The anchors of the guides that the README, the release notes, the
        # other documents, the code, the tests, and the scripts link to stay
        # when the guides change (v2.0.1 F1 made numbered steps of What you
        # need; the help panel of the GUI links to the files of the guides
        # only).
        def anchor(heading: str) -> str:
            return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")

        anchors = {
            path.name: {anchor(heading) for heading in re.findall(r"^#{1,6} (.+)$", path.read_text(encoding="utf-8"), re.M)}
            for path in GUIDES.values()
        }
        sources = [ROOT / "README.md", ROOT / "README.ja.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").rglob("*.md"))]
        sources += [
            path
            for folder in ("src", "tests", "scripts")
            for path in sorted((ROOT / folder).rglob("*"))
            if path.suffix in {".py", ".mjs", ".json", ".html"}
        ]
        found = []
        for path in sources:
            for name, fragment in re.findall(r"(gui_guide(?:\.ja)?\.md)#([^\s)\"'`>]+)", path.read_text(encoding="utf-8")):
                found.append((path.relative_to(ROOT).as_posix(), name, fragment))
        self.assertTrue(found)
        for source, name, fragment in found:
            with self.subTest(source=source, link=f"{name}#{fragment}"):
                self.assertIn(fragment, anchors[name])

    def test_guides_give_the_fixes_before_the_release_candidate_as_the_page_does(self) -> None:
        # Stage U1 of v2.2.0: the zero dot of a total recorded as 0, the words of
        # the name not used in the line at the top of the full screen, and the
        # focus of a press that cannot save, each tied to the code that does it
        # (the press and the way back from another view are held with the
        # saving and the shoes above).
        flow = (STATIC_ROOT / "view_flow.mjs").read_text(encoding="utf-8")
        page = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        chart = (STATIC_ROOT / "view_chart.mjs").read_text(encoding="utf-8")
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        says = {
            "en": (
                "drawn as a light point, as is a step whose recorded values add up to 0; before the first and after the last, it is empty, without a point. The 0 of a step without a record does not always mean that there was no run.",
                "where there are conditions, their words (not their numbers); where the names of the output could not be read and there are words of the name, the words end with **(the names could not be read, so the words of the name are not used)**.",
                "(but not while there is no panel); the line at the top of the full screen ends the words of the conditions with **(the names could not be read, so the words of the name are not used)**.",
                "the focus stays on **Save** where it can still be pressed, or goes to the title of the window where it cannot",
            ),
            "ja": (
                "記録の無い区切りが 0 になり、薄い点で出ます。記録された値の合計が 0 の区切りも、同じ点です。最初より前と最後より後は空で、点は出ません。記録の無い区切りの 0 は、「走らなかった」とは限りません。",
                "条件があれば条件の言葉が出ます（件数は出ません）。名前を読めない出力で名前の条件があるときは、条件の言葉のあとに「（名前を読めないので、名前の条件は使っていません）」と出ます。",
                "（段が 1 つも無いあいだは出ません）。全画面の上の 1 行では、条件の言葉のあとに「（名前を読めないので、名前の条件は使っていません）」と出ます。",
                "「保存」が押せるときは、フォーカスは「保存」に残り、押せないときは窓の題に移ります（[画像で保存](#画像で保存220-から)）。",
            ),
        }
        # What they said before, which is no longer so (Codex's review of the
        # plan of U1, 10: an assertion is rewritten, not added to).
        gone = {
            "en": ("0 means that nothing was recorded", "nor in the line at the top of the full screen"),
            "ja": ("0 は「記録が無い」ことで", "全画面の上の 1 行には出ません"),
        }
        quoted = {"en": "**{}**", "ja": "「{}」"}
        for language in ("en", "ja"):
            text = GUIDES[language].read_text(encoding="utf-8")
            reads = " ".join(text.split()) if language == "en" else re.sub(r"\n *", "", text)
            for phrase in says[language]:
                with self.subTest(language=language, phrase=phrase[:40]):
                    self.assertEqual(reads.count(phrase), 1)
            for phrase in gone[language]:
                with self.subTest(language=language, gone=phrase):
                    self.assertNotIn(phrase, reads)
            # The words quoted are those of the line under a picture, after the
            # words of the conditions, which the full screen shows too.
            words = catalog(language)
            unread = words["view.save.conditions_unread"].replace("{conditions}", "").strip()
            with self.subTest(language=language, part="quoted"):
                self.assertIn(quoted[language].format(unread), reads)
            # The help says the same of the zero dots.
            with self.subTest(language=language, part="help"):
                self.assertIn(
                    "; so is one whose recorded activities add up to 0." if language == "en" else "記録されたアクティビティの合計が 0 の区切りも、同じ点です。",
                    words["view.help.zero_text"],
                )
        # Every total of 0 is the same dot, recorded or not.
        self.assertIn("if (value !== 0) {\n      return;\n    }", function_body(chart, "zeroDots"))
        # The full screen: the line under a picture's words, for the answer of
        # the panels of the conditions of the page whose names were not read.
        self.assertIn(
            'return conditionsUnread(state.answer?.conditions ?? null, state.conditions) ? t("view.save.conditions_unread", { conditions: text }) : text;',
            function_body(page, "fullConditionsText"),
        )
        self.assertIn('conditions: state.conditions === null ? "" : fullConditionsText(),', page)
        # Its days, a dash where the answer has none (Codex's review of the diff
        # of U1, 1).
        self.assertIn("const days = fullDays(state.answer, state.language);", page)
        self.assertIn("        from: days.from,\n        to: days.to,\n", page)
        self.assertIn('return { from: "—", to: "—" };', function_body(flow, "fullDays"))
        self.assertIn(
            'return counts !== null && typeof counts === "object" && conditionsKey(counts.asked ?? null) === conditionsKey(conditions) && counts.name === "unread";',
            function_body(flow, "conditionsUnread"),
        )
        # The design document.
        for phrase in (
            "it is drawn as a light point, as is a period whose recorded values add up to 0. The 0 of a period without a record does not always mean that there was no run.",
            # From v2.3.0 the list gives it too (stage X9c-2), for the laps.
            "(`read`; from v2.3.0 also in those of `/api/view/activities` and `/api/view/laps`, which the page does not compare with that of the panels: the list gives it so that the laps of its rows are asked of the same reading)",
            "(`ONE_KEYS` and `countKey` of `i18n.mjs`, the same Japanese)",
            "that the words of the name were not used where the answer of the panels, of these conditions, says so (`conditionsUnread`).",
            "a press that can no longer save keeps no reason that the window says by itself (`saveSays`, `savePress`)",
            "and from v2.2.0 (stage U1) a dash for the period of an answer without its days (`fullDays`)",
        ):
            with self.subTest(design=phrase[:40]):
                self.assertEqual(design.count(phrase), 1)
        self.assertNotIn("0 means no record", design)


    def test_the_design_and_the_guides_say_what_x10_reads_and_writes(self) -> None:
        # Stage X10 of v2.3.0 (the checker's review of the guard, 1 and 2): the
        # design document says the new field of the list, the maximum heart
        # rate of the laps, and the factor of the cadence; the guides say that
        # the view page reads the FIT file of an activity in the store when its
        # laps are shown, in the four places that said that it reads outputs
        # only, and the words of the page too.
        design = " ".join((ROOT / "docs" / "gui_design.md").read_text(encoding="utf-8").split())
        for phrase in (
            "From stage X10, the list of a period gives with each row, besides `ref`, why the laps of that activity cannot be shown where the output alone tells it before a file is read (`laps_unavailable`): `key_shared` where the activity has no key or another activity has it too, else `not_from_store` where the manifest of the reading has no `snapshot/snapshot_lineage.json`, else `null`.",
            "(`elapsed_s`, `timer_s`, `distance_m`, `avg_heart_rate`, `max_heart_rate` from stage X10, `avg_cadence`, and `avg_speed`; none read anew from the store)",
            "in `ITEM_FORMATS` of `view_flow.mjs` it is the one item whose factor is not that of its unit (2),",
            "The answers of the server, the output, and the CSV file of `series` keep the values as recorded",
        ):
            with self.subTest(design=phrase[:40]):
                self.assertEqual(design.count(phrase), 1)
        said = {
            "ja": (
                # From stage X11, also when the work laps of the shoes are counted.
                "見るページは出力を読むだけで、書き換えません（2.3.0 からは、ラップを見るときと、靴ごとに疾走区間を数えるときだけ、保管場所の FIT ファイルも読みます）。",
                "見るページは出力を読むだけで、数字を外へ送りません（2.3.0 からは、ラップを見るときと、靴ごとに疾走区間を数えるときだけ、保管場所の FIT ファイルも読みます）。",
            ),
            "en": (
                "The view page only reads an output (from 2.3.0, also FIT files in the Snapshot Store, when the laps of an activity are shown or the work laps of the shoes are counted), and never changes it.",
                "The view page only reads an output (from 2.3.0, also FIT files in the Snapshot Store, when the laps of an activity are shown or the work laps of the shoes are counted), and sends no numbers anywhere.",
            ),
        }
        gone = {
            "ja": ("見るページは出力を読むだけで、書き換えません。", "見るページは出力を読むだけで、数字を外へ送りません。"),
            "en": ("The view page only reads an output, and never changes it.", "The view page only reads an output, and sends no numbers anywhere."),
        }
        for language in GUIDES:
            raw = GUIDES[language].read_text(encoding="utf-8")
            text = " ".join(raw.split()) if language == "en" else re.sub(r"\n *", "", raw)
            for sentence in said[language]:
                with self.subTest(language=language, said=sentence[:40]):
                    self.assertEqual(text.count(sentence), 1)
            for sentence in gone[language]:
                with self.subTest(language=language, gone=sentence[:40]):
                    self.assertNotIn(sentence, text)
        words = {
            language: json.loads((ROOT / "src/garmin_running_data_normalizer/gui/static/i18n" / f"{language}.json").read_text(encoding="utf-8"))["view.empty.latest_text"]
            for language in GUIDES
        }
        self.assertIn("この画面は出力（ラップを見るとき・疾走区間を数えるときは、保管場所の FIT ファイルも）を読むだけで、書き換えません。", words["ja"])
        self.assertIn("This page only reads the output (and, for the laps of an activity or the work laps of the shoes, FIT files in the Snapshot Store) and never changes them.", words["en"])

    def test_the_documents_and_the_guides_say_what_x11_reads(self) -> None:
        # Stage X11 of v2.3.0: the five documents that said that the view page
        # reads one FIT file for the laps of one activity also say the reading
        # of the work laps of the shoes, with its limits (the checker's review
        # of the samples, 1: the limits and the count said before reading);
        # the guides say how it counts, in both languages.
        def flat(name: str) -> str:
            return " ".join((ROOT / name).read_text(encoding="utf-8").split())

        held = {
            "docs/security_and_privacy_boundary.md": (
                "and only when the work laps of the shoes of a period are counted, after the page says how many activities it reads, the `store.json` and the FIT files of the activities with shoes of that period, in the same way: at most 5,000 activities in one counting, and in one request at most 100 activities and 32 MiB of FIT files.",
                "keeps nothing of a FIT file or of the sums after a request,",
            ),
            "docs/project/project_boundary.md": ("and, only when the work laps of the shoes of a period are counted, the FIT files of the activities with shoes of that period",),
            "docs/gui_design.md": (
                "### Work laps of the shoes (v2.3.0)",
                "until it has done 100 activities or the next FIT file would bring the bytes that it read past 32 MiB (by the size of the file as it was opened, before a byte of it is read;",
                "An activity of two pairs counts for each pair, with its distance, time, and heart rate.",
                # Whole numbers (Codex's eighth read of the diff of X11).
                "(all of them whole numbers: milliseconds, centimetres, and beats a minute times milliseconds, the units of the FIT file, so that the sums of the requests add up to those of one request exactly, wherever they end)",
                # A file read counts (Codex's read of the diff of X11, 1).
                "A FIT file that is read counts, whether or not it is then found as the output says.",
                "the answer of the shoes (`/api/view/shoes`) gives `work`: `{runs, known, limit, reason}`,",
                "and the FIT files of the activities with shoes of a period, only when the work laps of the shoes are counted",
                # The safety of the GUI says both readings of FIT files.
                "The view page reads outputs, and from v2.3.0 FIT files in the Snapshot Store that the GUI remembers (that of one activity when its laps are asked for, and those of the activities with shoes of a period when their work laps are counted), through the server only, and opens nothing outside the page.",
            ),
            "docs/architecture_overview.md": ("It also counts the work laps of the shoes of a period (`/api/view/shoes/work`):",),
            "docs/known_limitations.md": ("Laps of no known kind are never counted: a run with no work lap and some laps of no known kind is not counted,",),
        }
        for name, phrases in held.items():
            text = flat(name)
            for phrase in phrases:
                with self.subTest(document=name, phrase=phrase[:40]):
                    self.assertEqual(text.count(phrase), 1)
        said = {
            "ja": (
                "疾走区間は、時計が FIT ファイルに記録した区間の種類が「ラン」と「インターバル」のラップです。",
                "1 回に靴が 2 つ付いたランは、どちらの靴にも数えます。",
                "一度に数えられるのは、靴の付いたラン 5,000 回までです。",
                "（2.3.0 から）休みのラップを外した疾走区間（ラン・インターバル）の距離と平均ペースを靴ごとに見るときは、「疾走区間を数える…」を押し、「読む」を押します。",
            ),
            "en": (
                "The work laps are the laps whose kind, as the watch recorded it in the FIT file, is Active or Interval.",
                "A run with two pairs of shoes counts for each pair.",
                "One counting reads at most 5,000 runs with shoes.",
                "(From 2.3.0) To see the distance and the average pace of each pair over the work laps only (Active, Interval), without the rests, press **Count the work laps…**, then **Read**.",
            ),
        }
        for language in GUIDES:
            raw = GUIDES[language].read_text(encoding="utf-8")
            text = " ".join(raw.split()) if language == "en" else re.sub(r"\n *", "", raw)
            for sentence in said[language]:
                with self.subTest(language=language, said=sentence[:40]):
                    self.assertEqual(text.count(sentence), 1)

if __name__ == "__main__":
    unittest.main()
