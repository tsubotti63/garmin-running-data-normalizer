from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.fit.parser import parse_fit_export
from garmin_running_data_normalizer.relationships import build_activity_fit_relationship
from tests.fit_fixture_factory import synthetic_fit


def parsed_session(sport: int, sub_sport: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / "synthetic_activity.fit").write_bytes(
            synthetic_fit(sport=sport, sub_sport=sub_sport)
        )
        sessions, _laps, audit = parse_fit_export(directory)
    if [item["parse_status"] for item in audit] != ["parsed_activity"]:
        raise AssertionError(audit)
    return sessions[0]


class FitSportProfileTest(unittest.TestCase):
    def test_sport_and_sub_sport_names_follow_the_fit_profile(self) -> None:
        cases = {
            (0, 0): ("generic", "generic"),
            (1, 0): ("running", "generic"),
            (1, 1): ("running", "treadmill"),
            (1, 2): ("running", "street"),
            (1, 3): ("running", "trail"),
            (2, 6): ("cycling", "indoor_cycling"),
            (2, 7): ("cycling", "road"),
            (2, 8): ("cycling", "mountain"),
            (5, 17): ("swimming", "lap_swimming"),
            (10, 20): ("training", "strength_training"),
            (31, 0): ("rock_climbing", "generic"),
        }
        for (sport, sub_sport), expected in cases.items():
            with self.subTest(sport=sport, sub_sport=sub_sport):
                session = parsed_session(sport, sub_sport)
                self.assertEqual((session["sport"], session["sub_sport"]), expected)

    def test_codes_outside_the_bounded_tables_keep_the_fallback(self) -> None:
        session = parsed_session(60, 99)
        self.assertEqual(session["sport"], "60")
        self.assertIsNone(session["sub_sport"])

    def test_mountain_bike_session_links_to_a_cycling_activity(self) -> None:
        session = parsed_session(2, 8)
        start = datetime.fromisoformat(session["start_datetime_local"])
        activity = {
            "garmin_activity_key": "garmin_activity:synthetic-ride",
            "activity_id": 1,
            "activity_datetime_local": (start + timedelta(seconds=30)).isoformat(),
            "distance_m": session["distance_m"],
            "duration_sec": session["timer_time_sec"],
            "activity_type": "mountain_biking",
            "sport_type": "CYCLING",
            "source_path": "synthetic/activities.json",
            "source_sha256": "a" * 64,
        }

        links, _audit, metrics = build_activity_fit_relationship([activity], [session])

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["match_rule"], "near_start_exact_metrics")
        self.assertIn("compatible_sport", links[0]["match_basis"])
        self.assertEqual(metrics["unresolved_eligible_count"], 0)


if __name__ == "__main__":
    unittest.main()
