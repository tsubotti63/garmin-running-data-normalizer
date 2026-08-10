from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .merge import SnapshotMergeError, build_approved_input
from .store import (
    SnapshotStoreError,
    initialize_store,
    register_snapshot,
    snapshot_status,
    verify_store,
)


SnapshotLifecycleError = SnapshotStoreError


def run_snapshot_all(
    store_root: str | Path,
    output_root: str | Path,
    *,
    external_safe_pack: bool = False,
) -> dict[str, Any]:
    """Build an approved cumulative input and run the existing Run-All pipeline."""
    verification = verify_store(store_root)
    if verification["status"] != "PASS":
        raise SnapshotMergeError("snapshot store verification failed")
    output = Path(output_root)
    with tempfile.TemporaryDirectory(prefix="garmin-snapshot-run-all-") as temporary:
        build_root = Path(temporary) / "canonical-build"
        build = build_approved_input(store_root, build_root)
        from ..run_all import run_all

        result = run_all(
            build_root / "approved_input",
            output,
            external_safe_pack=external_safe_pack,
            snapshot_context={
                "lineage": build["lineage"],
                "coverage": build["coverage"],
                "merge_summary": build["merge_summary"],
                **build["relationship_context"],
            },
        )
    return {
        **result,
        "snapshot_count": build["snapshot_count"],
        "canonical_build_sha256": build["canonical_build_sha256"],
        "store_verification": verification["status"],
    }


__all__ = [
    "SnapshotLifecycleError",
    "build_approved_input",
    "initialize_store",
    "register_snapshot",
    "run_snapshot_all",
    "snapshot_status",
    "verify_store",
]
