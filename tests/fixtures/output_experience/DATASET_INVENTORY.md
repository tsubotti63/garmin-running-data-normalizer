# Dataset Inventory

This document is a deterministic human-readable projection of
`run_manifest.json`, `run_summary.json`, the dataset registry, and the
Run-All v1 runtime dataset definitions. The machine-readable artifacts
remain authoritative.

Run status: `PASS`

| Dataset | Family status | Required | Output path | Grain | Stable key | Records |
|---|---|---:|---|---|---|---:|
| `activities` | `PROCESSED` | yes | `normalized/activities.json` | activity | `garmin_activity_key` | 2 |
| `gear` | `PROCESSED` | no | `normalized/gear.json` | gear | `gear_key` | 1 |
| `activity_gear` | `PROCESSED` | no | `normalized/activity_gear.json` | activity_gear_link | `gear_key`, `activity_id` | 1 |
| `personal_records` | `PROCESSED` | no | `normalized/personal_records.json` | personal_record | `personal_record_id` | 1 |
| `fit_sessions` | `PROCESSED` | no | `normalized/fit_sessions.json` | fit_file_session | `fit_file_id` | 1 |
| `fit_laps` | `PROCESSED` | no | `normalized/fit_laps.json` | fit_file_lap | `fit_file_id`, `lap_index` | 2 |

## Interpretation Rules

- `SKIPPED_NOT_PRESENT` is an expected state for an absent optional family.
- `PROCESSED_EMPTY` is distinct from an absent family.
- Stable keys are local identifiers and are not permission to publish them.
- Record counts and paths are projections; provenance and integrity evidence
  remain in `run_manifest.json` and the normalized records.
- Cross-dataset joins are authorized only by the repository Dataset
  Relationship Catalog. Do not infer a relationship from similar fields or
  timestamp proximity.
