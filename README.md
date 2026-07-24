# Garmin Running Data Normalizer

Garmin Running Data Normalizer is a local-first Python project for discovering
an unmodified Garmin Account Export and producing deterministic,
provenance-rich Garmin records without sending the export to a hosted service.

## Current status

The source repository is public and maintained on `main`. Version `1.1.1` is
the Human-approved stable Production package candidate. It carries the reviewed
v1.1 FIT integrity, relationship QA, and standalone Output Experience while
preserving existing `1.x` CLI and output paths. The existing `v1.1.0` tag and
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.1.0)
remain immutable; their tagged source declares `1.1.0rc1`, and those TestPyPI
artifacts are not reused as stable Production artifacts. The `v1.1.1` tag,
GitHub Release, TestPyPI upload, and Production PyPI upload remain separate
Human Approval Boundaries.

The formal CLI supports the existing activities-only Golden Path and a minimum
multi-family Run-All workflow. Run-All requires Activities and processes Gear,
Personal Records, and bounded FIT sessions/laps when those families are
present. Public reproduction uses synthetic fixtures. A private real-export
validation completed with status `PASS`, exit code 0, unchanged input, two
independent byte-identical outputs, and a public-safe privacy check; no private
rows, paths, identifiers, dates, filenames, hashes, or fingerprints are
published. Only public-safe aggregate relationship acceptance counts are
reported.

This project is licensed under the
[Apache License 2.0](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/LICENSE).

The `1.0.0` scope aligns FIT Activity/Lap metric mappings and adds
dependency-free library-level Sleep, HRV, and Health Status normalization.
HRV uses the bounded FIT Message 370 candidate and keeps `healthStatusData`
comparison as validation evidence only. Health Status emits complete long and
fixed daily schemas without dynamic columns. These families are not yet part of
the formal CLI or Run-All public output contract.

## Supported datasets and interfaces

| Dataset or output | Implemented scope | Formal CLI support |
|---|---|---|
| Activities | `summarizedActivities.json` normalization with activity grain, `garmin_activity_key`, provenance, QA, and manifest | Yes |
| Gear and activity-gear links | `gear.json` normalizer | Run-All |
| Personal records | `personalRecord.json` normalizer | Run-All |
| FIT sessions and laps | CRC-validated multi-session parser with `fit_session_key` and `fit_lap_key`; record coordinates and raw telemetry are not emitted | Run-All |
| Activity/FIT links | Auditable evidence-qualified links with exclusions and relationship QA | Run-All |
| Sleep | `sleepData.json` daily normalization with review states and provenance; no filling or inference | No; library level only |
| HRV | FIT Message 370 / Field 1 daily candidate with invalid-sentinel handling and non-promotional JSON consistency evidence | No; library level only |
| Health Status | Exact-suffix `healthStatusData.json` long metrics and fixed daily schema with explicit dedupe/review evidence | No; library level only |
| Analysis Pack | Deterministic allowlist-only ZIP; optional external-safe profile is limited to month-level activity volume/count and removes identifiers, provenance, exact timestamps, and unneeded health/performance detail | Run-All opt-in |

The dataset registry documents stable keys, record grain, merge policy, and
provenance requirements. See the
[Supported Datasets](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/supported_datasets.md)
for the stable CLI/output boundary and library-level scope.

## Install

Garmin Running Data Normalizer requires Python 3.11 or later:

Production PyPI publication has not yet been performed. Until the `v1.1.1` tag
and package-index release are separately authorized, install the earlier
reviewed stable tag from a checkout:

```bash
git clone --branch v1.0.0 --depth 1 \
  https://github.com/tsubotti63/garmin-running-data-normalizer.git
cd garmin-running-data-normalizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m garmin_running_data_normalizer --version
```

The equivalent installed console command is `garmin-running-data-normalizer`.
The project has no third-party runtime package dependency.

After a separate PyPI publication is completed, the canonical index install
command will be:

```bash
python -m pip install garmin-running-data-normalizer
```

Maintainers can reproduce the packaging gate without uploading anything:

```bash
python -m pip install -e '.[test,release]'
python -m build
python -m twine check --strict dist/*
```

## Try the synthetic Golden Path

No Garmin account or real export is required. After local installation, run the
bounded activities workflow with the visibly synthetic fixture:

```bash
python -m garmin_running_data_normalizer normalize-activities --input examples/synthetic/garmin_export --output workspace/golden-path
```

It creates deterministic normalized activities, a QA summary, and a provenance
manifest without modifying the input. Follow the complete copy-and-paste setup,
Golden Result comparison, repeat-run check, privacy guidance, and current
limitations in the
[Product Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_quick_start.md).

## Run the minimum multi-family workflow

Use a new output directory for every run:

```bash
python -m garmin_running_data_normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all
```

The tracked fixture contains Activities only, so this tested example returns
`PASS_WITH_WARNINGS` with exit code 0 and records the absent optional families.
Run-All writes normalized JSON, FIT and relationship audit, deterministic
Activities CSV, dataset and relationship QA, three human-readable handoff
documents, machine-readable analysis/schema context, a run manifest, and
`run_summary.json` as its completion marker. `START_HERE.md`,
`ANALYSIS_HANDOFF.md`, and `ANALYSIS_CONTEXT.json` report coverage for every
explicit relationship without hiding unresolved, ambiguous, or duplicate
records; detailed evidence remains in relationship QA and audit artifacts.
Exit code 2 is fatal; exit code 3 is an explicit `PARTIAL_SUCCESS` for auditable
incomplete FIT parsing. See the
[Product Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_quick_start.md)
for the additive v1.1 output layout and privacy boundary. Add
`--external-safe-pack` to create a deterministic reviewable ZIP; Run-All never
uploads it.

Full normalized JSON and audit output use the `local_trusted_full` privacy mode.
They can retain memo text and source-relative Garmin filenames, including
email-shaped personal identifiers. Keep them local; the optional external-safe
pack removes those fields.

## Why this project matters

Run-All creates a reviewable boundary between a complex local Garmin export and
downstream analysis: deterministic normalization, fixed output, QA and
provenance, explicit warnings, and a separate human-owned interpretation step.
See the
[Primary Case Study](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md).

## Analyze Run-All output

Review generated `START_HERE.md` first. In a trusted local environment, follow
`DATASET_INVENTORY.md` and `ANALYSIS_HANDOFF.md`, then start with
`analysis/activities.csv` and the
[Analysis Handoff Specification](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/project/analysis_handoff_spec_v0_1.md).
The [Run-All Output Contract](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/output_contract.md),
[Dataset Catalog](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/supported_datasets.md),
and [Dataset Relationship Catalog](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/dataset_relationships.md)
explain artifact authority, dataset roles, and the explicit v1.1 joins.
The [prompt template](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/docs/project/analysis_prompt_template_v0_1.md),
[public usage example](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/docs/project/run_all_public_usage_example_v0_1.md), and
[use-case catalog](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/docs/project/run_all_use_case_catalog_v0_1.md) separate facts,
calculations, interpretation, and unknowns.

Three key-free synthetic examples are available:

- [Monthly and Weekly Training Trends](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/examples/analysis/monthly_weekly_training_trends/README.md)
- [Pace and Heart Rate Relationship](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/examples/analysis/pace_heart_rate_relationship/README.md)
- [Training Consistency and Return Pattern](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/examples/analysis/training_consistency_return_pattern/README.md)

Calculated facts are reproducible; generative wording is not claimed to be
byte-identical. The current `garmin_activity_key` may incorporate a source
activity ID. Keep real CSV local, remove that key from any externally shared
derivative, and review exact date/time granularity before transfer.

## Local verification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/validate_bootstrap.py
python3 scripts/static_policy_scan.py
python3 scripts/validate_platform_alignment.py
python3 scripts/validate_public_history.py --ci
```

The public-history command assumes a normal public clone whose `origin/HEAD`
points to `origin/main`. The no-argument mode is intentionally reserved for the
historical pre-registration checkout contract.

Only synthetic fixtures may be committed. Real Garmin exports and generated
personal output belong in ignored local directories.

## Activities Golden Path guarantees

- The documented Golden Path produces byte-identical JSON for identical input.
- Input is read-only; output must be absent or empty and is never silently
  overwritten.
- ZIP input is validated for traversal, links, encryption, entry count, size,
  total size, and compression-ratio limits.
- Stable keys, activity record grain, source-relative provenance, hashes, and
  deterministic QA are included in the reviewed output contract.
- Unsupported or unsafe Golden Path input fails closed with a non-zero exit
  status.

## Known limitations

Run-All v1 requires Activities; Gear, Personal Records, and FIT are optional.
Sleep, HRV, and Health Status are library-level interfaces and are not Run-All
outputs. Hosted processing, Open-Meteo, Parquet, automatic upload, and
Production PyPI publication are not included. The
documented CLI and versioned Run-All output contract are the stable `1.x`
interface; other Python modules may evolve compatibly as their contracts mature.
See
[Known Limitations](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/known_limitations.md)
for the precise boundaries.

## Non-goals

Hosted processing, Garmin account authentication, JMA or Instagram ingestion,
wellness/coaching interpretation, personal analysis, and non-Garmin data
platform generalization are outside the project scope.

See the
[Product Change History](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_changelog.md)
for factual product
changes. The root `CHANGELOG.md` is the byte-locked change log of the adopted AI
Collaboration Platform v0.9 Standard, not a Garmin product release history.

## Project map

- `docs/project_os/`: unmodified AI Collaboration Platform v0.9 Standard
- `docs/project/`: Project Customization and current phase controls
- `docs/proofs/`: Platform capability evidence
- `docs/reference/`: reuse, privacy, licensing, release, and handoff references
- `templates/`: unmodified Platform project/operation templates
- `runtime/`: unmodified Platform runtime plus Target Runtime Addendum
- `src/garmin_running_data_normalizer/`: public product implementation
- `tests/`: synthetic, dependency-free unit tests
- `packages/`: tracked package policy; review packs are generated under ignored
  `.review/`

Start with
[`docs/README.md`](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.0.0/docs/README.md).
