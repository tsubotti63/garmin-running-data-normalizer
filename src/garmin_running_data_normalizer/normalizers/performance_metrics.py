from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable

from ..common.time import daily_calendar_date
from ..common.values import INVALID, InvalidValues, ValueReader, read_value
from ..intake.discovery import DiscoveredAsset, parse_json_asset
from .daily_metrics import (
    RowsLeftOut,
    copies_within_snapshots,
    merge_observations,
    observation_weight,
    public_fields,
    snapshot_numbers,
    value_source_names,
)


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
# The source field of each value field (stage A3d-1); the other field is the
# record's key. A row left out that holds nothing in them is an empty record.
HILL_VALUE_SOURCES = {
    "overall_score": ("overallScore",),
    "strength_score": ("strengthScore",),
    "endurance_score": ("enduranceScore",),
    "classification_id": ("hillScoreClassificationId",),
    "feedback_phrase_id": ("hillScoreFeedbackPhraseId",),
}
HILL_FIELDS_WITHOUT_VALUES = ("calendar_date",)
ENDURANCE_VALUE_SOURCES = {
    "overall_score": ("overallScore",),
    "classification": ("classification",),
    "feedback_phrase": ("feedbackPhrase",),
}
ENDURANCE_FIELDS_WITHOUT_VALUES = ("calendar_date",)
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


@dataclass(frozen=True)
class DailyNormalizationResult:
    records: list[dict[str, Any]]
    audit: dict[str, Any]


def _logical_name(asset: DiscoveredAsset) -> str:
    return asset.member_path or asset.source_path


def _basename(asset: DiscoveredAsset) -> str:
    return PurePosixPath(_logical_name(asset)).name.lower()


def _load_json(asset: DiscoveredAsset) -> Any:
    """Return one file's JSON value; a file that cannot be read gives None.

    Such a file is left out with a reason in its reading (stage A3c).
    """
    readable, value = parse_json_asset(asset)
    return value if readable else None


def metric_rows(value: Any) -> list[dict[str, Any]]:
    """Return the records of a performance-metric file, as Run-All and the
    Snapshot build read them: the objects of its top list, of the list that
    its top object holds under ``records``, ``items``, or ``data``, or the top
    object itself."""
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
    """A Hill integer or an Endurance number, as the field takes it (stage
    A3d-2a: 70.0 is the integer 70, and NaN or text is not a number)."""
    return read_value(value, "integer" if integer else "number")[1]


def _left_out_reason(raw: dict[str, Any], *, is_hill: bool) -> str | None:
    if _calendar_date(raw.get("calendarDate")) is None:
        return "missing_or_invalid_calendar_date"
    if _number(raw.get("overallScore"), integer=is_hill) is None:
        return "missing_or_invalid_overall_score"
    return None


def hill_score_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why a Hill Score record is left out, or None when it is kept."""
    return _left_out_reason(raw, is_hill=True)


def endurance_score_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why an Endurance Score record is left out, or None when it is kept."""
    return _left_out_reason(raw, is_hill=False)


def _stable_row(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _normalize_daily(
    assets: Iterable[DiscoveredAsset],
    *,
    dataset: str,
) -> DailyNormalizationResult:
    is_hill = dataset == "hill_score_daily"
    prefix = "hillscore" if is_hill else "endurancescore"
    snapshot_name = f"snapshot_{prefix}.json"
    selected_assets = [
        asset
        for asset in assets
        if asset.kind == "json"
        and (
            _basename(asset).startswith(prefix)
            or _basename(asset) == snapshot_name
        )
    ]
    accepted: list[dict[str, Any]] = []
    left_out = RowsLeftOut(
        value_source_names(HILL_VALUE_SOURCES if is_hill else ENDURANCE_VALUE_SOURCES)
    )
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
        rows = metric_rows(_load_json(asset))
        source_record_count += len(rows)
        for raw in rows:
            excluded_private_fields.update(name for name in private_names if name in raw)
            reason = _left_out_reason(raw, is_hill=is_hill)
            if reason is not None:
                left_out.add(raw, reason)
                continue
            calendar_date = _calendar_date(raw.get("calendarDate"))
            overall = _number(raw.get("overallScore"), integer=is_hill)
            values = ValueReader()
            if is_hill:
                accepted.append(
                    {
                        "_snapshot_numbers": snapshot_numbers(raw),
                        "calendar_date": calendar_date,
                        "overall_score": overall,
                        "strength_score": values.integer(raw.get("strengthScore"), "strength_score"),
                        "endurance_score": values.integer(raw.get("enduranceScore"), "endurance_score"),
                        "classification_id": values.integer(
                            raw.get("hillScoreClassificationId"), "classification_id"
                        ),
                        "feedback_phrase_id": values.integer(
                            raw.get("hillScoreFeedbackPhraseId"), "feedback_phrase_id"
                        ),
                        "_value_problems": values.problems,
                    }
                )
            else:
                accepted.append(
                    {
                        "_snapshot_numbers": snapshot_numbers(raw),
                        "calendar_date": calendar_date,
                        "overall_score": overall,
                        "classification": values.number(raw.get("classification"), "classification"),
                        "feedback_phrase": values.number(raw.get("feedbackPhrase"), "feedback_phrase"),
                        "_value_problems": values.problems,
                    }
                )

    fields = HILL_FIELDS if is_hill else ENDURANCE_FIELDS
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # The values of another form, kept before the rows of a day are merged
    # (stage A3d-2a).
    invalid = InvalidValues()
    for row in accepted:
        rows_by_date[row["calendar_date"]].append(row)
        for field, value in row.get("_value_problems") or ():
            invalid.add(
                {"calendar_date": row["calendar_date"]},
                field,
                value,
                row.get("_snapshot_numbers"),
            )
    normalized: list[dict[str, Any]] = []
    duplicate_count = 0
    copy_count = 0
    disagreements: list[dict[str, Any]] = []
    absent_values: Counter[str] = Counter()
    for calendar_date in sorted(rows_by_date):
        numbers = [row.get("_snapshot_numbers") for row in rows_by_date[calendar_date]]
        rows = [public_fields(row) for row in rows_by_date[calendar_date]]
        signatures = {_stable_row(row) for row in rows}
        # Copies within one Snapshot count as in a one-shot run (stage A3b).
        copies = sum(copies_within_snapshots(items) for items in numbers)
        copy_count += copies
        duplicate_count += len(rows) - len(signatures) + copies
        if len(signatures) == 1:
            row = dict(rows[0])
            row["disagreeing_fields"] = []
            normalized.append(row)
            continue
        merged = merge_observations(
            rows,
            fields,
            key_fields=("calendar_date",),
            snapshots=numbers if any(numbers) else None,
        )
        row = dict(merged.row)
        row["disagreeing_fields"] = list(merged.disagreeing_fields)
        normalized.append(row)
        absent_values.update(merged.absent_values)
        if merged.disagreements:
            disagreements.append(
                {
                    "key": {"calendar_date": calendar_date},
                    "observation_count": sum(observation_weight(item) for item in numbers),
                    "fields": merged.disagreements,
                }
            )
    audit = {
        "format": "garmin-running-data-normalizer-performance-daily-audit-v2",
        "dataset": dataset,
        "status": "PASS",
        "detected_asset_count": len(selected_assets),
        "source_record_count": source_record_count + copy_count + left_out.copy_count,
        "accepted_record_count": len(normalized),
        "excluded_record_count": sum(left_out.reasons.values()),
        "excluded_reason_counts": dict(sorted(left_out.reasons.items())),
        # Rows left out that hold no value: counted apart, and not announced.
        **(
            {"empty_record_count": left_out.empty_record_count}
            if left_out.empty_record_count
            else {}
        ),
        "same_value_duplicate_count": duplicate_count,
        "disagreement_key_count": len(disagreements),
        "disagreements": disagreements,
        "absent_value_counts": dict(sorted(absent_values.items())),
        **invalid.audit_fields(),
        "stable_key": ["calendar_date"],
        "merge_policy": "daily_state_null_is_absent_disagreeing_values_kept_empty",
        "keep_last": False,
        "excluded_private_field_presence_counts": dict(
            sorted(excluded_private_fields.items())
        ),
        "source_paths_exposed": False,
        "source_hashes_exposed": False,
    }
    if left_out.reasons or left_out.empty_record_count:
        audit.update(
            {
                "review_required_count": 0,
                "review_item_count": 0,
            }
        )
    return DailyNormalizationResult(normalized, audit)


def normalize_hill_score(
    assets: Iterable[DiscoveredAsset],
) -> DailyNormalizationResult:
    return _normalize_daily(assets, dataset="hill_score_daily")


def normalize_endurance_score(
    assets: Iterable[DiscoveredAsset],
) -> DailyNormalizationResult:
    return _normalize_daily(assets, dataset="endurance_score_daily")


def _optional_number(
    value: Any,
    review_counts: Counter[str],
    field: str,
    invalid: InvalidValues,
    key: dict[str, Any],
) -> int | float | None:
    """A candidate's number. A value of another form is counted and kept with
    the candidate's key; an empty value is no value (stage A3d-2a)."""
    state, parsed = read_value(value, "number")
    if state == INVALID:
        review_counts[f"invalid_{field}"] += 1
        invalid.add(key, field, value)
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
    invalid = InvalidValues()

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
        rows = metric_rows(_load_json(asset))
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
            key = {"observation_family": family, "observation_timestamp": timestamp}
            row = {
                "observation_timestamp": timestamp,
                "observation_family": family,
                "lactate_threshold_speed": _optional_number(
                    raw.get("lactateThresholdSpeed"),
                    review_counts,
                    "lactate_threshold_speed",
                    invalid,
                    key,
                ),
                "lactate_threshold_heart_rate": _optional_number(
                    raw.get("lactateThresholdHeartRate"),
                    review_counts,
                    "lactate_threshold_heart_rate",
                    invalid,
                    key,
                ),
                "functional_threshold_power": _optional_number(
                    raw.get("functionalThresholdPower"),
                    review_counts,
                    "functional_threshold_power",
                    invalid,
                    key,
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
        **invalid.audit_fields(),
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
    "ENDURANCE_FIELDS_WITHOUT_VALUES",
    "ENDURANCE_VALUE_SOURCES",
    "HILL_FIELDS",
    "HILL_FIELDS_WITHOUT_VALUES",
    "HILL_VALUE_SOURCES",
    "LACTATE_FIELDS",
    "PerformanceMetricsError",
    "build_performance_metrics_daily_context",
    "collect_lactate_threshold_candidates",
    "endurance_score_left_out_reason",
    "hill_score_left_out_reason",
    "metric_rows",
    "normalize_endurance_score",
    "normalize_hill_score",
]
