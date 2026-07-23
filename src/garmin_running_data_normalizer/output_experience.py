from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from .run_all import DATASET_PATHS, DATASET_TABLE, OUTPUT_PATHS, RUN_ALL_VERSION


MANIFEST_FORMAT = "garmin-running-data-normalizer-run-manifest-v1"
SUMMARY_FORMAT = "garmin-running-data-normalizer-run-summary-v1"
SUMMARY_STATUSES = {"PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS"}
FAMILY_STATUSES = {"PROCESSED", "SKIPPED_NOT_PRESENT", "PROCESSED_EMPTY", "PARTIAL"}
DOCUMENT_NAMES = ("START_HERE.md", "DATASET_INVENTORY.md")
MANIFEST_OUTPUT_PATHS = (
    *DATASET_PATHS.values(),
    "audit/fit_audit.json",
    "analysis/activities.csv",
    "qa/dataset_summary.json",
)


class OutputExperienceError(ValueError):
    """Raised when machine artifacts cannot support a safe projection."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutputExperienceError(f"{label} must be an object")
    return value


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise OutputExperienceError(f"{label} must be a safe relative path")
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or ".." in path.parts:
        raise OutputExperienceError(f"{label} must be a safe relative path")
    return path.as_posix()


def _runtime_datasets() -> list[dict[str, Any]]:
    return [
        {
            "name": str(item["name"]),
            "family": str(item["family"]),
            "record_grain": str(item["record_grain"]),
            "stable_key": tuple(str(field) for field in item["stable_key"]),
            "required": bool(item["required"]),
            "output_path": DATASET_PATHS[str(item["name"])],
        }
        for item in DATASET_TABLE
    ]


def validate_registry_alignment(registry: Mapping[str, Any]) -> None:
    registry_object = _mapping(registry, "dataset registry")
    raw_datasets = registry_object.get("datasets")
    if not isinstance(raw_datasets, list):
        raise OutputExperienceError("dataset registry datasets must be a list")
    registry_by_name: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(raw_datasets):
        item = _mapping(value, f"dataset registry entry {index}")
        name = str(item.get("name", ""))
        if not name or name in registry_by_name:
            raise OutputExperienceError("dataset registry names must be non-empty and unique")
        registry_by_name[name] = item
    expected_names = [item["name"] for item in _runtime_datasets()]
    if set(registry_by_name) != set(expected_names):
        raise OutputExperienceError("dataset registry names do not match Run-All v1")
    for expected in _runtime_datasets():
        actual = registry_by_name[expected["name"]]
        if str(actual.get("record_grain")) != expected["record_grain"]:
            raise OutputExperienceError(f"{expected['name']}: registry record grain mismatch")
        stable_key = actual.get("stable_key")
        if not isinstance(stable_key, list) or tuple(str(field) for field in stable_key) != expected["stable_key"]:
            raise OutputExperienceError(f"{expected['name']}: registry stable key mismatch")
        if actual.get("provenance_required") is not True:
            raise OutputExperienceError(f"{expected['name']}: registry provenance must be required")


def _validate_projection_inputs(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]], list[str]]:
    manifest_object = _mapping(manifest, "run manifest")
    summary_object = _mapping(summary, "run summary")
    validate_registry_alignment(registry)
    if manifest_object.get("format") != MANIFEST_FORMAT:
        raise OutputExperienceError("run manifest format is not supported")
    if summary_object.get("format") != SUMMARY_FORMAT:
        raise OutputExperienceError("run summary format is not supported")
    if manifest_object.get("run_all_version") != RUN_ALL_VERSION:
        raise OutputExperienceError("run manifest version is not supported")
    if summary_object.get("run_all_version") != RUN_ALL_VERSION:
        raise OutputExperienceError("run summary version is not supported")
    if summary_object.get("status") not in SUMMARY_STATUSES:
        raise OutputExperienceError("run summary status is not a completed handoff status")
    if manifest_object.get("deterministic_output_digest") != summary_object.get("deterministic_output_digest"):
        raise OutputExperienceError("manifest and summary deterministic digests do not match")

    raw_outputs = manifest_object.get("outputs")
    if not isinstance(raw_outputs, list):
        raise OutputExperienceError("run manifest outputs must be a list")
    output_paths = [
        _safe_relative_path(_mapping(item, f"manifest output {index}").get("path"), "manifest output path")
        for index, item in enumerate(raw_outputs)
    ]
    if len(output_paths) != len(set(output_paths)):
        raise OutputExperienceError("run manifest output paths must be unique")
    if set(output_paths) != set(MANIFEST_OUTPUT_PATHS):
        raise OutputExperienceError("run manifest output paths do not match Run-All v1")

    generated_paths = summary_object.get("generated_paths")
    if not isinstance(generated_paths, list):
        raise OutputExperienceError("run summary generated paths must be a list")
    safe_generated_paths = [
        _safe_relative_path(path, "generated path") for path in generated_paths
    ]
    if safe_generated_paths != list(OUTPUT_PATHS):
        raise OutputExperienceError("run summary generated paths do not match Run-All v1")

    raw_manifest_datasets = manifest_object.get("datasets")
    if not isinstance(raw_manifest_datasets, list):
        raise OutputExperienceError("run manifest datasets must be a list")
    manifest_by_name: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(raw_manifest_datasets):
        item = _mapping(value, f"manifest dataset {index}")
        name = str(item.get("name", ""))
        if not name or name in manifest_by_name:
            raise OutputExperienceError("manifest dataset names must be non-empty and unique")
        manifest_by_name[name] = item

    expected_names = [item["name"] for item in _runtime_datasets()]
    if set(manifest_by_name) != set(expected_names):
        raise OutputExperienceError("run manifest datasets do not match Run-All v1")
    family_record_counts: dict[str, int] = {}
    for expected in _runtime_datasets():
        actual = manifest_by_name[expected["name"]]
        if str(actual.get("record_grain")) != expected["record_grain"]:
            raise OutputExperienceError(f"{expected['name']}: manifest record grain mismatch")
        stable_key = actual.get("stable_key")
        if not isinstance(stable_key, list) or tuple(str(field) for field in stable_key) != expected["stable_key"]:
            raise OutputExperienceError(f"{expected['name']}: manifest stable key mismatch")
        record_count = actual.get("record_count")
        if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count < 0:
            raise OutputExperienceError(f"{expected['name']}: record count must be a non-negative integer")
        family_record_counts[expected["family"]] = (
            family_record_counts.get(expected["family"], 0) + record_count
        )
        if expected["output_path"] not in output_paths:
            raise OutputExperienceError(f"{expected['name']}: normalized output is missing from manifest")

    raw_family_results = summary_object.get("family_results")
    family_results = _mapping(raw_family_results, "run summary family results")
    expected_families = list(dict.fromkeys(item["family"] for item in _runtime_datasets()))
    if set(family_results) != set(expected_families):
        raise OutputExperienceError("run summary families do not match Run-All v1")
    normalized_family_results: dict[str, Mapping[str, Any]] = {}
    total_family_warnings = 0
    total_family_errors = 0
    for family in expected_families:
        result = _mapping(family_results[family], f"family result {family}")
        status = result.get("status")
        if status not in FAMILY_STATUSES:
            raise OutputExperienceError(f"{family}: family status is not supported")
        record_count = _non_negative_integer(
            result.get("record_count"), f"{family} record count"
        )
        if record_count != family_record_counts[family]:
            raise OutputExperienceError(
                f"{family}: family record count does not match manifest datasets"
            )
        detected_asset_count = _non_negative_integer(
            result.get("detected_asset_count"), f"{family} detected asset count"
        )
        processed_asset_count = _non_negative_integer(
            result.get("processed_asset_count"), f"{family} processed asset count"
        )
        skipped_asset_count = _non_negative_integer(
            result.get("skipped_asset_count"), f"{family} skipped asset count"
        )
        family_warning_count = _non_negative_integer(
            result.get("warning_count"), f"{family} warning count"
        )
        family_error_count = _non_negative_integer(
            result.get("error_count"), f"{family} error count"
        )
        if processed_asset_count != detected_asset_count:
            raise OutputExperienceError(
                f"{family}: processed and detected asset counts do not match"
            )
        if family_error_count != 0:
            raise OutputExperienceError(
                f"{family}: completed Run-All family cannot contain errors"
            )

        if family == "activities":
            expected_status = "PROCESSED"
            expected_warning_count = 0
            if detected_asset_count == 0 or record_count == 0:
                raise OutputExperienceError(
                    "activities: required family must be detected and non-empty"
                )
            if skipped_asset_count != 0:
                raise OutputExperienceError(
                    "activities: required family cannot contain skipped assets"
                )
        else:
            expected_warning_count = 0
            if detected_asset_count == 0:
                expected_status = "SKIPPED_NOT_PRESENT"
                expected_warning_count += 1
                if record_count != 0:
                    raise OutputExperienceError(
                        f"{family}: absent family cannot contain normalized records"
                    )
            elif record_count == 0:
                expected_status = "PROCESSED_EMPTY"
                expected_warning_count += 1
            else:
                expected_status = "PROCESSED"

            if family == "fit":
                incomplete_asset_count = _non_negative_integer(
                    result.get("incomplete_asset_count"),
                    "fit incomplete asset count",
                )
                if incomplete_asset_count != skipped_asset_count:
                    raise OutputExperienceError(
                        "fit: incomplete and skipped asset counts do not match"
                    )
                if incomplete_asset_count > detected_asset_count:
                    raise OutputExperienceError(
                        "fit: incomplete asset count exceeds detected assets"
                    )
                if incomplete_asset_count:
                    expected_status = "PARTIAL"
                    expected_warning_count += 1
            elif skipped_asset_count != 0:
                raise OutputExperienceError(
                    f"{family}: non-FIT family cannot contain skipped assets"
                )

        if status != expected_status:
            raise OutputExperienceError(
                f"{family}: family status contradicts asset and record evidence"
            )
        if family_warning_count != expected_warning_count:
            raise OutputExperienceError(
                f"{family}: family warning count contradicts its status"
            )
        total_family_warnings += family_warning_count
        total_family_errors += family_error_count
        normalized_family_results[family] = result

    summary_warning_count = _non_negative_integer(
        summary_object.get("warning_count"), "warning count"
    )
    summary_error_count = _non_negative_integer(
        summary_object.get("error_count"), "error count"
    )
    warnings = summary_object.get("warnings")
    errors = summary_object.get("errors")
    if not isinstance(warnings, list) or len(warnings) != summary_warning_count:
        raise OutputExperienceError("warning list does not match warning count")
    if not isinstance(errors, list) or len(errors) != summary_error_count:
        raise OutputExperienceError("error list does not match error count")
    if summary_warning_count != total_family_warnings:
        raise OutputExperienceError(
            "summary warning count does not match family warning counts"
        )
    if summary_error_count != total_family_errors:
        raise OutputExperienceError(
            "summary error count does not match family error counts"
        )
    fit_is_partial = normalized_family_results["fit"]["status"] == "PARTIAL"
    expected_run_status = (
        "PARTIAL_SUCCESS"
        if fit_is_partial
        else "PASS_WITH_WARNINGS"
        if summary_warning_count
        else "PASS"
    )
    if summary_object.get("status") != expected_run_status:
        raise OutputExperienceError(
            "run status contradicts family and warning evidence"
        )

    return manifest_by_name, normalized_family_results, safe_generated_paths


def _code(value: Any) -> str:
    return f"`{value}`"


def _non_negative_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise OutputExperienceError(f"{label} must be a non-negative integer")
    return value


def _path_list(title: str, paths: list[str]) -> list[str]:
    lines = [f"### {title}", ""]
    if paths:
        lines.extend(f"- {_code(path)}" for path in paths)
    else:
        lines.append("- None")
    lines.append("")
    return lines


def render_dataset_inventory(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> str:
    manifest_by_name, family_results, _ = _validate_projection_inputs(
        manifest, summary, registry
    )
    lines = [
        "# Dataset Inventory",
        "",
        "This document is a deterministic human-readable projection of",
        "`run_manifest.json`, `run_summary.json`, the dataset registry, and the",
        "Run-All v1 runtime dataset definitions. The machine-readable artifacts",
        "remain authoritative.",
        "",
        f"Run status: {_code(summary['status'])}",
        "",
        "| Dataset | Family status | Required | Output path | Grain | Stable key | Records |",
        "|---|---|---:|---|---|---|---:|",
    ]
    for runtime in _runtime_datasets():
        dataset = manifest_by_name[runtime["name"]]
        family_status = family_results[runtime["family"]]["status"]
        stable_key = ", ".join(_code(field) for field in runtime["stable_key"])
        lines.append(
            "| "
            f"{_code(runtime['name'])} | {_code(family_status)} | "
            f"{'yes' if runtime['required'] else 'no'} | "
            f"{_code(runtime['output_path'])} | {runtime['record_grain']} | "
            f"{stable_key} | {dataset['record_count']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `SKIPPED_NOT_PRESENT` is an expected state for an absent optional family.",
            "- `PROCESSED_EMPTY` is distinct from an absent family.",
            "- Stable keys are local identifiers and are not permission to publish them.",
            "- Record counts and paths are projections; provenance and integrity evidence",
            "  remain in `run_manifest.json` and the normalized records.",
            "- Cross-dataset joins are authorized only by the repository Dataset",
            "  Relationship Catalog. Do not infer a relationship from similar fields or",
            "  timestamp proximity.",
            "",
        ]
    )
    return "\n".join(lines)


def render_start_here(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> str:
    _, family_results, generated_paths = _validate_projection_inputs(
        manifest, summary, registry
    )
    analysis_paths = sorted(path for path in generated_paths if path.startswith("analysis/"))
    qa_paths = sorted(path for path in generated_paths if path.startswith("qa/"))
    audit_paths = sorted(path for path in generated_paths if path.startswith("audit/"))
    warning_count = _non_negative_integer(summary.get("warning_count"), "warning count")
    error_count = _non_negative_integer(summary.get("error_count"), "error count")
    lines = [
        "# Start Here",
        "",
        "This document is a deterministic navigation view of the completed Run-All",
        "machine artifacts. It does not replace `run_summary.json`,",
        "`run_manifest.json`, dataset QA, or audit evidence.",
        "",
        "## Run Status",
        "",
        f"- Status: {_code(summary['status'])}",
        f"- Run-All contract version: {_code(summary['run_all_version'])}",
        f"- Warning count: {warning_count}",
        f"- Error count: {error_count}",
        "",
        "## Dataset Families",
        "",
        "| Family | Status | Records | Warnings | Errors |",
        "|---|---|---:|---:|---:|",
    ]
    for family, result in family_results.items():
        record_count = _non_negative_integer(
            result.get("record_count"), f"{family} record count"
        )
        family_warning_count = _non_negative_integer(
            result.get("warning_count"), f"{family} warning count"
        )
        family_error_count = _non_negative_integer(
            result.get("error_count"), f"{family} error count"
        )
        lines.append(
            f"| {_code(family)} | {_code(result['status'])} | "
            f"{record_count} | {family_warning_count} | {family_error_count} |"
        )
    lines.extend(
        [
            "",
            "## Recommended Reading Order",
            "",
            "1. Confirm the status and warnings in `run_summary.json`.",
            "2. Review `DATASET_INVENTORY.md` for dataset grain, keys, and availability.",
            "3. Consult the repository Analysis Handoff Specification before analysis.",
            "4. Consult the Dataset Relationship Catalog before any cross-dataset join.",
            "5. Use QA or audit evidence when a warning, partial result, or validation",
            "   question affects the analysis.",
            "",
        ]
    )
    lines.extend(_path_list("Available Analysis Files", analysis_paths))
    lines.extend(_path_list("QA Evidence", qa_paths))
    lines.extend(_path_list("Audit Evidence", audit_paths))
    lines.extend(
        [
            "## Relationship Safety",
            "",
            "This generated projection does not promote a cross-dataset relationship.",
            "Treat any relationship not declared `explicit` by the repository Dataset",
            "Relationship Catalog as `not_yet_defined`. Do not create timestamp-proximity",
            "joins or infer missing identifiers.",
            "",
            "## Privacy",
            "",
            "Run-All output can contain personal records, local stable keys, provenance,",
            "and exact timestamps. Keep real output local unless the data owner approves a",
            "specific transfer and the receiving environment has been reviewed.",
            "",
        ]
    )
    return "\n".join(lines)


def render_output_experience_documents(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, str]:
    """Return deterministic Markdown without writing or changing Run-All output."""
    return {
        "START_HERE.md": render_start_here(manifest, summary, registry),
        "DATASET_INVENTORY.md": render_dataset_inventory(manifest, summary, registry),
    }


__all__ = [
    "DOCUMENT_NAMES",
    "MANIFEST_OUTPUT_PATHS",
    "OutputExperienceError",
    "render_dataset_inventory",
    "render_output_experience_documents",
    "render_start_here",
    "validate_registry_alignment",
]
