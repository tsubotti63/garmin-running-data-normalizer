# Reusable Prompt — Pace and Heart Rate Relationship

Analyze the supplied synthetic activity CSV.

1. Derive pace only where `distance_m > 0` and `duration_sec` is present:
   `pace_min_per_km = duration_sec / 60 / (distance_m / 1000)`.
2. Report every derived pace with its activity type, but not a row identifier.
3. Report heart-rate coverage and missingness.
4. Describe visible pairings of pace and `avg_hr`; do not claim correlation,
   causation, exertion, fitness, or health from this small sample.
5. Keep trail and road-like labels distinct.

Return exactly:

## Evidence Received
## Observed Facts
## Interpretation
## Uncertainty
## Unsupported Conclusions
## Possible Next Questions

All dates and values are fictional synthetic examples. Missing heart rate must
remain missing.
