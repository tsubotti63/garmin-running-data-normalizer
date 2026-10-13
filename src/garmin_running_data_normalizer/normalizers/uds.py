from __future__ import annotations

from typing import Any, Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import (
    DailyMetricResult,
    RowsLeftOut,
    finalize_daily,
    number,
    selected_rows,
    snapshot_numbers,
    value_source_names,
)


UDS_FIELDS = (
    "calendar_date",
    "steps",
    "distance_meters",
    "active_calories",
    "bmr_calories",
    "resting_heart_rate",
    "min_heart_rate",
    "max_heart_rate",
    "bb_charged_value",
    "bb_drained_value",
    "stress_total_averageStressLevel",
    "stress_total_maxStressLevel",
    "stress_total_stressDuration",
    "stress_total_restDuration",
    "raw_has_body_battery",
    "raw_has_all_day_stress",
    "raw_has_body_battery_feedback",
)
# The source fields of each value field (stage A3d-1); the other field is the
# record's key. A row left out that holds nothing in them is an empty record.
UDS_VALUE_SOURCES = {
    "steps": ("totalSteps", "steps"),
    "distance_meters": ("totalDistanceMeters", "distanceMeters"),
    "active_calories": ("activeKilocalories",),
    "bmr_calories": ("bmrKilocalories",),
    "resting_heart_rate": ("restingHeartRate",),
    "min_heart_rate": ("minHeartRate",),
    "max_heart_rate": ("maxHeartRate",),
    "bb_charged_value": ("bodyBattery",),
    "bb_drained_value": ("bodyBattery",),
    "stress_total_averageStressLevel": ("allDayStress",),
    "stress_total_maxStressLevel": ("allDayStress",),
    "stress_total_stressDuration": ("allDayStress",),
    "stress_total_restDuration": ("allDayStress",),
    "raw_has_body_battery": ("bodyBattery",),
    "raw_has_all_day_stress": ("allDayStress",),
    "raw_has_body_battery_feedback": ("bodyBatteryFeedback",),
}
UDS_FIELDS_WITHOUT_VALUES = ("calendar_date",)


def _calendar_date(raw: dict[str, Any]) -> str | None:
    return daily_calendar_date(raw.get("calendarDate") or raw.get("date"))


def uds_left_out_reason(raw: dict[str, Any]) -> str | None:
    """Return why a UDS record is left out, or None when it is kept."""
    if _calendar_date(raw) is None:
        return "missing_or_invalid_calendar_date"
    return None


def _total_stress(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    items = value.get("aggregatorList")
    if not isinstance(items, list):
        return {}
    return next(
        (
            item
            for item in items
            if isinstance(item, dict) and str(item.get("type", "")).upper() == "TOTAL"
        ),
        {},
    )


def normalize_uds(
    assets: Iterable[DiscoveredAsset],
) -> DailyMetricResult:
    selected, rows = selected_rows(assets, lambda name: name.startswith("udsfile"))
    accepted = []
    left_out = RowsLeftOut(value_source_names(UDS_VALUE_SOURCES))
    for raw in rows:
        reason = uds_left_out_reason(raw)
        if reason is not None:
            left_out.add(raw, reason)
            continue
        date = _calendar_date(raw)
        battery = raw.get("bodyBattery")
        stress = raw.get("allDayStress")
        total = _total_stress(stress)
        accepted.append(
            {
                "_snapshot_numbers": snapshot_numbers(raw),
                "calendar_date": date,
                "steps": number(raw.get("totalSteps") if "totalSteps" in raw else raw.get("steps")),
                "distance_meters": number(raw.get("totalDistanceMeters") if "totalDistanceMeters" in raw else raw.get("distanceMeters")),
                "active_calories": number(raw.get("activeKilocalories")),
                "bmr_calories": number(raw.get("bmrKilocalories")),
                "resting_heart_rate": number(raw.get("restingHeartRate")),
                "min_heart_rate": number(raw.get("minHeartRate")),
                "max_heart_rate": number(raw.get("maxHeartRate")),
                "bb_charged_value": number(battery.get("chargedValue")) if isinstance(battery, dict) else None,
                "bb_drained_value": number(battery.get("drainedValue")) if isinstance(battery, dict) else None,
                "stress_total_averageStressLevel": number(total.get("averageStressLevel")),
                "stress_total_maxStressLevel": number(total.get("maxStressLevel")),
                "stress_total_stressDuration": number(total.get("stressDuration")),
                "stress_total_restDuration": number(total.get("restDuration")),
                "raw_has_body_battery": isinstance(battery, dict),
                "raw_has_all_day_stress": isinstance(stress, dict),
                "raw_has_body_battery_feedback": isinstance(raw.get("bodyBatteryFeedback"), dict),
            }
        )
    return finalize_daily(
        dataset="uds_daily",
        key_fields=("calendar_date",),
        selected_assets=selected,
        source_record_count=len(rows) + left_out.copy_count,
        accepted=accepted,
        excluded_reasons=left_out.reasons,
        empty_record_count=left_out.empty_record_count,
        fields=UDS_FIELDS,
        # A day's record either has these source groups or not; a record
        # without one does not disagree with a record that has it.
        presence_flags=frozenset(
            {"raw_has_body_battery", "raw_has_all_day_stress", "raw_has_body_battery_feedback"}
        ),
    )


__all__ = [
    "UDS_FIELDS",
    "UDS_FIELDS_WITHOUT_VALUES",
    "UDS_VALUE_SOURCES",
    "normalize_uds",
    "uds_left_out_reason",
]
