from __future__ import annotations

import importlib
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfoNotFoundError

from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.common import time as time_module
from garmin_running_data_normalizer.common.time import (
    TIMEZONE_DATA_ERROR_CODE,
    TimezoneDataUnavailableError,
    require_timezone_data,
)
from garmin_running_data_normalizer.normalizers.activities import (
    normalize_activities,
)
from garmin_running_data_normalizer.run_all import RunAllError, run_all


ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_FIXTURE = ROOT / "examples/synthetic/garmin_export"
RUN_ALL_MODULE = importlib.import_module("garmin_running_data_normalizer.run_all")


class WindowsTimezoneDataTest(unittest.TestCase):
    def test_asia_tokyo_resolves_and_activity_contract_is_unchanged(self) -> None:
        self.assertEqual(str(require_timezone_data("Asia/Tokyo")), "Asia/Tokyo")
        records = normalize_activities(str(ACTIVITIES_FIXTURE))
        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["activity_datetime_local"],
            "2030-01-01T09:00:00+09:00",
        )
        self.assertEqual(records[0]["activity_date_local"], "2030-01-01")

    def test_missing_timezone_database_raises_bounded_error(self) -> None:
        with mock.patch.object(
            time_module,
            "ZoneInfo",
            side_effect=ZoneInfoNotFoundError("synthetic missing timezone"),
        ):
            with self.assertRaises(TimezoneDataUnavailableError) as raised:
                require_timezone_data("Asia/Tokyo")

        self.assertEqual(raised.exception.code, TIMEZONE_DATA_ERROR_CODE)
        self.assertEqual(raised.exception.timezone_name, "Asia/Tokyo")
        self.assertEqual(
            raised.exception.safe_message,
            "IANA timezone data for Asia/Tokyo is unavailable. "
            "Reinstall the package in a clean environment.",
        )
        self.assertNotIn("synthetic missing timezone", raised.exception.safe_message)

    def test_run_all_preserves_general_boundary_with_specific_timezone_cause(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with mock.patch.object(
                RUN_ALL_MODULE,
                "require_timezone_data",
                side_effect=TimezoneDataUnavailableError("Asia/Tokyo"),
            ):
                with self.assertRaises(RunAllError) as raised:
                    run_all(ACTIVITIES_FIXTURE, output)

        self.assertEqual(raised.exception.code, TIMEZONE_DATA_ERROR_CODE)
        self.assertEqual(
            raised.exception.safe_message,
            "IANA timezone data for Asia/Tokyo is unavailable. "
            "Reinstall the package in a clean environment.",
        )
        self.assertFalse(output.exists())

    def test_cli_reports_safe_timezone_diagnostic_without_traceback(self) -> None:
        error = StringIO()
        with mock.patch.object(
            runner,
            "run_all",
            side_effect=TimezoneDataUnavailableError("Asia/Tokyo"),
        ):
            with redirect_stderr(error):
                exit_code = runner.main(
                    [
                        "run-all",
                        "--input",
                        "synthetic-input",
                        "--output",
                        "synthetic-output",
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            error.getvalue(),
            "ERROR [TIMEZONE_DATA_UNAVAILABLE]: "
            "IANA timezone data for Asia/Tokyo is unavailable. "
            "Reinstall the package in a clean environment.\n",
        )
        self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
