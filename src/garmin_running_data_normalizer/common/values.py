"""Compare values that differ only in how they are written."""

from __future__ import annotations

import json
from typing import Any


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


__all__ = ["comparable", "comparable_text", "is_empty"]
