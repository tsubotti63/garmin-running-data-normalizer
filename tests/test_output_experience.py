from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from garmin_running_data_normalizer.output_experience import (
    DOCUMENT_NAMES,
    OutputExperienceError,
    render_output_experience_documents,
    validate_registry_alignment,
)
from garmin_running_data_normalizer.run_all import (
    DATASET_PATHS,
    DATASET_TABLE,
    OUTPUT_PATHS,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/fixtures/output_experience"


def synthetic_projection_input() -> tuple[dict, dict]:
    counts = {
        "activities": 2,
        "gear": 1,
        "activity_gear": 1,
        "personal_records": 1,
        "fit_sessions": 1,
        "fit_laps": 2,
    }
    manifest = {
        "format": "garmin-running-data-normalizer-run-manifest-v1",
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
            for index, path in enumerate(
                (
                    *DATASET_PATHS.values(),
                    "audit/fit_audit.json",
                    "analysis/activities.csv",
                    "qa/dataset_summary.json",
                )
            )
        ],
        "deterministic_output_digest": "synthetic-digest",
    }
    summary = {
        "format": "garmin-running-data-normalizer-run-summary-v1",
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
                "record_count": 3,
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
    return manifest, summary


class OutputExperienceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            (ROOT / "config/dataset_registry.example.json").read_text(encoding="utf-8")
        )

    def test_projection_is_deterministic_and_matches_golden_files(self) -> None:
        manifest, summary = synthetic_projection_input()
        first = render_output_experience_documents(manifest, summary, self.registry)
        second = render_output_experience_documents(
            copy.deepcopy(manifest), copy.deepcopy(summary), copy.deepcopy(self.registry)
        )
        self.assertEqual(first, second)
        self.assertEqual(tuple(first), DOCUMENT_NAMES)
        for name, rendered in first.items():
            expected = (GOLDEN / name).read_text(encoding="utf-8")
            self.assertEqual(rendered, expected, name)

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
                "audit/fit_audit.json",
                "analysis/activities.csv",
                "qa/dataset_summary.json",
                "run_manifest.json",
                "run_summary.json",
            ),
        )
        self.assertTrue(set(DOCUMENT_NAMES).isdisjoint(OUTPUT_PATHS))

    def test_projection_does_not_expose_source_details_or_hash_values(self) -> None:
        manifest, summary = synthetic_projection_input()
        rendered = "\n".join(
            render_output_experience_documents(manifest, summary, self.registry).values()
        )
        self.assertNotIn("private/SYNTHETIC-ACTIVITY.json", rendered)
        self.assertNotIn("private-source-hash", rendered)
        self.assertNotIn("private-output-hash", rendered)
        self.assertNotRegex(rendered, r"/(?:Users|home)/[^\s]+")

    def test_projection_rejects_manifest_contract_drift(self) -> None:
        manifest, summary = synthetic_projection_input()
        manifest["datasets"][0]["stable_key"] = ["activity_id"]
        with self.assertRaisesRegex(OutputExperienceError, "manifest stable key mismatch"):
            render_output_experience_documents(manifest, summary, self.registry)

    def test_projection_rejects_registry_contract_drift(self) -> None:
        manifest, summary = synthetic_projection_input()
        registry = copy.deepcopy(self.registry)
        registry["datasets"][0]["record_grain"] = "unknown"
        with self.assertRaisesRegex(OutputExperienceError, "registry record grain mismatch"):
            render_output_experience_documents(manifest, summary, registry)

    def test_projection_rejects_family_count_and_status_drift(self) -> None:
        manifest, summary = synthetic_projection_input()
        summary["family_results"]["gear"]["record_count"] = 999
        with self.assertRaisesRegex(
            OutputExperienceError, "family record count does not match"
        ):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["family_results"]["activities"]["status"] = "SKIPPED_NOT_PRESENT"
        with self.assertRaisesRegex(
            OutputExperienceError, "family status contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["family_results"]["gear"]["status"] = "PROCESSED_EMPTY"
        with self.assertRaisesRegex(
            OutputExperienceError, "family status contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["family_results"]["gear"]["status"] = "SKIPPED_NOT_PRESENT"
        with self.assertRaisesRegex(
            OutputExperienceError, "family status contradicts asset"
        ):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["family_results"]["gear"]["warning_count"] = 3
        with self.assertRaisesRegex(
            OutputExperienceError, "family warning count contradicts"
        ):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
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
            render_output_experience_documents(manifest, summary, self.registry)

    def test_projection_accepts_supported_optional_and_partial_states(self) -> None:
        manifest, summary = synthetic_projection_input()
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
            manifest, summary, self.registry
        )
        self.assertIn("`SKIPPED_NOT_PRESENT`", rendered["START_HERE.md"])

        manifest, summary = synthetic_projection_input()
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
            manifest, summary, self.registry
        )
        self.assertIn("`PARTIAL_SUCCESS`", rendered["START_HERE.md"])
        self.assertIn("`PARTIAL`", rendered["DATASET_INVENTORY.md"])

    def test_projection_rejects_unsafe_or_changed_output_paths(self) -> None:
        manifest, summary = synthetic_projection_input()
        manifest["outputs"][0]["path"] = "/private/activities.json"
        with self.assertRaisesRegex(OutputExperienceError, "safe relative path"):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["generated_paths"] = [*summary["generated_paths"], "START_HERE.md"]
        with self.assertRaisesRegex(OutputExperienceError, "do not match Run-All v1"):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        manifest["outputs"].append({"path": "extra.json"})
        with self.assertRaisesRegex(OutputExperienceError, "do not match Run-All v1"):
            render_output_experience_documents(manifest, summary, self.registry)

    def test_projection_rejects_incomplete_or_unfinished_runs(self) -> None:
        manifest, summary = synthetic_projection_input()
        summary["status"] = "FAIL"
        with self.assertRaisesRegex(OutputExperienceError, "completed handoff status"):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["deterministic_output_digest"] = "different"
        with self.assertRaisesRegex(OutputExperienceError, "digests do not match"):
            render_output_experience_documents(manifest, summary, self.registry)

        manifest, summary = synthetic_projection_input()
        summary["family_results"]["activities"]["record_count"] = "2"
        with self.assertRaisesRegex(OutputExperienceError, "record count"):
            render_output_experience_documents(manifest, summary, self.registry)


if __name__ == "__main__":
    unittest.main()
