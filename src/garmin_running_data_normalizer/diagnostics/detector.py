"""Versioned source-family detector shared by Run-All and Snapshot diagnostics."""

from __future__ import annotations

from pathlib import PurePosixPath

# Snapshot build-input writes these merged files. Their names do not start with
# the Garmin family prefixes, so they are matched exactly.
_SNAPSHOT_MERGED_NAMES = {
    "snapshot_hillscore.json": "hill_score",
    "snapshot_endurancescore.json": "endurance_score",
    "snapshot_vo2max.json": "vo2max",
}


# The ends of the names of the files of Activities, Gear, and Personal Records.
RECORD_FILE_SUFFIXES = {
    "activities": "summarizedactivities.json",
    "gear": "gear.json",
    "personal_records": "personalrecord.json",
}


def reads_record_file(logical_name: str, family: str) -> bool:
    """Whether a JSON file of this name is a file of ``family`` (Activities,
    Gear, or Personal Records), whatever the case of its name. The input is
    classified, the one-shot normalizers and the Golden Path read their
    files, and the Snapshot build reads its files by this one rule, so that
    none of them reads a file that another passes over (stage A3d-4b)."""
    return logical_name.replace("\\", "/").lower().endswith(RECORD_FILE_SUFFIXES[family])


def classify_source_name(logical_name: str, kind: str) -> str:
    """Return the closed Product source-family ID for one discovered object."""
    lower_name = logical_name.replace("\\", "/").lower()
    basename = PurePosixPath(lower_name).name
    for family in RECORD_FILE_SUFFIXES:
        if kind == "json" and reads_record_file(logical_name, family):
            return family
    if kind == "json" and basename in _SNAPSHOT_MERGED_NAMES:
        return _SNAPSHOT_MERGED_NAMES[basename]
    if kind == "json" and basename.startswith("hillscore"):
        return "hill_score"
    if kind == "json" and basename.startswith("endurancescore"):
        return "endurance_score"
    if kind == "json" and basename.startswith("runracepredictions"):
        return "race_prediction"
    if kind == "json" and basename.endswith("sleepdata.json"):
        return "sleep"
    if kind == "json" and basename.startswith("udsfile"):
        return "uds"
    if kind == "json" and basename.startswith("metricsacutetrainingload"):
        return "acute_training_load"
    if kind == "json" and basename.startswith("trainingreadinessdto"):
        return "training_readiness"
    if kind == "json" and basename.startswith(
        ("activityvo2max", "metricsmaxmetdata")
    ):
        return "vo2max"
    if kind == "json" and basename.startswith("traininghistory"):
        return "training_history"
    if kind == "json" and basename.endswith(
        (
            "userbiometrics.json",
            "biometrics_latest.json",
            "userbiometricprofiledata.json",
            "heartratezones.json",
        )
    ):
        return "lactate_threshold"
    if kind == "fit":
        return "fit"
    return "unclassified"


def json_read_by_run_all(logical_name: str) -> bool:
    """Whether Run-All reads a JSON file of this name: one of a family that a
    dataset reads. A one-shot run and the Snapshot build count the text that
    they repair in the same files (stage A3d-2c-1)."""
    return classify_source_name(logical_name, "json") != "unclassified"


__all__ = ["classify_source_name", "json_read_by_run_all"]
