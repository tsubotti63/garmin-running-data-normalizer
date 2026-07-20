# Product Change History

This file records factual Garmin Running Data Normalizer product changes. The
root `CHANGELOG.md` belongs to the byte-locked AI Collaboration Platform v0.9
Standard adopted by this repository.

## v0.1.0-rc.1 — prerelease

- Provides a documented activities-only command that reads a local synthetic
  Garmin-shaped export and writes deterministic normalized activities, QA, and
  provenance manifest JSON.
- Includes a wholly synthetic Golden Result and repeat-run byte comparison.
- Includes fail-closed coverage for unsafe archives, symbolic links, invalid or
  insufficient input, non-empty output, empty normalization results, and
  provenance divergence.
- Documents the implemented library-level Garmin dataset support, current
  limitations, privacy boundary, and non-goals.
- Verifies the candidate with automated tests, deterministic QA, provenance and
  digest checks, repository validators, and GitHub Actions.

This is a Release Candidate with limited dataset and FIT coverage. It is not a
stable release, a complete Run-All workflow, or a PyPI publication.
