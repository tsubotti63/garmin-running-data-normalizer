from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from garmin_running_data_normalizer.output_experience import (
    DOCUMENT_NAMES,
    MANIFEST_OUTPUT_PATHS,
    MACHINE_CONTEXT_NAMES,
    OutputExperienceError,
    RELATIONSHIP_CONTRACTS,
    build_analysis_context,
    build_schema_catalog,
    render_analysis_handoff,
    render_output_experience_artifacts,
    render_output_experience_documents,
    render_start_here,
    validate_registry_alignment,
)
from garmin_running_data_normalizer.run_all import (
    DATASET_PATHS,
    DATASET_TABLE,
    OUTPUT_PATHS,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/fixtures/output_experience"


def synthetic_projection_input() -> tuple[dict, dict, dict]:
    counts = {
        "activities": 2,
        "gear": 1,
        "activity_gear": 1,
        "personal_records": 1,
        "fit_sessions": 1,
        "fit_laps": 2,
        "activity_fit_links": 1,
    }
    manifest = {
        "format": "garmin-running-data-normalizer-run-manifest-v1",
        "product_version": "1.1.0rc1",
        "run_all_version": 1,
        "input_assets": [
            {
                "source_path": "private/SYNTHETIC-ACTIVITY.json",
                "sha256": "private-source-hash",
            }
        ],
        "datasets": [
            {
                "name": item["name"],
                "record_grain": item["record_grain"],
                "stable_key": list(item["stable_key"]),
                "record_count": counts[item["name"]],
            }
            for item in DATASET_TABLE
        ],
        "outputs": [
            {"path": path, "sha256": f"private-output-hash-{index}"}
            for index, path in enumerate(MANIFEST_OUTPUT_PATHS)
        ],
        "deterministic_output_digest": "synthetic-digest",
    }
    summary = {
        "format": "garmin-running-data-normalizer-run-summary-v1",
        "product_version": "1.1.0rc1",
        "run_all_version": 1,
        "status": "PASS",
        "family_results": {
            "activities": {
                "status": "PROCESSED",
                "detected_asset_count": 1,
                "processed_asset_count": 1,
                "skipped_asset_count": 0,
                "record_count": 2,
                "warning_count": 0,
                "error_count": 0,
            },
            "gear": {
                "status": "PROCESSED",
                "detected_asset_count": 1,
                "processed_asset_count": 1,
                "skipped_asset_count": 0,
                "record_count": 2,
                "warning_count": 0,
                "error_count": 0,
            },
            "personal_records": {
                "status": "PROCESSED",
                "detected_asset_count": 1,
                "processed_asset_count": 1,
                "skipped_asset_count": 0,
                "record_count": 1,
                "warning_count": 0,
                "error_count": 0,
            },
            "fit": {
                "status": "PROCESSED",
                "detected_asset_count": 1,
                "processed_asset_count": 1,
                "skipped_asset_count": 0,
                "incomplete_asset_count": 0,
                "record_count": 4,
                "warning_count": 0,
                "error_count": 0,
            },
        },
        "warning_count": 0,
        "error_count": 0,
        "warnings": [],
        "errors": [],
        "generated_paths": list(OUTPUT_PATHS),
        "deterministic_output_digest": "synthetic-digest",
    }
    relationship_summary = {
        "status": "PASS",
        "relationships": {
            "activity_gear_to_activities": {
                "status": "explicit",
                "link_count": 1,
                "eligible_count": 1,
                "coverage": 1.0,
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "activity_gear_to_gear": {
                "status": "explicit",
                "link_count": 1,
                "eligible_count": 1,
                "coverage": 1.0,
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "personal_records_to_activities": {
                "status": "explicit",
                "link_count": 1,
                "eligible_count": 1,
                "coverage": 1.0,
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "fit_laps_to_fit_sessions": {
                "status": "explicit",
                "link_count": 2,
                "eligible_count": 2,
                "coverage": 1.0,
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "activities_to_fit_sessions": {
                "relationship_status": "explicit",
                "link_count": 1,
                "eligible_activity_count": 2,
                "eligible_fit_session_count": 1,
                "eligible_activity_coverage": 0.5,
                "eligible_fit_session_coverage": 1.0,
                "unresolved_eligible_activity_count": 1,
                "unresolved_eligible_fit_session_count": 0,
                "ambiguous_activity_count": 0,
                "ambiguous_fit_session_count": 0,
                "duplicate_mapping_count": 0,
                "inference_performed": False,
                "primary_unresolved_activity_reason": (
                    "no_evidence_qualified_candidate"
                ),
                "primary_unresolved_fit_session_reason": None,
            },
        },
    }
    return manifest, summary, relationship_summary


class OutputExperienceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            (ROOT / "config/dataset_registry.example.json").read_text(encoding="utf-8")
        )

    def test_projection_is_deterministic_and_matches_golden_files(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        first = render_output_experience_documents(manifest, summary, self.registry, relationship_summary)
        second = render_output_experience_documents(
            copy.deepcopy(manifest),
            copy.deepcopy(summary),
            copy.deepcopy(self.registry),
            copy.deepcopy(relationship_summary),
        )
        self.assertEqual(first, second)
        self.assertEqual(tuple(first), DOCUMENT_NAMES)
        for name, rendered in first.items():
            expected = (GOLDEN / name).read_text(encoding="utf-8")
            self.assertEqual(rendered, expected, name)

    def test_handoff_explains_fail_closed_multi_session_allocation(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        handoff = render_analysis_handoff(
            manifest,
            summary,
            self.registry,
            relationship_summary,
        )
        self.assertIn("CRC-valid multi-session FIT files", handoff)
        self.assertIn("session_lap_allocation_conflict", handoff)
        self.assertIn("do not enter the eligible", handoff)
        self.assertIn("Activity/FIT Relationship Coverage population", handoff)

    def test_registry_and_documents_cover_the_runtime_dataset_contract(self) -> None:
        validate_registry_alignment(self.registry)
        catalog = (ROOT / "docs/supported_datasets.md").read_text(encoding="utf-8")
        relationships = (ROOT / "docs/dataset_relationships.md").read_text(
            encoding="utf-8"
        )
        for dataset in DATASET_TABLE:
            self.assertIn(f"`{dataset['name']}`", catalog)
            self.assertIn(f"`{DATASET_PATHS[dataset['name']]}`", relationships)
            for field in dataset["stable_key"]:
                self.assertIn(f"`{field}`", catalog)
        self.assertIn("`explicit`", relationships)
        self.assertIn("`not_yet_defined`", relationships)
        explicit_rows = [
            line
            for line in relationships.splitlines()
            if "| `explicit`" in line
        ]
        self.assertEqual(len(explicit_rows), len(RELATIONSHIP_CONTRACTS))
        for contract in RELATIONSHIP_CONTRACTS:
            left_path = f"`{DATASET_PATHS[contract['left_dataset']]}`"
            right_path = f"`{DATASET_PATHS[contract['right_dataset']]}`"
            self.assertTrue(
                any(
                    left_path in row and right_path in row
                    for row in explicit_rows
                ),
                contract["relationship_id"],
            )

    def test_renderer_preparation_does_not_expand_run_all_output_paths(self) -> None:
        self.assertEqual(
            OUTPUT_PATHS,
            (
                "normalized/activities.json",
                "normalized/gear.json",
                "normalized/activity_gear.json",
                "normalized/personal_records.json",
                "normalized/fit_sessions.json",
                "normalized/fit_laps.json",
                "normalized/activity_fit_links.json",
                "audit/fit_audit.json",
                "audit/activity_fit_linkage.json",
                "analysis/activities.csv",
                "qa/dataset_summary.json",
                "qa/relationship_summary.json",
                "START_HERE.md",
                "DATASET_INVENTORY.md",
                "ANALYSIS_HANDOFF.md",
                "ANALYSIS_CONTEXT.json",
                "SCHEMA_CATALOG.json",
                "artifact_inventory.json",
                "run_manifest.json",
                "run_summary.json",
            ),
        )
        self.assertTrue(set((*DOCUMENT_NAMES, *MACHINE_CONTEXT_NAMES)).issubset(OUTPUT_PATHS))

    def test_projection_does_not_expose_source_details_or_hash_values(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        rendered = "\n".join(
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary).values()
        )
        self.assertNotIn("private/SYNTHETIC-ACTIVITY.json", rendered)
        self.assertNotIn("private-source-hash", rendered)
        self.assertNotIn("private-output-hash", rendered)
        self.assertNotRegex(rendered, r"/(?:Users|home)/[^\s]+")

    def test_projection_rejects_manifest_contract_drift(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        manifest["datasets"][0]["stable_key"] = ["activity_id"]
        with self.assertRaisesRegex(OutputExperienceError, "manifest stable key mismatch"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

    def test_projection_rejects_registry_contract_drift(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        registry = copy.deepcopy(self.registry)
        registry["datasets"][0]["record_grain"] = "unknown"
        with self.assertRaisesRegex(OutputExperienceError, "registry record grain mismatch"):
            render_output_experience_documents(manifest, summary, registry, relationship_summary)

    def test_projection_rejects_family_count_and_status_drift(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["gear"]["record_count"] = 999
        with self.assertRaisesRegex(
            OutputExperienceError, "family record count does not match"
        ):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["activities"]["status"] = "SKIPPED_NOT_PRESENT"
        with self.assertRaisesRegex(
            OutputExperienceError, "family status contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["gear"]["status"] = "PROCESSED_EMPTY"
        with self.assertRaisesRegex(
            OutputExperienceError, "family status contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["gear"]["status"] = "SKIPPED_NOT_PRESENT"
        with self.assertRaisesRegex(
            OutputExperienceError, "family status contradicts asset"
        ):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["gear"]["warning_count"] = 3
        with self.assertRaisesRegex(
            OutputExperienceError, "family warning count contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        for name in ("gear", "activity_gear"):
            next(
                item for item in manifest["datasets"] if item["name"] == name
            )["record_count"] = 0
        summary["family_results"]["gear"].update(
            {
                "status": "SKIPPED_NOT_PRESENT",
                "detected_asset_count": 0,
                "processed_asset_count": 0,
                "record_count": 0,
                "warning_count": 1,
            }
        )
        summary["warning_count"] = 1
        summary["warnings"] = [{"code": "OPTIONAL_FAMILY_NOT_PRESENT"}]
        with self.assertRaisesRegex(
            OutputExperienceError, "run status contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

    def test_projection_accepts_supported_optional_and_partial_states(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        for dataset in manifest["datasets"]:
            if dataset["name"] != "activities":
                dataset["record_count"] = 0
        for family in ("gear", "personal_records", "fit"):
            summary["family_results"][family].update(
                {
                    "status": "SKIPPED_NOT_PRESENT",
                    "detected_asset_count": 0,
                    "processed_asset_count": 0,
                    "record_count": 0,
                    "warning_count": 1,
                }
            )
        summary["warning_count"] = 3
        summary["warnings"] = [
            {"code": "OPTIONAL_FAMILY_NOT_PRESENT", "family": family}
            for family in ("gear", "personal_records", "fit")
        ]
        summary["status"] = "PASS_WITH_WARNINGS"
        rendered = render_output_experience_documents(
            manifest,
            summary,
            self.registry,
            relationship_summary,
        )
        self.assertIn("`SKIPPED_NOT_PRESENT`", rendered["START_HERE.md"])

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["fit"].update(
            {
                "status": "PARTIAL",
                "detected_asset_count": 2,
                "processed_asset_count": 2,
                "skipped_asset_count": 1,
                "incomplete_asset_count": 1,
                "warning_count": 1,
            }
        )
        summary["warning_count"] = 1
        summary["warnings"] = [{"code": "FIT_PARSE_INCOMPLETE", "family": "fit"}]
        summary["status"] = "PARTIAL_SUCCESS"
        rendered = render_output_experience_documents(
            manifest,
            summary,
            self.registry,
            relationship_summary,
        )
        self.assertIn("`PARTIAL_SUCCESS`", rendered["START_HERE.md"])
        self.assertIn("`PARTIAL`", rendered["DATASET_INVENTORY.md"])

    def test_projection_rejects_unsafe_or_changed_output_paths(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        manifest["outputs"][0]["path"] = "/private/activities.json"
        with self.assertRaisesRegex(OutputExperienceError, "safe relative path"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["generated_paths"] = [*summary["generated_paths"], "START_HERE.md"]
        with self.assertRaisesRegex(OutputExperienceError, "do not match Run-All v1"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        manifest["outputs"].append({"path": "extra.json"})
        with self.assertRaisesRegex(OutputExperienceError, "do not match Run-All v1"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

    def test_projection_rejects_incomplete_or_unfinished_runs(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["status"] = "FAIL"
        with self.assertRaisesRegex(OutputExperienceError, "completed handoff status"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

    def test_machine_context_covers_runtime_schema_and_relationships(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        context = build_analysis_context(manifest, summary, self.registry, relationship_summary)
        schema = build_schema_catalog(manifest, summary, self.registry)
        self.assertEqual(
            {item["name"] for item in context["datasets"]},
            {item["name"] for item in DATASET_TABLE},
        )
        self.assertEqual(
            {item["dataset"] for item in schema["datasets"]},
            {item["name"] for item in DATASET_TABLE},
        )
        flexible_identifier_fields = {
            descriptor["field"]: descriptor["logical_type"]
            for dataset in schema["datasets"]
            for descriptor in dataset["fields"]
            if descriptor["field"]
            in {"activity_id", "gear_key", "personal_record_id"}
        }
        self.assertEqual(
            flexible_identifier_fields,
            {
                "activity_id": "integer|string",
                "gear_key": "integer|string",
                "personal_record_id": "integer|string",
            },
        )
        self.assertEqual(len(context["relationships"]), 6)
        self.assertEqual(len(context["relationship_coverage"]), 6)
        activity_coverage = next(
            item
            for item in context["relationship_coverage"]
            if item["relationship_id"] == "activity_fit_links_to_activities"
        )
        self.assertEqual(
            activity_coverage["eligible_population"],
            {"label": "Activities", "count": 2},
        )
        self.assertEqual(activity_coverage["explicit_links"], 1)
        self.assertEqual(activity_coverage["coverage_percentage"], 50.0)
        self.assertEqual(activity_coverage["unresolved_count"], 1)
        self.assertEqual(activity_coverage["ambiguous_count"], 0)
        self.assertEqual(activity_coverage["duplicate_count"], 0)
        self.assertFalse(activity_coverage["inference_performed"])
        self.assertEqual(
            activity_coverage["primary_unresolved_reason"],
            "no_evidence_qualified_candidate",
        )
        self.assertEqual(
            activity_coverage["qa_reference"],
            "qa/relationship_summary.json",
        )
        self.assertEqual(context["product_version"], "1.1.0rc1")
        self.assertNotIn("not_yet_defined", json.dumps(context))
        rendered = render_output_experience_artifacts(
            manifest,
            summary,
            self.registry,
            relationship_summary,
        )
        self.assertEqual(
            set(rendered),
            set((*DOCUMENT_NAMES, *MACHINE_CONTEXT_NAMES)),
        )

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["deterministic_output_digest"] = "different"
        with self.assertRaisesRegex(OutputExperienceError, "digests do not match"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

        manifest, summary, relationship_summary = synthetic_projection_input()
        summary["family_results"]["activities"]["record_count"] = "2"
        with self.assertRaisesRegex(OutputExperienceError, "record count"):
            render_output_experience_documents(manifest, summary, self.registry, relationship_summary)

    def test_relationship_coverage_fails_closed_on_qa_drift(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        relationship_summary["relationships"]["activities_to_fit_sessions"][
            "eligible_activity_coverage"
        ] = 1.0
        with self.assertRaisesRegex(
            OutputExperienceError,
            "coverage contradicts counts",
        ):
            render_output_experience_documents(
                manifest,
                summary,
                self.registry,
                relationship_summary,
            )

        manifest, summary, relationship_summary = synthetic_projection_input()
        relationship_summary["relationships"]["activity_gear_to_activities"][
            "inference_performed"
        ] = True
        with self.assertRaisesRegex(
            OutputExperienceError,
            "must explicitly prohibit inference",
        ):
            render_output_experience_documents(
                manifest,
                summary,
                self.registry,
                relationship_summary,
            )

    def test_relationship_coverage_rejects_duplicate_count_drift_in_all_targets(
        self,
    ) -> None:
        renderers = {
            "START_HERE.md": render_start_here,
            "ANALYSIS_HANDOFF.md": render_analysis_handoff,
            "ANALYSIS_CONTEXT.json": build_analysis_context,
        }
        for target, renderer in renderers.items():
            with self.subTest(target=target):
                manifest, summary, relationship_summary = (
                    synthetic_projection_input()
                )
                relationship_summary["relationships"][
                    "activity_gear_to_activities"
                ]["duplicate_count"] = 999
                with self.assertRaisesRegex(
                    OutputExperienceError,
                    "duplicate count exceeds unresolved population",
                ):
                    renderer(
                        manifest,
                        summary,
                        self.registry,
                        relationship_summary,
                    )

    def test_relationship_coverage_preserves_public_safe_unresolved_counts(self) -> None:
        manifest, summary, relationship_summary = synthetic_projection_input()
        metrics = relationship_summary["relationships"][
            "activities_to_fit_sessions"
        ]
        metrics.update(
            {
                "link_count": 3463,
                "eligible_activity_count": 3466,
                "eligible_fit_session_count": 3466,
                "eligible_activity_coverage": 3463 / 3466,
                "eligible_fit_session_coverage": 3463 / 3466,
                "unresolved_eligible_activity_count": 3,
                "unresolved_eligible_fit_session_count": 3,
                "primary_unresolved_activity_reason": (
                    "no_evidence_qualified_candidate"
                ),
                "primary_unresolved_fit_session_reason": (
                    "no_evidence_qualified_candidate"
                ),
            }
        )
        context = build_analysis_context(
            manifest,
            summary,
            self.registry,
            relationship_summary,
        )
        activity_coverage = next(
            item
            for item in context["relationship_coverage"]
            if item["relationship_id"] == "activity_fit_links_to_activities"
        )
        self.assertEqual(activity_coverage["explicit_links"], 3463)
        self.assertEqual(activity_coverage["coverage_percentage"], 99.9134)
        self.assertEqual(activity_coverage["unresolved_count"], 3)
        rendered = render_output_experience_documents(
            manifest,
            summary,
            self.registry,
            relationship_summary,
        )
        self.assertIn("- Eligible population: 3466 (Activities)", rendered["START_HERE.md"])
        self.assertIn("- Explicit links: 3463", rendered["START_HERE.md"])
        self.assertIn("- Coverage: 99.91%", rendered["START_HERE.md"])
        self.assertIn("- Unresolved: 3", rendered["START_HERE.md"])


if __name__ == "__main__":
    unittest.main()
