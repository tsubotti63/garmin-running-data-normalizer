from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from garmin_running_data_normalizer import __version__
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
# (stage E1e): the code blocks inside the list of what you need.
ONE_LINE = re.compile(r"^  ```(bash|powershell)\n  (.*)\n  ```$", re.M)
WHAT_YOU_NEED = {"en": "What you need", "ja": "用意するもの"}


def one_lines(language: str) -> list[tuple[str, str]]:
    return ONE_LINE.findall(section(GUIDES[language].read_text(encoding="utf-8"), WHAT_YOU_NEED[language]))


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

    def test_guides_say_that_the_gui_is_in_this_release(self) -> None:
        # The stable release v2.0.0 has the gui command, and v1.7.1 does not
        # (stage E2b; the release candidates said so for themselves from
        # stage D2).
        english = GUIDES["en"].read_text(encoding="utf-8")
        japanese = GUIDES["ja"].read_text(encoding="utf-8")
        self.assertTrue(english.startswith("# GUI Guide\n\n> **This guide is for v2.0.0.**"))
        self.assertTrue(japanese.startswith("# GUI の手引き\n\n> **v2.0.0 の手引きです。**"))
        # The note at the top names this release and v1.7.1, and no
        # pre-release (stage D7).
        for language, text in (("en", english), ("ja", japanese)):
            with self.subTest(language=language):
                note = text.split("\n\n", 2)[1]
                self.assertEqual(set(re.findall(r"v\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", note)), {f"v{__version__}", "v1.7.1"})
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
        install = f"-m pip install garmin-running-data-normalizer=={__version__}"
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
        # the line, which uses py, does not need.
        phrases = {
            "en": (
                "**Download Python install manager**", "choose **Install**",
                "as `py --version` does, installs the latest Python by itself",
                "add a folder to `PATH`", "the line below uses `py`",
            ),
            "ja": (
                "「Download Python install manager」", "「Install」を押して",
                "いちばん新しい Python が自動で入ります", "`PATH` にフォルダーを足すか", "下の 1 行は `py` を",
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
                    "| `No matching distribution found`, without the two lines above |",
                    "| A line that starts with `ERROR [SHORTCUT_` |",
                    "On macOS as on Windows, stop the GUI first", '"Unable to copy"', "the versions are mixed",
                    "stay as they are", "open a new PowerShell window", "the terminal is the window of PowerShell",
                    "a line that ends with %", "there is nothing to move",
                    "an old pip does not show the line of `Requires-Python`",
                    "[Report a problem on GitHub](#report-a-problem-on-github)",
                ),
                "Start the GUI from an icon": ("**Show all filename extensions**", "the icon starts the new version"),
                "Go back to the GUI that is open": (
                    "A bookmark does not open the GUI", "one more GUI opens", "10 minutes",
                    "the easiest is to double-click the icon again", "the command key and C",
                    "right-click to copy it", "stops the GUI of that page only", "puts the tab to sleep",
                ),
                "Stop the GUI": ("the control key and C, on macOS too",),
            },
            "ja": {
                "用意するもの": (
                    "「3.」のあとの数が 11 以上", "このアプリには古いことがあります", "`%USERPROFILE%`",
                    "「移動」→「ホーム」",
                    "| `command not found`（macOS）、`認識されません` か `is not recognized`（Windows） |",
                    "| `xcode-select`（macOS） |", "| `Requires-Python` |", "| `Retrying` と `connection` |",
                    "| `No matching distribution found`（上の 2 つが無いとき） |", "| `ERROR [SHORTCUT_` で始まる行 |",
                    "macOS でも Windows でも、先に GUI を終えて", "「Unable to copy」",
                    "バージョンが混ざります", "そのまま残ります", "PowerShell の窓を開き直して",
                    "Windows では PowerShell の窓のことです", "% で終わる行", "そのフォルダーが無ければ",
                    "古い pip は `Requires-Python` の行を出しません", "[GitHub で報告する](#github-で報告する)",
                ),
                "アイコンから起動する": ("「すべてのファイル名拡張子を表示」", "アイコンから新しいバージョンが起動します"),
                "開いている GUI に戻る": (
                    "ブックマークからは開けません", "GUI がもう 1 つ開きます", "10 分たつと",
                    "アイコンをもう一度ダブルクリックするのがかんたんです", "command キーと C", "右クリックで写します",
                    "そのページの GUI だけが終わります", "タブを眠らせた",
                ),
                "GUI を終える": ("macOS でも control キーと C",),
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


if __name__ == "__main__":
    unittest.main()
