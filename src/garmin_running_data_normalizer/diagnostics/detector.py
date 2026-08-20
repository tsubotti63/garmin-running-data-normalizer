"""Versioned source-family detector shared by Run-All and Snapshot diagnostics."""

from __future__ import annotations

from pathlib import PurePosixPath


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


__all__ = ["classify_source_name"]
