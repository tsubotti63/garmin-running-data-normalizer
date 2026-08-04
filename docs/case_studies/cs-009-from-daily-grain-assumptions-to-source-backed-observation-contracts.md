# From Daily-Grain Assumptions to Source-Backed Observation Contracts in Garmin Data

Garmin Running Data Normalizer v1.3.0 expands the stable product to 17
datasets and 212 documented fields. The central engineering lesson was not how
to add more metrics. It was how to preserve source observations without
inventing a rule for which same-day value should win.

## The Problem

Wellness and Performance exports can represent more than one source
observation for the same calendar day. Normalization therefore needs an
identity contract that preserves the evidence the source actually provides.

A deterministic pipeline can still be wrong if its identity rule silently
discards one valid observation. The design question had to be resolved before
the added datasets could be treated as stable product output.

## Why One Row per Day Is Unsafe

Treating a date as the only identity forces every same-day observation into a
single slot. That approach either loses information or requires the normalizer
to choose a preferred record without source evidence that one observation
supersedes another.

The reviewed sources exposed finer observation evidence for five datasets.
The product therefore preserves independently represented observations rather
than forcing them into a one-row-per-day contract.

## Why Latest Wins Was Rejected

A generic latest-wins or keep-last rule would turn timestamp order, file order,
or parser order into product meaning. None of those orders independently proves
that one source observation replaces another.

v1.3.0 does not use latest-wins, keep-last, row order, or file order as truth
for the five reviewed observation-grain datasets. Derived day-level summaries
do not select a canonical daily row.

## The Source-Backed Observation Contract

Five Wellness and Performance datasets use source-backed observation grains.
Their stable identity is based on source evidence that explains observed
multiplicity, while exact private key composition remains unpublished.

This is a Garmin Running Data Normalizer Product contract. It does not claim
that Garmin officially guarantees those semantics, nor does it generalize
beyond the reviewed release scope.

## Separate Grain from Relationships

Record grain answers how one dataset represents an observation. It does not by
itself authorize a cross-dataset join.

The six established explicit relationships remain unchanged in v1.3.0. The new
Wellness and Performance datasets are documented as context-only; they do not
define direct Activity relationships. Similar dates or timestamps must not be
used to invent an Activity join or causal claim.

## Contract Before Code

The project inspected source multiplicity and identity evidence before the
final implementation was closed. Dataset grain, prohibited winner selection,
relationship status, and unsupported areas were recorded as Product decisions,
then projected into code, tests, machine-readable catalogs, and human guidance.

This Contract-before-Code workflow made an unsafe daily assumption reviewable
before it became hidden implementation behavior. It is process evidence, not a
claim that every defect was prevented.

## Public-Safe Evidence

Within the reviewed v1.3.0 scope:

- 17 datasets and 212 fields are documented;
- 6 explicit relationships remain defined;
- 5 datasets use source-backed observation grains; and
- bounded private aggregate validation found 0 divergent Stable Grain keys.

The zero-divergence result is a bounded aggregate conclusion from private
validation. It is not a universal guarantee. Garmin rows, exact keys, local
paths, account identifiers, and private validation artifacts are not included
in this case study.

## Release Quality

The released source passed:

- 199 pytest checks and 170 unittest checks;
- 44 of 44 deterministic validation cases;
- Ubuntu and Windows CI; and
- build, wheel, sdist, installed-package, and clean-install gates.

v1.3.0 was published as a stable GitHub Release and Production PyPI package.
The CI result applies to the reviewed configurations, and passing tests do not
imply zero defects or universal platform compatibility.

## Product Boundaries

v1.3.0 keeps several boundaries explicit:

- Health Status is deferred;
- Lactate Threshold is candidate/audit only;
- HRV is analysis-reference only and is not a coaching feature;
- no medical or coaching interpretation is provided;
- no direct Activity relationship is claimed for the new metric datasets; and
- source-backed grain is not a Garmin-official semantic guarantee.

These boundaries are part of the Product contract. They are not gaps that a
consumer or AI should fill by inference.

## Reusable Workflow

The engineering pattern is reusable for other exported operational data:

1. inspect source multiplicity before choosing a grain;
2. separate source evidence from product interpretation;
3. define identity, relationship, and exclusion contracts before implementation;
4. prohibit ordering shortcuts that are not source-backed;
5. validate with repository, installed-package, cross-platform, deterministic,
   and bounded private evidence; and
6. publish only aggregate conclusions that retain their exact qualifiers.

## Claim Traceability

- Case Study: `CS-009`
- Claims: `CLM-026` through `CLM-039`
- Achievements: `ACH-017` through `ACH-024`

Product direction, implementation, independent review, and release authority
were separated across Human and AI roles. Human approval retained final release
and publication authority.

## Related Documentation

- [Garmin Running Data Normalizer](../../README.md)
- [Supported Datasets](../supported_datasets.md)
- [Dataset Relationships](../dataset_relationships.md)
- [Wellness and Daily Metrics Contract](../wellness_metrics.md)
- [Known Limitations](../known_limitations.md)
- [v1.3.0 Release Notes](../release_notes/v1.3.0.md)

Publication of this page does not authorize a future product release or an
unsupported expansion of the documented claims.
