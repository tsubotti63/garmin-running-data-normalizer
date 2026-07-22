# M7.3 HRV Migration PoC Report

## Status and scope

M7.3 adds dependency-free, library-level Garmin HRV normalization using only
the Stable Release Migration Roadmap and authorized Public Edition Source Tree
packs `00_shared/`, `10_fit_normalization/`, and `20_wellness_platform/`.
The original private project was not accessed.

## Implemented behavior

- Extract FIT Message 370 / Field 1 and scale the raw value by 128 to
  milliseconds.
- Derive the daily candidate date from FIT Field 253 converted to the requested
  local timezone.
- Exclude invalid raw sentinel `65535` while retaining invalid-value counts.
- Deduplicate identical valid same-date values and retain conflicting values as
  review evidence without averaging.
- Preserve missing-date and unparseable candidates as explicit holds.
- Discover FIT and exact-suffix `healthStatusData.json` assets through the
  existing safe directory/ZIP intake layer.
- Derive stable FIT identity from content SHA-256 and retain relative path and
  SHA-256 provenance.
- Extract health-status-scoped HRV values and compare same-date availability or
  values without merging sources or asserting measurement equivalence.

## Public contract boundary

M7.3 remains a library capability. It does not change Run-All, the dataset
registry, schemas, CLI, package version, or fixed output layout. The authorized
later HRV candidate makes FIT-derived HRV the normalization target and treats
`healthStatusData` comparison as validation evidence only. No source-of-truth,
nightly-HRV, analysis-ready, or coaching promotion is made.

## Migration gaps and recommendations

The public Source Tree is sufficient for the bounded PoC but lacks synthetic,
dependency-free FIT Message 370 fixtures and expected JSON output. The FIT
Message 370 rule is explicitly a PoC rule and is not accompanied by a normative
Garmin profile reference. The Tree should add an asset manifest, synthetic
valid/invalid/conflicting fixtures, an explicit measurement-semantics table for
FIT versus health-status HRV, and a lifecycle decision for any future Run-All
or schema integration.

## Explicit non-targets

M7.3 does not implement Health Status normalization beyond the HRV comparison
reference, activity joins, filling, cross-date copying, averaging conflicts,
source promotion, analytics, coaching, Sleep changes, Weather, Instagram, JMA,
or future roadmap metrics.
