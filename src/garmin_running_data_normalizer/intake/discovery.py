from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .archive import ArchiveLimits, read_member, validated_members
from .source import ExportSource


SUPPORTED_SUFFIXES = {".json", ".fit"}


@dataclass(frozen=True)
class DiscoveredAsset:
    kind: str
    source_path: str
    member_path: str | None
    size_bytes: int
    sha256: str
    data: bytes

    @property
    def provenance_path(self) -> str:
        return f"{self.source_path}!{self.member_path}" if self.member_path else self.source_path


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def discover_export(root: str | Path, limits: ArchiveLimits = ArchiveLimits()) -> list[DiscoveredAsset]:
    """Read the JSON and FIT files of an Export folder or Export ZIP file.

    ZIP files in the Export are read one level deep; within them, only JSON
    and FIT members are read, and only those members count against the limits.
    """
    assets: list[DiscoveredAsset] = []
    with ExportSource(root, limits) as source:
        for item in source.files():
            if item.suffix in SUPPORTED_SUFFIXES:
                data = source.read(item)
                source.count_read(len(data))
                assets.append(
                    DiscoveredAsset(item.suffix[1:], item.relative_path, None, len(data), _digest(data), data)
                )
            elif item.suffix == ".zip":
                with source.open_archive(item) as archive:
                    for info in validated_members(
                        archive,
                        limits,
                        reads=lambda member: Path(member.filename).suffix.lower() in SUPPORTED_SUFFIXES,
                    ):
                        member_suffix = Path(info.filename).suffix.lower()
                        data = read_member(archive, info, limits)
                        source.count_read(len(data))
                        assets.append(
                            DiscoveredAsset(
                                member_suffix[1:],
                                item.relative_path,
                                info.filename,
                                len(data),
                                _digest(data),
                                data,
                            )
                        )
    return sorted(assets, key=lambda item: item.provenance_path)


def load_json_assets(root: str | Path, *, filename_suffix: str) -> list[tuple[Any, DiscoveredAsset]]:
    loaded: list[tuple[Any, DiscoveredAsset]] = []
    for asset in discover_export(root):
        logical_name = asset.member_path or asset.source_path
        if asset.kind != "json" or not logical_name.endswith(filename_suffix):
            continue
        loaded.append((json.loads(asset.data.decode("utf-8")), asset))
    return loaded
