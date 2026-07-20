# Garmin Running Data Normalizer

Garmin Running Data Normalizer is an early-stage, local-first Python project for
discovering an unmodified Garmin Account Export and producing deterministic,
provenance-rich records from Garmin JSON and FIT files.

## Current status

The currently implemented bounded core includes safe export discovery, archive
filtering, activity/gear/personal record normalization, a dependency-free FIT
session/lap parser, stable identity, dataset-policy inspection, deterministic QA,
and an allowlist-only Analysis Pack builder. Open-Meteo, a final end-user Run-All
command, complete FIT CRC and invalid-sentinel handling, real-data validation,
and packaging remain future work.

This project is licensed under the [Apache License 2.0](LICENSE).

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
python3 scripts/validate_public_history.py
```

Only synthetic fixtures may be committed. Real Garmin exports and generated
personal output belong in ignored local directories.

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
