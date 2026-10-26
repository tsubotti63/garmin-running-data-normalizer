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
from garmin_running_data_normalizer.diagnostics import doctor
from garmin_running_data_normalizer.diagnostics.contracts import (
    SAFE_WARNING_CODES,
    interpretation_for_status,
)
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input
from garmin_running_data_normalizer.gui.runs import RUN_STATUSES
from garmin_running_data_normalizer.gui.server import LANGUAGES, STATIC_FILES
from garmin_running_data_normalizer.gui.stores import ANSWER_CODES
from garmin_running_data_normalizer.run_all import PROGRESS_STAGES, PROGRESS_STEPS, run_all
from garmin_running_data_normalizer.snapshot.lifecycle import SNAPSHOT_PROGRESS_STAGES
from garmin_running_data_normalizer.stops import NEXT_ACTIONS, PAGE_MIX_WORDING, PAGE_STOPS, PAGE_WORDING, STOPS


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


def flow_entries(name: str) -> dict[str, str | None]:
    """Return one table of flow.mjs with its entries that show nothing (null)."""
    source = (STATIC_ROOT / "flow.mjs").read_text(encoding="utf-8")
    match = re.search(rf"const {name} = \{{(.*?)\n\}};", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"flow.mjs has no table {name}")
    return {
        key: None if value == "null" else value.strip('"')
        for key, value in re.findall(r'^\s+(\w+): ("[^"]+"|null),$', match.group(1), re.MULTILINE)
    }


def pre_run_findings() -> list[tuple[str, str, str]]:
    """The code, the message, and the next action of each finding that the
    pre-run check can give."""
    return re.findall(
        r'_finding\(\s*"([A-Z_]+)",.*?safe_message_id="([A-Z_]+)",\s*next_action_id="([A-Z_]+)"',
        inspect.getsource(doctor_input),
        re.DOTALL,
    )


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

    def test_texts_keep_the_corrections_of_the_mockup(self) -> None:
        # Stage B1b, from the checker's review of the mockup texts: exit code 0
        # does not say that every value is in the output, since files that no
        # dataset reads are not; and Snapshots are ordered by the times of
        # their Exports, not by when they were imported (merge rules v2.1).
        catalogs = {language: load_catalog(language) for language in LANGUAGES}
        for key in ("result.sub_pass_with_warnings", "info.exit_0"):
            with self.subTest(key=key):
                self.assertNotIn("値はすべて", catalogs["ja"][key])
                self.assertNotIn("every value", catalogs["en"][key])
        self.assertIn("エクスポートの日時の順", catalogs["ja"]["words.snapshot_text"])
        self.assertIn("ordered by the times of their exports", catalogs["en"]["words.snapshot_text"])
        # Only the fields whose values differ are left empty (stage A2), and
        # exit code 3 also comes from rows out of range (stage A3d-2a).
        self.assertIn("値の違う項目だけ", catalogs["ja"]["faq.values_a"])
        self.assertIn("only the fields whose values differ", catalogs["en"]["faq.values_a"])
        self.assertIn("範囲の外の行", catalogs["ja"]["info.exit_foot"])
        self.assertIn("out of range", catalogs["en"]["info.exit_foot"])

    def test_texts_keep_the_corrections_of_the_first_time_check(self) -> None:
        # Stage D6, after two new AI sessions used the page of v2.0.0rc1 with
        # no instructions: the page no longer says that it is in development
        # or that the command line is the reference, as both make the same
        # output.
        catalogs = {language: load_catalog(language) for language in LANGUAGES}
        self.assertNotIn("development", (STATIC_ROOT / "index.html").read_text(encoding="utf-8"))
        self.assertNotIn(".development", (STATIC_ROOT / "styles.css").read_text(encoding="utf-8"))
        for language, catalog in catalogs.items():
            with self.subTest(language=language):
                self.assertFalse([key for key, text in catalog.items() if "開発中" in text or "in development" in text])
        # The boxes stand in a row only on a wide window, so the help says
        # their numbers, not "from left to right".
        self.assertIn("番号の順", catalogs["ja"]["help.steps_lede"])
        self.assertIn("order of their numbers", catalogs["en"]["help.steps_lede"])
        # A warning of absent data says what to do, so that the next line,
        # which asks to read the warnings, reads well with it.
        self.assertNotIn("問題ではありません", catalogs["ja"]["warning.optional_family_not_present"])
        self.assertIn("使わないなら", catalogs["ja"]["warning.optional_family_not_present"])
        self.assertIn("If you do not use this data", catalogs["en"]["warning.optional_family_not_present"])
        # Of the absent families, those that add a warning are named under
        # the table: the daily families add none (docs/supported_datasets.md).
        for language, catalog in catalogs.items():
            for family in ("gear", "personal_records", "fit"):
                with self.subTest(language=language, family=family):
                    self.assertIn(catalog[f"family.{family}"], catalog["result.absent_note"])
        # A place to paste starts at the root, as the next step of the stop
        # says, in words that a person knows.
        for key in ("input.help", "stop.path_not_absolute"):
            with self.subTest(key=key):
                self.assertNotIn("いちばん上から", catalogs["ja"][key])
        self.assertNotIn("OS", catalogs["ja"]["open.requested"])
        # v2.0.1 F2: the tip of the fourth box names the button that shows the
        # output; the field of the timezone says that it has a list; and the
        # English words of opening agree with each other and with the
        # Japanese ones, "this computer".
        for language, catalog in catalogs.items():
            with self.subTest(language=language):
                quote = "“{}”" if language == "en" else "「{}」"
                self.assertIn(quote.format(catalog["open.folder"]), catalog["hint.run"])
        self.assertIn("from the list", catalogs["en"]["timezone.help"])
        self.assertIn("一覧から選んで", catalogs["ja"]["timezone.help"])
        self.assertIn("this computer", catalogs["en"]["open.requested"])
        self.assertEqual(catalogs["en"]["stop.open_failed"], "This computer could not open it.")
        # After Quit, the page says how to start the app again (v2.0.1 F2).
        for key in ("quit.text", "next_line.stopped"):
            with self.subTest(key=key):
                self.assertIn("start it from the icon or with the command", catalogs["en"][key].replace("this app", "it"))
                self.assertIn("アイコンかコマンドで起動します", catalogs["ja"][key])
        for key in ("open.requested", "stop.open_failed"):
            with self.subTest(key=key):
                self.assertNotIn("your computer", catalogs["en"][key])
                self.assertNotIn("The system", catalogs["en"][key])
                self.assertIn("このコンピューター", catalogs["ja"][key])

    def test_language_names_are_written_in_their_own_language(self) -> None:
        self.assertEqual(load_catalog("en")["language.name"], "English")
        self.assertEqual(load_catalog("ja")["language.name"], "日本語")

    def test_page_has_no_text_inline_script_style_or_handler(self) -> None:
        parsed = page()
        self.assertEqual(parsed.text, [], "visible text must come from the catalogs")
        self.assertEqual(parsed.inline_scripts, 0)
        self.assertEqual(parsed.styles, [])
        self.assertEqual(parsed.event_handlers, [])

    def test_page_scripts_change_text_without_markup(self) -> None:
        # Paths and names from the computer reach the page; it sets them with
        # textContent only, so that none of them is read as HTML (stage B1a).
        for script in sorted(STATIC_ROOT.glob("*.mjs")):
            source = script.read_text(encoding="utf-8")
            for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
                with self.subTest(script=script.name, sink=sink):
                    self.assertNotIn(sink, source)


def sentence(text: str) -> str:
    """The words of a table as the page writes them: a capital first, and a
    full stop at the end."""
    text = text[0].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else f"{text}."


class GuiStopWordsTest(unittest.TestCase):
    # Stage B2a: the English words of every stop on the page come from the
    # tables of stops.py; the Japanese words come from the text book of B0.

    def test_each_code_of_the_page_is_in_one_table(self) -> None:
        codes = set(flow_table("STOP_KEYS"))
        self.assertEqual(set(STOPS) & set(PAGE_STOPS), set())
        for code in codes:
            with self.subTest(code=code):
                self.assertTrue((code in STOPS) != (code in PAGE_STOPS))
        # The page's tables hold only codes that the page shows, and its
        # wording only codes of the CLI's table.
        self.assertLessEqual(set(PAGE_STOPS), codes)
        self.assertLessEqual(set(PAGE_WORDING), set(STOPS) & codes)

    def test_the_english_words_of_the_page_come_from_the_tables(self) -> None:
        english = load_catalog("en")
        whats = flow_table("STOP_KEYS")
        next_steps = flow_table("STOP_NEXT_KEYS")
        for code in whats:
            stop = PAGE_WORDING.get(code) or STOPS.get(code) or PAGE_STOPS[code]
            with self.subTest(code=code):
                self.assertEqual(english[whats[code]], sentence(stop.what))
                self.assertEqual(english[next_steps[code]], sentence(stop.next_step))
        # The cases of a mix that have words of their own (stage B4b-2).
        mixes, mix_steps = flow_table("MIX_KEYS"), flow_table("MIX_NEXT_KEYS")
        self.assertEqual(set(mixes), set(PAGE_MIX_WORDING))
        self.assertEqual(set(mix_steps), set(PAGE_MIX_WORDING))
        for kind, stop in PAGE_MIX_WORDING.items():
            with self.subTest(mix=kind):
                self.assertEqual(english[mixes[kind]], sentence(stop.what))
                self.assertEqual(english[mix_steps[kind]], sentence(stop.next_step))


class GuiMessageCoverageTest(unittest.TestCase):
    def test_every_error_code_has_a_message(self) -> None:
        codes = (
            codes_in("run_all.py", r'RunAllError\(\s*"([A-Z_]+)"')
            # The codes of the place of the output, which Run-All and the GUI
            # check alike (stage A3d-3a).
            | codes_in("output_location.py", r'\n    "(OUTPUT_[A-Z_]+)": ')
            | codes_in("common/time.py", r'"(TIMEZONE_[A-Z_]+)"')
            | codes_in("gui/runs.py", r'RunRequestError\("([A-Z_]+)"\)')
            | codes_in("gui/runs.py", r'super\(\)\.__init__\("([A-Z_]+)"\)')
            | codes_in("gui/runs.py", r'absolute_path\([^,]+, "([A-Z_]+)"\)')
            | codes_in("gui/server.py", r'absolute_path\([^,]+, "([A-Z_]+)"\)')
            | codes_in("gui/folders.py", r'FolderError\("([A-Z_]+)"\)')
            | codes_in("gui/chooser.py", r'ChooserError\("([A-Z_]+)"\)')
            | codes_in("gui/chooser.py", r'_failed\("([A-Z_]+)"\)')
            | codes_in("gui/server.py", r'ApiError\(HTTPStatus\.[A-Z_]+, "([A-Z_]+)"\)')
            | codes_in("gui/run_worker.py", r'"code": "([A-Z_]+)"')
            # A Snapshot run of the page (stage B4b-1) stops with the codes of
            # the CLI's snapshot commands: those of the Snapshot Store, and for
            # an error that no code describes, that of Run-All or of the
            # registration.
            | codes_in("snapshot/store.py", r'"(SNAPSHOT_[A-Z_]+)"')
            | codes_in("snapshot/merge.py", r'"(SNAPSHOT_[A-Z_]+)"')
            | codes_in("gui/run_worker.py", r'"([A-Z_]+_FAILED)"')
            | codes_in("gui/outputs.py", r'OutputActionError\("([A-Z_]+)"\)')
            # The checks of an output, which the view page shares, and what
            # the view page reads (stage G1).
            | codes_in("output_check.py", r'OutputActionError\("([A-Z_]+)"\)')
            | codes_in("view/data.py", r'OutputActionError\("([A-Z_]+)"\)')
            | codes_in("diagnostics/doctor.py", r'DoctorError\(\s*"([A-Z_]+)"')
            | codes_in("diagnostics/support_bundle.py", r'SupportBundleError\(\s*"([A-Z_]+)"')
            # The answers of the Snapshot Store (stage B4a).
            | set(ANSWER_CODES)
        )
        # Exactly the codes that can occur: none without a message, none stale.
        self.assertEqual(sorted(codes), sorted(flow_table("STOP_KEYS")))

    def test_every_error_message_has_a_next_step(self) -> None:
        whats = flow_table("STOP_KEYS")
        next_steps = flow_table("STOP_NEXT_KEYS")
        self.assertEqual(sorted(next_steps), sorted(whats))
        self.assertTrue(all(key.startswith("stop.") for key in whats.values()))
        self.assertTrue(all(step.startswith("stop_next.") for step in next_steps.values()))

    def test_output_actions_pass_on_codes_from_doctor_and_the_bundle_only(self) -> None:
        # The test above collects the codes of these two errors; any other
        # error passed on as it is would need its codes collected as well.
        # A Support Bundle of an output that another version made also passes
        # on that version (stage B5b).
        # The checks moved to output_check.py, and the view page passes on
        # the code of the timezone data, which common/time.py gives (stage G1).
        sources = {
            name: (SOURCE / name).read_text(encoding="utf-8")
            for name in ("gui/outputs.py", "output_check.py", "view/data.py")
        }
        self.assertEqual(
            {
                name: re.findall(
                    r"except (\w+) as exc:\n\s+raise OutputActionError\(exc\.code(?:, _made_by\(exc\))?\)", source
                )
                for name, source in sources.items()
            },
            {
                "gui/outputs.py": ["SupportBundleError"],
                "output_check.py": ["DoctorError"],
                "view/data.py": ["TimezoneDataUnavailableError"],
            },
        )
        self.assertEqual(
            sum(len(re.findall(r"OutputActionError\(exc\.code[,)]", source)) for source in sources.values()), 3
        )

    def test_every_progress_stage_and_step_has_a_message(self) -> None:
        # The stages of a Snapshot run come before and after those of Run-All
        # (stage B4b-1).
        self.assertEqual(set(flow_table("STAGE_KEYS")), set(PROGRESS_STAGES) | set(SNAPSHOT_PROGRESS_STAGES))
        self.assertEqual(set(flow_table("STEP_KEYS")), set(PROGRESS_STEPS))

    def test_every_pre_run_finding_has_a_message(self) -> None:
        # Stage B2b: a finding has words of its own message, and the next
        # step of the stop of its code, as the CLI's Doctor gives it; only
        # the findings whose code is not a stop take the next step of their
        # next action.
        findings = pre_run_findings()
        source = inspect.getsource(doctor_input)
        self.assertEqual(len(findings), source.count("_finding("))
        self.assertEqual({message for _code, message, _action in findings}, set(flow_entries("FINDING_KEYS")))
        stop_steps = flow_table("STOP_NEXT_KEYS")
        actions = flow_entries("ACTION_KEYS")
        self.assertEqual(
            {action for code, _message, action in findings if code not in STOPS}, set(actions)
        )
        english = load_catalog("en")
        for code, message, action in findings:
            with self.subTest(code=code, message=message):
                if code in STOPS:
                    self.assertIn(code, stop_steps)
                elif actions[action] is not None:
                    self.assertEqual(english[actions[action]], sentence(NEXT_ACTIONS[action]))
        # A finding that is a stop says what the stop says, unless its code
        # covers more than one finding.
        whats = flow_table("STOP_KEYS")
        messages = flow_table("FINDING_KEYS")
        for code, message, _action in findings:
            shared = sum(1 for other, *_rest in findings if other == code) > 1
            if code in STOPS and not shared:
                with self.subTest(message=message):
                    self.assertEqual(messages[message], whats[code])

    def test_every_post_run_doctor_value_has_a_message(self) -> None:
        self.assertEqual(
            {interpretation_for_status(status)["usability_scope"] for status in RUN_STATUSES},
            set(flow_table("USABILITY_KEYS")),
        )
        source = inspect.getsource(doctor._base)
        next_actions = dict(
            re.findall(
                r'product_status == "([A-Z_]+)":.*?doctor_next_action_id = "([A-Z_]+)"',
                source,
                re.DOTALL,
            )
        )
        self.assertEqual(set(next_actions), set(RUN_STATUSES))
        self.assertEqual(set(next_actions.values()), set(flow_table("NEXT_ACTION_KEYS")))
        # The page gives the next step in the words of the CLI's Doctor
        # (stage B2b).
        english = load_catalog("en")
        for action, key in flow_table("NEXT_ACTION_KEYS").items():
            with self.subTest(action=action):
                self.assertEqual(english[key], sentence(NEXT_ACTIONS[action]))
        self.assertEqual(set(SAFE_WARNING_CODES), set(flow_table("WARNING_KEYS")))

    def test_a_warning_says_a_count_only_where_the_run_gives_one(self) -> None:
        # Stage B2c: the words of a warning hold its count only for a code
        # whose every warning in a run has one; each names its family or
        # group and its code.
        source = (SOURCE / "run_all.py").read_text(encoding="utf-8")
        blocks = re.findall(r"warnings\.append\(\s*\{(.*?)\}\s*\)", source, re.DOTALL)
        counted: dict[str, set[bool]] = {}
        for block in blocks:
            code = re.search(r'"code": "([A-Z_]+)"', block)
            assert code is not None, block
            counted.setdefault(code.group(1), set()).add('"count":' in block)
        self.assertEqual(sum(1 for _block in blocks), 21)
        catalogs = {language: load_catalog(language) for language in LANGUAGES}
        keys = flow_table("WARNING_KEYS")
        for code, key in keys.items():
            for language, catalog in catalogs.items():
                with self.subTest(code=code, language=language):
                    self.assertIn("{name}", catalog[key])
                    self.assertIn("{code}", catalog[key])
                    if "{count}" in catalog[key]:
                        self.assertEqual(counted.get(code, {True}), {True})
        for language, catalog in catalogs.items():
            self.assertIn("{name}", catalog["warning.other"])

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
