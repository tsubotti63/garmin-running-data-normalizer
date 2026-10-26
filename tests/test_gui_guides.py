from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

# The guides of main are read by the users of the stable release, through the
# README, so they name and install the release that is published, which the
# product state knows, also while the source is a release candidate, whose
# procedure gives its own line (v2.0.1 F4; decision 20261024-4).
from scripts.validate_public_product_state import CURRENT_STABLE_VERSION
from tests import test_gui_i18n


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
            },
            "ja": {
                "how.single_note": "2 の箱：スナップショット",
                "run.again_note": "4 の箱：正規化",
                "run.again_same_export": "4 の箱：正規化",
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
             "Run the line for Windows PowerShell in [What you need](#what-you-need) instead. There is nothing to "
             "move to the Recycle Bin."),
            ("ja", "| `'&&'` と、`有効なステートメント区切りではありません` か `is not a valid statement separator`（Windows） | "
                   "macOS の 1 行を Windows PowerShell 5.1 に貼りました。",
             "[用意するもの](#用意するもの)の Windows PowerShell の 1 行を、代わりに動かしてください。ごみ箱へ入れる物はありません。"),
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
                "When something goes wrong": ("double-click the icon again", "10 minutes"),
                "Stop the GUI": ("seems to stand still", '"GUI stopped."'),
                "Remove this app": (
                    "`shell:programs`", "`GarminRunningData`", "personal data",
                    "`pip uninstall garmin-running-data-normalizer`",
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
                "うまくいかないとき": ("アイコンをもう一度ダブルクリック", "10 分間"),
                "GUI を終える": ("止まって見えます", "「GUI stopped.」"),
                "このアプリを片付ける": (
                    "`shell:programs`", "`GarminRunningData`", "個人のデータ",
                    "`pip uninstall garmin-running-data-normalizer`",
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
                "add a folder to `PATH`", "the line below uses `py`",
                "When an older Python is installed already, `py` starts that one",
                "run `pymanager install default` in PowerShell",
                "remove the Python Launcher in **Installed apps**",
                "[python.org describes](https://docs.python.org/3/using/windows.html)",
                "Keep the Python install manager and Python 3.11 and later.",
                "When it still shows the older Python, remove Python 3.10 and earlier too",
            ),
            "ja": (
                "「Download Python install manager」", "「Install」を押して",
                "いちばん新しい Python が自動で入ります", "`PATH` にフォルダーを足すか", "下の 1 行は `py` を",
                "`py` はその古い Python を起動する", "`pymanager install default` を動かして",
                "「インストールされているアプリ」で Python Launcher を外し",
                "[python.org の説明](https://docs.python.org/3/using/windows.html)",
                "Python install manager と 3.11 以降の Python は残します",
                "それでも古い Python が出るときは、3.10 以前の Python も外して",
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
                    "follow its steps in [What you need](#what-you-need) until `py --version` shows 3.11 or later",
                ),
                "Start the GUI from an icon": ("**Show all filename extensions**", "the icon starts the new version"),
                "Go back to the GUI that is open": (
                    "A bookmark does not open the GUI", "one more GUI opens", "10 minutes",
                    "When no normalization runs, you may instead double-click the icon again", "the command key and C",
                    "right-click to copy it", "stops the GUI of that page only", "puts the tab to sleep",
                    "The earlier GUI has no page, and stops by itself after 10 minutes when no run is active",
                    "A GUI whose page you closed stops by itself after 10 minutes when no run is active",
                ),
                "Stop the GUI": ("the control key and C, on macOS too", "When no page is open for 10 minutes"),
                "When something goes wrong": ("because no page was open for 10 minutes",),
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
                    "[用意するもの](#用意するもの)の Windows の手順で、`py --version` が 3.11 以降と出るまで",
                ),
                "アイコンから起動する": ("「すべてのファイル名拡張子を表示」", "アイコンから新しいバージョンが起動します"),
                "開いている GUI に戻る": (
                    "ブックマークからは開けません", "GUI がもう 1 つ開きます", "10 分たつと",
                    "実行中の正規化が無いときは、代わりにアイコンをもう一度ダブルクリック", "command キーと C", "右クリックで写します",
                    "そのページの GUI だけが終わります", "タブを眠らせた",
                    "前の GUI は、ページが無いので、実行中でなければ、10 分たつと",
                    "閉じた GUI は、実行中でなければ、10 分たつと",
                ),
                "GUI を終える": ("macOS でも control キーと C", "どのページも開いていないまま 10 分たつと"),
                "うまくいかないとき": ("どのページも 10 分間開いていなかった",),
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
        # GUI stops, since only the page forgets them.
        for language, export, forget, stop in (
            ("en", "- A Garmin Account Data Export", "**Forget the remembered settings…**", "2. Stop the GUI"),
            ("ja", "- Garmin のエクスポート", "「覚えた設定を消す…」", "2. GUI を終えます"),
        ):
            with self.subTest(language=language):
                text = GUIDES[language].read_text(encoding="utf-8")
                need = section(text, WHAT_YOU_NEED[language])
                self.assertTrue(need.split("\n\n", 2)[1].startswith(export))
                remove = flowing(language, {"en": "Remove this app", "ja": "このアプリを片付ける"}[language])
                self.assertLess(remove.index(forget), remove.index(stop))

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
                    "`Ctrl+C` in that window can stop the GUI, and cancel a normalization that runs",
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
                    "This app does not need Python itself to be removed",
                    f"[macOS]({mac_doc})", f"[Windows]({windows_doc})",
                ),
            },
            "ja": {
                "用意するもの": (
                    "Windows のコマンドプロンプトでは動きません",
                    "「Install Certificates.command」をダブルクリックして、入れるのを終えます",
                    f"[python.org の説明]({mac_doc})",
                    "その窓で Ctrl+C を押すと、GUI が止まり、実行中の正規化も取り消されることがあります",
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
                    "ブラウザの履歴からも開けません",
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
                    "do not install them in that window (do not choose **Install** there), and go on to step 2",
                    "it installs the certificates that Python uses for secure connections",
                    "the folder named like **Python 3.14** in **Applications** of the Finder",
                    "open a new PowerShell window, and run `py --version`",
                    "**Installed apps** is under **Apps** in the Settings of Windows (**Apps & features** on Windows 10)",
                    "when you do not know whether you may remove it, keep it",
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
                    "write down the places that boxes 2 and 3 show before you forget them",
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
                    "その窓では入れずに（そこで「インストール」を押さずに）、2 に進みます",
                    "Python が安全なつながりに使う証明書を入れます",
                    "「Python 3.14」のような名前のフォルダーにあります",
                    "新しい PowerShell の窓を開いて、`py --version` を動かします",
                    "「インストールされているアプリ」は、Windows の設定の「アプリ」の中にあります（Windows 10 では「アプリと機能」）",
                    "外してよいか分からないときは、外さずに知らせてください",
                    "ターミナルの窓をすべて閉じてから（macOS では、メニューの「ターミナル」→「ターミナルを終了」で終えてから）開き直して",
                    "枠の右上のコピーのボタンで写してから",
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
                    "2 と 3 の箱に出ている場所を書き留めておきます",
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


if __name__ == "__main__":
    unittest.main()
