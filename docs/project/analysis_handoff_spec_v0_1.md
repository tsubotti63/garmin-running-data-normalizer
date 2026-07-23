# Analysis Handoff Specification v0.1

## Status and purpose

- Status: M4 handoff contract
- Applies to: `garmin-running-data-normalizer-run-all-v1`
- Boundary: local Run-All output produced from a user-controlled Garmin Account Export

This specification defines how deterministic Run-All output may be handed to a
human analyst, a local analysis tool, or an AI assistant without confusing
normalization facts with later interpretation. It does not add an analysis
feature to Run-All and does not change the Run-All public contract.

## Intended users

- People reviewing their own local running data.
- Analysts producing descriptive aggregates from an authorized dataset.
- AI assistants operating in an environment approved by the data owner.
- Maintainers validating output completeness, provenance, and reproducibility.

This handoff is not designed for medical, coaching, or diagnostic decisions.

## Input and completion gate

The input is one complete Run-All output directory. Before analysis:

1. Require `run_summary.json`.
2. Accept only `PASS`, `PASS_WITH_WARNINGS`, or deliberately reviewed
   `PARTIAL_SUCCESS` output.
3. Read the warning and error counts before interpreting any dataset.
4. Confirm that every file used by the analysis is listed by the completion
   summary or manifest.
5. Do not analyze a failed run. Exit code `2` does not publish a valid handoff.

## Handoff files

### Required minimum

| File | Responsibility |
|---|---|
| `analysis/activities.csv` | Stable, reduced activity-level table for descriptive analysis |
| `run_summary.json` | Completion state, family status, warnings, errors, and generated paths |
| `run_manifest.json` | Reproducibility, dataset grain, stable keys, source counts, and output hashes |

The manifest contains source-relative provenance and hashes. It is required for
local verification but should not be uploaded to an external service without a
separate privacy review.

### Optional, question-specific files

| File | Use |
|---|---|
| `normalized/activities.json` | Detailed activity records and local provenance |
| `normalized/gear.json` | Gear attributes and lifecycle fields |
| `normalized/activity_gear.json` | Activity-to-gear links |
| `normalized/personal_records.json` | Personal-record entries and states |
| `normalized/fit_sessions.json` | Bounded FIT session summaries |
| `normalized/fit_laps.json` | Bounded FIT lap summaries |
| `audit/fit_audit.json` | Per-FIT parse status and completeness evidence |
| `qa/dataset_summary.json` | Stable-key, duplicate, serialization, and deterministic-digest QA |

Optional files remain personal local output. Use only the smallest set needed
for the stated question.

## Handoff output

The consumer produces a separate analysis artifact; it never edits the Run-All
directory. At minimum, that artifact records:

- files and completion status reviewed;
- filters, grouping rules, formulas, denominators, and missing-value counts;
- factual aggregates;
- descriptive trends;
- anomaly candidates requiring human review;
- interpretations clearly separated from facts;
- limitations, unknowns, and any additional confirmation needed.

The fixed response structure in the prompt template is the default human- and
AI-readable output. M4 does not define a new machine-readable analysis schema.

## Activities CSV contract

The grain is one normalized activity per row. Blank cells mean unavailable or
not represented by the source record; they never mean zero.

| Column | Meaning | Unit or domain |
|---|---|---|
| `garmin_activity_key` | Deterministic local activity key | May contain the source activity identifier; private |
| `activity_date_local` | Local calendar date | ISO date when available |
| `activity_datetime_local` | Local activity date-time | ISO date-time when available |
| `activity_type` | Garmin activity classification | Source-controlled label |
| `sport_type` | Garmin sport classification | Source-controlled label |
| `distance_m` | Activity distance | Metres |
| `duration_sec` | Activity duration | Seconds |
| `avg_hr` | Average heart rate | Beats per minute when available |
| `max_hr` | Maximum heart rate | Beats per minute when available |
| `avg_power` | Average power | Source value, normally watts |
| `max_power` | Maximum power | Source value, normally watts |
| `avg_run_cadence` | Average running cadence | Source value; do not reinterpret its basis |
| `training_effect_label` | Source training-effect label | String or blank |
| `activity_training_load` | Source training-load value | Source-defined numeric value |
| `lap_count` | Recorded lap count | Count |

The CSV has no separate raw `activity_id` column and excludes memo text, source
paths, hashes, and coordinates. However, the current
`garmin_activity_key` contract prefers a `garmin_activity:<activity_id>` value
when the source identifier exists. Treat that column as raw-identifier-bearing
data: never disclose it, and remove it from any reviewed derivative intended
for an external service.

## Other dataset grains and keys

| Dataset | Grain | Stable key |
|---|---|---|
| `activities` | Activity | `garmin_activity_key` |
| `gear` | Gear item | `gear_key` |
| `activity_gear` | Activity-gear link | `gear_key`, `activity_id` |
| `personal_records` | Personal record | `personal_record_id` |
| `fit_sessions` | FIT file session | `fit_file_id` |
| `fit_laps` | FIT file lap | `fit_file_id`, `lap_index` |

Stable keys support identity and reproducibility within their declared grain.
Only the [Dataset Relationship Catalog](../dataset_relationships.md) authorizes
cross-dataset joins. Some keys may incorporate source IDs; none are permission
to publish or identify a person.

## Missing values and aggregation

- Preserve missing values as missing; do not fill with zero, a population
  average, or a value from another activity.
- Report the denominator and missing-value count for every metric aggregate.
- Exclude missing numeric values only when the exclusion rule is stated.
- Do not combine fields with uncertain units or semantics.
- Do not treat a missing optional family as evidence that the user has no such
  data. It means only that Run-All did not detect that family in this export.
- Avoid causal claims from descriptive time series.

## Warnings and partial success

- `PASS`: all detected families completed without warnings.
- `PASS_WITH_WARNINGS`: valid output exists, but one or more non-fatal warnings
  require disclosure in the analysis.
- `PARTIAL_SUCCESS`: required Activities output is valid, while detected FIT
  input is auditably incomplete. FIT-derived conclusions must be limited to the
  successfully parsed subset and labeled partial.
- `SKIPPED_NOT_PRESENT` and `PROCESSED_EMPTY` are different states and must not
  be collapsed into the same interpretation.

Every analysis must repeat relevant warning codes and identify affected
families. Do not silently drop incomplete FIT files.

## Privacy boundary

- Keep real exports and detailed Run-All output local and uncommitted.
- Do not disclose raw IDs, stable keys, source-relative paths,
  filenames, hashes, memo text, coordinates, or record-level health data.
- Do not upload `run_manifest.json`, normalized JSON, or FIT audit data to an
  external AI service without data-owner approval and a provider-specific
  privacy review.
- Prefer a reviewed derivative containing only the required columns and
  aggregation level. For external analysis, remove `garmin_activity_key` and
  review date/time granularity before transfer. Synthetic examples are the
  default for public material.
- Never combine the handoff with unrelated personal datasets to re-identify a
  person.

## Rules for an analysis AI

The request supplied to an AI must define the authorized files, question,
aggregation level, and allowed outputs. The AI must:

1. Separate observed facts, calculations, interpretations, and unknowns.
2. Never infer a missing value, unit, identity, location, diagnosis, training
   intent, or causal explanation.
3. Return bounded aggregates and trends before any interpretation.
4. Describe anomaly candidates as review prompts, not conclusions.
5. Suppress identifiers and paths in both prose and examples.
6. State when the available files cannot answer the question.
7. Ask for an additional approved file rather than inventing context.

The reusable request format is defined in
[`analysis_prompt_template_v0_1.md`](analysis_prompt_template_v0_1.md).

## Responsibility separation

Run-All owns discovery, safe normalization, provenance, deterministic QA,
serialization, and the completion state. An analysis consumer owns filtering,
aggregation, interpretation, presentation, and any domain assumptions. An
analysis must not rewrite normalized files or present derived observations as
fields emitted by Run-All.

## Reproducibility

- Preserve the original Run-All output as read-only local evidence.
- Record the Run-All version and completion status used by the analysis.
- Record analysis filters, grouping rules, missing-value policy, and formulas.
- Use a new analysis destination for reruns.
- Byte-identical Run-All output supports reproducible input to analysis; it
  does not guarantee identical prose from a generative model.
- A published case study should include synthetic input and deterministic
  calculation steps whenever possible.

## Future extension boundary

Weather, Sleep, HRV, Parquet, notebooks, dashboards, coaching interpretation,
and new dataset families are outside v0.1. Adding them requires separate
contracts for schema, units, privacy, provenance, QA, and lifecycle behavior.
This handoff may later gain a machine-readable profile, but M4 does not add one.

No code or CLI change is required to use this local handoff. A future feature
that directly creates an external-sharing-safe file would require a separate
implementation task because the current Activities CSV retains a local stable
key and exact local date/time fields.
