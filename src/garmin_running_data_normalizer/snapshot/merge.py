from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .. import __version__
from ..common.identity import garmin_activity_key, stable_hash
from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..intake.archive import ArchiveLimits
from .policies import CONTRACT_VERSION, REGISTRY_VERSION
from .store import SnapshotStoreError, load_manifests, load_store, sha256_file
from .store import verify_store


BUILD_FORMAT = "garmin-running-data-normalizer-canonical-snapshot-build-v1"
DATASET_ORDER = (
    "activities",
    "gear",
    "activity_gear",
    "personal_records",
    "hill_score_daily",
    "endurance_score_daily",
    "race_prediction_daily",
    "sleep_daily",
    "uds_daily",
    "acute_training_load_daily",
    "training_readiness_daily",
    "vo2max_daily",
    "training_history_daily",
    "lactate_threshold_candidates",
)
DAILY_FAIL_CLOSED_DATASETS = {
    "hill_score_daily",
    "endurance_score_daily",
    "race_prediction_daily",
    "sleep_daily",
    "uds_daily",
    "acute_training_load_daily",
    "training_readiness_daily",
    "vo2max_daily",
    "training_history_daily",
}
PRESERVE_OBSERVED_VARIANT_DATASETS = {
    "endurance_score_daily",
    "uds_daily",
}
SOURCE_OBSERVATION_DATASETS = {
    "race_prediction_daily",
    "acute_training_load_daily",
    "training_readiness_daily",
    "vo2max_daily",
    "training_history_daily",
}
SCHEMA_VERSION = "garmin-run-all-output:v1.1"
APPROVED_INPUT_MAX_FILE_BYTES = ArchiveLimits().max_member_bytes


class SnapshotMergeError(SnapshotStoreError):
    """Canonical cumulative merge failed closed."""


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_value(value: Any) -> str:
    return _sha256_bytes(_stable_json(value).encode("utf-8"))


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def _write_json(path: Path, value: Any) -> None:
    _write_bytes(path, _json_bytes(value))


def _write_activity_input(
    fitness: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Write deterministic Run-All inputs without weakening intake limits."""

    def payload(partition: list[dict[str, Any]]) -> bytes:
        return _json_bytes([{"summarizedActivitiesExport": partition}])

    complete = payload(rows)
    if len(complete) <= APPROVED_INPUT_MAX_FILE_BYTES:
        _write_bytes(fitness / "snapshot_summarizedActivities.json", complete)
        return

    pending = [rows]
    partitions: list[bytes] = []
    while pending:
        partition = pending.pop(0)
        data = payload(partition)
        if len(data) <= APPROVED_INPUT_MAX_FILE_BYTES:
            partitions.append(data)
            continue
        if len(partition) <= 1:
            raise SnapshotMergeError(
                "canonical Activity record exceeds the intake file-size limit"
            )
        midpoint = len(partition) // 2
        pending[0:0] = [partition[:midpoint], partition[midpoint:]]

    width = max(4, len(str(len(partitions))))
    for index, data in enumerate(partitions, start=1):
        _write_bytes(
            fitness
            / (
                f"snapshot_part_{index:0{width}d}_"
                "summarizedActivities.json"
            ),
            data,
        )


def _read_blob(store: Path, row: dict[str, Any]) -> bytes:
    path = store / str(row["blob_relative_path"])
    if (
        not path.is_file()
        or path.stat().st_size != row["bytes"]
        or sha256_file(path) != row["sha256"]
    ):
        raise SnapshotMergeError("immutable snapshot blob failed verification")
    return path.read_bytes()


def _dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _containers(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _activity_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            rows.extend(_activity_rows(item))
    elif isinstance(value, dict):
        exported = value.get("summarizedActivitiesExport")
        if isinstance(exported, list):
            rows.extend(item for item in exported if isinstance(item, dict))
        elif "activityId" in value:
            rows.append(value)
        else:
            for item in value.values():
                if isinstance(item, (list, dict)):
                    rows.extend(_activity_rows(item))
    return rows


def _activity_key(row: dict[str, Any]) -> str:
    start = row.get("startTimeGmt")
    if start is None:
        start = row.get("beginTimestamp")
    return garmin_activity_key(
        row.get("activityId"),
        start,
        row.get("distance"),
        row.get("duration"),
        row.get("activityType"),
    )


def _gear_key(row: dict[str, Any]) -> int | str | None:
    raw = row.get("gearPk")
    if raw not in (None, ""):
        return raw
    fallback = [row.get("uuid"), row.get("displayName"), row.get("dateBegin")]
    if all(value in (None, "") for value in fallback):
        return None
    return stable_hash(fallback, prefix="garmin_gear_hash:")


def _personal_record_key(row: dict[str, Any]) -> int | str | None:
    raw = row.get("personalRecordId")
    if raw not in (None, ""):
        return raw if isinstance(raw, (int, str)) and not isinstance(raw, bool) else None
    fallback = [
        row.get("activityId"),
        row.get("personalRecordType"),
        row.get("value"),
        row.get("prStartTimeGMT"),
    ]
    if all(value in (None, "") for value in fallback):
        return None
    return stable_hash(fallback, prefix="garmin_personal_record_hash:")


def _metric_row(dataset: str, row: dict[str, Any]) -> dict[str, Any]:
    if dataset == "hill_score_daily":
        fields = (
            "calendarDate",
            "overallScore",
            "strengthScore",
            "enduranceScore",
            "hillScoreClassificationId",
            "hillScoreFeedbackPhraseId",
        )
    else:
        fields = (
            "calendarDate",
            "overallScore",
            "classification",
            "feedbackPhrase",
        )
    return {field: row[field] for field in fields if field in row}


def _daily_source_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("data", "items", "records", "values", "summaries", "sleepData"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _daily_definition(
    logical_name: str,
) -> tuple[str, tuple[str, ...], str | None] | None:
    name = PurePosixPath(logical_name).name.lower()
    definitions = (
        (
            "runracepredictions",
            "race_prediction_daily",
            (
                "calendarDate", "timestamp", "raceTime5K", "raceTime10K",
                "raceTimeHalf", "raceTimeMarathon",
            ),
            None,
        ),
        (
            "sleepdata.json",
            "sleep_daily",
            (
                "calendarDate", "sleepStartTimestampGMT", "sleepEndTimestampGMT",
                "sleepTimeSeconds", "totalSleepSeconds", "deepSleepSeconds",
                "lightSleepSeconds", "remSleepSeconds", "awakeSleepSeconds",
                "sleepScores",
            ),
            None,
        ),
        (
            "udsfile",
            "uds_daily",
            (
                "calendarDate", "date", "totalSteps", "steps", "totalDistanceMeters",
                "distanceMeters", "activeKilocalories", "bmrKilocalories",
                "restingHeartRate", "minHeartRate", "maxHeartRate", "bodyBattery",
                "allDayStress", "bodyBatteryFeedback",
            ),
            None,
        ),
        (
            "metricsacutetrainingload",
            "acute_training_load_daily",
            (
                "calendarDate", "acwrPercent", "acwrStatus", "dailyTrainingLoadAcute",
                "dailyTrainingLoadChronic", "dailyAcuteChronicWorkloadRatio", "timestamp",
            ),
            None,
        ),
        (
            "trainingreadinessdto",
            "training_readiness_daily",
            (
                "calendarDate", "score", "level", "recoveryTime", "acwrFactorPercent",
                "stressHistoryFactorPercent", "hrvFactorPercent",
                "sleepHistoryFactorPercent", "acuteLoad", "hrvWeeklyAverage",
                "validSleep", "sleepScore", "timestamp",
            ),
            None,
        ),
        (
            "activityvo2max",
            "vo2max_daily",
            (
                "calendarDate", "vo2MaxValue", "sport", "maxMet", "maxMetCategory",
                "calibratedData", "vo2MaxSourceSeries", "timestampGmt",
                "observationTimestamp", "activityId",
            ),
            "activity_vo2max_daily",
        ),
        (
            "metricsmaxmetdata",
            "vo2max_daily",
            (
                "calendarDate", "vo2MaxValue", "sport", "maxMet", "maxMetCategory",
                "calibratedData", "vo2MaxSourceSeries", "updateTimestamp",
                "observationTimestamp",
            ),
            "performance_metrics_daily",
        ),
        (
            "snapshot_vo2max",
            "vo2max_daily",
            (
                "calendarDate", "vo2MaxValue", "sport", "maxMet", "maxMetCategory",
                "calibratedData", "vo2MaxSourceSeries", "timestampGmt",
                "updateTimestamp", "observationTimestamp", "activityId",
            ),
            None,
        ),
        (
            "traininghistory",
            "training_history_daily",
            ("calendarDate", "timestamp", "trainingStatus", "sport"),
            None,
        ),
    )
    for marker, dataset, fields, source_series in definitions:
        if marker in name:
            return dataset, fields, source_series
    return None


def _daily_raw_key(
    dataset: str,
    record: dict[str, Any],
    source_series: str | None,
) -> tuple[Any, ...] | None:
    calendar_date = daily_calendar_date(
        record.get("calendarDate") or record.get("date")
    )
    if calendar_date in (None, ""):
        return None
    if dataset not in SOURCE_OBSERVATION_DATASETS:
        return (calendar_date,)

    series = source_series or record.get("vo2MaxSourceSeries")
    if dataset == "vo2max_daily":
        if series == "activity_vo2max_daily":
            raw_timestamp = record.get("timestampGmt")
            semantics = "UTC_SOURCE_FIELD"
        else:
            raw_timestamp = record.get("updateTimestamp")
            semantics = "UNCONFIRMED"
        if raw_timestamp in (None, ""):
            raw_timestamp = record.get("observationTimestamp")
            semantics = "UNCONFIRMED"
        observation_timestamp, _ = normalize_observation_timestamp(
            raw_timestamp,
            naive_timezone_semantics=semantics,
        )
        sport = record.get("sport")
        if series in (None, "") or sport in (None, "") or observation_timestamp is None:
            return None
        return (calendar_date, series, sport, observation_timestamp)

    observation_timestamp, _ = normalize_observation_timestamp(record.get("timestamp"))
    if observation_timestamp is None:
        observation_timestamp, _ = normalize_observation_timestamp(
            record.get("observationTimestamp")
        )
    if observation_timestamp is None:
        return None
    return (calendar_date, observation_timestamp)


def _lactate_family(logical_name: str) -> str | None:
    name = PurePosixPath(logical_name).name.lower()
    for family, suffix in (
        ("history", "userbiometrics.json"),
        ("latest_snapshot", "biometrics_latest.json"),
        ("profile_state", "userbiometricprofiledata.json"),
        ("derived_evidence", "heartratezones.json"),
    ):
        if name.endswith(suffix):
            return family
    return None


def _lactate_row(family: str, row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "lactateThresholdSpeed",
        "lactateThresholdHeartRate",
        "functionalThresholdPower",
    )
    result = {field: row[field] for field in fields if field in row}
    if family == "history":
        metadata = row.get("metaData")
        if isinstance(metadata, dict):
            result["metaData"] = {
                field: metadata[field]
                for field in ("calendarDate", "sequence")
                if field in metadata
            }
    elif family == "derived_evidence" and "trainingMethod" in row:
        result["trainingMethod"] = row["trainingMethod"]
    return result


def _dataset_records(
    logical_name: str,
    payload: Any,
) -> list[tuple[str, str, dict[str, Any], tuple[Any, ...] | None]]:
    lower = logical_name.lower()
    result: list[tuple[str, str, dict[str, Any], tuple[Any, ...] | None]] = []
    if lower.endswith("summarizedactivities.json"):
        for index, row in enumerate(_activity_rows(payload)):
            try:
                key: tuple[Any, ...] | None = (_activity_key(row),)
            except ValueError:
                key = None
            result.append(("activities", str(index), row, key))
    elif lower.endswith("gear.json"):
        for container_index, container in enumerate(_containers(payload)):
            for index, row in enumerate(_dict_rows(container.get("gearDTOS"))):
                gear_key = _gear_key(row)
                result.append(
                    (
                        "gear",
                        f"{container_index}:{index}",
                        row,
                        None if gear_key is None else (gear_key,),
                    )
                )
            links = container.get("gearActivityDTOs")
            if isinstance(links, dict):
                for gear_key in sorted(links, key=str):
                    for index, row in enumerate(_dict_rows(links[gear_key])):
                        link_record = {**row, "gearPk": gear_key}
                        activity_id = link_record.get("activityId")
                        key = (
                            None
                            if gear_key in (None, "") or activity_id in (None, "")
                            else (gear_key, activity_id)
                        )
                        result.append(
                            (
                                "activity_gear",
                                f"{container_index}:{gear_key}:{index}",
                                link_record,
                                key,
                            )
                        )
    elif lower.endswith("personalrecord.json"):
        for container_index, container in enumerate(_containers(payload)):
            for index, row in enumerate(_dict_rows(container.get("personalRecords"))):
                record_key = _personal_record_key(row)
                result.append(
                    (
                        "personal_records",
                        f"{container_index}:{index}",
                        row,
                        None if record_key is None else (record_key,),
                    )
                )
    elif PurePosixPath(lower).name.startswith("hillscore"):
        for index, row in enumerate(_containers(payload)):
            record = _metric_row("hill_score_daily", row)
            calendar_date = daily_calendar_date(record.get("calendarDate"))
            if calendar_date is not None:
                record["calendarDate"] = calendar_date
            result.append(
                (
                    "hill_score_daily",
                    str(index),
                    record,
                    None if calendar_date in (None, "") else (calendar_date,),
                )
            )
    elif PurePosixPath(lower).name.startswith("endurancescore"):
        for index, row in enumerate(_containers(payload)):
            record = _metric_row("endurance_score_daily", row)
            calendar_date = daily_calendar_date(record.get("calendarDate"))
            if calendar_date is not None:
                record["calendarDate"] = calendar_date
            result.append(
                (
                    "endurance_score_daily",
                    str(index),
                    record,
                    None if calendar_date in (None, "") else (calendar_date,),
                )
            )
    elif (definition := _daily_definition(logical_name)) is not None:
        dataset, fields, source_series = definition
        for index, row in enumerate(_daily_source_rows(payload)):
            record = {field: row[field] for field in fields if field in row}
            if source_series is not None and "vo2MaxSourceSeries" not in record:
                record["vo2MaxSourceSeries"] = source_series
            calendar_date = daily_calendar_date(record.get("calendarDate") or record.get("date"))
            if calendar_date is not None:
                record["calendarDate"] = calendar_date
            raw_key = _daily_raw_key(dataset, record, source_series)
            result.append(
                (
                    dataset,
                    str(index),
                    record,
                    raw_key,
                )
            )
    else:
        lactate_family = _lactate_family(logical_name)
        if lactate_family is not None:
            for index, row in enumerate(_containers(payload)):
                record = _lactate_row(lactate_family, row)
                measurement_fields = set(record) - {"metaData"}
                if not measurement_fields:
                    continue
                result.append(
                    (
                        "lactate_threshold_candidates",
                        str(index),
                        record,
                        (lactate_family, _stable_json(record)),
                    )
                )
    return result


def _value_state(value: Any) -> str:
    if value is None:
        return "explicit_null"
    if value == "" or value == [] or value == {}:
        return "explicit_empty"
    return "explicit_value"


def _lactate_power_conflicts(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for observation in observations:
        raw_key = observation.get("raw_key")
        family = str(raw_key[0]) if isinstance(raw_key, tuple) and raw_key else "unknown"
        record = observation.get("record", {})
        if not isinstance(record, dict):
            continue
        power = record.get("functionalThresholdPower")
        if power is None:
            continue
        timestamp = "timestamp-unavailable"
        metadata = record.get("metaData")
        if isinstance(metadata, dict) and metadata.get("calendarDate") not in (None, ""):
            timestamp = str(metadata["calendarDate"])
        grouped[(family, timestamp)].add(_stable_json(power))
    return [
        {
            "severity": "stop",
            "conflict_type": "lactate_functional_threshold_power_conflict",
            "dataset": "lactate_threshold_candidates",
            "observation_family": family,
            "observation_timestamp": timestamp,
        }
        for (family, timestamp), values in sorted(grouped.items())
        if len(values) > 1
    ]


def _canonical_key(dataset: str, values: tuple[Any, ...]) -> str:
    if dataset == "activities":
        return str(values[0])
    return f"{dataset}:{_sha256_value(list(values))}"


def _reappeared(bits: str) -> bool:
    first = bits.find("1")
    last = bits.rfind("1")
    return first >= 0 and last > first and "0" in bits[first:last]


def _merge_dataset(
    dataset: str,
    observations: list[dict[str, Any]],
    snapshot_count: int,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    holds: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    field_provenance: list[dict[str, Any]] = []
    for observation in observations:
        raw_key = observation["raw_key"]
        if raw_key is None or any(value in (None, "") for value in raw_key):
            holds.append(
                {
                    "hold_type": "null_stable_key",
                    "dataset": dataset,
                    "snapshot_id": observation["snapshot_id"],
                    "source_relative_path": observation["source_relative_path"],
                    "source_record_index": observation["source_record_index"],
                    "parser_state": "explicit_value",
                }
            )
            continue
        groups[_canonical_key(dataset, raw_key)].append(observation)

    canonical: list[dict[str, Any]] = []
    pattern_counts: Counter[str] = Counter()
    previous_only = 0
    new = 0
    reappeared = 0
    changed = 0
    updated_fields = 0
    state_counts: Counter[str] = Counter()
    observed_variants: list[dict[str, Any]] = []
    single_variant_key_count = 0
    multi_variant_key_count = 0
    observed_variant_count = 0
    exact_repeat_count = 0
    for key in sorted(groups):
        group = groups[key]
        by_snapshot: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for observation in group:
            by_snapshot[int(observation["logical_order"])].append(observation)
        for logical_order, rows in by_snapshot.items():
            signatures = {_stable_json(item["record"]) for item in rows}
            if len(signatures) > 1:
                conflicts.append(
                    {
                        "severity": "stop",
                        "conflict_type": "divergent_duplicate_within_snapshot",
                        "dataset": dataset,
                        "canonical_key": key,
                        "logical_order": logical_order,
                    }
                )
        by_observed_at: dict[str, set[str]] = defaultdict(set)
        for observation in group:
            by_observed_at[str(observation["export_observed_at"])].add(
                _stable_json(observation["record"])
            )
        for observed_at, signatures in by_observed_at.items():
            if len(signatures) > 1 and len(
                {
                    item["snapshot_id"]
                    for item in group
                    if item["export_observed_at"] == observed_at
                }
            ) > 1:
                conflicts.append(
                    {
                        "severity": "stop",
                        "conflict_type": "same_observation_time_different_value",
                        "dataset": dataset,
                        "canonical_key": key,
                        "export_observed_at": observed_at,
                    }
                )
        if conflicts and conflicts[-1].get("canonical_key") == key:
            continue

        ordered = sorted(
            group,
            key=lambda item: (
                int(item["logical_order"]),
                str(item["snapshot_id"]),
                str(item["source_relative_path"]),
                str(item["source_record_index"]),
            ),
        )
        distinct_signatures = {_stable_json(item["record"]) for item in ordered}
        if dataset in DAILY_FAIL_CLOSED_DATASETS and len(distinct_signatures) > 1:
            if dataset in PRESERVE_OBSERVED_VARIANT_DATASETS:
                multi_variant_key_count += 1
                observed_variant_count += len(distinct_signatures)
                exact_repeat_count += len(ordered) - len(distinct_signatures)
                by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for observation in ordered:
                    by_signature[_stable_json(observation["record"])].append(observation)
                for signature in sorted(by_signature):
                    variant_rows = by_signature[signature]
                    observed_variants.append(
                        {
                            "canonical_key": key,
                            "variant_fingerprint": _sha256_value(variant_rows[0]["record"]),
                            "observed_value": variant_rows[0]["record"],
                            "observation_count": len(variant_rows),
                            "snapshot_orders": sorted(
                                {int(item["logical_order"]) for item in variant_rows}
                            ),
                            "variant_status": "observed_variant",
                            "canonical_status": "unresolved_multiple_observed_values",
                        }
                    )
                continue
            conflicts.append(
                {
                    "severity": "stop",
                    "conflict_type": "same_stable_key_different_public_value",
                    "dataset": dataset,
                    "canonical_key": key,
                }
            )
            continue
        if len(distinct_signatures) == 1:
            single_variant_key_count += 1
            exact_repeat_count += len(ordered) - 1
            observed_variant_count += 1
        bits = "".join(
            "1" if logical_order in by_snapshot else "0"
            for logical_order in range(1, snapshot_count + 1)
        )
        pattern_counts[bits] += 1
        state_counts["record_absent"] += bits.count("0")
        if bits.endswith("0") and "1" in bits:
            previous_only += 1
        if bits.endswith("1") and "1" not in bits[:-1]:
            new += 1
        if _reappeared(bits):
            reappeared += 1

        merged: dict[str, Any] = {}
        selected: dict[str, dict[str, Any]] = {}
        field_universe = set().union(
            *(set(item["record"]) for item in ordered)
        )
        for observation in ordered:
            state_counts["field_absent"] += len(
                field_universe - set(observation["record"])
            )
            for value in observation["record"].values():
                state_counts[_value_state(value)] += 1
        if len(distinct_signatures) > 1:
            changed += 1
        for observation in ordered:
            for field in sorted(observation["record"]):
                value = observation["record"][field]
                state = _value_state(value)
                if state in {"explicit_null", "explicit_empty"}:
                    preserves_previous = (
                        field in merged
                        and _value_state(merged[field]) == "explicit_value"
                    )
                    holds.append(
                        {
                            "hold_type": (
                                f"{state}_preserved_previous"
                                if preserves_previous
                                else f"{state}_review_required"
                            ),
                            "dataset": dataset,
                            "canonical_key": key,
                            "field_name": field,
                            "snapshot_id": observation["snapshot_id"],
                            "source_relative_path": observation["source_relative_path"],
                            "source_record_index": observation["source_record_index"],
                            "parser_state": state,
                            "prior_explicit_value_preserved": preserves_previous,
                        }
                    )
                    if preserves_previous:
                        continue
                if field in merged and _stable_json(merged[field]) != _stable_json(value):
                    updated_fields += 1
                merged[field] = value
                selected[field] = observation
        canonical.append(
            {
                "canonical_key": key,
                "raw_record": merged,
                "presence_pattern": bits,
                "source_snapshot_count": len(by_snapshot),
                "source_observation_count": len(ordered),
            }
        )
        for observation in ordered:
            provenance.append(
                {
                    "dataset": dataset,
                    "canonical_key": key,
                    "snapshot_id": observation["snapshot_id"],
                    "logical_order": observation["logical_order"],
                    "source_relative_path": observation["source_relative_path"],
                    "source_record_index": observation["source_record_index"],
                    "source_object_sha256": observation["source_object_sha256"],
                    "record_sha256": _sha256_value(observation["record"]),
                    "field_presence": sorted(observation["record"]),
                    "merge_disposition": (
                        "field_contributor"
                        if observation in selected.values()
                        else "exact_duplicate"
                        if sum(
                            _stable_json(item["record"])
                            == _stable_json(observation["record"])
                            for item in ordered
                        )
                        > 1
                        else "superseded_record"
                    ),
                }
            )
        for field in sorted(selected):
            observation = selected[field]
            field_provenance.append(
                {
                    "dataset": dataset,
                    "canonical_key": key,
                    "field_name": field,
                    "value_state": _value_state(merged[field]),
                    "selected_value_sha256": _sha256_value(merged[field]),
                    "snapshot_id": observation["snapshot_id"],
                    "logical_order": observation["logical_order"],
                    "source_relative_path": observation["source_relative_path"],
                    "source_record_index": observation["source_record_index"],
                }
            )

    summary = {
        "source_observation_count": len(observations),
        "canonical_record_count": len(canonical),
        "null_key_hold_count": sum(
            item["dataset"] == dataset and item["hold_type"] == "null_stable_key"
            for item in holds
        ),
        "previous_only_retained_count": previous_only,
        "new_record_count": new,
        "reappeared_record_count": reappeared,
        "changed_record_count": changed,
        "updated_field_count": updated_fields,
        "presence_pattern_counts": dict(sorted(pattern_counts.items())),
        "presence_state_counts": dict(sorted(state_counts.items())),
        "automatic_deletion": False,
        "inference_performed": False,
    }
    if dataset in PRESERVE_OBSERVED_VARIANT_DATASETS:
        summary.update(
            {
                "single_variant_key_count": single_variant_key_count,
                "multi_variant_key_count": multi_variant_key_count,
                "observed_variant_count": observed_variant_count,
                "exact_repeat_count": exact_repeat_count,
                "malformed_count": summary["null_key_hold_count"],
                "canonicalization_unresolved_count": multi_variant_key_count,
                "automatic_winner": False,
                "observed_variants": sorted(
                    observed_variants,
                    key=lambda item: (
                        str(item["canonical_key"]),
                        str(item["variant_fingerprint"]),
                    ),
                ),
                "variant_policy": "preserve_observed_variants_fail_closed_canonicalization",
            }
        )
    return canonical, provenance, field_provenance, holds, conflicts, summary


def _validation_matrix(
    observations_by_dataset: dict[str, list[dict[str, Any]]],
    snapshot_count: int,
) -> dict[str, Any]:
    prefixes: list[dict[str, Any]] = []
    pairwise: list[dict[str, Any]] = []
    leave_one_out: list[dict[str, Any]] = []
    keys_by_dataset_snapshot: dict[str, dict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for dataset, observations in observations_by_dataset.items():
        for item in observations:
            if item["raw_key"] is None:
                continue
            keys_by_dataset_snapshot[dataset][int(item["logical_order"])].add(
                _canonical_key(dataset, item["raw_key"])
            )
    for prefix in range(1, snapshot_count + 1):
        prefixes.append(
            {
                "prefix_snapshot_count": prefix,
                "dataset_canonical_counts": {
                    dataset: len(
                        set().union(
                            *(
                                by_snapshot[index]
                                for index in range(1, prefix + 1)
                            )
                        )
                    )
                    for dataset, by_snapshot in sorted(keys_by_dataset_snapshot.items())
                },
            }
        )
    for left in range(1, snapshot_count + 1):
        for right in range(left + 1, snapshot_count + 1):
            dataset_counts = {}
            for dataset, by_snapshot in sorted(keys_by_dataset_snapshot.items()):
                left_keys = by_snapshot[left]
                right_keys = by_snapshot[right]
                dataset_counts[dataset] = {
                    "left": len(left_keys),
                    "right": len(right_keys),
                    "overlap": len(left_keys & right_keys),
                    "left_only": len(left_keys - right_keys),
                    "right_only": len(right_keys - left_keys),
                }
            pairwise.append(
                {
                    "left_logical_order": left,
                    "right_logical_order": right,
                    "datasets": dataset_counts,
                }
            )
    for omitted in range(1, snapshot_count + 1):
        contributions = {}
        for dataset, by_snapshot in sorted(keys_by_dataset_snapshot.items()):
            all_keys = set().union(*by_snapshot.values())
            remaining = set().union(
                *(
                    values
                    for index, values in by_snapshot.items()
                    if index != omitted
                )
            )
            contributions[dataset] = len(all_keys - remaining)
        leave_one_out.append(
            {
                "omitted_logical_order": omitted,
                "unique_contribution_by_dataset": contributions,
            }
        )
    return {
        "prefixes": prefixes,
        "pairwise": pairwise,
        "leave_one_out": leave_one_out,
    }


def _latest_relationship_state(
    observations_by_dataset: dict[str, list[dict[str, Any]]],
    snapshot_count: int,
) -> dict[str, list[str]]:
    """Return only the latest Export endpoint identities for validation.

    The cumulative approved input remains the validation record set. These
    latest-only sets let the relationship classifier distinguish an endpoint
    retained from an earlier authoritative Snapshot from one present in the
    current Export without inferring any identity.
    """

    latest = {
        dataset: [
            item
            for item in observations
            if int(item["logical_order"]) == snapshot_count
        ]
        for dataset, observations in observations_by_dataset.items()
    }
    activity_ids = {
        str(item["record"].get("activityId"))
        for item in latest.get("activities", [])
        if item["record"].get("activityId") not in (None, "")
    }
    gear_keys = {
        str(item["record"].get("gearPk"))
        for item in latest.get("gear", [])
        if item["record"].get("gearPk") not in (None, "")
    }
    return {
        "current_activity_ids": sorted(activity_ids),
        "current_gear_keys": sorted(gear_keys),
    }


def _approved_input_inventory(root: Path) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        rows.append(
            {
                "relative_path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows, _sha256_value(rows)


def build_approved_input(
    store_root: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    verification = verify_store(store_root)
    if verification["status"] != "PASS":
        raise SnapshotMergeError("snapshot store verification failed")
    store, store_metadata = load_store(store_root)
    verification_failures: list[str] = []
    manifests = load_manifests(store)
    if not manifests:
        raise SnapshotMergeError("snapshot store has no registered snapshots")
    requested_output = Path(output_root)
    if requested_output.is_symlink():
        raise SnapshotMergeError("canonical build output must not be a symbolic link")
    output = requested_output.resolve()
    if output.exists():
        raise SnapshotMergeError("canonical build output must not already exist")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.snapshot-build-", dir=output.parent)
    )
    try:
        observations_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
        parser_states: Counter[str] = Counter()
        unknown_object_count = 0
        unknown_families: set[str] = set()
        fit_aliases: list[dict[str, Any]] = []
        fit_unique: dict[str, dict[str, Any]] = {}
        unknown_aliases: list[dict[str, Any]] = []
        unknown_unique: dict[str, dict[str, Any]] = {}
        for logical_order, manifest in enumerate(manifests, start=1):
            for source in manifest["objects"]:
                extension = str(source.get("extension", "")).lower()
                object_kind = source.get("object_kind")
                logical_name = str(source["relative_path"])
                if extension == ".fit":
                    digest = str(source["sha256"])
                    fit_unique.setdefault(digest, source)
                    fit_aliases.append(
                        {
                            "fit_blob_sha256": digest,
                            "snapshot_id": manifest["snapshot_id"],
                            "logical_order": logical_order,
                            "source_relative_path": logical_name,
                            "source_object_sha256": source["sha256"],
                        }
                    )
                    parser_states["explicit_value"] += 1
                    continue
                if extension == ".zip" and object_kind == "file":
                    # The immutable Store preserves the archive container. Its
                    # validated members are materialized individually so the
                    # current discovery layer does not parse the same payload
                    # twice through a copied container.
                    parser_states["explicit_value"] += 1
                    continue
                if extension != ".json" or (
                    object_kind == "file"
                    and source.get("container_relative_path") is not None
                ):
                    unknown_object_count += 1
                    unknown_families.add(
                        str(source.get("source_family", "unknown"))
                    )
                    parser_states["parser_unsupported"] += 1
                    digest = str(source["sha256"])
                    unknown_unique.setdefault(digest, source)
                    unknown_aliases.append(
                        {
                            "object_sha256": digest,
                            "snapshot_id": manifest["snapshot_id"],
                            "logical_order": logical_order,
                            "source_relative_path": logical_name,
                            "parser_state": "parser_unsupported",
                        }
                    )
                    continue
                try:
                    value = json.loads(_read_blob(store, source).decode("utf-8-sig"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    parser_states["extraction_failed"] += 1
                    verification_failures.append("supported_json_extraction_failed")
                    continue
                extracted = _dataset_records(logical_name, value)
                if not extracted:
                    unknown_object_count += 1
                    unknown_families.add(
                        str(source.get("source_family", "unknown"))
                    )
                    parser_states["parser_unsupported"] += 1
                    digest = str(source["sha256"])
                    unknown_unique.setdefault(digest, source)
                    unknown_aliases.append(
                        {
                            "object_sha256": digest,
                            "snapshot_id": manifest["snapshot_id"],
                            "logical_order": logical_order,
                            "source_relative_path": logical_name,
                            "parser_state": "parser_unsupported",
                        }
                    )
                    continue
                parser_states["explicit_value"] += 1
                for dataset, record_index, record, raw_key in extracted:
                    observations_by_dataset[dataset].append(
                        {
                            "dataset": dataset,
                            "record": record,
                            "raw_key": raw_key,
                            "snapshot_id": manifest["snapshot_id"],
                            "logical_order": logical_order,
                            "export_observed_at": manifest["export_observed_at"],
                            "source_relative_path": logical_name,
                            "source_record_index": record_index,
                            "source_object_sha256": source["sha256"],
                        }
                    )
        if verification_failures:
            raise SnapshotMergeError("supported source extraction failed")

        canonical_by_dataset: dict[str, list[dict[str, Any]]] = {}
        all_provenance: list[dict[str, Any]] = []
        all_field_provenance: list[dict[str, Any]] = []
        all_holds: list[dict[str, Any]] = []
        all_conflicts: list[dict[str, Any]] = _lactate_power_conflicts(
            observations_by_dataset.get("lactate_threshold_candidates", [])
        )
        dataset_summaries: dict[str, Any] = {}
        for dataset in DATASET_ORDER:
            (
                canonical,
                provenance,
                field_provenance,
                holds,
                conflicts,
                summary,
            ) = _merge_dataset(
                dataset,
                observations_by_dataset.get(dataset, []),
                len(manifests),
            )
            canonical_by_dataset[dataset] = canonical
            all_provenance.extend(provenance)
            all_field_provenance.extend(field_provenance)
            all_holds.extend(holds)
            all_conflicts.extend(conflicts)
            dataset_summaries[dataset] = summary
        if all_conflicts:
            _write_json(stage / "canonical/review_holds.json", all_holds + all_conflicts)
            raise SnapshotMergeError("canonical merge contains unresolved stop conflicts")
        if not canonical_by_dataset["activities"]:
            raise SnapshotMergeError("canonical input contains no Activities records")

        approved = stage / "approved_input"
        fitness = approved / "DI-Connect-Fitness"
        uploaded = approved / "DI-Connect-Uploaded-Files"
        metrics = approved / "DI-Connect-Metrics"
        sleep_source = approved / "DI-Connect-Wellness"
        aggregator = approved / "DI-Connect-Aggregator"
        lactate_source = sleep_source
        activity_rows = [
            item["raw_record"] for item in canonical_by_dataset["activities"]
        ]
        _write_activity_input(fitness, activity_rows)
        gear_rows = [item["raw_record"] for item in canonical_by_dataset["gear"]]
        link_rows = [
            item["raw_record"] for item in canonical_by_dataset["activity_gear"]
        ]
        if gear_rows or link_rows:
            links_by_gear: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in link_rows:
                gear_key = row.get("gearPk")
                if gear_key in (None, ""):
                    continue
                links_by_gear[str(gear_key)].append(row)
            _write_json(
                fitness / "snapshot_gear.json",
                [{"gearDTOS": gear_rows, "gearActivityDTOs": dict(links_by_gear)}],
            )
        personal_rows = [
            item["raw_record"]
            for item in canonical_by_dataset["personal_records"]
        ]
        if personal_rows:
            _write_json(
                fitness / "snapshot_personalRecord.json",
                [{"personalRecords": personal_rows}],
            )
        hill_rows = [
            item["raw_record"]
            for item in canonical_by_dataset["hill_score_daily"]
        ]
        if hill_rows:
            _write_json(metrics / "snapshot_HillScore.json", hill_rows)
        endurance_rows = [
            item["raw_record"]
            for item in canonical_by_dataset["endurance_score_daily"]
        ]
        if endurance_rows:
            _write_json(metrics / "snapshot_EnduranceScore.json", endurance_rows)
        daily_materialization = {
            "race_prediction_daily": (metrics, "RunRacePredictions_snapshot.json"),
            "sleep_daily": (sleep_source, "snapshot_sleepData.json"),
            "uds_daily": (aggregator, "UDSFile_snapshot.json"),
            "acute_training_load_daily": (
                metrics,
                "MetricsAcuteTrainingLoad_snapshot.json",
            ),
            "training_readiness_daily": (
                metrics,
                "TrainingReadinessDTO_snapshot.json",
            ),
            "vo2max_daily": (metrics, "snapshot_vo2max.json"),
            "training_history_daily": (metrics, "TrainingHistory_snapshot.json"),
        }
        for dataset, (directory, filename) in daily_materialization.items():
            rows = [item["raw_record"] for item in canonical_by_dataset[dataset]]
            if rows:
                _write_json(directory / filename, rows)
        lactate_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in canonical_by_dataset["lactate_threshold_candidates"]:
            raw_record = item["raw_record"]
            raw_key = item["canonical_key"]
            family = next(
                (
                    str(observation["raw_key"][0])
                    for observation in observations_by_dataset[
                        "lactate_threshold_candidates"
                    ]
                    if _canonical_key(
                        "lactate_threshold_candidates",
                        observation["raw_key"],
                    )
                    == raw_key
                ),
                "unknown",
            )
            lactate_rows[family].append(raw_record)
        lactate_names = {
            "history": "snapshot_userBioMetrics.json",
            "latest_snapshot": "snapshot_bioMetrics_latest.json",
            "profile_state": "snapshot_userBioMetricProfileData.json",
            "derived_evidence": "snapshot_heartRateZones.json",
        }
        for family, rows in sorted(lactate_rows.items()):
            if family in lactate_names and rows:
                _write_json(lactate_source / lactate_names[family], rows)
        for digest, source in sorted(fit_unique.items()):
            destination = uploaded / f"snapshot_fit_{digest}.fit"
            destination.parent.mkdir(parents=True, exist_ok=True)
            blob = store / str(source["blob_relative_path"])
            if sha256_file(blob) != digest:
                raise SnapshotMergeError("cumulative FIT blob failed verification")
            shutil.copyfile(blob, destination)
        for digest, source in sorted(unknown_unique.items()):
            suffix = str(source.get("extension", "")).lower()
            if not suffix.startswith(".") or len(suffix) > 16:
                suffix = ".bin"
            destination = approved / "preserved_unknown" / f"object_{digest}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            blob = store / str(source["blob_relative_path"])
            if sha256_file(blob) != digest:
                raise SnapshotMergeError("preserved unknown blob failed verification")
            shutil.copyfile(blob, destination)

        approved_inventory, approved_hash = _approved_input_inventory(approved)
        canonical_records = {
            dataset: [
                {
                    "canonical_key": item["canonical_key"],
                    "raw_record_sha256": _sha256_value(item["raw_record"]),
                    "presence_pattern": item["presence_pattern"],
                }
                for item in rows
            ]
            + [
                {
                    "variant_fingerprint": item["variant_fingerprint"],
                    "canonical_key": item["canonical_key"],
                    "snapshot_orders": item["snapshot_orders"],
                }
                for item in dataset_summaries[dataset].get("observed_variants", [])
            ]
            for dataset, rows in canonical_by_dataset.items()
        }
        build_hash = _sha256_value(
            {
                "account_store_id": store_metadata["account_store_id"],
                "snapshot_content_ids": [
                    manifest["snapshot_content_id"] for manifest in manifests
                ],
                "policy_registry_version": REGISTRY_VERSION,
                "parser_version": __version__,
                "schema_version": SCHEMA_VERSION,
                "canonical_records": canonical_records,
                "fit_blob_sha256": sorted(fit_unique),
            }
        )
        lineage = {
            "format": "garmin-running-data-normalizer-snapshot-lineage-v1",
            "contract_version": CONTRACT_VERSION,
            "policy_registry_version": REGISTRY_VERSION,
            "parser_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "account_store_id": store_metadata["account_store_id"],
            "snapshot_count": len(manifests),
            "snapshots": [
                {
                    "snapshot_id": manifest["snapshot_id"],
                    "snapshot_label": manifest["snapshot_label"],
                    "logical_order": index,
                    "export_observed_at": manifest["export_observed_at"],
                    "snapshot_content_id": manifest["snapshot_content_id"],
                }
                for index, manifest in enumerate(manifests, start=1)
            ],
            "canonical_build_sha256": build_hash,
        }
        field_state_counts = {
            state: int(parser_states.get(state, 0))
            + sum(
                int(summary["presence_state_counts"].get(state, 0))
                for summary in dataset_summaries.values()
            )
            for state in (
                "record_absent",
                "field_absent",
                "explicit_null",
                "explicit_empty",
                "explicit_value",
                "parser_unsupported",
                "extraction_failed",
            )
        }
        explicit_null_review_count = sum(
            item.get("parser_state") == "explicit_null" for item in all_holds
        )
        explicit_empty_review_count = sum(
            item.get("parser_state") == "explicit_empty" for item in all_holds
        )
        coverage_gap_count = (
            field_state_counts["record_absent"]
            + field_state_counts["field_absent"]
        )
        aggregate_summary = {
            "format": "garmin-running-data-normalizer-snapshot-merge-summary-v1",
            "snapshot_count": len(manifests),
            "datasets": dataset_summaries,
            "snapshot_labels": [
                manifest["snapshot_label"] for manifest in manifests
            ],
            "snapshot_observed_range": {
                "first": manifests[0]["export_observed_at"],
                "last": manifests[-1]["export_observed_at"],
            },
            "policy_registry_version": REGISTRY_VERSION,
            "parser_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "fit": {
                "source_alias_count": len(fit_aliases),
                "unique_blob_count": len(fit_unique),
                "duplicate_alias_count": len(fit_aliases) - len(fit_unique),
                "decode_contract": "one_decode_per_unique_content",
                "sessions_laps_regenerated_by_current_parser": True,
                "activity_fit_links_regenerated": True,
            },
            "review_hold_count": len(all_holds),
            "review_hold_type_counts": dict(
                sorted(Counter(item["hold_type"] for item in all_holds).items())
            ),
            "explicit_null_review_count": explicit_null_review_count,
            "explicit_empty_review_count": explicit_empty_review_count,
            "stop_conflict_count": 0,
            "coverage_gap_count": coverage_gap_count,
            "unknown_or_unsupported_object_count": unknown_object_count,
            "unknown_or_unsupported_unique_blob_count": len(unknown_unique),
            "unknown_or_unsupported_families": sorted(unknown_families),
            "field_state_counts": dict(sorted(field_state_counts.items())),
            "canonical_completeness_boundary": (
                "registered complete exports only; unsupported or failed "
                "observations are preserved but not promoted"
            ),
            "automatic_deletion": False,
            "inference_performed": False,
        }
        coverage = {
            "format": "garmin-running-data-normalizer-snapshot-coverage-v1",
            "snapshot_count": len(manifests),
            "datasets": dataset_summaries,
            "validation_matrix": _validation_matrix(
                observations_by_dataset,
                len(manifests),
            ),
            "field_state_counts": dict(sorted(field_state_counts.items())),
            "explicit_null_review_count": explicit_null_review_count,
            "explicit_empty_review_count": explicit_empty_review_count,
            "coverage_gap_count": coverage_gap_count,
            "unknown_or_unsupported_object_count": unknown_object_count,
            "unknown_or_unsupported_families": sorted(unknown_families),
            "canonical_completeness_boundary": (
                "registered complete exports only; unsupported or failed "
                "observations are preserved but not promoted"
            ),
        }
        approved_manifest = {
            "format": "garmin-running-data-normalizer-approved-input-manifest-v1",
            "contract_version": CONTRACT_VERSION,
            "policy_registry_version": REGISTRY_VERSION,
            "parser_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "snapshot_count": len(manifests),
            "canonical_build_sha256": build_hash,
            "deterministic_content_sha256": approved_hash,
            "deterministic_content_scope": (
                "approved input payload files before lifecycle control files"
            ),
            "files": approved_inventory,
            "automatic_deletion": False,
            "inference_performed": False,
        }
        merge_manifest = {
            "format": BUILD_FORMAT,
            "contract_version": CONTRACT_VERSION,
            "policy_registry_version": REGISTRY_VERSION,
            "parser_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "snapshot_count": len(manifests),
            "canonical_build_sha256": build_hash,
            "approved_input_content_sha256": approved_hash,
            "approved_input_content_scope": (
                "approved input payload files before lifecycle control files"
            ),
            "dataset_summaries": dataset_summaries,
            "fit_unique_blob_count": len(fit_unique),
            "review_hold_count": len(all_holds),
            "stop_conflict_count": 0,
            "automatic_deletion": False,
            "inference_performed": False,
        }
        _write_json(stage / "canonical/snapshot_lineage.json", lineage)
        _write_json(stage / "canonical/snapshot_coverage.json", coverage)
        _write_json(stage / "canonical/canonical_delta.json", aggregate_summary)
        _write_json(stage / "canonical/snapshot_delta_report.json", aggregate_summary)
        _write_json(
            stage / "canonical/presence_pattern_report.json",
            {
                "format": "garmin-running-data-normalizer-presence-pattern-report-v1",
                "snapshot_count": len(manifests),
                "datasets": {
                    dataset: summary["presence_pattern_counts"]
                    for dataset, summary in dataset_summaries.items()
                },
                "automatic_deletion": False,
            },
        )
        _write_json(stage / "canonical/record_provenance.json", all_provenance)
        _write_json(
            stage / "canonical/field_provenance.json",
            all_field_provenance,
        )
        _write_json(stage / "canonical/review_holds.json", all_holds)
        _write_json(stage / "canonical/fit_blob_aliases.json", fit_aliases)
        _write_json(stage / "canonical/preserved_unknown_aliases.json", unknown_aliases)
        _write_json(stage / "canonical/approved_input_manifest.json", approved_manifest)
        _write_json(stage / "canonical/snapshot_merge_manifest.json", merge_manifest)
        _write_json(stage / "canonical/canonical_merge_manifest.json", merge_manifest)
        _write_json(approved / "approved_input_manifest.json", approved_manifest)
        _write_json(approved / "snapshot_lineage.json", lineage)
        _write_json(approved / "merge_summary.json", aggregate_summary)
        stage.rename(output)
        return {
            "status": "PASS",
            "snapshot_count": len(manifests),
            "canonical_build_sha256": build_hash,
            "approved_input_content_sha256": approved_hash,
            "approved_input": "approved_input",
            "lineage": lineage,
            "coverage": coverage,
            "merge_summary": aggregate_summary,
            "relationship_context": _latest_relationship_state(
                observations_by_dataset,
                len(manifests),
            ),
        }
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


__all__ = [
    "BUILD_FORMAT",
    "SnapshotMergeError",
    "build_approved_input",
]
