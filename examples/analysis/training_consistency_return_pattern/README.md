# Training Consistency and Return Pattern

## Purpose

Demonstrate decision support that organizes normalized evidence without making
a medical, coaching, or readiness decision.

## Intended question

What consistency and lower-volume return pattern is visible, and which options
could a human review without the analysis choosing for them?

## Data and columns

- File: `input_sample.csv`
- Grain: one fictional activity per row
- Columns: `activity_date_local`, `activity_type`, `distance_m`, `duration_sec`,
  `activity_training_load`
- Omitted: identifiers, paths, exact real dates, subjective condition, health,
  sleep, fatigue, recovery, and injury information

## Run method

Use [`prompt.md`](prompt.md) with the CSV. Calculate consecutive date gaps and
compare the first and last three rows using the formulas named in the prompt.

## Prompt and result

The reusable request is [`prompt.md`](prompt.md). The reviewed expected response
is [`result.md`](result.md).

## Reading the output

`Observed Facts` is calculated evidence. `Decision-Support Options` lists
human-owned choices without ranking or selecting them.

## Facts

The sample has one longer represented gap and a lower-distance, lower-load
three-row segment afterward.

## Interpretation

The structure can support a review of gradual return options, but it cannot
determine cause, health, readiness, or safety.

## What cannot be decided

Injury risk, overtraining, recovery, a correct progression, and medical or
coaching action are outside the supplied evidence.

## Privacy

The data is deliberately fictional. Never publish an actual activity timeline
or combine it with health context without explicit data-owner authorization.

## Reproduction

Use the same row order, date-gap calculation, segment definitions, and mean
formulas. Calculated values should match; narrative wording may vary.

See the project-wide
[`Analysis Handoff Specification`](../../../docs/project/analysis_handoff_spec_v0_1.md).
