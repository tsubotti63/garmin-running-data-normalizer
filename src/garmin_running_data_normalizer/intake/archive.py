from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
import stat
from typing import Callable
from zipfile import BadZipFile, ZipFile, ZipInfo

from ..common.os_metadata import is_os_metadata_path


MAX_ARCHIVE_MEMBERS = 100_000


class UnsafeArchiveError(ValueError):
    """Raised when an archive violates the fail-closed intake contract."""


@dataclass(frozen=True)
class ArchiveLimits:
    max_members: int = MAX_ARCHIVE_MEMBERS
    max_member_bytes: int = 128 * 1024 * 1024
    max_total_bytes: int = 2 * 1024 * 1024 * 1024
    max_compression_ratio: float = 200.0
    # The files read from an Export given as a ZIP file are held in memory.
    # These bound them in total, until reading no longer needs the whole
    # Export in memory; an extracted folder has no such bound.
    max_export_read_bytes: int = 2 * 1024 * 1024 * 1024
    max_export_read_files: int = 400_000
    # A ZIP file inside the Export ZIP up to this size is opened in memory;
    # a larger one is copied to a private temporary folder first.
    max_nested_in_memory_bytes: int = 128 * 1024 * 1024


def is_real_export_file(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return not (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or is_os_metadata_path(name)
    )


def _is_unsafe_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(name)
    return (
        not name
        or "\x00" in name
        or path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or normalized.startswith("//")
        or ".." in path.parts
    )


def is_safe_export_member(info: ZipInfo) -> bool:
    """Check one archive member for safety; return whether it is an Export file.

    Every member is checked, including members that are never read: an
    unsafe path, a symbolic link, or encryption rejects the whole archive.
    """
    if _is_unsafe_path(info.filename):
        raise UnsafeArchiveError(f"unsafe archive member path: {info.filename}")
    mode = info.external_attr >> 16
    if stat.S_IFMT(mode) == stat.S_IFLNK:
        raise UnsafeArchiveError(f"archive symbolic links are not supported: {info.filename}")
    if info.is_dir() or not is_real_export_file(info.filename):
        return False
    if info.flag_bits & 0x1:
        raise UnsafeArchiveError("encrypted archive members are not supported")
    return True


def check_member_size(info: ZipInfo, max_bytes: int, limits: ArchiveLimits) -> None:
    if info.file_size > max_bytes:
        raise UnsafeArchiveError(f"archive member exceeds size limit: {info.filename}")
    if info.file_size and info.compress_size == 0:
        raise UnsafeArchiveError(f"invalid compressed size: {info.filename}")
    if info.compress_size and info.file_size / info.compress_size > limits.max_compression_ratio:
        raise UnsafeArchiveError(f"archive member compression ratio is unsafe: {info.filename}")


def validated_members(
    archive: ZipFile,
    limits: ArchiveLimits = ArchiveLimits(),
    *,
    reads: Callable[[ZipInfo], bool] | None = None,
) -> list[ZipInfo]:
    """Return the members to read, after checking every member for safety.

    ``reads`` selects the members that the caller reads (by default every
    Export file). The size, count, and compression limits apply only to those
    members, so a large member that is never read does not reject the archive.
    """
    accepted: list[ZipInfo] = []
    total = 0
    for info in archive.infolist():
        if not is_safe_export_member(info):
            continue
        if reads is not None and not reads(info):
            continue
        if len(accepted) >= limits.max_members:
            raise UnsafeArchiveError("archive member count exceeds configured limit")
        check_member_size(info, limits.max_member_bytes, limits)
        total += info.file_size
        if total > limits.max_total_bytes:
            raise UnsafeArchiveError("archive expanded size exceeds configured limit")
        accepted.append(info)
    return accepted


def read_member(archive: ZipFile, info: ZipInfo, limits: ArchiveLimits = ArchiveLimits()) -> bytes:
    if info.file_size > limits.max_member_bytes:
        raise UnsafeArchiveError("archive member exceeds size limit")
    with archive.open(info, "r") as handle:
        data = handle.read(limits.max_member_bytes + 1)
    if len(data) != info.file_size or len(data) > limits.max_member_bytes:
        raise UnsafeArchiveError("archive member size changed or exceeded limit while reading")
    return data


__all__ = [
    "ArchiveLimits",
    "BadZipFile",
    "MAX_ARCHIVE_MEMBERS",
    "UnsafeArchiveError",
    "check_member_size",
    "is_real_export_file",
    "is_safe_export_member",
    "read_member",
    "validated_members",
]
