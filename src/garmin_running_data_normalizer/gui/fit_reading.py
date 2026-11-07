"""The laps of one activity of an output, with the kinds of the laps that its
FIT file records, read from the Snapshot Store (stage X9c-1 of v2.3.0,
internal: nothing calls it yet; the view page asks it from stage X9c-2).

The view page reads the output that it opened; from v2.3.0, when the user
asks for the laps of one activity, it also reads the one FIT file of that
activity in the Snapshot Store that the GUI remembers (the user's decision
of stage X8). It writes nothing, sends nothing, and reads no file of the
store but store.json and that one blob. An output made without a store, or
with another store, is told as such.

The files of the output are compared with the sizes and the SHA-256 that
the manifest of the view page's reading gives them, so that the laps are of
that reading. They are read one at a time, in the order in which a refusal
comes first: the lineage of the Snapshot build, the store's store.json, the
links of the activities to the FIT sessions, the sessions, and the laps; of
each, only the rows of the one activity are kept. The FIT file is the blob
of its SHA-256, read once, at most MAX_FIT_BYTES and one byte, and used only
when the SHA-256 of the bytes read is the output's; fit.lap_kinds scans the
same bytes. Its laps are tied to the output's by the SHA-256, the number of
the session, and the numbers of the laps; their start, timer time, distance,
and elapsed time are compared too, to find a difference of the two
readings. The kinds come from the FIT file, the other values from the
output.

The folder of the store is opened once, and store.json and the blob are
read in it. Where the system opens a file in an open folder without
following a link (``dir_fd``, O_NOFOLLOW, and O_DIRECTORY), each folder of
the way is opened from the one before it, so that a link put in place of a
folder is not followed. On Windows, which has no ``dir_fd``, the folder of
the store and each folder of the way are held open, from before they are
looked at until the file is read, by handles that take part in the checks
of sharing (FILE_LIST_DIRECTORY) and let no one rename or remove them (no
FILE_SHARE_DELETE), so that no folder can be put in place of another at its
place; the file is opened as itself, a link or a junction not followed
(FILE_FLAG_OPEN_REPARSE_POINT), and read only when the place where the
system opened it (GetFinalPathNameByHandleW) is, letter for letter, the
place where it had the folder of the store and the way to the file: a
folder of the way made a junction leads the opening elsewhere, which is
then refused before a byte is read. Each step is looked at too, before
the file is opened and after it is read, and a link, a junction, or another
reparse point is refused. Each look compares a
file or a folder by its identity, which the system must give (st_ino; a
file or a folder of a drive that gives none is refused). A FIT file is used
only with the content of the output's in any case. The folders above the
store are not looked at, as ``snapshot.store.load_store`` does not. The
files of the output are opened without waiting (O_NONBLOCK), so that a pipe
put in place of one is refused, not waited for, and as themselves (O_NOFOLLOW;
on Windows FILE_FLAG_OPEN_REPARSE_POINT), so that a link put in place of one
is refused.

The answer holds the kinds and the values of the laps, how many of them
have no known kind, or the reason why the laps cannot be shown: no place,
no SHA-256, no key of an activity, and no position. Nothing is kept.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from ..common.json_depth import check_json_depth
from ..fit.lap_kinds import intensity_name, read_lap_kinds
from ..fit.parser import FIT_EPOCH_OFFSET
from ..output_check import OutputActionError
from ..snapshot.store import (
    MAX_STORE_METADATA_BYTES,
    SHA256_RE,
    SnapshotStoreError,
    _blob_relative_path,
    check_store_metadata,
)
from ..view.data import MAX_FILE_BYTES, Row, _json_records, _json_value
from .stores import _candidates

if sys.platform == "win32":  # The way of opening of Windows (_open_handle, _open_file, _final_path).
    import _winapi
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _GET_FINAL_PATH = _KERNEL32.GetFinalPathNameByHandleW
    _GET_FINAL_PATH.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    _GET_FINAL_PATH.restype = wintypes.DWORD

LINEAGE = "snapshot/snapshot_lineage.json"
LINKS = "normalized/activity_fit_links.json"
SESSIONS = "normalized/fit_sessions.json"
LAPS = "normalized/fit_laps.json"
LAP_FILES = (LINEAGE, LINKS, SESSIONS, LAPS)
# The largest FIT file that the view page reads: a FIT file of 32 MiB took
# about 8.5 seconds on a Mac of 2026, so that a computer three times slower
# answers within 30 seconds (stage X9c-1). The normalizer reads up to 128 MiB.
MAX_FIT_BYTES = 32 * 1024 * 1024
KINDS = frozenset({"active", "rest", "warmup", "cooldown", "recovery", "interval"})
UNKNOWN_KIND = "unknown"
# Why the laps of an activity cannot be shown. key_shared is the caller's,
# for a row whose key another row has too (activity_key).
REASONS = (
    "not_from_store",
    "no_store",
    "other_store",
    "store_unreadable",
    "no_link",
    "key_shared",
    "fit_missing",
    "fit_too_large",
    "fit_changed",
    "fit_not_activity",
    "laps_differ",
)
# The values of a lap that are compared with the FIT file's, by their names
# in fit.lap_kinds and in the output.
COMPARED = (
    ("elapsed_s", "total_elapsed_time"),
    ("timer_s", "total_timer_time"),
    ("distance_m", "total_distance"),
)

_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
_OPENS_AT = os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_FOLDER_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | _CLOEXEC
_OUTPUT_FLAGS = (
    os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | _CLOEXEC
)
_WINDOWS = sys.platform == "win32"
# CreateFileW: list a folder (an access that takes part in the checks of
# sharing, which an access to the attributes alone does not), or read a
# file; a folder held so lets others read and write in it, as a registration
# does, but not rename or remove it (no FILE_SHARE_DELETE); a file may be
# read, written, renamed, and removed by others meanwhile; open a folder
# (FILE_FLAG_BACKUP_SEMANTICS); open a link or a junction as itself
# (FILE_FLAG_OPEN_REPARSE_POINT).
_FILE_LIST_DIRECTORY = 0x0001
_GENERIC_READ = 0x80000000
_FILE_SHARE_READ_WRITE = 0x0001 | 0x0002
_FILE_SHARE_ALL = 0x0001 | 0x0002 | 0x0004
_OPEN_EXISTING = 3
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000


@dataclass(frozen=True)
class LapRow:
    """One lap as the view page shows it: its kind from the FIT file, and its
    values from the output."""

    kind: str
    elapsed_s: float | None
    timer_s: float | None
    distance_m: float | None
    avg_heart_rate: float | None
    avg_cadence: float | None
    avg_speed: float | None


@dataclass(frozen=True)
class Laps:
    """The answer: status "laps" with the laps of the activity (none for an
    activity without laps) and how many of them have no known kind, or
    status "unavailable" with one of REASONS."""

    status: str
    reason: str | None = None
    laps: tuple[LapRow, ...] = ()
    unknown_kind: int = 0


class _Unavailable(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Missing(Exception):
    """A step of the way to a file of the store is not there."""


class _TooLarge(Exception):
    """A file of the store is larger than its limit."""


def activity_key(rows: Sequence[Row], ref: int) -> str | None:
    """The declared key of the activity at ``ref`` among the activities of a
    reading, or None where it has none or another row has it too, so that a
    key never stands for two activities."""
    key = rows[ref].marks.get("key") or ""
    if not key or sum(1 for row in rows if row.marks.get("key") == key) != 1:
        return None
    return key


def read_laps(
    output: Path,
    files: Mapping[str, tuple[int, str]],
    key: str,
    store_folder: Path | None,
) -> Laps:
    """The laps of the activity of ``key`` in ``output``, with their kinds
    from the FIT file in the store that the GUI remembers (``store_folder``,
    None where it remembers none). ``files`` are the sizes and the SHA-256
    of the files of the output, as the manifest of the view page's reading
    gives them. A file of the output that is not as its manifest gives it,
    or of a form that this version does not write, raises
    OutputActionError, as the view page's reading does."""
    try:
        return _read_laps(Path(output), files, key, store_folder)
    except _Unavailable as exc:
        return Laps("unavailable", exc.reason)


def _read_laps(
    output: Path,
    files: Mapping[str, tuple[int, str]],
    key: str,
    store_folder: Path | None,
) -> Laps:
    if not key:
        raise _Unavailable("key_shared")
    if LINEAGE not in files:
        raise _Unavailable("not_from_store")
    if any(path not in files for path in (LINKS, SESSIONS, LAPS)):
        raise OutputActionError("OUTPUT_CHANGED")
    account = _lineage_account(output, files)
    if store_folder is None:
        raise _Unavailable("no_store")
    with ExitStack() as stack:
        root, metadata = _open_store(Path(store_folder), stack)
        if metadata["account_store_id"] != account:
            raise _Unavailable("other_store")
        session_key, digest = _link(output, files, key)
        ordinal = _session(output, files, session_key, digest)
        rows = _output_laps(output, files, session_key, digest, ordinal)
        data = _fit_bytes(root, digest)
    return _laps(data, ordinal, rows)


# The files of the output.


def _output_bytes(output: Path, files: Mapping[str, tuple[int, str]], relative: str) -> bytes:
    """A file of the output, read once, at most the manifest's size and one
    byte, and compared with the manifest, as the view page's reading reads
    it (view.data._checked_bytes), opened without waiting: a plain file, not
    a link, a junction, or a pipe, also one put in its place at the
    opening."""
    size, digest = files[relative]
    if size > MAX_FILE_BYTES:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE")
    path = output.joinpath(*PurePosixPath(relative).parts)
    try:
        if not _plain(os.lstat(path)):
            raise OutputActionError("OUTPUT_NOT_AVAILABLE")
        descriptor = _open_output(path)
        try:
            if not _plain(os.fstat(descriptor)):
                raise OutputActionError("OUTPUT_NOT_AVAILABLE")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read(size + 1)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE") from exc
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise OutputActionError("OUTPUT_CHANGED")
    return data


def _open_output(path: Path) -> int:
    """A descriptor of a file of the output, opened to read without waiting
    and as itself (on Windows, a link or a junction opened as itself, which
    fstat then refuses)."""
    if not _WINDOWS:
        return os.open(path, _OUTPUT_FLAGS)
    handle = _open_handle(path, _GENERIC_READ, _FILE_FLAG_OPEN_REPARSE_POINT, _FILE_SHARE_ALL)
    try:
        return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        _close_handle(handle)
        raise


def _plain(status: os.stat_result) -> bool:
    """A plain file, not a link, a junction, another reparse point, or a pipe."""
    return stat.S_ISREG(status.st_mode) and not getattr(status, "st_file_attributes", 0) & _REPARSE_POINT


def _records(output: Path, files: Mapping[str, tuple[int, str]], relative: str) -> list[dict[str, Any]]:
    return _json_records(_output_bytes(output, files, relative))


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _lineage_account(output: Path, files: Mapping[str, tuple[int, str]]) -> str:
    lineage = _json_value(_output_bytes(output, files, LINEAGE))
    if not isinstance(lineage, dict) or not isinstance(lineage.get("account_store_id"), str):
        raise OutputActionError("OUTPUT_CHANGED")
    return lineage["account_store_id"]


def _link(output: Path, files: Mapping[str, tuple[int, str]], key: str) -> tuple[str, str]:
    """The FIT session and the SHA-256 of the FIT file that the one link of
    the activity names; the session must be linked to no other activity."""
    rows = _records(output, files, LINKS)
    mine = [row for row in rows if row.get("garmin_activity_key") == key]
    if len(mine) != 1:
        raise _Unavailable("no_link")
    link = mine[0]
    if (
        link.get("match_status") != "explicit"
        or link.get("ambiguous") is not False
        or link.get("eligibility_status") != "eligible"
    ):
        raise _Unavailable("no_link")
    session_key, digest = link.get("fit_session_key"), link.get("fit_source_sha256")
    if not isinstance(session_key, str) or not isinstance(digest, str):
        raise OutputActionError("OUTPUT_CHANGED")
    if sum(1 for row in rows if row.get("fit_session_key") == session_key) != 1:
        raise _Unavailable("no_link")
    return session_key, digest


def _session(output: Path, files: Mapping[str, tuple[int, str]], session_key: str, digest: str) -> int:
    """The number of the session in its FIT file, as its one row gives it,
    with the SHA-256 of the link and its key made of the two."""
    rows = [row for row in _records(output, files, SESSIONS) if row.get("fit_session_key") == session_key]
    if len(rows) != 1:
        raise OutputActionError("OUTPUT_CHANGED")
    ordinal, source = rows[0].get("session_ordinal"), rows[0].get("source_sha256")
    if (
        not _whole(ordinal)
        or not isinstance(source, str)
        or not SHA256_RE.fullmatch(source)
        or source != digest
        or session_key != f"fit_session:{source}:{ordinal}"
    ):
        raise OutputActionError("OUTPUT_CHANGED")
    return ordinal


def _output_laps(
    output: Path,
    files: Mapping[str, tuple[int, str]],
    session_key: str,
    digest: str,
    ordinal: int,
) -> list[dict[str, Any]]:
    """The rows of the laps of the session, by their numbers, which run from
    0 without a gap or a repeat."""
    rows = [row for row in _records(output, files, LAPS) if row.get("fit_session_key") == session_key]
    numbers = [row.get("lap_ordinal_within_session") for row in rows]
    if (
        any(
            row.get("source_sha256") != digest
            or not _whole(row.get("session_ordinal"))
            or row.get("session_ordinal") != ordinal
            for row in rows
        )
        or not all(_whole(number) for number in numbers)
        or sorted(numbers) != list(range(len(rows)))
    ):
        raise OutputActionError("OUTPUT_CHANGED")
    return sorted(rows, key=lambda row: row["lap_ordinal_within_session"])


# The files of the store.


class _Root:
    """The folder of a store, opened once, in which its files are read: by
    its descriptor where the system opens files in an open folder, else by
    its path, looked at first."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.descriptor: int | None = None
        self.looked: os.stat_result | None = None
        # Windows: the folder held (no one renames or removes it until the
        # reading ends), and where the system has it, to which each file read
        # in it must lead.
        self.hold: int | None = None
        self.final: str | None = None

    def __enter__(self) -> _Root:
        try:
            if _OPENS_AT:
                self.descriptor = os.open(self.path, _FOLDER_FLAGS)
            else:
                if _WINDOWS:
                    self.hold = _hold(self.path)
                    self.final = _final_path(self.hold)
                self.looked = _looked(self.path, folder=True)
        except FileNotFoundError as exc:
            self.close()
            raise _Missing() from exc
        except _Unavailable:
            self.close()
            raise
        except OSError as exc:
            self.close()
            raise _Unavailable("store_unreadable") from exc
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self.descriptor is not None:
            descriptor, self.descriptor = self.descriptor, None
            os.close(descriptor)
        if self.hold is not None:
            hold, self.hold = self.hold, None
            _close_handle(hold)

    def read(self, parts: tuple[str, ...], limit: int) -> bytes:
        """The bytes of the file at ``parts`` in the folder, read once. A
        step that is not there raises _Missing, a file over ``limit``
        _TooLarge, and a link, a reparse point, another kind of file, a file
        that changed while it was read, or a step that cannot be opened,
        store_unreadable."""
        try:
            if self.descriptor is not None:
                return _bytes_at(self.descriptor, parts, limit)
            if self.looked is None:
                raise _Unavailable("store_unreadable")
            return _bytes_by_path(self.path, self.looked, parts, limit, self.final)
        except FileNotFoundError as exc:
            raise _Missing() from exc
        except OSError as exc:
            raise _Unavailable("store_unreadable") from exc


def _open_store(folder: Path, stack: ExitStack) -> tuple[_Root, dict[str, Any]]:
    """The store at the remembered folder or in its folder snapshots, as the
    page opens one, open until ``stack`` closes; the next place is looked at
    only where the folder or its store.json is not there."""
    for candidate in _candidates(folder):
        root = _Root(candidate)
        try:
            stack.enter_context(root)
            data = root.read(("store.json",), MAX_STORE_METADATA_BYTES)
        except _Missing:
            root.close()
            continue
        except _TooLarge as exc:
            raise _Unavailable("store_unreadable") from exc
        return root, _store_metadata(data)
    raise _Unavailable("no_store")


def _store_metadata(data: bytes) -> dict[str, Any]:
    """store.json, checked as ``load_store`` checks it, with an account store
    id of text. A failure is told as a store that cannot be read: the
    message of the store's error, which may name a place, is not given."""
    try:
        metadata = json.loads(data.decode("utf-8"))
        check_json_depth(metadata)
    except (ValueError, RecursionError) as exc:
        raise _Unavailable("store_unreadable") from exc
    if not isinstance(metadata, dict):
        raise _Unavailable("store_unreadable")
    try:
        check_store_metadata(metadata)
    except (ValueError, OverflowError) as exc:
        # A SnapshotStoreError, or a time that cannot be told in UTC, which
        # stops load_store with an OverflowError (it is left as it is).
        raise _Unavailable("store_unreadable") from exc
    if not isinstance(metadata.get("account_store_id"), str):
        raise _Unavailable("store_unreadable")
    return metadata


def _fit_bytes(root: _Root, digest: str) -> bytes:
    """The bytes of the FIT file of ``digest``, its blob in the store."""
    try:
        data = root.read(tuple(_blob_relative_path(digest).split("/")), MAX_FIT_BYTES)
    except _Missing as exc:
        raise _Unavailable("fit_missing") from exc
    except _TooLarge as exc:
        raise _Unavailable("fit_too_large") from exc
    if hashlib.sha256(data).hexdigest() != digest:
        raise _Unavailable("fit_changed")
    return data


def _bytes_at(root: int, parts: tuple[str, ...], limit: int) -> bytes:
    """Each folder opened in the one before it, from the open folder of the
    store, none of them, nor the file, through a link."""
    opened: list[int] = []
    try:
        for part in parts[:-1]:
            opened.append(os.open(part, _FOLDER_FLAGS, dir_fd=opened[-1] if opened else root))
        opened.append(
            os.open(
                parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | _CLOEXEC,
                dir_fd=opened[-1] if opened else root,
            )
        )
        return _read_opened(opened[-1], limit, None)
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


def _bytes_by_path(
    root: Path, root_looked: os.stat_result, parts: tuple[str, ...], limit: int, root_final: str | None
) -> bytes:
    """Each step looked at before the file is opened and after it is read;
    the folder of the store as when it was opened, and on Windows the file
    where the system has the folder of the store and the way."""
    steps = [root]
    for part in parts:
        steps.append(steps[-1] / part)
    holds: list[int] = []
    try:
        before = [root_looked]
        for index, step in enumerate(steps[1:], 1):
            if _WINDOWS and index < len(parts):
                # Held before it is looked at, so that what is looked at is
                # the folder that stays at its place until the file is read.
                holds.append(_hold(step))
            before.append(_looked(step, folder=index < len(parts)))
        expected = None if root_final is None else "\\".join([root_final.rstrip("\\"), *parts])
        descriptor = _open_file(steps[-1], expected)
        try:
            data = _read_opened(descriptor, limit, before[-1])
        finally:
            os.close(descriptor)
        after = [_looked(step, folder=index < len(parts)) for index, step in enumerate(steps)]
    finally:
        for hold in reversed(holds):
            _close_handle(hold)
    if not all(_same_folder(first, second) for first, second in zip(before[:-1], after[:-1])) or not _same_file(before[-1], after[-1]):
        raise _Unavailable("store_unreadable")
    return data


def _open_handle(path: Path, access: int, flags: int, share: int) -> int:
    """Windows: a handle of ``path`` (CreateFileW)."""
    return _winapi.CreateFile(str(path), access, share, 0, _OPEN_EXISTING, flags, 0)


def _hold(path: Path) -> int:
    """Windows: a handle of a folder of the store, which lets no one rename
    or remove it until it is closed; a link or a junction is held as itself,
    which _looked then refuses."""
    return _open_handle(
        path, _FILE_LIST_DIRECTORY, _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT, _FILE_SHARE_READ_WRITE
    )


def _same_place(found: str, expected: str) -> bool:
    """Whether the place where the system has a file is the one expected,
    letter for letter: both are given by the system, so that another letter
    is another place (a folding of case, such as that of Python, would take
    some other names for the same)."""
    return found == expected


def _close_handle(handle: int) -> None:
    _winapi.CloseHandle(handle)


def _final_path(handle: int) -> str:
    """Windows: where the system has the file or the folder of ``handle``,
    after every link and junction of the way (GetFinalPathNameByHandleW)."""
    size = 1024
    while True:
        buffer = ctypes.create_unicode_buffer(size)
        length = _GET_FINAL_PATH(handle, buffer, size, 0)
        if length == 0:
            raise ctypes.WinError(ctypes.get_last_error())
        if length < size:
            return buffer.value
        size = length + 1


def _open_file(path: Path, expected: str | None) -> int:
    """A descriptor of the file at ``path``, opened to read. On Windows it is
    opened as itself, a link or a junction not followed (fstat then refuses
    it), and only where the system has it at ``expected``, the folder of the
    store and the way: one put in place of a folder of the way leads it
    elsewhere, refused before a byte is read."""
    if not _WINDOWS:
        return os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0))
    handle = _open_handle(path, _GENERIC_READ, _FILE_FLAG_OPEN_REPARSE_POINT, _FILE_SHARE_ALL)
    try:
        if expected is None or not _same_place(_final_path(handle), expected):
            raise _Unavailable("store_unreadable")
        return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        _close_handle(handle)
        raise


def _looked(path: Path, *, folder: bool) -> os.stat_result:
    status = os.lstat(path)
    kind = stat.S_ISDIR(status.st_mode) if folder else stat.S_ISREG(status.st_mode)
    if not kind or getattr(status, "st_file_attributes", 0) & _REPARSE_POINT:
        raise _Unavailable("store_unreadable")
    return status


def _same_identity(first: os.stat_result, second: os.stat_result) -> bool:
    """The same file or folder by its identity, which both looks must give:
    without one, another put in its place for a moment is not seen."""
    return bool(first.st_ino and second.st_ino) and (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _same_folder(first: os.stat_result, second: os.stat_result) -> bool:
    """The same folder, by its kind and its identity; its size and time
    change as a registration adds files."""
    return stat.S_IFMT(first.st_mode) == stat.S_IFMT(second.st_mode) and _same_identity(first, second)


def _same_file(first: os.stat_result, second: os.stat_result) -> bool:
    """The same file, unchanged: its kind, size, time, and identity."""
    return (
        stat.S_IFMT(first.st_mode) == stat.S_IFMT(second.st_mode)
        and first.st_size == second.st_size
        and first.st_mtime_ns == second.st_mtime_ns
        and _same_identity(first, second)
    )


def _read_opened(descriptor: int, limit: int, looked: os.stat_result | None) -> bytes:
    """Read an open file once, at most ``limit`` and one byte: a plain file,
    the one looked at before it was opened, unchanged while it was read."""
    opened = os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode) or getattr(opened, "st_file_attributes", 0) & _REPARSE_POINT:
        raise _Unavailable("store_unreadable")
    if looked is not None and not _same_file(looked, opened):
        raise _Unavailable("store_unreadable")
    if opened.st_size > limit:
        raise _TooLarge()
    with os.fdopen(descriptor, "rb", closefd=False) as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise _TooLarge()
    if not _same_file(opened, os.fstat(descriptor)):
        raise _Unavailable("store_unreadable")
    return data


# The laps of the FIT file and of the output.


def _fit_instant(seconds: int | None) -> datetime | None:
    """A FIT time as an instant, as fit.parser makes it; None out of range."""
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(seconds + FIT_EPOCH_OFFSET, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _output_instant(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise OutputActionError("OUTPUT_CHANGED")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OutputActionError("OUTPUT_CHANGED") from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise OutputActionError("OUTPUT_CHANGED")
    return moment


def _output_number(row: dict[str, Any], name: str) -> float | None:
    value = row.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OutputActionError("OUTPUT_CHANGED")
    try:
        number = float(value)
    except OverflowError as exc:
        # A whole number of JSON too large for a float.
        raise OutputActionError("OUTPUT_CHANGED") from exc
    if not math.isfinite(number):
        raise OutputActionError("OUTPUT_CHANGED")
    return number


def _agree(first: Any, second: Any) -> bool:
    """Both empty, or both values and the same."""
    return (first is None) == (second is None) and (first is None or first == second)


def _laps(data: bytes, ordinal: int, rows: list[dict[str, Any]]) -> Laps:
    kinds = read_lap_kinds(data)
    if kinds.status != "parsed_activity" or ordinal >= len(kinds.sessions):
        raise _Unavailable("fit_not_activity")
    fit_laps = kinds.sessions[ordinal].laps
    if len(fit_laps) != len(rows):
        raise _Unavailable("laps_differ")
    laps = []
    for lap, row in zip(fit_laps, rows):
        if not _agree(_fit_instant(lap.start_time), _output_instant(row.get("start_time"))):
            raise _Unavailable("laps_differ")
        for fit_name, output_name in COMPARED:
            if not _agree(getattr(lap, fit_name), _output_number(row, output_name)):
                raise _Unavailable("laps_differ")
        name = intensity_name(lap.intensity)
        laps.append(
            LapRow(
                kind=name if name in KINDS else UNKNOWN_KIND,
                elapsed_s=_output_number(row, "total_elapsed_time"),
                timer_s=_output_number(row, "total_timer_time"),
                distance_m=_output_number(row, "total_distance"),
                avg_heart_rate=_output_number(row, "avg_heart_rate"),
                avg_cadence=_output_number(row, "avg_cadence"),
                avg_speed=_output_number(row, "avg_speed"),
            )
        )
    return Laps("laps", laps=tuple(laps), unknown_kind=sum(1 for lap in laps if lap.kind == UNKNOWN_KIND))


__all__ = [
    "COMPARED",
    "KINDS",
    "LAPS",
    "LAP_FILES",
    "LINEAGE",
    "LINKS",
    "LapRow",
    "Laps",
    "MAX_FIT_BYTES",
    "REASONS",
    "SESSIONS",
    "UNKNOWN_KIND",
    "activity_key",
    "read_laps",
]
