"""A synthetic Export of about two and a half years for the view page (stage G1)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from garmin_running_data_normalizer.fit.parser import FIT_EPOCH_OFFSET
from tests.fit_fixture_factory import synthetic_fit
from tests.test_remaining_wellness_metrics import hrv_fit

FIRST = date(2023, 1, 1)
LAST = date(2025, 6, 30)
# The activities that FIT sessions link to: their start, 10 km, 3,500 seconds.
FIT_STARTS = ("2023-03-04T00:00:00Z", "2024-05-06T00:00:00Z", "2025-02-03T00:00:00Z")


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def epoch_ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def days() -> list[date]:
    return [FIRST + timedelta(days=offset) for offset in range((LAST - FIRST).days + 1)]


def activities() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for offset, day in enumerate(days()):
        start = datetime(day.year, day.month, day.day, 21, 0, tzinfo=timezone.utc)
        kinds = []
        if offset % 3 == 0:
            kinds.append(("running", "RUNNING"))
        if offset % 10 == 1:
            kinds.append(("treadmill_running", "RUNNING"))
        if offset % 15 == 2:
            kinds.append(("trail_running", "RUNNING"))
        if offset % 7 == 4:
            kinds.append(("road_biking", "CYCLING"))
        for number, (kind, sport) in enumerate(kinds):
            row: dict[str, object] = {
                "activityId": 100_000 + offset * 10 + number,
                "activityType": kind,
                "sportType": sport,
                "startTimeGmt": epoch_ms(start + timedelta(hours=number)),
                "distance": 500_000 + (offset % 9) * 100_000,
                "duration": 1_500_000 + (offset % 7) * 300_000,
                "maxHr": 170 + offset % 11,
                "activityTrainingLoad": 40 + offset % 50,
                "name": f"Synthetic {offset}",
            }
            # Some activities have no heart rate, power, or cadence.
            if offset % 4:
                row["avgHr"] = 140 + offset % 17
            if offset % 5:
                row["avgPower"] = 230 + offset % 23
                row["avgRunCadence"] = 80 + offset % 9
            rows.append(row)
    for number, text in enumerate(FIT_STARTS):
        rows.append(
            {
                "activityId": 900_000 + number,
                "activityType": "running",
                "sportType": "RUNNING",
                "startTimeGmt": epoch_ms(utc(text)),
                "distance": 1_000_000,
                "duration": 3_500_000,
                "avgHr": 150,
                "name": f"Synthetic FIT {number}",
            }
        )
    return rows


def write_view_export(root: Path) -> Path:
    fitness = root / "DI-Connect-Fitness"
    metrics = root / "DI-Connect-Metrics"
    sleep_folder = root / "DI-Connect-Wellness"
    uploaded = root / "DI-Connect-Uploaded-Files"
    for folder in (fitness, metrics, sleep_folder, uploaded):
        folder.mkdir(parents=True)
    (fitness / "synthetic_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": activities()}]), encoding="utf-8"
    )
    for number, text in enumerate(FIT_STARTS):
        start = int(utc(text).timestamp()) - FIT_EPOCH_OFFSET
        (uploaded / f"synthetic_activity_{number}.fit").write_bytes(
            synthetic_fit(sport=1, sub_sport=2, first_start=start, session_running_dynamics=(1000, 3500, 2500, 800, 5000, 1200))
        )
    sleep, uds, readiness, load, vo2_old, vo2_new, races, endurance, hill, hrv = ([] for _ in range(10))
    for offset, day in enumerate(days()):
        when = day.isoformat()
        if offset % 6:
            end = datetime(day.year, day.month, day.day, 22, 0, tzinfo=timezone.utc)
            row = {
                "calendarDate": when,
                "sleepStartTimestampGMT": (end - timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%S.0"),
                "sleepEndTimestampGMT": end.strftime("%Y-%m-%dT%H:%M:%S.0"),
                "deepSleepSeconds": 3600 + offset % 5 * 60,
                "lightSleepSeconds": 14400,
                "remSleepSeconds": 5400,
                # The shape that the normalization reads.
                "sleepScores": {"overall": {"value": 70 + offset % 20}},
            }
            if offset % 25 == 0:
                row.pop("sleepStartTimestampGMT")
            sleep.append(row)
        uds.append(
            {
                "calendarDate": when,
                "totalSteps": 6000 + offset % 13 * 500,
                **({"restingHeartRate": 45 + offset % 8} if offset % 9 else {}),
                "bodyBattery": {"chargedValue": 50 + offset % 30, "drainedValue": 55 + offset % 25},
                "allDayStress": {"aggregatorList": [{"type": "TOTAL", "averageStressLevel": 25 + offset % 15}]},
            }
        )
        for hour in range(1 + offset % 3):
            readiness.append({"calendarDate": when, "timestamp": f"{when}T{6 + hour * 5:02d}:00:00", "score": 40 + (offset + hour) % 50})
        load.append(
            {
                "calendarDate": when,
                "timestamp": epoch_ms(datetime(day.year, day.month, day.day, 3, tzinfo=timezone.utc)),
                "dailyTrainingLoadAcute": 300 + offset % 100,
                "dailyTrainingLoadChronic": 320 + offset % 60,
                "dailyAcuteChronicWorkloadRatio": round(0.8 + offset % 7 / 10, 1),
            }
        )
        if offset % 2 == 0:
            if day < date(2024, 1, 23):
                vo2_old.append({"calendarDate": when, "timestampGmt": f"{when}T05:00:00", "activityId": 100_000 + offset * 10, "vo2MaxValue": 50 + offset % 4, "sport": "RUNNING"})
            else:
                vo2_new.append({"calendarDate": when, "updateTimestamp": f"{when}T06:00:00", "vo2MaxValue": 52 + offset % 3, "sport": "RUNNING"})
                vo2_new.append({"calendarDate": when, "updateTimestamp": f"{when}T06:00:00", "vo2MaxValue": 48 + offset % 2, "sport": "CYCLING"})
        if offset % 7 == 0:
            races.append({"calendarDate": when, "timestamp": f"{when}T06:00:00", "raceTime5K": 1300 + offset % 40, "raceTime10K": 2750 + offset % 60, "raceTimeHalf": 6100 + offset % 90, "raceTimeMarathon": 12900 + offset % 120})
        endurance.append({"calendarDate": when, "overallScore": 6000 + offset % 300})
        if offset % 2:
            hill.append({"calendarDate": when, "overallScore": 50 + offset % 20})
        if day >= date(2024, 6, 1) and offset % 3:
            moment = datetime(day.year, day.month, day.day, 18, tzinfo=timezone.utc)
            hrv.append(((40 + offset % 25) * 128, int(moment.timestamp()) - FIT_EPOCH_OFFSET))
    (sleep_folder / "synthetic_sleepData.json").write_text(json.dumps(sleep), encoding="utf-8")
    files = {
        "UDSFile_synthetic.json": uds,
        "TrainingReadinessDTO_synthetic.json": readiness,
        "MetricsAcuteTrainingLoad_synthetic.json": load,
        "ActivityVo2Max_synthetic.json": vo2_old,
        "MetricsMaxMetData_synthetic.json": vo2_new,
        "RunRacePredictions_synthetic.json": races,
        "EnduranceScore_synthetic.json": endurance,
        "HillScore_synthetic.json": hill,
    }
    for name, rows in files.items():
        (metrics / name).write_text(json.dumps(rows), encoding="utf-8")
    (metrics / "synthetic_hrv.fit").write_bytes(hrv_fit(*hrv))
    return root
