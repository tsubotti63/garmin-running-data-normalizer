"""Closed v1 diagnostic vocabularies and deterministic projection helpers."""

from __future__ import annotations

from typing import Any


COMPLETENESS_FORMAT = "garmin-running-data-normalizer-source-completeness-v1"
COMPLETENESS_SCHEMA_VERSION = "garmin-source-completeness:v1"
RUN_QUALITY_FORMAT = "garmin-running-data-normalizer-run-quality-v1"
RUN_QUALITY_SCHEMA_VERSION = "garmin-run-quality:v1"
DOCTOR_FORMAT = "garmin-running-data-normalizer-doctor-v1"
DOCTOR_SCHEMA_VERSION = "garmin-export-evidence-doctor:v1"

COMPLETENESS_STATES = frozenset(
    {"PRESENT", "EMPTY", "ABSENT", "UNREADABLE", "UNSUPPORTED", "AMBIGUOUS"}
)
CONTENT_VALIDITIES = frozenset(
    {"VALID", "MALFORMED", "NOT_APPLICABLE", "UNKNOWN"}
)
STATE_VALIDITY = {
    "PRESENT": frozenset({"VALID", "MALFORMED"}),
    "EMPTY": frozenset({"VALID"}),
    "ABSENT": frozenset({"NOT_APPLICABLE"}),
    "UNREADABLE": frozenset({"UNKNOWN"}),
    "UNSUPPORTED": frozenset({"NOT_APPLICABLE"}),
    "AMBIGUOUS": frozenset({"UNKNOWN"}),
}

SOURCE_FAMILY_ORDER = (
    "activities",
    "gear",
    "personal_records",
    "fit",
    "hill_score",
    "endurance_score",
    "race_prediction",
    "sleep",
    "uds",
    "acute_training_load",
    "training_readiness",
    "vo2max",
    "training_history",
)

FAMILY_DATASETS = {
    "activities": ("activities",),
    "gear": ("gear", "activity_gear"),
    "personal_records": ("personal_records",),
    "fit": ("fit_sessions", "fit_laps", "activity_fit_links", "hrv_daily"),
    "hill_score": ("hill_score_daily",),
    "endurance_score": ("endurance_score_daily",),
    "race_prediction": ("race_prediction_daily",),
    "sleep": ("sleep_daily",),
    "uds": ("uds_daily",),
    "acute_training_load": ("acute_training_load_daily",),
    "training_readiness": ("training_readiness_daily",),
    "vo2max": ("vo2max_daily",),
    "training_history": ("training_history_daily",),
}

RELATIONSHIP_ORDER = (
    "activity_gear_to_activities",
    "activity_gear_to_gear",
    "personal_records_to_activities",
    "fit_laps_to_fit_sessions",
    "activity_fit_links_to_activities",
    "activity_fit_links_to_fit_sessions",
)

DATASET_ORDER = (
    "activities",
    "gear",
    "activity_gear",
    "personal_records",
    "fit_sessions",
    "fit_laps",
    "activity_fit_links",
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

STATUS_EXIT_CODE = {
    "PASS": 0,
    "PASS_WITH_WARNINGS": 0,
    "PARTIAL_SUCCESS": 3,
}

RESULT_INTERPRETATION = {
    "PASS": {
        "completion_state": "COMPLETED",
        "usability_scope": "FULL_WITHIN_DECLARED_CONTRACT",
        "boundary_class": "NO_KNOWN_BOUNDARY",
        "actionability": "NONE",
        "severity": "INFO",
        "known_boundary": False,
        "result_class": "COMPLETED_FULL",
        "support_bundle_suggested": False,
    },
    "PASS_WITH_WARNINGS": {
        "completion_state": "COMPLETED",
        "usability_scope": "USABLE_WITH_DISCLOSED_WARNINGS",
        "boundary_class": "KNOWN_NON_FATAL_BOUNDARY",
        "actionability": "REVIEW_RECOMMENDED",
        "severity": "WARNING",
        "known_boundary": True,
        "result_class": "COMPLETED_WITH_WARNINGS",
        "support_bundle_suggested": True,
    },
    "PARTIAL_SUCCESS": {
        "completion_state": "COMPLETED",
        "usability_scope": "BOUNDED_WITH_DISCLOSED_EXCLUSIONS",
        "boundary_class": "KNOWN_NON_FATAL_BOUNDARY",
        "actionability": "REVIEW_REQUIRED",
        "severity": "WARNING",
        "known_boundary": True,
        "result_class": "COMPLETED_BOUNDED",
        "support_bundle_suggested": True,
    },
}

SAFE_WARNING_CODES = frozenset(
    {
        "OPTIONAL_FAMILY_NOT_PRESENT",
        "OPTIONAL_FAMILY_EMPTY",
        "DAILY_METRICS_REVIEW_REQUIRED",
        "FIT_PARSE_INCOMPLETE",
        "LACTATE_CANDIDATE_AUTHORITY_UNRESOLVED",
        "RELATIONSHIP_UNRESOLVED_VALID_LINK",
    }
)

RUN_QUALITY_AUTHORITY_PATHS = frozenset(
    {
        "qa/daily_metrics_summary.json",
        "qa/dataset_summary.json",
        "qa/performance_metrics_summary.json",
        "qa/relationship_summary.json",
        "audit/activity_fit_linkage.json",
        "audit/acute_training_load_daily.json",
        "audit/endurance_score_daily.json",
        "audit/fit_audit.json",
        "audit/hill_score_daily.json",
        "audit/hrv_daily.json",
        "audit/lactate_threshold_candidates.json",
        "audit/race_prediction_daily.json",
        "audit/sleep_daily.json",
        "audit/training_history_daily.json",
        "audit/training_readiness_daily.json",
        "audit/uds_daily.json",
        "audit/vo2max_daily.json",
    }
)


def interpretation_for_status(status: Any) -> dict[str, Any]:
    if status not in RESULT_INTERPRETATION:
        raise ValueError("completed Product status is not registered")
    return dict(RESULT_INTERPRETATION[str(status)])


def exit_code_for_status(status: Any) -> int:
    if status not in STATUS_EXIT_CODE:
        raise ValueError("completed Product status is not registered")
    return STATUS_EXIT_CODE[str(status)]


def validate_state_validity(state: Any, validity: Any) -> None:
    if state not in COMPLETENESS_STATES:
        raise ValueError("Source Completeness state is not registered")
    if validity not in CONTENT_VALIDITIES or validity not in STATE_VALIDITY[str(state)]:
        raise ValueError("Source Completeness state/content validity pair is invalid")
