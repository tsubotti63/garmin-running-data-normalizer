from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from .run_all import (
    DATASET_PATHS,
    DATASET_TABLE,
    OUTPUT_PATHS,
    RUN_ALL_VERSION,
    SNAPSHOT_LIFECYCLE_PATHS,
)


MANIFEST_FORMAT = "garmin-running-data-normalizer-run-manifest-v1"
SUMMARY_FORMAT = "garmin-running-data-normalizer-run-summary-v1"
SUMMARY_STATUSES = {"PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS"}
FAMILY_STATUSES = {"PROCESSED", "SKIPPED_NOT_PRESENT", "PROCESSED_EMPTY", "PARTIAL"}
QUIET_OPTIONAL_FAMILIES = {
    "hill_score",
    "endurance_score",
    "race_prediction",
    "sleep",
    "uds",
    "acute_training_load",
    "training_readiness",
    "vo2max",
    "hrv",
    "training_history",
}
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
    "audit/hill_score_daily.json",
    "audit/endurance_score_daily.json",
    "audit/lactate_threshold_candidates.json",
    "audit/race_prediction_daily.json",
    "audit/sleep_daily.json",
    "audit/uds_daily.json",
    "audit/acute_training_load_daily.json",
    "audit/training_readiness_daily.json",
    "audit/vo2max_daily.json",
    "audit/hrv_daily.json",
    "audit/training_history_daily.json",
    "analysis/activities.csv",
    "analysis/performance_metrics_daily.csv",
    "qa/dataset_summary.json",
    "qa/relationship_summary.json",
    "qa/performance_metrics_summary.json",
    "qa/daily_metrics_summary.json",
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
    "hill_score_daily": {
        "role": "source-provided daily hill performance context",
        "authority": "normalized source of truth",
        "analysis_suitability": "daily context with raw source codes; no label inference",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "public-safe-metric-fields",
    },
    "endurance_score_daily": {
        "role": "source-provided daily endurance performance context",
        "authority": "normalized source of truth",
        "analysis_suitability": "daily context with raw source codes; no label inference",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "public-safe-metric-fields",
    },
    "race_prediction_daily": {
        "role": "source-provided race-prediction observations",
        "authority": "normalized source of truth",
        "analysis_suitability": "observation context with a non-canonical derived daily view; not an Activity fact join",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "public-safe-metric-fields",
    },
    "sleep_daily": {
        "role": "bounded daily sleep context",
        "authority": "normalized source of truth",
        "analysis_suitability": "daily condition context with explicit review states",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
    "uds_daily": {
        "role": "source-provided daily activity and stress context",
        "authority": "normalized source of truth",
        "analysis_suitability": "generation-aware daily condition context",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
    "acute_training_load_daily": {
        "role": "source-provided acute training-load observations",
        "authority": "normalized source of truth",
        "analysis_suitability": "observation context without recomputation or daily row selection",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
    "training_readiness_daily": {
        "role": "source-provided training-readiness observations",
        "authority": "normalized source of truth",
        "analysis_suitability": "observation context without component inference or daily row selection",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
    "vo2max_daily": {
        "role": "generation-aware VO2Max source observations",
        "authority": "normalized source of truth",
        "analysis_suitability": "two source series retained without cross-series overwrite",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
    "hrv_daily": {
        "role": "bounded FIT-derived HRV reference",
        "authority": "analysis reference only",
        "analysis_suitability": "reviewed trend context; not a daily source of truth",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
    "training_history_daily": {
        "role": "limited training-status source observations",
        "authority": "normalized source of truth",
        "analysis_suitability": "date, timestamp, status, and optional sport context only",
        "relationship_status": "not_yet_defined",
        "privacy_classification": "personal-local-metric-fields",
    },
}


def _activity_join(
    *,
    status: str,
    source_fields: tuple[str, ...],
    target_fields: tuple[str, ...],
    cardinality: str,
    semantics: str,
    via_datasets: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    return [
        {
            "target_dataset": "activities",
            "status": status,
            "source_fields": list(source_fields),
            "target_fields": list(target_fields),
            "cardinality": cardinality,
            "semantics": semantics,
            "direct": status in {"self", "explicit", "explicit_or_independent"},
            "via_datasets": list(via_datasets),
        }
    ]


def _relationship_metadata(
    *,
    relationship_role: str,
    semantic_role: str | None = None,
    activity_relationship: str,
    join_guidance: list[dict[str, Any]],
    cardinality: str,
    allowed_use: str,
    forbidden_join_guidance: tuple[str, ...],
    limitations: tuple[str, ...] = (),
    derived_projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "relationship_role": relationship_role,
        "semantic_role": semantic_role or relationship_role,
        "canonical": True,
        "projection_of": None,
        "activity_relationship": activity_relationship,
        "join_guidance": join_guidance,
        "forbidden_join_guidance": list(forbidden_join_guidance),
        "cardinality": cardinality,
        "allowed_use": allowed_use,
        "limitations": list(limitations),
        "derived_projection": derived_projection,
    }


DATASET_RELATIONSHIP_METADATA = {
    "activities": _relationship_metadata(
        relationship_role="primary_fact",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="self",
            source_fields=("garmin_activity_key",),
            target_fields=("garmin_activity_key",),
            cardinality="one_to_one",
            semantics="fact",
        ),
        cardinality="one_activity_per_stable_key",
        allowed_use="Primary Activity fact analysis and reviewed explicit links.",
        forbidden_join_guidance=("Do not infer links from timestamp proximity.",),
        derived_projection={
            "path": "analysis/activities.csv",
            "canonical": False,
            "projection_of": "activities",
            "selection_rule": None,
        },
    ),
    "gear": _relationship_metadata(
        relationship_role="primary_fact",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="explicit_via_activity_gear",
            source_fields=("gear_key",),
            target_fields=("garmin_activity_key",),
            cardinality="many_to_many_via_link_table",
            semantics="fact_attribute",
            via_datasets=("activity_gear",),
        ),
        cardinality="one_gear_per_stable_key",
        allowed_use="Join through activity_gear only.",
        forbidden_join_guidance=("Do not join by display name or date.",),
    ),
    "activity_gear": _relationship_metadata(
        relationship_role="direct_explicit_link",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="explicit",
            source_fields=("garmin_activity_key",),
            target_fields=("garmin_activity_key",),
            cardinality="many_to_one",
            semantics="link",
        ),
        cardinality="many_links_to_one_activity",
        allowed_use="Authoritative Activity/Gear link table.",
        forbidden_join_guidance=("Do not substitute source activity_id for the declared key.",),
    ),
    "personal_records": _relationship_metadata(
        relationship_role="primary_fact",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="explicit_or_independent",
            source_fields=("garmin_activity_key",),
            target_fields=("garmin_activity_key",),
            cardinality="many_to_zero_or_one",
            semantics="fact",
        ),
        cardinality="many_records_to_zero_or_one_activity",
        allowed_use="Join nonzero source Activity identities; preserve zero as independent.",
        forbidden_join_guidance=("Do not force an Activity identity for independent records.",),
    ),
    "fit_sessions": _relationship_metadata(
        relationship_role="primary_fact",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="explicit_via_activity_fit_links",
            source_fields=("fit_session_key",),
            target_fields=("garmin_activity_key",),
            cardinality="one_to_one_within_eligible_population",
            semantics="fact",
            via_datasets=("activity_fit_links",),
        ),
        cardinality="one_session_per_stable_key",
        allowed_use="Join to Activities only through activity_fit_links.",
        forbidden_join_guidance=("Do not join FIT and Activities by timestamp alone.",),
    ),
    "fit_laps": _relationship_metadata(
        relationship_role="direct_explicit_link",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="indirect_via_fit_sessions_and_activity_fit_links",
            source_fields=("fit_session_key",),
            target_fields=("garmin_activity_key",),
            cardinality="many_to_one_indirect",
            semantics="fact_child",
            via_datasets=("fit_sessions", "activity_fit_links"),
        ),
        cardinality="many_laps_to_one_fit_session",
        allowed_use="Join to FIT Sessions by fit_session_key, then use an explicit Activity/FIT link.",
        forbidden_join_guidance=("Do not join laps directly to Activities by time or ordinal.",),
    ),
    "activity_fit_links": _relationship_metadata(
        relationship_role="direct_explicit_link",
        activity_relationship="allowed",
        join_guidance=_activity_join(
            status="explicit",
            source_fields=("garmin_activity_key",),
            target_fields=("garmin_activity_key",),
            cardinality="one_to_one_within_eligible_population",
            semantics="link",
        ),
        cardinality="one_to_one_within_eligible_population",
        allowed_use="Sole Activity/FIT relationship authority.",
        forbidden_join_guidance=("Do not promote unresolved or ambiguous candidates.",),
    ),
    "hill_score_daily": _relationship_metadata(
        relationship_role="performance_context",
        semantic_role="daily_performance_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="not_yet_defined",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="one_to_many_context_candidate",
            semantics="daily_performance_context",
        ),
        cardinality="one_observation_per_calendar_day",
        allowed_use="Standalone daily performance context.",
        forbidden_join_guidance=("Do not materialize an Activity relationship from calendar_date.",),
        derived_projection={
            "path": "analysis/performance_metrics_daily.csv",
            "canonical": False,
            "projection_of": "hill_score_daily",
            "selection_rule": None,
        },
    ),
    "endurance_score_daily": _relationship_metadata(
        relationship_role="performance_context",
        semantic_role="daily_performance_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="not_yet_defined",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="one_to_many_context_candidate",
            semantics="daily_performance_context",
        ),
        cardinality="one_observation_per_calendar_day",
        allowed_use="Standalone daily performance context.",
        forbidden_join_guidance=("Do not materialize an Activity relationship from calendar_date.",),
        derived_projection={
            "path": "analysis/performance_metrics_daily.csv",
            "canonical": False,
            "projection_of": "endurance_score_daily",
            "selection_rule": None,
        },
    ),
    "race_prediction_daily": _relationship_metadata(
        relationship_role="prediction_context",
        semantic_role="daily_performance_prediction",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="not_yet_defined",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="many_to_many_context_only",
            semantics="daily_performance_prediction",
        ),
        cardinality="many_source_observations_per_calendar_day",
        allowed_use="Compare prediction observations by date without treating them as race facts.",
        forbidden_join_guidance=("Do not join an observation to an Activity by date or timestamp.",),
        limitations=("Prediction values are Garmin algorithm output, not measured results.",),
        derived_projection={
            "path": "qa/daily_metrics_summary.json",
            "canonical": False,
            "projection_of": "race_prediction_daily",
            "selection_rule": None,
        },
    ),
    "sleep_daily": _relationship_metadata(
        relationship_role="condition_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("sleep_day",),
            target_fields=("activity_date_local",),
            cardinality="one_to_many_context_only",
            semantics="same_day_condition_context",
        ),
        cardinality="one_reviewed_sleep_state_per_sleep_day",
        allowed_use=(
            "Same-day comparison using only resolved/available Sleep context while "
            "keeping Sleep separate from Activity facts."
        ),
        forbidden_join_guidance=(
            "Do not use needs_review or excluded Sleep rows for context joins, "
            "merge Sleep fields into an Activity fact, or infer causality.",
        ),
    ),
    "uds_daily": _relationship_metadata(
        relationship_role="condition_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="one_to_many_context_only",
            semantics="same_day_condition_context",
        ),
        cardinality="one_source_state_per_calendar_day",
        allowed_use="Same-day condition comparison while keeping UDS separate from Activity facts.",
        forbidden_join_guidance=("Do not merge UDS fields into an Activity fact or infer missing metrics.",),
    ),
    "acute_training_load_daily": _relationship_metadata(
        relationship_role="performance_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="many_to_many_context_only",
            semantics="same_day_performance_context",
        ),
        cardinality="many_source_observations_per_calendar_day",
        allowed_use="Same-day performance context without selecting one observation.",
        forbidden_join_guidance=("Do not create a direct Activity link or apply latest-wins.",),
        derived_projection={
            "path": "qa/daily_metrics_summary.json",
            "canonical": False,
            "projection_of": "acute_training_load_daily",
            "selection_rule": None,
        },
    ),
    "training_readiness_daily": _relationship_metadata(
        relationship_role="performance_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="many_to_many_context_only",
            semantics="same_day_performance_context",
        ),
        cardinality="many_source_observations_per_calendar_day",
        allowed_use="Same-day readiness context without selecting one observation.",
        forbidden_join_guidance=("Do not create a direct Activity link or infer component causes.",),
        derived_projection={
            "path": "qa/daily_metrics_summary.json",
            "canonical": False,
            "projection_of": "training_readiness_daily",
            "selection_rule": None,
        },
    ),
    "vo2max_daily": _relationship_metadata(
        relationship_role="performance_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="many_to_many_context_only",
            semantics="same_day_performance_context",
        ),
        cardinality="many_source_observations_per_calendar_day_and_series",
        allowed_use="Compare source-series observations without collapsing generations.",
        forbidden_join_guidance=(
            "Do not use source_activity_id as a public join authority.",
            "Do not overwrite one source series with another.",
        ),
        limitations=("Source series and sport remain part of observation identity.",),
        derived_projection={
            "path": "qa/daily_metrics_summary.json",
            "canonical": False,
            "projection_of": "vo2max_daily",
            "selection_rule": None,
        },
    ),
    "hrv_daily": _relationship_metadata(
        relationship_role="condition_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="one_to_many_context_only",
            semantics="same_day_condition_context",
        ),
        cardinality="one_resolved_or_review_row_per_calendar_day",
        allowed_use="Reviewed same-day trend context only.",
        forbidden_join_guidance=("Do not merge HRV into Activity facts or select a conflicting value.",),
        limitations=("analysis_reference_only; not a daily source of truth.",),
    ),
    "training_history_daily": _relationship_metadata(
        relationship_role="performance_context",
        activity_relationship="not_yet_defined",
        join_guidance=_activity_join(
            status="context_only",
            source_fields=("calendar_date",),
            target_fields=("activity_date_local",),
            cardinality="many_to_many_context_only",
            semantics="same_day_performance_context",
        ),
        cardinality="many_source_observations_per_calendar_day",
        allowed_use="Same-day training-status context without selecting one observation.",
        forbidden_join_guidance=("Do not create a direct Activity link or apply latest-wins.",),
        derived_projection={
            "path": "qa/daily_metrics_summary.json",
            "canonical": False,
            "projection_of": "training_history_daily",
            "selection_rule": None,
        },
    ),
}


LACTATE_THRESHOLD_RELATIONSHIP_METADATA = {
    "relationship_role": "observation_family",
    "semantic_role": "performance_threshold_observation",
    "canonical": False,
    "projection_of": None,
    "record_grain": "source-backed threshold observation",
    "stable_key": [],
    "machine_stable_key_status": "PRODUCT_DECISION_REQUIRED",
    "activity_relationship": "not_yet_defined",
    "families": [
        "history",
        "latest_snapshot",
        "profile_state",
        "derived_evidence",
    ],
    "join_guidance": [],
    "forbidden_join_guidance": [
        "Do not join candidate observations to Activities.",
        "Do not select latest-wins across observation families.",
    ],
    "cardinality": "many_candidate_observations_across_source_families",
    "allowed_use": "Audit and Product review of source-backed threshold observations.",
    "limitations": [
        "Candidate/audit-only; no stable dataset promotion.",
        "Units, timezone, and machine stable key remain unconfirmed.",
    ],
    "derived_projection": {
        "path": None,
        "canonical": False,
        "projection_of": "lactate_threshold_candidates",
        "selection_rule": None,
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
    "hill_score_daily": (
        "calendar_date", "overall_score", "strength_score", "endurance_score",
        "classification_id", "feedback_phrase_id",
    ),
    "endurance_score_daily": (
        "calendar_date", "overall_score", "classification", "feedback_phrase",
    ),
    "race_prediction_daily": (
        "calendar_date", "observation_timestamp", "race_time_5k_sec", "race_time_10k_sec",
        "race_time_half_sec", "race_time_marathon_sec",
    ),
    "sleep_daily": (
        "sleep_day", "sleep_start_local", "sleep_end_local",
        "sleep_window_minutes_including_awake", "sleep_duration_minutes_ex_awake",
        "sleep_stage_deep_minutes", "sleep_stage_light_minutes",
        "sleep_stage_rem_minutes", "sleep_score", "sleep_awake_minutes",
        "sleep_stage_available_flag", "sleep_score_available_flag",
        "sleep_normalization_status", "sleep_limitation_type", "sleep_reason_code",
        "sleep_source_available_for_analysis_flag",
    ),
    "uds_daily": (
        "calendar_date", "steps", "distance_meters", "active_calories",
        "bmr_calories", "resting_heart_rate", "min_heart_rate", "max_heart_rate",
        "bb_charged_value", "bb_drained_value", "stress_total_averageStressLevel",
        "stress_total_maxStressLevel", "stress_total_stressDuration",
        "stress_total_restDuration", "raw_has_body_battery",
        "raw_has_all_day_stress", "raw_has_body_battery_feedback",
    ),
    "acute_training_load_daily": (
        "calendar_date", "observation_timestamp", "acwr_percent", "acwr_status",
        "daily_training_load_acute", "daily_training_load_chronic",
        "daily_acute_chronic_workload_ratio",
    ),
    "training_readiness_daily": (
        "calendar_date", "observation_timestamp", "training_readiness_score", "training_readiness_level",
        "training_readiness_recovery_time", "acwr_factor_percent",
        "stress_history_factor_percent", "hrv_factor_percent",
        "sleep_history_factor_percent", "training_readiness_acute_load",
        "training_readiness_hrv_weekly_average", "training_readiness_valid_sleep",
        "training_readiness_sleep_score",
    ),
    "vo2max_daily": (
        "calendar_date", "observation_timestamp", "vo2max", "vo2max_source_series", "sport",
        "source_activity_id",
        "source_confidence", "max_met", "max_met_category", "calibrated_data",
    ),
    "hrv_daily": (
        "calendar_date", "hrv_value", "semantics_status", "analysis_role",
        "record_count_for_date", "source_file_count_for_date", "dedupe_status",
    ),
    "training_history_daily": (
        "calendar_date", "observation_timestamp", "training_status", "sport",
    ),
}

DATASET_OPTIONAL_FIELDS = {
    "fit_laps": frozenset(
        {
            "start_time",
            "total_elapsed_time",
            "total_timer_time",
            "total_distance",
            "avg_speed",
            "max_speed",
            "avg_heart_rate",
            "max_heart_rate",
            "avg_cadence",
            "max_cadence",
            "avg_power",
            "max_power",
            "total_ascent",
            "total_descent",
            "timestamp",
        }
    ),
}

DATASET_NONNULL_FIELDS = {
    "activities": frozenset(
        {
            "garmin_activity_key",
            "memo_present",
            "source_path",
            "source_sha256",
            "source_confidence",
        }
    ),
    "gear": frozenset({"gear_key", "source_path", "source_sha256"}),
    "activity_gear": frozenset(DATASET_FIELDS["activity_gear"]),
    "personal_records": frozenset(
        {
            "personal_record_id",
            "activity_id",
            "source_record_index",
            "activity_relationship_status",
            "activity_relationship_reason",
            "source_path",
            "source_sha256",
            "source_confidence",
        }
    ),
    "fit_sessions": frozenset(
        {
            "fit_file_id",
            "fit_session_key",
            "session_ordinal",
            "record_count",
            "lap_count",
            "source_path",
            "source_sha256",
        }
    ),
    "fit_laps": frozenset(
        {
            "fit_file_id",
            "fit_session_key",
            "fit_lap_key",
            "session_ordinal",
            "lap_ordinal_within_session",
            "lap_index",
            "source_path",
            "source_sha256",
        }
    ),
    "activity_fit_links": frozenset(
        set(DATASET_FIELDS["activity_fit_links"])
        - {
            "exclusion_reason",
            "distance_delta_m",
            "duration_delta_seconds",
        }
    ),
    "hill_score_daily": frozenset({"calendar_date", "overall_score"}),
    "endurance_score_daily": frozenset({"calendar_date", "overall_score"}),
    "race_prediction_daily": frozenset(DATASET_FIELDS["race_prediction_daily"]),
    "sleep_daily": frozenset(
        {
            "sleep_day", "sleep_stage_available_flag", "sleep_score_available_flag",
            "sleep_normalization_status", "sleep_limitation_type", "sleep_reason_code",
            "sleep_source_available_for_analysis_flag",
        }
    ),
    "uds_daily": frozenset(
        {
            "calendar_date", "raw_has_body_battery", "raw_has_all_day_stress",
            "raw_has_body_battery_feedback",
        }
    ),
    "acute_training_load_daily": frozenset({"calendar_date", "observation_timestamp"}),
    "training_readiness_daily": frozenset({"calendar_date", "observation_timestamp"}),
    "vo2max_daily": frozenset(
        {"calendar_date", "observation_timestamp", "vo2max", "vo2max_source_series", "sport"}
    ),
    "hrv_daily": frozenset(
        {
            "calendar_date", "semantics_status", "analysis_role",
            "record_count_for_date", "source_file_count_for_date", "dedupe_status",
        }
    ),
    "training_history_daily": frozenset(
        {"calendar_date", "observation_timestamp", "training_status"}
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


class SchemaContractError(ValueError):
    """Raised when normalized records contradict the public schema catalog."""


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


RELATIONSHIP_ROLES = frozenset(
    {
        "primary_fact",
        "direct_explicit_link",
        "daily_context",
        "condition_context",
        "performance_context",
        "prediction_context",
        "observation_family",
        "derived_projection",
        "not_yet_defined",
    }
)
ACTIVITY_RELATIONSHIP_STATUSES = frozenset(
    {"allowed", "not_yet_defined", "forbidden"}
)
JOIN_GUIDANCE_STATUSES = frozenset(
    {
        "self",
        "explicit",
        "explicit_or_independent",
        "explicit_via_activity_gear",
        "explicit_via_activity_fit_links",
        "indirect_via_fit_sessions_and_activity_fit_links",
        "context_only",
        "not_yet_defined",
    }
)


def _validate_relationship_metadata() -> None:
    runtime_names = {item["name"] for item in _runtime_datasets()}
    if set(DATASET_RELATIONSHIP_METADATA) != runtime_names:
        raise OutputExperienceError(
            "relationship metadata datasets do not match runtime datasets"
        )
    for dataset, metadata in DATASET_RELATIONSHIP_METADATA.items():
        if metadata.get("relationship_role") not in RELATIONSHIP_ROLES:
            raise OutputExperienceError(
                f"{dataset}: relationship role is unsupported"
            )
        if not isinstance(metadata.get("semantic_role"), str) or not metadata[
            "semantic_role"
        ]:
            raise OutputExperienceError(
                f"{dataset}: semantic role must be declared"
            )
        if metadata.get("activity_relationship") not in (
            ACTIVITY_RELATIONSHIP_STATUSES
        ):
            raise OutputExperienceError(
                f"{dataset}: activity relationship status is unsupported"
            )
        if metadata.get("canonical") is not True or metadata.get(
            "projection_of"
        ) is not None:
            raise OutputExperienceError(
                f"{dataset}: normalized dataset must remain canonical"
            )
        for field in (
            "join_guidance",
            "forbidden_join_guidance",
            "limitations",
        ):
            if not isinstance(metadata.get(field), list):
                raise OutputExperienceError(
                    f"{dataset}: {field} must be an array"
                )
        if not isinstance(metadata.get("cardinality"), str) or not metadata[
            "cardinality"
        ]:
            raise OutputExperienceError(
                f"{dataset}: relationship cardinality must be declared"
            )
        for guidance in metadata["join_guidance"]:
            if not isinstance(guidance, Mapping):
                raise OutputExperienceError(
                    f"{dataset}: join guidance must contain objects"
                )
            if guidance.get("target_dataset") != "activities":
                raise OutputExperienceError(
                    f"{dataset}: unsupported join-guidance target"
                )
            if guidance.get("status") not in JOIN_GUIDANCE_STATUSES:
                raise OutputExperienceError(
                    f"{dataset}: join-guidance status is unsupported"
                )
            if not isinstance(guidance.get("source_fields"), list) or not isinstance(
                guidance.get("target_fields"), list
            ):
                raise OutputExperienceError(
                    f"{dataset}: join-guidance fields must be arrays"
                )
            if not isinstance(guidance.get("direct"), bool) or not isinstance(
                guidance.get("via_datasets"), list
            ):
                raise OutputExperienceError(
                    f"{dataset}: join-guidance path must be explicit"
                )
            if metadata["activity_relationship"] != "allowed" and guidance[
                "direct"
            ]:
                raise OutputExperienceError(
                    f"{dataset}: unsupported direct Activity relationship"
                )
        projection = metadata.get("derived_projection")
        if projection is not None and (
            not isinstance(projection, Mapping)
            or projection.get("canonical") is not False
            or projection.get("projection_of") != dataset
            or projection.get("selection_rule") is not None
        ):
            raise OutputExperienceError(
                f"{dataset}: derived projection contract is invalid"
            )

    lactate = LACTATE_THRESHOLD_RELATIONSHIP_METADATA
    if lactate.get("relationship_role") not in RELATIONSHIP_ROLES:
        raise OutputExperienceError(
            "lactate threshold relationship role is unsupported"
        )
    if lactate.get("canonical") is not False or lactate.get(
        "activity_relationship"
    ) != "not_yet_defined":
        raise OutputExperienceError(
            "lactate threshold candidate relationship boundary is invalid"
        )
    if (
        lactate.get("record_grain") != "source-backed threshold observation"
        or lactate.get("stable_key") != []
        or lactate.get("machine_stable_key_status")
        != "PRODUCT_DECISION_REQUIRED"
    ):
        raise OutputExperienceError(
            "lactate threshold candidate identity boundary is invalid"
        )


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
    _validate_relationship_metadata()
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
        set((*MANIFEST_OUTPUT_PATHS, *SNAPSHOT_LIFECYCLE_PATHS)),
        set(
            (
                *MANIFEST_OUTPUT_PATHS,
                *OPTIONAL_MANIFEST_OUTPUT_PATHS,
                *SNAPSHOT_LIFECYCLE_PATHS,
            )
        ),
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
    snapshot_generated_paths = [
        *OUTPUT_PATHS[:-2],
        *SNAPSHOT_LIFECYCLE_PATHS,
        *OUTPUT_PATHS[-2:],
    ]
    optional_snapshot_generated_paths = [
        *optional_generated_paths[:-2],
        *SNAPSHOT_LIFECYCLE_PATHS,
        *optional_generated_paths[-2:],
    ]
    if safe_generated_paths not in (
        list(OUTPUT_PATHS),
        optional_generated_paths,
        snapshot_generated_paths,
        optional_snapshot_generated_paths,
    ):
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
                if family not in QUIET_OPTIONAL_FAMILIES:
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

            if family in QUIET_OPTIONAL_FAMILIES:
                review_item_count = _non_negative_integer(
                    result.get("review_item_count", 0),
                    f"{family} review item count",
                )
                if "review_required_count" in result:
                    review_required_count = _non_negative_integer(
                        result.get("review_required_count"),
                        f"{family} review required count",
                    )
                    if review_required_count != review_item_count:
                        raise OutputExperienceError(
                            f"{family}: review-required and review-item counts differ"
                        )
                if review_item_count:
                    expected_warning_count += 1

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
    relationship_warning_count = _non_negative_integer(
        summary_object.get("relationship_warning_count", 0),
        "relationship warning count",
    )
    candidate_warning_count = _non_negative_integer(
        summary_object.get("candidate_warning_count", 0),
        "candidate warning count",
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
    if summary_warning_count != (
        total_family_warnings + relationship_warning_count + candidate_warning_count
    ):
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


def _snapshot_lifecycle_lines(summary: Mapping[str, Any]) -> list[str]:
    lifecycle = summary.get("snapshot_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return []
    datasets = _mapping(
        lifecycle.get("datasets"),
        "snapshot lifecycle datasets",
    )
    observed_range = _mapping(
        lifecycle.get("snapshot_observed_range", {}),
        "snapshot observed range",
    )
    labels = lifecycle.get("snapshot_labels", [])
    if not isinstance(labels, list):
        raise OutputExperienceError("snapshot labels must be a list")
    unknown_families = lifecycle.get("unknown_or_unsupported_families", [])
    if not isinstance(unknown_families, list):
        raise OutputExperienceError("snapshot unknown families must be a list")
    totals = {
        field: sum(
            int(item.get(field, 0))
            for item in datasets.values()
            if isinstance(item, Mapping)
        )
        for field in (
            "previous_only_retained_count",
            "new_record_count",
            "reappeared_record_count",
            "changed_record_count",
            "updated_field_count",
        )
    }
    lines = [
        "## Snapshot Accumulation",
        "",
        f"- Snapshots used: {lifecycle.get('snapshot_count')}",
        f"- Snapshot labels: {', '.join(str(value) for value in labels) or 'not supplied'}",
        "- Observed range: "
        f"{observed_range.get('first', 'unknown')} to "
        f"{observed_range.get('last', 'unknown')}",
        "- Canonical merge policy: `missing_is_not_delete`",
        f"- Previous-only retained: {totals['previous_only_retained_count']}",
        f"- New records added: {totals['new_record_count']}",
        f"- Reappeared records: {totals['reappeared_record_count']}",
        f"- Changed records: {totals['changed_record_count']}",
        f"- Updated fields: {totals['updated_field_count']}",
        f"- Explicit null reviews: {lifecycle.get('explicit_null_review_count', 0)}",
        f"- Explicit empty reviews: {lifecycle.get('explicit_empty_review_count', 0)}",
        f"- Review holds: {lifecycle.get('review_hold_count', 0)}",
        f"- Stop conflicts: {lifecycle.get('stop_conflict_count', 0)}",
        f"- Coverage gaps: {lifecycle.get('coverage_gap_count', 0)}",
        f"- Unknown or unsupported objects preserved: {lifecycle.get('unknown_or_unsupported_object_count', 0)}",
        "- Unknown or unsupported families: "
        f"{', '.join(str(value) for value in unknown_families) or 'None'}",
        "- Canonical completeness boundary: "
        f"{lifecycle.get('canonical_completeness_boundary', 'not supplied')}",
        "- Automatic deletion: No",
        "- Inference performed: No",
        f"- Policy: `{lifecycle.get('policy_registry_version', 'unknown')}`",
        f"- Parser: `{lifecycle.get('parser_version', 'unknown')}`",
        f"- Schema: `{lifecycle.get('schema_version', 'unknown')}`",
        "- Lifecycle evidence: `snapshot/snapshot_lineage.json`,",
        "  `snapshot/snapshot_coverage.json`, and",
        "  `snapshot/canonical_merge_summary.json`.",
        "",
        "| Dataset | Canonical | Previous-only retained | New | Reappeared | Changed | Updated fields |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset, item in datasets.items():
        if not isinstance(item, Mapping):
            continue
        lines.append(
            f"| {_code(dataset)} | {item.get('canonical_record_count', 0)} | "
            f"{item.get('previous_only_retained_count', 0)} | "
            f"{item.get('new_record_count', 0)} | "
            f"{item.get('reappeared_record_count', 0)} | "
            f"{item.get('changed_record_count', 0)} | "
            f"{item.get('updated_field_count', 0)} |"
        )
    lines.append("")
    return lines


def _has_observed_variant_evidence(summary: Mapping[str, Any]) -> bool:
    lifecycle = summary.get("snapshot_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return False
    datasets = lifecycle.get("datasets")
    if not isinstance(datasets, Mapping):
        return False
    return any(
        isinstance(datasets.get(name), Mapping)
        and bool(datasets[name].get("observed_variants"))
        for name in ("endurance_score_daily", "uds_daily")
    )


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
        "| Dataset | Role | Status | Records | Warnings | Path | Grain | Stable key | Authority | Analysis use | Relationship role / semantic role | Activity use | Cardinality | Canonical/projection | Privacy |",
        "|---|---|---|---:|---:|---|---|---|---|---|---|---|---|---|---|",
    ]
    for runtime in _runtime_datasets():
        dataset = manifest_by_name[runtime["name"]]
        family_result = family_results[runtime["family"]]
        family_status = family_result["status"]
        stable_key = ", ".join(_code(field) for field in runtime["stable_key"])
        presentation = DATASET_PRESENTATION[runtime["name"]]
        relationship = DATASET_RELATIONSHIP_METADATA[runtime["name"]]
        projection = (
            "canonical + derived projection"
            if relationship["derived_projection"] is not None
            else "canonical"
        )
        lines.append(
            "| "
            f"{_code(runtime['name'])} | {presentation['role']} | "
            f"{_code(family_status)} | {dataset['record_count']} | "
            f"{family_result['warning_count']} | {_code(runtime['output_path'])} | "
            f"{runtime['record_grain']} | {stable_key} | "
            f"{presentation['authority']} | {presentation['analysis_suitability']} | "
            f"{_code(relationship['relationship_role'])} / "
            f"{_code(relationship['semantic_role'])} | "
            f"{_code(relationship['activity_relationship'])} | "
            f"{_code(relationship['cardinality'])} | {projection} | "
            f"{_code(presentation['privacy_classification'])} |"
        )
    snapshot_lines = _snapshot_lifecycle_lines(summary)
    if snapshot_lines:
        lines.extend(["", *snapshot_lines])
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
            "- Hill and Endurance are standalone daily observations. Their activity",
            "  relationship is `not_yet_defined`; do not join them to activities by date.",
            "- Lactate Threshold remains candidate/audit-only until Product approves a",
            "  machine stable key and the remaining field authority gates.",
            "",
        ]
    )
    return "\n".join(lines)


V1_3_RELATIONSHIP_DATASETS = (
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
)


def _v1_3_relationship_lines() -> list[str]:
    runtime_by_name = {item["name"]: item for item in _runtime_datasets()}
    lines = [
        "## v1.3 Context and Observation Relationships",
        "",
        "These entries are analysis guidance, not newly declared direct links.",
        "A `context_only` entry permits same-day comparison while datasets remain",
        "separate; it never authorizes an Activity fact-table merge.",
        "",
        "| Dataset | Relationship role | Grain | Stable key | Activity guidance | Join fields | Cardinality | Canonical/projection |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for dataset in V1_3_RELATIONSHIP_DATASETS:
        runtime = runtime_by_name[dataset]
        metadata = DATASET_RELATIONSHIP_METADATA[dataset]
        guidance = metadata["join_guidance"][0]
        join_fields = (
            " + ".join(_code(field) for field in guidance["source_fields"])
            + " → "
            + " + ".join(_code(field) for field in guidance["target_fields"])
        )
        stable_key = ", ".join(_code(field) for field in runtime["stable_key"])
        projection = (
            "canonical source + derived non-canonical projection"
            if metadata["derived_projection"] is not None
            else "canonical source"
        )
        lines.append(
            f"| {_code(dataset)} | {_code(metadata['semantic_role'])} | "
            f"{_code(runtime['record_grain'])} | {stable_key} | "
            f"{_code(guidance['status'])} | {join_fields} | "
            f"{_code(guidance['cardinality'])} | {projection} |"
        )
    lactate = LACTATE_THRESHOLD_RELATIONSHIP_METADATA
    lines.extend(
        [
            f"| `lactate_threshold_candidates` | {_code(lactate['relationship_role'])} | "
            "`source-backed threshold observation` | `PRODUCT_DECISION_REQUIRED` | "
            "`not_yet_defined` | none | "
            f"{_code(lactate['cardinality'])} | candidate/audit only; no canonical daily projection |",
            "",
        ]
    )
    return lines


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
    variant_guidance = _has_observed_variant_evidence(summary)
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
            "Recommended trusted-local activity entry point: `analysis/activities.csv`.",
            "Daily Hill/Endurance context: `analysis/performance_metrics_daily.csv`.",
            "Other daily condition datasets are separate normalized JSON files listed",
            "in `DATASET_INVENTORY.md`; they are not Activity fact-table joins.",
            "",
        ]
    )
    if variant_guidance:
        lines.extend(
            [
                "When Endurance or UDS audit reports multiple observed values for one",
                "stable key, no value is automatically newer or more correct. Use the",
                "preserved observed variants for review or sensitivity analysis; a single",
                "canonical daily value is not selected without source-backed authority.",
                "",
            ]
        )
    lines.extend(_path_list("Available Analysis Files", analysis_paths))
    lines.extend(_path_list("QA Evidence", qa_paths))
    lines.extend(_path_list("Audit Evidence", audit_paths))
    lines.extend(_relationship_coverage_lines(relationship_summary))
    lines.extend(_snapshot_lifecycle_lines(summary))
    candidate = summary.get("candidate_features", {})
    if isinstance(candidate, Mapping) and isinstance(
        candidate.get("lactate_threshold"), Mapping
    ):
        lactate = candidate["lactate_threshold"]
        lines.extend(
            [
                "## Lactate Threshold Candidate Boundary",
                "",
                f"- Status: {_code(lactate.get('status'))}",
                f"- Candidate observations: {lactate.get('candidate_count', 0)}",
                "- Stable public promotion: No",
                "- Machine stable key: `PRODUCT_DECISION_REQUIRED`",
                "- Audit: `audit/lactate_threshold_candidates.json`",
                "- Units and source timezone remain unconfirmed; do not convert or infer them.",
                "",
            ]
        )
        if "candidate_status" in lactate:
            lines[-1:-1] = [
                f"- Candidate status: {_code(lactate['candidate_status'])}",
                f"- Distinct candidate count: {lactate.get('distinct_candidate_count', lactate.get('candidate_count', 0))}",
                f"- Exact repeats: {lactate.get('exact_repeat_count', 0)}",
                f"- Authority-unresolved groups: {lactate.get('authority_unresolved_count', 0)}",
            ]
    lines.extend(
        [
            "## Relationship Safety",
            "",
            "The generated relationship contract declares only reviewed v1.1 joins.",
            "`activity_fit_links` is the sole Activity/FIT join authority. Do not create",
            "a timestamp-only join or infer a relationship from similar fields.",
            "",
        ]
    )
    lines.extend(_v1_3_relationship_lines())
    lines.extend(
        [
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
    variant_rule_lines = (
        [
            "16. Multiple observed Endurance or UDS values for one stable key are",
            "    preserved in the corresponding audit evidence. Do not choose a winner",
            "    without source-backed authority; use single-variant days for ordinary",
            "    single-value analysis and review multi-variant days separately.",
        ]
        if _has_observed_variant_evidence(summary)
        else []
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
        "- `analysis/performance_metrics_daily.csv`",
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
        "4. Use only `explicit` relationships for direct joins. A documented",
        "   `context_only` alignment permits comparison, never a fact-table merge.",
        "5. Use `activity_fit_links` for Activity/FIT joins; timestamp-only joins are prohibited.",
        "6. Treat Personal Records with `activity_relationship_status=independent`",
        "   as non-activity records and do not force an activity identity.",
        "7. Preserve and disclose warnings or partial FIT status.",
        "8. Ask for an additional approved file when the supplied artifacts cannot",
        "   answer the question; do not invent source fields or context.",
        "9. Treat Hill and Endurance as canonical daily performance context. Their",
        "   CSV is a derived projection; their Activity relationship remains undefined.",
        "10. Lactate Threshold is candidate/audit-only. Do not treat candidates as a",
        "    stable dataset, convert unconfirmed units, or apply latest-wins.",
        "11. Sleep, UDS, and HRV may be compared as same-day condition context, but",
        "    they remain separate datasets and must not become Activity fact fields.",
        "12. Race Prediction, Acute Training Load, Training Readiness, VO2Max, and",
        "    Training History retain every canonical source observation. Their daily",
        "    summaries are derived projections with no selected row.",
        "13. VO2Max source series are retained explicitly. Do not overwrite one series",
        "    with another or infer equivalence across device generations.",
        "14. HRV is `analysis_reference_only`, not a daily source of truth. A null HRV",
        "    value with a review status must remain unresolved.",
        "15. Approximate generation ranges (2015-2021 and 2022+) are descriptive",
        "    source context only; they do not authorize automatic field equivalence.",
        *variant_rule_lines,
        "",
        *_v1_3_relationship_lines(),
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
    if isinstance(summary.get("snapshot_lifecycle"), Mapping):
        lines.extend(_snapshot_lifecycle_lines(summary))
        lines.extend(
            [
                "Snapshot FIT sessions and laps were regenerated from the cumulative",
                "unique FIT blob set; Activity/FIT links were regenerated afterward.",
                "",
            ]
        )
    return "\n".join(lines)


def _field_descriptor(dataset: str, field: str) -> dict[str, Any]:
    boolean_fields = {
        "memo_present", "current", "confirmed", "ambiguous",
        "sleep_stage_available_flag", "sleep_score_available_flag",
        "sleep_source_available_for_analysis_flag", "raw_has_body_battery",
        "raw_has_all_day_stress", "raw_has_body_battery_feedback",
        "training_readiness_valid_sleep",
    }
    integer_fields = {
        "session_ordinal", "lap_ordinal_within_session", "lap_index",
        "record_count", "lap_count", "source_record_index", "match_score",
        "strength_score", "endurance_score", "classification_id",
        "feedback_phrase_id",
        "record_count_for_date", "source_file_count_for_date",
        "source_activity_id",
    }
    numeric_fields = {
        "distance_m", "duration_sec", "avg_hr", "max_hr", "avg_power",
        "max_power", "avg_run_cadence", "activity_training_load",
        "maximum_meters", "value", "elapsed_time_sec", "timer_time_sec",
        "avg_heart_rate", "max_heart_rate", "avg_cadence", "max_cadence",
        "total_ascent", "total_descent", "total_elapsed_time",
        "total_timer_time", "total_distance", "avg_speed", "max_speed",
        "time_delta_seconds", "distance_delta_m", "duration_delta_seconds",
        "start_time_gmt_ms", "duration_ms", "elapsed_duration_ms",
        "moving_duration_ms", "distance_raw_centimeters",
        "race_time_5k_sec", "race_time_10k_sec", "race_time_half_sec",
        "race_time_marathon_sec", "sleep_window_minutes_including_awake",
        "sleep_duration_minutes_ex_awake", "sleep_stage_deep_minutes",
        "sleep_stage_light_minutes", "sleep_stage_rem_minutes", "sleep_score",
        "sleep_awake_minutes", "steps", "distance_meters", "active_calories",
        "bmr_calories", "resting_heart_rate", "min_heart_rate", "max_heart_rate",
        "bb_charged_value", "bb_drained_value", "stress_total_averageStressLevel",
        "stress_total_maxStressLevel", "stress_total_stressDuration",
        "stress_total_restDuration", "acwr_percent", "daily_training_load_acute",
        "daily_training_load_chronic", "daily_acute_chronic_workload_ratio",
        "training_readiness_score", "training_readiness_recovery_time",
        "acwr_factor_percent", "stress_history_factor_percent", "hrv_factor_percent",
        "sleep_history_factor_percent", "training_readiness_acute_load",
        "training_readiness_hrv_weekly_average", "training_readiness_sleep_score",
        "vo2max", "max_met", "calibrated_data", "hrv_value",
    }
    array_fields = {"match_basis"}
    flexible_identifier_fields = {
        "activity_id",
        "gear_key",
        "personal_record_id",
    }
    flexible_number_string_fields = {"start_time_local_raw"}
    if dataset == "hill_score_daily" and field == "overall_score":
        logical_type = "integer"
    elif dataset == "endurance_score_daily" and field in {
        "overall_score", "classification", "feedback_phrase"
    }:
        logical_type = "number"
    elif field in boolean_fields:
        logical_type = "boolean"
    elif field in integer_fields:
        logical_type = "integer"
    elif field in numeric_fields:
        logical_type = "number"
    elif field in array_fields:
        logical_type = "array[string]"
    elif field in flexible_identifier_fields:
        logical_type = "integer|string"
    elif field in flexible_number_string_fields:
        logical_type = "number|string"
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
    elif dataset in {"hill_score_daily", "endurance_score_daily"} and field != "calendar_date":
        unit = "source_value_or_code"
    elif field in {"calendar_date", "sleep_day"}:
        unit = "ISO-8601-date"
    elif field == "observation_timestamp":
        unit = "ISO-8601-source-timestamp"
    elif field.endswith("_minutes") or "minutes_" in field:
        unit = "minute"
    elif field.startswith("race_time_") and field.endswith("_sec"):
        unit = "second"

    if dataset == "sleep_daily" and field == "sleep_duration_minutes_ex_awake":
        provenance = "derived"
    else:
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
        "public_safe"
        if dataset in {"hill_score_daily", "endurance_score_daily", "race_prediction_daily"}
        else
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
        "Observed non-null deep/light/REM stage minutes are summed when any "
        "finite stage is present. When all stages are absent, the approved "
        "direct source aliases are used only when they agree; otherwise the "
        "value remains null or the row fails closed. Missing stages are never "
        "filled with zero, awake time and window-minus-awake are never used, "
        "and available-only Sleep rows may be used as context."
        if dataset == "sleep_daily" and field == "sleep_duration_minutes_ex_awake"
        else
        "FIT-derived HRV is analysis_reference_only. Same-date differing values remain unresolved, and this dataset is not a daily source of truth."
        if dataset == "hrv_daily"
        else
        "Source-provided metric observation. Missing values are preserved and labels, units, daily canonical rows, and activity relationships are not inferred."
        if dataset in {
            "hill_score_daily", "endurance_score_daily", "race_prediction_daily",
            "sleep_daily", "uds_daily", "acute_training_load_daily",
            "training_readiness_daily", "vo2max_daily", "training_history_daily",
        }
        else
        "Source identifiers are preserved as JSON integers or strings; "
        "deterministic fallback identifiers are strings. Compare values only "
        "after applying the declared explicit relationship contract."
        if field in flexible_identifier_fields
        else "Defined by the v1.1 runtime schema; do not infer missing values."
    )
    observation_stable_keys = {
        "race_prediction_daily": {"calendar_date", "observation_timestamp"},
        "acute_training_load_daily": {"calendar_date", "observation_timestamp"},
        "training_readiness_daily": {"calendar_date", "observation_timestamp"},
        "vo2max_daily": {
            "calendar_date", "vo2max_source_series", "sport", "observation_timestamp",
        },
        "training_history_daily": {"calendar_date", "observation_timestamp"},
    }
    return {
        "logical_type": logical_type,
        "required": field not in DATASET_OPTIONAL_FIELDS.get(dataset, frozenset()),
        "nullable": field not in DATASET_NONNULL_FIELDS[dataset],
        "unit_or_domain": unit,
        "semantic_role": "stable_key"
        if field.endswith("_key")
        or field in {"personal_record_id"}
        or field in observation_stable_keys.get(dataset, set())
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
    runtime_by_name = {item["name"]: item for item in _runtime_datasets()}
    return {
        "format": "garmin-running-data-normalizer-schema-catalog-v1",
        "run_all_version": RUN_ALL_VERSION,
        "datasets": [
            {
                "dataset": dataset,
                "record_grain": runtime_by_name[dataset]["record_grain"],
                "stable_key": list(runtime_by_name[dataset]["stable_key"]),
                **DATASET_RELATIONSHIP_METADATA[dataset],
                "fields": [
                    {"field": field, **_field_descriptor(dataset, field)}
                    for field in fields
                ],
            }
            for dataset, fields in DATASET_FIELDS.items()
        ],
    }


def _logical_type_matches(value: Any, logical_type: str) -> bool:
    if logical_type == "string":
        return isinstance(value, str)
    if logical_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if logical_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if logical_type == "boolean":
        return isinstance(value, bool)
    if logical_type == "array[string]":
        return isinstance(value, list) and all(
            isinstance(item, str) for item in value
        )
    if logical_type == "integer|string":
        return (
            isinstance(value, int) and not isinstance(value, bool)
        ) or isinstance(value, str)
    if logical_type == "number|string":
        return (
            isinstance(value, (int, float)) and not isinstance(value, bool)
        ) or isinstance(value, str)
    return False


SUPPORTED_LOGICAL_TYPES = frozenset(
    {
        "string",
        "integer",
        "number",
        "boolean",
        "array[string]",
        "integer|string",
        "number|string",
    }
)


def validate_schema_contract(
    records: Mapping[str, Any],
    schema_catalog: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate every normalized dataset field without exposing record values."""
    if schema_catalog.get("format") != (
        "garmin-running-data-normalizer-schema-catalog-v1"
    ):
        raise SchemaContractError("schema catalog format is not supported")
    raw_datasets = schema_catalog.get("datasets")
    if not isinstance(raw_datasets, list):
        raise SchemaContractError("schema catalog datasets must be a list")
    catalog_by_name: dict[str, Mapping[str, Any]] = {}
    for index, raw_dataset in enumerate(raw_datasets):
        if not isinstance(raw_dataset, Mapping):
            raise SchemaContractError(
                f"schema catalog dataset {index} must be an object"
            )
        name = raw_dataset.get("dataset")
        if not isinstance(name, str) or not name or name in catalog_by_name:
            raise SchemaContractError(
                "schema catalog dataset names must be non-empty and unique"
            )
        catalog_by_name[name] = raw_dataset
    expected_datasets = set(DATASET_FIELDS)
    if set(catalog_by_name) != expected_datasets:
        raise SchemaContractError(
            "schema catalog datasets do not match normalized datasets"
        )
    if set(records) != expected_datasets:
        raise SchemaContractError(
            "normalized record datasets do not match schema catalog"
        )

    dataset_results: list[dict[str, Any]] = []
    total_records = 0
    total_fields = 0
    runtime_by_name = {item["name"]: item for item in _runtime_datasets()}
    for dataset in DATASET_FIELDS:
        raw_dataset = catalog_by_name[dataset]
        runtime = runtime_by_name[dataset]
        if raw_dataset.get("record_grain") != runtime["record_grain"]:
            raise SchemaContractError(
                f"{dataset}: schema record grain does not match runtime"
            )
        if raw_dataset.get("stable_key") != list(runtime["stable_key"]):
            raise SchemaContractError(
                f"{dataset}: schema stable key does not match runtime"
            )
        for field, expected in DATASET_RELATIONSHIP_METADATA[dataset].items():
            if raw_dataset.get(field) != expected:
                raise SchemaContractError(
                    f"{dataset}: schema relationship metadata is inconsistent"
                )
        raw_fields = raw_dataset.get("fields")
        if not isinstance(raw_fields, list):
            raise SchemaContractError(f"{dataset}: schema fields must be a list")
        descriptors: dict[str, Mapping[str, Any]] = {}
        for index, raw_descriptor in enumerate(raw_fields):
            if not isinstance(raw_descriptor, Mapping):
                raise SchemaContractError(
                    f"{dataset}: schema field {index} must be an object"
                )
            field = raw_descriptor.get("field")
            if (
                not isinstance(field, str)
                or not field
                or field in descriptors
            ):
                raise SchemaContractError(
                    f"{dataset}: schema field names must be non-empty and unique"
                )
            if not isinstance(raw_descriptor.get("required"), bool):
                raise SchemaContractError(
                    f"{dataset}.{field}: required must be boolean"
                )
            if not isinstance(raw_descriptor.get("nullable"), bool):
                raise SchemaContractError(
                    f"{dataset}.{field}: nullable must be boolean"
                )
            logical_type = raw_descriptor.get("logical_type")
            if logical_type not in SUPPORTED_LOGICAL_TYPES:
                raise SchemaContractError(
                    f"{dataset}.{field}: logical type is unsupported"
                )
            descriptors[field] = raw_descriptor
        if set(descriptors) != set(DATASET_FIELDS[dataset]):
            raise SchemaContractError(
                f"{dataset}: schema fields do not match runtime fields"
            )

        rows = records[dataset]
        if not isinstance(rows, list):
            raise SchemaContractError(
                f"{dataset}: normalized dataset must be an array"
            )
        for row_index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise SchemaContractError(
                    f"{dataset}[{row_index}]: record must be an object"
                )
            extra_fields = set(row) - set(descriptors)
            if extra_fields:
                raise SchemaContractError(
                    f"{dataset}[{row_index}]: record contains undeclared fields"
                )
            for field, descriptor in descriptors.items():
                if field not in row:
                    if descriptor["required"]:
                        raise SchemaContractError(
                            f"{dataset}[{row_index}].{field}: required field is missing"
                        )
                    continue
                value = row[field]
                if value is None:
                    if not descriptor["nullable"]:
                        raise SchemaContractError(
                            f"{dataset}[{row_index}].{field}: null is not allowed"
                        )
                    continue
                if not _logical_type_matches(value, descriptor["logical_type"]):
                    raise SchemaContractError(
                        f"{dataset}[{row_index}].{field}: value type does not match logical type"
                    )
        total_records += len(rows)
        total_fields += len(descriptors)
        dataset_results.append(
            {
                "dataset": dataset,
                "record_count": len(rows),
                "field_count": len(descriptors),
                "status": "PASS",
            }
        )
    return {
        "status": "PASS",
        "dataset_count": len(dataset_results),
        "field_count": total_fields,
        "record_count": total_records,
        "datasets": dataset_results,
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
    candidate_features_raw = summary.get("candidate_features", {})
    candidate_features = (
        dict(candidate_features_raw)
        if isinstance(candidate_features_raw, Mapping)
        else {}
    )
    lactate_threshold = candidate_features.get("lactate_threshold")
    if isinstance(lactate_threshold, Mapping):
        candidate_features["lactate_threshold"] = {
            **lactate_threshold,
            **LACTATE_THRESHOLD_RELATIONSHIP_METADATA,
        }
    context = {
        "format": "garmin-running-data-normalizer-analysis-context-v1",
        "product_version": manifest["product_version"],
        "run_all_version": RUN_ALL_VERSION,
        "run_status": summary["status"],
        "analysis_entry_point": "analysis/activities.csv",
        "additional_analysis_entry_points": [
            {
                "path": "analysis/performance_metrics_daily.csv",
                "role": "standalone daily Hill and Endurance context",
                "activity_relationship": "not_yet_defined",
            }
        ],
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
                **DATASET_RELATIONSHIP_METADATA[runtime["name"]],
            }
            for runtime in _runtime_datasets()
        ],
        "relationships": list(RELATIONSHIP_CONTRACTS),
        "relationship_coverage": _relationship_coverage(relationship_summary),
        "prohibited_operations": [
            "timestamp_only_join",
            "join_not_declared_explicit",
            "context_only_as_fact_join",
            "missing_value_inference",
            "identity_or_location_inference",
            "automatic_external_upload",
            "medical_or_coaching_interpretation",
        ],
        "warnings": summary.get("warnings", []),
        "candidate_features": candidate_features,
    }
    if isinstance(summary.get("snapshot_lifecycle"), Mapping):
        context["snapshot_lifecycle"] = {
            "enabled": True,
            "snapshot_count": summary["snapshot_lifecycle"].get("snapshot_count"),
            "snapshot_labels": summary["snapshot_lifecycle"].get(
                "snapshot_labels", []
            ),
            "snapshot_observed_range": summary["snapshot_lifecycle"].get(
                "snapshot_observed_range", {}
            ),
            "policy": "missing_is_not_delete",
            "policy_registry_version": summary["snapshot_lifecycle"].get(
                "policy_registry_version"
            ),
            "parser_version": summary["snapshot_lifecycle"].get("parser_version"),
            "schema_version": summary["snapshot_lifecycle"].get("schema_version"),
            "datasets": summary["snapshot_lifecycle"].get("datasets", {}),
            "field_state_counts": summary["snapshot_lifecycle"].get(
                "field_state_counts", {}
            ),
            "review_hold_count": summary["snapshot_lifecycle"].get(
                "review_hold_count", 0
            ),
            "review_hold_type_counts": summary["snapshot_lifecycle"].get(
                "review_hold_type_counts", {}
            ),
            "explicit_null_review_count": summary["snapshot_lifecycle"].get(
                "explicit_null_review_count", 0
            ),
            "explicit_empty_review_count": summary["snapshot_lifecycle"].get(
                "explicit_empty_review_count", 0
            ),
            "stop_conflict_count": summary["snapshot_lifecycle"].get(
                "stop_conflict_count", 0
            ),
            "coverage_gap_count": summary["snapshot_lifecycle"].get(
                "coverage_gap_count", 0
            ),
            "unknown_or_unsupported_object_count": summary[
                "snapshot_lifecycle"
            ].get("unknown_or_unsupported_object_count", 0),
            "unknown_or_unsupported_families": summary[
                "snapshot_lifecycle"
            ].get("unknown_or_unsupported_families", []),
            "canonical_completeness_boundary": summary[
                "snapshot_lifecycle"
            ].get("canonical_completeness_boundary"),
            "automatic_deletion": False,
            "inference_performed": False,
            "evidence_paths": list(SNAPSHOT_LIFECYCLE_PATHS),
        }
    return context


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
    "SchemaContractError",
    "build_analysis_context",
    "build_artifact_inventory",
    "build_schema_catalog",
    "render_dataset_inventory",
    "render_analysis_handoff",
    "render_output_experience_artifacts",
    "render_output_experience_documents",
    "render_start_here",
    "validate_registry_alignment",
    "validate_schema_contract",
]
