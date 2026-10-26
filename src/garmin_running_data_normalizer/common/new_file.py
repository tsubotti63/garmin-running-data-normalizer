"""A new file that this app writes beside an output (stage G2): its folder
must be there, as no folder is made (decision 20261016-13), it is never
inside the output, whose checks it would fail, and nothing that is there
already is replaced, not even a file put there after the place was checked.

The Support Bundle had these rules (stages A5b-2 and B5a). Stage G2 moved
them here without changing them, so that the CSV file of the series command
follows them as well; each caller gives the codes of its stops.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path


class NewFileError(Exception):
    """Why a new file was not made: ``parent`` (its folder is not there),
    ``inside`` (its place is inside the folder that it must stay out of),
    ``exists`` (a file or a link is in its place), or ``not_written``."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def inside(folder: Path, root: Path) -> bool:
    """Whether ``folder`` is ``root`` or inside it, as the system finds the
    two, through links and the case of the names."""
    for place in (Path(os.path.realpath(folder)), *Path(os.path.realpath(folder)).parents):
        try:
            if os.path.samefile(place, root):
                return True
        except OSError:
            continue
    return False


def check_new_file_place(outside: Path, destination: Path) -> None:
    """The place of a new file: its folder must be there, never inside
    ``outside``, and nothing may be there already."""
    parent = destination.parent
    if not parent.is_dir():
        raise NewFileError("parent")
    if inside(parent, outside):
        raise NewFileError("inside")
    if destination.is_symlink() or destination.exists():
        raise NewFileError("exists")


def put_in_place(temporary: Path, destination: Path) -> None:
    """Give the written file its name without replacing what is there,
    also a file put there since the place was checked: a hard link fails
    when the name is taken, and where the disk makes no hard links, the
    file is copied into a file that only a new name can be."""
    try:
        os.link(temporary, destination)
        return
    except FileExistsError as exc:
        raise NewFileError("exists") from exc
    except OSError:
        pass
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(destination, flags, 0o600)
    except FileExistsError as exc:
        raise NewFileError("exists") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(temporary.read_bytes())
    except BaseException:
        # The copy is this command's own file, made with its new name.
        destination.unlink(missing_ok=True)
        raise


def write_new_file(
    destination: Path,
    data: bytes,
    *,
    put_in_place: Callable[[Path, Path], None] = put_in_place,
) -> None:
    """Write ``data`` beside its place under a temporary name, which only the
    owner may read on macOS and Linux (Windows gives it the permissions of
    its folder), and give it its name in one step that never replaces a
    file. The temporary name goes, also on Ctrl+C; a file that another
    program put in the place stays. ``put_in_place`` gives the file its
    name; the Support Bundle gives its own name for it, which its tests
    replace."""
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    except OSError as exc:
        raise NewFileError("not_written") from exc
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(data)
        put_in_place(temporary, destination)
    except OSError as exc:
        raise NewFileError("not_written") from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = ["NewFileError", "check_new_file_place", "inside", "put_in_place", "write_new_file"]
