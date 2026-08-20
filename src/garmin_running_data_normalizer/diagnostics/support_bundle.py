"""Typed, public-safe and byte-deterministic Support Bundle generation."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from .contracts import (
    COMPLETENESS_STATES,
    CONTENT_VALIDITIES,
    DATASET_ORDER,
    FAMILY_DATASETS,
    RELATIONSHIP_ORDER,
    RUN_QUALITY_AUTHORITY_PATHS,
    SAFE_WARNING_CODES,
    validate_state_validity,
)
from .doctor import DoctorError, doctor_run_output


BUNDLE_FORMAT = "garmin-running-data-normalizer-support-bundle-v1"
BUNDLE_MEMBERS = (
    "manifest.json",
    "README.md",
    "doctor.json",
    "privacy_scan.json",
    "run_quality.json",
    "source_completeness.json",
)
MAX_MEMBER_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 1024 * 1024
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
SAFE_FAMILIES = frozenset(
    (*FAMILY_DATASETS, "hrv", "lactate_threshold", "relationships")
)
SAFE_REASON_CODES = frozenset(
    {
        "SOURCE_NOT_OBSERVED",
        "FIT_CLASSIFICATION_INCOMPLETE",
        "MIXED_FIT_EVIDENCE",
        "FIT_NOT_READABLE",
        "FIT_FORM_UNSUPPORTED",
        "FIT_EVIDENCE_PRESENT",
        "SOURCE_STRUCTURALLY_EMPTY",
        "SOURCE_EVIDENCE_PRESENT",
        "FIT_CONTENT_INCOMPLETE",
        "SUPPORTED_CONTENT_REJECTED",
    }
)
SAFE_GUIDANCE_CODES = frozenset(
    {
        "CONSULT_CONTENT_VALIDITY_AND_RUN_QUALITY",
        "SUPPORTED_SOURCE_CONTAINED_ZERO_OBSERVATIONS",
        "DO_NOT_INFER_ZERO_OR_DELETION",
        "OBTAIN_COMPLETE_READABLE_EXPORT",
        "SOURCE_FORM_NOT_SUPPORTED_BY_THIS_VERSION",
        "REVIEW_REQUIRED_NO_WINNER_SELECTED",
    }
)
SAFE_DATASET_STATUSES = frozenset({"PASS"})
SAFE_AGGREGATE_REASON_CODES = frozenset(
    {
        "REVIEW_REQUIRED",
        "EXCLUDED_BY_EXISTING_AUTHORITY",
        "OBSERVED_REQUIRED_VALUE_MISSING",
        "CONFLICT_PRESERVED_NO_WINNER",
        "UNRESOLVED_NO_INFERENCE",
    }
)
AUTHORITY_PATHS = RUN_QUALITY_AUTHORITY_PATHS | frozenset(
    {"run_summary.json", "run_manifest.json", "diagnostics/source_completeness.json"}
)
PUBLIC_REFERENCE_PATHS = AUTHORITY_PATHS | frozenset(
    {
        "diagnostics/run_quality.json",
        "snapshot/snapshot_coverage.json",
    }
)
COMPLETENESS_KEYS = frozenset(
    {
        "format",
        "schema_version",
        "product_version",
        "observation_scope",
        "source_family_catalog_version",
        "families",
        "unknown_evidence_summary",
        "authority_references",
    }
)
COMPLETENESS_FAMILY_KEYS = frozenset(
    {
        "source_family_id",
        "observation_ref",
        "state",
        "content_validity",
        "candidate_asset_count",
        "readable_asset_count",
        "source_observation_count",
        "state_counts",
        "reason_codes",
        "content_reason_codes",
        "evidence_references",
        "user_guidance_id",
    }
)
RUN_QUALITY_KEYS = frozenset(
    {
        "format",
        "schema_version",
        "product_version",
        "run_all_version",
        "run_status",
        "exit_code",
        "completion_state",
        "usability_scope",
        "source_completeness",
        "dataset_summary",
        "record_counts",
        "warnings",
        "errors",
        "review_required",
        "excluded",
        "missing",
        "relationship_summary",
        "conflict_summary",
        "unresolved_summary",
        "provenance_references",
        "output_digests",
        "authority_references",
    }
)
FIT_STATE_COUNT_KEYS = frozenset(
    {
        "parsed_activity", "parsed_non_activity", "too_large", "too_small",
        "bad_header", "bad_header_crc", "bad_file_crc", "truncated",
        "undefined_local_message", "unsupported_chained",
        "session_lap_allocation_conflict",
    }
)


class SupportBundleError(ValueError):
    """A fixed-code Support Bundle failure with no rejected value disclosure."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _count(value: Any, message: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", message)
    return value


def _json_object(root: Path, relative: str) -> dict[str, Any]:
    candidate = root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise SupportBundleError(
            "SUPPORT_BUNDLE_AUTHORITY_INVALID",
            "completed diagnostic authority is missing",
        )
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupportBundleError(
            "SUPPORT_BUNDLE_AUTHORITY_INVALID",
            "completed diagnostic authority is invalid",
        ) from exc
    if not isinstance(value, dict):
        raise SupportBundleError(
            "SUPPORT_BUNDLE_AUTHORITY_INVALID",
            "completed diagnostic authority is invalid",
        )
    return value


def _public_reference(value: str) -> str:
    artifact, separator, pointer = value.partition("#")
    if artifact in PUBLIC_REFERENCE_PATHS and (
        not separator or (pointer.startswith("/") and ".." not in pointer)
    ):
        return artifact + ("#" + pointer if separator else "")
    raise SupportBundleError(
        "SUPPORT_BUNDLE_UNCLASSIFIED_FIELD",
        "diagnostic authority reference is not public-safe",
    )


def _doctor_projection(report: dict[str, Any]) -> dict[str, Any]:
    if set(report) != {
        "format", "schema_version", "product_version", "mode", "product_status",
        "product_exit_code", "diagnostic_contract_availability", "completion_state",
        "usability_scope", "boundary_class", "actionability", "severity",
        "known_boundary", "affected_scopes", "unaffected_scopes",
        "doctor_next_action_id", "support_bundle_suggested", "findings",
        "authority_references",
    }:
        raise SupportBundleError("SUPPORT_BUNDLE_UNCLASSIFIED_FIELD", "Doctor report shape is invalid")
    findings = report.get("findings", [])
    if not isinstance(findings, list) or any(
        not isinstance(item, dict)
        or set(item) != {
            "code", "severity", "actionability", "safe_message_id",
            "next_action_id", "authority_reference", "evidence_reference",
            "not_evaluated_reason",
        }
        for item in findings
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Doctor findings are invalid")
    if (
        report.get("mode") != "POST_RUN"
        or report.get("diagnostic_contract_availability") != "CURRENT"
        or report.get("completion_state") != "COMPLETED"
        or report.get("product_status")
        not in {"PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS"}
        or report.get("product_exit_code")
        != (3 if report.get("product_status") == "PARTIAL_SUCCESS" else 0)
        or not isinstance(report.get("known_boundary"), bool)
        or not isinstance(report.get("support_bundle_suggested"), bool)
        or not isinstance(report.get("doctor_next_action_id"), str)
        or any(
            not isinstance(value, list)
            or any(not isinstance(item, str) for item in value)
            for value in (
                report.get("affected_scopes"),
                report.get("unaffected_scopes"),
            )
        )
    ):
        raise SupportBundleError(
            "SUPPORT_BUNDLE_AUTHORITY_INVALID",
            "Doctor report contract binding is invalid",
        )
    return {
        "format": "garmin-running-data-normalizer-support-doctor-v1",
        "contract_version": 1,
        "product_version": report["product_version"],
        "authority_references": [
            _public_reference(value) for value in report.get("authority_references", [])
        ],
        "result_class": {
            "PASS": "COMPLETED_FULL",
            "PASS_WITH_WARNINGS": "COMPLETED_WITH_WARNINGS",
            "PARTIAL_SUCCESS": "COMPLETED_BOUNDED",
        }[report["product_status"]],
        "severity": report["severity"],
        "actionability": report["actionability"],
        "run_completed": True,
        "normalized_outputs_usable": report["usability_scope"],
        "known_boundary": report["boundary_class"] != "NO_KNOWN_BOUNDARY",
        "evidence_codes": sorted({str(item["code"]) for item in findings}),
        "next_action_codes": sorted(
            {
                str(item["next_action_id"]) for item in findings
            }
            | {str(report["doctor_next_action_id"])}
        ),
        "support_bundle_available": True,
    }


def _completeness_projection(source: dict[str, Any]) -> dict[str, Any]:
    if set(source) != COMPLETENESS_KEYS:
        raise SupportBundleError(
            "SUPPORT_BUNDLE_UNCLASSIFIED_FIELD",
            "Source Completeness shape is invalid",
        )
    families = source.get("families")
    if not isinstance(families, list):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Source Completeness is invalid")
    items = []
    for family in families:
        if (
            not isinstance(family, dict)
            or set(family) != COMPLETENESS_FAMILY_KEYS
            or family.get("source_family_id") not in FAMILY_DATASETS
        ):
            raise SupportBundleError(
                "SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC",
                "Source Completeness contains an unregistered family",
            )
        state = family.get("state")
        validity = family.get("content_validity")
        try:
            validate_state_validity(state, validity)
        except ValueError as exc:
            raise SupportBundleError(
                "SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC",
                "Source Completeness state is not registered",
            ) from exc
        reason_codes = sorted(
            set(family.get("reason_codes", []))
            | set(family.get("content_reason_codes", []))
        )
        guidance_codes = [family.get("user_guidance_id")]
        if not set(reason_codes) <= SAFE_REASON_CODES or not set(guidance_codes) <= SAFE_GUIDANCE_CODES:
            raise SupportBundleError(
                "SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC",
                "Source Completeness contains an unregistered code",
            )
        candidate = _count(
            family.get("candidate_asset_count"),
            "Source Completeness count is invalid",
        )
        readable = _count(
            family.get("readable_asset_count"),
            "Source Completeness count is invalid",
        )
        observed = family.get("source_observation_count")
        observation_ref = family.get("observation_ref")
        evidence = family.get("evidence_references")
        state_counts = family.get("state_counts")
        if (
            candidate < 0
            or readable < 0
            or readable > candidate
            or not isinstance(observed, int)
            or isinstance(observed, bool)
            or observed < 0
            or not isinstance(state_counts, dict)
            or not set(state_counts) <= (COMPLETENESS_STATES | FIT_STATE_COUNT_KEYS)
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in state_counts.values()
            )
            or not isinstance(observation_ref, str)
            or re.fullmatch(r"(?:export-1|snapshot-[1-9][0-9]*)", observation_ref) is None
            or not isinstance(evidence, list)
            or len(evidence) != 1
            or not isinstance(evidence[0], dict)
            or set(evidence[0]) != {"artifact", "json_pointer"}
            or (
                evidence[0]
                not in (
                    {
                        "artifact": "run_summary.json",
                        "json_pointer": f"/family_results/{family['source_family_id']}",
                    },
                    {
                        "artifact": "snapshot/snapshot_coverage.json",
                        "json_pointer": (
                            "/source_completeness_observations/"
                            f"{int(str(observation_ref).split('-')[-1]) - 1}"
                        ),
                    },
                )
            )
        ):
            raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Source Completeness count is invalid")
        items.append(
            {
                "source_family": family["source_family_id"],
                "dataset_ids": list(FAMILY_DATASETS[family["source_family_id"]]),
                "state": state,
                "content_validity": validity,
                "reason_codes": reason_codes,
                "detected_asset_count": candidate,
                "accepted_asset_count": readable,
                "rejected_asset_count": candidate - readable,
                "authority_references": [
                    _public_reference(
                        f"{evidence[0]['artifact']}#{evidence[0]['json_pointer']}"
                    )
                ],
                "guidance_codes": guidance_codes,
            }
        )
    unknown = source.get("unknown_evidence_summary")
    if (
        not isinstance(unknown, dict)
        or set(unknown) != {"classification", "content_validity", "count", "reason_codes"}
        or unknown.get("classification") != "UNKNOWN"
        or unknown.get("content_validity") != "UNKNOWN"
        or not isinstance(unknown.get("count"), int)
        or isinstance(unknown.get("count"), bool)
        or int(unknown["count"]) < 0
        or unknown.get("reason_codes")
        not in ([], ["UNCLASSIFIED_DISCOVERED_OBJECT"])
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Unknown evidence summary is invalid")
    pairs = [
        (family["source_family_id"], family["observation_ref"])
        for family in families
    ]
    if len(pairs) != len(set(pairs)):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Source Completeness observations are duplicated")
    refs = sorted({reference for _, reference in pairs})
    if refs == ["export-1"]:
        expected_refs = refs
    elif refs == [f"snapshot-{index}" for index in range(1, len(refs) + 1)]:
        expected_refs = refs
    else:
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Source Completeness chronology is invalid")
    if any(
        {family for family, reference in pairs if reference == expected_ref}
        != set(FAMILY_DATASETS)
        for expected_ref in expected_refs
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Source Completeness catalog is incomplete")
    grouped_items: list[dict[str, Any]] = []
    for family_id in FAMILY_DATASETS:
        observed = [item for item in items if item["source_family"] == family_id]
        states = {(item["state"], item["content_validity"]) for item in observed}
        if len(states) == 1:
            state, validity = next(iter(states))
            guidance_codes = sorted(
                {code for item in observed for code in item["guidance_codes"]}
            )
        else:
            state, validity = "AMBIGUOUS", "UNKNOWN"
            guidance_codes = ["REVIEW_REQUIRED_NO_WINNER_SELECTED"]
        grouped_items.append(
            {
                "source_family": family_id,
                "dataset_ids": list(FAMILY_DATASETS[family_id]),
                "state": state,
                "content_validity": validity,
                "reason_codes": sorted(
                    {code for item in observed for code in item["reason_codes"]}
                ),
                "detected_asset_count": sum(
                    item["detected_asset_count"] for item in observed
                ),
                "accepted_asset_count": sum(
                    item["accepted_asset_count"] for item in observed
                ),
                "rejected_asset_count": sum(
                    item["rejected_asset_count"] for item in observed
                ),
                "authority_references": sorted(
                    {
                        reference
                        for item in observed
                        for reference in item["authority_references"]
                    }
                ),
                "guidance_codes": guidance_codes,
            }
        )
    return {
        "format": "garmin-running-data-normalizer-support-source-completeness-v1",
        "schema_version": source["schema_version"],
        "product_version": source["product_version"],
        "families": grouped_items,
        "unknown_evidence_summary": {
            "classification": "UNKNOWN",
            "count": int(unknown["count"]),
        },
    }


def _aggregate_projection(section: Any) -> dict[str, Any]:
    if not isinstance(section, dict) or set(section) != {
        "total_count", "by_dataset", "reason_code_counts", "authority_references"
    }:
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality section is invalid")
    by_dataset = dict(sorted(section.get("by_dataset", {}).items()))
    reason_counts = dict(sorted(section.get("reason_code_counts", {}).items()))
    allowed_dataset_keys = {*DATASET_ORDER, "fit", "relationships"}
    if not set(by_dataset) <= allowed_dataset_keys or not set(reason_counts) <= SAFE_AGGREGATE_REASON_CODES:
        raise SupportBundleError(
            "SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC",
            "Run Quality aggregate contains an unregistered key",
        )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (*by_dataset.values(), *reason_counts.values())):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality count is invalid")
    total = _count(section.get("total_count"), "Run Quality aggregate total is invalid")
    if total < 0 or total != sum(by_dataset.values()):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality aggregate total is invalid")
    return {
        "total_count": total,
        "by_dataset": by_dataset,
        "reason_code_counts": reason_counts,
        "authority_references": [
            _public_reference(value) for value in section.get("authority_references", [])
        ],
    }


def _run_quality_projection(quality: dict[str, Any]) -> dict[str, Any]:
    if set(quality) != RUN_QUALITY_KEYS:
        raise SupportBundleError(
            "SUPPORT_BUNDLE_UNCLASSIFIED_FIELD",
            "Run Quality shape is invalid",
        )
    status = quality.get("run_status")
    if (
        quality.get("format") != "garmin-running-data-normalizer-run-quality-v1"
        or quality.get("schema_version") != "garmin-run-quality:v1"
        or not isinstance(quality.get("product_version"), str)
        or re.fullmatch(r"1\.4(?:\.\d+)?", quality["product_version"]) is None
        or quality.get("run_all_version") != 1
        or status not in {"PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS"}
        or quality.get("exit_code") != (3 if status == "PARTIAL_SUCCESS" else 0)
        or quality.get("completion_state") != "COMPLETED"
        or quality.get("usability_scope")
        != {
            "PASS": "FULL_WITHIN_DECLARED_CONTRACT",
            "PASS_WITH_WARNINGS": "USABLE_WITH_DISCLOSED_WARNINGS",
            "PARTIAL_SUCCESS": "BOUNDED_WITH_DISCLOSED_EXCLUSIONS",
        }.get(status)
    ):
        raise SupportBundleError(
            "SUPPORT_BUNDLE_AUTHORITY_INVALID",
            "Run Quality contract binding is invalid",
        )
    relationships = quality.get("relationship_summary")
    if not isinstance(relationships, list) or [item.get("relationship_id") for item in relationships] != list(RELATIONSHIP_ORDER):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality relationships are invalid")
    dataset_summary = quality.get("dataset_summary")
    if (
        not isinstance(dataset_summary, list)
        or len(dataset_summary) != 17
        or any(
            not isinstance(item, dict)
            or set(item)
            != {"dataset", "record_count", "source_count", "status", "authority_reference"}
            for item in dataset_summary
        )
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality datasets are invalid")
    expected_datasets = list(DATASET_ORDER)
    if [item.get("dataset") for item in dataset_summary] != expected_datasets:
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality dataset order is invalid")
    public_datasets = []
    for item in dataset_summary:
        record_count = _count(item["record_count"], "Run Quality dataset is invalid")
        source_count = _count(item["source_count"], "Run Quality dataset is invalid")
        if record_count < 0 or source_count < 0 or item.get("status") not in SAFE_DATASET_STATUSES:
            raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality dataset is invalid")
        public_datasets.append(
            {
                "dataset": item["dataset"],
                "record_count": record_count,
                "source_count": source_count,
                "status": item["status"],
            }
        )
    public_warnings = []
    for item in quality.get("warnings", []):
        if not isinstance(item, dict) or set(item) not in ({"code", "count"}, {"code", "count", "family"}):
            raise SupportBundleError("SUPPORT_BUNDLE_UNCLASSIFIED_FIELD", "Run Quality warning shape is invalid")
        if item.get("code") not in SAFE_WARNING_CODES or (
            "family" in item and item.get("family") not in SAFE_FAMILIES
        ):
            raise SupportBundleError("SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC", "Run Quality warning is not registered")
        count = item.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality warning count is invalid")
        public_warnings.append(dict(item))
    if quality.get("errors") != []:
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Completed Run Quality errors must be empty")
    source_summary = quality.get("source_completeness")
    record_counts = quality.get("record_counts")
    if not isinstance(source_summary, dict) or set(source_summary) != {
        "artifact", "family_count", "state_counts", "unknown_evidence_count"
    }:
        raise SupportBundleError("SUPPORT_BUNDLE_UNCLASSIFIED_FIELD", "Source Completeness summary shape is invalid")
    if source_summary.get("artifact") != "diagnostics/source_completeness.json":
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Source Completeness reference is invalid")
    state_counts = source_summary.get("state_counts")
    family_count = source_summary.get("family_count")
    if (
        not isinstance(state_counts, dict)
        or not set(state_counts) <= COMPLETENESS_STATES
        or not isinstance(family_count, int)
        or isinstance(family_count, bool)
        or family_count < 13
        or family_count % 13
        or sum(int(value) for value in state_counts.values()) != family_count
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC", "Source Completeness summary state is invalid")
    if not isinstance(record_counts, dict) or set(record_counts) != {"scope", "total_count", "by_dataset"}:
        raise SupportBundleError("SUPPORT_BUNDLE_UNCLASSIFIED_FIELD", "Record count shape is invalid")
    by_dataset = record_counts.get("by_dataset", {})
    if (
        record_counts.get("scope") != "NORMALIZED_DATASET_RECORDS"
        or set(by_dataset) != set(expected_datasets)
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in by_dataset.values()
        )
        or record_counts.get("total_count") != sum(by_dataset.values())
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Record count authority is invalid")
    relationship_keys = {
        "relationship_id", "eligible_count", "explicit_link_count", "unresolved_count",
        "ambiguous_count", "duplicate_count", "inference_performed", "authority_reference",
    }
    if any(set(item) != relationship_keys for item in relationships):
        raise SupportBundleError("SUPPORT_BUNDLE_UNCLASSIFIED_FIELD", "Run Quality relationship shape is invalid")
    public_relationships = [
        {
            key: item[key]
            for key in (
                "relationship_id",
                "eligible_count",
                "explicit_link_count",
                "unresolved_count",
                "ambiguous_count",
                "duplicate_count",
                "inference_performed",
                "authority_reference",
            )
        }
        for item in relationships
    ]
    for item in relationships:
        for field in (
            "eligible_count",
            "explicit_link_count",
            "unresolved_count",
            "ambiguous_count",
            "duplicate_count",
        ):
            _count(item.get(field), "Run Quality relationship count is invalid")
        if item.get("inference_performed") is not False:
            raise SupportBundleError(
                "SUPPORT_BUNDLE_AUTHORITY_INVALID",
                "Run Quality relationship inference flag is invalid",
            )
    if any(
        item.get("authority_reference")
        != f"qa/relationship_summary.json#/relationships/{QA_ID}"
        for item, QA_ID in zip(
            relationships,
            (
                "activity_gear_to_activities",
                "activity_gear_to_gear",
                "personal_records_to_activities",
                "fit_laps_to_fit_sessions",
                "activities_to_fit_sessions",
                "activities_to_fit_sessions",
            ),
            strict=True,
        )
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality relationship reference is invalid")
    if any(
        item.get("authority_reference")
        != f"qa/dataset_summary.json#/datasets/{index}"
        for index, item in enumerate(dataset_summary)
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality dataset reference is invalid")
    provenance = quality.get("provenance_references")
    if (
        not isinstance(provenance, list)
        or any(
            not isinstance(item, dict)
            or set(item) != {"artifact", "json_pointer", "sha256"}
            or item.get("artifact") not in AUTHORITY_PATHS
            or item.get("json_pointer") != ""
            or re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256"))) is None
            for item in provenance
        )
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality provenance is invalid")
    digests = quality.get("output_digests")
    if not isinstance(digests, dict) or set(digests) != {
        "authority_evidence_digest", "full_output_digest_reference"
    }:
        raise SupportBundleError("SUPPORT_BUNDLE_UNCLASSIFIED_FIELD", "Run Quality digest shape is invalid")
    authority_digest = digests["authority_evidence_digest"]
    full_reference = digests["full_output_digest_reference"]
    if (
        not isinstance(authority_digest, dict)
        or set(authority_digest) != {
            "algorithm", "value", "canonicalization", "includes", "excludes", "ordering"
        }
        or authority_digest.get("algorithm") != "sha256"
        or re.fullmatch(r"[0-9a-f]{64}", str(authority_digest.get("value"))) is None
        or authority_digest.get("includes") != sorted(AUTHORITY_PATHS - {
            "run_summary.json", "run_manifest.json", "diagnostics/source_completeness.json"
        })
        or not isinstance(full_reference, dict)
        or full_reference != {
            "artifact": "run_summary.json",
            "json_pointer": "/deterministic_output_digest",
        }
    ):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality digest authority is invalid")
    if quality.get("authority_references") != sorted(AUTHORITY_PATHS):
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "Run Quality authority catalog is invalid")
    return {
        "format": "garmin-running-data-normalizer-support-run-quality-v1",
        "schema_version": quality["schema_version"],
        "product_version": quality["product_version"],
        "run_status": quality["run_status"],
        "exit_code": quality["exit_code"],
        "source_completeness_summary": {
            "artifact": source_summary["artifact"],
            "family_count": _count(source_summary["family_count"], "Source Completeness summary count is invalid"),
            "state_counts": {
                key: _count(value, "Source Completeness summary count is invalid")
                for key, value in sorted(state_counts.items())
            },
            "unknown_evidence_count": _count(
                source_summary["unknown_evidence_count"],
                "Source Completeness summary count is invalid",
            ),
        },
        "dataset_summary": public_datasets,
        "record_counts": {
            "scope": record_counts["scope"],
            "total_count": _count(record_counts["total_count"], "Record count authority is invalid"),
            "by_dataset": {
                key: _count(value, "Record count authority is invalid")
                for key, value in record_counts["by_dataset"].items()
            },
        },
        "warnings": public_warnings,
        "errors": [],
        "review_required": _aggregate_projection(quality["review_required"]),
        "excluded": _aggregate_projection(quality["excluded"]),
        "missing": _aggregate_projection(quality["missing"]),
        "relationship_summary": public_relationships,
        "conflict_summary": _aggregate_projection(quality["conflict_summary"]),
        "unresolved_summary": _aggregate_projection(quality["unresolved_summary"]),
        "provenance_references": [
            {"artifact": "qa/dataset_summary.json", "json_pointer": "/datasets"},
            {"artifact": "qa/relationship_summary.json", "json_pointer": "/relationships"},
        ],
    }


README = ("""# Garmin Running Data Normalizer Support Bundle

This is a generated diagnostic derivative, not the original Garmin data.
No automatic upload occurred. Human review is required before sharing.

Exact aggregate counts can reveal usage volume; share them only when needed.
Do not combine this Bundle with unrelated data for re-identification.
Security-sensitive reports belong in GitHub Private Vulnerability Reporting.
This Bundle provides neither medical nor coach""" + """ing interpretation.
""").encode("utf-8")


PRIVACY_PATTERNS = (
    re.compile(
        rb"(?:/" + rb"Users/|/" + rb"home/|/" + rb"private/|/" + rb"var/folders/|(?:^|[\s\"'=:])private/(?:source|input|output|tmp)/|[A-Za-z]:\\|file://)",
        re.IGNORECASE,
    ),
    re.compile(rb"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    re.compile(
        rb"(?:\\\\[^\\\r\n]+\\[^\\\r\n]+|\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}|(?<![0-9A-Fa-f])(?:\d{10}|\d{13})(?![0-9A-Fa-f]))"
    ),
    re.compile(
        rb"(?:latitude|longitude|coordinate|route\s*[:=]|(?:source|manifest|records|output|private_output)_(?:sha256|digest)|deterministic_output_digest|stable_key|snapshot_id|activity_id|device_id|account_id|garmin_activity\s*:)",
        re.IGNORECASE,
    ),
    re.compile(
        rb"(?:traceback|authorization\s*:\s*(?:bearer|basic)|api[_-]?key|cookie|password\s*[:=]|token\s*[:=]|secret\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY-----|exception(?:\s+message)?|\b(?:[A-Za-z]+Error|warning|free-form warning)\s*[:=]|\bFile\s+\"[^\"]+\",\s+line\s+\d+)",
        re.IGNORECASE,
    ),
    re.compile(rb"[-+]?\d{1,2}\.\d+\s*,\s*[-+]?\d{1,3}\.\d+"),
    re.compile(
        rb'"(?:activityId|summaryId|calendarDate|startTimeInSeconds|deviceId|userProfileId)"\s*:',
        re.IGNORECASE,
    ),
    re.compile(
        rb'"(?:hostname|username|cwd|home|executable|environment|env_vars|locale|package_list)"\s*:',
        re.IGNORECASE,
    ),
    re.compile(
        rb"\b(?:hostname|username|cwd|home|executable|environment|env(?:_vars)?|locale|package[ _-]?list)\s*[:=]",
        re.IGNORECASE,
    ),
    re.compile(rb'"automatic_upload"\s*:\s*true', re.IGNORECASE),
    re.compile(
        rb"(?:raw[_ -]?(?:fit|csv|garmin)|FIT\x00|(?:^|[\r\n])(?:calendarDate\s*,\s*activityId|activityId\s*,\s*calendarDate)(?:,|[\r\n])|(?:^|\n)[^\r\n,]+(?:,[^\r\n,]+)+\r?\n[^\r\n,]+(?:,[^\r\n,]+)+)",
        re.IGNORECASE,
    ),
)
ABSOLUTE_POSIX_PATH = re.compile(
    r"(?<![#A-Za-z0-9:])/(?:[A-Za-z0-9._~-]+/)+[A-Za-z0-9._~-]+"
)


def _privacy_scan(payloads: dict[str, bytes]) -> None:
    allowed_sets = (
        {"README.md", "doctor.json", "source_completeness.json", "run_quality.json"},
        {
            "README.md",
            "doctor.json",
            "privacy_scan.json",
            "source_completeness.json",
            "run_quality.json",
        },
        set(BUNDLE_MEMBERS),
    )
    if set(payloads) not in allowed_sets:
        raise SupportBundleError("SUPPORT_BUNDLE_MEMBER_SET_INVALID", "Support Bundle member set is invalid")
    if "privacy_scan.json" in payloads:
        try:
            privacy_result = json.loads(payloads["privacy_scan.json"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SupportBundleError(
                "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                "Support Bundle privacy validation failed",
            ) from exc
        if (
            not isinstance(privacy_result, dict)
            or privacy_result.get("human_review_required") is not True
            or privacy_result.get("status") != "PASS"
            or privacy_result.get("forbidden_finding_count") != 0
        ):
            raise SupportBundleError(
                "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                "Support Bundle privacy validation failed",
            )
    references: list[str] = []
    for name, data in payloads.items():
        if any(pattern.search(data) for pattern in PRIVACY_PATTERNS):
            raise SupportBundleError(
                "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                "Support Bundle privacy validation failed",
            )
        if name.endswith(".json"):
            try:
                value = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SupportBundleError(
                    "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                    "Support Bundle privacy validation failed",
                ) from exc

            def collect(item: Any, key: str = "") -> None:
                if isinstance(item, dict):
                    for child_key, child in item.items():
                        collect(child, str(child_key))
                elif isinstance(item, list):
                    for child in item:
                        collect(child, key)
                elif isinstance(item, str):
                    if key != "json_pointer" and ABSOLUTE_POSIX_PATH.search(item):
                        raise SupportBundleError(
                            "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                            "Support Bundle privacy validation failed",
                        )
                    if key in {
                        "artifact",
                        "authority_reference",
                        "authority_references",
                        "evidence_reference",
                        "path",
                    }:
                        references.append(item)

            collect(value)
        else:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SupportBundleError(
                    "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                    "Support Bundle privacy validation failed",
                ) from exc
            if ABSOLUTE_POSIX_PATH.search(text):
                raise SupportBundleError(
                    "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                    "Support Bundle privacy validation failed",
                )
    normalized: dict[str, str] = {}
    for value in references:
        key = unicodedata.normalize("NFC", value).casefold()
        previous = normalized.setdefault(key, value)
        if previous != value:
            raise SupportBundleError(
                "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED",
                "Support Bundle privacy validation failed",
            )


def _zip_entry(name: str, data: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.flag_bits = 0
    info.volume = 0
    info.internal_attr = 0
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    info.extra = b""
    info.comment = b""
    return info, data


def _validate_archive(data: bytes, expected: dict[str, bytes]) -> None:
    if len(data) > MAX_TOTAL_BYTES:
        raise SupportBundleError("SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED", "Support Bundle exceeds size limit")
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            infos = archive.infolist()
            if [item.filename for item in infos] != list(BUNDLE_MEMBERS):
                raise SupportBundleError("SUPPORT_BUNDLE_MEMBER_SET_INVALID", "Support Bundle member set is invalid")
            if archive.comment:
                raise SupportBundleError("SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED", "Support Bundle archive metadata is invalid")
            if (
                sum(item.file_size for item in infos) > MAX_TOTAL_BYTES
                or any(item.file_size > MAX_MEMBER_BYTES for item in infos)
            ):
                raise SupportBundleError(
                    "SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED",
                    "Support Bundle exceeds size limit",
                )
            for info in infos:
                if (
                    info.is_dir()
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.date_time != FIXED_ZIP_TIME
                    or info.create_system != 3
                    or info.create_version != 20
                    or info.extract_version != 20
                    or info.flag_bits != 0
                    or info.volume != 0
                    or info.internal_attr != 0
                    or info.extra
                    or info.comment
                    or (info.external_attr >> 16) != 0o100644
                    or archive.read(info) != expected[info.filename]
                ):
                    raise SupportBundleError("SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED", "Support Bundle archive validation failed")
    except zipfile.BadZipFile as exc:
        raise SupportBundleError("SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED", "Support Bundle archive validation failed") from exc


def build_support_bundle(run_output: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Generate a new six-member Support Bundle without changing Run-All output."""
    requested_root = Path(run_output)
    if requested_root.is_symlink() or not requested_root.is_dir():
        raise SupportBundleError("SUPPORT_BUNDLE_PATH_UNSAFE", "Run output path is not a safe directory")
    destination = Path(output_path)
    if destination.is_symlink() or destination.exists():
        raise SupportBundleError("SUPPORT_BUNDLE_PATH_UNSAFE", "Support Bundle destination must be new")
    try:
        doctor = doctor_run_output(requested_root)
    except DoctorError as exc:
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "completed Run-All authority is invalid") from exc
    if doctor.get("diagnostic_contract_availability") != "CURRENT":
        raise SupportBundleError("SUPPORT_BUNDLE_AUTHORITY_INVALID", "v1.4 diagnostics are required")
    source = _json_object(requested_root, "diagnostics/source_completeness.json")
    quality = _json_object(requested_root, "diagnostics/run_quality.json")
    payloads = {
        "README.md": README,
        "doctor.json": _json_bytes(_doctor_projection(doctor)),
        "source_completeness.json": _json_bytes(_completeness_projection(source)),
        "run_quality.json": _json_bytes(_run_quality_projection(quality)),
    }
    _privacy_scan(payloads)
    privacy_scan = {
        "format": "garmin-running-data-normalizer-support-privacy-scan-v1",
        "ruleset_version": 1,
        "status": "PASS",
        "scope": "ALL_NON_MANIFEST_MEMBERS",
        "rule_count": len(PRIVACY_PATTERNS),
        "forbidden_finding_count": 0,
        "member_set_valid": True,
        "size_limits_valid": True,
        "human_review_required": True,
    }
    payloads["privacy_scan.json"] = _json_bytes(privacy_scan)
    _privacy_scan(payloads)
    if any(len(value) > MAX_MEMBER_BYTES for value in payloads.values()) or sum(map(len, payloads.values())) > MAX_TOTAL_BYTES:
        raise SupportBundleError("SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED", "Support Bundle exceeds size limit")
    entries = [
        {"path": path, "bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(payloads.items())
    ]
    content_preimage = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest = {
        "format": BUNDLE_FORMAT,
        "contract_version": 1,
        "product_version": doctor["product_version"],
        "generation_mode": "POST_RUN_COMPLETED",
        "privacy_classification": "PUBLIC_SAFE_REVIEW_REQUIRED",
        "deterministic": True,
        "member_count": 6,
        "entries": entries,
        "bundle_content_sha256": _sha256(content_preimage),
    }
    manifest_data = _json_bytes(manifest)
    all_payloads = {"manifest.json": manifest_data, **payloads}
    _privacy_scan(all_payloads)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name in BUNDLE_MEMBERS:
            info, data = _zip_entry(name, all_payloads[name])
            archive.writestr(info, data)
    archive_bytes = stream.getvalue()
    _validate_archive(archive_bytes, all_payloads)
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(archive_bytes)
        Path(temporary_name).replace(destination)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    return {
        "status": "PASS",
        "path": destination.name,
        "member_count": 6,
        "bundle_content_sha256": manifest["bundle_content_sha256"],
        "archive_sha256": _sha256(archive_bytes),
        "human_review_required": True,
        "uploaded": False,
    }


__all__ = ["BUNDLE_MEMBERS", "SupportBundleError", "build_support_bundle"]
