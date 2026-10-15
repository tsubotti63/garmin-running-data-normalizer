"""Links whose endpoint is not in the output stay, unresolved, and Activities
and FIT sessions with more than one equally matching candidate are announced
(stage A4a).

A Personal Record or an ``activity_gear`` link whose valid link points to a
record that is not in the output stays in its table with that endpoint
unresolved and the reason, as a Personal Record whose link cannot be followed
has since stage A3d-1b. The relationship summary counts each endpoint of an
``activity_gear`` link by itself, as the statuses of the rows give it, and
warning ``RELATIONSHIP_UNRESOLVED_VALID_LINK`` keeps its count. Warning
``ACTIVITY_FIT_LINK_AMBIGUOUS`` gives the number of Activities and FIT sessions
whose candidates tie.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output  # noqa: F401
from garmin_running_data_normalizer.run_all import run_all
from tests.fit_fixture_factory import synthetic_fit
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_parity import differences, runs
from tests.test_snapshot_record_updates import gear, load, personal_record, write_export

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "src/garmin_running_data_normalizer/gui/static/i18n"
FLOW = ROOT / "src/garmin_running_data_normalizer/gui/static/flow.mjs"


def links_to_nothing(root: Path) -> Path:
    """An Export whose Gear links and Personal Records also point to
    Activities and Gear that it does not hold."""
    return write_export(
        root,
        "export",
        [_activity("A1"), _activity("A2")],
        gear_rows=[gear(1, "Synthetic Shoe")],
        links={"1": ["A1", "MISSING-1", "MISSING-0"], "9": ["A2", "MISSING-2"]},
        records=[
            personal_record(1, "A1", 1.0),
            personal_record(2, "MISSING-1", 2.0),
            personal_record(3, "0", 3.0),
        ],
    )


def warning_counts(output: Path, family: str) -> dict[str, Any]:
    return {
        item["code"]: item["count"]
        for item in load(output / "run_summary.json")["warnings"]
        if item.get("family") == family
    }


def fit_activity(activity_id: str) -> dict[str, Any]:
    """An Activity that starts with the session of the synthetic FIT file,
    with its sport, distance, and timer time."""
    return _activity(
        activity_id,
        startTimeGmt=632_065_600_000,
        startTimeLocal="1990-01-11T22:46:40",
        distance=1_000_000,
        duration=3_500_000,
    )


def fit_export(root: Path, activities: list[dict[str, Any]], files: dict[str, bytes]) -> Path:
    source = write_export(root, "export", activities)
    for name, data in files.items():
        path = source / "DI-Connect-Uploaded-Files" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return source


class UnresolvedLinksTest(unittest.TestCase):
    def test_links_and_records_stay_with_the_endpoint_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(links_to_nothing(root), output)
            summary = load(output / "run_summary.json")
            self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
            # The links of each Gear by their Activity; those whose Activity
            # is not in the output follow, by the activity identifier.
            self.assertEqual(
                [
                    (
                        row["gear_key"],
                        row["activity_id"],
                        row["garmin_activity_key"] is None,
                        row["activity_relationship_status"],
                        row["activity_relationship_reason"],
                        row["gear_relationship_status"],
                        row["gear_relationship_reason"],
                    )
                    for row in load(output / "normalized/activity_gear.json")
                ],
                [
                    (1, "A1", False, "explicit", "source_activity_id", "explicit", "source_gear_key"),
                    (1, "MISSING-0", True, "unresolved", "missing_activity_endpoint", "explicit", "source_gear_key"),
                    (1, "MISSING-1", True, "unresolved", "missing_activity_endpoint", "explicit", "source_gear_key"),
                    (9, "A2", False, "explicit", "source_activity_id", "unresolved", "missing_gear_endpoint"),
                    (9, "MISSING-2", True, "unresolved", "missing_activity_endpoint", "unresolved", "missing_gear_endpoint"),
                ],
            )
            self.assertEqual(
                [
                    (
                        row["personal_record_id"],
                        row["garmin_activity_key"] is None,
                        row["activity_relationship_status"],
                        row["activity_relationship_reason"],
                    )
                    for row in load(output / "normalized/personal_records.json")
                ],
                [
                    (1, False, "explicit", "source_activity_id"),
                    (2, True, "unresolved", "missing_activity_endpoint"),
                    (3, True, "independent", "non_activity_personal_record"),
                ],
            )
            # Each endpoint of a link is counted by itself in the entries of
            # activity_gear, whose eligible_count counts each link once. The
            # totals and the warning stay as before: relationship_unresolved
            # and the warning count each endpoint that is not in the output,
            # and relationship_total the links followed and those endpoints,
            # so the link with neither endpoint counts twice in both.
            relationships = load(output / "qa/relationship_summary.json")
            entries = relationships["relationships"]
            self.assertEqual(
                {
                    name: (
                        entries[name]["eligible_count"],
                        entries[name]["link_count"],
                        entries[name]["unresolved_count"],
                        entries[name]["orphan_count"],
                    )
                    for name in (
                        "activity_gear_to_activities",
                        "activity_gear_to_gear",
                        "personal_records_to_activities",
                    )
                },
                {
                    "activity_gear_to_activities": (5, 2, 3, 3),
                    "activity_gear_to_gear": (5, 3, 2, 2),
                    "personal_records_to_activities": (2, 1, 1, 1),
                },
            )
            self.assertEqual(
                (
                    relationships["relationship_total"],
                    relationships["relationship_resolved"],
                    relationships["relationship_unresolved"],
                ),
                (8, 2, 6),
            )
            self.assertEqual(
                relationships["relationship_total"],
                relationships["relationship_resolved"]
                + relationships["relationship_unresolved"]
                + relationships["relationship_malformed"]
                + relationships["relationship_conflict"],
            )
            for name, entry in entries.items():
                if name != "activities_to_fit_sessions":
                    with self.subTest(relationship=name):
                        self.assertEqual(
                            entry["unresolved_count"], entry["eligible_count"] - entry["link_count"]
                        )
            self.assertEqual(
                warning_counts(output, "relationships"), {"RELATIONSHIP_UNRESOLVED_VALID_LINK": 6}
            )
            self.assertEqual(summary["relationship_warning_count"], 1)
            counts = {
                item["dataset"]: item["record_count"]
                for item in load(output / "qa/dataset_summary.json")["datasets"]
            }
            self.assertEqual((counts["activity_gear"], counts["personal_records"]), (5, 3))

    def test_a_snapshot_run_keeps_them_as_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root / "runs", links_to_nothing(root))
            self.assertEqual(differences(one_shot, snapshot), [])
            self.assertEqual(
                (
                    len(load(snapshot / "normalized/activity_gear.json")),
                    len(load(snapshot / "normalized/personal_records.json")),
                ),
                (5, 3),
            )

    def test_only_the_activity_key_of_a_link_may_be_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(links_to_nothing(root), output)
            catalog = load(output / "SCHEMA_CATALOG.json")
            fields = next(item for item in catalog["datasets"] if item["dataset"] == "activity_gear")["fields"]
            self.assertEqual(
                {field["field"] for field in fields if field["nullable"]}, {"garmin_activity_key"}
            )
            self.assertLessEqual(
                {"activity_relationship_reason", "gear_relationship_reason"},
                {field["field"] for field in fields},
            )


class AmbiguousFitLinkTest(unittest.TestCase):
    def assert_ambiguous(self, source: Path, root: Path, activity_reasons: list[str], session_reasons: list[str]) -> None:
        one_shot, snapshot = runs(root, source)
        self.assertEqual(differences(one_shot, snapshot), [])
        for output in (one_shot, snapshot):
            with self.subTest(run=output.name):
                self.assertEqual(
                    warning_counts(output, "relationships"), {"ACTIVITY_FIT_LINK_AMBIGUOUS": 1}
                )
                summary = load(output / "run_summary.json")
                self.assertEqual(summary["status"], "PASS_WITH_WARNINGS")
                self.assertEqual(summary["relationship_warning_count"], 1)
                audit = load(output / "audit/activity_fit_linkage.json")
                self.assertEqual(
                    [item["reason"] for item in audit["activity_exclusions"]], activity_reasons
                )
                self.assertEqual(
                    [item["reason"] for item in audit["fit_session_exclusions"]], session_reasons
                )
                self.assertEqual(audit["metrics"]["ambiguous_count"], 1)
                self.assertEqual(load(output / "normalized/activity_fit_links.json"), [])

    def test_one_session_written_in_two_fit_files_is_announced(self) -> None:
        # The two files differ only in the form of their header: the
        # Activity has two equally matching sessions.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = fit_export(
                root,
                [fit_activity("1001")],
                {"a.fit": synthetic_fit(), "b.fit": synthetic_fit(header_size=12, header_crc_present=False)},
            )
            self.assert_ambiguous(
                source, root / "runs", ["ambiguous_candidate"], ["one_to_one_conflict", "one_to_one_conflict"]
            )

    def test_two_activities_of_one_session_are_announced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = fit_export(root, [fit_activity("1001"), fit_activity("1002")], {"a.fit": synthetic_fit()})
            self.assert_ambiguous(
                source, root / "runs", ["one_to_one_conflict", "one_to_one_conflict"], ["ambiguous_candidate"]
            )

    def test_one_fit_file_in_two_places_is_read_once_and_linked(self) -> None:
        # The same content is read once (stage A3a), so nothing ties.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fit = synthetic_fit()
            source = fit_export(root, [fit_activity("1001")], {"a.fit": fit, "again/a.fit": fit})
            one_shot, snapshot = runs(root / "runs", source)
            self.assertEqual(differences(one_shot, snapshot), [])
            for output in (one_shot, snapshot):
                with self.subTest(run=output.name):
                    self.assertNotIn("ACTIVITY_FIT_LINK_AMBIGUOUS", warning_counts(output, "relationships"))
                    self.assertEqual(len(load(output / "normalized/activity_fit_links.json")), 1)


class MessagesTest(unittest.TestCase):
    def test_the_gui_tells_that_rows_stay_and_where_ties_are_listed(self) -> None:
        en = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
        ja = json.loads((I18N / "ja.json").read_text(encoding="utf-8"))
        self.assertIn("kept with the link unresolved", en["warning.relationship_unresolved"])
        self.assertIn("行は残し", ja["warning.relationship_unresolved"])
        for catalog in (en, ja):
            self.assertIn("audit/activity_fit_linkage.json", catalog["warning.activity_fit_link_ambiguous"])
        self.assertIn(
            'ACTIVITY_FIT_LINK_AMBIGUOUS: "warning.activity_fit_link_ambiguous"',
            FLOW.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
