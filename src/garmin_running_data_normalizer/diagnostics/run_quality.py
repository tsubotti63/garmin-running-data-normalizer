"""Deterministic Run Quality projection over existing Run-All authorities."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (
    DATASET_ORDER,
    RELATIONSHIP_ORDER,
    RUN_QUALITY_FORMAT,
    RUN_QUALITY_SCHEMA_VERSION,
    SAFE_WARNING_CODES,
    exit_code_for_status,
    interpretation_for_status,
)


QA_RELATIONSHIP_ID = {
    "activity_gear_to_activities": "activity_gear_to_activities",
    "activity_gear_to_gear": "activity_gear_to_gear",
    "personal_records_to_activities": "personal_records_to_activities",
    "fit_laps_to_fit_sessions": "fit_laps_to_fit_sessions",
    "activity_fit_links_to_activities": "activities_to_fit_sessions",
    "activity_fit_links_to_fit_sessions": "activities_to_fit_sessions",
}

RELATIONSHIP_FIELDS = {
    "activity_fit_links_to_activities": (
        "eligible_activity_count",
        "link_count",
        "unresolved_eligible_activity_count",
        "ambiguous_activity_count",
        "duplicate_mapping_count",
    ),
    "activity_fit_links_to_fit_sessions": (
        "eligible_fit_session_count",
        "link_count",
        "unresolved_eligible_fit_session_count",
        "ambiguous_fit_session_count",
        "duplicate_mapping_count",
    ),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Run Quality count must be a non-negative integer")
    return value


def _reason_counts(values: Sequence[tuple[str, int]]) -> dict[str, int]:
    return {code: count for code, count in sorted(values) if count}


def _section(
    *,
    by_dataset: Mapping[str, int],
    reason_counts: Mapping[str, int],
    authority_references: Sequence[str],
) -> dict[str, Any]:
    safe_counts = {name: _count(value) for name, value in sorted(by_dataset.items()) if value}
    safe_reasons = {name: _count(value) for name, value in sorted(reason_counts.items()) if value}
    return {
        "total_count": sum(safe_counts.values()),
        "by_dataset": safe_counts,
        "reason_code_counts": safe_reasons,
        "authority_references": sorted(set(authority_references)),
    }


def _relationship_projection(relationship_summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = relationship_summary.get("relationships")
    if not isinstance(raw, Mapping):
        raise ValueError("relationship summary is missing")
    projected: list[dict[str, Any]] = []
    for relationship_id in RELATIONSHIP_ORDER:
        qa_id = QA_RELATIONSHIP_ID[relationship_id]
        item = raw.get(qa_id)
        if not isinstance(item, Mapping) or not (
            item.get("status") == "explicit"
            or item.get("relationship_status") == "explicit"
        ):
            raise ValueError("one of the six relationship authorities is missing")
        fields = RELATIONSHIP_FIELDS.get(
            relationship_id,
            (
                "eligible_count",
                "link_count",
                "unresolved_count",
                "ambiguous_count",
                "duplicate_count",
            ),
        )
        projected.append(
            {
                "relationship_id": relationship_id,
                "eligible_count": _count(item.get(fields[0], 0)),
                "explicit_link_count": _count(item.get(fields[1], 0)),
                "unresolved_count": _count(item.get(fields[2], 0)),
                "ambiguous_count": _count(item.get(fields[3], 0)),
                "duplicate_count": _count(item.get(fields[4], 0)),
                "inference_performed": item.get("inference_performed"),
                "authority_reference": f"qa/relationship_summary.json#/relationships/{qa_id}",
            }
        )
    if len(projected) != 6 or any(
        item["inference_performed"] is not False for item in projected
    ):
        raise ValueError("relationship projection violates the frozen six-contract boundary")
    return projected


def build_run_quality(
    *,
    product_version: str,
    run_all_version: int,
    status: str,
    warnings: Sequence[Mapping[str, Any]],
    dataset_qa_entries: Sequence[Mapping[str, Any]],
    relationship_summary: Mapping[str, Any],
    performance_audit: Mapping[str, Mapping[str, Any]],
    fit_status: Mapping[str, Any],
    source_completeness: Mapping[str, Any],
    authority_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Project aggregate run evidence without rereading normalized records."""
    interpretation = interpretation_for_status(status)
    if (
        len(dataset_qa_entries) != 17
        or [entry.get("dataset") for entry in dataset_qa_entries]
        != list(DATASET_ORDER)
    ):
        raise ValueError("Run Quality requires exactly 17 datasets")
    dataset_summary: list[dict[str, Any]] = []
    for entry in dataset_qa_entries:
        dataset = entry.get("dataset")
        if (
            not isinstance(dataset, str)
            or not dataset
            or entry.get("status") != "PASS"
        ):
            raise ValueError("dataset QA entry is invalid")
        dataset_summary.append(
            {
                "dataset": dataset,
                "record_count": _count(entry.get("record_count", 0)),
                "source_count": _count(entry.get("source_count", 0)),
                "status": entry.get("status"),
                "authority_reference": f"qa/dataset_summary.json#/datasets/{len(dataset_summary)}",
            }
        )

    review_by_dataset: dict[str, int] = {}
    excluded_by_dataset: dict[str, int] = {}
    missing_by_dataset: dict[str, int] = {}
    conflict_by_dataset: dict[str, int] = {}
    unresolved_by_dataset: dict[str, int] = {}
    for dataset, audit in sorted(performance_audit.items()):
        if dataset == "lactate_threshold":
            continue
        review = _count(
            audit.get("review_required_count", 0)
            or audit.get("review_item_count", 0)
            or audit.get("review_key_count", 0)
            or 0
        )
        excluded = _count(audit.get("excluded_record_count", 0) or 0)
        missing = sum(
            _count(audit.get(key, 0) or 0)
            for key in ("missing_date_count", "missing_required_count")
        )
        conflicts = sum(
            _count(audit.get(key, 0) or 0)
            for key in ("same_day_conflict_count", "divergent_duplicate_count", "conflict_count")
        )
        unresolved = _count(audit.get("canonicalization_unresolved_count", 0) or 0)
        if review:
            review_by_dataset[dataset] = review
        if excluded:
            excluded_by_dataset[dataset] = excluded
        if missing:
            missing_by_dataset[dataset] = missing
        if conflicts:
            conflict_by_dataset[dataset] = conflicts
        if unresolved:
            unresolved_by_dataset[dataset] = unresolved
    incomplete_fit = _count(fit_status.get("incomplete_fit_count", 0) or 0)
    if incomplete_fit:
        excluded_by_dataset["fit"] = incomplete_fit

    projected_relationships = _relationship_projection(relationship_summary)
    relationship_unresolved = sum(item["unresolved_count"] for item in projected_relationships)
    warnings_projection: list[dict[str, Any]] = []
    for warning in warnings:
        code = warning.get("code")
        if code not in SAFE_WARNING_CODES:
            raise ValueError("Run Quality encountered an unregistered warning code")
        item: dict[str, Any] = {
            "code": code,
            "count": _count(warning.get("count", 1)),
        }
        family = warning.get("family")
        if isinstance(family, str) and family:
            item["family"] = family
        warnings_projection.append(item)
    warnings_projection.sort(key=lambda item: (str(item.get("code")), str(item.get("family", ""))))

    authority_entries = [
        {"path": path, "sha256": _sha256(data)}
        for path, data in sorted(authority_payloads.items())
        if path.startswith(("qa/", "audit/"))
    ]
    canonical = "\n".join(f"{item['path']}:{item['sha256']}" for item in authority_entries)
    authority_digest = _sha256(canonical.encode("utf-8"))
    authority_refs = [item["path"] for item in authority_entries]
    return {
        "format": RUN_QUALITY_FORMAT,
        "schema_version": RUN_QUALITY_SCHEMA_VERSION,
        "product_version": product_version,
        "run_all_version": run_all_version,
        "run_status": status,
        "exit_code": exit_code_for_status(status),
        "completion_state": interpretation["completion_state"],
        "usability_scope": interpretation["usability_scope"],
        "source_completeness": {
            "artifact": "diagnostics/source_completeness.json",
            "family_count": len(source_completeness.get("families", [])),
            "state_counts": _reason_counts(
                [
                    (state, sum(1 for item in source_completeness.get("families", []) if item.get("state") == state))
                    for state in ("PRESENT", "EMPTY", "ABSENT", "UNREADABLE", "UNSUPPORTED", "AMBIGUOUS")
                ]
            ),
            "unknown_evidence_count": _count(
                source_completeness.get("unknown_evidence_summary", {}).get("count", 0)
            ),
        },
        "dataset_summary": dataset_summary,
        "record_counts": {
            "scope": "NORMALIZED_DATASET_RECORDS",
            "total_count": sum(item["record_count"] for item in dataset_summary),
            "by_dataset": {item["dataset"]: item["record_count"] for item in dataset_summary},
        },
        "warnings": warnings_projection,
        "errors": [],
        "review_required": _section(
            by_dataset=review_by_dataset,
            reason_counts={"REVIEW_REQUIRED": sum(review_by_dataset.values())},
            authority_references=authority_refs,
        ),
        "excluded": _section(
            by_dataset=excluded_by_dataset,
            reason_counts={"EXCLUDED_BY_EXISTING_AUTHORITY": sum(excluded_by_dataset.values())},
            authority_references=authority_refs,
        ),
        "missing": _section(
            by_dataset=missing_by_dataset,
            reason_counts={"OBSERVED_REQUIRED_VALUE_MISSING": sum(missing_by_dataset.values())},
            authority_references=authority_refs,
        ),
        "relationship_summary": projected_relationships,
        "conflict_summary": _section(
            by_dataset=conflict_by_dataset,
            reason_counts={"CONFLICT_PRESERVED_NO_WINNER": sum(conflict_by_dataset.values())},
            authority_references=authority_refs,
        ),
        "unresolved_summary": _section(
            by_dataset={
                **unresolved_by_dataset,
                **({"relationships": relationship_unresolved} if relationship_unresolved else {}),
            },
            reason_counts={
                "UNRESOLVED_NO_INFERENCE": sum(unresolved_by_dataset.values()) + relationship_unresolved
            },
            authority_references=authority_refs,
        ),
        "provenance_references": [
            {
                "artifact": item["path"],
                "json_pointer": "",
                "sha256": item["sha256"],
            }
            for item in authority_entries
        ],
        "output_digests": {
            "authority_evidence_digest": {
                "algorithm": "sha256",
                "value": authority_digest,
                "canonicalization": "lexical path:sha256 lines joined by LF",
                "includes": [item["path"] for item in authority_entries],
                "excludes": [
                    "diagnostics/",
                    "run_manifest.json",
                    "run_summary.json",
                    "support_bundle",
                ],
                "ordering": "ASCII lexical path order",
            },
            "full_output_digest_reference": {
                "artifact": "run_summary.json",
                "json_pointer": "/deterministic_output_digest",
            },
        },
        "authority_references": sorted(
            set(
                [
                    "run_summary.json",
                    "run_manifest.json",
                    "diagnostics/source_completeness.json",
                ]
                + authority_refs
            )
        ),
    }


__all__ = ["build_run_quality"]
