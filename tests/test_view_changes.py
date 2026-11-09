"""The records that changed between two outputs (stage X7 of v2.3.0): the
comparison of two readings (view.changes), the output before that the view
page compares an output with (gui.outputs.output_before, change_reasons), the
answer of the view page (/api/view/changes) and the numbers of the
normalization page (/api/changes).

Synthetic data only: rows made by hand, and two synthetic Exports normalized
in this test's folder, the second the first with a few records changed
(write_changed_exports). Every server test has its own settings
(``tests/conftest.py``).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer import __version__
from garmin_running_data_normalizer.gui import places
from garmin_running_data_normalizer.gui import server as gui_server
from garmin_running_data_normalizer.gui import settings as gui_settings
from garmin_running_data_normalizer.gui import views as gui_views
from garmin_running_data_normalizer.gui.outputs import change_reasons, output_before, output_summary
from garmin_running_data_normalizer.run_all import RUN_ALL_VERSION, run_all
from garmin_running_data_normalizer.view import changes as changes_module
from garmin_running_data_normalizer.view.changes import (
    CHANGE_FIELDS,
    CHANGE_ITEMS,
    change_answer,
    change_counts,
    compare_outputs,
)
from garmin_running_data_normalizer.view.data import MANIFEST, Gear, Names, Row, Shoe, ViewData
from garmin_running_data_normalizer.view.items import ACTIVITIES, ITEMS_BY_KEY
from garmin_running_data_normalizer.gui.server import API_ROUTES
from tests.test_gui_accessibility import STATIC_ROOT, by_id, page
from tests.test_gui_runs import child_environment, wait_until
from tests.test_gui_server import GuiServerTestCase
from tests.test_gui_view_save import function_body
from tests.test_view_series import dataset_fields, view_data
from tests.view_export import write_view_export

_MADE: dict[str, Any] = {}


def run(when: str, key: str, kind: str = "running", moment: str | None = None, **values: float | None) -> tuple[str, Row]:
    """An activity with its declared key, made by hand."""
    marks: dict[str, Any] = {"type": kind, "key": key}
    if moment is not None:
        marks["datetime"] = moment
    fields = dataset_fields(ACTIVITIES)
    return ACTIVITIES, Row(date.fromisoformat(when).toordinal(), {name: values.get(name) for name in fields}, frozenset(), marks)


def shoe(key: str, name: str, place: int, **set_by_garmin: Any) -> Shoe:
    return Shoe(key=key, name=name, begin=set_by_garmin.get("begin"), end=set_by_garmin.get("end"), maximum=set_by_garmin.get("maximum"), place=place)


def reading(rows: list[tuple[str, Row]], names: dict[str, str] | None = None, gear: Gear | None = None, too_large: str = "") -> ViewData:
    """A reading of an output: its rows, the names of its activities, and its
    shoes; ``too_large`` names the parts left out for their size."""
    made_names = None if names is None else Names(names=names, folded={}, too_large="names" in too_large)
    made_gear = gear if gear is None or "gear" not in too_large else replace(gear, too_large=True)
    return replace(view_data(rows), names=made_names, gear=made_gear)


def field_names(answer: dict[str, Any]) -> list[list[str]]:
    return [[entry["field"] for entry in row["fields"]] for row in answer["list_changed"]]


class CompareTest(unittest.TestCase):
    """The comparison of two readings made by hand."""

    def setUp(self) -> None:
        self.shoes_before = (shoe("A", "Road A", 0, maximum=800000.0), shoe("B", "Road B", 1), shoe("C", "Trail C", 2))
        self.before = reading(
            [
                run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", distance_m=5000.0, duration_sec=1500.0),
                run("2025-06-02", "k2", moment="2025-06-02T06:00:00+09:00", distance_m=6000.0),
                run("2025-06-03", "k3", moment="2025-06-03T06:00:00+09:00", distance_m=7000.0),
                run("2025-06-04", "k4", moment="2025-06-04T06:00:00+09:00", distance_m=8000.0),
                run("2025-06-05", "k5", moment="2025-06-05T06:00:00+09:00", distance_m=9000.0),
            ],
            names={"k1": "Easy", "k2": "Tempo", "k3": "Long", "k4": "Hills", "k5": "Track"},
            gear=Gear(shoes=self.shoes_before, links={"k1": frozenset({"A"}), "k2": frozenset({"A"}), "k3": frozenset({"B"}), "k4": frozenset({"B"})}, unknown=frozenset()),
        )
        self.shoes_now = (shoe("A", "Road A", 0, maximum=1000000.0), shoe("C", "Trail C", 1), shoe("D", "Road D", 2))
        self.now = reading(
            [
                # k1: its distance; k2: its name and its shoes; k3: its shoes
                # only; k4: gone; k5: the same; k6: new.
                run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", distance_m=5100.0, duration_sec=1500.0),
                run("2025-06-02", "k2", moment="2025-06-02T06:00:00+09:00", distance_m=6000.0),
                run("2025-06-03", "k3", moment="2025-06-03T06:00:00+09:00", distance_m=7000.0),
                run("2025-06-05", "k5", moment="2025-06-05T06:00:00+09:00", distance_m=9000.0),
                run("2025-06-06", "k6", moment="2025-06-06T07:30:00+09:00", distance_m=10000.0),
            ],
            names={"k1": "Easy", "k2": "Tempo run", "k3": "Long", "k5": "Track", "k6": "New"},
            gear=Gear(shoes=self.shoes_now, links={"k1": frozenset({"A"}), "k2": frozenset({"D"}), "k3": frozenset({"C"}), "k6": frozenset({"D"})}, unknown=frozenset()),
        )

    def test_new_removed_and_changed_activities_and_shoes(self) -> None:
        changes = compare_outputs(self.before, self.now)
        self.assertEqual([activity.row.marks["key"] for activity in changes.added], ["k6"])
        self.assertEqual([activity.row.marks["key"] for activity in changes.removed], ["k4"])
        self.assertEqual(
            [(now.row.marks["key"], fields) for _before, now, fields in changes.changed],
            [("k2", ("name", "shoes")), ("k1", ("dist",))],
        )
        self.assertEqual([now.row.marks["key"] for _before, now in changes.shoes_changed], ["k3"])
        self.assertEqual([pair.key for pair in changes.pairs_added], ["D"])
        self.assertEqual([pair.key for pair in changes.pairs_removed], ["B"])
        self.assertEqual([(now.key, fields) for _before, now, fields in changes.pairs_changed], [("A", ("maximum",))])
        self.assertEqual(
            change_counts(changes),
            {
                "added": 1,
                "removed": 1,
                "changed": 2,
                "shoes_changed": 1,
                "unmatched": {"before": 0, "now": 0},
                "pairs": {"added": 1, "removed": 1, "changed": 1},
                "names_unread": None,
                "shoes_unread": None,
            },
        )

    def test_the_same_readings_have_no_change(self) -> None:
        self.assertEqual(
            change_counts(compare_outputs(self.now, self.now)),
            {
                "added": 0,
                "removed": 0,
                "changed": 0,
                "shoes_changed": 0,
                "unmatched": {"before": 0, "now": 0},
                "pairs": {"added": 0, "removed": 0, "changed": 0},
                "names_unread": None,
                "shoes_unread": None,
            },
        )

    def test_each_field_of_the_list_is_compared(self) -> None:
        values = {ITEMS_BY_KEY[key].field: 100.0 for key in CHANGE_ITEMS}
        base = reading([run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", **values)], names={"k1": "Easy"})
        self.assertEqual(CHANGE_FIELDS, ("when", "type", "name", "dist", "time", "hr", "mx", "cad", "asc", "shoes"))
        cases: list[tuple[str, ViewData]] = [
            ("when", reading([run("2025-06-01", "k1", moment="2025-06-01T06:05:00+09:00", **values)], names={"k1": "Easy"})),
            ("when", reading([run("2025-06-02", "k1", moment="2025-06-01T06:00:00+09:00", **values)], names={"k1": "Easy"})),
            ("type", reading([run("2025-06-01", "k1", "trail_running", moment="2025-06-01T06:00:00+09:00", **values)], names={"k1": "Easy"})),
            ("name", reading([run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", **values)], names={"k1": "Easy 2"})),
            ("name", reading([run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", **values)], names={})),
        ]
        for key in CHANGE_ITEMS:
            field = ITEMS_BY_KEY[key].field
            cases.append((key, reading([run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", **{**values, field: 101.0})], names={"k1": "Easy"})))
            # A value against none differs too.
            cases.append((key, reading([run("2025-06-01", "k1", moment="2025-06-01T06:00:00+09:00", **{**values, field: None})], names={"k1": "Easy"})))
        for expected, now in cases:
            with self.subTest(field=expected):
                changes = compare_outputs(base, now)
                self.assertEqual([fields for _before, _now, fields in changes.changed], [(expected,)])
        # The pace is not compared: it is made of the distance and the time.
        self.assertNotIn("pace", CHANGE_ITEMS)

    def test_the_shoes_of_an_activity_are_its_pairs_and_a_link_that_tells_no_shoe(self) -> None:
        pairs = (shoe("A", "Road A", 0),)
        base = reading([run("2025-06-01", "k1")], names={}, gear=Gear(shoes=pairs, links={"k1": frozenset({"A"})}, unknown=frozenset()))
        unknown = reading([run("2025-06-01", "k1")], names={}, gear=Gear(shoes=pairs, links={"k1": frozenset({"A"})}, unknown=frozenset({"k1"})))
        none = reading([run("2025-06-01", "k1")], names={}, gear=Gear(shoes=pairs, links={}, unknown=frozenset()))
        for now in (unknown, none):
            changes = compare_outputs(base, now)
            self.assertEqual(len(changes.shoes_changed), 1)
            self.assertEqual(changes.changed, ())
        answer = change_answer(compare_outputs(base, unknown), base, unknown)
        [row] = answer["list_shoes_changed"]
        self.assertEqual((row["before"], row["now"]), ({"shoes": [0], "unknown": False}, {"shoes": [0], "unknown": True}))

    def test_activities_without_a_key_or_with_a_key_held_twice_are_counted_apart(self) -> None:
        before = reading([run("2025-06-01", "k1"), run("2025-06-02", ""), run("2025-06-03", "k3")], names={})
        now = reading([run("2025-06-01", "k1"), run("2025-06-02", "k2"), run("2025-06-02", "k2"), run("2025-06-03", ""), run("2025-06-04", "")], names={})
        changes = compare_outputs(before, now)
        self.assertEqual((changes.unmatched_before, changes.unmatched_now), (1, 4))
        self.assertEqual([activity.row.marks["key"] for activity in changes.removed], ["k3"])
        self.assertEqual((changes.added, changes.changed), ((), ()))

    def test_names_that_one_reading_left_out_are_not_compared(self) -> None:
        for before_part, now_part, unread in (
            ("names", "", "before"),
            ("", "names", "now"),
            ("names", "names", "both"),
        ):
            with self.subTest(unread=unread):
                before = replace(self.before, names=replace(self.before.names, too_large=True)) if before_part else self.before
                now = replace(self.now, names=replace(self.now.names, too_large=True)) if now_part else self.now
                changes = compare_outputs(before, now)
                self.assertEqual(changes.names_unread, unread)
                self.assertNotIn("name", [field for _before, _now, fields in changes.changed for field in fields])
                self.assertTrue(all(activity.name is None for activity in changes.added))
        # Names not read at all (None) are left out the same way.
        changes = compare_outputs(replace(self.before, names=None), self.now)
        self.assertEqual(changes.names_unread, "before")
        # The run renamed whose shoes changed has only its shoes changed then.
        self.assertEqual([(now.row.marks["key"], fields) for _before, now, fields in changes.changed], [("k1", ("dist",))])
        self.assertEqual([now.row.marks["key"] for _before, now in changes.shoes_changed], ["k3", "k2"])

    def test_shoes_that_one_reading_left_out_are_not_compared(self) -> None:
        for before_gear, now_gear, unread in (
            (replace(self.before.gear, too_large=True), self.now.gear, "before"),
            (self.before.gear, None, "now"),
            (None, replace(self.now.gear, too_large=True), "both"),
        ):
            with self.subTest(unread=unread):
                changes = compare_outputs(replace(self.before, gear=before_gear), replace(self.now, gear=now_gear))
                self.assertEqual(changes.shoes_unread, unread)
                self.assertEqual((changes.shoes_changed, changes.pairs_added, changes.pairs_removed, changes.pairs_changed), ((), (), (), ()))
                self.assertEqual([(now.row.marks["key"], fields) for _before, now, fields in changes.changed], [("k2", ("name",)), ("k1", ("dist",))])
                answer = change_answer(changes, replace(self.before, gear=before_gear), replace(self.now, gear=now_gear))
                self.assertEqual((answer["shoes_before"], answer["shoes_now"], answer["list_pairs"]), ([], [], []))
                self.assertEqual(answer["list_added"][0]["shoes"], [])

    def test_newest_first_by_the_day_and_the_time_of_the_day(self) -> None:
        before = reading([], names={})
        now = reading(
            [
                run("2025-06-01", "a", moment="2025-06-01T21:00:00+09:00"),
                run("2025-06-02", "b", moment="2025-06-02T06:00:00-05:00"),
                run("2025-06-02", "c", moment="2025-06-02T05:00:00+09:00"),
                run("2025-06-02", "d"),
            ],
            names={},
        )
        self.assertEqual([activity.row.marks["key"] for activity in compare_outputs(before, now).added], ["b", "c", "d", "a"])

    def test_the_time_of_the_day_keeps_its_fraction_and_the_key_comes_last(self) -> None:
        # Codex's review of the diff of X7, 4: the fraction of a second orders
        # activities of the same second, and the key those of the same moment.
        before = reading([], names={})
        now = reading(
            [
                run("2025-06-02", "a", moment="2025-06-02T06:00:00.100000+09:00"),
                run("2025-06-02", "b", moment="2025-06-02T06:00:00.900000+09:00"),
                run("2025-06-02", "c", moment="2025-06-02T06:00:00+09:00"),
                # Eight of one moment, in the order of their keys, whatever the
                # order of a set of them.
                *(run("2025-06-02", f"t{number}", moment="2025-06-02T07:00:00+09:00") for number in (3, 6, 0, 7, 1, 5, 2, 4)),
            ],
            names={},
        )
        self.assertEqual(
            [activity.row.marks["key"] for activity in compare_outputs(before, now).added],
            ["t7", "t6", "t5", "t4", "t3", "t2", "t1", "t0", "b", "a", "c"],
        )

    def test_the_answer_gives_the_lists_by_places_and_never_a_declared_key(self) -> None:
        changes = compare_outputs(self.before, self.now)
        answer = change_answer(changes, self.before, self.now)
        # Only the shoes that the rows given name, in the order of the output:
        # Trail C of the output before is in no row of it (Codex's review of the
        # diff of X7, 2).
        self.assertEqual([entry["name"] for entry in answer["shoes_before"]], ["Road A", "Road B"])
        self.assertEqual([entry["name"] for entry in answer["shoes_now"]], ["Road A", "Trail C", "Road D"])
        self.assertEqual(
            answer["list_added"],
            [
                {
                    "day": "2025-06-06",
                    "datetime": "2025-06-06T07:30:00+09:00",
                    "type": "running",
                    "name": "New",
                    "values": {"dist": 10000.0, "time": None, "hr": None, "mx": None, "cad": None, "asc": None},
                    "shoes": [2],
                    "unknown": False,
                }
            ],
        )
        # The shoes of an activity in the output before only are those of the
        # output before, by their places there (Road B is not in the output now).
        self.assertEqual(answer["list_removed"][0]["shoes"], [1])
        self.assertEqual(answer["list_removed"][0]["name"], "Hills")
        self.assertEqual(field_names(answer), [["name", "shoes"], ["dist"]])
        self.assertEqual(
            answer["list_changed"][0]["fields"],
            [
                {"field": "name", "before": "Tempo", "now": "Tempo run"},
                {"field": "shoes", "before": {"shoes": [0], "unknown": False}, "now": {"shoes": [2], "unknown": False}},
            ],
        )
        self.assertEqual(answer["list_changed"][1]["fields"], [{"field": "dist", "before": 5000.0, "now": 5100.0}])
        self.assertEqual(answer["list_shoes_changed"][0]["before"], {"shoes": [1], "unknown": False})
        self.assertEqual(answer["list_shoes_changed"][0]["now"], {"shoes": [1], "unknown": False})
        self.assertEqual(
            answer["list_pairs"],
            [
                {"kind": "added", "pair": 2, "fields": []},
                {"kind": "changed", "pair": 0, "fields": [{"field": "maximum", "before": 800000.0, "now": 1000000.0}]},
                {"kind": "removed", "before_pair": 1, "fields": []},
            ],
        )
        self.assertEqual(answer["more"], {"added": 0, "removed": 0, "changed": 0, "shoes_changed": 0, "pairs": 0})
        text = json.dumps(answer)
        for key in ("k1", "k2", "k3", "k4", "k5", "k6"):
            self.assertNotIn(f'"{key}"', text)

    def test_each_list_of_the_answer_has_its_newest_rows_up_to_the_limit(self) -> None:
        before = reading([], names={})
        now = reading([run(f"2025-06-{day:02d}", f"k{day}") for day in range(1, 8)], names={})
        with patch.object(changes_module, "MAX_CHANGE_ROWS", 3):
            answer = change_answer(compare_outputs(before, now), before, now)
        self.assertEqual([row["day"] for row in answer["list_added"]], ["2025-06-07", "2025-06-06", "2025-06-05"])
        self.assertEqual((answer["added"], answer["more"]["added"]), (7, 4))


def summary_output(folder: Path, *, snapshots: bool = False, version: str = __version__, run_all_version: int = RUN_ALL_VERSION, timezone_name: str = "Asia/Tokyo") -> Path:
    """A folder with the summary of an output only, as output_summary reads it."""
    folder.mkdir(parents=True)
    summary = {
        "family_results": {"activities": {"record_count": 3}},
        "product_version": version,
        "run_all_version": run_all_version,
        "local_timezone": timezone_name,
        "snapshot_lifecycle": {"snapshot_count": 2} if snapshots else None,
    }
    (folder / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


class OutputBeforeTest(unittest.TestCase):
    """The output before that the view page compares an output with."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_the_first_output_after_it_that_is_there_with_a_summary(self) -> None:
        first, second = summary_output(self.root / "first"), summary_output(self.root / "second")
        third = summary_output(self.root / "third")
        unreadable = self.root / "unreadable"
        unreadable.mkdir()
        (unreadable / "run_summary.json").write_text("{", encoding="utf-8")
        remembered = [str(third), str(self.root / "gone"), str(unreadable), str(second), str(first)]
        self.assertEqual(output_before(remembered, third), ("found", second))
        # An older output opened is compared with an output older still,
        # never with a newer one.
        self.assertEqual(output_before(remembered, second), ("found", first))
        self.assertEqual(output_before(remembered, first), ("none", None))
        self.assertEqual(output_before(remembered, self.root / "elsewhere"), ("not_remembered", None))
        self.assertEqual(output_before([], third), ("not_remembered", None))

    def test_two_outputs_are_compared_only_when_made_the_same_way(self) -> None:
        now = output_summary(summary_output(self.root / "now"))
        assert now is not None
        for name, folder, expected in (
            ("same", summary_output(self.root / "same"), []),
            ("snapshots", summary_output(self.root / "snapshots", snapshots=True), ["how"]),
            ("version", summary_output(self.root / "version", version="2.2.0"), ["version"]),
            ("run_all", summary_output(self.root / "run_all", run_all_version=RUN_ALL_VERSION + 1), ["version"]),
            ("timezone", summary_output(self.root / "timezone", timezone_name="UTC"), ["timezone"]),
        ):
            with self.subTest(name=name):
                before = output_summary(folder)
                assert before is not None
                self.assertEqual(change_reasons(before, now), expected)
        before = output_summary(summary_output(self.root / "all", snapshots=True, version="2.2.0", timezone_name="UTC"))
        assert before is not None
        self.assertEqual(change_reasons(before, now), ["how", "version", "timezone"])


LAST_DAY_MS = int(datetime(2025, 6, 30, tzinfo=timezone.utc).timestamp() * 1000)


def write_changed_exports(root: Path) -> tuple[Path, Path]:
    """Two synthetic Exports: that of tests/view_export.py, and the same with a
    run renamed, a distance corrected, a run removed with its links, a run
    whose shoes changed, a new run with a new pair of shoes, and a pair whose
    maximum distance changed. Made-up names and synthetic ids only."""
    before = write_view_export(root / "before-export", gear=True, names=True)
    now = write_view_export(root / "now-export", gear=True, names=True)
    activities_path = now / "DI-Connect-Fitness" / "synthetic_summarizedActivities.json"
    gear_path = now / "DI-Connect-Fitness" / "synthetic_gear.json"
    activities = json.loads(activities_path.read_text(encoding="utf-8"))
    gear = json.loads(gear_path.read_text(encoding="utf-8"))
    rows = activities[0]["summarizedActivitiesExport"]
    container = gear[0]
    links: dict[str, list[dict[str, int]]] = container["gearActivityDTOs"]

    def shoes_of(activity_id: int) -> list[str]:
        return sorted(key for key, items in links.items() if any(item.get("activityId") == activity_id for item in items))

    # The runs before the last day of the synthetic data (30 June 2025): the
    # rows after today (the module has some in 2099) are not compared.
    runs = sorted(
        (row for row in rows if row.get("activityType") == "running" and isinstance(row.get("startTimeGmt"), int) and 0 < row["startTimeGmt"] < LAST_DAY_MS),
        key=lambda row: row["startTimeGmt"],
        reverse=True,
    )
    with_shoes = [row for row in runs if shoes_of(row["activityId"])]
    renamed, corrected, removed, relinked = runs[0], runs[1], runs[2], next(row for row in with_shoes if row not in runs[:3])
    renamed["name"] = "Renamed run"
    corrected["distance"] = int(corrected["distance"]) + 123_400
    rows.remove(removed)
    for key in list(links):
        links[key] = [item for item in links[key] if item.get("activityId") not in (removed["activityId"], relinked["activityId"])]
    links.setdefault("3", []).append({"activityId": relinked["activityId"]})
    container["gearDTOS"].append({"gearPk": 10, "displayName": "Road E", "customMakeModel": "Synthetic road 3", "gearTypeName": "Shoes", "dateBegin": "2025-06-25T00:00:00.0", "maximumMeters": 800000})
    moment = datetime(2025, 6, 29, 6, 0, tzinfo=timezone.utc)
    rows.append({"activityId": 990_001, "activityType": "running", "sportType": "RUNNING", "startTimeGmt": int(moment.timestamp() * 1000), "distance": 800_000, "duration": 2_700_000, "name": "New run"})
    links.setdefault("10", []).append({"activityId": 990_001})
    for pair in container["gearDTOS"]:
        if pair.get("gearPk") == "0123":
            pair["maximumMeters"] = 1_000_000
    container["gearActivityDTOs"] = {key: items for key, items in links.items() if items}
    activities_path.write_text(json.dumps(activities), encoding="utf-8")
    gear_path.write_text(json.dumps(gear, ensure_ascii=False), encoding="utf-8")
    return before, now


EXPECTED_COUNTS = {
    "added": 1,
    "removed": 1,
    "changed": 2,
    "shoes_changed": 1,
    "unmatched": {"before": 0, "now": 0},
    "pairs": {"added": 1, "removed": 0, "changed": 1},
    "names_unread": None,
    "shoes_unread": None,
}


def setUpModule() -> None:
    directory = tempfile.TemporaryDirectory()
    root = Path(directory.name).resolve()
    before_export, now_export = write_changed_exports(root)
    (root / "made").mkdir()
    run_all(before_export, root / "made" / "before", timezone_name="Asia/Tokyo")
    run_all(now_export, root / "made" / "now", timezone_name="Asia/Tokyo")
    run_all(before_export, root / "made" / "utc", timezone_name="UTC")
    _MADE.update(directory=directory, root=root, now_export=now_export)


def tearDownModule() -> None:
    _MADE["directory"].cleanup()


class ChangesApiTest(GuiServerTestCase):
    """The answer of the view page, from two outputs normalized here."""

    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name).resolve()
        for name in ("before", "now", "utc"):
            shutil.copytree(_MADE["root"] / "made" / name, self.parent / name)

    def call(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def remember(self, *names: str) -> None:
        """Remember outputs as runs that made them, the last one newest."""
        for name in names:
            self.assertIsNone(gui_settings.remember_run_at(places.settings_file(), self.parent / name, None))

    def open_view(self, name: str) -> dict[str, Any]:
        status, answer = self.call("/api/view/open", {"output": "chosen", "path": str(self.parent / name)})
        self.assertEqual(status, 200, answer)
        return answer

    def test_an_output_is_compared_with_the_output_before_it(self) -> None:
        self.remember("before", "now")
        opened = self.open_view("now")
        self.assertEqual(opened["changes"], {"state": "ready", "before": "before", "reasons": []})
        status, answer = self.call("/api/view/changes", {"view": opened["view"]})
        self.assertEqual(status, 200)
        self.assertEqual((answer["state"], answer["before"], answer["now"], answer["reasons"]), ("ready", "before", "now", []))
        self.assertEqual({name: answer[name] for name in EXPECTED_COUNTS}, EXPECTED_COUNTS)
        self.assertEqual([row["name"] for row in answer["list_added"]], ["New run"])
        self.assertEqual(sorted(field for row in answer["list_changed"] for field in [entry["field"] for entry in row["fields"]]), ["dist", "name"])
        self.assertEqual(answer["list_pairs"][0]["kind"], "added")
        self.assertEqual(answer["shoes_now"][answer["list_pairs"][0]["pair"]]["name"], "Road E")
        self.assertEqual(type(answer["read"]), int)
        self.assertEqual(set(answer["output"]), {"first_day", "last_day", "types", "partial"})
        text = json.dumps(answer)
        self.assertNotIn(str(self.parent), text)
        self.assertNotIn("garmin_activity_key", text)
        self.assertNotIn("990001", text)

    def test_an_older_output_is_compared_with_an_older_one_or_none(self) -> None:
        self.remember("before", "now")
        opened = self.open_view("before")
        self.assertEqual(opened["changes"], {"state": "none", "before": None, "reasons": []})
        status, answer = self.call("/api/view/changes", {"view": opened["view"]})
        self.assertEqual((status, answer["state"], answer["before"]), (200, "none", None))
        self.assertNotIn("list_added", answer)

    def test_an_output_that_is_not_remembered_is_not_compared(self) -> None:
        self.remember("before")
        opened = self.open_view("now")
        self.assertEqual(opened["changes"], {"state": "not_remembered", "before": None, "reasons": []})
        self.assertEqual(self.call("/api/view/changes", {"view": opened["view"]})[1]["state"], "not_remembered")

    def test_outputs_made_another_way_are_not_compared(self) -> None:
        self.remember("utc", "now")
        opened = self.open_view("now")
        self.assertEqual(opened["changes"], {"state": "differs", "before": "utc", "reasons": ["timezone"]})
        status, answer = self.call("/api/view/changes", {"view": opened["view"]})
        self.assertEqual((status, answer["state"], answer["reasons"]), (200, "differs", ["timezone"]))
        self.assertNotIn("list_added", answer)

    def test_an_output_before_that_cannot_be_read_is_told_and_the_output_stays_open(self) -> None:
        self.remember("before", "now")
        opened = self.open_view("now")
        with (self.parent / "before" / "analysis" / "activities.csv").open("ab") as stream:
            stream.write(b"\n")
        status, answer = self.call("/api/view/changes", {"view": opened["view"]})
        self.assertEqual((status, answer["state"], answer["before"], answer["code"]), (200, "unreadable", "before", "HANDOFF_INVALID"))
        self.assertNotIn("list_added", answer)
        # The output shown stays open.
        status, again = self.call("/api/view/changes", {"view": opened["view"]})
        self.assertEqual((status, again["state"]), (200, "unreadable"))

    def test_the_output_before_is_read_once_and_again_when_it_changes(self) -> None:
        self.remember("before", "now")
        opened = self.open_view("now")
        loads: list[Path] = []
        real = gui_views.load_view

        def counted(output: Path) -> ViewData:
            loads.append(output)
            return real(output)

        with patch.object(self.server.views, "_load", counted):
            first = self.call("/api/view/changes", {"view": opened["view"]})[1]
            second = self.call("/api/view/changes", {"view": opened["view"]})[1]
            self.assertEqual(loads, [self.parent / "before"])
            manifest = self.parent / "before" / MANIFEST
            status = os.stat(manifest)
            os.utime(manifest, ns=(status.st_atime_ns, status.st_mtime_ns + 1_000_000_000))
            third = self.call("/api/view/changes", {"view": opened["view"]})[1]
        self.assertEqual(loads, [self.parent / "before", self.parent / "before"])
        for answer in (first, second, third):
            self.assertEqual({name: answer[name] for name in EXPECTED_COUNTS}, EXPECTED_COUNTS)

    def test_another_output_before_is_read_in_the_place_of_the_one_kept(self) -> None:
        shutil.copytree(self.parent / "before", self.parent / "middle")
        self.remember("before", "middle", "now")
        opened = self.open_view("now")
        loads: list[Path] = []
        real = gui_views.load_view

        def counted(output: Path) -> ViewData:
            loads.append(output)
            return real(output)

        with patch.object(self.server.views, "_load", counted):
            self.assertEqual(self.call("/api/view/changes", {"view": opened["view"]})[1]["before"], "middle")
            # The output before is not there any more: the one before it is
            # the output before now.
            (self.parent / "middle").rename(self.parent / "middle-moved")
            self.assertEqual(self.call("/api/view/changes", {"view": opened["view"]})[1]["before"], "before")
        self.assertEqual(loads, [self.parent / "middle", self.parent / "before"])

    def test_an_answer_over_the_limit_of_its_size_is_refused(self) -> None:
        self.remember("before", "now")
        opened = self.open_view("now")
        with patch.object(gui_server, "MAX_ANSWER_BYTES", 1000):
            self.assertEqual(self.call("/api/view/changes", {"view": opened["view"]}), (422, {"error": "VIEW_ANSWER_TOO_LARGE"}))
        self.assertEqual(self.call("/api/view/changes", {"view": opened["view"]})[0], 200)

    def test_requests_of_another_form_are_refused(self) -> None:
        self.assertEqual(self.call("/api/view/changes", {}), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(self.call("/api/view/changes", {"view": 3}), (422, {"error": "REQUEST_INVALID"}))
        self.assertEqual(self.call("/api/view/changes", {"view": "unknown"}), (409, {"error": "VIEW_NOT_OPEN"}))


class RunChangesApiTest(GuiServerTestCase):
    """The numbers of the normalization page, after a run through the API."""

    idle_timeout = None

    def setUp(self) -> None:
        super().setUp()
        environment = patch.dict(os.environ, child_environment())
        environment.start()
        self.addCleanup(environment.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name).resolve()
        for name in ("before", "utc"):
            shutil.copytree(_MADE["root"] / "made" / name, self.parent / name)

    def call(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def run_now(self, timezone_name: str = "Asia/Tokyo") -> None:
        request = {"input": str(_MADE["now_export"]), "output_parent": str(self.parent), "output_name": "now", "timezone": timezone_name}
        self.assertEqual(self.call("/api/run/start", request)[0], 200)
        answer: dict[str, Any] = {}

        def finished() -> bool:
            nonlocal answer
            answer = self.call("/api/run/status", {})[1]
            return answer["state"] in {"finished", "failed"}

        self.assertTrue(wait_until(finished, 120.0))
        self.assertEqual(answer["state"], "finished")

    def test_the_run_is_compared_with_the_output_before_it(self) -> None:
        self.assertIsNone(gui_settings.remember_run_at(places.settings_file(), self.parent / "before", None))
        self.start_server(600.0)
        self.assertEqual(self.call("/api/changes", {"list": 1, "index": 0}), (409, {"error": "NO_FINISHED_OUTPUT"}))
        self.run_now()
        outputs = self.call("/api/outputs", {})[1]
        previous = outputs["previous"]
        self.assertEqual(previous["name"], "before")
        status, answer = self.call("/api/changes", {"list": outputs["list"], "index": previous["index"]})
        self.assertEqual(status, 200)
        self.assertEqual(answer, {"state": "ready", "before": "before", "view": True, **EXPECTED_COUNTS})
        # Where the settings do not remember the output of the run, the view
        # page could not open the lists: the numbers come without them
        # (Codex's second read of the diff of X7, 1).
        with patch.object(gui_server, "recent_outputs", lambda: [str(self.parent / "before")]):
            status, answer = self.call("/api/changes", {"list": outputs["list"], "index": previous["index"]})
        self.assertEqual((status, answer["state"], answer["view"]), (200, "ready", False))
        # Numbers only: no list, no name of an activity.
        self.assertNotIn("New run", json.dumps(answer))
        for payload, expected in (
            ({"list": outputs["list"] + 1, "index": previous["index"]}, (409, {"error": "OUTPUT_LIST_CHANGED"})),
            ({"list": outputs["list"], "index": 5}, (422, {"error": "REQUEST_INVALID"})),
            ({"list": outputs["list"], "index": "0"}, (422, {"error": "REQUEST_INVALID"})),
            ({}, (422, {"error": "REQUEST_INVALID"})),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/changes", payload), expected)

    def test_an_output_before_made_another_way_is_not_compared(self) -> None:
        self.assertIsNone(gui_settings.remember_run_at(places.settings_file(), self.parent / "utc", None))
        self.start_server(600.0)
        self.run_now()
        outputs = self.call("/api/outputs", {})[1]
        status, answer = self.call("/api/changes", {"list": outputs["list"], "index": outputs["previous"]["index"]})
        self.assertEqual((status, answer), (200, {"state": "differs", "before": "utc", "reasons": ["timezone"]}))



class PageScriptTest(unittest.TestCase):
    """What the page scripts do with the changes, where node runs none of it:
    the lines held to the bodies of their functions, and the parts of the two
    pages (the partial guard of X7 breaks them one at a time)."""

    def setUp(self) -> None:
        self.view = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.app = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        self.css = (STATIC_ROOT / "view.css").read_text(encoding="utf-8")

    def held(self, script: str, name: str, lines: tuple[str, ...]) -> str:
        body = function_body(script, name)
        for line in lines:
            with self.subTest(function=name, line=line[:60]):
                self.assertIn(line, body)
        return body

    def test_the_routes_of_the_server(self) -> None:
        self.assertEqual((API_ROUTES["/api/changes"], API_ROUTES["/api/view/changes"]), ("_api_changes", "_api_view_changes"))

    def test_the_view_page_enters_and_leaves_the_changes_as_another_view(self) -> None:
        self.held(
            self.view,
            "enterChanges",
            (
                "if (state.view === null || comparing() || changesWhy(state.changesAvailable) !== null) {\n    return;\n  }",
                'listChanged("changes");',
                "state.changes = {};",
                "state.typesOpen = false;",
                "state.conditionsOpen = false;",
                "ui.changesTitle.focus();\n  requestChanges();",
            ),
        )
        self.held(
            self.view,
            "leaveChanges",
            ("state.changes = null;", "state.changesSeq += 1;", "ui.otherViews.focus();", "if (state.panelsStale) {\n    state.panelsStale = false;\n    requestSeries();\n  }"),
        )
        self.held(self.view, "changesShown", ("return state.changes !== null && state.view !== null;",))
        self.held(self.view, "otherShown", ("return plotting() || spreading() || shoesShown() || changesShown();",))
        # Its item of the menu, with why it cannot be chosen, does nothing then.
        self.assertIn(
            'ui.otherChanges.addEventListener("click", () => {\n    if (changesWhy(state.changesAvailable) !== null) {\n      return;\n    }\n    setOtherViews(false);\n    enterChanges();\n  });',
            self.view,
        )
        self.assertIn('ui.changesBack.addEventListener("click", leaveChanges);', self.view)
        self.held(
            self.view,
            "renderOtherViews",
            (
                "const changesNot = changesWhy(state.changesAvailable);",
                'ui.otherChanges.setAttribute("aria-disabled", String(changesNot !== null));',
                "ui.otherChangesWhy.hidden = changesNot === null;",
                'setText(ui.otherChangesWhy, changesNot === null ? "" : describe(changesNot));',
            ),
        )

    def test_the_changes_use_no_period_types_or_conditions_and_are_not_saved(self) -> None:
        for line in (
            # The grouping goes by the comparison alone: its line of what is
            # not used and its groupings read the comparison, which is null
            # while the changes show (the real page of X7, page1).
            "const apart = viewing && comparing();",
            "const noPeriod = apart || (viewing && changesShown());",
            "button.disabled = !viewing || noPeriod;",
            "ui.filtersHint.hidden = !state.hints || !viewing || noPeriod;",
            "ui.typesButton.disabled = !viewing || !types.length || changesShown();",
            "renderConditions(viewing && !changesShown());",
            "ui.changesOff.hidden = !(viewing && changesShown());",
            "ui.compareOff.hidden = !apart;",
            "const byRace = apart && compareByNow() === \"race\";",
        ):
            with self.subTest(line=line):
                self.assertIn(line, self.view)
        self.held(self.view, "saveViewNow", ('shoesShown() ? "shoes" : changesShown() ? "changes" : "panels";',))
        self.assertIn("  renderShoes(live);\n  renderChanges(live);\n", function_body(self.view, "render"))

    def test_the_answers_of_the_changes_are_one_generation(self) -> None:
        body = self.held(
            self.view,
            "requestChanges",
            (
                "if (!changesShown()) {\n    return;\n  }",
                "const seq = ++state.changesSeq;",
                "const payload = { view: state.view.view };",
                'const answer = await callApi("/api/view/changes", payload);',
                "if (!takeReading(payload.view, answer)) {\n      state.changesLoading = false;\n      return;\n    }",
                "otherReading(answer);",
                "state.changesAvailable = changesAvailableFrom(answer);",
                'error.code === "VIEW_NOT_OPEN" && again && state.target !== null',
                "await requestChanges(false);",
                'error.code === "REQUEST_INVALID" && reopenOnce(payload.view)',
                "OUTPUT_STOPS.includes(error.code)",
                "state.changesStop = { code: error.code, detail: error.detail };",
                "if (seq === state.changesSeq) {\n    state.changesLoading = false;\n  }",
            ),
        )
        self.assertEqual(body.count("if (seq !== state.changesSeq) {\n      return;\n    }"), 2)
        opened = function_body(self.view, "openOutput")
        for line in (
            "state.changesSeq += 1;",
            "state.changesAvailable = answer.changes ?? null;",
            "if (state.changes !== null && changesWhy(state.changesAvailable) !== null) {\n      state.changes = null;\n    }",
            "    requestShoes();\n    requestChanges();\n",
            "if (state.showChanges) {\n      state.showChanges = false;\n      if (state.changes === null) {\n        closeOtherViews();\n        enterChanges();\n      }\n    }",
            "      state.changes = null;\n      state.showChanges = false;\n",
        ):
            with self.subTest(line=line[:60]):
                self.assertIn(line, opened)
        self.assertLess(opened.index("state.changesSeq += 1;"), opened.index("const ticket = auto === null"))

    def test_the_address_closes_another_view_for_the_changes(self) -> None:
        # Codex's review of the diff of X7, 1: a tab that showed a comparison
        # or another view shows the changes in its place, the answers of that
        # view on their way dropped.
        body = function_body(self.view, "closeOtherViews")
        for view in ("compare", "plot", "spread", "shoes"):
            for line in (f"state.{view} = null;", f"state.{view}Answer = null;", f"state.{view}Stop = null;", f"state.{view}Loading = false;", f"state.{view}Seq += 1;"):
                with self.subTest(line=line):
                    self.assertIn(line, body)
        self.assertIn("dropShoesWork();", body)

    def test_the_lists_are_drawn_again_only_for_another_answer_and_as_tables(self) -> None:
        self.held(
            self.view,
            "renderChanges",
            (
                "ui.changes.hidden = !shown;",
                'setText(ui.changesLoading, state.changesLoading ? t("view.loading") : "");',
                'drawn !== null && drawn.state === "ready" ? describe(changesOutputs(drawn)) : ""',
                "const lines = drawn === null ? [] : changesLines(drawn).map(describe);",
                "if (ui.changesLists.dataset.drawn !== signature) {",
                "changesTables(drawn, state.language).map(changesTable)",
                "const notes = drawn === null ? [] : changesNotes(drawn).map(describe);",
            ),
        )
        self.held(
            self.view,
            "changesTable",
            ('cell.scope = "col";', 'const cell = element(index === 0 ? "th" : "td", "", describe(value));', 'cell.scope = "row";', "if (list.more !== null) {"),
        )
        # The lists scroll in their own box, and the menu is as wide as its
        # longest item.
        self.assertIn(".changes-body {\n  flex: 1;\n  min-height: 0;\n  overflow: auto;", self.css)
        self.assertIn(".list-table.changes-table {\n  max-height: none;", self.css)
        self.assertIn("  width: max-content;\n  max-width: min(24em, calc(100vw - 32px));", self.css)

    def test_the_address_asks_for_the_changes_once_and_nothing_remembers_it(self) -> None:
        for name in ("start", "addressChanged"):
            body = function_body(self.view, name)
            with self.subTest(function=name):
                self.assertLess(body.index('addressValue("show")'), body.index("readLaunchKey()"))
                self.assertIn('state.showChanges = show === "changes";', body)
        self.assertNotIn("showChanges", function_body(self.view, "rememberItems"))
        self.assertNotIn("changes", function_body(self.view, "viewSettings") if "function viewSettings(" in self.view else "")

    def test_the_normalization_page_counts_the_changes_once_for_a_run(self) -> None:
        self.held(
            self.app,
            "countChanges",
            (
                "FINISHED_STATES.includes(run.state) &&\n    previous !== null &&\n    typeof run.output_path === \"string\" &&\n    changePlan(previous, {",
                "    }).comparable;",
                # The line of an output before that is gone goes, and an answer
                # on its way is dropped (Codex's review of the diff of X7, 3).
                "if (!comparable) {\n    if (state.changes !== null) {\n      state.changes = null;\n      state.changesSeq += 1;\n    }\n    return;\n  }",
                "const asked = JSON.stringify([run.output_path, state.earlier.list, previous.index]);",
                "if (state.changes?.asked === asked) {\n    return;\n  }",
                "requestChanges(asked, state.earlier.list, previous.index);",
            ),
        )
        body = self.held(
            self.app,
            "requestChanges",
            (
                "const seq = ++state.changesSeq;",
                'state.changes = { asked, status: "counting", answer: null, code: null };',
                'const answer = await callApi("/api/changes", { list, index });',
                'answer?.state === "ready"',
            ),
        )
        self.assertEqual(body.count("if (seq !== state.changesSeq) {\n      return;\n    }"), 2)
        self.held(
            self.app,
            "renderChanges",
            (
                "const shown = state.changes !== null && FINISHED_STATES.includes(state.run.state);",
                "ui.runChanges.hidden = !shown;",
                "const changes = changeRecordsView(shown ? state.changes : null);",
                "ui.runChangesButton.hidden = !changes.button;",
            ),
        )
        self.held(self.app, "startRun", ("state.changes = null;\n  state.changesSeq += 1;",))
        self.held(self.app, "loadEarlier", ("countChanges();",))
        self.held(self.app, "renderRun", ("renderChanges();",))
        self.assertIn('ui.runChangesButton.addEventListener("click", () => openViewPage(true, true));', self.app)

    def test_the_parts_of_the_two_pages(self) -> None:
        elements = page("view.html")
        item = by_id(elements, "other-changes")
        self.assertEqual((item.get("role"), item.get("tabindex"), item.get("class")), ("menuitem", "-1", "with-why"))
        self.assertIn("hidden", by_id(elements, "other-changes-why").attributes)
        section = by_id(elements, "changes")
        self.assertIn("hidden", section.attributes)
        self.assertEqual(section.get("aria-labelledby"), "changes-title")
        for name in ("changes-title", "changes-back", "changes-outputs", "changes-loading", "changes-stop", "changes-body", "changes-lines", "changes-lists", "changes-notes"):
            with self.subTest(part=name):
                by_id(elements, name)
        self.assertEqual(by_id(elements, "changes-loading").get("aria-live"), "polite")
        # The box of the lists scrolls, and the keys reach it, as the boxes of
        # the summary and of the laps (Codex's second read of the diff of X7, 2).
        body = by_id(elements, "changes-body")
        self.assertEqual((body.get("tabindex"), body.get("role"), body.get("aria-labelledby")), ("0", "region", "changes-title"))
        off = by_id(elements, "changes-off")
        self.assertEqual((off.get("data-i18n"), "hidden" in off.attributes), ("view.changes.off", True))
        normalization = page("index.html")
        box = by_id(normalization, "run-changes")
        self.assertIn("hidden", box.attributes)
        lines = by_id(normalization, "run-changes-lines")
        self.assertEqual((lines.get("role"), lines.get("aria-live")), ("status", "polite"))
        button = by_id(normalization, "run-changes-button")
        self.assertEqual((button.get("data-i18n"), "hidden" in button.attributes), ("change.records.button", True))



# The words of the guides and of the design document of X7, whole: each
# sentence pinned as the guides join their lines (Japanese without the breaks,
# English with one space).
GUIDE_JA = (
    '前回の出力とくらべられるときは（同じ正規化のしかた・同じバージョン・同じタイムゾーンのとき。[2 回目からの起動](#2-回目からの起動)）、結果の行の下に、前回の出力から変わった記録の数が出ます（2.3.0 から）。新しく入った・値が変わった・靴が変わった・前回の出力にだけあるアクティビティの回数と、新しい・変わった・前回の出力にだけある靴の足の数です。変わった記録があれば、「見るページでくらべる」で、見るページの「前回の出力とくらべる」が開きます（[前回の出力とくらべる](#前回の出力とくらべる230-から)）。数えるために、正規化のページも、前回と今回の出力のアクティビティの値を読みます（読むだけで、どこにも書きません）。',
    '段の上の「ほかの見方」で、段の代わりに「点で並べる」「分かれ方」「靴ごと」か「前回の出力とくらべる」（2.3.0 から）を出します。メニューは、Enter・Space・↓ キーで開いて最初の項目に移り、↑ ↓・Home・End キーで動き、Esc キーでボタンに戻って閉じます。Tab キーか、ほかの所を押しても閉じます。',
    '出ている間は「項目の棚」「レイアウト」「まとめ方」を使いません。フィルターの下に、そのことが 1 行で出ます。「期間」・‹ ›・「範囲を選ぶ…」の日付の欄と「数える種目」「条件…」は使えます。ここで変えた期間と数える種目と条件は、段に戻ってもそのまま段に効きます。「前回の出力とくらべる」の間は、期間・数える種目・条件も使いません。',
    '見ている出力と、その前回の出力のあいだで変わった記録を、表で並べます。新しく入ったアクティビティ、値が変わったアクティビティ（変わった所と、前と今の値）、靴が変わったアクティビティ、前回の出力にだけあるアクティビティと、靴そのもの（新しい靴、名前・使い始めと使い終わりの日・上限の距離が変わった靴、前回の出力にだけある靴）の表です。表の上に、正規化のページと同じ数の行が出ます。どの表も、新しい順です。日時は、年も入れて出します。',
    '前回の出力は、前の出力の一覧（[2 回目からの起動](#2-回目からの起動)）で、見ている出力の 1 つ前の、読める出力です。見ている出力と、正規化のしかた・バージョン・タイムゾーンのどれかが違うとき、前回の出力が無いとき、見ている出力が一覧に無いとき（ほかの場所から選んだ出力や、新しい出力が 10 個できて一覧から外れた出力）は、メニューの項目の下にわけが出て、選べません。',
    'くらべるのは、区切りのアクティビティの一覧の列（日時・名前・種目・距離・時間・平均心拍・最大心拍・ピッチ・総上昇量）と靴です。平均ペースは距離と時間から作るので、距離か時間の変わりとして出ます。毎日の記録（体の記録・推定値）、一覧に無い列（トレーニング負荷・パワーなど）、日付の無い記録と、今日より後の記録はくらべません。期間・数える種目・条件も使いません（記録そのものをくらべます）。',
    'アクティビティは、記録を見分ける欄（`garmin_activity_key`）で合わせます。この欄の無い記録や、同じ値を 2 つ以上の記録が持つものは、合わせずに、その数だけが出ます。id の無い記録は、値が変わると、前回の出力にだけある記録と、新しく入った記録に分かれて出ます。どちらかの出力で、名前や靴のデータが大きすぎて読めなかったときは、名前や靴はくらべず、そのことが出ます。',
    'スナップショットで作った出力どうしでは、Garmin で消したランも出力に残るので、前回の出力にだけある記録には出ません。今回のエクスポートだけで作った出力どうしでだけ出ます。変わったわけ（Garmin で消した・直したなど）は、出力に無いので言いません。',
    '表は、1 つにつき 500 行までです。それより古い分は、数だけが出ます。前回の出力は読むだけで、くらべた結果はどこにも書かず、覚えません（次に開いたときは、段が出ます）。画像では保存できません。正規化のページの「見るページでくらべる」で開いたときも同じです。',
    '前回の出力：前の出力の一覧のうち、いちばん新しく、読める出力です。正規化のページは、これと増減を比べます。見るページの「前回の出力とくらべる」は、見ている出力の 1 つ前の、読める出力とくらべます（2.3.0 から）。',
)
GUIDE_EN = (
    'Where the run can be compared with the output before (normalized the same way, by the same version, with the same timezone; see [Later launches](#later-launches)), a line under the lines of the result gives the numbers of the records that changed since the output before (from 2.3.0): the activities new, with values changed, with shoes changed, and in the output before only, and the pairs of shoes new, changed, and in the output before only. Where a record changed, **Compare on the view page** opens **Compare with the output before** on the view page ([Compare with the output before](#compare-with-the-output-before-from-230)). To count them, the normalization page also reads the values of the activities of the two outputs (it only reads them, and writes nothing).',
    '**Other views** above the panels shows **Plot two items**, **Distribution**, **By shoes**, or **Compare with the output before** (from 2.3.0) in the place of the panels. Enter, Space, or ↓ opens its menu on the first item; ↑, ↓, Home, and End move in it, and Esc closes it, back to its button. Tab or a click elsewhere closes it too.',
    'While one shows, the **Items**, **Layouts**, and **Group by** are not used; a line under the filters says so. The **Period**, ‹ ›, the days of a custom range, **Activity types counted**, and **Conditions…** can be used, and a period, activity types, or conditions changed here stay for the panels when you go back. **Compare with the output before** uses no period, activity types, or conditions either.',
    'It lists the records that changed between the output shown and the output before it: the activities new, the activities whose values changed (what changed, before and now), the activities whose shoes changed, the activities in the output before only, and the shoes themselves (pairs new, pairs whose name, start or end date, or maximum distance changed, and pairs in the output before only). Above the lists, lines give the numbers, as the normalization page does. Each list is newest first, its dates with their years.',
    'The output before is the readable output just before the output shown in the list of earlier outputs (see [Later launches](#later-launches)). Where the two were not normalized the same way, by the same version, and with the same timezone, where there is no output before, or where the output shown is not in that list (one chosen from another place, or one that left it after 10 newer outputs), the item of the menu says why under its name and cannot be chosen.',
    'It compares the columns of the list of a period (date and time, name, type, distance, time, average heart rate, maximum heart rate, cadence, total ascent) and the shoes. The average pace is made of the distance and the time, so its change shows as a change of one of them. The daily records (body records and estimates), the columns that the list does not have (training load, power, and others), records without a date, and records after today are not compared, and no period, activity types, or conditions are used: the records themselves are compared.',
    'The activities are matched by the field that tells records apart (`garmin_activity_key`); a record without it, or with a value that two records or more hold, is not matched, and only their number is given. A record without an id shows as one in the output before only and as one new when its values change. Where one of the outputs had names or shoes too large to read, the names or the shoes are not compared, and a line says so.',
    'Between outputs made from Snapshots, a run deleted in Garmin stays in the output, so it is not among the records in the output before only: only outputs made from one Export alone show it. Why a record changed (deleted or corrected in Garmin, for example) is not in an output, and is not said.',
    'A list has up to 500 rows; the older ones are counted only. The output before is only read: nothing compared is written or remembered (the panels show at the next launch), and the view cannot be saved as a picture. It is the same when **Compare on the view page** of the normalization page opens it.',
    'The output before: the newest output of that list that can be read. The normalization page shows the change since this one. **Compare with the output before** of the view page compares the output shown with the readable output just before it (from 2.3.0).',
)
DESIGN = (
    "From v2.3.0 (stage X7, the Human's choice D of its samples), where the change shows, the fourth box also gives the numbers of the records that changed since the output before, under the lines of the result: the page asks `/api/changes` once for the finished run, with the number of the output before in the list of earlier outputs and the list's mark (a mark that is not the last one is `OUTPUT_LIST_CHANGED`). The server checks the summaries again (`change_reasons`: the same rule as the page's), reads the output of the run and the output before as the view page reads an output (`read_checked`: the same checks and limits for each, a change while reading is `OUTPUT_CHANGED`), keeps neither, and answers the numbers only (`view/changes.py` `change_counts`), with whether the view page can open them (the output of the run among the outputs remembered, with the same output before); an output that cannot be read answers its code, which the line says. Where a record changed and the view page can open them, **Compare on the view page** opens the view page on the output of the run with `show=changes` in the fragment of its address, read once and never remembered.",
    "From v2.3.0 (stage X7) the server also reads the output before the output shown, for the records that changed (see Changes since the output before below), and the normalization page's server reads the output of the run and the output before it for their numbers: with the same checks and the same limits for each output, so that two outputs may take twice the memory of one, as two outputs opened one after the other do. The output before of the view page is kept with the output shown (one at a time) and read again where its stamp or the date of today changed, or where another output is the output before; the normalization page keeps neither.",
    "From v2.3.0 the view page can compare the output shown with the output before it (stage X7, the Human's choice D of the samples: the lists on the view page only, and the numbers on the normalization page). **Compare with the output before**, the last item of **Other views**, shows in the place of the panels the activities new, changed (by field, before and now), with their shoes changed only, and in the output before only, and the pairs of shoes new, changed, and in the output before only, each list newest first and of up to 500 rows (`MAX_CHANGE_ROWS`; the older ones are counted).",
    'The output before is the first output after the output shown among those that the settings remember (newest first) that is there as a plain folder and whose summary can be read (`gui/outputs.py` `output_before`), the rule of the output before a run; `earlier_outputs` is not used, as it gives the outputs newer than an older one shown too. The two are compared only where `change_reasons` gives none (the way of normalizing, the version and the version of Run-All, and the timezone); otherwise, and where the settings do not remember the output shown (`not_remembered`) or no output is after it (`none`), the item of the menu says why under its name and cannot be chosen. The answer of opening an output gives it (`changes`), and the answer of the changes again.',
    'The comparison (`view/changes.py`) reads nothing: it takes two readings (`ViewData`). The activities are matched by their declared key; an activity without one, or with one that another activity of the same output holds, is counted apart for each output. The fields compared are those of the list of a period (`LIST_ITEMS` without the pace, which the distance and the time make), the date and time, the activity type, the name, and the shoes (the pairs that an activity links to, and whether it has a link that tells no shoe); a value against none differs. The names are compared only where both readings read them, and the shoes (their links and the pairs) only where both read them, so that a file left out of one reading never makes every record look changed; the answer says which reading left them out. Rows without a date or after today are not compared, as no view shows them.',
    'The answer never gives the declared keys nor the places of the outputs: the values as numbers, which the page writes as the list of a period does (the dates with their years, as the lists go across the periods), the names of the activities and of the shoes, the shoes by their places in the lists of the shoes of each output (named as the view by shoes names them), and the names of the two outputs; it is refused over `MAX_ANSWER_BYTES`. A reading of the output before that fails answers its code, and the output shown stays open. No period, activity types, or conditions are used, and the view is not saved as a picture; nothing is remembered (it is not a key of the view settings) or written.',
    'From v2.3.0 (stage X7) the view page and the normalization page read the output before an output for the records that changed, as they read an output; the answer of the view page holds the names and the values of the activities that changed and the names of their shoes, as the list of a period and the view by shoes do, and the names of the two outputs, never their places nor the declared keys; the normalization page gets their numbers only. Nothing of it is written or remembered.',
)


class GuideTest(unittest.TestCase):
    """The guides and the design document say the changes since the output
    before, every sentence once, with the words of the pages quoted."""

    def test_the_guides_and_the_design_say_the_changes(self) -> None:
        root = STATIC_ROOT.parents[3]
        texts = {
            "ja": (root / "docs/gui_guide.ja.md").read_text(encoding="utf-8"),
            "en": (root / "docs/gui_guide.md").read_text(encoding="utf-8"),
            "design": (root / "docs/gui_design.md").read_text(encoding="utf-8"),
        }
        joined = {
            "ja": re.sub(r"\n *", "", texts["ja"]),
            "en": " ".join(texts["en"].split()),
            "design": " ".join(texts["design"].split()),
        }
        for name, pins in (("ja", GUIDE_JA), ("en", GUIDE_EN), ("design", DESIGN)):
            for pin in pins:
                with self.subTest(text=name, pin=pin[:40]):
                    self.assertEqual(joined[name].count(pin if name == "ja" else " ".join(pin.split())), 1)
        self.assertIn("\n#### 前回の出力とくらべる（2.3.0 から）\n", texts["ja"])
        self.assertIn("\n#### Compare with the output before (from 2.3.0)\n", texts["en"])
        self.assertIn("\n### Changes since the output before (v2.3.0)\n", texts["design"])
        # The words quoted are those of the pages.
        for language, pins, pattern in (("ja", GUIDE_JA, r"「([^」]+)」"), ("en", GUIDE_EN, r"\*\*([^*]+)\*\*")):
            words = set(json.loads((STATIC_ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8")).values())
            for pin in pins:
                for quoted in re.findall(pattern, pin):
                    with self.subTest(language=language, quoted=quoted):
                        self.assertIn(quoted, words)


if __name__ == "__main__":
    unittest.main()
