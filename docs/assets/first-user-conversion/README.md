# First-user Conversion Assets

These SVGs provide a compact, public-safe preview of the first product flow and
its outputs. Every asset is code-generated and explicitly labelled
`Synthetic / fictional data`.

## Assets

| Asset | Evidence source | Purpose |
|---|---|---|
| `product-flow.svg` | Product contract summary | Shows Export → Run-All → datasets/evidence → reusable analysis context, followed by bounded analysis and Human review |
| `synthetic-output-preview.svg` | Actual Run-All output generated from the tracked Synthetic fixture | Previews `START_HERE.md`, `DATASET_INVENTORY.md`, and `ANALYSIS_HANDOFF.md` |
| `synthetic-monthly-distance.svg` | `examples/analysis/monthly_weekly_training_trends/input_sample.csv` | Shows a bounded descriptive chart from fictional rows |

The source Synthetic Run-All completed with `PASS_WITH_WARNINGS`, exit code 0,
one detected/processed Activity and one Activity record, three warnings, zero
errors, 17 dataset inventory entries, and 46 generated files. Its deterministic
output digest was
`f67ac0787884b4df8bb25f578525176f64c1a1e0a3a9670df16f9b04403a27bb`.
A repeated run produced byte-identical output.

The tracked fictional chart input aggregates to:

- `2030-01`: 4 activities, 37.0 km;
- `2030-02`: 4 activities, 47.0 km.

These are product demonstration values, not observations about a person and not
evidence of training outcomes.

## Reproduce

Use a new output directory for Run-All:

```text
python -m garmin_running_data_normalizer run-all --input examples/synthetic/garmin_export --output workspace/first-user-conversion-run-all
python scripts/generate_first_user_conversion_assets.py --run-all-output workspace/first-user-conversion-run-all
```

The generator uses only the completed Synthetic Run-All handoff and the tracked
fictional analysis CSV. Re-running it from the same inputs produces identical
SVG bytes.

## Accessibility and safety

Each SVG includes a `title`, a detailed `desc`, `role="img"`, and
`aria-labelledby="title desc"`. Text and essential values remain in the SVG;
color is not the only carrier of meaning. The files contain no scripts,
`foreignObject`, external images, personal rows, private paths, identifiers, or
host metadata.
