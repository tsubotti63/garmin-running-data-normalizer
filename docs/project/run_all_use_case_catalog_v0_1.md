# Run-All Use Case Catalog v0.1

## Scope

This catalog describes analysis opportunities supported by Run-All v1 output.
It does not add analytics to the product. Examples must use synthetic data or a
separately reviewed anonymous aggregate. Missing values remain missing, and all
warning or partial-success states must accompany derived results.

## 1. Activity-count trend

- **Purpose:** Count completed activity rows by calendar period.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_date_local`; optionally `activity_type`, `sport_type`.
- **Output example:** Monthly table with activity count and source row count.
- **Interpretation caution:** A count change describes this export only and
  does not establish motivation, fitness, or data completeness.
- **Not currently supported:** Inferring missed or unrecorded activities.

## 2. Monthly distance and duration

- **Purpose:** Sum distance and duration by calendar month.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_date_local`, `distance_m`, `duration_sec`.
- **Output example:** Month, activity count, total kilometres, total hours, and
  missing-value counts.
- **Interpretation caution:** Exclude missing values per metric and disclose the
  denominator; blank values are not zero.
- **Not currently supported:** Correcting device measurement error or deriving
  unrecorded distance.

## 3. Activity-type composition

- **Purpose:** Compare the share of activities across source classifications.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_type`, `sport_type`.
- **Output example:** Count and percentage by observed label.
- **Interpretation caution:** Preserve labels as exported; do not silently merge
  classifications with similar names.
- **Not currently supported:** A universal sport taxonomy or semantic relabeling.

## 4. Heart-rate trend

- **Purpose:** Describe available average and maximum heart-rate values over
  time or by activity type.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_date_local`, `avg_hr`, `max_hr`, `activity_type`.
- **Output example:** Monthly median or mean, range, observed count, and missing
  count for each heart-rate field.
- **Interpretation caution:** Values are descriptive device records, not medical
  evidence; sensor quality and context are not normalized.
- **Not currently supported:** Heart-rate zones, diagnoses, or health advice.

## 5. Power trend

- **Purpose:** Summarize available average and maximum power values.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_date_local`, `avg_power`, `max_power`, `activity_type`.
- **Output example:** Period-level coverage, central tendency, and range.
- **Interpretation caution:** Report missingness and avoid comparing activities
  whose source semantics or equipment context are unknown.
- **Not currently supported:** Critical-power modeling or calibration checks.

## 6. Cadence trend

- **Purpose:** Summarize observed running cadence over time.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_date_local`, `avg_run_cadence`, `activity_type`.
- **Output example:** Monthly observed count, median cadence, and missing count.
- **Interpretation caution:** Do not reinterpret the source cadence basis or
  compare it with a different cadence convention without confirmation.
- **Not currently supported:** Form assessment or technique recommendations.

## 7. Training-load trend

- **Purpose:** Describe exported training-load values and labels by period.
- **Required files:** `analysis/activities.csv`, `run_summary.json`.
- **Columns:** `activity_date_local`, `activity_training_load`,
  `training_effect_label`.
- **Output example:** Monthly sum and median of observed values, label counts,
  and missing counts.
- **Interpretation caution:** Preserve Garmin-provided semantics and avoid
  converting descriptive values into coaching prescriptions.
- **Not currently supported:** Recovery readiness, training plans, or causal
  attribution.

## 8. Gear usage

- **Purpose:** Review which gear records are linked to activities and summarize
  link counts.
- **Required files:** `normalized/gear.json`,
  `normalized/activity_gear.json`, `run_summary.json`.
- **Fields:** `gear_key`, `display_name`, `gear_type`, `date_begin`, `date_end`,
  `maximum_meters`, and link `activity_id`.
- **Output example:** Local table of gear item, type, lifecycle dates, and linked
  activity count with identifiers suppressed from presentation.
- **Interpretation caution:** `activity_id` is a raw local join field; never
  expose it. A missing link does not prove gear was unused.
- **Not currently supported:** Distance-by-gear joins from the reduced CSV,
  wear prediction, or replacement advice without an explicitly reviewed join.

## 9. Personal-record reference

- **Purpose:** List observed personal-record types and current/confirmed states.
- **Required files:** `normalized/personal_records.json`, `run_summary.json`.
- **Fields:** `personal_record_type`, `value`, `start_time_gmt`, `created_date`,
  `current`, `confirmed`.
- **Output example:** Private summary by record type and status.
- **Interpretation caution:** Do not publish identifiers or assume units for
  `value` unless the source contract supplies them.
- **Not currently supported:** Record verification against external rules or
  cross-user rankings.

## 10. FIT session and lap review

- **Purpose:** Inspect bounded session and lap summaries from detected FIT files.
- **Required files:** `normalized/fit_sessions.json`,
  `normalized/fit_laps.json`, `audit/fit_audit.json`, `run_summary.json`.
- **Fields:** Session `start_datetime_local`, `sport`, `sub_sport`, `distance_m`,
  `elapsed_time_sec`, `timer_time_sec`, heart rate, power, `lap_count`; lap
  `lap_index`, timing, distance, speed, heart rate, cadence, power, ascent, and
  descent when present.
- **Output example:** Private session table with lap count and parse status.
- **Interpretation caution:** Filter only after reviewing audit status; selected
  session/lap fields are not a complete FIT representation.
- **Not currently supported:** Record-level telemetry, coordinates, complete
  CRC validation, or all FIT message types.

## 11. Warning and audit review

- **Purpose:** Establish which families are complete before analysis.
- **Required files:** `run_summary.json`; add `audit/fit_audit.json` and
  `qa/dataset_summary.json` when relevant.
- **Fields:** Overall `status`, warnings, errors, family results, parse status,
  incomplete count, dataset QA status, and missing/duplicate key counts.
- **Output example:** Completeness matrix by family with affected conclusions.
- **Interpretation caution:** Keep `SKIPPED_NOT_PRESENT`, `PROCESSED_EMPTY`, and
  incomplete FIT statuses distinct.
- **Not currently supported:** Repairing malformed source data during analysis.

## 12. Reproducibility verification

- **Purpose:** Confirm that identical input produced byte-identical Run-All
  output in separate new destinations.
- **Required files:** Both output trees and their `run_manifest.json` and
  `run_summary.json` files.
- **Fields:** Output paths, hashes, deterministic output digest, Run-All version,
  and completion status.
- **Output example:** Boolean byte-identical result plus compared version and
  status, without publishing private fingerprints.
- **Interpretation caution:** Compare files locally. Do not publish source or
  output hashes derived from personal data without a privacy decision.
- **Not currently supported:** Reproducible generative prose or equivalence
  across different input exports.

## 13. Future export-difference comparison

- **Purpose:** Compare two separately authorized Garmin exports to identify
  added, removed, or changed normalized records.
- **Required files:** Future contract; likely two manifests and normalized
  datasets with compatible schema versions.
- **Fields:** Stable keys, record digests, dataset grains, and export version
  metadata.
- **Output example:** Counts of added, removed, unchanged, and changed records.
- **Interpretation caution:** Export coverage and deletion semantics must be
  defined before a difference is interpreted.
- **Not currently supported:** Run-All v1 has no diff command, lifecycle merge
  contract, or public comparison artifact. This is a future concept only.

## Handoff rule

Use the minimum files needed for one question and follow
[`analysis_handoff_spec_v0_1.md`](analysis_handoff_spec_v0_1.md). Any result that
depends on missing, skipped, or partial input must say so explicitly.
