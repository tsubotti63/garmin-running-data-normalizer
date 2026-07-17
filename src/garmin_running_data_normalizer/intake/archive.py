from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
import stat
from zipfile import BadZipFile, ZipFile, ZipInfo


class UnsafeArchiveError(ValueError):
    """Raised when an archive violates the fail-closed intake contract."""


@dataclass(frozen=True)
class ArchiveLimits:
    max_members: int = 10_000
    max_member_bytes: int = 128 * 1024 * 1024
    max_total_bytes: int = 2 * 1024 * 1024 * 1024
    max_compression_ratio: float = 200.0


def is_real_export_file(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return not (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "__MACOSX" in path.parts
        or path.name.startswith("._")
        or path.name == ".DS_Store"
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


def validated_members(archive: ZipFile, limits: ArchiveLimits = ArchiveLimits()) -> list[ZipInfo]:
    members = archive.infolist()
    if len(members) > limits.max_members:
        raise UnsafeArchiveError("archive member count exceeds configured limit")
    accepted: list[ZipInfo] = []
    total = 0
    for info in members:
        if _is_unsafe_path(info.filename):
            raise UnsafeArchiveError(f"unsafe archive member path: {info.filename}")
        mode = info.external_attr >> 16
        if stat.S_IFMT(mode) == stat.S_IFLNK:
            raise UnsafeArchiveError(f"archive symbolic links are not supported: {info.filename}")
        if info.is_dir() or not is_real_export_file(info.filename):
            continue
        if info.flag_bits & 0x1:
            raise UnsafeArchiveError("encrypted archive members are not supported")
        if info.file_size > limits.max_member_bytes:
            raise UnsafeArchiveError(f"archive member exceeds size limit: {info.filename}")
        total += info.file_size
        if total > limits.max_total_bytes:
            raise UnsafeArchiveError("archive expanded size exceeds configured limit")
        if info.file_size and info.compress_size == 0:
            raise UnsafeArchiveError(f"invalid compressed size: {info.filename}")
        if info.compress_size and info.file_size / info.compress_size > limits.max_compression_ratio:
            raise UnsafeArchiveError(f"archive member compression ratio is unsafe: {info.filename}")
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


__all__ = ["ArchiveLimits", "BadZipFile", "UnsafeArchiveError", "is_real_export_file", "read_member", "validated_members"]
