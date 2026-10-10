"""Stand-in for the GUI Run-All child process, for run manager tests.

It takes the worker's options and a --mode, uses the standard library only,
and behaves in one fixed way per mode so that cancellation can be tested
without depending on how fast Run-All finishes.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

CANCELLED_EXIT_CODE = 130


def emit(message: object) -> None:
    sys.stdout.write((message if isinstance(message, str) else json.dumps(message)) + "\n")
    sys.stdout.flush()


def raise_keyboard_interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def follow_stop_signals() -> None:
    signal.signal(signal.SIGINT, signal.default_int_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, raise_keyboard_interrupt)


def ignore_stop_signals() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.SIG_IGN)


def wait_forever() -> None:
    while True:
        time.sleep(0.05)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--output", required=True)
    args, _ = parser.parse_known_args()
    output = Path(args.output)
    progress = {"event": "progress", "stage": "normalizing", "step": "activities"}

    if args.mode in {"wait", "publish-then-wait"}:
        follow_stop_signals()
        if args.mode == "publish-then-wait":
            output.mkdir()
        emit(progress)
        try:
            wait_forever()
        except KeyboardInterrupt:
            ignore_stop_signals()
            emit({"event": "cancelled"})
            return CANCELLED_EXIT_CODE
    if args.mode in {"ignore", "stage-then-ignore"}:
        ignore_stop_signals()
        if args.mode == "stage-then-ignore":
            (output.parent / f".{output.name}.run-all-stub").mkdir()
        emit(progress)
        wait_forever()
    if args.mode == "noise":
        emit("not json")
        emit("x" * 70_000)
        emit(["array"])
        emit({"event": "progress", "stage": "/path/to/private"})
        emit({"event": "progress", "stage": "reading_fit", "done": 5, "total": 3})
        emit({"event": "progress", "stage": "reading_fit", "done": True, "total": 3})
        emit({**progress, "extra": "/path/to/private"})
        emit({"event": "finished", "status": "PASS", "exit_code": 0, "families": "/path/to/private"})
        emit({"event": "failed", "code": "bad code /path/to/private"})
        sys.stderr.write("Traceback (most recent call last): /path/to/private\n")
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
