# Result — Pace and Heart Rate Relationship

## Evidence Received

- Six synthetic activity-grain rows.
- Distance and duration are present and positive in all six rows.
- Average heart rate is present in five rows and missing in one.
- One row is labeled `trail_running`; the others are labeled `running`.

## Observed Facts

Derived paces are 6.00, 5.50, 6.00, 7.00, 5.50, and 6.25 minutes per kilometre.
Five rows have paired pace and average heart rate:

| Activity type | Pace | Average HR |
|---|---:|---:|
| running | 6.00 min/km | 140 |
| running | 5.50 min/km | 148 |
| running | 6.00 min/km | 150 |
| trail_running | 7.00 min/km | 152 |
| running | 6.25 min/km | 155 |

Heart-rate coverage is 5/6, with one missing value. The fastest represented
pace with heart rate is 5.50 min/km at 148. The highest represented average
heart rate is 155 at 6.25 min/km.

## Interpretation

The small sample does not show a simple rule in which faster pace always pairs
with higher average heart rate. The trail-labeled row also has context that is
not comparable to the other labels without more information.

## Uncertainty

No elevation, weather, sensor quality, route, recovery, or perceived effort is
provided. One heart-rate value is missing. Six rows are insufficient for a
reliable relationship model.

## Unsupported Conclusions

- A physiological response curve or heart-rate zone.
- Improved or reduced fitness.
- Why any heart-rate value differs.
- Medical, coaching, or safety advice.

## Possible Next Questions

- Does the descriptive pairing change after separating activity types?
- How much heart-rate coverage is available in a larger synthetic sample?
- Which additional approved context would be needed before comparison?
