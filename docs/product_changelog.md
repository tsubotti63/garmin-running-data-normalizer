# Product Change History

This file records factual Garmin Running Data Normalizer product changes. The
root `CHANGELOG.md` belongs to the byte-locked AI Collaboration Platform v0.9
Standard adopted by this repository.

## Unreleased — M7.1 FIT migration

- Aligns selected FIT Activity and FIT Lap field mappings with the authorized
  public migration source.
- Converts FIT invalid sentinels for migrated numeric metrics to null before
  applying scale factors.
- Extends synthetic unit and Run-All regression coverage for heart rate,
  cadence, power, ascent, stable identity, and lap provenance.
- Retains the existing safe discovery, content-derived FIT file identifiers,
  source-relative provenance, and exclusion of record coordinates and raw
  telemetry.

This work is unreleased. Complete FIT CRC validation and multi-session identity
remain migration gaps.

## v0.1.0-rc.2 — prerelease (2026-07-22)

- Adds the formal multi-family Run-All command with Activities required and
  optional Gear, Personal Records, and bounded FIT session/lap output.
- Raises the bounded archive member limit to support large legitimate Garmin
  exports while preserving fail-closed safety controls.
- Records public-safe private real-export completion evidence: unchanged input,
  two independent byte-identical outputs, and privacy PASS.
- Adds Analysis Handoff guidance, three key-free synthetic analysis examples,
  a Primary Case Study, and release-readiness planning.
- Corrects current Run-All, real-validation, and stable-key privacy wording.

The exact candidate passed required review, CI, clean-clone validation, and
post-release validation before and after publication as a GitHub prerelease.
It is not a stable release or PyPI publication.

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
