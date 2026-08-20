"""Fail-closed validation of v1.4 diagnostic authorities."""

from __future__ import annotations

import json
import hashlib
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .completeness import (
    FIT_MALFORMED,
    FIT_UNREADABLE,
    FIT_UNSUPPORTED,
    build_source_completeness,
)
from .contracts import (
    COMPLETENESS_FORMAT,
    COMPLETENESS_SCHEMA_VERSION,
    FAMILY_DATASETS,
    RUN_QUALITY_AUTHORITY_PATHS,
    SOURCE_FAMILY_ORDER,
    validate_state_validity,
)
from .run_quality import build_run_quality


COMPLETENESS_KEYS = {
    "format",
    "schema_version",
    "product_version",
    "observation_scope",
    "source_family_catalog_version",
    "families",
    "unknown_evidence_summary",
    "authority_references",
}
COMPLETENESS_FAMILY_KEYS = {
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
AUDIT_PATHS = {
    "hill_score_daily": "audit/hill_score_daily.json",
    "endurance_score_daily": "audit/endurance_score_daily.json",
    "lactate_threshold": "audit/lactate_threshold_candidates.json",
    "race_prediction_daily": "audit/race_prediction_daily.json",
    "sleep_daily": "audit/sleep_daily.json",
    "uds_daily": "audit/uds_daily.json",
    "acute_training_load_daily": "audit/acute_training_load_daily.json",
    "training_readiness_daily": "audit/training_readiness_daily.json",
    "vo2max_daily": "audit/vo2max_daily.json",
    "hrv_daily": "audit/hrv_daily.json",
    "training_history_daily": "audit/training_history_daily.json",
}
COMPLETENESS_REASON_CODES = {
    "SOURCE_NOT_OBSERVED",
    "FIT_CLASSIFICATION_INCOMPLETE",
    "MIXED_FIT_EVIDENCE",
    "FIT_NOT_READABLE",
    "FIT_FORM_UNSUPPORTED",
    "FIT_EVIDENCE_PRESENT",
    "SOURCE_STRUCTURALLY_EMPTY",
    "SOURCE_EVIDENCE_PRESENT",
}
COMPLETENESS_CONTENT_REASON_CODES = {
    "FIT_CONTENT_INCOMPLETE",
    "SUPPORTED_CONTENT_REJECTED",
}
COMPLETENESS_GUIDANCE_CODES = {
    "CONSULT_CONTENT_VALIDITY_AND_RUN_QUALITY",
    "SUPPORTED_SOURCE_CONTAINED_ZERO_OBSERVATIONS",
    "DO_NOT_INFER_ZERO_OR_DELETION",
    "OBTAIN_COMPLETE_READABLE_EXPORT",
    "SOURCE_FORM_NOT_SUPPORTED_BY_THIS_VERSION",
    "REVIEW_REQUIRED_NO_WINNER_SELECTED",
}


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("diagnostic count is invalid")
    return value


def _json(root: Path, relative: str) -> Any:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("diagnostic authority is missing")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("diagnostic authority is invalid") from exc


def _bytes(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("diagnostic authority is missing")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError("diagnostic authority is invalid") from exc


def validate_source_completeness(
    report: Mapping[str, Any], *, product_version: str
) -> None:
    """Validate the complete local diagnostic schema without inferring values."""
    if (
        set(report) != COMPLETENESS_KEYS
        or report.get("format") != COMPLETENESS_FORMAT
        or report.get("schema_version") != COMPLETENESS_SCHEMA_VERSION
        or report.get("product_version") != product_version
        or report.get("source_family_catalog_version") != 1
        or report.get("observation_scope")
        not in {"ONE_EXPORT_OBSERVATION", "REGISTERED_SNAPSHOT_OBSERVATIONS"}
    ):
        raise ValueError("Source Completeness contract binding is invalid")
    families = report.get("families")
    if not isinstance(families, list) or not families or len(families) % 13:
        raise ValueError("Source Completeness family catalog is invalid")
    observations: dict[str, list[str]] = {}
    for item in families:
        if not isinstance(item, dict) or set(item) != COMPLETENESS_FAMILY_KEYS:
            raise ValueError("Source Completeness family shape is invalid")
        family = item.get("source_family_id")
        reference = item.get("observation_ref")
        if (
            family not in FAMILY_DATASETS
            or not isinstance(reference, str)
            or re.fullmatch(r"(?:export-1|snapshot-[1-9][0-9]*)", reference) is None
        ):
            raise ValueError("Source Completeness family identity is invalid")
        validate_state_validity(item.get("state"), item.get("content_validity"))
        candidate = _count(item.get("candidate_asset_count"))
        readable = _count(item.get("readable_asset_count"))
        _count(item.get("source_observation_count"))
        if readable > candidate:
            raise ValueError("Source Completeness count relation is invalid")
        state_counts = item.get("state_counts")
        if not isinstance(state_counts, dict) or any(
            not isinstance(key, str) or _count(value) < 0
            for key, value in state_counts.items()
        ):
            raise ValueError("Source Completeness state counts are invalid")
        for key in ("reason_codes", "content_reason_codes"):
            value = item.get(key)
            if not isinstance(value, list) or any(not isinstance(code, str) for code in value):
                raise ValueError("Source Completeness reason code list is invalid")
        if (
            not set(item["reason_codes"]) <= COMPLETENESS_REASON_CODES
            or not set(item["content_reason_codes"])
            <= COMPLETENESS_CONTENT_REASON_CODES
            or item.get("user_guidance_id") not in COMPLETENESS_GUIDANCE_CODES
        ):
            raise ValueError("Source Completeness diagnostic code is not registered")
        evidence = item.get("evidence_references")
        if (
            not isinstance(evidence, list)
            or len(evidence) != 1
            or not isinstance(evidence[0], dict)
            or set(evidence[0]) != {"artifact", "json_pointer"}
        ):
            raise ValueError("Source Completeness evidence reference is invalid")
        expected_evidence = (
            {
                "artifact": "run_summary.json",
                "json_pointer": f"/family_results/{family}",
            }
            if report["observation_scope"] == "ONE_EXPORT_OBSERVATION"
            else {
                "artifact": "snapshot/snapshot_coverage.json",
                "json_pointer": (
                    "/source_completeness_observations/"
                    f"{int(str(reference).split('-')[-1]) - 1}"
                ),
            }
        )
        if evidence != [expected_evidence]:
            raise ValueError("Source Completeness evidence reference is invalid")
        observations.setdefault(reference, []).append(str(family))
    expected_refs = (
        ["export-1"]
        if report["observation_scope"] == "ONE_EXPORT_OBSERVATION"
        else [f"snapshot-{index}" for index in range(1, len(observations) + 1)]
    )
    if sorted(observations) != sorted(expected_refs) or any(
        set(observations[reference]) != set(SOURCE_FAMILY_ORDER)
        or len(observations[reference]) != len(SOURCE_FAMILY_ORDER)
        for reference in expected_refs
    ):
        raise ValueError("Source Completeness observation catalog is invalid")
    expected_order = [
        (family, reference)
        for family in SOURCE_FAMILY_ORDER
        for reference in expected_refs
    ]
    actual_order = [
        (item["source_family_id"], item["observation_ref"])
        for item in families
    ]
    if actual_order != expected_order:
        raise ValueError("Source Completeness ordering is invalid")
    unknown = report.get("unknown_evidence_summary")
    if (
        not isinstance(unknown, dict)
        or set(unknown) != {"classification", "content_validity", "count", "reason_codes"}
        or unknown.get("classification") != "UNKNOWN"
        or unknown.get("content_validity") != "UNKNOWN"
        or _count(unknown.get("count")) < 0
        or unknown.get("reason_codes")
        not in ([], ["UNCLASSIFIED_DISCOVERED_OBJECT"])
        or not isinstance(report.get("authority_references"), list)
        or any(not isinstance(value, str) for value in report["authority_references"])
    ):
        raise ValueError("Source Completeness unknown evidence is invalid")


def _fit_status(fit_audit: Any) -> dict[str, int]:
    if not isinstance(fit_audit, list):
        raise ValueError("FIT audit is invalid")
    statuses: Counter[str] = Counter()
    incomplete = 0
    for item in fit_audit:
        if not isinstance(item, dict) or not isinstance(item.get("parse_status"), str):
            raise ValueError("FIT audit entry is invalid")
        status = item["parse_status"]
        statuses[status] += 1
        unknown = _count(item.get("unknown_records", 0))
        if status in FIT_UNREADABLE | FIT_UNSUPPORTED | FIT_MALFORMED or unknown:
            incomplete += 1
    return {
        "incomplete_fit_count": incomplete,
        **{f"status_{key}": value for key, value in sorted(statuses.items())},
    }


def _dataset_record_counts(dataset_qa: Mapping[str, Any]) -> dict[str, int]:
    entries = dataset_qa.get("datasets")
    if not isinstance(entries, list):
        raise ValueError("dataset QA authority is invalid")
    result: dict[str, int] = {}
    for item in entries:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("dataset"), str)
            or item["dataset"] in result
        ):
            raise ValueError("dataset QA authority is invalid")
        result[item["dataset"]] = _count(item.get("record_count"))
    return result


def _reconcile_one_export_completeness(
    report: Mapping[str, Any],
    *,
    product_version: str,
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
    dataset_qa: Mapping[str, Any],
    performance_audit: Mapping[str, Mapping[str, Any]],
    fit_audit: Any,
) -> None:
    family_results = summary.get("family_results")
    if not isinstance(family_results, dict):
        raise ValueError("Run Summary family authority is invalid")
    candidate_counts: dict[str, int] = {}
    for family in SOURCE_FAMILY_ORDER:
        result = family_results.get(family)
        if not isinstance(result, dict):
            raise ValueError("Run Summary family authority is invalid")
        candidate_counts[family] = _count(result.get("detected_asset_count"))
    dataset_counts = _dataset_record_counts(dataset_qa)
    source_counts = {
        family: sum(dataset_counts.get(dataset, 0) for dataset in datasets)
        for family, datasets in FAMILY_DATASETS.items()
    }
    input_assets = manifest.get("input_assets")
    if not isinstance(input_assets, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("detected_family"), str)
        for item in input_assets
    ):
        raise ValueError("Run Manifest input authority is invalid")
    expected = build_source_completeness(
        product_version=product_version,
        family_candidate_counts=candidate_counts,
        records={},
        fit_status=_fit_status(fit_audit),
        performance_audit=performance_audit,
        unknown_evidence_count=sum(
            item["detected_family"] == "unclassified" for item in input_assets
        ),
        source_observation_counts=source_counts,
    )
    if report != expected:
        raise ValueError("Source Completeness contradicts Run-All authorities")


def _reconcile_snapshot_completeness(
    root: Path,
    report: Mapping[str, Any],
    *,
    product_version: str,
    fit_audit: Any,
) -> None:
    lineage = _json(root, "snapshot/snapshot_lineage.json")
    coverage = _json(root, "snapshot/snapshot_coverage.json")
    merge_summary = _json(root, "snapshot/canonical_merge_summary.json")
    if not all(isinstance(value, dict) for value in (lineage, coverage, merge_summary)):
        raise ValueError("Snapshot completeness authority is invalid")
    snapshot_count = _count(lineage.get("snapshot_count"))
    snapshots = lineage.get("snapshots")
    if (
        snapshot_count < 1
        or coverage.get("snapshot_count") != snapshot_count
        or merge_summary.get("snapshot_count") != snapshot_count
        or not isinstance(snapshots, list)
        or len(snapshots) != snapshot_count
        or [item.get("logical_order") for item in snapshots if isinstance(item, dict)]
        != list(range(1, snapshot_count + 1))
        or [item.get("acquisition_order") for item in snapshots if isinstance(item, dict)]
        != list(range(1, snapshot_count + 1))
    ):
        raise ValueError("Snapshot chronology authority is invalid")
    if report.get("authority_references") != [
        "snapshot/snapshot_lineage.json",
        "snapshot/snapshot_coverage.json",
        "run_summary.json#/family_results",
        "audit/fit_audit.json",
    ]:
        raise ValueError("Snapshot completeness reference authority is invalid")
    observations = coverage.get("source_completeness_observations")
    if not isinstance(observations, list) or len(observations) != snapshot_count:
        raise ValueError("Snapshot completeness observation authority is invalid")
    expected = build_source_completeness(
        product_version=product_version,
        family_candidate_counts={family: 0 for family in SOURCE_FAMILY_ORDER},
        records={},
        fit_status={},
        performance_audit={},
        unknown_evidence_count=0,
        snapshot_context={
            "observation_scope": "REGISTERED_SNAPSHOT_OBSERVATIONS",
            "observations": observations,
        },
        fit_audit=fit_audit if isinstance(fit_audit, list) else (),
    )
    if report != expected:
        raise ValueError("Snapshot Source Completeness contradicts coverage")
    if (
        _count(report["unknown_evidence_summary"].get("count"))
        != _count(coverage.get("unknown_or_unsupported_object_count"))
        or sum(
            _count(item.get("candidate_counts", {}).get("fit"))
            for item in observations
            if isinstance(item, dict)
        )
        != _count(merge_summary.get("fit", {}).get("source_alias_count"))
    ):
        raise ValueError("Snapshot completeness aggregate contradicts coverage")


def validate_diagnostic_authorities(
    root: Path,
    *,
    manifest: Mapping[str, Any],
    summary: Mapping[str, Any],
    completeness: Mapping[str, Any],
    quality: Mapping[str, Any],
) -> None:
    """Reconcile diagnostics with existing QA/audit authorities fail-closed."""
    product_version = summary.get("product_version")
    if not isinstance(product_version, str):
        raise ValueError("Product version is invalid")
    validate_source_completeness(completeness, product_version=product_version)
    dataset_qa = _json(root, "qa/dataset_summary.json")
    relationship_qa = _json(root, "qa/relationship_summary.json")
    if (
        not isinstance(dataset_qa, dict)
        or set(dataset_qa) != {"format", "status", "datasets", "fit_semantic_normalization"}
        or dataset_qa.get("status") != "PASS"
        or not isinstance(dataset_qa.get("datasets"), list)
        or not isinstance(relationship_qa, dict)
    ):
        raise ValueError("QA authority shape is invalid")
    performance_audit = {
        name: _json(root, relative) for name, relative in AUDIT_PATHS.items()
    }
    if any(not isinstance(value, dict) for value in performance_audit.values()):
        raise ValueError("audit authority shape is invalid")
    fit_audit = _json(root, "audit/fit_audit.json")
    if completeness.get("observation_scope") == "ONE_EXPORT_OBSERVATION":
        _reconcile_one_export_completeness(
            completeness,
            product_version=product_version,
            summary=summary,
            manifest=manifest,
            dataset_qa=dataset_qa,
            performance_audit=performance_audit,
            fit_audit=fit_audit,
        )
    else:
        _reconcile_snapshot_completeness(
            root,
            completeness,
            product_version=product_version,
            fit_audit=fit_audit,
        )
    authority_payloads = {
        relative: _bytes(root, relative)
        for relative in RUN_QUALITY_AUTHORITY_PATHS
    }
    expected = build_run_quality(
        product_version=product_version,
        run_all_version=summary.get("run_all_version"),
        status=summary.get("status"),
        warnings=summary.get("warnings", []),
        dataset_qa_entries=dataset_qa["datasets"],
        relationship_summary=relationship_qa,
        performance_audit=performance_audit,
        fit_status=_fit_status(fit_audit),
        source_completeness=completeness,
        authority_payloads=authority_payloads,
    )
    if quality != expected:
        raise ValueError("Run Quality contradicts QA or audit authority")
    manifest_outputs = manifest.get("outputs")
    if not isinstance(manifest_outputs, list):
        raise ValueError("manifest output inventory is invalid")
    manifest_by_path = {
        item.get("path"): item
        for item in manifest_outputs
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    for relative in (
        *RUN_QUALITY_AUTHORITY_PATHS,
        "diagnostics/source_completeness.json",
        "diagnostics/run_quality.json",
    ):
        item = manifest_by_path.get(relative)
        data = _bytes(root, relative)
        if (
            not isinstance(item, dict)
            or item.get("bytes") != len(data)
            or item.get("sha256")
            != hashlib.sha256(data).hexdigest()
        ):
            raise ValueError("diagnostic authority manifest binding is invalid")


__all__ = ["validate_diagnostic_authorities", "validate_source_completeness"]
