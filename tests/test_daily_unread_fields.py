"""The source fields of the daily datasets that a run does not read are
counted (stage A4c-2).

The audit records of UDS, Sleep, Training Readiness, Acute Training Load,
Training History, Hill Score, Endurance Score, VO2max, and Race Prediction,
and that of the Lactate Threshold candidates, count by name the fields of the
rows read that no field takes, as those of Activities, Gear, links, and
Personal Records are counted (stage A4c-1). VO2max reads other fields for
each series, and the Lactate Threshold candidates for each kind of file. The
private fields of Hill and Endurance are counted apart, so they are not
counted again.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output  # noqa: F401
from garmin_running_data_normalizer.normalizers import (
    performance_metrics,
    race_prediction,
    sleep,
    training_history,
    training_load,
    training_readiness,
    uds,
    vo2max,
)
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import build_approved_input, initialize_store
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_parity import differences, runs
from tests.test_snapshot_record_updates import ACCOUNT, load, register, write_export
from tests.test_unread_fields import OTHER_NAMES, RecordingRow, read_fields

DAILY_AUDITS = (
    "uds_daily",
    "sleep_daily",
    "training_readiness_daily",
    "acute_training_load_daily",
    "training_history_daily",
    "hill_score_daily",
    "endurance_score_daily",
    "vo2max_daily",
    "race_prediction_daily",
    "lactate_threshold_candidates",
)


def write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


def daily_export(root: Path, name: str = "export", *, extra: bool = True) -> Path:
    """An Export whose daily rows hold a field that no field takes; without
    ``extra``, the same Export without it. The build and Run-All decide apart
    which rows are kept (stage A4c-2), so every daily file also has a row
    that is left out, and every Lactate Threshold file a row that is not a
    candidate, whose fields are not counted; the heart rate zones also have a
    row that is a candidate by its method alone."""

    def more(**fields: object) -> dict[str, object]:
        return fields if extra else {}

    # A row without its date, which is left out.
    left_out = more(leftOutNote=1)

    source = write_export(root, name, [_activity("1001")])
    metrics = source / "DI-Connect-Metrics"
    wellness = source / "DI-Connect-Wellness"
    aggregator = source / "DI-Connect-Aggregator"
    date = "2030-02-01"
    write(aggregator / "UDSFile_1.json", [
        {"calendarDate": date, "totalSteps": 5, **more(floorsAscended=3)}, {"totalSteps": 7, **left_out}])
    write(wellness / "synthetic_sleepData.json", [{
        "calendarDate": date, "sleepStartTimestampGMT": "2030-02-01T12:00:00Z",
        "sleepEndTimestampGMT": "2030-02-01T20:00:00Z", "sleepTimeSeconds": 27000,
        **more(sleepNote=1)}, {"sleepTimeSeconds": 27000, **left_out}])
    write(metrics / "TrainingReadinessDTO_1.json", [{
        "calendarDate": date, "timestamp": f"{date}T06:00:00", "score": 50, **more(feedbackShort="x")},
        {"timestamp": f"{date}T06:00:00", "score": 50, **left_out}])
    write(metrics / "MetricsAcuteTrainingLoad_1.json", [{
        "calendarDate": date, "timestamp": f"{date}T06:00:00Z", "dailyTrainingLoadAcute": 5,
        **more(trainingLoadNote=1)}, {"timestamp": f"{date}T06:00:00Z", "dailyTrainingLoadAcute": 5, **left_out}])
    write(metrics / "TrainingHistory_1.json", [{
        "calendarDate": date, "timestamp": f"{date}T06:00:00", "trainingStatus": "PRODUCTIVE",
        "sport": "RUNNING", **more(fitnessTrend=1)},
        {"timestamp": f"{date}T06:00:00", "trainingStatus": "PRODUCTIVE", "sport": "RUNNING", **left_out}])
    write(metrics / "RunRacePredictions_1.json", [{
        "calendarDate": date, "timestamp": f"{date}T06:00:00", "raceTime5K": 1000, "raceTime10K": 2100,
        "raceTimeHalf": 4700, "raceTimeMarathon": 9900, **more(predictionNote=1)},
        {"timestamp": f"{date}T06:00:00", "raceTime5K": 1000, **left_out}])
    write(metrics / "HillScore_synthetic_1.json", [{
        "calendarDate": date, "overallScore": 70, "strengthScore": 60, "deviceId": "PRIVATE-DEVICE",
        **more(hillNote=1)}, {"overallScore": 70, **left_out}])
    write(metrics / "EnduranceScore_synthetic_1.json", [{
        "calendarDate": date, "overallScore": 6000, "classification": 5, "userProfilePK": "PRIVATE-ACCOUNT",
        **more(enduranceNote=1)}, {"overallScore": 6000, **left_out}])
    write(metrics / "ActivityVo2Max_1.json", [{
        "calendarDate": date, "timestampGmt": f"{date}T07:00:00", "vo2MaxValue": 50, "sport": "RUNNING",
        "activityId": 1001, **more(updateTimestamp=f"{date}T08:00:00")},
        {"timestampGmt": f"{date}T07:00:00", "vo2MaxValue": 50, "sport": "RUNNING", **left_out}])
    write(metrics / "MetricsMaxMetData_1.json", [{
        "calendarDate": date, "updateTimestamp": f"{date}T06:00:00", "vo2MaxValue": 51, "sport": "RUNNING",
        **more(timestampGmt=f"{date}T05:00:00")},
        {"updateTimestamp": f"{date}T06:00:00", "vo2MaxValue": 51, "sport": "RUNNING", **left_out}])
    write(wellness / "synthetic_userBioMetrics.json", [
        {"metaData": {"calendarDate": date, "sequence": 1}, "lactateThresholdHeartRate": 166, **more(weight=60000)},
        {"metaData": {"calendarDate": date, "sequence": 2}, "weight": 60000, **more(height=170)},
    ])
    # The other three kinds of Lactate Threshold files, each with a row that
    # holds no value and is not a candidate.
    write(wellness / "synthetic_biometrics_latest.json", [
        {"functionalThresholdPower": 250, **more(latestNote=1)}, {"functionalThresholdPower": None, **left_out}])
    write(wellness / "synthetic_userBiometricProfileData.json", [
        {"lactateThresholdHeartRate": 170, **more(profileNote=1)}, {"weight": 60000, **left_out}])
    write(metrics / "synthetic_heartRateZones.json", [
        {"trainingMethod": "LACTATE_THRESHOLD", "lactateThresholdSpeed": 3.2, **more(zonesNote=1)},
        {"trainingMethod": "LACTATE_THRESHOLD", **more(zonesMethodNote=1)},
        {"trainingMethod": "HEART_RATE_RESERVE", **left_out}])
    return source


def unread(output: Path, audit: str) -> tuple[dict[str, int] | None, int | None]:
    record = load(output / f"audit/{audit}.json")
    return record.get("unread_field_counts"), record.get("unread_other_name_count")


EXPECTED = {
    "uds_daily": {"floorsAscended": 1},
    "sleep_daily": {"sleepNote": 1},
    "training_readiness_daily": {"feedbackShort": 1},
    "acute_training_load_daily": {"trainingLoadNote": 1},
    "training_history_daily": {"fitnessTrend": 1},
    "hill_score_daily": {"hillNote": 1},
    "endurance_score_daily": {"enduranceNote": 1},
    # Each series reads its own time: the other one is not read.
    "vo2max_daily": {"timestampGmt": 1, "updateTimestamp": 1},
    "race_prediction_daily": {"predictionNote": 1},
    # The row that is not a candidate is not counted.
    "lactate_threshold_candidates": {
        "latestNote": 1, "profileNote": 1, "weight": 1, "zonesMethodNote": 1, "zonesNote": 1},
}


class DailyUnreadFieldsTest(unittest.TestCase):
    def test_the_fields_that_no_field_takes_are_counted_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(daily_export(root), output)
            self.assertEqual(
                {audit: unread(output, audit) for audit in DAILY_AUDITS},
                {audit: (counts, None) for audit, counts in EXPECTED.items()},
            )
            # Nothing else is announced: the same Export without these fields
            # gives the same status, warnings, and record counts.
            plain = root / "plain-output"
            run_all(daily_export(root, "plain", extra=False), plain)
            for audit in DAILY_AUDITS:
                with self.subTest(audit=audit):
                    self.assertEqual(unread(plain, audit), (None, None))
            for name in ("status", "warnings", "normalized_record_count"):
                with self.subTest(field=name):
                    self.assertEqual(load(output / "run_summary.json")[name], load(plain / "run_summary.json")[name])

    def test_names_that_are_not_words_are_counted_without_their_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            write(source / "DI-Connect-Aggregator" / "UDSFile_1.json", [
                {"calendarDate": "2030-02-01", "totalSteps": 5, **{name: 1 for name in OTHER_NAMES}}])
            output = root / "output"
            run_all(source, output)
            self.assertEqual(unread(output, "uds_daily"), (None, len(OTHER_NAMES)))
            text = (output / "audit/uds_daily.json").read_text(encoding="utf-8")
            for name in OTHER_NAMES:
                self.assertNotIn(name, text)

    def test_rows_left_out_are_not_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            write(source / "DI-Connect-Aggregator" / "UDSFile_1.json", [
                {"calendarDate": "2030-02-01", "totalSteps": 5, "kept": 1},
                {"totalSteps": 7, "leftOut": 1},
            ])
            output = root / "output"
            run_all(source, output)
            self.assertEqual(load(output / "audit/uds_daily.json")["excluded_record_count"], 1)
            self.assertEqual(unread(output, "uds_daily"), ({"kept": 1}, None))

    def test_a_snapshot_run_counts_as_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root / "runs", daily_export(root))
            self.assertEqual(differences(one_shot, snapshot), [])
            for audit in DAILY_AUDITS:
                with self.subTest(audit=audit):
                    self.assertEqual(unread(snapshot, audit), unread(one_shot, audit))


def uds_export(root: Path, name: str, rows: list[dict[str, Any]]) -> Path:
    source = write_export(root, name, [_activity("1001")])
    write(source / "DI-Connect-Aggregator" / "UDSFile_1.json", rows)
    return source


DAY = {"calendarDate": "2030-02-01", "totalSteps": 5}


class CopiesTest(unittest.TestCase):
    """The build passes the copies of a daily record within one Snapshot as
    one record only when they hold the same fields, as the names that it
    passes with them tell; a Snapshot run then counts as a one-shot run."""

    def check(self, rows: list[dict[str, Any]], expected: dict[str, int] | None) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root / "runs", uds_export(root, "export", rows))
            self.assertEqual(differences(one_shot, snapshot), [])
            for output in (one_shot, snapshot):
                with self.subTest(run=output.name):
                    self.assertEqual(unread(output, "uds_daily"), (expected, None))
                    self.assertEqual(load(output / "audit/uds_daily.json")["same_value_duplicate_count"], 1)

    def test_copies_that_differ_in_the_names_of_fields_not_read(self) -> None:
        self.check([{**DAY, "extraNote": 1}, DAY], {"extraNote": 1})

    def test_copies_one_of_which_holds_a_field_not_read_with_null(self) -> None:
        self.check([{**DAY, "extraNote": None}, DAY], {"extraNote": 1})

    def test_copies_that_differ_only_in_the_values_of_fields_not_read(self) -> None:
        self.check([{**DAY, "extraNote": 1}, {**DAY, "extraNote": 2}], {"extraNote": 2})

    def test_two_snapshots_that_differ_only_in_the_names_of_fields_not_read(self) -> None:
        # The build passes the record of each Snapshot, as their names
        # differ; the values agree, so nothing disagrees, and the field of
        # the first Snapshot counts once.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = uds_export(root, "first", [{**DAY, "extraNote": 1}])
            second = uds_export(root, "second", [DAY])
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            output = root / "snapshot"
            from garmin_running_data_normalizer.snapshot import run_snapshot_all

            run_snapshot_all(store, output)
            self.assertEqual(unread(output, "uds_daily"), ({"extraNote": 1}, None))
            audit = load(output / "audit/uds_daily.json")
            self.assertEqual((audit["disagreement_key_count"], audit["accepted_record_count"]), (0, 1))
            codes = {item["code"] for item in load(output / "run_summary.json")["warnings"]}
            self.assertNotIn("VALUES_DISAGREE", codes)

    def test_the_field_states_of_a_snapshot_count_the_fields_passed(self) -> None:
        # The record of the day holds the two fields of UDS that the build
        # passes; the field states of the merge summary count those only.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _one_shot, snapshot = runs(root / "runs", uds_export(root, "export", [{**DAY, "extraNote": 1}]))
            summary = load(snapshot / "snapshot/canonical_merge_summary.json")
            self.assertEqual(
                summary["datasets"]["uds_daily"]["presence_state_counts"],
                {"explicit_value": 2, "field_absent": 0, "record_absent": 0},
            )

    def test_copies_of_a_lactate_threshold_candidate(self) -> None:
        row = {"metaData": {"calendarDate": "2030-01-01", "sequence": 1}, "lactateThresholdHeartRate": 166, "weight": 1}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("1001")])
            for copy in range(2):
                write(source / "DI-Connect-Wellness" / f"synthetic_copy{copy}_userBioMetrics.json", [row])
            one_shot, snapshot = runs(root / "runs", source)
            self.assertEqual(differences(one_shot, snapshot), [])
            for output in (one_shot, snapshot):
                with self.subTest(run=output.name):
                    self.assertEqual(unread(output, "lactate_threshold_candidates"), ({"weight": 2}, None))

    def test_the_build_passes_the_records_as_before(self) -> None:
        # The build counts the fields itself and passes the daily records
        # narrowed to the fields of their dataset, as before stage A4c-2.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, daily_export(root), "S1", 1)
            build = root / "build"
            build_approved_input(store, build)
            names = {"floorsAscended", "sleepNote", "feedbackShort", "trainingLoadNote", "fitnessTrend",
                     "predictionNote", "hillNote", "enduranceNote", "weight"}
            for path in build.rglob("*.json"):
                text = path.read_text(encoding="utf-8")
                for name in names:
                    with self.subTest(file=path.name, name=name):
                        self.assertNotIn(f'"{name}"', text)


class LactateCandidateRuleTest(unittest.TestCase):
    def test_the_rule_of_the_build_is_that_of_the_candidates(self) -> None:
        rows = [
            ("history", {"metaData": {"calendarDate": "2030-01-01"}, "lactateThresholdHeartRate": 166}),
            ("history", {"metaData": {"calendarDate": "2030-01-01"}, "lactateThresholdHeartRate": None}),
            ("history", {"metaData": {"calendarDate": "2030-01-01"}, "lactateThresholdHeartRate": "fast"}),
            ("history", {"metaData": {"calendarDate": "2030-01-01"}, "lactateThresholdHeartRate": True}),
            ("history", {"metaData": {}, "lactateThresholdHeartRate": 166}),
            ("history", {"lactateThresholdHeartRate": 166}),
            ("latest_snapshot", {"functionalThresholdPower": 250}),
            ("latest_snapshot", {"functionalThresholdPower": ""}),
            ("derived_evidence", {"trainingMethod": "LACTATE_THRESHOLD", "lactateThresholdSpeed": 3.2}),
            # The method alone gives a value in the heart rate zones only.
            ("derived_evidence", {"trainingMethod": "LACTATE_THRESHOLD"}),
            ("derived_evidence", {"trainingMethod": "HEART_RATE_RESERVE"}),
            ("derived_evidence", {"trainingMethod": "HEART_RATE_RESERVE", "lactateThresholdSpeed": 3.2}),
            ("latest_snapshot", {"trainingMethod": "LACTATE_THRESHOLD"}),
            ("history", {"metaData": {"calendarDate": "2030-01-01"}, "trainingMethod": "LACTATE_THRESHOLD"}),
            ("profile_state", {"weight": 60000}),
        ]
        names = {
            "history": "synthetic_userBioMetrics.json",
            "latest_snapshot": "synthetic_biometrics_latest.json",
            "profile_state": "synthetic_userBiometricProfileData.json",
            "derived_evidence": "synthetic_heartRateZones.json",
        }
        for family, row in rows:
            with self.subTest(family=family, row=row):
                with mock.patch.object(performance_metrics, "_load_json", return_value=[row]):
                    collected = performance_metrics.collect_lactate_threshold_candidates([asset(names[family])])
                self.assertEqual(
                    performance_metrics.is_lactate_threshold_candidate(row, family),
                    collected["candidate_count"] == 1,
                )


def asset(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        kind="json", source_path=name, member_path=None, provenance_path=name, sha256="0" * 64
    )


def rows_of(fields: frozenset[str], touched: set[str], *variants: dict[str, Any]) -> list[RecordingRow]:
    """Rows that hold every field of a list, with a value, and the variants
    that take the other ways of the reading, all remembering what is read."""
    full = {name: 1 for name in fields}
    return [RecordingRow({**full, **variant}, touched=touched) for variant in ({}, *variants)]


class FieldListTest(unittest.TestCase):
    """The field lists are the fields that the daily datasets read, in both
    directions, for each series and each way of the reading."""

    def selected(self, module: Any, function: str, name: str, rows: list[RecordingRow]) -> None:
        item = asset(name)
        with mock.patch.object(module, "selected_rows", return_value=([item], rows)):
            getattr(module, function)([item])

    def assertRead(self, touched: set[str], fields: frozenset[str]) -> None:
        self.assertEqual(read_fields(touched), set(fields))

    def test_uds(self) -> None:
        touched: set[str] = set()
        fields = uds.UDS_SOURCE_FIELDS
        rows = rows_of(
            fields, touched,
            {"calendarDate": "2030-02-01"},
            # Without a calendar date, the date; without totals, the others.
            {"calendarDate": None, "date": "2030-02-02"},
        )
        rows.append(RecordingRow(
            {key: value for key, value in rows[1].items() if key not in ("totalSteps", "totalDistanceMeters")},
            touched=touched,
        ))
        self.selected(uds, "normalize_uds", "UDSFile_1.json", rows)
        self.assertRead(touched, fields)

    def test_training_readiness_load_history_and_race_prediction(self) -> None:
        cases = (
            (training_readiness, "normalize_training_readiness", "TrainingReadinessDTO_1.json",
             training_readiness.TRAINING_READINESS_SOURCE_FIELDS),
            (training_load, "normalize_acute_training_load", "MetricsAcuteTrainingLoad_1.json",
             training_load.ACUTE_TRAINING_LOAD_SOURCE_FIELDS),
            (training_history, "normalize_training_history", "TrainingHistory_1.json",
             training_history.TRAINING_HISTORY_SOURCE_FIELDS),
            (race_prediction, "normalize_race_prediction", "RunRacePredictions_1.json",
             race_prediction.RACE_PREDICTION_SOURCE_FIELDS),
        )
        for module, function, name, fields in cases:
            with self.subTest(dataset=function):
                touched: set[str] = set()
                rows = rows_of(
                    fields, touched,
                    {"calendarDate": "2030-02-01", "timestamp": "2030-02-01T06:00:00", "trainingStatus": "PRODUCTIVE"},
                )
                self.selected(module, function, name, rows)
                self.assertRead(touched, fields)

    def test_sleep(self) -> None:
        touched: set[str] = set()
        fields = sleep.SLEEP_SOURCE_FIELDS
        rows = rows_of(
            fields, touched,
            {"calendarDate": "2030-02-01", "sleepStartTimestampGMT": "2030-02-01T12:00:00Z",
             "sleepEndTimestampGMT": "2030-02-01T20:00:00Z"},
            # Without a calendar date, the day of the end time; without the
            # first names of the stages and scores, the others.
            {"calendarDate": None, "sleepEndTimestampGMT": "2030-02-02T20:00:00Z",
             "deepSleepSeconds": None, "lightSleepSeconds": None, "remSleepSeconds": None,
             "awakeSleepSeconds": None, "sleepScores": None, "overallScore": None},
            # Without any stage, the direct durations.
            {"calendarDate": "2030-02-03", "deepSleepSeconds": None, "deep_sleep_seconds": None,
             "lightSleepSeconds": None, "light_sleep_seconds": None, "remSleepSeconds": None,
             "rem_sleep_seconds": None},
        )
        item = SimpleNamespace(kind="json", source_path="DI-Connect-Wellness/x_sleepData.json",
                               member_path=None, provenance_path="x", sha256="0" * 64)
        with mock.patch.object(sleep, "load_rows", return_value=rows):
            sleep.normalize_sleep_daily_assets([item])
        self.assertRead(touched, fields)

    def test_vo2max_for_each_series(self) -> None:
        for name, fields, series_time in (
            ("ActivityVo2Max_1.json", vo2max.VO2MAX_ACTIVITY_SOURCE_FIELDS, "timestampGmt"),
            ("MetricsMaxMetData_1.json", vo2max.VO2MAX_METRICS_SOURCE_FIELDS, "updateTimestamp"),
        ):
            with self.subTest(file=name):
                touched: set[str] = set()
                rows = rows_of(
                    fields, touched,
                    {"calendarDate": "2030-02-01", "vo2MaxSourceSeries": None, series_time: "2030-02-01T06:00:00",
                     "sport": "RUNNING"},
                    # Without the time of the series, the observation time.
                    {"calendarDate": "2030-02-01", "vo2MaxSourceSeries": None, series_time: None,
                     "observationTimestamp": "2030-02-01T06:00:00", "sport": "RUNNING"},
                )
                item = asset(name)
                with mock.patch.object(vo2max, "selected_rows", return_value=([item], rows)), \
                        mock.patch.object(vo2max, "load_rows", return_value=rows):
                    vo2max.normalize_vo2max([item])
                self.assertRead(touched, fields)

    def test_hill_and_endurance(self) -> None:
        for function, name, fields in (
            ("normalize_hill_score", "HillScore_synthetic_1.json", performance_metrics.HILL_SOURCE_FIELDS),
            ("normalize_endurance_score", "EnduranceScore_synthetic_1.json", performance_metrics.ENDURANCE_SOURCE_FIELDS),
        ):
            with self.subTest(dataset=function):
                touched: set[str] = set()
                rows = rows_of(fields, touched, {"calendarDate": "2030-02-01", "overallScore": 70})
                with mock.patch.object(performance_metrics, "_load_json", return_value=rows):
                    getattr(performance_metrics, function)([asset(name)])
                self.assertRead(touched, fields)

    def test_lactate_threshold_for_each_kind_of_file(self) -> None:
        for family, name in (
            ("history", "synthetic_userBioMetrics.json"),
            ("latest_snapshot", "synthetic_biometrics_latest.json"),
            ("profile_state", "synthetic_userBiometricProfileData.json"),
            ("derived_evidence", "synthetic_heartRateZones.json"),
        ):
            with self.subTest(family=family):
                touched: set[str] = set()
                fields = performance_metrics.LACTATE_SOURCE_FIELDS[family]
                rows = rows_of(
                    fields, touched,
                    {"metaData": {"calendarDate": "2030-02-01", "sequence": 1}, "trainingMethod": "LACTATE_THRESHOLD"},
                )
                with mock.patch.object(performance_metrics, "_load_json", return_value=rows):
                    performance_metrics.collect_lactate_threshold_candidates([asset(name)])
                self.assertRead(touched, fields)


if __name__ == "__main__":
    unittest.main()
