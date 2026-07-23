# Dataset Inventory

This document is a deterministic human-readable projection of
`run_manifest.json`, `run_summary.json`, the dataset registry, and the
Run-All v1 runtime dataset definitions. The machine-readable artifacts
remain authoritative.

Run status: `PASS`

| Dataset | Role | Status | Records | Warnings | Path | Grain | Stable key | Authority | Analysis use | Relationships | Privacy |
|---|---|---|---:|---:|---|---|---|---|---|---|---|
| `activities` | authoritative normalized activities | `PROCESSED` | 2 | 0 | `normalized/activities.json` | activity | `garmin_activity_key` | normalized source of truth | detailed trusted-local activity analysis | `explicit` | `personal-local` |
| `gear` | authoritative normalized gear | `PROCESSED` | 1 | 0 | `normalized/gear.json` | gear | `gear_key` | normalized source of truth | trusted-local gear attributes | `explicit` | `personal-local` |
| `activity_gear` | activity-to-gear links | `PROCESSED` | 1 | 0 | `normalized/activity_gear.json` | activity_gear_link | `gear_key`, `activity_id` | normalized relationship source of truth | explicit activity and gear joins | `explicit` | `identifier-bearing-local` |
| `personal_records` | authoritative personal records | `PROCESSED` | 1 | 0 | `normalized/personal_records.json` | personal_record | `personal_record_id` | normalized source of truth | explicit nonzero activity joins; zero is independent | `explicit-or-independent` | `personal-local` |
| `fit_sessions` | bounded FIT session summaries | `PROCESSED` | 1 | 0 | `normalized/fit_sessions.json` | fit_session | `fit_session_key` | normalized source of truth | trusted-local session analysis after audit review | `explicit` | `personal-local` |
| `fit_laps` | bounded FIT lap summaries | `PROCESSED` | 2 | 0 | `normalized/fit_laps.json` | fit_session_lap | `fit_lap_key` | normalized source of truth | explicit child of FIT session | `explicit` | `personal-local` |
| `activity_fit_links` | evidence-qualified Activity/FIT session links | `PROCESSED` | 1 | 0 | `normalized/activity_fit_links.json` | activity_fit_session_link | `garmin_activity_key`, `fit_session_key` | normalized relationship source of truth | explicit one-to-one eligible-population joins | `explicit` | `identifier-bearing-local` |

## Interpretation Rules

- `SKIPPED_NOT_PRESENT` is an expected state for an absent optional family.
- `PROCESSED_EMPTY` is distinct from an absent family.
- Stable keys are local identifiers and are not permission to publish them.
- Record counts and paths are projections; provenance and integrity evidence
  remain in `run_manifest.json` and the normalized records.
- Cross-dataset joins are authorized only by the repository Dataset
  Relationship Catalog. Do not infer a relationship from similar fields or
  timestamp proximity.
- Required/optional input behavior remains available in `run_manifest.json`
  and `run_summary.json`; an absent optional family is not a claim of no data.
