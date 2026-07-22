# Product Change History

This file records factual Garmin Running Data Normalizer product changes. The
root `CHANGELOG.md` belongs to the byte-locked AI Collaboration Platform v0.9
Standard adopted by this repository.

## Unreleased — M7.4 Health Status migration

- Adds dependency-free normalization of exact-suffix `healthStatusData.json`
  assets into complete long metric and fixed daily schemas.
- Covers HRV, HR, SPO2, skin temperature, and respiration daily fields while
  retaining unknown metrics in long-form evidence without dynamic columns.
- Resolves duplicate calendar dates by explicit latest-timestamp selection,
  retains superseded long-form evidence, and refuses silent duplicate-metric
  overwrite.
- Adds wholly synthetic directory/ZIP, schema, provenance, duplicate, missing,
  unsafe-number, and unknown-metric coverage.

This work does not add Health Status to Run-All or promote health-status HRV to
nightly HRV, analytics, interpretation, or coaching.

## Unreleased — M7.3 HRV migration

- Adds dependency-free extraction of the bounded FIT HRV candidate from
  Message 370 / Field 1 using `raw / 128` milliseconds.
- Excludes Garmin/FIT raw sentinel `65535`, preserves invalid counts, and does
  not average conflicting same-date valid values.
- Adds `healthStatusData` HRV reference extraction and same-date consistency
  evidence without merging the sources or asserting measurement equivalence.
- Adds wholly synthetic directory/ZIP, provenance, conflict, invalid-value,
  unsafe-number, and negative FIT coverage.

This work does not add HRV to Run-All, promote a source of truth, or rename
health-status-scoped HRV as nightly HRV.

## Unreleased — M7.2 Sleep migration

- Adds dependency-free library-level normalization for Garmin
  `sleepData.json`, including safe directory/ZIP discovery and provenance.
- Attributes `sleep_day` to the local date on which the recorded sleep period
  ends, while retaining the source calendar date separately.
- Preserves duplicate, missing, invalid-interval, and empty retro-only records
  with explicit review or exclusion states rather than silently filling,
  shifting, or deduplicating them.
- Adds wholly synthetic coverage for stage metrics, score variants, timezone
  attribution, review states, safe ZIP input, and content-derived identity.

This work does not add Sleep to Run-All or change the public dataset registry.
FIT/JSON reconciliation, score recalculation, missing-day filling, nap
inference, and activity joins remain out of scope.

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
