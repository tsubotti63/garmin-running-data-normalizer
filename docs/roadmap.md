# Roadmap

## Bootstrap — complete

- Independent repository and task model.
- Public/private classification and migration plan.
- Privacy, dependency, license, sample, and public-readiness policies.
- Synthetic fixture and bootstrap validation.

## Milestone 1 — Garmin intake

- Export-as-is discovery.
- Input inventory and content hashes.
- Safe ZIP/FIT traversal and dataset registry.

## Milestone 2 — deterministic normalization

- Activities, gear, records, and FIT session normalization.
- Stable-key and merge-policy contracts.
- Provenance and deterministic QA.

## Milestone 3 — orchestration and packaging

- One phase-independent Run-All command.
- Optional Open-Meteo adapter with attribution and use-tier configuration.
- Analysis Pack ZIP and reproducibility validation.

## Milestone 4 — versioned release readiness — complete

- Rights for predecessor-derived responsibilities included in `v1.0.0` were
  Human-confirmed; future material still requires review. Complete any required
  third-party notices.
- Complete dependency lock review, security/privacy checks, documentation, and
  release-specific review evidence.
- `v1.0.0` remains the first stable release. At v1.2.0 release preparation,
  `v1.1.1` remains the current stable
  GitHub Release and Production PyPI version. Any future tag, GitHub Release,
  stable release, or package publication requires its own current review and
  separate Human authorization.

## Milestone 5 — v1.2 Snapshot Accumulation — release prepared

- Preserve complete Garmin Exports as immutable account-bounded observations.
- Build deterministic cumulative approved input with
  `missing_is_not_delete`, explicit review holds, and no automatic deletion.
- Reparse cumulative unique FIT content and regenerate reviewed relationships.
- Public behavior is validated with synthetic fixtures. Public-safe aggregate
  evidence from four separately supplied private/local Snapshots confirms the
  required cumulative behavior without adding private evidence to Git.
- Keep the v1.1.1 one-shot CLI and output contract compatible.
- Complete Unit Review, Target Core Review, and Green CI before publication;
  TestPyPI verification, stable release publication, and Production PyPI
  verification remain separately observed release steps.
