"""Operating-system metadata files that are never Garmin data or Product output."""
from __future__ import annotations

from pathlib import PurePosixPath

OS_METADATA_FILE_NAMES = frozenset({".DS_Store", "Thumbs.db"})
OS_METADATA_DIRECTORY_NAMES = frozenset({"__MACOSX"})
APPLEDOUBLE_PREFIX = "._"


def is_os_metadata_path(relative_path: str) -> bool:
    """Return whether a relative path is Finder, AppleDouble, or thumbnail metadata.

    Folder input discovery, ZIP member selection, Snapshot registration, and
    handoff validation all use this single rule, so they ignore the same
    files. ZIP members follow it from v1.5.0, which changes the Snapshot
    content identity of a ZIP that contains ``Thumbs.db``.
    """
    path = PurePosixPath(relative_path.replace("\\", "/"))
    return (
        path.name in OS_METADATA_FILE_NAMES
        or path.name.startswith(APPLEDOUBLE_PREFIX)
        or any(part in OS_METADATA_DIRECTORY_NAMES for part in path.parts)
    )
