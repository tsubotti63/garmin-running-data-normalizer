# Frequently Asked Questions

These short answers apply to Garmin Running Data Normalizer `v1.2.0` and route
to the current product authorities.

## Getting started

### What does this project do?

It turns a local Garmin Account Data Export into deterministic normalized
datasets, QA, audit evidence, provenance, explicit relationship boundaries,
and reusable analysis context. It is more than a file converter, but it does
not replace Human Review.

Start with the [README](../README.md) and
[Product Quick Start](product_quick_start.md).

### Can I try it without a Garmin Account or real data?

Yes. Use the tracked synthetic fixture in the
[Product Quick Start](product_quick_start.md). Public reproduction uses
synthetic data.

### Which version is stable?

`v1.2.0` is the current stable release on PyPI. It includes the compatible
one-shot workflow and optional Snapshot Accumulation.

## Garmin Export and Run-All

### Which Garmin export should I use?

Use a complete Garmin Account Data Export, not an individual Activity GPX or
TCX export. Follow
[Getting Started from a Garmin Export](getting_started_from_garmin_export.md).

### Can I pass the downloaded ZIP directly to `--input`?

No. Direct ZIP input is unsupported. Preserve the downloaded outer archive,
extract that outer ZIP into a dedicated directory, and pass the extracted
directory to `--input`. Validated inner ZIP assets may be discovered inside
that directory.

### Can the output path already exist or be inside the input?

No. Use a new output path outside the input directory. Run-All fails closed
instead of silently overwriting an existing result.

### What input is required?

Activities are required through a supported filename ending in
`summarizedActivities.json`. Gear, Personal Records, and FIT are optional.
See [Supported Datasets](supported_datasets.md).

### What happens when an optional family is absent?

The family can be recorded as `SKIPPED_NOT_PRESENT`. That means it was not
detected in the supplied input; it does not prove the account has never
contained that kind of data. `PROCESSED_EMPTY` is a different state.

### How do I know Run-All completed?

`<output>/run_summary.json` is the completion marker. Then read
`<output>/START_HERE.md`. A directory without `run_summary.json` is not a
completed handoff.

### What do the exit codes mean?

| Exit | Meaning |
|---:|---|
| `0` | `PASS` or `PASS_WITH_WARNINGS` |
| `2` | Fatal contract, input, QA, or publication error |
| `3` | `PARTIAL_SUCCESS` because detected FIT is auditably incomplete |

Review warnings and affected families before analysis. See the
[Output Contract](output_contract.md).

## Multiple Exports and Snapshot Accumulation

### Does one-shot Run-All combine multiple Export downloads?

No. It processes one supplied Export. Keep every original download until it
has been registered and verified if you adopt Snapshot Accumulation.

### Is the latest Export always complete?

No completeness guarantee is made. Missing from a later Export is not evidence
of deletion.

### Is Snapshot Accumulation stable?

Yes. It is an optional additive capability in `v1.2.0`. It preserves immutable
observations from repeated complete Exports within one account boundary and
builds a cumulative approved input before reusing Run-All.

Read the
[v1.2 Snapshot Migration Guide](project/v1_2_snapshot_migration_guide_v1_0.md).

### What missing/value states remain distinct?

The reviewed lifecycle keeps seven materially distinct states:

- absent;
- null;
- empty;
- malformed;
- unsupported;
- retained; and
- promoted.

They are not collapsed into generic “missing data.”

### What did the bounded Snapshot validation prove?

[CS-007](case_studies/cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md)
used four repeated complete Exports from one account, not four independent
datasets. Within that reviewed set and merge policy, 6/6 pairwise comparisons,
24/24 tested registration orders, and 13/13 specified failure/recovery checks
passed, with source mutation 0.

This is bounded evidence, not a universal recovery, statistical,
zero-defect, or external-adoption claim.

### Can I delete old Snapshot blobs?

No supported Snapshot/blob deletion or automatic garbage collection workflow
is provided. Do not manually edit or delete Store internals. Verify the Store
before backup and again after restore.

## AI-assisted analysis

### Does the product upload data to an AI provider?

No. Processing is local-first, and no Export, full output, or optional pack is
uploaded automatically.

### What does “AI-ready” mean?

The output provides context about dataset roles, grain, keys, relationships,
warnings, missing-value rules, and privacy boundaries. It does not guarantee
that an AI answer is correct.

Use the [AI Analysis Quick Start](ai_analysis_quick_start.md).

### Can missing values be treated as zero?

No.

```text
missing != zero
unresolved != error
coverage != success rate
```

Report denominators and missing counts, and use only explicit relationships in
the handoff. See [Dataset Relationships](dataset_relationships.md).

### What is the external-safe pack?

`--external-safe-pack` creates
`analysis/external_safe_handoff.zip` locally. It contains five allowlisted
files, including an Activities CSV with six columns and one Activity per row.
The date is reduced to month; the file is not pre-aggregated by month.

The pack reduces the exposed data surface but still requires Human Review of
the receiving provider, plan, workspace, and exact transfer.

### Can the pack answer heart-rate or FIT questions?

No. It excludes exact dates/times, identifiers, paths, hashes, memo text,
coordinates, heart rate, power, cadence, training effect/load, Gear, Personal
Records, FIT details, and Activity/FIT relationships.

### Does the product provide training or medical advice?

No. Medical diagnosis, injury assessment, fatigue/readiness conclusions,
coaching prescriptions, and causal claims are outside the product boundary.

## Platforms, privacy, and support

### Is Windows supported?

Windows is an intended supported platform and public validation is in progress.
One third-party Windows environment reproduced missing IANA timezone data on
stable v1.2.0. After manually installing `tzdata`, the tracked Synthetic
Run-All completed with `PASS_WITH_WARNINGS`, exit code 0, and Activities
detected=1 / processed=1. This single-environment result is not a claim that all
Windows versions are validated.

Public-safe Windows reports are welcome through
[Support](../SUPPORT.md).

### Why does stable v1.2.0 fail with `ACTIVITIES_NORMALIZATION_FAILED` on Windows?

Python may be unable to resolve the IANA `Asia/Tokyo` timezone because stable
v1.2.0 did not install timezone data on Windows. Confirm the cause inside the
same environment:

```powershell
python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Tokyo'))"
```

If this reports `ZoneInfoNotFoundError`, install the temporary workaround:

```powershell
python -m pip install tzdata
```

Then rerun normalization with a new output path. A patch release is being
prepared to install `tzdata` automatically on Windows and provide a bounded
`TIMEZONE_DATA_UNAVAILABLE` diagnostic. Until that patch is published, v1.2.0
remains the current stable release.

### Can I attach my Garmin Export to a GitHub Issue?

No. Do not attach a real Export, full output, real Activity rows, IDs or stable
keys, filenames, paths, hashes, exact dates, locations, or memo text.

Use the public bug form only for sanitized, reproducible, non-sensitive
reports. See [Support](../SUPPORT.md).

### Where are the detailed contracts?

- [Run-All Output Contract](output_contract.md)
- [Supported Datasets](supported_datasets.md)
- [Dataset Relationships](dataset_relationships.md)
- [Known Limitations](known_limitations.md)
- [Analysis Handoff Specification](project/analysis_handoff_spec_v0_1.md)
- [Snapshot Migration Guide](project/v1_2_snapshot_migration_guide_v1_0.md)
