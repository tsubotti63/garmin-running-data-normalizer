"""The records that changed between two outputs (stage X7 of v2.3.0).

The view page compares the output that it shows with the output before it,
and the normalization page the output of its run with the output before the
run, as the person chose (the samples of X7, 2026-11-09: D): the activities
by their declared key (garmin_activity_key), in the fields of the list of a
period (the date and time, the activity type, the name, and the values of its
columns but the pace, which the distance and the time make) and by their
shoes, and the shoes themselves by their key.

- An activity only in the output now is new; one only in the output before
  is in the output before only; one in both changed where one of its fields
  differs (a value against none too), and only its shoes changed where they
  alone differ: the shoes that it links to, and whether it has a link that
  tells no shoe, as the view by shoes tells them.
- An activity without a key, or with a key that another activity of the same
  output holds, cannot be matched: each output counts its own.
- The names are compared only where both outputs read them, and the shoes
  (their links and the pairs) only where both read them, so that a file left
  out of one reading never makes every record look changed (the checker's
  review of the plan of the making of X7, 1).
- The rows that a reading leaves out (without a date, after today) are not
  compared, as the view page does not show them.

Nothing is read or written here: the rows are those of two readings
(ViewData). The answers never give the declared keys; they give the values
as numbers, which the page writes as the list of a period does, and the
shoes by their places in the lists of the shoes of each output.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

from .data import Row, Shoe, ViewData
from .items import ACTIVITIES, ITEMS_BY_KEY

# The columns of the list of a period that are compared: those of
# view.series.LIST_ITEMS but the pace, which the distance and the time make.
CHANGE_ITEMS = ("dist", "time", "hr", "mx", "cad", "asc")
# The fields of an activity, in the order of the answer: its date and time,
# its activity type, its name, the values, and its shoes.
CHANGE_FIELDS = ("when", "type", "name", *CHANGE_ITEMS, "shoes")
# The fields of a pair of shoes that are compared, as Garmin sets them.
SHOE_FIELDS = ("name", "begin", "end", "maximum")
# The rows of each list of the answer of the view page, newest first, as the
# list of a period gives at most MAX_LIST_ROWS; the older ones are counted.
MAX_CHANGE_ROWS = 500
# The time of the day of a local date and time as the output writes it, before
# its offset, with the fraction of a second where there is one.
LOCAL_TIME = re.compile(r"T(\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)")


@dataclass(frozen=True)
class Activity:
    """An activity of a reading as the changes compare it: its row, its name
    (None where it has none or the names are not compared), the keys of the
    shoes that it links to, and whether it has a link that tells no shoe."""

    row: Row
    name: str | None
    shoes: frozenset[str]
    unknown: bool


@dataclass(frozen=True)
class Changes:
    """What changed between two readings, newest first: the activities new,
    in the output before only, changed (with the fields that changed), and
    with only their shoes changed; the activities of each output that cannot
    be matched; the pairs of shoes new, in the output before only, and
    changed (with the fields that changed); and which output did not read the
    names, or the shoes ("before", "now", "both"), or None where both did."""

    added: tuple[Activity, ...]
    removed: tuple[Activity, ...]
    changed: tuple[tuple[Activity, Activity, tuple[str, ...]], ...]
    shoes_changed: tuple[tuple[Activity, Activity], ...]
    unmatched_before: int
    unmatched_now: int
    pairs_added: tuple[Shoe, ...]
    pairs_removed: tuple[Shoe, ...]
    pairs_changed: tuple[tuple[Shoe, Shoe, tuple[str, ...]], ...]
    names_unread: str | None
    shoes_unread: str | None


def _unread(before: Any, now: Any) -> str | None:
    """Which reading did not read a part (names or shoes): left out where it
    was not asked for or was too large."""
    missing = [name for name, part in (("before", before), ("now", now)) if part is None or part.too_large]
    if not missing:
        return None
    return "both" if len(missing) == 2 else missing[0]


def _moment(row: Row) -> tuple[int, str, str]:
    """The order of an activity: its day, then its time of the day as the
    output writes it, before the offset (with the fraction of a second), as
    the list of a period orders them, then its key, so that activities of the
    same moment come in one order (Codex's review of the diff of X7, 4)."""
    moment = row.marks.get("datetime")
    found = LOCAL_TIME.search(moment) if isinstance(moment, str) else None
    return row.day, found.group(1) if found else "", row.marks.get("key") or ""


def _activities(data: ViewData, names: bool, shoes: bool) -> tuple[dict[str, Activity], int]:
    """The activities of a reading by their declared key, and the number of
    those that cannot be matched: without a key, or with a key that another
    activity of the reading holds."""
    rows = data.rows[ACTIVITIES]
    held = Counter(row.marks.get("key") or "" for row in rows)
    found: dict[str, Activity] = {}
    unmatched = 0
    for row in rows:
        key = row.marks.get("key") or ""
        if not key or held[key] > 1:
            unmatched += 1
            continue
        gear = data.gear
        found[key] = Activity(
            row=row,
            name=data.names.names.get(key) if names and data.names is not None else None,
            shoes=gear.links.get(key, frozenset()) if shoes and gear is not None else frozenset(),
            unknown=shoes and gear is not None and key in gear.unknown,
        )
    return found, unmatched


def _differing(before: Activity, now: Activity, names: bool, shoes: bool) -> tuple[str, ...]:
    """The fields of an activity that differ between two readings, in the
    order of CHANGE_FIELDS: a value against none differs too."""
    fields = []
    if (before.row.day, before.row.marks.get("datetime")) != (now.row.day, now.row.marks.get("datetime")):
        fields.append("when")
    if before.row.marks.get("type") != now.row.marks.get("type"):
        fields.append("type")
    if names and before.name != now.name:
        fields.append("name")
    for key in CHANGE_ITEMS:
        field = ITEMS_BY_KEY[key].field
        if before.row.values.get(field) != now.row.values.get(field):
            fields.append(key)
    if shoes and (before.shoes, before.unknown) != (now.shoes, now.unknown):
        fields.append("shoes")
    return tuple(fields)


def compare_outputs(before: ViewData, now: ViewData) -> Changes:
    """Compare two readings of outputs of this version: ``before``, of the
    output before, and ``now``. See the module."""
    names_unread = _unread(before.names, now.names)
    shoes_unread = _unread(before.gear, now.gear)
    names, shoes = names_unread is None, shoes_unread is None
    old, unmatched_before = _activities(before, names, shoes)
    new, unmatched_now = _activities(now, names, shoes)

    def newest_first(found: dict[str, Activity], keys: set[str]) -> tuple[Activity, ...]:
        return tuple(sorted((found[key] for key in keys), key=lambda activity: _moment(activity.row), reverse=True))

    changed: list[tuple[Activity, Activity, tuple[str, ...]]] = []
    shoes_changed: list[tuple[Activity, Activity]] = []
    for key in sorted(old.keys() & new.keys(), key=lambda key: _moment(new[key].row), reverse=True):
        fields = _differing(old[key], new[key], names, shoes)
        if fields == ("shoes",):
            shoes_changed.append((old[key], new[key]))
        elif fields:
            changed.append((old[key], new[key], fields))
    pairs_added: tuple[Shoe, ...] = ()
    pairs_removed: tuple[Shoe, ...] = ()
    pairs_changed: list[tuple[Shoe, Shoe, tuple[str, ...]]] = []
    if shoes and before.gear is not None and now.gear is not None:
        old_pairs = {shoe.key: shoe for shoe in before.gear.shoes}
        new_pairs = {shoe.key: shoe for shoe in now.gear.shoes}
        pairs_added = tuple(shoe for shoe in now.gear.shoes if shoe.key not in old_pairs)
        pairs_removed = tuple(shoe for shoe in before.gear.shoes if shoe.key not in new_pairs)
        for shoe in now.gear.shoes:
            earlier = old_pairs.get(shoe.key)
            if earlier is None:
                continue
            fields = tuple(field for field in SHOE_FIELDS if getattr(earlier, field) != getattr(shoe, field))
            if fields:
                pairs_changed.append((earlier, shoe, fields))
    return Changes(
        added=newest_first(new, new.keys() - old.keys()),
        removed=newest_first(old, old.keys() - new.keys()),
        changed=tuple(changed),
        shoes_changed=tuple(shoes_changed),
        unmatched_before=unmatched_before,
        unmatched_now=unmatched_now,
        pairs_added=pairs_added,
        pairs_removed=pairs_removed,
        pairs_changed=tuple(pairs_changed),
        names_unread=names_unread,
        shoes_unread=shoes_unread,
    )


def change_counts(changes: Changes) -> dict[str, Any]:
    """The numbers of the changes, which the normalization page says in one
    line under the result of its run, and the view page above its lists."""
    return {
        "added": len(changes.added),
        "removed": len(changes.removed),
        "changed": len(changes.changed),
        "shoes_changed": len(changes.shoes_changed),
        "unmatched": {"before": changes.unmatched_before, "now": changes.unmatched_now},
        "pairs": {"added": len(changes.pairs_added), "removed": len(changes.pairs_removed), "changed": len(changes.pairs_changed)},
        "names_unread": changes.names_unread,
        "shoes_unread": changes.shoes_unread,
    }


def _shoe_entry(shoe: Shoe) -> dict[str, Any]:
    """A pair of shoes as the view by shoes gives it: its name, what tells it
    from the shoes of the same name, and what Garmin sets of it."""
    return {
        "name": shoe.name,
        "day": shoe.day,
        "number": shoe.number,
        "begin": shoe.begin,
        "end": shoe.end,
        "maximum": shoe.maximum,
    }


def _when(row: Row) -> dict[str, Any]:
    return {"day": date.fromordinal(row.day).isoformat(), "datetime": row.marks.get("datetime")}


def _shoes_value(activity: Activity, places: dict[str, int]) -> dict[str, Any]:
    return {"shoes": sorted(places[key] for key in activity.shoes if key in places), "unknown": activity.unknown}


def _field_value(activity: Activity, field: str, places: dict[str, int]) -> Any:
    if field == "when":
        return _when(activity.row)
    if field == "type":
        return activity.row.marks.get("type")
    if field == "name":
        return activity.name
    if field == "shoes":
        return _shoes_value(activity, places)
    return activity.row.values.get(ITEMS_BY_KEY[field].field)


def _activity_entry(activity: Activity, places: dict[str, int]) -> dict[str, Any]:
    return {
        **_when(activity.row),
        "type": activity.row.marks.get("type"),
        "name": activity.name,
        "values": {key: activity.row.values.get(ITEMS_BY_KEY[key].field) for key in CHANGE_ITEMS},
        **_shoes_value(activity, places),
    }


def change_answer(changes: Changes, before: ViewData, now: ViewData) -> dict[str, Any]:
    """The lists of the changes for the view page, newest first, each up to
    MAX_CHANGE_ROWS rows (the rest are counted in ``more``): the values as
    numbers, and the shoes by their places in ``shoes_before`` and
    ``shoes_now``, the shoes of each output that the rows given name (Codex's
    review of the diff of X7, 2), as the view by shoes gives them. No declared
    key is given."""
    compared = changes.shoes_unread is None
    used_before: set[str] = set()
    used_now: set[str] = set()
    for activity in changes.added[:MAX_CHANGE_ROWS]:
        used_now |= activity.shoes
    for activity in changes.removed[:MAX_CHANGE_ROWS]:
        used_before |= activity.shoes
    for before_activity, now_activity, fields in changes.changed[:MAX_CHANGE_ROWS]:
        if "shoes" in fields:
            used_before |= before_activity.shoes
            used_now |= now_activity.shoes
    for before_activity, now_activity in changes.shoes_changed[:MAX_CHANGE_ROWS]:
        used_before |= before_activity.shoes
        used_now |= now_activity.shoes
    pairs: list[tuple[str, Shoe, Shoe, tuple[str, ...]]] = [
        *(("added", shoe, shoe, ()) for shoe in changes.pairs_added),
        *(("changed", earlier, shoe, fields) for earlier, shoe, fields in changes.pairs_changed),
        *(("removed", shoe, shoe, ()) for shoe in changes.pairs_removed),
    ][:MAX_CHANGE_ROWS]
    for kind, earlier, shoe, _fields in pairs:
        (used_before if kind == "removed" else used_now).add(shoe.key)
    shoes_before = tuple(shoe for shoe in before.gear.shoes if shoe.key in used_before) if compared and before.gear is not None else ()
    shoes_now = tuple(shoe for shoe in now.gear.shoes if shoe.key in used_now) if compared and now.gear is not None else ()
    places_before = {shoe.key: place for place, shoe in enumerate(shoes_before)}
    places_now = {shoe.key: place for place, shoe in enumerate(shoes_now)}
    answer = change_counts(changes)
    answer.update(
        {
            "list_added": [_activity_entry(activity, places_now) for activity in changes.added[:MAX_CHANGE_ROWS]],
            "list_removed": [_activity_entry(activity, places_before) for activity in changes.removed[:MAX_CHANGE_ROWS]],
            "list_changed": [
                {
                    **_when(now_activity.row),
                    "type": now_activity.row.marks.get("type"),
                    "name": now_activity.name,
                    "fields": [
                        {
                            "field": field,
                            "before": _field_value(before_activity, field, places_before),
                            "now": _field_value(now_activity, field, places_now),
                        }
                        for field in fields
                    ],
                }
                for before_activity, now_activity, fields in changes.changed[:MAX_CHANGE_ROWS]
            ],
            "list_shoes_changed": [
                {
                    **_when(now_activity.row),
                    "type": now_activity.row.marks.get("type"),
                    "name": now_activity.name,
                    "before": _shoes_value(before_activity, places_before),
                    "now": _shoes_value(now_activity, places_now),
                }
                for before_activity, now_activity in changes.shoes_changed[:MAX_CHANGE_ROWS]
            ],
            "list_pairs": [
                {"kind": kind, "before_pair": places_before[shoe.key], "fields": []}
                if kind == "removed"
                else {
                    "kind": kind,
                    "pair": places_now[shoe.key],
                    "fields": [{"field": field, "before": getattr(earlier, field), "now": getattr(shoe, field)} for field in fields],
                }
                for kind, earlier, shoe, fields in pairs
            ],
            "shoes_before": [_shoe_entry(shoe) for shoe in shoes_before],
            "shoes_now": [_shoe_entry(shoe) for shoe in shoes_now],
            "more": {
                "added": max(0, len(changes.added) - MAX_CHANGE_ROWS),
                "removed": max(0, len(changes.removed) - MAX_CHANGE_ROWS),
                "changed": max(0, len(changes.changed) - MAX_CHANGE_ROWS),
                "shoes_changed": max(0, len(changes.shoes_changed) - MAX_CHANGE_ROWS),
                "pairs": max(0, len(changes.pairs_added) + len(changes.pairs_changed) + len(changes.pairs_removed) - MAX_CHANGE_ROWS),
            },
        }
    )
    return answer
