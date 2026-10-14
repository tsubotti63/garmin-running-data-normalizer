"""Find and read the JSON and FIT files of a Garmin Export.

``read_export`` reads every file once, in parts, for its size and SHA-256
digest, and keeps nothing else; an asset reads its content again when its
``data`` is used, one file at a time, while the reading is open. A file whose
content then differs from the first reading marks the reading as changed.
``discover_export`` keeps every file's content, for callers that use the assets
after the reading is closed. The Export to read is chosen in the input as
``roots.open_export`` describes.

A file that cannot be read is left out with a reason, and the reading goes on
(stage A3c): a ZIP file in the Export that cannot be opened, holds a damaged
or unsafe member, or exceeds the limits for a ZIP file; a JSON or FIT file
larger than the limit for one file; and, when it is parsed, a JSON file that
is not UTF-8 or not JSON. A JSON file over the limit that no dataset reads is
not left out but only listed as not read. Problems of the Export ZIP file
itself still stop.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Iterator
from zipfile import ZipInfo

from ..common.text import repair_json_text
from .archive import (
    ArchiveLimitError,
    ArchiveLimits,
    MemberTooLargeError,
    UnsafeArchiveError,
    digest_member,
    read_member,
    validated_members,
)
from .roots import ExportView, open_export
from .source import DAMAGED_ZIP_ERRORS, ExportFile, ExportTooLargeError


SUPPORTED_SUFFIXES = {".json", ".fit"}

# Why a file was left out (stage A3c).
JSON_NOT_READABLE = "json_not_readable"
ZIP_NOT_READABLE = "zip_not_readable"
ZIP_UNSAFE_MEMBER = "zip_unsafe_member"
ZIP_TOO_LARGE = "zip_too_large"
FILE_TOO_LARGE = "file_too_large"


class InputChangedError(Exception):
    """Raised when an Export file differs from its first reading in the same run."""


class DiscoveredAsset:
    """One JSON or FIT file of the Export: its place, size, and content digest.

    ``data`` is the file's content. An asset from ``discover_export`` holds it.
    An asset from ``read_export`` reads it again each time ``data`` is used,
    while the reading is open, and does not keep it.
    """

    __slots__ = (
        "kind",
        "source_path",
        "member_path",
        "size_bytes",
        "sha256",
        "_data",
        "_load",
        "_leave_out",
        "_repaired_text_count",
    )

    def __init__(
        self,
        kind: str,
        source_path: str,
        member_path: str | None,
        size_bytes: int,
        sha256: str,
        data: bytes | None = None,
        *,
        load: Callable[[], bytes] | None = None,
        leave_out: Callable[[str, int, str], None] | None = None,
    ) -> None:
        self.kind = kind
        self.source_path = source_path
        self.member_path = member_path
        self.size_bytes = size_bytes
        self.sha256 = sha256
        self._data = data
        self._load = load
        self._leave_out = leave_out
        self._repaired_text_count: int | None = None

    @property
    def data(self) -> bytes:
        if self._data is not None:
            return self._data
        if self._load is None:
            raise ValueError("the content of this asset is not available")
        return self._load()

    @property
    def provenance_path(self) -> str:
        return f"{self.source_path}!{self.member_path}" if self.member_path else self.source_path

    def leave_out(self, reason: str) -> None:
        """Record that this file is left out, with the reason, in its reading."""
        if self._leave_out is not None:
            self._leave_out(self.provenance_path, self.size_bytes, reason)

    @property
    def repaired_text_count(self) -> int | None:
        """The texts and names with a lone surrogate that reading this JSON
        file repaired, or None before it is read (stage A3d-2c-1)."""
        return self._repaired_text_count

    def __repr__(self) -> str:
        return f"DiscoveredAsset({self.kind!r}, {self.provenance_path!r}, {self.size_bytes})"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def path_family(path: str) -> str:
    """Return the source family of an Export file from its path.

    A member of a ZIP file in the Export is named ``inner.zip!member``. A file
    that no dataset reads, such as a ZIP file, is ``unclassified``.
    """
    from ..diagnostics.detector import classify_source_name

    logical_name = path.split("!", 1)[1] if "!" in path else path
    kind = PurePosixPath(logical_name).suffix.lower().lstrip(".")
    return classify_source_name(logical_name, kind)


def _is_read(info: ZipInfo) -> bool:
    return Path(info.filename).suffix.lower() in SUPPORTED_SUFFIXES


class ExportReading:
    """The JSON and FIT files of one open Export, read once for their digests.

    ZIP files in the Export are read one level deep; within them, only JSON and
    FIT members are read, and only those members count against the limits.
    ``same_export_count`` is the number of other copies of the same Export in
    the input, which are not read, and ``outside_files`` are the files outside
    the Export, as (path, bytes), which are not read either. ``left_out``
    lists the files that could not be read, as (path, bytes, reason), in the
    order they were found; a JSON file joins it when it is parsed.
    ``not_read`` lists, in the same form, the JSON files over the limit for
    one file that no dataset reads: they are not read, and nothing is left
    out of the datasets for them (stage A3c).
    """

    def __init__(self, source: ExportView, *, keep_data: bool) -> None:
        self._source = source
        self.changed = False
        self.same_export_count = 0
        self.outside_files: list[tuple[str, int]] = []
        self.left_out: list[tuple[str, int, str]] = []
        self.not_read: list[tuple[str, int, str]] = []
        self.assets = self._index(keep_data)

    def _record_left_out(self, path: str, size: int, reason: str) -> None:
        if all(item[0] != path for item in self.left_out):
            self.left_out.append((path, size, reason))

    def _record_too_large(self, path: str, size: int) -> None:
        """Record a file over the limit for one file, which is not read.

        It is left out when a dataset reads files of its kind, and otherwise
        only listed as not read.
        """
        if path_family(path) == "unclassified":
            self.not_read.append((path, size, FILE_TOO_LARGE))
        else:
            self._record_left_out(path, size, FILE_TOO_LARGE)

    def _index(self, keep_data: bool) -> list[DiscoveredAsset]:
        source = self._source
        limits = source.limits
        assets: list[DiscoveredAsset] = []
        for item in source.files():
            if item.suffix in SUPPORTED_SUFFIXES:
                if item.size > limits.max_member_bytes:
                    self._record_too_large(item.relative_path, item.size)
                    continue
                if keep_data:
                    data: bytes | None = source.read(item)
                    digest, size = _digest(data), len(data)
                else:
                    data = None
                    digest, size = source.digest(item)
                source.count_read(size)
                assets.append(self._asset(item.suffix[1:], item, None, size, digest, data))
            elif item.suffix == ".zip":
                assets.extend(self._zip_assets(item, keep_data))
        return sorted(assets, key=lambda asset: asset.provenance_path)

    def _zip_assets(self, item: ExportFile, keep_data: bool) -> list[DiscoveredAsset]:
        """Return the read members of one ZIP file in the Export.

        A ZIP file that cannot be opened, holds a damaged member, holds a
        member that fails a safety check, or exceeds the limits for one ZIP
        file is left out whole: its members are read in memory and never
        written out, so leaving it out is safe. A member larger than the
        limit for one file is not read, alone. A ZIP file in an Export ZIP
        file that is too large to copy out is left out; the other problems
        of the Export ZIP file itself, and its totals, still stop.
        """
        source = self._source
        limits = source.limits
        try:
            source.local_path(item)
        except MemberTooLargeError:
            self._record_left_out(item.relative_path, item.size, ZIP_TOO_LARGE)
            return []
        found: list[DiscoveredAsset] = []
        oversize: list[ZipInfo] = []
        try:
            archive = source.archive(item)
            for info in validated_members(archive, limits, reads=_is_read, oversize=oversize):
                if keep_data:
                    data = read_member(archive, info, limits)
                    digest, size = _digest(data), len(data)
                else:
                    data = None
                    digest, size = digest_member(archive, info, limits)
                source.count_read(size)
                kind = Path(info.filename).suffix.lower()[1:]
                found.append(self._asset(kind, item, info, size, digest, data))
        except ExportTooLargeError:
            raise
        except DAMAGED_ZIP_ERRORS:
            self._record_left_out(item.relative_path, item.size, ZIP_NOT_READABLE)
            return []
        except ArchiveLimitError:
            self._record_left_out(item.relative_path, item.size, ZIP_TOO_LARGE)
            return []
        except UnsafeArchiveError:
            self._record_left_out(item.relative_path, item.size, ZIP_UNSAFE_MEMBER)
            return []
        for info in oversize:
            self._record_too_large(f"{item.relative_path}!{info.filename}", info.file_size)
        return found

    def _asset(
        self,
        kind: str,
        item: ExportFile,
        info: ZipInfo | None,
        size: int,
        digest: str,
        data: bytes | None,
    ) -> DiscoveredAsset:
        member_path = None if info is None else info.filename
        if data is not None:
            return DiscoveredAsset(
                kind,
                item.relative_path,
                member_path,
                size,
                digest,
                data,
                leave_out=self._record_left_out,
            )
        return DiscoveredAsset(
            kind,
            item.relative_path,
            member_path,
            size,
            digest,
            load=lambda: self._load(item, info, digest),
            leave_out=self._record_left_out,
        )

    def _load(self, item: ExportFile, info: ZipInfo | None, digest: str) -> bytes:
        source = self._source
        try:
            if info is None:
                data = source.read(item)
            else:
                data = read_member(source.archive(item), info, source.limits)
        except Exception as exc:
            self.changed = True
            raise InputChangedError("an Export file could not be read again") from exc
        if _digest(data) != digest:
            self.changed = True
            raise InputChangedError("an Export file changed during the run")
        return data


@contextmanager
def read_export(
    root: str | Path,
    limits: ArchiveLimits = ArchiveLimits(),
    *,
    keep_data: bool = False,
) -> Iterator[ExportReading]:
    """Open an Export folder or Export ZIP file and list its JSON and FIT files.

    Raises ``MixedExportsError`` when the input holds different Exports.
    """
    with open_export(root, limits) as opened:
        reading = ExportReading(opened.source, keep_data=keep_data)
        reading.same_export_count = opened.same_export_count
        reading.outside_files = list(opened.outside_files)
        yield reading


def _read_json(asset: DiscoveredAsset) -> tuple[bool, Any]:
    """Read a JSON file and repair its text with a lone surrogate, counting
    the texts and names repaired on the asset, once however often it is read."""
    try:
        text = asset.data.decode("utf-8-sig")
        # json.loads raises ValueError only for text that is not JSON
        # (JSONDecodeError) or a number too long to convert.
        value, repaired = repair_json_text(text, json.loads(text))
    except (ValueError, RecursionError):
        return False, None
    asset._repaired_text_count = repaired
    return True, value


def parse_json_asset(asset: DiscoveredAsset) -> tuple[bool, Any]:
    """Parse a JSON file; return whether it could be read, and its value.

    A file that is not UTF-8 (a byte order mark is accepted), is not JSON,
    nests too deeply, or holds a number too long to convert is left out
    with the reason ``json_not_readable`` (stage A3c). Only these errors are
    caught; any other error, such as a file that changed during the run,
    still stops the run. Text with a lone UTF-16 surrogate, such as a
    truncated emoji, is written with U+FFFD in its place, and the asset
    counts the texts and names repaired (stage A3d-2c-1).
    """
    readable, value = _read_json(asset)
    if not readable:
        asset.leave_out(JSON_NOT_READABLE)
    return readable, value


def repaired_text_count(asset: DiscoveredAsset) -> int:
    """Return the texts and names that reading this JSON file repairs.

    A file that no dataset parsed is read here for the count only: a file
    that cannot be read counts none and is not left out, so that the count
    changes nothing else.
    """
    if asset.repaired_text_count is None:
        _read_json(asset)
    return asset.repaired_text_count or 0


def discover_export(root: str | Path, limits: ArchiveLimits = ArchiveLimits()) -> list[DiscoveredAsset]:
    """Read the JSON and FIT files of an Export folder or Export ZIP file, with their content."""
    with read_export(root, limits, keep_data=True) as reading:
        return reading.assets


def load_json_assets(
    root: str | Path,
    *,
    filename_suffix: str,
    assets: Iterable[DiscoveredAsset] | None = None,
) -> list[tuple[Any, DiscoveredAsset]]:
    """Load the JSON files whose names end in ``filename_suffix``.

    ``assets``, when given, are the Export's files from an open reading; the
    Export at ``root`` is not read again.
    """
    loaded: list[tuple[Any, DiscoveredAsset]] = []
    for asset in discover_export(root) if assets is None else assets:
        logical_name = asset.member_path or asset.source_path
        if asset.kind != "json" or not logical_name.endswith(filename_suffix):
            continue
        readable, value = parse_json_asset(asset)
        if readable:
            loaded.append((value, asset))
    return loaded


__all__ = [
    "DiscoveredAsset",
    "ExportReading",
    "FILE_TOO_LARGE",
    "InputChangedError",
    "JSON_NOT_READABLE",
    "SUPPORTED_SUFFIXES",
    "ZIP_NOT_READABLE",
    "ZIP_TOO_LARGE",
    "ZIP_UNSAFE_MEMBER",
    "discover_export",
    "load_json_assets",
    "parse_json_asset",
    "repaired_text_count",
    "path_family",
    "read_export",
]
