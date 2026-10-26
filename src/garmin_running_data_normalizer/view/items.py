"""The items of the view page and the files that they come from (stage G1).

Each item reads one field of one file of the output, and combines its values
over a period in one way. The units are those of SCHEMA_CATALOG.json; an item
without a unit there shows the value as Garmin gives it, and is not
converted. The names of the items are words of the page, not of this module.
"""

from __future__ import annotations

from dataclasses import dataclass

# The ways of combining the values of a period.
SUM = "sum"  # the total of the recorded activities
COUNT = "count"  # the number of the recorded activities
PACE = "pace"  # the total time divided by the total distance
TIME_WEIGHTED = "tw"  # the mean weighted by the duration of each activity
MAXIMUM = "max"  # the highest value
DAILY = "day"  # the mean of the days with a value
OBSERVED = "obs"  # every record at the grain of a day, otherwise their mean

ACTIVITIES = "activities"
# The fields of analysis/activities.csv that every activity item reads besides
# its own: the duration weighs the means, and the pace reads both.
DISTANCE = "distance_m"
DURATION = "duration_sec"


@dataclass(frozen=True)
class Dataset:
    """A file that the view page reads: its place in the output, the field of
    its date, and, for the files that hold several records a day, the fields
    that keep their records apart in separate lines."""

    name: str
    path: str
    date_field: str
    observed: bool = False
    series: tuple[str, ...] = ()


DATASETS = (
    Dataset(ACTIVITIES, "analysis/activities.csv", "activity_date_local"),
    Dataset("race_prediction_daily", "normalized/race_prediction_daily.json", "calendar_date", observed=True),
    Dataset("sleep_daily", "normalized/sleep_daily.json", "sleep_day"),
    Dataset("uds_daily", "normalized/uds_daily.json", "calendar_date"),
    Dataset("acute_training_load_daily", "normalized/acute_training_load_daily.json", "calendar_date", observed=True),
    Dataset("training_readiness_daily", "normalized/training_readiness_daily.json", "calendar_date", observed=True),
    # The two series of VO2max, and the sports, are never mixed.
    Dataset(
        "vo2max_daily",
        "normalized/vo2max_daily.json",
        "calendar_date",
        observed=True,
        series=("vo2max_source_series", "sport"),
    ),
    Dataset("hrv_daily", "normalized/hrv_daily.json", "calendar_date"),
    Dataset("endurance_score_daily", "normalized/endurance_score_daily.json", "calendar_date"),
    Dataset("hill_score_daily", "normalized/hill_score_daily.json", "calendar_date"),
)
DATASETS_BY_NAME = {dataset.name: dataset for dataset in DATASETS}


@dataclass(frozen=True)
class Item:
    """One item of the view page.

    ``field`` is None for the count and the pace, which read the rows and
    their distance and duration. ``unit`` is the unit of SCHEMA_CATALOG.json,
    or the unit of what this package calculates, and None for a value as
    Garmin gives it. ``per_day`` marks the mean per day of the days with a
    value; ``sleep``, an item that uses only the sleeps that may be used; and
    ``unit_group``, the panels that may share one scale.
    """

    key: str
    group: str
    dataset: str
    field: str | None
    kind: str
    unit: str | None
    per_day: bool = False
    sleep: bool = False
    unit_group: str | None = None

    @property
    def from_fit(self) -> bool:
        """Whether the value comes from the FIT session linked to the activity."""
        return self.field is not None and self.field.startswith("fit_")


ITEMS = (
    # Training (per activity).
    Item("dist", "act", ACTIVITIES, DISTANCE, SUM, "metre"),
    Item("time", "act", ACTIVITIES, DURATION, SUM, "second"),
    Item("count", "act", ACTIVITIES, None, COUNT, "activity"),
    Item("pace", "act", ACTIVITIES, None, PACE, "second_per_metre"),
    Item("hr", "act", ACTIVITIES, "avg_hr", TIME_WEIGHTED, "beats_per_minute", unit_group="bpm"),
    Item("mx", "act", ACTIVITIES, "max_hr", MAXIMUM, "beats_per_minute", unit_group="bpm"),
    Item("cad", "act", ACTIVITIES, "avg_run_cadence", TIME_WEIGHTED, None),
    Item("pow", "act", ACTIVITIES, "avg_power", TIME_WEIGHTED, None),
    Item("load", "act", ACTIVITIES, "activity_training_load", SUM, None),
    Item("asc", "act", ACTIVITIES, "fit_total_ascent_m", SUM, "metre"),
    # Running form (FIT).
    Item("vo", "fit", ACTIVITIES, "fit_avg_vertical_oscillation_mm", TIME_WEIGHTED, "millimetre"),
    Item("gct", "fit", ACTIVITIES, "fit_avg_stance_time_ms", TIME_WEIGHTED, "millisecond"),
    Item("gctp", "fit", ACTIVITIES, "fit_avg_stance_time_percent", TIME_WEIGHTED, "percent"),
    Item("bal", "fit", ACTIVITIES, "fit_avg_stance_time_balance_percent", TIME_WEIGHTED, "percent"),
    Item("vr", "fit", ACTIVITIES, "fit_avg_vertical_ratio_percent", TIME_WEIGHTED, "percent"),
    Item("sl", "fit", ACTIVITIES, "fit_avg_step_length_mm", TIME_WEIGHTED, "millimetre"),
    # Body (daily).
    Item("rhr", "body", "uds_daily", "resting_heart_rate", DAILY, "beats_per_minute", unit_group="bpm"),
    Item("steps", "body", "uds_daily", "steps", DAILY, None, per_day=True),
    Item("stress", "body", "uds_daily", "stress_total_averageStressLevel", DAILY, None),
    Item("bbc", "body", "uds_daily", "bb_charged_value", DAILY, None),
    Item("bbd", "body", "uds_daily", "bb_drained_value", DAILY, None),
    Item("sleep", "body", "sleep_daily", "sleep_duration_minutes_ex_awake", DAILY, "minute", sleep=True),
    Item("deep", "body", "sleep_daily", "sleep_stage_deep_minutes", DAILY, "minute", sleep=True, unit_group="sleepst"),
    Item("light", "body", "sleep_daily", "sleep_stage_light_minutes", DAILY, "minute", sleep=True, unit_group="sleepst"),
    Item("rem", "body", "sleep_daily", "sleep_stage_rem_minutes", DAILY, "minute", sleep=True, unit_group="sleepst"),
    Item("sscore", "body", "sleep_daily", "sleep_score", DAILY, None, sleep=True),
    Item("hrv", "body", "hrv_daily", "hrv_value", DAILY, None),
    # Garmin estimates.
    Item("vo2", "est", "vo2max_daily", "vo2max", OBSERVED, None),
    Item("p5k", "est", "race_prediction_daily", "race_time_5k_sec", OBSERVED, "second"),
    Item("p10k", "est", "race_prediction_daily", "race_time_10k_sec", OBSERVED, "second"),
    Item("phalf", "est", "race_prediction_daily", "race_time_half_sec", OBSERVED, "second"),
    Item("pfull", "est", "race_prediction_daily", "race_time_marathon_sec", OBSERVED, "second"),
    Item("tr", "est", "training_readiness_daily", "training_readiness_score", OBSERVED, None),
    Item("acute", "est", "acute_training_load_daily", "daily_training_load_acute", OBSERVED, None, unit_group="load"),
    Item("chronic", "est", "acute_training_load_daily", "daily_training_load_chronic", OBSERVED, None, unit_group="load"),
    Item("acwr", "est", "acute_training_load_daily", "daily_acute_chronic_workload_ratio", OBSERVED, None),
    Item("endu", "est", "endurance_score_daily", "overall_score", DAILY, None),
    Item("hill", "est", "hill_score_daily", "overall_score", DAILY, None),
)
ITEMS_BY_KEY = {item.key: item for item in ITEMS}
# The items of the first time that the page opens (decided on 2026-10-26).
FIRST_ITEMS = ("dist", "rhr", "vo2")


def dataset_fields(dataset: str) -> tuple[str, ...]:
    """The fields of the values that the view page keeps of a file."""
    fields = [item.field for item in ITEMS if item.dataset == dataset and item.field is not None]
    if dataset == ACTIVITIES:
        fields += [DISTANCE, DURATION]
    return tuple(dict.fromkeys(fields))


__all__ = [
    "ACTIVITIES",
    "COUNT",
    "DAILY",
    "DATASETS",
    "DATASETS_BY_NAME",
    "DISTANCE",
    "DURATION",
    "Dataset",
    "FIRST_ITEMS",
    "ITEMS",
    "ITEMS_BY_KEY",
    "Item",
    "MAXIMUM",
    "OBSERVED",
    "PACE",
    "SUM",
    "TIME_WEIGHTED",
    "dataset_fields",
]
