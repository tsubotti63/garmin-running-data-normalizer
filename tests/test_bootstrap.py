import unittest
from contextlib import redirect_stdout
from io import StringIO

from garmin_running_data_normalizer import IMPLEMENTATION_STATUS, __version__
from garmin_running_data_normalizer.runner import main


class PackageIdentityTest(unittest.TestCase):
    def test_stable_release_identity(self) -> None:
        self.assertEqual(__version__, "1.1.0rc1")
        self.assertEqual(IMPLEMENTATION_STATUS, "STABLE_RELEASE_READY")

    def test_cli_reports_package_version(self) -> None:
        output = StringIO()
        with self.assertRaises(SystemExit) as exited, redirect_stdout(output):
            main(["--version"])
        self.assertEqual(exited.exception.code, 0)
        self.assertEqual(
            output.getvalue().strip(),
            "python -m garmin_running_data_normalizer 1.1.0rc1",
        )


if __name__ == "__main__":
    unittest.main()
