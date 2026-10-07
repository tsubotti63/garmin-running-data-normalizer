# Migration Notes

## v1.4.1 to v1.5.0

v1.5.0 does not require data migration. Existing Snapshot Stores load and
verify as before, and one-shot Run-All output from the same Export changes only
in `product_version` and the digests that include it. Rerun Run-All after
upgrading.

| Contract | v1.5.0 position |
|---|---|
| CLI and Python imports | Unchanged |
| Datasets, schemas, and stable keys | Unchanged; 17 datasets and 212 fields |
| Output paths | Unchanged |
| Exit codes | Unchanged `0 / 0 / 3 / 2` Product mapping |
| Snapshot lifecycle contract and policy registry | Unchanged `v1.0`; existing Stores need no migration |
| Relationships and privacy boundary | Unchanged |

What can change:

- New Snapshot Stores and new `normalize-activities` output directories are
  owner-only on Unix-like systems. Stores created by earlier versions keep
  their permissions; tighten one with `chmod -R go-rwx <store>`. Windows
  ignores these modes, so rely on the folder's access control there.
- A ZIP that contains `Thumbs.db` receives a different Snapshot content
  identity when registered with v1.5.0. Do not re-register Exports already
  registered with an earlier version: the original label fails, and a new
  label adds another Snapshot.
- Snapshot Sleep keeps every Sleep field that Run-All reads. A Store whose
  Exports differ for one `calendarDate` only in the added fields
  (`durationInSeconds`, `sleepDuration`, the snake_case stage fields,
  `overallScore`, and `sleepScore`) now stops `snapshot build-input` and
  `snapshot run-all`, and the error reports
  `sleep_daily same_stable_key_different_public_value=<count>`.
- The Snapshot stop-conflict and lock errors keep their previous opening text
  and add counts or recovery guidance.

Upgrade the package in a new or existing Python 3.11+ environment:

```bash
python -m pip install --upgrade garmin-running-data-normalizer==1.5.0
python -m garmin_running_data_normalizer --version
```

Use a new output directory when rerunning with v1.5.0. An output produced by
v1.4.0 or v1.4.1 contains `diagnostics/`, so `validate-handoff`,
`doctor --run-output`, and `support-bundle` from v1.5.0 reject it; rerun
Run-All instead. See
[Known Limitations](known_limitations.md#snapshot-lifecycle) and the
[v1.5.0 Release Notes](release_notes/v1.5.0.md).

## v1.4.0 to v1.4.1

v1.4.1 is a patch release. It does not require data migration, but Run-All
output from the same Export can change, so rerun Run-All after upgrading.

| Contract | v1.4.1 position |
|---|---|
| CLI and Python imports | Unchanged |
| Datasets, schemas, and stable keys | Unchanged; 17 datasets and 212 fields |
| Output paths | Unchanged |
| Exit codes | Unchanged `0 / 0 / 3 / 2` Product mapping |
| Snapshot policies | Unchanged, including ZIP member selection, content identities, and re-registration |
| Relationships and privacy boundary | Unchanged |

What can change for the same Export:

- FIT session `sport` and `sub_sport` now use FIT profile names. Sport code 10
  is `training` rather than `strength_training`; filter strength sessions by
  `sub_sport` `strength_training`. Sub-sport code 0 is `generic` rather than
  null.
- Activity/FIT links can increase where a FIT session's sport was misnamed.
- `hrv_daily` can lose days from FIT files that fail the container checks, and
  the HRV audit can report `bad_file_crc`, `bad_header_crc`,
  `unsupported_chained`, or `truncated`.
- Operating-system metadata files in an Export folder are ignored, so a run that
  previously failed or ended as `PARTIAL_SUCCESS` because of AppleDouble files
  can now complete.

Upgrade the package in a new or existing Python 3.11+ environment:

```bash
python -m pip install --upgrade garmin-running-data-normalizer==1.4.1
python -m garmin_running_data_normalizer --version
```

Use a new output directory when rerunning with v1.4.1. An output produced by
v1.4.0 contains `diagnostics/`, so `validate-handoff`, `doctor --run-output`,
and `support-bundle` from v1.4.1 reject it; rerun Run-All instead. See
[Known Limitations](known_limitations.md#diagnostics-and-handoff-validation)
and the [v1.4.1 Release Notes](release_notes/v1.4.1.md).

## v1.3.3 to v1.4.0

v1.4.0 adds read-only Export evidence and diagnostics. It does not require data
migration and does not change normalized output semantics.

| Contract | v1.4.0 position |
|---|---|
| CLI and Python imports | Additive `doctor` and `support-bundle` commands |
| Datasets, schemas, and stable keys | Unchanged; 17 datasets and 212 fields |
| Output paths | Additive `diagnostics/source_completeness.json` and `diagnostics/run_quality.json`; the synthetic Run-All output grows from 44 to 46 files |
| Exit codes | Unchanged `0 / 0 / 3 / 2` Product mapping |
| Snapshot policies | Unchanged |
| Relationships and privacy boundary | Unchanged; the Support Bundle is local-only and requires Human review |

Upgrade the package in a new or existing Python 3.11+ environment:

```bash
python -m pip install --upgrade garmin-running-data-normalizer==1.4.0
python -m garmin_running_data_normalizer --version
```

Existing v1.3.3 outputs remain valid evidence for their original package
version. Use a new output directory when rerunning with v1.4.0; deterministic
output includes exact product-version metadata, so cross-version bytes are not
expected to be identical. Check an output that contains `diagnostics/` with the
same package version that produced it, and rerun Run-All after a later upgrade;
see [Known Limitations](known_limitations.md#diagnostics-and-handoff-validation) and the
[v1.4 Export Evidence and Diagnostics](v1_4_diagnostics.md) guide.

## v1.3.2 to v1.3.3

v1.3.3 restores the Sleep duration contract. It does not require data
migration.

| Contract | v1.3.3 position |
|---|---|
| CLI and Python imports | Unchanged |
| Datasets, schemas, and stable keys | Unchanged; 17 datasets, 212 fields, and the `sleep_day` grain |
| Output paths and exit codes | Unchanged |
| Sleep duration | `sleep_duration_minutes_ex_awake` sums observed finite deep/light/REM stages; missing stages stay missing, and conflicting direct aliases fail closed |
| Daily-metric audits | Review-required counts are separated from excluded-record evidence |
| Snapshot policies, relationships, and privacy boundary | Unchanged |

Upgrade with `python -m pip install --upgrade garmin-running-data-normalizer==1.3.3`.
Exact output and semantic digests change for inputs whose Sleep duration is
restored, so rerun into a new output directory instead of comparing bytes with
v1.3.2 output.

## v1.3.1 to v1.3.2

v1.3.2 is a Snapshot correctness and evidence-preservation patch. It does not
require data migration.

| Contract | v1.3.2 position |
|---|---|
| CLI and Python imports | Unchanged |
| Datasets, schemas, and stable keys | Unchanged |
| Output paths and exit codes | Unchanged |
| Snapshot processing | Snapshot-aware relationship endpoint resolution; exact Sleep duplicates collapse with audit counts; Endurance/UDS observed variants and Lactate candidates are retained in audit evidence; chronology comes from `manifest.export_observed_at` |
| Relationships and privacy boundary | Contracts unchanged |

Upgrade with `python -m pip install --upgrade garmin-running-data-normalizer==1.3.2`.
Snapshot-based Run-All results can differ from v1.3.1 where these boundaries
apply, so rerun into a new output directory.

## v1.3.0 to v1.3.1

v1.3.1 is a documentation, public-surface, and validation patch. It does not
require data migration and does not change normalized output semantics.

| Contract | v1.3.1 position |
|---|---|
| CLI and Python imports | Unchanged |
| Datasets, schemas, and stable keys | Unchanged |
| Output paths and exit codes | Unchanged |
| Snapshot policies | Unchanged |
| Relationships and privacy boundary | Unchanged |
| Public documentation | Current stable state and Product-owned entry points aligned |
| Validation | Public Product State and ownership-alignment regression coverage added |

Upgrade the package in a new or existing Python 3.11+ environment:

```bash
python -m pip install --upgrade garmin-running-data-normalizer==1.3.1
python -m garmin_running_data_normalizer --version
```

Existing v1.3.0 outputs remain valid evidence for their original package
version. Use a new output directory when rerunning with v1.3.1; deterministic
output includes exact product-version metadata, so cross-version bytes are not
expected to be identical.

## v1.2.1 to v1.3.0

v1.3.0 is an additive dataset release. It does not require an in-place data
migration and does not overwrite existing output.

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
