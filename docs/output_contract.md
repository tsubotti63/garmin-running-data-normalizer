# Run-All Output Contract

## Status and authority

This document defines the additive Run-All v1.1 contract. Executable authority
remains in `run_all.py`, the versioned dataset registry, and each run's
`run_manifest.json` and `run_summary.json`.

Both machine authorities record the exact installed `product_version`;
`ANALYSIS_CONTEXT.json` preserves the same value for standalone handoff.

The Dataset Catalog, Dataset Relationship Catalog, and Analysis Handoff
Specification are normative human-readable guidance projected from those
authorities.

## Run-All v1.1 layout

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

## Output Experience

`START_HERE.md`, `DATASET_INVENTORY.md`, and `ANALYSIS_HANDOFF.md` are
deterministic projections of the machine authorities. They do not recompute
normalization semantics. `ANALYSIS_CONTEXT.json` declares the analysis entry
point, dataset states, explicit relationships, warnings, prohibited
operations, and privacy mode. `SCHEMA_CATALOG.json` comes from the runtime
schema definitions, not the first data row. Source identifiers that Garmin may
emit as either a JSON integer or string—`activity_id`, `gear_key`, and
`personal_record_id`—use the explicit `integer|string` logical type; the
normalizer does not silently coerce identity.

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

## Privacy boundary

Full normalized output contains personal metrics, local identifiers,
provenance, hashes, exact timestamps, memo text, and source-relative filenames.
Garmin source filenames can contain email-shaped personal identifiers. It is a
local/trusted handoff. Public fixtures are synthetic. External transfer requires
review of the optional safe pack and the receiving environment.
