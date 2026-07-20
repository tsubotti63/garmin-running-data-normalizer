# Garmin Running Data Normalizer

Garmin Running Data Normalizer is a local-first Python project for discovering
an unmodified Garmin Account Export and producing deterministic,
provenance-rich Garmin records without sending the export to a hosted service.

## Current status

The source repository is public and maintained on `main`. No Git tag, GitHub
Release, PyPI distribution, or versioned product release has been issued.

The formal end-user command currently supports one activities-only Golden Path.
Additional Garmin normalizers and exporters are available as library
components, but they are not exposed through a combined end-user workflow.

This project is licensed under the [Apache License 2.0](LICENSE).

## Supported datasets and interfaces

| Dataset or output | Implemented scope | Formal CLI support |
|---|---|---|
| Activities | `summarizedActivities.json` normalization with activity grain, `garmin_activity_key`, provenance, QA, and manifest | Yes |
| Gear and activity-gear links | `gear.json` library normalizer | No |
| Personal records | `personalRecord.json` library normalizer | No |
| FIT sessions and laps | Bounded, dependency-free library parser; record coordinates and raw telemetry are not emitted | No |
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

- The formal CLI processes activities only; it is not a full Run-All workflow.
- The implementation has been validated with synthetic fixtures, not real
  Garmin Account Export data.
- FIT support is limited to selected session and lap fields. Complete FIT CRC
  and invalid-sentinel handling are not implemented.
- Open-Meteo, Parquet output, PyPI publication, and a versioned product release
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
