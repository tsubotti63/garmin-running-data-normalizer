"""Activities, Gear, activity_gear, and Personal Records across Snapshots (stage A2b-2)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.run_all import RECORD_AUDIT_DATASETS, RunAllError, run_all
from garmin_running_data_normalizer.runner import main as cli_main
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from garmin_running_data_normalizer.standalone import validate_standalone_handoff
from tests.test_snapshot_lifecycle import _activity, _write_snapshot

ACCOUNT = "synthetic-account-boundary"
ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_FIELDS = {"source_path", "source_sha256"}


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def gear(gear_pk: int, name: str) -> dict[str, object]:
    return {
        "gearPk": gear_pk,
        "uuid": f"synthetic-uuid-{gear_pk}",
        "displayName": name,
        "customMakeModel": f"Synthetic model {gear_pk}",
        "gearTypeName": "Shoes",
        "dateBegin": "2030-01-01T00:00:00.0",
        "maximumMeters": 800000,
    }


def personal_record(record_id: int, activity_id: str, value: float) -> dict[str, object]:
    return {
        "personalRecordId": record_id,
        "activityId": activity_id,
        "personalRecordType": "synthetic_best",
        "value": value,
        "current": True,
        "confirmed": True,
    }


def write_export(
    root: Path,
    name: str,
    activities: list[dict[str, object]],
    *,
    gear_rows: list[dict[str, object]] | None = None,
    links: dict[str, list[str]] | None = None,
    records: list[dict[str, object]] | None = None,
) -> Path:
    """Write a synthetic Export.

    The Gear file is written when Gear or links are given; it has the
    ``gearActivityDTOs`` object only when ``links`` is given, even empty.
    """
    source = root / name
    _write_snapshot(source, activities)
    fitness = source / "DI-Connect-Fitness"
    if gear_rows is not None or links is not None:
        container: dict[str, object] = {"gearDTOS": gear_rows or []}
        if links is not None:
            container["gearActivityDTOs"] = {
                gear_key: [{"activityId": activity_id} for activity_id in activity_ids]
                for gear_key, activity_ids in links.items()
            }
        (fitness / "synthetic_gear.json").write_text(json.dumps([container]), encoding="utf-8")
    if records is not None:
        (fitness / "synthetic_personalRecord.json").write_text(
            json.dumps([{"personalRecords": records}]), encoding="utf-8"
        )
    return source


def register(store: Path, source: Path, label: str, day: int) -> None:
    register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
        confirm_complete=True,
    )


def store_with(root: Path, exports: dict[int, Path], order: list[int] | None = None) -> Path:
    """Register the Exports by day, in the given registration order."""
    store = root / "store"
    initialize_store(store, ACCOUNT)
    for day in order or sorted(exports):
        register(store, exports[day], f"S{day}", day)
    return store


def warning_counts(output: Path) -> dict[tuple[str, str], int]:
    return {
        (item["code"], item.get("family", "")): item.get("count", 1)
        for item in load(output / "run_summary.json")["warnings"]
        if item["code"] in {"VALUES_UPDATED", "RECORDS_NOT_IN_LATEST_SNAPSHOT"}
    }


class SnapshotRecordUpdatesTest(unittest.TestCase):
    def test_later_values_replace_earlier_ones_and_every_value_is_kept(self) -> None:
        exports_by_day = {
            1: [
                _activity(
                    "A1",
                    name="Morning run",
                    description="first memo",
                    splitSummaries=[{"split": 1}],
                    summaryDTO={"synthetic": 1},
                ),
                _activity("A2", name="Kept run"),
            ],
            2: [
                _activity("A1", name="Morning run 10k", description=None),
                _activity("A2", name="Kept run"),
            ],
            3: [_activity("A1", name="Morning run 10k", splitSummaries=[], summaryDTO={})],
            4: [_activity("A1", name="Morning run 10k"), _activity("A3")],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {
                day: write_export(root, f"source-{day}", rows)
                for day, rows in exports_by_day.items()
            }
            # Registered out of order: the Snapshot numbers follow the Export
            # observation times, not the order of registration.
            store = store_with(root, exports, order=[3, 1, 4, 2])
            output = root / "output"
            result = run_snapshot_all(store, output)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")

            activities = {
                row["activity_id"]: row
                for row in load(output / "normalized/activities.json")
            }
            self.assertEqual(set(activities), {"A1", "A2", "A3"})
            # The latest value, a removed value, and a value that a later
            # Snapshot does not contain.
            self.assertEqual(activities["A1"]["name"], "Morning run 10k")
            self.assertIsNone(activities["A1"]["memo_text_raw"])
            self.assertFalse(activities["A1"]["memo_present"])
            self.assertEqual(activities["A2"]["name"], "Kept run")

            audit = load(output / "audit/activities.json")
            self.assertEqual(audit["observation_scope"], "REGISTERED_SNAPSHOT_OBSERVATIONS")
            self.assertEqual(audit["record_count"], 3)
            self.assertEqual(audit["updated_record_count"], 1)
            [update] = audit["updates"]
            self.assertEqual(update["key"], {"garmin_activity_key": "garmin_activity:A1"})
            self.assertEqual(
                {item["field"]: item["values"] for item in update["fields"]},
                {
                    "description": [
                        {"value": "first memo", "snapshots": [1]},
                        {"value": None, "snapshots": [2]},
                    ],
                    "name": [
                        {"value": "Morning run", "snapshots": [1]},
                        {"value": "Morning run 10k", "snapshots": [2, 3, 4]},
                    ],
                    "splitSummaries": [
                        {"value": [{"split": 1}], "snapshots": [1]},
                        {"value": [], "snapshots": [3]},
                    ],
                    "summaryDTO": [
                        {"value": {"synthetic": 1}, "snapshots": [1]},
                        {"value": {}, "snapshots": [3]},
                    ],
                },
            )
            self.assertEqual(
                audit["not_in_latest_snapshot"],
                [{"key": {"garmin_activity_key": "garmin_activity:A2"}, "last_seen_snapshot": 2}],
            )
            self.assertEqual(
                warning_counts(output),
                {
                    ("VALUES_UPDATED", "activities"): 1,
                    ("RECORDS_NOT_IN_LATEST_SNAPSHOT", "activities"): 1,
                },
            )
            family = load(output / "run_summary.json")["family_results"]["activities"]
            self.assertEqual(family["updated_record_count"], 1)
            self.assertEqual(family["not_in_latest_snapshot_count"], 1)
            merge_summary = load(output / "snapshot/canonical_merge_summary.json")
            self.assertEqual(merge_summary["merge_rules_version"], "garmin_snapshot_merge_rules:v2.1")
            self.assertEqual(merge_summary["datasets"]["activities"]["updated_record_count"], 1)
            self.assertEqual(merge_summary["explicit_null_review_count"], 0)
            # The output stays valid for the checks of completed outputs.
            validate_standalone_handoff(output)
            self.assertEqual(doctor_run_output(output)["product_exit_code"], 0)

    def test_values_that_differ_only_in_form_are_not_updates(self) -> None:
        exports_by_day = {
            1: [
                _activity(
                    "X1",
                    description=None,
                    distance=1000,
                    tags=[],
                    summaryDTO={"split": 1, "laps": [None]},
                    synthetic=True,
                )
            ],
            2: [
                _activity(
                    "X1",
                    description="",
                    distance=1000.0,
                    tags={},
                    summaryDTO={"split": 1.0, "laps": [""]},
                    synthetic=1,
                )
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {
                day: write_export(root, f"source-{day}", rows)
                for day, rows in exports_by_day.items()
            }
            output = root / "output"
            result = run_snapshot_all(store_with(root, exports), output)
            self.assertEqual(result["exit_code"], 0)
            # A boolean is not a number, so only `synthetic` changed.
            [update] = load(output / "audit/activities.json")["updates"]
            self.assertEqual(
                update["fields"],
                [
                    {
                        "field": "synthetic",
                        "values": [
                            {"value": True, "snapshots": [1]},
                            {"value": 1, "snapshots": [2]},
                        ],
                    }
                ],
            )
            self.assertEqual(warning_counts(output), {("VALUES_UPDATED", "activities"): 1})
            # The table keeps the latest Snapshot's value as it was written.
            [row] = load(output / "normalized/activities.json")
            self.assertEqual(row["memo_text_raw"], "")
            self.assertIsInstance(row["distance_raw_centimeters"], float)
            summary = load(output / "snapshot/canonical_merge_summary.json")
            self.assertEqual(summary["datasets"]["activities"]["updated_field_count"], 1)

    def test_a_gear_change_removes_the_earlier_link(self) -> None:
        # The example the maintainer approved: the shoe of run X1 changes
        # from A to B; the table has B only, and the audit keeps A.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shoes = [gear(11, "Shoe A"), gear(12, "Shoe B")]
            activities = [_activity("X1"), _activity("X2")]
            exports = {
                1: write_export(root, "source-1", activities, gear_rows=shoes, links={"11": ["X1", "X2"]}),
                2: write_export(
                    root, "source-2", activities, gear_rows=shoes, links={"11": ["X2"], "12": ["X1"]}
                ),
            }
            output = root / "output"
            result = run_snapshot_all(store_with(root, exports), output)
            self.assertEqual(result["exit_code"], 0)
            links = {
                (row["gear_key"], row["activity_id"])
                for row in load(output / "normalized/activity_gear.json")
            }
            self.assertEqual(links, {(11, "X2"), (12, "X1")})
            audit = load(output / "audit/activity_gear.json")
            self.assertEqual(
                audit["removed_links"],
                [{"key": {"gear_key": 11, "activity_id": "X1"}, "last_seen_snapshot": 1}],
            )
            self.assertEqual(audit["removed_link_count"], 1)
            self.assertEqual(audit["not_in_latest_snapshot"], [])
            self.assertEqual(warning_counts(output), {("VALUES_UPDATED", "gear"): 1})
            summary = load(output / "snapshot/canonical_merge_summary.json")
            self.assertEqual(summary["datasets"]["activity_gear"]["removed_link_count"], 1)
            self.assertEqual(summary["datasets"]["activity_gear"]["previous_only_retained_count"], 0)

    def test_a_missing_link_is_removed_only_when_the_latest_snapshot_shows_the_change(self) -> None:
        shoes = [gear(11, "Shoe A"), gear(12, "Shoe B")]
        both = [_activity("X1"), _activity("X2")]
        earlier = {"gear_rows": shoes, "links": {"11": ["X1"], "12": ["X2"]}}
        # Each case: the latest Export, its Activities, the records kept that it
        # does not contain, and the links removed.
        cases = {
            # Neither Gear nor links: the latest Export has no Gear file.
            "no gear file": (
                {},
                both,
                {("gear", 11), ("gear", 12), ("activity_gear", (11, "X1")), ("activity_gear", (12, "X2"))},
                set(),
            ),
            # Gear but no links: the Gear file has no gearActivityDTOs object.
            "no links": (
                {"gear_rows": shoes},
                both,
                {("activity_gear", (11, "X1")), ("activity_gear", (12, "X2"))},
                set(),
            ),
            # Links, but not the row of run X1, whose Gear and Activity are there.
            "row missing": (
                {"gear_rows": shoes, "links": {"12": ["X2"]}},
                both,
                set(),
                {(11, "X1")},
            ),
            # An empty gearActivityDTOs object: no Activity has Gear any more.
            "links empty": (
                {"gear_rows": shoes, "links": {}},
                both,
                set(),
                {(11, "X1"), (12, "X2")},
            ),
            # Gear A is not in the latest Export, which has links.
            "gear missing": (
                {"gear_rows": [gear(12, "Shoe B")], "links": {"12": ["X2"]}},
                both,
                {("gear", 11), ("activity_gear", (11, "X1"))},
                set(),
            ),
            # Activity X2 is not in the latest Export, which has links.
            "activity missing": (
                {"gear_rows": shoes, "links": {"11": ["X1"]}},
                [_activity("X1")],
                {("activities", "garmin_activity:X2"), ("activity_gear", (12, "X2"))},
                set(),
            ),
        }
        for name, (latest, latest_activities, kept_expected, removed_expected) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                exports = {
                    1: write_export(root, "source-1", both, **earlier),
                    2: write_export(root, "source-2", latest_activities, **latest),
                }
                output = root / "output"
                result = run_snapshot_all(store_with(root, exports), output)
                self.assertEqual(result["exit_code"], 0)
                links = {
                    (row["gear_key"], row["activity_id"])
                    for row in load(output / "normalized/activity_gear.json")
                }
                self.assertEqual(links, {(11, "X1"), (12, "X2")} - removed_expected)
                kept = set()
                for dataset in ("activities", "gear", "activity_gear"):
                    audit = load(output / f"audit/{dataset}.json")
                    for item in audit["not_in_latest_snapshot"]:
                        self.assertEqual(item["last_seen_snapshot"], 1)
                        key = item["key"]
                        kept.add(
                            (
                                dataset,
                                (key["gear_key"], key["activity_id"])
                                if dataset == "activity_gear"
                                else next(iter(key.values())),
                            )
                        )
                self.assertEqual(kept, kept_expected)
                removed = load(output / "audit/activity_gear.json")["removed_links"]
                self.assertEqual(
                    {(item["key"]["gear_key"], item["key"]["activity_id"]) for item in removed},
                    removed_expected,
                )
                self.assertTrue(all(item["last_seen_snapshot"] == 1 for item in removed))

    def test_a_personal_record_with_a_new_identifier_keeps_the_earlier_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activities = [_activity("X1"), _activity("X2")]
            exports = {
                1: write_export(root, "source-1", activities, records=[personal_record(1, "X1", 1500.0)]),
                2: write_export(root, "source-2", activities, records=[personal_record(2, "X2", 1400.0)]),
            }
            output = root / "output"
            result = run_snapshot_all(store_with(root, exports), output)
            self.assertEqual(result["exit_code"], 0)
            records = {row["personal_record_id"]: row for row in load(output / "normalized/personal_records.json")}
            self.assertEqual(set(records), {1, 2})
            # The earlier record keeps the values of the last Snapshot that had it.
            self.assertTrue(records[1]["current"])
            audit = load(output / "audit/personal_records.json")
            self.assertEqual(
                audit["not_in_latest_snapshot"],
                [{"key": {"personal_record_id": 1}, "last_seen_snapshot": 1}],
            )
            self.assertEqual(audit["updates"], [])
            self.assertEqual(
                warning_counts(output), {("RECORDS_NOT_IN_LATEST_SNAPSHOT", "personal_records"): 1}
            )

    def test_a_removed_required_value_is_normalized_as_in_a_one_shot_run(self) -> None:
        later = _activity("X1", startTimeGmt=None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {
                1: write_export(root, "source-1", [_activity("X1")]),
                2: write_export(root, "source-2", [later]),
            }
            output = root / "output"
            result = run_snapshot_all(store_with(root, exports), output)
            self.assertEqual(result["exit_code"], 0)
            [snapshot_row] = load(output / "normalized/activities.json")
            self.assertIsNone(snapshot_row["start_time_gmt_ms"])
            self.assertIsNone(snapshot_row["activity_date_local"])
            one_shot = root / "one-shot"
            run_all(write_export(root, "one-shot-source", [later]), one_shot)
            [one_shot_row] = load(one_shot / "normalized/activities.json")
            self.assertEqual(
                {key: value for key, value in snapshot_row.items() if key not in PROVENANCE_FIELDS},
                {key: value for key, value in one_shot_row.items() if key not in PROVENANCE_FIELDS},
            )

    def test_a_removed_value_that_the_dataset_rejects_stops_as_in_a_one_shot_run(self) -> None:
        # Until stage A3, which leaves such a row out and counts it (exit 3),
        # the Snapshot run stops as a one-shot run of the same row does.
        cases = {
            "empty string for a number": (
                {"activities": [_activity("X1", startTimeGmt="")]},
                "OUTPUT_EXPERIENCE_FAILED",
            ),
            "empty list for a text": (
                {"activities": [_activity("X1", name=[])]},
                "OUTPUT_EXPERIENCE_FAILED",
            ),
            "null Activity of a Personal Record": (
                {
                    "activities": [_activity("X1")],
                    "records": [{**personal_record(1, "X1", 1500.0), "activityId": None}],
                },
                "RELATIONSHIP_CONTRACT_FAILED",
            ),
        }
        for name, (latest, code) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                latest_rows = dict(latest)
                exports = {
                    1: write_export(
                        root,
                        "source-1",
                        [_activity("X1")],
                        records=[personal_record(1, "X1", 1500.0)],
                    ),
                    2: write_export(root, "source-2", latest_rows.pop("activities"), **latest_rows),
                }
                store = store_with(root, exports)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    exit_code = cli_main(
                        ["snapshot", "run-all", "--store", str(store), "--output", str(root / "output")]
                    )
                self.assertEqual(exit_code, 2)
                self.assertIn(f"ERROR [{code}]", stderr.getvalue())
                self.assertFalse((root / "output").exists())
                one_shot_rows = dict(latest)
                with self.assertRaises(RunAllError) as raised:
                    run_all(
                        write_export(root, "one-shot", one_shot_rows.pop("activities"), **one_shot_rows),
                        root / "one-shot-output",
                    )
                self.assertEqual(raised.exception.code, code)

    def test_processing_sequence_does_not_change_the_changes_or_their_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {
                day: write_export(
                    root,
                    f"source-{day}",
                    [_activity("A1", name=f"name {day % 2}")] + ([_activity("A2")] if day < 3 else []),
                    gear_rows=[gear(11, "Shoe A"), gear(12, "Shoe B")],
                    links={"11" if day < 2 else "12": ["A1"]},
                )
                for day in (1, 2, 3)
            }
            store = store_with(root, exports, order=[2, 3, 1])
            builds = [
                build_approved_input(store, root / f"build-{index}", processing_sequence=sequence)
                for index, sequence in enumerate((None, ["S3", "S1", "S2"], ["S2", "S1", "S3"]))
            ]
            for build in builds[1:]:
                self.assertEqual(build["record_changes"], builds[0]["record_changes"])
                self.assertEqual(build["canonical_build_sha256"], builds[0]["canonical_build_sha256"])
            changes = builds[0]["record_changes"]
            self.assertEqual(
                changes["activities"]["updates"][0]["fields"],
                [
                    {
                        "field": "name",
                        "values": [
                            {"value": "name 1", "snapshots": [1]},
                            {"value": "name 0", "snapshots": [2]},
                            {"value": "name 1", "snapshots": [3]},
                        ],
                    }
                ],
            )
            self.assertEqual(
                changes["activity_gear"]["removed_links"],
                [{"key": {"gear_key": 11, "activity_id": "A1"}, "last_seen_snapshot": 1}],
            )
            outputs = []
            for index, sequence in enumerate((["S1", "S2", "S3"], ["S3", "S2", "S1"])):
                output = root / f"output-{index}"
                run_snapshot_all(store, output, processing_sequence=sequence)
                outputs.append(
                    [(output / f"audit/{name}.json").read_bytes() for name in RECORD_AUDIT_DATASETS]
                )
            self.assertEqual(outputs[0], outputs[1])

    def test_one_shot_runs_write_the_same_audits_with_counts_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(
                root,
                "source",
                [_activity("X1"), _activity("X2")],
                gear_rows=[gear(11, "Shoe A")],
                links={"11": ["X1"]},
                records=[personal_record(1, "X1", 1500.0)],
            )
            outputs = [root / "first", root / "second"]
            for output in outputs:
                run_all(source, output)
            summary = load(outputs[0] / "run_summary.json")
            for name in RECORD_AUDIT_DATASETS:
                with self.subTest(dataset=name):
                    relative = f"audit/{name}.json"
                    self.assertIn(relative, summary["generated_paths"])
                    data = (outputs[0] / relative).read_bytes()
                    self.assertEqual(data, (outputs[1] / relative).read_bytes())
                    audit = json.loads(data)
                    expected = {
                        "format": "garmin-running-data-normalizer-dataset-audit-v1",
                        "dataset": name,
                        "observation_scope": "ONE_EXPORT_OBSERVATION",
                        "record_count": len(load(outputs[0] / f"normalized/{name}.json")),
                        "updated_record_count": 0,
                        "updates": [],
                        "not_in_latest_snapshot_count": 0,
                        "not_in_latest_snapshot": [],
                    }
                    if name == "activity_gear":
                        expected.update({"removed_link_count": 0, "removed_links": []})
                    self.assertEqual(audit, expected)
            self.assertEqual(warning_counts(outputs[0]), {})
            quality = load(outputs[0] / "diagnostics/run_quality.json")
            bound = {item["artifact"] for item in quality["provenance_references"]}
            self.assertTrue({f"audit/{name}.json" for name in RECORD_AUDIT_DATASETS} <= bound)

    def test_shared_files_carry_counts_and_no_earlier_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {
                1: write_export(
                    root,
                    "source-1",
                    [_activity("X1", name="Earlier-private-name", description="Earlier-private-memo")],
                    gear_rows=[gear(11, "Earlier-private-shoe")],
                ),
                2: write_export(
                    root,
                    "source-2",
                    [_activity("X1", name="Later name", description="")],
                    gear_rows=[gear(11, "Later shoe")],
                ),
            }
            output = root / "output"
            run_snapshot_all(store_with(root, exports), output, external_safe_pack=True)
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            earlier = (b"Earlier-private-name", b"Earlier-private-memo", b"Earlier-private-shoe")
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with self.subTest(file=path.name), zipfile.ZipFile(path) as archive:
                    content = b"".join(archive.read(name) for name in archive.namelist())
                    for value in earlier:
                        self.assertNotIn(value, content)
            for relative in (
                "snapshot/canonical_merge_summary.json",
                "snapshot/snapshot_coverage.json",
                "run_summary.json",
                "diagnostics/run_quality.json",
            ):
                with self.subTest(file=relative):
                    data = (output / relative).read_bytes()
                    for value in earlier:
                        self.assertNotIn(value, data)
            # The local audits keep the earlier values with their Snapshots.
            self.assertIn(b"Earlier-private-memo", (output / "audit/activities.json").read_bytes())
            self.assertIn(b"Earlier-private-shoe", (output / "audit/gear.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
