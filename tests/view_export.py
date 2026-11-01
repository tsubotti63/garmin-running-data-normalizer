"""A synthetic Export of about two and a half years for the view page (stage G1).

With ``gear``, it has synthetic shoes too (stage S1 of v2.2.0): made-up names
only, as every test and picture of the guides has. Without it, it is as it
was, so that the numbers of the other tests stay. With ``names``, the
activities have made-up names of training instead (stage T1 of v2.2.0), a
synthetic memo, and a few activities just on and just outside the bounds of
the conditions, and without a distance or a time.
"""

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
# Made-up names of training (stage T1 of v2.2.0): full and half width, case,
# no name, and a name of spaces only.
TRAINING_NAMES = ("ペース走", "ﾍﾟｰｽ走 朝", "TEMPO run", "ジョグ", "インターバル 400m", None, "  ")
# A synthetic memo, which no answer of the view page may hold (Codex's review
# of the plan of T1).
MEMO_MARK = "synthetic-memo-t1"
# Activities just on and just outside the bounds of 10 km and 60 minutes, and
# without a distance or a time: id, start, centimetres, milliseconds, name.
BOUND_ACTIVITIES = (
    (700_001, "2024-06-01T21:00:00Z", 1_000_000, 3_600_000, "境目 ちょうど"),
    (700_002, "2024-06-02T21:00:00Z", 999_999, 3_599_999, "境目 すぐ外"),
    (700_003, "2024-06-03T21:00:00Z", None, 3_000_000, "距離なし"),
    (700_004, "2024-06-04T21:00:00Z", 800_000, None, "時間なし"),
)


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def epoch_ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def days() -> list[date]:
    return [FIRST + timedelta(days=offset) for offset in range((LAST - FIRST).days + 1)]


def activities(gear: bool = False, names: bool = False) -> list[dict[str, object]]:
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
            if names:
                name = TRAINING_NAMES[(offset + number) % len(TRAINING_NAMES)]
                if name is None:
                    row.pop("name")
                else:
                    row["name"] = name
                if offset % 4 == 0:
                    row["description"] = f"{MEMO_MARK} {offset}"
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
    if names:
        for activity_id, text, distance, duration, name in BOUND_ACTIVITIES:
            row = {"activityId": activity_id, "activityType": "running", "sportType": "RUNNING", "startTimeGmt": epoch_ms(utc(text)), "name": name}
            if distance is not None:
                row["distance"] = distance
            if duration is not None:
                row["duration"] = duration
            rows.append(row)
    if gear:
        # Runs with a shoe that the numbers leave out or count apart (stage
        # S1 of v2.2.0): without a distance, after today, and without a date.
        for activity_id, start, distance in (
            (800_001, epoch_ms(utc("2024-10-10T21:00:00Z")), None),
            (800_002, epoch_ms(utc("2099-01-01T21:00:00Z")), 1_000_000),
            (800_003, None, 1_000_000),
        ):
            row = {"activityId": activity_id, "activityType": "running", "sportType": "RUNNING", "duration": 3_000_000}
            if start is not None:
                row["startTimeGmt"] = start
            if distance is not None:
                row["distance"] = distance
            rows.append(row)
    return rows


# The synthetic gear (stage S1 of v2.2.0), by its gearPk: the shoes, a bike,
# and gear whose two names of the type disagree, so that its type is null.
# Two shoes share a name and are told apart by the day of their start; one has
# no displayName and is named by its customMakeModel; the gearPk "0123" is the
# key 123 of its links, as one token.
SYNTHETIC_GEAR = (
    {"gearPk": 1, "displayName": "ロード用 A", "customMakeModel": "Synthetic road 1", "gearTypeName": "Shoes", "dateBegin": "2023-01-01T00:00:00.0", "dateEnd": "2024-03-31T00:00:00.0", "maximumMeters": 800000},
    {"gearPk": "0123", "displayName": "ロード用 B", "customMakeModel": "Synthetic road 2", "gearTypeName": "running_shoes", "dateBegin": "2024-03-01T00:00:00.0", "maximumMeters": 800000},
    {"gearPk": 3, "displayName": "トレイル用 C", "customMakeModel": "Synthetic trail", "gearTypeName": "Shoes", "dateBegin": "2023-01-01T00:00:00.0", "maximumMeters": 600000},
    {"gearPk": 4, "displayName": "レース用 D", "customMakeModel": "Synthetic race", "gearTypeName": "Shoes", "dateBegin": "2023-01-01T00:00:00.0", "maximumMeters": 0},
    {"gearPk": 5, "displayName": "", "customMakeModel": "Synthetic model X", "gearTypeName": "Shoes", "dateBegin": "2024-09-01T00:00:00.0"},
    {"gearPk": 6, "displayName": "ロード用 A", "customMakeModel": "Synthetic road 1", "gearTypeName": "Shoes", "dateBegin": "2025-01-01T00:00:00.0", "maximumMeters": 800000},
    {"gearPk": 8, "displayName": "自転車", "gearTypeName": "Bike", "dateBegin": "2023-01-01T00:00:00.0"},
    {"gearPk": 9, "displayName": "種類の分からない道具", "gearTypeName": "Shoes", "gearType": "Bike"},
)


def gear_links(rows: list[dict[str, object]]) -> dict[str, list[int]]:
    """The links of the synthetic gear, by the key that the Gear file gives
    (stage S1 of v2.2.0): the road runs with the shoe of their days, the trail
    runs with C, the long runs with D too (two shoes), the treadmill runs
    from September 2024 with the shoe of a model, and some with the bike only,
    with the gear of a type not known only, or with gear not in the Export
    (555); the bike rides with the bike, and a link to an activity not in the
    Export (999999)."""
    links: dict[str, list[int]] = {}

    def link(key: str, activity_id: int) -> None:
        links.setdefault(key, []).append(activity_id)

    for row in rows:
        activity_id, kind = row["activityId"], row["activityType"]
        start = row.get("startTimeGmt")
        day = datetime.fromtimestamp(start / 1000, timezone.utc).date() if isinstance(start, int) else None
        if kind == "running":
            if day is None or day < date(2024, 3, 1):
                link("1", activity_id)
            elif day < date(2025, 1, 1) or activity_id % 2:
                link("123", activity_id)
            else:
                link("6", activity_id)
            # The longest runs, which are runs (offset % 9 == 6), with D too.
            if row.get("distance") == 1_100_000:
                link("4", activity_id)
            if isinstance(activity_id, int) and activity_id % 50 == 0:
                link("8", activity_id)
        elif kind == "trail_running":
            link("3", activity_id)
        elif kind == "treadmill_running":
            if activity_id % 7 == 1:
                link("8", activity_id)
            elif activity_id % 7 == 2:
                link("9", activity_id)
            elif activity_id % 7 == 3:
                link("555", activity_id)
            elif day is not None and day >= date(2024, 9, 1):
                link("5", activity_id)
        elif kind == "road_biking":
            link("8", activity_id)
    link("1", 999_999)
    return links


def write_view_export(root: Path, gear: bool = False, names: bool = False) -> Path:
    fitness = root / "DI-Connect-Fitness"
    metrics = root / "DI-Connect-Metrics"
    sleep_folder = root / "DI-Connect-Wellness"
    uploaded = root / "DI-Connect-Uploaded-Files"
    for folder in (fitness, metrics, sleep_folder, uploaded):
        folder.mkdir(parents=True)
    (fitness / "synthetic_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": activities(gear, names)}]), encoding="utf-8"
    )
    if gear:
        links = gear_links(activities(gear))
        container = {
            "gearDTOS": [dict(row) for row in SYNTHETIC_GEAR],
            "gearActivityDTOs": {key: [{"activityId": activity_id} for activity_id in ids] for key, ids in links.items()},
        }
        (fitness / "synthetic_gear.json").write_text(json.dumps([container], ensure_ascii=False), encoding="utf-8")
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
