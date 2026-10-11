"""Find and read the JSON and FIT files of a Garmin Export.

``read_export`` reads every file once, in parts, for its size and SHA-256
digest, and keeps nothing else; an asset reads its content again when its
``data`` is used, one file at a time, while the reading is open. A file whose
content then differs from the first reading marks the reading as changed.
``discover_export`` keeps every file's content, for callers that use the assets
after the reading is closed.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator
from zipfile import ZipInfo

from .archive import ArchiveLimits, digest_member, read_member, validated_members
from .source import ExportFile, ExportSource


SUPPORTED_SUFFIXES = {".json", ".fit"}


class InputChangedError(Exception):
    """Raised when an Export file differs from its first reading in the same run."""


class DiscoveredAsset:
    """One JSON or FIT file of the Export: its place, size, and content digest.

    ``data`` is the file's content. An asset from ``discover_export`` holds it.
    An asset from ``read_export`` reads it again each time ``data`` is used,
    while the reading is open, and does not keep it.
    """

    __slots__ = ("kind", "source_path", "member_path", "size_bytes", "sha256", "_data", "_load")

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
    ) -> None:
        self.kind = kind
        self.source_path = source_path
        self.member_path = member_path
        self.size_bytes = size_bytes
        self.sha256 = sha256
        self._data = data
        self._load = load

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

    def __repr__(self) -> str:
        return f"DiscoveredAsset({self.kind!r}, {self.provenance_path!r}, {self.size_bytes})"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_read(info: ZipInfo) -> bool:
    return Path(info.filename).suffix.lower() in SUPPORTED_SUFFIXES


class ExportReading:
    """The JSON and FIT files of one open Export, read once for their digests.

    ZIP files in the Export are read one level deep; within them, only JSON and
    FIT members are read, and only those members count against the limits.
    """

    def __init__(self, source: ExportSource, *, keep_data: bool) -> None:
        self._source = source
        self.changed = False
        self.assets = self._index(keep_data)

    def _index(self, keep_data: bool) -> list[DiscoveredAsset]:
        source = self._source
        limits = source.limits
        assets: list[DiscoveredAsset] = []
        for item in source.files():
            if item.suffix in SUPPORTED_SUFFIXES:
                if keep_data:
                    data: bytes | None = source.read(item)
                    digest, size = _digest(data), len(data)
                else:
                    data = None
                    digest, size = source.digest(item)
                source.count_read(size)
                assets.append(self._asset(item.suffix[1:], item, None, size, digest, data))
            elif item.suffix == ".zip":
                archive = source.archive(item)
                for info in validated_members(archive, limits, reads=_is_read):
                    if keep_data:
                        data = read_member(archive, info, limits)
                        digest, size = _digest(data), len(data)
                    else:
                        data = None
                        digest, size = digest_member(archive, info, limits)
                    source.count_read(size)
                    kind = Path(info.filename).suffix.lower()[1:]
                    assets.append(self._asset(kind, item, info, size, digest, data))
        return sorted(assets, key=lambda asset: asset.provenance_path)

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
            return DiscoveredAsset(kind, item.relative_path, member_path, size, digest, data)
        return DiscoveredAsset(
            kind,
            item.relative_path,
            member_path,
            size,
            digest,
            load=lambda: self._load(item, info, digest),
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
    """Open an Export folder or Export ZIP file and list its JSON and FIT files."""
    with ExportSource(root, limits) as source:
        yield ExportReading(source, keep_data=keep_data)


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
        loaded.append((json.loads(asset.data.decode("utf-8")), asset))
    return loaded


__all__ = [
    "DiscoveredAsset",
    "ExportReading",
    "InputChangedError",
    "SUPPORTED_SUFFIXES",
    "discover_export",
    "load_json_assets",
    "read_export",
]
