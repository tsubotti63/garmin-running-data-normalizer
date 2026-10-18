"""Child process that runs one GUI Run-All (internal).

The GUI server starts this module with the options of the run-all command, or
from stage B4b-1 with those of a Snapshot run: importing this Export into a
Snapshot Store, after making the store when it is new, and normalizing every
Snapshot together, or normalizing the Snapshots again without importing. It
calls the same functions as the CLI and reports on standard output, one JSON
object per line: progress events, the result of an import, then the outcome,
with the codes with which the CLI stops (``runner.stop_of``). Messages carry
only stage names, counts, statuses, and error codes, never paths, names, or
data values; the place inside the input or the store that cannot be opened
goes to the page only.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from typing import Any

from ..common.time import DEFAULT_TIMEZONE
from ..run_all import run_all
from ..runner import stop_of
from ..snapshot import initialize_store, register_snapshot, run_snapshot_all

CANCELLED_EXIT_CODE = 130
FAILED_EXIT_CODE = 2
# The ways to normalize (stage B4b-1): this Export only, importing it into the
# Snapshots and normalizing them together, or the Snapshots only.
HOWS = ("single", "snapshots", "rerun")
# The codes whose places are given to the page.
PLACE_CODES = ("INPUT_NOT_READABLE", "SNAPSHOT_STORE_NOT_READABLE")
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


def _failure(exc: Exception, phase: str) -> dict[str, Any]:
    """The message of a stop: the code with which the CLI stops for it, and
    for a place that cannot be opened, the first one and how many more. An
    error that no code describes is that of the phase, as the CLI's command
    of the phase says: Run-All, or the registration."""
    known = stop_of(exc)
    code = known[0] if known is not None else ("RUN_ALL_FAILED" if phase == "run" else "COMMAND_FAILED")
    message: dict[str, Any] = {"event": "failed", "code": code}
    # The case of a mix, which the page says in its own words (stage B4b-2):
    # a mix that Run-All found is one of the input.
    if code == "INPUT_MULTIPLE_EXPORTS":
        message["mix"] = getattr(exc, "kind", "input")
    places = getattr(exc, "places", None)
    # Where the input or the store cannot be opened is shown on the page
    # only (stage A3d-3a); "" is the input or the store itself.
    if code in PLACE_CODES and places:
        message["place"] = places[0]
        message["more"] = len(places) - 1
    return message


def _normalize(args: argparse.Namespace, phase: list[str]) -> dict[str, Any]:
    """Run the way that ``args.how`` names, with the functions of the CLI."""
    if args.how == "single":
        return run_all(
            args.input,
            args.output,
            external_safe_pack=args.external_safe_pack,
            timezone_name=args.timezone,
            progress=_report_progress,
        )
    if args.how == "snapshots":
        phase[0] = "import"
        if args.new_store_account is not None:
            _report_progress({"stage": "creating_store"})
            initialize_store(args.store, args.new_store_account)
        # The page asks for the download time only; the request and the
        # observation are given the same time (stage B0, decision 20261017-16).
        imported = register_snapshot(
            args.store,
            args.input,
            snapshot_label=args.label,
            export_requested_at=args.downloaded_at,
            export_downloaded_at=args.downloaded_at,
            export_observed_at=args.downloaded_at,
            confirm_complete=True,
            progress=_report_progress,
        )
        # The import is done even when the run then stops.
        _emit(
            {
                "event": "imported",
                "order": int(imported["logical_order"]),
                "same_content": bool(imported.get("registration_was_idempotent")),
                "snapshot_count": int(imported["snapshot_count"]),
            }
        )
    phase[0] = "run"
    return run_snapshot_all(
        args.store,
        args.output,
        external_safe_pack=args.external_safe_pack,
        timezone_name=args.timezone,
        progress=_report_progress,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="garmin_running_data_normalizer.gui.run_worker")
    parser.add_argument("--how", choices=HOWS, default="single")
    parser.add_argument("--input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--store")
    parser.add_argument("--new-store-account")
    parser.add_argument("--label")
    parser.add_argument("--downloaded-at")
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
    phase = ["run"]
    try:
        try:
            result = _normalize(args, phase)
            # The output is published now; a late cancellation must not turn
            # it into a reported cancellation.
            _ignore_stop_signals()
        except KeyboardInterrupt:
            _ignore_stop_signals()
            _emit({"event": "cancelled"})
            return CANCELLED_EXIT_CODE
        except Exception as exc:
            _emit(_failure(exc, phase[0]))
            return FAILED_EXIT_CODE
        totals = result["warning_totals"]
        _emit(
            {
                "event": "finished",
                "status": result["status"],
                "exit_code": int(result["exit_code"]),
                "generated_file_count": len(result["generated_files"]),
                "families": _family_summary(result["family_results"]),
                # The total of the warnings, and those that belong to no
                # family, as the CLI prints them (stage A5a).
                "warning_count": int(totals["total"]),
                "other_warning_counts": {
                    name: int(count) for name, count in totals["other"].items()
                },
                # Each warning by its code, names, and count, without its
                # words, for the page's lists (stage B2c).
                "warning_items": result["warning_items"],
                # The Snapshots that a Snapshot run used (stage B4b-1).
                **(
                    {"snapshot_count": int(result["snapshot_count"])}
                    if "snapshot_count" in result
                    else {}
                ),
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
