from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from .archive import ArchiveLimits, read_member, validated_members


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
    base = Path(root).resolve()
    if not base.is_dir():
        raise FileNotFoundError(f"Garmin export directory does not exist: {root}")
    assets: list[DiscoveredAsset] = []
    for path in sorted(candidate for candidate in base.rglob("*") if candidate.is_file()):
        relative = path.relative_to(base).as_posix()
        if path.is_symlink():
            raise ValueError(f"symbolic-link inputs are not supported: {relative}")
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_SUFFIXES:
            data = path.read_bytes()
            if len(data) > limits.max_member_bytes:
                raise ValueError(f"input file exceeds size limit: {relative}")
            assets.append(DiscoveredAsset(suffix[1:], relative, None, len(data), _digest(data), data))
        elif suffix == ".zip":
            with ZipFile(path, "r") as archive:
                for info in validated_members(archive, limits):
                    member_suffix = Path(info.filename).suffix.lower()
                    if member_suffix not in SUPPORTED_SUFFIXES:
                        continue
                    data = read_member(archive, info, limits)
                    assets.append(
                        DiscoveredAsset(member_suffix[1:], relative, info.filename, len(data), _digest(data), data)
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
