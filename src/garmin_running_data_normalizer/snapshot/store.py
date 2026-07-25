from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator
from zipfile import BadZipFile, ZipFile

from ..intake.archive import UnsafeArchiveError, read_member, validated_members
from .policies import CONTRACT_VERSION, REGISTRY_VERSION


STORE_FORMAT = "garmin-running-data-normalizer-snapshot-store-v1"
STORE_FORMAT_VERSION = 1
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
ACCOUNT_STORE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SnapshotStoreError(ValueError):
    """Fail-closed snapshot store contract error."""


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_store_symlink_components(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise SnapshotStoreError("snapshot store path escaped its root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise SnapshotStoreError(
                "symbolic links are prohibited inside the snapshot store"
            )


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_write(path, _json_bytes(value))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_aware_iso(value: str, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SnapshotStoreError(f"{label} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SnapshotStoreError(f"{label} must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc).isoformat()


def _logical_time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _validate_account_store_id(value: str) -> str:
    if not ACCOUNT_STORE_ID_RE.fullmatch(value):
        raise SnapshotStoreError(
            "account_store_id must be an opaque 3-128 character token"
        )
    return value


def _validate_label(value: str) -> str:
    if not LABEL_RE.fullmatch(value):
        raise SnapshotStoreError(
            "snapshot label must use 1-64 letters, digits, dot, underscore, or hyphen"
        )
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotStoreError(f"invalid snapshot store metadata: {path.name}") from exc
    if not isinstance(value, dict):
        raise SnapshotStoreError(f"snapshot store metadata must be an object: {path.name}")
    return value


def load_store(store_root: str | Path) -> tuple[Path, dict[str, Any]]:
    requested = Path(store_root)
    if requested.is_symlink():
        raise SnapshotStoreError("snapshot store must not be a symbolic link")
    root = requested.resolve()
    metadata_path = root / "store.json"
    if not metadata_path.is_file():
        raise SnapshotStoreError("snapshot store is not initialized")
    metadata = _load_json(metadata_path)
    if (
        metadata.get("format") != STORE_FORMAT
        or metadata.get("format_version") != STORE_FORMAT_VERSION
        or metadata.get("contract_version") != CONTRACT_VERSION
        or metadata.get("policy_registry_version") != REGISTRY_VERSION
    ):
        raise SnapshotStoreError("snapshot store format is not supported")
    if metadata.get("single_writer") is not True:
        raise SnapshotStoreError("snapshot store single-writer policy is not enabled")
    if metadata.get("automatic_deletion") is not False:
        raise SnapshotStoreError("snapshot store enables automatic deletion")
    if metadata.get("garbage_collection") is not False:
        raise SnapshotStoreError("snapshot store enables garbage collection")
    _validate_account_store_id(str(metadata.get("account_store_id", "")))
    _require_aware_iso(str(metadata.get("created_at_utc", "")), "created_at_utc")
    return root, metadata


def initialize_store(
    store_root: str | Path,
    account_store_id: str,
) -> dict[str, Any]:
    account_id = _validate_account_store_id(account_store_id)
    requested = Path(store_root)
    if requested.is_symlink():
        raise SnapshotStoreError("snapshot store must not be a symbolic link")
    root = requested.resolve()
    metadata_path = root / "store.json"
    if metadata_path.exists():
        existing_root, existing = load_store(root)
        if existing["account_store_id"] != account_id:
            raise SnapshotStoreError("initialized store belongs to another account boundary")
        return {
            "status": "PASS",
            "initialized": False,
            "account_store_id": account_id,
            "snapshot_count": len(load_manifests(existing_root)),
        }
    if root.exists() and any(root.iterdir()):
        raise SnapshotStoreError("new snapshot store directory must be absent or empty")
    for relative in ("blobs/sha256", "snapshots", "journal"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    metadata = {
        "format": STORE_FORMAT,
        "format_version": STORE_FORMAT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "policy_registry_version": REGISTRY_VERSION,
        "account_store_id": account_id,
        "created_at_utc": _now_utc(),
        "single_writer": True,
        "automatic_deletion": False,
        "garbage_collection": False,
    }
    _atomic_json(metadata_path, metadata)
    _write_registry(root, [])
    return {
        "status": "PASS",
        "initialized": True,
        "account_store_id": account_id,
        "snapshot_count": 0,
    }


@contextmanager
def _store_lock(root: Path) -> Iterator[None]:
    lock_path = root / ".single-writer.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SnapshotStoreError("snapshot store is locked by another writer") from exc
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock_path.unlink(missing_ok=True)


def _recover_journal(root: Path) -> str:
    journal_path = root / "journal" / "registration.json"
    if not journal_path.exists():
        return "not_required"
    journal = _load_json(journal_path)
    snapshot_id = str(journal.get("snapshot_id", ""))
    committed = bool(snapshot_id and (root / "snapshots" / snapshot_id / "manifest.json").is_file())
    journal_path.unlink()
    _write_registry(root, load_manifests(root))
    return "completed_commit_reconciled" if committed else "incomplete_registration_reconciled"


def load_manifests(root: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    snapshots_dir = root / "snapshots"
    if not snapshots_dir.exists():
        return manifests
    for path in sorted(snapshots_dir.glob("*/manifest.json")):
        manifest = _load_json(path)
        required = {
            "snapshot_id",
            "snapshot_content_id",
            "snapshot_label",
            "account_store_id",
            "export_requested_at",
            "export_downloaded_at",
            "export_observed_at",
            "registered_at",
            "file_count",
            "archive_member_count",
            "total_bytes",
            "objects",
        }
        if not required.issubset(manifest):
            raise SnapshotStoreError("snapshot manifest is missing required metadata")
        if manifest.get("snapshot_id") != path.parent.name:
            raise SnapshotStoreError("snapshot directory and manifest identity differ")
        _validate_label(str(manifest["snapshot_label"]))
        _validate_account_store_id(str(manifest["account_store_id"]))
        for field in (
            "export_requested_at",
            "export_downloaded_at",
            "export_observed_at",
            "registered_at",
        ):
            _require_aware_iso(str(manifest[field]), field)
        if not isinstance(manifest["objects"], list) or any(
            not isinstance(item, dict) for item in manifest["objects"]
        ):
            raise SnapshotStoreError("snapshot manifest objects must be a list of objects")
        if manifest.get("export_completion_confirmed") is not True:
            raise SnapshotStoreError("snapshot manifest lacks complete-export confirmation")
        if manifest.get("immutable") is not True:
            raise SnapshotStoreError("snapshot manifest is not immutable")
        if manifest.get("automatic_deletion") is not False:
            raise SnapshotStoreError("snapshot manifest enables automatic deletion")
        manifests.append(manifest)
    try:
        return sorted(
            manifests,
            key=lambda item: (
                _logical_time(str(item["export_observed_at"])),
                str(item["snapshot_id"]),
            ),
        )
    except (TypeError, ValueError) as exc:
        raise SnapshotStoreError("snapshot logical ordering metadata is invalid") from exc


def _inventory_document(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "garmin-running-data-normalizer-snapshot-inventory-v1",
        "contract_version": CONTRACT_VERSION,
        "snapshot_id": manifest["snapshot_id"],
        "objects": manifest["objects"],
    }


def _registry_documents(
    manifests: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshots = []
    for logical_order, manifest in enumerate(manifests, start=1):
        snapshots.append(
            {
                "snapshot_id": manifest["snapshot_id"],
                "snapshot_label": manifest["snapshot_label"],
                "logical_order": logical_order,
                "export_requested_at": manifest["export_requested_at"],
                "export_downloaded_at": manifest["export_downloaded_at"],
                "export_observed_at": manifest["export_observed_at"],
                "registered_at": manifest["registered_at"],
                "snapshot_content_id": manifest["snapshot_content_id"],
                "file_count": manifest["file_count"],
                "archive_member_count": manifest["archive_member_count"],
                "total_bytes": manifest["total_bytes"],
                "export_completion_confirmed": True,
                "manifest_sha256": _sha256_bytes(_stable_json_bytes(manifest)),
                "inventory_sha256": _sha256_bytes(
                    _stable_json_bytes(_inventory_document(manifest))
                ),
            }
        )
    registry = {
        "format": "garmin-running-data-normalizer-snapshot-registry-v1",
        "contract_version": CONTRACT_VERSION,
        "snapshots": snapshots,
    }
    family_coverage: dict[str, dict[str, Any]] = {}
    for logical_order, manifest in enumerate(manifests, start=1):
        for family, count in manifest.get("family_counts", {}).items():
            entry = family_coverage.setdefault(
                str(family),
                {
                    "snapshot_presence": [],
                    "object_count": 0,
                },
            )
            entry["snapshot_presence"].append(logical_order)
            entry["object_count"] += int(count)
    coverage = {
        "format": "garmin-running-data-normalizer-snapshot-family-coverage-v1",
        "contract_version": CONTRACT_VERSION,
        "snapshot_count": len(manifests),
        "families": {
            family: {
                **details,
                "presence_pattern": "".join(
                    "1" if index in details["snapshot_presence"] else "0"
                    for index in range(1, len(manifests) + 1)
                ),
            }
            for family, details in sorted(family_coverage.items())
        },
    }
    return registry, coverage


def _write_registry(root: Path, manifests: list[dict[str, Any]]) -> None:
    registry, coverage = _registry_documents(manifests)
    _atomic_json(root / "registry.json", registry)
    _atomic_json(root / "snapshot_registry.json", registry)
    _atomic_json(root / "snapshot_family_coverage.json", coverage)


def _is_ignored(path: Path) -> bool:
    return (
        path.name in IGNORED_NAMES
        or path.name.startswith("._")
        or "__MACOSX" in path.parts
    )


def _source_family(relative_path: str) -> str:
    for part in Path(relative_path.replace("!", "/")).parts:
        if part.startswith("DI-Connect-") or part == "DI-GOLF":
            return part
    return "unknown"


def _blob_relative_path(digest: str) -> str:
    return f"blobs/sha256/{digest[:2]}/{digest}"


def _validate_inventory_object(row: dict[str, Any]) -> tuple[str, int, str]:
    digest = str(row.get("sha256", ""))
    if not SHA256_RE.fullmatch(digest):
        raise SnapshotStoreError("snapshot inventory contains an invalid SHA-256")
    byte_count = row.get("bytes")
    if (
        isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count < 0
    ):
        raise SnapshotStoreError("snapshot inventory contains an invalid byte count")
    blob_relative_path = str(row.get("blob_relative_path", ""))
    if blob_relative_path != _blob_relative_path(digest):
        raise SnapshotStoreError("snapshot inventory blob path is not content-derived")
    relative_path = str(row.get("relative_path", ""))
    normalized = PurePosixPath(relative_path.replace("!", "/"))
    if (
        not relative_path
        or normalized.is_absolute()
        or ".." in normalized.parts
    ):
        raise SnapshotStoreError("snapshot inventory source path is unsafe")
    if row.get("object_kind") not in {"file", "archive_member"}:
        raise SnapshotStoreError("snapshot inventory object kind is unsupported")
    return digest, byte_count, blob_relative_path


def _preserve_blob(root: Path, digest: str, source: bytes | Path) -> bool:
    destination = root / _blob_relative_path(digest)
    _reject_store_symlink_components(root, destination)
    size = len(source) if isinstance(source, bytes) else source.stat().st_size
    if destination.exists():
        if destination.stat().st_size != size or sha256_file(destination) != digest:
            raise SnapshotStoreError("existing immutable blob failed integrity validation")
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_store_symlink_components(root, destination)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    _reject_store_symlink_components(root, temporary)
    with temporary.open("xb") as handle:
        if isinstance(source, bytes):
            handle.write(source)
        else:
            with source.open("rb") as input_handle:
                while chunk := input_handle.read(1024 * 1024):
                    handle.write(chunk)
        handle.flush()
        os.fsync(handle.fileno())
    if sha256_file(temporary) != digest:
        temporary.unlink(missing_ok=True)
        raise SnapshotStoreError("new immutable blob failed integrity validation")
    os.replace(temporary, destination)
    destination.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return True


def _scan_source(
    source: Path,
) -> tuple[list[dict[str, Any]], dict[str, bytes | Path]]:
    inventory: list[dict[str, Any]] = []
    payloads: dict[str, bytes | Path] = {}
    for path in source.rglob("*"):
        if path.is_symlink():
            raise SnapshotStoreError("symbolic links are prohibited in snapshot input")
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if not files:
        raise SnapshotStoreError("snapshot input contains no files")
    for path in files:
        if _is_ignored(path):
            continue
        relative = path.relative_to(source).as_posix()
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        digest = sha256_file(path)
        after = (path.stat().st_size, path.stat().st_mtime_ns)
        if before != after:
            raise SnapshotStoreError("snapshot input changed during completeness scan")
        payloads.setdefault(digest, path)
        row = {
            "object_kind": "file",
            "relative_path": relative,
            "container_relative_path": None,
            "sha256": digest,
            "bytes": before[0],
            "source_family": _source_family(relative),
            "extension": path.suffix.lower(),
            "blob_relative_path": _blob_relative_path(digest),
            "parser_state": "parser_unsupported",
        }
        inventory.append(row)
        if path.suffix.lower() != ".zip":
            continue
        try:
            with ZipFile(path, "r") as archive:
                for info in validated_members(archive):
                    member_data = read_member(archive, info)
                    member_digest = _sha256_bytes(member_data)
                    payloads.setdefault(member_digest, member_data)
                    logical_path = f"{relative}!{info.filename}"
                    inventory.append(
                        {
                            "object_kind": "archive_member",
                            "relative_path": logical_path,
                            "container_relative_path": relative,
                            "archive_member_path": info.filename,
                            "sha256": member_digest,
                            "bytes": len(member_data),
                            "source_family": _source_family(logical_path),
                            "extension": Path(info.filename).suffix.lower(),
                            "blob_relative_path": _blob_relative_path(member_digest),
                            "parser_state": "parser_unsupported",
                        }
                    )
        except (BadZipFile, OSError, UnsafeArchiveError) as exc:
            raise SnapshotStoreError("detected ZIP input failed safe archive validation") from exc
    if not inventory:
        raise SnapshotStoreError("snapshot input contains no accepted files")
    return inventory, payloads


def _inventory_content_id(inventory: list[dict[str, Any]]) -> str:
    identity_rows = [
        {
            "object_kind": row["object_kind"],
            "relative_path": row["relative_path"],
            "sha256": row["sha256"],
            "bytes": row["bytes"],
        }
        for row in sorted(
            inventory,
            key=lambda item: (item["object_kind"], item["relative_path"]),
        )
    ]
    return f"content:{_sha256_bytes(_stable_json_bytes(identity_rows))}"


def register_snapshot(
    store_root: str | Path,
    input_root: str | Path,
    *,
    snapshot_label: str,
    export_requested_at: str,
    export_downloaded_at: str,
    export_observed_at: str,
    confirm_complete: bool,
) -> dict[str, Any]:
    if confirm_complete is not True:
        raise SnapshotStoreError("snapshot registration requires --confirm-complete")
    root, store_metadata = load_store(store_root)
    requested_source = Path(input_root)
    if requested_source.is_symlink():
        raise SnapshotStoreError("snapshot input must not be a symbolic link")
    source = requested_source.resolve()
    if not source.is_dir():
        raise SnapshotStoreError("snapshot input directory does not exist")
    if source == root or root in source.parents or source in root.parents:
        raise SnapshotStoreError("snapshot input and snapshot store must be separate")
    label = _validate_label(snapshot_label)
    requested_at = _require_aware_iso(export_requested_at, "export_requested_at")
    downloaded_at = _require_aware_iso(export_downloaded_at, "export_downloaded_at")
    observed_at = _require_aware_iso(export_observed_at, "export_observed_at")
    if not (_logical_time(requested_at) <= _logical_time(downloaded_at) <= _logical_time(observed_at)):
        raise SnapshotStoreError("snapshot timestamps must be requested <= downloaded <= observed")

    with _store_lock(root):
        recovery_status = _recover_journal(root)
        inventory, payloads = _scan_source(source)
        content_id = _inventory_content_id(inventory)
        snapshot_digest = _sha256_bytes(
            _stable_json_bytes(
                {
                    "account_store_id": store_metadata["account_store_id"],
                    "export_observed_at": observed_at,
                    "snapshot_content_id": content_id,
                }
            )
        )
        snapshot_id = f"snapshot-{snapshot_digest}"
        manifest_path = root / "snapshots" / snapshot_id / "manifest.json"
        manifests = load_manifests(root)
        if any(
            item["snapshot_label"] == label and item["snapshot_id"] != snapshot_id
            for item in manifests
        ):
            raise SnapshotStoreError("snapshot label is already registered")
        existing = next(
            (item for item in manifests if item["snapshot_id"] == snapshot_id),
            None,
        )
        if existing is not None:
            if existing["snapshot_content_id"] != content_id:
                raise SnapshotStoreError("snapshot identity collision")
            expected_metadata = {
                "snapshot_label": label,
                "export_requested_at": requested_at,
                "export_downloaded_at": downloaded_at,
                "export_observed_at": observed_at,
            }
            if any(existing.get(field) != value for field, value in expected_metadata.items()):
                raise SnapshotStoreError(
                    "idempotent registration metadata must match the original"
                )
            _write_registry(root, manifests)
            return {
                "status": "PASS",
                "snapshot_id": snapshot_id,
                "registration_was_idempotent": True,
                "snapshot_count": len(manifests),
                "logical_order": manifests.index(existing) + 1,
                "recovery_status": recovery_status,
            }

        _atomic_json(
            root / "journal" / "registration.json",
            {
                "format": "snapshot-registration-journal-v1",
                "snapshot_id": snapshot_id,
                "phase": "preserving_blobs",
            },
        )
        added = 0
        reused = 0
        for digest in sorted(payloads):
            if _preserve_blob(root, digest, payloads[digest]):
                added += 1
            else:
                reused += 1
        family_counts = Counter(row["source_family"] for row in inventory)
        manifest = {
            "format": "garmin-running-data-normalizer-snapshot-manifest-v1",
            "contract_version": CONTRACT_VERSION,
            "policy_registry_version": REGISTRY_VERSION,
            "snapshot_id": snapshot_id,
            "snapshot_content_id": content_id,
            "snapshot_label": label,
            "account_store_id": store_metadata["account_store_id"],
            "export_requested_at": requested_at,
            "export_downloaded_at": downloaded_at,
            "export_observed_at": observed_at,
            "registered_at": _now_utc(),
            "export_completion_confirmed": True,
            "file_count": sum(row["object_kind"] == "file" for row in inventory),
            "archive_member_count": sum(
                row["object_kind"] == "archive_member" for row in inventory
            ),
            "total_bytes": sum(int(row["bytes"]) for row in inventory),
            "family_counts": dict(sorted(family_counts.items())),
            "objects": inventory,
            "immutable": True,
            "automatic_deletion": False,
        }
        inventory_path = manifest_path.parent / f"{snapshot_id}.inventory.json"
        _atomic_json(inventory_path, _inventory_document(manifest))
        _atomic_json(manifest_path, manifest)
        inventory_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        manifest_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        manifests.append(manifest)
        manifests = sorted(
            manifests,
            key=lambda item: (
                _logical_time(str(item["export_observed_at"])),
                str(item["snapshot_id"]),
            ),
        )
        _write_registry(root, manifests)
        (root / "journal" / "registration.json").unlink()
        return {
            "status": "PASS",
            "snapshot_id": snapshot_id,
            "registration_was_idempotent": False,
            "snapshot_count": len(manifests),
            "logical_order": manifests.index(manifest) + 1,
            "blob_added_count": added,
            "blob_reused_count": reused,
            "recovery_status": recovery_status,
        }


def snapshot_status(store_root: str | Path) -> dict[str, Any]:
    root, metadata = load_store(store_root)
    manifests = load_manifests(root)
    return {
        "status": "PASS",
        "account_store_id": metadata["account_store_id"],
        "snapshot_count": len(manifests),
        "automatic_deletion": False,
        "snapshots": [
            {
                "logical_order": index,
                "snapshot_label": manifest["snapshot_label"],
                "export_observed_at": manifest["export_observed_at"],
                "file_count": manifest["file_count"],
                "archive_member_count": manifest["archive_member_count"],
            }
            for index, manifest in enumerate(manifests, start=1)
        ],
    }


def verify_store(store_root: str | Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        root, metadata = load_store(store_root)
        manifests = load_manifests(root)
    except SnapshotStoreError:
        return {
            "status": "FAIL",
            "snapshot_count": 0,
            "referenced_blob_count": 0,
            "unreferenced_blob_count": 0,
            "failure_count": 1,
            "failures": ["snapshot_store_metadata_failure"],
            "automatic_deletion": False,
            "garbage_collection_performed": False,
        }
    referenced: set[str] = set()
    if (root / "journal" / "registration.json").exists():
        failures.append("incomplete_registration_journal_present")
    for manifest in manifests:
        if manifest.get("account_store_id") != metadata["account_store_id"]:
            failures.append("account_boundary_mismatch")
        try:
            objects = list(manifest.get("objects", []))
            for row in objects:
                _validate_inventory_object(row)
            expected_content = _inventory_content_id(objects)
            if expected_content != manifest.get("snapshot_content_id"):
                failures.append("snapshot_content_id_mismatch")
            expected_snapshot_digest = _sha256_bytes(
                _stable_json_bytes(
                    {
                        "account_store_id": metadata["account_store_id"],
                        "export_observed_at": manifest["export_observed_at"],
                        "snapshot_content_id": expected_content,
                    }
                )
            )
            if manifest["snapshot_id"] != f"snapshot-{expected_snapshot_digest}":
                failures.append("snapshot_identity_mismatch")
        except SnapshotStoreError:
            failures.append("snapshot_inventory_contract_failure")
        for row in manifest.get("objects", []):
            try:
                digest, byte_count, blob_relative_path = _validate_inventory_object(
                    row
                )
            except SnapshotStoreError:
                failures.append("snapshot_inventory_contract_failure")
                continue
            referenced.add(digest)
            blob = root / blob_relative_path
            try:
                _reject_store_symlink_components(root, blob)
                blob_valid = (
                    blob.is_file()
                    and blob.stat().st_size == byte_count
                    and sha256_file(blob) == digest
                )
            except SnapshotStoreError:
                failures.append("immutable_blob_symlink_failure")
                blob_valid = False
            if not blob_valid:
                failures.append("immutable_blob_integrity_failure")
    try:
        registry = _load_json(root / "registry.json")
        expected_registry, expected_family_coverage = _registry_documents(manifests)
        if registry != expected_registry:
            failures.append("registry_manifest_binding_mismatch")
        public_registry = _load_json(root / "snapshot_registry.json")
        if public_registry != registry:
            failures.append("snapshot_registry_alias_mismatch")
        family_coverage = _load_json(root / "snapshot_family_coverage.json")
        if family_coverage != expected_family_coverage:
            failures.append("snapshot_family_coverage_binding_mismatch")
    except SnapshotStoreError:
        failures.append("snapshot_registry_metadata_failure")
    for manifest in manifests:
        inventory_path = (
            root
            / "snapshots"
            / str(manifest["snapshot_id"])
            / f"{manifest['snapshot_id']}.inventory.json"
        )
        try:
            inventory = _load_json(inventory_path)
            if inventory != _inventory_document(manifest):
                failures.append("snapshot_inventory_mismatch")
        except SnapshotStoreError:
            failures.append("snapshot_inventory_metadata_failure")
    blob_root = root / "blobs" / "sha256"
    try:
        _reject_store_symlink_components(root, blob_root)
        blob_tree = list(blob_root.rglob("*")) if blob_root.exists() else []
    except SnapshotStoreError:
        failures.append("immutable_blob_symlink_failure")
        blob_tree = []
    if any(path.is_symlink() for path in blob_tree):
        failures.append("immutable_blob_symlink_failure")
    all_blobs = {
        path.name
        for path in blob_tree
        if path.is_file() and not path.is_symlink()
    }
    return {
        "status": "PASS" if not failures else "FAIL",
        "snapshot_count": len(manifests),
        "referenced_blob_count": len(referenced),
        "unreferenced_blob_count": len(all_blobs - referenced),
        "failure_count": len(failures),
        "failures": sorted(Counter(failures)),
        "automatic_deletion": False,
        "garbage_collection_performed": False,
    }


__all__ = [
    "SnapshotStoreError",
    "initialize_store",
    "load_manifests",
    "load_store",
    "register_snapshot",
    "sha256_file",
    "snapshot_status",
    "verify_store",
]
