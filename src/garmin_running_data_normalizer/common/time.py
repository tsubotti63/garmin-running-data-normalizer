from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "Asia/Tokyo"
TIMEZONE_DATA_ERROR_CODE = "TIMEZONE_DATA_UNAVAILABLE"


class TimezoneDataUnavailableError(RuntimeError):
    """Raised when the requested IANA timezone cannot be loaded."""

    code = TIMEZONE_DATA_ERROR_CODE

    def __init__(self, timezone_name: str) -> None:
        self.timezone_name = timezone_name
        self.safe_message = (
            f"IANA timezone data for {timezone_name} is unavailable. "
            "Reinstall the package in a clean environment."
        )
        super().__init__(self.safe_message)


def require_timezone_data(timezone_name: str = DEFAULT_TIMEZONE) -> ZoneInfo:
    """Resolve an IANA timezone or raise a bounded, privacy-safe error."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise TimezoneDataUnavailableError(timezone_name) from exc


def unix_ms_to_local_datetime(
    value: int | float | None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, timezone.utc).astimezone(
            require_timezone_data(timezone_name)
        ).isoformat()
    except (OverflowError, TypeError, ValueError):
        return None


def unix_ms_to_local_date(
    value: int | float | None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> str | None:
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
