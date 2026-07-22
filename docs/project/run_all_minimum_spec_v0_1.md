# Minimum Run-All Specification v0.1

## Status and Scope

- Specification status: implementation-ready for M2
- Command contract version: `garmin-running-data-normalizer-run-all-v1`
- Applies to: the public `garmin-running-data-normalizer` Python package
- Data boundary: local Garmin Account Export input and local output only

This is the minimum specification required to implement and test a complete
Run-All path. Future dataset families and analysis features are not implied.

## Command and Entry Point

The single Run-All command is:

```bash
python -m garmin_running_data_normalizer run-all \
  --input <export-directory> \
  --output <new-output-directory>
```

Entry flow:

```text
garmin_running_data_normalizer.__main__
  -> runner.main()
  -> run-all subcommand
  -> run_all.run_all()
```

`normalize-activities` remains supported and byte-compatible. M2 must not
rename it or redirect it through Run-All.

### Required arguments

- `--input`: an existing, non-symlink directory containing an extracted Garmin
  export, one or more Garmin export ZIP files, or both.
- `--output`: a destination directory that does not yet exist and is outside
  the resolved input directory.

### Optional arguments

None in v1. Timezone behavior and archive limits retain their existing library
defaults. New switches require evidence from M3 rather than speculative design.

## Input Contract

### Directory and safety rules

1. Resolve input and output before processing.
2. Reject a missing/non-directory input, input symlink, output symlink, output
   inside input, or an existing output path.
3. Recursively discover regular files in deterministic relative-path order.
4. Read direct `.json` and `.fit` files and supported members from `.zip` files.
5. Apply existing archive traversal, link, encryption, count, size, expanded
   size, and compression-ratio guards before normalizing any archive content.
6. Never write, rename, delete, touch, or create a file under input.
7. Snapshot `(provenance_path, size_bytes, sha256)` at the beginning and compare
   it with a final discovery snapshot before publishing output. A difference is
   fatal.

The logical filename checks below are case-sensitive and use the complete
source-relative path or archive member path.

### Dataset family detection

| Input family | Detection | Requirement | Missing behavior |
|---|---|---|---|
| Activities | logical name ends with `summarizedActivities.json` | Required | `ERROR`; no published output |
| Gear / activity-gear | logical name ends with `gear.json` | Optional | `SKIPPED_NOT_PRESENT`; warning |
| Personal records | logical name ends with `personalRecord.json` | Optional | `SKIPPED_NOT_PRESENT`; warning |
| FIT | asset kind is `.fit` | Optional | `SKIPPED_NOT_PRESENT`; warning |

At least one Activities asset must produce at least one valid activity record.
The presence of FIT sessions does not substitute for the required Activities
family in v1.

## Processing Order

M2 must execute these steps in order:

1. Validate paths and create an initial discovery snapshot in memory.
2. Classify detected assets and reject missing required Activities.
3. Validate the in-package Run-All dataset table against the stable keys and
   record grains documented by the example registry. Normal execution must not
   require the repository-level `config/` path.
4. Normalize Activities.
5. Normalize Gear and activity-gear links when detected.
6. Normalize Personal Records when detected.
7. Parse FIT sessions and laps and retain the FIT audit when detected.
8. Run per-dataset key, duplicate, serializability, and deterministic-digest QA.
9. Build the stable Activities CSV.
10. Repeat discovery and fail if the input snapshot changed.
11. Serialize all output in an internal sibling staging directory.
12. Hash staged outputs and write the run manifest.
13. Write `run_summary.json` last.
14. Publish the staging directory as the requested destination only after all
    fatal checks pass.

Steps for absent optional families still create empty normalized JSON arrays and
record the skip reason. They do not invoke the corresponding normalizer.

## Dataset and QA Contract

The v1 dataset table is:

| Dataset | Record grain | Stable key | Required |
|---|---|---|---|
| `activities` | activity | `garmin_activity_key` | yes |
| `gear` | gear | `gear_key` | no |
| `activity_gear` | activity-gear link | `gear_key`, `activity_id` | no |
| `personal_records` | personal record | `personal_record_id` | no |
| `fit_sessions` | FIT file session | `fit_file_id` | no |
| `fit_laps` | FIT file lap | `fit_file_id`, `lap_index` | no |

Every non-empty dataset must be JSON serializable and have non-null stable keys.
Duplicate keys with divergent records, unresolved merge conflicts, or a
provenance mismatch are fatal. Deterministic record digests are recorded per
dataset.

## Warning, Error, and Partial-Success Boundary

### Non-fatal warning

- An optional family is not present.
- A present optional family is valid but contains zero recognized records.
- A FIT file is `parsed_non_activity` with no unknown-record stop.

These conditions are recorded with dataset/file counts. Optional-family absence
alone results in `PASS_WITH_WARNINGS` and exit code 0.

### Partial success

`PARTIAL_SUCCESS` is used only when:

- Activities completed and passed QA; and
- one or more detected FIT assets produced an auditable parse status such as
  `too_small`, `bad_header`, or `truncated`, or parsing stopped at one or more
  unknown records.

It must identify the affected family, processed count, skipped count, parse
statuses, and warning count. This applies even if every detected FIT file is
rejected and the FIT session output is empty. It returns exit code 3. A
completion summary exists because the partial output is deliberate and
reviewable.

### Fatal error

The following are always fatal:

- path or archive safety violation;
- required Activities missing or empty;
- malformed/undecodable detected JSON;
- exception from a detected JSON normalizer;
- missing/null stable key, divergent duplicate key, or failed QA;
- input snapshot change during processing;
- output destination exists or becomes occupied;
- serialization, staging, hashing, or publication failure.

Fatal errors return exit code 2 and must not publish the final destination or a
completion marker. Unexpected exceptions use the same privacy-safe CLI error
boundary and do not print record contents or host paths.

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | `PASS` or `PASS_WITH_WARNINGS`; all detected data completed without an incomplete detected family |
| `2` | `ERROR`; invalid command contract, unsafe input, required data loss, QA failure, or processing failure |
| `3` | `PARTIAL_SUCCESS`; required output is valid but a detected FIT family is explicitly incomplete or fully rejected with audit evidence |

Argparse usage errors retain argparse's exit code 2.

## Output Contract

The destination contains this fixed layout:

```text
<output>/
  normalized/
    activities.json
    gear.json
    activity_gear.json
    personal_records.json
    fit_sessions.json
    fit_laps.json
  audit/
    fit_audit.json
  analysis/
    activities.csv
  qa/
    dataset_summary.json
  run_manifest.json
  run_summary.json
```

All JSON is UTF-8, sorted-key, two-space indented, and newline terminated.
Records use the deterministic order already provided by each normalizer. Empty
optional datasets are serialized as `[]`.

### Activities CSV

`analysis/activities.csv` is UTF-8 with `\n` line endings and this fixed column
order:

1. `garmin_activity_key`
2. `activity_date_local`
3. `activity_datetime_local`
4. `activity_type`
5. `sport_type`
6. `distance_m`
7. `duration_sec`
8. `avg_hr`
9. `max_hr`
10. `avg_power`
11. `max_power`
12. `avg_run_cadence`
13. `training_effect_label`
14. `activity_training_load`
15. `lap_count`

Rows are ordered by `garmin_activity_key` and source-relative provenance before
the provenance columns are omitted. Raw memo text, Garmin activity IDs, source
paths, and hashes are not copied into the analysis CSV.

### Run manifest

`run_manifest.json` contains at minimum:

- `format`: `garmin-running-data-normalizer-run-manifest-v1`
- `run_all_version`: `1`
- `input_assets`: source-relative path, bytes, SHA-256, and detected family
- `datasets`: name, grain, stable key, source count, record count, and records
  digest
- `outputs`: relative path, bytes, and SHA-256 for every file except the
  manifest and completion summary
- `deterministic_output_digest`: digest over sorted output path/hash pairs

No absolute host path is permitted.

### Run summary and completion marker

`run_summary.json` is written last and is the only completion marker. Its
presence means the final output was deliberately published as PASS or partial
success. It contains at minimum:

- `format`: `garmin-running-data-normalizer-run-summary-v1`
- `run_all_version`: `1`
- `status`: `PASS`, `PASS_WITH_WARNINGS`, or `PARTIAL_SUCCESS`
- detected, processed, skipped, warning, and error counts by family
- total input asset count and normalized record count
- generated relative paths
- warning and error entries using bounded codes and safe messages
- manifest SHA-256

Wall-clock timestamps, elapsed time, hostnames, usernames, absolute paths, and
environment details are excluded from v1 deterministic output. M3 execution
evidence may record elapsed time outside this deterministic product dataset.

## Rerun, Overwrite, Backup, and Skip Policy

- Overwrite: never.
- Existing destination: fail before normalization, even if it is empty.
- Backup/retirement: not performed by Run-All.
- Rerun: choose a new destination. Identical input must produce byte-identical
  output.
- Input family skip: only an absent optional family is skipped automatically.
- Record skip: only FIT parser statuses already represented in `fit_audit.json`
  may be skipped; JSON normalizer errors are fatal.
- Staging cleanup: remove only the staging directory created by the current run
  after a handled failure. Never search broadly for or delete other paths.

## Console Log Contract

The CLI prints only:

- final status and exit meaning;
- dataset family names;
- bounded source/record/warning/error counts;
- generated relative output paths;
- deterministic digest; and
- safe error codes/messages.

It must not print record contents, activity/account IDs, memo text, coordinates,
credentials, email addresses, absolute input/output paths, usernames,
hostnames, environment variables, or raw exception representations.
Source-relative provenance remains in local JSON/manifest output only.

## Fixture and CI Privacy Contract

- Tests use visibly synthetic IDs, names, dates, metrics, and FIT bytes.
- No real Garmin export, generated personal output, coordinates, email,
  credential, cookie, token, or host path is committed.
- Temporary output is created outside tracked paths.
- CI runs the synthetic tests but does not upload normalized output as an
  artifact.
- Static policy and privacy assertions cover the new code, fixture strings,
  console output, summary, manifest, JSON, and CSV.

## M2 File Scope

Expected product changes:

- new `src/garmin_running_data_normalizer/run_all.py`
- modified `src/garmin_running_data_normalizer/runner.py`
- optional new `src/garmin_running_data_normalizer/common/paths.py` only for a
  behavior-preserving extraction of shared path validation
- new `tests/test_run_all.py`
- optional synthetic expected Run-All output under
  `examples/synthetic/expected/run_all/` if byte fixtures are used
- minimal tested-command updates to `README.md` and
  `docs/product_quick_start.md`

M2 must not change normalizer record shapes, Platform Standard files, license,
release state, CI artifact publication, or unrelated governance documents.

## M2 Acceptance Tests

1. All-family synthetic run returns 0, produces the fixed layout, has PASS QA,
   and leaves the input byte-identical.
2. Activities-only run returns 0 with `PASS_WITH_WARNINGS`, empty optional
   arrays, and explicit `SKIPPED_NOT_PRESENT` entries.
3. Missing Activities and every safety/JSON/QA violation return 2 with no final
   destination or summary marker.
4. A mixed valid/invalid FIT input returns 3 with `PARTIAL_SUCCESS`, exact audit
   counts, and valid required output.
5. Same-destination rerun returns 2 without changing the first output; a new
   destination is byte-identical.
6. Unit tests, pytest in the CI test environment, bootstrap validation, static
   policy, Platform alignment in a clean clone, and public-history validation
   pass.

## Risks and Deferred Items

- Filename aliases require real-export evidence and are deferred to M3.
- M7.1 implements invalid-sentinel handling for the selected migrated FIT
  Activity and FIT Lap numeric metrics. Complete FIT CRC validation and
  multi-session identity remain documented limitations.
- Parquet, automatic Analysis Pack ZIP, performance metrics, and real-data
  evidence are deferred.
- The example dataset registry lifecycle wording is not changed by M2.
- If the implementation cannot publish the staged directory without weakening
  the no-overwrite contract on a supported platform, it must fail closed and
  report the platform constraint rather than write in place.

## Decision Log

| Decision | Fixed v1 behavior |
|---|---|
| Command | `python -m garmin_running_data_normalizer run-all` |
| Required family | Activities |
| Optional families | Gear/activity-gear, Personal Records, FIT |
| Analysis format | Deterministic activities CSV |
| Existing output | Fatal; no overwrite, backup, or automatic skip |
| Optional absence | Warning with exit 0 |
| Incomplete detected FIT | `PARTIAL_SUCCESS` with exit 3 |
| Completion signal | `run_summary.json` written last |
| Privacy | Local-only detailed output; bounded console; synthetic-only CI |
| M2 review scope | Command behavior, output, non-destruction, privacy, and partial-success boundary only |
