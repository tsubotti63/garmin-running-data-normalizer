# Dataset Relationship Catalog

## Purpose

This catalog defines every cross-dataset relationship supported by the public
Run-All contract and the bounded contextual guidance under review for v1.3.
Similar fields, filenames, dates, or timestamps never authorize a direct join
by themselves.

Relationship status uses `explicit`, `indirect`, `independent`,
`not_yet_defined`, or `unsupported`. The stable Run-All datasets use
only reviewed `explicit` relationships plus the documented independent
Personal Record exception. The v1.3 entries add contextual
comparison guidance; they do not add a direct Activity relationship.

`analysis/activities.csv` is a reduced deterministic projection of
`normalized/activities.json`, not an additional cross-dataset relationship.
Its presence does not authorize a join beyond the explicit contracts below.

## Relationship map

```text
Activities
  ├─ Activity/Gear Links ─ Gear
  ├─ Personal Records (nonzero source activity identity)
  └─ Activity/FIT Links ─ FIT Sessions ─ FIT Laps

Personal Records (activity_id = 0)
  └─ independent non-activity record

Hill Score Daily                Endurance Score Daily
  └─ not_yet_defined       └─ not_yet_defined
     (standalone daily context; no Activity date join)

Sleep / UDS / HRV
  └─ context_only by local calendar day (separate facts; no Activity merge)

Race Prediction / Acute Load / Readiness / VO2Max / Training History
  └─ source observations; derived daily view has no selected row

Lactate Threshold
  └─ candidate/audit observation families; no stable promotion or join
```

## Stable direct relationship catalog

| Left artifact | Right artifact | Status | Fields | Cardinality | Validation |
|---|---|---|---|---|---|
| `normalized/activity_gear.json` | `normalized/gear.json` | `explicit` | `gear_key` | many-to-one | null, type mismatch, duplicate link, and orphan gear fail closed |
| `normalized/activity_gear.json` | `normalized/activities.json` | `explicit` | `garmin_activity_key` | many-to-one | source `activity_id` must resolve to exactly one normalized Activity |
| `normalized/personal_records.json` | `normalized/activities.json` | `explicit` or `independent` | `garmin_activity_key` | many-to-zero-or-one | nonzero source activity identity must resolve; `activity_id = 0` remains independent |
| `normalized/fit_laps.json` | `normalized/fit_sessions.json` | `explicit` | `fit_session_key` | many-to-one | every lap has one existing parent session |
| `normalized/activity_fit_links.json` | `normalized/activities.json` | `explicit` | `garmin_activity_key` | one-to-one within eligible population | link rows are mutual unique evidence-qualified matches |
| `normalized/activity_fit_links.json` | `normalized/fit_sessions.json` | `explicit` | `fit_session_key` | one-to-one within eligible population | link rows are mutual unique evidence-qualified matches |

## Unreleased v1.3 context and observation catalog

`context_only` means that an analysis may compare separately aggregated facts
for a declared local calendar day. It does not create row identity, authorize a
fact-table merge, or establish causality. `not_yet_defined` means that even
contextual alignment is not a direct relationship contract.

| Dataset | Role | Canonical grain and stable key | Activity guidance | Fields | Cardinality | Canonical / projection | Allowed use | Forbidden use |
|---|---|---|---|---|---|---|---|---|
| `normalized/hill_score_daily.json` | daily performance context | one calendar day; `calendar_date` | direct relationship `not_yet_defined` | candidate `calendar_date` to `activity_date_local` | one context row to many Activities | normalized JSON canonical; namespaced CSV derived | standalone trends and separately labelled daily comparison | no Activity merge, causal claim, or date-derived identity |
| `normalized/endurance_score_daily.json` | daily performance context | one calendar day; `calendar_date` | direct relationship `not_yet_defined` | candidate `calendar_date` to `activity_date_local` | one context row to many Activities | normalized JSON canonical; namespaced CSV derived | standalone trends and separately labelled daily comparison | no Activity merge, causal claim, or date-derived identity |
| `normalized/race_prediction_daily.json` | daily performance prediction | one source observation; `calendar_date`, `observation_timestamp` | direct relationship `not_yet_defined` | candidate `calendar_date` to `activity_date_local` | many observations to many Activities | observations canonical; daily summary derived with `selection_rule: null` | compare Garmin predictions over time | no measured-result claim, latest-wins, or Activity join |
| `normalized/sleep_daily.json` | condition context | one reviewed sleep state; `sleep_day` | same-day `context_only`; direct relationship `not_yet_defined` | `sleep_day` to `activity_date_local` | one context row to many Activities | normalized JSON canonical | compare separately aggregated same-day sleep and Activity measures | never copy Sleep fields into Activity facts or infer causality |
| `normalized/uds_daily.json` | condition context | one source state; `calendar_date` | same-day `context_only`; direct relationship `not_yet_defined` | `calendar_date` to `activity_date_local` | one context row to many Activities | normalized JSON canonical | generation-aware same-day condition comparison | no Activity fact merge or missing-value reconstruction |
| `normalized/acute_training_load_daily.json` | performance context | one source observation; `calendar_date`, `observation_timestamp` | same-day `context_only`; direct relationship `not_yet_defined` | `calendar_date` to `activity_date_local` | many observations to many Activities | observations canonical; daily summary derived with `selection_rule: null` | compare preserved load observations by day | no latest-wins, direct Activity link, or ratio recomputation |
| `normalized/training_readiness_daily.json` | performance context | one source observation; `calendar_date`, `observation_timestamp` | same-day `context_only`; direct relationship `not_yet_defined` | `calendar_date` to `activity_date_local` | many observations to many Activities | observations canonical; daily summary derived with `selection_rule: null` | compare preserved readiness context by day | no direct Activity link or component-cause inference |
| `normalized/vo2max_daily.json` | performance context | one source observation; date, source series, sport, timestamp | same-day `context_only`; direct relationship `not_yet_defined` | `calendar_date` to `activity_date_local` | many observations to many Activities | observations canonical; daily summary derived with `selection_rule: null` | compare each retained source series separately | no join through supplemental `source_activity_id`, cross-series overwrite, or latest-wins |
| `normalized/hrv_daily.json` | condition context | one resolved or review row; `calendar_date` | same-day `context_only`; direct relationship `not_yet_defined` | `calendar_date` to `activity_date_local` | one context row to many Activities | normalized JSON canonical; `analysis_reference_only` | reviewed trend comparison with unresolved rows preserved | no Activity fact merge, conflicting-value selection, or daily Source-of-Truth claim |
| `normalized/training_history_daily.json` | performance context | one source observation; `calendar_date`, `observation_timestamp` | same-day `context_only`; direct relationship `not_yet_defined` | `calendar_date` to `activity_date_local` | many observations to many Activities | observations canonical; daily summary derived with `selection_rule: null` | compare limited status context by day | no direct Activity link or latest-wins |
| `audit/lactate_threshold_candidates.json` | performance threshold observation family | one source-backed observation; stable key pending Product decision | direct relationship `not_yet_defined` | none | many observations across history, latest snapshot, profile state, and derived evidence | candidate/audit only; no canonical daily projection | source-family audit and Product review | no Activity join, unit conversion, cross-family collapse, or latest-wins |

When multiple source observations share a day, analysis must keep the
observations distinct. `qa/daily_metrics_summary.json` may summarize their
presence and counts, but it never chooses a canonical daily row.

## Machine-readable authority

`ANALYSIS_CONTEXT.json` and `SCHEMA_CATALOG.json` carry the same grain, stable
key, semantic role, canonical status, Activity relationship status, join
guidance, cardinality, allowed use, forbidden guidance, limitations, and
derived-projection metadata. `DATASET_INVENTORY.md`, `START_HERE.md`, and
`ANALYSIS_HANDOFF.md` are deterministic human-readable projections of that
generator-owned contract. `qa/relationship_summary.json` remains evidence for
the stable explicit links; contextual guidance is not counted as an explicit
link or coverage score.

## Activity/FIT eligibility contract

The physical FIT identity (`fit_file_id`, `fit_session_key`, `fit_lap_key`) is
separate from the Activity/FIT business relationship. A link is emitted only
when one candidate is the unique best candidate in both directions and meets
one of these evidence rules:

1. exact local start time plus at least one corroborating compatible sport,
   distance within 200 metres, or duration within 5 seconds; or
2. start time within 60 seconds plus compatible sport, distance within
   1 metre, and duration within 1 second.

Timestamp-only candidates are rejected. A record becomes eligible when it has
valid timezone-aware local start time and positive distance or duration. Sport
compatibility remains candidate evidence rather than an eligibility
prerequisite. This source-scope definition is evaluated before candidate
search and does not depend on finding a match. Ties,
one-to-one conflicts, and eligible records with no evidence-qualified
candidate are withheld as `eligible_unresolved` rather than guessed, so they
reduce eligible coverage. Structurally ineligible records are excluded with a
specific reason. Candidate-promotion coverage is reported separately and must
not be presented as source-scope coverage. The
`audit/activity_fit_linkage.json` file records the eligibility contract,
exclusions, match coverage, ambiguity, duplicate, and unresolved metrics.
`qa/relationship_summary.json` is the machine-readable relationship gate.

## Compatibility and identity

- `fit_file_id` remains a compatible content-derived file identity.
- `fit_session_key` is the stable FIT session identity and includes the
  content identity plus `session_ordinal`.
- `fit_lap_key` is the stable lap identity; `fit_session_key` is its parent key.
- `lap_index` remains as a compatible within-session ordinal, but it is not the
  v1.1 lap stable key.
- Cross-dataset identity never replaces source-relative provenance.

## Evidence relationships

`qa/dataset_summary.json`, `qa/relationship_summary.json`,
`audit/fit_audit.json`, `audit/activity_fit_linkage.json`,
`run_manifest.json`, and `run_summary.json` qualify a run but do not introduce
analytical facts.

For Snapshot Run-All, FIT Sessions/Laps and Activity/FIT links are regenerated
from the cumulative unique FIT blob set and canonical Activities using these
same contracts. Snapshot order, filename similarity, or timestamp proximity
does not create an additional relationship. Lifecycle lineage and coverage
qualify the cumulative input but do not authorize a new analytical join.

v1.3 also emits `analysis/performance_metrics_daily.csv` as a
convenience projection of the two daily datasets. Columns are namespaced with
`hill_` and `endurance_`; co-presence on a calendar day is presentation
context, not an inferred causal or Activity relationship. Lactate Threshold
observations remain candidate/audit evidence only and introduce no analytical
relationship.

The remaining v1.3 daily datasets are exposed as separate normalized JSON
artifacts and aggregate audits. They do not form a denormalized daily master,
and calendar co-presence never authorizes an Activity or cross-metric join.

## Prohibited joins

- Do not join Activities and FIT by timestamp proximity outside
  `activity_fit_links`.
- Do not infer an activity relationship for `activity_id = 0`.
- Do not join by labels, names, distance, duration, filenames, or similar
  values when no explicit relationship row exists.
- Do not treat an absent optional family as evidence that the user has no such
  data.
- Do not override an exclusion or ambiguity recorded by relationship audit.
- A documented `context_only` comparison may align separately aggregated rows
  by local calendar day, but must not create Activity row identity, merge the
  context fields into Activity facts, or imply causality. All other date-only
  joins remain prohibited.
- Do not treat Lactate Threshold candidates as a stable dataset or choose a
  latest observation across source families.

## Promotion requirements

Any future relationship requires field-level rules, cardinality, null and type
behavior, orphan policy, synthetic positive and negative tests, compatibility
and privacy review, and Product approval when it expands the public contract.

## Bounded analysis examples

- Compare monthly Activity volume with the separately aggregated monthly trend
  in Hill or Endurance Score; label the two series as context, not cause.
- Compare same-day aggregate Activity measures with Sleep, UDS, or HRV context
  without copying condition fields onto individual Activity rows.
- Plot all Race Prediction, Acute Load, Readiness, VO2Max, or Training History
  source observations in timestamp order; do not select one row per day unless
  a later Product-approved contract defines that selection.
- Inspect Lactate Threshold candidate families to assess source consistency;
  do not publish a stable threshold, unit conversion, or Activity relationship.
