"""Merge the repeated records of Activities, Gear, activity_gear, and Personal Records.

Rows with the same stable key are one record (stage A3b). They are compared
field by field on their normalized values; the provenance fields, whose names
start with ``source_``, and the fields that name the record come from the
first row. Rows that give the same values are one row, and the copies are
counted. A field whose rows give different values is empty and listed in the
row's ``disagreeing_fields``, and every value is kept for the audit record.
An empty value (null, "", [], or {}) or a missing field means that the row
has no value. Values that differ only in how they are written are one value,
identifiers are compared as identifiers, so " 123" and 123 name the same
record, and a presence flag such as ``memo_present`` is set when any row has
it, so that it is never empty.

In a Snapshot run, a row may carry the import numbers of the Snapshots that
gave it, one for each copy; copies are then counted within each Snapshot, and
the audit record names the Snapshots that gave each value.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from ..common.identity import identity_token
from ..common.values import comparable_text, is_empty
from .daily_metrics import (
    _value_order,
    merge_observations,
    observation_weight,
    public_fields,
    snapshot_numbers,
)

RECORD_DATASETS = ("activities", "gear", "activity_gear", "personal_records")

# The stable key of each dataset, as the normalized dataset names it.
STABLE_KEYS: dict[str, tuple[str, ...]] = {
    "activities": ("garmin_activity_key",),
    "gear": ("gear_key",),
    "activity_gear": ("gear_key", "activity_id"),
    "personal_records": ("personal_record_id",),
}
# The fields that name the record; they are taken from the first row.
_NAMING_FIELDS: dict[str, frozenset[str]] = {
    "activities": frozenset({"garmin_activity_key", "activity_id"}),
    "gear": frozenset({"gear_key"}),
    "activity_gear": frozenset({"gear_key", "activity_id"}),
    "personal_records": frozenset({"personal_record_id"}),
}
# Fields that hold the identifier of another record.
_IDENTIFIER_FIELDS: dict[str, frozenset[str]] = {
    "personal_records": frozenset({"activity_id"}),
}
# Flags that say whether a row has a value, such as a memo: a merged row has
# the flag when any of its rows has it, as a UDS raw_has_* flag; the flag is
# never empty.
_PRESENCE_FLAGS: dict[str, frozenset[str]] = {
    "activities": frozenset({"memo_present"}),
}
# The internal field that carries the import numbers of a row in a Snapshot run.
ROW_SNAPSHOT_NUMBERS = "_snapshot_numbers"
# A Snapshot build writes, for a field that the record's last time point does
# not contain and whose earlier values disagree, a probe record without the
# field and one probe record for each value, marked with the field's name.
# They show which normalized fields come from it; they are not observations.
SNAPSHOT_PROBE_FIELD = "garminRunningDataNormalizerSnapshotProbe"
ROW_SNAPSHOT_PROBE = "_snapshot_probe"


@dataclass(frozen=True)
class RecordMerge:
    """The rows of one dataset after their repeated records are merged."""

    rows: list[dict[str, Any]]
    same_value_duplicate_count: int
    absent_value_counts: dict[str, int]
    disagreements: list[dict[str, Any]]


def row_snapshot_marks(raw: dict[str, Any]) -> dict[str, Any]:
    """Return the marks that a Snapshot build gave a source record.

    The marks are the import numbers of the observations behind the record
    and, for a probe record, the name of its field. An Export's own records
    never carry them.
    """
    marks: dict[str, Any] = {}
    numbers = snapshot_numbers(raw)
    if numbers:
        marks[ROW_SNAPSHOT_NUMBERS] = numbers
    probe = raw.get(SNAPSHOT_PROBE_FIELD)
    if isinstance(probe, str) and probe:
        marks[ROW_SNAPSHOT_PROBE] = probe
    return marks


def _identifier(value: Any) -> str:
    token = identity_token(value)
    if token is not None:
        return "identifier:" + token
    return "value:" + comparable_text(value)


def _record_identity(dataset: str, row: dict[str, Any]) -> tuple[str, ...]:
    """Return what tells the records of one dataset apart."""
    if dataset == "activities":
        # An Activity is named by its identifier; one without a usable
        # identifier by the key made from its other fields.
        token = identity_token(row.get("activity_id"))
        if token is not None:
            return ("identifier:" + token,)
        return ("key:" + str(row.get("garmin_activity_key")),)
    return tuple(_identifier(row.get(field)) for field in STABLE_KEYS[dataset])


def _is_provenance(field: str) -> bool:
    return field.startswith("source_")


def _numbers(row: dict[str, Any]) -> list[int]:
    numbers = row.get(ROW_SNAPSHOT_NUMBERS)
    return list(numbers) if isinstance(numbers, list) and numbers else [0]


def merge_repeated_records(dataset: str, rows: list[dict[str, Any]]) -> RecordMerge:
    """Merge the rows of one dataset that name the same record.

    ``rows`` are in their order of observation; the first row of a record
    gives its provenance and the written form of each value.
    """
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    probes: dict[tuple[str, ...], dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        identity = _record_identity(dataset, row)
        probe = row.get(ROW_SNAPSHOT_PROBE)
        if probe is not None:
            probes.setdefault(identity, {}).setdefault(probe, []).append(row)
        else:
            groups.setdefault(identity, []).append(row)
    naming = _NAMING_FIELDS[dataset]
    flags = _PRESENCE_FLAGS.get(dataset, frozenset())
    identifiers = _IDENTIFIER_FIELDS.get(dataset, frozenset())

    def form(field: str, value: Any) -> str:
        if field in identifiers:
            return _identifier(value)
        return comparable_text(value)

    output: list[dict[str, Any]] = []
    copies = 0
    absent: Counter[str] = Counter()
    disagreements: list[dict[str, Any]] = []
    for identity, group in groups.items():
        public = [public_fields(row) for row in group]
        numbers = [_numbers(row) for row in group]
        fields = [
            field
            for field in public[0]
            if field not in naming
            and not _is_provenance(field)
            and field != "disagreeing_fields"
        ]
        copies += _copy_count(public, numbers, fields, form)
        row = dict(public[0])
        entry: dict[str, Any] | None = None
        if len(group) == 1:
            row["disagreeing_fields"] = []
        else:
            entry = _merge_group(row, public, numbers, fields, flags, form, absent)
        for field_rows in probes.get(identity, {}).values():
            entry = _apply_probes(row, field_rows, fields, flags, form, entry)
        output.append(row)
        if entry is not None:
            entry["key"] = {field: row.get(field) for field in STABLE_KEYS[dataset]}
            disagreements.append(entry)
    disagreements.sort(
        key=lambda item: json.dumps(item["key"], ensure_ascii=False, sort_keys=True, default=str)
    )
    return RecordMerge(
        rows=output,
        same_value_duplicate_count=copies,
        absent_value_counts=dict(sorted(absent.items())),
        disagreements=disagreements,
    )


def _copy_count(
    public: list[dict[str, Any]],
    numbers: list[list[int]],
    fields: list[str],
    form: Callable[[str, Any], str],
) -> int:
    """Count the copies with the same values, within each Snapshot; a one-shot run is one."""

    def signature(row: dict[str, Any]) -> str:
        return json.dumps([form(field, row.get(field)) for field in fields])

    copies = 0
    for snapshot in sorted({number for items in numbers for number in items}):
        held = [
            (row, items.count(snapshot))
            for row, items in zip(public, numbers)
            if snapshot in items
        ]
        copies += sum(count for _row, count in held) - len(
            {signature(row) for row, _count in held}
        )
    return copies


def _merge_group(
    row: dict[str, Any],
    public: list[dict[str, Any]],
    numbers: list[list[int]],
    fields: list[str],
    flags: frozenset[str],
    form: Callable[[str, Any], str],
    absent: Counter[str],
) -> dict[str, Any] | None:
    """Merge the rows of one record into ``row``; return its disagreements, if any.

    An empty value (null, "", [], or {}) means that the row has no value, as
    a missing field does; when no row has a value, the first row's is kept.
    """
    snapshots = numbers if any(number for items in numbers for number in items) else None
    merged = merge_observations(
        public,
        fields,
        key_fields=(),
        presence_flags=flags,
        snapshots=snapshots,
        form=form,
        is_absent=is_empty,
    )
    row.update(merged.row)
    row["disagreeing_fields"] = list(merged.disagreeing_fields)
    absent.update(merged.absent_values)
    if not merged.disagreements:
        return None
    return {
        "key": {},
        "observation_count": sum(
            observation_weight(items if snapshots else None) for items in numbers
        ),
        "fields": list(merged.disagreements),
    }


def _apply_probes(
    row: dict[str, Any],
    field_rows: list[dict[str, Any]],
    fields: list[str],
    flags: frozenset[str],
    form: Callable[[str, Any], str],
    entry: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Apply the probe records of one source field to the merged ``row``.

    The first probe has no value for the field; each other probe has one of
    the field's disagreeing values. A normalized field that differs between
    them comes from the source field: when every value gives it the same
    value, the row takes that value; otherwise it is empty and disagrees. A
    presence flag is set when any value gives it.
    """
    base, *valued = [public_fields(item) for item in field_rows]
    weights = [_numbers(item) for item in field_rows[1:]]
    for field in fields:
        if field in flags:
            row[field] = row.get(field) is True or any(item.get(field) is True for item in valued)
            continue
        if all(form(field, item.get(field)) == form(field, base.get(field)) for item in valued):
            continue
        counts: dict[str, list[Any]] = {}
        for item, numbers in zip(valued, weights):
            value = item.get(field)
            held = counts.setdefault(form(field, value), [value, 0, set()])
            held[1] += len(numbers)
            held[2].update(numbers)
        if len(counts) == 1:
            row[field] = next(iter(counts.values()))[0]
            continue
        row[field] = None
        if field not in row["disagreeing_fields"]:
            row["disagreeing_fields"].append(field)
        if entry is None:
            entry = {
                "key": {},
                "observation_count": sum(len(numbers) for numbers in weights),
                "fields": [],
            }
        entry["fields"].append(
            {
                "field": field,
                "values": [
                    {"value": value, "observation_count": count, "snapshots": sorted(numbers)}
                    for _text, (value, count, numbers) in sorted(counts.items(), key=_value_order)
                ],
            }
        )
    return entry


__all__ = [
    "RECORD_DATASETS",
    "ROW_SNAPSHOT_NUMBERS",
    "RecordMerge",
    "STABLE_KEYS",
    "SNAPSHOT_PROBE_FIELD",
    "merge_repeated_records",
    "row_snapshot_marks",
]
