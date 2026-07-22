# Analysis Prompt Template v0.1

Use this template only with files the data owner has approved for the selected
analysis environment. Replace bracketed fields before use. Delete any optional
section that is not needed.

```text
You are analyzing local output from Garmin Running Data Normalizer Run-All v1.

Authorized question:
[State one descriptive analysis question.]

Authorized files:
- analysis/activities.csv
- run_summary.json
[Add the smallest necessary optional file, or write "none".]

Run state:
- Status: [PASS | PASS_WITH_WARNINGS | PARTIAL_SUCCESS]
- Relevant warning codes: [codes or "none"]
- Affected dataset families: [families or "none"]

Analysis rules:
1. Treat the supplied files as the complete evidence for this answer.
2. Separate source facts, calculated results, interpretations, and unknowns.
3. Do not infer or impute missing values. Blank is not zero.
4. For every aggregate, report its denominator and missing-value count.
5. Do not expose raw IDs, stable keys, paths, filenames, hashes, memo text,
   coordinates, or other personal identifiers.
6. Do not make medical, coaching, diagnostic, or causal claims.
7. Do not assign meaning or units that are not defined by the handoff spec.
8. Treat anomaly candidates as items for review, not confirmed problems.
9. If a warning or PARTIAL_SUCCESS affects a result, label that result partial.
10. If the evidence cannot answer the question, say so and name the minimum
    additional approved field or file required. Do not invent an answer.

Requested aggregation:
- Population: [for example, all supplied synthetic activities]
- Date range: [range or "all available rows"]
- Grouping: [for example, calendar month and activity_type]
- Metrics: [explicit columns and formulas]
- Missing-value policy: exclude missing values per metric and report counts

Return exactly these sections:

## Evidence Received
- Files used
- Run status and relevant warnings
- Rows included and excluded, without identifiers

## Factual Aggregates
- Tables or bullets containing calculated values only
- Denominator and missing-value count for each metric

## Trends
- Descriptive changes over the requested groups
- No causal explanation

## Anomaly Candidates
- Candidate pattern
- Calculation that triggered it
- Why it requires human review

## Interpretation
- Clearly labeled, conservative interpretations supported by the aggregates
- No new facts

## Limitations and Unknowns
- Missing fields, partial families, semantic limitations, and unsupported asks

## Additional Confirmation Needed
- "None" or the smallest additional approved input required
```

## Usage notes

- For public demonstrations, use the repository's visibly synthetic fixture or
  a separately reviewed anonymous aggregate. Do not paste real Run-All output.
- For a trusted local AI, `activities.csv` and `run_summary.json` are the normal
  minimum. Add normalized JSON, QA, manifest, or audit files only when the
  question requires them.
- For an external AI, do not send the unmodified CSV. Use an approved derivative
  with `garmin_activity_key` removed and date/time granularity reviewed.
- `run_manifest.json` is verification evidence and can contain source-relative
  provenance. It is not a default analysis upload.
- Preserve the completed prompt with the calculation output when reproducible
  analysis evidence is required.
