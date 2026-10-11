"""Actions on the output of the last finished GUI run (internal).

The server passes the output folder that its own run published; the page never
names a path here. Checks and the Support Bundle call the same functions as
the CLI and report codes and counts only. Opening shows the folder or opens
START_HERE.md with the operating system's default application, from an
argument list with an absolute path and without a shell.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..diagnostics.doctor import DoctorError, doctor_run_output
from ..diagnostics.support_bundle import SupportBundleError, build_support_bundle
from ..standalone import StandaloneHandoffError, validate_standalone_handoff

OPEN_TARGETS = ("folder", "start_here")
MACOS_OPEN = "/usr/bin/open"
# Windows marks junctions as reparse points, and lstat reports a junction as a
# folder.
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


class OutputActionError(ValueError):
    """An output action that failed, reported to the page as a code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def check_output(output: Path) -> dict[str, Any]:
    """Run handoff validation and the post-run Doctor; return codes and counts."""
    try:
        handoff = validate_standalone_handoff(output)
        report = doctor_run_output(output)
    except StandaloneHandoffError as exc:
        raise OutputActionError("HANDOFF_INVALID") from exc
    except DoctorError as exc:
        raise OutputActionError(exc.code) from exc
    except OSError as exc:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE") from exc
    if (
        report["completion_state"] != "COMPLETED"
        or report["diagnostic_contract_availability"] != "CURRENT"
    ):
        # The run wrote a completed output with current diagnostics, so the
        # folder changed after the run.
        raise OutputActionError("OUTPUT_CHANGED")
    return {
        "handoff": {
            "status": handoff["status"],
            "dataset_count": handoff["dataset_count"],
            "relationship_count": handoff["explicit_relationship_count"],
            "warning_count": handoff["warning_count"],
        },
        "doctor": {
            "product_status": report["product_status"],
            "usability_scope": report["usability_scope"],
            "next_action_id": report["doctor_next_action_id"],
            "support_bundle_suggested": bool(report["support_bundle_suggested"]),
            "warning_codes": sorted({finding["code"] for finding in report["findings"]}),
        },
    }


def support_bundle_path(output: Path) -> Path:
    """Place the bundle next to the output: inside, it would contradict the manifest."""
    return output.parent / f"{output.name}-support-bundle.zip"


def make_support_bundle(output: Path) -> dict[str, Any]:
    """Build the Support Bundle next to the output; never replace an existing file."""
    destination = support_bundle_path(output)
    if destination.is_symlink() or destination.exists():
        raise OutputActionError("SUPPORT_BUNDLE_EXISTS")
    try:
        result = build_support_bundle(output, destination)
    except SupportBundleError as exc:
        raise OutputActionError(exc.code) from exc
    except OSError as exc:
        raise OutputActionError("SUPPORT_BUNDLE_NOT_WRITTEN") from exc
    return {
        "path": str(destination),
        "member_count": int(result["member_count"]),
        "human_review_required": bool(result["human_review_required"]),
    }


def _is_plain(path: Path, kind: Callable[[int], bool]) -> bool:
    """Return whether ``path`` itself, not a link or junction, is of ``kind``."""
    info = os.lstat(path)
    return kind(info.st_mode) and not getattr(info, "st_file_attributes", 0) & _REPARSE_POINT


def _checked_target(output: Path, target: Any) -> Path:
    """Return the path to open after checking that nothing replaced it with a link."""
    if target not in OPEN_TARGETS:
        raise OutputActionError("REQUEST_INVALID")
    try:
        if not _is_plain(output, stat.S_ISDIR):
            raise OutputActionError("OUTPUT_NOT_AVAILABLE")
        if target == "folder":
            return output
        start_here = output / "START_HERE.md"
        if not _is_plain(start_here, stat.S_ISREG):
            raise OutputActionError("OUTPUT_NOT_AVAILABLE")
        return start_here
    except OSError as exc:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE") from exc


def open_command(path: Path, *, folder: bool, platform: str) -> list[str] | None:
    """Return the argument list that opens ``path``, or None for os.startfile."""
    if platform == "win32":
        return None
    if platform == "darwin":
        # "open -R" reveals the folder in Finder, so a name such as x.app is
        # never launched as an application.
        return [MACOS_OPEN, "-R", str(path)] if folder else [MACOS_OPEN, str(path)]
    opener = shutil.which("xdg-open")
    if opener is None:
        raise OutputActionError("OPEN_NOT_AVAILABLE")
    return [opener, str(path)]


def _launch(path: Path, *, folder: bool) -> None:
    command = open_command(path, folder=folder, platform=sys.platform)
    if command is None:
        # "explore" shows a folder as a folder; files open with their default app.
        os.startfile(str(path), "explore" if folder else "open")  # type: ignore[attr-defined]
        return
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    # Collect the opener when it exits; the page is told only that it started.
    threading.Thread(target=process.wait, daemon=True).start()


def open_output(output: Path, target: Any) -> None:
    """Show the output folder or open its START_HERE.md."""
    path = _checked_target(output, target)
    if not path.is_absolute():
        raise OutputActionError("OUTPUT_NOT_AVAILABLE")
    try:
        _launch(path, folder=target == "folder")
    except OSError as exc:
        raise OutputActionError("OPEN_FAILED") from exc


__all__ = [
    "OPEN_TARGETS",
    "OutputActionError",
    "check_output",
    "make_support_bundle",
    "open_command",
    "open_output",
    "support_bundle_path",
]
