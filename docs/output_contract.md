# Run-All Output Contract

## Status and authority

- Current stable contract: v1.3.1
- Compatibility family: stable 1.x

This document describes the current stable contract and identifies when each
additive layer entered the `1.x` family. Executable authority remains in
`run_all.py`, the versioned dataset registry, and each run's `run_manifest.json`
and `run_summary.json`.

Both machine authorities record the exact installed `product_version`;
`ANALYSIS_CONTEXT.json` preserves the same value for standalone handoff.

The Dataset Catalog, Dataset Relationship Catalog, and Analysis Handoff
Specification are normative human-readable guidance projected from those
authorities.

## Core stable 1.x layout

```text
<output>/
  normalized/
    activities.json
    gear.json
    activity_gear.json
    personal_records.json
    fit_sessions.json
    fit_laps.json
    activity_fit_links.json
  audit/
    fit_audit.json
    activity_fit_linkage.json
  analysis/activities.csv
  qa/
    dataset_summary.json
    relationship_summary.json
  START_HERE.md
  DATASET_INVENTORY.md
  ANALYSIS_HANDOFF.md
  ANALYSIS_CONTEXT.json
  SCHEMA_CATALOG.json
  artifact_inventory.json
  run_manifest.json
  run_summary.json
```

`run_summary.json` is written last and is the completion marker. A directory
without it is not a completed handoff. Existing v1 paths are preserved; all
v1.1 paths are additive. With `--external-safe-pack`,
`analysis/external_safe_handoff.zip` is additionally emitted and listed.

## Dataset and FIT behavior

Activities are required. Gear, Personal Records, and FIT are optional. Stable
normalized files are always emitted, with empty arrays and
`SKIPPED_NOT_PRESENT` evidence for an absent optional family.

FIT input is accepted for normalization only after file CRC validation and,
when present, header CRC validation. Unsupported chained files, malformed or
truncated files, CRC failures, undefined local messages, and session/lap
allocation conflicts remain auditable incomplete input. CRC-valid multi-session
files are normalized when declared lap counts allocate every lap to exactly one
session. When that allocation cannot be proven, the whole file is excluded from
normalized FIT sessions/laps and recorded as
`session_lap_allocation_conflict` in `audit/fit_audit.json`; no session or lap is
guessed. Those excluded records never enter the eligible Activity/FIT
Relationship Coverage population. `fit_file_id` is retained for compatibility;
`fit_session_key` and `fit_lap_key` are the v1.1 stable keys.

FIT protocol invalid sentinels are converted to JSON null before scaling or
enum projection. The per-file audit, FIT family result, and dataset QA record
deterministic counts by message and field so semantic cleanup remains
traceable to source-relative provenance without exposing a raw sentinel as a
valid domain value.

Cross-dataset joins are valid only through the Dataset Relationship Catalog.
Activity/FIT identity is represented by the separate
`activity_fit_links` dataset and never replaces physical FIT identity.

## Additive v1.1 relationship handoff

`START_HERE.md`, `DATASET_INVENTORY.md`, and `ANALYSIS_HANDOFF.md` are
deterministic projections of the machine authorities. They do not recompute
normalization semantics. `ANALYSIS_CONTEXT.json` declares the analysis entry
point, dataset states, explicit relationships, warnings, prohibited
operations, and privacy mode. `SCHEMA_CATALOG.json` comes from the runtime
schema definitions, not the first data row. Source identifiers that Garmin may
emit as either a JSON integer or string—`activity_id`, `gear_key`, and
`personal_record_id`—use the explicit `integer|string` logical type; the
normalizer does not silently coerce identity.

For every normalized dataset, both machine artifacts also declare the runtime
grain and stable key plus identical `relationship_role`, `semantic_role`,
`canonical`, `projection_of`, `activity_relationship`, `join_guidance`,
`forbidden_join_guidance`, `cardinality`, `allowed_use`, `limitations`, and
`derived_projection` metadata. Direct joins still require a reviewed explicit
relationship. A `context_only` entry permits a separately labelled same-day
comparison but never an Activity fact-table merge. Derived CSV and QA daily
views are non-canonical and have no selected-row rule.

Every schema field separately declares `required` and `nullable`. A required
field must be present in every record but may still allow an explicit JSON
`null`; an optional field may be omitted when the source FIT definition did
not contain that field. Runtime values are checked against the catalog before
Run-All publishes output. Source duration, distance, and timestamp-like
numeric fields use `number` when Garmin exports may contain either JSON
integers or decimals. `start_time_local_raw` uses `number|string` because the
source representation is preserved rather than silently coerced.

`START_HERE.md`, `ANALYSIS_HANDOFF.md`, and `ANALYSIS_CONTEXT.json` include
Relationship Coverage for every explicit relationship. Each entry reports the
eligible population, explicit-link count, coverage percentage, unresolved,
ambiguous, and duplicate counts, whether inference was performed, and the
primary unresolved reason. Coverage communicates the evidence boundary and is
not a success score. Detailed referential and Activity/FIT evidence remains
authoritative in `qa/relationship_summary.json` and
`audit/activity_fit_linkage.json`.

The optional external-safe Analysis Pack is deterministic and allowlist-only.
It excludes source paths, filenames, source hashes, raw identifiers/stable
keys, memo text, coordinates, exact dates/timestamps, heart rate, power,
cadence, training effect/load, other unneeded health or performance detail,
and unlisted files. Its default profile is limited to month-level activity
volume and count context. It is never uploaded automatically.

## Status and exit contract

| Run status | Exit code | Meaning |
|---|---:|---|
| `PASS` | 0 | Every detected family completed without warnings |
| `PASS_WITH_WARNINGS` | 0 | Valid output exists with disclosed non-fatal warnings |
| `PARTIAL_SUCCESS` | 3 | Activities are valid and detected FIT input is auditably incomplete |
| Fatal error | 2 | No valid completed output is published |

Family states include `PROCESSED`, `SKIPPED_NOT_PRESENT`,
`PROCESSED_EMPTY`, and FIT-specific `PARTIAL`.

## Determinism and publication

- Input is read-only and re-snapshotted before atomic publication.
- Output must not already exist.
- Normalized records, relationship rows, guidance, machine context, and ZIP
  entries use deterministic ordering.
- The manifest lists every payload with size and SHA-256.
- Manifest and summary share a deterministic output digest.
- Run-All does not send or upload output.

## Compatibility boundary

The CLI, existing paths, manifest/summary formats, status meanings, completion
marker, exit behavior, and compatible legacy FIT fields remain stable `1.x`
contracts. v1.1 adds relationship artifacts, FIT session/lap stable keys,
generated analysis context, and an opt-in safe pack under explicit Product
approval.

## Additive v1.2 Snapshot lifecycle

The existing one-shot command, paths, statuses, and completion semantics remain
unchanged. `snapshot run-all` first creates an immutable cumulative approved
input and then invokes the same Run-All implementation. It adds:

```text
snapshot/
  snapshot_lineage.json
  snapshot_coverage.json
  canonical_merge_summary.json
```

The lineage binds the ordered immutable Snapshot set, policy registry, current
parser/schema versions, and deterministic Canonical build identity. Coverage
reports dataset presence patterns, previous-only retention, new and reappeared
records, changed records/fields, review holds, unsupported objects, pairwise and
leave-one-out evidence. Missing from a later Export never means delete.
Explicit null or empty values preserve an earlier explicit value and remain
reviewable. Automatic deletion and timestamp-only relationship inference are
both `false`.

The local Canonical build also records `canonical_merge_manifest.json`,
`snapshot_delta_report.json`, `presence_pattern_report.json`,
`field_provenance.json`, `review_holds.json`, and
`approved_input_manifest.json`. Those build artifacts are private lifecycle
evidence and are not added to a normal one-shot output.

## Additive v1.3 Wellness / Metrics

The stable v1.3.0 release adds the following optional Run-All artifacts:

```text
normalized/hill_score_daily.json
normalized/endurance_score_daily.json
normalized/race_prediction_daily.json
normalized/sleep_daily.json
normalized/uds_daily.json
normalized/acute_training_load_daily.json
normalized/training_readiness_daily.json
normalized/vo2max_daily.json
normalized/hrv_daily.json
normalized/training_history_daily.json
audit/hill_score_daily.json
audit/endurance_score_daily.json
audit/lactate_threshold_candidates.json
audit/race_prediction_daily.json
audit/sleep_daily.json
audit/uds_daily.json
audit/acute_training_load_daily.json
audit/training_readiness_daily.json
audit/vo2max_daily.json
audit/hrv_daily.json
audit/training_history_daily.json
analysis/performance_metrics_daily.csv
qa/performance_metrics_summary.json
qa/daily_metrics_summary.json
```

The listed normalized datasets are optional stable datasets. When their
source files are absent, Run-All emits empty normalized arrays and
`SKIPPED_NOT_PRESENT` family evidence without adding a warning. Detected rows
with missing or invalid required values remain visible through aggregate audit
and warning counts. Race Prediction, Acute Training Load, Training Readiness,
VO2Max, and Training History retain one row per source observation and expose
`observation_timestamp`; no latest-wins or canonical daily-row selection is
performed. Divergent public values for one stable key fail
closed; HRV instead emits an unresolved review row with no selected value. The
public rows intentionally exclude device, account, unapproved raw timestamp,
and source-path fields. The five observation contracts expose only their
normalized `observation_timestamp`. Health Status remains deferred.

The Lactate Threshold file is an audit-only candidate catalog. It preserves
source-family distinctions and explicitly records unconfirmed unit/timezone
semantics; it does not publish a stable dataset, infer a machine stable key, or
select a latest value. `analysis/performance_metrics_daily.csv` namespaces the
two stable daily contexts with `hill_` and `endurance_` prefixes and
does not authorize an Activity date join.

The Lactate candidate entry in `ANALYSIS_CONTEXT.json` carries the same
candidate boundary: one source-backed observation grain, no machine stable
key, Activity relationship `not_yet_defined`, no join guidance, and no
canonical daily projection. This metadata does not promote the audit file to a
normalized dataset.

When Snapshot Merge observes multiple accepted Lactate candidates without
resolved authority, it preserves the distinct candidates, records exact replay
counts and an unresolved candidate status, and continues with a warning. This
candidate-only warning does not make Stable promotion available and does not
select a winner. Malformed source structure remains fail-closed.

Race Prediction, Sleep, UDS, Acute Training Load, Training Readiness, VO2Max,
HRV, and Training History remain separate context. Their detailed fields,
generation boundary, source-series behavior, missing-value policy, and
interpretation limits are defined in [Wellness and Daily Metrics](wellness_metrics.md).

## Privacy boundary

Full normalized output contains personal metrics, local identifiers,
provenance, hashes, exact timestamps, memo text, and source-relative filenames.
Garmin source filenames can contain email-shaped personal identifiers. It is a
local/trusted handoff. Public fixtures are synthetic. External transfer requires
review of the optional safe pack and the receiving environment.
