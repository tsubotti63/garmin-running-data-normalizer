# Migration Notes

## Extraction strategy

1. Preserve the private Source Project unchanged.
2. Use the reuse matrix and file-level evidence inventory to select one bounded
   Garmin responsibility at a time.
3. Confirm rights and target license compatibility before copying code.
4. Remove private paths, phase names, JMA, Instagram, personal analysis, and
   real-data dependencies.
5. Recreate tests with synthetic fixtures and compare behavior using aggregate,
   non-personal evidence only.
6. Admit code only after independent Target Project Core Review.

## Not migrated in bootstrap

Production code, private data, Git history, generated outputs, runtime evidence,
JMA, personal analysis, coaching logic, and Open-Meteo response data.

## Reproducibility

Historical Source reproduction remains a Source Project responsibility. The
Target must reproduce only its own public contracts from synthetic or
user-supplied local inputs.
