from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones


DEFAULT_TIMEZONE = "Asia/Tokyo"
TIMEZONE_DATA_ERROR_CODE = "TIMEZONE_DATA_UNAVAILABLE"
TIMEZONE_INVALID_ERROR_CODE = "TIMEZONE_INVALID"
# "Factory" is the IANA placeholder for an unset local time, not a location.
_UNSUPPORTED_TIMEZONE_NAMES = frozenset({"Factory"})
_TIMEZONE_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_+\-]*(?:/[A-Za-z0-9_+\-]+)*")


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


class TimezoneNameInvalidError(ValueError):
    """Raised when a requested local timezone is not an exact IANA name."""

    code = TIMEZONE_INVALID_ERROR_CODE
    safe_message = (
        "--timezone must be an exact IANA timezone name, "
        "such as Asia/Tokyo or America/New_York."
    )

    def __init__(self) -> None:
        super().__init__(self.safe_message)


def require_timezone_data(timezone_name: str = DEFAULT_TIMEZONE) -> ZoneInfo:
    """Resolve an IANA timezone or raise a bounded, privacy-safe error."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise TimezoneDataUnavailableError(timezone_name) from exc
    except (ValueError, IsADirectoryError) as exc:
        raise TimezoneNameInvalidError() from exc


@lru_cache(maxsize=1)
def available_timezone_names() -> frozenset[str]:
    """Return the IANA timezone names that this environment can resolve."""
    return frozenset(available_timezones())


def resolve_timezone_name(timezone_name: Any) -> str:
    """Return an exact, resolvable IANA timezone name for local dates and times.

    The name must match an available IANA key exactly, so a case-insensitive
    file system cannot accept ``asia/tokyo`` on one platform and reject it on
    another. The returned name is the one recorded in Run-All output.
    """
    if (
        not isinstance(timezone_name, str)
        or not _TIMEZONE_NAME_PATTERN.fullmatch(timezone_name)
        or timezone_name in _UNSUPPORTED_TIMEZONE_NAMES
    ):
        raise TimezoneNameInvalidError()
    names = available_timezone_names()
    if timezone_name not in names:
        if not names:
            raise TimezoneDataUnavailableError(timezone_name)
        raise TimezoneNameInvalidError()
    require_timezone_data(timezone_name)
    return timezone_name


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
    if isinstance(value, bool):
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


def normalize_observation_timestamp(
    value: Any,
    *,
    naive_timezone_semantics: str = "UNCONFIRMED",
) -> tuple[str | None, str]:
    """Normalize a source timestamp without inventing unknown timezone semantics.

    Epoch-millisecond values are UTC instants. Offset-aware strings are
    canonicalized to UTC. Naive ISO strings are retained as naive values unless
    the source field itself explicitly establishes UTC/GMT semantics.
    """
    if value in (None, "") or isinstance(value, bool):
        return None, "MISSING"
    if isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(float(value) / 1000.0, timezone.utc)
        except (OverflowError, TypeError, ValueError):
            return None, "INVALID"
        return parsed.isoformat().replace("+00:00", "Z"), "EPOCH_MILLISECONDS_UTC"
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None, "INVALID"
    if parsed.tzinfo is not None:
        return (
            parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "EXPLICIT_OFFSET_UTC_NORMALIZED",
        )
    if naive_timezone_semantics == "UTC_SOURCE_FIELD":
        return (
            parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "SOURCE_FIELD_NAMED_UTC_OR_GMT",
        )
    return parsed.isoformat(), "NAIVE_ISO8601_TIMEZONE_UNCONFIRMED"
