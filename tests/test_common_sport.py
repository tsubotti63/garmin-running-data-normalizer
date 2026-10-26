"""The group of a sport, which the link of an activity and a FIT session and
the view page share (stage G1). The tests of the link saw running only, so
these see every branch of the rule, and the link with a sport of each kind."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.common.sport import activity_sport, sport_group
from garmin_running_data_normalizer.fit.parser import parse_fit_export
from garmin_running_data_normalizer.relationships import build_activity_fit_relationship
from tests.fit_fixture_factory import synthetic_fit


def running_session() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / "synthetic_activity.fit").write_bytes(synthetic_fit(sport=1, sub_sport=0))
        sessions, _laps, _audit = parse_fit_export(directory)
    return sessions[0]


def activity_at(session: dict[str, Any], **fields: Any) -> dict[str, Any]:
    start = datetime.fromisoformat(session["start_datetime_local"])
    return {
        "garmin_activity_key": "garmin_activity:synthetic-run",
        "activity_id": 1,
        "activity_datetime_local": start.isoformat(),
        "distance_m": session["distance_m"],
        "duration_sec": session["timer_time_sec"],
        "source_path": "synthetic/activities.json",
        "source_sha256": "a" * 64,
        **fields,
    }


class SportGroupTest(unittest.TestCase):
    def test_every_branch_of_the_rule(self) -> None:
        cases = {
            None: None,
            "": None,
            "   ": None,
            # The FIT numbers of the sports of old files.
            "10": "strength_training",
            "11": "walking",
            "17": "hiking",
            "1": "1",
            # Any name with "run" in it, and the sub-sports of running.
            "running": "running",
            "RUNNING": "running",
            "treadmill_running": "running",
            "Trail Running": "running",
            "track-running": "running",
            "virtual_run": "running",
            "street": "running",
            "trail": "running",
            "strength_training": "strength_training",
            "training": "strength_training",
            "fitness_equipment": "strength_training",
            "FITNESS_EQUIPMENT": "strength_training",
            "walking": "walking",
            "casual_walking": "walking",
            "hiking": "hiking",
            # Any other name is its own group, written in one form.
            "cycling": "cycling",
            "Road Biking": "road_biking",
            "lap_swimming": "lap_swimming",
        }
        for value, group in cases.items():
            with self.subTest(value=value):
                self.assertEqual(sport_group(value), group)

    def test_an_activity_takes_its_sport_type_first_and_else_its_type(self) -> None:
        self.assertEqual(activity_sport({"sport_type": "CYCLING", "activity_type": "running"}), "cycling")
        self.assertEqual(activity_sport({"sport_type": "", "activity_type": "treadmill_running"}), "running")
        self.assertEqual(activity_sport({"activity_type": "hiking"}), "hiking")
        self.assertIsNone(activity_sport({"sport_type": None, "activity_type": ""}))


class SportOfTheLinkTest(unittest.TestCase):
    def test_the_link_reads_the_group_of_each_side(self) -> None:
        session = running_session()
        cases = {
            "running": ({"sport_type": "RUNNING", "activity_type": "running"}, True),
            "a type only": ({"sport_type": "", "activity_type": "treadmill_running"}, True),
            "cycling": ({"sport_type": "CYCLING", "activity_type": "road_biking"}, False),
        }
        for name, (fields, compatible) in cases.items():
            with self.subTest(case=name):
                links, _audit, _metrics = build_activity_fit_relationship([activity_at(session, **fields)], [session])
                # The same start links them either way; the sport adds to the basis.
                self.assertEqual(len(links), 1)
                self.assertEqual("compatible_sport" in links[0]["match_basis"], compatible)


if __name__ == "__main__":
    unittest.main()
