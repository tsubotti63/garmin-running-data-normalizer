from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .intake.discovery import discover_export
from .normalizers.activities import normalize_activities
from .qa import summarize_records
from .run_all import RunAllError, run_all


OUTPUT_FILES = (
    "normalized_activities.json",
    "qa_summary.json",
    "run_manifest.json",
)


class GoldenPathError(ValueError):
    """Raised when the bounded Golden Path contract is not satisfied."""


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
        raise GoldenPathError("input directory must not be a symbolic link")
    input_root = requested_input.resolve()
    if not input_root.is_dir():
        raise GoldenPathError("input directory does not exist")
    if requested_output.is_symlink():
        raise GoldenPathError("output directory must not be a symbolic link")
    output_root = requested_output.resolve()
    if _is_within(output_root, input_root):
        raise GoldenPathError("output directory must be outside the input directory")
    if output_root.exists():
        if not output_root.is_dir():
            raise GoldenPathError("output path must be a directory")
        if any(output_root.iterdir()):
            raise GoldenPathError("output directory must be absent or empty")
    return input_root, output_root


def run_activities(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Run the deterministic, activities-only Golden Path."""
    input_root, output_root = _validate_paths(input_path, output_path)
    assets = [
        asset
        for asset in discover_export(input_root)
        if asset.kind == "json"
        and (asset.member_path or asset.source_path).endswith("summarizedActivities.json")
    ]
    if not assets:
        raise GoldenPathError("no supported summarizedActivities.json input was found")

    records = normalize_activities(str(input_root))
    if not records:
        raise GoldenPathError("supported input contained no activity records")
    discovered_sources = {(asset.provenance_path, asset.sha256) for asset in assets}
    normalized_sources = {
        (str(record.get("source_path")), str(record.get("source_sha256")))
        for record in records
    }
    if normalized_sources != discovered_sources:
        raise GoldenPathError("input changed or provenance diverged during processing")
    qa = {
        "dataset": "activities",
        "record_grain": "activity",
        "stable_key": ["garmin_activity_key"],
        "source_asset_count": len(assets),
        **summarize_records(records, key_field="garmin_activity_key"),
    }
    if qa["status"] != "PASS":
        raise GoldenPathError("activity QA did not pass")

    normalized_data = _json_bytes(records)
    qa_data = _json_bytes(qa)
    outputs = [
        {
            "path": "normalized_activities.json",
            "bytes": len(normalized_data),
            "sha256": _sha256(normalized_data),
        },
        {
            "path": "qa_summary.json",
            "bytes": len(qa_data),
            "sha256": _sha256(qa_data),
        },
    ]
    manifest = {
        "format": "garmin-running-data-normalizer-golden-path-v1",
        "dataset": "activities",
        "record_grain": "activity",
        "stable_key": ["garmin_activity_key"],
        "deterministic_digest": qa["records_sha256"],
        "input_assets": [
            {
                "source_path": asset.provenance_path,
                "bytes": asset.size_bytes,
                "sha256": asset.sha256,
            }
            for asset in assets
        ],
        "outputs": outputs,
    }
    manifest_data = _json_bytes(manifest)

    if output_root.exists():
        if any(output_root.iterdir()):
            raise GoldenPathError("output directory became non-empty during processing")
    else:
        output_root.mkdir(parents=True, exist_ok=False)
    payloads = {
        "normalized_activities.json": normalized_data,
        "qa_summary.json": qa_data,
        "run_manifest.json": manifest_data,
    }
    for name in OUTPUT_FILES:
        with (output_root / name).open("xb") as handle:
            handle.write(payloads[name])
    return {
        "status": "PASS",
        "record_count": qa["record_count"],
        "deterministic_digest": qa["records_sha256"],
        "generated_files": list(OUTPUT_FILES),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m garmin_running_data_normalizer",
        description="Run bounded local Garmin normalization workflows.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    activities = commands.add_parser(
        "normalize-activities",
        help="Normalize Garmin summarized activities with deterministic QA.",
    )
    activities.add_argument("--input", required=True, help="Garmin export directory")
    activities.add_argument("--output", required=True, help="Absent or empty output directory")
    combined = commands.add_parser(
        "run-all",
        help="Run the minimum deterministic multi-family Garmin workflow.",
    )
    combined.add_argument("--input", required=True, help="Garmin export directory")
    combined.add_argument("--output", required=True, help="New output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "normalize-activities":
            result = run_activities(args.input, args.output)
        elif args.command == "run-all":
            result = run_all(args.input, args.output)
        else:
            raise GoldenPathError("unsupported command")
    except GoldenPathError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except RunAllError as exc:
        print(f"ERROR [{exc.code}]: {exc.safe_message}", file=sys.stderr)
        return 2
    except Exception:
        if args.command == "run-all":
            print("ERROR [RUN_ALL_FAILED]: Run-All failed; verify the input and output contract", file=sys.stderr)
        else:
            print("ERROR: Golden Path failed; verify the input and output contract", file=sys.stderr)
        return 2

    if args.command == "run-all":
        print(f"STATUS: {result['status']}")
        print(f"exit: {result['exit_code']}")
        for family, details in result["family_results"].items():
            print(
                f"{family}: detected={details['detected_asset_count']} "
                f"processed={details['processed_asset_count']} "
                f"skipped={details['skipped_asset_count']} "
                f"records={details['record_count']} "
                f"warnings={details['warning_count']} errors={details['error_count']}"
            )
        print(f"generated: {', '.join(result['generated_files'])}")
        print(f"digest: {result['deterministic_digest']}")
        return int(result["exit_code"])

    print("PASS")
    print(f"records: {result['record_count']}")
    print(f"digest: {result['deterministic_digest']}")
    print(f"generated: {', '.join(result['generated_files'])}")
    return 0


__all__ = ["GoldenPathError", "OUTPUT_FILES", "build_parser", "main", "run_activities"]
