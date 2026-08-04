from __future__ import annotations

import json
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


def finalize_daily(
    *,
    dataset: str,
    key_field: str,
    selected_assets: list[DiscoveredAsset],
    source_record_count: int,
    accepted: list[dict[str, Any]],
    excluded_reasons: Counter[str],
    review_on_any_duplicate: bool = False,
    duplicate_review_factory: Callable[[str, list[dict[str, Any]]], dict[str, Any]] | None = None,
) -> DailyMetricResult:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        grouped[str(row[key_field])].append(row)
    output: list[dict[str, Any]] = []
    same_value_duplicates = 0
    review_key_count = 0
    for key in sorted(grouped):
        rows = grouped[key]
        signatures = {stable_json(row) for row in rows}
        same_value_duplicates += len(rows) - len(signatures)
        if review_on_any_duplicate and len(rows) > 1:
            if duplicate_review_factory is None:
                raise DailyMetricError("duplicate review factory is required")
            output.append(duplicate_review_factory(key, rows))
            review_key_count += 1
            continue
        if len(signatures) > 1:
            raise DailyMetricConflictError(
                f"{dataset} contains divergent values for one daily stable key"
            )
        output.append(rows[0])
    review_items = sum(excluded_reasons.values()) + review_key_count
    return DailyMetricResult(
        records=output,
        audit={
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
            "stable_key": [key_field],
            "merge_policy": "daily_state_upsert_missing_is_not_delete_conflict_fail_closed",
            "keep_last": False,
            "carry_forward": False,
            "interpolation": False,
            "source_paths_exposed": False,
            "private_identifiers_exposed": False,
        },
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
]
