"""A Snapshot run of a store that holds one Export gives what a one-shot run of
that Export gives (stage A3d-4); with more Exports, the counts follow the rule
of stage A3b: the same content in two Snapshots once, and its copies within
one Snapshot.

Stage A3d-4a: the files found and processed of each family, the files that
the audit records of the daily datasets found, the source counts of the
dataset summary, the places of each FIT file in its audit, and the status
and warning of a family whose files hold no record.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from tests.fit_fixture_factory import synthetic_fit
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


if __name__ == "__main__":
    unittest.main()
