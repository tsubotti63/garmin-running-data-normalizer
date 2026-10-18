"""Actions on the output of the last finished GUI run (internal).

The server passes the output folder that its own run published; the page never
names a path here, except the folder that the person chose for the Support
Bundle (stage B5a), which goes through the CLI's checks of its place. Checks
and the Support Bundle call the same functions as the CLI and report codes
and counts only. Opening shows the folder or opens START_HERE.md with the
operating system's default application, and shows the Support Bundle that
this server made or the External-safe Pack of the output in their folder,
from an argument list with an absolute path and without a shell. From stage
B5b, an output that an earlier run made, or one that the person chose, is
checked and bundled the same way, and the summary of the output before a run
gives the counts that the page compares the run with.
"""
from __future__ import annotations

import json
import os
import re
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
from ..standalone import VERSION_FORM, OtherVersionError, StandaloneHandoffError, validate_standalone_handoff

OPEN_TARGETS = ("folder", "start_here", "bundle", "safe_pack")
# What is read from the summary of an earlier output (stage B5b).
MAX_SUMMARY_BYTES = 8 * 1024 * 1024
FAMILY_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
TIMEZONE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_+\-]{0,63}(?:/[A-Za-z0-9_+\-]{1,64}){0,3}")
# The External-safe Pack, inside the output (stage B5a).
SAFE_PACK = Path("analysis") / "external_safe_handoff.zip"
MACOS_OPEN = "/usr/bin/open"
# Windows marks junctions as reparse points, and lstat reports a junction as a
# folder.
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


class OutputActionError(ValueError):
    """An output action that failed, reported to the page as a code, and for
    an output that another version made, that version (stage B5b)."""

    def __init__(self, code: str, version: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.version = version


def _made_by(exc: BaseException | None) -> str | None:
    """The version that made an output that this version cannot check, from
    the error that told it, through the errors that it caused."""
    while exc is not None:
        if isinstance(exc, OtherVersionError):
            return exc.version
        exc = exc.__cause__
    return None


def check_output(output: Path) -> dict[str, Any]:
    """Run handoff validation and the post-run Doctor; return codes and counts."""
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
    version = report.get("product_version")
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
            "legacy": legacy,
            "product_version": version if isinstance(version, str) and VERSION_FORM.fullmatch(version) else None,
        },
    }


def earlier_outputs(remembered: list[str], exclude: Path | None) -> list[Path]:
    """The outputs that the settings remember, newest first, that are there as
    plain folders, except ``exclude``, the output of this launch's last run
    (stage B5b). One that is not found is left out, and stays remembered."""
    found: list[Path] = []
    for place in remembered:
        path = Path(place)
        if exclude is not None and path == exclude:
            continue
        try:
            if _is_plain(path, stat.S_ISDIR):
                found.append(path)
        except OSError:
            continue
    return found


def output_summary(output: Path) -> dict[str, Any] | None:
    """What the page compares a run with (stage B5b): the count of the records
    of each family, whether the output is of Snapshots, its version, and its
    timezone, from its run_summary.json; None when it cannot be read. Nothing
    else of the output is read."""
    path = output / "run_summary.json"
    try:
        if not _is_plain(path, stat.S_ISREG) or path.stat().st_size > MAX_SUMMARY_BYTES:
            return None
        summary = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(summary, dict) or not isinstance(summary.get("family_results"), dict):
        return None
    families: dict[str, int] = {}
    for family, details in summary["family_results"].items():
        count = details.get("record_count") if isinstance(details, dict) else None
        if not isinstance(family, str) or not FAMILY_NAME.fullmatch(family):
            return None
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            return None
        families[family] = count
    version = summary.get("product_version")
    timezone = summary.get("local_timezone")
    run_all_version = summary.get("run_all_version")
    return {
        "name": output.name,
        "families": families,
        "snapshots": summary.get("snapshot_lifecycle") is not None,
        "version": version if isinstance(version, str) and VERSION_FORM.fullmatch(version) else None,
        "run_all_version": run_all_version if isinstance(run_all_version, int) and not isinstance(run_all_version, bool) else None,
        "timezone": timezone if isinstance(timezone, str) and TIMEZONE_NAME.fullmatch(timezone) else None,
    }


def support_bundle_path(output: Path, folder: Path | None = None) -> Path:
    """Place the bundle next to the output by default, or in the folder that
    the person chose (stage B5a): never inside, where it would contradict
    the manifest, which ``build_support_bundle`` refuses."""
    return (output.parent if folder is None else folder) / f"{output.name}-support-bundle.zip"


def make_support_bundle(output: Path, folder: Path | None = None) -> dict[str, Any]:
    """Build the Support Bundle next to the output, or in a chosen folder.
    ``build_support_bundle`` checks its place as the CLI does: a folder that
    is there, outside the output, and nothing there to replace (stages A5b-2
    and B5a)."""
    destination = support_bundle_path(output, folder)
    try:
        result = build_support_bundle(output, destination)
    except SupportBundleError as exc:
        raise OutputActionError(exc.code, _made_by(exc)) from exc
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


def _checked_target(output: Path, target: Any, bundle: Path | None = None) -> Path:
    """Return the path to open after checking that nothing replaced it with a link."""
    if target not in OPEN_TARGETS:
        raise OutputActionError("REQUEST_INVALID")
    try:
        if target == "bundle":
            # Only the Support Bundle that this server made.
            if bundle is None or not _is_plain(bundle, stat.S_ISREG):
                raise OutputActionError("OUTPUT_NOT_AVAILABLE")
            return bundle
        if not _is_plain(output, stat.S_ISDIR):
            raise OutputActionError("OUTPUT_NOT_AVAILABLE")
        if target == "folder":
            return output
        place = output / (SAFE_PACK if target == "safe_pack" else Path("START_HERE.md"))
        if not _is_plain(place.parent, stat.S_ISDIR) or not _is_plain(place, stat.S_ISREG):
            raise OutputActionError("OUTPUT_NOT_AVAILABLE")
        return place
    except OSError as exc:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE") from exc


def _windows_explorer() -> str:
    return str(Path(os.environ.get("SystemRoot") or r"C:\Windows") / "explorer.exe")


def open_command(path: Path, *, folder: bool, platform: str, reveal: bool = False) -> list[str] | str | None:
    """Return the argument list that opens ``path``, or None for os.startfile.
    ``reveal`` shows a file in its folder (stage B5a): selected in Finder or
    File Explorer, and elsewhere by opening the folder that holds it."""
    if platform == "win32":
        if not reveal:
            return None
        # File Explorer reads its own command line and takes /select only
        # with the place alone in quotes, which a list does not give a place
        # with a space: one command line, still without a shell. Windows
        # names hold no quotes, so the place cannot leave its own.
        explorer, place = _windows_explorer(), str(path)
        if '"' in explorer or '"' in place:
            raise OutputActionError("OPEN_FAILED")
        return f'"{explorer}" /select,"{place}"'
    if platform == "darwin":
        # "open -R" reveals the folder in Finder, so a name such as x.app is
        # never launched as an application.
        return [MACOS_OPEN, "-R", str(path)] if folder or reveal else [MACOS_OPEN, str(path)]
    opener = shutil.which("xdg-open")
    if opener is None:
        raise OutputActionError("OPEN_NOT_AVAILABLE")
    return [opener, str(path.parent if reveal else path)]


def _launch(path: Path, *, folder: bool, reveal: bool = False) -> None:
    command = open_command(path, folder=folder, platform=sys.platform, reveal=reveal)
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


def open_output(output: Path, target: Any, bundle: Path | None = None) -> None:
    """Show the output folder, open its START_HERE.md, or show the Support
    Bundle that this server made (``bundle``) or the External-safe Pack of
    the output in their folder (stage B5a)."""
    path = _checked_target(output, target, bundle)
    if not path.is_absolute():
        raise OutputActionError("OUTPUT_NOT_AVAILABLE")
    try:
        _launch(path, folder=target == "folder", reveal=target in ("bundle", "safe_pack"))
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
