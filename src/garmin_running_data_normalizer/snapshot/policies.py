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
# until stage A3d. Snapshots are numbered from 1 in the order of their
# Export observation times, and the numbers are given again in every build.
# From v2.2, Snapshots with the same content are one Snapshot, and a store that
# holds the Exports of more than one account stops the build. From v2.3, Snapshots
# observed at the same time are one time point; the repeated records of
# Activities, Gear, activity_gear, and Personal Records within one time point
# are compared as in a one-shot run instead of stopping the build, a change
# is a difference between time points, identifiers written in two ways name
# one record, and copies within one Snapshot are counted as in a one-shot run.
# From v2.4, a file that a one-shot run leaves out, or does not read because of
# its size, is left out of the build in the same way and listed by Snapshot
# number, and the records that the latest Snapshot lacks while a file of their
# family was left out from it are marked. From v2.5, a daily record without a
# stable key, such as one without a date, is not held: it is written for
# Run-All, which leaves it out as a one-shot run does, or only counts it when
# it holds no value. From v2.6, an identifier is read as Run-All reads it (an
# integral number such as 123.0 is 123, and only the ASCII digits are digits),
# and a record of Activities, Gear, activity_gear, or Personal Records without
# a usable identifier is passed to Run-All in the same way. From v2.7, the
# build leaves the values of another form as they are, and Run-All leaves them
# empty and keeps them in its audit records as a one-shot run does; a Lactate
# Threshold candidate with such a value no longer stops the build. From v2.8,
# the build writes text with a lone UTF-16 surrogate, such as a truncated
# emoji, with U+FFFD in its place as it reads a file that Run-All reads, and
# lists the file with the number of texts repaired by Snapshot number, as a
# one-shot run counts them. From v2.9, the build and Run-All read the records
# of a file in one way: an item of a list of records that is not an object,
# and a value of another form in the place of a list of records, are passed
# to Run-All as marks without a key, which Run-All leaves out as a one-shot
# run does, or only counts when the item is an empty value; and the Lactate
# Threshold candidates are read as Run-All reads them. From v2.10, the build
# keeps the activity of a VO2max record from the files of either series, as a
# one-shot run reads it (stage A3d-4b). From v2.11, the build tells the files
# of an Export as a one-shot run tells them, a member of a ZIP file by its
# name within the ZIP file and a daily file by the beginning of its name, to
# read and count them, and counts as unknown evidence only the JSON and FIT
# files of no family (stage A3d-4c-1). From v2.12, a record of Activities,
# Gear, links, or Personal Records carries the import numbers of every
# Snapshot that holds it, and the build no longer counts the observations of
# Source Completeness, which Run-All counts from its rows (stage A3d-4c-2).
# From v2.13, the build lists the files that a one-shot run does not read, by
# Snapshot number, and writes a ZIP file inside a ZIP file of the Export under
# a name that Run-All does not open, as a one-shot run does not read it (stage
# A4b). From v2.14, the build keeps the Gear key of a link under a name of its
# own and writes the link for Run-All with the fields of the Export only, and
# passes the copies of a record within one Snapshot as one record only when
# they also hold the same fields, so that Run-All counts the fields that it
# does not read as a one-shot run counts them (stage A4c-1). From v2.15, the
# build counts the fields of the daily rows and the Lactate Threshold candidates
# that their dataset does not read, which it leaves out, by name, as it counts
# the private fields, and Run-All takes the counts from it (stage A4c-2). From
# v2.16, the build merges the source names of one field (the Gear type) as one
# field across time points when a record uses more than one of them: the last
# time point that holds any of them gives the names that go on, and a change
# is listed once, under the names joined by "|" (stage A4d-1). From v2.17, so
# does it the two names of the start of an Activity (stage A4d-2).
MERGE_RULES_VERSION = "garmin_snapshot_merge_rules:v2.17"
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
        "copies_within_snapshot": "counted_as_in_a_one_shot_run",
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
        "merge_mode": "latest_time_point_containing_the_field",
        "snapshot_order": "export_observed_at",
        "time_point": "snapshots_observed_at_the_same_time",
        "within_time_point_policy": "compared_as_in_a_one_shot_run",
        "within_snapshot_conflict_policy": "disagreement_kept_empty_values_audited",
        "same_observation_time_conflict_policy": "disagreement_kept_empty_values_audited",
        "copies_within_snapshot": "merged_and_counted_as_in_a_one_shot_run",
        "update_policy": "differences_between_time_points_only",
        "field_unit": "top_level_field_replaced_whole",
        "explicit_null_policy": "value_removed_field_empty",
        "explicit_empty_policy": "value_removed_field_empty",
        "explicit_empty_values": ["null", "empty_string", "empty_list", "empty_object"],
        "absent_field_policy": "not_observed_earlier_value_kept",
        "absent_record_policy": "kept_last_seen_snapshot_audited",
        "earlier_values": "kept_in_dataset_audit_with_snapshot_numbers",
        "update_comparison": "empty_values_alike_numbers_by_value_booleans_apart",
        "identifier_forms": "spaces_trimmed_ascii_digits_and_integral_numbers_as_numbers_one_identifier",
        "snapshot_reference": "snapshot_number_in_export_observed_order",
        "automatic_deletion": False,
    },
    "dataset_rules": {
        "sleep_daily": {
            "missing_calendar_date_policy": "sleep_day_from_end_time_as_one_shot",
        },
        "hrv_daily": {
            "snapshot_reference": "snapshot_numbers_of_the_snapshots_holding_the_fit_file",
            "copies_within_snapshot": "counted_as_files_as_in_a_one_shot_run",
        },
        "activity_gear": {
            "absent_link_policy": "removed_and_audited_when_the_latest_snapshot_shows_the_change",
            "absent_link_removal_requires": [
                "gear_links_object_in_the_latest_time_point",
                "gear_in_the_latest_time_point",
                "activity_in_the_latest_time_point",
            ],
        },
    },
    "same_content_snapshots": "counted_once_earliest_observed_kept",
    "account_consistency": "one_account_per_store_else_stop",
    "files_that_cannot_be_read": {
        "policy": "left_out_as_in_a_one_shot_run",
        "listed_by": "snapshot_number_in_export_observed_order",
        "json_over_the_file_limit_that_no_dataset_reads": "not_read_as_in_a_one_shot_run",
        "zip_file_without_listed_members": "left_out_with_the_reason_from_registration",
        "records_the_latest_snapshot_lacks": "kept_and_marked_when_a_file_of_their_family_was_left_out",
        "accounts": "files_left_out_not_compared",
    },
    "rows_without_a_stable_key": {
        "datasets": [
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
            "training_history_daily",
        ],
        "policy": "passed_to_run_all_and_left_out_as_in_a_one_shot_run",
        "same_content": "passed_once_with_one_snapshot_number_per_occurrence",
        "copies_within_snapshot": "counted_as_in_a_one_shot_run",
        "rows_that_hold_no_value": "counted_as_empty_records_not_announced_in_daily_datasets",
        "identifiers_that_cannot_name_a_record": "passed_to_run_all_without_a_key",
        "review_hold": False,
    },
    "values_of_another_form": {
        "policy": "passed_to_run_all_which_leaves_them_empty_and_keeps_them",
        "lactate_threshold_candidates": "passed_to_run_all_instead_of_stopping_the_build",
    },
    "text_with_a_lone_surrogate": {
        "policy": "written_with_u_fffd_as_the_file_is_read_as_in_a_one_shot_run",
        "files": "those_that_run_all_reads",
        "count": "texts_and_names_repaired_listed_by_file_and_snapshot_number",
        "equal_names_once_repaired": "later_value_kept_as_json_keeps_the_later_of_two_equal_names",
    },
    "items_that_are_not_records": {
        "policy": "passed_to_run_all_as_marks_without_a_key_and_left_out_as_in_a_one_shot_run",
        "items_that_are_empty_values": "counted_as_empty_records_not_announced",
        "lists_of_records_of_another_form": "one_mark_left_out_as_records_not_readable",
        "same_content": "passed_once_with_one_snapshot_number_per_occurrence",
        "activity_gear_marks": "passed_without_a_gear_key",
        "lactate_threshold_candidates": "marks_passed_apart_from_the_candidates_and_candidates_read_as_run_all_reads_them",
    },
    # The fields of a record that the build keeps, as a one-shot run reads
    # them (stage A3d-4b).
    "fields_kept": {
        "vo2max_activity_id": "kept_from_the_files_of_either_series",
    },
    # The files of an Export, told and counted as a one-shot run tells and
    # counts them (stage A3d-4c-1).
    "file_names": {
        "policy": "told_as_in_a_one_shot_run",
        "zip_members": "told_by_their_names_within_the_zip_file",
        "daily_files": "told_by_the_beginning_of_their_names",
        "unknown_evidence": "json_and_fit_files_of_no_family_as_in_a_one_shot_run",
    },
    # The observations of Source Completeness: the output rows that each
    # Snapshot observed, which Run-All counts as a one-shot run counts its
    # rows (stage A3d-4c-2).
    "source_completeness_observations": {
        "counted_by": "run_all_from_the_output_rows_of_each_snapshot",
        "entity_records": "written_with_the_import_numbers_of_every_snapshot_holding_them",
    },
    # The files that a one-shot run does not read, listed as it lists them
    # (stage A4b).
    "files_not_read": {
        "listed_by": "snapshot_number_as_in_a_one_shot_run",
        "files_of_a_form_that_no_dataset_reads": "format_not_read",
        "zip_files_inside_zip_files": "zip_in_zip_and_written_under_a_name_that_run_all_does_not_open",
        "files_outside_the_export": "not_registered_so_not_listed",
    },
    # The source fields that Run-All does not read, which it counts from the
    # records that the build passes as a one-shot run counts them (stage A4c-1).
    "fields_not_read": {
        "counted_by": "run_all_from_the_records_that_the_build_passes",
        "activity_gear_gear_key": "kept_by_the_build_under_its_own_name_and_not_written_with_the_link",
        "copies_within_snapshot": "counted_as_in_a_one_shot_run",
        "copies_passed_as_one_record": "only_when_they_hold_the_same_fields",
        "daily_records_and_lactate_threshold_candidates": "counted_by_the_build_by_content_as_run_all_keeps_them",
    },
    # The source names of one field of the records that the build merges
    # across time points (stage A4d-1).
    "names_of_one_field": {
        "activities": [["startTimeGmt", "beginTimestamp"]],
        "gear": [["gearTypeName", "gearType"]],
        "records_using_two_or_more_names": "one_field_across_time_points_the_latest_time_point_holding_any_name_gives_the_names",
        "names_not_given_by_that_time_point": "not_carried_and_not_written_as_probes",
        "change": "listed_once_under_the_names_joined_by_a_vertical_bar",
        "records_using_one_name": "merged_field_by_field_as_before",
        "daily_datasets": "observations_passed_with_every_name_run_all_reads_the_names",
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
