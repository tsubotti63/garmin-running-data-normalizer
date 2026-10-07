from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.common import time as time_module
from garmin_running_data_normalizer.common.time import (
    TIMEZONE_INVALID_ERROR_CODE,
    TimezoneDataUnavailableError,
    TimezoneNameInvalidError,
    resolve_timezone_name,
)
from garmin_running_data_normalizer.diagnostics.doctor import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.fit.parser import parse_fit_export
from garmin_running_data_normalizer.normalizers.activities import normalize_activities
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
)
from garmin_running_data_normalizer.standalone import validate_standalone_handoff
from tests.fit_fixture_factory import synthetic_fit
from tests.test_hrv_normalizer import fit_timestamp, synthetic_hrv_fit

NEW_YORK = "America/New_York"
AUCKLAND = "Pacific/Auckland"
INVALID_MESSAGE = (
    "--timezone must be an exact IANA timezone name, "
    "such as Asia/Tokyo or America/New_York."
)
# The audit reproduction: a run at 20:00 EST on 2024-01-01 (01:00 UTC on 2024-01-02).
EVENING_IN_NEW_YORK = "2024-01-02T01:00:00Z"
# 22:00 EST on 2024-01-31 is already 2024-02-01 in Tokyo.
MONTH_END_IN_NEW_YORK = "2024-02-01T03:00:00Z"
# The synthetic FIT session starts at FIT time 1_000_000 (1990-01-11T13:46:40Z).
FIT_SESSION_START = "1990-01-11T13:46:40Z"


def epoch_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def activity_row(activity_id: int, start: str, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "activityId": activity_id,
        "activityType": "running",
        "sportType": "RUNNING",
        "startTimeGmt": epoch_ms(start),
        "distance": 1_000_000,
        "duration": 3_500_000,
        "name": f"Synthetic {activity_id}",
    }
    row.update(fields)
    return row


def write_export(
    root: Path,
    activities: list[dict[str, object]],
    *,
    sleep_rows: list[dict[str, object]] | None = None,
    session_fit: bool = False,
    hrv_fit: bytes | None = None,
) -> Path:
    fitness = root / "DI-Connect-Fitness"
    fitness.mkdir(parents=True)
    (fitness / "synthetic_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": activities}]),
        encoding="utf-8",
    )
    if sleep_rows is not None:
        wellness = root / "DI-Connect-Wellness"
        wellness.mkdir()
        (wellness / "synthetic_sleepData.json").write_text(
            json.dumps(sleep_rows), encoding="utf-8"
        )
    if session_fit:
        uploaded = root / "DI-Connect-Uploaded-Files"
        uploaded.mkdir()
        (uploaded / "synthetic_activity.fit").write_bytes(synthetic_fit(sport=1, sub_sport=2))
    if hrv_fit is not None:
        metrics = root / "DI-Connect-Metrics"
        metrics.mkdir()
        (metrics / "synthetic_hrv.fit").write_bytes(hrv_fit)
    return root


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_cli(*arguments: str) -> tuple[int, str]:
    error = StringIO()
    with redirect_stderr(error), redirect_stdout(StringIO()):
        exit_code = runner.main(list(arguments))
    return exit_code, error.getvalue()


class TimezoneNameTest(unittest.TestCase):
    def test_exact_iana_names_are_accepted(self) -> None:
        for name in ("Asia/Tokyo", NEW_YORK, "UTC", "America/Argentina/Buenos_Aires"):
            with self.subTest(name=name):
                self.assertEqual(resolve_timezone_name(name), name)

    def test_invalid_names_raise_a_bounded_error(self) -> None:
        for name in (
            "America",
            "",
            "../x",
            "/etc/localtime",
            "asia/tokyo",
            "Asia/Tokyo ",
            "JST",
            "+09:00",
            "Factory",
            None,
        ):
            with self.subTest(name=name):
                with self.assertRaises(TimezoneNameInvalidError) as raised:
                    resolve_timezone_name(name)
                self.assertEqual(raised.exception.code, TIMEZONE_INVALID_ERROR_CODE)
                self.assertEqual(raised.exception.safe_message, INVALID_MESSAGE)

    def test_names_follow_the_available_timezone_database(self) -> None:
        with mock.patch.object(
            time_module,
            "available_timezone_names",
            return_value=frozenset({"Asia/Tokyo", "Japan"}),
        ), mock.patch.object(time_module, "require_timezone_data"):
            self.assertEqual(resolve_timezone_name("Japan"), "Japan")
            with self.assertRaises(TimezoneNameInvalidError):
                resolve_timezone_name(NEW_YORK)
        with mock.patch.object(
            time_module, "available_timezone_names", return_value=frozenset()
        ):
            with self.assertRaises(TimezoneDataUnavailableError):
                resolve_timezone_name("Asia/Tokyo")

    def test_daylight_saving_transitions_in_new_york(self) -> None:
        expected = {
            "2024-03-10T06:30:00Z": "2024-03-10T01:30:00-05:00",
            "2024-03-10T07:30:00Z": "2024-03-10T03:30:00-04:00",
            "2024-11-03T05:30:00Z": "2024-11-03T01:30:00-04:00",
            "2024-11-03T06:30:00Z": "2024-11-03T01:30:00-05:00",
        }
        with tempfile.TemporaryDirectory() as directory:
            export = write_export(
                Path(directory) / "export",
                [activity_row(index, start) for index, start in enumerate(expected, 1)],
            )
            records = normalize_activities(str(export), NEW_YORK)
        observed = {
            datetime.fromtimestamp(row["start_time_gmt_ms"] / 1000, timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"): row["activity_datetime_local"]
            for row in records
        }
        self.assertEqual(observed, expected)


class RunAllTimezoneTest(unittest.TestCase):
    def test_default_equals_explicit_tokyo_and_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(
                root / "export", [activity_row(1, EVENING_IN_NEW_YORK)]
            )
            run_all(export, root / "default")
            run_all(export, root / "tokyo", timezone_name="Asia/Tokyo")

            self.assertEqual(tree_bytes(root / "default"), tree_bytes(root / "tokyo"))
            output = root / "default"
            for name in ("run_manifest.json", "run_summary.json", "ANALYSIS_CONTEXT.json"):
                self.assertEqual(load(output / name)["local_timezone"], "Asia/Tokyo")
            activity = load(output / "normalized/activities.json")[0]
            self.assertEqual(activity["activity_date_local"], "2024-01-02")
            self.assertEqual(
                activity["activity_datetime_local"], "2024-01-02T10:00:00+09:00"
            )
            self.assertIn(
                "- Local dates and times: `Asia/Tokyo` (IANA timezone)",
                (output / "START_HERE.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(validate_standalone_handoff(output)["dataset_count"], 17)

    def test_new_york_moves_local_dates_and_stays_out_of_shared_bundles(self) -> None:
        sleep_rows = [
            {
                "sleepStartTimestampGMT": "2024-01-01T20:00:00Z",
                "sleepEndTimestampGMT": "2024-01-02T03:30:00Z",
                "sleepTimeSeconds": 27000,
            }
        ]
        hrv = synthetic_hrv_fit((73 * 128, fit_timestamp("2024-01-02T03:00:00Z")))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(
                root / "export",
                [
                    activity_row(1, EVENING_IN_NEW_YORK),
                    activity_row(2, MONTH_END_IN_NEW_YORK),
                ],
                sleep_rows=sleep_rows,
                hrv_fit=hrv,
            )
            outputs = {}
            for name in ("Asia/Tokyo", NEW_YORK):
                output = root / name.replace("/", "_")
                run_all(export, output, timezone_name=name, external_safe_pack=True)
                outputs[name] = output

            output = outputs[NEW_YORK]
            for name in ("run_manifest.json", "run_summary.json", "ANALYSIS_CONTEXT.json"):
                self.assertEqual(load(output / name)["local_timezone"], NEW_YORK)
            activities = {
                row["activity_id"]: row
                for row in load(output / "normalized/activities.json")
            }
            self.assertEqual(activities[1]["activity_date_local"], "2024-01-01")
            self.assertEqual(
                activities[1]["activity_datetime_local"], "2024-01-01T20:00:00-05:00"
            )
            self.assertEqual(activities[2]["activity_date_local"], "2024-01-31")
            sleep = load(output / "normalized/sleep_daily.json")[0]
            self.assertEqual(sleep["sleep_day"], "2024-01-01")
            self.assertEqual(sleep["sleep_start_local"], "2024-01-01T15:00:00-05:00")
            self.assertEqual(sleep["sleep_end_local"], "2024-01-01T22:30:00-05:00")
            hrv_rows = load(output / "normalized/hrv_daily.json")
            self.assertEqual([row["calendar_date"] for row in hrv_rows], ["2024-01-01"])
            tokyo_hrv = load(outputs["Asia/Tokyo"] / "normalized/hrv_daily.json")
            self.assertEqual([row["calendar_date"] for row in tokyo_hrv], ["2024-01-02"])
            tokyo_sleep = load(outputs["Asia/Tokyo"] / "normalized/sleep_daily.json")[0]
            self.assertEqual(tokyo_sleep["sleep_day"], "2024-01-02")

            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            handoff = (output / "ANALYSIS_HANDOFF.md").read_text(encoding="utf-8")
            self.assertIn(f"- Local dates and times: `{NEW_YORK}` (IANA timezone)", start_here)
            self.assertIn("## Local Dates and Times", handoff)
            self.assertIn(f"`{NEW_YORK}`", handoff)

            months = {}
            for name, run_output in outputs.items():
                with zipfile.ZipFile(run_output / "analysis/external_safe_handoff.zip") as pack:
                    payload = b"".join(pack.read(member) for member in pack.namelist())
                    activities_csv = pack.read("safe/activities_monthly.csv").decode("utf-8")
                self.assertNotIn(NEW_YORK.encode("utf-8"), payload)
                self.assertNotIn(b"Asia/Tokyo", payload)
                months[name] = sorted(
                    line.split(",")[0] for line in activities_csv.splitlines()[1:]
                )
            self.assertEqual(months[NEW_YORK], ["2024-01", "2024-01"])
            self.assertEqual(months["Asia/Tokyo"], ["2024-01", "2024-02"])

            self.assertEqual(validate_standalone_handoff(output)["dataset_count"], 17)
            self.assertEqual(doctor_run_output(output)["completion_state"], "COMPLETED")
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            with zipfile.ZipFile(bundle) as archive:
                bundle_bytes = b"".join(archive.read(name) for name in archive.namelist())
            self.assertNotIn(NEW_YORK.encode("utf-8"), bundle_bytes)

    def test_timezone_can_decide_whether_daily_rows_share_a_day(self) -> None:
        sleep_rows = [
            {
                "calendarDate": "2024-01-01",
                "sleepStartTimestampGMT": "2024-01-01T03:00:00Z",
                "sleepEndTimestampGMT": "2024-01-01T11:00:00Z",
                "sleepTimeSeconds": 27000,
            },
            {
                "sleepStartTimestampGMT": "2024-01-01T20:00:00Z",
                "sleepEndTimestampGMT": "2024-01-02T03:30:00Z",
                "sleepTimeSeconds": 20000,
            },
        ]
        hrv = synthetic_hrv_fit(
            (60 * 128, fit_timestamp("2024-01-01T14:00:00Z")),
            (70 * 128, fit_timestamp("2024-01-01T16:00:00Z")),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(
                root / "export",
                [activity_row(1, EVENING_IN_NEW_YORK)],
                sleep_rows=sleep_rows,
            )
            run_all(export, root / "sleep-tokyo")
            self.assertEqual(
                sorted(row["sleep_day"] for row in load(root / "sleep-tokyo/normalized/sleep_daily.json")),
                ["2024-01-01", "2024-01-02"],
            )
            with self.assertRaises(RunAllError) as raised:
                run_all(export, root / "sleep-new-york", timezone_name=NEW_YORK)
            self.assertEqual(raised.exception.code, "DAILY_METRICS_CONFLICT")
            self.assertFalse((root / "sleep-new-york").exists())

            hrv_export = write_export(
                root / "hrv-export", [activity_row(1, EVENING_IN_NEW_YORK)], hrv_fit=hrv
            )
            statuses = {}
            for name in ("Asia/Tokyo", NEW_YORK):
                output = root / ("hrv-" + name.replace("/", "_"))
                run_all(hrv_export, output, timezone_name=name)
                statuses[name] = {
                    row["calendar_date"]: row["dedupe_status"]
                    for row in load(output / "normalized/hrv_daily.json")
                }
            self.assertEqual(sorted(statuses["Asia/Tokyo"]), ["2024-01-01", "2024-01-02"])
            self.assertNotIn(
                "review_required_same_day_differing_values", statuses["Asia/Tokyo"].values()
            )
            self.assertEqual(
                statuses[NEW_YORK],
                {"2024-01-01": "review_required_same_day_differing_values"},
            )

    def test_fit_times_follow_the_timezone_and_links_do_not_change(self) -> None:
        fit_start = epoch_ms(FIT_SESSION_START)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(
                root / "export",
                [
                    activity_row(
                        1,
                        datetime.fromtimestamp((fit_start + 30_000) / 1000, timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                    )
                ],
                session_fit=True,
            )
            sessions, laps, _audit = parse_fit_export(export, timezone_name=AUCKLAND)
            self.assertEqual(sessions[0]["start_datetime_local"], "1990-01-12T02:46:40+13:00")
            self.assertTrue(all(lap["start_time"].endswith("+13:00") for lap in laps))
            default_sessions, _laps, _audit = parse_fit_export(export)
            self.assertEqual(
                default_sessions[0]["start_datetime_local"], "1990-01-11T22:46:40+09:00"
            )

            links = {}
            for name in ("Asia/Tokyo", AUCKLAND):
                output = root / name.replace("/", "_")
                run_all(export, output, timezone_name=name)
                links[name] = [
                    (row["garmin_activity_key"], row["fit_session_key"], row["match_rule"])
                    for row in load(output / "normalized/activity_fit_links.json")
                ]
            self.assertEqual(len(links["Asia/Tokyo"]), 1)
            self.assertEqual(links["Asia/Tokyo"], links[AUCKLAND])


class TimezoneEntryPointTest(unittest.TestCase):
    def test_invalid_names_stop_every_entry_point_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export", [activity_row(1, EVENING_IN_NEW_YORK)])
            for name in ("America", "", "asia/tokyo"):
                with self.subTest(name=name):
                    with self.assertRaises(RunAllError) as raised:
                        run_all(export, root / "api", timezone_name=name)
                    self.assertEqual(raised.exception.code, TIMEZONE_INVALID_ERROR_CODE)
                    self.assertFalse((root / "api").exists())
            commands = {
                "run-all": ["run-all", "--input", str(export), "--output", str(root / "cli")],
                "normalize-activities": [
                    "normalize-activities",
                    "--input",
                    str(export),
                    "--output",
                    str(root / "golden"),
                ],
                "snapshot run-all": [
                    "snapshot",
                    "run-all",
                    "--store",
                    str(root / "missing-store"),
                    "--output",
                    str(root / "snapshot-output"),
                ],
                "doctor": ["doctor", "--input", str(export)],
            }
            for label, arguments in commands.items():
                with self.subTest(command=label):
                    exit_code, stderr = run_cli(*arguments, "--timezone", "America")
                    self.assertEqual(exit_code, 2)
                    self.assertEqual(
                        stderr, f"ERROR [{TIMEZONE_INVALID_ERROR_CODE}]: {INVALID_MESSAGE}\n"
                    )
            self.assertFalse((root / "cli").exists())
            self.assertFalse((root / "golden").exists())
            self.assertFalse((root / "snapshot-output").exists())

    def test_normalize_activities_records_the_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export", [activity_row(1, EVENING_IN_NEW_YORK)])
            exit_code, stderr = run_cli(
                "normalize-activities",
                "--input",
                str(export),
                "--output",
                str(root / "output"),
                "--timezone",
                NEW_YORK,
            )
            self.assertEqual((exit_code, stderr), (0, ""))
            self.assertEqual(load(root / "output/run_manifest.json")["local_timezone"], NEW_YORK)
            record = load(root / "output/normalized_activities.json")[0]
            self.assertEqual(record["activity_date_local"], "2024-01-01")

    def test_snapshot_run_all_uses_the_timezone_without_changing_the_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export", [activity_row(1, EVENING_IN_NEW_YORK)])
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            register_snapshot(
                store,
                export,
                snapshot_label="S1",
                export_requested_at="2030-01-01T00:00:00+00:00",
                export_downloaded_at="2030-01-01T01:00:00+00:00",
                export_observed_at="2030-01-01T02:00:00+00:00",
                confirm_complete=True,
            )
            tokyo = run_snapshot_all(store, root / "tokyo")
            new_york = run_snapshot_all(store, root / "new-york", timezone_name=NEW_YORK)

            self.assertEqual(tokyo["canonical_build_sha256"], new_york["canonical_build_sha256"])
            self.assertEqual(
                (root / "tokyo/snapshot/snapshot_lineage.json").read_bytes(),
                (root / "new-york/snapshot/snapshot_lineage.json").read_bytes(),
            )
            self.assertEqual(load(root / "new-york/run_summary.json")["local_timezone"], NEW_YORK)
            activity = load(root / "new-york/normalized/activities.json")[0]
            self.assertEqual(activity["activity_date_local"], "2024-01-01")

    def test_handoff_rejects_disagreeing_timezone_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = write_export(root / "export", [activity_row(1, EVENING_IN_NEW_YORK)])
            output = root / "output"
            run_all(export, output, timezone_name=NEW_YORK)
            context_path = output / "ANALYSIS_CONTEXT.json"
            context = load(context_path)
            context["local_timezone"] = "Asia/Tokyo"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            exit_code, stderr = run_cli("validate-handoff", "--input", str(output))
            self.assertEqual(exit_code, 2)
            self.assertIn("local timezone does not match", stderr)


if __name__ == "__main__":
    unittest.main()
