"""Additive Garmin Export snapshot lifecycle.

The snapshot package preserves immutable local inputs and materializes a
deterministic approved input view for the existing one-shot Run-All pipeline.
"""

from .lifecycle import (
    NOTICE_MESSAGES,
    SnapshotLifecycleError,
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    shown_store_message,
    snapshot_status,
    verification_error,
    verify_store,
)

__all__ = [
    "NOTICE_MESSAGES",
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
