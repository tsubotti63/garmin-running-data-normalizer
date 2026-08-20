"""Versioned, read-only diagnostics for completed Garmin Run-All evidence."""

from .completeness import build_source_completeness
from .doctor import DoctorError, doctor_input, doctor_run_output
from .run_quality import build_run_quality
from .support_bundle import SupportBundleError, build_support_bundle

__all__ = [
    "DoctorError",
    "SupportBundleError",
    "build_run_quality",
    "build_source_completeness",
    "build_support_bundle",
    "doctor_input",
    "doctor_run_output",
]
