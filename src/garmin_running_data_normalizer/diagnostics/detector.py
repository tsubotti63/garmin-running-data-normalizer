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


def classify_source_name(logical_name: str, kind: str) -> str:
    """Return the closed Product source-family ID for one discovered object."""
    lower_name = logical_name.replace("\\", "/").lower()
    basename = PurePosixPath(lower_name).name
    if kind == "json" and lower_name.endswith("summarizedactivities.json"):
        return "activities"
    if kind == "json" and lower_name.endswith("gear.json"):
        return "gear"
    if kind == "json" and lower_name.endswith("personalrecord.json"):
        return "personal_records"
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
