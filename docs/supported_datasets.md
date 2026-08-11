# Supported Datasets

This document defines the supported Garmin dataset and interface scope for the
stable `1.3.2` release. All processing is local-first. Public fixtures are
synthetic; real exports and generated personal output must remain local.

## Stable CLI and output scope

This section is the human-readable Dataset Catalog for the stable Run-All v1
families. The executable dataset definitions and versioned registry remain the
machine authorities.

| Dataset | Source / interface | Role and authority | Grain | Stable key | Required | Provenance | Analysis suitability |
|---|---|---|---|---|---:|---|---|
| `activities` | `summarizedActivities.json`; `normalize-activities`, Run-All | Authoritative normalized activity records | activity | `garmin_activity_key` | yes | `source_path`, `source_sha256`, confidence | Detailed local activity analysis; use the reduced CSV when its columns are sufficient |
| `gear` | `gear.json`; Run-All | Authoritative normalized gear records | gear | `gear_key` | no | `source_path`, `source_sha256` | Local gear attribute analysis; cross-dataset use requires the relationship catalog |
| `activity_gear` | `gear.json`; Run-All | Authoritative normalized link records, not an activity Source of Truth | activity-gear link | `gear_key`, `activity_id` | no | `source_path`, `source_sha256` | Explicit joins to Activities through `garmin_activity_key` and to Gear through `gear_key` |
| `personal_records` | `personalRecord.json`; Run-All | Authoritative normalized personal-record entries | personal record | `personal_record_id` | no | `source_path`, `source_sha256`, confidence | Nonzero activity IDs resolve explicitly; `activity_id = 0` remains independent |
| `fit_sessions` | CRC-valid bounded Activity `.fit`; Run-All | Authoritative bounded FIT session summaries | FIT session | `fit_session_key` | no | `source_path`, `source_sha256`; compatible `fit_file_id` retained | Local bounded session analysis after audit review |
| `fit_laps` | CRC-valid bounded Activity `.fit`; Run-All | Authoritative bounded FIT lap summaries | FIT session lap | `fit_lap_key` | no | `source_path`, `source_sha256`; compatible `fit_file_id`, `lap_index` retained | Explicit child of a FIT session through `fit_session_key` |
| `activity_fit_links` | Activities and CRC-valid FIT Sessions; Run-All | Auditable evidence-qualified relationship records | Activity/FIT session link | `garmin_activity_key`, `fit_session_key` | no | both Activity and FIT provenance | Explicit one-to-one join within the evidence-qualified eligible population |
| `hill_score_daily` | exact-suffix `HillScore*.json`; Run-All | Authoritative public-safe daily Hill Score state | calendar day | `calendar_date` | no | aggregate source-lineage audit; private source fields are not emitted | Standalone daily performance context; no Activity relationship is defined |
| `endurance_score_daily` | exact-suffix `EnduranceScore*.json`; Run-All | Authoritative public-safe daily Endurance Score state | calendar day | `calendar_date` | no | aggregate source-lineage audit; private source fields are not emitted | Standalone daily performance context; no Activity relationship is defined |
| `race_prediction_daily` | `RunRacePredictions*.json`; Run-All | Garmin source-provided race predictions | source observation | `calendar_date`, `observation_timestamp` | no | aggregate source-lineage audit | Standalone prediction context; not a measured race result |
| `sleep_daily` | `*sleepData.json`; Run-All | Bounded normalized sleep state and explicit review rows | sleep day | `sleep_day` | no | aggregate source-lineage audit | Standalone condition context; missing values are not inferred |
| `uds_daily` | `UDSFile*.json`; Run-All | Selected source-provided activity, heart-rate, Body Battery, and stress context | calendar day | `calendar_date` | no | aggregate source-lineage audit | Generation-aware condition context with explicit source-presence flags |
| `acute_training_load_daily` | `MetricsAcuteTrainingLoad*.json`; Run-All | Source-provided acute/chronic load observations | source observation | `calendar_date`, `observation_timestamp` | no | aggregate source-lineage audit | No ratio or status recomputation; no daily row selection |
| `training_readiness_daily` | `TrainingReadinessDTO*.json`; Run-All | Source-provided readiness and component observations | source observation | `calendar_date`, `observation_timestamp` | no | aggregate source-lineage audit | HRV-labelled components remain source-provided readiness fields |
| `vo2max_daily` | `ActivityVo2Max*.json`, `MetricsMaxMetData*.json`; Run-All | Unified observation schema retaining two source series | source observation | `calendar_date`, `vo2max_source_series`, `sport`, `observation_timestamp` | no | aggregate source-lineage audit; supplemental source Activity ID | Source-series boundary is explicit; no cross-series overwrite or Activity join |
| `hrv_daily` | non-running FIT message 370 field 1; Run-All | Bounded FIT-derived analysis reference | calendar day | `calendar_date` | no | aggregate FIT audit | `analysis_reference_only`; conflicting same-day values remain unresolved |
| `training_history_daily` | `TrainingHistory*.json`; Run-All | Limited training-status observations | source observation | `calendar_date`, `observation_timestamp` | no | aggregate source-lineage audit | Status plus optional sport context; no promotion of other sparse fields |

Run-All requires Activities. Gear, Personal Records, and FIT are optional and
produce explicit `SKIPPED_NOT_PRESENT` evidence when absent. The documented CLI,
exit-code behavior, fixed output paths, run completion marker, provenance, and
versioned Run-All manifest fields form the stable `1.x` interface.

All v1.3 daily families are optional. Their absence is an expected
source condition and does not add a warning. Exact duplicates are deduplicated.
Snapshot-based Endurance and UDS values that differ for one stable key are
preserved in their audit evidence while canonicalization remains unresolved;
same-export malformed/divergent values fail closed. The HRV reference preserves
an explicit unresolved review row. Missing from a later Snapshot never means
delete. The shared generation/source boundary and exact field contracts are
defined in [Wellness and Daily Metrics](wellness_metrics.md).

The deterministic `analysis/activities.csv` is a reduced one-row-per-activity
projection of `normalized/activities.json`. It is the existing analysis handoff
entry point, but it is not a separate Source of Truth. QA, audit, manifest, and
summary files are evidence or navigation artifacts rather than normalized
datasets. Run-All also emits `START_HERE.md`, `DATASET_INVENTORY.md`,
`ANALYSIS_HANDOFF.md`, `ANALYSIS_CONTEXT.json`, `SCHEMA_CATALOG.json`, and
`artifact_inventory.json`. The optional `--external-safe-pack` flag adds a
deterministic reviewable ZIP without automatically uploading it.

Cross-dataset joins are governed by the [Dataset Relationship
Catalog](dataset_relationships.md). Stable keys establish identity within their
declared grain; they do not independently authorize a cross-dataset join.

## v1.3 relationship and projection guidance

The normalized JSON for every listed v1.3 dataset is canonical at its declared
grain. A CSV or QA day-level view is a non-canonical projection and never
selects a preferred observation. Direct Activity relationships remain
`not_yet_defined`; `context_only` permits a separately labelled same-day
comparison, not an Activity fact-table merge.

| Dataset | Semantic role | Activity guidance | Cardinality | Projection |
|---|---|---|---|---|
| `hill_score_daily`, `endurance_score_daily` | daily performance context | date is a candidate context field; direct link `not_yet_defined` | one context row to many Activities | `analysis/performance_metrics_daily.csv`, derived and non-canonical |
| `race_prediction_daily` | daily performance prediction | direct link `not_yet_defined` | many observations to many Activities | QA daily summary, `selection_rule: null` |
| `sleep_daily`, `uds_daily`, `hrv_daily` | condition context | same-day `context_only`; direct link `not_yet_defined` | one context row to many Activities | no canonical replacement; HRV stays `analysis_reference_only` |
| `acute_training_load_daily`, `training_readiness_daily`, `vo2max_daily`, `training_history_daily` | performance context | same-day `context_only`; direct link `not_yet_defined` | many observations to many Activities | QA daily summary, `selection_rule: null` |
| Lactate Threshold candidate families | performance threshold observation | no join; direct link `not_yet_defined` | many candidates across source families | audit-only, no canonical daily projection |

See the relationship catalog for join fields, allowed and forbidden use,
multiple-observation behavior, generation limits, and bounded analysis examples.

## Snapshot accumulation policy (compatible v1.3.0)

| Dataset | Snapshot merge mode | Absence behavior | Materialization |
|---|---|---|---|
| Activities | entity upsert by `garmin_activity_key` | retain previous | source-shaped JSON |
| Gear | entity upsert by `gear_key` | retain previous | source-shaped JSON |
| Activity/Gear | event union by `gear_key`, `activity_id` | retain previous | source-shaped JSON |
| Personal Records | entity upsert by `personal_record_id` | retain previous | source-shaped JSON |
| FIT blobs | immutable content union | retain old-only content | one file per unique content |
| FIT Sessions/Laps | regenerate | derived from cumulative FIT union | current parser and stable keys |
| Activity/FIT links | regenerate | unresolved remains unresolved | current evidence-qualified policy |
| Hill Score Daily | daily state upsert by `calendar_date` | retain previous | public-safe daily JSON |
| Endurance Score Daily | daily state upsert by `calendar_date` | retain previous | public-safe daily JSON |
| Race Prediction observations | immutable observation union by date and source timestamp | retain previous | normalized observation JSON |
| Sleep Daily | daily state upsert by `sleep_day` | retain previous | normalized daily JSON |
| UDS Daily | daily state upsert by `calendar_date` | retain previous | normalized daily JSON |
| Acute Training Load observations | immutable observation union by date and source timestamp | retain previous | normalized observation JSON |
| Training Readiness observations | immutable observation union by date and source timestamp | retain previous | normalized observation JSON |
| VO2Max observations | immutable observation union by date, source series, sport, and source timestamp | retain previous | two-series normalized observation JSON |
| HRV Daily | regenerate from cumulative FIT blob union | derived from retained FIT evidence | analysis-reference JSON |
| Training History observations | immutable observation union by date and source timestamp | retain previous | limited normalized observation JSON |
| Lactate Threshold candidates | immutable candidate observation union | retain all source families | audit-only; no stable dataset promotion |
| Unknown/unsupported | preserve only | never discard automatically | raw private evidence only |

The machine-readable policy authority is
`config/garmin_snapshot_dataset_merge_policies_v1.json`. Health Status remains
the only deferred future-ready policy entry in this tranche.

## Library-level scope

| Dataset or output | Implemented behavior | Stable CLI/Run-All status |
|---|---|---|
| Health Status | Complete long metrics and fixed daily schema | Library only |
| Analysis Pack | Deterministic allowlist-only ZIP builder | Library only |

Library-level support means the implementation and synthetic tests are present,
but the dataset is not a promised Run-All output. These interfaces may evolve
compatibly as their normative contracts mature.

## Lactate Threshold candidate boundary

P13-M3 discovers Lactate Threshold observations from history,
latest-snapshot, profile-state, and derived-evidence source families. The
records remain in `audit/lactate_threshold_candidates.json`; they are not
promoted to a stable normalized dataset. Units and timezone are explicitly
`UNCONFIRMED`, sequence is ordering evidence only, and no latest-wins,
cross-source collapse, value conversion, or relationship inference is
performed. A machine stable key remains a Product decision gate.

## Registry lifecycle

The example registry is version `1.3.0` with status `stable_release_ready`. It
declares 17 reviewed stable datasets, keeps Lactate Threshold in the separate
candidate registry section, and defers Health Status. This status describes the
reviewed source; it does not itself create a tag, Release, or PyPI publication.

See [Known Limitations](known_limitations.md), the
[Product Quick Start](product_quick_start.md), and the
[dataset registry](../config/dataset_registry.example.json). The consolidated
[Run-All Output Contract](output_contract.md) defines authority, completion,
status, compatibility, and privacy behavior.
