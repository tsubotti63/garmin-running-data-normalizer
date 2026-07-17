from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable


def stable_hash(parts: Iterable[object], *, prefix: str = "") -> str:
    """Build a deterministic opaque identifier from normalized parts."""
    canonical = json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}{digest}"


def garmin_activity_key(activity_id: object | None, *fallback_parts: object) -> str:
    """Prefer Garmin's activity identifier, with a deterministic fallback."""
    if activity_id not in (None, ""):
        return f"garmin_activity:{activity_id}"
    if not fallback_parts or all(part in (None, "") for part in fallback_parts):
        raise ValueError("activity_id or at least one fallback part is required")
    return stable_hash(fallback_parts, prefix="garmin_activity_hash:")
