# M7.4 Health Status Migration PoC Report

## Status and scope

M7.4 adds dependency-free, library-level Garmin Health Status normalization
using only the Stable Release Migration Roadmap and authorized Public Edition
Source Tree packs `00_shared/` and `20_wellness_platform/`. The original private
project was not accessed.

## Complete library schemas

The normalizer returns `metrics` and `daily` collections. The long metric schema
retains calendar date, source timestamps, outlier count, metric type, value,
baseline limits, Garmin status, percentage, feedback key, normalization and
daily-selection states, stable keys, and provenance.

The daily schema has fixed fields for HRV, HR, SPO2, skin temperature, and
respiration. Each family exposes value, Garmin status, baseline limits,
percentage, and feedback key. Unknown metric types remain in long form and only
increment an unknown count; they never create uncontrolled daily columns.

## Safety and dedupe behavior

- Input discovery uses exact `healthStatusData.json` suffix matching and the
  existing safe directory/ZIP layer.
- Numeric values outside the JSON exact-integer range and non-finite values are
  normalized to null.
- Duplicate metric types remain in long form and their daily slots stay null
  rather than being silently overwritten.
- Duplicate calendar dates select the latest valid update timestamp, then create
  timestamp, then stable key. Superseded metric rows remain explicit evidence.
- Missing dates and empty metric lists remain review states without inference.
- Stable keys derive from content SHA-256 and record position; provenance is
  relative and includes the full content SHA-256.

## Public contract boundary

M7.4 does not change Run-All, the dataset registry, public schemas, CLI, package
version, or fixed output layout. Health-status HRV keeps its source-scoped name;
nightly/rolling/baseline equivalence is not asserted. No analysis-ready,
interpretive, medical, wellness-coaching, or personal recommendation promotion
is made.

## Migration gaps and recommendations

The Source Tree provides a clear long/wide schema and a later staging candidate,
but no dependency-free synthetic expected-output fixture or normative metric
semantics reference. The Tree should add a versioned Health Status schema,
synthetic duplicate/unknown/invalid fixtures, metric units and semantics, and an
explicit lifecycle decision before any Run-All integration.

## Explicit non-targets

M7.4 does not change FIT HRV or Sleep, perform activity joins, infer missing
metrics, create dynamic daily fields, interpret statuses, or add analytics,
coaching, Weather, Instagram, JMA, or future roadmap metrics.
