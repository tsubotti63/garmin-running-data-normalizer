# Relationship Coverage as an Evidence Boundary

## Summary

Cross-dataset similarity is not proof of identity. Garmin Running Data
Normalizer limits joins to reviewed explicit relationship contracts and leaves
unknowns visible.

In one real-user `v1.1.1` validation dataset, it established 3,464 explicit
Activity–FIT relationships. Four Activities and one eligible FIT Session
remained unresolved rather than being guessed; ambiguous matches were 0,
duplicate matches were 0, and inference was not performed. Coverage is reported
separately for each relationship's eligible population. It is an Evidence
Boundary, not a normalization success score.

## Why implicit joins are unsafe

Two records may share similar timestamps, distances, labels, or order without
being the same real-world entity. Treating similarity as identity can:

- connect an Activity to the wrong FIT Session;
- hide duplicates or ambiguity;
- inflate downstream counts;
- make a result impossible to audit;
- turn an AI-generated guess into an apparently authoritative join.

The project therefore requires a documented relationship contract before a join
is promoted.

## Grain before join

Every dataset has a record grain and a stable-key contract. Relationships are
reviewed against those grains rather than inferred from convenient columns.
Examples include:

```text
Activities
  ├─ Activity/Gear Links ─ Gear
  ├─ Personal Records / independent
  └─ Activity/FIT Links ─ FIT Sessions ─ FIT Laps
```

A relationship is evaluated only within its defined eligible population. Input
excluded by a fail-closed parser boundary is not silently moved into the
relationship denominator.

## Relationship states

The Output Experience keeps distinct states visible:

| State | Meaning |
|---|---|
| `explicit` | A reviewed contract established the relationship |
| `unresolved` | An eligible record could not be linked without guessing |
| `excluded` | The record is outside the eligible population under a documented boundary |
| `independent` | The contract says the record is valid without a relationship |
| `ambiguous` | More than one candidate prevents unique promotion |
| `duplicate` | Duplicate evidence prevents unique promotion |

`unresolved`, `excluded`, and `independent` are not interchangeable with error.

## Activity–FIT evidence boundary

The reviewed one-user validation produced:

| Side | Explicit | Eligible denominator | Unresolved |
|---|---:|---:|---:|
| Activity side | 3,464 | 3,468 | 4 |
| FIT Session side | 3,464 | 3,465 | 1 |

Additional reviewed states:

| State | Count / value |
|---|---:|
| Ambiguous matches | 0 |
| Duplicate matches | 0 |
| Inference performed | No |

The two denominators answer different questions and must not be merged into one
percentage. The result is not “99.88% of Garmin data succeeded.” It says how far
explicit evidence reaches within each defined eligible population.

## Other explicit relationships

The same design applies beyond Activity–FIT:

- Activity/Gear → Activities reached 100% explicit coverage within its defined
  eligible population.
- Activity/Gear → Gear reached 100% explicit coverage within its defined
  eligible population.
- FIT Laps → FIT Sessions reached 100% explicit coverage within its defined
  eligible population.
- Sixty-six Personal Records were explicitly related to Activities, while five
  were retained as contract-defined independent records.

These scoped statements do not mean that all Garmin data or every possible
relationship is complete.

## Fail-closed FIT boundary

The same validation completed with `PARTIAL_SUCCESS`, 0 errors, and one
`FIT_PARSE_INCOMPLETE` warning. Twenty incomplete FIT assets—19 session/lap
allocation conflicts and one unsupported chained asset—were retained as
auditable partial evidence rather than guessed.

Those parser states remain visible in FIT audit and affect which Sessions and
Laps are eligible for promoted relationships. They are not hidden to improve a
coverage percentage.

## Human-readable and machine-readable projections

Relationship Coverage is projected into:

- `START_HERE.md`;
- `ANALYSIS_HANDOFF.md`;
- `ANALYSIS_CONTEXT.json`;
- `qa/relationship_summary.json`;
- `audit/activity_fit_linkage.json`.

The human-readable views explain how to interpret the boundary. The
machine-readable views preserve counts and states so an approved analysis tool
does not need to reconstruct the join policy.

## Reuse beyond Garmin

The pattern applies to other data systems:

1. define record grain;
2. define stable identity;
3. define the eligible population;
4. promote only evidence-qualified relationships;
5. preserve unresolved, excluded, independent, ambiguous, and duplicate states;
6. expose the same contract to humans and machines;
7. prohibit inference where identity is not established.

This is useful in migrations, entity matching, audit pipelines, and AI-assisted
analysis where a plausible join can be more dangerous than an explicit unknown.

## Privacy and interpretation boundary

This case study publishes only reviewed aggregates. It does not include real
rows, stable keys, raw identifiers, memo text, coordinates, source filenames,
private paths, raw hashes, or exact row-level dates.

Relationship Coverage does not establish export completeness, data correctness
outside the contract, fitness, training effect, readiness, or causality.

## Related material

- [CS-001: From a Real Garmin Export to an Auditable AI-Ready Handoff](cs-001-real-garmin-export-to-auditable-ai-ready-handoff.md)
- [Product Quick Start](../product_quick_start.md)
- [Dataset Relationship Catalog](../dataset_relationships.md)
- [Run-All Output Contract](../output_contract.md)
- [Known Limitations](../known_limitations.md)
