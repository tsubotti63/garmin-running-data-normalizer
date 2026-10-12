from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable


def stable_hash(parts: Iterable[object], *, prefix: str = "") -> str:
    """Build a deterministic opaque identifier from normalized parts."""
    canonical = json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}{digest}"


def identity_token(value: object) -> str | None:
    """Return an identifier as one text, or None when the value is not one.

    Identifiers written in two ways are one identifier: the spaces around a
    text are left out, and a text of digits is read as a number, so " 123",
    "0123", and 123 are the same identifier, as the relationship checks read
    them. A boolean, an empty text, or a value of another type is not one.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return None
        return str(int(token)) if token.isdecimal() else token
    return None


def garmin_activity_key(activity_id: object | None, *fallback_parts: object) -> str:
    """Prefer Garmin's activity identifier, with a deterministic fallback."""
    if activity_id not in (None, ""):
        return f"garmin_activity:{activity_id}"
    if not fallback_parts or all(part in (None, "") for part in fallback_parts):
        raise ValueError("activity_id or at least one fallback part is required")
    return stable_hash(fallback_parts, prefix="garmin_activity_hash:")
