"""The work laps of the shoes of a period (stage X11 of v2.3.0): for each pair
of shoes of the view by shoes, the laps of its activities in the period whose
kind, as their FIT files record it, is one of WORK_KINDS (Active and Interval:
the person's choice of the samples of X11), counted from the laps that the view
page's server reads in the Snapshot Store that the GUI remembers
(gui.fit_reading.read_many_laps), a request of the page at a time.

The activities are those of the view by shoes with shoes in the period, of the
activity types counted that meet the conditions, in the order of the output;
the pairs are in the order of the view by shoes (view.series.shoe_order). A
request reads the activities from a place in that order (``start``), as many
as read_many_laps does in one request, and gives the sums of their work laps
by pair, which add up over the requests (Codex's review of the plan of X11,
5): the laps, the time and the laps that have one, the distance and the laps
that have one, the time and the distance of the laps that have both (of a
distance above 0) for the average pace, and the heart rate weighted by the time
and that time, all of them whole numbers (milliseconds, centimetres, and beats
a minute times milliseconds, the units of the FIT file), so that the sums of
the requests add up to those of one request exactly, wherever the requests
end (Codex's eighth read of the diff of X11); and the counts of the activities: counted, counted with no work
lap (all of known kinds), counted with the laps of no known kind left out, and
those laps, counted with no work lap of a pace, and not counted, by reason. An
activity of two pairs counts for each pair; the counts of the period count it
once. Nothing is kept; the answer holds no place, SHA-256, or key of an
activity.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Collection, Mapping

from ..view.data import ViewData
from ..view.items import ACTIVITIES
from ..view.series import Conditions, shoe_order
from .fit_reading import LINEAGE, UNKNOWN_KIND, Laps, read_many_laps

WORK_KINDS = frozenset({"active", "interval"})
# The activities of one counting (Codex's review of the plan of X11, 3; the
# person's whole period is below it, as the counts of X9a told).
MAX_WORK_RUNS = 5000
SUMS = ("laps", "time_ms", "time_laps", "distance_cm", "distance_laps", "paced_time_ms", "paced_distance_cm", "heart_bpm_ms", "heart_time_ms")
RUN_COUNTS = ("counted", "no_work", "unknown_left", "unknown_laps", "no_pace")
# Why an activity is not counted: the reasons of read_laps for one activity,
# and of its laps, none (no_laps) or none of a work kind with some of no known
# kind (unknown_kinds).
NOT_COUNTED = (
    "unknown_kinds",
    "no_laps",
    "key_shared",
    "no_link",
    "fit_missing",
    "fit_too_large",
    "fit_changed",
    "fit_not_activity",
    "laps_differ",
    "store_unreadable",
)


class WorkRequestError(ValueError):
    """A place to start from that the activities have not."""


def work_runs(
    data: ViewData,
    period: str | tuple[date, date],
    types: Collection[str] | None,
    conditions: Conditions | None,
) -> tuple[int, list[tuple[str | None, tuple[int, ...]]]]:
    """The number of the pairs of the view by shoes, and its activities with
    shoes: the key of each (None where it has none or another activity of the
    output has it too, as read_laps takes it: key_shared) and the places of its
    pairs in the order of the view."""
    order = shoe_order(data, period, types, conditions)
    places = {key: index for index, (key, _own) in enumerate(order)}
    shared = Counter(row.marks.get("key") or "" for row in data.rows[ACTIVITIES])
    seen: dict[int, list[int]] = {}
    for index, (_key, own) in enumerate(order):
        for row in own:
            seen.setdefault(id(row), []).append(index)
    runs = []
    for row in data.rows[ACTIVITIES]:
        if id(row) not in seen:
            continue
        key = row.marks.get("key") or ""
        runs.append((key if key and shared[key] == 1 else None, tuple(sorted(seen[id(row)]))))
    return len(places), runs


def work_known(
    data: ViewData,
    files: Mapping[str, tuple[int, str]],
    period: str | tuple[date, date],
    types: Collection[str] | None,
    conditions: Conditions | None,
) -> dict[str, Any]:
    """What the page says before it reads (stage X11 of v2.3.0): the
    activities with shoes of the view (``runs``), those known not to be read
    before a file is read (``known``: key_shared), the most of one counting
    (``limit``), and the reason of the output where it tells it (``reason``:
    not_from_store), else None."""
    _pairs, runs = work_runs(data, period, types, conditions)
    return {
        "runs": len(runs),
        "known": sum(1 for key, _places in runs if key is None),
        "limit": MAX_WORK_RUNS,
        "reason": None if LINEAGE in files else "not_from_store",
    }


def _ms(seconds: float) -> int:
    """Seconds of a lap as the whole milliseconds that its FIT file records."""
    return round(seconds * 1000)


def _cm(metres: float) -> int:
    """Metres of a lap as the whole centimetres that its FIT file records."""
    return round(metres * 100)


def _empty() -> dict[str, Any]:
    return {**{name: 0 for name in SUMS}, **{name: 0 for name in RUN_COUNTS}, "not_counted": {}}


def _add(target: dict[str, Any], laps: Laps) -> None:
    """Add an activity, as read_many_laps read it, to the sums of a pair or of
    the period."""
    if laps.status != "laps":
        reason = laps.reason or "store_unreadable"
        target["not_counted"][reason] = target["not_counted"].get(reason, 0) + 1
        return
    if not laps.laps:
        target["not_counted"]["no_laps"] = target["not_counted"].get("no_laps", 0) + 1
        return
    work = [lap for lap in laps.laps if lap.kind in WORK_KINDS]
    unknown = sum(1 for lap in laps.laps if lap.kind == UNKNOWN_KIND)
    if not work:
        if unknown:
            # A work lap may be among the laps of no known kind.
            target["not_counted"]["unknown_kinds"] = target["not_counted"].get("unknown_kinds", 0) + 1
        else:
            target["counted"] += 1
            target["no_work"] += 1
        return
    target["counted"] += 1
    if unknown:
        target["unknown_left"] += 1
        target["unknown_laps"] += unknown
    timed = [_ms(lap.timer_s) for lap in work if lap.timer_s is not None]
    measured = [_cm(lap.distance_m) for lap in work if lap.distance_m is not None]
    paced = [lap for lap in work if lap.timer_s is not None and lap.distance_m is not None and _cm(lap.distance_m) > 0]
    hearts = [lap for lap in work if lap.timer_s is not None and _ms(lap.timer_s) > 0 and lap.avg_heart_rate is not None]
    target["laps"] += len(work)
    target["time_ms"] += sum(timed)
    target["time_laps"] += len(timed)
    target["distance_cm"] += sum(measured)
    target["distance_laps"] += len(measured)
    target["paced_time_ms"] += sum(_ms(lap.timer_s) for lap in paced)
    target["paced_distance_cm"] += sum(_cm(lap.distance_m) for lap in paced)
    target["heart_bpm_ms"] += sum(round(lap.avg_heart_rate) * _ms(lap.timer_s) for lap in hearts)
    target["heart_time_ms"] += sum(_ms(lap.timer_s) for lap in hearts)
    if not paced:
        target["no_pace"] += 1


def work_answer(
    data: ViewData,
    files: Mapping[str, tuple[int, str]],
    output: Path,
    store_folder: Path | None,
    pairs: int,
    runs: list[tuple[str | None, tuple[int, ...]]],
    start: int,
) -> dict[str, Any]:
    """The work laps of the activities of ``runs`` from ``start``, as many as
    one request reads: the sums of each pair (in the order of the view), the
    counts of the period, the activities in all (``runs``), and where the
    next request starts (``next``; None after the last). A reason of the
    output or of the store, or more activities than MAX_WORK_RUNS, is told
    for all (status "unavailable")."""
    if len(runs) > MAX_WORK_RUNS:
        return {"status": "unavailable", "reason": "too_many", "runs": len(runs)}
    if start > len(runs):
        raise WorkRequestError("start")
    rest = runs[start:]
    many = read_many_laps(output, files, [key for key, _places in rest], store_folder)
    if many.status != "laps":
        return {"status": "unavailable", "reason": many.reason, "runs": len(runs)}
    by_pair = [_empty() for _ in range(pairs)]
    period = {**_empty(), "two_pairs": 0}
    for (_key, places), laps in zip(rest, many.runs):
        for place in places:
            _add(by_pair[place], laps)
        _add(period, laps)
        if len(places) > 1:
            period["two_pairs"] += 1
    done = start + many.done
    return {
        "status": "work",
        "runs": len(runs),
        "from": start,
        "next": done if done < len(runs) else None,
        "pairs": by_pair,
        "counts": period,
    }


__all__ = [
    "MAX_WORK_RUNS",
    "NOT_COUNTED",
    "RUN_COUNTS",
    "SUMS",
    "WORK_KINDS",
    "WorkRequestError",
    "work_answer",
    "work_known",
    "work_runs",
]
