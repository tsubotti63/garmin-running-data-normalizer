from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from .run_all import DATASET_PATHS, DATASET_TABLE, OUTPUT_PATHS, RUN_ALL_VERSION


MANIFEST_FORMAT = "garmin-running-data-normalizer-run-manifest-v1"
SUMMARY_FORMAT = "garmin-running-data-normalizer-run-summary-v1"
SUMMARY_STATUSES = {"PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS"}
FAMILY_STATUSES = {"PROCESSED", "SKIPPED_NOT_PRESENT", "PROCESSED_EMPTY", "PARTIAL"}
DOCUMENT_NAMES = ("START_HERE.md", "DATASET_INVENTORY.md", "ANALYSIS_HANDOFF.md")
MACHINE_CONTEXT_NAMES = (
    "ANALYSIS_CONTEXT.json",
    "SCHEMA_CATALOG.json",
    "artifact_inventory.json",
)
MANIFEST_OUTPUT_PATHS = (
    *DATASET_PATHS.values(),
    "audit/fit_audit.json",
    "audit/activity_fit_linkage.json",
    "analysis/activities.csv",
    "qa/dataset_summary.json",
    "qa/relationship_summary.json",
    *DOCUMENT_NAMES,
    *MACHINE_CONTEXT_NAMES,
)
OPTIONAL_MANIFEST_OUTPUT_PATHS = ("analysis/external_safe_handoff.zip",)

DATASET_PRESENTATION = {
    "activities": {
        "role": "authoritative normalized activities",
        "authority": "normalized source of truth",
        "analysis_suitability": "detailed trusted-local activity analysis",
        "relationship_status": "explicit",
        "privacy_classification": "personal-local",
    },
    "gear": {
        "role": "authoritative normalized gear",
        "authority": "normalized source of truth",
        "analysis_suitability": "trusted-local gear attributes",
        "relationship_status": "explicit",
        "privacy_classification": "personal-local",
    },
    "activity_gear": {
        "role": "activity-to-gear links",
        "authority": "normalized relationship source of truth",
        "analysis_suitability": "explicit activity and gear joins",
        "relationship_status": "explicit",
        "privacy_classification": "identifier-bearing-local",
    },
    "personal_records": {
        "role": "authoritative personal records",
        "authority": "normalized source of truth",
        "analysis_suitability": "explicit nonzero activity joins; zero is independent",
        "relationship_status": "explicit-or-independent",
        "privacy_classification": "personal-local",
    },
    "fit_sessions": {
        "role": "bounded FIT session summaries",
        "authority": "normalized source of truth",
        "analysis_suitability": "trusted-local session analysis after audit review",
        "relationship_status": "explicit",
        "privacy_classification": "personal-local",
    },
    "fit_laps": {
        "role": "bounded FIT lap summaries",
        "authority": "normalized source of truth",
        "analysis_suitability": "explicit child of FIT session",
        "relationship_status": "explicit",
        "privacy_classification": "personal-local",
    },
    "activity_fit_links": {
        "role": "evidence-qualified Activity/FIT session links",
        "authority": "normalized relationship source of truth",
        "analysis_suitability": "explicit one-to-one eligible-population joins",
        "relationship_status": "explicit",
        "privacy_classification": "identifier-bearing-local",
    },
}

DATASET_FIELDS = {
    "activities": (
        "garmin_activity_key", "activity_id", "name", "memo_text_raw",
        "memo_present", "activity_type", "sport_type", "start_time_gmt_ms",
        "start_time_local_raw", "activity_datetime_local", "activity_date_local",
        "distance_raw_centimeters", "distance_m", "duration_ms", "duration_sec",
        "elapsed_duration_ms", "moving_duration_ms", "avg_hr", "max_hr",
        "avg_power", "max_power", "avg_run_cadence", "training_effect_label",
        "activity_training_load", "lap_count", "source_path", "source_sha256",
        "source_confidence",
    ),
    "gear": (
        "gear_key", "uuid", "display_name", "custom_make_model", "gear_type",
        "date_begin", "date_end", "maximum_meters", "source_path",
        "source_sha256",
    ),
    "activity_gear": (
        "gear_key", "activity_id", "garmin_activity_key",
        "activity_relationship_status", "gear_relationship_status",
        "source_path", "source_sha256",
    ),
    "personal_records": (
        "personal_record_id", "activity_id", "personal_record_type", "value",
        "start_time_gmt", "created_date", "current", "confirmed",
        "source_record_index", "garmin_activity_key",
        "activity_relationship_status", "activity_relationship_reason",
        "source_path", "source_sha256", "source_confidence",
    ),
    "fit_sessions": (
        "fit_file_id", "fit_session_key", "session_ordinal", "start_datetime_local",
        "sport", "sub_sport", "distance_m", "elapsed_time_sec",
        "timer_time_sec", "avg_heart_rate", "max_heart_rate", "avg_cadence",
        "max_cadence", "avg_power", "max_power", "total_ascent",
        "total_descent", "record_count", "lap_count", "source_path",
        "source_sha256",
    ),
    "fit_laps": (
        "fit_file_id", "fit_session_key", "fit_lap_key", "session_ordinal",
        "lap_ordinal_within_session", "lap_index", "start_time",
        "total_elapsed_time", "total_timer_time", "total_distance", "avg_speed",
        "max_speed", "avg_heart_rate", "max_heart_rate", "avg_cadence",
        "max_cadence", "avg_power", "max_power", "total_ascent",
        "total_descent", "timestamp", "source_path", "source_sha256",
    ),
    "activity_fit_links": (
        "garmin_activity_key", "fit_session_key", "match_rule", "match_basis",
        "match_score", "match_status", "ambiguous", "eligibility_status",
        "exclusion_reason", "time_delta_seconds", "distance_delta_m",
        "duration_delta_seconds", "activity_source_path",
        "activity_source_sha256", "fit_source_path", "fit_source_sha256",
        "source_path", "source_sha256",
    ),
}

RELATIONSHIP_CONTRACTS = (
    {
        "relationship_id": "activity_gear_to_activities",
        "left_dataset": "activity_gear",
        "right_dataset": "activities",
        "status": "explicit",
        "left_fields": ["garmin_activity_key"],
        "right_fields": ["garmin_activity_key"],
        "cardinality": "many_to_one",
    },
    {
        "relationship_id": "activity_gear_to_gear",
        "left_dataset": "activity_gear",
        "right_dataset": "gear",
        "status": "explicit",
        "left_fields": ["gear_key"],
        "right_fields": ["gear_key"],
        "cardinality": "many_to_one",
    },
    {
        "relationship_id": "personal_records_to_activities",
        "left_dataset": "personal_records",
        "right_dataset": "activities",
        "status": "explicit",
        "left_fields": ["garmin_activity_key"],
        "right_fields": ["garmin_activity_key"],
        "cardinality": "many_to_zero_or_one",
        "exception": "activity_id_zero_is_independent",
    },
    {
        "relationship_id": "fit_laps_to_fit_sessions",
        "left_dataset": "fit_laps",
        "right_dataset": "fit_sessions",
        "status": "explicit",
        "left_fields": ["fit_session_key"],
        "right_fields": ["fit_session_key"],
        "cardinality": "many_to_one",
    },
    {
        "relationship_id": "activity_fit_links_to_activities",
        "left_dataset": "activity_fit_links",
        "right_dataset": "activities",
        "status": "explicit",
        "left_fields": ["garmin_activity_key"],
        "right_fields": ["garmin_activity_key"],
        "cardinality": "one_to_one_within_eligible_population",
    },
    {
        "relationship_id": "activity_fit_links_to_fit_sessions",
        "left_dataset": "activity_fit_links",
        "right_dataset": "fit_sessions",
        "status": "explicit",
        "left_fields": ["fit_session_key"],
        "right_fields": ["fit_session_key"],
        "cardinality": "one_to_one_within_eligible_population",
    },
)

RELATIONSHIP_COVERAGE_PRESENTATION = {
    "activity_gear_to_activities": {
        "title": "Activity/Gear Links → Activities",
        "qa_relationship_id": "activity_gear_to_activities",
        "eligible_population_label": "Activity/Gear link records",
        "eligible_count_field": "eligible_count",
        "coverage_field": "coverage",
        "unresolved_count_field": "unresolved_count",
        "ambiguous_count_field": "ambiguous_count",
        "duplicate_count_field": "duplicate_count",
        "primary_reason_field": "primary_unresolved_reason",
    },
    "activity_gear_to_gear": {
        "title": "Activity/Gear Links → Gear",
        "qa_relationship_id": "activity_gear_to_gear",
        "eligible_population_label": "Activity/Gear link records",
        "eligible_count_field": "eligible_count",
        "coverage_field": "coverage",
        "unresolved_count_field": "unresolved_count",
        "ambiguous_count_field": "ambiguous_count",
        "duplicate_count_field": "duplicate_count",
        "primary_reason_field": "primary_unresolved_reason",
    },
    "personal_records_to_activities": {
        "title": "Personal Records → Activities",
        "qa_relationship_id": "personal_records_to_activities",
        "eligible_population_label": "nonzero-activity Personal Records",
        "eligible_count_field": "eligible_count",
        "coverage_field": "coverage",
        "unresolved_count_field": "unresolved_count",
        "ambiguous_count_field": "ambiguous_count",
        "duplicate_count_field": "duplicate_count",
        "primary_reason_field": "primary_unresolved_reason",
    },
    "fit_laps_to_fit_sessions": {
        "title": "FIT Laps → FIT Sessions",
        "qa_relationship_id": "fit_laps_to_fit_sessions",
        "eligible_population_label": "FIT Laps",
        "eligible_count_field": "eligible_count",
        "coverage_field": "coverage",
        "unresolved_count_field": "unresolved_count",
        "ambiguous_count_field": "ambiguous_count",
        "duplicate_count_field": "duplicate_count",
        "primary_reason_field": "primary_unresolved_reason",
    },
    "activity_fit_links_to_activities": {
        "title": "Activity ↔ FIT — Activity coverage",
        "qa_relationship_id": "activities_to_fit_sessions",
        "eligible_population_label": "Activities",
        "eligible_count_field": "eligible_activity_count",
        "coverage_field": "eligible_activity_coverage",
        "unresolved_count_field": "unresolved_eligible_activity_count",
        "ambiguous_count_field": "ambiguous_activity_count",
        "duplicate_count_field": "duplicate_mapping_count",
        "primary_reason_field": "primary_unresolved_activity_reason",
        "audit_reference": "audit/activity_fit_linkage.json",
    },
    "activity_fit_links_to_fit_sessions": {
        "title": "Activity ↔ FIT — FIT Session coverage",
        "qa_relationship_id": "activities_to_fit_sessions",
        "eligible_population_label": "FIT Sessions",
        "eligible_count_field": "eligible_fit_session_count",
        "coverage_field": "eligible_fit_session_coverage",
        "unresolved_count_field": "unresolved_eligible_fit_session_count",
        "ambiguous_count_field": "ambiguous_fit_session_count",
        "duplicate_count_field": "duplicate_mapping_count",
        "primary_reason_field": "primary_unresolved_fit_session_reason",
        "audit_reference": "audit/activity_fit_linkage.json",
    },
}


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
    product_version = manifest_object.get("product_version")
    if (
        not isinstance(product_version, str)
        or not product_version
        or summary_object.get("product_version") != product_version
    ):
        raise OutputExperienceError("manifest and summary product versions do not match")
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
    allowed_output_sets = (
        set(MANIFEST_OUTPUT_PATHS),
        set((*MANIFEST_OUTPUT_PATHS, *OPTIONAL_MANIFEST_OUTPUT_PATHS)),
    )
    if set(output_paths) not in allowed_output_sets:
        raise OutputExperienceError("run manifest output paths do not match Run-All v1")

    generated_paths = summary_object.get("generated_paths")
    if not isinstance(generated_paths, list):
        raise OutputExperienceError("run summary generated paths must be a list")
    safe_generated_paths = [
        _safe_relative_path(path, "generated path") for path in generated_paths
    ]
    optional_generated_paths = [
        *OUTPUT_PATHS[:-2],
        *OPTIONAL_MANIFEST_OUTPUT_PATHS,
        *OUTPUT_PATHS[-2:],
    ]
    if safe_generated_paths not in (list(OUTPUT_PATHS), optional_generated_paths):
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


def _coverage_ratio(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise OutputExperienceError(f"{label} must be a ratio from zero to one")
    return float(value)


def _relationship_coverage(
    relationship_summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    summary_object = _mapping(relationship_summary, "relationship summary")
    if summary_object.get("status") != "PASS":
        raise OutputExperienceError("relationship summary must have PASS status")
    qa_relationships = _mapping(
        summary_object.get("relationships"),
        "relationship summary relationships",
    )
    coverage_entries: list[dict[str, Any]] = []
    for contract in RELATIONSHIP_CONTRACTS:
        relationship_id = str(contract["relationship_id"])
        presentation = RELATIONSHIP_COVERAGE_PRESENTATION[relationship_id]
        qa_relationship_id = str(presentation["qa_relationship_id"])
        qa = _mapping(
            qa_relationships.get(qa_relationship_id),
            f"relationship summary {qa_relationship_id}",
        )
        if qa.get("relationship_status", qa.get("status")) != "explicit":
            raise OutputExperienceError(
                f"relationship summary {qa_relationship_id} must be explicit"
            )
        eligible_count = _non_negative_integer(
            qa.get(presentation["eligible_count_field"]),
            f"{relationship_id} eligible count",
        )
        explicit_links = _non_negative_integer(
            qa.get("link_count"),
            f"{relationship_id} explicit link count",
        )
        unresolved_count = _non_negative_integer(
            qa.get(presentation["unresolved_count_field"]),
            f"{relationship_id} unresolved count",
        )
        ambiguous_count = _non_negative_integer(
            qa.get(presentation["ambiguous_count_field"]),
            f"{relationship_id} ambiguous count",
        )
        duplicate_count = _non_negative_integer(
            qa.get(presentation["duplicate_count_field"]),
            f"{relationship_id} duplicate count",
        )
        coverage = _coverage_ratio(
            qa.get(presentation["coverage_field"]),
            f"{relationship_id} coverage",
        )
        inference_performed = qa.get("inference_performed")
        if inference_performed is not False:
            raise OutputExperienceError(
                f"{relationship_id} must explicitly prohibit inference"
            )
        primary_reason = qa.get(presentation["primary_reason_field"])
        if primary_reason is not None and (
            not isinstance(primary_reason, str) or not primary_reason
        ):
            raise OutputExperienceError(
                f"{relationship_id} primary unresolved reason is invalid"
            )
        if explicit_links > eligible_count:
            raise OutputExperienceError(
                f"{relationship_id} explicit links exceed eligible population"
            )
        if unresolved_count != eligible_count - explicit_links:
            raise OutputExperienceError(
                f"{relationship_id} unresolved count contradicts coverage"
            )
        if ambiguous_count > unresolved_count:
            raise OutputExperienceError(
                f"{relationship_id} ambiguity exceeds unresolved population"
            )
        if duplicate_count > unresolved_count:
            raise OutputExperienceError(
                f"{relationship_id} duplicate count exceeds unresolved population"
            )
        if eligible_count == 0:
            if coverage is not None:
                raise OutputExperienceError(
                    f"{relationship_id} zero eligible population must use null coverage"
                )
        else:
            expected_coverage = explicit_links / eligible_count
            if coverage is None or abs(coverage - expected_coverage) > 1e-12:
                raise OutputExperienceError(
                    f"{relationship_id} coverage contradicts counts"
                )
        if (unresolved_count == 0) != (primary_reason is None):
            raise OutputExperienceError(
                f"{relationship_id} primary unresolved reason contradicts count"
            )
        entry = {
            "relationship_id": relationship_id,
            "title": presentation["title"],
            "eligible_population": {
                "label": presentation["eligible_population_label"],
                "count": eligible_count,
            },
            "explicit_links": explicit_links,
            "coverage_percentage": (
                round(coverage * 100.0, 4) if coverage is not None else None
            ),
            "unresolved_count": unresolved_count,
            "ambiguous_count": ambiguous_count,
            "duplicate_count": duplicate_count,
            "inference_performed": False,
            "primary_unresolved_reason": primary_reason,
            "qa_reference": "qa/relationship_summary.json",
        }
        if "audit_reference" in presentation:
            entry["audit_reference"] = presentation["audit_reference"]
        coverage_entries.append(entry)
    return coverage_entries


def _relationship_coverage_lines(
    relationship_summary: Mapping[str, Any],
) -> list[str]:
    lines = [
        "## Relationship Coverage",
        "",
        "Coverage communicates the evidence boundary; it is not a success score.",
        "Detailed relationship QA remains authoritative in",
        "`qa/relationship_summary.json`. Activity/FIT exclusions and match evidence",
        "remain in `audit/activity_fit_linkage.json`.",
        "",
    ]
    for entry in _relationship_coverage(relationship_summary):
        coverage = entry["coverage_percentage"]
        coverage_text = (
            f"{coverage:.2f}%"
            if coverage is not None
            else "N/A (no eligible records)"
        )
        primary_reason = entry["primary_unresolved_reason"]
        lines.extend(
            [
                f"### {entry['title']}",
                "",
                "- Eligible population: "
                f"{entry['eligible_population']['count']} "
                f"({entry['eligible_population']['label']})",
                f"- Explicit links: {entry['explicit_links']}",
                f"- Coverage: {coverage_text}",
                f"- Unresolved: {entry['unresolved_count']}",
                f"- Ambiguous: {entry['ambiguous_count']}",
                f"- Duplicate: {entry['duplicate_count']}",
                "- Inference performed: No",
                "- Primary unresolved reason: "
                f"{_code(primary_reason) if primary_reason is not None else 'None'}",
                "",
            ]
        )
    return lines


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
        "| Dataset | Role | Status | Records | Warnings | Path | Grain | Stable key | Authority | Analysis use | Relationships | Privacy |",
        "|---|---|---|---:|---:|---|---|---|---|---|---|---|",
    ]
    for runtime in _runtime_datasets():
        dataset = manifest_by_name[runtime["name"]]
        family_result = family_results[runtime["family"]]
        family_status = family_result["status"]
        stable_key = ", ".join(_code(field) for field in runtime["stable_key"])
        presentation = DATASET_PRESENTATION[runtime["name"]]
        lines.append(
            "| "
            f"{_code(runtime['name'])} | {presentation['role']} | "
            f"{_code(family_status)} | {dataset['record_count']} | "
            f"{family_result['warning_count']} | {_code(runtime['output_path'])} | "
            f"{runtime['record_grain']} | {stable_key} | "
            f"{presentation['authority']} | {presentation['analysis_suitability']} | "
            f"{_code(presentation['relationship_status'])} | "
            f"{_code(presentation['privacy_classification'])} |"
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
            "- Required/optional input behavior remains available in `run_manifest.json`",
            "  and `run_summary.json`; an absent optional family is not a claim of no data.",
            "",
        ]
    )
    return "\n".join(lines)


def render_start_here(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
    relationship_summary: Mapping[str, Any],
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
            "1. Confirm this run status and any warnings below.",
            "2. Review `DATASET_INVENTORY.md` for dataset grain, keys, and availability.",
            "3. Read `ANALYSIS_HANDOFF.md` before supplying files to an analyst or AI.",
            "4. Use `ANALYSIS_CONTEXT.json` and `SCHEMA_CATALOG.json` for machine context.",
            "5. Use only relationships marked explicit in the handoff/context.",
            "6. Use QA or audit evidence when a warning, partial result, or validation",
            "   question affects the analysis.",
            "",
            "Recommended trusted-local analysis entry point: `analysis/activities.csv`.",
            "",
        ]
    )
    lines.extend(_path_list("Available Analysis Files", analysis_paths))
    lines.extend(_path_list("QA Evidence", qa_paths))
    lines.extend(_path_list("Audit Evidence", audit_paths))
    lines.extend(_relationship_coverage_lines(relationship_summary))
    lines.extend(
        [
            "## Relationship Safety",
            "",
            "The generated relationship contract declares only reviewed v1.1 joins.",
            "`activity_fit_links` is the sole Activity/FIT join authority. Do not create",
            "a timestamp-only join or infer a relationship from similar fields.",
            "",
            "## Privacy",
            "",
            "Privacy mode: `local_trusted_full`.",
            "",
            "Run-All output can contain personal records, local stable keys, provenance,",
            "exact timestamps, memo text, and source-relative filenames. A Garmin export",
            "filename may itself contain an email-shaped personal identifier. Keep real",
            "output local unless the data owner approves a specific transfer and the",
            "receiving environment has been reviewed. Use the optional external-safe",
            "handoff only after reviewing its aggregation level.",
            "",
            "## Next Action",
            "",
            "Review warnings and relationship QA, then formulate an analysis question",
            "using only the declared entry point, fields, and explicit relationships.",
            "",
        ]
    )
    return "\n".join(lines)


def render_analysis_handoff(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
    relationship_summary: Mapping[str, Any],
) -> str:
    _validate_projection_inputs(manifest, summary, registry)
    warning_lines = (
        [
            f"- `{item.get('code', 'UNSPECIFIED_WARNING')}`"
            for item in summary.get("warnings", [])
            if isinstance(item, Mapping)
        ]
        or ["- None"]
    )
    lines = [
        "# Analysis Handoff",
        "",
        "This file is the deterministic receiving contract for this completed Run-All",
        "output. It is sufficient to begin bounded analysis without repository or",
        "Internet access. The normalized data and machine artifacts remain authoritative.",
        "",
        "## Authorized Default Files",
        "",
        "- `START_HERE.md`",
        "- `DATASET_INVENTORY.md`",
        "- `ANALYSIS_CONTEXT.json`",
        "- `SCHEMA_CATALOG.json`",
        "- `analysis/activities.csv`",
        "- `run_summary.json`",
        "",
        "Use normalized JSON, relationship links, QA, or audit files only when the",
        "question requires them and the local/trusted environment is authorized.",
        "",
        "## Receiving Rules",
        "",
        "1. Separate observed facts, calculations, interpretations, and unknowns.",
        "2. Preserve null and missing values; never convert them to zero.",
        "3. State filters, formulas, denominators, and missing-value counts.",
        "4. Use only relationships marked `explicit` in `ANALYSIS_CONTEXT.json`.",
        "5. Use `activity_fit_links` for Activity/FIT joins; timestamp-only joins are prohibited.",
        "6. Treat Personal Records with `activity_relationship_status=independent`",
        "   as non-activity records and do not force an activity identity.",
        "7. Preserve and disclose warnings or partial FIT status.",
        "8. Ask for an additional approved file when the supplied artifacts cannot",
        "   answer the question; do not invent source fields or context.",
        "",
        *_relationship_coverage_lines(relationship_summary),
        "## Multi-Session FIT Completeness",
        "",
        "- CRC-valid multi-session FIT files are normalized when every lap can be",
        "  assigned to exactly one declared session without inference.",
        "- If declared session/lap counts cannot allocate every lap exactly once, the",
        "  whole FIT file is excluded from normalized sessions and laps with",
        "  `session_lap_allocation_conflict` in `audit/fit_audit.json`.",
        "- Sessions excluded at this parse boundary do not enter the eligible",
        "  Activity/FIT Relationship Coverage population. Coverage therefore describes",
        "  only emitted, independently eligible sessions and does not claim that an",
        "  allocation-conflict file was normalized.",
        "",
        "## Current Warnings",
        "",
        *warning_lines,
        "",
        "## Privacy Modes",
        "",
        "- `local_trusted_full`: full Run-All output, provenance, stable keys, QA,",
        "  audit evidence, memo text, and source-relative filenames remain in a",
        "  user-controlled trusted environment. Source filenames can contain",
        "  email-shaped personal identifiers.",
        "- `external_safe`: only the explicit safe-pack allowlist may leave that",
        "  environment after review. The pack excludes paths, hashes, raw IDs, stable",
        "  keys, memo text, coordinates, exact timestamps, and unlisted files.",
        "- Run-All never uploads output automatically.",
        "",
        "## Reproducibility",
        "",
        "Record the product version, run status, files used, filters, formulas, and",
        "missing-value policy. Identical normalized input can reproduce deterministic",
        "machine artifacts and guidance; generative prose is not claimed byte-identical.",
        "",
        "## Prompt Preamble",
        "",
        "> Use only the supplied files. Preserve missing values. Honor each dataset",
        "> grain and stable key. Use only explicit relationships. Do not infer identity,",
        "> location, intent, diagnosis, or causal explanation. Cite the dataset and",
        "> fields supporting each factual statement, separate calculations from",
        "> interpretation, and state what remains unknown.",
        "",
    ]
    return "\n".join(lines)


def _field_descriptor(field: str) -> dict[str, Any]:
    boolean_fields = {"memo_present", "current", "confirmed", "ambiguous"}
    integer_fields = {
        "session_ordinal", "lap_ordinal_within_session", "lap_index",
        "record_count", "lap_count", "source_record_index", "match_score",
        "start_time_gmt_ms", "duration_ms", "elapsed_duration_ms",
        "moving_duration_ms", "distance_raw_centimeters",
    }
    numeric_fields = {
        "distance_m", "duration_sec", "avg_hr", "max_hr", "avg_power",
        "max_power", "avg_run_cadence", "activity_training_load",
        "maximum_meters", "value", "elapsed_time_sec", "timer_time_sec",
        "avg_heart_rate", "max_heart_rate", "avg_cadence", "max_cadence",
        "total_ascent", "total_descent", "total_elapsed_time",
        "total_timer_time", "total_distance", "avg_speed", "max_speed",
        "time_delta_seconds", "distance_delta_m", "duration_delta_seconds",
    }
    array_fields = {"match_basis"}
    flexible_identifier_fields = {
        "activity_id",
        "gear_key",
        "personal_record_id",
    }
    if field in boolean_fields:
        logical_type = "boolean"
    elif field in integer_fields:
        logical_type = "integer"
    elif field in numeric_fields:
        logical_type = "number"
    elif field in array_fields:
        logical_type = "array[string]"
    elif field in flexible_identifier_fields:
        logical_type = "integer|string"
    else:
        logical_type = "string"

    unit = None
    if field.endswith("_m") or field in {"total_distance", "total_ascent", "total_descent"}:
        unit = "metre"
    elif field.endswith("_sec") or field.endswith("_seconds") or field in {
        "elapsed_time_sec", "timer_time_sec", "total_elapsed_time",
        "total_timer_time",
    }:
        unit = "second"
    elif field.endswith("_ms"):
        unit = "millisecond"
    elif "heart_rate" in field or field in {"avg_hr", "max_hr"}:
        unit = "beats_per_minute"
    elif "power" in field:
        unit = "source_power_value"

    provenance = (
        "provenance"
        if field.startswith("source_")
        or field.endswith("_source_path")
        or field.endswith("_source_sha256")
        else "derived"
        if field
        in {
            "garmin_activity_key", "fit_session_key", "fit_lap_key",
            "activity_relationship_status", "gear_relationship_status",
            "activity_relationship_reason", "match_rule", "match_basis",
            "match_score", "match_status", "ambiguous", "eligibility_status",
            "exclusion_reason", "time_delta_seconds", "distance_delta_m",
            "duration_delta_seconds",
        }
        else "source"
    )
    privacy = (
        "restricted_identifier"
        if field.endswith("_key")
        or field.endswith("_id")
        or field in {"uuid", "activity_id", "personal_record_id", "fit_file_id"}
        else "restricted_provenance"
        if "path" in field or "sha256" in field
        else "restricted_text"
        if field in {"memo_text_raw", "name", "display_name", "custom_make_model"}
        else "personal"
    )
    notes = (
        "Source identifiers are preserved as JSON integers or strings; "
        "deterministic fallback identifiers are strings. Compare values only "
        "after applying the declared explicit relationship contract."
        if field in flexible_identifier_fields
        else "Defined by the v1.1 runtime schema; do not infer missing values."
    )
    return {
        "logical_type": logical_type,
        "nullable": field
        not in {
            "garmin_activity_key", "gear_key", "personal_record_id",
            "fit_session_key", "fit_lap_key", "source_path", "source_sha256",
        },
        "unit_or_domain": unit,
        "semantic_role": "stable_key"
        if field.endswith("_key") or field in {"personal_record_id"}
        else "provenance"
        if provenance == "provenance"
        else "attribute",
        "origin": provenance,
        "privacy_sensitivity": privacy,
        "notes": notes,
    }


def build_schema_catalog(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_projection_inputs(manifest, summary, registry)
    return {
        "format": "garmin-running-data-normalizer-schema-catalog-v1",
        "run_all_version": RUN_ALL_VERSION,
        "datasets": [
            {
                "dataset": dataset,
                "fields": [
                    {"field": field, **_field_descriptor(field)}
                    for field in fields
                ],
            }
            for dataset, fields in DATASET_FIELDS.items()
        ],
    }


def build_analysis_context(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
    relationship_summary: Mapping[str, Any],
) -> dict[str, Any]:
    manifest_by_name, family_results, _ = _validate_projection_inputs(
        manifest,
        summary,
        registry,
    )
    return {
        "format": "garmin-running-data-normalizer-analysis-context-v1",
        "product_version": manifest["product_version"],
        "run_all_version": RUN_ALL_VERSION,
        "run_status": summary["status"],
        "analysis_entry_point": "analysis/activities.csv",
        "privacy_mode": "local_trusted_full",
        "datasets": [
            {
                "name": runtime["name"],
                "path": runtime["output_path"],
                "status": family_results[runtime["family"]]["status"],
                "record_count": manifest_by_name[runtime["name"]]["record_count"],
                "record_grain": runtime["record_grain"],
                "stable_key": list(runtime["stable_key"]),
                **DATASET_PRESENTATION[runtime["name"]],
            }
            for runtime in _runtime_datasets()
        ],
        "relationships": list(RELATIONSHIP_CONTRACTS),
        "relationship_coverage": _relationship_coverage(relationship_summary),
        "prohibited_operations": [
            "timestamp_only_join",
            "join_not_declared_explicit",
            "missing_value_inference",
            "identity_or_location_inference",
            "automatic_external_upload",
            "medical_or_coaching_interpretation",
        ],
        "warnings": summary.get("warnings", []),
    }


def build_artifact_inventory(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_projection_inputs(manifest, summary, registry)
    return {
        "format": "garmin-running-data-normalizer-artifact-inventory-v1",
        "completion_marker": "run_summary.json",
        "artifacts": [
            {
                "path": path,
                "category": path.split("/", 1)[0] if "/" in path else "guidance",
                "listed": True,
            }
            for path in summary["generated_paths"]
        ],
    }


def render_output_experience_documents(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
    relationship_summary: Mapping[str, Any],
) -> dict[str, str]:
    """Return deterministic Markdown without writing or changing Run-All output."""
    return {
        "START_HERE.md": render_start_here(
            manifest,
            summary,
            registry,
            relationship_summary,
        ),
        "DATASET_INVENTORY.md": render_dataset_inventory(manifest, summary, registry),
        "ANALYSIS_HANDOFF.md": render_analysis_handoff(
            manifest,
            summary,
            registry,
            relationship_summary,
        ),
    }


def render_output_experience_artifacts(
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry: Mapping[str, Any],
    relationship_summary: Mapping[str, Any],
) -> dict[str, bytes]:
    documents = render_output_experience_documents(
        manifest,
        summary,
        registry,
        relationship_summary,
    )
    machine = {
        "ANALYSIS_CONTEXT.json": build_analysis_context(
            manifest,
            summary,
            registry,
            relationship_summary,
        ),
        "SCHEMA_CATALOG.json": build_schema_catalog(manifest, summary, registry),
        "artifact_inventory.json": build_artifact_inventory(
            manifest,
            summary,
            registry,
        ),
    }
    return {
        **{
            path: (content + "\n").encode("utf-8")
            for path, content in documents.items()
        },
        **{
            path: (
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")
            for path, value in machine.items()
        },
    }


__all__ = [
    "DOCUMENT_NAMES",
    "MACHINE_CONTEXT_NAMES",
    "MANIFEST_OUTPUT_PATHS",
    "OPTIONAL_MANIFEST_OUTPUT_PATHS",
    "OutputExperienceError",
    "build_analysis_context",
    "build_artifact_inventory",
    "build_schema_catalog",
    "render_dataset_inventory",
    "render_analysis_handoff",
    "render_output_experience_artifacts",
    "render_output_experience_documents",
    "render_start_here",
    "validate_registry_alignment",
]
