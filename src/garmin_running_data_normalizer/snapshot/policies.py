from __future__ import annotations

import copy
from typing import Any


# A Snapshot Store records these two versions and is read only with the same
# ones. The store keeps them unchanged, so that it stays readable without
# migration, also by earlier releases that use the same versions. The policy
# registry below is the record of the v1.0 rules; the merge rules of later
# releases have their own version (MERGE_RULES_VERSION).
REGISTRY_VERSION = "garmin_public_snapshot_dataset_merge_policies:v1.0"
CONTRACT_VERSION = "garmin_public_snapshot_lifecycle:v1.0"

DEFAULTS: dict[str, Any] = {
    "absence_policy": "missing_is_not_delete",
    "explicit_null_policy": "preserve_previous_and_review",
    "explicit_empty_policy": "preserve_previous_and_review",
    "deletion_policy": "no_automatic_delete",
    "exact_duplicate_policy": "dedupe_preserve_all_provenance",
    "null_key_policy": "preserve_raw_and_review",
    "conflict_policy": "deterministic_if_ordered_else_stop",
    "provenance_required": True,
    "public_status": "approved_for_implementation",
}

POLICIES: dict[str, dict[str, Any]] = {
    "activities": {
        "dataset": "activities",
        "source_family": "DI-Connect-Fitness",
        "merge_mode": "entity_upsert",
        "record_grain": "activity",
        "stable_key": ["garmin_activity_key"],
        "materialization": "source_shaped_json",
    },
    "gear": {
        "dataset": "gear",
        "source_family": "DI-Connect-Fitness",
        "merge_mode": "entity_upsert",
        "record_grain": "gear",
        "stable_key": ["gear_key"],
        "materialization": "source_shaped_json",
    },
    "activity_gear": {
        "dataset": "activity_gear",
        "source_family": "DI-Connect-Fitness",
        "merge_mode": "temporal_event_union",
        "record_grain": "activity_gear_link",
        "stable_key": ["gear_key", "activity_id"],
        "materialization": "source_shaped_json",
    },
    "personal_records": {
        "dataset": "personal_records",
        "source_family": "DI-Connect-Fitness",
        "merge_mode": "entity_upsert",
        "record_grain": "personal_record",
        "stable_key": ["personal_record_id"],
        "relationship_exception": "activity_id_zero_is_independent",
        "materialization": "source_shaped_json",
    },
    "hill_score_daily": {
        "dataset": "hill_score_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "daily_state_upsert",
        "record_grain": "calendar_day",
        "stable_key": ["calendar_date"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
    },
    "endurance_score_daily": {
        "dataset": "endurance_score_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "daily_state_upsert",
        "record_grain": "calendar_day",
        "stable_key": ["calendar_date"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "variant_policy": "preserve_observed_variants_fail_closed_canonicalization",
        "keep_last": False,
    },
    "race_prediction_daily": {
        "dataset": "race_prediction_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "immutable_observation_union",
        "record_grain": "source_observation",
        "stable_key": ["calendar_date", "observation_timestamp"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
    },
    "sleep_daily": {
        "dataset": "sleep_daily",
        "source_family": "DI-Connect-Wellness",
        "merge_mode": "daily_state_upsert",
        "record_grain": "sleep_day",
        "stable_key": ["sleep_day"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
    },
    "uds_daily": {
        "dataset": "uds_daily",
        "source_family": "DI-Connect-Aggregator",
        "merge_mode": "daily_state_upsert",
        "record_grain": "calendar_day",
        "stable_key": ["calendar_date"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "variant_policy": "preserve_observed_variants_fail_closed_canonicalization",
        "keep_last": False,
    },
    "acute_training_load_daily": {
        "dataset": "acute_training_load_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "immutable_observation_union",
        "record_grain": "source_observation",
        "stable_key": ["calendar_date", "observation_timestamp"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
    },
    "training_readiness_daily": {
        "dataset": "training_readiness_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "immutable_observation_union",
        "record_grain": "source_observation",
        "stable_key": ["calendar_date", "observation_timestamp"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
    },
    "vo2max_daily": {
        "dataset": "vo2max_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "immutable_observation_union",
        "record_grain": "source_observation",
        "stable_key": ["calendar_date", "vo2max_source_series", "sport", "observation_timestamp"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
        "source_series_required": True,
    },
    "hrv_daily": {
        "dataset": "hrv_daily",
        "source_family": "DI-Connect-Uploaded-Files",
        "merge_mode": "regenerate",
        "record_grain": "calendar_day",
        "regeneration_source": "fit_blobs",
        "stable_key": ["calendar_date"],
        "analysis_role": "analysis_reference_only",
        "source_of_truth": False,
    },
    "training_history_daily": {
        "dataset": "training_history_daily",
        "source_family": "DI-Connect-Metrics",
        "merge_mode": "immutable_observation_union",
        "record_grain": "source_observation",
        "stable_key": ["calendar_date", "observation_timestamp"],
        "materialization": "source_shaped_json",
        "conflict_policy": "review_fail_closed",
        "keep_last": False,
    },
    "lactate_threshold_candidates": {
        "dataset": "lactate_threshold_candidates",
        "source_family": "DI-Connect-Wellness",
        "merge_mode": "immutable_observation_union",
        "record_grain": "threshold_observation_candidate",
        "identity_anchor": "observation_timestamp",
        "machine_stable_key_status": "PRODUCT_DECISION_REQUIRED",
        "candidate_identity": "internal_content_fingerprint_not_public_stable_key",
        "materialization": "source_shaped_candidate_json",
        "canonical_public_output": False,
        "latest_wins": False,
    },
    "fit_blobs": {
        "dataset": "fit_blobs",
        "source_family": "DI-Connect-Uploaded-Files",
        "merge_mode": "immutable_blob_union",
        "record_grain": "unique_fit_binary",
        "stable_key": ["fit_blob_sha256"],
        "materialization": "cumulative_unique_fit_files",
    },
    "fit_sessions": {
        "dataset": "fit_sessions",
        "source_family": "DI-Connect-Uploaded-Files",
        "merge_mode": "regenerate",
        "record_grain": "fit_session",
        "regeneration_source": "fit_blobs",
        "stable_key": ["fit_session_key"],
    },
    "fit_laps": {
        "dataset": "fit_laps",
        "source_family": "DI-Connect-Uploaded-Files",
        "merge_mode": "regenerate",
        "record_grain": "fit_session_lap",
        "regeneration_source": "fit_blobs",
        "stable_key": ["fit_lap_key"],
    },
    "activity_fit_links": {
        "dataset": "activity_fit_links",
        "source_family": "derived_relationship",
        "merge_mode": "regenerate",
        "record_grain": "activity_fit_session_link",
        "regeneration_source": ["activities", "fit_sessions"],
        "stable_key": ["garmin_activity_key", "fit_session_key"],
        "inference_policy": "no_timestamp_only_inference",
    },
    "qa_audit_output_experience": {
        "dataset": "qa_audit_output_experience",
        "source_family": "derived_output",
        "merge_mode": "regenerate",
        "record_grain": "generated_artifact",
        "stable_key": ["artifact_path"],
    },
    "unknown_or_unsupported": {
        "dataset": "unknown_or_unsupported",
        "source_family": "unknown",
        "merge_mode": "preserve_only",
        "record_grain": "raw_file_or_member",
        "stable_key": ["snapshot_id", "relative_path", "sha256"],
        "canonical_public_output": False,
    },
}

PUBLIC_POLICY_ORDER = (
    "activities",
    "gear",
    "activity_gear",
    "personal_records",
    "hill_score_daily",
    "endurance_score_daily",
    "race_prediction_daily",
    "sleep_daily",
    "uds_daily",
    "acute_training_load_daily",
    "training_readiness_daily",
    "vo2max_daily",
    "hrv_daily",
    "training_history_daily",
    "lactate_threshold_candidates",
    "fit_blobs",
    "fit_sessions",
    "fit_laps",
    "activity_fit_links",
    "qa_audit_output_experience",
    "unknown_or_unsupported",
)
FUTURE_READY_DATASETS = ("health_status",)


# The rules for merging the registered Snapshots into one Run-All input. A build
# records this version in its lineage, manifests, and digest; a store never
# records it. For the daily datasets (v2.0) and for Activities, Gear,
# activity_gear, and Personal Records (v2.1), these rules replace the merge
# fields of the v1.0 policy registry; the other datasets follow that registry
# until stage A3. Snapshots are numbered from 1 in the order of their Export
# observation times, and the numbers are given again in every build.
MERGE_RULES_VERSION = "garmin_snapshot_merge_rules:v2.1"
MERGE_RULES: dict[str, Any] = {
    "merge_rules_version": MERGE_RULES_VERSION,
    "store_policy_registry_version": REGISTRY_VERSION,
    "store_contract_version": CONTRACT_VERSION,
    "daily_datasets": {
        "datasets": [
            "hill_score_daily",
            "endurance_score_daily",
            "race_prediction_daily",
            "sleep_daily",
            "uds_daily",
            "acute_training_load_daily",
            "training_readiness_daily",
            "vo2max_daily",
            "training_history_daily",
        ],
        "merge_mode": "every_distinct_record_compared_in_run_all",
        "conflict_policy": "disagreement_kept_empty_values_audited",
        "within_snapshot_conflict_policy": "disagreement_kept_empty_values_audited",
        "same_observation_time_conflict_policy": "disagreement_kept_empty_values_audited",
        "explicit_null_policy": "absent_counted_not_disagreement",
        "explicit_empty_policy": "absent_counted_not_disagreement",
        "snapshot_reference": "snapshot_number_in_export_observed_order",
        "keep_last": False,
        "automatic_winner": False,
    },
    "entity_datasets": {
        "datasets": [
            "activities",
            "gear",
            "activity_gear",
            "personal_records",
        ],
        "merge_mode": "latest_snapshot_containing_the_field",
        "snapshot_order": "export_observed_at",
        "field_unit": "top_level_field_replaced_whole",
        "explicit_null_policy": "value_removed_field_empty",
        "explicit_empty_policy": "value_removed_field_empty",
        "explicit_empty_values": ["null", "empty_string", "empty_list", "empty_object"],
        "absent_field_policy": "not_observed_earlier_value_kept",
        "absent_record_policy": "kept_last_seen_snapshot_audited",
        "earlier_values": "kept_in_dataset_audit_with_snapshot_numbers",
        "update_comparison": "empty_values_alike_numbers_by_value_booleans_apart",
        "conflict_policy": "deterministic_if_ordered_else_stop",
        "snapshot_reference": "snapshot_number_in_export_observed_order",
        "automatic_deletion": False,
    },
    "dataset_rules": {
        "sleep_daily": {
            "missing_calendar_date_policy": "sleep_day_from_end_time_as_one_shot",
        },
        "hrv_daily": {
            "snapshot_reference": "snapshot_numbers_of_the_snapshots_holding_the_fit_file",
        },
        "activity_gear": {
            "absent_link_policy": "removed_and_audited_when_the_latest_snapshot_shows_the_change",
            "absent_link_removal_requires": [
                "gear_links_object_in_the_latest_snapshot",
                "gear_in_the_latest_snapshot",
                "activity_in_the_latest_snapshot",
            ],
        },
    },
    "other_datasets_follow": REGISTRY_VERSION,
}


def merge_rules() -> dict[str, Any]:
    """Return the Snapshot merge rules as a JSON-serializable object."""
    return copy.deepcopy(MERGE_RULES)


def public_registry() -> dict[str, Any]:
    """Return the frozen public policy registry as a JSON-serializable object."""
    return {
        "registry_version": REGISTRY_VERSION,
        "contract_version": CONTRACT_VERSION,
        "target_release": "1.3.0",
        "defaults": DEFAULTS,
        "policies": [POLICIES[name] for name in PUBLIC_POLICY_ORDER],
        "future_ready_policies": [
            {
                "dataset": name,
                "merge_mode": "daily_state_upsert",
                "public_dataset_status": "not_in_v1.2.0",
            }
            for name in FUTURE_READY_DATASETS
        ],
    }


__all__ = [
    "CONTRACT_VERSION",
    "DEFAULTS",
    "FUTURE_READY_DATASETS",
    "MERGE_RULES",
    "MERGE_RULES_VERSION",
    "POLICIES",
    "PUBLIC_POLICY_ORDER",
    "REGISTRY_VERSION",
    "merge_rules",
    "public_registry",
]
