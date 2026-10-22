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

    def test_guides_say_that_the_gui_is_in_the_release_candidate(self) -> None:
        # The release candidate, such as v2.0.0rc1, has the gui command, and
        # the stable release does not (stage D2).
        english = GUIDES["en"].read_text(encoding="utf-8")
        japanese = GUIDES["ja"].read_text(encoding="utf-8")
        self.assertTrue(english.startswith("# GUI Guide\n\n> **Release candidate of v2.0.0.**"))
        self.assertTrue(japanese.startswith("# GUI の手引き\n\n> **v2.0.0 の試しのバージョンです。**"))
        # The note at the top names this release candidate, and no other
        # (stage D7).
        for language, text in (("en", english), ("ja", japanese)):
            with self.subTest(language=language):
                note = text.split("\n\n", 2)[1]
                self.assertEqual(set(re.findall(r"v\d+\.\d+\.\d+(?:a|b|rc)\d+", note)), {f"v{__version__}"})
        self.assertIn("[日本語](gui_guide.ja.md)", english)
        self.assertIn("[English](gui_guide.md)", japanese)
        index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
        entry = re.search(r"^- \[v2\.0\.0 GUI Guide\]\(gui_guide\.md\).*?(?=^- |\Z)", index, re.M | re.S)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertIn(
            f"in the release candidate v{__version__}, not in the stable release",
            " ".join(entry.group(0).split()),
        )

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
        # "&&", "if ($?) { … }" one inside the other, since an "if" that reads
        # $? leaves it true (stage E1i; WindowsPowerShellLineTest in
        # tests/test_shortcut.py runs the line). The places are quoted for a
        # home folder with spaces.
        found = {language: one_lines(language) for language in GUIDES}
        self.assertEqual(found["en"], found["ja"])
        (mac_language, mac), (windows_language, windows) = found["en"]
        self.assertEqual((mac_language, windows_language), ("bash", "powershell"))
        install = (
            "-m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "
            f"garmin-running-data-normalizer=={__version__}"
        )
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
                    "stop the GUI first", "request it early", "you add nothing yourself",
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
                    "先に GUI を終えて", "先にリクエストして", "自分で足すものはありません",
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


if __name__ == "__main__":
    unittest.main()
