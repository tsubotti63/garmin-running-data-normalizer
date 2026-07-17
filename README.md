# Garmin Running Data Normalizer

Bootstrap repository for a future public OSS tool that will normalize Garmin
Account Export data into documented, deterministic datasets.

## Current status

This repository is **bootstrap-only**. It contains project governance,
architecture, public/private boundaries, a synthetic example, and validation
scaffolding. Garmin parsing, normalization, Open-Meteo integration, Analysis
Pack export, and the final Run-All command are not implemented here yet.

## Intended user flow

1. Place an unmodified Garmin Account Export in a local input directory.
2. Run one documented command.
3. Inspect normalized data, provenance, deterministic QA, and an optional
   portable Analysis Pack.

Real exports and generated personal data must never be committed. See
[`docs/project_boundary.md`](docs/project_boundary.md) and
[`docs/security_and_privacy_boundary.md`](docs/security_and_privacy_boundary.md).

## Bootstrap validation

```bash
python3 scripts/validate_bootstrap.py
python3 -m pytest
```

## Documentation

- [Project Charter](docs/project_charter.md)
- [Project Boundary](docs/project_boundary.md)
- [Architecture Overview](docs/architecture_overview.md)
- [Roadmap](docs/roadmap.md)
- [Existing Asset Reuse Matrix](docs/existing_asset_reuse_matrix.md)
- [Migration Notes](docs/migration_notes.md)
- [Public Readiness Checklist](docs/github_public_readiness_checklist.md)

## License

No OSS license has been selected. No `LICENSE` file is included. Public release
and reuse of Source Project code remain blocked until the Human owner selects a
license and confirms the rights position. See
[`docs/dependency_license_inventory.md`](docs/dependency_license_inventory.md).

