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
| `fit` | `PROCESSED` | 3 | 0 | 0 |

## Recommended Reading Order

1. Confirm the status and warnings in `run_summary.json`.
2. Review `DATASET_INVENTORY.md` for dataset grain, keys, and availability.
3. Consult the repository Analysis Handoff Specification before analysis.
4. Consult the Dataset Relationship Catalog before any cross-dataset join.
5. Use QA or audit evidence when a warning, partial result, or validation
   question affects the analysis.

### Available Analysis Files

- `analysis/activities.csv`

### QA Evidence

- `qa/dataset_summary.json`

### Audit Evidence

- `audit/fit_audit.json`

## Relationship Safety

This generated projection does not promote a cross-dataset relationship.
Treat any relationship not declared `explicit` by the repository Dataset
Relationship Catalog as `not_yet_defined`. Do not create timestamp-proximity
joins or infer missing identifiers.

## Privacy

Run-All output can contain personal records, local stable keys, provenance,
and exact timestamps. Keep real output local unless the data owner approves a
specific transfer and the receiving environment has been reviewed.
