# Wellness and Daily Metrics Candidate Contract

This document defines the unreleased v1.3 Product-review contract for daily
condition and prediction datasets. The current stable package remains `1.2.1`.
Every family is optional, remains separate from the Activity fact table, and is
stored at one calendar-day grain unless the Sleep contract says `sleep_day`.

## Common rules

- Missing is not zero and missing from a later Snapshot is not deletion.
- Nulls are not filled, carried forward, averaged, or interpolated.
- Source values are not recalculated and unconfirmed units are not inferred.
- Exact duplicates are deterministic; divergent values for the same stable key
  fail closed or remain an explicit review item where the dataset contract says so.
- Similar dates do not authorize a join to Activities or another daily dataset.
- Private device/account identifiers, source paths, extraction metadata, and
  parser metadata are excluded from these normalized rows.

## Generation boundary

Available Garmin measurements change across device and export generations. For
this candidate, approximately 2015-2021 is described as the earlier generation
and 2022 onward as the later generation. This is descriptive source context,
not a claim that the periods are complete, homogeneous, or automatically
equivalent. A missing field outside its source period remains null. The VO2Max
source transition observed between `2022-01-22` and `2022-01-23` is represented
by `vo2max_source_series`; neither series overwrites the other.

## Dataset contracts

| Dataset | Stable key | Public fields | Interpretation boundary |
|---|---|---|---|
| `race_prediction_daily` | `calendar_date` | `calendar_date`, `race_time_5k_sec`, `race_time_10k_sec`, `race_time_half_sec`, `race_time_marathon_sec` | Garmin algorithm predictions, not measured race results or calculations made by this package |
| `sleep_daily` | `sleep_day` | `sleep_day`, local start/end, sleep-window and duration minutes, stage minutes, score, awake minutes, availability flags, normalization/reason fields | Duplicate day and missing/invalid windows remain reviewable; missing awake time is never derived |
| `uds_daily` | `calendar_date` | date; steps, distance, calories and heart-rate fields; Body Battery charged/drained; total stress values; three `raw_has_*` flags | Sparse generation-specific source context; excluded respiration, detailed stress, hydration, and private provenance are not reconstructed |
| `acute_training_load_daily` | `calendar_date` | `calendar_date`, `acwr_percent`, `acwr_status`, `daily_training_load_acute`, `daily_training_load_chronic`, `daily_acute_chronic_workload_ratio` | Garmin source values only; the ratio is not recalculated when absent |
| `training_readiness_daily` | `calendar_date` | date; readiness score/level/recovery; ACWR, stress-history, HRV and sleep factors; acute load; HRV weekly average; valid-sleep and sleep-score fields | HRV-labelled fields are Garmin source-provided readiness components, not HRV values calculated by this package |
| `vo2max_daily` | `calendar_date` | `calendar_date`, `vo2max`, `vo2max_source_series`, `sport`, `source_confidence`, `max_met`, `max_met_category`, `calibrated_data` | Two source series share one schema; later-series-only fields remain null in earlier rows; value-range differences are not explained automatically |
| `hrv_daily` | `calendar_date` | `calendar_date`, `hrv_value`, `semantics_status`, `analysis_role`, record/file counts, `dedupe_status` | `analysis_reference_only`; not a daily Source of Truth and not automatically selected when same-day values differ |
| `training_history_daily` | `calendar_date` | `calendar_date`, `training_status` | Deliberately limited two-field contract; other sparse or unapproved fields are not emitted |

## HRV source definition

The bounded HRV reference is read from non-running FIT message `370`, field
`1`, scaled as raw value divided by `128`, with the FIT end date interpreted in
the configured local timezone. Same-date same-value observations are deduped.
Same-date differing values produce a null selected value and
`review_required_same_day_differing_values`; the package never chooses a latest
or average value. Health Status data is not treated as equivalent HRV evidence.

## Snapshot and output behavior

The JSON daily datasets use `daily_state_upsert` with missing-is-not-delete and
same-key conflict fail-closed behavior. HRV is regenerated from the cumulative
unique FIT blob set. Run-All emits one normalized JSON and aggregate audit per
dataset, plus `qa/daily_metrics_summary.json`. An absent optional family is
reported as `SKIPPED_NOT_PRESENT` and does not fail the run.

Health Status is deferred from v1.3. Its fields are not promoted to the public
registry, Run-All output, Snapshot merge, or schema catalog.
