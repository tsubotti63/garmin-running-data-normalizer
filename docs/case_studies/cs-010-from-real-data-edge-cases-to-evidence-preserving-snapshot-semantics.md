# CS-010: From Real-Data Edge Cases to Evidence-Preserving Snapshot Semantics

## Summary

Garmin Running Data Normalizer v1.3.2 was shaped by repeated real Garmin
Account Data Exports that did not always describe the same observation in the
same way. The important result was not a more aggressive cleanup rule. It was
a stricter separation between what the exports observed, what the product can
declare as canonical, and what must remain unresolved.

The release preserves observed facts, refuses unsupported winner selection,
distinguishes resolvable absence from malformed input, and keeps processing
sequence from changing normalized truth. This case study describes the
incident-to-evidence path that led to those contracts.

## Context

Snapshot accumulation was already designed to treat repeated exports as
observations rather than disposable replacements. v1.3.0 had also introduced
source-backed observation grains for Wellness and Performance datasets.

v1.3.2 applied those principles to edge cases found while validating repeated
exports and then carried the resulting contracts through focused patches,
bounded matrices, release checks, Production PyPI installation, and public
truth reconciliation.

## What triggered the investigation

Real-data validation exposed several classes of behavior that a generic
one-row-per-day or latest-wins rule would have hidden:

- a current export could omit an endpoint that was observed in an earlier
  snapshot;
- identical Sleep observations could be reported more than once;
- Endurance and UDS could contain different observed values for one daily key;
- more than one valid Lactate Threshold power candidate could exist; and
- runtime processing sequence could influence relationship classification even
  when snapshot acquisition chronology was unchanged.

These were not one bug with one universal fallback. They were different
evidence and authority questions.

## What the real data exposed

The repeated exports showed that absence, repetition, difference, and malformed
content have different meanings. A later file is not automatically a complete
replacement, and a parser's iteration order is not source authority.

The investigation therefore classified each issue before changing code:

1. Can the observation be resolved from authoritative snapshot evidence?
2. Is it an exact duplicate under the dataset's public equality contract?
3. Are multiple values genuine observations with no supported winner?
4. Is the input malformed enough to require fail-closed behavior?
5. Is a value a candidate for audit rather than a Stable public fact?

## Why “fail on difference” was the wrong model

Failing every time two observations differed would preserve safety at the cost
of discarding evidence. It would also conflate a legitimate variant with a
malformed record.

The product decision became:

- missing is not zero;
- missing is not delete;
- different is not overwrite;
- unknown semantics is not data loss;
- no inference, latest-wins, or keep-last shortcut; and
- canonicalization requires evidence.

When a difference is a real observed variant and no authority rule exists, the
normalizer retains the variants and leaves the canonical interpretation
unresolved. When the input is malformed, the existing fail-closed boundary is
preserved.

## Product decision: preserve evidence, not invent authority

The v1.3.2 contract is conservative in a specific way: it does not make
ambiguous exports look cleaner than the source evidence supports. A clean
output is useful only when its selection rule is explainable and reproducible.

This is a Product contract for the reviewed release scope. It is not a claim
about Garmin-official semantics, every possible export, or medical or coaching
interpretation.

## Fixes

### Relationship: snapshot-aware resolution

Relationship resolution can use an authoritative endpoint observed in an
earlier snapshot when the current export has no endpoint. A valid unresolved
candidate is retained as a non-fatal, auditable outcome. Malformed input still
fails closed; the new path does not turn malformed data into a guessed link.

### Sleep: exact duplicate handling

Sleep observations that are exactly equal under the public canonical and
presence contract are collapsed deterministically. Divergent values,
null-versus-value differences, and absent-versus-null differences remain
reviewable and fail-closed. Filename or processing order is not used as a
winner rule.

### Endurance / UDS: observed variants

Cross-snapshot values that genuinely differ are preserved as observed variants.
The normalizer does not select a latest or preferred value without authority.
If a Stable canonical value cannot be justified, the canonical result remains
unresolved while the observations remain available for audit.

### Lactate: candidate preservation

Multiple valid Lactate Threshold power candidates are retained as candidates.
No candidate is promoted to Stable merely because it is newest, last in a file,
or encountered first. Stable public promotion remains outside this contract.

### Ordering: acquisition chronology versus processing sequence

Snapshot chronology is derived from the acquisition metadata
(`manifest.export_observed_at`). Runtime processing sequence is operational
metadata only. Processing sequence must not alter normalized truth, relationship
classification, or candidate authority.

## Validation strategy

The evidence is intentionally split into bounded categories:

### Four real snapshots

The release evidence uses four repeated real Garmin Export snapshots. They are
not four independent users or four independent datasets.

### Fifteen non-empty real-data subsets

All 15 non-empty subset combinations completed the reviewed Full Run-All
validation. The result is bounded to those snapshots, the reviewed input
contract, and the release validation environment.

### Synthetic 24 processing-order permutations

All 24 processing-order permutations of the tracked Synthetic Store produced
the same deterministic result, with `PASS_WITH_WARNINGS` and exit code `0`.
This demonstrates the processing-sequence separation on the public fixture; it
does not establish universal order independence for arbitrary private exports.

### Four representative real-data processing orders

Four representative real-data processing orders produced equal aggregate build
and output evidence, with zero lost values, invented values, or automatic
winners. Their known non-fatal boundary remains visible in the reported
`PARTIAL_SUCCESS` / exit `3` status.

### Preservation and quality evidence

The confirmed aggregate evidence records:

- lost observed values: `0`;
- invented values: `0`;
- automatic winners: `0`;
- malformed silently tolerated: `0`; and
- unknown warnings: `0`.

The release source also passed `251` pytest checks and `208` unittest checks.
The public catalog contains 17 datasets and 212 fields, with 6 explicit
relationships. Ubuntu and Windows CI passed.

## What was intentionally not resolved

v1.3.2 does not claim any of the following:

- a completed exhaustive 24-order **real-data** matrix;
- a universal guarantee for all Garmin exports or all platforms;
- Garmin-official meaning for the Product's observation contracts;
- Stable public Lactate Threshold promotion;
- HRV coaching availability;
- medical accuracy or coaching advice; or
- an automatic winner when source authority is absent.

The four representative real-data orders and the synthetic 24-order matrix are
separate from any future exhaustive real-data ordering evidence.

## Release and production validation

v1.3.2 was released as the Latest GitHub Release and published to Production
PyPI. The production package passed isolated build and `twine check` gates,
wheel and sdist validation, and a clean Production PyPI installation. A
Synthetic Run-All from the production package completed with
`PASS_WITH_WARNINGS` and exit code `0`.

These checks validate the reviewed source, package, fixture, and execution
paths. They do not convert bounded evidence into a universal support claim.

## Public-truth reconciliation

The public repository, release, PyPI package, README, Quick Start, Release
Notes, and Zenn links were reconciled for the v1.3.2 state. Historical
pre-release records remain historical; they are not silently rewritten as
current state.

The repository's `main` branch is now protected by the active
`main-protection` Ruleset. Ordinary changes require a Pull Request and the
existing `test` and `windows-runtime` checks; release and PyPI workflows remain
separate operations.

## Repository governance follow-up

The governance change was intentionally docs-only. A PoC Pull Request verified
that merge is blocked while required checks are pending and allowed after both
checks pass. A normal direct push to `main` was rejected by GitHub. Force-push
and deletion protections were verified from the active Ruleset without running
destructive tests.

## Lessons

The durable lesson is not “make every export agree.” It is to make every
selection rule explainable:

1. inspect multiplicity before choosing a grain;
2. separate acquisition chronology from runtime processing sequence;
3. preserve observations when authority is unknown;
4. distinguish resolvable, unresolved, and malformed states;
5. test both synthetic permutations and bounded real-data orders; and
6. publish only aggregate evidence with its qualifiers intact.

## Evidence boundary

This case study contains no Garmin rows, local paths, stable keys, account
identifiers, filenames, private hashes, or private generated artifacts. The
reported real-data results are public-safe aggregates from one reviewed set of
repeated exports. The synthetic ordering result is reproducible from the
tracked fixture.

## Reproduction / references

- [Product Quick Start](../product_quick_start.md)
- [v1.3.2 Release Notes](../release_notes/v1.3.2.md)
- [CS-007: Preserving Garmin History Across Incomplete Repeated Exports](cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md)
- [CS-008: Windows Timezone Hotfix from Field Report to Production Validation](cs-008-windows-timezone-hotfix-from-field-report-to-production-validation.md)
- [CS-009: From Daily-Grain Assumptions to Source-Backed Observation Contracts](cs-009-from-daily-grain-assumptions-to-source-backed-observation-contracts.md)
- [Supported Datasets](../supported_datasets.md)
- [Dataset Relationships](../dataset_relationships.md)

This draft is a candidate for Product review. Its presence on a review branch
does not authorize merge, Zenn publication, external outreach, or a future
release.
