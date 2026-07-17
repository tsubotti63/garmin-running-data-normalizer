from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo


def unix_ms_to_local_datetime(value: int | float | None, timezone_name: str = "Asia/Tokyo") -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, timezone.utc).astimezone(
            ZoneInfo(timezone_name)
        ).isoformat()
    except (OverflowError, TypeError, ValueError):
        return None


def unix_ms_to_local_date(value: int | float | None, timezone_name: str = "Asia/Tokyo") -> str | None:
    converted = unix_ms_to_local_datetime(value, timezone_name)
    return converted[:10] if converted else None


def daily_calendar_date(value: Any) -> str | None:
    """Normalize Garmin daily labels without shifting epoch-millisecond dates."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value) / 1000.0, timezone.utc).date().isoformat()
        except (OverflowError, TypeError, ValueError):
            return None
    text = str(value)
    if len(text) >= 10:
        try:
            return datetime.fromisoformat(text[:10]).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None
