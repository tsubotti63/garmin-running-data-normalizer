"""Child process that runs one GUI Run-All (internal).

The GUI server starts this module with the options of the run-all command. It
calls the same run_all function as the CLI and reports on standard output, one
JSON object per line: progress events, then the outcome. Messages carry only
stage names, counts, statuses, and error codes, never paths or data values.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from typing import Any

from ..common.time import DEFAULT_TIMEZONE
from ..run_all import RunAllError, run_all

CANCELLED_EXIT_CODE = 130
FAILED_EXIT_CODE = 2
FAMILY_COUNT_FIELDS = (
    "detected_asset_count",
    "processed_asset_count",
    "skipped_asset_count",
    "record_count",
    "warning_count",
    "error_count",
    "review_item_count",
    "review_required_count",
)


class ParentGone(BaseException):
    """Stops the run when the server no longer reads; passes through Run-All."""


def _emit(message: dict[str, Any]) -> None:
    try:
        sys.stdout.write(json.dumps(message, sort_keys=True) + "\n")
        sys.stdout.flush()
    except (OSError, ValueError) as exc:
        raise ParentGone from exc


def _report_progress(event: dict[str, Any]) -> None:
    _emit({"event": "progress", **event})


def _stop_with_keyboard_interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def _ignore_stop_signals() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.SIG_IGN)


def _family_summary(family_results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for family, details in sorted(family_results.items()):
        summary[family] = {
            field: int(details[field])
            for field in FAMILY_COUNT_FIELDS
            if isinstance(details.get(field), int)
        }
        summary[family]["status"] = str(details.get("status", ""))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="garmin_running_data_normalizer.gui.run_worker")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--external-safe-pack", action="store_true")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    args = parser.parse_args(argv)
    # A child of a process that ignores SIGINT would inherit that; install the
    # handler that raises KeyboardInterrupt explicitly.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    if hasattr(signal, "SIGBREAK"):
        # CTRL_BREAK_EVENT is the only signal that reaches a child started in a
        # new process group on Windows; without a handler it ends the process
        # without the cleanup that KeyboardInterrupt runs.
        signal.signal(signal.SIGBREAK, _stop_with_keyboard_interrupt)
    try:
        try:
            result = run_all(
                args.input,
                args.output,
                external_safe_pack=args.external_safe_pack,
                timezone_name=args.timezone,
                progress=_report_progress,
            )
            # The output is published now; a late cancellation must not turn
            # it into a reported cancellation.
            _ignore_stop_signals()
        except KeyboardInterrupt:
            _ignore_stop_signals()
            _emit({"event": "cancelled"})
            return CANCELLED_EXIT_CODE
        except RunAllError as exc:
            _emit({"event": "failed", "code": exc.code})
            return FAILED_EXIT_CODE
        except Exception:
            _emit({"event": "failed", "code": "RUN_ALL_FAILED"})
            return FAILED_EXIT_CODE
        _emit(
            {
                "event": "finished",
                "status": result["status"],
                "exit_code": int(result["exit_code"]),
                "generated_file_count": len(result["generated_files"]),
                "families": _family_summary(result["family_results"]),
            }
        )
        return int(result["exit_code"])
    except ParentGone:
        # Point standard output at the null device, so that the final flush at
        # exit cannot fail again and change the exit code.
        null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null, sys.stdout.fileno())
        os.close(null)
        return FAILED_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
