from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ..common.time import (
    DEFAULT_TIMEZONE,
    TimezoneDataUnavailableError,
    TimezoneNameInvalidError,
    resolve_timezone_name,
)
from ..intake.source import is_disk_full
from .merge import (
    ActivitiesNotReadableError,
    SnapshotBuildOutputError,
    SnapshotMergeError,
    build_approved_input,
)
from .store import (
    NOTICE_MESSAGES,
    SnapshotStoreError,
    initialize_store,
    register_snapshot,
    shown_store_message,
    snapshot_status,
    verification_error,
    verify_store,
)


SnapshotLifecycleError = SnapshotStoreError
# The build of a Snapshot run is written in the temporary folder
# (stage A3d-3b).
SNAPSHOT_BUILD_TEMP_MESSAGE = (
    "the temporary folder does not have enough free space to build the Snapshots; "
    "free some space"
)


def run_snapshot_all(
    store_root: str | Path,
    output_root: str | Path,
    *,
    external_safe_pack: bool = False,
    processing_sequence: list[str] | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict[str, Any]:
    """Build an approved cumulative input and run the existing Run-All pipeline."""
    from ..run_all import (
        ACTIVITIES_NOT_READABLE_MESSAGE,
        RunAllError,
        check_run_output,
        run_all,
    )

    try:
        timezone_name = resolve_timezone_name(timezone_name)
    except (TimezoneDataUnavailableError, TimezoneNameInvalidError) as exc:
        raise RunAllError(exc.code, exc.safe_message) from exc
    # The output is checked before the build, which can take long (stage A3d-3a).
    check_run_output(output_root)
    verification = verify_store(store_root)
    if verification["status"] != "PASS":
        raise verification_error(verification, SnapshotMergeError)
    output = Path(output_root)
    try:
        temporary_folder = tempfile.TemporaryDirectory(prefix="garmin-snapshot-run-all-")
    except OSError as exc:
        if is_disk_full(exc):
            raise RunAllError("TEMP_SPACE_INSUFFICIENT", SNAPSHOT_BUILD_TEMP_MESSAGE) from exc
        raise
    with temporary_folder as temporary:
        build_root = Path(temporary) / "canonical-build"
        try:
            build = build_approved_input(
                store_root,
                build_root,
                processing_sequence=processing_sequence,
            )
        except ActivitiesNotReadableError as exc:
            # As a one-shot run of the same Exports stops (stage A3c-2).
            raise RunAllError("ACTIVITIES_EMPTY", ACTIVITIES_NOT_READABLE_MESSAGE) from exc
        except SnapshotBuildOutputError as exc:
            # The build is written in the temporary folder (stage A3d-3b).
            if exc.code == "OUTPUT_SPACE_INSUFFICIENT":
                raise RunAllError("TEMP_SPACE_INSUFFICIENT", SNAPSHOT_BUILD_TEMP_MESSAGE) from exc
            raise
        result = run_all(
            build_root / "approved_input",
            output,
            external_safe_pack=external_safe_pack,
            timezone_name=timezone_name,
            snapshot_context={
                "lineage": build["lineage"],
                "coverage": build["coverage"],
                "merge_summary": build["merge_summary"],
                "source_completeness_context": build[
                    "source_completeness_context"
                ],
                "fit_snapshot_numbers": build["fit_snapshot_numbers"],
                "family_file_counts": build["family_file_counts"],
                "lactate_threshold_counts": build["lactate_threshold_counts"],
                "private_field_counts": build["private_field_counts"],
                "record_changes": build["record_changes"],
                "files_left_out": build["files_left_out"],
                "files_not_read": build["files_not_read"],
                "files_with_repaired_text": build["files_with_repaired_text"],
                **build["relationship_context"],
            },
        )
    return {
        **result,
        "snapshot_count": build["snapshot_count"],
        "canonical_build_sha256": build["canonical_build_sha256"],
        "store_verification": verification["status"],
        "processing_sequence": build["processing_sequence"],
    }


__all__ = [
    "NOTICE_MESSAGES",
    "SNAPSHOT_BUILD_TEMP_MESSAGE",
    "SnapshotLifecycleError",
    "build_approved_input",
    "initialize_store",
    "register_snapshot",
    "run_snapshot_all",
    "shown_store_message",
    "snapshot_status",
    "verification_error",
    "verify_store",
]
