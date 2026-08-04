from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from garmin_running_data_normalizer.snapshot import (
    SnapshotLifecycleError,
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    snapshot_status,
    verify_store,
)
from garmin_running_data_normalizer.snapshot.merge import SnapshotMergeError
from garmin_running_data_normalizer.snapshot.policies import public_registry


def _tree_hash(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(
            (
                path.relative_to(root).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return hashlib.sha256(
        json.dumps(rows, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _activity(activity_id: str, **fields: object) -> dict[str, object]:
    base: dict[str, object] = {
        "activityId": activity_id,
        "activityType": "running",
        "sportType": "running",
        "distance": 500000,
        "duration": 1800000,
        "startTimeGmt": 1893456000000,
        "startTimeLocal": "2030-01-01T09:00:00",
        "name": f"Synthetic {activity_id}",
        "synthetic": True,
    }
    base.update(fields)
    return base


def _write_snapshot(
    root: Path,
    rows: list[dict[str, object]],
    *,
    fit_payload: bytes | None = None,
    archive: bool = False,
) -> None:
    fitness = root / "DI-Connect-Fitness"
    fitness.mkdir(parents=True)
    payload = json.dumps(
        [{"summarizedActivitiesExport": rows}],
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if archive:
        with zipfile.ZipFile(root / "export.zip", "w") as bundle:
            bundle.writestr(
                "DI-Connect-Fitness/synthetic_summarizedActivities.json",
                payload,
            )
            if fit_payload is not None:
                bundle.writestr(
                    "DI-Connect-Uploaded-Files/synthetic.fit",
                    fit_payload,
                )
    else:
        (fitness / "synthetic_summarizedActivities.json").write_bytes(payload)
        if fit_payload is not None:
            uploaded = root / "DI-Connect-Uploaded-Files"
            uploaded.mkdir()
            (uploaded / "synthetic.fit").write_bytes(fit_payload)
    (root / "preserved-unknown.txt").write_text("synthetic\n", encoding="utf-8")


def _write_performance_metrics(root: Path, day: int) -> None:
    metrics = root / "DI-Connect-Metrics"
    wellness = root / "DI-Connect-Wellness"
    metrics.mkdir(exist_ok=True)
    wellness.mkdir(exist_ok=True)
    calendar_date = f"2030-01-{day:02d}"
    (metrics / f"HillScore_synthetic_{day}.json").write_text(
        json.dumps(
            [
                {
                    "calendarDate": calendar_date,
                    "overallScore": 70 + day,
                    "strengthScore": 60 + day,
                    "enduranceScore": 80 + day,
                    "hillScoreClassificationId": 4,
                    "hillScoreFeedbackPhraseId": 12,
                    "deviceId": "PRIVATE-DEVICE",
                }
            ]
        ),
        encoding="utf-8",
    )
    (metrics / f"EnduranceScore_synthetic_{day}.json").write_text(
        json.dumps(
            [
                {
                    "calendarDate": calendar_date,
                    "overallScore": 6000 + day,
                    "classification": 5,
                    "feedbackPhrase": 19,
                    "userProfilePK": "PRIVATE-ACCOUNT",
                }
            ]
        ),
        encoding="utf-8",
    )
    (wellness / f"synthetic_{day}_userBioMetrics.json").write_text(
        json.dumps(
            [
                {
                    "metaData": {
                        "calendarDate": calendar_date,
                        "sequence": day,
                        "userProfilePK": "PRIVATE-ACCOUNT",
                    },
                    "lactateThresholdHeartRate": 165 + day,
                }
            ]
        ),
        encoding="utf-8",
    )


def _write_remaining_daily_metrics(root: Path, day: int) -> None:
    metrics = root / "DI-Connect-Metrics"
    wellness = root / "DI-Connect-Wellness"
    aggregator = root / "DI-Connect-Aggregator"
    metrics.mkdir(exist_ok=True)
    wellness.mkdir(exist_ok=True)
    aggregator.mkdir(exist_ok=True)
    date = f"2030-02-{day:02d}"
    fixtures = {
        metrics / f"RunRacePredictions_{day}.json": [{"calendarDate": date, "timestamp": f"{date}T06:00:00", "raceTime5K": 1000, "raceTime10K": 2100, "raceTimeHalf": 4700, "raceTimeMarathon": 9900}],
        wellness / f"synthetic_{day}_sleepData.json": [{"calendarDate": date, "sleepStartTimestampGMT": "2030-02-01T12:00:00Z", "sleepEndTimestampGMT": "2030-02-01T20:00:00Z", "sleepTimeSeconds": 27000}],
        aggregator / f"UDSFile_{day}.json": [{"calendarDate": date, "totalSteps": day}],
        metrics / f"MetricsAcuteTrainingLoad_{day}.json": [{"calendarDate": date, "timestamp": f"{date}T06:00:00Z", "dailyTrainingLoadAcute": day}],
        metrics / f"TrainingReadinessDTO_{day}.json": [{"calendarDate": date, "timestamp": f"{date}T06:00:00", "score": day}],
        metrics / f"MetricsMaxMetData_{day}.json": [{"calendarDate": date, "updateTimestamp": f"{date}T06:00:00", "vo2MaxValue": 50 + day, "sport": "RUNNING"}],
        metrics / f"TrainingHistory_{day}.json": [{"calendarDate": date, "timestamp": f"{date}T06:00:00", "trainingStatus": "PRODUCTIVE", "sport": "RUNNING"}],
    }
    for path, value in fixtures.items():
        path.write_text(json.dumps(value), encoding="utf-8")


class SnapshotLifecycleTest(unittest.TestCase):
    def register(
        self,
        store: Path,
        source: Path,
        label: str,
        day: int,
    ) -> dict[str, object]:
        return register_snapshot(
            store,
            source,
            snapshot_label=label,
            export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
            export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
            export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
            confirm_complete=True,
        )

    def test_four_snapshot_merge_missing_is_not_delete_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            snapshots = {}
            rows_by_day = {
                1: [
                    _activity("A1", description="first"),
                    _activity("A2", name="retained-after-gap"),
                ],
                2: [
                    _activity("A1", name="updated", description=None),
                    _activity("A3", first_observation_null=None),
                ],
                3: [
                    _activity("A1", name="updated"),
                    _activity("A2", name="retained-after-gap"),
                ],
                4: [
                    _activity("A1", name="updated", description=""),
                    _activity("A2", name="retained-after-gap"),
                    _activity("A3"),
                    _activity("A4"),
                    {},
                ],
            }
            for day in (1, 3, 4, 2):
                source = root / f"source-{day}"
                _write_snapshot(source, rows_by_day[day])
                snapshots[day] = source
                self.register(store, source, f"S{day}", day)

            status = snapshot_status(store)
            self.assertEqual(
                [item["snapshot_label"] for item in status["snapshots"]],
                ["S1", "S2", "S3", "S4"],
            )
            self.assertEqual(status["snapshot_count"], 4)
            self.assertFalse(status["automatic_deletion"])
            self.assertEqual(verify_store(store)["status"], "PASS")
            self.assertTrue((store / "snapshot_registry.json").is_file())
            self.assertTrue((store / "snapshot_family_coverage.json").is_file())
            self.assertEqual(
                len(list((store / "snapshots").glob("*/*.inventory.json"))),
                4,
            )

            idempotent = self.register(store, snapshots[2], "S2", 2)
            self.assertTrue(idempotent["registration_was_idempotent"])
            self.assertEqual(idempotent["snapshot_count"], 4)
            with self.assertRaises(SnapshotLifecycleError):
                self.register(store, snapshots[2], "S2-renamed", 2)
            duplicate_label_source = root / "duplicate-label-source"
            _write_snapshot(duplicate_label_source, [_activity("A5")])
            with self.assertRaises(SnapshotLifecycleError):
                self.register(store, duplicate_label_source, "S2", 5)

            first = build_approved_input(store, root / "build-a")
            second = build_approved_input(store, root / "build-b")
            self.assertEqual(
                first["canonical_build_sha256"],
                second["canonical_build_sha256"],
            )
            self.assertEqual(
                first["approved_input_content_sha256"],
                second["approved_input_content_sha256"],
            )
            self.assertEqual(_tree_hash(root / "build-a"), _tree_hash(root / "build-b"))
            self.assertEqual(first["approved_input"], "approved_input")
            for relative in (
                "canonical/canonical_merge_manifest.json",
                "canonical/snapshot_delta_report.json",
                "canonical/presence_pattern_report.json",
                "canonical/field_provenance.json",
                "canonical/review_holds.json",
                "canonical/approved_input_manifest.json",
                "approved_input/approved_input_manifest.json",
                "approved_input/snapshot_lineage.json",
                "approved_input/merge_summary.json",
            ):
                self.assertTrue((root / "build-a" / relative).is_file(), relative)

            merged = json.loads(
                (
                    root
                    / "build-a/approved_input/DI-Connect-Fitness/"
                    "snapshot_summarizedActivities.json"
                ).read_text(encoding="utf-8")
            )[0]["summarizedActivitiesExport"]
            by_id = {row["activityId"]: row for row in merged}
            self.assertEqual(set(by_id), {"A1", "A2", "A3", "A4"})
            self.assertEqual(by_id["A1"]["description"], "first")
            self.assertEqual(by_id["A1"]["name"], "updated")

            summary = first["merge_summary"]
            activities = summary["datasets"]["activities"]
            self.assertEqual(activities["presence_pattern_counts"]["1011"], 1)
            self.assertEqual(activities["reappeared_record_count"], 2)
            self.assertEqual(activities["canonical_record_count"], 4)
            self.assertFalse(summary["automatic_deletion"])
            self.assertFalse(summary["inference_performed"])
            holds = json.loads(
                (root / "build-a/canonical/review_holds.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(
                any(item["hold_type"] == "explicit_null_preserved_previous" for item in holds)
            )
            self.assertTrue(
                any(item["hold_type"] == "explicit_empty_preserved_previous" for item in holds)
            )
            self.assertTrue(
                any(
                    item["hold_type"] == "explicit_null_review_required"
                    and item["prior_explicit_value_preserved"] is False
                    for item in holds
                )
            )
            self.assertTrue(
                any(item["hold_type"] == "null_stable_key" for item in holds)
            )
            self.assertEqual(
                set(first["coverage"]["field_state_counts"]),
                {
                    "record_absent",
                    "field_absent",
                    "explicit_null",
                    "explicit_empty",
                    "explicit_value",
                    "parser_unsupported",
                    "extraction_failed",
                },
            )
            self.assertTrue(
                list((root / "build-a/approved_input/preserved_unknown").iterdir())
            )

    def test_performance_metrics_accumulate_without_private_fields_or_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            for day in range(1, 5):
                source = root / f"source-{day}"
                _write_snapshot(source, [_activity(f"A{day}")])
                if day in {1, 3}:
                    _write_performance_metrics(source, day)
                self.register(store, source, f"S{day}", day)

            build = build_approved_input(store, root / "build")
            approved = root / "build/approved_input"
            hill = json.loads(
                (approved / "DI-Connect-Metrics/snapshot_HillScore.json").read_text(
                    encoding="utf-8"
                )
            )
            endurance = json.loads(
                (
                    approved
                    / "DI-Connect-Metrics/snapshot_EnduranceScore.json"
                ).read_text(encoding="utf-8")
            )
            lactate = json.loads(
                (
                    approved
                    / "DI-Connect-Wellness/snapshot_userBioMetrics.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                [row["calendarDate"] for row in hill],
                ["2030-01-01", "2030-01-03"],
            )
            self.assertEqual(
                [row["calendarDate"] for row in endurance],
                ["2030-01-01", "2030-01-03"],
            )
            public_payload = json.dumps(
                {"hill": hill, "endurance": endurance, "lactate": lactate}
            )
            self.assertNotIn("PRIVATE-DEVICE", public_payload)
            self.assertNotIn("PRIVATE-ACCOUNT", public_payload)
            self.assertEqual(
                build["merge_summary"]["datasets"]["hill_score_daily"][
                    "previous_only_retained_count"
                ],
                2,
            )
            self.assertEqual(
                build["merge_summary"]["datasets"]["endurance_score_daily"][
                    "previous_only_retained_count"
                ],
                2,
            )
            policy = next(
                item
                for item in public_registry()["policies"]
                if item["dataset"] == "lactate_threshold_candidates"
            )
            self.assertFalse(policy["canonical_public_output"])
            self.assertEqual(
                policy["machine_stable_key_status"], "PRODUCT_DECISION_REQUIRED"
            )

    def test_performance_metric_same_day_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            for day, score in ((1, 71), (2, 99)):
                source = root / f"source-{day}"
                _write_snapshot(source, [_activity(f"A{day}")])
                metrics = source / "DI-Connect-Metrics"
                metrics.mkdir()
                (metrics / f"HillScore_conflict_{day}.json").write_text(
                    json.dumps(
                        [
                            {
                                "calendarDate": "2030-01-01",
                                "overallScore": score,
                                "strengthScore": 60,
                                "enduranceScore": 80,
                                "hillScoreClassificationId": 4,
                                "hillScoreFeedbackPhraseId": 12,
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                self.register(store, source, f"S{day}", day)

            with self.assertRaisesRegex(
                SnapshotMergeError,
                "canonical merge contains unresolved stop conflicts",
            ):
                build_approved_input(store, root / "build")
            self.assertFalse((root / "build").exists())

    def test_remaining_daily_metrics_are_retained_and_conflicts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            first = root / "source-1"
            _write_snapshot(first, [_activity("A1")])
            _write_remaining_daily_metrics(first, 1)
            self.register(store, first, "S1", 1)
            second = root / "source-2"
            _write_snapshot(second, [_activity("A1")])
            self.register(store, second, "S2", 2)
            build = build_approved_input(store, root / "build")
            expected_paths = {
                "race_prediction_daily": "DI-Connect-Metrics/RunRacePredictions_snapshot.json",
                "sleep_daily": "DI-Connect-Wellness/snapshot_sleepData.json",
                "uds_daily": "DI-Connect-Aggregator/UDSFile_snapshot.json",
                "acute_training_load_daily": "DI-Connect-Metrics/MetricsAcuteTrainingLoad_snapshot.json",
                "training_readiness_daily": "DI-Connect-Metrics/TrainingReadinessDTO_snapshot.json",
                "vo2max_daily": "DI-Connect-Metrics/snapshot_vo2max.json",
                "training_history_daily": "DI-Connect-Metrics/TrainingHistory_snapshot.json",
            }
            for dataset, relative_path in expected_paths.items():
                rows = json.loads(
                    (root / "build" / "approved_input" / relative_path).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(len(rows), 1)
                self.assertEqual(
                    build["merge_summary"]["datasets"][dataset][
                        "previous_only_retained_count"
                    ],
                    1,
                )

            conflict_store = root / "conflict-store"
            initialize_store(conflict_store, "synthetic-account-boundary")
            for day, value in ((1, 1000), (2, 1001)):
                source = root / f"conflict-{day}"
                _write_snapshot(source, [_activity(f"C{day}")])
                metrics = source / "DI-Connect-Metrics"
                metrics.mkdir()
                (metrics / f"RunRacePredictions_{day}.json").write_text(
                    json.dumps([{"calendarDate": "2030-02-01", "timestamp": "2030-02-01T06:00:00", "raceTime5K": value}]),
                    encoding="utf-8",
                )
                self.register(conflict_store, source, f"C{day}", day)
            with self.assertRaisesRegex(
                SnapshotMergeError,
                "canonical merge contains unresolved stop conflicts",
            ):
                build_approved_input(conflict_store, root / "conflict-build")

    def test_source_observation_union_preserves_same_day_distinct_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])
            metrics = source / "DI-Connect-Metrics"
            metrics.mkdir()
            (metrics / "RunRacePredictions_observations.json").write_text(
                json.dumps(
                    [
                        {
                            "calendarDate": "2030-02-01",
                            "timestamp": "2030-02-01T06:00:00",
                            "raceTime5K": 1000,
                        },
                        {
                            "calendarDate": "2030-02-01",
                            "timestamp": "2030-02-01T18:00:00",
                            "raceTime5K": 1001,
                        },
                    ]
                ),
                encoding="utf-8",
            )
            self.register(store, source, "S1", 1)
            build = build_approved_input(store, root / "build")
            rows = json.loads(
                (
                    root
                    / "build/approved_input/DI-Connect-Metrics/"
                    "RunRacePredictions_snapshot.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                build["merge_summary"]["datasets"]["race_prediction_daily"][
                    "canonical_record_count"
                ],
                2,
            )

    def test_performance_metric_calendar_date_encodings_share_one_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            for day, calendar_date in (
                (1, "2026-01-01"),
                (2, 1_767_225_600_000),
            ):
                source = root / f"source-{day}"
                _write_snapshot(source, [_activity(f"A{day}")])
                metrics = source / "DI-Connect-Metrics"
                metrics.mkdir()
                (metrics / f"HillScore_encoding_{day}.json").write_text(
                    json.dumps(
                        [
                            {
                                "calendarDate": calendar_date,
                                "overallScore": 71,
                                "strengthScore": 60,
                                "enduranceScore": 80,
                                "hillScoreClassificationId": 4,
                                "hillScoreFeedbackPhraseId": 12,
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                self.register(store, source, f"S{day}", day)

            build = build_approved_input(store, root / "build")
            hill = json.loads(
                (
                    root
                    / "build/approved_input/DI-Connect-Metrics/"
                    "snapshot_HillScore.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(len(hill), 1)
            self.assertEqual(hill[0]["calendarDate"], "2026-01-01")
            self.assertEqual(
                build["merge_summary"]["datasets"]["hill_score_daily"][
                    "canonical_record_count"
                ],
                1,
            )

    def test_archive_inventory_fit_dedup_and_run_all_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            fit_payload = b"synthetic-non-fit-evidence"
            for day, archive in ((1, True), (2, False)):
                source = root / f"source-{day}"
                _write_snapshot(
                    source,
                    [_activity("A1")],
                    fit_payload=fit_payload,
                    archive=archive,
                )
                self.register(store, source, f"S{day}", day)

            build = build_approved_input(store, root / "build")
            self.assertEqual(
                build["merge_summary"]["fit"]["source_alias_count"],
                2,
            )
            self.assertEqual(
                build["merge_summary"]["fit"]["unique_blob_count"],
                1,
            )
            self.assertEqual(
                len(list((root / "build/approved_input").rglob("*.fit"))),
                1,
            )

            output = root / "output"
            result = run_snapshot_all(store, output)
            self.assertEqual(result["status"], "PARTIAL_SUCCESS")
            self.assertEqual(result["snapshot_count"], 2)
            self.assertEqual(result["store_verification"], "PASS")
            self.assertTrue((output / "snapshot/snapshot_lineage.json").is_file())
            self.assertTrue((output / "snapshot/snapshot_coverage.json").is_file())
            self.assertIn(
                "Snapshot Accumulation",
                (output / "START_HERE.md").read_text(encoding="utf-8"),
            )
            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("- Snapshot labels: S1, S2", start_here)
            self.assertIn("- Automatic deletion: No", start_here)
            self.assertIn("- Inference performed: No", start_here)
            self.assertIn("Previous-only retained", start_here)
            self.assertIn("Unknown or unsupported objects preserved", start_here)
            self.assertIn("Explicit null reviews:", start_here)
            self.assertIn("Explicit empty reviews:", start_here)
            self.assertIn("Coverage gaps:", start_here)
            self.assertIn("Canonical completeness boundary:", start_here)
            for document_name in (
                "DATASET_INVENTORY.md",
                "ANALYSIS_HANDOFF.md",
            ):
                document = (output / document_name).read_text(encoding="utf-8")
                self.assertIn("## Snapshot Accumulation", document)
                self.assertIn("- Snapshot labels: S1, S2", document)
                self.assertIn("Explicit null reviews:", document)
                self.assertIn("Explicit empty reviews:", document)
                self.assertIn("Coverage gaps:", document)
                self.assertIn("Canonical completeness boundary:", document)
                self.assertIn("- Automatic deletion: No", document)
                self.assertIn("- Inference performed: No", document)
            context = json.loads(
                (output / "ANALYSIS_CONTEXT.json").read_text(encoding="utf-8")
            )
            self.assertTrue(context["snapshot_lifecycle"]["enabled"])
            self.assertFalse(context["snapshot_lifecycle"]["automatic_deletion"])
            self.assertFalse(context["snapshot_lifecycle"]["inference_performed"])
            self.assertEqual(
                context["snapshot_lifecycle"]["snapshot_labels"],
                ["S1", "S2"],
            )
            self.assertEqual(
                set(context["snapshot_lifecycle"]["field_state_counts"]),
                {
                    "record_absent",
                    "field_absent",
                    "explicit_null",
                    "explicit_empty",
                    "explicit_value",
                    "parser_unsupported",
                    "extraction_failed",
                },
            )
            self.assertIn(
                "explicit_null_review_count",
                context["snapshot_lifecycle"],
            )
            self.assertIn(
                "explicit_empty_review_count",
                context["snapshot_lifecycle"],
            )
            self.assertIn("coverage_gap_count", context["snapshot_lifecycle"])
            self.assertIn(
                "canonical_completeness_boundary",
                context["snapshot_lifecycle"],
            )

    def test_malformed_supported_json_is_extraction_failed_not_deletion(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])
            malformed = (
                source
                / "DI-Connect-Fitness/synthetic_summarizedActivities.json"
            )
            malformed.write_text("{malformed-json", encoding="utf-8")
            source_hash_before = _tree_hash(source)
            self.register(store, source, "S1", 1)

            with self.assertRaisesRegex(
                SnapshotMergeError,
                "supported source extraction failed",
            ):
                build_approved_input(store, root / "build")

            self.assertEqual(_tree_hash(source), source_hash_before)
            self.assertFalse((root / "build").exists())
            self.assertEqual(verify_store(store)["status"], "PASS")

    def test_oversized_canonical_activities_are_partitioned_for_run_all(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            rows = [
                _activity(
                    f"A{index:03d}",
                    description="synthetic-" + ("x" * 256),
                    startTimeGmt=1893456000000 + index * 60_000,
                )
                for index in range(24)
            ]
            source = root / "source"
            _write_snapshot(source, rows)
            self.register(store, source, "S1", 1)

            synthetic_limit = 2_048
            with patch(
                "garmin_running_data_normalizer.snapshot.merge."
                "APPROVED_INPUT_MAX_FILE_BYTES",
                synthetic_limit,
            ):
                first = build_approved_input(store, root / "build-a")
                second = build_approved_input(store, root / "build-b")
                activity_parts = sorted(
                    (
                        root
                        / "build-a/approved_input/DI-Connect-Fitness"
                    ).glob("*summarizedActivities.json")
                )
                self.assertGreater(len(activity_parts), 1)
                self.assertTrue(
                    all(
                        part.stat().st_size <= synthetic_limit
                        for part in activity_parts
                    )
                )
                self.assertEqual(
                    first["approved_input_content_sha256"],
                    second["approved_input_content_sha256"],
                )
                self.assertEqual(
                    _tree_hash(root / "build-a"),
                    _tree_hash(root / "build-b"),
                )
                result = run_snapshot_all(store, root / "output")

            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
            activities = json.loads(
                (
                    root / "output/normalized/activities.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(len(activities), len(rows))

    def test_single_oversized_canonical_activity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            source = root / "source"
            _write_snapshot(
                source,
                [
                    _activity(
                        "A1",
                        description="synthetic-" + ("x" * 4_096),
                    )
                ],
            )
            self.register(store, source, "S1", 1)

            with patch(
                "garmin_running_data_normalizer.snapshot.merge."
                "APPROVED_INPUT_MAX_FILE_BYTES",
                1_024,
            ):
                with self.assertRaisesRegex(
                    SnapshotMergeError,
                    "record exceeds the intake file-size limit",
                ):
                    build_approved_input(store, root / "build")

            self.assertFalse((root / "build").exists())

    def test_fail_closed_boundaries_and_policy_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])
            with self.assertRaises(SnapshotLifecycleError):
                register_snapshot(
                    store,
                    source,
                    snapshot_label="S1",
                    export_requested_at="2030-01-01T00:00:00+00:00",
                    export_downloaded_at="2030-01-01T01:00:00+00:00",
                    export_observed_at="2030-01-01T02:00:00+00:00",
                    confirm_complete=False,
                )
            with self.assertRaises(SnapshotLifecycleError):
                initialize_store(store, "different-account-boundary")
            symlink_source = root / "symlink-source"
            _write_snapshot(symlink_source, [_activity("A2")])
            (symlink_source / "linked-directory").symlink_to(
                symlink_source / "DI-Connect-Fitness",
                target_is_directory=True,
            )
            with self.assertRaises(SnapshotLifecycleError):
                self.register(store, symlink_source, "SYMLINK", 2)
            self.register(store, source, "S1", 1)
            with self.assertRaises(SnapshotMergeError):
                build_approved_input(store, root / "empty-output")
                build_approved_input(store, root / "empty-output")

            registry = public_registry()
            disk_registry = json.loads(
                (
                    Path(__file__).resolve().parents[1]
                    / "config/garmin_snapshot_dataset_merge_policies_v1.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(registry, disk_registry)
            self.assertEqual(
                registry["defaults"]["absence_policy"],
                "missing_is_not_delete",
            )
            self.assertEqual(
                registry["defaults"]["deletion_policy"],
                "no_automatic_delete",
            )
            (store / "registry.json").write_text("{", encoding="utf-8")
            verification = verify_store(store)
            self.assertEqual(verification["status"], "FAIL")
            self.assertIn(
                "snapshot_registry_metadata_failure",
                verification["failures"],
            )

    def test_corrupt_archive_lock_integrity_and_same_order_conflict_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")

            corrupt = root / "corrupt"
            corrupt.mkdir()
            (corrupt / "broken.zip").write_bytes(b"not-a-zip")
            with self.assertRaises(SnapshotLifecycleError):
                self.register(store, corrupt, "BAD", 1)
            unsafe = root / "unsafe"
            unsafe.mkdir()
            with zipfile.ZipFile(unsafe / "unsafe.zip", "w") as archive:
                archive.writestr("../escape.json", "{}")
            with self.assertRaises(SnapshotLifecycleError):
                self.register(store, unsafe, "UNSAFE", 1)

            locked = root / "locked"
            _write_snapshot(locked, [_activity("A1")])
            (store / ".single-writer.lock").write_text("synthetic\n", encoding="ascii")
            with self.assertRaises(SnapshotLifecycleError):
                self.register(store, locked, "LOCKED", 1)
            (store / ".single-writer.lock").unlink()

            conflict = root / "conflict"
            _write_snapshot(
                conflict,
                [
                    _activity("A1", name="first"),
                    _activity("A1", name="divergent"),
                ],
            )
            self.register(store, conflict, "S1", 1)
            with self.assertRaises(SnapshotMergeError):
                build_approved_input(store, root / "conflict-build")

            manifest = next((store / "snapshots").glob("*/manifest.json"))
            inventory = json.loads(manifest.read_text(encoding="utf-8"))["objects"]
            blob = store / inventory[0]["blob_relative_path"]
            blob.unlink()
            verification = verify_store(store)
            self.assertEqual(verification["status"], "FAIL")
            self.assertIn("immutable_blob_integrity_failure", verification["failures"])

    def test_cli_contract_accepts_specification_option_names(self) -> None:
        from garmin_running_data_normalizer.runner import build_parser

        parser = build_parser()
        init_args = parser.parse_args(
            [
                "snapshot",
                "init",
                "--store",
                "store",
                "--account",
                "opaque-account",
            ]
        )
        self.assertEqual(init_args.account_store_id, "opaque-account")
        register_args = parser.parse_args(
            [
                "snapshot",
                "register",
                "--store",
                "store",
                "--input",
                "input",
                "--label",
                "S1",
                "--requested-at",
                "2030-01-01T00:00:00+00:00",
                "--downloaded-at",
                "2030-01-01T01:00:00+00:00",
                "--observed-at",
                "2030-01-01T02:00:00+00:00",
                "--confirm-complete",
            ]
        )
        self.assertEqual(
            register_args.export_observed_at,
            "2030-01-01T02:00:00+00:00",
        )

    def test_integrity_binding_journal_and_build_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])

            completion_store = root / "completion-store"
            initialize_store(completion_store, "synthetic-account-boundary")
            self.register(completion_store, source, "S1", 1)
            completion_manifest = next(
                (completion_store / "snapshots").glob("*/manifest.json")
            )
            completion_value = json.loads(
                completion_manifest.read_text(encoding="utf-8")
            )
            completion_value["export_completion_confirmed"] = False
            completion_manifest.chmod(0o600)
            completion_manifest.write_text(
                json.dumps(completion_value),
                encoding="utf-8",
            )
            self.assertEqual(verify_store(completion_store)["status"], "FAIL")
            with self.assertRaises(SnapshotMergeError):
                build_approved_input(completion_store, root / "completion-build")

            journal_store = root / "journal-store"
            initialize_store(journal_store, "synthetic-account-boundary")
            self.register(journal_store, source, "S1", 1)
            (journal_store / "journal/registration.json").write_text(
                json.dumps(
                    {
                        "format": "snapshot-registration-journal-v1",
                        "snapshot_id": "snapshot-interrupted",
                        "phase": "preserving_blobs",
                    }
                ),
                encoding="utf-8",
            )
            journal_verification = verify_store(journal_store)
            self.assertEqual(journal_verification["status"], "FAIL")
            self.assertIn(
                "incomplete_registration_journal_present",
                journal_verification["failures"],
            )
            source_two = root / "source-two"
            _write_snapshot(source_two, [_activity("A2")])
            recovered = self.register(journal_store, source_two, "S2", 2)
            self.assertEqual(
                recovered["recovery_status"],
                "incomplete_registration_reconciled",
            )
            self.assertEqual(verify_store(journal_store)["status"], "PASS")

            registry_store = root / "registry-store"
            initialize_store(registry_store, "synthetic-account-boundary")
            self.register(registry_store, source, "S1", 1)
            (registry_store / "registry.json").write_text(
                json.dumps({"format": "tampered", "snapshots": []}),
                encoding="utf-8",
            )
            self.assertEqual(verify_store(registry_store)["status"], "FAIL")
            with self.assertRaises(SnapshotMergeError):
                build_approved_input(registry_store, root / "registry-build")

            path_store = root / "path-store"
            initialize_store(path_store, "synthetic-account-boundary")
            self.register(path_store, source, "S1", 1)
            path_manifest = next((path_store / "snapshots").glob("*/manifest.json"))
            path_value = json.loads(path_manifest.read_text(encoding="utf-8"))
            path_value["objects"][0]["blob_relative_path"] = "../../outside"
            path_manifest.chmod(0o600)
            path_manifest.write_text(json.dumps(path_value), encoding="utf-8")
            path_verification = verify_store(path_store)
            self.assertEqual(path_verification["status"], "FAIL")
            self.assertIn(
                "snapshot_inventory_contract_failure",
                path_verification["failures"],
            )

    def test_store_safety_flags_and_blob_symlinks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])

            policy_store = root / "policy-store"
            initialize_store(policy_store, "synthetic-account-boundary")
            store_metadata_path = policy_store / "store.json"
            store_metadata = json.loads(
                store_metadata_path.read_text(encoding="utf-8")
            )
            store_metadata["automatic_deletion"] = True
            store_metadata_path.write_text(
                json.dumps(store_metadata),
                encoding="utf-8",
            )
            with self.assertRaises(SnapshotLifecycleError):
                self.register(policy_store, source, "S1", 1)
            self.assertEqual(verify_store(policy_store)["status"], "FAIL")
            with self.assertRaises(SnapshotMergeError):
                build_approved_input(policy_store, root / "policy-build")

            symlink_store = root / "symlink-store"
            initialize_store(symlink_store, "synthetic-account-boundary")
            source_blob = (
                source
                / "DI-Connect-Fitness"
                / "synthetic_summarizedActivities.json"
            )
            digest = hashlib.sha256(source_blob.read_bytes()).hexdigest()
            external_blob = root / "external-matching-blob"
            external_blob.write_bytes(source_blob.read_bytes())
            external_before = external_blob.read_bytes()
            blob_destination = (
                symlink_store / "blobs" / "sha256" / digest[:2] / digest
            )
            blob_destination.parent.mkdir(parents=True)
            blob_destination.symlink_to(external_blob)
            with self.assertRaises(SnapshotLifecycleError):
                self.register(symlink_store, source, "S1", 1)
            symlink_verification = verify_store(symlink_store)
            self.assertEqual(symlink_verification["status"], "FAIL")
            self.assertIn(
                "immutable_blob_symlink_failure",
                symlink_verification["failures"],
            )
            with self.assertRaises(SnapshotMergeError):
                build_approved_input(symlink_store, root / "symlink-build")
            self.assertEqual(external_blob.read_bytes(), external_before)

            parent_store = root / "parent-symlink-store"
            initialize_store(parent_store, "synthetic-account-boundary")
            external_prefix = root / "external-prefix"
            external_prefix.mkdir()
            (external_prefix / digest).write_bytes(source_blob.read_bytes())
            blob_prefix = parent_store / "blobs" / "sha256" / digest[:2]
            blob_prefix.symlink_to(external_prefix, target_is_directory=True)
            with self.assertRaises(SnapshotLifecycleError):
                self.register(parent_store, source, "S1", 1)
            parent_verification = verify_store(parent_store)
            self.assertEqual(parent_verification["status"], "FAIL")
            self.assertIn(
                "immutable_blob_symlink_failure",
                parent_verification["failures"],
            )

            for name, structural_relative in (
                ("blob-root", Path("blobs")),
                ("sha-root", Path("blobs/sha256")),
            ):
                structural_store = root / f"{name}-symlink-store"
                initialize_store(
                    structural_store,
                    "synthetic-account-boundary",
                )
                structural_path = structural_store / structural_relative
                if structural_relative == Path("blobs"):
                    (structural_path / "sha256").rmdir()
                structural_path.rmdir()
                external_structure = root / f"external-{name}"
                external_structure.mkdir()
                if structural_relative == Path("blobs"):
                    (external_structure / "sha256").mkdir()
                structural_path.symlink_to(
                    external_structure,
                    target_is_directory=True,
                )
                structural_verification = verify_store(structural_store)
                self.assertEqual(structural_verification["status"], "FAIL")
                self.assertIn(
                    "immutable_blob_symlink_failure",
                    structural_verification["failures"],
                )
                with self.assertRaises(SnapshotLifecycleError):
                    self.register(structural_store, source, "S1", 1)
                with self.assertRaises(SnapshotMergeError):
                    build_approved_input(
                        structural_store,
                        root / f"{name}-build",
                    )


if __name__ == "__main__":
    unittest.main()
