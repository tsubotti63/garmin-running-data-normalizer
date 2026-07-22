# Pace and Heart Rate Relationship

## Purpose

Show how a transparent derived metric can be paired with an observed field
while keeping facts, interpretation, and unknown context separate.

## Intended question

What pace and average-heart-rate pairings are visible in this synthetic sample?

## Data and columns

- File: `input_sample.csv`
- Grain: one synthetic activity per row
- Columns: `activity_date_local`, `activity_type`, `distance_m`, `duration_sec`,
  `avg_hr`
- Derived field: minutes per kilometre from distance and duration
- Omitted: stable keys, raw IDs, paths, hashes, locations, and personal dates

## Run method

Use [`prompt.md`](prompt.md) with the CSV. Derive pace only with the formula
shown in the prompt and never divide by zero or fill missing heart rate.

## Prompt and result

The reusable request is [`prompt.md`](prompt.md). The reviewed expected response
is [`result.md`](result.md).

## Reading the output

The pace table is calculated evidence. The interpretation is deliberately
limited because activity type and unobserved context affect comparison.

## Facts

All six paces are derivable. Five rows have average heart rate; one does not.

## Interpretation

The visible pairs can organize a follow-up question, but they cannot establish
a physiological relationship.

## What cannot be decided

Correlation, causation, fitness, exertion, health, recovery, and training advice
are unsupported.

## Privacy

The dates and values are fictional. Do not publish real activity-level dates or
metrics. Use only a data-owner-approved, key-free derivative outside a trusted
local environment.

## Reproduction

Recalculate pace from the supplied values and use the same five-row heart-rate
denominator. Numeric facts should match even when prose varies.

See the project-wide
[`Analysis Handoff Specification`](../../../docs/project/analysis_handoff_spec_v0_1.md).
