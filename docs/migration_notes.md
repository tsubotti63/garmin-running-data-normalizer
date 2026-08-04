# Migration Notes

## v1.2.1 to v1.3.0

v1.3.0 is an additive dataset release. The prepared source does not require an
in-place data migration and does not overwrite existing output.

| Contract | v1.3.0 position |
|---|---|
| CLI | No command or argument removal/change |
| Output paths | Existing paths unchanged; new optional dataset/audit paths are additive |
| Existing datasets | IDs, record grain, schemas, and authority unchanged |
| Existing stable keys | Unchanged |
| Exit codes | Unchanged |
| Package imports | Existing imports unchanged |
| Relationships | Six existing explicit contracts unchanged |
| Privacy | Existing local/private boundary unchanged |

### New normalized datasets

Run-All can additionally emit Hill Score Daily, Endurance Score Daily, Race
Prediction, Sleep Daily, UDS Daily, Acute Training Load, Training Readiness,
VO2Max, HRV Daily, and Training History. These optional datasets are documented
in [Supported Datasets](supported_datasets.md). Lactate Threshold remains
candidate/audit-only, and Health Status remains deferred.

### New Output Experience

Generated human- and machine-readable handoff artifacts now document 17
normalized datasets. The new daily dataset JSON and audit files are additive.
`analysis/performance_metrics_daily.csv` is a derived convenience projection,
not a replacement Source of Truth.

### Snapshot compatibility

Existing Snapshot Stores retain the same account boundary, immutable evidence,
missing-is-not-delete policy, locking, recovery, and verification contracts.
After upgrading the package, verify the store and build a fresh canonical output
with the new parser/policies. Do not replace a previously reviewed output until
the new output passes validation. Missing optional families do not delete
previous observations.

### Repeat execution

Run-All still refuses to overwrite an existing output directory. Use a new
output path. Identical input and the same package version must produce the same
deterministic output; different package versions can legitimately change the
generated product-version metadata and add v1.3 artifacts.

### Rollback

Keep the v1.2.1 environment, previous verified output, and verified Snapshot
Store backup until v1.3.0 validation completes. Roll back by restoring that
environment/output and rerunning v1.2.1 against the retained input. Do not
delete or rewrite Snapshot evidence as part of rollback.

## Historical extraction strategy

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
