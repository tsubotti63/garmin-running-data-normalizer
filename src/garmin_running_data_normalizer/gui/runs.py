"""Run one GUI Run-All at a time in a child process (internal).

The child is started from an argument list without a shell, in its own process
group, with its standard error discarded because it may contain paths. Only
validated progress events, results, and error codes from its standard output
reach the page. Cancellation sends SIGINT on POSIX or CTRL_BREAK_EVENT on
Windows, then terminates and finally kills the child if it does not stop.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any

from ..diagnostics.contracts import SAFE_WARNING_CODES
from ..intake.source import place_can_be_shown
from ..output_location import (
    MAX_OUTPUT_NAME_BYTES,
    WINDOWS_MAX_FILE_PATH,
    WINDOWS_MAX_FOLDER_PATH,
    OutputLocationError,
    check_output_location,
    valid_output_name,
)
from ..output_location import long_paths_enabled as _long_paths_enabled
from ..output_location import windows_paths_too_long as _windows_paths_too_long
from ..output_location import write_error_code
from ..run_all import OTHER_WARNING_FIELDS, OUTPUT_PATHS, PROGRESS_STAGES, PROGRESS_STEPS
from ..snapshot.lifecycle import SNAPSHOT_PROGRESS_STAGES
from ..snapshot.store import (
    SnapshotStoreError,
    cancel_notices,
    check_input_apart,
    check_label_free,
    check_new_store_place,
    load_manifests,
    load_store,
    lock_exists,
    new_snapshot_label,
    registration_times,
)
from ..stops import MIX_KINDS
from .places import default_folder, default_store, make_default_folder
from .run_worker import FAMILY_COUNT_FIELDS, HOWS

WORKER_MODULE = "garmin_running_data_normalizer.gui.run_worker"
CANCEL_GRACE_SECONDS = 10.0
KILL_GRACE_SECONDS = 5.0
MAX_MESSAGE_BYTES = 64 * 1024
MAX_TIMEZONE_LENGTH = 64
# The stages of every run: those of a Snapshot run, then those of Run-All
# (stage B4b-1).
RUN_STAGES = (*SNAPSHOT_PROGRESS_STAGES, *PROGRESS_STAGES)
RUN_STATUSES = ("PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS")
# States whose output folder is complete: Run-All published it.
FINISHED_STATES = ("finished", "finished_after_cancel")
CODE = re.compile(r"[A-Z0-9_]{1,64}")
FAMILY_NAME = re.compile(r"[a-z0-9_]{1,40}")
FAMILY_STATUS = re.compile(r"[A-Z_]{1,40}")


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


def windows_paths_too_long(parent: str, name: str) -> bool:
    """Return whether Run-All's deepest paths for this output exceed MAX_PATH."""
    return _windows_paths_too_long(parent, name, OUTPUT_PATHS)


def output_path_too_long(parent: Path, name: str) -> bool:
    """Return whether this output cannot be written on this Windows system."""
    if os.name != "nt" or _long_paths_enabled():
        return False
    return windows_paths_too_long(str(parent), name)


def validate_output_name(name: Any) -> str:
    """Accept one portable folder name that cannot be taken for a staging
    folder, by the rule that the CLI takes too (stage A5a)."""
    if not valid_output_name(name):
        raise RunRequestError("OUTPUT_NAME_INVALID")
    return name


def _valid_detail(message: dict[str, Any]) -> dict[str, Any] | None:
    """Return where the input cannot be opened, as the worker named it, or
    None (stage A3d-3a). It goes to the page only, never to a log. A name
    that cannot be shown goes as None, as the check gives it (stage B3c).
    For a place of the Snapshot Store, ``store`` is true, and "" is the
    store's folder itself (stage B4b-1)."""
    place = message.get("place")
    more = message.get("more")
    if not isinstance(place, str) or not isinstance(more, int) or isinstance(more, bool) or more < 0:
        return None
    detail: dict[str, Any] = {"place": place if place_can_be_shown(place) else None, "more": more}
    if message.get("code") == "SNAPSHOT_STORE_NOT_READABLE":
        detail["store"] = True
    return detail


def _valid_mix(message: dict[str, Any]) -> dict[str, Any] | None:
    """The case of a mix that the child named, one of MIX_KINDS (stage
    B4b-2), or None."""
    mix = message.get("mix")
    if message.get("code") == "INPUT_MULTIPLE_EXPORTS" and isinstance(mix, str) and mix in MIX_KINDS:
        return {"mix": mix}
    return None


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


def _counted(message: dict[str, Any]) -> dict[str, int] | None:
    done, total = message.get("done"), message.get("total")
    if type(done) is not int or type(total) is not int or not 0 <= done <= total:
        return None
    return {"done": done, "total": total}


def _valid_progress(message: dict[str, Any]) -> dict[str, Any] | None:
    """A progress event as the page may have it: a stage of RUN_STAGES, with
    its step and its numbers only."""
    stage = message.get("stage")
    if stage not in RUN_STAGES:
        return None
    progress: dict[str, Any] = {"stage": stage}
    if stage == "normalizing":
        if message.get("step") not in PROGRESS_STEPS:
            return None
        progress["step"] = message["step"]
    elif stage in ("reading_fit", "reading_export", "importing"):
        counts = _counted(message)
        if counts is None:
            return None
        progress.update(counts)
    elif stage == "building_snapshots":
        if not _count(message.get("snapshots")):
            return None
        progress["snapshots"] = message["snapshots"]
    return progress


def _valid_import(message: dict[str, Any]) -> dict[str, Any] | None:
    """The result of an import (stage B4b-1): the place of the Snapshot in
    the order of the Exports, whether the store held the same Export, and the
    number of Snapshots."""
    order, same, count = message.get("order"), message.get("same_content"), message.get("snapshot_count")
    if type(order) is not int or type(count) is not int or not 1 <= order <= count or type(same) is not bool:
        return None
    return {"order": order, "same_content": same, "snapshot_count": count}


def _count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _valid_result(message: dict[str, Any]) -> dict[str, Any] | None:
    status = message.get("status")
    exit_code = message.get("exit_code")
    file_count = message.get("generated_file_count")
    families = message.get("families")
    warning_count = message.get("warning_count")
    other_warnings = message.get("other_warning_counts")
    if (
        status not in RUN_STATUSES
        or exit_code not in (0, 3)
        or type(exit_code) is not int
        or type(file_count) is not int
        or not isinstance(families, dict)
        or not _count(warning_count)
        or not isinstance(other_warnings, dict)
        or set(other_warnings) != {name for name, _field in OTHER_WARNING_FIELDS}
        or not all(_count(value) for value in other_warnings.values())
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
    snapshot_count = message.get("snapshot_count")
    return {
        "status": status,
        "exit_code": exit_code,
        "generated_file_count": file_count,
        "families": summary,
        "warning_count": warning_count,
        "other_warning_counts": {name: other_warnings[name] for name, _field in OTHER_WARNING_FIELDS},
        "warning_items": _warning_items(message.get("warning_items")),
        # The Snapshots that a Snapshot run used (stage B4b-1).
        **({"snapshot_count": snapshot_count} if _count(snapshot_count) else {}),
    }


def _name(value: Any) -> bool:
    return value is None or (isinstance(value, str) and FAMILY_NAME.fullmatch(value) is not None)


def _warning_items(items: Any) -> list[dict[str, Any]]:
    """The warnings of a finished run one by one: a registered code, the
    names of the family and the dataset, and a count (stage B2c). An item
    that is not so is left out alone, never the result: the run finished,
    and its totals come from their own counts."""
    if not isinstance(items, list):
        return []
    kept = []
    for item in items:
        if not isinstance(item, dict):
            continue
        code, family, dataset, count = (item.get(key) for key in ("code", "family", "dataset", "count"))
        if code in SAFE_WARNING_CODES and _name(family) and _name(dataset) and (count is None or _count(count)):
            kept.append({"code": code, "family": family, "dataset": dataset, "count": count})
    return kept


def _staging_folders(output: Path) -> list[str]:
    """Return the names of staging folders that Run-All left for this output."""
    prefix = f".{output.name}.run-all-"
    try:
        with os.scandir(output.parent) as entries:
            return sorted(entry.name for entry in entries if entry.name.startswith(prefix))
    except OSError:
        return []


class _Run:
    def __init__(
        self, process: subprocess.Popen[bytes], output: Path, staging_before: set[str]
    ) -> None:
        self.process = process
        self.output = output
        # The staging folders for this output that were there before the run
        # started, which it did not leave (stage A5c).
        self.staging_before = staging_before
        self.started = time.monotonic()
        self.last_progress = self.started
        self.ended: float | None = None
        self.state = "running"
        self.progress: dict[str, Any] = {}
        # The seconds spent in each stage of Run-All, for the steps table of
        # the page (stage B1a): the stage now, since when, and the totals of
        # the stages that it left.
        self.stage: str | None = None
        self.stage_since = self.started
        self.stage_totals: dict[str, float] = {}
        self.result: dict[str, Any] | None = None
        # The way of the run and the result of its import (stage B4b-1).
        self.how = "single"
        self.imported: dict[str, Any] | None = None
        # The store of an import, whether it had a lock file before, and the
        # notices of the store that a cancelled import left (stage B4b-2).
        self.store: Path | None = None
        self.lock_before = False
        self.store_notices: list[str] = []
        self.error_code: str | None = None
        self.error_detail: dict[str, Any] | None = None
        self.cancel_requested = False
        self.reported_cancel = False
        self.staging_folders: list[str] = []
        self.follower: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return self.ended is None

    def enter_stage(self, stage: str, now: float) -> None:
        if stage == self.stage:
            return
        if self.stage is not None:
            self.stage_totals[self.stage] = self.stage_totals.get(self.stage, 0.0) + now - self.stage_since
        self.stage = stage
        self.stage_since = now

    def stage_seconds(self, now: float) -> dict[str, float]:
        """Return the seconds of each stage so far: names from PROGRESS_STAGES
        and numbers only. The stage that a run ended in counts until its end."""
        totals = dict(self.stage_totals)
        if self.stage is not None:
            end = self.ended if self.ended is not None else now
            totals[self.stage] = totals.get(self.stage, 0.0) + end - self.stage_since
        return {stage: round(totals[stage], 1) for stage in RUN_STAGES if stage in totals}


def _store_request_error(exc: SnapshotStoreError) -> RunRequestError:
    return RunRequestError(exc.code)


def _snapshot_request(
    how: str, request: dict[str, Any], input_path: Path | None
) -> tuple[Path, list[str], bool, str | None]:
    """Check the fields of a Snapshot run before its child starts, with the
    functions that the registration uses, so that a rule is written once
    (stage B4b-1). Return the store, the child's options, whether the store
    is new, and the label of an import. An existing store is read once no
    run is active (``_check_store``), and the place of a new one once the
    default place is there (``_check_new_store``)."""
    store = absolute_path(request.get("store"), "PATH_INVALID")
    new_store = request.get("new_store", False)
    if not isinstance(new_store, bool) or (new_store and how != "snapshots"):
        raise RunRequestError("REQUEST_INVALID")
    options = [f"--how={how}", f"--store={store}"]
    label: str | None = None
    if input_path is not None:
        try:
            label = new_snapshot_label(request.get("label"))
            downloaded = request.get("downloaded_at")
            # The page asks for the download time only (decision 20261017-16).
            _requested, downloaded_at, _observed = registration_times(downloaded, downloaded, downloaded)
            check_input_apart(input_path.resolve(), store.resolve())
        except SnapshotStoreError as exc:
            raise _store_request_error(exc) from exc
        options += [f"--label={label}", f"--downloaded-at={downloaded_at}"]
    return store, options, new_store, label


def _check_store(store: Path, label: str | None) -> None:
    """Read an existing store for a Snapshot run, once no run is active,
    which could be writing in it: an import needs a name that the store does
    not have, and normalizing again needs a Snapshot."""
    try:
        root, _metadata = load_store(store)
        manifests = load_manifests(root)
        # The page and the server refuse a name that the store has before
        # the Export is read; the registration reads it first and takes the
        # same Export again under any name (stage A3a), so with another name
        # the outcome is the same.
        if label is not None:
            check_label_free(manifests, label)
        elif not manifests:
            raise RunRequestError("SNAPSHOT_STORE_EMPTY")
    except SnapshotStoreError as exc:
        raise _store_request_error(exc) from exc


def _check_new_store(store: Path) -> None:
    try:
        check_new_store_place(store)
    except SnapshotStoreError as exc:
        raise _store_request_error(exc) from exc


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
        # The way to normalize (stage B4b-1); "single" until then.
        how = request.get("how", "single")
        if how not in HOWS:
            raise RunRequestError("REQUEST_INVALID")
        input_path = absolute_path(request.get("input"), "INPUT_PATH_INVALID") if how != "rerun" else None
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
        store: Path | None = None
        snapshot_options: list[str] = []
        new_store = False
        label: str | None = None
        if how != "single":
            store, snapshot_options, new_store, label = _snapshot_request(how, request, input_path)
        # The default place is made here, once the request is valid and no
        # run is active (stage B4a): for the output, and for a new store in
        # it (stage B4b-1); any other missing parent is refused below, by the
        # check that Run-All makes too, and neither creates folders for a
        # mistyped parent (stage A5a).
        if self.active():
            raise RunActiveError()
        if store is not None and not new_store:
            _check_store(store, label)
        try:
            make_default_folder(parent)
        except OSError as exc:
            raise RunRequestError(write_error_code(exc) or "OUTPUT_PARENT_NOT_WRITABLE") from exc
        if store is not None and new_store:
            if store == default_store():
                try:
                    make_default_folder(default_folder())
                except OSError as exc:
                    raise RunRequestError("SNAPSHOT_STORE_NOT_WRITABLE") from exc
            _check_new_store(store)
            # The account boundary of a new store is the server's own token,
            # never one that the page sends; nobody sees it.
            snapshot_options.append(f"--new-store-account=gui-{secrets.token_hex(12)}")
        output = parent / name
        # Run-All checks this too. Checking it here also means that an output
        # found after a cancelled run was created by that run.
        if output.is_symlink():
            raise RunRequestError("OUTPUT_SYMLINK")
        if output.exists():
            raise RunRequestError("OUTPUT_EXISTS")
        # Run-All writes to the parent only at the end, by creating a staging
        # folder there; try the same now instead of failing after a long run.
        # Run-All makes the same check (stage A3d-3a).
        try:
            check_output_location(output, output_path_too_long)
        except OutputLocationError as exc:
            raise RunRequestError(exc.code) from exc
        # What the store holds before an import, to tell after a cancellation
        # of what it left, as the CLI does (stage B4b-2).
        lock_before = how == "snapshots" and store is not None and lock_exists(store)
        command = [
            *self._prefix,
            *([f"--input={input_path}"] if input_path is not None else []),
            f"--output={output}",
            f"--timezone={timezone_name}",
            *snapshot_options,
        ]
        if external_safe_pack:
            command.append("--external-safe-pack")
        staging_before = set(_staging_folders(output))
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
            run = _Run(process, output, staging_before)
            run.how = how
            if how == "snapshots" and store is not None:
                run.store = store
                run.lock_before = lock_before
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
                "stage_seconds": run.stage_seconds(now),
                "output_path": str(run.output),
                "result": json.loads(json.dumps(run.result)) if run.result else None,
                "error_code": run.error_code,
                **({"error_detail": dict(run.error_detail)} if run.error_detail else {}),
                "staging_folders": list(run.staging_folders),
                # The way of the run and the result of its import (stage B4b-1).
                "how": run.how,
                "imported": dict(run.imported) if run.imported else None,
                # The notices of the store that a cancelled import left
                # (stage B4b-2): codes only.
                "store_notices": list(run.store_notices),
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
                run.enter_stage(progress["stage"], run.last_progress)
        elif event == "imported":
            # A message that is not valid leaves the result of the import.
            imported = _valid_import(message)
            if imported is not None:
                run.imported = imported
        elif event == "finished":
            run.result = _valid_result(message)
        elif event == "failed":
            code = message.get("code")
            if isinstance(code, str) and CODE.fullmatch(code):
                run.error_code = code
                run.error_detail = _valid_detail(message) or _valid_mix(message)
        elif event == "cancelled":
            run.reported_cancel = True

    def _finish(self, run: _Run, returncode: int) -> None:
        output_exists = run.output.is_dir()
        staging_folders = [
            name for name in _staging_folders(run.output) if name not in run.staging_before
        ]
        # A cancelled import, also one that was stopped by force, may leave
        # the record of an interrupted import or a lock file (stage B4b-2).
        store_notices = (
            cancel_notices(run.store, run.lock_before)
            if run.store is not None and (run.cancel_requested or run.reported_cancel)
            else []
        )
        with self._lock:
            run.ended = time.monotonic()
            if run.error_code is not None and run.result is None:
                # A failure that the child reported comes first, also when a
                # cancellation was asked for after it (stage A5c).
                run.state = "failed"
            elif run.cancel_requested or run.reported_cancel:
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
            if run.state == "cancelled":
                run.store_notices = store_notices


__all__ = [
    "CANCEL_GRACE_SECONDS",
    "FINISHED_STATES",
    "KILL_GRACE_SECONDS",
    "MAX_OUTPUT_NAME_BYTES",
    "MAX_TIMEZONE_LENGTH",
    "RunActiveError",
    "RunManager",
    "RunRequestError",
    "WINDOWS_MAX_FILE_PATH",
    "WINDOWS_MAX_FOLDER_PATH",
    "absolute_path",
    "output_path_too_long",
    "validate_output_name",
    "windows_paths_too_long",
]
