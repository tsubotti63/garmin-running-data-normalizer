# Performance Metrics Contract

## Status

This document describes the performance-metrics contract that the stable
v1.3.0 GitHub Release and Production PyPI distribution introduced, as the
current stable v2.1.0 keeps it; text that begins "Starting with v2.0.0"
describes what v2.0.0 changes.

## Stable daily datasets

`hill_score_daily` has calendar-day grain and exposes only:

- `calendar_date`
- `overall_score`
- `strength_score`
- `endurance_score`
- `classification_id`
- `feedback_phrase_id`

`endurance_score_daily` has calendar-day grain and exposes only:

- `calendar_date`
- `overall_score`
- `classification`
- `feedback_phrase`

For both datasets, `calendar_date` is the stable key. Exact duplicates and
same-public-value duplicates collapse deterministically. Starting with v2.0.0,
a same-day public value conflict, within one Export or across Snapshots, keeps
the day: each field whose values differ is null and listed in
`disagreeing_fields`, the dataset's audit record keeps every observed value
and the Snapshots that gave it, and the run warns with `VALUES_DISAGREE` (see
[Values that disagree](v2_data_handling.md#values-that-disagree)). A row
without a usable overall score is left out with `DATA_ROW_LEFT_OUT`, and a
value of another form in another field is null with `DATA_VALUE_INVALID` (see
[Rows and values with problems](v2_data_handling.md#rows-and-values-with-problems)).
Snapshot accumulation retains earlier daily state when a later complete Export
omits it; it never uses keep-last to resolve a conflict.

Garmin may encode source `calendarDate` as an ISO-like string or epoch
milliseconds. Epoch milliseconds represent the labeled UTC calendar day and
are converted to that UTC date without a local-time shift. Raw timestamps are
not emitted in the public daily rows.

Private account, device, raw timestamp, path, filename, and hash details are
not present in stable rows. Audit exposes aggregate counts rather than private
values.

## Lactate Threshold gate

The implementation collects bounded candidates from four source families:

- history
- latest snapshot
- profile state
- derived evidence

The result remains in `audit/lactate_threshold_candidates.json`. Observation
timestamp is an identity anchor, not an approved machine stable key. Numeric
units and timezone semantics remain `UNCONFIRMED`. Sequence can support
deterministic within-source ordering only. Cross-source candidates are not
collapsed, converted, averaged, or resolved by latest-wins logic. Derived
evidence is audit-only. Starting with v2.0.0, an item that is not a record is
left out with `DATA_ROW_LEFT_OUT`, and a value of another form stays in the
audit record with `DATA_VALUE_INVALID`, both for the family
`lactate_threshold`; a malformed candidate no longer stops the run.

Stable promotion requires Product approval of the identity, unit, timezone,
and conflict contracts.

## Analysis boundary

`analysis/performance_metrics_daily.csv` is a deterministic convenience view.
Hill fields use the `hill_` prefix and Endurance fields use the `endurance_`
prefix. No Activity relationship is defined, and consumers must not infer one
from date equality.
