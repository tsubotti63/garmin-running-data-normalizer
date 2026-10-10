from __future__ import annotations

import inspect
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

# Import the diagnostics package before modules that import standalone:
# the other order meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input
from garmin_running_data_normalizer.gui.server import LANGUAGES, STATIC_FILES
from garmin_running_data_normalizer.run_all import PROGRESS_STAGES, PROGRESS_STEPS, run_all


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/garmin_running_data_normalizer"
STATIC_ROOT = SOURCE / "gui/static"
MESSAGE_KEY = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+")
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
    """Return the message keys that the page scripts use as literal strings."""
    keys: set[str] = set()
    for script in sorted(STATIC_ROOT.glob("*.mjs")):
        source = script.read_text(encoding="utf-8")
        keys.update(
            literal
            for literal in DOUBLE_QUOTED.findall(source)
            if MESSAGE_KEY.fullmatch(literal)
        )
    return keys


def flow_table(name: str) -> dict[str, str]:
    """Return one code-to-message-key table from flow.mjs."""
    source = (STATIC_ROOT / "flow.mjs").read_text(encoding="utf-8")
    match = re.search(rf"const {name} = \{{(.*?)\n\}};", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"flow.mjs has no table {name}")
    return dict(re.findall(r'^\s+(\w+): "([^"]+)",$', match.group(1), re.MULTILINE))


def codes_in(relative: str, pattern: str) -> set[str]:
    return set(re.findall(pattern, (SOURCE / relative).read_text(encoding="utf-8")))


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


class GuiMessageCoverageTest(unittest.TestCase):
    def test_every_error_code_has_a_message(self) -> None:
        codes = (
            codes_in("run_all.py", r'RunAllError\(\s*"([A-Z_]+)"')
            | codes_in("common/time.py", r'"(TIMEZONE_[A-Z_]+)"')
            | codes_in("gui/runs.py", r'RunRequestError\("([A-Z_]+)"\)')
            | codes_in("gui/runs.py", r'super\(\)\.__init__\("([A-Z_]+)"\)')
            | codes_in("gui/runs.py", r'absolute_path\([^,]+, "([A-Z_]+)"\)')
            | codes_in("gui/server.py", r'absolute_path\([^,]+, "([A-Z_]+)"\)')
            | codes_in("gui/folders.py", r'FolderError\("([A-Z_]+)"\)')
            | codes_in("gui/server.py", r'ApiError\(HTTPStatus\.[A-Z_]+, "([A-Z_]+)"\)')
            | codes_in("gui/run_worker.py", r'"code": "([A-Z_]+)"')
        )
        # Exactly the codes that can occur: none without a message, none stale.
        self.assertEqual(sorted(codes), sorted(flow_table("ERROR_KEYS")))

    def test_every_progress_stage_and_step_has_a_message(self) -> None:
        self.assertEqual(set(flow_table("STAGE_KEYS")), set(PROGRESS_STAGES))
        self.assertEqual(set(flow_table("STEP_KEYS")), set(PROGRESS_STEPS))

    def test_every_pre_run_finding_has_a_message(self) -> None:
        source = inspect.getsource(doctor_input)
        self.assertEqual(
            set(re.findall(r'safe_message_id="([A-Z_]+)"', source)),
            set(flow_table("FINDING_KEYS")),
        )
        self.assertEqual(
            set(re.findall(r'next_action_id="([A-Z_]+)"', source)),
            set(flow_table("ACTION_KEYS")),
        )

    def test_every_family_and_family_status_has_a_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_all(ROOT / "examples/synthetic/garmin_export", Path(directory) / "output")
        self.assertEqual(set(result["family_results"]), set(flow_table("FAMILY_KEYS")))
        source = (SOURCE / "run_all.py").read_text(encoding="utf-8")
        start = source.index("def _family_results(")
        body = source[start : source.index("\ndef ", start)]
        statuses = set(re.findall(r'"(PROCESSED[A-Z_]*|SKIPPED_[A-Z_]+|PARTIAL)"', body))
        self.assertEqual(statuses, set(flow_table("FAMILY_STATUS_KEYS")))


if __name__ == "__main__":
    unittest.main()
