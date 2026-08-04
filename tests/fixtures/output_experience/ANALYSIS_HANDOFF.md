# Analysis Handoff

This file is the deterministic receiving contract for this completed Run-All
output. It is sufficient to begin bounded analysis without repository or
Internet access. The normalized data and machine artifacts remain authoritative.

## Authorized Default Files

- `START_HERE.md`
- `DATASET_INVENTORY.md`
- `ANALYSIS_CONTEXT.json`
- `SCHEMA_CATALOG.json`
- `analysis/activities.csv`
- `analysis/performance_metrics_daily.csv`
- `run_summary.json`

Use normalized JSON, relationship links, QA, or audit files only when the
question requires them and the local/trusted environment is authorized.

## Receiving Rules

1. Separate observed facts, calculations, interpretations, and unknowns.
2. Preserve null and missing values; never convert them to zero.
3. State filters, formulas, denominators, and missing-value counts.
4. Use only `explicit` relationships for direct joins. A documented
   `context_only` alignment permits comparison, never a fact-table merge.
5. Use `activity_fit_links` for Activity/FIT joins; timestamp-only joins are prohibited.
6. Treat Personal Records with `activity_relationship_status=independent`
   as non-activity records and do not force an activity identity.
7. Preserve and disclose warnings or partial FIT status.
8. Ask for an additional approved file when the supplied artifacts cannot
   answer the question; do not invent source fields or context.
9. Treat Hill and Endurance as canonical daily performance context. Their
   CSV is a derived projection; their Activity relationship remains undefined.
10. Lactate Threshold is candidate/audit-only. Do not treat candidates as a
    stable dataset, convert unconfirmed units, or apply latest-wins.
11. Sleep, UDS, and HRV may be compared as same-day condition context, but
    they remain separate datasets and must not become Activity fact fields.
12. Race Prediction, Acute Training Load, Training Readiness, VO2Max, and
    Training History retain every canonical source observation. Their daily
    summaries are derived projections with no selected row.
13. VO2Max source series are retained explicitly. Do not overwrite one series
    with another or infer equivalence across device generations.
14. HRV is `analysis_reference_only`, not a daily source of truth. A null HRV
    value with a review status must remain unresolved.
15. Approximate generation ranges (2015-2021 and 2022+) are descriptive
    source context only; they do not authorize automatic field equivalence.

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

## Multi-Session FIT Completeness

- CRC-valid multi-session FIT files are normalized when every lap can be
  assigned to exactly one declared session without inference.
- If declared session/lap counts cannot allocate every lap exactly once, the
  whole FIT file is excluded from normalized sessions and laps with
  `session_lap_allocation_conflict` in `audit/fit_audit.json`.
- Sessions excluded at this parse boundary do not enter the eligible
  Activity/FIT Relationship Coverage population. Coverage therefore describes
  only emitted, independently eligible sessions and does not claim that an
  allocation-conflict file was normalized.

## Current Warnings

- None

## Privacy Modes

- `local_trusted_full`: full Run-All output, provenance, stable keys, QA,
  audit evidence, memo text, and source-relative filenames remain in a
  user-controlled trusted environment. Source filenames can contain
  email-shaped personal identifiers.
- `external_safe`: only the explicit safe-pack allowlist may leave that
  environment after review. The pack excludes paths, hashes, raw IDs, stable
  keys, memo text, coordinates, exact timestamps, and unlisted files.
- Run-All never uploads output automatically.

## Reproducibility

Record the product version, run status, files used, filters, formulas, and
missing-value policy. Identical normalized input can reproduce deterministic
machine artifacts and guidance; generative prose is not claimed byte-identical.

## Prompt Preamble

> Use only the supplied files. Preserve missing values. Honor each dataset
> grain and stable key. Use only explicit relationships. Do not infer identity,
> location, intent, diagnosis, or causal explanation. Cite the dataset and
> fields supporting each factual statement, separate calculations from
> interpretation, and state what remains unknown.
