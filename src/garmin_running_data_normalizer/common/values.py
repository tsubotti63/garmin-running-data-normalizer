"""Compare values that differ only in how they are written, and read values
as the fields of the normalized datasets take them."""

from __future__ import annotations

import json
import math
from typing import Any

# How a value fits the field that it goes to (stage A3d-2a): a value of the
# field's form, no value, or a value of another form.
VALID = "valid"
ABSENT = "absent"
INVALID = "invalid"
# The largest number that a value can be. Beyond it, a float does not hold
# every integer exactly, and readers of the output may change the number.
LARGEST_NUMBER = (1 << 53) - 1
# The internal field of a normalized row that carries the values of another
# form that a normalizer found while it made other values from them.
VALUE_PROBLEMS = "_value_problems"


def is_empty(value: Any) -> bool:
    """Return whether a value is an empty value: null, "", [], or {}."""
    return value is None or value == "" or value == [] or value == {}


def comparable(value: Any) -> Any:
    """Return the form in which a value is compared with another.

    Values that differ only in how they are written are one value: every
    empty value (null, "", [], or {}) is the same empty value, and numbers are
    compared by their value, so 1000 and 1000.0 are the same, also inside
    lists and objects. A boolean is not a number.
    """
    if is_empty(value):
        return ["empty"]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return ["number", value]
    if isinstance(value, str):
        return ["text", value]
    if isinstance(value, list):
        return ["list", [comparable(item) for item in value]]
    if isinstance(value, dict):
        return ["object", {str(key): comparable(item) for key, item in value.items()}]
    return ["other", value]


def comparable_text(value: Any) -> str:
    """Return the comparable form of a value as deterministic JSON text."""
    return json.dumps(
        comparable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _number_fits(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return abs(value) <= LARGEST_NUMBER


def read_value(value: Any, logical_type: str) -> tuple[str, Any]:
    """Return how a value fits a field of a logical type, and the value as
    the field takes it.

    The result is ``(VALID, value)``, ``(ABSENT, None)``, or ``(INVALID,
    None)`` (stage A3d-2a). An empty value (null, "", [], or {}) is no value,
    except that "" is a value of a text field. A number is finite and at most
    2**53 - 1 in size, and a whole number written with a decimal point is an
    integer, so 3.0 is 3. Text is never a number, so "5" is a value of
    another form for a number field, and a boolean is never a number.
    """
    if value is None:
        return ABSENT, None
    if isinstance(value, str) and logical_type in ("string", "integer|string", "number|string"):
        return VALID, value
    if is_empty(value):
        return ABSENT, None
    if logical_type == "boolean":
        return (VALID, value) if isinstance(value, bool) else (INVALID, None)
    if logical_type in ("number", "number|string"):
        return (VALID, value) if _number_fits(value) else (INVALID, None)
    if logical_type in ("integer", "integer|string"):
        if not _number_fits(value):
            return INVALID, None
        if isinstance(value, int):
            return VALID, value
        return (VALID, int(value)) if value.is_integer() else (INVALID, None)
    if logical_type == "array[string]":
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return VALID, value
        return INVALID, None
    return INVALID, None


def json_safe(value: Any) -> Any:
    """Return a value that strict JSON can write: a number that is not
    finite, which ``json.loads`` reads from NaN or Infinity, becomes an object
    that names it, also inside lists and objects."""
    if isinstance(value, float) and not math.isfinite(value):
        name = "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        return {"non_finite_number": name}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value


class ValueReader:
    """Read the values of one source row as their fields take them.

    A value of another form is left empty, and its field and the value are
    kept in ``problems`` (stage A3d-2a); an empty value is no value. A text
    field takes "" as no value, as the daily datasets always did.
    """

    def __init__(self) -> None:
        self.problems: list[tuple[str, Any]] = []

    def read(self, value: Any, logical_type: str, field: str) -> Any:
        state, result = read_value(value, logical_type)
        if state == INVALID:
            self.problems.append((field, value))
        return result

    def number(self, value: Any, field: str, *, positive: bool = False) -> int | float | None:
        """A number; with ``positive``, a number of 0 or less is of another form."""
        result = self.read(value, "number", field)
        if positive and result is not None and result <= 0:
            self.problems.append((field, value))
            return None
        return result

    def integer(self, value: Any, field: str) -> int | None:
        return self.read(value, "integer", field)

    def text(self, value: Any, field: str) -> str | None:
        return None if value == "" else self.read(value, "string", field)

    def boolean(self, value: Any, field: str) -> bool | None:
        return self.read(value, "boolean", field)


class InvalidValues:
    """The values of another form of one dataset, for its audit record.

    Each value is kept with the key of its row and its field, and counted
    once for each observation: in a Snapshot run, once for each Snapshot
    that gave it, with the Snapshot numbers (stage A3d-2a).
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add(
        self,
        key: dict[str, Any],
        field: str,
        value: Any,
        snapshots: list[int] | None = None,
    ) -> None:
        safe = json_safe(value)
        identity = (_stable(key), field, _stable(safe))
        entry = self._entries.setdefault(
            identity,
            {"key": key, "field": field, "value": safe, "observation_count": 0},
        )
        entry["observation_count"] += len(snapshots) if snapshots else 1
        if snapshots:
            entry["snapshots"] = sorted(set(entry.get("snapshots", [])) | set(snapshots))

    def counts(self) -> dict[str, int]:
        found: dict[str, int] = {}
        for entry in self._entries.values():
            found[entry["field"]] = found.get(entry["field"], 0) + entry["observation_count"]
        return dict(sorted(found.items()))

    def audit_fields(self) -> dict[str, Any]:
        """``invalid_value_counts`` by field and ``invalid_values``, when there is any."""
        if not self._entries:
            return {}
        return {
            "invalid_value_counts": self.counts(),
            "invalid_values": [
                self._entries[identity] for identity in sorted(self._entries)
            ],
        }


def _stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)


__all__ = [
    "ABSENT",
    "INVALID",
    "InvalidValues",
    "LARGEST_NUMBER",
    "VALID",
    "VALUE_PROBLEMS",
    "ValueReader",
    "comparable",
    "comparable_text",
    "is_empty",
    "json_safe",
    "read_value",
]
