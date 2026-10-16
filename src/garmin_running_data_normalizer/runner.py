from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from contextlib import ExitStack, contextmanager, suppress
from pathlib import Path
from typing import Any, Iterator

from . import __version__
from .common.time import (
    DEFAULT_TIMEZONE,
    TimezoneDataUnavailableError,
    TimezoneNameInvalidError,
    require_timezone_data,
    resolve_timezone_name,
)
from .common.private_files import PRIVATE_DIRECTORY_MODE, open_private_file
from .intake.accounts import asset_accounts
from .intake.discovery import ExportReading, InputChangedError, read_export, repaired_text_count
from .intake.roots import MixedExportsError
from .intake.source import (
    CorruptArchiveError,
    ExportTooLargeError,
    InputNotReadableError,
    TempSpaceError,
    is_zip_input,
)
from .output_location import (
    MESSAGES as OUTPUT_LOCATION_MESSAGES,
    OutputLocationError,
    check_output_location,
    output_path_too_long,
    path_error_code,
    valid_output_name,
    write_error_code,
)
from .normalizers.activities import normalize_activities
from .normalizers.records import EMPTY_RECORD, check_values
from .normalizers.source_records import MARK_KINDS
from .qa import summarize_records
from .run_all import (
    TEMP_SPACE_MESSAGE,
    RunAllError,
    _input_error,
    _value_types,
    input_not_readable_message,
    left_out_files,
    run_all,
    shown_message,
)
from .diagnostics.detector import reads_record_file
from .diagnostics.doctor import (
    DoctorError,
    doctor_input,
    doctor_run_output,
    render_doctor_human,
)
from .diagnostics.support_bundle import SupportBundleError, build_support_bundle
from .snapshot import (
    NOTICE_MESSAGES,
    SnapshotLifecycleError,
    shown_store_message,
    verification_error,
)
from .standalone import StandaloneHandoffError, validate_standalone_handoff
from .stops import STOPS, stop_line


OUTPUT_FILES = (
    "normalized_activities.json",
    "qa_summary.json",
    "run_manifest.json",
)


class GoldenPathError(ValueError):
    """Raised when the bounded Golden Path contract is not satisfied.

    ``code`` says why, with Run-All's code for the same problem (stage
    A3d-3a). A problem in the data that Run-All reports and goes on, which the
    Golden Path output has no place for, is ``GOLDEN_PATH_DATA_NEEDS_RUN_ALL``.
    """

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


# The code of the stops for data that Run-All leaves out, keeps, or repairs
# and reports (stage A3d-3a).
DATA_NEEDS_RUN_ALL = "GOLDEN_PATH_DATA_NEEDS_RUN_ALL"


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
    # A path that cannot be looked at, such as a name too long for the
    # system, has a code too (stage A3d-3a).
    try:
        if requested_input.is_symlink():
            raise GoldenPathError("input must not be a symbolic link", "INPUT_SYMLINK")
        input_root = requested_input.resolve()
        is_input = input_root.is_dir() or is_zip_input(input_root)
    except OSError as exc:
        if isinstance(exc, PermissionError):
            raise GoldenPathError(input_not_readable_message([""]), "INPUT_NOT_READABLE") from exc
        raise GoldenPathError(
            "input must be an existing folder or ZIP file", "INPUT_NOT_DIRECTORY"
        ) from exc
    if not is_input:
        raise GoldenPathError("input must be an existing folder or ZIP file", "INPUT_NOT_DIRECTORY")
    try:
        if requested_output.is_symlink():
            raise GoldenPathError("output directory must not be a symbolic link", "OUTPUT_SYMLINK")
        # The name of an output folder that this command makes must be one
        # that Run-All and the GUI take too (stage A5a). It is checked as it
        # was given: Windows drops a dot or a space at the end of a name when
        # it resolves a path. An empty folder that is there already keeps its
        # name.
        if not requested_output.exists() and not valid_output_name(requested_output.name):
            raise GoldenPathError(
                OUTPUT_LOCATION_MESSAGES["OUTPUT_NAME_INVALID"], "OUTPUT_NAME_INVALID"
            )
        output_root = requested_output.resolve()
        if _is_within(output_root, input_root):
            raise GoldenPathError(
                "output directory must be outside the input directory", "OUTPUT_INSIDE_INPUT"
            )
        if output_root.exists():
            if not output_root.is_dir():
                raise GoldenPathError("output path must be a directory", "OUTPUT_EXISTS")
            if any(output_root.iterdir()):
                raise GoldenPathError("output directory must be absent or empty", "OUTPUT_EXISTS")
    except OSError as exc:
        code = path_error_code(requested_output, exc)
        raise GoldenPathError(OUTPUT_LOCATION_MESSAGES[code], code) from exc
    _check_output_place(output_root)
    return input_root, output_root


def _check_output_place(output_root: Path) -> None:
    """Check now the place where the output will be written (stage A3d-3a):
    an empty output folder that is there already is written in, and a new
    one is made next to the place of its staging folder, in a folder that
    must exist (stage A5a)."""
    if not output_root.exists():
        try:
            check_output_location(
                output_root, lambda parent, name: output_path_too_long(parent, name, OUTPUT_FILES)
            )
        except OutputLocationError as exc:
            raise GoldenPathError(exc.safe_message, exc.code) from exc
        return
    try:
        probe = tempfile.mkdtemp(prefix=".write-check-", dir=output_root)
    except OSError as exc:
        code = write_error_code(exc) or "OUTPUT_PARENT_NOT_WRITABLE"
        raise GoldenPathError(OUTPUT_LOCATION_MESSAGES[code], code) from exc
    try:
        os.rmdir(probe)
    except OSError:
        pass  # At most an empty folder whose name starts with a dot remains.


def _check_activities_read(left_out: list[tuple[str, int, str]]) -> None:
    """Stop when an Activities file could not be read (stage A3c).

    Run-All leaves such a file out and lists it; the Golden Path output has no
    such list, so it stops instead of leaving records out silently. Files of
    other families are not used here.
    """
    if any(item["family"] == "activities" for item in left_out_files(left_out)):
        raise GoldenPathError(
            "an Activities file could not be read, which run-all leaves out and lists",
            DATA_NEEDS_RUN_ALL,
        )


def run_activities(
    input_path: str | Path,
    output_path: str | Path,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict[str, Any]:
    """Run the deterministic, activities-only Golden Path."""
    input_root, output_root = _validate_paths(input_path, output_path)
    timezone_name = resolve_timezone_name(timezone_name)
    require_timezone_data(timezone_name)
    with _read_golden_input(input_root) as reading:
        assets = [
            asset
            for asset in reading.assets
            if asset.kind == "json"
            and reads_record_file(asset.member_path or asset.source_path, "activities")
        ]
        _check_activities_read(reading.left_out)
        if not assets:
            raise GoldenPathError(
                "no supported summarizedActivities.json input was found", "ACTIVITIES_NOT_FOUND"
            )
        try:
            if len(asset_accounts(assets)) > 1:
                raise MixedExportsError()
            left_out: Counter[str] = Counter()
            records = normalize_activities(
                str(input_root), timezone_name, assets=assets, left_out=left_out
            )
            # Text with a lone surrogate, repaired as the files were read
            # (stage A3d-2c-1).
            repaired_text = sum(repaired_text_count(asset) for asset in assets)
        except InputChangedError as exc:
            raise GoldenPathError("the input changed while it was read", "INPUT_CHANGED") from exc
        _check_activities_read(reading.left_out)
    # An item that is an empty value holds nothing; Run-All only counts it.
    left_out.pop(EMPTY_RECORD, None)
    if MARK_KINDS & set(left_out):
        # Run-All leaves such items out and counts them; the Golden Path
        # output has no such count, so it stops (stage A3d-2c-2).
        raise GoldenPathError(
            "an Activities file holds an item that is not a record, or a list of "
            "Activities that cannot be read, which run-all leaves out and counts",
            DATA_NEEDS_RUN_ALL,
        )
    if left_out:
        # Run-All leaves such rows out and counts them; the Golden Path output
        # has no such count, so it stops instead of leaving rows out silently
        # (stage A3d-1b).
        raise GoldenPathError(
            "an Activities row has no usable identifier, which run-all leaves out and counts",
            DATA_NEEDS_RUN_ALL,
        )
    # Values are read as Run-All reads them; a value of another form stops the
    # Golden Path, whose output has no place to keep it (stage A3d-2a).
    if check_values(records, _value_types("activities"), ("garmin_activity_key",)).audit_fields():
        raise GoldenPathError(
            "an Activities value has a form that its field does not take, which "
            "run-all leaves empty and keeps in its audit records",
            DATA_NEEDS_RUN_ALL,
        )
    # Run-All repairs such text and reports it; the Golden Path output has no
    # place for the report, so it stops instead of repairing silently.
    if repaired_text:
        raise GoldenPathError(
            "an Activities file holds text with a broken character, such as a "
            "truncated emoji, which run-all writes with U+FFFD and reports",
            DATA_NEEDS_RUN_ALL,
        )
    if not records:
        raise GoldenPathError("supported input contained no activity records", "ACTIVITIES_EMPTY")
    discovered_sources = {(asset.provenance_path, asset.sha256) for asset in assets}
    normalized_sources = {
        (str(record.get("source_path")), str(record.get("source_sha256")))
        for record in records
    }
    if normalized_sources != discovered_sources:
        raise GoldenPathError(
            "input changed or provenance diverged during processing", "PROVENANCE_MISMATCH"
        )
    qa = {
        "dataset": "activities",
        "record_grain": "activity",
        "stable_key": ["garmin_activity_key"],
        "source_asset_count": len(assets),
        **summarize_records(records, key_field="garmin_activity_key"),
    }
    if qa["status"] != "PASS":
        raise GoldenPathError("activity QA did not pass", "OUTPUT_CONTRACT_INVALID")

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
        "local_timezone": timezone_name,
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

    payloads = {
        "normalized_activities.json": normalized_data,
        "qa_summary.json": qa_data,
        "run_manifest.json": manifest_data,
    }
    _publish_golden_output(output_root, payloads)
    return {
        "status": "PASS",
        "record_count": qa["record_count"],
        "deterministic_digest": qa["records_sha256"],
        "generated_files": list(OUTPUT_FILES),
    }


@contextmanager
def _read_golden_input(input_root: Path) -> Iterator[ExportReading]:
    """Open the input, with Run-All's codes for the problems of reading it
    (stage A3d-3a)."""
    with ExitStack() as stack:
        try:
            reading = stack.enter_context(read_export(input_root))
        except Exception as exc:
            error = _input_error(exc)
            raise GoldenPathError(shown_message(error), error.code) from exc
        yield reading


def _publish_golden_output(output_root: Path, payloads: dict[str, bytes]) -> None:
    """Write every output file in a staging folder first, so that a stop, such
    as a disk that runs out of space, leaves no part of an output (stage
    A3d-3a). A new output folder is the staging folder renamed, as Run-All
    publishes its output; into an empty output folder that was there before,
    which keeps its permissions, the written files are moved from a staging
    folder inside it."""
    existing = output_root.exists()
    try:
        if not existing:
            output_root.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{output_root.name}.golden-",
                dir=output_root if existing else output_root.parent,
            )
        )
    except OSError as exc:
        raise _golden_write_error(exc) from exc
    try:
        stage.chmod(PRIVATE_DIRECTORY_MODE)
        for name in OUTPUT_FILES:
            with open_private_file(stage / name) as handle:
                handle.write(payloads[name])
        if existing:
            if any(entry != stage for entry in output_root.iterdir()):
                raise GoldenPathError(
                    "output directory became non-empty during processing", "OUTPUT_EXISTS"
                )
            moved: list[str] = []
            try:
                for name in OUTPUT_FILES:
                    (stage / name).rename(output_root / name)
                    moved.append(name)
            except OSError:
                # The files are moved one at a time; take back those that
                # were, so that a stop leaves no part of an output in the
                # folder that was empty (stage A5b).
                for name in moved:
                    with suppress(OSError):
                        (output_root / name).unlink()
                raise
        else:
            if output_root.exists():
                raise GoldenPathError(
                    "output directory became non-empty during processing", "OUTPUT_EXISTS"
                )
            stage.rename(output_root)
    except GoldenPathError:
        raise
    except OSError as exc:
        raise _golden_write_error(exc) from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _golden_write_error(exc: OSError) -> GoldenPathError:
    code = write_error_code(exc)
    if code is None:
        return GoldenPathError(
            "Golden Path output could not be published atomically", "OUTPUT_PUBLISH_FAILED"
        )
    return GoldenPathError(OUTPUT_LOCATION_MESSAGES[code], code)


def _stop(code: str, message: str) -> int:
    """Print the line of a stop, with the next step of its code, and return
    the exit code of a stop (stage A5b)."""
    print(stop_line(code, message), file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m garmin_running_data_normalizer",
        description="Run bounded local Garmin normalization workflows.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    activities = commands.add_parser(
        "normalize-activities",
        help="Normalize Garmin summarized activities with deterministic QA.",
    )
    activities.add_argument("--input", required=True, help="Garmin Export folder or ZIP file")
    activities.add_argument("--output", required=True, help="Absent or empty output directory")
    activities.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="IANA timezone for local dates and times (default: Asia/Tokyo)",
    )
    combined = commands.add_parser(
        "run-all",
        help="Run the minimum deterministic multi-family Garmin workflow.",
    )
    combined.add_argument("--input", required=True, help="Garmin Export folder or ZIP file")
    combined.add_argument("--output", required=True, help="New output directory")
    combined.add_argument(
        "--external-safe-pack",
        action="store_true",
        help="Add a deterministic, reviewable external-safe Analysis Pack",
    )
    combined.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="IANA timezone for local dates and times (default: Asia/Tokyo)",
    )
    snapshot = commands.add_parser(
        "snapshot",
        help="Manage immutable Garmin Export snapshots and cumulative Run-All.",
    )
    snapshot_commands = snapshot.add_subparsers(
        dest="snapshot_command",
        required=True,
    )
    snapshot_init = snapshot_commands.add_parser(
        "init",
        help="Initialize one local snapshot store for one opaque account boundary.",
    )
    snapshot_init.add_argument("--store", required=True)
    snapshot_init.add_argument(
        "--account",
        "--account-store-id",
        dest="account_store_id",
        required=True,
    )
    snapshot_register = snapshot_commands.add_parser(
        "register",
        help="Register a complete immutable Garmin Export observation.",
    )
    snapshot_register.add_argument("--store", required=True)
    snapshot_register.add_argument("--input", required=True, help="Garmin Export folder or ZIP file")
    snapshot_register.add_argument("--label", required=True)
    snapshot_register.add_argument(
        "--requested-at",
        "--export-requested-at",
        dest="export_requested_at",
        required=True,
    )
    snapshot_register.add_argument(
        "--downloaded-at",
        "--export-downloaded-at",
        dest="export_downloaded_at",
        required=True,
    )
    snapshot_register.add_argument(
        "--observed-at",
        "--export-observed-at",
        dest="export_observed_at",
        required=True,
    )
    snapshot_register.add_argument(
        "--confirm-complete",
        action="store_true",
        help="Confirm the Export copy is complete before immutable registration.",
    )
    snapshot_status_parser = snapshot_commands.add_parser(
        "status",
        help="Show privacy-bounded snapshot labels, ordering, and coverage counts.",
    )
    snapshot_status_parser.add_argument("--store", required=True)
    snapshot_verify = snapshot_commands.add_parser(
        "verify",
        help="Verify immutable manifests, blobs, registry order, and account boundary.",
    )
    snapshot_verify.add_argument("--store", required=True)
    snapshot_build = snapshot_commands.add_parser(
        "build-input",
        help="Build a new deterministic cumulative approved input view.",
    )
    snapshot_build.add_argument("--store", required=True)
    snapshot_build.add_argument("--output", required=True)
    snapshot_run_all = snapshot_commands.add_parser(
        "run-all",
        help="Build cumulative input and execute the existing Run-All contract.",
    )
    snapshot_run_all.add_argument("--store", required=True)
    snapshot_run_all.add_argument("--output", required=True)
    snapshot_run_all.add_argument(
        "--external-safe-pack",
        action="store_true",
        help="Add the existing deterministic external-safe Analysis Pack",
    )
    snapshot_run_all.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="IANA timezone for local dates and times (default: Asia/Tokyo)",
    )
    handoff = commands.add_parser(
        "validate-handoff",
        help="Validate a completed Run-All output without repository access.",
    )
    handoff.add_argument("--input", required=True, help="Completed Run-All output")
    doctor = commands.add_parser(
        "doctor",
        help="Explain bounded pre-run or completed Run-All evidence without changing it.",
    )
    doctor_mode = doctor.add_mutually_exclusive_group(required=True)
    doctor_mode.add_argument("--input", help="Garmin Export folder or ZIP file to inspect")
    doctor_mode.add_argument("--run-output", help="Completed Run-All output to inspect")
    doctor.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Diagnostic presentation format",
    )
    doctor.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="IANA timezone whose data --input checks (default: Asia/Tokyo)",
    )
    support_bundle = commands.add_parser(
        "support-bundle",
        help="Generate a deterministic public-safe diagnostic Bundle for Human review.",
    )
    support_bundle.add_argument("--run-output", required=True, help="Completed v1.4 Run-All output")
    support_bundle.add_argument("--output", required=True, help="New Support Bundle ZIP path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "normalize-activities":
            result = run_activities(args.input, args.output, args.timezone)
        elif args.command == "run-all":
            result = run_all(
                args.input,
                args.output,
                external_safe_pack=args.external_safe_pack,
                timezone_name=args.timezone,
            )
        elif args.command == "snapshot":
            from .snapshot import (
                build_approved_input,
                initialize_store,
                register_snapshot,
                run_snapshot_all,
                snapshot_status,
                verify_store,
            )

            if args.snapshot_command == "init":
                result = initialize_store(args.store, args.account_store_id)
            elif args.snapshot_command == "register":
                result = register_snapshot(
                    args.store,
                    args.input,
                    snapshot_label=args.label,
                    export_requested_at=args.export_requested_at,
                    export_downloaded_at=args.export_downloaded_at,
                    export_observed_at=args.export_observed_at,
                    confirm_complete=args.confirm_complete,
                )
            elif args.snapshot_command == "status":
                result = snapshot_status(args.store)
            elif args.snapshot_command == "verify":
                result = verify_store(args.store)
            elif args.snapshot_command == "build-input":
                result = build_approved_input(args.store, args.output)
            elif args.snapshot_command == "run-all":
                result = run_snapshot_all(
                    args.store,
                    args.output,
                    external_safe_pack=args.external_safe_pack,
                    timezone_name=args.timezone,
                )
            else:
                raise GoldenPathError("unsupported snapshot command", "COMMAND_UNSUPPORTED")
        elif args.command == "validate-handoff":
            result = validate_standalone_handoff(args.input)
        elif args.command == "doctor":
            result = (
                doctor_input(args.input, timezone_name=args.timezone)
                if args.input is not None
                else doctor_run_output(args.run_output)
            )
        elif args.command == "support-bundle":
            result = build_support_bundle(args.run_output, args.output)
        else:
            raise GoldenPathError("unsupported command", "COMMAND_UNSUPPORTED")
    # Every stop prints what happened and the next step of its code (stage
    # A5b), and exits with 2.
    except GoldenPathError as exc:
        return _stop(exc.code, str(exc))
    # A folder or file of the input that this app may not open, met while a
    # Snapshot is registered (stage A3d-3a).
    except InputNotReadableError as exc:
        return _stop("INPUT_NOT_READABLE", input_not_readable_message(exc.places))
    except (TimezoneDataUnavailableError, TimezoneNameInvalidError) as exc:
        return _stop(exc.code, exc.safe_message)
    except RunAllError as exc:
        return _stop(exc.code, shown_message(exc))
    # Each stop of the Snapshot Store has its code (stage A3d-3b); the stops
    # of the store's contract keep SNAPSHOT_LIFECYCLE_FAILED.
    except SnapshotLifecycleError as exc:
        return _stop(exc.code, shown_store_message(exc))
    except StandaloneHandoffError as exc:
        return _stop("HANDOFF_INVALID", str(exc))
    except DoctorError as exc:
        return _stop(exc.code, exc.safe_message)
    except SupportBundleError as exc:
        return _stop(exc.code, exc.safe_message)
    # The same codes as Run-All, for the commands that read an Export without
    # Run-All (normalize-activities and snapshot register) and for a Snapshot
    # Store that holds the Exports of more than one account.
    except MixedExportsError as exc:
        return _stop(exc.code, exc.safe_message)
    except CorruptArchiveError:
        return _stop("INPUT_ZIP_CORRUPT", STOPS["INPUT_ZIP_CORRUPT"].what)
    except ExportTooLargeError:
        return _stop("INPUT_TOO_LARGE", STOPS["INPUT_TOO_LARGE"].what)
    except TempSpaceError:
        return _stop("TEMP_SPACE_INSUFFICIENT", TEMP_SPACE_MESSAGE)
    except Exception:
        # Until stage A3d-3a, the other commands also said "Golden Path
        # failed", and until stage A3d-3b, the other snapshot commands "Run-All
        # failed"; until stage A5b, the next step of all three was to verify
        # the input and output contract.
        if args.command == "run-all" or (
            args.command == "snapshot" and args.snapshot_command == "run-all"
        ):
            return _stop("RUN_ALL_FAILED", STOPS["RUN_ALL_FAILED"].what)
        if args.command == "normalize-activities":
            return _stop("GOLDEN_PATH_FAILED", STOPS["GOLDEN_PATH_FAILED"].what)
        name = f"snapshot {args.snapshot_command}" if args.command == "snapshot" else args.command
        return _stop("COMMAND_FAILED", f"{name} stopped unexpectedly")

    if args.command == "run-all" or (
        args.command == "snapshot" and args.snapshot_command == "run-all"
    ):
        totals = result["warning_totals"]
        print(f"STATUS: {result['status']}")
        print(f"exit: {result['exit_code']}")
        # The total, the count of each family, and on their own line the
        # warnings that belong to no family, as the GUI reports them (stage
        # A5a); the last line is printed even when its counts are 0.
        print(f"warnings: {totals['total']}")
        for family, details in result["family_results"].items():
            print(
                f"{family}: detected={details['detected_asset_count']} "
                f"processed={details['processed_asset_count']} "
                f"skipped={details['skipped_asset_count']} "
                f"records={details['record_count']} "
                f"warnings={details['warning_count']} errors={details['error_count']}"
            )
        print(
            "other warnings: "
            + " ".join(f"{name}={count}" for name, count in totals["other"].items())
        )
        print(f"generated: {', '.join(result['generated_files'])}")
        print(f"digest: {result['deterministic_digest']}")
        return int(result["exit_code"])

    if args.command == "snapshot":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        # A NOTE line never means a stop; an ERROR line always does
        # (stage A3d-3b).
        for code in result.get("notices", []):
            print(f"NOTE [{code}]: {NOTICE_MESSAGES[code]}", file=sys.stderr)
        if result.get("status") == "PASS":
            return 0
        if args.snapshot_command == "verify":
            error = verification_error(result)
            return _stop(error.code, str(error))
        return 2

    if args.command == "validate-handoff":
        print("PASS")
        print(f"datasets: {result['dataset_count']}")
        print(f"relationships: {result['explicit_relationship_count']}")
        # The total of the run's warnings, as the GUI's check of an output
        # reports it (stage A5a).
        print(f"warnings: {result['warning_count']}")
        print(f"first-read: {result['first_read']}")
        print(f"analysis-entry: {result['analysis_entry_point']}")
        return 0

    if args.command == "doctor":
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_doctor_human(result))
        return 0

    if args.command == "support-bundle":
        print("PASS")
        print(f"generated: {result['path']}")
        print(f"members: {result['member_count']}")
        print(f"digest: {result['archive_sha256']}")
        print("Human review required before sharing")
        return 0

    print("PASS")
    print(f"records: {result['record_count']}")
    print(f"digest: {result['deterministic_digest']}")
    print(f"generated: {', '.join(result['generated_files'])}")
    return 0


__all__ = ["GoldenPathError", "OUTPUT_FILES", "build_parser", "main", "run_activities"]
