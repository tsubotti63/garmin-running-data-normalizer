# Synthetic example policy

Files in this directory must be fabricated and must not be derived from a real
Garmin account, activity identifier, coordinate, email address, or health
record.

`garmin_export/` is a hand-authored, visibly fictional Garmin-shaped directory
for the product Golden Path. It contains one running activity, uses a synthetic
identifier and a future example timestamp, and omits coordinates, identity,
device, and health fields. It is not anonymized or transformed real data.

`expected/golden_path/` contains the deterministic JSON files produced from
that fixture. Update those files only when an intentional fixture or output
contract change is reviewed together with the end-to-end test.
