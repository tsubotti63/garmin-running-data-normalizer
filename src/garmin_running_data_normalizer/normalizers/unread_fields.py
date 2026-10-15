"""The source fields of the rows that a run reads but that no dataset field
takes, counted by name for the dataset's audit record (stage A4c-1).

Each row read counts once for each field outside the dataset's field list,
and so does each copy of it within one Snapshot that a Snapshot build passes
as one record, as the rows left out are counted. Only the names of the fields
at the top of a row are counted, never their values. The fields that this app
adds to the records it passes, whose names start with
``garminRunningDataNormalizer``, are not counted, and neither are the probe
records of a Snapshot build, which are not observations. A name that is not a
word, such as a date or a number, may be a value: such fields are counted
together without their names.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .daily_metrics import copies_within_snapshots, snapshot_numbers
from .records import SNAPSHOT_PROBE_FIELD

# The fields that this app adds to the records it reads: the marks of an item
# that is not a record and those of a Snapshot build. No Garmin record has them.
INTERNAL_FIELD_PREFIX = "garminRunningDataNormalizer"
# A name that the audit record writes: a word of up to 64 letters, digits,
# and underscores that starts with a letter.
_FIELD_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")


@dataclass
class UnreadFields:
    """The fields outside one dataset's field list, counted by name."""

    read: frozenset[str]
    counts: Counter[str] = field(default_factory=Counter)
    other_name_count: int = 0

    def add(self, raw: dict[str, Any], read: frozenset[str] | None = None) -> None:
        """Count the fields of one row read that the dataset does not read;
        ``read``, when given, is the field list of the row's series."""
        probe = raw.get(SNAPSHOT_PROBE_FIELD)
        if isinstance(probe, str) and probe:
            return
        read = self.read if read is None else read
        copies = 1 + copies_within_snapshots(snapshot_numbers(raw))
        for name in raw:
            if name in read or name.startswith(INTERNAL_FIELD_PREFIX):
                continue
            if _FIELD_NAME.fullmatch(name):
                self.counts[name] += copies
            else:
                self.other_name_count += copies

    def add_counts(self, counts: Mapping[str, int]) -> None:
        """Add the rows that hold each field, by name, as a Snapshot build
        counts them for the daily datasets (stage A4c-2)."""
        for name, count in counts.items():
            if name in self.read or name.startswith(INTERNAL_FIELD_PREFIX):
                continue
            if _FIELD_NAME.fullmatch(name):
                self.counts[name] += count
            else:
                self.other_name_count += count

    def audit_fields(self) -> dict[str, Any]:
        """The fields of the audit record: present only when there is
        something to count, so that an Export without such fields gives the
        same bytes as before."""
        fields: dict[str, Any] = {}
        if self.counts:
            fields["unread_field_counts"] = dict(sorted(self.counts.items()))
        if self.other_name_count:
            fields["unread_other_name_count"] = self.other_name_count
        return fields


def count_unread(unread: UnreadFields | None, raw: dict[str, Any]) -> None:
    if unread is not None:
        unread.add(raw)


__all__ = ["INTERNAL_FIELD_PREFIX", "UnreadFields", "count_unread"]
