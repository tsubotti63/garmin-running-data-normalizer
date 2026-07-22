# Garmin Running Data Normalizer

Garmin Running Data Normalizer is a local-first Python project for discovering
an unmodified Garmin Account Export and producing deterministic,
provenance-rich Garmin records without sending the export to a hosted service.

## Current status

The source repository is public and maintained on `main`. The latest published
prerelease is [`v0.1.0-rc.2`](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v0.1.0-rc.2)
(Python package version `0.1.0rc2`). It is not a stable release, and no PyPI
distribution has been published.

The formal CLI supports the existing activities-only Golden Path and a minimum
multi-family Run-All workflow. Run-All requires Activities and processes Gear,
Personal Records, and bounded FIT sessions/laps when those families are
present. Public reproduction uses synthetic fixtures. A private real-export
validation completed with status `PASS`, exit code 0, unchanged input, two
independent byte-identical outputs, and a public-safe privacy check; no private
rows, paths, identifiers, counts, or fingerprints are published.

This project is licensed under the [Apache License 2.0](LICENSE).

Unreleased migration work on `main` aligns FIT Activity/Lap metric mappings and
adds dependency-free library-level Sleep normalization from `sleepData.json`.
Sleep is not yet part of the formal CLI or Run-All public output contract.

## Supported datasets and interfaces

| Dataset or output | Implemented scope | Formal CLI support |
|---|---|---|
| Activities | `summarizedActivities.json` normalization with activity grain, `garmin_activity_key`, provenance, QA, and manifest | Yes |
| Gear and activity-gear links | `gear.json` normalizer | Run-All |
| Personal records | `personalRecord.json` normalizer | Run-All |
| FIT sessions and laps | Bounded, dependency-free parser; record coordinates and raw telemetry are not emitted | Run-All |
| Sleep | `sleepData.json` daily normalization with review states and provenance; no filling or inference | No; library level only |
| Analysis Pack | Deterministic ZIP builder from an explicit `.csv`/`.json`/`.md` allowlist | No |

The dataset registry documents stable keys, record grain, merge policy, and
provenance requirements. Gate 2 does not change those contracts.

## Try the synthetic Golden Path

No Garmin account or real export is required. After local installation, run the
bounded activities workflow with the visibly synthetic fixture:

```bash
python -m garmin_running_data_normalizer normalize-activities --input examples/synthetic/garmin_export --output workspace/golden-path
```

It creates deterministic normalized activities, a QA summary, and a provenance
manifest without modifying the input. Follow the complete copy-and-paste setup,
Golden Result comparison, repeat-run check, privacy guidance, and current
limitations in the [Product Quick Start](docs/product_quick_start.md).

## Run the minimum multi-family workflow

Use a new output directory for every run:

```bash
python -m garmin_running_data_normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all
```

The tracked fixture contains Activities only, so this tested example returns
`PASS_WITH_WARNINGS` with exit code 0 and records the absent optional families.
Run-All writes normalized JSON, FIT audit, deterministic Activities CSV,
dataset QA, a run manifest, and `run_summary.json` as its completion marker.
Exit code 2 is fatal; exit code 3 is an explicit `PARTIAL_SUCCESS` for auditable
incomplete FIT parsing. See the [Product Quick Start](docs/product_quick_start.md)
for the fixed output layout and privacy boundary.

## Why this project matters

Run-All creates a reviewable boundary between a complex local Garmin export and
downstream analysis: deterministic normalization, fixed output, QA and
provenance, explicit warnings, and a separate human-owned interpretation step.
See the [Primary Case Study](docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md).

## Analyze Run-All output

Review `run_summary.json` first. In a trusted local environment, start with
`analysis/activities.csv` and the
[Analysis Handoff Specification](docs/project/analysis_handoff_spec_v0_1.md).
The [prompt template](docs/project/analysis_prompt_template_v0_1.md),
[public usage example](docs/project/run_all_public_usage_example_v0_1.md), and
[use-case catalog](docs/project/run_all_use_case_catalog_v0_1.md) separate facts,
calculations, interpretation, and unknowns.

Three key-free synthetic examples are available:

- [Monthly and Weekly Training Trends](examples/analysis/monthly_weekly_training_trends/README.md)
- [Pace and Heart Rate Relationship](examples/analysis/pace_heart_rate_relationship/README.md)
- [Training Consistency and Return Pattern](examples/analysis/training_consistency_return_pattern/README.md)

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

- Run-All v1 requires `summarizedActivities.json`; Gear, Personal Records, and
  FIT are optional and detected using the existing exact filename rules.
- FIT support is limited to selected session and lap fields. Invalid sentinels
  for the migrated numeric metrics are converted to null before scaling;
  complete FIT CRC validation and multi-session identity are not implemented.
- Sleep normalization is library-level only. It does not perform FIT/JSON
  reconciliation, score recalculation, missing-day filling, day shifting, nap
  inference, activity joins, or Run-All integration.
- Open-Meteo, Parquet output, PyPI publication, and a stable product release
  are not implemented.
- The package does not guarantee a stable third-party Python API at this stage.

## Non-goals

Hosted processing, Garmin account authentication, JMA or Instagram ingestion,
wellness/coaching interpretation, personal analysis, and non-Garmin data
platform generalization are outside the project scope.

See the [Product Change History](docs/product_changelog.md) for factual product
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

Start with [`docs/README.md`](docs/README.md).
