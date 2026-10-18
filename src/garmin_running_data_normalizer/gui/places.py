"""The default places of the GUI, and places that a cloud may copy (internal).

The default place is the folder GarminRunningData in the home folder: the
Snapshot Store goes in its folder snapshots, and the outputs in it (stage
B4a). Only the GUI has default places; the CLI takes every place as an
argument and makes no folder above it. The GUI makes the folder
GarminRunningData alone, when a run starts with it as the folder for the
output and nothing is there.

A place may be copied to a cloud when it is in a folder that a cloud app
keeps. Only fixed names are compared: no program is asked and nothing is
sent, so the answer means "may be", not "is".
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..common.private_files import PRIVATE_DIRECTORY_MODE

DEFAULT_FOLDER_NAME = "GarminRunningData"
STORE_FOLDER_NAME = "snapshots"
# Folders that cloud apps keep under these names, wherever they are.
_CLOUD_FOLDER_NAMES = frozenset({"dropbox", "onedrive", "google drive", "icloud drive", "iclouddrive"})
# OneDrive for work or school names its folder "OneDrive - <organization>".
_ONEDRIVE_PREFIX = "onedrive - "
# The places of OneDrive that Windows gives.
_ONEDRIVE_VARIABLES = ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")


def home() -> Path:
    """The home folder, as the system gives it; tests replace it."""
    return Path.home()


def default_folder() -> Path:
    return home() / DEFAULT_FOLDER_NAME


def default_store() -> Path:
    return default_folder() / STORE_FOLDER_NAME


def make_default_folder(parent: Path) -> None:
    """Make the folder GarminRunningData when ``parent`` is that folder, as
    this server names it, and nothing is there. A folder, a link, or a file
    there, or a home folder that is missing, is left to the checks of the
    place of the output. Raises OSError when it cannot be made."""
    folder = default_folder()
    if parent != folder:
        return
    try:
        os.mkdir(folder, PRIVATE_DIRECTORY_MODE)
    except (FileExistsError, FileNotFoundError):
        return
    # As the private folders of this app: the umask cannot widen it.
    folder.chmod(PRIVATE_DIRECTORY_MODE)


def _key(path: Path, platform: str) -> tuple[str, ...]:
    """The parts of a path, compared without case where the system does."""
    parts = Path(os.path.abspath(path)).parts
    return tuple(part.casefold() for part in parts) if platform in ("darwin", "win32") else parts


def _inside(path: Path, folder: Path, platform: str) -> bool:
    """Whether ``path`` is ``folder`` or inside it."""
    place, base = _key(path, platform), _key(folder, platform)
    return place[: len(base)] == base


def _named_cloud_folder(path: Path) -> bool:
    for part in Path(os.path.abspath(path)).parts:
        name = part.casefold()
        if name in _CLOUD_FOLDER_NAMES or name.startswith(_ONEDRIVE_PREFIX):
            return True
    return False


def cloud_kind(path: Path, platform: str = sys.platform) -> str | None:
    """Whether a cloud may copy ``path``: "cloud" in a folder that a cloud
    app keeps, "desktop_documents" in the Desktop or Documents of a Mac,
    which iCloud copies when its setting for them is on, and None otherwise.
    The place is compared as it is given and as its links lead."""
    candidates = [Path(os.path.abspath(path))]
    real = Path(os.path.realpath(path))
    if real != candidates[0]:
        candidates.append(real)
    folders: list[Path] = []
    if platform == "darwin":
        library = home() / "Library"
        folders += [library / "Mobile Documents", library / "CloudStorage"]
    if platform == "win32":
        folders += [Path(value) for name in _ONEDRIVE_VARIABLES if (value := os.environ.get(name))]
        folders.append(home() / "iCloudDrive")
    for candidate in candidates:
        if _named_cloud_folder(candidate) or any(
            folder.is_absolute() and _inside(candidate, folder, platform) for folder in folders
        ):
            return "cloud"
    if platform == "darwin":
        for candidate in candidates:
            if any(_inside(candidate, home() / name, platform) for name in ("Desktop", "Documents")):
                return "desktop_documents"
    return None


__all__ = [
    "DEFAULT_FOLDER_NAME",
    "STORE_FOLDER_NAME",
    "cloud_kind",
    "default_folder",
    "default_store",
    "home",
    "make_default_folder",
]
