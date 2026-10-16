from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZipFile

from .. import __version__
from ..common.identity import identifier_value, identity_token, is_ascii_digits
from ..common.text import repair_json_text
from ..common.time import daily_calendar_date, normalize_observation_timestamp
from ..common.values import comparable as _comparable
from ..common.values import is_empty
from ..diagnostics.contracts import FAMILY_DATASETS, SOURCE_FAMILY_ORDER
from ..diagnostics.detector import (
    classify_source_name,
    json_read_by_run_all,
    reads_record_file,
)
from ..intake.accounts import names_account, payload_accounts
from ..intake.archive import ArchiveLimits, is_real_export_file
from ..intake.discovery import (
    FILE_TOO_LARGE,
    FORMAT_NOT_READ,
    JSON_NOT_READABLE,
    SUPPORTED_SUFFIXES,
    ZIP_IN_ZIP,
    ZIP_NOT_READABLE,
    ZIP_TOO_LARGE,
    ZIP_UNSAFE_MEMBER,
    path_family,
)
from ..intake.source import DAMAGED_ZIP_ERRORS
from ..intake.roots import MIXED_STORE_MESSAGE, MixedExportsError
from ..normalizers.activities import activity_key, activity_left_out_reason
from ..normalizers.aliases import ENTITY_FIELD_NAMES
from ..normalizers.daily_metrics import (
    SNAPSHOT_NUMBERS_FIELD,
    SNAPSHOT_PRESENCE_FIELD,
    copies_within_snapshots,
    value_source_names,
)
from ..normalizers.gear import (
    gear_left_out_reason,
    gear_links,
    gear_record_key,
    link_left_out_reason,
)
from ..normalizers.performance_metrics import (
    ENDURANCE_SOURCE_FIELDS,
    ENDURANCE_VALUE_SOURCES,
    HILL_SOURCE_FIELDS,
    HILL_VALUE_SOURCES,
    LACTATE_SOURCE_FIELDS,
    PRIVATE_FIELD_NAMES,
    endurance_score_left_out_reason,
    hill_score_left_out_reason,
    is_lactate_threshold_candidate,
    metric_rows,
)
from ..normalizers.personal_records import (
    personal_record_key,
    personal_record_left_out_reason,
)
from ..normalizers.race_prediction import (
    RACE_PREDICTION_SOURCE_FIELDS,
    RACE_PREDICTION_VALUE_SOURCES,
    race_prediction_left_out_reason,
)
from ..normalizers.records import SNAPSHOT_PROBE_FIELD
from ..normalizers.source_records import (
    DAILY_WRAPPERS,
    activity_items,
    container_items,
    file_items,
    is_mark,
    list_items,
    mark_holds_a_value,
)
from ..normalizers.sleep import SLEEP_SOURCE_FIELDS, SLEEP_VALUE_SOURCES, sleep_left_out_reason
from ..normalizers.training_history import (
    TRAINING_HISTORY_SOURCE_FIELDS,
    TRAINING_HISTORY_VALUE_SOURCES,
    training_history_left_out_reason,
)
from ..normalizers.training_load import (
    ACUTE_TRAINING_LOAD_SOURCE_FIELDS,
    ACUTE_TRAINING_LOAD_VALUE_SOURCES,
    acute_training_load_left_out_reason,
)
from ..normalizers.training_readiness import (
    TRAINING_READINESS_SOURCE_FIELDS,
    TRAINING_READINESS_VALUE_SOURCES,
    training_readiness_left_out_reason,
)
from ..normalizers.unread_fields import INTERNAL_FIELD_PREFIX
from ..normalizers.uds import UDS_SOURCE_FIELDS, UDS_VALUE_SOURCES, uds_left_out_reason
from ..normalizers.vo2max import (
    VO2MAX_VALUE_SOURCES,
    vo2max_left_out_reason,
    vo2max_series,
    vo2max_source_fields,
)
from ..output_location import MESSAGES as OUTPUT_MESSAGES
from ..output_location import (
    OutputLocationError,
    check_output_location,
    path_error_code,
    write_error_code,
)
from .policies import CONTRACT_VERSION, MERGE_RULES, MERGE_RULES_VERSION, REGISTRY_VERSION
from .store import (
    SnapshotStoreError,
    content_multiset,
    load_manifests,
    load_store,
    not_readable_error,
    sha256_file,
    verification_error,
    verify_store,
)


BUILD_FORMAT = "garmin-running-data-normalizer-canonical-snapshot-build-v1"
# The Gear key of a link, which the build keeps with the link's record under
# a name of its own and does not write for Run-All: Run-All takes it from the
# Gear links object, as a one-shot run does, and the link keeps only the
# fields of the Export, whose other fields Run-All counts (stage A4c-1).
LINK_GEAR_KEY_FIELD = "garminRunningDataNormalizerSnapshotGearKey"
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
# Daily datasets (merge rules v2.0): every distinct record of a key goes to
# Run-All with the numbers of the Snapshots that gave it, and Run-All compares
# their normalized values as it does within one Export. Daily values are
# computed by Garmin, not edited by the user, so no Snapshot's value replaces
# another's. Snapshots are numbered from 1 in the order of their Export
# observation times.
DAILY_DATASETS = frozenset(MERGE_RULES["daily_datasets"]["datasets"])
# Activities, Gear, activity_gear, and Personal Records (merge rules v2.1)
# reflect the user's own edits in Garmin Connect, so each field takes the value
# of the latest Snapshot that contains it, and every earlier value is kept for
# the dataset's audit record.
ENTITY_DATASETS = frozenset(MERGE_RULES["entity_datasets"]["datasets"])
SOURCE_OBSERVATION_DATASETS = {
    "race_prediction_daily",
    "acute_training_load_daily",
    "training_readiness_daily",
    "vo2max_daily",
    "training_history_daily",
}
# The reason for which Run-All leaves a record of each daily dataset out, and
# the source fields of the dataset's values, as Run-All reads them (stage A3d-1).
# The reason for a VO2max record also needs the name of its file; see
# _left_out_with_a_value.
DAILY_LEFT_OUT_REASONS = {
    "hill_score_daily": hill_score_left_out_reason,
    "endurance_score_daily": endurance_score_left_out_reason,
    "race_prediction_daily": race_prediction_left_out_reason,
    "sleep_daily": sleep_left_out_reason,
    "uds_daily": uds_left_out_reason,
    "acute_training_load_daily": acute_training_load_left_out_reason,
    "training_readiness_daily": training_readiness_left_out_reason,
    "training_history_daily": training_history_left_out_reason,
}
DAILY_VALUE_SOURCE_NAMES = {
    "hill_score_daily": value_source_names(HILL_VALUE_SOURCES),
    "endurance_score_daily": value_source_names(ENDURANCE_VALUE_SOURCES),
    "race_prediction_daily": value_source_names(RACE_PREDICTION_VALUE_SOURCES),
    "sleep_daily": value_source_names(SLEEP_VALUE_SOURCES),
    "uds_daily": value_source_names(UDS_VALUE_SOURCES),
    "acute_training_load_daily": value_source_names(ACUTE_TRAINING_LOAD_VALUE_SOURCES),
    "training_readiness_daily": value_source_names(TRAINING_READINESS_VALUE_SOURCES),
    "vo2max_daily": value_source_names(VO2MAX_VALUE_SOURCES),
    "training_history_daily": value_source_names(TRAINING_HISTORY_VALUE_SOURCES),
}
# The source fields that Run-All reads from a record of each daily dataset;
# VO2max reads those of the record's series (stage A4c-2).
DAILY_SOURCE_FIELDS = {
    "hill_score_daily": HILL_SOURCE_FIELDS,
    "endurance_score_daily": ENDURANCE_SOURCE_FIELDS,
    "race_prediction_daily": RACE_PREDICTION_SOURCE_FIELDS,
    "sleep_daily": SLEEP_SOURCE_FIELDS,
    "uds_daily": UDS_SOURCE_FIELDS,
    "acute_training_load_daily": ACUTE_TRAINING_LOAD_SOURCE_FIELDS,
    "training_readiness_daily": TRAINING_READINESS_SOURCE_FIELDS,
    "training_history_daily": TRAINING_HISTORY_SOURCE_FIELDS,
}
SCHEMA_VERSION = "garmin-run-all-output:v1.1"
APPROVED_INPUT_MAX_FILE_BYTES = ArchiveLimits().max_member_bytes
# The limit for one file that a run reads: the build does not read a stored
# file over it, as a run does not (stage A3c-2).
SOURCE_FILE_MAX_BYTES = ArchiveLimits().max_member_bytes


# The reasons for which registration stores a ZIP file without its members
# (stage A3c-2); the build leaves such a ZIP file out.
ZIP_LEFT_OUT_REASONS = frozenset({ZIP_NOT_READABLE, ZIP_UNSAFE_MEMBER, ZIP_TOO_LARGE})


class SnapshotMergeError(SnapshotStoreError):
    """Canonical cumulative merge failed closed."""


class SnapshotBuildOutputError(SnapshotMergeError):
    """The build cannot be written in its place (stage A3d-3b); ``code`` is
    one of the codes of the place of an output, as for a run."""

    def __init__(self, code: str) -> None:
        super().__init__(OUTPUT_MESSAGES[code], code)


def _build_output_error(exc: OSError) -> SnapshotBuildOutputError | None:
    code = write_error_code(exc)
    return None if code is None else SnapshotBuildOutputError(code)


# The blobs of the store that the build reads: one that cannot be opened is
# named, and one that differs from its record makes a damaged store
# (stage A3d-3b).
_BLOB_FAILED = "immutable snapshot blob failed verification"


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


# The datasets whose rows hold the private fields that their audit records
# count (stage A3d-4b).
PRIVATE_FIELD_DATASETS = {
    "hill_score": "hill_score_daily",
    "endurance_score": "endurance_score_daily",
}


def _content_counts(numbers_by_family: dict[str, dict[str, list[int]]]) -> dict[str, int]:
    """For each family, its files or rows counted as a one-shot run of each
    Export counts them: the same content in two Snapshots once, and each copy
    within one Snapshot (stage A3b)."""
    return {
        family: sum(1 + copies_within_snapshots(numbers) for numbers in by_content.values())
        for family, by_content in sorted(numbers_by_family.items())
    }


def _unread_rows(name: str, payload: Any) -> list[tuple[str, dict[str, Any], frozenset[str]]]:
    """Return the rows of one file that Run-All keeps in a daily dataset or
    as Lactate Threshold candidates, as a one-shot run keeps them, each with
    its dataset and the source fields that the dataset reads from it.

    The build passes these rows narrowed to the fields of their dataset, so it
    counts the others itself, as it counts the private fields (stage A4c-2).
    """
    family = classify_source_name(name, "json")
    found: list[tuple[str, dict[str, Any], frozenset[str]]] = []
    if family in ("hill_score", "endurance_score"):
        dataset = f"{family}_daily"
        for row in metric_rows(payload):
            if not is_mark(row) and DAILY_LEFT_OUT_REASONS[dataset](row) is None:
                found.append((dataset, row, DAILY_SOURCE_FIELDS[dataset]))
    elif family == "lactate_threshold":
        lactate_family = _lactate_family(name)
        if lactate_family is not None:
            for row in metric_rows(payload):
                if not is_mark(row) and is_lactate_threshold_candidate(row, lactate_family):
                    found.append(("lactate_threshold", row, LACTATE_SOURCE_FIELDS[lactate_family]))
    elif (definition := _daily_definition(family, name)) is not None:
        dataset = definition[0]
        file_name = PurePosixPath(name.replace("\\", "/")).name.lower()
        for row in file_items(payload, DAILY_WRAPPERS):
            if is_mark(row):
                continue
            if dataset == "vo2max_daily":
                if vo2max_left_out_reason(row, file_name) is None:
                    found.append((dataset, row, vo2max_source_fields(vo2max_series(row, file_name))))
            elif DAILY_LEFT_OUT_REASONS[dataset](row) is None:
                found.append((dataset, row, DAILY_SOURCE_FIELDS[dataset]))
    return found


def _unread_field_counts(
    rows: dict[str, tuple[dict[str, Any], frozenset[str], list[int]]],
) -> dict[str, int]:
    """The rows that hold each field that their dataset does not read, by
    name, counted as the private fields are: the same content in two
    Snapshots once, and each copy within one Snapshot (stage A4c-2)."""
    counts: Counter[str] = Counter()
    for row, read, numbers in rows.values():
        weight = 1 + copies_within_snapshots(numbers)
        for name in row:
            if name not in read and not name.startswith(INTERNAL_FIELD_PREFIX):
                counts[name] += weight
    return dict(sorted(counts.items()))


def _private_field_counts(rows: dict[str, tuple[dict[str, Any], list[int]]]) -> dict[str, int]:
    """The rows that hold each private field, counted as above."""
    counts: Counter[str] = Counter()
    for row, numbers in rows.values():
        weight = 1 + copies_within_snapshots(numbers)
        for name in PRIVATE_FIELD_NAMES & set(row):
            counts[name] += weight
    return dict(sorted(counts.items()))


class ActivitiesNotReadableError(SnapshotMergeError):
    """No Activities record remains because every Activities file was left out."""


def _oversize_members(store: Path, row: dict[str, Any]) -> list[tuple[str, int]]:
    """Return the members of a stored ZIP file that are over the limit for
    one file, as (name, bytes).

    Only the central directory is read: registration lists every other
    member, and the ZIP file holds these (stage A3c-2). A run does not read
    them: those of a form that a dataset reads are too large, and the others
    are of a form not read (stage A4b).
    """
    blob = store / str(row["blob_relative_path"])
    try:
        with ZipFile(blob) as archive:
            infos = archive.infolist()
    except PermissionError as exc:
        raise not_readable_error(store, blob) from exc
    except DAMAGED_ZIP_ERRORS as exc:
        raise SnapshotMergeError(_BLOB_FAILED, "SNAPSHOT_STORE_INVALID") from exc
    return sorted(
        (info.filename, info.file_size)
        for info in infos
        if not info.is_dir()
        and is_real_export_file(info.filename)
        and info.file_size > SOURCE_FILE_MAX_BYTES
    )


def _not_read_reason(name: str) -> str:
    """Why a run does not read a file of a form that no dataset reads, from
    its name in the Export or in its ZIP file: a ZIP file inside a ZIP file of
    the Export, or a file of another form (stage A4b)."""
    return ZIP_IN_ZIP if PurePosixPath(name).suffix.lower() == ".zip" else FORMAT_NOT_READ


def _read_blob(store: Path, row: dict[str, Any]) -> bytes:
    path = store / str(row["blob_relative_path"])
    try:
        data = path.read_bytes()
    except PermissionError as exc:
        raise not_readable_error(store, path) from exc
    except OSError as exc:
        raise SnapshotMergeError(_BLOB_FAILED, "SNAPSHOT_STORE_INVALID") from exc
    if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise SnapshotMergeError(_BLOB_FAILED, "SNAPSHOT_STORE_INVALID")
    return data


def _copy_blob(store: Path, row: dict[str, Any], destination: Path, failure: str) -> None:
    """Copy a blob of the store into the build, checking its SHA-256 as it is
    read. A blob that cannot be read is named; an error of the destination is
    left to the build, which gives it the code of the output's place."""
    blob = store / str(row["blob_relative_path"])
    digest = hashlib.sha256()
    try:
        source = blob.open("rb")
    except PermissionError as exc:
        raise not_readable_error(store, blob) from exc
    except OSError as exc:
        raise SnapshotMergeError(failure, "SNAPSHOT_STORE_INVALID") from exc
    with source, destination.open("xb") as target:
        while True:
            try:
                chunk = source.read(1024 * 1024)
            except PermissionError as exc:
                raise not_readable_error(store, blob) from exc
            except OSError as exc:
                raise SnapshotMergeError(failure, "SNAPSHOT_STORE_INVALID") from exc
            if not chunk:
                break
            digest.update(chunk)
            target.write(chunk)
    if digest.hexdigest() != str(row["sha256"]):
        raise SnapshotMergeError(failure, "SNAPSHOT_STORE_INVALID")


def _fit_copy_bytes(manifests: list[dict[str, Any]]) -> int:
    """The bytes of the FIT files that the build copies, each once: what it
    writes for them, known before it starts (stage A3d-3b). The build writes
    more, so these bytes are the least it needs."""
    sizes: dict[str, int] = {}
    for manifest in manifests:
        for row in manifest["objects"]:
            size = int(row["bytes"])
            if str(row.get("extension", "")).lower() == ".fit" and size <= SOURCE_FILE_MAX_BYTES:
                sizes.setdefault(str(row["sha256"]), size)
    return sum(sizes.values())


def _left_out_with_a_value(dataset: str, record: dict[str, Any], logical_name: str) -> bool:
    """Tell whether Run-All leaves a daily record out while it holds a value.

    Such a record makes the family of its Snapshot malformed; a record that
    holds no value is an empty record, which Run-All only counts (stage A3d-1).
    """
    if dataset == "vo2max_daily":
        reason = vo2max_left_out_reason(record, PurePosixPath(logical_name).name.lower())
    else:
        reason = DAILY_LEFT_OUT_REASONS[dataset](record)
    return reason is not None and any(
        not is_empty(record.get(name)) for name in DAILY_VALUE_SOURCE_NAMES[dataset]
    )


# A record without a usable identifier, as Run-All reads it, has no stable
# key: the build passes it to Run-All, which leaves it out (stage A3d-1b).


def _activity_key(row: dict[str, Any]) -> str:
    if activity_left_out_reason(row) is not None:
        raise ValueError("Activities row without a usable identifier")
    return activity_key(row)


def _gear_key(row: dict[str, Any]) -> Any:
    return None if gear_left_out_reason(row) is not None else gear_record_key(row)


def _personal_record_key(row: dict[str, Any]) -> Any:
    if personal_record_left_out_reason(row) is not None:
        return None
    return personal_record_key(row)


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


def _object_name(source: dict[str, Any]) -> str:
    """Return the name by which the build tells a stored file, as a one-shot
    run tells it: its path in the Export, and for a member of a ZIP file its
    name within the ZIP file (stage A3d-4c-1)."""
    return str(source.get("archive_member_path") or source["relative_path"])


def _daily_definition(
    family: str,
    name: str,
) -> tuple[str, tuple[str, ...], str | None] | None:
    """Return the dataset, the fields, and the series of the records of a
    daily file of this family. The family is told as a one-shot run tells it
    (stage A3d-4c-1); the series of a VO2max file, by the beginning of its
    name, as Run-All takes it."""
    basename = PurePosixPath(name.replace("\\", "/")).name.lower()
    definitions = (
        (
            "race_prediction",
            None,
            "race_prediction_daily",
            (
                "calendarDate", "timestamp", "raceTime5K", "raceTime10K",
                "raceTimeHalf", "raceTimeMarathon",
            ),
            None,
        ),
        (
            "sleep",
            None,
            "sleep_daily",
            (
                "calendarDate", "sleepStartTimestampGMT", "sleepEndTimestampGMT",
                "sleepTimeSeconds", "totalSleepSeconds", "durationInSeconds",
                "sleepDuration", "deepSleepSeconds", "deep_sleep_seconds",
                "lightSleepSeconds", "light_sleep_seconds", "remSleepSeconds",
                "rem_sleep_seconds", "awakeSleepSeconds", "awake_sleep_seconds",
                "sleepScores", "overallScore", "sleepScore",
            ),
            None,
        ),
        (
            "uds",
            None,
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
            "acute_training_load",
            None,
            "acute_training_load_daily",
            (
                "calendarDate", "acwrPercent", "acwrStatus", "dailyTrainingLoadAcute",
                "dailyTrainingLoadChronic", "dailyAcuteChronicWorkloadRatio", "timestamp",
            ),
            None,
        ),
        (
            "training_readiness",
            None,
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
            "vo2max",
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
            "vo2max",
            "metricsmaxmetdata",
            "vo2max_daily",
            # The activity is kept as a one-shot run reads it (merge rules
            # v2.10).
            (
                "calendarDate", "vo2MaxValue", "sport", "maxMet", "maxMetCategory",
                "calibratedData", "vo2MaxSourceSeries", "updateTimestamp",
                "observationTimestamp", "activityId",
            ),
            "performance_metrics_daily",
        ),
        (
            "vo2max",
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
            "training_history",
            None,
            "training_history_daily",
            ("calendarDate", "timestamp", "trainingStatus", "sport"),
            None,
        ),
    )
    for definition_family, prefix, dataset, fields, source_series in definitions:
        if definition_family == family and (prefix is None or basename.startswith(prefix)):
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
        if dataset == "sleep_daily":
            # As in a one-shot run, Run-All takes the sleep day from the end
            # time, which also identifies the same sleep across Snapshots.
            end, _ = normalize_observation_timestamp(
                record.get("sleepEndTimestampGMT"),
                naive_timezone_semantics="UTC_SOURCE_FIELD",
            )
            return None if end is None else ("sleep_end", end)
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


# The marks of the items of a Lactate Threshold file that are not records and
# of its lists of records that cannot be read (stage A3d-2c-2). They are not
# candidates: the build writes them for Run-All apart from the candidates.
LACTATE_MARKS = "lactate_threshold_marks"


def _dataset_records(
    name: str,
    payload: Any,
) -> list[tuple[str, str, dict[str, Any], tuple[Any, ...] | None]]:
    """Return the records of one file, by dataset, as Run-All reads them.

    The file is told by its name as a one-shot run tells it, a member of a
    ZIP file by its name within the ZIP file (stage A3d-4c-1). The marks of
    its items that are not records and of its lists of records that cannot
    be read (stage A3d-2c-2) are records without a key, passed as they are,
    so that Run-All counts them as a one-shot run does. A link's mark has no
    Gear key.
    """
    family = classify_source_name(name, "json")
    result: list[tuple[str, str, dict[str, Any], tuple[Any, ...] | None]] = []
    if family == "activities":
        for index, row in enumerate(activity_items(payload)):
            try:
                key: tuple[Any, ...] | None = None if is_mark(row) else (_activity_key(row),)
            except ValueError:
                key = None
            result.append(("activities", str(index), row, key))
    elif family == "gear":
        for container_index, container in enumerate(container_items(payload)):
            if is_mark(container):
                # An item of the file's top list counts as Gear, as in a run.
                result.append(("gear", str(container_index), container, None))
                continue
            for index, row in enumerate(list_items(container.get("gearDTOS"))):
                gear_key = None if is_mark(row) else _gear_key(row)
                result.append(
                    (
                        "gear",
                        f"{container_index}:{index}",
                        row,
                        None if gear_key is None else (gear_key,),
                    )
                )
            links, unreadable = gear_links(container)
            for row in unreadable:
                result.append(("activity_gear", f"{container_index}:links", row, None))
            for gear_key in sorted(links, key=str):
                for index, row in enumerate(list_items(links[gear_key])):
                    record_index = f"{container_index}:{gear_key}:{index}"
                    if is_mark(row):
                        result.append(("activity_gear", record_index, row, None))
                        continue
                    link_record = {**row, LINK_GEAR_KEY_FIELD: gear_key}
                    key = (
                        None
                        if link_left_out_reason(gear_key, row) is not None
                        else (gear_key, identifier_value(row.get("activityId")))
                    )
                    result.append(("activity_gear", record_index, link_record, key))
    elif family == "personal_records":
        for container_index, container in enumerate(container_items(payload)):
            if is_mark(container):
                result.append(("personal_records", str(container_index), container, None))
                continue
            for index, row in enumerate(list_items(container.get("personalRecords"))):
                record_key = None if is_mark(row) else _personal_record_key(row)
                result.append(
                    (
                        "personal_records",
                        f"{container_index}:{index}",
                        row,
                        None if record_key is None else (record_key,),
                    )
                )
    elif family == "hill_score":
        for index, row in enumerate(metric_rows(payload)):
            if is_mark(row):
                result.append(("hill_score_daily", str(index), row, None))
                continue
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
    elif family == "endurance_score":
        for index, row in enumerate(metric_rows(payload)):
            if is_mark(row):
                result.append(("endurance_score_daily", str(index), row, None))
                continue
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
    elif (definition := _daily_definition(family, name)) is not None:
        dataset, fields, source_series = definition
        for index, row in enumerate(file_items(payload, DAILY_WRAPPERS)):
            if is_mark(row):
                # Not narrowed to the dataset's fields, and without a series.
                result.append((dataset, str(index), row, None))
                continue
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
    elif family == "lactate_threshold":
        lactate_family = _lactate_family(name)
        if lactate_family is not None:
            # The candidates are read as Run-All reads them (stage A3d-2c-2;
            # until then, the build read only the top object or the objects
            # of the top list).
            for index, row in enumerate(metric_rows(payload)):
                if is_mark(row):
                    result.append((LACTATE_MARKS, str(index), row, None))
                    continue
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


def _as_counted(record: dict[str, Any]) -> dict[str, Any]:
    """A record as the field states count it: the Gear key that the build
    keeps with a link counts as the link's field ``gearPk``, as it did when
    the build kept it there, before stage A4c-1."""
    if LINK_GEAR_KEY_FIELD not in record:
        return record
    counted = {name: value for name, value in record.items() if name != LINK_GEAR_KEY_FIELD}
    counted["gearPk"] = record[LINK_GEAR_KEY_FIELD]
    return counted


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
            "severity": "review",
            "conflict_type": "lactate_functional_threshold_power_conflict",
            "dataset": "lactate_threshold_candidates",
            "observation_family": family,
            "observation_timestamp": timestamp,
            "candidate_status": "multiple_observed_candidates",
            "authority_status": "unresolved",
            "stable_promotion_available": False,
        }
        for (family, timestamp), values in sorted(grouped.items())
        if len(values) > 1
    ]


def _lactate_malformed_conflicts(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a record for each candidate with a field of another form.

    The build counts them in the candidates' summary and passes the
    candidates to Run-All; they no longer stop the build (stage A3d-2a).
    """

    conflicts: list[dict[str, Any]] = []
    numeric_fields = {
        "lactateThresholdSpeed",
        "lactateThresholdHeartRate",
        "functionalThresholdPower",
    }
    for observation in observations:
        record = observation.get("record", {})
        if not isinstance(record, dict):
            conflicts.append(
                {
                    "severity": "stop",
                    "conflict_type": "lactate_malformed_candidate",
                    "dataset": "lactate_threshold_candidates",
                    "reason": "candidate record is not an object",
                }
            )
            continue
        for field in numeric_fields:
            value = record.get(field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                conflicts.append(
                    {
                        "severity": "stop",
                        "conflict_type": "lactate_malformed_candidate",
                        "dataset": "lactate_threshold_candidates",
                        "field": field,
                        "reason": "numeric candidate field has invalid type",
                    }
                )
                break
    return conflicts


def _conflict_count_summary(conflicts: list[dict[str, Any]]) -> str:
    """Count stop conflicts by dataset and type without dates, keys, or values."""
    counts = Counter(
        (str(item.get("dataset", "unknown")), str(item.get("conflict_type", "unknown")))
        for item in conflicts
    )
    return ", ".join(
        f"{dataset} {conflict_type}={count}"
        for (dataset, conflict_type), count in sorted(counts.items())
    )


def _canonical_key(dataset: str, values: tuple[Any, ...]) -> str:
    if dataset == "activities":
        return str(values[0])
    return f"{dataset}:{_sha256_value(list(values))}"


def _record_identity(dataset: str, observation: dict[str, Any]) -> tuple[str, ...]:
    """Return what tells the records of one dataset apart.

    In Activities, Gear, activity_gear, and Personal Records, identifiers
    written in two ways, such as " 123" and 123, name one record (stage A3b).
    """
    raw_key = observation["raw_key"]
    if dataset not in ENTITY_DATASETS:
        return (_canonical_key(dataset, raw_key),)
    if dataset == "activities":
        token = identity_token(observation["record"].get("activityId"))
        if token is not None:
            return ("identifier:" + token,)
        return ("key:" + str(raw_key[0]),)
    return tuple(
        "identifier:" + token
        if (token := identity_token(value)) is not None
        else "value:" + _stable_json(value)
        for value in raw_key
    )


def _observation_order(item: dict[str, Any]) -> tuple[int, str, str, str]:
    return (
        int(item["logical_order"]),
        str(item["snapshot_id"]),
        str(item["source_relative_path"]),
        str(item["source_record_index"]),
    )


def _reappeared(bits: str) -> bool:
    first = bits.find("1")
    last = bits.rfind("1")
    return first >= 0 and last > first and "0" in bits[first:last]


def _audit_key(dataset: str, raw_key: tuple[Any, ...]) -> dict[str, Any]:
    """Return a record's stable key as its normalized dataset names it."""
    if dataset == "activities":
        return {"garmin_activity_key": raw_key[0]}
    if dataset == "gear":
        return {"gear_key": raw_key[0]}
    if dataset == "activity_gear":
        gear_key = raw_key[0]
        return {
            "gear_key": int(gear_key) if is_ascii_digits(str(gear_key)) else gear_key,
            "activity_id": raw_key[1],
        }
    return {"personal_record_id": raw_key[0]}


def _link_removed(
    raw_key: tuple[Any, ...],
    latest_endpoints: tuple[set[str], set[str]] | None,
) -> bool:
    """Whether the latest Snapshot shows an Activity and a Gear without their link.

    A link that the latest Snapshot does not contain was removed when that
    Snapshot contains both its Gear and its Activity. Otherwise its absence
    may come from records that the Export left out, so the link stays.
    """
    if latest_endpoints is None:
        return False
    gear_keys, activity_ids = latest_endpoints
    return (
        identity_token(raw_key[0]) in gear_keys
        and identity_token(raw_key[1]) in activity_ids
    )


def _entry_order(entry: tuple[str, Any, list[int], dict[str, Any]]) -> tuple[int, float, str]:
    """Order the values of one time point: numbers by size, then the others by text."""
    form, value, _numbers, _first = entry
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, float(value), form)
    return (1, 0.0, form)


def _merge_entity(
    ordered: list[dict[str, Any]],
    point_of: dict[int, int],
    field_names: tuple[tuple[str, ...], ...] = (),
) -> dict[str, Any]:
    """Merge the observations of one Activity, Gear, link, or Personal Record.

    Snapshots observed at the same time are one time point (stage A3b, merge
    rules v2.3). At each time point, a field's value is the value of the
    observations that contain the field; an empty value (null, "", [], or
    {}) is no value there, unless every observation that contains the field
    leaves it empty, which removes the value. Two or more values at one time
    point disagree. Each field takes its value from the last time point that
    contains it, as in stage A2b-2, and a change is a value, or a set of
    disagreeing values, that differs from the previous time point's;
    differences within one time point are disagreements only.

    The records written for Run-All are the observations of the record's last
    time point: one record when they hold the same values and fields, and
    otherwise one record for each set of observations with the same values
    and fields, so that Run-All merges them, and counts the fields that it
    does not read, as in a one-shot run; each record has the fields that no
    observation of that time point contains, taken from the earlier time
    points. Each record carries the import numbers of the observations behind
    it, one for each copy, when there is more than one. A field that the last
    time point does not contain and whose earlier values disagree is written
    as probes, which let Run-All mark the fields that come from it. The
    copies within each Snapshot of the earlier time points are counted here;
    Run-All counts those of the last time point.

    ``field_names`` are the groups of source names of one field (stage
    A4d-1, merge rules v2.16). When the record's observations use two or more
    names of a group, the names are one field across time points: the last
    time point that holds any of them gives the names that go on, with their
    values, and the others are not carried; a change is listed once, under
    the names joined by ``|``. A record that uses one name of a group is
    merged field by field, as before.
    """
    points: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for observation in ordered:
        points[point_of[int(observation["logical_order"])]].append(observation)
    fields = sorted(set().union(*(set(item["record"]) for item in ordered)))
    groups = [
        names
        for names in (tuple(name for name in group if name in fields) for group in field_names)
        if len(names) > 1
    ]
    grouped = {name for names in groups for name in names}

    def same_values(item: dict[str, Any]) -> str:
        # A null or missing field is no value; forms alike are one value.
        return _stable_json(_comparable({field: item["record"].get(field) for field in fields}))

    earlier_copies = 0
    for point in sorted(points)[:-1]:
        by_number: dict[int, set[str]] = defaultdict(set)
        count: Counter[int] = Counter()
        for item in points[point]:
            number = int(item["logical_order"])
            by_number[number].add(same_values(item))
            count[number] += 1
        earlier_copies += sum(count[number] - len(by_number[number]) for number in count)
    states: dict[str, list[tuple[int, list[tuple[str, Any, list[int], dict[str, Any]]]]]] = {}
    for field in fields:
        by_point: list[tuple[int, list[tuple[str, Any, list[int], dict[str, Any]]]]] = []
        for point in sorted(points):
            holders = [item for item in points[point] if field in item["record"]]
            if not holders:
                continue
            given = [item for item in holders if not is_empty(item["record"][field])]
            values: dict[str, list[Any]] = {}
            # Only empty values: the value was removed at this time point.
            for item in given or holders:
                value = item["record"][field]
                entry = values.setdefault(
                    _stable_json(_comparable(value)), [value, [], item]
                )
                entry[1].append(int(item["logical_order"]))
            by_point.append(
                (
                    point,
                    [
                        (form, value, sorted(numbers), first)
                        for form, (value, numbers, first) in values.items()
                    ],
                )
            )
        states[field] = by_point

    def value_runs(
        by_point: list[tuple[int, list[tuple[str, Any, list[int], dict[str, Any]]]]],
    ) -> tuple[list[dict[str, Any]], int]:
        """The values of a field by time point, and the number of changes."""
        runs: list[dict[str, Any]] = []
        open_form: str | None = None
        previous: frozenset[str] | None = None
        changes = 0
        for _point, entries in by_point:
            signature = frozenset(entry[0] for entry in entries)
            if previous is not None and signature != previous:
                changes += 1
            previous = signature
            if len(entries) == 1:
                form, value, numbers, _first = entries[0]
                if open_form == form:
                    # Values that differ only in form share an entry, which
                    # shows the value of its latest time point.
                    runs[-1]["value"] = value
                    runs[-1]["snapshots"] = sorted(set(runs[-1]["snapshots"]) | set(numbers))
                else:
                    runs.append({"value": value, "snapshots": sorted(set(numbers))})
                    open_form = form
            else:
                # The values of a time point that disagree, each with the
                # Snapshots that gave it; they never share an entry.
                for _form, value, numbers, _first in sorted(entries, key=_entry_order):
                    runs.append({"value": value, "snapshots": sorted(set(numbers))})
                open_form = None
        return runs, changes

    updates: list[dict[str, Any]] = []
    change_count = 0
    merged: dict[str, Any] = {}
    selected: dict[str, dict[str, Any]] = {}
    disagreeing: dict[str, list[tuple[str, Any, list[int], dict[str, Any]]]] = {}
    for field, by_point in states.items():
        runs, changes = value_runs(by_point)
        _last_point, last_entries = by_point[-1]
        selected[field] = last_entries[0][3]
        if len(last_entries) == 1:
            merged[field] = last_entries[0][1]
        else:
            disagreeing[field] = last_entries
        if changes and field not in grouped:
            change_count += changes
            updates.append({"field": field, "values": runs})
    for names in groups:
        # The names of one field, which the record's observations use two or
        # more of: one field across time points (stage A4d-1).
        by_point = []
        for point in sorted(points):
            pairs = [
                (item, item["record"][name])
                for item in points[point]
                for name in names
                if name in item["record"]
            ]
            if not pairs:
                continue
            given = [(item, value) for item, value in pairs if not is_empty(value)]
            values: dict[str, list[Any]] = {}
            for item, value in given or pairs:
                entry = values.setdefault(_stable_json(_comparable(value)), [value, [], item])
                entry[1].append(int(item["logical_order"]))
            by_point.append(
                (
                    point,
                    [
                        (form, value, sorted(numbers), first)
                        for form, (value, numbers, first) in values.items()
                    ],
                )
            )
        runs, changes = value_runs(by_point)
        if changes:
            change_count += changes
            updates.append({"field": "|".join(names), "values": runs})
        # The names of the last time point that holds any of them go on; the
        # others are neither carried nor written as probes.
        last_point = by_point[-1][0]
        for name in names:
            if not any(name in item["record"] for item in points[last_point]):
                merged.pop(name, None)
                selected.pop(name, None)
                disagreeing.pop(name, None)
    updates.sort(key=lambda item: item["field"])

    last = points[max(points)]
    contained = sorted(set().union(*(set(item["record"]) for item in last)))
    copies: dict[str, list[dict[str, Any]]] = {}
    for item in last:
        # Copies are one record only when they also hold the same fields, as
        # an empty value and a missing field are alike here: Run-All then
        # counts the fields that it does not read as a one-shot run counts
        # those of each copy (stage A4c-1).
        values = _comparable({field: item["record"].get(field) for field in contained})
        signature = _stable_json([values, sorted(item["record"])])
        copies.setdefault(signature, []).append(item)

    def merge_copies(items: list[dict[str, Any]]) -> dict[str, Any]:
        record: dict[str, Any] = {}
        for field in contained:
            holders = [item["record"][field] for item in items if field in item["record"]]
            if holders:
                given = [value for value in holders if not is_empty(value)]
                record[field] = given[0] if given else holders[0]
        return record

    carried = {field: value for field, value in merged.items() if field not in contained}
    records: list[tuple[dict[str, Any], list[int] | None]] = []
    if len(copies) == 1:
        (items,) = copies.values()
        numbers = sorted(int(item["logical_order"]) for item in items)
        records.append(({**carried, **merge_copies(items)}, numbers if len(items) > 1 else None))
    else:
        for items in copies.values():
            records.append(
                (
                    {**carried, **merge_copies(items)},
                    sorted(int(item["logical_order"]) for item in items),
                )
            )
    probes: list[tuple[dict[str, Any], str, list[int] | None]] = []
    for field, entries in sorted(disagreeing.items()):
        if field in contained:
            continue
        base = {name: value for name, value in records[0][0].items() if name != field}
        probes.append((base, field, None))
        for _form, value, numbers, _first in sorted(entries, key=_entry_order):
            probes.append(({**base, field: value}, field, numbers))
    return {
        "records": records,
        "probes": probes,
        "updates": updates,
        "change_count": change_count,
        "merged": merged,
        "selected": selected,
        "disagreeing": sorted(disagreeing),
        "earlier_copies": earlier_copies,
    }


def _merge_dataset(
    dataset: str,
    observations: list[dict[str, Any]],
    snapshot_count: int,
    *,
    latest_state: dict[str, list[str]] | None = None,
    time_points: list[list[int]] | None = None,
    latest_file_left_out: bool = False,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, list[dict[str, Any]]] | None,
]:
    """Merge one dataset's observations from every registered Snapshot.

    The last item returned is, for Activities, Gear, activity_gear, and
    Personal Records, the record of their changes for the dataset's audit
    record: values that changed, with the Snapshots that gave each value,
    records that the latest Snapshot does not contain, and removed links.
    ``latest_state`` gives the latest Snapshot's Activities and Gear for
    activity_gear, only when the latest Snapshot holds Gear links (the
    ``gearActivityDTOs`` object, even an empty one); without it, no link is
    removed. ``time_points`` groups the Snapshot numbers of the Snapshots
    observed at the same time, in time order (stage A3b); the Snapshots of
    the last group are together the latest Snapshot.
    ``latest_file_left_out`` tells that the latest Snapshot had a file of the
    dataset's family left out (stage A3c-2): the records that it lacks are
    marked, since they may only have been in that file.
    A daily record without a stable key is not held: it is written for
    Run-All, which leaves it out as a one-shot run does (stage A3d-1), and so
    is a record of Activities, Gear, activity_gear, or Personal Records
    without a usable identifier (stage A3d-1b).
    """
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    holds: list[dict[str, Any]] = []
    keyless: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    field_provenance: list[dict[str, Any]] = []
    for observation in observations:
        raw_key = observation["raw_key"]
        if raw_key is None or any(value in (None, "") for value in raw_key):
            if dataset in DAILY_DATASETS or dataset in ENTITY_DATASETS:
                keyless.append(observation)
                continue
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
        groups[_record_identity(dataset, observation)].append(observation)

    canonical: list[dict[str, Any]] = []
    pattern_counts: Counter[str] = Counter()
    previous_only = 0
    new = 0
    reappeared = 0
    changed = 0
    updated_fields = 0
    state_counts: Counter[str] = Counter()
    exact_repeat_count = 0
    earlier_copies = 0
    daily = dataset in DAILY_DATASETS
    entity = dataset in ENTITY_DATASETS
    record_audit: dict[str, list[dict[str, Any]]] | None = (
        {"updates": [], "not_in_latest_snapshot": [], "removed_links": []}
        if entity
        else None
    )
    if time_points is None:
        time_points = [[number] for number in range(1, snapshot_count + 1)]
    point_of = {
        number: index for index, numbers in enumerate(time_points) for number in numbers
    }
    latest_endpoints = (
        (
            set(latest_state["current_gear_keys"]),
            set(latest_state["current_activity_ids"]),
        )
        if latest_state is not None
        else None
    )
    # Each record is named by the key of its first observation.
    named = sorted(
        (_canonical_key(dataset, min(group, key=_observation_order)["raw_key"]), identity)
        for identity, group in groups.items()
    )
    for key, identity in named:
        group = groups[identity]
        by_snapshot: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for observation in group:
            by_snapshot[int(observation["logical_order"])].append(observation)
        # Daily records are compared in Run-All, and Activities, Gear, links,
        # and Personal Records by time point (stage A3b). Lactate candidates
        # whose order cannot be told apart, within one Snapshot or in two
        # Snapshots observed at the same time, still stop.
        compared_here = not daily and not entity
        for logical_order, rows in (by_snapshot.items() if compared_here else []):
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
        for observed_at, signatures in (by_observed_at.items() if compared_here else []):
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

        ordered = sorted(group, key=_observation_order)
        counted = [_as_counted(item["record"]) for item in ordered]
        distinct_signatures = {_stable_json(record) for record in counted}
        exact_repeat_count += len(ordered) - len(distinct_signatures)
        bits = "".join(
            "1" if logical_order in by_snapshot else "0"
            for logical_order in range(1, snapshot_count + 1)
        )
        pattern_counts[bits] += 1
        state_counts["record_absent"] += bits.count("0")
        # Presence by time point: a record in any Snapshot of the latest time
        # point is in the latest Snapshot.
        point_bits = "".join(
            "1" if any(point_of[number] == point for number in by_snapshot) else "0"
            for point in range(len(time_points))
        )
        in_latest = point_bits.endswith("1")
        removed = (
            dataset == "activity_gear"
            and not in_latest
            and _link_removed(ordered[0]["raw_key"], latest_endpoints)
        )
        if not in_latest and not removed:
            previous_only += 1
        if in_latest and "1" not in point_bits[:-1]:
            new += 1
        if _reappeared(point_bits):
            reappeared += 1

        merged: dict[str, Any] = {}
        selected: dict[str, dict[str, Any]] = {}
        field_universe = set().union(*(set(record) for record in counted))
        for record in counted:
            state_counts["field_absent"] += len(field_universe - set(record))
            for value in record.values():
                state_counts[_value_state(value)] += 1
        if len(distinct_signatures) > 1:
            changed += 1
        if daily:
            # Each distinct record is kept once, with the import number of each
            # Snapshot occurrence; nothing is chosen here.
            by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for observation in ordered:
                by_signature[_stable_json(observation["record"])].append(observation)
            for signature in sorted(by_signature):
                rows = by_signature[signature]
                canonical.append(
                    {
                        "canonical_key": key,
                        "raw_record": rows[0]["record"],
                        "snapshot_numbers": sorted(
                            int(item["logical_order"]) for item in rows
                        ),
                        "presence_pattern": bits,
                        "source_snapshot_count": len(
                            {int(item["logical_order"]) for item in rows}
                        ),
                        "source_observation_count": len(rows),
                    }
                )
                for index, observation in enumerate(rows):
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
                                "observation_kept" if index == 0 else "exact_duplicate"
                            ),
                        }
                    )
            continue
        if removed:
            # The link is left out of the normalized dataset; the audit record
            # keeps it with the last Snapshot that contained it.
            record_audit["removed_links"].append(
                {
                    "key": _audit_key(dataset, ordered[0]["raw_key"]),
                    "last_seen_snapshot": max(by_snapshot),
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
                        "merge_disposition": "link_removed",
                    }
                )
            continue
        if entity:
            # Activities, Gear, links, and Personal Records: values by time
            # point; the records of the last time point go to Run-All.
            result = _merge_entity(ordered, point_of, ENTITY_FIELD_NAMES.get(dataset, ()))
            updated_fields += result["change_count"]
            earlier_copies += result["earlier_copies"]
            audit_key = _audit_key(dataset, ordered[0]["raw_key"])
            if result["updates"]:
                record_audit["updates"].append(
                    {"key": audit_key, "fields": result["updates"]}
                )
            if not in_latest:
                missing = {"key": audit_key, "last_seen_snapshot": max(by_snapshot)}
                if latest_file_left_out:
                    missing["latest_file_left_out"] = True
                record_audit["not_in_latest_snapshot"].append(missing)
            for record, numbers in result["records"]:
                canonical.append(
                    {
                        "canonical_key": key,
                        "raw_record": record,
                        "snapshot_numbers": numbers,
                        # Every Snapshot that holds the record, for the rows
                        # that each Snapshot observed (stage A3d-4c-2).
                        "observed_snapshots": sorted(by_snapshot),
                        "presence_pattern": bits,
                        "source_snapshot_count": len(by_snapshot),
                        "source_observation_count": len(ordered),
                    }
                )
            for record, field, numbers in result["probes"]:
                canonical.append(
                    {
                        "canonical_key": key,
                        "raw_record": record,
                        "snapshot_numbers": numbers,
                        "probe_field": field,
                        "presence_pattern": bits,
                        "source_snapshot_count": len(by_snapshot),
                        "source_observation_count": len(ordered),
                    }
                )
            contributors = {id(item) for item in result["selected"].values()}
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
                            if id(observation) in contributors
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
            for field, observation in sorted(result["selected"].items()):
                disagrees = field in result["disagreeing"]
                field_provenance.append(
                    {
                        "dataset": dataset,
                        "canonical_key": key,
                        "field_name": field,
                        "value_state": (
                            "values_disagree"
                            if disagrees
                            else _value_state(result["merged"][field])
                        ),
                        "selected_value_sha256": (
                            None if disagrees else _sha256_value(result["merged"][field])
                        ),
                        "snapshot_id": observation["snapshot_id"],
                        "logical_order": observation["logical_order"],
                        "source_relative_path": observation["source_relative_path"],
                        "source_record_index": observation["source_record_index"],
                    }
                )
            continue
        for observation in ordered:
            for field in sorted(observation["record"]):
                value = observation["record"][field]
                if (state := _value_state(value)) in {
                    "explicit_null",
                    "explicit_empty",
                }:
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

    # Each distinct record without a stable key is written once, after the
    # records with one, with the import number of each Snapshot occurrence,
    # so that Run-All counts it as a one-shot run of each Export does. It has
    # no presence, changes, or record audit (stages A3d-1 and A3d-1b).
    keyed_record_count = len(canonical)
    by_content: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in keyless:
        by_content[_stable_json(observation["record"])].append(observation)
    for signature in sorted(by_content):
        rows = sorted(by_content[signature], key=_observation_order)
        key = f"{dataset}:keyless:{_sha256_bytes(signature.encode('utf-8'))}"
        numbers = sorted(int(item["logical_order"]) for item in rows)
        canonical.append(
            {
                "canonical_key": key,
                "raw_record": rows[0]["record"],
                "snapshot_numbers": numbers,
                "presence_pattern": "".join(
                    "1" if number in numbers else "0"
                    for number in range(1, snapshot_count + 1)
                ),
                "source_snapshot_count": len(set(numbers)),
                "source_observation_count": len(rows),
            }
        )
        for index, observation in enumerate(rows):
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
                        "observation_kept" if index == 0 else "exact_duplicate"
                    ),
                }
            )

    summary = {
        "source_observation_count": len(observations),
        "canonical_record_count": len(
            {item["canonical_key"] for item in canonical[:keyed_record_count]}
        ),
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
    if daily:
        summary.update(
            {
                "distinct_record_count": keyed_record_count,
                "exact_repeat_count": exact_repeat_count,
                # Records without a stable key, written for Run-All (stage A3d-1).
                "keyless_observation_count": len(keyless),
                "keyless_record_count": len(by_content),
                "automatic_winner": False,
            }
        )
    elif dataset == "lactate_threshold_candidates":
        # Candidate-layer audit metadata is extended by build_approved_input,
        # but the primitive merge summary must expose deterministic repeat
        # accounting as well for direct merge QA and permutation tests.
        summary["exact_repeat_count"] = exact_repeat_count
    if entity:
        # Records without a usable identifier, written for Run-All (stage A3d-1b).
        summary["keyless_observation_count"] = len(keyless)
        summary["keyless_record_count"] = len(by_content)
    if record_audit is not None:
        for entries in record_audit.values():
            entries.sort(key=lambda item: _stable_json(item["key"]))
        # The copies within the Snapshots of earlier time points, which
        # Run-All adds to the copies that it counts (stage A3b).
        record_audit["earlier_copy_count"] = earlier_copies
        # Counts only: the values stay in the dataset's audit record.
        summary["updated_record_count"] = len(record_audit["updates"])
        if dataset == "activity_gear":
            summary["removed_link_count"] = len(record_audit["removed_links"])
        else:
            del record_audit["removed_links"]
    return canonical, provenance, field_provenance, holds, conflicts, summary, record_audit


def _materialized_record(item: dict[str, Any]) -> dict[str, Any]:
    """Return a canonical record as written for Run-All.

    A daily record carries the import numbers of the Snapshots that gave it,
    and so does a record of Activities, Gear, links, or Personal Records
    that stands for more than one observation; every such record with a
    stable key also carries those of every Snapshot that holds it (stage
    A3d-4c-2); a probe record also carries the name of its field.
    """
    record = dict(item["raw_record"])
    if item.get("snapshot_numbers") is not None:
        record[SNAPSHOT_NUMBERS_FIELD] = item["snapshot_numbers"]
    if item.get("observed_snapshots") is not None:
        record[SNAPSHOT_PRESENCE_FIELD] = item["observed_snapshots"]
    if item.get("probe_field") is not None:
        record[SNAPSHOT_PROBE_FIELD] = item["probe_field"]
    return record


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
    latest_numbers: set[int],
) -> dict[str, list[str]]:
    """Return only the latest Export endpoint identities for validation.

    The cumulative approved input remains the validation record set. These
    latest-only sets let the relationship classifier distinguish an endpoint
    retained from an earlier authoritative Snapshot from one present in the
    current Export without inferring any identity. ``latest_numbers`` are the
    Snapshot numbers of the latest time point: the Snapshots observed at the
    latest time are together the latest Export (stage A3b). Identifiers are
    written as the relationship checks read them.
    """

    # `logical_order` is now fixed to the canonical acquisition chronology, so
    # the final registered Snapshots are the latest authoritative order even
    # when a Dataset has no observations in them. This preserves an empty
    # current endpoint instead of retaining a stale older endpoint.
    latest = {
        dataset: [
            item
            for item in observations
            if int(item.get("acquisition_order", item["logical_order"]))
            in latest_numbers
        ]
        for dataset, observations in observations_by_dataset.items()
    }
    activity_ids = {
        token
        for item in latest.get("activities", [])
        if (token := identity_token(item["record"].get("activityId"))) is not None
    }
    gear_keys = {
        token
        for item in latest.get("gear", [])
        if (token := identity_token(item["record"].get("gearPk"))) is not None
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
    *,
    processing_sequence: list[str] | None = None,
) -> dict[str, Any]:
    # The output is checked before the store, whose verification can take
    # long (stage A3d-3b).
    requested_output = Path(output_root)
    try:
        if requested_output.is_symlink():
            raise SnapshotMergeError("canonical build output must not be a symbolic link")
        output = requested_output.resolve()
        exists = output.exists()
    except OSError as exc:
        raise SnapshotBuildOutputError(path_error_code(requested_output, exc)) from exc
    if exists:
        raise SnapshotMergeError("canonical build output must not already exist")
    try:
        check_output_location(output, lambda parent, name: False)
    except OutputLocationError as exc:
        raise SnapshotBuildOutputError(exc.code) from exc
    verification = verify_store(store_root)
    if verification["status"] != "PASS":
        raise verification_error(verification, SnapshotMergeError)
    store, store_metadata = load_store(store_root)
    registered = load_manifests(store)
    if not registered:
        raise SnapshotMergeError("snapshot store has no registered snapshots")
    # Snapshots with the same content are one Export, registered more than
    # once; the earliest observed one is used (merge rules v2.2), so that an
    # Export registered again later never becomes the latest Snapshot.
    manifests: list[dict[str, Any]] = []
    same_content: list[tuple[dict[str, Any], dict[str, Any]]] = []
    first_by_content: dict[tuple[tuple[str, int], ...], dict[str, Any]] = {}
    for manifest in registered:
        content = tuple(content_multiset(list(manifest.get("objects", []))))
        if content in first_by_content:
            same_content.append((manifest, first_by_content[content]))
        else:
            first_by_content[content] = manifest
            manifests.append(manifest)
    acquisition_order_by_snapshot_id = {
        str(manifest["snapshot_id"]): index
        for index, manifest in enumerate(manifests, start=1)
    }
    # Snapshots observed at the same time are one time point (stage A3b);
    # the Snapshots of the last one are together the latest Snapshot.
    time_points: list[list[int]] = []
    previous_time: datetime | None = None
    for index, manifest in enumerate(manifests, start=1):
        observed = datetime.fromisoformat(str(manifest["export_observed_at"])).astimezone(
            timezone.utc
        )
        if time_points and observed == previous_time:
            time_points[-1].append(index)
        else:
            time_points.append([index])
        previous_time = observed
    manifests_by_label = {
        str(manifest["snapshot_label"]): manifest for manifest in registered
    }
    manifests_by_id = {
        str(manifest["snapshot_id"]): manifest for manifest in registered
    }
    if processing_sequence is None:
        processing_manifests = list(manifests)
        processing_labels = [str(item["snapshot_label"]) for item in manifests]
    else:
        sequence = [str(item) for item in processing_sequence]
        if len(sequence) != len(registered) or len(set(sequence)) != len(sequence):
            raise SnapshotMergeError(
                "processing_sequence must contain each registered snapshot exactly once"
            )
        if set(sequence).issubset(manifests_by_label):
            processing_manifests = [manifests_by_label[item] for item in sequence]
        elif set(sequence).issubset(manifests_by_id):
            processing_manifests = [manifests_by_id[item] for item in sequence]
        else:
            raise SnapshotMergeError(
                "processing_sequence must use registered snapshot labels or IDs"
            )
        processing_manifests = [
            item
            for item in processing_manifests
            if str(item["snapshot_id"]) in acquisition_order_by_snapshot_id
        ]
        processing_labels = [str(item["snapshot_label"]) for item in processing_manifests]
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        # The least that the build needs, against the free space where it is
        # written: a build that cannot fit stops before it starts.
        if _fit_copy_bytes(processing_manifests) > shutil.disk_usage(output.parent).free:
            raise SnapshotBuildOutputError("OUTPUT_SPACE_INSUFFICIENT")
        stage = Path(
            tempfile.mkdtemp(prefix=f".{output.name}.snapshot-build-", dir=output.parent)
        )
    except OSError as exc:
        error = _build_output_error(exc)
        if error is None:
            raise
        raise error from exc
    try:
        observations_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
        dataset_to_family = {
            dataset: family
            for family, datasets in FAMILY_DATASETS.items()
            for dataset in datasets
        }
        # The observations of each Snapshot, without the rows that it
        # observed: Run-All counts them in its output, as a one-shot run
        # counts its rows (stage A3d-4c-2).
        snapshot_diagnostics = {
            str(manifest["snapshot_id"]): {
                "observation_ref": f"snapshot-{acquisition_order_by_snapshot_id[str(manifest['snapshot_id'])]}",
                "candidate_counts": {family: 0 for family in SOURCE_FAMILY_ORDER},
                "malformed_counts": {family: 0 for family in SOURCE_FAMILY_ORDER},
                "fit_source_sha256": [],
                "unknown_evidence_count": 0,
            }
            for manifest in manifests
        }
        parser_states: Counter[str] = Counter()
        unknown_object_count = 0
        unknown_families: set[str] = set()
        fit_aliases: list[dict[str, Any]] = []
        fit_unique: dict[str, dict[str, Any]] = {}
        unknown_aliases: list[dict[str, Any]] = []
        unknown_unique: dict[str, dict[str, Any]] = {}
        # The Snapshots, by number, that hold Gear links: a Gear file with the
        # gearActivityDTOs object, even an empty one.
        link_snapshots: set[int] = set()
        # The accounts that the records name, compared here only and never
        # written: a store holds the Exports of one account.
        accounts: set[str] = set()
        # The files of each family, by content, with the import number of
        # each occurrence, so that Run-All counts them as a one-shot run of
        # each Export does (stage A3d-4a).
        family_file_numbers: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # The JSON and FIT files that a run of each Export reads, of any
        # family or none, by content, with the import number of each
        # occurrence, so that Run-All counts its input files as a one-shot
        # run of each Export does (stage A3d-4c-1).
        input_file_numbers: dict[str, list[int]] = defaultdict(list)
        # The Lactate Threshold files and their rows, also the rows that are
        # not candidates, and the Hill and Endurance rows, by content, with
        # the import number of each occurrence, so that Run-All counts their
        # files, rows, and private fields as a one-shot run of each Export
        # does (stage A3d-4b).
        lactate_file_numbers: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        lactate_row_numbers: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        private_rows: dict[str, dict[str, tuple[dict[str, Any], list[int]]]] = defaultdict(dict)
        # The rows that Run-All keeps in a daily dataset or as Lactate
        # Threshold candidates, by dataset and content (stage A4c-2).
        unread_rows: dict[
            str, dict[str, tuple[dict[str, Any], frozenset[str], list[int]]]
        ] = defaultdict(dict)
        # The files that a run leaves out or does not read, by Snapshot
        # number, as in a one-shot run of each Export (stage A3c-2).
        files_left_out: list[dict[str, Any]] = []
        files_not_read: list[dict[str, Any]] = []
        # The files whose text with a lone surrogate the build repaired as it
        # read them, by Snapshot number, as a run counts them (stage A3d-2c-1).
        files_with_repaired_text: list[dict[str, Any]] = []
        left_out_families: dict[int, set[str]] = defaultdict(set)

        def leave_out(number: int, path: str, size: int, reason: str) -> None:
            family = path_family(path)
            files_left_out.append(
                {
                    "snapshot": number,
                    "source_path": path,
                    "bytes": size,
                    "family": family,
                    "reason": reason,
                }
            )
            left_out_families[number].add(family)
            parser_states["extraction_failed"] += 1

        def too_large(number: int, path: str, size: int) -> None:
            # A file that no dataset reads adds nothing to the datasets: it
            # is not read rather than left out (decision 20261013-7).
            if path_family(path) == "unclassified":
                files_not_read.append(
                    {"snapshot": number, "source_path": path, "bytes": size, "reason": FILE_TOO_LARGE}
                )
                parser_states["parser_unsupported"] += 1
            else:
                leave_out(number, path, size, FILE_TOO_LARGE)

        def not_read(number: int, path: str, size: int, name: str) -> None:
            # A file of a form that no dataset reads, and a ZIP file inside
            # a ZIP file, are not read, as in a run (stage A4b).
            files_not_read.append(
                {
                    "snapshot": number,
                    "source_path": path,
                    "bytes": size,
                    "reason": _not_read_reason(name),
                }
            )

        for processing_index, manifest in enumerate(processing_manifests, start=1):
            diagnostic = snapshot_diagnostics[str(manifest["snapshot_id"])]
            acquisition_order = acquisition_order_by_snapshot_id[
                str(manifest["snapshot_id"])
            ]
            for source in manifest["objects"]:
                extension = str(source.get("extension", "")).lower()
                object_kind = source.get("object_kind")
                logical_name = str(source["relative_path"])
                name = _object_name(source)
                size = int(source["bytes"])
                if extension in SUPPORTED_SUFFIXES and size > SOURCE_FILE_MAX_BYTES:
                    # As in a run, a JSON or FIT file over the limit for one
                    # file is not read.
                    too_large(acquisition_order, logical_name, size)
                    continue
                if (
                    extension == ".zip"
                    and object_kind == "file"
                    and source.get("parser_state") in ZIP_LEFT_OUT_REASONS
                ):
                    # Registration stored the ZIP file without its members;
                    # it is not opened again.
                    leave_out(acquisition_order, logical_name, size, str(source["parser_state"]))
                    continue
                detected_kind = "fit" if extension == ".fit" else (
                    "json" if extension == ".json" else "unknown"
                )
                detected_family = classify_source_name(name, detected_kind)
                if detected_family in diagnostic["candidate_counts"]:
                    diagnostic["candidate_counts"][detected_family] += 1
                    family_file_numbers[detected_family][str(source["sha256"])].append(
                        acquisition_order
                    )
                if extension in SUPPORTED_SUFFIXES:
                    # A JSON or FIT file that a run of the Export reads; one
                    # of no family is unknown evidence, as a one-shot run
                    # counts it, and the other objects that the build does
                    # not read are not (stage A3d-4c-1).
                    input_file_numbers[str(source["sha256"])].append(acquisition_order)
                    if detected_family == "unclassified":
                        diagnostic["unknown_evidence_count"] += 1
                if extension == ".fit":
                    digest = str(source["sha256"])
                    diagnostic["fit_source_sha256"].append(digest)
                    fit_unique.setdefault(digest, source)
                    fit_aliases.append(
                        {
                            "fit_blob_sha256": digest,
                            "snapshot_id": manifest["snapshot_id"],
                            "logical_order": acquisition_order,
                            "acquisition_order": acquisition_order,
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
                    # twice through a copied container. Its members over the
                    # limit for one file are not listed; a run does not read
                    # them either (stage A3c-2), and lists those of a form
                    # not read as such (stage A4b).
                    for member_name, member_size in _oversize_members(store, source):
                        member_path = f"{logical_name}!{member_name}"
                        if PurePosixPath(member_name).suffix.lower() in SUPPORTED_SUFFIXES:
                            too_large(acquisition_order, member_path, member_size)
                        else:
                            not_read(acquisition_order, member_path, member_size, member_name)
                            parser_states["parser_unsupported"] += 1
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
                            "logical_order": acquisition_order,
                            "acquisition_order": acquisition_order,
                            "source_relative_path": logical_name,
                            "parser_state": "parser_unsupported",
                        }
                    )
                    if extension not in SUPPORTED_SUFFIXES:
                        not_read(acquisition_order, logical_name, size, name)
                    continue
                data = _read_blob(store, source)
                read_by_run_all = json_read_by_run_all(name)
                try:
                    text = data.decode("utf-8-sig")
                    value = json.loads(text)
                    repaired = 0
                    if read_by_run_all:
                        # Text with a lone surrogate is repaired as a run
                        # repairs it, so that the records can be written
                        # (stage A3d-2c-1).
                        value, repaired = repair_json_text(text, value)
                    readable = True
                except (ValueError, RecursionError):
                    # The errors for which a run leaves a JSON file out: not
                    # UTF-8, not JSON, nested too deeply, or a number with
                    # too many digits (stage A3c-2).
                    value = None
                    readable = False
                if readable and repaired:
                    files_with_repaired_text.append(
                        {
                            "snapshot": acquisition_order,
                            "source_path": logical_name,
                            "family": detected_family,
                            "repaired_text_count": repaired,
                        }
                    )
                lactate_family = _lactate_family(name)
                if lactate_family is not None:
                    # A file that cannot be read counts as a file without rows.
                    lactate_file_numbers[lactate_family][str(source["sha256"])].append(
                        acquisition_order
                    )
                    family_rows = lactate_row_numbers[lactate_family]
                    for row in metric_rows(value) if readable else []:
                        family_rows[_stable_json(row)].append(acquisition_order)
                metric_dataset = PRIVATE_FIELD_DATASETS.get(detected_family)
                if metric_dataset is not None and readable:
                    for row in metric_rows(value):
                        if not is_mark(row):
                            _row, numbers = private_rows[metric_dataset].setdefault(
                                _stable_json(row), (row, [])
                            )
                            numbers.append(acquisition_order)
                if readable:
                    for dataset, row, read in _unread_rows(name, value):
                        _row, _read, numbers = unread_rows[dataset].setdefault(
                            _stable_json([sorted(read), row]), (row, read, [])
                        )
                        numbers.append(acquisition_order)
                if not readable and detected_family != "unclassified":
                    leave_out(acquisition_order, logical_name, size, JSON_NOT_READABLE)
                    continue
                if readable and names_account(name):
                    # A file left out is not compared, as in a run.
                    accounts |= payload_accounts(value)
                if readable and reads_record_file(name, "gear") and any(
                    isinstance(container.get("gearActivityDTOs"), dict)
                    for container in container_items(value)
                ):
                    link_snapshots.add(acquisition_order)
                # A JSON file that no dataset reads is kept as an unknown
                # object, also when it cannot be read.
                extracted = _dataset_records(name, value) if readable else []
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
                            "logical_order": acquisition_order,
                            "acquisition_order": acquisition_order,
                            "source_relative_path": logical_name,
                            "parser_state": "parser_unsupported",
                        }
                    )
                    continue
                parser_states["explicit_value"] += 1
                for dataset, record_index, record, raw_key in extracted:
                    diagnostic_family = dataset_to_family.get(dataset)
                    if diagnostic_family is not None:
                        # A mark that holds a value is left out by Run-All; an
                        # item that is an empty value is an empty record.
                        malformed = (
                            mark_holds_a_value(record)
                            if is_mark(record)
                            else _left_out_with_a_value(dataset, record, name)
                            if dataset in DAILY_VALUE_SOURCE_NAMES
                            else raw_key is None
                        )
                        if malformed:
                            diagnostic["malformed_counts"][diagnostic_family] += 1
                    observations_by_dataset[dataset].append(
                        {
                            "dataset": dataset,
                            "record": record,
                            "raw_key": raw_key,
                            "snapshot_id": manifest["snapshot_id"],
                            "logical_order": acquisition_order,
                            "acquisition_order": acquisition_order,
                            "processing_sequence": processing_index,
                            "export_observed_at": manifest["export_observed_at"],
                            "source_relative_path": logical_name,
                            "source_record_index": record_index,
                            "source_object_sha256": source["sha256"],
                        }
                    )
        if len(accounts) > 1:
            raise MixedExportsError(MIXED_STORE_MESSAGE)

        canonical_by_dataset: dict[str, list[dict[str, Any]]] = {}
        all_provenance: list[dict[str, Any]] = []
        all_field_provenance: list[dict[str, Any]] = []
        all_holds: list[dict[str, Any]] = []
        candidate_reviews = _lactate_power_conflicts(
            observations_by_dataset.get("lactate_threshold_candidates", [])
        )
        # A candidate with a value of another form is passed to Run-All, which
        # counts it as a one-shot run does; the build only counts it (stage
        # A3d-2a, merge rules v2.7). Until then, it stopped the build.
        malformed_candidates = _lactate_malformed_conflicts(
            observations_by_dataset.get("lactate_threshold_candidates", [])
        )
        all_conflicts: list[dict[str, Any]] = []
        dataset_summaries: dict[str, Any] = {}
        latest_state = _latest_relationship_state(
            observations_by_dataset,
            set(time_points[-1]),
        )
        # The families with a file left out in the latest Snapshot: their
        # records that it lacks are marked (stage A3c-2).
        latest_left_out_families = set().union(
            *(left_out_families.get(number, set()) for number in time_points[-1])
        )
        record_changes: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for dataset in DATASET_ORDER:
            (
                canonical,
                provenance,
                field_provenance,
                holds,
                conflicts,
                summary,
                record_audit,
            ) = _merge_dataset(
                dataset,
                observations_by_dataset.get(dataset, []),
                len(manifests),
                time_points=time_points,
                latest_state=(
                    latest_state
                    if dataset == "activity_gear"
                    and any(number in link_snapshots for number in time_points[-1])
                    else None
                ),
                latest_file_left_out=dataset_to_family.get(dataset) in latest_left_out_families,
            )
            canonical_by_dataset[dataset] = canonical
            all_provenance.extend(provenance)
            all_field_provenance.extend(field_provenance)
            all_holds.extend(holds)
            all_conflicts.extend(conflicts)
            dataset_summaries[dataset] = summary
            if record_audit is not None:
                record_changes[dataset] = record_audit
        lactate_summary = dataset_summaries["lactate_threshold_candidates"]
        lactate_observations = observations_by_dataset.get(
            "lactate_threshold_candidates", []
        )
        lactate_null_key_count = int(lactate_summary.get("null_key_hold_count", 0))
        lactate_summary.update(
            {
                "candidate_rows": len(lactate_observations),
                "distinct_candidate_count": int(
                    lactate_summary.get("canonical_record_count", 0)
                ),
                "exact_repeat_count": max(
                    0,
                    len(lactate_observations)
                    - int(lactate_summary.get("canonical_record_count", 0))
                    - lactate_null_key_count,
                ),
                "multiple_candidate_group_count": len(candidate_reviews),
                "authority_unresolved_count": len(candidate_reviews),
                "stable_promotion_available": False,
                "malformed_count": lactate_null_key_count + len(malformed_candidates),
                "candidate_status": (
                    "multiple_observed_candidates"
                    if candidate_reviews
                    else "identity_or_semantics_unknown"
                ),
                "candidate_review_required": bool(candidate_reviews),
            }
        )
        if all_conflicts:
            _write_json(
                stage / "canonical/review_holds.json",
                all_holds + candidate_reviews + all_conflicts,
            )
            raise SnapshotMergeError(
                "canonical merge contains unresolved stop conflicts: "
                + _conflict_count_summary(all_conflicts)
            )
        if not canonical_by_dataset["activities"]:
            if any(item["family"] == "activities" for item in files_left_out):
                # As in a run: the Activities files could not be read.
                from ..run_all import ACTIVITIES_NOT_READABLE_MESSAGE

                raise ActivitiesNotReadableError(ACTIVITIES_NOT_READABLE_MESSAGE)
            raise SnapshotMergeError("canonical input contains no Activities records")

        approved = stage / "approved_input"
        fitness = approved / "DI-Connect-Fitness"
        uploaded = approved / "DI-Connect-Uploaded-Files"
        metrics = approved / "DI-Connect-Metrics"
        sleep_source = approved / "DI-Connect-Wellness"
        aggregator = approved / "DI-Connect-Aggregator"
        lactate_source = sleep_source
        activity_rows = [
            _materialized_record(item) for item in canonical_by_dataset["activities"]
        ]
        _write_activity_input(fitness, activity_rows)
        gear_rows = [_materialized_record(item) for item in canonical_by_dataset["gear"]]
        link_rows = [
            _materialized_record(item) for item in canonical_by_dataset["activity_gear"]
        ]
        if gear_rows or link_rows:
            links_by_gear: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in link_rows:
                # A link without a usable Gear key keeps the key it had, also
                # an empty one, so that Run-All leaves it out (stage A3d-1b).
                gear_key = row.pop(LINK_GEAR_KEY_FIELD, None)
                links_by_gear["" if gear_key is None else str(gear_key)].append(row)
            _write_json(
                fitness / "snapshot_gear.json",
                [{"gearDTOS": gear_rows, "gearActivityDTOs": dict(links_by_gear)}],
            )
        personal_rows = [
            _materialized_record(item)
            for item in canonical_by_dataset["personal_records"]
        ]
        if personal_rows:
            _write_json(
                fitness / "snapshot_personalRecord.json",
                [{"personalRecords": personal_rows}],
            )
        hill_rows = [
            _materialized_record(item)
            for item in canonical_by_dataset["hill_score_daily"]
        ]
        if hill_rows:
            _write_json(metrics / "snapshot_HillScore.json", hill_rows)
        endurance_rows = [
            _materialized_record(item)
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
            rows = [_materialized_record(item) for item in canonical_by_dataset[dataset]]
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
        # The marks of the Lactate Threshold files follow the candidates of
        # their family, each distinct mark once, with the import number of
        # each Snapshot occurrence, so that Run-All counts them as a one-shot
        # run of each Export does (stage A3d-2c-2).
        lactate_marks: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for observation in observations_by_dataset.get(LACTATE_MARKS, []):
            mark_family = str(_lactate_family(str(observation["source_relative_path"])))
            lactate_marks[(mark_family, _stable_json(observation["record"]))].append(
                observation
            )
        for (family, _signature), marks in sorted(lactate_marks.items()):
            lactate_rows[family].append(
                {
                    **marks[0]["record"],
                    SNAPSHOT_NUMBERS_FIELD: sorted(
                        int(item["logical_order"]) for item in marks
                    ),
                }
            )
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
            _copy_blob(store, source, destination, "cumulative FIT blob failed verification")
        for digest, source in sorted(unknown_unique.items()):
            suffix = str(source.get("extension", "")).lower()
            # A ZIP file inside a ZIP file of the Export is written under a
            # name that a run does not open: a run of the Export does not
            # read it (stage A4b).
            if not suffix.startswith(".") or len(suffix) > 16 or suffix == ".zip":
                suffix = ".bin"
            destination = approved / "preserved_unknown" / f"object_{digest}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            _copy_blob(store, source, destination, "preserved unknown blob failed verification")

        # Source discovery follows runtime processing order, but every
        # audit/provenance list is serialized in authoritative acquisition
        # order so processing_sequence cannot change normalized truth or its
        # semantic digest.
        fit_aliases.sort(
            key=lambda item: (
                int(item["acquisition_order"]),
                str(item["snapshot_id"]),
                str(item["source_relative_path"]),
            )
        )
        unknown_aliases.sort(
            key=lambda item: (
                int(item["acquisition_order"]),
                str(item["snapshot_id"]),
                str(item["source_relative_path"]),
            )
        )
        all_provenance.sort(
            key=lambda item: (
                str(item["dataset"]),
                str(item["canonical_key"]),
                int(item["logical_order"]),
                str(item["snapshot_id"]),
                str(item["source_relative_path"]),
                str(item["source_record_index"]),
            )
        )
        all_field_provenance.sort(
            key=lambda item: (
                str(item["dataset"]),
                str(item["canonical_key"]),
                str(item["field_name"]),
                int(item["logical_order"]),
                str(item["snapshot_id"]),
            )
        )
        all_holds.sort(key=_stable_json)
        all_conflicts.sort(key=_stable_json)

        approved_inventory, approved_hash = _approved_input_inventory(approved)
        canonical_records = {
            dataset: [
                {
                    "canonical_key": item["canonical_key"],
                    "raw_record_sha256": _sha256_value(item["raw_record"]),
                    "presence_pattern": item["presence_pattern"],
                    **(
                        {"snapshot_numbers": item["snapshot_numbers"]}
                        if "snapshot_numbers" in item
                        else {}
                    ),
                }
                for item in rows
            ]
            for dataset, rows in canonical_by_dataset.items()
        }
        # The Snapshots that contained each FIT file, one number per
        # occurrence, so that HRV can name the Snapshots behind its values.
        fit_snapshot_numbers: dict[str, list[int]] = defaultdict(list)
        for alias in fit_aliases:
            fit_snapshot_numbers[str(alias["fit_blob_sha256"])].append(
                int(alias["acquisition_order"])
            )
        build_hash = _sha256_value(
            {
                "account_store_id": store_metadata["account_store_id"],
                "snapshot_content_ids": [
                    manifest["snapshot_content_id"] for manifest in manifests
                ],
                "policy_registry_version": REGISTRY_VERSION,
                "merge_rules_version": MERGE_RULES_VERSION,
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
            "merge_rules_version": MERGE_RULES_VERSION,
            "parser_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "account_store_id": store_metadata["account_store_id"],
            "snapshot_count": len(manifests),
            "chronology_authority": "manifest.export_observed_at",
            "processing_sequence": "runtime-only; never authoritative",
            **(
                {
                    "same_content_snapshot_count": len(same_content),
                    "same_content_snapshots": [
                        {
                            "snapshot_label": manifest["snapshot_label"],
                            "same_as_snapshot_number": acquisition_order_by_snapshot_id[
                                str(first["snapshot_id"])
                            ],
                        }
                        for manifest, first in same_content
                    ],
                }
                if same_content
                else {}
            ),
            "snapshots": [
                {
                    "snapshot_id": manifest["snapshot_id"],
                    "snapshot_label": manifest["snapshot_label"],
                    "logical_order": index,
                    "acquisition_order": index,
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
            **(
                {"same_content_snapshot_count": len(same_content)}
                if same_content
                else {}
            ),
            "policy_registry_version": REGISTRY_VERSION,
            "merge_rules_version": MERGE_RULES_VERSION,
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
            "candidate_review_count": len(candidate_reviews),
            "candidate_review_type_counts": dict(
                sorted(Counter(item["conflict_type"] for item in candidate_reviews).items())
            ),
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
            # v1.4 additive diagnostic authority. These are bounded counts and
            # local FIT evidence bindings only; they never select a canonical
            # value and are removed from the public Support Bundle projection.
            "source_completeness_observations": sorted(
                snapshot_diagnostics.values(),
                key=lambda item: int(
                    str(item["observation_ref"]).split("-")[-1]
                ),
            ),
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
            # The JSON and FIT files of no family in all the Snapshots, which
            # Source Completeness counts as unknown evidence; the objects that
            # the build does not read are counted above (stage A3d-4c-1).
            "unknown_evidence_count": sum(
                int(item["unknown_evidence_count"]) for item in snapshot_diagnostics.values()
            ),
            "canonical_completeness_boundary": (
                "registered complete exports only; unsupported or failed "
                "observations are preserved but not promoted"
            ),
        }
        approved_manifest = {
            "format": "garmin-running-data-normalizer-approved-input-manifest-v1",
            "contract_version": CONTRACT_VERSION,
            "policy_registry_version": REGISTRY_VERSION,
            "merge_rules_version": MERGE_RULES_VERSION,
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
            "merge_rules_version": MERGE_RULES_VERSION,
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
            "candidate_review_count": len(candidate_reviews),
            "candidate_review_type_counts": dict(
                sorted(Counter(item["conflict_type"] for item in candidate_reviews).items())
            ),
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
        _write_json(
            stage / "canonical/review_holds.json",
            all_holds + candidate_reviews,
        )
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
            "relationship_context": latest_state,
            # Runtime only, like relationship_context: never written to an
            # output.
            "fit_snapshot_numbers": {
                digest: sorted(numbers)
                for digest, numbers in sorted(fit_snapshot_numbers.items())
            },
            # Runtime only: Run-All writes these changes, with their values,
            # to the dataset audit records of the local output.
            "record_changes": record_changes,
            # Runtime only: the files of each family, counted as a one-shot
            # run of each Export counts them: the same content in two
            # Snapshots once, and its copies within one Snapshot (stage A3b),
            # for the family results, the audit records, and the dataset
            # summary (stage A3d-4a).
            "family_file_counts": {
                family: sum(
                    1 + copies_within_snapshots(numbers) for numbers in by_content.values()
                )
                for family, by_content in sorted(family_file_numbers.items())
            },
            # Runtime only: the JSON and FIT files of the Exports, of any
            # family or none, counted in the same way, for the run summary
            # (stage A3d-4c-1).
            "input_file_count": sum(
                1 + copies_within_snapshots(numbers) for numbers in input_file_numbers.values()
            ),
            # Runtime only: the Lactate Threshold files and rows, also the
            # rows that are not candidates, which the build does not pass, and
            # the private fields of the Hill and Endurance rows, which it
            # leaves out, counted in the same way (stage A3d-4b).
            "lactate_threshold_counts": {
                "family_asset_counts": _content_counts(lactate_file_numbers),
                "family_source_record_counts": _content_counts(lactate_row_numbers),
            },
            "private_field_counts": {
                dataset: _private_field_counts(by_content)
                for dataset, by_content in sorted(private_rows.items())
            },
            # Runtime only: the fields of the daily rows and the Lactate
            # Threshold candidates that their dataset does not read, by name,
            # which the build leaves out, counted in the same way (stage
            # A4c-2).
            "unread_field_counts": {
                dataset: counts
                for dataset, by_content in sorted(unread_rows.items())
                if (counts := _unread_field_counts(by_content))
            },
            # Runtime only: Run-All lists these files, by Snapshot number, in
            # the local run manifest (stage A3c-2).
            "files_left_out": sorted(
                files_left_out, key=lambda item: (item["snapshot"], item["source_path"])
            ),
            "files_not_read": sorted(
                files_not_read, key=lambda item: (item["snapshot"], item["source_path"])
            ),
            # Runtime only: Run-All lists these files, by Snapshot number, in
            # the local run manifest (stage A3d-2c-1).
            "files_with_repaired_text": sorted(
                files_with_repaired_text,
                key=lambda item: (item["snapshot"], item["source_path"]),
            ),
            "source_completeness_context": {
                "observation_scope": "REGISTERED_SNAPSHOT_OBSERVATIONS",
                "observations": sorted(
                    snapshot_diagnostics.values(),
                    key=lambda item: int(str(item["observation_ref"]).split("-")[-1]),
                ),
            },
            # This is returned for runtime diagnostics only and is not written
            # into the public normalized payload or semantic digest.
            "processing_sequence": processing_labels,
        }
    except Exception as exc:
        if stage.exists():
            shutil.rmtree(stage)
        # An error of writing the build: no free space, no permission, or a
        # path too long (stage A3d-3b).
        error = _build_output_error(exc) if isinstance(exc, OSError) else None
        if error is None:
            raise
        raise error from exc


__all__ = [
    "ActivitiesNotReadableError",
    "BUILD_FORMAT",
    "SnapshotBuildOutputError",
    "SnapshotMergeError",
    "build_approved_input",
]
