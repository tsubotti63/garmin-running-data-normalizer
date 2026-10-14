"""Text with a lone UTF-16 surrogate, such as a truncated emoji, is written with
U+FFFD in its place as its file is read, and the run counts the texts and names
repaired by file, alike in one-shot and Snapshot runs (stage A3d-2c-1)."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output  # noqa: F401
from garmin_running_data_normalizer.common.text import (
    REPLACEMENT_CHARACTER,
    may_hold_lone_surrogates,
    repair_text,
)
from garmin_running_data_normalizer.diagnostics.detector import json_read_by_run_all
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.intake.discovery import (
    DiscoveredAsset,
    parse_json_asset,
    repaired_text_count,
)
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.runner import GoldenPathError, run_activities
from garmin_running_data_normalizer.snapshot import initialize_store, run_snapshot_all
from garmin_running_data_normalizer.snapshot.policies import MERGE_RULES_VERSION
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, gear, load
from tests.test_snapshot_unreadable_files import one_snapshot, register

LONE = "\ud83d"
ACTIVITIES = "DI-Connect-Fitness/synthetic_summarizedActivities.json"
GEAR = "DI-Connect-Fitness/synthetic_gear.json"
HISTORY = "DI-Connect-Metrics/TrainingHistory_1.json"
LACTATE = "DI-Connect-Wellness/synthetic_userBioMetrics.json"


def activities(*rows: dict[str, Any], **wrapper: Any) -> list[dict[str, Any]]:
    return [{"summarizedActivitiesExport": list(rows), **wrapper}]


BASE = {ACTIVITIES: activities(_activity("A1"), _activity("A2"))}


def export(root: Path, name: str, files: dict[str, Any]) -> Path:
    """An Export whose JSON files write every other character as an ASCII
    escape, as JSON allows, so that a lone surrogate can be written."""
    source = root / name
    for relative, value in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)
        path.write_text(text, encoding="ascii")
    return source


def asset(name: str, text: str, leave_out: Any = None) -> DiscoveredAsset:
    data = text.encode("utf-8")
    return DiscoveredAsset(
        "json", name, None, len(data), hashlib.sha256(data).hexdigest(), data, leave_out=leave_out
    )


def outcome(output: Path) -> dict[str, Any]:
    """What a run gives for repaired text, whatever the form of the run."""
    summary = load(output / "run_summary.json")
    manifest = load(output / "run_manifest.json")
    return {
        "status": summary["status"],
        "warnings": sorted(
            (item["code"], item.get("family", ""), item.get("count", 1))
            for item in summary["warnings"]
            if item["code"] not in {"OPTIONAL_FAMILY_NOT_PRESENT", "OPTIONAL_FAMILY_EMPTY"}
        ),
        "repaired_text_counts": {
            family: result["repaired_text_count"]
            for family, result in summary["family_results"].items()
            if "repaired_text_count" in result
        },
        "candidate_warning_count": summary.get("candidate_warning_count", 0),
        "files": sorted(
            (item["source_path"].rsplit("/", 1)[-1], item["family"], item["repaired_text_count"])
            for item in manifest.get("files_with_repaired_text", [])
        ),
        "activities": load(output / "normalized/activities.json"),
        "gear": load(output / "normalized/gear.json"),
        "training_history": load(output / "normalized/training_history_daily.json"),
    }


def both_forms(test: unittest.TestCase, root: Path, source: Path, name: str) -> Path:
    """Run one Export once and as one Snapshot; check that they agree, and
    return the output of the one-shot run."""
    one_shot = root / f"{name}-one-shot"
    run_all(source, one_shot)
    snapshot = one_snapshot(root, source, f"{name}-snapshot")
    expected = outcome(one_shot)
    actual = outcome(snapshot)
    for table in ("activities", "gear", "training_history"):
        # Provenance names the Snapshot's own files.
        for rows in (expected[table], actual[table]):
            for row in rows:
                for field in [field for field in row if field.startswith("source_")]:
                    del row[field]
    test.assertEqual(actual, expected)
    snapshot_files = load(snapshot / "run_manifest.json").get("files_with_repaired_text", [])
    test.assertEqual({item["snapshot"] for item in snapshot_files}, {1} if snapshot_files else set())
    return one_shot


class TextRuleTest(unittest.TestCase):
    def test_lone_surrogates_are_replaced_and_counted(self) -> None:
        cases = (
            ("a" + LONE, ("a" + REPLACEMENT_CHARACTER, 1)),
            (LONE + "b" + "\ude00", (REPLACEMENT_CHARACTER + "b" + REPLACEMENT_CHARACTER, 1)),
            (["x", "y" + LONE, {"z": LONE}], (["x", "y" + REPLACEMENT_CHARACTER, {"z": REPLACEMENT_CHARACTER}], 2)),
            ({"k" + LONE: "v" + LONE}, ({"k" + REPLACEMENT_CHARACTER: "v" + REPLACEMENT_CHARACTER}, 2)),
            ("plain \U0001f600 text", ("plain \U0001f600 text", 0)),
            ([1, 2.5, None, True], ([1, 2.5, None, True], 0)),
        )
        for value, expected in cases:
            with self.subTest(value=ascii(value)):
                self.assertEqual(repair_text(value), expected)

    def test_names_that_read_alike_once_repaired_keep_the_later_value(self) -> None:
        repaired, count = repair_text({"a" + LONE: 1, "a" + REPLACEMENT_CHARACTER: 2})
        self.assertEqual(repaired, {"a" + REPLACEMENT_CHARACTER: 2})
        self.assertEqual(count, 1)
        repaired, count = repair_text({"a" + REPLACEMENT_CHARACTER: 1, "a" + LONE: 2})
        self.assertEqual(repaired, {"a" + REPLACEMENT_CHARACTER: 2})
        self.assertEqual(count, 1)

    def test_escapes_of_surrogates_are_found_in_small_and_capital_digits(self) -> None:
        self.assertTrue(may_hold_lone_surrogates('["\\ud83d"]'))
        self.assertTrue(may_hold_lone_surrogates('["\\uD83D"]'))
        self.assertTrue(may_hold_lone_surrogates('["\\uDE00"]'))
        self.assertFalse(may_hold_lone_surrogates('["\\u00e9", "\\uabcd", "plain"]'))

    def test_the_files_that_run_all_reads(self) -> None:
        for name, read in (
            ("DI-Connect-Fitness/x_summarizedActivities.json", True),
            ("DI-Connect-Fitness/x_summarizedactivities.json", True),
            ("DI-Connect-Aggregator/UDSFile_1.json", True),
            ("DI-Connect-Wellness/x_userBioMetrics.json", True),
            ("DI-Connect-Fitness/x_unknown.json", False),
        ):
            with self.subTest(name=name):
                self.assertEqual(json_read_by_run_all(name), read)


class ReadingTest(unittest.TestCase):
    def test_a_file_counts_once_however_often_it_is_read(self) -> None:
        item = asset("x_summarizedActivities.json", '[{"name": "Run \\uD83D", "note": "\\ud83d\\ud83d"}]')
        self.assertIsNone(item.repaired_text_count)
        for _ in range(3):
            readable, value = parse_json_asset(item)
            self.assertTrue(readable)
            self.assertEqual(value, [{"name": "Run �", "note": "��"}])
        self.assertEqual(item.repaired_text_count, 2)
        self.assertEqual(repaired_text_count(item), 2)

    def test_a_file_that_no_dataset_parsed_is_read_for_the_count_only(self) -> None:
        left_out: list[Any] = []
        unread = asset("x.json", '{"name": "\\ud83d"}', leave_out=lambda *item: left_out.append(item))
        self.assertEqual(repaired_text_count(unread), 1)
        broken = asset("y.json", '{"name": ', leave_out=lambda *item: left_out.append(item))
        self.assertEqual(repaired_text_count(broken), 0)
        self.assertEqual(left_out, [])


class RepairedTextRunTest(unittest.TestCase):
    def test_repaired_text_in_each_place(self) -> None:
        cases = {
            "an activity name": (
                {ACTIVITIES: activities(_activity("A1", name="Run " + LONE), _activity("A2"))},
                [("activities", 1)],
            ),
            "an activity field that no table uses": (
                {ACTIVITIES: activities(_activity("A1", unusedNote="x" + LONE), _activity("A2"))},
                [("activities", 1)],
            ),
            "the wrapper of the records": (
                {ACTIVITIES: activities(_activity("A1"), _activity("A2"), note=LONE)},
                [("activities", 1)],
            ),
            "a name of a field": (
                {ACTIVITIES: activities(_activity("A1", **{"k" + LONE: 1}), _activity("A2"))},
                [("activities", 1)],
            ),
            "a Gear name": (
                {**BASE, GEAR: [{"gearDTOS": [gear(1, "Shoe " + LONE)]}]},
                [("gear", 1)],
            ),
            "a daily text value": (
                {
                    **BASE,
                    HISTORY: [
                        {
                            "calendarDate": "2030-02-01",
                            "timestamp": "2030-02-01T06:00:00",
                            "trainingStatus": "PEAKING" + LONE,
                        }
                    ],
                },
                [("training_history", 1)],
            ),
            "two texts of one file and an escape in capital digits": (
                {ACTIVITIES: '[{"summarizedActivitiesExport": ['
                 + json.dumps(_activity("A1", name="x"))[:-1] + ', "name": "Run \\uD83D"},'
                 + json.dumps(_activity("A2", name="y" + LONE)) + "]}]"},
                [("activities", 2)],
            ),
        }
        for name, (files, expected) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = both_forms(self, root, export(root, "export", files), "run")
                result = outcome(output)
                self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
                self.assertEqual(
                    [(family, count) for code, family, count in result["warnings"] if code == "DATA_TEXT_REPAIRED"],
                    expected,
                )
                self.assertEqual(result["repaired_text_counts"], dict(expected))
                self.assertEqual([(family, count) for _file, family, count in result["files"]], expected)
                for path in output.rglob("*.json"):
                    # Every output file is UTF-8 and strict JSON.
                    json.loads(path.read_bytes().decode("utf-8"))

    def test_the_repaired_text_is_written_with_u_fffd(self) -> None:
        files = {ACTIVITIES: activities(_activity("A1", name="Run " + LONE), _activity("A2"))}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export(root, "export", files), "run")
            names = {row["activity_id"]: row["name"] for row in load(output / "normalized/activities.json")}
            self.assertEqual(names["A1"], "Run �")
            text = (output / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("- Text repaired: 1 (`activities` 1)", text)

    def test_lactate_threshold_files_give_a_candidate_warning(self) -> None:
        files = {
            **BASE,
            LACTATE: [
                {
                    "lactateThresholdHeartRate": 166,
                    "metaData": {"calendarDate": "2030-02-01", "sequence": 1},
                    "note": LONE,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export(root, "export", files), "run")
            result = outcome(output)
            self.assertIn(("DATA_TEXT_REPAIRED", "lactate_threshold", 1), result["warnings"])
            self.assertEqual(result["repaired_text_counts"], {})

    def test_a_file_that_no_normalizer_parses_is_counted_alike(self) -> None:
        # The Activities family takes this name, which the one-shot Activities
        # normalizer does not read; a run counts its text as the build does.
        files = {
            **BASE,
            "DI-Connect-Fitness/extra_summarizedactivities.json": [
                {"summarizedActivitiesExport": [], "note": LONE}
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export(root, "export", files), "run")
            self.assertEqual(
                outcome(output)["files"], [("extra_summarizedactivities.json", "activities", 1)]
            )

    def test_copies_and_two_snapshots(self) -> None:
        files = {
            ACTIVITIES: activities(_activity("A1", name="Run " + LONE), _activity("A2")),
            "DI-Connect-Fitness/copy/synthetic_summarizedActivities.json": activities(
                _activity("A1", name="Run " + LONE), _activity("A2")
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files)
            output = both_forms(self, root, source, "copies")
            self.assertEqual(outcome(output)["repaired_text_counts"], {"activities": 2})
            # A later Export with the same files and one more; the same Export
            # registered again would be no new Snapshot.
            later = export(root, "later", {**files, GEAR: [{"gearDTOS": [gear(1, "Shoe")]}]})
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source, "S1", 1)
            register(store, later, "S2", 2)
            snapshots = root / "snapshots"
            run_snapshot_all(store, snapshots)
            listed = load(snapshots / "run_manifest.json")["files_with_repaired_text"]
            # Listed by Snapshot number, as the files left out are.
            self.assertEqual(sorted(item["snapshot"] for item in listed), [1, 1, 2, 2])
            self.assertEqual(outcome(snapshots)["repaired_text_counts"], {"activities": 4})
            self.assertEqual(
                load(snapshots / "snapshot/canonical_merge_summary.json")["merge_rules_version"],
                MERGE_RULES_VERSION,
            )

    def test_the_support_bundle_and_the_safe_pack_carry_counts_only(self) -> None:
        files = {ACTIVITIES: activities(_activity("A1", name="Run " + LONE), _activity("A2"))}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files)
            output = root / "output"
            run_all(source, output, external_safe_pack=True)
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with zipfile.ZipFile(path) as archive:
                    for name in archive.namelist():
                        data = archive.read(name)
                        with self.subTest(archive=path.name, member=name):
                            self.assertNotIn(b"synthetic_summarizedActivities", data)
                            self.assertNotIn("Run �".encode(), data)

    def test_without_such_text_the_outputs_have_nothing_new(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = both_forms(self, root, export(root, "export", BASE), "plain")
            summary = load(output / "run_summary.json")
            self.assertNotIn("files_with_repaired_text", load(output / "run_manifest.json"))
            self.assertNotIn("DATA_TEXT_REPAIRED", {item["code"] for item in summary["warnings"]})
            self.assertFalse(
                any("repaired_text_count" in result for result in summary["family_results"].values())
            )

    def test_the_golden_path_stops(self) -> None:
        files = {ACTIVITIES: activities(_activity("A1", unusedNote="x" + LONE), _activity("A2"))}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root, "export", files)
            with self.assertRaisesRegex(GoldenPathError, "broken character"):
                run_activities(source, root / "golden")
            self.assertFalse((root / "golden").exists())


if __name__ == "__main__":
    unittest.main()
