"""The settings of an earlier launch of the GUI (internal; stage B4c).

The GUI remembers, in one file on this computer (decision 20261017-15): the
Snapshot Store and the folder for the output of the last run that made its
output, the outputs that runs made (the latest ten), and whether the tips
show. Only the names of places are kept, never what is in them, and never the
place of an Export. The CLI remembers nothing.

The file is the person's own: an owner-only folder and file, written whole
through a temporary file in the same folder, so that no half-written file is
left. It is read with care: a link, a folder, a file over 64 KiB, or a file
of another form is not used, and the next settings replace it; a file of a
newer version is not used and never written over, so that going back to an
older version leaves the newer settings as they are. Keys that this version
does not know are left out. Places read from it are absolute places of this
system without control characters, and the server checks them again as it
checks places that the page sends.
"""
from __future__ import annotations

import json
import os
import secrets
import stat
from pathlib import Path
from typing import Any

from ..common.private_files import PRIVATE_DIRECTORY_MODE, PRIVATE_FILE_MODE
from . import places

SETTINGS_FORMAT = "garmin-running-data-normalizer-gui-settings-v1"
_FORMAT_PREFIX = "garmin-running-data-normalizer-gui-settings-v"
_FORMAT_VERSION = 1
MAX_SETTINGS_BYTES = 64 * 1024
MAX_RECENT_OUTPUTS = 10
MAX_PLACE_LENGTH = 4096
PLACE_KEYS = ("store", "output_parent")

# What the settings tell the page, codes only.
SETTINGS_INVALID = "SETTINGS_INVALID"
SETTINGS_NEWER = "SETTINGS_NEWER"
SETTINGS_NOT_WRITTEN = "SETTINGS_NOT_WRITTEN"
SETTINGS_NOT_REMOVED = "SETTINGS_NOT_REMOVED"


def _place(value: Any) -> str | None:
    """A place as the file may hold it: an absolute place of this system, of
    a sensible length, without control characters; None otherwise."""
    if not isinstance(value, str) or not 0 < len(value) <= MAX_PLACE_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    try:
        # A name that the system gave in bytes that are not UTF-8 cannot be
        # kept in the file.
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return value if Path(value).is_absolute() else None


def _version(value: Any) -> int | None:
    if isinstance(value, str) and value.startswith(_FORMAT_PREFIX):
        number = value[len(_FORMAT_PREFIX):]
        if number.isascii() and number.isdigit():
            return int(number)
    return None


def _known(data: Any) -> dict[str, Any] | None:
    """The values that this version knows, or None when one of them is not
    of its form; other keys are left out."""
    if not isinstance(data, dict):
        return None
    values: dict[str, Any] = {}
    for key in PLACE_KEYS:
        if data.get(key) is not None:
            place = _place(data[key])
            if place is None:
                return None
            values[key] = place
    if data.get("recent_outputs") is not None:
        outputs = data["recent_outputs"]
        if not isinstance(outputs, list) or len(outputs) > MAX_RECENT_OUTPUTS:
            return None
        found = [_place(item) for item in outputs]
        if any(place is None for place in found) or len(set(found)) != len(found):
            return None
        values["recent_outputs"] = found
    if data.get("hints") is not None:
        if not isinstance(data["hints"], bool):
            return None
        values["hints"] = data["hints"]
    return values


def _read_all(descriptor: int) -> bytes | None:
    """The bytes of an open file, or None when there are more than the limit."""
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(descriptor, MAX_SETTINGS_BYTES + 1 - size)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_SETTINGS_BYTES:
            return None


def read_settings(path: Path) -> tuple[dict[str, Any], str | None]:
    """The settings at ``path``, and what to tell of the file: nothing when
    there is none or it is used, SETTINGS_INVALID for a file that cannot be
    read or is not of this form, and SETTINGS_NEWER for a file of a newer
    version. A file that is not used gives no settings."""
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return {}, None
    except OSError:
        return {}, SETTINGS_INVALID
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SETTINGS_BYTES:
        return {}, SETTINGS_INVALID
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return {}, SETTINGS_INVALID
    try:
        content = _read_all(descriptor)
    except OSError:
        content = None
    finally:
        os.close(descriptor)
    if content is None:
        return {}, SETTINGS_INVALID
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return {}, SETTINGS_INVALID
    version = _version(data.get("format")) if isinstance(data, dict) else None
    if version is not None and version > _FORMAT_VERSION:
        return {}, SETTINGS_NEWER
    values = _known(data) if version == _FORMAT_VERSION else None
    return ({}, SETTINGS_INVALID) if values is None else (values, None)


def _make_folder(folder: Path, own: bool) -> None:
    """Make a missing folder, owner-only. One that is there keeps its
    permissions; this app's own folder must be a folder itself, not a link."""
    try:
        os.mkdir(folder, PRIVATE_DIRECTORY_MODE)
    except FileExistsError:
        if own and not stat.S_ISDIR(os.lstat(folder).st_mode):
            raise NotADirectoryError(str(folder)) from None
        if not own and not folder.is_dir():
            raise NotADirectoryError(str(folder)) from None
        return
    # The umask cannot widen it.
    folder.chmod(PRIVATE_DIRECTORY_MODE)


def write_settings(path: Path, values: dict[str, Any], makeable: tuple[Path, ...] = ()) -> str | None:
    """Write ``values`` as the settings at ``path``, whole, through a
    temporary file in the same folder: None when they are written, or
    SETTINGS_NOT_WRITTEN. This app's folder is made when it is missing, and
    the folders of ``makeable`` above it; no other folder is made."""
    known = _known(values)
    if known is None:
        return SETTINGS_NOT_WRITTEN
    content = (
        json.dumps({"format": SETTINGS_FORMAT, **known}, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")
    folder = path.parent
    temporary = folder / f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    written = False
    try:
        for parent in makeable:
            _make_folder(parent, own=False)
        _make_folder(folder, own=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(temporary, flags, PRIVATE_FILE_MODE)
        written = True
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, PRIVATE_FILE_MODE)
            view = memoryview(content)
            while view:
                view = view[os.write(descriptor, view):]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
    except OSError:
        if written:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        return SETTINGS_NOT_WRITTEN
    return None


def remove_settings(path: Path) -> str | None:
    """Forget the settings: remove the file at ``path`` (a link there is
    removed, not what it points to) and this app's folder when nothing else
    is in it. None when there is no file now, or SETTINGS_NOT_REMOVED."""
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        status = None
    except OSError:
        return SETTINGS_NOT_REMOVED
    if status is not None:
        if stat.S_ISDIR(status.st_mode):
            return SETTINGS_NOT_REMOVED
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        except OSError:
            return SETTINGS_NOT_REMOVED
    try:
        os.rmdir(path.parent)
    except OSError:
        pass
    return None


def remember_run_at(path: Path, output: Path, store: Path | None, makeable: tuple[Path, ...] = ()) -> str | None:
    """Remember the places of a run that made its output: the folder for the
    output, the output first in the latest ones, and the store of a Snapshot
    run (a run of this Export alone keeps the store that was remembered).
    None when they are written, or a code: SETTINGS_NEWER leaves the file of
    a newer version as it is."""
    current, notice = read_settings(path)
    if notice == SETTINGS_NEWER:
        return SETTINGS_NEWER
    made = str(output)
    recent = [made, *(item for item in current.get("recent_outputs", []) if item != made)]
    values = {**current, "output_parent": str(output.parent), "recent_outputs": recent[:MAX_RECENT_OUTPUTS]}
    if store is not None:
        values["store"] = str(store)
    return write_settings(path, values, makeable)


def remember_hints_at(path: Path, on: bool, makeable: tuple[Path, ...] = ()) -> str | None:
    """Remember whether the tips show, as the person switched them."""
    current, notice = read_settings(path)
    if notice == SETTINGS_NEWER:
        return SETTINGS_NEWER
    return write_settings(path, {**current, "hints": on}, makeable)


def launch_answer(values: dict[str, Any], notice: str | None) -> dict[str, Any]:
    """What the page takes from the settings when it starts: a later launch
    when a place is remembered (the tips alone do not make one), the places,
    the tips, and what to tell of the file."""
    store = values.get("store")
    parent = values.get("output_parent")
    return {
        "launch": "later" if store is not None or parent is not None else "first",
        "store": store,
        "output_parent": parent,
        "hints": values.get("hints"),
        "notice": notice,
    }


def _target() -> tuple[Path, tuple[Path, ...]]:
    # The place is asked for each time, so that a test's place is used.
    path = places.settings_file()
    return path, places.makeable_settings_folders(path)


def launch_settings() -> dict[str, Any]:
    path, _makeable = _target()
    return launch_answer(*read_settings(path))


def remember_run(output: Path, store: Path | None) -> str | None:
    path, makeable = _target()
    return remember_run_at(path, output, store, makeable)


def remember_hints(on: bool) -> str | None:
    path, makeable = _target()
    return remember_hints_at(path, on, makeable)


def forget_settings() -> str | None:
    path, _makeable = _target()
    return remove_settings(path)


__all__ = [
    "MAX_PLACE_LENGTH",
    "MAX_RECENT_OUTPUTS",
    "MAX_SETTINGS_BYTES",
    "SETTINGS_FORMAT",
    "SETTINGS_INVALID",
    "SETTINGS_NEWER",
    "SETTINGS_NOT_REMOVED",
    "SETTINGS_NOT_WRITTEN",
    "forget_settings",
    "launch_answer",
    "launch_settings",
    "read_settings",
    "remember_hints",
    "remember_hints_at",
    "remember_run",
    "remember_run_at",
    "remove_settings",
    "write_settings",
]
