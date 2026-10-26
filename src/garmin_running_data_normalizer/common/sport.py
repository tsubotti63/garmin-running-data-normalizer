"""The group of the sport of an activity or of a FIT session (stage G1).

A sport that an activity and a FIT session share supports the link between
them (``compatible_sport`` in relationships.py). Stage G1 moved the rule here
without changing it, so that the view page counts as running what the link
counts as running: the activity types that the page counts at first are the
names whose group is ``running``.
"""

from __future__ import annotations

from typing import Any


def sport_group(value: Any) -> str | None:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return None
    legacy_fit_sports = {
        "10": "strength_training",
        "11": "walking",
        "17": "hiking",
    }
    if text in legacy_fit_sports:
        return legacy_fit_sports[text]
    if "run" in text or text in {"street", "trail"}:
        return "running"
    if "strength" in text or text in {"training", "fitness_equipment"}:
        return "strength_training"
    if "walk" in text:
        return "walking"
    if "hik" in text:
        return "hiking"
    return text


def activity_sport(record: dict[str, Any]) -> str | None:
    return sport_group(record.get("sport_type")) or sport_group(
        record.get("activity_type")
    )


__all__ = ["activity_sport", "sport_group"]
