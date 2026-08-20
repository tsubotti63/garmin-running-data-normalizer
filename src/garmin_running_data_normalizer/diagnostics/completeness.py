"""Source Completeness projection over existing discovery and audit evidence."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (
    COMPLETENESS_FORMAT,
    COMPLETENESS_SCHEMA_VERSION,
    FAMILY_DATASETS,
    SOURCE_FAMILY_ORDER,
    validate_state_validity,
)


FIT_READABLE = frozenset({"parsed_activity", "parsed_non_activity"})
FIT_UNREADABLE = frozenset(
    {
        "too_large",
        "too_small",
        "bad_header",
        "bad_header_crc",
        "bad_file_crc",
        "truncated",
        "undefined_local_message",
    }
)
FIT_UNSUPPORTED = frozenset({"unsupported_chained"})
FIT_MALFORMED = frozenset({"session_lap_allocation_conflict"})


def _non_negative(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("diagnostic count must be a non-negative integer")
    return value


def _audit_for_family(
    family: str,
    performance_audit: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    datasets = FAMILY_DATASETS[family]
    for dataset in datasets:
        if dataset in performance_audit:
            return performance_audit[dataset]
    return {}


def _fit_interpretation(
    *,
    candidate_count: int,
    source_observation_count: int,
    fit_status: Mapping[str, Any],
) -> tuple[str, str, list[str], list[str], dict[str, int], int]:
    counts = {
        key.removeprefix("status_"): _non_negative(value)
        for key, value in fit_status.items()
        if key.startswith("status_")
    }
    if candidate_count == 0:
        return "ABSENT", "NOT_APPLICABLE", ["SOURCE_NOT_OBSERVED"], [], {}, 0
    readable = sum(counts.get(name, 0) for name in FIT_READABLE)
    unreadable = sum(counts.get(name, 0) for name in FIT_UNREADABLE)
    unsupported = sum(counts.get(name, 0) for name in FIT_UNSUPPORTED)
    malformed = sum(counts.get(name, 0) for name in FIT_MALFORMED)
    classified = readable + unreadable + unsupported + malformed
    if classified != candidate_count:
        return (
            "AMBIGUOUS",
            "UNKNOWN",
            ["FIT_CLASSIFICATION_INCOMPLETE"],
            [],
            dict(sorted(counts.items())),
            readable + malformed,
        )
    category_count = sum(bool(value) for value in (readable, unreadable, unsupported, malformed))
    if category_count > 1:
        return (
            "AMBIGUOUS",
            "UNKNOWN",
            ["MIXED_FIT_EVIDENCE"],
            [],
            dict(sorted(counts.items())),
            readable + malformed,
        )
    if unreadable:
        return (
            "UNREADABLE",
            "UNKNOWN",
            ["FIT_NOT_READABLE"],
            [],
            dict(sorted(counts.items())),
            0,
        )
    if unsupported:
        return (
            "UNSUPPORTED",
            "NOT_APPLICABLE",
            ["FIT_FORM_UNSUPPORTED"],
            [],
            dict(sorted(counts.items())),
            0,
        )
    if malformed or int(fit_status.get("incomplete_fit_count", 0)):
        return (
            "PRESENT",
            "MALFORMED",
            ["FIT_EVIDENCE_PRESENT"],
            ["FIT_CONTENT_INCOMPLETE"],
            dict(sorted(counts.items())),
            readable + malformed,
        )
    state = "PRESENT" if source_observation_count else "EMPTY"
    return (
        state,
        "VALID",
        ["FIT_EVIDENCE_PRESENT" if state == "PRESENT" else "SOURCE_STRUCTURALLY_EMPTY"],
        [],
        dict(sorted(counts.items())),
        readable,
    )


def build_source_completeness(
    *,
    product_version: str,
    family_candidate_counts: Mapping[str, int],
    records: Mapping[str, Sequence[Mapping[str, Any]]],
    fit_status: Mapping[str, Any],
    performance_audit: Mapping[str, Mapping[str, Any]],
    unknown_evidence_count: int,
    source_observation_counts: Mapping[str, int] | None = None,
    snapshot_context: Mapping[str, Any] | None = None,
    fit_audit: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build deterministic one-shot or per-Snapshot completeness observations."""
    if snapshot_context is not None:
        if set(snapshot_context) != {"observation_scope", "observations"} or (
            snapshot_context.get("observation_scope")
            != "REGISTERED_SNAPSHOT_OBSERVATIONS"
        ):
            raise ValueError("Snapshot completeness context is invalid")
        observations = snapshot_context.get("observations")
        if not isinstance(observations, list) or not observations:
            raise ValueError("Snapshot completeness observations are missing")
        fit_by_sha = {
            str(item.get("source_sha256")): item
            for item in fit_audit
            if isinstance(item, Mapping) and item.get("source_sha256")
        }
        all_families: list[dict[str, Any]] = []
        unknown_total = 0
        expected_refs = [f"snapshot-{index}" for index in range(1, len(observations) + 1)]
        for observation_index, (expected_ref, observation) in enumerate(
            zip(expected_refs, observations, strict=True)
        ):
            if not isinstance(observation, Mapping) or set(observation) != {
                "observation_ref",
                "candidate_counts",
                "source_observation_counts",
                "malformed_counts",
                "fit_source_sha256",
                "unknown_evidence_count",
            }:
                raise ValueError("Snapshot completeness observation is invalid")
            if observation.get("observation_ref") != expected_ref:
                raise ValueError("Snapshot completeness chronology is invalid")
            candidate_counts = observation.get("candidate_counts")
            observed_counts = observation.get("source_observation_counts")
            malformed_counts = observation.get("malformed_counts")
            if (
                not isinstance(candidate_counts, Mapping)
                or not isinstance(observed_counts, Mapping)
                or not isinstance(malformed_counts, Mapping)
                or set(candidate_counts) != set(SOURCE_FAMILY_ORDER)
                or set(observed_counts) != set(SOURCE_FAMILY_ORDER)
                or set(malformed_counts) != set(SOURCE_FAMILY_ORDER)
            ):
                raise ValueError("Snapshot source-family catalog is invalid")
            per_snapshot_audit: dict[str, dict[str, Any]] = {}
            for family in SOURCE_FAMILY_ORDER:
                malformed = _non_negative(malformed_counts[family])
                if malformed:
                    per_snapshot_audit[FAMILY_DATASETS[family][0]] = {
                        "malformed_count": malformed
                    }
            fit_counts: Counter[str] = Counter()
            fit_record_count = 0
            fit_incomplete_count = 0
            fit_digests = observation.get("fit_source_sha256")
            if not isinstance(fit_digests, list) or any(
                not isinstance(value, str) for value in fit_digests
            ):
                raise ValueError("Snapshot FIT evidence is invalid")
            for digest in fit_digests:
                item = fit_by_sha.get(digest)
                if item is None:
                    raise ValueError("Snapshot FIT audit binding is incomplete")
                status = str(item.get("parse_status"))
                fit_counts[status] += 1
                fit_record_count += _non_negative(item.get("record_count", 0))
                if status in FIT_UNREADABLE | FIT_UNSUPPORTED | FIT_MALFORMED or _non_negative(
                    item.get("unknown_records", 0)
                ):
                    fit_incomplete_count += 1
            per_snapshot_fit_status = {
                "incomplete_fit_count": fit_incomplete_count,
                **{
                    f"status_{status}": count
                    for status, count in sorted(fit_counts.items())
                },
            }
            effective_counts = {
                family: _non_negative(observed_counts[family])
                for family in SOURCE_FAMILY_ORDER
            }
            effective_counts["fit"] = fit_record_count
            per_snapshot = build_source_completeness(
                product_version=product_version,
                family_candidate_counts={
                    family: _non_negative(candidate_counts[family])
                    for family in SOURCE_FAMILY_ORDER
                },
                records=records,
                fit_status=per_snapshot_fit_status,
                performance_audit=per_snapshot_audit,
                unknown_evidence_count=_non_negative(
                    observation["unknown_evidence_count"]
                ),
                source_observation_counts=effective_counts,
            )
            unknown_total += int(
                per_snapshot["unknown_evidence_summary"]["count"]
            )
            for family_entry in per_snapshot["families"]:
                family_entry["observation_ref"] = expected_ref
                family_entry["evidence_references"] = [
                    {
                        "artifact": "snapshot/snapshot_coverage.json",
                        "json_pointer": (
                            "/source_completeness_observations/"
                            f"{observation_index}"
                        ),
                    }
                ]
                all_families.append(family_entry)
        family_order = {family: index for index, family in enumerate(SOURCE_FAMILY_ORDER)}
        all_families.sort(
            key=lambda item: (
                family_order[str(item["source_family_id"])],
                int(str(item["observation_ref"]).split("-")[-1]),
            )
        )
        return {
            "format": COMPLETENESS_FORMAT,
            "schema_version": COMPLETENESS_SCHEMA_VERSION,
            "product_version": product_version,
            "observation_scope": "REGISTERED_SNAPSHOT_OBSERVATIONS",
            "source_family_catalog_version": 1,
            "families": all_families,
            "unknown_evidence_summary": {
                "classification": "UNKNOWN",
                "content_validity": "UNKNOWN",
                "count": unknown_total,
                "reason_codes": (
                    ["UNCLASSIFIED_DISCOVERED_OBJECT"] if unknown_total else []
                ),
            },
            "authority_references": [
                "snapshot/snapshot_lineage.json",
                "snapshot/snapshot_coverage.json",
                "run_summary.json#/family_results",
                "audit/fit_audit.json",
            ],
        }
    if set(family_candidate_counts) != set(SOURCE_FAMILY_ORDER):
        raise ValueError("source-family candidate catalog does not match v1")
    if source_observation_counts is not None and set(source_observation_counts) != set(
        SOURCE_FAMILY_ORDER
    ):
        raise ValueError("source-family observation catalog does not match v1")
    families: list[dict[str, Any]] = []
    for family in SOURCE_FAMILY_ORDER:
        candidate_count = _non_negative(family_candidate_counts[family])
        source_observation_count = (
            _non_negative(source_observation_counts[family])
            if source_observation_counts is not None
            else sum(len(records[name]) for name in FAMILY_DATASETS[family])
        )
        if family == "fit":
            state, validity, reasons, content_reasons, state_counts, readable = (
                _fit_interpretation(
                    candidate_count=candidate_count,
                    source_observation_count=source_observation_count,
                    fit_status=fit_status,
                )
            )
        elif candidate_count == 0:
            state, validity = "ABSENT", "NOT_APPLICABLE"
            reasons, content_reasons, readable = ["SOURCE_NOT_OBSERVED"], [], 0
            state_counts = {"ABSENT": 1}
        else:
            audit = _audit_for_family(family, performance_audit)
            malformed_count = sum(
                int(audit.get(key, 0) or 0)
                for key in (
                    "invalid_value_count",
                    "missing_date_count",
                    "malformed_count",
                    "excluded_record_count",
                )
            )
            if malformed_count:
                state, validity = "PRESENT", "MALFORMED"
                reasons = ["SOURCE_EVIDENCE_PRESENT"]
                content_reasons = ["SUPPORTED_CONTENT_REJECTED"]
            elif source_observation_count:
                state, validity = "PRESENT", "VALID"
                reasons, content_reasons = ["SOURCE_EVIDENCE_PRESENT"], []
            else:
                state, validity = "EMPTY", "VALID"
                reasons, content_reasons = ["SOURCE_STRUCTURALLY_EMPTY"], []
            readable = candidate_count
            state_counts = {state: candidate_count}
        validate_state_validity(state, validity)
        guidance = {
            "PRESENT": "CONSULT_CONTENT_VALIDITY_AND_RUN_QUALITY",
            "EMPTY": "SUPPORTED_SOURCE_CONTAINED_ZERO_OBSERVATIONS",
            "ABSENT": "DO_NOT_INFER_ZERO_OR_DELETION",
            "UNREADABLE": "OBTAIN_COMPLETE_READABLE_EXPORT",
            "UNSUPPORTED": "SOURCE_FORM_NOT_SUPPORTED_BY_THIS_VERSION",
            "AMBIGUOUS": "REVIEW_REQUIRED_NO_WINNER_SELECTED",
        }[state]
        families.append(
            {
                "source_family_id": family,
                "observation_ref": "export-1",
                "state": state,
                "content_validity": validity,
                "candidate_asset_count": candidate_count,
                "readable_asset_count": readable,
                "source_observation_count": source_observation_count,
                "state_counts": dict(sorted(state_counts.items())),
                "reason_codes": sorted(reasons),
                "content_reason_codes": sorted(content_reasons),
                "evidence_references": [
                    {
                        "artifact": "run_summary.json",
                        "json_pointer": f"/family_results/{family}",
                    }
                ],
                "user_guidance_id": guidance,
            }
        )
    unknown_count = _non_negative(unknown_evidence_count)
    return {
        "format": COMPLETENESS_FORMAT,
        "schema_version": COMPLETENESS_SCHEMA_VERSION,
        "product_version": product_version,
        "observation_scope": "ONE_EXPORT_OBSERVATION",
        "source_family_catalog_version": 1,
        "families": families,
        "unknown_evidence_summary": {
            "classification": "UNKNOWN",
            "content_validity": "UNKNOWN",
            "count": unknown_count,
            "reason_codes": (["UNCLASSIFIED_DISCOVERED_OBJECT"] if unknown_count else []),
        },
        "authority_references": [
            "run_manifest.json#/input_assets",
            "run_summary.json#/family_results",
            "audit/fit_audit.json",
        ],
    }


__all__ = ["build_source_completeness"]
