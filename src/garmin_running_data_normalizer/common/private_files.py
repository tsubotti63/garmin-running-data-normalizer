"""Owner-only directories and files for private Product output."""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def ensure_private_directory(directory: Path) -> None:
    """Create every missing directory down to *directory* as owner-only.

    Existing directories keep their permissions. Modes are applied with an
    explicit chmod so that the process umask cannot widen them; Windows
    ignores POSIX modes.
    """
    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        current = current.parent
    for path in reversed(missing):
        path.mkdir(mode=PRIVATE_DIRECTORY_MODE)
        path.chmod(PRIVATE_DIRECTORY_MODE)


def open_private_file(path: Path) -> BinaryIO:
    """Create a new owner-only binary file regardless of the process umask."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, PRIVATE_FILE_MODE)
        return os.fdopen(descriptor, "wb")
    except BaseException:
        os.close(descriptor)
        raise
