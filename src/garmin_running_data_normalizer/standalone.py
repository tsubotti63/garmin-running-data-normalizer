from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .common.os_metadata import is_os_metadata_path
from .diagnostics.validation import validate_diagnostic_authorities
from .run_all import OUTPUT_PATHS, RUN_ALL_VERSION, SNAPSHOT_LIFECYCLE_PATHS


OPTIONAL_OUTPUT_PATH = "analysis/external_safe_handoff.zip"
# The files that the 1.3 releases wrote, in their order, and those of their
# Snapshot runs (stage B5b): an output of 1.3, which has no diagnostics, is
# checked against these, as v1.4 through v1.7.1 did, and never against the
# files of this version, which stage A2b-2 made longer. Outputs of 1.0 to
# 1.2 were never taken.
LEGACY_V1_3_OUTPUT_PATHS = (
    "normalized/activities.json",
    "normalized/gear.json",
    "normalized/activity_gear.json",
    "normalized/personal_records.json",
    "normalized/fit_sessions.json",
    "normalized/fit_laps.json",
    "normalized/activity_fit_links.json",
    "normalized/hill_score_daily.json",
    "normalized/endurance_score_daily.json",
    "normalized/race_prediction_daily.json",
    "normalized/sleep_daily.json",
    "normalized/uds_daily.json",
    "normalized/acute_training_load_daily.json",
    "normalized/training_readiness_daily.json",
    "normalized/vo2max_daily.json",
    "normalized/hrv_daily.json",
    "normalized/training_history_daily.json",
    "audit/fit_audit.json",
    "audit/activity_fit_linkage.json",
    "audit/hill_score_daily.json",
    "audit/endurance_score_daily.json",
    "audit/lactate_threshold_candidates.json",
    "audit/race_prediction_daily.json",
    "audit/sleep_daily.json",
    "audit/uds_daily.json",
    "audit/acute_training_load_daily.json",
    "audit/training_readiness_daily.json",
    "audit/vo2max_daily.json",
    "audit/hrv_daily.json",
    "audit/training_history_daily.json",
    "analysis/activities.csv",
    "analysis/performance_metrics_daily.csv",
    "qa/dataset_summary.json",
    "qa/relationship_summary.json",
    "qa/performance_metrics_summary.json",
    "qa/daily_metrics_summary.json",
    "START_HERE.md",
    "DATASET_INVENTORY.md",
    "ANALYSIS_HANDOFF.md",
    "ANALYSIS_CONTEXT.json",
    "SCHEMA_CATALOG.json",
    "artifact_inventory.json",
    "run_manifest.json",
    "run_summary.json",
)
LEGACY_V1_3_SNAPSHOT_PATHS = (
    "snapshot/snapshot_lineage.json",
    "snapshot/snapshot_coverage.json",
    "snapshot/canonical_merge_summary.json",
)
# A version that an output names and that its stop may repeat.
VERSION_FORM = re.compile(r"(?:0|[1-9][0-9]{0,3})(?:\.(?:0|[1-9][0-9]{0,3})){1,2}")


def _path_shapes(base: tuple[str, ...], snapshot_paths: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """A run's files, with the External-safe Pack, of a Snapshot run, and of
    both, each before the manifest and the summary."""
    optional = [*base[:-2], OPTIONAL_OUTPUT_PATH, *base[-2:]]
    snapshot = [*base[:-2], *snapshot_paths, *base[-2:]]
    optional_snapshot = [*optional[:-2], *snapshot_paths, *optional[-2:]]
    return tuple(tuple(value) for value in (base, optional, snapshot, optional_snapshot))


def _generated_path_sets(*, diagnostics_available: bool) -> tuple[tuple[str, ...], ...]:
    if diagnostics_available:
        return _path_shapes(OUTPUT_PATHS, SNAPSHOT_LIFECYCLE_PATHS)
    return _path_shapes(LEGACY_V1_3_OUTPUT_PATHS, LEGACY_V1_3_SNAPSHOT_PATHS)


class StandaloneHandoffError(ValueError):
    """Raised when a Run-All directory is not a self-contained safe handoff."""


class OtherVersionError(StandaloneHandoffError):
    """An output that another version of this app made, which this version
    cannot check (stage B5b): one of 1.0 to 1.2, or of 1.4 or later that is
    not this version. ``version`` is the version that the output names, when
    it is in the form of a version."""

    def __init__(self, version: Any) -> None:
        self.version = version if isinstance(version, str) and VERSION_FORM.fullmatch(version) else None
        named = f"version {self.version}" if self.version else "another version"
        super().__init__(f"the output was made by {named} of this app, which this version cannot check")


def _diagnostics_available(summary: dict[str, Any]) -> bool:
    """Whether the output has the diagnostics of v1.4 and later, from the
    version that its summary names, before its files are compared (stage
    B5b): an output of 1.3 has none and is checked as v1.4 through v1.7.1
    did; one of 1.0 to 1.2, or of 1.4 or later that another version made,
    is told as such, so that it is never taken for one whose files changed.
    An output whose summary names another version is only told that it
    cannot be checked, never taken."""
    product_version = summary.get("product_version")
    try:
        version_parts = tuple(int(part) for part in str(product_version).split(".")[:2])
    except ValueError as exc:
        raise StandaloneHandoffError("handoff Product version is invalid") from exc
    if len(version_parts) != 2 or version_parts[0] < 1:
        raise StandaloneHandoffError("handoff Product version is not supported")
    if version_parts < (1, 3):
        raise OtherVersionError(product_version)
    if version_parts < (1, 4):
        return False
    if product_version != __version__ or summary.get("run_all_version") != RUN_ALL_VERSION:
        raise OtherVersionError(product_version)
    return True


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
    # The version decides first (stage B5b).
    summary = _json_object(output_root, "run_summary.json")
    diagnostics_available = _diagnostics_available(summary)

    required_documents = (
        "START_HERE.md",
        "DATASET_INVENTORY.md",
        "ANALYSIS_HANDOFF.md",
    )
    for name in required_documents:
        if not (output_root / name).is_file():
            raise StandaloneHandoffError(f"required handoff file is missing: {name}")

    manifest = _json_object(output_root, "run_manifest.json")
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
    product_version = summary.get("product_version")
    if diagnostics_available:
        completeness = _json_object(
            output_root, "diagnostics/source_completeness.json"
        )
        quality = _json_object(output_root, "diagnostics/run_quality.json")
        expected_exit = 3 if summary.get("status") == "PARTIAL_SUCCESS" else 0
        if (
            completeness.get("product_version") != product_version
            or quality.get("product_version") != product_version
            or quality.get("run_status") != summary.get("status")
            or quality.get("exit_code") != expected_exit
            or len(quality.get("dataset_summary", [])) != 17
            or len(quality.get("relationship_summary", [])) != 6
        ):
            raise StandaloneHandoffError(
                "v1.4 diagnostic authorities do not match the completed handoff"
            )
    if context.get("run_status") != summary.get("status"):
        raise StandaloneHandoffError("analysis context status does not match summary")
    if context.get("product_version") != summary.get("product_version"):
        raise StandaloneHandoffError("analysis context product version does not match summary")
    if context.get("warnings") != summary.get("warnings"):
        raise StandaloneHandoffError("analysis context does not preserve warnings")
    if (
        manifest.get("local_timezone") != summary.get("local_timezone")
        or context.get("local_timezone") != summary.get("local_timezone")
    ):
        raise StandaloneHandoffError("local timezone does not match across handoff authorities")
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
    if tuple(generated_paths) not in _generated_path_sets(
        diagnostics_available=diagnostics_available
    ):
        raise StandaloneHandoffError(
            "generated paths do not match the version-aware exact set"
        )
    actual_paths: set[str] = set()
    for path in output_root.rglob("*"):
        if path.is_symlink():
            raise StandaloneHandoffError("handoff contains a symbolic link")
        if path.is_file():
            relative = path.relative_to(output_root).as_posix()
            if not is_os_metadata_path(relative):
                actual_paths.add(relative)
    if actual_paths != set(generated_paths):
        raise StandaloneHandoffError("handoff contains an undeclared or missing file")
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
    if diagnostics_available:
        try:
            validate_diagnostic_authorities(
                output_root,
                manifest=manifest,
                summary=summary,
                completeness=completeness,
                quality=quality,
            )
        except ValueError as exc:
            raise StandaloneHandoffError(
                "v1.4 diagnostic authorities contradict Product evidence"
            ) from exc

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
        "diagnostic_contract_availability": (
            "CURRENT" if diagnostics_available else "LEGACY_NOT_AVAILABLE"
        ),
    }


__all__ = [
    "LEGACY_V1_3_OUTPUT_PATHS",
    "OtherVersionError",
    "StandaloneHandoffError",
    "validate_standalone_handoff",
]
