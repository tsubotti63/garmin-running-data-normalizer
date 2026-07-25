"""Additive Garmin Export snapshot lifecycle.

The snapshot package preserves immutable local inputs and materializes a
deterministic approved input view for the existing one-shot Run-All pipeline.
"""

from .lifecycle import (
    SnapshotLifecycleError,
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    snapshot_status,
    verify_store,
)

__all__ = [
    "SnapshotLifecycleError",
    "build_approved_input",
    "initialize_store",
    "register_snapshot",
    "run_snapshot_all",
    "snapshot_status",
    "verify_store",
]
