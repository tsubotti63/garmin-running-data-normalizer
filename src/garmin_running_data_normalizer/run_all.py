from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import __version__
from .fit.parser import parse_fit_bytes, parse_fit_export
from .export.analysis_pack import build_analysis_pack_payloads
from .intake.discovery import DiscoveredAsset, discover_export
from .normalizers.activities import normalize_activities
from .normalizers.gear import normalize_gear
from .normalizers.personal_records import normalize_personal_records
from .qa import deterministic_records_digest
from .relationships import (
    RelationshipContractError,
    build_activity_fit_relationship,
    validate_declared_relationships,
)


RUN_ALL_VERSION = 1
DATASET_TABLE = (
    {"name": "activities", "family": "activities", "record_grain": "activity", "stable_key": ("garmin_activity_key",), "required": True},
    {"name": "gear", "family": "gear", "record_grain": "gear", "stable_key": ("gear_key",), "required": False},
    {"name": "activity_gear", "family": "gear", "record_grain": "activity_gear_link", "stable_key": ("gear_key", "activity_id"), "required": False},
    {"name": "personal_records", "family": "personal_records", "record_grain": "personal_record", "stable_key": ("personal_record_id",), "required": False},
    {"name": "fit_sessions", "family": "fit", "record_grain": "fit_session", "stable_key": ("fit_session_key",), "required": False},
    {"name": "fit_laps", "family": "fit", "record_grain": "fit_session_lap", "stable_key": ("fit_lap_key",), "required": False},
    {"name": "activity_fit_links", "family": "fit", "record_grain": "activity_fit_session_link", "stable_key": ("garmin_activity_key", "fit_session_key"), "required": False},
)

FAMILY_ORDER = ("activities", "gear", "personal_records", "fit")
DATASET_PATHS = {
    "activities": "normalized/activities.json",
    "gear": "normalized/gear.json",
    "activity_gear": "normalized/activity_gear.json",
    "personal_records": "normalized/personal_records.json",
    "fit_sessions": "normalized/fit_sessions.json",
    "fit_laps": "normalized/fit_laps.json",
    "activity_fit_links": "normalized/activity_fit_links.json",
}
ACTIVITIES_CSV_COLUMNS = (
    "garmin_activity_key",
    "activity_date_local",
    "activity_datetime_local",
    "activity_type",
    "sport_type",
    "distance_m",
    "duration_sec",
    "avg_hr",
    "max_hr",
    "avg_power",
    "max_power",
    "avg_run_cadence",
    "training_effect_label",
    "activity_training_load",
    "lap_count",
)
EXTERNAL_SAFE_CSV_COLUMNS = (
    "activity_month",
    "activity_type",
    "sport_type",
    "distance_m",
    "duration_sec",
    "lap_count",
)
OUTPUT_PATHS = (
    "normalized/activities.json",
    "normalized/gear.json",
    "normalized/activity_gear.json",
    "normalized/personal_records.json",
    "normalized/fit_sessions.json",
    "normalized/fit_laps.json",
    "normalized/activity_fit_links.json",
    "audit/fit_audit.json",
    "audit/activity_fit_linkage.json",
    "analysis/activities.csv",
    "qa/dataset_summary.json",
    "qa/relationship_summary.json",
    "START_HERE.md",
    "DATASET_INVENTORY.md",
    "ANALYSIS_HANDOFF.md",
    "ANALYSIS_CONTEXT.json",
    "SCHEMA_CATALOG.json",
    "artifact_inventory.json",
    "run_manifest.json",
    "run_summary.json",
)
INCOMPLETE_FIT_STATUSES = {
    "too_large",
    "too_small",
    "bad_header",
    "bad_header_crc",
    "bad_file_crc",
    "truncated",
    "undefined_local_message",
    "unsupported_chained",
    "session_lap_allocation_conflict",
}


class RunAllError(ValueError):
    """A fatal Run-All error with a bounded, privacy-safe public message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_paths(input_path: str | Path, output_path: str | Path) -> tuple[Path, Path]:
    requested_input = Path(input_path)
    requested_output = Path(output_path)
    if requested_input.is_symlink():
        raise RunAllError("INPUT_SYMLINK", "input directory must not be a symbolic link")
    input_root = requested_input.resolve()
    if not input_root.is_dir():
        raise RunAllError("INPUT_NOT_DIRECTORY", "input directory does not exist")
    if requested_output.is_symlink():
        raise RunAllError("OUTPUT_SYMLINK", "output directory must not be a symbolic link")
    output_root = requested_output.resolve()
    if _is_within(output_root, input_root):
        raise RunAllError("OUTPUT_INSIDE_INPUT", "output directory must be outside the input directory")
    if output_root.exists():
        raise RunAllError("OUTPUT_EXISTS", "output directory must not already exist")
    return input_root, output_root


def _discover(root: Path) -> list[DiscoveredAsset]:
    try:
        return discover_export(root)
    except Exception as exc:
        raise RunAllError("INPUT_DISCOVERY_FAILED", "input discovery or archive safety validation failed") from exc


def _asset_family(asset: DiscoveredAsset) -> str:
    logical_name = asset.member_path or asset.source_path
    if asset.kind == "json" and logical_name.endswith("summarizedActivities.json"):
        return "activities"
    if asset.kind == "json" and logical_name.endswith("gear.json"):
        return "gear"
    if asset.kind == "json" and logical_name.endswith("personalRecord.json"):
        return "personal_records"
    if asset.kind == "fit":
        return "fit"
    return "unclassified"


def _classify_assets(assets: list[DiscoveredAsset]) -> dict[str, list[DiscoveredAsset]]:
    families = {family: [] for family in FAMILY_ORDER}
    for asset in assets:
        family = _asset_family(asset)
        if family in families:
            families[family].append(asset)
    return families


def _snapshot(assets: list[DiscoveredAsset]) -> tuple[tuple[str, int, str], ...]:
    return tuple((asset.provenance_path, asset.size_bytes, asset.sha256) for asset in assets)


def _validate_dataset_table() -> None:
    expected = {
        "activities": ("activity", ("garmin_activity_key",), True),
        "gear": ("gear", ("gear_key",), False),
        "activity_gear": ("activity_gear_link", ("gear_key", "activity_id"), False),
        "personal_records": ("personal_record", ("personal_record_id",), False),
        "fit_sessions": ("fit_session", ("fit_session_key",), False),
        "fit_laps": ("fit_session_lap", ("fit_lap_key",), False),
        "activity_fit_links": (
            "activity_fit_session_link",
            ("garmin_activity_key", "fit_session_key"),
            False,
        ),
    }
    actual = {
        str(item["name"]): (str(item["record_grain"]), tuple(item["stable_key"]), bool(item["required"]))
        for item in DATASET_TABLE
    }
    if actual != expected or any(item["family"] not in FAMILY_ORDER for item in DATASET_TABLE):
        raise RunAllError("DATASET_TABLE_INVALID", "in-package dataset contract is invalid")


def _normalize_datasets(
    input_root: Path,
    families: dict[str, list[DiscoveredAsset]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
    dict[str, int],
    dict[str, Any],
    dict[str, Any],
]:
    records: dict[str, list[dict[str, Any]]] = {name: [] for name in DATASET_PATHS}
    fit_audit: list[dict[str, Any]] = []
    fit_status_counts: Counter[str] = Counter()
    incomplete_fit_count = 0

    try:
        records["activities"] = normalize_activities(str(input_root))
    except Exception as exc:
        raise RunAllError("ACTIVITIES_NORMALIZATION_FAILED", "detected Activities input could not be normalized") from exc
    if not records["activities"]:
        raise RunAllError("ACTIVITIES_EMPTY", "Activities input produced no valid records")

    if families["gear"]:
        try:
            records["gear"], records["activity_gear"] = normalize_gear(str(input_root))
        except Exception as exc:
            raise RunAllError("GEAR_NORMALIZATION_FAILED", "detected Gear input could not be normalized") from exc

    if families["personal_records"]:
        try:
            records["personal_records"] = normalize_personal_records(str(input_root))
        except Exception as exc:
            raise RunAllError(
                "PERSONAL_RECORDS_NORMALIZATION_FAILED",
                "detected Personal Records input could not be normalized",
            ) from exc

    if families["fit"]:
        try:
            records["fit_sessions"], records["fit_laps"], base_audit = parse_fit_export(input_root)
            detail_by_file: dict[str, dict[str, Any]] = {}
            for asset in families["fit"]:
                file_id = f"fit_file:{asset.sha256[:24]}"
                detail_by_file[file_id] = parse_fit_bytes(
                    asset.data,
                    file_id=file_id,
                    source_path=asset.provenance_path,
                )
            for item in base_audit:
                detail = detail_by_file.get(str(item["fit_file_id"]), {})
                unknown_records = int(detail.get("unknown_records", 0) or 0)
                enriched = {**item, "unknown_records": unknown_records}
                fit_audit.append(enriched)
                status = str(item["parse_status"])
                fit_status_counts[status] += 1
                if status in INCOMPLETE_FIT_STATUSES or unknown_records > 0:
                    incomplete_fit_count += 1
        except Exception as exc:
            raise RunAllError("FIT_PROCESSING_FAILED", "detected FIT input could not be audited") from exc

    try:
        relationship_summary = validate_declared_relationships(records)
        (
            records["activity_fit_links"],
            activity_fit_audit,
            activity_fit_metrics,
        ) = build_activity_fit_relationship(
            records["activities"],
            records["fit_sessions"],
        )
        relationship_summary["relationships"]["activities_to_fit_sessions"] = (
            activity_fit_metrics
        )
    except RelationshipContractError as exc:
        raise RunAllError(
            "RELATIONSHIP_CONTRACT_FAILED",
            "a declared dataset relationship failed validation",
        ) from exc

    return (
        records,
        fit_audit,
        {
            "incomplete_fit_count": incomplete_fit_count,
            **{
                f"status_{key}": value
                for key, value in sorted(fit_status_counts.items())
            },
        },
        activity_fit_audit,
        relationship_summary,
    )


def _canonical_key(record: dict[str, Any], fields: tuple[str, ...]) -> tuple[str, ...] | None:
    values = [record.get(field) for field in fields]
    if any(value in (None, "") for value in values):
        return None
    return tuple(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) for value in values)


def _dataset_qa(
    dataset: dict[str, Any],
    records: list[dict[str, Any]],
    source_count: int,
) -> dict[str, Any]:
    try:
        json.dumps(records, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise RunAllError("DATASET_NOT_SERIALIZABLE", "normalized dataset is not JSON serializable") from exc

    key_fields = tuple(dataset["stable_key"])
    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    missing_key_count = 0
    for record in records:
        key = _canonical_key(record, key_fields)
        if key is None:
            missing_key_count += 1
            continue
        grouped[key].append(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if missing_key_count:
        raise RunAllError("STABLE_KEY_MISSING", "normalized dataset contains a missing stable key")
    divergent_duplicates = sum(1 for values in grouped.values() if len(values) > 1 and len(set(values)) > 1)
    if divergent_duplicates:
        raise RunAllError("DIVERGENT_DUPLICATE", "normalized dataset contains a divergent duplicate key")
    duplicate_extra_rows = sum(max(len(values) - 1, 0) for values in grouped.values())
    return {
        "dataset": dataset["name"],
        "record_grain": dataset["record_grain"],
        "stable_key": list(key_fields),
        "source_count": source_count,
        "record_count": len(records),
        "missing_key_count": 0,
        "duplicate_extra_rows": duplicate_extra_rows,
        "divergent_duplicate_key_count": 0,
        "json_serializable": True,
        "records_sha256": deterministic_records_digest(records),
        "status": "PASS",
    }


def _validate_provenance(
    records: dict[str, list[dict[str, Any]]],
    fit_audit: list[dict[str, Any]],
    families: dict[str, list[DiscoveredAsset]],
) -> None:
    sources = {
        family: {(asset.provenance_path, asset.sha256) for asset in assets}
        for family, assets in families.items()
    }
    for dataset in DATASET_TABLE:
        if dataset["name"] == "activity_fit_links":
            for record in records["activity_fit_links"]:
                activity_source = (
                    str(record.get("activity_source_path")),
                    str(record.get("activity_source_sha256")),
                )
                fit_source = (
                    str(record.get("fit_source_path")),
                    str(record.get("fit_source_sha256")),
                )
                if (
                    activity_source not in sources["activities"]
                    or fit_source not in sources["fit"]
                ):
                    raise RunAllError(
                        "PROVENANCE_MISMATCH",
                        "relationship provenance does not match discovered input",
                    )
            continue
        expected = sources[str(dataset["family"])]
        for record in records[str(dataset["name"])]:
            actual = (str(record.get("source_path")), str(record.get("source_sha256")))
            if actual not in expected:
                raise RunAllError("PROVENANCE_MISMATCH", "normalized dataset provenance does not match discovered input")
    for record in fit_audit:
        actual = (str(record.get("source_path")), str(record.get("source_sha256")))
        if actual not in sources["fit"]:
            raise RunAllError("PROVENANCE_MISMATCH", "FIT audit provenance does not match discovered input")


def _activities_csv(records: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=ACTIVITIES_CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for record in sorted(records, key=lambda item: (str(item["garmin_activity_key"]), str(item["source_path"]))):
        writer.writerow(record)
    return stream.getvalue().encode("utf-8")


def _external_safe_pack(
    activities: list[dict[str, Any]],
    *,
    run_status: str,
    warnings: list[dict[str, Any]],
) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=EXTERNAL_SAFE_CSV_COLUMNS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for record in sorted(
        activities,
        key=lambda item: (
            str(item.get("activity_date_local", ""))[:7],
            str(item.get("activity_type", "")),
            str(item.get("distance_m", "")),
            str(item.get("duration_sec", "")),
        ),
    ):
        writer.writerow(
            {
                **record,
                "activity_month": str(record.get("activity_date_local", ""))[:7],
            }
        )
    safe_schema = {
        "format": "garmin-running-data-normalizer-external-safe-schema-v1",
        "dataset": "safe/activities_monthly.csv",
        "grain": "activity_with_month_only",
        "fields": list(EXTERNAL_SAFE_CSV_COLUMNS),
        "excluded": [
            "source paths",
            "filenames",
            "source hashes",
            "raw IDs and stable keys",
            "memo text",
            "coordinates",
            "exact dates and timestamps",
            "heart rate, power, cadence, training effect, and training load",
            "health and performance detail not required by this volume profile",
            "unallowlisted artifacts",
        ],
    }
    safe_context = {
        "format": "garmin-running-data-normalizer-external-safe-context-v1",
        "privacy_mode": "external_safe",
        "run_status": run_status,
        "warnings": [
            {
                "code": str(item.get("code", "UNSPECIFIED_WARNING")),
                "family": item.get("family"),
                "count": item.get("count"),
            }
            for item in warnings
        ],
        "analysis_entry_point": "safe/activities_monthly.csv",
        "relationships": [],
        "prohibited_operations": [
            "identity_inference",
            "location_inference",
            "timestamp_only_join",
            "join_to_unlisted_data",
            "medical_or_coaching_interpretation",
        ],
        "automatic_upload": False,
    }
    readme = (
        "# External-safe Analysis Handoff\n\n"
        "This deterministic pack contains an explicit, reviewable allowlist. "
        "It does not upload itself. The activity calendar is reduced to month "
        "granularity, and identifiers, provenance, hashes, memo text, coordinates, "
        "exact timestamps, heart rate, power, cadence, training effect, and "
        "training load are excluded. The default profile is limited to activity "
        "volume and count context.\n\n"
        "Use only the listed CSV and JSON files. Preserve missing values, report "
        "denominators, and do not infer identity, location, or unsupported joins.\n"
    ).encode("utf-8")
    pack, _ = build_analysis_pack_payloads(
        {
            "README.md": readme,
            "safe/activities_monthly.csv": stream.getvalue().encode("utf-8"),
            "safe/ANALYSIS_CONTEXT.json": _json_bytes(safe_context),
            "safe/SCHEMA_CATALOG.json": _json_bytes(safe_schema),
        }
    )
    return pack


def _family_results(
    families: dict[str, list[DiscoveredAsset]],
    records: dict[str, list[dict[str, Any]]],
    fit_status: dict[str, int],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], str]:
    warnings: list[dict[str, Any]] = []
    results: dict[str, dict[str, Any]] = {}
    family_record_counts = {
        "activities": len(records["activities"]),
        "gear": len(records["gear"]) + len(records["activity_gear"]),
        "personal_records": len(records["personal_records"]),
        "fit": (
            len(records["fit_sessions"])
            + len(records["fit_laps"])
            + len(records["activity_fit_links"])
        ),
    }
    incomplete_fit_count = int(fit_status.get("incomplete_fit_count", 0))
    for family in FAMILY_ORDER:
        detected = len(families[family])
        family_warnings = 0
        status = "PROCESSED"
        skipped = 0
        if family != "activities" and detected == 0:
            status = "SKIPPED_NOT_PRESENT"
            family_warnings += 1
            warnings.append({
                "code": "OPTIONAL_FAMILY_NOT_PRESENT",
                "family": family,
                "message": "optional dataset family was not present",
            })
        elif family != "activities" and family_record_counts[family] == 0:
            status = "PROCESSED_EMPTY"
            family_warnings += 1
            warnings.append({
                "code": "OPTIONAL_FAMILY_EMPTY",
                "family": family,
                "message": "optional dataset family produced no normalized records",
            })
        if family == "fit" and incomplete_fit_count:
            status = "PARTIAL"
            skipped = incomplete_fit_count
            family_warnings += 1
            warnings.append({
                "code": "FIT_PARSE_INCOMPLETE",
                "family": "fit",
                "count": incomplete_fit_count,
                "message": "one or more FIT assets were not completely parsed",
            })
        results[family] = {
            "status": status,
            "detected_asset_count": detected,
            "processed_asset_count": detected,
            "skipped_asset_count": skipped,
            "record_count": family_record_counts[family],
            "warning_count": family_warnings,
            "error_count": 0,
        }
        if family == "fit":
            results[family]["parse_status_counts"] = {
                key.removeprefix("status_"): value
                for key, value in sorted(fit_status.items())
                if key.startswith("status_")
            }
            results[family]["incomplete_asset_count"] = incomplete_fit_count

    overall = "PARTIAL_SUCCESS" if incomplete_fit_count else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    return results, warnings, overall


def _output_digest(entries: list[dict[str, Any]]) -> str:
    canonical = "\n".join(f"{item['path']}:{item['sha256']}" for item in sorted(entries, key=lambda row: row["path"]))
    return _sha256(canonical.encode("utf-8"))


def _write_exclusive(root: Path, relative: str, data: bytes) -> None:
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(data)


def _publish_outputs(
    output_root: Path,
    payloads: dict[str, bytes],
    manifest: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    output_root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_root.name}.run-all-", dir=output_root.parent))
    try:
        for relative in sorted(payloads):
            _write_exclusive(stage, relative, payloads[relative])
        manifest_data = _json_bytes(manifest)
        _write_exclusive(stage, "run_manifest.json", manifest_data)
        summary["manifest_sha256"] = _sha256(manifest_data)
        _write_exclusive(stage, "run_summary.json", _json_bytes(summary))
        if output_root.exists():
            raise RunAllError("OUTPUT_EXISTS", "output directory became occupied before publication")
        stage.rename(output_root)
    except RunAllError:
        raise
    except Exception as exc:
        raise RunAllError("OUTPUT_PUBLISH_FAILED", "Run-All output could not be published atomically") from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def run_all(
    input_path: str | Path,
    output_path: str | Path,
    *,
    external_safe_pack: bool = False,
) -> dict[str, Any]:
    """Compose the existing Garmin normalizers into deterministic Run-All v1."""
    input_root, output_root = _validate_paths(input_path, output_path)
    initial_assets = _discover(input_root)
    initial_snapshot = _snapshot(initial_assets)
    families = _classify_assets(initial_assets)
    if not families["activities"]:
        raise RunAllError("ACTIVITIES_NOT_FOUND", "required Activities input was not found")
    _validate_dataset_table()

    (
        records,
        fit_audit,
        fit_status,
        activity_fit_audit,
        relationship_summary,
    ) = _normalize_datasets(input_root, families)
    _validate_provenance(records, fit_audit, families)
    qa_entries = [
        _dataset_qa(dataset, records[str(dataset["name"])], len(families[str(dataset["family"])]))
        for dataset in DATASET_TABLE
    ]
    dataset_summary = {
        "format": "garmin-running-data-normalizer-dataset-summary-v1",
        "status": "PASS",
        "datasets": qa_entries,
    }
    csv_data = _activities_csv(records["activities"])

    final_assets = _discover(input_root)
    if _snapshot(final_assets) != initial_snapshot:
        raise RunAllError("INPUT_CHANGED", "input assets changed during Run-All processing")

    family_results, warnings, status = _family_results(families, records, fit_status)
    payloads = {
        **{DATASET_PATHS[name]: _json_bytes(value) for name, value in records.items()},
        "audit/fit_audit.json": _json_bytes(fit_audit),
        "audit/activity_fit_linkage.json": _json_bytes(activity_fit_audit),
        "analysis/activities.csv": csv_data,
        "qa/dataset_summary.json": _json_bytes(dataset_summary),
        "qa/relationship_summary.json": _json_bytes(relationship_summary),
    }
    generated_paths = list(OUTPUT_PATHS)
    if external_safe_pack:
        safe_pack_path = "analysis/external_safe_handoff.zip"
        payloads[safe_pack_path] = _external_safe_pack(
            records["activities"],
            run_status=status,
            warnings=warnings,
        )
        generated_paths = [
            *OUTPUT_PATHS[:-2],
            safe_pack_path,
            *OUTPUT_PATHS[-2:],
        ]
    qa_by_name = {entry["dataset"]: entry for entry in qa_entries}
    manifest = {
        "format": "garmin-running-data-normalizer-run-manifest-v1",
        "product_version": __version__,
        "run_all_version": RUN_ALL_VERSION,
        "input_assets": [
            {
                "source_path": asset.provenance_path,
                "bytes": asset.size_bytes,
                "sha256": asset.sha256,
                "detected_family": _asset_family(asset),
            }
            for asset in initial_assets
        ],
        "datasets": [
            {
                "name": dataset["name"],
                "record_grain": dataset["record_grain"],
                "stable_key": list(dataset["stable_key"]),
                "source_count": qa_by_name[str(dataset["name"])]["source_count"],
                "record_count": qa_by_name[str(dataset["name"])]["record_count"],
                "records_sha256": qa_by_name[str(dataset["name"])]["records_sha256"],
            }
            for dataset in DATASET_TABLE
        ],
        "outputs": [],
        "deterministic_output_digest": "projection-pending",
    }
    summary = {
        "format": "garmin-running-data-normalizer-run-summary-v1",
        "product_version": __version__,
        "run_all_version": RUN_ALL_VERSION,
        "status": status,
        "family_results": family_results,
        "input_asset_count": len(initial_assets),
        "normalized_record_count": sum(len(value) for value in records.values()),
        "warning_count": len(warnings),
        "error_count": 0,
        "warnings": warnings,
        "errors": [],
        "generated_paths": generated_paths,
        "deterministic_output_digest": "projection-pending",
    }
    from .output_experience import (
        DOCUMENT_NAMES,
        MACHINE_CONTEXT_NAMES,
        MANIFEST_OUTPUT_PATHS,
        OPTIONAL_MANIFEST_OUTPUT_PATHS,
        render_output_experience_artifacts,
    )

    projection_names = (*DOCUMENT_NAMES, *MACHINE_CONTEXT_NAMES)
    provisional_payloads = {**payloads, **{name: b"" for name in projection_names}}
    allowed_payload_paths = set(MANIFEST_OUTPUT_PATHS)
    if external_safe_pack:
        allowed_payload_paths.update(OPTIONAL_MANIFEST_OUTPUT_PATHS)
    if set(provisional_payloads) != allowed_payload_paths:
        raise RunAllError(
            "OUTPUT_CONTRACT_INVALID",
            "Run-All payload paths do not match the v1.1 output contract",
        )
    manifest["outputs"] = [
        {"path": path, "bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(provisional_payloads.items())
    ]
    try:
        payloads.update(
            render_output_experience_artifacts(
                manifest,
                summary,
                {
                    "datasets": [
                        {
                            "name": dataset["name"],
                            "record_grain": dataset["record_grain"],
                            "stable_key": list(dataset["stable_key"]),
                            "provenance_required": True,
                        }
                        for dataset in DATASET_TABLE
                    ]
                },
                relationship_summary,
            )
        )
    except Exception as exc:
        raise RunAllError(
            "OUTPUT_EXPERIENCE_FAILED",
            "deterministic analysis handoff generation failed",
        ) from exc

    output_entries = [
        {"path": path, "bytes": len(data), "sha256": _sha256(data)}
        for path, data in sorted(payloads.items())
    ]
    deterministic_digest = _output_digest(output_entries)
    manifest["outputs"] = output_entries
    manifest["deterministic_output_digest"] = deterministic_digest
    summary["deterministic_output_digest"] = deterministic_digest
    _publish_outputs(output_root, payloads, manifest, summary)
    exit_code = 3 if status == "PARTIAL_SUCCESS" else 0
    return {
        "status": status,
        "exit_code": exit_code,
        "family_results": family_results,
        "generated_files": generated_paths,
        "deterministic_digest": deterministic_digest,
    }


__all__ = [
    "ACTIVITIES_CSV_COLUMNS",
    "DATASET_TABLE",
    "OUTPUT_PATHS",
    "RUN_ALL_VERSION",
    "RunAllError",
    "run_all",
]
