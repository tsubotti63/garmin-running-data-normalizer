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
- `run_summary.json`

Use normalized JSON, relationship links, QA, or audit files only when the
question requires them and the local/trusted environment is authorized.

## Receiving Rules

1. Separate observed facts, calculations, interpretations, and unknowns.
2. Preserve null and missing values; never convert them to zero.
3. State filters, formulas, denominators, and missing-value counts.
4. Use only relationships marked `explicit` in `ANALYSIS_CONTEXT.json`.
5. Use `activity_fit_links` for Activity/FIT joins; timestamp-only joins are prohibited.
6. Treat Personal Records with `activity_relationship_status=independent`
   as non-activity records and do not force an activity identity.
7. Preserve and disclose warnings or partial FIT status.
8. Ask for an additional approved file when the supplied artifacts cannot
   answer the question; do not invent source fields or context.

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
