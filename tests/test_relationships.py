from __future__ import annotations

import copy
import unittest

from garmin_running_data_normalizer.relationships import (
    RelationshipContractError,
    build_activity_fit_relationship,
    validate_declared_relationships,
)


def activity(
    key: str,
    activity_id: object,
    *,
    start: str = "2030-01-01T09:00:00+09:00",
    distance: float = 5000.0,
    duration: float = 1800.0,
    sport: str = "running",
) -> dict:
    return {
        "garmin_activity_key": key,
        "activity_id": activity_id,
        "activity_datetime_local": start,
        "distance_m": distance,
        "duration_sec": duration,
        "activity_type": sport,
        "sport_type": sport,
        "source_path": "synthetic/activities.json",
        "source_sha256": "a" * 64,
    }


def session(
    key: str,
    *,
    start: str = "2030-01-01T09:00:00+09:00",
    distance: float = 5000.0,
    duration: float = 1800.0,
    sport: str = "running",
) -> dict:
    return {
        "fit_session_key": key,
        "start_datetime_local": start,
        "distance_m": distance,
        "timer_time_sec": duration,
        "sport": sport,
        "source_path": "synthetic/session.fit",
        "source_sha256": "b" * 64,
    }


def declared_records() -> dict[str, list[dict]]:
    return {
        "activities": [activity("garmin_activity:1", 1)],
        "gear": [
            {
                "gear_key": 7,
                "source_path": "synthetic/gear.json",
                "source_sha256": "c" * 64,
            }
        ],
        "activity_gear": [
            {
                "gear_key": "7",
                "activity_id": "1",
                "source_path": "synthetic/gear.json",
                "source_sha256": "c" * 64,
            }
        ],
        "personal_records": [
            {
                "personal_record_id": "pr-1",
                "activity_id": 1,
                "source_path": "synthetic/personal.json",
                "source_sha256": "d" * 64,
            },
            {
                "personal_record_id": "pr-independent",
                "activity_id": 0,
                "source_path": "synthetic/personal.json",
                "source_sha256": "d" * 64,
            },
        ],
        "fit_sessions": [session("fit_session:one")],
        "fit_laps": [
            {
                "fit_lap_key": "fit_session:one:lap:0",
                "fit_session_key": "fit_session:one",
                "source_path": "synthetic/session.fit",
                "source_sha256": "b" * 64,
            }
        ],
    }


class RelationshipContractTest(unittest.TestCase):
    def test_declared_relationships_are_explicit_and_zero_pr_is_independent(self) -> None:
        records = declared_records()
        summary = validate_declared_relationships(records)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(
            records["activity_gear"][0]["garmin_activity_key"],
            "garmin_activity:1",
        )
        self.assertEqual(
            records["personal_records"][0]["activity_relationship_status"],
            "explicit",
        )
        independent = next(
            row
            for row in records["personal_records"]
            if row["personal_record_id"] == "pr-independent"
        )
        self.assertEqual(independent["activity_relationship_status"], "independent")
        self.assertIsNone(independent["garmin_activity_key"])

    def test_declared_relationships_fail_closed_on_orphan_duplicate_null_and_type(self) -> None:
        mutations = []
        orphan_activity = declared_records()
        orphan_activity["activity_gear"][0]["activity_id"] = 999
        mutations.append(orphan_activity)
        orphan_gear = declared_records()
        orphan_gear["activity_gear"][0]["gear_key"] = 999
        mutations.append(orphan_gear)
        orphan_session = declared_records()
        orphan_session["fit_laps"][0]["fit_session_key"] = "missing"
        mutations.append(orphan_session)
        duplicate = declared_records()
        duplicate["activity_gear"].append(copy.deepcopy(duplicate["activity_gear"][0]))
        mutations.append(duplicate)
        null_value = declared_records()
        null_value["personal_records"][0]["activity_id"] = None
        mutations.append(null_value)
        type_mismatch = declared_records()
        type_mismatch["activity_gear"][0]["activity_id"] = 1.5
        mutations.append(type_mismatch)
        unresolved_pr = declared_records()
        unresolved_pr["personal_records"][0]["activity_id"] = 999
        mutations.append(unresolved_pr)
        for records in mutations:
            with self.subTest(records=records), self.assertRaises(
                RelationshipContractError
            ):
                validate_declared_relationships(records)

    def test_activity_fit_link_is_deterministic_and_not_timestamp_only(self) -> None:
        activities = [activity("garmin_activity:1", 1)]
        sessions = [session("fit_session:one")]
        first = build_activity_fit_relationship(activities, sessions)
        second = build_activity_fit_relationship(
            copy.deepcopy(activities),
            copy.deepcopy(sessions),
        )
        self.assertEqual(first, second)
        links, audit, metrics = first
        self.assertEqual(len(links), 1)
        self.assertEqual(metrics["eligible_activity_coverage"], 1.0)
        self.assertEqual(metrics["eligible_fit_session_coverage"], 1.0)
        self.assertEqual(metrics["ambiguous_count"], 0)
        self.assertEqual(metrics["unresolved_eligible_activity_count"], 0)
        self.assertEqual(metrics["unresolved_eligible_fit_session_count"], 0)
        self.assertFalse(metrics["inference_performed"])
        self.assertEqual(audit["activity_exclusions"], [])

        timestamp_only = [
            session(
                "fit_session:timestamp-only",
                distance=9000.0,
                duration=3000.0,
                sport="cycling",
            )
        ]
        links, audit, metrics = build_activity_fit_relationship(
            activities,
            timestamp_only,
        )
        self.assertEqual(links, [])
        self.assertEqual(metrics["eligible_activity_count"], 1)
        self.assertEqual(metrics["eligible_fit_session_count"], 1)
        self.assertEqual(metrics["unresolved_eligible_count"], 2)
        self.assertEqual(metrics["unresolved_eligible_activity_count"], 1)
        self.assertEqual(metrics["unresolved_eligible_fit_session_count"], 1)
        self.assertEqual(
            metrics["primary_unresolved_activity_reason"],
            "no_evidence_qualified_candidate",
        )
        self.assertEqual(
            metrics["primary_unresolved_fit_session_reason"],
            "no_evidence_qualified_candidate",
        )
        self.assertEqual(
            audit["fit_session_exclusions"][0]["reason"],
            "no_evidence_qualified_candidate",
        )

    def test_near_time_requires_exact_metrics_and_ambiguity_is_excluded(self) -> None:
        activities = [activity("garmin_activity:1", 1)]
        near = [
            session(
                "fit_session:near",
                start="2030-01-01T09:00:39+09:00",
            )
        ]
        links, _, _ = build_activity_fit_relationship(activities, near)
        self.assertEqual(links[0]["match_rule"], "near_start_exact_metrics")

        weak_near = [
            session(
                "fit_session:weak",
                start="2030-01-01T09:00:39+09:00",
                distance=5002.0,
            )
        ]
        self.assertEqual(
            build_activity_fit_relationship(activities, weak_near)[0],
            [],
        )

        ambiguous_sessions = [
            session("fit_session:a"),
            session("fit_session:b"),
        ]
        links, audit, metrics = build_activity_fit_relationship(
            activities,
            ambiguous_sessions,
        )
        self.assertEqual(links, [])
        self.assertEqual(metrics["eligible_activity_count"], 1)
        self.assertEqual(metrics["eligible_fit_session_count"], 2)
        self.assertEqual(metrics["eligible_activity_coverage"], 0.0)
        self.assertEqual(metrics["eligible_fit_session_coverage"], 0.0)
        self.assertEqual(metrics["ambiguous_count"], 1)
        self.assertEqual(metrics["unresolved_eligible_count"], 3)
        self.assertEqual(
            audit["activity_exclusions"][0]["reason"],
            "ambiguous_candidate",
        )
        self.assertEqual(
            audit["activity_exclusions"][0]["eligibility_status"],
            "eligible_unresolved",
        )

    def test_missing_optional_fit_produces_explicit_exclusions(self) -> None:
        links, audit, metrics = build_activity_fit_relationship(
            [activity("garmin_activity:1", 1)],
            [],
        )
        self.assertEqual(links, [])
        self.assertEqual(metrics["link_count"], 0)
        self.assertEqual(metrics["eligible_activity_count"], 1)
        self.assertEqual(metrics["excluded_activity_count"], 0)
        self.assertEqual(metrics["unresolved_eligible_count"], 1)
        self.assertEqual(len(audit["activity_exclusions"]), 1)
        self.assertEqual(
            audit["activity_exclusions"][0]["eligibility_status"],
            "eligible_unresolved",
        )

    def test_eligibility_is_independent_of_candidate_existence(self) -> None:
        links, audit, metrics = build_activity_fit_relationship(
            [activity("garmin_activity:1", 1)],
            [
                session(
                    "fit_session:unmatched",
                    start="2030-01-02T09:00:00+09:00",
                )
            ],
        )
        self.assertEqual(links, [])
        self.assertEqual(metrics["eligible_activity_count"], 1)
        self.assertEqual(metrics["eligible_fit_session_count"], 1)
        self.assertEqual(metrics["candidate_activity_count"], 0)
        self.assertEqual(metrics["candidate_fit_session_count"], 0)
        self.assertEqual(metrics["unresolved_eligible_count"], 2)
        self.assertTrue(
            all(
                item["eligibility_status"] == "eligible_unresolved"
                for item in (
                    *audit["activity_exclusions"],
                    *audit["fit_session_exclusions"],
                )
            )
        )

    def test_structurally_unsupported_records_are_excluded_before_matching(self) -> None:
        links, audit, metrics = build_activity_fit_relationship(
            [
                activity(
                    "garmin_activity:invalid",
                    1,
                    start="not-a-datetime",
                    distance=0,
                    duration=0,
                )
            ],
            [
                session(
                    "fit_session:invalid",
                    start="not-a-datetime",
                    distance=0,
                    duration=0,
                )
            ],
        )
        self.assertEqual(links, [])
        self.assertEqual(metrics["eligible_activity_count"], 0)
        self.assertEqual(metrics["eligible_fit_session_count"], 0)
        self.assertEqual(metrics["excluded_activity_count"], 1)
        self.assertEqual(metrics["excluded_fit_session_count"], 1)
        self.assertEqual(
            audit["activity_exclusions"][0]["reason"],
            "missing_or_invalid_start_datetime",
        )
        self.assertEqual(
            audit["fit_session_exclusions"][0]["reason"],
            "missing_or_invalid_start_datetime",
        )

    def test_one_to_one_conflict_reduces_eligible_coverage(self) -> None:
        activities = [
            activity("garmin_activity:best", 1),
            activity(
                "garmin_activity:conflict",
                2,
                distance=9000.0,
                duration=3000.0,
            ),
        ]
        links, audit, metrics = build_activity_fit_relationship(
            activities,
            [session("fit_session:one")],
        )
        self.assertEqual(len(links), 1)
        self.assertEqual(metrics["eligible_activity_count"], 2)
        self.assertEqual(metrics["eligible_activity_coverage"], 0.5)
        self.assertEqual(metrics["eligible_fit_session_coverage"], 1.0)
        self.assertEqual(metrics["unresolved_eligible_count"], 1)
        conflict = next(
            item
            for item in audit["activity_exclusions"]
            if item["garmin_activity_key"] == "garmin_activity:conflict"
        )
        self.assertEqual(conflict["reason"], "one_to_one_conflict")
        self.assertEqual(conflict["eligibility_status"], "eligible_unresolved")


if __name__ == "__main__":
    unittest.main()
