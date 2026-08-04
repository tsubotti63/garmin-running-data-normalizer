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
| `hill_score_daily` | source-provided daily hill performance context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/hill_score_daily.json` | calendar_day | `calendar_date` | normalized source of truth | daily context with raw source codes; no label inference | `not_yet_defined` | `public-safe-metric-fields` |
| `endurance_score_daily` | source-provided daily endurance performance context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/endurance_score_daily.json` | calendar_day | `calendar_date` | normalized source of truth | daily context with raw source codes; no label inference | `not_yet_defined` | `public-safe-metric-fields` |
| `race_prediction_daily` | source-provided daily race predictions | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/race_prediction_daily.json` | calendar_day | `calendar_date` | normalized source of truth | daily condition context; not an Activity fact join | `not_yet_defined` | `public-safe-metric-fields` |
| `sleep_daily` | bounded daily sleep context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/sleep_daily.json` | sleep_day | `sleep_day` | normalized source of truth | daily condition context with explicit review states | `not_yet_defined` | `personal-local-metric-fields` |
| `uds_daily` | source-provided daily activity and stress context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/uds_daily.json` | calendar_day | `calendar_date` | normalized source of truth | generation-aware daily condition context | `not_yet_defined` | `personal-local-metric-fields` |
| `acute_training_load_daily` | source-provided acute training-load context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/acute_training_load_daily.json` | calendar_day | `calendar_date` | normalized source of truth | daily condition context without recomputation | `not_yet_defined` | `personal-local-metric-fields` |
| `training_readiness_daily` | source-provided training-readiness context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/training_readiness_daily.json` | calendar_day | `calendar_date` | normalized source of truth | daily condition context without component inference | `not_yet_defined` | `personal-local-metric-fields` |
| `vo2max_daily` | generation-aware daily VO2Max observations | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/vo2max_daily.json` | calendar_day | `calendar_date` | normalized source of truth | two source series retained without cross-series overwrite | `not_yet_defined` | `personal-local-metric-fields` |
| `hrv_daily` | bounded FIT-derived HRV reference | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/hrv_daily.json` | calendar_day | `calendar_date` | analysis reference only | reviewed trend context; not a daily source of truth | `not_yet_defined` | `personal-local-metric-fields` |
| `training_history_daily` | limited daily training status context | `SKIPPED_NOT_PRESENT` | 0 | 0 | `normalized/training_history_daily.json` | calendar_day | `calendar_date` | normalized source of truth | two-field public contract only | `not_yet_defined` | `personal-local-metric-fields` |

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
- Hill and Endurance are standalone daily observations. Their activity
  relationship is `not_yet_defined`; do not join them to activities by date.
- Lactate Threshold remains candidate/audit-only until Product approves a
  machine stable key and the remaining field authority gates.
