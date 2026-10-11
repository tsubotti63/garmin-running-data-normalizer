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


def _value_order(item: tuple[str, list[Any]]) -> tuple[int, float, str]:
    """Order observed values: numbers by size, then other values by their JSON."""
    key, (value, _count) = item
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, value, key)
    return (1, 0, key)


@dataclass(frozen=True)
class MergedObservations:
    """Observations of one stable key merged into one row.

    ``disagreements`` lists, for each field whose observed values differ, every
    value and how many observations gave it. ``absent_values`` counts, per
    field, the observations without a value while another observation had one.
    """

    row: dict[str, Any]
    disagreeing_fields: list[str]
    disagreements: list[dict[str, Any]]
    absent_values: Counter[str]


def merge_observations(
    rows: list[dict[str, Any]],
    fields: Iterable[str],
    *,
    key_fields: tuple[str, ...],
    presence_flags: frozenset[str] = frozenset(),
    recomputed_fields: frozenset[str] = frozenset(),
    alternatives: list[dict[str, list[Any]]] | None = None,
) -> MergedObservations:
    """Merge the observations of one stable key, field by field.

    A null value means that the observation has no value; it is left out of
    the comparison. A field with one observed value keeps it. A field with
    several observed values is left empty and listed as disagreeing. A flag in
    ``presence_flags`` says whether a source group was present, so it is true
    when any observation had the group. Fields in ``recomputed_fields`` are
    set afterwards from the merged row and are not compared here.
    ``alternatives``, one entry per row, give the values that one observation
    holds for a field when its source fields disagree among themselves.
    """
    merged: dict[str, Any] = {}
    disagreeing: list[str] = []
    disagreements: list[dict[str, Any]] = []
    absent: Counter[str] = Counter()
    for field in fields:
        if field in key_fields:
            merged[field] = rows[0].get(field)
            continue
        if field in recomputed_fields:
            merged[field] = None
            continue
        if field in presence_flags:
            merged[field] = any(row.get(field) is True for row in rows)
            continue
        counts: dict[str, list[Any]] = {}
        observed = 0
        for index, row in enumerate(rows):
            held = (alternatives[index] if alternatives else {}).get(field)
            values = [item for item in held if item is not None] if held else [row.get(field)]
            values = [value for value in values if value is not None]
            if not values:
                continue
            observed += 1
            # One observation counts once for each value it gives.
            for value in {stable_json(value): value for value in values}.values():
                counts.setdefault(stable_json(value), [value, 0])[1] += 1
        if observed and observed < len(rows):
            absent[field] += len(rows) - observed
        if len(counts) > 1:
            merged[field] = None
            disagreeing.append(field)
            disagreements.append(
                {
                    "field": field,
                    "values": [
                        {"value": value, "observation_count": count}
                        for _key, (value, count) in sorted(counts.items(), key=_value_order)
                    ],
                }
            )
        else:
            merged[field] = next(iter(counts.values()))[0] if counts else None
    return MergedObservations(merged, disagreeing, disagreements, absent)


def finalize_daily(
    *,
    dataset: str,
    key_fields: tuple[str, ...],
    selected_assets: list[DiscoveredAsset],
    source_record_count: int,
    accepted: list[dict[str, Any]],
    excluded_reasons: Counter[str],
    fields: tuple[str, ...] | None = None,
    review_on_any_duplicate: bool = False,
    duplicate_review_factory: Callable[[str, list[dict[str, Any]]], dict[str, Any]] | None = None,
    provenance_conflict_predicate: Callable[[list[dict[str, Any]]], bool] | None = None,
    strip_internal_fields: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    dedupe_exact_duplicates: bool = False,
    presence_flags: frozenset[str] = frozenset(),
    recomputed_fields: frozenset[str] = frozenset(),
    finalize_merged: Callable[[dict[str, Any], list[str]], None] | None = None,
    alternatives: Callable[[dict[str, Any]], dict[str, list[Any]]] | None = None,
) -> DailyMetricResult:
    """Keep one row per stable key; values that disagree are left empty.

    ``fields`` are the dataset's public fields, in order and without
    ``disagreeing_fields``; by default, those of the first row. Each output row
    lists its disagreeing fields in ``disagreeing_fields``, and the audit keeps
    every observed value of them. ``finalize_merged`` sets the
    ``recomputed_fields`` of a merged row from its merged values.
    ``alternatives`` returns, from an accepted row before its internal fields
    are stripped, the values that the row holds for a field whose source
    fields disagree; such a field disagrees even within one observation.
    """
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
    collapsed_exact = False
    merged_different = False
    disagreements: list[dict[str, Any]] = []
    absent_values: Counter[str] = Counter()
    for key in sorted(grouped):
        rows = [
            strip_internal_fields(row) if strip_internal_fields else dict(row)
            for row in grouped[key]
        ]
        held = [alternatives(row) for row in grouped[key]] if alternatives else []
        signatures = {stable_json(row) for row in rows}
        same_value_duplicates += len(rows) - len(signatures)
        if len(rows) > 1:
            duplicate_group_count += 1
            duplicate_row_count += len(rows) - 1
        provenance_conflict = bool(
            provenance_conflict_predicate
            and len(rows) > 1
            and provenance_conflict_predicate(grouped[key])
        )
        if provenance_conflict or (review_on_any_duplicate and len(rows) > 1):
            if duplicate_review_factory is None:
                raise DailyMetricError("duplicate review factory is required")
            row = dict(duplicate_review_factory(key[0], grouped[key]))
            row["disagreeing_fields"] = []
            output.append(row)
            review_key_count += 1
            continue
        if len(signatures) == 1 and not any(held):
            row = dict(rows[0])
            row["disagreeing_fields"] = []
            output.append(row)
            collapsed_exact = collapsed_exact or len(rows) > 1
            continue
        merged_different = merged_different or len(signatures) > 1
        merged = merge_observations(
            rows,
            fields if fields is not None else tuple(rows[0]),
            key_fields=key_fields,
            presence_flags=presence_flags,
            recomputed_fields=recomputed_fields,
            alternatives=held or None,
        )
        if finalize_merged is not None:
            finalize_merged(merged.row, merged.disagreeing_fields)
        row = dict(merged.row)
        row["disagreeing_fields"] = list(merged.disagreeing_fields)
        output.append(row)
        absent_values.update(merged.absent_values)
        if merged.disagreements:
            disagreements.append(
                {
                    "key": {field: value for field, value in zip(key_fields, key)},
                    "observation_count": len(rows),
                    "fields": merged.disagreements,
                }
            )
    if review_key_count:
        dedupe_method = "review_required"
    elif merged_different:
        dedupe_method = "observations_merged_field_by_field"
    elif collapsed_exact and dedupe_exact_duplicates:
        dedupe_method = "exact_canonical_duplicate_collapsed"
    else:
        dedupe_method = "none"
    # Exclusions are evidence about records that could not enter the accepted
    # population; they are not themselves review-required observations.  Keep
    # the two counters separate so an excluded-only family remains a clean PASS
    # while its exclusion evidence stays visible in the audit.
    review_required_count = review_key_count
    review_items = review_required_count
    audit = {
        "format": "garmin-running-data-normalizer-daily-metric-audit-v2",
        "dataset": dataset,
        "status": "PASS_WITH_REVIEW_ITEMS" if review_items else "PASS",
        "detected_asset_count": len(selected_assets),
        "source_record_count": source_record_count,
        "accepted_record_count": len(output),
        "excluded_record_count": sum(excluded_reasons.values()),
        "excluded_reason_counts": dict(sorted(excluded_reasons.items())),
        "same_value_duplicate_count": same_value_duplicates,
        "review_key_count": review_key_count,
        "disagreement_key_count": len(disagreements),
        "disagreements": disagreements,
        "absent_value_counts": dict(sorted(absent_values.items())),
        "stable_key": list(key_fields),
        "merge_policy": "observation_union_null_is_absent_disagreeing_values_kept_empty",
        "keep_last": False,
        "carry_forward": False,
        "interpolation": False,
        "source_paths_exposed": False,
        "private_identifiers_exposed": False,
    }
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
                "review_required_count": review_required_count,
                "review_item_count": review_items,
            }
        )
    return DailyMetricResult(
        records=output,
        audit=audit,
    )


__all__ = [
    "DailyMetricError",
    "DailyMetricResult",
    "MergedObservations",
    "boolean",
    "finalize_daily",
    "load_rows",
    "logical_basename",
    "merge_observations",
    "number",
    "selected_rows",
    "stable_json",
    "text",
    "variant_fingerprint",
]
