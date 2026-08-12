from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset


HILL_FIELDS = (
    "calendar_date",
    "overall_score",
    "strength_score",
    "endurance_score",
    "classification_id",
    "feedback_phrase_id",
)
ENDURANCE_FIELDS = (
    "calendar_date",
    "overall_score",
    "classification",
    "feedback_phrase",
)
LACTATE_FIELDS = (
    "observation_timestamp",
    "observation_family",
    "lactate_threshold_speed",
    "lactate_threshold_heart_rate",
    "functional_threshold_power",
    "lactate_threshold_type",
)


class PerformanceMetricsError(ValueError):
    """Base error for bounded performance-metric normalization."""


class PerformanceMetricsConflictError(PerformanceMetricsError):
    """Raised when one daily key has more than one public value."""


@dataclass(frozen=True)
class DailyNormalizationResult:
    records: list[dict[str, Any]]
    audit: dict[str, Any]


def _logical_name(asset: DiscoveredAsset) -> str:
    return asset.member_path or asset.source_path


def _basename(asset: DiscoveredAsset) -> str:
    return PurePosixPath(_logical_name(asset)).name.lower()


def _load_json(asset: DiscoveredAsset) -> Any:
    try:
        return json.loads(asset.data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PerformanceMetricsError("performance metric JSON could not be decoded") from exc


def _root_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("records", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _calendar_date(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    return daily_calendar_date(value)


def _number(value: Any, *, integer: bool) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if integer:
        return value if isinstance(value, int) else None
    return value


def _stable_row(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _variant_fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_row(value).encode("utf-8")).hexdigest()


def _normalize_daily(
    assets: Iterable[DiscoveredAsset],
    *,
    dataset: str,
    preserve_observed_variants: bool = False,
    variant_lineage: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> DailyNormalizationResult:
    is_hill = dataset == "hill_score_daily"
    prefix = "hillscore" if is_hill else "endurancescore"
    selected_assets = [
        asset
        for asset in assets
        if asset.kind == "json" and _basename(asset).startswith(prefix)
    ]
    accepted: list[dict[str, Any]] = []
    excluded_reasons: Counter[str] = Counter()
    source_record_count = 0
    excluded_private_fields: Counter[str] = Counter()
    private_names = {
        "deviceId",
        "userProfilePk",
        "userProfilePK",
        "primaryTrainingDevice",
        "timestamp",
        "timestampGmt",
        "enduranceScoreContributor",
    }

    for asset in selected_assets:
        rows = _root_rows(_load_json(asset))
        source_record_count += len(rows)
        for raw in rows:
            excluded_private_fields.update(name for name in private_names if name in raw)
            calendar_date = _calendar_date(raw.get("calendarDate"))
            if calendar_date is None:
                excluded_reasons["missing_or_invalid_calendar_date"] += 1
                continue
            if is_hill:
                overall = _number(raw.get("overallScore"), integer=True)
                if overall is None:
                    excluded_reasons["missing_or_invalid_overall_score"] += 1
                    continue
                accepted.append(
                    {
                        "calendar_date": calendar_date,
                        "overall_score": overall,
                        "strength_score": _number(raw.get("strengthScore"), integer=True),
                        "endurance_score": _number(raw.get("enduranceScore"), integer=True),
                        "classification_id": _number(
                            raw.get("hillScoreClassificationId"), integer=True
                        ),
                        "feedback_phrase_id": _number(
                            raw.get("hillScoreFeedbackPhraseId"), integer=True
                        ),
                    }
                )
            else:
                overall = _number(raw.get("overallScore"), integer=False)
                if overall is None:
                    excluded_reasons["missing_or_invalid_overall_score"] += 1
                    continue
                accepted.append(
                    {
                        "calendar_date": calendar_date,
                        "overall_score": overall,
                        "classification": _number(raw.get("classification"), integer=False),
                        "feedback_phrase": _number(raw.get("feedbackPhrase"), integer=False),
                    }
                )

    by_date: dict[str, set[str]] = defaultdict(set)
    row_by_signature: dict[str, dict[str, Any]] = {}
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        signature = _stable_row(row)
        by_date[row["calendar_date"]].add(signature)
        row_by_signature[signature] = row
        rows_by_date[row["calendar_date"]].append(row)
    conflicts = [key for key, values in by_date.items() if len(values) > 1]
    if conflicts and not preserve_observed_variants:
        raise PerformanceMetricsConflictError(
            f"{dataset} contains divergent values for one calendar date"
        )
    normalized = [
        row_by_signature[next(iter(by_date[key]))]
        for key in sorted(by_date)
        if len(by_date[key]) == 1 or not preserve_observed_variants
    ]
    duplicate_count = sum(
        len(rows_by_date[key]) - len(by_date[key]) for key in rows_by_date
    )
    observed_variants: list[dict[str, Any]] = []
    if preserve_observed_variants:
        for calendar_date in sorted(conflicts):
            signatures = sorted(by_date[calendar_date])
            for signature in signatures:
                row = row_by_signature[signature]
                fingerprint = _variant_fingerprint(row)
                evidence = {
                    "canonical_key": {"calendar_date": calendar_date},
                    "variant_fingerprint": fingerprint,
                    "observed_value": dict(row),
                    "observation_count": sum(
                        _stable_row(item) == signature
                        for item in rows_by_date[calendar_date]
                    ),
                    "variant_status": "observed_variant",
                    "canonical_status": "unresolved_multiple_observed_values",
                }
                lineage = (variant_lineage or {}).get((calendar_date, fingerprint))
                if lineage:
                    evidence["snapshot_lineage"] = dict(lineage)
                observed_variants.append(evidence)
    review_required_count = len(conflicts)
    audit = {
        "format": "garmin-running-data-normalizer-performance-daily-audit-v1",
        "dataset": dataset,
        "status": "PASS_WITH_REVIEW_ITEMS" if review_required_count else "PASS",
        "detected_asset_count": len(selected_assets),
        "source_record_count": source_record_count,
        "accepted_record_count": len(normalized),
        "excluded_record_count": sum(excluded_reasons.values()),
        "excluded_reason_counts": dict(sorted(excluded_reasons.items())),
        "same_value_duplicate_count": duplicate_count,
        "divergent_duplicate_key_count": 0,
        "stable_key": ["calendar_date"],
        "merge_policy": "daily_state_upsert_missing_is_not_delete_conflict_fail_closed",
        "keep_last": False,
        "excluded_private_field_presence_counts": dict(
            sorted(excluded_private_fields.items())
        ),
        "source_paths_exposed": False,
        "source_hashes_exposed": False,
    }
    if preserve_observed_variants:
        audit.update(
            {
                "status": "PASS_WITH_REVIEW_ITEMS" if conflicts else "PASS",
                "canonical_key_count": len(by_date),
                "single_variant_key_count": len(by_date) - len(conflicts),
                "multi_variant_key_count": len(conflicts),
                "observed_variant_count": sum(len(values) for values in by_date.values()),
                "exact_repeat_count": sum(
                    len(rows_by_date[key]) - len(by_date[key]) for key in rows_by_date
                ),
                "malformed_count": sum(excluded_reasons.values()),
                "canonicalization_unresolved_count": len(conflicts),
                "automatic_winner": False,
                "observed_variants": observed_variants,
                "variant_policy": "preserve_observed_variants_fail_closed_canonicalization",
            }
        )
    if excluded_reasons or review_required_count:
        audit.update(
            {
                "review_required_count": review_required_count,
                "review_item_count": review_required_count,
            }
        )
    return DailyNormalizationResult(normalized, audit)


def normalize_hill_score(
    assets: Iterable[DiscoveredAsset],
) -> DailyNormalizationResult:
    return _normalize_daily(assets, dataset="hill_score_daily")


def normalize_endurance_score(
    assets: Iterable[DiscoveredAsset],
    *,
    preserve_observed_variants: bool = False,
    variant_lineage: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> DailyNormalizationResult:
    return _normalize_daily(
        assets,
        dataset="endurance_score_daily",
        preserve_observed_variants=preserve_observed_variants,
        variant_lineage=variant_lineage,
    )


def _optional_number(value: Any, review_counts: Counter[str], field: str) -> int | float | None:
    if value is None:
        return None
    parsed = _number(value, integer=False)
    if parsed is None:
        review_counts[f"invalid_{field}"] += 1
    return parsed


def collect_lactate_threshold_candidates(
    assets: Iterable[DiscoveredAsset],
) -> dict[str, Any]:
    family_patterns = (
        ("history", "userbiometrics.json"),
        ("latest_snapshot", "biometrics_latest.json"),
        ("profile_state", "userbiometricprofiledata.json"),
        ("derived_evidence", "heartratezones.json"),
    )
    candidates: list[tuple[int, str, int, dict[str, Any]]] = []
    family_asset_counts: Counter[str] = Counter()
    family_source_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()

    for asset in assets:
        if asset.kind != "json":
            continue
        name = _basename(asset)
        matched = next(
            ((index, family) for index, (family, suffix) in enumerate(family_patterns) if name.endswith(suffix)),
            None,
        )
        if matched is None:
            continue
        family_order, family = matched
        rows = _root_rows(_load_json(asset))
        family_asset_counts[family] += 1
        family_source_counts[family] += len(rows)
        for source_index, raw in enumerate(rows):
            timestamp: str | None = None
            sequence = 0
            if family == "history":
                metadata = raw.get("metaData")
                if not isinstance(metadata, dict):
                    review_counts["history_metadata_missing"] += 1
                    continue
                timestamp = _calendar_date(metadata.get("calendarDate"))
                raw_sequence = metadata.get("sequence")
                if isinstance(raw_sequence, int) and not isinstance(raw_sequence, bool):
                    sequence = raw_sequence
                if timestamp is None:
                    review_counts["history_timestamp_missing_or_invalid"] += 1
                    continue

            threshold_type = None
            if family == "derived_evidence" and raw.get("trainingMethod") == "LACTATE_THRESHOLD":
                threshold_type = "LACTATE_THRESHOLD"
            row = {
                "observation_timestamp": timestamp,
                "observation_family": family,
                "lactate_threshold_speed": _optional_number(
                    raw.get("lactateThresholdSpeed"),
                    review_counts,
                    "lactate_threshold_speed",
                ),
                "lactate_threshold_heart_rate": _optional_number(
                    raw.get("lactateThresholdHeartRate"),
                    review_counts,
                    "lactate_threshold_heart_rate",
                ),
                "functional_threshold_power": _optional_number(
                    raw.get("functionalThresholdPower"),
                    review_counts,
                    "functional_threshold_power",
                ),
                "lactate_threshold_type": threshold_type,
            }
            if not any(row[field] is not None for field in LACTATE_FIELDS[2:]):
                continue
            candidates.append((family_order, timestamp or "", sequence, row))

    candidates.sort(key=lambda item: (item[0], item[1], item[2], _stable_row(item[3])))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _family_order, _timestamp, _sequence, row in candidates:
        signature = _stable_row(row)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(row)

    power_by_anchor: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in unique:
        power = row["functional_threshold_power"]
        if power is None:
            continue
        anchor = (
            row["observation_family"],
            row["observation_timestamp"] or "timestamp-unavailable",
        )
        power_by_anchor[anchor].add(json.dumps(power))
    power_conflicts = sum(len(values) > 1 for values in power_by_anchor.values())
    if power_conflicts:
        review_counts["functional_threshold_power_conflict"] += power_conflicts

    return {
        "format": "garmin-running-data-normalizer-lactate-threshold-candidates-v1",
        "status": "REVIEW_REQUIRED_STABLE_PROMOTION_BLOCKED",
        "dataset": "lactate_threshold",
        "public_promotion": False,
        "machine_stable_key_status": "PRODUCT_DECISION_REQUIRED",
        "identity_anchor": "observation_timestamp",
        "sequence_usage": "ordering_only_not_exposed_not_stable_key",
        "observation_families": [item[0] for item in family_patterns],
        "units": {
            "lactate_threshold_speed": "UNCONFIRMED",
            "lactate_threshold_heart_rate": "UNCONFIRMED",
            "functional_threshold_power": "UNCONFIRMED",
        },
        "timezone": "UNCONFIRMED",
        "candidate_count": len(unique),
        "family_asset_counts": dict(sorted(family_asset_counts.items())),
        "family_source_record_counts": dict(sorted(family_source_counts.items())),
        "review_condition_counts": dict(sorted(review_counts.items())),
        "source_paths_exposed": False,
        "source_hashes_exposed": False,
        "private_identifiers_exposed": False,
        "latest_wins": False,
        "inference_performed": False,
        "candidates": unique,
    }


def build_performance_metrics_daily_context(
    hill_rows: Iterable[dict[str, Any]],
    endurance_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for row in hill_rows:
        target = by_date.setdefault(row["calendar_date"], {"calendar_date": row["calendar_date"]})
        for field in HILL_FIELDS[1:]:
            target[f"hill_{field}"] = row.get(field)
    for row in endurance_rows:
        target = by_date.setdefault(row["calendar_date"], {"calendar_date": row["calendar_date"]})
        for field in ENDURANCE_FIELDS[1:]:
            target[f"endurance_{field}"] = row.get(field)
    return [by_date[key] for key in sorted(by_date)]


__all__ = [
    "DailyNormalizationResult",
    "ENDURANCE_FIELDS",
    "HILL_FIELDS",
    "LACTATE_FIELDS",
    "PerformanceMetricsConflictError",
    "PerformanceMetricsError",
    "build_performance_metrics_daily_context",
    "collect_lactate_threshold_candidates",
    "normalize_endurance_score",
    "normalize_hill_score",
]
