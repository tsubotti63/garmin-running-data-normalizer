# Dataset Relationship Catalog

## Purpose

This catalog defines the cross-artifact relationships already supported by the
public Run-All v1 implementation and identifies unresolved relationships
without inference. A matching field name or nearby timestamp is not sufficient
to authorize a join.

Relationship status uses:

- `explicit`: implementation and existing tests support the stated fields and
  direction.
- `indirect`: access requires another declared artifact.
- `independent`: no cross-dataset join is intended.
- `not_yet_defined`: the public product has not established a safe join
  contract.
- `unsupported`: outside the current product boundary.

## Relationship catalog

| Left artifact | Right artifact | Status | Fields | Cardinality | Public rule |
|---|---|---|---|---|---|
| `analysis/activities.csv` | `normalized/activities.json` | `explicit` | `garmin_activity_key` | one-to-one projection | CSV is a reduced deterministic projection and is not a new Source of Truth |
| `normalized/fit_laps.json` | `normalized/fit_sessions.json` | `explicit` | `fit_file_id` | many laps to one bounded session | Valid only within the current one-session-per-FIT-file implementation |
| `normalized/activity_gear.json` | `normalized/gear.json` | `not_yet_defined` | candidate field: `gear_key` | not declared | Referential integrity and orphan policy are not part of the current public contract |
| `normalized/activity_gear.json` | `normalized/activities.json` | `not_yet_defined` | candidate fields: `activity_id`, `garmin_activity_key` | not declared | Do not construct or infer an activity key without an approved relationship contract |
| `normalized/personal_records.json` | `normalized/activities.json` | `not_yet_defined` | candidate field: `activity_id` | not declared | Personal records remain independently usable; non-activity records must not be forced into an activity identity |
| `normalized/fit_sessions.json` | `normalized/activities.json` | `not_yet_defined` | none | not declared | Filename, sport, distance, and timestamp proximity do not establish identity |

## Evidence relationships

The following are evidence or projection relationships, not analytical joins:

- `qa/dataset_summary.json` reports dataset-level QA for normalized outputs.
- `audit/fit_audit.json` reports FIT-file parse status and completeness.
- `run_manifest.json` records dataset grain, stable keys, provenance inventory,
  and output integrity.
- `run_summary.json` records run and family completion status.

These artifacts may qualify or limit an analysis, but they do not add rows or
new normalized facts.

## Explicit relationship details

### Activities CSV projection

The CSV renderer iterates the normalized Activities records, preserves one row
per activity, retains `garmin_activity_key`, and emits a fixed reduced column
set. The normalized JSON remains authoritative. The stable key can contain a
source activity identifier and must remain private.

### FIT laps to FIT sessions

The FIT parser derives `fit_file_id` from FIT content identity and assigns the
same value to the bounded session and its laps. `lap_index` identifies a lap
within that file. Complete multi-session FIT identity is not implemented, so
this relationship must not be generalized beyond the current bounded parser.

## Prohibited joins

- Do not join datasets by timestamp proximity.
- Do not transform `activity_id` into `garmin_activity_key` unless a later
  reviewed public contract authorizes the exact transformation and fallback
  behavior.
- Do not use labels, names, distance, duration, or sport values as identity.
- Do not treat missing optional-family output as evidence that the user has no
  such data.
- Do not promote a `not_yet_defined` relationship through documentation,
  prompts, examples, or AI inference.

## Promotion requirements

Changing a relationship from `not_yet_defined` to `explicit` requires:

1. field-level join rules;
2. cardinality and optionality;
3. null and type-mismatch behavior;
4. orphan-left and orphan-right behavior where applicable;
5. synthetic positive and negative tests;
6. compatibility and privacy review;
7. Product approval when the change expands the public contract.
