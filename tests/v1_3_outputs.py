"""The outputs of the 1.3 releases, for the tests of the outputs of versions
before 1.4 (stage B5b): the files that they wrote, in their order, as the
1.3.0 to 1.3.3 releases wrote them and never taken from this version, and a
way to give an output of this version their shape. Until stage B5b, the tests
made a 1.3 output from one of this version without its diagnostics only, so
that the files that stage A2b-2 added stayed, and the change that refused the
outputs of 1.3 passed them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

V1_3_FILES = (
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
V1_3_PACK = "analysis/external_safe_handoff.zip"
V1_3_SNAPSHOT_FILES = (
    "snapshot/snapshot_lineage.json",
    "snapshot/snapshot_coverage.json",
    "snapshot/canonical_merge_summary.json",
)
# The four shapes, each with its files before the manifest and the summary.
V1_3_SHAPES = {
    "plain": V1_3_FILES,
    "pack": (*V1_3_FILES[:42], V1_3_PACK, *V1_3_FILES[42:]),
    "snapshot": (*V1_3_FILES[:42], *V1_3_SNAPSHOT_FILES, *V1_3_FILES[42:]),
    "both": (*V1_3_FILES[:42], V1_3_PACK, *V1_3_SNAPSHOT_FILES, *V1_3_FILES[42:]),
}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_release(output: Path, version: str, shape: tuple[str, ...], run_all_version: int = 1) -> tuple[str, ...]:
    """Give an output of this version the files of ``shape``, in its order,
    and the version that the output names: the other files go, and the
    inventory, the manifest, and the summary list the files that stay."""
    kept = set(shape)
    for path in sorted(output.rglob("*"), reverse=True):
        relative = path.relative_to(output).as_posix()
        if path.is_file() and relative not in kept:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    summary_path = output / "run_summary.json"
    manifest_path = output / "run_manifest.json"
    context_path = output / "ANALYSIS_CONTEXT.json"
    inventory_path = output / "artifact_inventory.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["product_version"] = version
    _write_json(context_path, context)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["artifacts"] = [item for item in inventory["artifacts"] if item["path"] in kept]
    _write_json(inventory_path, inventory)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["product_version"] = version
    manifest["run_all_version"] = run_all_version
    manifest["outputs"] = [item for item in manifest["outputs"] if item["path"] in kept]
    for item in manifest["outputs"]:
        data = (output / item["path"]).read_bytes()
        item["bytes"] = len(data)
        item["sha256"] = hashlib.sha256(data).hexdigest()
    canonical = "\n".join(
        f"{item['path']}:{item['sha256']}"
        for item in sorted(manifest["outputs"], key=lambda value: value["path"])
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    manifest["deterministic_output_digest"] = digest
    _write_json(manifest_path, manifest)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["product_version"] = version
    summary["run_all_version"] = run_all_version
    summary["generated_paths"] = [path for path in summary["generated_paths"] if path in kept]
    summary["deterministic_output_digest"] = digest
    summary["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    _write_json(summary_path, summary)
    return tuple(summary["generated_paths"])


def as_v1_3(output: Path, version: str = "1.3.3") -> tuple[str, ...]:
    """Give an output of this version the shape of a 1.3 release, by the
    files that it has: with the External-safe Pack, of Snapshots, or both."""
    pack = (output / V1_3_PACK).is_file()
    snapshot = (output / V1_3_SNAPSHOT_FILES[0]).is_file()
    name = {(False, False): "plain", (True, False): "pack", (False, True): "snapshot", (True, True): "both"}[(pack, snapshot)]
    return as_release(output, version, V1_3_SHAPES[name])
