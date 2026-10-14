"""Check the place of an output before a run writes it (stage A3d-3a).

Run-All writes its output at the end, by creating a hidden staging folder next
to the output and renaming it, and so does the Golden Path. Checking the same
place before a run starts means that a run that cannot write its output stops
at once, with a code and a next step, instead of after all its work. The GUI
makes the same check before it starts a run, so the CLI and the GUI give the
same codes.
"""

from __future__ import annotations

import errno
import ntpath
import os
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path

from .intake.source import is_disk_full

# Without long paths, Windows limits a file path to 259 characters and a folder
# path to 247, which leaves room for an 8.3 name. Both count UTF-16 units.
WINDOWS_MAX_FILE_PATH = 260
WINDOWS_MAX_FOLDER_PATH = 248
# Run-All's staging folder is ".<name>.run-all-" and 8 random characters.
STAGING_SUFFIX_LENGTH = len(".run-all-") + 8
# The error of Windows for a path that is too long.
_WINDOWS_PATH_TOO_LONG = 206

MESSAGES = {
    "OUTPUT_PARENT_NOT_FOUND": (
        "the place for the output is not a folder; choose an existing folder for the output"
    ),
    "OUTPUT_PARENT_NOT_WRITABLE": (
        "this app cannot write in the folder for the output; choose another folder, "
        "or allow this app to write in it"
    ),
    "OUTPUT_NAME_INVALID": "the output folder name is too long; choose a shorter name",
    "OUTPUT_PATH_TOO_LONG": (
        "the output path is too long; choose a shorter folder or name, or on Windows "
        "turn on long paths"
    ),
    "OUTPUT_SPACE_INSUFFICIENT": (
        "the place for the output does not have enough free space; free some space, "
        "or choose another folder"
    ),
}


class OutputLocationError(Exception):
    """The output cannot be written in its place; ``code`` says why."""

    def __init__(self, code: str) -> None:
        super().__init__(MESSAGES[code])
        self.code = code
        self.safe_message = MESSAGES[code]


def long_paths_enabled() -> bool:
    """Return whether Windows accepts long paths; assume not when unknown."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
    except (ImportError, OSError):
        return False
    return value == 1


def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le", "surrogatepass")) // 2


def windows_paths_too_long(parent: str, name: str, output_paths: Iterable[str]) -> bool:
    """Return whether the deepest paths of this output exceed MAX_PATH.

    The paths are those inside the staging folder, which is longer than the
    output folder; the write check and the Support Bundle's temporary file are
    shorter. ``parent`` is measured in its absolute Windows form.
    """
    base = ntpath.abspath(parent)
    if base.startswith("\\\\?\\"):
        return False  # Such paths have no MAX_PATH limit.
    paths = list(output_paths)
    staging = utf16_length(ntpath.join(base, f".{name}")) + STAGING_SUFFIX_LENGTH
    longest_file = max(len(path) for path in paths)
    longest_folder = max(
        (len(path.rsplit("/", 1)[0]) for path in paths if "/" in path), default=0
    )
    return (
        staging + 1 + longest_file >= WINDOWS_MAX_FILE_PATH
        or staging + 1 + longest_folder >= WINDOWS_MAX_FOLDER_PATH
    )


def output_path_too_long(parent: Path, name: str, output_paths: Iterable[str]) -> bool:
    """Return whether this output cannot be written on this Windows system."""
    if os.name != "nt" or long_paths_enabled():
        return False
    return windows_paths_too_long(str(parent), name, output_paths)


def write_error_code(error: OSError) -> str | None:
    """Return the code for an error met while an output was written, or None
    when it is none of these: no free space, no permission, a path too long."""
    if is_disk_full(error):
        return "OUTPUT_SPACE_INSUFFICIENT"
    if isinstance(error, PermissionError) or error.errno == errno.EROFS:
        return "OUTPUT_PARENT_NOT_WRITABLE"
    if error.errno == errno.ENAMETOOLONG or getattr(error, "winerror", None) == _WINDOWS_PATH_TOO_LONG:
        return "OUTPUT_PATH_TOO_LONG"
    return None


def path_error_code(output: Path, error: OSError) -> str:
    """The code for an error met while the output's path was looked at, as a
    name too long for the system raises on some systems (stage A3d-3a)."""
    if error.errno == errno.ENAMETOOLONG or getattr(error, "winerror", None) == _WINDOWS_PATH_TOO_LONG:
        try:
            name_too_long = len(output.name.encode("utf-8")) > 255
        except UnicodeEncodeError:
            name_too_long = False
        return "OUTPUT_NAME_INVALID" if name_too_long else "OUTPUT_PATH_TOO_LONG"
    return "OUTPUT_PARENT_NOT_WRITABLE"


def check_output_location(output: Path, too_long: Callable[[Path, str], bool]) -> None:
    """Check that a run can write ``output``, before it starts.

    Missing folders above the output are created by Run-All when it writes, so
    the nearest folder that exists is tried, by creating a hidden folder in it
    and removing it at once, as the staging folder will be created; nothing
    else is written. ``too_long`` tells whether the output's deepest paths
    are too long for this system. Raises ``OutputLocationError``.
    """
    parent = output.parent
    place = parent
    try:
        while not place.exists() and place.parent != place:
            place = place.parent
        is_folder = place.is_dir()
    except PermissionError as exc:
        raise OutputLocationError("OUTPUT_PARENT_NOT_WRITABLE") from exc
    if not is_folder:
        raise OutputLocationError("OUTPUT_PARENT_NOT_FOUND")
    if too_long(parent, output.name):
        raise OutputLocationError("OUTPUT_PATH_TOO_LONG")
    prefix = f".{output.name}.write-check-" if place == parent else ".write-check-"
    try:
        probe = tempfile.mkdtemp(prefix=prefix, dir=place)
    except OSError as exc:
        if exc.errno == errno.ENAMETOOLONG:
            # A shorter name fixes this; the folder may well be writable.
            raise OutputLocationError("OUTPUT_NAME_INVALID") from exc
        if is_disk_full(exc):
            raise OutputLocationError("OUTPUT_SPACE_INSUFFICIENT") from exc
        raise OutputLocationError("OUTPUT_PARENT_NOT_WRITABLE") from exc
    try:
        os.rmdir(probe)
    except OSError:
        pass  # At most an empty folder whose name starts with a dot remains.


__all__ = [
    "MESSAGES",
    "OutputLocationError",
    "STAGING_SUFFIX_LENGTH",
    "WINDOWS_MAX_FILE_PATH",
    "WINDOWS_MAX_FOLDER_PATH",
    "check_output_location",
    "long_paths_enabled",
    "output_path_too_long",
    "path_error_code",
    "utf16_length",
    "windows_paths_too_long",
    "write_error_code",
]
