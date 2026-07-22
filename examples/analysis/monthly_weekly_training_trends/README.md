# Monthly and Weekly Training Trends

## Purpose

Demonstrate reproducible calendar aggregation from the reduced Run-All
Activities CSV without exposing stable keys or personal data.

## Intended question

How do activity frequency, total distance, and total duration differ by month
and ISO week in the supplied sample?

## Data and columns

- File: `input_sample.csv`
- Grain: one synthetic activity per row
- Columns: `activity_date_local`, `activity_type`, `sport_type`, `distance_m`,
  `duration_sec`, `avg_hr`, `activity_training_load`
- Deliberately omitted: `garmin_activity_key`, raw IDs, paths, hashes, exact
  real-world dates, coordinates, and memo text

## Run method

Supply `input_sample.csv` and [`prompt.md`](prompt.md) to a trusted analysis
tool, or reproduce the calculations with any CSV-capable local tool:

- month = first seven characters of `activity_date_local`;
- ISO week = the ISO calendar year and week for the date;
- distance km = sum of `distance_m` divided by 1,000;
- duration hours = sum of `duration_sec` divided by 3,600;
- missing coverage = non-blank count divided by row count.

## Prompt and result

The reusable request is in [`prompt.md`](prompt.md). The reviewed expected
analysis is in [`result.md`](result.md).

## Reading the output

`Observed Facts` contains calculations. `Interpretation` describes only the
visible pattern. `Uncertainty` and `Unsupported Conclusions` prevent the sample
from being treated as coaching, health, or causal evidence.

## Facts

The sample contains eight rows, two represented months, complete distance and
duration, and one missing value in each of two optional metrics.

## Interpretation

The example can show a frequency-stable but volume-higher second month. It
cannot explain the change.

## What cannot be decided

Fitness, fatigue, training quality, data completeness, and an appropriate next
training decision cannot be determined from these columns alone.

## Privacy

All values and future dates are fictional. Do not replace the sample with real
Run-All rows in a public copy. A real CSV must remain local, and any external
derivative must remove `garmin_activity_key` and review date granularity.

## Reproduction

Use the same input, formulas, grouping rules, and prompt sections. Calculated
tables should match; generative wording may vary and is not byte-deterministic.

See the project-wide
[`Analysis Handoff Specification`](../../../docs/project/analysis_handoff_spec_v0_1.md).
