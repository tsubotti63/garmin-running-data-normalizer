# Product Change History

This file records factual Garmin Running Data Normalizer product changes. It is
not a release note and does not claim that a versioned product release exists.
The root `CHANGELOG.md` belongs to the byte-locked AI Collaboration Platform
v0.9 Standard adopted by this repository.

## Unreleased

- Added a documented activities-only command that reads a local synthetic
  Garmin-shaped export and writes deterministic normalized activities, QA, and
  provenance manifest JSON.
- Added a wholly synthetic Golden Result and repeat-run byte comparison.
- Added fail-closed coverage for unsafe archives, symbolic links, invalid or
  insufficient input, non-empty output, empty normalization results, and
  provenance divergence.
- Documented the implemented library-level Garmin dataset support, current
  limitations, privacy boundary, and non-goals.

No tag, GitHub Release, PyPI distribution, or versioned product release is
represented by this Unreleased history.
