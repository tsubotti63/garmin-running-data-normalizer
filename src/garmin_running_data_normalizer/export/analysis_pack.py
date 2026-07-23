from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

ALLOWED_SUFFIXES = {".csv", ".json", ".md"}
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(root: Path, candidate: str | Path) -> tuple[Path, str]:
    requested = PurePosixPath(str(candidate).replace("\\", "/"))
    if requested.is_absolute() or ".." in requested.parts or not requested.parts:
        raise ValueError(f"unsafe Analysis Pack path: {candidate}")
    absolute = (root / Path(*requested.parts)).resolve()
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Analysis Pack path escapes root: {candidate}") from exc
    if absolute.is_symlink() or not absolute.is_file():
        raise ValueError(f"Analysis Pack input must be a regular file: {candidate}")
    if absolute.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"Analysis Pack file type is not allowlisted: {candidate}")
    return absolute, relative


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def build_analysis_pack_payloads(payloads: Mapping[str, bytes]) -> tuple[bytes, dict[str, Any]]:
    """Build deterministic Analysis Pack bytes from an explicit in-memory allowlist."""
    if not payloads:
        raise ValueError("Analysis Pack payload allowlist must not be empty")
    selected: list[tuple[str, bytes]] = []
    for raw_path in sorted(payloads):
        requested = PurePosixPath(str(raw_path).replace("\\", "/"))
        if requested.is_absolute() or ".." in requested.parts or not requested.parts:
            raise ValueError(f"unsafe Analysis Pack path: {raw_path}")
        relative = requested.as_posix()
        if requested.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"Analysis Pack file type is not allowlisted: {raw_path}")
        data = payloads[raw_path]
        if not isinstance(data, bytes):
            raise TypeError("Analysis Pack payloads must be bytes")
        selected.append((relative, data))
    entries = [
        {"path": path, "bytes": len(data), "sha256": _sha256(data)}
        for path, data in selected
    ]
    manifest = {
        "format": "garmin-running-data-normalizer-analysis-pack-v1",
        "deterministic": True,
        "entries": entries,
    }
    manifest_data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        _write_entry(archive, "manifest.json", manifest_data)
        for relative, data in selected:
            _write_entry(archive, relative, data)
    pack = stream.getvalue()
    return pack, {**manifest, "pack_sha256": _sha256(pack)}


def build_analysis_pack(
    root: str | Path,
    include: list[str],
    output_path: str | Path,
) -> dict[str, Any]:
    """Build a deterministic ZIP from an explicit relative-path allowlist."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise FileNotFoundError(root)
    if not include:
        raise ValueError("Analysis Pack include allowlist must not be empty")
    selected = [_safe_relative(base, value) for value in sorted(set(include))]
    payloads: dict[str, bytes] = {}
    for absolute, relative in selected:
        data = absolute.read_bytes()
        payloads[relative] = data
    pack, result = build_analysis_pack_payloads(payloads)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pack)
    return result


__all__ = ["build_analysis_pack", "build_analysis_pack_payloads"]
