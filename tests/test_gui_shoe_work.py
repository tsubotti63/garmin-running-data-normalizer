"""The work laps of the shoes of a period (stage X11 of v2.3.0): the reading of
the laps of many activities (gui.fit_reading.read_many_laps) and their sums by
pair of shoes (gui.shoe_work).

The outputs and the stores are made as the CLI and the GUI make them: a
synthetic Export registered in a store, normalized from the store with
run_snapshot_all. Synthetic data and made-up names only.
"""
from __future__ import annotations

import inspect
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from garmin_running_data_normalizer.gui import fit_reading, shoe_work
from garmin_running_data_normalizer.gui import settings as gui_settings
from garmin_running_data_normalizer.gui.fit_reading import (
    LINEAGE,
    LapRow,
    Laps,
    ManyLaps,
    read_laps,
    read_many_laps,
)
from garmin_running_data_normalizer.gui.shoe_work import (
    MAX_WORK_RUNS,
    NOT_COUNTED,
    RUN_COUNTS,
    SUMS,
    WORK_KINDS,
    _add,
    _empty,
    work_answer,
    work_known,
    work_runs,
)
from garmin_running_data_normalizer.output_check import OutputActionError
from garmin_running_data_normalizer.snapshot import initialize_store, register_snapshot, run_snapshot_all
from garmin_running_data_normalizer.view.data import load_view_data
from garmin_running_data_normalizer.view.items import ACTIVITIES
from garmin_running_data_normalizer.view.series import shoe_answer, shoe_order
from tests.fit_fixture_factory import synthetic_fit
from tests.test_fit_running_dynamics import FIT_SESSION_START_MS
from tests.test_gui_fit_reading import WINDOWS, blob, entries, make_link, rewrite, writable
from tests.test_gui_server import GuiServerTestCase
from tests.view_export import write_view_export

ACCOUNT = "synthetic-account-x11"
# Intensities of the FIT profile: 0 active, 1 rest, 2 warmup, 3 cooldown,
# 4 recovery, 5 interval.
INTERVALS = (2, 5, 4, 5, 4, 5, 3)
EASY = (0, 0, 0)
RESTS = (1, 1)
DAY = 86_400
SHOES = [
    {"gearPk": 1, "displayName": "Made-up road", "customMakeModel": "Synthetic road", "gearTypeName": "Shoes", "dateBegin": "2023-01-01T00:00:00.0"},
    {"gearPk": 2, "displayName": "Made-up race", "customMakeModel": "Synthetic race", "gearTypeName": "Shoes", "dateBegin": "2023-01-01T00:00:00.0"},
]


def build(root: Path, runs: list[tuple[tuple[int, ...] | None, tuple[int, ...]]]) -> tuple[Path, Path]:
    """A synthetic Export of running activities, one a day, each with a FIT
    file whose laps have the intensities given (None: laps without one) and
    linked to the gear given (by gearPk); its store and its output."""
    export = root / "export"
    fitness = export / "DI-Connect-Fitness"
    uploaded = export / "DI-Connect-Uploaded-Files"
    fitness.mkdir(parents=True)
    uploaded.mkdir()
    activities, links = [], {}
    for number, (intensities, gear) in enumerate(runs, 1):
        offset = (number - 1) * DAY
        fit = synthetic_fit(first_start=1_000_000 + offset, lap_intensities=intensities)
        (uploaded / f"synthetic_activity_{number}.fit").write_bytes(fit)
        activities.append({
            "activityId": number,
            "activityType": "running",
            "sportType": "RUNNING",
            "startTimeGmt": FIT_SESSION_START_MS + offset * 1000 + 30_000,
            "distance": 1_000_000,
            "duration": 3_500_000,
            "name": f"Synthetic {number}",
        })
        for key in gear:
            links.setdefault(str(key), []).append({"activityId": number})
    (fitness / "synthetic_summarizedActivities.json").write_text(json.dumps([{"summarizedActivitiesExport": activities}]), encoding="utf-8")
    (fitness / "synthetic_gear.json").write_text(json.dumps([{"gearDTOS": SHOES, "gearActivityDTOs": links}]), encoding="utf-8")
    store, output = root / "store", root / "out"
    initialize_store(store, ACCOUNT)
    register_snapshot(
        store,
        export,
        snapshot_label="S1",
        export_requested_at="2030-01-01T00:00:00+00:00",
        export_downloaded_at="2030-01-01T01:00:00+00:00",
        export_observed_at="2030-01-01T02:00:00+00:00",
        confirm_complete=True,
    )
    run_snapshot_all(store, output)
    return store, output


def keys_of(output: Path) -> list[str | None]:
    data = load_view_data(output, gear=True)
    return [row.marks.get("key") for row in data.rows[ACTIVITIES]]


def lap(kind: str, timer: float | None = 100.0, distance: float | None = 400.0, heart: float | None = 150.0) -> LapRow:
    return LapRow(kind=kind, elapsed_s=timer, timer_s=timer, distance_m=distance, avg_heart_rate=heart, max_heart_rate=heart, avg_cadence=None, avg_speed=None)


class ManyLapsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self) -> None:
        for path in self.root.rglob("*"):
            if not path.is_symlink():
                writable(path)
        self.directory.cleanup()

    def test_each_activity_is_read_as_read_laps_reads_it(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (1,)), (RESTS, (2,)), (None, (2,)), (INTERVALS, (1, 2))])
        files = entries(output)
        keys = keys_of(output)
        # A FIT file missing, and one changed, for two of the activities.
        digests = [link["fit_source_sha256"] for link in json.loads((output / fit_reading.LINKS).read_text(encoding="utf-8"))]
        os.remove(writable(blob(store, digests[1])))
        writable(blob(store, digests[2])).write_bytes(b"other bytes")
        many = read_many_laps(output, files, keys, store)
        self.assertEqual(many.status, "laps")
        self.assertEqual(many.done, len(keys))
        self.assertEqual(list(many.runs), [read_laps(output, files, key, store) for key in keys])
        self.assertEqual([run.reason for run in many.runs][1:3], ["fit_missing", "fit_changed"])

    def test_a_key_shared_and_the_reasons_of_the_output_are_told(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (1,))])
        files = entries(output)
        keys = keys_of(output)
        self.assertEqual(read_many_laps(output, files, [None, keys[1]], store).runs[0], Laps("unavailable", "key_shared"))
        self.assertEqual(read_many_laps(output, files, keys, None), ManyLaps("unavailable", "no_store"))
        without = {name: entry for name, entry in files.items() if name != LINEAGE}
        self.assertEqual(read_many_laps(output, without, keys, store), ManyLaps("unavailable", "not_from_store"))
        other = self.root / "other"
        initialize_store(other, "synthetic-account-other")
        self.assertEqual(read_many_laps(output, files, keys, other), ManyLaps("unavailable", "other_store"))

    def test_the_rows_of_the_output_are_checked_as_read_laps_checks_them(self) -> None:
        # The index of a request finds an activity with the checks of
        # read_laps, over all the rows of the output: those of the activities
        # not asked for too (Codex's review of the plan of X11, 1 and 18).
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (1,)), (RESTS, (2,))])
        files = entries(output)
        keys = keys_of(output)
        original = {name: json.loads((output / name).read_text(encoding="utf-8")) for name in (fit_reading.LINKS, fit_reading.SESSIONS, fit_reading.LAPS)}
        links, sessions = original[fit_reading.LINKS], original[fit_reading.SESSIONS]
        first = next(row for row in links if row["garmin_activity_key"] == keys[0])
        second = next(row for row in links if row["garmin_activity_key"] == keys[1])
        others = [row for row in links if row is not first and row is not second]
        laps = sorted((row for row in original[fit_reading.LAPS] if row["fit_session_key"] == first["fit_session_key"]), key=lambda row: row["lap_ordinal_within_session"])
        rest = [row for row in original[fit_reading.LAPS] if row["fit_session_key"] != first["fit_session_key"]]
        for name, relative, rows in (
            ("the session linked to an activity not asked for too", fit_reading.LINKS, [first, {**second, "fit_session_key": first["fit_session_key"]}, *others]),
            ("two links of the activity", fit_reading.LINKS, [first, first, second, *others]),
            # The other link first, to a session of no other row: only the
            # links of the activity tell (the guard of X11, ZR9).
            ("two links of the activity, the first to a session of no other row", fit_reading.LINKS, [{**first, "fit_session_key": "fit_session:" + "0" * 64 + ":0"}, first, second, *others]),
            ("two sessions", fit_reading.SESSIONS, [*sessions, next(row for row in sessions if row["fit_session_key"] == first["fit_session_key"])]),
            ("a lap fewer", fit_reading.LAPS, [*laps[:-1], *rest]),
            ("another SHA-256 of a lap", fit_reading.LAPS, [{**laps[0], "source_sha256": "0" * 64}, *laps[1:], *rest]),
        ):
            with self.subTest(name):
                rewrite(output, files, relative, rows)
                try:
                    alone = read_laps(output, files, keys[0], store)
                except OutputActionError as exc:
                    for asked in (keys[:1], keys):
                        with self.assertRaises(OutputActionError) as caught:
                            read_many_laps(output, files, asked, store)
                        self.assertEqual(caught.exception.code, exc.code)
                else:
                    self.assertEqual(alone.status, "unavailable")
                    self.assertEqual(read_many_laps(output, files, keys[:1], store).runs, (alone,))
                    self.assertEqual(read_many_laps(output, files, keys, store).runs[0], alone)
                rewrite(output, files, relative, original[relative])
        self.assertEqual(read_many_laps(output, files, keys, store).runs, tuple(read_laps(output, files, key, store) for key in keys))

    def test_a_request_ends_before_the_fit_file_past_its_budget(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (INTERVALS, (1,)), (INTERVALS, (1,))])
        files = entries(output)
        keys = keys_of(output)
        size = blob(store, json.loads((output / fit_reading.LINKS).read_text(encoding="utf-8"))[0]["fit_source_sha256"]).stat().st_size
        # The first FIT file is read whatever the budget; the next would pass it.
        one = read_many_laps(output, files, keys, store, budget=1)
        self.assertEqual(one.done, 1)
        two = read_many_laps(output, files, keys, store, budget=2 * size)
        self.assertEqual(two.done, 2)
        self.assertEqual(read_many_laps(output, files, keys, store, runs=1).done, 1)
        # Nothing after the FIT file past the budget is answered in that
        # request, not even an activity told without a file read.
        self.assertEqual(read_many_laps(output, files, [keys[0], keys[1], None], store, budget=1).runs, (read_laps(output, files, keys[0], store),))
        # Read on from where a request ended, as the page asks the next.
        parts, start = [], 0
        while start < len(keys):
            part = read_many_laps(output, files, keys[start:], store, budget=1)
            parts.extend(part.runs)
            start += part.done
        self.assertEqual(parts, list(read_many_laps(output, files, keys, store).runs))

    def test_a_fit_file_read_counts_also_where_it_is_found_changed(self) -> None:
        # A FIT file is counted by its size as it was opened, before a byte
        # of it is read, whether or not it is then found as the output says
        # (Codex's read of the diff of X11, 1): changed files of a request
        # end it at its budget as files found right do.
        store, output = build(self.root, [(INTERVALS, (1,)), (INTERVALS, (1,)), (INTERVALS, (1,))])
        files = entries(output)
        keys = keys_of(output)
        for link in json.loads((output / fit_reading.LINKS).read_text(encoding="utf-8")):
            writable(blob(store, link["fit_source_sha256"])).write_bytes(b"other bytes")
        one = read_many_laps(output, files, keys, store, budget=1)
        self.assertEqual(one.done, 1)
        self.assertEqual(one.runs, (Laps("unavailable", "fit_changed"),))
        self.assertEqual(read_many_laps(output, files, keys, store, budget=2 * len(b"other bytes")).done, 2)
        self.assertEqual(read_many_laps(output, files, keys, store).done, 3)

    def test_a_file_is_read_up_to_its_size_as_opened(self) -> None:
        # At most the size of a file as it was opened and one byte, so that a
        # file that grows while it is read is not read past what the budget
        # counted (Codex's second read of the diff of X11, 1).
        store, output = build(self.root, [(INTERVALS, (1,))])
        files = entries(output)
        keys = keys_of(output)
        digest = json.loads((output / fit_reading.LINKS).read_text(encoding="utf-8"))[0]["fit_source_sha256"]
        sizes = [entry[0] for entry in files.values()] + [(store / "store.json").stat().st_size, blob(store, digest).stat().st_size]
        asked = []
        real = os.fdopen

        class Counted:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                self.handle.__enter__()
                return self

            def __exit__(self, *exc):
                return self.handle.__exit__(*exc)

            def read(self, size=-1):
                asked.append(size)
                return self.handle.read(size)

        with mock.patch.object(fit_reading.os, "fdopen", lambda *args, **kwargs: Counted(real(*args, **kwargs))):
            many = read_many_laps(output, files, keys, store)
        self.assertEqual(many.runs[0].status, "laps")
        self.assertIn(blob(store, digest).stat().st_size + 1, asked)
        self.assertLessEqual(max(asked), max(sizes) + 1)

    def test_a_fit_file_is_not_read_past_its_budget(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (INTERVALS, (1,))])
        files = entries(output)
        keys = keys_of(output)
        reads = []
        real = fit_reading._read_opened

        def counted(descriptor, limit, looked, budget=None):
            try:
                data = real(descriptor, limit, looked, budget)
            except fit_reading._OverBudget:
                reads.append("over")
                raise
            reads.append(len(data))
            return data

        with mock.patch.object(fit_reading, "_read_opened", counted):
            many = read_many_laps(output, files, keys, store, budget=1)
        # store.json, the first FIT file, then the second refused unread.
        self.assertEqual(many.done, 1)
        self.assertEqual(reads[-1], "over")

    def test_a_fit_file_that_cannot_be_read_is_told_for_its_run(self) -> None:
        # A blob that the reader refuses (store_unreadable: a link in its
        # place, as the reading of one activity refuses it) is told for its
        # run, and the other runs are read; a store.json that cannot be read
        # is told for all (plan_v230_X11.md 9b 8; the checker's review of
        # the guard of X11, G3).
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (1,)), (RESTS, (2,))])
        files = entries(output)
        keys = keys_of(output)
        digest = {row["garmin_activity_key"]: row["fit_source_sha256"] for row in json.loads((output / fit_reading.LINKS).read_text(encoding="utf-8"))}[keys[1]]
        alone = [read_laps(output, files, key, store) for key in keys]
        real = fit_reading._fit_bytes

        def refused(root, asked, budget=None):
            if asked == digest:
                raise fit_reading._Unavailable("store_unreadable")
            return real(root, asked, budget)

        with mock.patch.object(fit_reading, "_fit_bytes", refused):
            many = read_many_laps(output, files, keys, store)
        self.assertEqual(many.status, "laps")
        self.assertEqual(list(many.runs), [alone[0], Laps("unavailable", "store_unreadable"), alone[2]])
        if not WINDOWS:
            path = blob(store, digest)
            moved = path.with_name(path.name + "-real")
            path.rename(moved)
            make_link(moved, path, folder=False)
            self.assertEqual(read_laps(output, files, keys[1], store), Laps("unavailable", "store_unreadable"))
            self.assertEqual(list(read_many_laps(output, files, keys, store).runs), [alone[0], Laps("unavailable", "store_unreadable"), alone[2]])
        writable(store / "store.json").write_bytes(b"{")
        self.assertEqual(read_many_laps(output, files, keys, store), ManyLaps("unavailable", "store_unreadable"))

    def test_a_fit_file_is_read_once_in_a_request(self) -> None:
        # Two activities of one FIT file (of two sessions) are rare; the same
        # activity asked twice reads its FIT file once all the same, by its
        # SHA-256 (Codex's review of the plan of X11, 2).
        store, output = build(self.root, [(INTERVALS, (1,))])
        files = entries(output)
        keys = keys_of(output) * 2
        calls = []
        real = fit_reading._fit_bytes

        def counted(root, digest, budget=None):
            calls.append(digest)
            return real(root, digest, budget)

        with mock.patch.object(fit_reading, "_fit_bytes", counted):
            many = read_many_laps(output, files, keys, store)
        statuses = [run.status for run in many.runs]
        self.assertEqual(statuses, ["laps", "laps"], [run.reason for run in many.runs])
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(many.runs), [read_laps(output, files, key, store) for key in keys])


class WorkSumsTest(unittest.TestCase):
    def test_an_activity_is_counted_by_its_laps(self) -> None:
        cases = [
            # (laps, counted, no_work, unknown_left, unknown_laps, no_pace, not counted)
            ((lap("interval"), lap("recovery")), 1, 0, 0, 0, 0, {}),
            ((lap("rest"), lap("warmup")), 1, 1, 0, 0, 0, {}),
            ((lap("rest"), lap("unknown")), 0, 0, 0, 0, 0, {"unknown_kinds": 1}),
            ((lap("unknown"),), 0, 0, 0, 0, 0, {"unknown_kinds": 1}),
            ((lap("active"), lap("unknown"), lap("unknown")), 1, 0, 1, 2, 0, {}),
            ((lap("active", distance=0.0), lap("interval", timer=None)), 1, 0, 0, 0, 1, {}),
            ((), 0, 0, 0, 0, 0, {"no_laps": 1}),
        ]
        for laps, counted, no_work, unknown_left, unknown_laps, no_pace, not_counted in cases:
            target = _empty()
            _add(target, Laps("laps", laps=laps, unknown_kind=sum(1 for one in laps if one.kind == "unknown")))
            self.assertEqual(
                (target["counted"], target["no_work"], target["unknown_left"], target["unknown_laps"], target["no_pace"], target["not_counted"]),
                (counted, no_work, unknown_left, unknown_laps, no_pace, not_counted),
                [one.kind for one in laps],
            )
        target = _empty()
        _add(target, Laps("unavailable", "fit_missing"))
        self.assertEqual(target["not_counted"], {"fit_missing": 1})

    def test_the_sums_are_those_of_the_work_laps(self) -> None:
        target = _empty()
        laps = (
            lap("warmup", 600.0, 1500.0, 130.0),
            lap("interval", 80.0, 400.0, 170.0),
            lap("recovery", 90.0, 200.0, 140.0),
            lap("active", 300.0, 1000.0, None),
            lap("interval", 60.0, 0.0, 160.0),
            lap("interval", None, 400.0, 165.0),
        )
        _add(target, Laps("laps", laps=laps))
        self.assertEqual(target["laps"], 4)
        # Whole milliseconds and centimetres (Codex's eighth read of the diff of X11).
        self.assertEqual((target["time_ms"], target["time_laps"]), (440_000, 3))
        self.assertEqual((target["distance_cm"], target["distance_laps"]), (180_000, 4))
        self.assertEqual((target["paced_time_ms"], target["paced_distance_cm"]), (380_000, 140_000))
        self.assertEqual((target["heart_bpm_ms"], target["heart_time_ms"]), (170 * 80_000 + 160 * 60_000, 140_000))
        self.assertTrue(all(type(target[name]) is int for name in SUMS))
        self.assertEqual(WORK_KINDS, frozenset({"active", "interval"}))
        self.assertEqual(set(_empty()), set(SUMS) | set(RUN_COUNTS) | {"not_counted"})
        self.assertIn("store_unreadable", NOT_COUNTED)


    def test_the_sums_do_not_depend_on_where_the_requests_end(self) -> None:
        # Whole numbers, so that the sums of the requests add up to those of
        # one request exactly (Codex's eighth read of the diff of X11): 100
        # activities of a lap of 300.6 s and 1,200 m, as one and as two halves.
        laps = Laps("laps", laps=(lap("interval", 300.6, 1200.0, 150.0),))
        whole, halves = _empty(), [_empty(), _empty()]
        for index in range(100):
            _add(whole, laps)
            _add(halves[index // 50], laps)
        names = (*SUMS, *RUN_COUNTS)
        self.assertEqual({name: halves[0][name] + halves[1][name] for name in names}, {name: whole[name] for name in names})
        self.assertEqual((whole["paced_time_ms"], whole["paced_distance_cm"]), (30_060_000, 12_000_000))


class WorkAnswerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self) -> None:
        for path in self.root.rglob("*"):
            if not path.is_symlink():
                writable(path)
        self.directory.cleanup()

    def test_the_sums_add_up_over_the_requests(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (2,)), (INTERVALS, (1, 2)), (RESTS, (1,)), (None, (2,))])
        data = load_view_data(output, gear=True)
        pairs, runs = work_runs(data, "all", None, None)
        whole = work_answer(data, data.files, output, store, pairs, runs, 0)
        self.assertEqual((whole["status"], whole["runs"], whole["next"]), ("work", 5, None))
        real = shoe_work.read_many_laps
        with mock.patch.object(shoe_work, "read_many_laps", lambda *args, **kwargs: real(*args, runs=2, **kwargs)):
            parts, start = [], 0
            while start is not None:
                part = work_answer(data, data.files, output, store, pairs, runs, start)
                self.assertEqual(part["from"], start)
                parts.append(part)
                start = part["next"]
        self.assertEqual(len(parts), 3)

        def total(answers, pick):
            sums = _empty()
            for answer in answers:
                one = pick(answer)
                for name in (*SUMS, *RUN_COUNTS):
                    sums[name] += one[name]
                for reason, count in one["not_counted"].items():
                    sums["not_counted"][reason] = sums["not_counted"].get(reason, 0) + count
            return sums

        for index in range(pairs):
            self.assertEqual(total(parts, lambda answer: answer["pairs"][index]), total([whole], lambda answer: answer["pairs"][index]))
        self.assertEqual(total(parts, lambda answer: answer["counts"]), total([whole], lambda answer: answer["counts"]))
        self.assertEqual(sum(part["counts"]["two_pairs"] for part in parts), 1)
        # The activity of two pairs counts for each pair, once for the period.
        self.assertEqual(whole["counts"]["counted"] + sum(whole["counts"]["not_counted"].values()), 5)
        self.assertEqual(sum(pair["counted"] + sum(pair["not_counted"].values()) for pair in whole["pairs"]), 6)

    def test_the_limits_of_a_request_are_those_that_the_documents_say(self) -> None:
        # The documents say at most 100 runs and 32 MiB of FIT files in one
        # request, and 5,000 runs in one counting; the counting asks with the
        # limits of the reader (the checker's review of the guard of X11,
        # G1).
        self.assertEqual((fit_reading.MAX_MANY_RUNS, fit_reading.MAX_MANY_BYTES, MAX_WORK_RUNS), (100, 32 * 1024 * 1024, 5000))
        parameters = inspect.signature(read_many_laps).parameters
        self.assertEqual((parameters["runs"].default, parameters["budget"].default), (100, 32 * 1024 * 1024))
        store, output = build(self.root, [(INTERVALS, (1,))])
        data = load_view_data(output, gear=True)
        pairs, runs = work_runs(data, "all", None, None)
        asked = []
        real = shoe_work.read_many_laps

        def kept(*args, **kwargs):
            asked.append(kwargs)
            return real(*args, **kwargs)

        with mock.patch.object(shoe_work, "read_many_laps", kept):
            self.assertEqual(work_answer(data, data.files, output, store, pairs, runs, 0)["status"], "work")
        self.assertEqual(asked, [{}])

    def test_what_the_page_says_before_it_reads(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (2,)), (EASY, ())])
        data = load_view_data(output, gear=True)
        self.assertEqual(work_known(data, data.files, "all", None, None), {"runs": 2, "known": 0, "limit": MAX_WORK_RUNS, "reason": None})
        without = {name: entry for name, entry in data.files.items() if name != LINEAGE}
        self.assertEqual(work_known(data, without, "all", None, None)["reason"], "not_from_store")

    def test_more_activities_than_the_limit_are_not_read(self) -> None:
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (2,))])
        data = load_view_data(output, gear=True)
        pairs, runs = work_runs(data, "all", None, None)
        with mock.patch.object(shoe_work, "MAX_WORK_RUNS", 1), mock.patch.object(shoe_work, "read_many_laps") as reader:
            answer = work_answer(data, data.files, output, store, pairs, runs, 0)
        self.assertEqual(answer, {"status": "unavailable", "reason": "too_many", "runs": 2})
        reader.assert_not_called()
        # As many as the limit are read.
        with mock.patch.object(shoe_work, "MAX_WORK_RUNS", 2):
            self.assertEqual(work_answer(data, data.files, output, store, pairs, runs, 0)["status"], "work")
        with self.assertRaises(shoe_work.WorkRequestError):
            work_answer(data, data.files, output, store, pairs, runs, 3)

    def test_a_key_that_two_activities_have_is_known_before_reading(self) -> None:
        # As read_laps takes it (key_shared), before a file is read; the
        # activity is not counted.
        store, output = build(self.root, [(INTERVALS, (1,)), (EASY, (2,)), (RESTS, (1,))])
        data = load_view_data(output, gear=True)
        rows = data.rows[ACTIVITIES]
        rows[2].marks["key"] = rows[0].marks["key"]
        pairs, runs = work_runs(data, "all", None, None)
        self.assertEqual([key is None for key, _places in runs], [True, False, True])
        self.assertEqual(work_known(data, data.files, "all", None, None), {"runs": 3, "known": 2, "limit": MAX_WORK_RUNS, "reason": None})
        answer = work_answer(data, data.files, output, store, pairs, runs, 0)
        self.assertEqual(answer["counts"]["not_counted"], {"key_shared": 2})
        self.assertEqual(answer["counts"]["counted"], 1)


class ShoeOrderTest(unittest.TestCase):
    def test_the_pairs_are_in_the_order_of_the_view_by_shoes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            from garmin_running_data_normalizer.run_all import run_all

            export = write_view_export(Path(directory) / "export", gear=True)
            output = Path(directory) / "out"
            run_all(export, output)
            data = load_view_data(output, gear=True)
            names = {shoe.key: shoe.name for shoe in data.gear.shoes}
            for period in ("all", "1y", "3y"):
                order = [names[key] for key, _own in shoe_order(data, period)]
                self.assertEqual(order, [entry["name"] for entry in shoe_answer(data, period)["shoes"]], period)
                counts = [len(own) for _key, own in shoe_order(data, period)]
                self.assertEqual(counts, [entry["activities"] for entry in shoe_answer(data, period)["shoes"]], period)


class ShoesWorkApiTest(GuiServerTestCase):
    """/api/view/shoes/work through the server of the view page, and what the
    answer of /api/view/shoes says before it reads."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.made = tempfile.TemporaryDirectory()
        cls.made_root = Path(cls.made.name).resolve()
        build(cls.made_root / "made", [(INTERVALS, (1,)), (EASY, (2,)), (INTERVALS, (1, 2))])

    @classmethod
    def tearDownClass(cls) -> None:
        for path in cls.made_root.rglob("*"):
            if not path.is_symlink():
                writable(path)
        cls.made.cleanup()
        super().tearDownClass()

    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.place = Path(directory.name).resolve()
        root = self.place / "copy"
        shutil.copytree(self.made_root / "made", root, symlinks=True)
        self.addCleanup(lambda: [writable(path) for path in root.rglob("*") if not path.is_symlink()])
        self.output, self.store = root / "out", root / "store"

    def call(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def opened(self, store: Path | None = "remembered") -> tuple[dict[str, Any], dict[str, Any]]:
        self.assertIsNone(gui_settings.remember_run(self.output, self.store if store == "remembered" else store))
        status, opened = self.call("/api/view/open", {"output": "chosen", "path": str(self.output)})
        self.assertEqual(status, 200, opened)
        status, shoes = self.call("/api/view/shoes", {"view": opened["view"], "period": "all", "types": None})
        self.assertEqual(status, 200, shoes)
        return opened, shoes

    def work(self, opened: dict[str, Any], read: Any, start: Any = 0) -> tuple[int, dict[str, Any]]:
        return self.call("/api/view/shoes/work", {"view": opened["view"], "read": read, "period": "all", "types": None, "from": start})

    def test_the_shoes_answer_tells_what_is_read(self) -> None:
        _opened, shoes = self.opened()
        self.assertEqual(shoes["work"], {"runs": 3, "known": 0, "limit": MAX_WORK_RUNS, "reason": None})

    def test_the_work_laps_of_the_pairs(self) -> None:
        opened, shoes = self.opened()
        status, answer = self.work(opened, shoes["read"])
        self.assertEqual(status, 200, answer)
        self.assertEqual((answer["status"], answer["runs"], answer["from"], answer["next"]), ("work", 3, 0, None))
        self.assertEqual(len(answer["pairs"]), len(shoes["shoes"]))
        self.assertEqual(answer["counts"]["counted"], 3)
        self.assertEqual(answer["counts"]["two_pairs"], 1)
        self.assertEqual(answer["read"], shoes["read"])
        self.assertIn("output", answer)
        # No place, SHA-256, or key of an activity.
        text = json.dumps(answer)
        links = json.loads((self.output / fit_reading.LINKS).read_text(encoding="utf-8"))
        for row in links:
            self.assertNotIn(row["fit_source_sha256"], text)
            self.assertNotIn(row["garmin_activity_key"], text)
        self.assertNotIn(str(self.store), text)
        self.assertNotIn(str(self.output), text)

    def test_another_reading_is_told_stale(self) -> None:
        opened, shoes = self.opened()
        status, answer = self.work(opened, shoes["read"] + 1)
        self.assertEqual((status, answer["status"], answer["reason"]), (200, "unavailable", "read_stale"))

    def test_another_reading_of_a_store_is_told_busy(self) -> None:
        opened, shoes = self.opened()
        lock = self.server.laps_lock
        self.assertTrue(lock.acquire(timeout=10))
        try:
            status, answer = self.work(opened, shoes["read"])
        finally:
            lock.release()
        self.assertEqual((status, answer["status"], answer["reason"]), (200, "unavailable", "busy"))

    def test_the_lock_is_free_after_each_request(self) -> None:
        # As after /api/view/laps (the checker's review of the guard of X11,
        # G2): after a request read, one refused, and one that failed, else
        # every later reading of the laps would be told busy.
        opened, shoes = self.opened()
        status, answer = self.work(opened, shoes["read"])
        self.assertEqual((status, answer["status"]), (200, "work"), answer)
        self.assertFalse(self.server.laps_lock.locked())
        status, answer = self.work(opened, shoes["read"], 4)
        self.assertEqual((status, answer.get("error")), (422, "REQUEST_INVALID"), answer)
        self.assertFalse(self.server.laps_lock.locked())
        with mock.patch("garmin_running_data_normalizer.gui.server.work_answer", side_effect=RuntimeError("synthetic")):
            status, answer = self.work(opened, shoes["read"])
        self.assertEqual((status, answer.get("error")), (500, "COMMAND_FAILED"), answer)
        self.assertFalse(self.server.laps_lock.locked())

    def test_types_that_the_output_has_not_are_refused(self) -> None:
        opened, shoes = self.opened()
        status, answer = self.call("/api/view/shoes/work", {"view": opened["view"], "read": shoes["read"], "period": "all", "types": ["not a type"], "from": 0})
        self.assertEqual((status, answer.get("error")), (422, "REQUEST_INVALID"), answer)

    def test_a_place_that_the_activities_have_not_is_refused(self) -> None:
        opened, shoes = self.opened()
        for start in (4, -1, "0", True, None):
            with self.subTest(start=start):
                status, answer = self.work(opened, shoes["read"], start)
                self.assertEqual((status, answer.get("error")), (422, "REQUEST_INVALID"), answer)

    def test_no_store_remembered(self) -> None:
        opened, shoes = self.opened(None)
        status, answer = self.work(opened, shoes["read"])
        self.assertEqual((status, answer["status"], answer["reason"]), (200, "unavailable", "no_store"))


if __name__ == "__main__":
    unittest.main()
