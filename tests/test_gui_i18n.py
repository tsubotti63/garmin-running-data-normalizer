from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from garmin_running_data_normalizer.gui.server import LANGUAGES, STATIC_FILES


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "src/garmin_running_data_normalizer/gui/static"
MESSAGE_KEY = re.compile(r"[a-z]+(?:\.[a-z]+)+")
PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)\}")
DOUBLE_QUOTED = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def load_catalog(language: str) -> dict[str, str]:
    return json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.keys: set[str] = set()
        self.text: list[str] = []
        self.inline_scripts = 0
        self.styles: list[str] = []
        self.event_handlers: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("data-i18n"):
            self.keys.add(str(attributes["data-i18n"]))
        if tag == "script" and not attributes.get("src"):
            self.inline_scripts += 1
        if tag == "style" or "style" in attributes:
            self.styles.append(tag)
        self.event_handlers.extend(name for name in attributes if name.startswith("on"))

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())


def page() -> _PageParser:
    parser = _PageParser()
    parser.feed((STATIC_ROOT / "index.html").read_text(encoding="utf-8"))
    parser.close()
    return parser


def script_keys() -> set[str]:
    """Return the message keys that the page script uses as literal strings."""
    source = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
    return {
        literal for literal in DOUBLE_QUOTED.findall(source) if MESSAGE_KEY.fullmatch(literal)
    }


class GuiCatalogTest(unittest.TestCase):
    def test_catalog_files_match_the_supported_languages(self) -> None:
        self.assertEqual(LANGUAGES, ("en", "ja"))
        catalog_paths = {
            path for path in STATIC_FILES if path.startswith("/i18n/") and path.endswith(".json")
        }
        self.assertEqual(catalog_paths, {f"/i18n/{language}.json" for language in LANGUAGES})
        source = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        self.assertIn('const LANGUAGES = ["en", "ja"];', source)

    def test_catalogs_have_the_same_keys_and_placeholders(self) -> None:
        catalogs = {language: load_catalog(language) for language in LANGUAGES}
        english = catalogs["en"]
        for language, catalog in catalogs.items():
            with self.subTest(language=language):
                self.assertEqual(sorted(catalog), sorted(english))
                for key, message in catalog.items():
                    self.assertRegex(key, MESSAGE_KEY)
                    self.assertIsInstance(message, str)
                    self.assertTrue(message.strip(), key)
                    self.assertEqual(
                        sorted(PLACEHOLDER.findall(message)),
                        sorted(PLACEHOLDER.findall(english[key])),
                        key,
                    )

    def test_every_used_key_exists_and_every_key_is_used(self) -> None:
        used = page().keys | script_keys()
        catalog_keys = set(load_catalog("en"))
        self.assertEqual(sorted(used - catalog_keys), [], "keys missing from the catalogs")
        self.assertEqual(sorted(catalog_keys - used), [], "catalog keys that are never used")

    def test_language_names_are_written_in_their_own_language(self) -> None:
        self.assertEqual(load_catalog("en")["language.name"], "English")
        self.assertEqual(load_catalog("ja")["language.name"], "日本語")

    def test_page_has_no_text_inline_script_style_or_handler(self) -> None:
        parsed = page()
        self.assertEqual(parsed.text, [], "visible text must come from the catalogs")
        self.assertEqual(parsed.inline_scripts, 0)
        self.assertEqual(parsed.styles, [])
        self.assertEqual(parsed.event_handlers, [])


if __name__ == "__main__":
    unittest.main()
