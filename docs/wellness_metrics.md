# Wellness and Daily Metrics Candidate Contract

This document defines the unreleased v1.3 Product-review contract for daily
condition and prediction datasets. The current stable package remains `1.2.1`.
Every family is optional and remains separate from the Activity fact table.
Race Prediction, Acute Training Load, Training Readiness, VO2Max, and Training
History are stored at one source-observation grain. Hill Score, Endurance Score,
UDS, and HRV retain calendar-day contracts; Sleep uses `sleep_day`.

## Common rules

- Missing is not zero and missing from a later Snapshot is not deletion.
- Nulls are not filled, carried forward, averaged, or interpolated.
- Source values are not recalculated and unconfirmed units are not inferred.
- Exact duplicates are deterministic; divergent values for the same stable key
  fail closed or remain an explicit review item where the dataset contract says so.
- Source observations are never collapsed by latest-wins, keep-last, source
  order, or a canonical daily-row selection. A day-level summary is derived
  from preserved observations and is not a normalized Source of Truth.
- Epoch-millisecond source timestamps are normalized to UTC. Naive ISO-8601
  source timestamps remain timezone-unconfirmed rather than receiving an
  invented offset. Activity VO2Max `timestampGmt` is treated as UTC because the
  source field explicitly names GMT.
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
| `race_prediction_daily` | `calendar_date`, `observation_timestamp` | date, source observation timestamp, and 5K/10K/Half/Marathon predictions | Garmin algorithm predictions, not measured race results or calculations made by this package |
| `sleep_daily` | `sleep_day` | `sleep_day`, local start/end, sleep-window and duration minutes, stage minutes, score, awake minutes, availability flags, normalization/reason fields | Duplicate day and missing/invalid windows remain reviewable; missing awake time is never derived |
| `uds_daily` | `calendar_date` | date; steps, distance, calories and heart-rate fields; Body Battery charged/drained; total stress values; three `raw_has_*` flags | Sparse generation-specific source context; excluded respiration, detailed stress, hydration, and private provenance are not reconstructed |
| `acute_training_load_daily` | `calendar_date`, `observation_timestamp` | date, source timestamp, ACWR fields, and acute/chronic load values | Garmin source values only; the ratio is not recalculated when absent |
| `training_readiness_daily` | `calendar_date`, `observation_timestamp` | date and source timestamp; readiness score/level/recovery; ACWR, stress-history, HRV and sleep factors; acute load; HRV weekly average; valid-sleep and sleep-score fields | HRV-labelled fields are Garmin source-provided readiness components, not HRV values calculated by this package |
| `vo2max_daily` | `calendar_date`, `vo2max_source_series`, `sport`, `observation_timestamp` | date, source timestamp, VO2Max, source series, sport, supplemental `source_activity_id`, confidence, MaxMET fields, and calibration value | Two source series share one schema; source Activity ID is provenance only; later-series-only fields remain null; value-range differences are not explained automatically |
| `hrv_daily` | `calendar_date` | `calendar_date`, `hrv_value`, `semantics_status`, `analysis_role`, record/file counts, `dedupe_status` | `analysis_reference_only`; not a daily Source of Truth and not automatically selected when same-day values differ |
| `training_history_daily` | `calendar_date`, `observation_timestamp` | `calendar_date`, `observation_timestamp`, `training_status`, optional `sport` | Deliberately limited observation contract; other sparse or unapproved fields are not emitted |

## HRV source definition

The bounded HRV reference is read from non-running FIT message `370`, field
`1`, scaled as raw value divided by `128`, with the FIT end date interpreted in
the configured local timezone. Same-date same-value observations are deduped.
Same-date differing values produce a null selected value and
`review_required_same_day_differing_values`; the package never chooses a latest
or average value. Health Status data is not treated as equivalent HRV evidence.

## Snapshot and output behavior

The five source-observation datasets use `immutable_observation_union` with
missing-is-not-delete and same-stable-key conflict fail-closed behavior. The
remaining daily JSON datasets keep their declared daily-state contracts. HRV is
regenerated from the cumulative unique FIT blob set. Run-All emits one normalized
JSON and aggregate audit per dataset, plus `qa/daily_metrics_summary.json`. For
the five observation datasets, that summary includes a derived, non-canonical
day-level projection with `selection_rule: null`. An absent optional family is
reported as `SKIPPED_NOT_PRESENT` and does not fail the run.

Health Status is deferred from v1.3. Its fields are not promoted to the public
registry, Run-All output, Snapshot merge, or schema catalog.
