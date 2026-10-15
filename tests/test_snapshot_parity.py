"""A Snapshot run of a store that holds one Export gives what a one-shot run of
that Export gives (stage A3d-4); with more Exports, the counts follow the rule
of stage A3b: the same content in two Snapshots once, and its copies within
one Snapshot.

Stage A3d-4a: the files found and processed of each family, the files that
the audit records of the daily datasets found, the source counts of the
dataset summary, the places of each FIT file in its audit, and the status
and warning of a family whose files hold no record.

Stage A3d-4b: the Lactate Threshold audit and candidate features, the
private fields of the Hill and Endurance rows, the activity of a VO2max row
of either series, the counters of the relationship summary, and the files of
Activities, Gear, and Personal Records whatever the case of their names.

Stage A3d-4c-1: the input files of the run summary, the unknown evidence of
Source Completeness, the FIT files counted in each place where they are
found, and the files of an Export told by one rule, a member of a ZIP file by
its name within the ZIP file and a daily file by the beginning of its name.

Stage A3d-4c-2: the observations of Source Completeness, which Run-All
counts from the output rows that each Snapshot observed; and every output of
a Snapshot run of one Export, which is that of a one-shot run of it but for
what differs by design (``BY_DESIGN``).

Stage A4b: the files that a run does not read, which both runs list, and a
ZIP file inside a ZIP file, which neither run reads; the files outside the
Export, which are not registered, differ by design.
"""

from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.diagnostics.detector import (
    classify_source_name,
    reads_record_file,
)
from garmin_running_data_normalizer.intake.discovery import DiscoveredAsset
from garmin_running_data_normalizer.run_all import _asset_family, run_all
from garmin_running_data_normalizer.runner import run_activities
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from garmin_running_data_normalizer.snapshot.merge import _object_name
from tests.fit_fixture_factory import synthetic_fit, truncated_fit, unsupported_chained_fit
from tests.test_snapshot_lifecycle import (
    _activity,
    _write_performance_metrics,
    _write_remaining_daily_metrics,
)
from tests.test_snapshot_record_updates import ACCOUNT, gear, personal_record, write_export

FIT_A = synthetic_fit()
FIT_B = synthetic_fit(sessions=2)
DAILY_DATASETS = (
    "hill_score_daily",
    "endurance_score_daily",
    "race_prediction_daily",
    "sleep_daily",
    "uds_daily",
    "acute_training_load_daily",
    "training_readiness_daily",
    "vo2max_daily",
    "training_history_daily",
    "hrv_daily",
)
# The fields that tell where a row came from, named one by one (learning
# 20261014-26); a Snapshot run takes them from the files of its build.
PROVENANCE_FIELDS = frozenset(
    {
        "source_path",
        "source_sha256",
        "source_record_index",
        "activity_source_path",
        "activity_source_sha256",
        "fit_source_path",
        "fit_source_sha256",
    }
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(zipfile.ZipInfo(name, date_time=(2030, 1, 1, 0, 0, 0)), data)
    return buffer.getvalue()


def every_family(root: Path, name: str, day: int) -> Path:
    """An Export with a file of every family, two VO2max series, and the same
    FIT file twice, as a file and in a ZIP file, next to another one."""
    source = write_export(
        root,
        name,
        [_activity("1001"), _activity("1002", startTimeLocal="2030-01-02T09:00:00")],
        gear_rows=[gear(1, "Shoe")],
        links={"1": ["1001"]},
        records=[personal_record(11, "1001", 300.0)],
    )
    uploaded = source / "DI-Connect-Uploaded-Files"
    uploaded.mkdir(exist_ok=True)
    (uploaded / "synthetic.fit").write_bytes(FIT_A)
    (uploaded / "UploadedFiles_0-_Part1.zip").write_bytes(
        zip_bytes({"same.fit": FIT_A, "other.fit": FIT_B})
    )
    _write_performance_metrics(source, day)
    _write_remaining_daily_metrics(source, day)
    (source / "DI-Connect-Metrics" / f"ActivityVo2Max_{day}.json").write_text(
        json.dumps(
            [
                {
                    "calendarDate": f"2030-02-{day:02d}",
                    "timestampGmt": f"2030-02-{day:02d}T07:00:00",
                    "vo2MaxValue": 48 + day,
                    "sport": "RUNNING",
                    "activityId": 1001,
                }
            ]
        ),
        encoding="utf-8",
    )
    return source


def runs(root: Path, *sources: Path) -> tuple[Path, Path]:
    """A one-shot run of the last Export, and a Snapshot run of a store that
    holds every Export, one day apart."""
    store = root / "store"
    initialize_store(store, ACCOUNT)
    for day, source in enumerate(sources, start=1):
        stamp = f"2030-01-{day:02d}T02:00:00+00:00"
        register_snapshot(
            store,
            source,
            snapshot_label=f"S{day}",
            export_requested_at=stamp,
            export_downloaded_at=stamp,
            export_observed_at=stamp,
            confirm_complete=True,
        )
    run_all(sources[-1], root / "one-shot")
    run_snapshot_all(store, root / "snapshot")
    return root / "one-shot", root / "snapshot"


def counts(output: Path) -> dict[str, Any]:
    """The counts of files of stage A3d-4a, whatever the form of the run."""
    summary = load(output / "run_summary.json")
    return {
        "family_results": summary["family_results"],
        "warnings": sorted(
            (item["code"], item.get("family"), item.get("dataset"), item.get("count"))
            for item in summary["warnings"]
        ),
        "status": summary["status"],
        "audits": {
            dataset: load(output / "audit" / f"{dataset}.json")["detected_asset_count"]
            for dataset in DAILY_DATASETS
        },
        "source_counts": {
            item["dataset"]: item["source_count"]
            for item in load(output / "qa/dataset_summary.json")["datasets"]
        },
        "fit_places": sorted(
            (item["source_sha256"], item["source_alias_count"], item["duplicate_source_alias_count"])
            for item in load(output / "audit/fit_audit.json")
        ),
    }


class FileCountTest(unittest.TestCase):
    def test_a_store_of_one_export_counts_its_files_as_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root, every_family(root, "export", 1))
            expected = counts(one_shot)
            self.assertEqual(counts(snapshot), expected)
            # The Export holds the same FIT file twice and two VO2max series.
            self.assertEqual(expected["family_results"]["fit"]["detected_asset_count"], 3)
            self.assertEqual(expected["audits"]["vo2max_daily"], 2)
            self.assertIn((2, 1), [place[1:] for place in expected["fit_places"]])

    def test_a_file_of_a_family_without_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            (source / "DI-Connect-Fitness" / "synthetic_gear.json").write_text(
                json.dumps([{"gearDTOS": []}]), encoding="utf-8"
            )
            one_shot, snapshot = runs(root, source)
            for output in (one_shot, snapshot):
                with self.subTest(output=output.name):
                    gear_result = load(output / "run_summary.json")["family_results"]["gear"]
                    self.assertEqual(gear_result["status"], "PROCESSED_EMPTY")
                    self.assertEqual(gear_result["detected_asset_count"], 1)
            self.assertEqual(counts(snapshot), counts(one_shot))
            self.assertIn(("OPTIONAL_FAMILY_EMPTY", "gear", None, None), counts(snapshot)["warnings"])

    def test_the_files_of_several_exports_follow_the_rule_of_stage_a3b(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _one_shot, snapshot = runs(
                root, every_family(root, "first", 1), every_family(root, "second", 2)
            )
            found = counts(snapshot)
            families = {
                family: result["detected_asset_count"]
                for family, result in found["family_results"].items()
            }
            # The same FIT file twice in each Snapshot: once, and its copy in
            # each; the other FIT file in both Snapshots: once.
            self.assertEqual(families["fit"], 4)
            self.assertEqual(
                sorted(place[1:] for place in found["fit_places"]), [(1, 0), (3, 2)]
            )
            # The same Gear file in both Snapshots once; the daily files of
            # each day apart.
            self.assertEqual(families["gear"], 1)
            self.assertEqual(families["uds"], 2)
            self.assertEqual(families["vo2max"], 4)
            self.assertEqual(found["audits"]["vo2max_daily"], 4)
            self.assertEqual(found["audits"]["hrv_daily"], 4)
            self.assertEqual(found["source_counts"]["vo2max_daily"], 4)
            for family, result in found["family_results"].items():
                self.assertEqual(
                    result["processed_asset_count"], result["detected_asset_count"], family
                )


def lactate_and_private_fields(root: Path, name: str, day: int, copies: int = 2) -> Path:
    """An Export with a Lactate Threshold file of one row, and ``copies``
    equal files of two rows, one of them not a candidate; and with Hill and
    Endurance rows that hold private fields."""
    source = write_export(root, name, [_activity("1001")])
    _write_performance_metrics(source, day)
    wellness = source / "DI-Connect-Wellness"
    rows = [
        {"metaData": {"calendarDate": f"2030-01-{day:02d}", "sequence": 1}, "lactateThresholdHeartRate": 166},
        {"metaData": {"calendarDate": f"2030-01-{day:02d}", "sequence": 2}, "weight": 60000},
    ]
    for copy in range(copies):
        (wellness / f"synthetic_copy{copy}_userBioMetrics.json").write_text(
            json.dumps(rows), encoding="utf-8"
        )
    return source


def lactate_and_private_counts(output: Path) -> dict[str, Any]:
    lactate = load(output / "audit/lactate_threshold_candidates.json")
    return {
        "lactate": {
            key: lactate[key]
            for key in ("candidate_count", "family_asset_counts", "family_source_record_counts")
        },
        "lactate_fields": sorted(lactate),
        "features": [
            load(output / name)["candidate_features"]
            for name in ("run_summary.json", "run_manifest.json", "ANALYSIS_CONTEXT.json")
        ],
        "private": {
            dataset: load(output / "audit" / f"{dataset}.json")["excluded_private_field_presence_counts"]
            for dataset in ("hill_score_daily", "endurance_score_daily")
        },
    }


class AuditContentTest(unittest.TestCase):
    def test_the_lactate_audit_and_the_private_fields_of_one_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root, lactate_and_private_fields(root, "export", 1))
            expected = lactate_and_private_counts(one_shot)
            self.assertEqual(lactate_and_private_counts(snapshot), expected)
            # A file of one row, and two equal files of two rows, one of
            # them not a candidate in each.
            self.assertEqual(expected["lactate"]["family_asset_counts"], {"history": 3})
            self.assertEqual(expected["lactate"]["family_source_record_counts"], {"history": 5})
            self.assertNotIn("candidate_rows", expected["lactate_fields"])
            self.assertEqual(expected["private"]["hill_score_daily"], {"deviceId": 1})
            self.assertEqual(expected["private"]["endurance_score_daily"], {"userProfilePK": 1})

    def test_the_lactate_and_private_counts_of_several_exports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _one_shot, snapshot = runs(
                root,
                lactate_and_private_fields(root, "first", 1, copies=1),
                lactate_and_private_fields(root, "second", 1, copies=1),
                lactate_and_private_fields(root, "third", 1, copies=2),
            )
            found = lactate_and_private_counts(snapshot)
            # The same files and rows in the three Snapshots once, and the
            # copy of the second file within the third Snapshot: files 1 + 2,
            # rows 1 + 2 * 2.
            self.assertEqual(found["lactate"]["family_asset_counts"], {"history": 3})
            self.assertEqual(found["lactate"]["family_source_record_counts"], {"history": 5})
            # The same Hill and Endurance rows in the three Snapshots once.
            self.assertEqual(found["private"]["hill_score_daily"], {"deviceId": 1})
            self.assertEqual(found["private"]["endurance_score_daily"], {"userProfilePK": 1})

    def test_the_activity_of_a_vo2max_row_of_either_series(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            metrics = source / "DI-Connect-Metrics"
            metrics.mkdir()
            (metrics / "MetricsMaxMetData_1.json").write_text(
                json.dumps(
                    [
                        {
                            "calendarDate": "2030-02-01",
                            "updateTimestamp": "2030-02-01T06:00:00",
                            "vo2MaxValue": 51,
                            "sport": "RUNNING",
                            "activityId": 1001,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            one_shot, snapshot = runs(root, source)
            rows = [load(output / "normalized/vo2max_daily.json") for output in (one_shot, snapshot)]
            self.assertEqual(rows[1], rows[0])
            self.assertEqual([row["source_activity_id"] for row in rows[1]], [1001])

    def test_the_relationship_counters_follow_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linked = write_export(
                root, "linked", [_activity("1001")], gear_rows=[gear(1, "Shoe")], links={"1": ["1001"]}
            )
            one_shot, snapshot = runs(root / "first", linked)
            summaries = [load(output / "qa/relationship_summary.json") for output in (one_shot, snapshot)]
            self.assertEqual(summaries[1], summaries[0])
            self.assertNotIn("relationship_total", summaries[1])
            # A link whose Activity is absent: both give the counters.
            unlinked = write_export(
                root, "unlinked", [_activity("1001")], gear_rows=[gear(1, "Shoe")], links={"1": ["9999"]}
            )
            one_shot, snapshot = runs(root / "second", unlinked)
            summaries = [load(output / "qa/relationship_summary.json") for output in (one_shot, snapshot)]
            self.assertEqual(summaries[1], summaries[0])
            self.assertEqual(summaries[1]["relationship_unresolved"], 1)


class NameCaseTest(unittest.TestCase):
    def test_one_rule_tells_the_record_files_whatever_their_case(self) -> None:
        for name, family in (
            ("DI-Connect-Fitness/x_summarizedActivities.json", "activities"),
            ("DI-Connect-Fitness/X_SUMMARIZEDACTIVITIES.JSON", "activities"),
            ("DI-Connect-Fitness/x_Gear.json", "gear"),
            ("DI-Connect-Fitness/x_personalrecord.json", "personal_records"),
        ):
            with self.subTest(name=name):
                self.assertTrue(reads_record_file(name, family))
                self.assertEqual(classify_source_name(name, "json"), family)
        self.assertFalse(reads_record_file("DI-Connect-Fitness/x_summarizedActivities.json.bak", "activities"))

    def test_a_file_whose_name_differs_only_in_case_is_read_by_both_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001"), _activity("1002")])
            path = source / "DI-Connect-Fitness" / "synthetic_summarizedActivities.json"
            path.rename(path.with_name("synthetic_summarizedactivities.json"))
            # A one-shot run stopped with ACTIVITIES_EMPTY until stage A3d-4b.
            one_shot, snapshot = runs(root, source)
            tables = [load(output / "normalized/activities.json") for output in (one_shot, snapshot)]
            self.assertEqual(len(tables[0]), 2)
            self.assertEqual(counts(snapshot), counts(one_shot))
            # The Golden Path reads it too.
            self.assertEqual(run_activities(source, root / "golden")["record_count"], 2)

    def test_two_names_that_differ_only_in_case_are_both_read(self) -> None:
        # A ZIP file holds both names on every system; a folder can hold them
        # where names are case-sensitive, as on Linux.
        payload = json.dumps([{"summarizedActivitiesExport": [_activity("1001")]}]).encode()
        other = json.dumps([{"summarizedActivitiesExport": [_activity("1001"), _activity("1002")]}]).encode()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "export.zip"
            archive.write_bytes(
                zip_bytes(
                    {
                        "DI-Connect-Fitness/synthetic_summarizedActivities.json": payload,
                        "DI-Connect-Fitness/synthetic_summarizedactivities.json": other,
                    }
                )
            )
            one_shot, snapshot = runs(root, archive)
            for output in (one_shot, snapshot):
                with self.subTest(output=output.name):
                    activities = load(output / "run_summary.json")["family_results"]["activities"]
                    self.assertEqual(activities["detected_asset_count"], 2)
                    self.assertEqual(len(load(output / "normalized/activities.json")), 2)
            # The Activity in both files is one row and a copy, in both runs.
            audits = [load(output / "audit/activities.json") for output in (one_shot, snapshot)]
            self.assertEqual(
                {key: value for key, value in audits[1].items() if key != "observation_scope"},
                {key: value for key, value in audits[0].items() if key != "observation_scope"},
            )
            self.assertEqual(counts(snapshot), counts(one_shot))


def file_figures(output: Path) -> dict[str, Any]:
    """The counts of files of stage A3d-4c-1, whatever the form of the run."""
    report = load(output / "diagnostics/source_completeness.json")
    return {
        "input_asset_count": load(output / "run_summary.json")["input_asset_count"],
        "unknown_evidence": report["unknown_evidence_summary"],
        "quality_unknown_evidence": load(output / "diagnostics/run_quality.json")[
            "source_completeness"
        ]["unknown_evidence_count"],
        "candidates": sorted(
            (item["source_family_id"], item["candidate_asset_count"]) for item in report["families"]
        ),
        "fit": [
            {key: item[key] for key in ("candidate_asset_count", "readable_asset_count", "state_counts")}
            for item in report["families"]
            if item["source_family_id"] == "fit"
        ],
    }


def fit_completeness(output: Path) -> dict[str, Any]:
    return next(
        item
        for item in load(output / "diagnostics/source_completeness.json")["families"]
        if item["source_family_id"] == "fit"
    )


def without_provenance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in row.items() if key not in PROVENANCE_FIELDS} for row in rows]


def with_fit_files(root: Path, name: str, members: dict[str, bytes]) -> Path:
    """An Export whose FIT files are the members of one ZIP file."""
    source = write_export(root, name, [_activity("1001")])
    uploaded = source / "DI-Connect-Uploaded-Files"
    uploaded.mkdir()
    (uploaded / "UploadedFiles_0-_Part1.zip").write_bytes(zip_bytes(members))
    return source


class InputFileTest(unittest.TestCase):
    def test_the_input_files_and_unknown_evidence_of_one_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # The text file of every Export here, a CSV file, a JSON file of no
            # family, and a ZIP file that holds a text file next to a FIT file.
            source = with_fit_files(root, "export", {"readme.txt": b"synthetic", "a.fit": FIT_A})
            fitness = source / "DI-Connect-Fitness"
            (fitness / "synthetic_notes.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (fitness / "synthetic_unknown.json").write_text(json.dumps([{"x": 1}]), encoding="utf-8")
            one_shot, snapshot = runs(root, source)
            expected = file_figures(one_shot)
            self.assertEqual(file_figures(snapshot), expected)
            # The Activities file, the JSON file of no family, and the FIT
            # file are read; only the JSON file of no family is unknown
            # evidence, not the text and CSV files, which no run reads.
            self.assertEqual(expected["input_asset_count"], 3)
            self.assertEqual(expected["unknown_evidence"]["count"], 1)

    def test_the_input_files_of_several_exports_follow_the_rule_of_stage_a3b(self) -> None:
        uds = [{"calendarDate": "2030-02-01", "totalSteps": 5}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = with_fit_files(root, "first", {"a.fit": FIT_A})
            (first / "DI-Connect-Aggregator").mkdir()
            (first / "DI-Connect-Aggregator" / "UDSFile_1.json").write_text(json.dumps(uds), encoding="utf-8")
            second = with_fit_files(root, "second", {"a.fit": FIT_A, "b.fit": FIT_A})
            (second / "DI-Connect-Aggregator").mkdir()
            (second / "DI-Connect-Aggregator" / "UDSFile_2.json").write_text(
                json.dumps([{**uds[0], "totalSteps": 6}]), encoding="utf-8"
            )
            one_shot, snapshot = runs(root, first, second)
            # The same Activities file in both Snapshots once; the FIT file
            # once, and its copy within the second; each UDS file once: 5,
            # where the second Export alone has 4 and the two 7.
            self.assertEqual(load(one_shot / "run_summary.json")["input_asset_count"], 4)
            self.assertEqual(load(snapshot / "run_summary.json")["input_asset_count"], 5)

    def test_a_fit_file_in_two_places_is_counted_in_each(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root, with_fit_files(root, "export", {"a.fit": FIT_A, "b.fit": FIT_A}))
            fit = fit_completeness(one_shot)
            # Until stage A3d-4c-1, the one content of the two files was taken
            # for one of two files left unclassified: AMBIGUOUS.
            self.assertEqual(
                (fit["state"], fit["content_validity"], fit["reason_codes"]),
                ("PRESENT", "VALID", ["FIT_EVIDENCE_PRESENT"]),
            )
            self.assertEqual((fit["readable_asset_count"], fit["state_counts"]), (2, {"parsed_activity": 2}))
            self.assertEqual(file_figures(snapshot), file_figures(one_shot))

    def test_fit_files_of_several_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            members = {
                "activity.fit": FIT_A,
                "activity_again.fit": FIT_A,
                "broken.fit": truncated_fit(),
                "chained.fit": unsupported_chained_fit(),
            }
            one_shot, snapshot = runs(root, with_fit_files(root, "export", members))
            for output in (one_shot, snapshot):
                with self.subTest(output=output.name):
                    fit = fit_completeness(output)
                    self.assertEqual(
                        (fit["state"], fit["reason_codes"], fit["readable_asset_count"], fit["state_counts"]),
                        (
                            "AMBIGUOUS",
                            ["MIXED_FIT_EVIDENCE"],
                            2,
                            {"parsed_activity": 2, "truncated": 1, "unsupported_chained": 1},
                        ),
                    )


class FileNameTest(unittest.TestCase):
    def test_the_build_and_a_one_shot_run_tell_a_file_by_one_rule(self) -> None:
        # (path in the Export, name within a ZIP file, kind, family)
        examples = (
            ("DI-Connect-Aggregator/UDSFile_1.json", None, "json", "uds"),
            ("DI-Connect-Aggregator/udsfile_1.JSON", None, "json", "uds"),
            ("DI-Connect-Aggregator/Parts.zip", "UDSFile_1.json", "json", "uds"),
            ("DI-Connect-Aggregator/Parts.zip", "inner/UDSFile_2.json", "json", "uds"),
            ("DI-Connect-Metrics/Parts.zip", "HillScore_synthetic_1.json", "json", "hill_score"),
            ("DI-Connect-Metrics/MetricsMaxMetData_1.json", None, "json", "vo2max"),
            ("DI-Connect-Fitness/Parts.zip", "x_summarizedActivities.json", "json", "activities"),
            ("DI-Connect-Aggregator/old_UDSFile_1.json", None, "json", "unclassified"),
            ("DI-Connect-Aggregator/Copy of UDSFile_1.json", None, "json", "unclassified"),
            ("DI-Connect-Uploaded-Files/Parts.zip", "a.fit", "fit", "fit"),
        )
        for path, member, kind, family in examples:
            with self.subTest(path=path, member=member):
                stored = {
                    "relative_path": path if member is None else f"{path}!{member}",
                    "archive_member_path": member,
                }
                read = DiscoveredAsset(kind, path, member, 0, "0" * 64, b"")
                self.assertEqual(classify_source_name(_object_name(stored), kind), family)
                self.assertEqual(_asset_family(read), family)

    def test_daily_files_at_the_top_of_a_zip_file_are_read_by_both_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            (source / "DI-Connect-Aggregator").mkdir()
            (source / "DI-Connect-Aggregator" / "Parts.zip").write_bytes(
                zip_bytes(
                    {
                        "UDSFile_1.json": json.dumps([{"calendarDate": "2030-02-01", "totalSteps": 5}]).encode(),
                        "inner/UDSFile_2.json": json.dumps([{"calendarDate": "2030-02-02", "totalSteps": 6}]).encode(),
                    }
                )
            )
            (source / "DI-Connect-Metrics").mkdir()
            (source / "DI-Connect-Metrics" / "Parts.zip").write_bytes(
                zip_bytes(
                    {
                        "HillScore_synthetic_1.json": json.dumps(
                            [{"calendarDate": "2030-02-01", "overallScore": 50, "strengthScore": 40,
                              "enduranceScore": 30, "hillScoreClassificationId": 4}]
                        ).encode()
                    }
                )
            )
            one_shot, snapshot = runs(root, source)
            for table, rows in (("uds_daily", 2), ("hill_score_daily", 1)):
                with self.subTest(table=table):
                    found = [without_provenance(load(output / "normalized" / f"{table}.json")) for output in (one_shot, snapshot)]
                    self.assertEqual(len(found[0]), rows)
                    self.assertEqual(found[1], found[0])
            self.assertEqual(counts(snapshot), counts(one_shot))
            self.assertEqual(file_figures(snapshot), file_figures(one_shot))

    def test_a_name_that_holds_the_marker_of_a_family_inside_is_read_by_neither_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            (source / "DI-Connect-Aggregator").mkdir()
            (source / "DI-Connect-Aggregator" / "Copy of UDSFile_1.json").write_text(
                json.dumps([{"calendarDate": "2030-02-01", "totalSteps": 5}]), encoding="utf-8"
            )
            # A Snapshot run read it and, from stage A3d-4a, stopped with
            # OUTPUT_EXPERIENCE_FAILED: the build read rows of a file that the
            # counts did not hold.
            one_shot, snapshot = runs(root, source)
            for output in (one_shot, snapshot):
                with self.subTest(output=output.name):
                    self.assertEqual(load(output / "normalized/uds_daily.json"), [])
            self.assertEqual(counts(snapshot), counts(one_shot))
            self.assertEqual(file_figures(snapshot), file_figures(one_shot))
            self.assertEqual(file_figures(one_shot)["unknown_evidence"]["count"], 1)


# What differs by design between a one-shot run and a Snapshot run of one
# Export, by the names of the fields (decisions 20261014-25 and -27); a
# pattern covers what lies under it. The normalized tables are compared
# without the provenance fields, and the documents without their Snapshot
# Accumulation section; everything else is the same.
BY_DESIGN = tuple(
    re.compile(pattern)
    for pattern in (
        # The names of the scope.
        r"audit/\w+\.json/observation_scope",
        r"diagnostics/source_completeness\.json/(observation_scope|authority_references)",
        r"diagnostics/source_completeness\.json/families\[\*\]/observation_ref",
        r"diagnostics/source_completeness\.json/families\[\*\]/evidence_references\[\*\]/(artifact|json_pointer)",
        # Provenance, and the digests made from it or from the outputs.
        r"audit/fit_audit\.json\[\*\]/source_path",
        r"(qa/dataset_summary|run_manifest)\.json/datasets\[\*\]/records_sha256",
        r"diagnostics/run_quality\.json/provenance_references\[\*\]/sha256",
        r"diagnostics/run_quality\.json/output_digests/authority_evidence_digest/value",
        r"(run_manifest|run_summary)\.json/deterministic_output_digest",
        r"run_summary\.json/manifest_sha256",
        r"run_manifest\.json/input_assets",
        # The Snapshot numbers of the values and of the files listed.
        r"audit/\w+\.json/(disagreements\[\*\]/fields\[\*\]/values\[\*\]|invalid_values\[\*\])/snapshots",
        r"run_manifest\.json/(files_left_out|files_not_read|files_with_repaired_text)\[\*\]/snapshot",
        # The files of a Snapshot run only, and the lists and sections about them.
        r"snapshot/(canonical_merge_summary|snapshot_coverage|snapshot_lineage)\.json",
        r"run_manifest\.json/outputs",
        r"run_summary\.json/generated_paths",
        r"artifact_inventory\.json/artifacts",
        r"(ANALYSIS_CONTEXT|run_manifest|run_summary)\.json/snapshot_lifecycle",
    )
)
SNAPSHOT_SECTION = "## Snapshot Accumulation"
DOCUMENTS = ("START_HERE.md", "DATASET_INVENTORY.md", "ANALYSIS_HANDOFF.md")
# Files outside the Export are not registered in the store, so a Snapshot run
# does not list them (stage A4b): the rows of files_not_read whose reason is
# outside_export_root, and their count in START_HERE.md, differ by design.
OUTSIDE_REASON = "outside_export_root"
FILES_NOT_READ_LINE = re.compile(r"- Files not read: (\d+);")


def by_design(path: str) -> bool:
    for pattern in BY_DESIGN:
        found = pattern.match(path)
        if found and (found.end() == len(path) or path[found.end()] in "/["):
            return True
    return False


def walk(a: Any, b: Any, path: str, found: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                found.append(f"{path}/{key}")
            else:
                walk(a[key], b[key], f"{path}/{key}", found)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for x, y in zip(a, b):
            walk(x, y, f"{path}[*]", found)
    elif a != b:
        found.append(path)


def without_section(text: str) -> list[str]:
    kept, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.rstrip() == SNAPSHOT_SECTION
        if not inside:
            kept.append(line)
    return kept


def without_outside_rows(manifest: Any) -> Any:
    """A run manifest without the rows of the files outside the Export."""
    if not isinstance(manifest, dict):
        return manifest
    rows = [row for row in manifest.get("files_not_read", []) if row.get("reason") != OUTSIDE_REASON]
    kept = {key: value for key, value in manifest.items() if key != "files_not_read"}
    return {**kept, "files_not_read": rows} if rows else kept


def without_outside_count(lines: list[str], outside: int) -> list[str]:
    """The lines of a document, with the count of files not read less the
    files outside the Export."""
    kept: list[str] = []
    for line in lines:
        found = FILES_NOT_READ_LINE.match(line)
        if found and outside:
            rest = int(found.group(1)) - outside
            if not rest:
                continue
            line = f"- Files not read: {rest};{line[found.end():]}"
        kept.append(line)
    return kept


def differences(one_shot: Path, snapshot: Path) -> list[str]:
    """The places where every output file of the two runs differs, other
    than by design."""
    found: list[str] = []
    manifest = one_shot / "run_manifest.json"
    outside = (
        sum(row.get("reason") == OUTSIDE_REASON for row in load(manifest).get("files_not_read", []))
        if manifest.is_file()
        else 0
    )
    names = sorted(
        {path.relative_to(one_shot).as_posix() for path in one_shot.rglob("*") if path.is_file()}
        | {path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file()}
    )
    for name in names:
        left, right = one_shot / name, snapshot / name
        if not left.is_file() or not right.is_file():
            found.append(name)
        elif name.endswith(".json"):
            a, b = load(left), load(right)
            if name.startswith("normalized/"):
                a, b = without_provenance(a), without_provenance(b)
            if name == "run_manifest.json":
                a, b = without_outside_rows(a), without_outside_rows(b)
            walk(a, b, name, found)
        elif name in DOCUMENTS:
            if without_outside_count(
                without_section(left.read_text(encoding="utf-8")), outside
            ) != without_section(right.read_text(encoding="utf-8")):
                found.append(name)
        elif left.read_bytes() != right.read_bytes():
            found.append(name)
    return sorted({path for path in found if not by_design(path)})


def daily_rows(source: Path, folder: str, name: str, rows: list[dict[str, Any]]) -> None:
    (source / folder).mkdir(exist_ok=True)
    (source / folder / name).write_text(json.dumps(rows), encoding="utf-8")


def scenarios(root: Path) -> dict[str, Path]:
    """Synthetic Exports of one kind each, among them those of the survey of
    stage A3d-4c and the three that it found."""
    from tests.test_hrv_readings import VALUE_TIME, day, hrv_fit, reading

    found: dict[str, Path] = {"every family": every_family(root, "every-family", 1)}
    source = write_export(root, "empty-gear", [_activity("1001")])
    (source / "DI-Connect-Fitness" / "synthetic_gear.json").write_text(json.dumps([{"gearDTOS": []}]), encoding="utf-8")
    found["a Gear file without records"] = source
    source = write_export(root, "lower-case", [_activity("1001")])
    path = source / "DI-Connect-Fitness" / "synthetic_summarizedActivities.json"
    path.rename(path.with_name("synthetic_summarizedactivities.json"))
    found["a name in lower case"] = source
    source = write_export(root, "without-date", [_activity("1001")])
    daily_rows(source, "DI-Connect-Aggregator", "UDSFile_1.json", [{"totalSteps": 5}])
    found["a daily row without its date"] = source
    source = write_export(root, "vo2max", [_activity("1001")])
    daily_rows(source, "DI-Connect-Metrics", "MetricsMaxMetData_1.json", [
        {"calendarDate": "2030-02-01", "updateTimestamp": "2030-02-01T06:00:00", "vo2MaxValue": 51,
         "sport": "RUNNING", "activityId": 1001}])
    found["the activity of a VO2max row"] = source
    found["Lactate Threshold rows that are not candidates"] = lactate_and_private_fields(root, "lactate", 1)
    found["FIT files of several kinds"] = with_fit_files(root, "fit-kinds", {
        "activity.fit": FIT_A, "activity_again.fit": FIT_A, "broken.fit": truncated_fit(),
        "chained.fit": unsupported_chained_fit()})
    source = with_fit_files(root, "unknown", {"readme.txt": b"synthetic", "a.fit": FIT_A})
    (source / "DI-Connect-Fitness" / "synthetic_unknown.json").write_text(json.dumps([{"x": 1}]), encoding="utf-8")
    found["objects of no family"] = source
    source = write_export(root, "repeated", [_activity("1001"), _activity("1001"), {"activityName": "no id"}])
    row = {"calendarDate": "2030-02-01", "totalSteps": 5}
    daily_rows(source, "DI-Connect-Aggregator", "UDSFile_1.json", [row, row, {"totalSteps": 7}])
    daily_rows(source, "DI-Connect-Aggregator", "UDSFile_2.json", [row, {"calendarDate": "2030-02-02", "totalSteps": 6}])
    found["repeated rows and rows left out"] = source
    source = write_export(root, "invalid", [_activity("1001", distance="far")])
    daily_rows(source, "DI-Connect-Aggregator", "UDSFile_1.json", [{"calendarDate": "2030-02-01", "totalSteps": "many"}])
    found["values of another form"] = source
    source = write_export(root, "broken", [_activity("1001")])
    (source / "DI-Connect-Aggregator").mkdir()
    (source / "DI-Connect-Aggregator" / "UDSFile_1.json").write_text('{"calendarDate": ', encoding="utf-8")
    daily_rows(source, "DI-Connect-Aggregator", "UDSFile_2.json", [{"calendarDate": "2030-02-02", "totalSteps": 6}])
    found["a file that is not JSON"] = source
    found["links to nothing"] = write_export(
        root, "links", [_activity("1001")], gear_rows=[gear(1, "Shoe")], links={"1": ["1001", "9999"]},
        records=[personal_record(11, "1001", 300.0), personal_record(12, "", 200.0)])
    source = write_export(root, "hrv", [_activity("1001")])
    (source / "DI-Connect-Metrics").mkdir()
    for name, value in (("a", 6400), ("b", 6400), ("c", 6528)):
        (source / "DI-Connect-Metrics" / f"synthetic_hrv_{name}.fit").write_bytes(hrv_fit(VALUE_TIME, [reading(value, day(1))]))
    found["HRV readings in copies of a FIT file"] = source
    source = write_export(root, "zip-top", [_activity("1001")])
    (source / "DI-Connect-Aggregator").mkdir()
    (source / "DI-Connect-Aggregator" / "Parts.zip").write_bytes(zip_bytes({
        "UDSFile_1.json": json.dumps([{"calendarDate": "2030-02-01", "totalSteps": 5}]).encode()}))
    (source / "DI-Connect-Metrics").mkdir()
    (source / "DI-Connect-Metrics" / "Parts.zip").write_bytes(zip_bytes({
        "HillScore_synthetic_1.json": json.dumps([{"calendarDate": "2030-02-01", "overallScore": 50, "strengthScore": 40,
                                                   "enduranceScore": 30, "hillScoreClassificationId": 4}]).encode()}))
    found["daily files at the top of a ZIP file"] = source
    source = write_export(root, "copy-name", [_activity("1001")])
    daily_rows(source, "DI-Connect-Aggregator", "Copy of UDSFile_1.json", [{"calendarDate": "2030-02-01", "totalSteps": 5}])
    found["a name with the mark of a family inside"] = source
    # Stage A4b: files of a form not read, and a ZIP file inside a ZIP file
    # that holds a UDS file, which stopped a Snapshot run from stage A3d-4a.
    source = write_export(root, "not-read", [_activity("1001")])
    uploaded = source / "DI-Connect-Uploaded-Files"
    uploaded.mkdir(exist_ok=True)
    (uploaded / "synthetic-track.tcx").write_bytes(b"<synthetic/>")
    (uploaded / "UploadedFiles_0-_Part1.zip").write_bytes(zip_bytes({
        "synthetic.fit": FIT_A, "synthetic-notes.txt": b"synthetic\n",
        "UDSFile_parts.zip": zip_bytes({
            "UDSFile_1.json": json.dumps([{"calendarDate": "2030-02-01", "totalSteps": 5}]).encode()})}))
    found["files of a form not read and a ZIP file inside a ZIP file"] = source
    # Files outside the Export, which a Snapshot run does not list.
    parent = root / "outside"
    write_export(parent, "export", [_activity("1001")])
    (parent / "Outside-notes.json").write_text("[]", encoding="utf-8")
    (parent / "Outside-readme.txt").write_text("synthetic", encoding="utf-8")
    found["files outside the Export"] = parent
    # Stage A4c-1: fields that no dataset reads, in a record and its copy, in
    # Gear, its links, and Personal Records, and FIT messages and developer
    # fields that no dataset reads.
    from tests.test_unread_fields import other_messages

    source = write_export(
        root, "unread", [_activity("1001", maxSpeed=3.5), _activity("1001", maxSpeed=3.5)],
        gear_rows=[{**gear(1, "Shoe"), "gearStatusName": "active"}], links={"1": ["1001"]},
        records=[{**personal_record(11, "1001", 300.0), "prTypeLabelKey": "synthetic"}])
    path = source / "DI-Connect-Fitness" / "synthetic_gear.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[0]["gearActivityDTOs"]["1"][0]["activityName"] = "synthetic"
    path.write_text(json.dumps(payload), encoding="utf-8")
    uploaded = source / "DI-Connect-Uploaded-Files"
    uploaded.mkdir(exist_ok=True)
    (uploaded / "synthetic-unread.fit").write_bytes(synthetic_fit(extra_body=other_messages()))
    found["fields and FIT messages that no dataset reads"] = source
    return found


def completeness_entries(output: Path, reference: str | None = None) -> list[dict[str, Any]]:
    """The Source Completeness of each family, without the names of the
    scope; of one Snapshot when ``reference`` names it."""
    return [
        {key: value for key, value in item.items() if key not in ("observation_ref", "evidence_references")}
        for item in load(output / "diagnostics/source_completeness.json")["families"]
        if reference is None or item["observation_ref"] == reference
    ]


class EveryOutputTest(unittest.TestCase):
    def test_every_output_of_one_export_is_that_of_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in scenarios(root / "exports").items():
                with self.subTest(scenario=name):
                    folder = root / "runs" / source.name
                    one_shot, snapshot = runs(folder, source)
                    self.assertEqual(differences(one_shot, snapshot), [])

    def test_the_observations_of_one_export_are_its_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root, every_family(root, "export", 1))
            self.assertEqual(completeness_entries(snapshot), completeness_entries(one_shot))
            fit = fit_completeness(snapshot)
            # The sessions and laps of the FIT files: until stage A3d-4c-2, the
            # per-second records of the files, none in these, made it EMPTY.
            self.assertEqual((fit["state"], fit["source_observation_count"] > 0), ("PRESENT", True))
            coverage = load(snapshot / "snapshot/snapshot_coverage.json")
            self.assertEqual(
                coverage["source_completeness_observations"][0]["source_observation_counts"],
                {item["source_family_id"]: item["source_observation_count"] for item in completeness_entries(one_shot)},
            )

    def test_each_snapshot_of_two_exports_observes_its_own_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = every_family(root, "first", 1), every_family(root, "second", 2)
            _one_shot, snapshot = runs(root / "store", first, second)
            for number, source in enumerate((first, second), start=1):
                with self.subTest(snapshot=number):
                    run_all(source, root / f"one-shot-{number}")
                    self.assertEqual(
                        completeness_entries(snapshot, f"snapshot-{number}"),
                        completeness_entries(root / f"one-shot-{number}"),
                    )

    def test_a_build_alone_writes_no_observations(self) -> None:
        from garmin_running_data_normalizer.snapshot import build_approved_input

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            stamp = "2030-01-01T02:00:00+00:00"
            register_snapshot(store, every_family(root, "export", 1), snapshot_label="S1",
                              export_requested_at=stamp, export_downloaded_at=stamp,
                              export_observed_at=stamp, confirm_complete=True)
            build_approved_input(store, root / "build")
            coverage = load(root / "build/canonical/snapshot_coverage.json")
            # The rows are Run-All's to count.
            self.assertNotIn("source_observation_counts", coverage["source_completeness_observations"][0])


if __name__ == "__main__":
    unittest.main()
