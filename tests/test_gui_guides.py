from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests import test_gui_i18n


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "src/garmin_running_data_normalizer/gui/static"
GUIDES = {"en": ROOT / "docs/gui_guide.md", "ja": ROOT / "docs/gui_guide.ja.md"}
# The labels that the guides quote: bold in English, 「」 in Japanese.
QUOTED_LABELS = (
    "language.label",
    "input.label",
    "browse.button",
    "check.button",
    "output.parent",
    "output.name",
    "timezone.label",
    "pack.label",
    "run.start",
    "run.cancel",
    "output_check.heading",
    "open.folder",
    "open.start_here",
    "bundle.button",
    "quit.button",
)


def section(text: str, heading: str) -> str:
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


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

    def test_guides_say_that_the_gui_is_in_development(self) -> None:
        # Until the release candidate exposes the gui command (stage 5).
        english = GUIDES["en"].read_text(encoding="utf-8")
        japanese = GUIDES["ja"].read_text(encoding="utf-8")
        self.assertTrue(english.startswith("# GUI Guide\n\n> **In development for v2.0.0.**"))
        self.assertTrue(japanese.startswith("# GUI の手引き\n\n> **v2.0.0 に向けて開発中です。**"))
        self.assertIn("[日本語](gui_guide.ja.md)", english)
        self.assertIn("[English](gui_guide.md)", japanese)
        index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
        entry = re.search(r"^- \[v2\.0\.0 GUI Guide\]\(gui_guide\.md\).*?(?=^- |\Z)", index, re.M | re.S)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertIn("in development and not available yet", " ".join(entry.group(0).split()))

    def test_guides_describe_the_same_sections_and_codes(self) -> None:
        english = GUIDES["en"].read_text(encoding="utf-8")
        japanese = GUIDES["ja"].read_text(encoding="utf-8")
        self.assertEqual(english.count("\n## "), japanese.count("\n## "))
        codes = re.compile(r"^\| `([A-Z_]+)` \|", re.M)
        english_codes = codes.findall(section(english, "When something goes wrong"))
        self.assertEqual(english_codes, codes.findall(section(japanese, "うまくいかないとき")))
        # Only codes that the page can show.
        self.assertTrue(english_codes)
        self.assertLessEqual(set(english_codes), set(test_gui_i18n.flow_table("ERROR_KEYS")))
        commands = re.compile(r"^garmin-running-data-normalizer .*$", re.M)
        self.assertEqual(commands.findall(english), commands.findall(japanese))


if __name__ == "__main__":
    unittest.main()
