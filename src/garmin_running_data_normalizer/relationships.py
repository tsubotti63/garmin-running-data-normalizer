from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


class RelationshipContractError(ValueError):
    """Raised when a declared public relationship cannot be proven safely."""


def _identity(value: Any, label: str, *, allow_zero: bool = False) -> str:
    if isinstance(value, bool) or value in (None, ""):
        raise RelationshipContractError(f"{label} is missing")
    if isinstance(value, int):
        token = str(value)
    elif isinstance(value, str):
        token = value.strip()
        if not token:
            raise RelationshipContractError(f"{label} is missing")
        if token.isdecimal():
            token = str(int(token))
    else:
        raise RelationshipContractError(f"{label} has an unsupported type")
    if token == "0" and not allow_zero:
        raise RelationshipContractError(f"{label} cannot be zero")
    return token


def _index_unique(
    records: list[dict[str, Any]],
    field: str,
    target_field: str,
    label: str,
    *,
    allow_missing: bool = False,
) -> dict[str, str]:
    index: dict[str, str] = {}
    for record in records:
        if allow_missing and record.get(field) in (None, ""):
            continue
        token = _identity(record.get(field), label)
        target = _identity(record.get(target_field), target_field)
        previous = index.get(token)
        if previous is not None and previous != target:
            raise RelationshipContractError(f"{label} maps to multiple identities")
        index[token] = target
    return index


def _record_key_index(
    records: list[dict[str, Any]],
    field: str,
    label: str,
) -> set[str]:
    values: set[str] = set()
    for record in records:
        token = _identity(record.get(field), label)
        if token in values:
            raise RelationshipContractError(f"{label} contains a duplicate identity")
        values.add(token)
    return values


def validate_declared_relationships(
    records: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Validate and enrich the non-heuristic v1.1 relationship contracts."""
    activity_ids = _index_unique(
        records["activities"],
        "activity_id",
        "garmin_activity_key",
        "activity_id",
        allow_missing=True,
    )
    gear_keys = _record_key_index(records["gear"], "gear_key", "gear_key")
    fit_session_keys = _record_key_index(
        records["fit_sessions"],
        "fit_session_key",
        "fit_session_key",
    )

    enriched_activity_gear: list[dict[str, Any]] = []
    seen_activity_gear: set[tuple[str, str]] = set()
    for record in records["activity_gear"]:
        gear_key = _identity(record.get("gear_key"), "activity_gear.gear_key")
        activity_id = _identity(
            record.get("activity_id"),
            "activity_gear.activity_id",
        )
        pair = (gear_key, activity_id)
        if pair in seen_activity_gear:
            raise RelationshipContractError("activity_gear contains a duplicate link")
        seen_activity_gear.add(pair)
        if gear_key not in gear_keys:
            raise RelationshipContractError("activity_gear contains an orphan gear link")
        activity_key = activity_ids.get(activity_id)
        if activity_key is None:
            raise RelationshipContractError("activity_gear contains an orphan activity link")
        enriched_activity_gear.append(
            {
                **record,
                "garmin_activity_key": activity_key,
                "activity_relationship_status": "explicit",
                "gear_relationship_status": "explicit",
            }
        )
    records["activity_gear"] = sorted(
        enriched_activity_gear,
        key=lambda item: (
            str(item["gear_key"]),
            str(item["garmin_activity_key"]),
            str(item["source_path"]),
        ),
    )

    enriched_personal_records: list[dict[str, Any]] = []
    personal_record_activity_links = 0
    independent_personal_records = 0
    for record in records["personal_records"]:
        activity_id = _identity(
            record.get("activity_id"),
            "personal_records.activity_id",
            allow_zero=True,
        )
        if activity_id == "0":
            independent_personal_records += 1
            enriched_personal_records.append(
                {
                    **record,
                    "garmin_activity_key": None,
                    "activity_relationship_status": "independent",
                    "activity_relationship_reason": "non_activity_personal_record",
                }
            )
            continue
        activity_key = activity_ids.get(activity_id)
        if activity_key is None:
            raise RelationshipContractError(
                "personal_records contains an unresolved nonzero activity identity"
            )
        personal_record_activity_links += 1
        enriched_personal_records.append(
            {
                **record,
                "garmin_activity_key": activity_key,
                "activity_relationship_status": "explicit",
                "activity_relationship_reason": "source_activity_id",
            }
        )
    records["personal_records"] = sorted(
        enriched_personal_records,
        key=lambda item: (
            str(item["personal_record_id"]),
            str(item["source_path"]),
        ),
    )

    seen_laps: set[str] = set()
    for record in records["fit_laps"]:
        lap_key = _identity(record.get("fit_lap_key"), "fit_lap_key")
        if lap_key in seen_laps:
            raise RelationshipContractError("fit_laps contains a duplicate identity")
        seen_laps.add(lap_key)
        session_key = _identity(record.get("fit_session_key"), "fit_session_key")
        if session_key not in fit_session_keys:
            raise RelationshipContractError("fit_laps contains an orphan session link")

    return {
        "status": "PASS",
        "relationships": {
            "activity_gear_to_activities": {
                "status": "explicit",
                "link_count": len(records["activity_gear"]),
                "eligible_count": len(records["activity_gear"]),
                "coverage": (
                    1.0 if records["activity_gear"] else None
                ),
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "orphan_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "activity_gear_to_gear": {
                "status": "explicit",
                "link_count": len(records["activity_gear"]),
                "eligible_count": len(records["activity_gear"]),
                "coverage": (
                    1.0 if records["activity_gear"] else None
                ),
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "orphan_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "personal_records_to_activities": {
                "status": "explicit",
                "link_count": personal_record_activity_links,
                "eligible_count": personal_record_activity_links,
                "coverage": (
                    1.0 if personal_record_activity_links else None
                ),
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "independent_count": independent_personal_records,
                "orphan_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
            "fit_laps_to_fit_sessions": {
                "status": "explicit",
                "link_count": len(records["fit_laps"]),
                "eligible_count": len(records["fit_laps"]),
                "coverage": (
                    1.0 if records["fit_laps"] else None
                ),
                "unresolved_count": 0,
                "ambiguous_count": 0,
                "orphan_count": 0,
                "duplicate_count": 0,
                "inference_performed": False,
                "primary_unresolved_reason": None,
            },
        },
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _sport_group(value: Any) -> str | None:
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


def _activity_sport(record: dict[str, Any]) -> str | None:
    return _sport_group(record.get("sport_type")) or _sport_group(
        record.get("activity_type")
    )


def _activity_eligibility_exclusion(record: dict[str, Any]) -> str | None:
    if _instant(record.get("activity_datetime_local")) is None:
        return "missing_or_invalid_start_datetime"
    distance = _number(record.get("distance_m"))
    duration = _number(record.get("duration_sec"))
    if not (
        (distance is not None and distance > 0)
        or (duration is not None and duration > 0)
    ):
        return "missing_or_nonpositive_distance_and_duration"
    return None


def _fit_session_eligibility_exclusion(record: dict[str, Any]) -> str | None:
    if _instant(record.get("start_datetime_local")) is None:
        return "missing_or_invalid_start_datetime"
    distance = _number(record.get("distance_m"))
    duration = _number(record.get("timer_time_sec"))
    if duration is None:
        duration = _number(record.get("elapsed_time_sec"))
    if not (
        (distance is not None and distance > 0)
        or (duration is not None and duration > 0)
    ):
        return "missing_or_nonpositive_distance_and_duration"
    return None


def _candidate(
    activity: dict[str, Any],
    session: dict[str, Any],
) -> dict[str, Any] | None:
    activity_time = _instant(activity.get("activity_datetime_local"))
    fit_time = _instant(session.get("start_datetime_local"))
    if activity_time is None or fit_time is None:
        return None
    delta_seconds = abs((activity_time - fit_time).total_seconds())
    activity_distance = _number(activity.get("distance_m"))
    fit_distance = _number(session.get("distance_m"))
    activity_duration = _number(activity.get("duration_sec"))
    fit_duration = _number(session.get("timer_time_sec"))
    if fit_duration is None:
        fit_duration = _number(session.get("elapsed_time_sec"))
    sport_match = (
        _activity_sport(activity) is not None
        and _activity_sport(activity) == _sport_group(session.get("sport"))
    )
    distance_delta = (
        abs(activity_distance - fit_distance)
        if activity_distance is not None and fit_distance is not None
        else None
    )
    duration_delta = (
        abs(activity_duration - fit_duration)
        if activity_duration is not None and fit_duration is not None
        else None
    )
    corroboration: list[str] = []
    if sport_match:
        corroboration.append("compatible_sport")
    if distance_delta is not None and distance_delta <= 200.0:
        corroboration.append("distance_within_200m")
    if duration_delta is not None and duration_delta <= 5.0:
        corroboration.append("duration_within_5s")

    if delta_seconds == 0 and corroboration:
        rule = "exact_start_with_corroboration"
        score = 1000 + len(corroboration) * 100
    elif (
        delta_seconds <= 60
        and sport_match
        and distance_delta is not None
        and distance_delta <= 1.0
        and duration_delta is not None
        and duration_delta <= 1.0
    ):
        rule = "near_start_exact_metrics"
        corroboration = [
            "compatible_sport",
            "distance_within_1m",
            "duration_within_1s",
        ]
        score = 800 + int(60 - delta_seconds)
    else:
        return None

    return {
        "garmin_activity_key": str(activity["garmin_activity_key"]),
        "fit_session_key": str(session["fit_session_key"]),
        "match_rule": rule,
        "match_basis": ["start_datetime_local", *corroboration],
        "match_score": score,
        "time_delta_seconds": delta_seconds,
        "distance_delta_m": distance_delta,
        "duration_delta_seconds": duration_delta,
    }


def build_activity_fit_relationship(
    activities: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Build deterministic, evidence-qualified one-to-one Activity/FIT links."""
    candidates: list[dict[str, Any]] = []
    activities_by_key = {
        _identity(record.get("garmin_activity_key"), "garmin_activity_key"): record
        for record in activities
    }
    sessions_by_key = {
        _identity(record.get("fit_session_key"), "fit_session_key"): record
        for record in sessions
    }
    if len(activities_by_key) != len(activities):
        raise RelationshipContractError("activities contains a duplicate identity")
    if len(sessions_by_key) != len(sessions):
        raise RelationshipContractError("fit_sessions contains a duplicate identity")

    activity_exclusion_reasons = {
        key: reason
        for key, record in activities_by_key.items()
        if (reason := _activity_eligibility_exclusion(record)) is not None
    }
    session_exclusion_reasons = {
        key: reason
        for key, record in sessions_by_key.items()
        if (reason := _fit_session_eligibility_exclusion(record)) is not None
    }
    eligible_activity_keys = set(activities_by_key) - set(activity_exclusion_reasons)
    eligible_session_keys = set(sessions_by_key) - set(session_exclusion_reasons)

    for activity_key in sorted(eligible_activity_keys):
        for session_key in sorted(eligible_session_keys):
            candidate = _candidate(
                activities_by_key[activity_key],
                sessions_by_key[session_key],
            )
            if candidate is not None:
                candidates.append(candidate)

    by_activity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_activity[candidate["garmin_activity_key"]].append(candidate)
        by_session[candidate["fit_session_key"]].append(candidate)

    activity_best: dict[str, dict[str, Any]] = {}
    activity_ambiguous: set[str] = set()
    for key, values in by_activity.items():
        highest = max(item["match_score"] for item in values)
        top = [item for item in values if item["match_score"] == highest]
        if len(top) == 1:
            activity_best[key] = top[0]
        else:
            activity_ambiguous.add(key)

    session_best: dict[str, dict[str, Any]] = {}
    session_ambiguous: set[str] = set()
    for key, values in by_session.items():
        highest = max(item["match_score"] for item in values)
        top = [item for item in values if item["match_score"] == highest]
        if len(top) == 1:
            session_best[key] = top[0]
        else:
            session_ambiguous.add(key)

    selected: list[dict[str, Any]] = []
    for activity_key in sorted(activity_best):
        candidate = activity_best[activity_key]
        if activity_key in activity_ambiguous:
            continue
        if candidate["fit_session_key"] in session_ambiguous:
            continue
        if session_best.get(candidate["fit_session_key"]) != candidate:
            continue
        activity = activities_by_key[activity_key]
        session = sessions_by_key[candidate["fit_session_key"]]
        selected.append(
            {
                **candidate,
                "match_status": "explicit",
                "ambiguous": False,
                "eligibility_status": "eligible",
                "exclusion_reason": None,
                "activity_source_path": activity["source_path"],
                "activity_source_sha256": activity["source_sha256"],
                "fit_source_path": session["source_path"],
                "fit_source_sha256": session["source_sha256"],
                "source_path": activity["source_path"],
                "source_sha256": activity["source_sha256"],
            }
        )

    selected_activity_keys = {item["garmin_activity_key"] for item in selected}
    selected_session_keys = {item["fit_session_key"] for item in selected}
    activity_exclusions = []
    for key in sorted(set(activities_by_key) - selected_activity_keys):
        structural_reason = activity_exclusion_reasons.get(key)
        if structural_reason is not None:
            reason = structural_reason
            eligibility_status = "excluded"
        else:
            reason = (
                "ambiguous_candidate"
                if key in activity_ambiguous
                else "no_evidence_qualified_candidate"
                if key not in by_activity
                else "one_to_one_conflict"
            )
            eligibility_status = "eligible_unresolved"
        activity_exclusions.append(
            {
                "garmin_activity_key": key,
                "eligibility_status": eligibility_status,
                "reason": reason,
            }
        )
    session_exclusions = []
    for key in sorted(set(sessions_by_key) - selected_session_keys):
        structural_reason = session_exclusion_reasons.get(key)
        if structural_reason is not None:
            reason = structural_reason
            eligibility_status = "excluded"
        else:
            reason = (
                "ambiguous_candidate"
                if key in session_ambiguous
                else "no_evidence_qualified_candidate"
                if key not in by_session
                else "one_to_one_conflict"
            )
            eligibility_status = "eligible_unresolved"
        session_exclusions.append(
            {
                "fit_session_key": key,
                "eligibility_status": eligibility_status,
                "reason": reason,
            }
        )

    link_pairs = {
        (item["garmin_activity_key"], item["fit_session_key"]) for item in selected
    }
    if len(link_pairs) != len(selected):
        raise RelationshipContractError("activity_fit_links contains a duplicate mapping")
    eligible_activity_count = len(eligible_activity_keys)
    eligible_session_count = len(eligible_session_keys)
    candidate_activity_count = len(by_activity)
    candidate_session_count = len(by_session)
    unresolved_eligible_count = sum(
        item["eligibility_status"] == "eligible_unresolved"
        for item in (*activity_exclusions, *session_exclusions)
    )
    excluded_activity_count = sum(
        item["eligibility_status"] == "excluded" for item in activity_exclusions
    )
    excluded_session_count = sum(
        item["eligibility_status"] == "excluded" for item in session_exclusions
    )
    unresolved_activity_reasons: dict[str, int] = dict(
        sorted(
            (
                reason,
                sum(
                    item["eligibility_status"] == "eligible_unresolved"
                    and item["reason"] == reason
                    for item in activity_exclusions
                ),
            )
            for reason in {
                item["reason"]
                for item in activity_exclusions
                if item["eligibility_status"] == "eligible_unresolved"
            }
        )
    )
    unresolved_session_reasons: dict[str, int] = dict(
        sorted(
            (
                reason,
                sum(
                    item["eligibility_status"] == "eligible_unresolved"
                    and item["reason"] == reason
                    for item in session_exclusions
                ),
            )
            for reason in {
                item["reason"]
                for item in session_exclusions
                if item["eligibility_status"] == "eligible_unresolved"
            }
        )
    )

    def primary_reason(reason_counts: dict[str, int]) -> str | None:
        if not reason_counts:
            return None
        return sorted(reason_counts, key=lambda reason: (-reason_counts[reason], reason))[0]

    metrics = {
        "status": "PASS",
        "relationship_status": "explicit",
        "eligibility_contract": (
            "independent source scope: valid timezone-aware local start and "
            "positive distance or duration; promotion then requires a mutual "
            "unique evidence-qualified candidate"
        ),
        "source_scope_activity_count": len(activities_by_key),
        "source_scope_fit_session_count": len(sessions_by_key),
        "candidate_count": len(candidates),
        "link_count": len(selected),
        "eligible_activity_count": eligible_activity_count,
        "eligible_fit_session_count": eligible_session_count,
        "unresolved_eligible_activity_count": (
            eligible_activity_count - len(selected_activity_keys)
        ),
        "unresolved_eligible_fit_session_count": (
            eligible_session_count - len(selected_session_keys)
        ),
        "candidate_activity_count": candidate_activity_count,
        "candidate_fit_session_count": candidate_session_count,
        "eligible_activity_coverage": (
            len(selected_activity_keys) / eligible_activity_count
            if eligible_activity_count
            else None
        ),
        "eligible_fit_session_coverage": (
            len(selected_session_keys) / eligible_session_count
            if eligible_session_count
            else None
        ),
        "candidate_activity_promotion_coverage": (
            len(selected_activity_keys) / candidate_activity_count
            if candidate_activity_count
            else None
        ),
        "candidate_fit_session_promotion_coverage": (
            len(selected_session_keys) / candidate_session_count
            if candidate_session_count
            else None
        ),
        "ambiguous_count": len(activity_ambiguous) + len(session_ambiguous),
        "ambiguous_activity_count": len(activity_ambiguous),
        "ambiguous_fit_session_count": len(session_ambiguous),
        "duplicate_mapping_count": 0,
        "unresolved_eligible_count": unresolved_eligible_count,
        "unresolved_activity_reason_counts": unresolved_activity_reasons,
        "unresolved_fit_session_reason_counts": unresolved_session_reasons,
        "primary_unresolved_activity_reason": primary_reason(
            unresolved_activity_reasons
        ),
        "primary_unresolved_fit_session_reason": primary_reason(
            unresolved_session_reasons
        ),
        "inference_performed": False,
        "excluded_activity_count": excluded_activity_count,
        "excluded_fit_session_count": excluded_session_count,
    }
    audit = {
        "format": "garmin-running-data-normalizer-activity-fit-audit-v1",
        "metrics": metrics,
        "activity_exclusions": activity_exclusions,
        "fit_session_exclusions": session_exclusions,
    }
    return selected, audit, metrics


__all__ = [
    "RelationshipContractError",
    "build_activity_fit_relationship",
    "validate_declared_relationships",
]
