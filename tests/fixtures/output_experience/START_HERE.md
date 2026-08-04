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
| `hill_score` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `endurance_score` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `race_prediction` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `sleep` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `uds` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `acute_training_load` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `training_readiness` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `vo2max` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `hrv` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |
| `training_history` | `SKIPPED_NOT_PRESENT` | 0 | 0 | 0 |

## Recommended Reading Order

1. Confirm this run status and any warnings below.
2. Review `DATASET_INVENTORY.md` for dataset grain, keys, and availability.
3. Read `ANALYSIS_HANDOFF.md` before supplying files to an analyst or AI.
4. Use `ANALYSIS_CONTEXT.json` and `SCHEMA_CATALOG.json` for machine context.
5. Use only relationships marked explicit in the handoff/context.
6. Use QA or audit evidence when a warning, partial result, or validation
   question affects the analysis.

Recommended trusted-local activity entry point: `analysis/activities.csv`.
Daily Hill/Endurance context: `analysis/performance_metrics_daily.csv`.
Other daily condition datasets are separate normalized JSON files listed
in `DATASET_INVENTORY.md`; they are not Activity fact-table joins.

### Available Analysis Files

- `analysis/activities.csv`
- `analysis/performance_metrics_daily.csv`

### QA Evidence

- `qa/daily_metrics_summary.json`
- `qa/dataset_summary.json`
- `qa/performance_metrics_summary.json`
- `qa/relationship_summary.json`

### Audit Evidence

- `audit/activity_fit_linkage.json`
- `audit/acute_training_load_daily.json`
- `audit/endurance_score_daily.json`
- `audit/fit_audit.json`
- `audit/hill_score_daily.json`
- `audit/hrv_daily.json`
- `audit/lactate_threshold_candidates.json`
- `audit/race_prediction_daily.json`
- `audit/sleep_daily.json`
- `audit/training_history_daily.json`
- `audit/training_readiness_daily.json`
- `audit/uds_daily.json`
- `audit/vo2max_daily.json`

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

## Lactate Threshold Candidate Boundary

- Status: `REVIEW_REQUIRED_STABLE_PROMOTION_BLOCKED`
- Candidate observations: 0
- Stable public promotion: No
- Machine stable key: `PRODUCT_DECISION_REQUIRED`
- Audit: `audit/lactate_threshold_candidates.json`
- Units and source timezone remain unconfirmed; do not convert or infer them.

## Relationship Safety

The generated relationship contract declares only reviewed v1.1 joins.
`activity_fit_links` is the sole Activity/FIT join authority. Do not create
a timestamp-only join or infer a relationship from similar fields.

## v1.3 Context and Observation Relationships

These entries are analysis guidance, not newly declared direct links.
A `context_only` entry permits same-day comparison while datasets remain
separate; it never authorizes an Activity fact-table merge.

| Dataset | Relationship role | Grain | Stable key | Activity guidance | Join fields | Cardinality | Canonical/projection |
|---|---|---|---|---|---|---|---|
| `hill_score_daily` | `daily_performance_context` | `calendar_day` | `calendar_date` | `not_yet_defined` | `calendar_date` → `activity_date_local` | `one_to_many_context_candidate` | canonical source + derived non-canonical projection |
| `endurance_score_daily` | `daily_performance_context` | `calendar_day` | `calendar_date` | `not_yet_defined` | `calendar_date` → `activity_date_local` | `one_to_many_context_candidate` | canonical source + derived non-canonical projection |
| `race_prediction_daily` | `daily_performance_prediction` | `source_observation` | `calendar_date`, `observation_timestamp` | `not_yet_defined` | `calendar_date` → `activity_date_local` | `many_to_many_context_only` | canonical source + derived non-canonical projection |
| `sleep_daily` | `condition_context` | `sleep_day` | `sleep_day` | `context_only` | `sleep_day` → `activity_date_local` | `one_to_many_context_only` | canonical source |
| `uds_daily` | `condition_context` | `calendar_day` | `calendar_date` | `context_only` | `calendar_date` → `activity_date_local` | `one_to_many_context_only` | canonical source |
| `acute_training_load_daily` | `performance_context` | `source_observation` | `calendar_date`, `observation_timestamp` | `context_only` | `calendar_date` → `activity_date_local` | `many_to_many_context_only` | canonical source + derived non-canonical projection |
| `training_readiness_daily` | `performance_context` | `source_observation` | `calendar_date`, `observation_timestamp` | `context_only` | `calendar_date` → `activity_date_local` | `many_to_many_context_only` | canonical source + derived non-canonical projection |
| `vo2max_daily` | `performance_context` | `source_observation` | `calendar_date`, `vo2max_source_series`, `sport`, `observation_timestamp` | `context_only` | `calendar_date` → `activity_date_local` | `many_to_many_context_only` | canonical source + derived non-canonical projection |
| `hrv_daily` | `condition_context` | `calendar_day` | `calendar_date` | `context_only` | `calendar_date` → `activity_date_local` | `one_to_many_context_only` | canonical source |
| `training_history_daily` | `performance_context` | `source_observation` | `calendar_date`, `observation_timestamp` | `context_only` | `calendar_date` → `activity_date_local` | `many_to_many_context_only` | canonical source + derived non-canonical projection |
| `lactate_threshold_candidates` | `observation_family` | `source-backed threshold observation` | `PRODUCT_DECISION_REQUIRED` | `not_yet_defined` | none | `many_candidate_observations_across_source_families` | candidate/audit only; no canonical daily projection |

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
