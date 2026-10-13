"""Read a Garmin Export from its extracted folder or from its downloaded ZIP file.

A ZIP file is read as if it were the folder extracted from it: the same Export
gives the same files, the same paths, and therefore the same assets, the same
provenance, and the same Snapshot inventory in either form. Folders around the
Export are left out of the paths: while everything sits inside one folder that
is not part of the Export's own layout (as when an extracted folder is
compressed again, or when a folder above it is selected), the root moves into
that folder, in a ZIP file and in a folder alike and at any depth.

Files are read one at a time and are not kept. A ZIP file inside an Export ZIP
file is copied, when it is first used, to a private temporary folder, and stays
open until the Export is closed; a ZIP file inside a folder is opened in place.
"""

from __future__ import annotations

import errno
import hashlib
import shutil
import tempfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterator
from zipfile import BadZipFile, ZipFile, ZipInfo

from ..common.os_metadata import is_os_metadata_path
from .archive import (
    ArchiveLimits,
    UnsafeArchiveError,
    check_member_size,
    is_safe_export_member,
)

# Folders that belong to the Export's own layout, compared in lower case.
_LAYOUT_FOLDERS = frozenset({"di_connect", "di-golf"})
_LAYOUT_FOLDER_PREFIX = "di-connect-"

# Python errors that mean that bytes in a ZIP file are damaged or incomplete.
DAMAGED_ZIP_ERRORS = (BadZipFile, EOFError, zlib.error)

# Free space to leave in the temporary folder beyond the copies themselves.
_TEMPORARY_SPACE_MARGIN = 64 * 1024 * 1024
_CHUNK_BYTES = 1024 * 1024


class CorruptArchiveError(ValueError):
    """Raised when the Export ZIP file is damaged or incomplete."""


class ExportTooLargeError(UnsafeArchiveError):
    """Raised when an Export ZIP file holds more than one reading of it may read."""


class TempSpaceError(Exception):
    """Raised when the temporary folder cannot hold the copies of the ZIP
    files inside an Export ZIP file."""


def is_zip_input(path: Path) -> bool:
    """Return whether ``path`` is a ZIP file given as the Export (not a folder)."""
    return path.is_file() and path.suffix.lower() == ".zip"


def is_layout_folder(name: str) -> bool:
    """Return whether a folder name belongs to the Export's own layout."""
    lower = name.lower()
    return lower in _LAYOUT_FOLDERS or lower.startswith(_LAYOUT_FOLDER_PREFIX)


def _is_disk_full(error: OSError) -> bool:
    # ERROR_HANDLE_DISK_FULL and ERROR_DISK_FULL on Windows.
    return error.errno == errno.ENOSPC or getattr(error, "winerror", None) in (39, 112)


@dataclass(frozen=True)
class ExportFile:
    """One file of the Export: a file in the folder or a member of the ZIP."""

    relative_path: str
    size: int
    path: Path | None = None
    member: ZipInfo | None = None

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.relative_path).suffix.lower()


class ExportSource:
    """Open an Export given as a folder or a ZIP file; use it as a context manager."""

    def __init__(self, root: str | Path, limits: ArchiveLimits = ArchiveLimits()) -> None:
        self.root = Path(root).resolve()
        self.limits = limits
        self.is_zip = is_zip_input(self.root)
        if not self.is_zip and not self.root.is_dir():
            raise FileNotFoundError("Garmin Export folder or ZIP file does not exist")
        self._archive: ZipFile | None = None
        self._nested: dict[str, ZipFile] = {}
        self._local: dict[str, Path] = {}
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self._space_checked = False
        self._files: list[ExportFile] = []
        self._read_files = 0
        self._read_bytes = 0
        self._copies = 0

    def __enter__(self) -> "ExportSource":
        try:
            if self.is_zip:
                self._files = self._zip_files()
            else:
                self._files = self._folder_files()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        # Close every open ZIP file before removing the temporary folder:
        # Windows cannot remove a folder that holds an open file.
        nested, self._nested = self._nested, {}
        for archive in nested.values():
            archive.close()
        if self._archive is not None:
            self._archive.close()
            self._archive = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def files(self) -> list[ExportFile]:
        return list(self._files)

    def _folder_files(self) -> list[ExportFile]:
        base = self.root
        while True:
            children = [
                child for child in base.iterdir() if not is_os_metadata_path(child.name)
            ]
            if not (
                len(children) == 1
                and children[0].is_dir()
                and not children[0].is_symlink()
                and not is_layout_folder(children[0].name)
            ):
                break
            base = children[0]
        files: list[ExportFile] = []
        for path in sorted(
            candidate for candidate in base.rglob("*") if candidate.is_file()
        ):
            relative = path.relative_to(base).as_posix()
            if path.is_symlink():
                raise ValueError(f"symbolic-link inputs are not supported: {relative}")
            if is_os_metadata_path(relative):
                continue
            files.append(ExportFile(relative, path.stat().st_size, path=path))
        return files

    def _zip_files(self) -> list[ExportFile]:
        try:
            self._archive = ZipFile(self.root, "r")
            members = [
                info
                for info in self._archive.infolist()
                if is_safe_export_member(info)
            ]
        except DAMAGED_ZIP_ERRORS as exc:
            raise CorruptArchiveError("the Export ZIP file is damaged or incomplete") from exc
        names = [PurePosixPath(info.filename).parts for info in members]
        prefix_parts = 0
        while names and all(len(parts) > prefix_parts + 1 for parts in names):
            tops = {parts[prefix_parts] for parts in names}
            if len(tops) != 1 or is_layout_folder(next(iter(tops))):
                break
            prefix_parts += 1
        files = [
            ExportFile(
                PurePosixPath(*parts[prefix_parts:]).as_posix(),
                info.file_size,
                member=info,
            )
            for info, parts in zip(members, names)
        ]
        # The same order as the files of a folder, which are sorted as paths:
        # a Snapshot inventory keeps this order.
        return sorted(files, key=lambda item: Path(item.relative_path))

    def count_read(self, size: int) -> None:
        """Count one file read from the Export; enforce the totals for a ZIP input."""
        self._read_files += 1
        self._read_bytes += size
        if not self.is_zip:
            return
        if self._read_files > self.limits.max_export_read_files:
            raise ExportTooLargeError("the Export ZIP file holds too many files to read directly")
        if self._read_bytes > self.limits.max_export_read_bytes:
            raise ExportTooLargeError("the Export ZIP file is too large to read directly")

    def read(self, item: ExportFile) -> bytes:
        """Read one Export file whole, within the size limit for one file."""
        if item.member is None:
            assert item.path is not None
            data = item.path.read_bytes()
            if len(data) > self.limits.max_member_bytes:
                raise ValueError(f"input file exceeds size limit: {item.relative_path}")
            return data
        check_member_size(item.member, self.limits.max_member_bytes, self.limits)
        return self._read_member(item.member, self.limits.max_member_bytes)

    def digest(self, item: ExportFile) -> tuple[str, int]:
        """Return one Export file's SHA-256 digest and size, reading it in parts.

        The checks are those of ``read``, without holding the file.
        """
        maximum = self.limits.max_member_bytes
        if item.member is not None:
            check_member_size(item.member, maximum, self.limits)
        digest = hashlib.sha256()
        size = 0
        with self.open_stream(item) as handle:
            while size <= maximum and (chunk := handle.read(_CHUNK_BYTES)):
                digest.update(chunk)
                size += len(chunk)
        if item.member is None:
            if size > maximum:
                raise ValueError(f"input file exceeds size limit: {item.relative_path}")
        elif size != item.member.file_size or size > maximum:
            raise CorruptArchiveError("the Export ZIP file is damaged or incomplete")
        return digest.hexdigest(), size

    def _read_member(self, info: ZipInfo, max_bytes: int) -> bytes:
        assert self._archive is not None
        try:
            with self._archive.open(info, "r") as handle:
                data = handle.read(max_bytes + 1)
        except DAMAGED_ZIP_ERRORS as exc:
            raise CorruptArchiveError("the Export ZIP file is damaged or incomplete") from exc
        if len(data) != info.file_size or len(data) > max_bytes:
            raise CorruptArchiveError("the Export ZIP file is damaged or incomplete")
        return data

    @contextmanager
    def open_stream(self, item: ExportFile) -> Iterator[BinaryIO]:
        """Open one Export file for streaming, as for hashing or copying it."""
        if item.member is None:
            assert item.path is not None
            with item.path.open("rb") as handle:
                yield handle
            return
        assert self._archive is not None
        try:
            with self._archive.open(item.member, "r") as handle:
                yield handle
        except DAMAGED_ZIP_ERRORS as exc:
            raise CorruptArchiveError("the Export ZIP file is damaged or incomplete") from exc

    def archive(self, item: ExportFile) -> ZipFile:
        """Return a ZIP file found in the Export, opened once until the Export is closed."""
        archive = self._nested.get(item.relative_path)
        if archive is None:
            archive = ZipFile(self.local_path(item), "r")
            self._nested[item.relative_path] = archive
        return archive

    def local_path(self, item: ExportFile) -> Path:
        """Return a path on disk for one Export file.

        A file of a folder is used in place; a member of an Export ZIP file is
        copied once to the private temporary folder, which stays until the
        Export is closed.
        """
        if item.member is None:
            assert item.path is not None
            return item.path
        path = self._local.get(item.relative_path)
        if path is None:
            path = self._copy(item)
            self._local[item.relative_path] = path
        return path

    def _copy(self, item: ExportFile) -> Path:
        """Copy a ZIP file inside the Export ZIP file to the private temporary folder."""
        info = item.member
        assert info is not None
        check_member_size(info, self.limits.max_total_bytes, self.limits)
        if not self._space_checked:
            # Before the first copy, check that every ZIP file inside the
            # Export ZIP file fits, so that a run does not stop halfway.
            needed = sum(entry.size for entry in self._files if entry.suffix == ".zip")
            free = shutil.disk_usage(tempfile.gettempdir()).free
            if free < needed + _TEMPORARY_SPACE_MARGIN:
                raise TempSpaceError("the temporary folder does not have enough free space")
            self._space_checked = True
        if self._temporary is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="garmin-export-zip-")
        self._copies += 1
        copy = Path(self._temporary.name) / f"nested-{self._copies}.zip"
        try:
            with self.open_stream(item) as source, copy.open("xb") as target:
                shutil.copyfileobj(source, target, _CHUNK_BYTES)
        except OSError as exc:
            copy.unlink(missing_ok=True)
            if _is_disk_full(exc):
                raise TempSpaceError("the temporary folder ran out of free space") from exc
            raise
        except BaseException:
            copy.unlink(missing_ok=True)
            raise
        if copy.stat().st_size != info.file_size:
            copy.unlink(missing_ok=True)
            raise CorruptArchiveError("the Export ZIP file is damaged or incomplete")
        return copy


__all__ = [
    "CorruptArchiveError",
    "DAMAGED_ZIP_ERRORS",
    "ExportFile",
    "ExportSource",
    "ExportTooLargeError",
    "TempSpaceError",
    "is_layout_folder",
    "is_zip_input",
]
