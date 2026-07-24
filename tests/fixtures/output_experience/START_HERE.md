# Start Here

This document is a deterministic navigation view of the completed Run-All
machine artifacts. It does not replace `run_summary.json`,
`run_manifest.json`, dataset QA, or audit evidence.

## Run Status

- Status: `PASS`
- Run-All contract version: `1`
- Warning count: 0
- Error count: 0

## Dataset Families

| Family | Status | Records | Warnings | Errors |
|---|---|---:|---:|---:|
| `activities` | `PROCESSED` | 2 | 0 | 0 |
| `gear` | `PROCESSED` | 2 | 0 | 0 |
| `personal_records` | `PROCESSED` | 1 | 0 | 0 |
| `fit` | `PROCESSED` | 4 | 0 | 0 |

## Recommended Reading Order

1. Confirm this run status and any warnings below.
2. Review `DATASET_INVENTORY.md` for dataset grain, keys, and availability.
3. Read `ANALYSIS_HANDOFF.md` before supplying files to an analyst or AI.
4. Use `ANALYSIS_CONTEXT.json` and `SCHEMA_CATALOG.json` for machine context.
5. Use only relationships marked explicit in the handoff/context.
6. Use QA or audit evidence when a warning, partial result, or validation
   question affects the analysis.

Recommended trusted-local analysis entry point: `analysis/activities.csv`.

### Available Analysis Files

- `analysis/activities.csv`

### QA Evidence

- `qa/dataset_summary.json`
- `qa/relationship_summary.json`

### Audit Evidence

- `audit/activity_fit_linkage.json`
- `audit/fit_audit.json`

## Relationship Coverage

Coverage communicates the evidence boundary; it is not a success score.
Detailed relationship QA remains authoritative in
`qa/relationship_summary.json`. Activity/FIT exclusions and match evidence
remain in `audit/activity_fit_linkage.json`.

### Activity/Gear Links → Activities

- Eligible population: 1 (Activity/Gear link records)
- Explicit links: 1
- Coverage: 100.00%
- Unresolved: 0
- Ambiguous: 0
- Duplicate: 0
- Inference performed: No
- Primary unresolved reason: None

### Activity/Gear Links → Gear

- Eligible population: 1 (Activity/Gear link records)
- Explicit links: 1
- Coverage: 100.00%
- Unresolved: 0
- Ambiguous: 0
- Duplicate: 0
- Inference performed: No
- Primary unresolved reason: None

### Personal Records → Activities

- Eligible population: 1 (nonzero-activity Personal Records)
- Explicit links: 1
- Coverage: 100.00%
- Unresolved: 0
- Ambiguous: 0
- Duplicate: 0
- Inference performed: No
- Primary unresolved reason: None

### FIT Laps → FIT Sessions

- Eligible population: 2 (FIT Laps)
- Explicit links: 2
- Coverage: 100.00%
- Unresolved: 0
- Ambiguous: 0
- Duplicate: 0
- Inference performed: No
- Primary unresolved reason: None

### Activity ↔ FIT — Activity coverage

- Eligible population: 2 (Activities)
- Explicit links: 1
- Coverage: 50.00%
- Unresolved: 1
- Ambiguous: 0
- Duplicate: 0
- Inference performed: No
- Primary unresolved reason: `no_evidence_qualified_candidate`

### Activity ↔ FIT — FIT Session coverage

- Eligible population: 1 (FIT Sessions)
- Explicit links: 1
- Coverage: 100.00%
- Unresolved: 0
- Ambiguous: 0
- Duplicate: 0
- Inference performed: No
- Primary unresolved reason: None

## Relationship Safety

The generated relationship contract declares only reviewed v1.1 joins.
`activity_fit_links` is the sole Activity/FIT join authority. Do not create
a timestamp-only join or infer a relationship from similar fields.

## Privacy

Privacy mode: `local_trusted_full`.

Run-All output can contain personal records, local stable keys, provenance,
exact timestamps, memo text, and source-relative filenames. A Garmin export
filename may itself contain an email-shaped personal identifier. Keep real
output local unless the data owner approves a specific transfer and the
receiving environment has been reviewed. Use the optional external-safe
handoff only after reviewing its aggregation level.

## Next Action

Review warnings and relationship QA, then formulate an analysis question
using only the declared entry point, fields, and explicit relationships.
