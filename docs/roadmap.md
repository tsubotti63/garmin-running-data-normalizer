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
- `v1.0.0` remains the first stable release. `v1.3.0` is the current stable
  GitHub Release and Production PyPI version. Any future tag, GitHub Release,
  stable release, or package publication requires its own current review and
  separate Human authorization.

## Milestone 5 — v1.2 Snapshot Accumulation — complete

- Preserve complete Garmin Exports as immutable account-bounded observations.
- Build deterministic cumulative approved input with
  `missing_is_not_delete`, explicit review holds, and no automatic deletion.
- Reparse cumulative unique FIT content and regenerate reviewed relationships.
- Public behavior is validated with synthetic fixtures. Public-safe aggregate
  evidence from four separately supplied private/local Snapshots confirms the
  required cumulative behavior without adding private evidence to Git.
- Keep the v1.1.1 one-shot CLI and output contract compatible.
- Unit Review, Target Core Review, Green CI, TestPyPI verification, stable
  GitHub Release publication, and Production PyPI verification are complete.

## Milestone 6 — v1.3 Wellness / Metrics — complete

- Add ten optional normalized daily/observation datasets, expanding Run-All to
  17 normalized datasets without changing existing IDs or stable keys.
- Carry each new dataset through schema, registry, Snapshot, deterministic QA,
  Output Experience, and relationship documentation.
- Keep Wellness/Metrics separate from Activity facts; preserve the six existing
  explicit relationships and use same-day context only where documented.
- Keep Lactate Threshold candidate/audit-only and defer Health Status.
- Published version `1.3.0` directly as the next stable release after its
  separate merge, tag, GitHub Release, Production PyPI, and verification gates.
- Close additional v1.3 feature work and hand future Integrity / Evidence
  Foundation planning to the v1.4 candidate phase without starting
  implementation.
