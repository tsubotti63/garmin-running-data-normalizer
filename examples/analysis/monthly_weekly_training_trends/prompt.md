# Reusable Prompt — Monthly and Weekly Training Trends

Analyze the supplied synthetic activity CSV under these rules:

1. Use only the supplied rows.
2. Group by calendar month and ISO calendar week.
3. Calculate activity count, total distance in kilometres, and total duration in
   hours. For heart rate and training load, report observed and missing counts;
   do not impute blanks.
4. Separate calculations from interpretation.
5. Do not infer fitness, intent, fatigue, health, or causality.
6. Do not output identifiers; none are supplied.

Return exactly:

## Evidence Received
## Observed Facts
## Interpretation
## Uncertainty
## Unsupported Conclusions
## Possible Next Questions

For every aggregate, state its denominator and missing-value count. Treat the
2030 dates and all values as deliberately fictional synthetic examples.
