from __future__ import annotations

import json
import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable, Iterable

from ..intake.discovery import DiscoveredAsset


class DailyMetricError(ValueError):
    """Base error for bounded Garmin daily-metric normalization."""


class DailyMetricConflictError(DailyMetricError):
    """Raised when one daily stable key has divergent public state."""


@dataclass(frozen=True)
class DailyMetricResult:
    records: list[dict[str, Any]]
    audit: dict[str, Any]


def logical_basename(asset: DiscoveredAsset) -> str:
    return PurePosixPath(asset.member_path or asset.source_path).name.lower()


def load_rows(asset: DiscoveredAsset) -> list[dict[str, Any]]:
    try:
        value = json.loads(asset.data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DailyMetricError("daily metric JSON could not be decoded") from exc
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("data", "items", "records", "values", "summaries", "sleepData"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def selected_rows(
    assets: Iterable[DiscoveredAsset],
    predicate: Callable[[str], bool],
) -> tuple[list[DiscoveredAsset], list[dict[str, Any]]]:
    selected = [
        asset
        for asset in assets
        if asset.kind == "json" and predicate(logical_basename(asset))
    ]
    rows = [row for asset in selected for row in load_rows(asset)]
    return selected, rows


def number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, int):
        return value if abs(value) <= (1 << 53) - 1 else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:
        parsed = float(str(value))
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed) if parsed.is_integer() else parsed


def text(value: Any) -> str | None:
    return value if isinstance(value, str) and value != "" else None


def boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def variant_fingerprint(value: Any) -> str:
    """Return a deterministic, content-only identity for an observed value."""
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def finalize_daily(
    *,
    dataset: str,
    key_fields: tuple[str, ...],
    selected_assets: list[DiscoveredAsset],
    source_record_count: int,
    accepted: list[dict[str, Any]],
    excluded_reasons: Counter[str],
    review_on_any_duplicate: bool = False,
    duplicate_review_factory: Callable[[str, list[dict[str, Any]]], dict[str, Any]] | None = None,
    signature_factory: Callable[[dict[str, Any]], str] | None = None,
    provenance_conflict_predicate: Callable[[list[dict[str, Any]]], bool] | None = None,
    strip_internal_fields: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    dedupe_exact_duplicates: bool = False,
    preserve_observed_variants: bool = False,
    variant_lineage: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> DailyMetricResult:
    if not key_fields:
        raise DailyMetricError("daily metric stable key must not be empty")
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        grouped[tuple(str(row[field]) for field in key_fields)].append(row)
    output: list[dict[str, Any]] = []
    same_value_duplicates = 0
    review_key_count = 0
    duplicate_group_count = 0
    duplicate_row_count = 0
    divergent_duplicate_count = 0
    dedupe_method = "none"
    observed_variants: list[dict[str, Any]] = []
    multi_variant_key_count = 0
    observed_variant_count = 0
    for key in sorted(grouped):
        rows = grouped[key]
        signatures = {
            (signature_factory(row) if signature_factory else stable_json(row))
            for row in rows
        }
        same_value_duplicates += len(rows) - len(signatures)
        if len(rows) > 1:
            duplicate_group_count += 1
            duplicate_row_count += len(rows) - 1
        provenance_conflict = bool(
            provenance_conflict_predicate and len(rows) > 1 and provenance_conflict_predicate(rows)
        )
        if provenance_conflict or (review_on_any_duplicate and len(rows) > 1):
            if duplicate_review_factory is None:
                raise DailyMetricError("duplicate review factory is required")
            output.append(duplicate_review_factory(key[0], rows))
            review_key_count += 1
            dedupe_method = "review_required"
            continue
        if len(signatures) > 1:
            divergent_duplicate_count += 1
            if not preserve_observed_variants:
                raise DailyMetricConflictError(
                    f"{dataset} contains divergent values for one stable key"
                )
            multi_variant_key_count += 1
            observed_variant_count += len(signatures)
            for signature in sorted(signatures):
                row = next(item for item in rows if (signature_factory(item) if signature_factory else stable_json(item)) == signature)
                evidence = {
                    "canonical_key": {field: value for field, value in zip(key_fields, key)},
                    "variant_fingerprint": variant_fingerprint(row),
                    "observed_value": strip_internal_fields(row) if strip_internal_fields else dict(row),
                    "observation_count": sum(
                        (signature_factory(item) if signature_factory else stable_json(item)) == signature
                        for item in rows
                    ),
                    "variant_status": "observed_variant",
                    "canonical_status": "unresolved_multiple_observed_values",
                }
                lineage = (variant_lineage or {}).get((key[0], variant_fingerprint(row)))
                if lineage:
                    evidence["snapshot_lineage"] = dict(lineage)
                observed_variants.append(evidence)
            continue
        output.append(strip_internal_fields(rows[0]) if strip_internal_fields else rows[0])
        if len(rows) > 1 and dedupe_exact_duplicates:
            dedupe_method = "exact_canonical_duplicate_collapsed"
    # Exclusions are evidence about records that could not enter the accepted
    # population; they are not themselves review-required observations.  Keep
    # the two counters separate so an excluded-only family remains a clean PASS
    # while its exclusion evidence stays visible in the audit.
    review_required_count = review_key_count + (
        multi_variant_key_count if preserve_observed_variants else 0
    )
    review_items = review_required_count
    audit = {
        "format": "garmin-running-data-normalizer-daily-metric-audit-v1",
        "dataset": dataset,
        "status": "PASS_WITH_REVIEW_ITEMS" if review_items else "PASS",
        "detected_asset_count": len(selected_assets),
        "source_record_count": source_record_count,
        "accepted_record_count": len(output),
        "excluded_record_count": sum(excluded_reasons.values()),
        "excluded_reason_counts": dict(sorted(excluded_reasons.items())),
        "same_value_duplicate_count": same_value_duplicates,
        "review_key_count": review_key_count,
        "stable_key": list(key_fields),
        "merge_policy": "observation_union_missing_is_not_delete_conflict_fail_closed",
        "keep_last": False,
        "carry_forward": False,
        "interpolation": False,
        "source_paths_exposed": False,
        "private_identifiers_exposed": False,
    }
    if preserve_observed_variants:
        audit.update(
            {
                "canonical_key_count": len(grouped),
                "single_variant_key_count": len(grouped) - multi_variant_key_count,
                "multi_variant_key_count": multi_variant_key_count,
                "observed_variant_count": observed_variant_count,
                "exact_repeat_count": same_value_duplicates,
                "malformed_count": sum(excluded_reasons.values()),
                "canonicalization_unresolved_count": multi_variant_key_count,
                "automatic_winner": False,
                "observed_variants": sorted(
                    observed_variants,
                    key=lambda item: (
                        stable_json(item["canonical_key"]),
                        item["variant_fingerprint"],
                    ),
                ),
                "variant_policy": "preserve_observed_variants_fail_closed_canonicalization",
            }
        )
    if (
        source_record_count
        and (
            dedupe_exact_duplicates
            or provenance_conflict_predicate is not None
            or excluded_reasons
            or review_required_count
        )
    ):
        audit.update(
            {
                "duplicate_group_count": duplicate_group_count,
                "duplicate_row_count": duplicate_row_count,
                "dedupe_method": dedupe_method,
                "divergent_duplicate_count": divergent_duplicate_count,
                "review_required_count": review_required_count,
                "review_item_count": review_items,
            }
        )
    return DailyMetricResult(
        records=output,
        audit=audit,
    )


__all__ = [
    "DailyMetricConflictError",
    "DailyMetricError",
    "DailyMetricResult",
    "boolean",
    "finalize_daily",
    "load_rows",
    "logical_basename",
    "number",
    "selected_rows",
    "stable_json",
    "text",
    "variant_fingerprint",
]
