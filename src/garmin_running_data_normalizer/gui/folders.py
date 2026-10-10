"""List the folders inside a local folder for the GUI folder browser (internal).

Only folder names are returned, never file names or contents. Hidden folders
(a leading dot, the Windows hidden or system attribute, or the macOS hidden
flag), symbolic links, and Windows junctions are left out.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

MAX_FOLDERS = 2000
# Windows marks junctions as reparse points, which is_symlink() does not
# detect before Python 3.12, and hides folders with attributes. macOS hides
# folders such as Library with a flag.
_EXCLUDED_ATTRIBUTES = (
    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    | getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0)
    | getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0)
)
_HIDDEN_FLAG = getattr(stat, "UF_HIDDEN", 0)


class FolderError(ValueError):
    """A folder that cannot be listed, reported to the page as a code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _listed(entry: os.DirEntry[str]) -> bool:
    if entry.name.startswith(".") or entry.is_symlink():
        return False
    if not entry.is_dir(follow_symlinks=False):
        return False
    info = entry.stat(follow_symlinks=False)
    if getattr(info, "st_file_attributes", 0) & _EXCLUDED_ATTRIBUTES:
        return False
    return not getattr(info, "st_flags", 0) & _HIDDEN_FLAG


def list_folders(path: Any = None) -> dict[str, Any]:
    """Return the names of the visible folders inside ``path`` (default: home)."""
    if path is None or path == "":
        folder = Path.home()
    elif not isinstance(path, str) or "\x00" in path:
        raise FolderError("PATH_INVALID")
    else:
        folder = Path(path).expanduser()
        if not folder.is_absolute():
            raise FolderError("PATH_NOT_ABSOLUTE")
    folder = Path(os.path.abspath(folder))
    names: list[str] = []
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                try:
                    if _listed(entry):
                        names.append(entry.name)
                except OSError:
                    continue
    except FileNotFoundError as exc:
        raise FolderError("FOLDER_NOT_FOUND") from exc
    except NotADirectoryError as exc:
        raise FolderError("NOT_A_FOLDER") from exc
    except OSError as exc:
        # macOS answers PermissionError when the user declines access to
        # protected folders such as Documents, Desktop, and Downloads.
        raise FolderError("FOLDER_NOT_READABLE") from exc
    names.sort(key=lambda name: (name.casefold(), name))
    parent = folder.parent
    return {
        "path": str(folder),
        "parent": None if parent == folder else str(parent),
        "folders": names[:MAX_FOLDERS],
        "truncated": len(names) > MAX_FOLDERS,
    }


__all__ = ["FolderError", "MAX_FOLDERS", "list_folders"]
