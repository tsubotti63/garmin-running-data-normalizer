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

The settings of an earlier launch are one file in this app's folder in the
place that the system keeps for each person's application data (stage B4c):
Application Support in the Library of a Mac, LOCALAPPDATA on Windows, and the
XDG state home elsewhere. Only ``settings_file`` names it, and the tests
replace that function, so that no test reads or writes the settings of the
person who runs them. From v2.2.0 (stage M1) the marks of the view page are
another file in the same folder, which ``marks_file`` names from the place
of the settings.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from ..common.private_files import PRIVATE_DIRECTORY_MODE

DEFAULT_FOLDER_NAME = "GarminRunningData"
STORE_FOLDER_NAME = "snapshots"
# This app's folder of settings and its one file (stage B4c).
SETTINGS_FOLDER_NAME = "garmin-running-data-normalizer"
SETTINGS_FILE_NAME = "gui-settings.json"
# The marks of the view page, in a file of their own (stage M1 of v2.2.0).
MARKS_FILE_NAME = "gui-marks.json"
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


def _absolute_value(value: str | None) -> Path | None:
    """A place that a variable of the environment gives, when it is absolute;
    an empty or relative one counts as not given, as the XDG Base Directory
    Specification says."""
    if not value:
        return None
    place = Path(value)
    return place if place.is_absolute() else None


def settings_file_for(platform: str, environ: Mapping[str, str], home_folder: Path) -> Path:
    """Where the settings of an earlier launch are, for a system (stage
    B4c): in this app's folder in Application Support on a Mac, in
    LOCALAPPDATA on Windows (or AppData/Local in the home folder), and in
    XDG_STATE_HOME elsewhere (or .local/state in the home folder)."""
    if platform == "darwin":
        base = home_folder / "Library" / "Application Support"
    elif platform == "win32":
        base = _absolute_value(environ.get("LOCALAPPDATA")) or home_folder / "AppData" / "Local"
    else:
        base = _absolute_value(environ.get("XDG_STATE_HOME")) or home_folder / ".local" / "state"
    return base / SETTINGS_FOLDER_NAME / SETTINGS_FILE_NAME


def settings_file() -> Path:
    """The file of the settings of an earlier launch on this computer (stage
    B4c). Tests replace this function."""
    return settings_file_for(sys.platform, os.environ, home())


def marks_file() -> Path:
    """The file of the marks of the view page, in this app's folder of
    settings (stage M1 of v2.2.0): it follows ``settings_file``, so that the
    tests that replace that function keep the marks in their folder too."""
    return settings_file().with_name(MARKS_FILE_NAME)


def makeable_settings_folders(path: Path, platform: str = sys.platform) -> tuple[Path, ...]:
    """The folders above this app's folder of settings that may be made when
    they are missing (stage B4c): on systems other than a Mac and Windows,
    .local and .local/state in the home folder, which the XDG Base Directory
    Specification asks an app to make, when the file is in that state home;
    no other folder, as the place that the system keeps is there or is not
    this app's to make."""
    if platform in ("darwin", "win32"):
        return ()
    state = home() / ".local" / "state"
    if path.parent.parent != state:
        return ()
    return (state.parent, state)


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
    "MARKS_FILE_NAME",
    "SETTINGS_FILE_NAME",
    "SETTINGS_FOLDER_NAME",
    "STORE_FOLDER_NAME",
    "cloud_kind",
    "default_folder",
    "default_store",
    "home",
    "make_default_folder",
    "makeable_settings_folders",
    "marks_file",
    "settings_file",
    "settings_file_for",
]
