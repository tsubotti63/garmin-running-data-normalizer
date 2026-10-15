from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

from . import __version__
from .common.time import (
    DEFAULT_TIMEZONE,
    TimezoneDataUnavailableError,
    TimezoneNameInvalidError,
    require_timezone_data,
    resolve_timezone_name,
)
from .fit.parser import parse_fit_export
from .export.analysis_pack import build_analysis_pack_payloads
from .intake.accounts import asset_accounts
from .intake.discovery import (
    FORMAT_NOT_READ,
    DiscoveredAsset,
    ExportReading,
    InputChangedError,
    path_family,
    read_export,
    repaired_text_count,
)
from .intake.roots import MIXED_INPUT_MESSAGE, OUTSIDE_EXPORT_ROOT, MixedExportsError
from .intake.source import (
    CorruptArchiveError,
    ExportTooLargeError,
    InputNotReadableError,
    TempSpaceError,
    is_zip_input,
)
from .output_location import (
    MESSAGES as OUTPUT_LOCATION_MESSAGES,
    OutputLocationError,
    check_output_location,
    output_path_too_long,
    path_error_code,
    write_error_code,
)
from .normalizers.activities import normalize_activities
from .normalizers.daily_metrics import DailyMetricError, copies_within_snapshots
from .normalizers.gear import normalize_gear
from .normalizers.hrv import normalize_hrv_daily_assets
from .normalizers.personal_records import normalize_personal_records
from .normalizers.performance_metrics import (
    ENDURANCE_FIELDS,
    HILL_FIELDS,
    PerformanceMetricsError,
    build_performance_metrics_daily_context,
    collect_lactate_threshold_candidates,
    normalize_endurance_score,
    normalize_hill_score,
)
from .normalizers.race_prediction import normalize_race_prediction
from .common.values import InvalidValues
from .normalizers.records import (
    EMPTY_RECORD,
    STABLE_KEYS,
    RecordMerge,
    check_values,
    identifier_fields,
    merge_repeated_records,
)
from .normalizers.source_records import MARK_KINDS
from .normalizers.sleep import normalize_sleep_daily_assets
from .normalizers.training_history import normalize_training_history
from .normalizers.training_load import normalize_acute_training_load
from .normalizers.training_readiness import normalize_training_readiness
from .normalizers.uds import normalize_uds
from .normalizers.vo2max import normalize_vo2max
from .qa import deterministic_records_digest
from .relationships import (
    RelationshipContractError,
    build_activity_fit_relationship,
    validate_declared_relationships,
)


RUN_ALL_VERSION = 2
# The message when every Activities file was left out (stage A3c).
ACTIVITIES_NOT_READABLE_MESSAGE = (
    "the Activities files could not be read; obtain a complete, readable Export"
)
# An internal check: the Snapshot build leaves out the files that a run
# cannot read (stage A3c-2).
SNAPSHOT_LEFT_OUT_MESSAGE = (
    "the approved Snapshot input holds a file that the build should have left out"
)
SNAPSHOT_REPAIRED_TEXT_MESSAGE = (
    "the approved Snapshot input holds text that the build should have repaired"
)
# A folder or file of the input that this app may not open stops the run
# (stage A3d-3a); the message names it, only where the run is started.
INPUT_NOT_READABLE_NEXT_STEP = (
    "allow this app to read it (on a Mac, in System Settings > Privacy & Security; "
    "on Windows, in the Security tab of its Properties), or select the Export folder itself"
)
INPUT_CHANGED_MESSAGE = (
    "input assets changed during Run-All processing; run again when the input no longer changes"
)


def input_not_readable_message(places: list[str] | None = None) -> str:
    """The message of ``INPUT_NOT_READABLE``. With ``places``, for where the
    run is started, it names the first folder or file that cannot be opened
    and how many more; without them, it names none."""
    if places is None:
        return f"this app may not open a folder or file of the input; {INPUT_NOT_READABLE_NEXT_STEP}"
    first = places[0] if places and places[0] else "the input folder or ZIP file itself"
    more = len(places) - 1
    named = first if more <= 0 else f"{first} and {more} more"
    return (
        f"this app may not open a folder or file of the input: {named}; "
        f"{INPUT_NOT_READABLE_NEXT_STEP}"
    )


def shown_message(exc: RunAllError) -> str:
    """The message of a Run-All error where the run is started: with the
    places that cannot be opened, when there are some."""
    if exc.code == "INPUT_NOT_READABLE" and exc.places is not None:
        return input_not_readable_message(exc.places)
    return exc.safe_message


REPAIRED_TEXT_MESSAGE = (
    "text with a broken character, such as a truncated emoji, is written with "
    "U+FFFD in its place; run_manifest.json lists the files"
)
# The warnings about rows left out (stages A3d-1 and A3d-1b). When a dataset
# also leaves out items that are not records or lists of records that cannot
# be read (stage A3d-2c-2), its warning names them too.
DAILY_ROWS_LEFT_OUT_MESSAGE = (
    "rows that lack a required value, such as a date, were left out; the "
    "dataset's audit record counts them by reason"
)
RECORD_ROWS_LEFT_OUT_MESSAGE = (
    "rows without a usable identifier were left out; the dataset's audit "
    "record counts them by reason"
)
ITEMS_LEFT_OUT_MESSAGE = (
    "rows that lack a required value or a usable identifier, items that are "
    "not records, or lists of records that cannot be read were left out; the "
    "dataset's audit record counts them by reason"
)
CANDIDATE_ITEMS_LEFT_OUT_MESSAGE = (
    "items that are not candidate records, or lists of candidates that cannot "
    "be read, were left out; the candidates' audit record counts them by reason"
)


def _rows_left_out_message(audit: dict[str, Any], message: str) -> str:
    """Return the message of a dataset's warning about rows left out."""
    if MARK_KINDS & set(audit.get("excluded_reason_counts") or {}):
        return ITEMS_LEFT_OUT_MESSAGE
    return message


DATASET_TABLE = (
    {"name": "activities", "family": "activities", "record_grain": "activity", "stable_key": ("garmin_activity_key",), "required": True},
    {"name": "gear", "family": "gear", "record_grain": "gear", "stable_key": ("gear_key",), "required": False},
    {"name": "activity_gear", "family": "gear", "record_grain": "activity_gear_link", "stable_key": ("gear_key", "activity_id"), "required": False},
    {"name": "personal_records", "family": "personal_records", "record_grain": "personal_record", "stable_key": ("personal_record_id",), "required": False},
    {"name": "fit_sessions", "family": "fit", "record_grain": "fit_session", "stable_key": ("fit_session_key",), "required": False},
    {"name": "fit_laps", "family": "fit", "record_grain": "fit_session_lap", "stable_key": ("fit_lap_key",), "required": False},
    {"name": "activity_fit_links", "family": "fit", "record_grain": "activity_fit_session_link", "stable_key": ("garmin_activity_key", "fit_session_key"), "required": False},
    {"name": "hill_score_daily", "family": "hill_score", "record_grain": "calendar_day", "stable_key": ("calendar_date",), "required": False},
    {"name": "endurance_score_daily", "family": "endurance_score", "record_grain": "calendar_day", "stable_key": ("calendar_date",), "required": False},
    {"name": "race_prediction_daily", "family": "race_prediction", "record_grain": "source_observation", "stable_key": ("calendar_date", "observation_timestamp"), "required": False},
    {"name": "sleep_daily", "family": "sleep", "record_grain": "sleep_day", "stable_key": ("sleep_day",), "required": False},
    {"name": "uds_daily", "family": "uds", "record_grain": "calendar_day", "stable_key": ("calendar_date",), "required": False},
    {"name": "acute_training_load_daily", "family": "acute_training_load", "record_grain": "source_observation", "stable_key": ("calendar_date", "observation_timestamp"), "required": False},
    {"name": "training_readiness_daily", "family": "training_readiness", "record_grain": "source_observation", "stable_key": ("calendar_date", "observation_timestamp"), "required": False},
    {"name": "vo2max_daily", "family": "vo2max", "record_grain": "source_observation", "stable_key": ("calendar_date", "vo2max_source_series", "sport", "observation_timestamp"), "required": False},
    {"name": "hrv_daily", "family": "hrv", "record_grain": "calendar_day", "stable_key": ("calendar_date",), "required": False},
    {"name": "training_history_daily", "family": "training_history", "record_grain": "source_observation", "stable_key": ("calendar_date", "observation_timestamp"), "required": False},
)

# Datasets whose audit record keeps, in a Snapshot run, every value that a
# later Snapshot changed, with the Snapshots that gave it, and the records that
# the latest Snapshot does not contain. A one-shot run reads one Export, so
# these lists are empty and the record has counts only.
RECORD_AUDIT_DATASETS = ("activities", "gear", "activity_gear", "personal_records")
RECORD_AUDIT_FORMAT = "garmin-running-data-normalizer-dataset-audit-v1"

# Datasets whose rows are each built from one observation: every row has an
# empty ``disagreeing_fields``, as every row of every dataset has the field.
# Activities, Gear, activity_gear, and Personal Records merge their repeated
# records instead (stage A3b), and their rows name the fields that disagree.
SINGLE_OBSERVATION_DATASETS = (
    "fit_sessions",
    "fit_laps",
    "activity_fit_links",
)

FAMILY_ORDER = (
    "activities",
    "gear",
    "personal_records",
    "fit",
    "hill_score",
    "endurance_score",
    "race_prediction",
    "sleep",
    "uds",
    "acute_training_load",
    "training_readiness",
    "vo2max",
    "hrv",
    "training_history",
)
CANDIDATE_FAMILY_ORDER = ("lactate_threshold",)
OBSERVATION_GRAIN_DATASETS = frozenset(
    {
        "race_prediction_daily",
        "acute_training_load_daily",
        "training_readiness_daily",
        "vo2max_daily",
        "training_history_daily",
    }
)
DATASET_PATHS = {
    "activities": "normalized/activities.json",
    "gear": "normalized/gear.json",
    "activity_gear": "normalized/activity_gear.json",
    "personal_records": "normalized/personal_records.json",
    "fit_sessions": "normalized/fit_sessions.json",
    "fit_laps": "normalized/fit_laps.json",
    "activity_fit_links": "normalized/activity_fit_links.json",
    "hill_score_daily": "normalized/hill_score_daily.json",
    "endurance_score_daily": "normalized/endurance_score_daily.json",
    "race_prediction_daily": "normalized/race_prediction_daily.json",
    "sleep_daily": "normalized/sleep_daily.json",
    "uds_daily": "normalized/uds_daily.json",
    "acute_training_load_daily": "normalized/acute_training_load_daily.json",
    "training_readiness_daily": "normalized/training_readiness_daily.json",
    "vo2max_daily": "normalized/vo2max_daily.json",
    "hrv_daily": "normalized/hrv_daily.json",
    "training_history_daily": "normalized/training_history_daily.json",
}
ACTIVITIES_CSV_COLUMNS = (
    "garmin_activity_key",
    "activity_date_local",
    "activity_datetime_local",
    "activity_type",
    "sport_type",
    "distance_m",
    "duration_sec",
    "avg_hr",
    "max_hr",
    "avg_power",
    "max_power",
    "avg_run_cadence",
    "training_effect_label",
    "activity_training_load",
    "lap_count",
    "elapsed_duration_sec",
    "moving_duration_sec",
    "fit_avg_vertical_oscillation_mm",
    "fit_avg_stance_time_ms",
    "fit_avg_stance_time_percent",
    "fit_avg_stance_time_balance_percent",
    "fit_avg_vertical_ratio_percent",
    "fit_avg_step_length_mm",
    "fit_total_ascent_m",
    "fit_total_descent_m",
    "disagreeing_fields",
)
# analysis/activities.csv columns converted from Activity millisecond fields.
ACTIVITIES_CSV_DURATION_COLUMNS = (
    ("elapsed_duration_sec", "elapsed_duration_ms"),
    ("moving_duration_sec", "moving_duration_ms"),
)
# analysis/activities.csv columns taken from the FIT session that an explicit
# activity_fit_links row joins to the activity; empty without such a link.
ACTIVITIES_CSV_FIT_SESSION_COLUMNS = (
    ("fit_avg_vertical_oscillation_mm", "avg_vertical_oscillation_mm"),
    ("fit_avg_stance_time_ms", "avg_stance_time_ms"),
    ("fit_avg_stance_time_percent", "avg_stance_time_percent"),
    ("fit_avg_stance_time_balance_percent", "avg_stance_time_balance_percent"),
    ("fit_avg_vertical_ratio_percent", "avg_vertical_ratio_percent"),
    ("fit_avg_step_length_mm", "avg_step_length_mm"),
    ("fit_total_ascent_m", "total_ascent"),
    ("fit_total_descent_m", "total_descent"),
)
EXTERNAL_SAFE_CSV_COLUMNS = (
    "activity_month",
    "activity_type",
    "sport_type",
    "distance_m",
    "duration_sec",
    "lap_count",
)
OUTPUT_PATHS = (
    "normalized/activities.json",
    "normalized/gear.json",
    "normalized/activity_gear.json",
    "normalized/personal_records.json",
    "normalized/fit_sessions.json",
    "normalized/fit_laps.json",
    "normalized/activity_fit_links.json",
    "normalized/hill_score_daily.json",
    "normalized/endurance_score_daily.json",
    "normalized/race_prediction_daily.json",
    "normalized/sleep_daily.json",
    "normalized/uds_daily.json",
    "normalized/acute_training_load_daily.json",
    "normalized/training_readiness_daily.json",
    "normalized/vo2max_daily.json",
    "normalized/hrv_daily.json",
    "normalized/training_history_daily.json",
    "audit/activities.json",
    "audit/gear.json",
    "audit/activity_gear.json",
    "audit/personal_records.json",
    "audit/fit_audit.json",
    "audit/activity_fit_linkage.json",
    "audit/hill_score_daily.json",
    "audit/endurance_score_daily.json",
    "audit/lactate_threshold_candidates.json",
    "audit/race_prediction_daily.json",
    "audit/sleep_daily.json",
    "audit/uds_daily.json",
    "audit/acute_training_load_daily.json",
    "audit/training_readiness_daily.json",
    "audit/vo2max_daily.json",
    "audit/hrv_daily.json",
    "audit/training_history_daily.json",
    "analysis/activities.csv",
    "analysis/performance_metrics_daily.csv",
    "qa/dataset_summary.json",
    "qa/relationship_summary.json",
    "qa/performance_metrics_summary.json",
    "qa/daily_metrics_summary.json",
    "diagnostics/source_completeness.json",
    "diagnostics/run_quality.json",
    "START_HERE.md",
    "DATASET_INVENTORY.md",
    "ANALYSIS_HANDOFF.md",
    "ANALYSIS_CONTEXT.json",
    "SCHEMA_CATALOG.json",
    "artifact_inventory.json",
    "run_manifest.json",
    "run_summary.json",
)
SNAPSHOT_LIFECYCLE_PATHS = (
    "snapshot/snapshot_lineage.json",
    "snapshot/snapshot_coverage.json",
    "snapshot/canonical_merge_summary.json",
)
# Progress events name a stage and, where useful, a step or counts. They never
# carry paths, file names, or data values.
PROGRESS_STAGES = (
    "discovering",
    "normalizing",
    "reading_fit",
    "verifying_input",
    "building_output",
    "writing_output",
)
PROGRESS_STEPS = (
    "activities",
    "gear",
    "personal_records",
    "fit",
    "performance_metrics",
    "daily_metrics",
    "relationships",
)
ProgressCallback = Callable[[dict[str, Any]], None]
INCOMPLETE_FIT_STATUSES = {
    "too_large",
    "too_small",
    "bad_header",
    "bad_header_crc",
    "bad_file_crc",
    "truncated",
    "undefined_local_message",
    "unsupported_chained",
    "session_lap_allocation_conflict",
}


class RunAllError(ValueError):
    """A fatal Run-All error with a bounded, privacy-safe public message.

    ``places`` name, for ``INPUT_NOT_READABLE``, the folders or files of the
    input that cannot be opened (stage A3d-3a). They are not part of the
    message: they are shown only where the run is started.
    """

    def __init__(self, code: str, message: str, *, places: list[str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.places = list(places) if places is not None else None


def _notify(progress: ProgressCallback | None, stage: str, **details: Any) -> None:
    if progress is not None:
        progress({"stage": stage, **details})


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_paths(input_path: str | Path, output_path: str | Path) -> tuple[Path, Path]:
    requested_input = Path(input_path)
    requested_output = Path(output_path)
    # A path that cannot be looked at, such as a name too long for the
    # system, has a code too (stage A3d-3a).
    try:
        if requested_input.is_symlink():
            raise RunAllError("INPUT_SYMLINK", "input must not be a symbolic link")
        input_root = requested_input.resolve()
        is_input = input_root.is_dir() or is_zip_input(input_root)
    except OSError as exc:
        if isinstance(exc, PermissionError):
            raise RunAllError("INPUT_NOT_READABLE", input_not_readable_message(), places=[""]) from exc
        raise RunAllError("INPUT_NOT_DIRECTORY", "input must be an existing folder or ZIP file") from exc
    if not is_input:
        raise RunAllError("INPUT_NOT_DIRECTORY", "input must be an existing folder or ZIP file")
    output_root = _requested_output(requested_output)
    if _is_within(output_root, input_root):
        raise RunAllError("OUTPUT_INSIDE_INPUT", "output directory must be outside the input directory")
    _check_output_place(output_root)
    return input_root, output_root


def _requested_output(requested_output: Path) -> Path:
    """Return the output's full path; it must be neither a symbolic link nor
    there already."""
    try:
        if requested_output.is_symlink():
            raise RunAllError("OUTPUT_SYMLINK", "output directory must not be a symbolic link")
        output_root = requested_output.resolve()
        exists = output_root.exists()
    except OSError as exc:
        code = path_error_code(requested_output, exc)
        raise RunAllError(code, OUTPUT_LOCATION_MESSAGES[code]) from exc
    if exists:
        raise RunAllError("OUTPUT_EXISTS", "output directory must not already exist")
    return output_root


def _check_output_place(output_root: Path) -> None:
    """Check the place of the output now, as the GUI checks it, instead of
    after the whole run (stage A3d-3a)."""
    try:
        check_output_location(
            output_root, lambda parent, name: output_path_too_long(parent, name, OUTPUT_PATHS)
        )
    except OutputLocationError as exc:
        raise RunAllError(exc.code, exc.safe_message) from exc


def check_run_output(output_path: str | Path) -> None:
    """Check the output of a Snapshot run before its build (stage A3d-3a)."""
    _check_output_place(_requested_output(Path(output_path)))


def _input_error(exc: Exception) -> RunAllError:
    if isinstance(exc, MixedExportsError):
        return RunAllError("INPUT_MULTIPLE_EXPORTS", exc.safe_message)
    # A folder or file that this app may not open, and one that went away
    # while the input was read (stage A3d-3a).
    if isinstance(exc, InputNotReadableError):
        return RunAllError("INPUT_NOT_READABLE", input_not_readable_message(), places=exc.places)
    if isinstance(exc, PermissionError):
        return RunAllError("INPUT_NOT_READABLE", input_not_readable_message(), places=[""])
    if isinstance(exc, (FileNotFoundError, InputChangedError)):
        return RunAllError("INPUT_CHANGED", INPUT_CHANGED_MESSAGE)
    if isinstance(exc, CorruptArchiveError):
        return RunAllError("INPUT_ZIP_CORRUPT", "the Export ZIP file is damaged or incomplete")
    if isinstance(exc, ExportTooLargeError):
        return RunAllError(
            "INPUT_TOO_LARGE",
            "the Export ZIP file is too large to read directly; extract it and use the folder",
        )
    if isinstance(exc, TempSpaceError):
        return RunAllError(
            "TEMP_SPACE_INSUFFICIENT",
            "the temporary folder does not have enough free space to read the Export ZIP file; "
            "free some space, or extract it and use the folder",
        )
    return RunAllError("INPUT_DISCOVERY_FAILED", "input discovery or archive safety validation failed")


@contextmanager
def _read_input(root: Path) -> Iterator[ExportReading]:
    """Open the input for the run: each file is read once for its digest,
    and again, one at a time, when a normalizer uses it."""
    with ExitStack() as stack:
        try:
            reading = stack.enter_context(read_export(root))
        except Exception as exc:
            raise _input_error(exc) from exc
        yield reading


def _input_snapshot(root: Path) -> tuple[tuple[str, int, str], ...]:
    """Read the input again, for its digests only."""
    try:
        with read_export(root) as reading:
            return _snapshot(reading.assets)
    except Exception as exc:
        raise _input_error(exc) from exc


def _asset_family(asset: DiscoveredAsset) -> str:
    from .diagnostics.detector import classify_source_name

    logical_name = asset.member_path or asset.source_path
    return classify_source_name(logical_name, asset.kind)


def _repaired_text_files(assets: list[DiscoveredAsset]) -> list[dict[str, Any]]:
    """The JSON files that Run-All reads whose text with a lone surrogate was
    repaired, with the number of texts and names, as the Snapshot build lists
    them by Snapshot number (stage A3d-2c-1)."""
    from .diagnostics.detector import json_read_by_run_all

    files = []
    for asset in assets:
        if asset.kind != "json" or not json_read_by_run_all(asset.member_path or asset.source_path):
            continue
        count = repaired_text_count(asset)
        if count:
            files.append(
                {
                    "source_path": asset.provenance_path,
                    "family": _asset_family(asset),
                    "repaired_text_count": count,
                }
            )
    return sorted(files, key=lambda item: item["source_path"])


def left_out_files(left_out: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Return the files left out of the run, with their family and reason (stage A3c)."""
    files = [
        {"source_path": path, "bytes": size, "family": path_family(path), "reason": reason}
        for path, size, reason in left_out
    ]
    return sorted(files, key=lambda item: item["source_path"])


# The daily datasets whose audit records count the files that they found, by
# family. In a Snapshot run, the build writes one file for each, and the
# files found are those of the Exports, as the build counted them (stage
# A3d-4a); HRV counts its FIT files itself, from their import numbers.
SNAPSHOT_COUNTED_DATASETS = {
    "hill_score_daily": "hill_score",
    "endurance_score_daily": "endurance_score",
    "race_prediction_daily": "race_prediction",
    "sleep_daily": "sleep",
    "uds_daily": "uds",
    "acute_training_load_daily": "acute_training_load",
    "training_readiness_daily": "training_readiness",
    "vo2max_daily": "vo2max",
    "training_history_daily": "training_history",
}


def _file_count(
    family: str,
    families: dict[str, list[DiscoveredAsset]],
    file_counts: Mapping[str, int] | None,
) -> int:
    """The files of a family: those of the input, or in a Snapshot run those
    of the Exports, as the build counted them (stage A3d-4a). HRV is read
    from every FIT file, as in a one-shot run."""
    if file_counts is None:
        return len(families[family])
    return int(file_counts.get("fit" if family == "hrv" else family, 0))


def _classify_assets(assets: list[DiscoveredAsset]) -> dict[str, list[DiscoveredAsset]]:
    families = {family: [] for family in (*FAMILY_ORDER, *CANDIDATE_FAMILY_ORDER)}
    for asset in assets:
        family = _asset_family(asset)
        if family in families:
            families[family].append(asset)
        if asset.kind == "fit":
            families["hrv"].append(asset)
    return families


def _snapshot(assets: list[DiscoveredAsset]) -> tuple[tuple[str, int, str], ...]:
    return tuple((asset.provenance_path, asset.size_bytes, asset.sha256) for asset in assets)


def _validate_dataset_table() -> None:
    expected = {
        "activities": ("activity", ("garmin_activity_key",), True),
        "gear": ("gear", ("gear_key",), False),
        "activity_gear": ("activity_gear_link", ("gear_key", "activity_id"), False),
        "personal_records": ("personal_record", ("personal_record_id",), False),
        "fit_sessions": ("fit_session", ("fit_session_key",), False),
        "fit_laps": ("fit_session_lap", ("fit_lap_key",), False),
        "activity_fit_links": (
            "activity_fit_session_link",
            ("garmin_activity_key", "fit_session_key"),
            False,
        ),
        "hill_score_daily": ("calendar_day", ("calendar_date",), False),
        "endurance_score_daily": ("calendar_day", ("calendar_date",), False),
        "race_prediction_daily": ("source_observation", ("calendar_date", "observation_timestamp"), False),
        "sleep_daily": ("sleep_day", ("sleep_day",), False),
        "uds_daily": ("calendar_day", ("calendar_date",), False),
        "acute_training_load_daily": ("source_observation", ("calendar_date", "observation_timestamp"), False),
        "training_readiness_daily": ("source_observation", ("calendar_date", "observation_timestamp"), False),
        "vo2max_daily": ("source_observation", ("calendar_date", "vo2max_source_series", "sport", "observation_timestamp"), False),
        "hrv_daily": ("calendar_day", ("calendar_date",), False),
        "training_history_daily": ("source_observation", ("calendar_date", "observation_timestamp"), False),
    }
    actual = {
        str(item["name"]): (str(item["record_grain"]), tuple(item["stable_key"]), bool(item["required"]))
        for item in DATASET_TABLE
    }
    if actual != expected or any(item["family"] not in FAMILY_ORDER for item in DATASET_TABLE):
        raise RunAllError("DATASET_TABLE_INVALID", "in-package dataset contract is invalid")


def _normalize_datasets(
    input_root: Path,
    families: dict[str, list[DiscoveredAsset]],
    assets: list[DiscoveredAsset],
    relationship_context: dict[str, Any] | None = None,
    snapshot_context: dict[str, Any] | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
    progress: ProgressCallback | None = None,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, RecordMerge],
    dict[str, Counter[str]],
    dict[str, InvalidValues],
    dict[str, tuple[tuple[str, ...], dict[tuple[str, ...], tuple[int, ...]]]],
]:
    records: dict[str, list[dict[str, Any]]] = {name: [] for name in DATASET_PATHS}
    # Repeated records of the same stable key become one row (stage A3b).
    merges: dict[str, RecordMerge] = {
        name: merge_repeated_records(name, []) for name in RECORD_AUDIT_DATASETS
    }
    # The rows left out without a usable identifier, by reason (stage A3d-1b).
    rows_left_out: dict[str, Counter[str]] = {
        name: Counter() for name in RECORD_AUDIT_DATASETS
    }
    # The values of another form of these datasets, left empty before their
    # repeated records are merged (stage A3d-2a).
    invalid_values: dict[str, InvalidValues] = {}

    def checked(name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        invalid_values[name] = check_values(rows, _value_types(name), STABLE_KEYS[name])
        return rows

    fit_audit: list[dict[str, Any]] = []
    fit_status_counts: Counter[str] = Counter()
    fit_invalid_value_counts: Counter[str] = Counter()
    fit_invalid_sentinel_counts: Counter[str] = Counter()
    incomplete_fit_count = 0
    performance_audit: dict[str, Any] = {}

    _notify(progress, "normalizing", step="activities")
    try:
        merges["activities"] = merge_repeated_records(
            "activities",
            checked(
                "activities",
                normalize_activities(
                    str(input_root),
                    timezone_name,
                    assets=assets,
                    left_out=rows_left_out["activities"],
                ),
            ),
        )
        records["activities"] = merges["activities"].rows
    except Exception as exc:
        raise RunAllError("ACTIVITIES_NORMALIZATION_FAILED", "detected Activities input could not be normalized") from exc
    if not records["activities"]:
        raise RunAllError("ACTIVITIES_EMPTY", "Activities input produced no valid records")

    if families["gear"]:
        _notify(progress, "normalizing", step="gear")
        try:
            gear_rows, link_rows = normalize_gear(
                str(input_root), assets=assets, left_out=rows_left_out
            )
            merges["gear"] = merge_repeated_records("gear", checked("gear", gear_rows))
            merges["activity_gear"] = merge_repeated_records(
                "activity_gear", checked("activity_gear", link_rows)
            )
            records["gear"] = merges["gear"].rows
            records["activity_gear"] = merges["activity_gear"].rows
        except Exception as exc:
            raise RunAllError("GEAR_NORMALIZATION_FAILED", "detected Gear input could not be normalized") from exc

    if families["personal_records"]:
        _notify(progress, "normalizing", step="personal_records")
        try:
            merges["personal_records"] = merge_repeated_records(
                "personal_records",
                checked(
                    "personal_records",
                    normalize_personal_records(
                        str(input_root),
                        assets=assets,
                        left_out=rows_left_out["personal_records"],
                    ),
                ),
            )
            records["personal_records"] = merges["personal_records"].rows
        except Exception as exc:
            raise RunAllError(
                "PERSONAL_RECORDS_NORMALIZATION_FAILED",
                "detected Personal Records input could not be normalized",
            ) from exc

    if families["fit"]:
        _notify(progress, "normalizing", step="fit")
        try:
            records["fit_sessions"], records["fit_laps"], base_audit = parse_fit_export(
                input_root,
                timezone_name=timezone_name,
                progress=progress,
                assets=assets,
            )
            # The build writes each FIT file once: in a Snapshot run, its
            # places are counted as a one-shot run of each Export counts
            # them, from the import number of each occurrence (stage A3d-4a).
            fit_numbers = (snapshot_context or {}).get("fit_snapshot_numbers")
            if fit_numbers is not None:
                for item in base_audit:
                    aliases = 1 + copies_within_snapshots(
                        fit_numbers.get(str(item["source_sha256"]))
                    )
                    item["source_alias_count"] = aliases
                    item["duplicate_source_alias_count"] = aliases - 1
            # The values of another form in the sessions and laps of a FIT
            # file are left empty and kept in its audit entry (stage A3d-2a).
            audit_by_file = {str(item["fit_file_id"]): item for item in base_audit}
            for dataset, key_field in (("fit_sessions", "fit_session_key"), ("fit_laps", "fit_lap_key")):
                rows_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in records[dataset]:
                    rows_by_file[str(row["fit_file_id"])].append(row)
                types = _value_types(dataset)
                for file_id, rows in sorted(rows_by_file.items()):
                    found = check_values(rows, types, (key_field,)).audit_fields()
                    if not found:
                        continue
                    item = audit_by_file[file_id]
                    counts = item.setdefault("invalid_value_counts", {})
                    for field, count in found["invalid_value_counts"].items():
                        counts[f"{dataset}.{field}"] = count
                    item.setdefault("invalid_values", []).extend(
                        {**entry, "field": f"{dataset}.{entry['field']}"}
                        for entry in found["invalid_values"]
                    )
                    fit_invalid_value_counts[dataset] += sum(found["invalid_value_counts"].values())
            for item in base_audit:
                unknown_records = int(item.get("unknown_records", 0) or 0)
                fit_audit.append(item)
                status = str(item["parse_status"])
                fit_status_counts[status] += 1
                sentinel_counts = item.get("invalid_sentinel_counts", {})
                if isinstance(sentinel_counts, dict):
                    fit_invalid_sentinel_counts.update(
                        {
                            str(field): int(count)
                            for field, count in sentinel_counts.items()
                        }
                    )
                if status in INCOMPLETE_FIT_STATUSES or unknown_records > 0:
                    incomplete_fit_count += 1
        except Exception as exc:
            raise RunAllError("FIT_PROCESSING_FAILED", "detected FIT input could not be audited") from exc

    all_metric_assets = [
        asset
        for family in ("hill_score", "endurance_score", "lactate_threshold")
        for asset in families[family]
    ]
    _notify(progress, "normalizing", step="performance_metrics")
    try:
        hill_result = normalize_hill_score(all_metric_assets)
        endurance_result = normalize_endurance_score(all_metric_assets)
        lactate_candidates = collect_lactate_threshold_candidates(all_metric_assets)
    except PerformanceMetricsError as exc:
        raise RunAllError(
            "PERFORMANCE_METRICS_NORMALIZATION_FAILED",
            "detected performance metric input could not be normalized",
        ) from exc
    records["hill_score_daily"] = hill_result.records
    records["endurance_score_daily"] = endurance_result.records
    performance_audit = {
        "hill_score_daily": hill_result.audit,
        "endurance_score_daily": endurance_result.audit,
        "lactate_threshold": lactate_candidates,
    }

    _notify(progress, "normalizing", step="daily_metrics")
    try:
        daily_results = {
            "race_prediction_daily": normalize_race_prediction(
                families["race_prediction"]
            ),
            "sleep_daily": normalize_sleep_daily_assets(
                families["sleep"],
                timezone_name=timezone_name,
            ),
            "uds_daily": normalize_uds(families["uds"]),
            "acute_training_load_daily": normalize_acute_training_load(
                families["acute_training_load"]
            ),
            "training_readiness_daily": normalize_training_readiness(
                families["training_readiness"]
            ),
            "vo2max_daily": normalize_vo2max(families["vo2max"]),
            "training_history_daily": normalize_training_history(
                families["training_history"]
            ),
        }
        for dataset_name, result in daily_results.items():
            records[dataset_name] = result.records
            performance_audit[dataset_name] = result.audit
        hrv_result = normalize_hrv_daily_assets(
            families["hrv"],
            timezone_name=timezone_name,
            snapshot_numbers=(
                snapshot_context.get("fit_snapshot_numbers")
                if snapshot_context is not None
                else None
            ),
        )
        records["hrv_daily"] = hrv_result["records"]
        performance_audit["hrv_daily"] = hrv_result["audit"]
    except DailyMetricError as exc:
        raise RunAllError(
            "DAILY_METRICS_NORMALIZATION_FAILED",
            "detected daily metric input could not be normalized",
        ) from exc

    # In a Snapshot run, the Snapshots that observed each row, by the row's
    # stable key, for the observations of Source Completeness (stage A3d-4c-2).
    observed: dict[str, tuple[tuple[str, ...], dict[tuple[str, ...], tuple[int, ...]]]] = {}
    if snapshot_context is not None:
        for name in RECORD_AUDIT_DATASETS:
            observed[name] = _observed_by_key(
                merges[name].rows, merges[name].row_snapshot_numbers, STABLE_KEYS[name]
            )
        for name, metric_result in (
            ("hill_score_daily", hill_result),
            ("endurance_score_daily", endurance_result),
        ):
            observed[name] = _observed_by_key(
                metric_result.records, metric_result.row_snapshot_numbers, ("calendar_date",)
            )
        for name, result in daily_results.items():
            observed[name] = _observed_by_key(
                result.records, result.row_snapshot_numbers, tuple(result.audit["stable_key"])
            )
        observed["hrv_daily"] = _observed_by_key(
            hrv_result["records"], hrv_result.get("row_snapshot_numbers", []), ("calendar_date",)
        )

    file_counts = (snapshot_context or {}).get("family_file_counts")
    if file_counts is not None:
        for dataset, family in SNAPSHOT_COUNTED_DATASETS.items():
            audit = performance_audit.get(dataset)
            if isinstance(audit, dict) and "detected_asset_count" in audit:
                audit["detected_asset_count"] = _file_count(family, families, file_counts)

    # The build passes the Lactate Threshold candidates only, and the Hill and
    # Endurance rows without their private fields: in a Snapshot run, the
    # audit records take the counts of the Exports from the build, as a
    # one-shot run counts them (stage A3d-4b). The build's own figures for
    # the candidates stay in its merge summary.
    lactate_counts = (snapshot_context or {}).get("lactate_threshold_counts")
    if lactate_counts is not None:
        performance_audit["lactate_threshold"]["family_asset_counts"] = dict(
            lactate_counts["family_asset_counts"]
        )
        performance_audit["lactate_threshold"]["family_source_record_counts"] = dict(
            lactate_counts["family_source_record_counts"]
        )
    private_counts = (snapshot_context or {}).get("private_field_counts")
    if private_counts is not None:
        for dataset in ("hill_score_daily", "endurance_score_daily"):
            performance_audit[dataset]["excluded_private_field_presence_counts"] = dict(
                private_counts.get(dataset, {})
            )

    _notify(progress, "normalizing", step="relationships")
    try:
        relationship_summary = validate_declared_relationships(
            records,
            current_activity_ids=(
                set(relationship_context["current_activity_ids"])
                if relationship_context is not None
                and "current_activity_ids" in relationship_context
                else None
            ),
            current_gear_keys=(
                set(relationship_context["current_gear_keys"])
                if relationship_context is not None
                and "current_gear_keys" in relationship_context
                else None
            ),
            current_fit_session_keys=(
                set(relationship_context["current_fit_session_keys"])
                if relationship_context is not None
                and "current_fit_session_keys" in relationship_context
                else None
            ),
        )
        (
            records["activity_fit_links"],
            activity_fit_audit,
            activity_fit_metrics,
        ) = build_activity_fit_relationship(
            records["activities"],
            records["fit_sessions"],
        )
        relationship_summary["relationships"]["activities_to_fit_sessions"] = (
            activity_fit_metrics
        )
    except RelationshipContractError as exc:
        raise RunAllError(
            "RELATIONSHIP_CONTRACT_FAILED",
            "a declared dataset relationship failed validation",
        ) from exc
    for name in SINGLE_OBSERVATION_DATASETS:
        for record in records[name]:
            record["disagreeing_fields"] = []

    return (
        records,
        fit_audit,
        {
            "incomplete_fit_count": incomplete_fit_count,
            "invalid_sentinel_count": sum(fit_invalid_sentinel_counts.values()),
            "invalid_sentinel_counts": dict(
                sorted(fit_invalid_sentinel_counts.items())
            ),
            **{
                f"status_{key}": value
                for key, value in sorted(fit_status_counts.items())
            },
            **(
                {"invalid_value_counts": dict(sorted(fit_invalid_value_counts.items()))}
                if fit_invalid_value_counts
                else {}
            ),
        },
        activity_fit_audit,
        relationship_summary,
        performance_audit,
        merges,
        rows_left_out,
        invalid_values,
        observed,
    )


def _observed_by_key(
    rows: list[dict[str, Any]],
    numbers: list[tuple[int, ...]],
    key_fields: tuple[str, ...],
) -> tuple[tuple[str, ...], dict[tuple[str, ...], tuple[int, ...]]]:
    """Return the key fields of a dataset and the Snapshots that observed its
    rows by their keys: the relationships later sort, leave out, or rebuild
    rows, and their keys stay (stage A3d-4c-2)."""
    return key_fields, {
        tuple(str(row.get(field)) for field in key_fields): snapshots
        for row, snapshots in zip(rows, numbers)
    }


def _snapshot_observations(
    records: dict[str, list[dict[str, Any]]],
    observed: dict[str, tuple[tuple[str, ...], dict[tuple[str, ...], tuple[int, ...]]]],
    fit_numbers: dict[str, list[int]],
    numbers: list[int],
) -> dict[int, dict[str, int]]:
    """Count, for each Snapshot, the rows of each family that it observed, as
    a one-shot run of its Export counts the rows of the family's datasets
    (stage A3d-4c-2). The rows that a FIT file gives, its sessions, laps,
    links, and HRV dates, belong to the Snapshots that hold the file."""
    from .diagnostics.contracts import FAMILY_DATASETS, SOURCE_FAMILY_ORDER

    counts = {number: {family: 0 for family in SOURCE_FAMILY_ORDER} for number in numbers}
    for family, datasets in FAMILY_DATASETS.items():
        for dataset in datasets:
            key_fields, by_key = observed.get(dataset, ((), {}))
            for row in records[dataset]:
                if dataset in ("fit_sessions", "fit_laps"):
                    snapshots = set(fit_numbers.get(str(row.get("source_sha256"))) or ())
                elif dataset == "activity_fit_links":
                    snapshots = set(fit_numbers.get(str(row.get("fit_source_sha256"))) or ())
                else:
                    snapshots = set(by_key.get(tuple(str(row.get(field)) for field in key_fields), ()))
                for number in snapshots & set(counts):
                    counts[number][family] += 1
    return counts


def _invalid_value_counts(
    family: str,
    record_audits: dict[str, dict[str, Any]],
    performance_audit: dict[str, Any],
    fit_status: dict[str, Any],
    daily_dataset_by_family: dict[str, str],
) -> list[tuple[str, int]]:
    """The values of another form of each dataset of a family, by dataset."""
    if family == "fit":
        counts = dict(fit_status.get("invalid_value_counts") or {})
    else:
        audits = {
            name: record_audits[name]
            for name in {
                "activities": ("activities",),
                "gear": ("gear", "activity_gear"),
                "personal_records": ("personal_records",),
            }.get(family, ())
        }
        if family in daily_dataset_by_family:
            name = daily_dataset_by_family[family]
            audits[name] = performance_audit.get(name, {})
        counts = {
            name: sum(int(count) for count in (audit.get("invalid_value_counts") or {}).values())
            for name, audit in audits.items()
        }
    return [(name, int(count)) for name, count in counts.items() if count]


def _value_types(dataset: str) -> dict[str, str]:
    """The logical type of each value field of a normalized dataset: not
    ``disagreeing_fields``, which the merge of repeated records adds, nor the
    identifiers, which their own rules read (stage A3d-1b)."""
    from .output_experience import DATASET_FIELDS, _field_descriptor

    skipped = identifier_fields(dataset) | {"disagreeing_fields"}
    return {
        field: str(_field_descriptor(dataset, field)["logical_type"])
        for field in DATASET_FIELDS[dataset]
        if field not in skipped
    }


def _record_audits(
    records: dict[str, list[dict[str, Any]]],
    snapshot_context: dict[str, Any] | None,
    merges: dict[str, RecordMerge],
    rows_left_out: dict[str, Counter[str]] | None = None,
    invalid_values: dict[str, InvalidValues] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return the audit records of Activities, Gear, activity_gear, and Personal Records.

    In a Snapshot run, ``updates`` lists, for each record whose values changed
    in a later Snapshot, each changed field with its values in Snapshot order
    and the Snapshots that gave each value; ``not_in_latest_snapshot`` lists
    the records kept although the latest Snapshot does not contain them, and
    ``removed_links`` the activity_gear links left out because the latest
    Snapshot has Gear links and their Activity and Gear, but not them.

    When repeated records were merged (stage A3b), the record also counts
    the copies with the same values, the observations without a value,
    and the keys whose values disagree, and lists every disagreeing value;
    these keys appear only when there is something to count, so that an
    Export without repeated records gives the same bytes as before. So do the
    counts of the rows left out without a usable identifier, by reason, as
    the daily audit records count theirs (stage A3d-1b), the values of
    another form that were left empty, with the keys of their records
    (stage A3d-2a), and the items left out that are not records, by reason,
    and those that are empty values (stage A3d-2c-2).
    """
    changes = (
        snapshot_context.get("record_changes") or {}
        if snapshot_context is not None
        else {}
    )
    audits: dict[str, dict[str, Any]] = {}
    for name in RECORD_AUDIT_DATASETS:
        change = changes.get(name, {})
        updates = list(change.get("updates", []))
        not_in_latest = list(change.get("not_in_latest_snapshot", []))
        audit = {
            "format": RECORD_AUDIT_FORMAT,
            "dataset": name,
            "observation_scope": (
                "REGISTERED_SNAPSHOT_OBSERVATIONS"
                if snapshot_context is not None
                else "ONE_EXPORT_OBSERVATION"
            ),
            "record_count": len(records[name]),
            "updated_record_count": len(updates),
            "updates": updates,
            "not_in_latest_snapshot_count": len(not_in_latest),
            "not_in_latest_snapshot": not_in_latest,
        }
        if name == "activity_gear":
            removed = list(change.get("removed_links", []))
            audit["removed_link_count"] = len(removed)
            audit["removed_links"] = removed
        merge = merges[name]
        # In a Snapshot run, the build counts the copies within the Snapshots
        # of earlier time points, and the merge those of the last one.
        copies = merge.same_value_duplicate_count + int(change.get("earlier_copy_count", 0))
        if copies:
            audit["same_value_duplicate_count"] = copies
        if merge.absent_value_counts:
            audit["absent_value_counts"] = dict(merge.absent_value_counts)
        if merge.disagreements:
            audit["disagreement_key_count"] = len(merge.disagreements)
            audit["disagreements"] = list(merge.disagreements)
        left_out = Counter((rows_left_out or {}).get(name) or {})
        # Items that are empty values, counted apart and not announced, as the
        # daily audit records count their empty records (stage A3d-2c-2).
        empty_record_count = left_out.pop(EMPTY_RECORD, 0)
        if left_out:
            audit["excluded_record_count"] = sum(left_out.values())
            audit["excluded_reason_counts"] = dict(sorted(left_out.items()))
        if empty_record_count:
            audit["empty_record_count"] = empty_record_count
        invalid = (invalid_values or {}).get(name)
        if invalid is not None:
            audit.update(invalid.audit_fields())
        audits[name] = audit
    return audits


def _canonical_key(record: dict[str, Any], fields: tuple[str, ...]) -> tuple[str, ...] | None:
    values = [record.get(field) for field in fields]
    if any(value in (None, "") for value in values):
        return None
    return tuple(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) for value in values)


def _dataset_qa(
    dataset: dict[str, Any],
    records: list[dict[str, Any]],
    source_count: int,
) -> dict[str, Any]:
    try:
        json.dumps(records, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise RunAllError("DATASET_NOT_SERIALIZABLE", "normalized dataset is not JSON serializable") from exc

    key_fields = tuple(dataset["stable_key"])
    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    missing_key_count = 0
    for record in records:
        key = _canonical_key(record, key_fields)
        if key is None:
            missing_key_count += 1
            continue
        grouped[key].append(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if missing_key_count:
        raise RunAllError("STABLE_KEY_MISSING", "normalized dataset contains a missing stable key")
    divergent_duplicates = sum(1 for values in grouped.values() if len(values) > 1 and len(set(values)) > 1)
    if divergent_duplicates:
        raise RunAllError("DIVERGENT_DUPLICATE", "normalized dataset contains a divergent duplicate key")
    duplicate_extra_rows = sum(max(len(values) - 1, 0) for values in grouped.values())
    return {
        "dataset": dataset["name"],
        "record_grain": dataset["record_grain"],
        "stable_key": list(key_fields),
        "source_count": source_count,
        "record_count": len(records),
        "missing_key_count": 0,
        "duplicate_extra_rows": duplicate_extra_rows,
        "divergent_duplicate_key_count": 0,
        "json_serializable": True,
        "records_sha256": deterministic_records_digest(records),
        "status": "PASS",
    }


def _validate_provenance(
    records: dict[str, list[dict[str, Any]]],
    fit_audit: list[dict[str, Any]],
    families: dict[str, list[DiscoveredAsset]],
) -> None:
    sources = {
        family: {(asset.provenance_path, asset.sha256) for asset in assets}
        for family, assets in families.items()
    }
    for dataset in DATASET_TABLE:
        if dataset["name"] in {
            "hill_score_daily",
            "endurance_score_daily",
            "race_prediction_daily",
            "sleep_daily",
            "uds_daily",
            "acute_training_load_daily",
            "training_readiness_daily",
            "vo2max_daily",
            "hrv_daily",
            "training_history_daily",
        }:
            continue
        if dataset["name"] == "activity_fit_links":
            for record in records["activity_fit_links"]:
                activity_source = (
                    str(record.get("activity_source_path")),
                    str(record.get("activity_source_sha256")),
                )
                fit_source = (
                    str(record.get("fit_source_path")),
                    str(record.get("fit_source_sha256")),
                )
                if (
                    activity_source not in sources["activities"]
                    or fit_source not in sources["fit"]
                ):
                    raise RunAllError(
                        "PROVENANCE_MISMATCH",
                        "relationship provenance does not match discovered input",
                    )
            continue
        expected = sources[str(dataset["family"])]
        for record in records[str(dataset["name"])]:
            actual = (str(record.get("source_path")), str(record.get("source_sha256")))
            if actual not in expected:
                raise RunAllError("PROVENANCE_MISMATCH", "normalized dataset provenance does not match discovered input")
    for record in fit_audit:
        actual = (str(record.get("source_path")), str(record.get("source_sha256")))
        if actual not in sources["fit"]:
            raise RunAllError("PROVENANCE_MISMATCH", "FIT audit provenance does not match discovered input")


def _seconds_from_milliseconds(value: Any) -> float | None:
    return float(value) / 1000.0 if isinstance(value, (int, float)) else None


def _activities_csv(
    records: list[dict[str, Any]],
    fit_links: list[dict[str, Any]],
    fit_sessions: list[dict[str, Any]],
) -> bytes:
    sessions_by_key = {str(session["fit_session_key"]): session for session in fit_sessions}
    linked_sessions = {
        str(link["garmin_activity_key"]): sessions_by_key.get(str(link["fit_session_key"]))
        for link in fit_links
        if link.get("match_status") == "explicit" and link.get("ambiguous") is False
    }
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=ACTIVITIES_CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for record in sorted(records, key=lambda item: (str(item["garmin_activity_key"]), str(item["source_path"]))):
        row = dict(record)
        for column, source in ACTIVITIES_CSV_DURATION_COLUMNS:
            row[column] = _seconds_from_milliseconds(record.get(source))
        session = linked_sessions.get(str(record["garmin_activity_key"])) or {}
        for column, source in ACTIVITIES_CSV_FIT_SESSION_COLUMNS:
            row[column] = session.get(source)
        row["disagreeing_fields"] = _field_names_cell(record.get("disagreeing_fields"))
        writer.writerow(row)
    return stream.getvalue().encode("utf-8")


def _field_names_cell(names: Any) -> str:
    """Write a list of field names in one CSV cell, separated by ``;``."""
    return ";".join(str(name) for name in names or ())


def _performance_metrics_csv(
    hill_rows: list[dict[str, Any]],
    endurance_rows: list[dict[str, Any]],
) -> bytes:
    fields = (
        "calendar_date",
        *(f"hill_{field}" for field in HILL_FIELDS[1:]),
        *(f"endurance_{field}" for field in ENDURANCE_FIELDS[1:]),
        "hill_disagreeing_fields",
        "endurance_disagreeing_fields",
    )
    disagreeing = {
        prefix: {
            str(row["calendar_date"]): _field_names_cell(row.get("disagreeing_fields"))
            for row in rows
        }
        for prefix, rows in (("hill", hill_rows), ("endurance", endurance_rows))
    }
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in build_performance_metrics_daily_context(hill_rows, endurance_rows):
        date = str(row["calendar_date"])
        for prefix, by_date in disagreeing.items():
            row[f"{prefix}_disagreeing_fields"] = by_date.get(date)
        writer.writerow(row)
    return stream.getvalue().encode("utf-8")


def _daily_observation_projection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe a non-canonical day-level view without selecting a source row."""
    counts = Counter(str(row["calendar_date"]) for row in rows)
    timestamps = sorted(
        str(row["observation_timestamp"])
        for row in rows
        if row.get("observation_timestamp") not in (None, "")
    )
    return {
        "status": "DERIVED_NON_CANONICAL",
        "selection_rule": None,
        "source_observations_preserved": True,
        "calendar_date_count": len(counts),
        "multiple_observation_date_count": sum(
            1 for count in counts.values() if count > 1
        ),
        "maximum_observation_count_per_date": max(counts.values(), default=0),
        "first_observation_timestamp": timestamps[0] if timestamps else None,
        "last_observation_timestamp": timestamps[-1] if timestamps else None,
    }


def _external_safe_pack(
    activities: list[dict[str, Any]],
    *,
    run_status: str,
    warnings: list[dict[str, Any]],
) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=EXTERNAL_SAFE_CSV_COLUMNS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for record in sorted(
        activities,
        key=lambda item: (
            str(item.get("activity_date_local", ""))[:7],
            str(item.get("activity_type", "")),
            str(item.get("distance_m", "")),
            str(item.get("duration_sec", "")),
        ),
    ):
        writer.writerow(
            {
                **record,
                "activity_month": str(record.get("activity_date_local", ""))[:7],
            }
        )
    safe_schema = {
        "format": "garmin-running-data-normalizer-external-safe-schema-v1",
        "dataset": "safe/activities_monthly.csv",
        "grain": "activity_with_month_only",
        "fields": list(EXTERNAL_SAFE_CSV_COLUMNS),
        "excluded": [
            "source paths",
            "filenames",
            "source hashes",
            "raw IDs and stable keys",
            "memo text",
            "coordinates",
            "exact dates and timestamps",
            "heart rate, power, cadence, training effect, and training load",
            "health and performance detail not required by this volume profile",
            "unallowlisted artifacts",
        ],
    }
    safe_context = {
        "format": "garmin-running-data-normalizer-external-safe-context-v1",
        "privacy_mode": "external_safe",
        "run_status": run_status,
        "warnings": [
            {
                "code": str(item.get("code", "UNSPECIFIED_WARNING")),
                "family": item.get("family"),
                "count": item.get("count"),
            }
            for item in warnings
        ],
        "analysis_entry_point": "safe/activities_monthly.csv",
        "relationships": [],
        "prohibited_operations": [
            "identity_inference",
            "location_inference",
            "timestamp_only_join",
            "join_to_unlisted_data",
            "medical_or_coaching_interpretation",
        ],
        "automatic_upload": False,
    }
    readme = (
        "# External-safe Analysis Handoff\n\n"
        "This deterministic pack contains an explicit, reviewable allowlist. "
        "It does not upload itself. The activity calendar is reduced to month "
        "granularity, and identifiers, provenance, hashes, memo text, coordinates, "
        "exact timestamps, heart rate, power, cadence, training effect, and "
        "training load are excluded. The default profile is limited to activity "
        "volume and count context.\n\n"
        "Use only the listed CSV and JSON files. Preserve missing values, report "
        "denominators, and do not infer identity, location, or unsupported joins.\n"
    ).encode("utf-8")
    pack, _ = build_analysis_pack_payloads(
        {
            "README.md": readme,
            "safe/activities_monthly.csv": stream.getvalue().encode("utf-8"),
            "safe/ANALYSIS_CONTEXT.json": _json_bytes(safe_context),
            "safe/SCHEMA_CATALOG.json": _json_bytes(safe_schema),
        }
    )
    return pack


def _family_results(
    families: dict[str, list[DiscoveredAsset]],
    records: dict[str, list[dict[str, Any]]],
    fit_status: dict[str, Any],
    performance_audit: dict[str, Any],
    relationship_summary: dict[str, Any],
    record_audits: dict[str, dict[str, Any]],
    repaired_text_by_family: dict[str, int] | None = None,
    file_counts: Mapping[str, int] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], str]:
    repaired_text_by_family = repaired_text_by_family or {}
    warnings: list[dict[str, Any]] = []
    results: dict[str, dict[str, Any]] = {}
    # A link removed in a later Snapshot counts as an update of the Gear family.
    record_audit_datasets = {
        "activities": ("activities",),
        "gear": ("gear", "activity_gear"),
        "personal_records": ("personal_records",),
    }
    family_record_counts = {
        "activities": len(records["activities"]),
        "gear": len(records["gear"]) + len(records["activity_gear"]),
        "personal_records": len(records["personal_records"]),
        "fit": (
            len(records["fit_sessions"])
            + len(records["fit_laps"])
            + len(records["activity_fit_links"])
        ),
        "hill_score": len(records["hill_score_daily"]),
        "endurance_score": len(records["endurance_score_daily"]),
        "race_prediction": len(records["race_prediction_daily"]),
        "sleep": len(records["sleep_daily"]),
        "uds": len(records["uds_daily"]),
        "acute_training_load": len(records["acute_training_load_daily"]),
        "training_readiness": len(records["training_readiness_daily"]),
        "vo2max": len(records["vo2max_daily"]),
        "hrv": len(records["hrv_daily"]),
        "training_history": len(records["training_history_daily"]),
    }
    quiet_optional_families = {
        "hill_score",
        "endurance_score",
        "race_prediction",
        "sleep",
        "uds",
        "acute_training_load",
        "training_readiness",
        "vo2max",
        "hrv",
        "training_history",
    }
    daily_dataset_by_family = {
        "hill_score": "hill_score_daily",
        "endurance_score": "endurance_score_daily",
        "race_prediction": "race_prediction_daily",
        "sleep": "sleep_daily",
        "uds": "uds_daily",
        "acute_training_load": "acute_training_load_daily",
        "training_readiness": "training_readiness_daily",
        "vo2max": "vo2max_daily",
        "hrv": "hrv_daily",
        "training_history": "training_history_daily",
    }
    incomplete_fit_count = int(fit_status.get("incomplete_fit_count", 0))
    for family in FAMILY_ORDER:
        detected = _file_count(family, families, file_counts)
        if (
            family == "hrv"
            and int(performance_audit["hrv_daily"].get("source_record_count", 0))
            == 0
        ):
            detected = 0
        family_warnings = 0
        status = "PROCESSED"
        skipped = 0
        if family != "activities" and detected == 0:
            status = "SKIPPED_NOT_PRESENT"
            if family not in quiet_optional_families:
                family_warnings += 1
                warnings.append({
                    "code": "OPTIONAL_FAMILY_NOT_PRESENT",
                    "family": family,
                    "message": "optional dataset family was not present",
                })
        elif family != "activities" and family_record_counts[family] == 0:
            status = "PROCESSED_EMPTY"
            family_warnings += 1
            warnings.append({
                "code": "OPTIONAL_FAMILY_EMPTY",
                "family": family,
                "message": "optional dataset family produced no normalized records",
            })
        review_item_count = 0
        disagreement_key_count = 0
        left_out_row_count = 0
        if family in daily_dataset_by_family:
            audit = performance_audit[daily_dataset_by_family[family]]
            # Rows left out that hold a value (stage A3d-1); the rows that hold
            # none are counted apart in the audit and not announced.
            left_out_row_count = int(audit.get("excluded_record_count", 0))
            if left_out_row_count:
                family_warnings += 1
                warnings.append(
                    {
                        "code": "DATA_ROW_LEFT_OUT",
                        "family": family,
                        "dataset": daily_dataset_by_family[family],
                        "count": left_out_row_count,
                        "message": _rows_left_out_message(audit, DAILY_ROWS_LEFT_OUT_MESSAGE),
                    }
                )
            # No dataset of Run-All gives review items since stage A3d-2b,
            # when HRV readings joined the rules of the other daily datasets.
            review_item_count = int(
                audit.get("review_required_count", 0)
                or audit.get("review_item_count", 0)
                or audit.get("review_key_count", 0)
            )
            disagreement_key_count = int(audit.get("disagreement_key_count", 0))
            if review_item_count:
                family_warnings += 1
                warnings.append(
                    {
                        "code": "DAILY_METRICS_REVIEW_REQUIRED",
                        "family": family,
                        "count": review_item_count,
                        "message": "one or more daily metric observations require review",
                    }
                )
            if disagreement_key_count:
                family_warnings += 1
                warnings.append(
                    {
                        "code": "VALUES_DISAGREE",
                        "family": family,
                        "count": disagreement_key_count,
                        "message": (
                            "observations of one or more stable keys have different values; "
                            "those fields are empty and the audit keeps every observed value"
                        ),
                    }
                )
        # Rows left out without a usable identifier (stage A3d-1b): one
        # warning for each dataset, so that Gear and its links are told apart.
        for name in record_audit_datasets.get(family, ()):
            dataset_left_out = int(record_audits[name].get("excluded_record_count", 0))
            if dataset_left_out:
                left_out_row_count += dataset_left_out
                family_warnings += 1
                warnings.append(
                    {
                        "code": "DATA_ROW_LEFT_OUT",
                        "family": family,
                        "dataset": name,
                        "count": dataset_left_out,
                        "message": _rows_left_out_message(
                            record_audits[name], RECORD_ROWS_LEFT_OUT_MESSAGE
                        ),
                    }
                )
        # Values of another form, left empty (stage A3d-2a): one warning for
        # each dataset of the family, as for the rows left out.
        invalid_value_count = 0
        for name, count in _invalid_value_counts(
            family,
            record_audits,
            performance_audit,
            fit_status,
            daily_dataset_by_family,
        ):
            invalid_value_count += count
            family_warnings += 1
            warnings.append(
                {
                    "code": "DATA_VALUE_INVALID",
                    "family": family,
                    "dataset": name,
                    "count": count,
                    "message": (
                        "values of a form that their field does not take were left "
                        "empty; the audit records keep them"
                    ),
                }
            )
        # Text with a lone surrogate, repaired as it was read (stage A3d-2c-1).
        repaired_text = int(repaired_text_by_family.get(family, 0))
        if repaired_text:
            family_warnings += 1
            warnings.append(
                {
                    "code": "DATA_TEXT_REPAIRED",
                    "family": family,
                    "count": repaired_text,
                    "message": REPAIRED_TEXT_MESSAGE,
                }
            )
        # Repeated records whose values disagree (stage A3b).
        record_disagreement_count = sum(
            int(record_audits[name].get("disagreement_key_count", 0))
            for name in record_audit_datasets.get(family, ())
        )
        if record_disagreement_count:
            disagreement_key_count = record_disagreement_count
            family_warnings += 1
            warnings.append(
                {
                    "code": "VALUES_DISAGREE",
                    "family": family,
                    "count": record_disagreement_count,
                    "message": (
                        "observations of one or more stable keys have different values; "
                        "those fields are empty and the audit keeps every observed value"
                    ),
                }
            )
        updated_record_count = sum(
            int(record_audits[name]["updated_record_count"])
            + int(record_audits[name].get("removed_link_count", 0))
            for name in record_audit_datasets.get(family, ())
        )
        not_in_latest_snapshot_count = sum(
            int(record_audits[name]["not_in_latest_snapshot_count"])
            for name in record_audit_datasets.get(family, ())
        )
        if updated_record_count:
            family_warnings += 1
            warnings.append(
                {
                    "code": "VALUES_UPDATED",
                    "family": family,
                    "count": updated_record_count,
                    "message": (
                        "a later Snapshot changed values of one or more records; "
                        "the normalized datasets hold the latest values and the "
                        "audit keeps the earlier ones"
                    ),
                }
            )
        if not_in_latest_snapshot_count:
            family_warnings += 1
            warnings.append(
                {
                    "code": "RECORDS_NOT_IN_LATEST_SNAPSHOT",
                    "family": family,
                    "count": not_in_latest_snapshot_count,
                    "message": (
                        "the latest Snapshot does not contain one or more records; "
                        "they are kept, and the audit names the last Snapshot "
                        "that contained each"
                    ),
                }
            )
        if family == "fit" and incomplete_fit_count:
            status = "PARTIAL"
            skipped = incomplete_fit_count
            family_warnings += 1
            warnings.append({
                "code": "FIT_PARSE_INCOMPLETE",
                "family": "fit",
                "count": incomplete_fit_count,
                "message": "one or more FIT assets were not completely parsed",
            })
        results[family] = {
            "status": status,
            "detected_asset_count": detected,
            "processed_asset_count": detected,
            "skipped_asset_count": skipped,
            "record_count": family_record_counts[family],
            "warning_count": family_warnings,
            "error_count": 0,
            "review_required_count": review_item_count,
            "review_item_count": review_item_count,
            "disagreement_key_count": disagreement_key_count,
            "updated_record_count": updated_record_count,
            "not_in_latest_snapshot_count": not_in_latest_snapshot_count,
        }
        if left_out_row_count:
            results[family]["left_out_row_count"] = left_out_row_count
        if invalid_value_count:
            results[family]["invalid_value_count"] = invalid_value_count
        if repaired_text:
            results[family]["repaired_text_count"] = repaired_text
        if family == "fit":
            results[family]["parse_status_counts"] = {
                key.removeprefix("status_"): value
                for key, value in sorted(fit_status.items())
                if key.startswith("status_")
            }
            results[family]["incomplete_asset_count"] = incomplete_fit_count
            results[family]["invalid_sentinel_count"] = int(
                fit_status.get("invalid_sentinel_count", 0)
            )
            results[family]["invalid_sentinel_counts"] = dict(
                fit_status.get("invalid_sentinel_counts", {})
            )

    unresolved_relationship_count = int(
        relationship_summary.get("relationship_unresolved", 0)
    )
    lactate_audit = performance_audit.get("lactate_threshold", {})
    lactate_review_count = int(
        lactate_audit.get("multiple_candidate_group_count", 0)
        or lactate_audit.get("review_condition_counts", {}).get(
            "functional_threshold_power_conflict", 0
        )
    )
    if lactate_review_count:
        warnings.append(
            {
                "code": "LACTATE_CANDIDATE_AUTHORITY_UNRESOLVED",
                "family": "lactate_threshold",
                "count": lactate_review_count,
                "message": (
                    "multiple accepted Lactate Threshold candidates are preserved; "
                    "Stable promotion remains unavailable"
                ),
            }
        )
    # Candidate values of another form (stage A3d-2a); a candidate warning,
    # as Lactate has no family result.
    lactate_invalid_count = sum(
        int(count) for count in (lactate_audit.get("invalid_value_counts") or {}).values()
    )
    if lactate_invalid_count:
        warnings.append(
            {
                "code": "DATA_VALUE_INVALID",
                "family": "lactate_threshold",
                "count": lactate_invalid_count,
                "message": (
                    "candidate values of a form that their field does not take were "
                    "left empty; the candidates' audit record keeps them"
                ),
            }
        )
    # Candidate items that are not records, and lists of candidates that
    # cannot be read (stage A3d-2c-2): a candidate warning too, which bounds
    # the run as the rows left out of a dataset do.
    lactate_left_out = int(lactate_audit.get("excluded_record_count", 0))
    if lactate_left_out:
        warnings.append(
            {
                "code": "DATA_ROW_LEFT_OUT",
                "family": "lactate_threshold",
                "count": lactate_left_out,
                "message": CANDIDATE_ITEMS_LEFT_OUT_MESSAGE,
            }
        )
    # Repaired text of the Lactate Threshold files, a candidate warning too.
    lactate_repaired_text = int(repaired_text_by_family.get("lactate_threshold", 0))
    if lactate_repaired_text:
        warnings.append(
            {
                "code": "DATA_TEXT_REPAIRED",
                "family": "lactate_threshold",
                "count": lactate_repaired_text,
                "message": REPAIRED_TEXT_MESSAGE,
            }
        )
    if unresolved_relationship_count:
        warnings.append(
            {
                "code": "RELATIONSHIP_UNRESOLVED_VALID_LINK",
                "family": "relationships",
                "count": unresolved_relationship_count,
                "message": (
                    "valid relationship links have unresolved endpoints; "
                    "no endpoint was inferred"
                ),
            }
        )
    # Personal Records kept with an activity link that is missing, malformed,
    # or whose values disagree (stage A3d-1b): no data is missing.
    invalid_link_count = int(relationship_summary.get("relationship_malformed", 0)) + int(
        relationship_summary.get("relationship_conflict", 0)
    )
    if invalid_link_count:
        warnings.append(
            {
                "code": "RELATIONSHIP_UNRESOLVED_INVALID_LINK",
                "family": "relationships",
                "count": invalid_link_count,
                "message": (
                    "records whose link is missing, malformed, or disagrees are "
                    "kept with the relationship unresolved; no endpoint was inferred"
                ),
            }
        )

    # Rows left out bound the run as a FIT file not completely parsed does.
    rows_left_out = lactate_left_out > 0 or any(
        result.get("left_out_row_count") for result in results.values()
    )
    overall = (
        "PARTIAL_SUCCESS"
        if incomplete_fit_count or rows_left_out
        else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    )
    return results, warnings, overall


def _output_digest(entries: list[dict[str, Any]]) -> str:
    canonical = "\n".join(f"{item['path']}:{item['sha256']}" for item in sorted(entries, key=lambda row: row["path"]))
    return _sha256(canonical.encode("utf-8"))


def _write_exclusive(root: Path, relative: str, data: bytes) -> None:
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(data)


def _publish_outputs(
    output_root: Path,
    payloads: dict[str, bytes],
    manifest: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    try:
        output_root.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(
            tempfile.mkdtemp(prefix=f".{output_root.name}.run-all-", dir=output_root.parent)
        )
    except OSError as exc:
        raise _publish_error(exc) from exc
    try:
        for relative in sorted(payloads):
            _write_exclusive(stage, relative, payloads[relative])
        manifest_data = _json_bytes(manifest)
        _write_exclusive(stage, "run_manifest.json", manifest_data)
        summary["manifest_sha256"] = _sha256(manifest_data)
        _write_exclusive(stage, "run_summary.json", _json_bytes(summary))
        if output_root.exists():
            raise RunAllError("OUTPUT_EXISTS", "output directory became occupied before publication")
        stage.rename(output_root)
    except RunAllError:
        raise
    except Exception as exc:
        raise _publish_error(exc) from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _publish_error(exc: BaseException) -> RunAllError:
    """The code for an output that could not be written: no free space, no
    permission, or a path too long (stage A3d-3a); otherwise the general one."""
    code = write_error_code(exc) if isinstance(exc, OSError) else None
    if code is None:
        return RunAllError("OUTPUT_PUBLISH_FAILED", "Run-All output could not be published atomically")
    return RunAllError(code, OUTPUT_LOCATION_MESSAGES[code])


def run_all(
    input_path: str | Path,
    output_path: str | Path,
    *,
    external_safe_pack: bool = False,
    snapshot_context: dict[str, Any] | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Compose the existing Garmin normalizers into deterministic Run-All v2.

    ``progress``, when given, receives one event dictionary per step: a
    ``stage`` from PROGRESS_STAGES, a ``step`` from PROGRESS_STEPS while
    normalizing, and ``done`` and ``total`` while reading FIT files with
    distinct content. Events never carry paths, names, or data values, and the
    output is the same with or without the callback. The callback must not
    raise: an exception it raises may be replaced by a RunAllError code.
    """
    input_root, output_root = _validate_paths(input_path, output_path)
    try:
        timezone_name = resolve_timezone_name(timezone_name)
        require_timezone_data(timezone_name)
    except (TimezoneDataUnavailableError, TimezoneNameInvalidError) as exc:
        raise RunAllError(exc.code, exc.safe_message) from exc
    _notify(progress, "discovering")
    with _read_input(input_root) as reading:
        if snapshot_context is not None and (
            reading.left_out
            or any(reason != FORMAT_NOT_READ for _path, _size, reason in reading.not_read)
        ):
            # The Snapshot build leaves such files out and lists them by
            # Snapshot number (stage A3c-2); the approved input holds none.
            # It holds the stored objects of a form that a run does not read,
            # which the build lists by Snapshot number (stage A4b).
            raise RunAllError("SNAPSHOT_CONTEXT_INVALID", SNAPSHOT_LEFT_OUT_MESSAGE)
        initial_assets = reading.assets
        initial_snapshot = _snapshot(initial_assets)
        families = _classify_assets(initial_assets)
        if not families["activities"]:
            # Activities files that were left out make an Export without
            # Activities records, not an input without Activities (stage A3c).
            if any(
                item["family"] == "activities"
                for item in left_out_files(reading.left_out)
            ):
                raise RunAllError("ACTIVITIES_EMPTY", ACTIVITIES_NOT_READABLE_MESSAGE)
            raise RunAllError("ACTIVITIES_NOT_FOUND", "required Activities input was not found")
        # Records that name more than one account mix Exports; the accounts
        # are compared here only and never written.
        try:
            accounts = asset_accounts(initial_assets)
        except InputChangedError as exc:
            raise RunAllError("INPUT_CHANGED", INPUT_CHANGED_MESSAGE) from exc
        if len(accounts) > 1:
            raise RunAllError("INPUT_MULTIPLE_EXPORTS", MIXED_INPUT_MESSAGE)
        same_export_count = reading.same_export_count
        outside_files = list(reading.outside_files)
        # JSON files over the limit that no dataset reads (stage A3c), and
        # files of a form not read and ZIP files inside ZIP files (stage
        # A4b), as the Snapshot build lists them by Snapshot number in a
        # Snapshot run.
        not_read_files = (
            [
                {"source_path": path, "bytes": size, "reason": reason}
                for path, size, reason in sorted(reading.not_read)
            ]
            if snapshot_context is None
            else list(snapshot_context.get("files_not_read", []))
        )
        _validate_dataset_table()

        try:
            (
                records,
                fit_audit,
                fit_status,
                activity_fit_audit,
                relationship_summary,
                performance_audit,
                record_merges,
                record_rows_left_out,
                record_invalid_values,
                observed_rows,
            ) = _normalize_datasets(
                input_root,
                families,
                initial_assets,
                relationship_context=snapshot_context,
                snapshot_context=snapshot_context,
                timezone_name=timezone_name,
                progress=progress,
            )
        except InputChangedError as exc:
            # The daily and performance-metric normalizers let it through; it
            # is a changed input for every family (stage A3d-3a).
            raise RunAllError("INPUT_CHANGED", INPUT_CHANGED_MESSAGE) from exc
        except RunAllError as exc:
            # A file that changed while it was read stops the run as a changed
            # input, whichever normalizer met it.
            if reading.changed:
                raise RunAllError("INPUT_CHANGED", INPUT_CHANGED_MESSAGE) from exc
            if exc.code == "ACTIVITIES_EMPTY" and any(
                item["family"] == "activities"
                for item in left_out_files(reading.left_out)
            ):
                raise RunAllError("ACTIVITIES_EMPTY", ACTIVITIES_NOT_READABLE_MESSAGE) from exc
            raise
        changed_while_reading = reading.changed
        # The files that could not be read, found while listing and while
        # parsing (stage A3c); in a Snapshot run, those that the build left
        # out, by Snapshot number (stage A3c-2).
        if snapshot_context is None:
            files_left_out = left_out_files(reading.left_out)
        elif reading.left_out:
            raise RunAllError("SNAPSHOT_CONTEXT_INVALID", SNAPSHOT_LEFT_OUT_MESSAGE)
        else:
            files_left_out = list(snapshot_context.get("files_left_out", []))
        # The files whose text with a lone surrogate was repaired as it was
        # read (stage A3d-2c-1); in a Snapshot run, those that the build
        # repaired, by Snapshot number, as the approved input holds none.
        try:
            repaired_files = _repaired_text_files(initial_assets)
        except InputChangedError as exc:
            raise RunAllError("INPUT_CHANGED", INPUT_CHANGED_MESSAGE) from exc
        if snapshot_context is None:
            files_with_repaired_text = repaired_files
        elif repaired_files:
            raise RunAllError("SNAPSHOT_CONTEXT_INVALID", SNAPSHOT_REPAIRED_TEXT_MESSAGE)
        else:
            files_with_repaired_text = list(
                snapshot_context.get("files_with_repaired_text", [])
            )
    _validate_provenance(records, fit_audit, families)
    qa_entries = [
        _dataset_qa(
            dataset,
            records[str(dataset["name"])],
            _file_count(
                str(dataset["family"]),
                families,
                snapshot_context.get("family_file_counts") if snapshot_context is not None else None,
            ),
        )
        for dataset in DATASET_TABLE
    ]
    dataset_summary = {
        "format": "garmin-running-data-normalizer-dataset-summary-v1",
        "status": "PASS",
        "datasets": qa_entries,
        "fit_semantic_normalization": {
            "invalid_sentinel_count": int(
                fit_status.get("invalid_sentinel_count", 0)
            ),
            "invalid_sentinel_counts": dict(
                fit_status.get("invalid_sentinel_counts", {})
            ),
            "status": "PASS",
        },
    }
    csv_data = _activities_csv(
        records["activities"],
        records["activity_fit_links"],
        records["fit_sessions"],
    )
    performance_csv_data = _performance_metrics_csv(
        records["hill_score_daily"],
        records["endurance_score_daily"],
    )

    _notify(progress, "verifying_input")
    if changed_while_reading or _input_snapshot(input_root) != initial_snapshot:
        raise RunAllError("INPUT_CHANGED", INPUT_CHANGED_MESSAGE)
    _notify(progress, "building_output")

    record_audits = _record_audits(
        records, snapshot_context, record_merges, record_rows_left_out, record_invalid_values
    )
    repaired_text_by_family: Counter[str] = Counter()
    for item in files_with_repaired_text:
        repaired_text_by_family[str(item["family"])] += int(item["repaired_text_count"])
    file_counts = (
        snapshot_context.get("family_file_counts") if snapshot_context is not None else None
    )
    family_results, warnings, status = _family_results(
        families,
        records,
        fit_status,
        performance_audit,
        relationship_summary,
        record_audits,
        dict(repaired_text_by_family),
        file_counts=file_counts,
    )
    if files_left_out:
        # A file left out leaves the run bounded: PARTIAL_SUCCESS (exit 3).
        warnings.append(
            {
                "code": "DATA_FILE_LEFT_OUT",
                "count": len(files_left_out),
                "message": (
                    "one or more files could not be read and were left out; "
                    "run_manifest.json lists them with the reason"
                ),
            }
        )
        status = "PARTIAL_SUCCESS"
    if same_export_count:
        warnings.append(
            {
                "code": "INPUT_DUPLICATE_SOURCES",
                "count": same_export_count,
                "message": "the input holds the same Export more than once; it was read once",
            }
        )
        if status == "PASS":
            status = "PASS_WITH_WARNINGS"
    performance_summary = {
        "format": "garmin-running-data-normalizer-performance-metrics-summary-v1",
        "status": (
            "PASS_WITH_REVIEW_ITEMS"
            if any(
                int(
                    performance_audit[name].get("review_required_count", 0)
                    or performance_audit[name].get("review_item_count", 0)
                )
                for name in ("hill_score_daily", "endurance_score_daily")
            )
            else "PASS"
        ),
        "stable_datasets": {
            name: {
                "record_count": len(records[name]),
                "audit_status": performance_audit[name]["status"],
                "excluded_record_count": performance_audit[name][
                    "excluded_record_count"
                ],
                "same_value_duplicate_count": performance_audit[name][
                    "same_value_duplicate_count"
                ],
            }
            for name in ("hill_score_daily", "endurance_score_daily")
        },
        "lactate_threshold": {
            "status": performance_audit["lactate_threshold"]["status"],
            "candidate_count": performance_audit["lactate_threshold"][
                "candidate_count"
            ],
            "public_promotion": False,
            "machine_stable_key_status": "PRODUCT_DECISION_REQUIRED",
        },
    }
    daily_metric_names = (
        "race_prediction_daily",
        "sleep_daily",
        "uds_daily",
        "acute_training_load_daily",
        "training_readiness_daily",
        "vo2max_daily",
        "hrv_daily",
        "training_history_daily",
    )
    daily_metrics_summary = {
        "format": "garmin-running-data-normalizer-daily-metrics-summary-v1",
        "status": (
            "PASS_WITH_REVIEW_ITEMS"
            if any(
                performance_audit[name].get("status") == "PASS_WITH_REVIEW_ITEMS"
                for name in daily_metric_names
            )
            else "PASS"
        ),
        "datasets": {
            name: {
                "record_count": len(records[name]),
                "audit_status": performance_audit[name]["status"],
                "record_grain": next(
                    item["record_grain"] for item in DATASET_TABLE if item["name"] == name
                ),
                "stable_key": list(
                    next(item["stable_key"] for item in DATASET_TABLE if item["name"] == name)
                ),
                **(
                    {"daily_projection": _daily_observation_projection(records[name])}
                    if name in OBSERVATION_GRAIN_DATASETS
                    else {}
                ),
            }
            for name in daily_metric_names
        },
        "generation_boundary": {
            "earlier_generation": "approximately 2015-2021",
            "later_generation": "approximately 2022 and later",
            "automatic_equivalence_assumed": False,
        },
        "hrv": {
            "analysis_role": "analysis_reference_only",
            "source_of_truth": False,
            "daily_coach_use": False,
        },
        "health_status": {
            "status": "DEFERRED_PENDING_SEMANTICS",
            "public_promotion": False,
        },
    }
    payloads = {
        **{DATASET_PATHS[name]: _json_bytes(value) for name, value in records.items()},
        **{
            f"audit/{name}.json": _json_bytes(record_audits[name])
            for name in RECORD_AUDIT_DATASETS
        },
        "audit/fit_audit.json": _json_bytes(fit_audit),
        "audit/activity_fit_linkage.json": _json_bytes(activity_fit_audit),
        "audit/hill_score_daily.json": _json_bytes(
            performance_audit["hill_score_daily"]
        ),
        "audit/endurance_score_daily.json": _json_bytes(
            performance_audit["endurance_score_daily"]
        ),
        "audit/lactate_threshold_candidates.json": _json_bytes(
            performance_audit["lactate_threshold"]
        ),
        **{
            f"audit/{name}.json": _json_bytes(performance_audit[name])
            for name in daily_metric_names
        },
        "analysis/activities.csv": csv_data,
        "analysis/performance_metrics_daily.csv": performance_csv_data,
        "qa/dataset_summary.json": _json_bytes(dataset_summary),
        "qa/relationship_summary.json": _json_bytes(relationship_summary),
        "qa/performance_metrics_summary.json": _json_bytes(performance_summary),
        "qa/daily_metrics_summary.json": _json_bytes(daily_metrics_summary),
    }
    completeness_context: dict[str, Any] | None = None
    if snapshot_context is not None:
        required_snapshot_context = {"lineage", "coverage", "merge_summary"}
        allowed_snapshot_context = required_snapshot_context | {
            "current_activity_ids",
            "current_gear_keys",
            "current_fit_session_keys",
            "source_completeness_context",
            "fit_snapshot_numbers",
            "family_file_counts",
            "input_file_count",
            "lactate_threshold_counts",
            "private_field_counts",
            "record_changes",
            "files_left_out",
            "files_not_read",
            "files_with_repaired_text",
        }
        if not required_snapshot_context <= set(snapshot_context) or not set(
            snapshot_context
        ) <= allowed_snapshot_context:
            raise RunAllError(
                "SNAPSHOT_CONTEXT_INVALID",
                "snapshot lifecycle context is incomplete",
            )
        # The observations of Source Completeness are the output rows of each
        # family that each Snapshot observed, counted here as a one-shot run
        # counts its rows; the build does not count them (stage A3d-4c-2).
        snapshot_coverage = snapshot_context["coverage"]
        completeness_context = snapshot_context.get("source_completeness_context")
        observations = (completeness_context or {}).get("observations")
        if isinstance(observations, list) and all(
            isinstance(item, dict) for item in observations
        ):
            counts = _snapshot_observations(
                records,
                observed_rows,
                snapshot_context.get("fit_snapshot_numbers") or {},
                list(range(1, len(observations) + 1)),
            )
            observations = [
                {**item, "source_observation_counts": counts[number]}
                for number, item in enumerate(observations, start=1)
            ]
            completeness_context = {**completeness_context, "observations": observations}
            snapshot_coverage = {
                **snapshot_coverage,
                "source_completeness_observations": observations,
            }
        payloads.update(
            {
                "snapshot/snapshot_lineage.json": _json_bytes(
                    snapshot_context["lineage"]
                ),
                "snapshot/snapshot_coverage.json": _json_bytes(snapshot_coverage),
                "snapshot/canonical_merge_summary.json": _json_bytes(
                    snapshot_context["merge_summary"]
                ),
            }
        )
    from .diagnostics.completeness import build_source_completeness
    from .diagnostics.contracts import SOURCE_FAMILY_ORDER
    from .diagnostics.run_quality import build_run_quality

    source_completeness = build_source_completeness(
        product_version=__version__,
        family_candidate_counts={
            family: len(families[family]) for family in SOURCE_FAMILY_ORDER
        },
        records=records,
        fit_status=fit_status,
        # The record audits count the rows left out of Activities, Gear,
        # activity_gear, and Personal Records (stage A3d-1b).
        performance_audit={**performance_audit, **record_audits},
        unknown_evidence_count=sum(
            1 for asset in initial_assets if _asset_family(asset) == "unclassified"
        ),
        snapshot_context=completeness_context,
        fit_audit=fit_audit,
    )
    run_quality = build_run_quality(
        product_version=__version__,
        run_all_version=RUN_ALL_VERSION,
        status=status,
        warnings=warnings,
        dataset_qa_entries=qa_entries,
        relationship_summary=relationship_summary,
        performance_audit=performance_audit,
        fit_status=fit_status,
        source_completeness=source_completeness,
        authority_payloads=payloads,
        record_audits=record_audits,
    )
    payloads.update(
        {
            "diagnostics/source_completeness.json": _json_bytes(
                source_completeness
            ),
            "diagnostics/run_quality.json": _json_bytes(run_quality),
        }
    )
    generated_paths = list(OUTPUT_PATHS)
    if external_safe_pack:
        safe_pack_path = "analysis/external_safe_handoff.zip"
        payloads[safe_pack_path] = _external_safe_pack(
            records["activities"],
            run_status=status,
            warnings=warnings,
        )
        generated_paths = [
            *OUTPUT_PATHS[:-2],
            safe_pack_path,
            *OUTPUT_PATHS[-2:],
        ]
    if snapshot_context is not None:
        generated_paths = [
            *generated_paths[:-2],
            *SNAPSHOT_LIFECYCLE_PATHS,
            *generated_paths[-2:],
        ]
    qa_by_name = {entry["dataset"]: entry for entry in qa_entries}
    lactate_audit = performance_audit["lactate_threshold"]
    lactate_candidate_features = {
        "status": lactate_audit["status"],
        "candidate_count": lactate_audit["candidate_count"],
        "public_promotion": False,
        "machine_stable_key_status": "PRODUCT_DECISION_REQUIRED",
        "audit_path": "audit/lactate_threshold_candidates.json",
    }
    manifest = {
        "format": "garmin-running-data-normalizer-run-manifest-v1",
        "product_version": __version__,
        "run_all_version": RUN_ALL_VERSION,
        "local_timezone": timezone_name,
        "input_assets": [
            {
                "source_path": asset.provenance_path,
                "bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "detected_family": _asset_family(asset),
            }
            for asset in initial_assets
        ],
        "datasets": [
            {
                "name": dataset["name"],
                "record_grain": dataset["record_grain"],
                "stable_key": list(dataset["stable_key"]),
                "source_count": qa_by_name[str(dataset["name"])]["source_count"],
                "record_count": qa_by_name[str(dataset["name"])]["record_count"],
                "records_sha256": qa_by_name[str(dataset["name"])]["records_sha256"],
            }
            for dataset in DATASET_TABLE
        ],
        "outputs": [],
        "deterministic_output_digest": "projection-pending",
        "candidate_features": {"lactate_threshold": lactate_candidate_features},
    }
    if outside_files or not_read_files:
        # Files outside the Export, JSON files over the limit that no
        # dataset reads, files of a form not read, and ZIP files inside ZIP
        # files are not read; the list keeps the established manifest
        # byte-stable when there are none.
        manifest["files_not_read"] = [
            *(
                {"source_path": relative, "bytes": size, "reason": OUTSIDE_EXPORT_ROOT}
                for relative, size in outside_files
            ),
            *not_read_files,
        ]
    if files_left_out:
        # Files that could not be read are left out with the reason; the
        # list appears only when there is one (stage A3c).
        manifest["files_left_out"] = files_left_out
    if files_with_repaired_text:
        # Files whose text was repaired, only when there is one (stage
        # A3d-2c-1).
        manifest["files_with_repaired_text"] = files_with_repaired_text
    summary = {
        "format": "garmin-running-data-normalizer-run-summary-v1",
        "product_version": __version__,
        "run_all_version": RUN_ALL_VERSION,
        "local_timezone": timezone_name,
        "status": status,
        "family_results": family_results,
        # A Snapshot run counts the JSON and FIT files of the Exports, as a
        # one-shot run of each Export counts its own, not the files of the
        # build (stage A3d-4c-1).
        "input_asset_count": (snapshot_context or {}).get(
            "input_file_count", len(initial_assets)
        ),
        "normalized_record_count": sum(len(value) for value in records.values()),
        "warning_count": len(warnings),
        "error_count": 0,
        "warnings": warnings,
        "errors": [],
        "generated_paths": generated_paths,
        "deterministic_output_digest": "projection-pending",
        "candidate_features": {"lactate_threshold": lactate_candidate_features},
    }
    lactate_warning_count = sum(
        1 for item in warnings if item.get("family") == "lactate_threshold"
    )
    if lactate_warning_count:
        # Candidate-layer warnings are intentionally separate from runtime
        # family results: Lactate is audit-only and has no normalized public
        # dataset family.  The output validator accounts for this additive
        # warning bucket without fabricating a family result.
        summary["candidate_warning_count"] = lactate_warning_count
    relationship_warning_count = int(
        bool(relationship_summary.get("relationship_unresolved", 0))
    ) + int(
        bool(
            relationship_summary.get("relationship_malformed", 0)
            or relationship_summary.get("relationship_conflict", 0)
        )
    )
    if relationship_warning_count:
        # Keep the established PASS summary byte-stable; this additive field
        # appears only when a relationship warning exists.
        summary["relationship_warning_count"] = relationship_warning_count
    input_warning_count = int(bool(same_export_count)) + int(bool(files_left_out))
    if input_warning_count:
        # The input warnings have no family; like the warnings above, they
        # are counted only when they exist.
        summary["input_warning_count"] = input_warning_count
    # Records that the latest Snapshot lacks while a file of their family was
    # left out from it keep their earlier values (stage A3c-2); counted only
    # when there are some.
    latest_left_out_count = sum(
        bool(row.get("latest_file_left_out"))
        for audit in record_audits.values()
        for row in audit["not_in_latest_snapshot"]
    )
    if latest_left_out_count:
        summary["not_in_latest_file_left_out_count"] = latest_left_out_count
    if snapshot_context is not None:
        lifecycle_summary = dict(snapshot_context["merge_summary"])
        manifest["snapshot_lifecycle"] = {
            "enabled": True,
            "snapshot_count": snapshot_context["lineage"]["snapshot_count"],
            "canonical_build_sha256": snapshot_context["lineage"][
                "canonical_build_sha256"
            ],
            "automatic_deletion": False,
            "inference_performed": False,
        }
        summary["snapshot_lifecycle"] = lifecycle_summary
    from .output_experience import (
        DOCUMENT_NAMES,
        MACHINE_CONTEXT_NAMES,
        MANIFEST_OUTPUT_PATHS,
        OPTIONAL_MANIFEST_OUTPUT_PATHS,
        render_output_experience_artifacts,
        validate_schema_contract,
    )

    projection_names = (*DOCUMENT_NAMES, *MACHINE_CONTEXT_NAMES)
    provisional_payloads = {**payloads, **{name: b"" for name in projection_names}}
    allowed_payload_paths = set(MANIFEST_OUTPUT_PATHS)
    if external_safe_pack:
        allowed_payload_paths.update(OPTIONAL_MANIFEST_OUTPUT_PATHS)
    if snapshot_context is not None:
        allowed_payload_paths.update(SNAPSHOT_LIFECYCLE_PATHS)
    if set(provisional_payloads) != allowed_payload_paths:
        raise RunAllError(
            "OUTPUT_CONTRACT_INVALID",
            "Run-All payload paths do not match the v1.1 output contract",
        )
    manifest["outputs"] = [
        {"path": path, "bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(provisional_payloads.items())
    ]
    try:
        experience_payloads = render_output_experience_artifacts(
            manifest,
            summary,
            {
                "datasets": [
                    {
                        "name": dataset["name"],
                        "record_grain": dataset["record_grain"],
                        "stable_key": list(dataset["stable_key"]),
                        "provenance_required": True,
                    }
                    for dataset in DATASET_TABLE
                ]
            },
            relationship_summary,
        )
        validate_schema_contract(
            records,
            json.loads(experience_payloads["SCHEMA_CATALOG.json"]),
        )
        payloads.update(experience_payloads)
    except Exception as exc:
        raise RunAllError(
            "OUTPUT_EXPERIENCE_FAILED",
            "deterministic analysis handoff generation failed",
        ) from exc

    output_entries = [
        {"path": path, "bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(payloads.items())
    ]
    deterministic_digest = _output_digest(output_entries)
    manifest["outputs"] = output_entries
    manifest["deterministic_output_digest"] = deterministic_digest
    summary["deterministic_output_digest"] = deterministic_digest
    _notify(progress, "writing_output")
    _publish_outputs(output_root, payloads, manifest, summary)
    exit_code = 3 if status == "PARTIAL_SUCCESS" else 0
    return {
        "status": status,
        "exit_code": exit_code,
        "family_results": family_results,
        "generated_files": generated_paths,
        "deterministic_digest": deterministic_digest,
    }


__all__ = [
    "ACTIVITIES_CSV_COLUMNS",
    "ACTIVITIES_CSV_DURATION_COLUMNS",
    "ACTIVITIES_CSV_FIT_SESSION_COLUMNS",
    "DATASET_TABLE",
    "OUTPUT_PATHS",
    "PROGRESS_STAGES",
    "PROGRESS_STEPS",
    "ProgressCallback",
    "SNAPSHOT_LIFECYCLE_PATHS",
    "RUN_ALL_VERSION",
    "RunAllError",
    "left_out_files",
    "run_all",
]
