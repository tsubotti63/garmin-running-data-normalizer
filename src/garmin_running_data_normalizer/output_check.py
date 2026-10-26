"""The check of a finished output that the GUI and the view page share (stage G1).

The GUI checks an output before it offers actions on it, and the view page
checks one before it reads it. Both call ``checked_output``, so that one
answer of the checks gives one code in both: with the rule in two places, one
could be changed without the other. The module belongs to neither of them,
because the view page's numbers are also for the CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# The diagnostics package is imported before standalone: the other order meets
# a circular import when this module is the first that is imported.
from .diagnostics.doctor import DoctorError, doctor_run_output
from .standalone import OtherVersionError, StandaloneHandoffError, validate_standalone_handoff


class OutputActionError(ValueError):
    """An output action that failed, reported to the page as a code, and for
    an output that another version made, that version (stage B5b)."""

    def __init__(self, code: str, version: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.version = version


def checked_output(output: Path) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Run handoff validation and the post-run Doctor, as the CLI runs them;
    return their answers, and whether the output is one of 1.3, which has no
    diagnostics. A check that fails raises ``OutputActionError`` with its
    code."""
    try:
        handoff = validate_standalone_handoff(output)
        report = doctor_run_output(output)
    except OtherVersionError as exc:
        # Another version made the output (stage B5b).
        raise OutputActionError("OUTPUT_OTHER_VERSION", exc.version) from exc
    except StandaloneHandoffError as exc:
        raise OutputActionError("HANDOFF_INVALID") from exc
    except DoctorError as exc:
        raise OutputActionError(exc.code) from exc
    except OSError as exc:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE") from exc
    # An output of 1.3 has no diagnostics, and is told so (stage B5b); a run
    # of this version wrote a completed output with its diagnostics, so any
    # other answer means that the folder changed after the run.
    legacy = report["diagnostic_contract_availability"] == "LEGACY_NOT_AVAILABLE"
    if report["completion_state"] != "COMPLETED" or (
        report["diagnostic_contract_availability"] != "CURRENT" and not legacy
    ):
        raise OutputActionError("OUTPUT_CHANGED")
    return handoff, report, legacy


__all__ = ["OutputActionError", "checked_output"]
