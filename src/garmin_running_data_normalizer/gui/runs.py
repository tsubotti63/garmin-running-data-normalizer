"""Run one GUI Run-All at a time in a child process (internal).

The child is started from an argument list without a shell, in its own process
group, with its standard error discarded because it may contain paths. Only
validated progress events, results, and error codes from its standard output
reach the page. Cancellation sends SIGINT on POSIX or CTRL_BREAK_EVENT on
Windows, then terminates and finally kills the child if it does not stop.
"""
from __future__ import annotations

import errno
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any

from ..run_all import PROGRESS_STAGES, PROGRESS_STEPS
from .run_worker import FAMILY_COUNT_FIELDS

WORKER_MODULE = "garmin_running_data_normalizer.gui.run_worker"
CANCEL_GRACE_SECONDS = 10.0
KILL_GRACE_SECONDS = 5.0
MAX_MESSAGE_BYTES = 64 * 1024
MAX_TIMEZONE_LENGTH = 64
RUN_STATUSES = ("PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS")
# States whose output folder is complete: Run-All published it.
FINISHED_STATES = ("finished", "finished_after_cancel")
CODE = re.compile(r"[A-Z0-9_]{1,64}")
FAMILY_NAME = re.compile(r"[a-z0-9_]{1,40}")
FAMILY_STATUS = re.compile(r"[A-Z_]{1,40}")
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
INVALID_NAME_CHARACTERS = frozenset('<>:"/\\|?*')
# Hidden names derived from the output name are longer: Run-All's staging
# folder by 18 bytes, the write check by 22, and the Support Bundle's temporary
# file by 29. Many file systems allow 255 bytes in one name, so 200 bytes leave
# room on every system.
MAX_OUTPUT_NAME_BYTES = 200


class RunRequestError(ValueError):
    """A run request that the GUI refuses before starting a child process."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RunActiveError(RunRequestError):
    """Another run is still active."""

    def __init__(self) -> None:
        super().__init__("RUN_ACTIVE")


def absolute_path(value: Any, code: str) -> Path:
    """Return the requested absolute path unchanged apart from expanding ``~``."""
    if not isinstance(value, str) or not value or "\x00" in value:
        raise RunRequestError(code)
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise RunRequestError("PATH_NOT_ABSOLUTE")
    return path


def _utf8_size(text: str) -> int | None:
    """Return the size of ``text`` in UTF-8, or None if it holds a lone surrogate."""
    try:
        return len(text.encode("utf-8"))
    except UnicodeEncodeError:
        return None


def validate_output_name(name: Any) -> str:
    """Accept one portable folder name that cannot be taken for a staging folder."""
    size = _utf8_size(name) if isinstance(name, str) else None
    if (
        size is None
        or not 0 < size <= MAX_OUTPUT_NAME_BYTES
        or name.startswith(".")
        or name.endswith((".", " "))
        or any(character in INVALID_NAME_CHARACTERS or ord(character) < 32 for character in name)
        or name.split(".", 1)[0].rstrip(" ").upper() in WINDOWS_RESERVED_NAMES
    ):
        raise RunRequestError("OUTPUT_NAME_INVALID")
    return name


def _process_group_options() -> dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _messages(stream: IO[bytes]) -> Iterator[dict[str, Any]]:
    """Yield JSON objects, one per line; skip other lines and over-long lines."""
    while True:
        line = stream.readline(MAX_MESSAGE_BYTES + 1)
        if not line:
            return
        if not line.endswith(b"\n"):
            while line and not line.endswith(b"\n"):
                line = stream.readline(MAX_MESSAGE_BYTES + 1)
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if isinstance(message, dict):
            yield message


def _valid_progress(message: dict[str, Any]) -> dict[str, Any] | None:
    stage = message.get("stage")
    if stage not in PROGRESS_STAGES:
        return None
    progress: dict[str, Any] = {"stage": stage}
    if stage == "normalizing":
        if message.get("step") not in PROGRESS_STEPS:
            return None
        progress["step"] = message["step"]
    elif stage == "reading_fit":
        done, total = message.get("done"), message.get("total")
        if type(done) is not int or type(total) is not int or not 0 <= done <= total:
            return None
        progress.update(done=done, total=total)
    return progress


def _valid_result(message: dict[str, Any]) -> dict[str, Any] | None:
    status = message.get("status")
    exit_code = message.get("exit_code")
    file_count = message.get("generated_file_count")
    families = message.get("families")
    if (
        status not in RUN_STATUSES
        or exit_code not in (0, 3)
        or type(exit_code) is not int
        or type(file_count) is not int
        or not isinstance(families, dict)
    ):
        return None
    summary: dict[str, dict[str, Any]] = {}
    for family, details in families.items():
        if not isinstance(family, str) or not FAMILY_NAME.fullmatch(family):
            return None
        if not isinstance(details, dict):
            return None
        entry = {
            field: value
            for field, value in details.items()
            if field in FAMILY_COUNT_FIELDS and type(value) is int
        }
        family_status = details.get("status")
        if isinstance(family_status, str) and FAMILY_STATUS.fullmatch(family_status):
            entry["status"] = family_status
        summary[family] = entry
    return {
        "status": status,
        "exit_code": exit_code,
        "generated_file_count": file_count,
        "families": summary,
    }


def _staging_folders(output: Path) -> list[str]:
    """Return the names of staging folders that Run-All left for this output."""
    prefix = f".{output.name}.run-all-"
    try:
        with os.scandir(output.parent) as entries:
            return sorted(entry.name for entry in entries if entry.name.startswith(prefix))
    except OSError:
        return []


class _Run:
    def __init__(self, process: subprocess.Popen[bytes], output: Path) -> None:
        self.process = process
        self.output = output
        self.started = time.monotonic()
        self.last_progress = self.started
        self.ended: float | None = None
        self.state = "running"
        self.progress: dict[str, Any] = {}
        self.result: dict[str, Any] | None = None
        self.error_code: str | None = None
        self.cancel_requested = False
        self.reported_cancel = False
        self.staging_folders: list[str] = []
        self.follower: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return self.ended is None


class RunManager:
    """Start, follow, and cancel one Run-All child process at a time."""

    def __init__(
        self,
        *,
        command_prefix: list[str] | None = None,
        cancel_grace: float = CANCEL_GRACE_SECONDS,
        kill_grace: float = KILL_GRACE_SECONDS,
    ) -> None:
        # -P keeps the current folder out of the child's module search path.
        self._prefix = list(command_prefix or [sys.executable, "-P", "-m", WORKER_MODULE])
        self._cancel_grace = cancel_grace
        self._kill_grace = kill_grace
        self._lock = threading.Lock()
        self._run: _Run | None = None

    def active(self) -> bool:
        with self._lock:
            return self._run is not None and self._run.active

    def finished_output(self) -> Path | None:
        """Return the output folder of the last run if that run published it."""
        with self._lock:
            run = self._run
            if run is None or run.state not in FINISHED_STATES:
                return None
            return run.output

    def start(self, request: dict[str, Any]) -> dict[str, Any]:
        input_path = absolute_path(request.get("input"), "INPUT_PATH_INVALID")
        parent = absolute_path(request.get("output_parent"), "OUTPUT_PARENT_INVALID")
        name = validate_output_name(request.get("output_name"))
        timezone_name = request.get("timezone")
        if (
            not isinstance(timezone_name, str)
            or not timezone_name
            or len(timezone_name) > MAX_TIMEZONE_LENGTH
        ):
            raise RunRequestError("TIMEZONE_INVALID")
        external_safe_pack = request.get("external_safe_pack", False)
        if not isinstance(external_safe_pack, bool):
            raise RunRequestError("REQUEST_INVALID")
        # Run-All would create a missing parent; a mistyped parent must not
        # leave new folders behind.
        if not parent.is_dir():
            raise RunRequestError("OUTPUT_PARENT_NOT_FOUND")
        output = parent / name
        # Run-All checks this too. Checking it here also means that an output
        # found after a cancelled run was created by that run.
        if output.is_symlink():
            raise RunRequestError("OUTPUT_SYMLINK")
        if output.exists():
            raise RunRequestError("OUTPUT_EXISTS")
        # Run-All writes to the parent only at the end, by creating a staging
        # folder there; try the same now instead of failing after a long run.
        try:
            probe = tempfile.mkdtemp(prefix=f".{name}.write-check-", dir=parent)
        except OSError as exc:
            if exc.errno == errno.ENAMETOOLONG:
                # A shorter name fixes this; the parent may well be writable.
                raise RunRequestError("OUTPUT_NAME_INVALID") from exc
            raise RunRequestError("OUTPUT_PARENT_NOT_WRITABLE") from exc
        try:
            os.rmdir(probe)
        except OSError:
            pass  # At most an empty folder whose name starts with a dot remains.
        command = [
            *self._prefix,
            f"--input={input_path}",
            f"--output={output}",
            f"--timezone={timezone_name}",
        ]
        if external_safe_pack:
            command.append("--external-safe-pack")
        with self._lock:
            if self._run is not None and self._run.active:
                raise RunActiveError()
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                **_process_group_options(),
            )
            run = _Run(process, output)
            self._run = run
        run.follower = threading.Thread(target=self._follow, args=(run,), daemon=True)
        run.follower.start()
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            run = self._run
            if run is None:
                return {"state": "idle"}
            now = time.monotonic()
            ended = run.ended if run.ended is not None else now
            return {
                "state": run.state,
                "elapsed_seconds": round(ended - run.started, 1),
                "seconds_since_progress": (
                    round(now - run.last_progress, 1) if run.active else None
                ),
                "progress": dict(run.progress),
                "output_path": str(run.output),
                "result": json.loads(json.dumps(run.result)) if run.result else None,
                "error_code": run.error_code,
                "staging_folders": list(run.staging_folders),
            }

    def cancel(self) -> dict[str, Any]:
        with self._lock:
            run = self._run
            if run is None or not run.active or run.cancel_requested:
                run = None
            else:
                run.cancel_requested = True
                run.state = "cancelling"
        if run is not None:
            self._send_stop(run.process)
            threading.Thread(target=self._escalate, args=(run,), daemon=True).start()
        return self.status()

    def stop(self) -> None:
        """Cancel an active run and wait until its outcome is recorded."""
        with self._lock:
            run = self._run
        if run is None or not run.active:
            return
        self.cancel()
        try:
            run.process.wait(timeout=self._cancel_grace + self._kill_grace + 5)
        except subprocess.TimeoutExpired:
            pass
        # The follower thread records the outcome after it reads the end of the
        # child's output, which can come after the process has ended.
        if run.follower is not None:
            run.follower.join(timeout=5)

    @staticmethod
    def _send_stop(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGINT)
        except (OSError, ValueError):
            pass  # The escalation below stops a process that missed the signal.

    def _escalate(self, run: _Run) -> None:
        for grace, stop in (
            (self._cancel_grace, run.process.terminate),
            (self._kill_grace, run.process.kill),
        ):
            try:
                run.process.wait(timeout=grace)
                return
            except subprocess.TimeoutExpired:
                pass
            try:
                stop()
            except OSError:
                pass

    def _follow(self, run: _Run) -> None:
        stream = run.process.stdout
        assert stream is not None
        for message in _messages(stream):
            with self._lock:
                self._apply(run, message)
        returncode = run.process.wait()
        stream.close()
        self._finish(run, returncode)

    @staticmethod
    def _apply(run: _Run, message: dict[str, Any]) -> None:
        event = message.get("event")
        if event == "progress":
            progress = _valid_progress(message)
            if progress is not None:
                run.progress = progress
                run.last_progress = time.monotonic()
        elif event == "finished":
            run.result = _valid_result(message)
        elif event == "failed":
            code = message.get("code")
            if isinstance(code, str) and CODE.fullmatch(code):
                run.error_code = code
        elif event == "cancelled":
            run.reported_cancel = True

    def _finish(self, run: _Run, returncode: int) -> None:
        output_exists = run.output.is_dir()
        staging_folders = _staging_folders(run.output)
        with self._lock:
            run.ended = time.monotonic()
            if run.cancel_requested or run.reported_cancel:
                # Run-All checked that the output was absent before it started,
                # so an output now means the run finished before the stop.
                run.state = "finished_after_cancel" if output_exists else "cancelled"
            elif run.result is not None and returncode in (0, 3):
                run.state = "finished"
            else:
                run.state = "failed"
                run.error_code = run.error_code or "RUN_ALL_FAILED"
            if run.state != "finished":
                run.staging_folders = staging_folders


__all__ = [
    "CANCEL_GRACE_SECONDS",
    "FINISHED_STATES",
    "KILL_GRACE_SECONDS",
    "MAX_OUTPUT_NAME_BYTES",
    "MAX_TIMEZONE_LENGTH",
    "RunActiveError",
    "RunManager",
    "RunRequestError",
    "absolute_path",
    "validate_output_name",
]
