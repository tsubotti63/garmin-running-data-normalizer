from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from ..common.time import daily_calendar_date
from ..intake.discovery import DiscoveredAsset
from .daily_metrics import DailyMetricResult, finalize_daily, number, selected_rows


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


def normalize_uds(assets: Iterable[DiscoveredAsset]) -> DailyMetricResult:
    selected, rows = selected_rows(assets, lambda name: name.startswith("udsfile"))
    accepted = []
    excluded: Counter[str] = Counter()
    for raw in rows:
        date = daily_calendar_date(raw.get("calendarDate") or raw.get("date"))
        if date is None:
            excluded["missing_or_invalid_calendar_date"] += 1
            continue
        battery = raw.get("bodyBattery")
        stress = raw.get("allDayStress")
        total = _total_stress(stress)
        accepted.append(
            {
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
        key_field="calendar_date",
        selected_assets=selected,
        source_record_count=len(rows),
        accepted=accepted,
        excluded_reasons=excluded,
    )


__all__ = ["UDS_FIELDS", "normalize_uds"]
