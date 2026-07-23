# Dataset Relationship Catalog

## Purpose

This catalog defines every cross-dataset relationship supported by the public
Run-All v1.1 contract. Similar fields, filenames, dates, or timestamps never
authorize a join by themselves.

Relationship status uses `explicit`, `indirect`, `independent`,
`not_yet_defined`, or `unsupported`. The current stable Run-All datasets use
only reviewed `explicit` relationships plus the documented independent
Personal Record exception.

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
```

## Relationship catalog

| Left artifact | Right artifact | Status | Fields | Cardinality | Validation |
|---|---|---|---|---|---|
| `normalized/activity_gear.json` | `normalized/gear.json` | `explicit` | `gear_key` | many-to-one | null, type mismatch, duplicate link, and orphan gear fail closed |
| `normalized/activity_gear.json` | `normalized/activities.json` | `explicit` | `garmin_activity_key` | many-to-one | source `activity_id` must resolve to exactly one normalized Activity |
| `normalized/personal_records.json` | `normalized/activities.json` | `explicit` or `independent` | `garmin_activity_key` | many-to-zero-or-one | nonzero source activity identity must resolve; `activity_id = 0` remains independent |
| `normalized/fit_laps.json` | `normalized/fit_sessions.json` | `explicit` | `fit_session_key` | many-to-one | every lap has one existing parent session |
| `normalized/activity_fit_links.json` | `normalized/activities.json` | `explicit` | `garmin_activity_key` | one-to-one within eligible population | link rows are mutual unique evidence-qualified matches |
| `normalized/activity_fit_links.json` | `normalized/fit_sessions.json` | `explicit` | `fit_session_key` | one-to-one within eligible population | link rows are mutual unique evidence-qualified matches |

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

## Prohibited joins

- Do not join Activities and FIT by timestamp proximity outside
  `activity_fit_links`.
- Do not infer an activity relationship for `activity_id = 0`.
- Do not join by labels, names, distance, duration, filenames, or similar
  values when no explicit relationship row exists.
- Do not treat an absent optional family as evidence that the user has no such
  data.
- Do not override an exclusion or ambiguity recorded by relationship audit.

## Promotion requirements

Any future relationship requires field-level rules, cardinality, null and type
behavior, orphan policy, synthetic positive and negative tests, compatibility
and privacy review, and Product approval when it expands the public contract.
