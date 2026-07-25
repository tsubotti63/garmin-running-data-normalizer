# Snapshot Accumulation Public Adaptation — Implementation Report

Status: Public implementation and validation complete; release candidate
review in progress
Target: v1.2.0
Stable compatibility baseline: v1.1.1
Public/private boundary: synthetic public evidence; real Snapshots local only

## Reference implementation

The implementation adapts the reviewed predecessor Snapshot Store, candidate,
diff, dataset-policy, full-rebuild, test, script, design, and QA assets. The
curated Work Package copies were verified byte-for-byte against the designated
Stable Release Public Edition Source Tree before adaptation.

No `running_platform` or phase-specific production import is introduced. The
public package keeps the current `garmin_running_data_normalizer` namespace,
standard-library runtime dependency boundary, stable keys, archive controls,
FIT parser, relationship policy, and one-shot Run-All behavior.

## Implemented public scope

- Opaque one-store/one-account boundary.
- Explicit completeness confirmation and timezone-aware lifecycle metadata.
- Immutable content-addressed files and safe archive-member inventory.
- Arbitrary historical insertion, content-idempotent registration, lock,
  journal reconciliation, integrity verification, and no garbage collection.
- Versioned public dataset merge policy.
- Missing/not-delete behavior, null/empty review holds, raw null-key holds,
  deterministic conflict stops, provenance, presence patterns, pairwise,
  prefixes, and leave-one-out evidence.
- Cumulative unique FIT materialization and current-parser regeneration.
- Additive CLI, approved input, Snapshot Run-All, lineage, coverage, and Output
  Experience integration.

## Intentional public adaptation

The predecessor implementation was not copied as-is. Private paths, known IDs,
phase status vocabulary, source namespaces, pandas/PyYAML assumptions, and
private evidence were excluded. The predecessor restriction to append/earliest
backfill was replaced with deterministic arbitrary insertion; lock/journal
recovery and cumulative unique FIT materialization were added to meet the
approved Public lifecycle contract.

## Boundaries

- Missing from a later Snapshot is never an automatic delete.
- Explicit null/empty does not clear a prior explicit value.
- Unknown/unsupported input is preserved privately but is not promoted.
- Snapshot Store, approved input, and full Run-All output are private local
  artifacts.
- Tag, GitHub Release, TestPyPI, and Production PyPI remain separate Human
  Approval Boundaries.

## Validation closeout

Synthetic lifecycle, recovery, order-invariance, determinism, package-installed
flow, and privacy-boundary checks are complete. Public-safe aggregate evidence
from four repeated private/local Garmin Exports also confirms cumulative
rebuild behavior without placing private paths, rows, identifiers, filenames,
or source hashes in the repository. Release publication remains outside this
implementation report.
