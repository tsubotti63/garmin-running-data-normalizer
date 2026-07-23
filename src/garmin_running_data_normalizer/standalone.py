from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


class StandaloneHandoffError(ValueError):
    """Raised when a Run-All directory is not a self-contained safe handoff."""


def _json_object(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    if not path.is_file():
        raise StandaloneHandoffError(f"required handoff file is missing: {name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StandaloneHandoffError(f"handoff file is not valid JSON: {name}") from exc
    if not isinstance(value, dict):
        raise StandaloneHandoffError(f"handoff file must contain an object: {name}")
    return value


def _validate_manifest_payloads(
    output_root: Path,
    manifest: dict[str, Any],
) -> str:
    raw_outputs = manifest.get("outputs")
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise StandaloneHandoffError("run manifest output inventory is missing")
    seen: set[str] = set()
    for item in raw_outputs:
        if not isinstance(item, dict):
            raise StandaloneHandoffError("run manifest output entry is invalid")
        raw_path = item.get("path")
        path = PurePosixPath(raw_path) if isinstance(raw_path, str) else None
        if (
            path is None
            or path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or path.as_posix() in seen
        ):
            raise StandaloneHandoffError("run manifest output path is unsafe or duplicated")
        relative = path.as_posix()
        seen.add(relative)
        candidate = output_root.joinpath(*path.parts)
        if candidate.is_symlink() or not candidate.is_file():
            raise StandaloneHandoffError(f"manifest payload is missing: {relative}")
        resolved = candidate.resolve()
        if output_root != resolved.parent and output_root not in resolved.parents:
            raise StandaloneHandoffError("manifest payload escapes the handoff root")
        data = candidate.read_bytes()
        if item.get("bytes") != len(data):
            raise StandaloneHandoffError(
                f"manifest payload size does not match: {relative}"
            )
        if item.get("sha256") != hashlib.sha256(data).hexdigest():
            raise StandaloneHandoffError(
                f"manifest payload hash does not match: {relative}"
            )
    canonical = "\n".join(
        f"{item['path']}:{item['sha256']}"
        for item in sorted(raw_outputs, key=lambda value: value["path"])
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_standalone_handoff(root: str | Path) -> dict[str, Any]:
    """Validate a completed handoff using only files inside its output root."""
    requested = Path(root)
    if requested.is_symlink():
        raise StandaloneHandoffError("handoff root must not be a symbolic link")
    output_root = requested.resolve()
    if not output_root.is_dir():
        raise StandaloneHandoffError("handoff root does not exist")

    required_documents = (
        "START_HERE.md",
        "DATASET_INVENTORY.md",
        "ANALYSIS_HANDOFF.md",
    )
    for name in required_documents:
        if not (output_root / name).is_file():
            raise StandaloneHandoffError(f"required handoff file is missing: {name}")

    manifest = _json_object(output_root, "run_manifest.json")
    summary = _json_object(output_root, "run_summary.json")
    context = _json_object(output_root, "ANALYSIS_CONTEXT.json")
    schema = _json_object(output_root, "SCHEMA_CATALOG.json")
    inventory = _json_object(output_root, "artifact_inventory.json")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "PARTIAL_SUCCESS"}:
        raise StandaloneHandoffError("handoff status is not analyzable")
    manifest_bytes = (output_root / "run_manifest.json").read_bytes()
    if summary.get("manifest_sha256") != hashlib.sha256(manifest_bytes).hexdigest():
        raise StandaloneHandoffError("run manifest hash does not match summary")
    if (
        manifest.get("product_version") != summary.get("product_version")
        or manifest.get("run_all_version") != summary.get("run_all_version")
    ):
        raise StandaloneHandoffError("manifest and summary versions do not match")
    if context.get("run_status") != summary.get("status"):
        raise StandaloneHandoffError("analysis context status does not match summary")
    if context.get("product_version") != summary.get("product_version"):
        raise StandaloneHandoffError("analysis context product version does not match summary")
    if context.get("warnings") != summary.get("warnings"):
        raise StandaloneHandoffError("analysis context does not preserve warnings")
    if context.get("analysis_entry_point") != "analysis/activities.csv":
        raise StandaloneHandoffError("analysis entry point is not declared")

    datasets = context.get("datasets")
    schema_datasets = schema.get("datasets")
    relationships = context.get("relationships")
    prohibited = context.get("prohibited_operations")
    if not isinstance(datasets, list) or not datasets:
        raise StandaloneHandoffError("dataset context is missing")
    if not isinstance(schema_datasets, list) or not schema_datasets:
        raise StandaloneHandoffError("schema catalog is missing")
    if {item.get("name") for item in datasets if isinstance(item, dict)} != {
        item.get("dataset") for item in schema_datasets if isinstance(item, dict)
    }:
        raise StandaloneHandoffError("schema coverage does not match datasets")
    if not isinstance(relationships, list) or not relationships:
        raise StandaloneHandoffError("relationship context is missing")
    if any(
        not isinstance(item, dict) or item.get("status") != "explicit"
        for item in relationships
    ):
        raise StandaloneHandoffError("handoff contains a non-explicit join")
    if not isinstance(prohibited, list) or "timestamp_only_join" not in prohibited:
        raise StandaloneHandoffError("prohibited join rules are missing")

    artifacts = inventory.get("artifacts")
    generated_paths = summary.get("generated_paths")
    if not isinstance(artifacts, list) or not isinstance(generated_paths, list):
        raise StandaloneHandoffError("artifact inventory is missing")
    if [item.get("path") for item in artifacts if isinstance(item, dict)] != generated_paths:
        raise StandaloneHandoffError("artifact inventory does not match generated paths")
    for required in (
        *required_documents,
        "ANALYSIS_CONTEXT.json",
        "SCHEMA_CATALOG.json",
        "analysis/activities.csv",
    ):
        if required not in generated_paths or not (output_root / required).is_file():
            raise StandaloneHandoffError(f"declared handoff file is missing: {required}")
    deterministic_digest = _validate_manifest_payloads(output_root, manifest)
    if (
        manifest.get("deterministic_output_digest") != deterministic_digest
        or summary.get("deterministic_output_digest") != deterministic_digest
    ):
        raise StandaloneHandoffError(
            "deterministic output digest does not match manifest payloads"
        )

    return {
        "status": "PASS",
        "run_status": summary["status"],
        "dataset_count": len(datasets),
        "schema_dataset_count": len(schema_datasets),
        "explicit_relationship_count": len(relationships),
        "warning_count": len(summary.get("warnings", [])),
        "first_read": "START_HERE.md",
        "analysis_entry_point": "analysis/activities.csv",
        "repository_required": False,
        "internet_required": False,
    }


__all__ = [
    "StandaloneHandoffError",
    "validate_standalone_handoff",
]
