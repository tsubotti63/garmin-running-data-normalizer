"""The Snapshot Store on the GUI page (stage B4a, internal).

The page opens a store and lists its Snapshots, checks the place of a new
store, and checks a store, with the functions of the CLI's snapshot
commands. Nothing here writes: the page makes a store when it imports an
Export (stage B4b). A problem of a store is an answer, with the code of the
CLI, since the page shows it beside the store and goes on; the answers give
places, numbers, labels, times, and codes only.
"""
from __future__ import annotations

import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..intake.source import place_can_be_shown
from ..snapshot.store import (
    SnapshotStoreError,
    check_new_store_place,
    lock_created_at,
    remove_lock,
    snapshot_status,
    verification_error,
    verify_store,
)
from .places import STORE_FOLDER_NAME, cloud_kind, default_folder, default_store

# The codes that the answers give: the stops of snapshot status, snapshot
# verify, and the place of a new store, and the notices of a store, which the
# page shows in yellow.
ANSWER_CODES = (
    "SNAPSHOT_STORE_NOT_FOUND",
    "SNAPSHOT_STORE_INVALID",
    "SNAPSHOT_STORE_VERSION_UNSUPPORTED",
    "SNAPSHOT_STORE_NOT_READABLE",
    "SNAPSHOT_STORE_SYMLINK",
    "SNAPSHOT_STORE_PARENT_NOT_FOUND",
    "SNAPSHOT_STORE_NOT_EMPTY",
    "SNAPSHOT_STORE_INSIDE_STORE",
    "SNAPSHOT_STORE_LOCKED",
    "SNAPSHOT_REGISTRATION_INCOMPLETE",
    # Removing a lock file (stage B4b-2).
    "SNAPSHOT_UNLOCK_NOT_CONFIRMED",
    "SNAPSHOT_LOCK_NOT_FOUND",
    "SNAPSHOT_LOCK_INVALID",
    "SNAPSHOT_STORE_NOT_WRITABLE",
)


def not_readable_detail(places: Any) -> dict[str, Any] | None:
    """The first folder or file that cannot be opened, or None for a name
    that cannot be shown, and how many more (stage B3c)."""
    if not isinstance(places, list) or not places:
        return None
    first = places[0]
    return {"place": first if place_can_be_shown(first) else None, "more": len(places) - 1}


def _problem(path: Path, error: SnapshotStoreError) -> dict[str, Any]:
    answer: dict[str, Any] = {"state": "error", "path": str(path), "error_code": error.code}
    if error.code == "SNAPSHOT_STORE_NOT_READABLE":
        detail = not_readable_detail(error.places)
        if detail is not None:
            # "" is the store's folder itself, not the input.
            answer["detail"] = {**detail, "store": True}
    return answer


def _opened(path: Path, status: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": "store",
        "path": str(path),
        "snapshots": [
            {
                "order": item["logical_order"],
                "label": item["snapshot_label"],
                "observed_at": item["export_observed_at"],
                "files": item["file_count"],
            }
            for item in status["snapshots"]
        ],
        "notices": list(status.get("notices", [])),
        # When the lock file was written, for the person who decides whether
        # an import still runs (stage B4b-2).
        **(
            {"lock_created_at": lock_created_at(path)}
            if "SNAPSHOT_STORE_LOCKED" in status.get("notices", [])
            else {}
        ),
        "cloud": cloud_kind(path),
    }


def _candidates(folder: Path) -> list[Path]:
    """Where a store may be for a chosen folder: the folder itself, then its
    folder snapshots, as in the default place."""
    if folder.name == STORE_FOLDER_NAME:
        return [folder]
    return [folder, folder / STORE_FOLDER_NAME]


def _find(folder: Path) -> dict[str, Any] | None:
    """The store at a chosen folder or in its folder snapshots, or a problem
    of one there; None when neither holds a store."""
    for candidate in _candidates(folder):
        try:
            status = snapshot_status(candidate)
        except SnapshotStoreError as exc:
            if exc.code == "SNAPSHOT_STORE_NOT_FOUND":
                continue
            return _problem(candidate, exc)
        return _opened(candidate, status)
    return None


def open_store(folder: Path) -> dict[str, Any]:
    """Open the store that the user chose: the folder, or its folder
    snapshots. A folder without one answers SNAPSHOT_STORE_NOT_FOUND."""
    found = _find(folder)
    if found is not None:
        return found
    return {"state": "error", "path": str(folder), "error_code": "SNAPSHOT_STORE_NOT_FOUND"}


def unlock_store(path: Path, confirmed: Any) -> dict[str, Any]:
    """Remove the lock file of the store at ``path`` with the function of
    snapshot unlock (stage B4b-2), and answer as opening the store does, with
    ``unlocked``; a stop is an answer with its code."""
    try:
        remove_lock(path, confirmed=confirmed is True)
    except SnapshotStoreError as exc:
        return _problem(path, exc)
    answer = open_store(path)
    answer["unlocked"] = True
    return answer


def store_place(folder: Path) -> dict[str, Any]:
    """The place for a new store in a chosen folder: its folder snapshots,
    or the folder itself when it is named snapshots. A store there is opened
    instead. The default place may wait for its folder GarminRunningData,
    which the page makes with the store (stage B4b); any other place is
    checked as ``snapshot init`` checks it."""
    found = _find(folder)
    if found is not None:
        return found
    place = folder if folder.name == STORE_FOLDER_NAME else folder / STORE_FOLDER_NAME
    if place != default_store() or default_folder().exists() or default_folder().is_symlink():
        try:
            check_new_store_place(place)
        except SnapshotStoreError as exc:
            return _problem(place, exc)
    return {"state": "new", "path": str(place), "cloud": cloud_kind(place)}


def check_store(path: Path) -> dict[str, Any]:
    """Check a store as ``snapshot verify`` does: its count and notices, or
    the code with which the CLI stops for it."""
    try:
        result = verify_store(path)
    except SnapshotStoreError as exc:
        return _problem(path, exc)
    if result["status"] != "PASS":
        return {"state": "error", "path": str(path), "error_code": verification_error(result).code}
    return {
        "state": "checked",
        "path": str(path),
        "snapshot_count": result["snapshot_count"],
        "notices": list(result.get("notices", [])),
    }


def download_time(input_path: Path) -> tuple[str | None, str | None]:
    """The time to propose as the download of an Export, and where it came
    from (stage B4b-1, decision 20261017-16): the time of a ZIP file, which
    the browser set when it downloaded it, or the time of the newest file of
    an extracted folder, which is near the time when the Export was made,
    since the folder itself has the time of the extraction. Hidden files,
    links, and what cannot be opened are passed over. None for an input
    without a file to read it from."""
    try:
        if input_path.is_file():
            return _proposed(input_path.stat().st_mtime, "zip")
    except OSError:
        return None, None
    newest: float | None = None
    for folder, names, files in os.walk(input_path, followlinks=False):
        names[:] = [name for name in names if not name.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            try:
                status = os.lstat(os.path.join(folder, name))
            except OSError:
                continue
            if stat.S_ISREG(status.st_mode) and (newest is None or status.st_mtime > newest):
                newest = status.st_mtime
    return _proposed(newest, "newest_file")


def _proposed(timestamp: float | None, source: str) -> tuple[str | None, str | None]:
    if timestamp is None:
        return None, None
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds"), source
    except (OverflowError, OSError, ValueError):
        return None, None


__all__ = [
    "ANSWER_CODES",
    "check_store",
    "download_time",
    "not_readable_detail",
    "open_store",
    "store_place",
    "unlock_store",
]
