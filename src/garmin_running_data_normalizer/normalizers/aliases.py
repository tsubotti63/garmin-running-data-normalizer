"""The value of a field that several source names give (stage A4d-1).

When two or more names hold values that differ, the field disagrees: the row
leaves it empty, and the values are kept for the audit record, as the values
that disagree are kept (stage A2a). When the names agree, or only one holds a
value, that value is the field's. An empty value (null, "", [], or {}) is no
value, and so is a value of another form, which the reading keeps apart
(stage A3d-2a). Values are compared as the app compares them, so 1000 and
1000.0 are one value.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from ..common.values import comparable_text, is_empty
from .daily_metrics import copies_within_snapshots

# The internal field of a row that holds, for each of its fields whose source
# names disagree, the values that the names give.
ROW_VALUE_ALTERNATIVES = "_value_alternatives"
# The names of the Gear type, in the order in which they are read.
GEAR_TYPE_NAMES = ("gearTypeName", "gearType")
# The names of the start of an Activity: the second fills the first (stage
# A4d-2).
ACTIVITY_START_NAMES = ("startTimeGmt", "beginTimestamp")
# The groups of source names of one field of the datasets whose records a
# Snapshot build merges across time points: a record that uses two or more
# names of a group has them as one field there (merge rules v2.16; the start
# of an Activity from v2.17).
ENTITY_FIELD_NAMES: dict[str, tuple[tuple[str, ...], ...]] = {
    "activities": (ACTIVITY_START_NAMES,),
    "gear": (GEAR_TYPE_NAMES,),
}


def alias_value(values: Iterable[Any]) -> tuple[Any, list[Any]]:
    """Return the value of a field and, when its names disagree, the values
    that they give, in the order of the names; the field is then empty."""
    distinct: dict[str, Any] = {}
    for value in values:
        if value is None or is_empty(value):
            continue
        distinct.setdefault(comparable_text(value), value)
    if len(distinct) > 1:
        return None, list(distinct.values())
    return next(iter(distinct.values()), None), []


def value_alternatives(row: dict[str, Any]) -> dict[str, list[Any]]:
    """The values of the fields of a row whose source names disagree."""
    return dict(row.get(ROW_VALUE_ALTERNATIVES) or {})


class AliasDisagreements:
    """The rows read whose source names disagree, counted for each field, each
    copy within one Snapshot as in a one-shot run."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def add(self, alternatives: dict[str, list[Any]], numbers: list[int] | None) -> None:
        weight = 1 + copies_within_snapshots(numbers)
        for field in alternatives:
            self.counts[field] += weight

    def audit_fields(self) -> dict[str, Any]:
        """The field of the audit record, only when a row disagrees, so that
        an Export without such rows gives the same bytes as before."""
        if not self.counts:
            return {}
        return {"aliases_disagree_counts": dict(sorted(self.counts.items()))}


__all__ = [
    "ACTIVITY_START_NAMES",
    "AliasDisagreements",
    "ENTITY_FIELD_NAMES",
    "GEAR_TYPE_NAMES",
    "ROW_VALUE_ALTERNATIVES",
    "alias_value",
    "value_alternatives",
]
