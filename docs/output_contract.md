# Run-All Output Contract

## Status and authority

This document consolidates the existing public Run-All v1 contract. It does not
replace the executable authorities:

1. `src/garmin_running_data_normalizer/run_all.py` defines the runtime dataset
   table, stable output paths, completion behavior, and machine artifact formats.
2. `config/dataset_registry.example.json` defines dataset grain, stable keys,
   merge policy, and provenance requirements.
3. `run_manifest.json` and `run_summary.json` are the per-run machine-readable
   authorities.

The [Dataset Catalog](supported_datasets.md), [Dataset Relationship
Catalog](dataset_relationships.md), and [Analysis Handoff
Specification](project/analysis_handoff_spec_v0_1.md) are human-readable
normative guidance projected from those authorities.

## Stable Run-All v1 layout

```text
<output>/
  normalized/
    activities.json
    gear.json
    activity_gear.json
    personal_records.json
    fit_sessions.json
    fit_laps.json
  audit/fit_audit.json
  analysis/activities.csv
  qa/dataset_summary.json
  run_manifest.json
  run_summary.json
```

`run_summary.json` is written last and is the completion marker. A directory
without it is not a completed Run-All handoff.

The Output Experience renderer can deterministically prepare `START_HERE.md`
and `DATASET_INVENTORY.md` from existing machine artifacts. The renderer is not
wired into Run-All v1, and those Markdown names are not part of the stable
output layout above.

## Dataset and family behavior

Activities are required. Gear, Personal Records, and FIT are optional input
families. The six normalized dataset outputs are always present in a completed
Run-All directory; an absent optional family produces an empty array and
`SKIPPED_NOT_PRESENT` evidence instead of invented records.

Dataset grains, keys, roles, and analysis suitability are maintained in the
[Dataset Catalog](supported_datasets.md).

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

- Input is treated as read-only and is checked for change before publication.
- Output must not already exist and is published atomically.
- Dataset records, payloads, and output inventory use deterministic ordering.
- The manifest records dataset digests and output hashes.
- The summary and manifest share the deterministic output digest.
- Human-readable Output Experience documents must be projections of these
  authorities and must not independently recompute normalization semantics.

## Compatibility boundary

The documented CLI, output paths, dataset stable keys, manifest/summary formats,
status meanings, completion marker, and exit behavior are stable `1.x`
contracts. Changing any of them requires compatibility review and Human
Approval.

Documentation may clarify existing behavior. A renderer may be implemented and
tested without changing Run-All. Adding generated documents to the fixed
Run-All output layout remains a separate Product and compatibility decision.

## Privacy boundary

Normalized records, stable keys, source-relative paths, hashes, and exact
timestamps may be private. Machine artifacts remain local by default. Public
examples and golden outputs must use synthetic data. See the [Security and
Privacy Boundary](security_and_privacy_boundary.md) and [Analysis Handoff
Specification](project/analysis_handoff_spec_v0_1.md).
