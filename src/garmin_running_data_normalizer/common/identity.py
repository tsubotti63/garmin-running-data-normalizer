from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable

# How a value names a record (stage A3d-1b): an identifier, no identifier, or
# a value that cannot be one.
IDENTIFIER = "identifier"
MISSING = "missing"
INVALID = "invalid"
# The longest text of digits that is read as an identifier. It is the
# product's own limit, so that every machine reads the same identifiers
# whatever its Python settings.
IDENTIFIER_MAX_DIGITS = 4300
# The largest integer that a float holds exactly.
_LARGEST_EXACT_FLOAT_INTEGER = (1 << 53) - 1


def stable_hash(parts: Iterable[object], *, prefix: str = "") -> str:
    """Build a deterministic opaque identifier from normalized parts."""
    canonical = json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}{digest}"


def read_identifier(value: object) -> tuple[str, str | None]:
    """Return how a value names a record, and the identifier as one text.

    The result is ``(IDENTIFIER, token)``, ``(MISSING, None)``, or
    ``(INVALID, None)`` (stage A3d-1b). An identifier is an integer, a float
    with an integral value of at most 2**53 - 1, or a text that is not blank.
    Identifiers written in two ways are one identifier: the spaces around a
    text are left out, and a text of the ASCII digits 0-9 is read as a number
    without its leading zeros, so " 0123", "123", 123, and 123.0 name the same
    record, and so do -5 and "-5". Other digits, such as "²" or full-width
    digits, are text. A value that is absent, null, "", or blank is missing; a
    boolean, a list, an object, any other float, a text of more than
    IDENTIFIER_MAX_DIGITS digits, or a value of another type is invalid. Zero
    is an identifier here; the datasets in which it names no record treat it
    apart.
    """
    if value is None:
        return MISSING, None
    if isinstance(value, bool):
        return INVALID, None
    if isinstance(value, int):
        return IDENTIFIER, str(value)
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer() and abs(value) <= _LARGEST_EXACT_FLOAT_INTEGER:
            return IDENTIFIER, str(int(value))
        return INVALID, None
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return MISSING, None
        if is_ascii_digits(token):
            if len(token) > IDENTIFIER_MAX_DIGITS:
                return INVALID, None
            return IDENTIFIER, token.lstrip("0") or "0"
        return IDENTIFIER, token
    return INVALID, None


def is_ascii_digits(text: str) -> bool:
    """Tell whether a text holds only the ASCII digits 0-9."""
    return bool(text) and text.isascii() and text.isdigit()


def identity_token(value: object) -> str | None:
    """Return an identifier as one text, or None when the value is not one."""
    state, token = read_identifier(value)
    return token if state == IDENTIFIER else None


def identifier_value(value: object) -> object:
    """Return an identifier as the output writes it: as the source wrote it,
    except that a float with an integral value is written as an integer."""
    if isinstance(value, float) and read_identifier(value)[0] == IDENTIFIER:
        return int(value)
    return value


def garmin_activity_key(activity_id: object | None, *fallback_parts: object) -> str:
    """Prefer Garmin's activity identifier, with a deterministic fallback."""
    if activity_id not in (None, ""):
        return f"garmin_activity:{activity_id}"
    if not fallback_parts or all(part in (None, "") for part in fallback_parts):
        raise ValueError("activity_id or at least one fallback part is required")
    return stable_hash(fallback_parts, prefix="garmin_activity_hash:")
