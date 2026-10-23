from __future__ import annotations

import contextlib
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor as doctor_module
from garmin_running_data_normalizer.diagnostics.doctor import DoctorError, doctor_run_output
from garmin_running_data_normalizer import run_all as run_all_module
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer import standalone
from garmin_running_data_normalizer.diagnostics.support_bundle import (
    SupportBundleError,
    _supported_run_quality_version,
    build_support_bundle,
)
from garmin_running_data_normalizer.standalone import (
    OtherVersionError,
    StandaloneHandoffError,
    validate_standalone_handoff,
)
from tests.v1_3_outputs import as_v1_3


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"

# Support Bundle decisions for Run Quality product versions. Every 1.x row keeps
# the result of the expression used through v1.7.0; only later major versions
# and pre-release versions after major.minor.patch are newly accepted.
RUN_QUALITY_VERSIONS = (
    ("1.4", True),
    ("1.4.0", True),
    ("1.4.01", True),
    ("1.9.9", True),
    ("1.10", True),
    ("1.10.3", True),
    ("1.7.0", True),
    ("1.04", False),
    ("1.3", False),
    ("1.3.0", False),
    ("0.9.0", False),
    ("02.0.0", False),
    ("2", False),
    ("2.x", False),
    ("2.0rc1", False),
    ("1.4.0.post1", False),
    ("1.7.0rc1", True),
    ("2.0.0", True),
    ("2.0.0rc1", True),
    ("2.0.0a1", True),
    ("2.0.0b2", True),
    ("10.1.0", True),
)


@contextlib.contextmanager
def installed(version: str) -> Iterator[None]:
    """Make validation behave as if the given Product version were installed."""
    with patch.object(standalone, "__version__", version), patch.object(
        doctor_module, "__version__", version
    ):
        yield


def run_as(version: str, output: Path) -> None:
    """Produce a consistent synthetic Run-All output that records the given version."""
    with patch.object(run_all_module, "__version__", version):
        run_all(SYNTHETIC_EXPORT, output)


class MajorVersionAcceptanceTest(unittest.TestCase):
    def test_support_bundle_version_rule_table(self) -> None:
        for version, accepted in RUN_QUALITY_VERSIONS:
            with self.subTest(version=version):
                self.assertIs(_supported_run_quality_version(version), accepted)
        self.assertFalse(_supported_run_quality_version(None))
        self.assertFalse(_supported_run_quality_version(2))

    def test_current_major_one_output_is_accepted_as_before(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            validate_standalone_handoff(output)
            report = doctor_run_output(output)
            self.assertEqual(report["diagnostic_contract_availability"], "CURRENT")
            build_support_bundle(output, root / "support.zip")

    def test_legacy_major_one_version_keeps_the_legacy_handling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "handoff"
            run_all(SYNTHETIC_EXPORT, output)
            as_v1_3(output)
            validate_standalone_handoff(output)
            report = doctor_run_output(output)
            self.assertEqual(
                report["diagnostic_contract_availability"], "LEGACY_NOT_AVAILABLE"
            )
            with self.assertRaises(SupportBundleError) as caught:
                build_support_bundle(output, root / "support.zip")
            self.assertEqual(caught.exception.code, "SUPPORT_BUNDLE_AUTHORITY_INVALID")

    def test_later_major_output_is_rejected_by_a_different_installed_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "handoff"
            # A later major version than the installed 2.0.0 (stage E2b).
            run_as("3.0.0", output)
            # Told as an output of another version (stage B5b); until then,
            # HANDOFF_INVALID, DOCTOR_AUTHORITY_INVALID, and
            # SUPPORT_BUNDLE_AUTHORITY_INVALID.
            with self.assertRaisesRegex(OtherVersionError, "made by version 3.0.0 of this app"):
                validate_standalone_handoff(output)
            with self.assertRaises(DoctorError) as caught:
                doctor_run_output(output)
            self.assertEqual(caught.exception.code, "OUTPUT_OTHER_VERSION")
            with self.assertRaises(SupportBundleError) as caught_bundle:
                build_support_bundle(output, root / "support.zip")
            self.assertEqual(caught_bundle.exception.code, "OUTPUT_OTHER_VERSION")

    def test_later_major_and_pre_release_outputs_are_accepted_when_installed(self) -> None:
        for version in ("2.0.0", "2.0.0rc1"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "handoff"
                run_as(version, output)
                with installed(version):
                    validate_standalone_handoff(output)
                    report = doctor_run_output(output)
                    self.assertEqual(report["product_version"], version)
                    self.assertEqual(
                        report["diagnostic_contract_availability"], "CURRENT"
                    )
                    build_support_bundle(output, root / "support.zip")

    def test_major_zero_output_is_rejected_even_when_installed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "handoff"
            run_as("0.9.0", output)
            with installed("0.9.0"):
                with self.assertRaisesRegex(StandaloneHandoffError, "not supported"):
                    validate_standalone_handoff(output)
                with self.assertRaises(DoctorError) as caught:
                    doctor_run_output(output)
                self.assertEqual(caught.exception.code, "DOCTOR_VERSION_UNSUPPORTED")
                with self.assertRaises(SupportBundleError) as caught_bundle:
                    build_support_bundle(output, root / "support.zip")
                self.assertEqual(
                    caught_bundle.exception.code, "SUPPORT_BUNDLE_AUTHORITY_INVALID"
                )

    def test_malformed_versions_are_rejected(self) -> None:
        # A version of another form than this one's is another version
        # (stage B5b), and is not repeated in the words of its stop.
        cases = (
            ("2", "not supported", "DOCTOR_VERSION_UNSUPPORTED", "SUPPORT_BUNDLE_AUTHORITY_INVALID"),
            ("2.x", "invalid", "DOCTOR_VERSION_UNSUPPORTED", "SUPPORT_BUNDLE_AUTHORITY_INVALID"),
            ("2.0rc1", "invalid", "DOCTOR_VERSION_UNSUPPORTED", "SUPPORT_BUNDLE_AUTHORITY_INVALID"),
            ("02.0.0", "made by another version of this app", "OUTPUT_OTHER_VERSION", "OUTPUT_OTHER_VERSION"),
        )
        for version, handoff_message, doctor_code, bundle_code in cases:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "handoff"
                run_as(version, output)
                with self.assertRaisesRegex(StandaloneHandoffError, handoff_message):
                    validate_standalone_handoff(output)
                with self.assertRaises(DoctorError) as caught:
                    doctor_run_output(output)
                self.assertEqual(caught.exception.code, doctor_code)
                with self.assertRaises(SupportBundleError) as caught_bundle:
                    build_support_bundle(output, root / "support.zip")
                self.assertEqual(caught_bundle.exception.code, bundle_code)


if __name__ == "__main__":
    unittest.main()
