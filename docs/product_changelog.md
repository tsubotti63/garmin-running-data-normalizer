# Product Change History

This file records factual Garmin Running Data Normalizer product changes. The
root `CHANGELOG.md` belongs to the byte-locked AI Collaboration Platform v0.9
Standard adopted by this repository.

## v1.1.0rc1 — release candidate

- Adds complete FIT file CRC validation, optional header CRC validation, and
  explicit audit states for CRC, truncation, chained, undefined-message, and
  session/lap-allocation failures.
- Adds content-derived multi-session `fit_session_key` and child
  `fit_lap_key` while retaining compatible `fit_file_id` and `lap_index`.
- Adds an auditable `activity_fit_links` dataset with deterministic
  evidence-qualified eligibility, exclusions, zero ambiguity, and no
  timestamp-only join.
- Promotes reviewed Activity/Gear, Personal Record/Activity, FIT Lap/Session,
  and Activity/FIT relationships with fail-closed referential QA.
- Integrates `START_HERE.md`, `DATASET_INVENTORY.md`, `ANALYSIS_HANDOFF.md`,
  machine-readable analysis/schema context, and artifact inventory into
  Run-All.
- Adds evidence-boundary Relationship Coverage to `START_HERE.md`,
  `ANALYSIS_HANDOFF.md`, and `ANALYSIS_CONTEXT.json` for every explicit
  relationship without suppressing unresolved, ambiguous, or duplicate
  records.
- Adds an opt-in deterministic external-safe Analysis Pack that excludes
  provenance, hashes, IDs/keys, memo text, coordinates, exact dates/times,
  heart rate, power, cadence, training effect/load, and other health or
  performance detail outside its month-level volume/count profile; it never
  uploads automatically.
- Preserves all existing `1.x` CLI and output paths; v1.1 artifacts are
  additive. Tag, Release, and package-index publication remain separate Human
  Approval Boundaries.

## v1.0.1 — approved initial PyPI publication candidate

- Advances the package, import, CLI, and exact-version tests from `1.0.0` to
  `1.0.1` without changing runtime behavior or the stable `1.x` interface.
- Carries the P0 packaging checks and P1 guarded Trusted Publishing workflow
  into an exact patch candidate for initial package-index publication.
- Adds release notes and P2 approval-gate evidence while retaining the
  existing Apache-2.0, dependency, privacy, and supported-dataset boundaries.

The Human owner approved version `1.0.1` and candidate commit
`89677a78cd0e75c1ad168aca89b27724feb31013`. The final release-state
documentation update, annotated tag, GitHub Release, protected GitHub
Environments, approval variables, and Trusted Publisher configuration are
authorized. TestPyPI and PyPI uploads remain separate Human Approval
Boundaries.

## Unreleased — P1 PyPI publish readiness

- Adds a manual-only, build-only-by-default publication workflow for exact
  reviewed source commits and versions.
- Separates TestPyPI and PyPI with target-specific approval variables,
  protected GitHub Environments, OIDC-only publish jobs, and automatic clean
  install verification.
- Pins all actions by commit and keeps credentials, API tokens, automatic
  triggers, duplicate-version bypass, and index deletion outside the workflow.
- Adds the publication runbook, current-state evidence, failure handling, and
  explicit Product decision packet.

P1 performs no upload, publisher/environment configuration, version change,
tag, or GitHub Release operation. Its status is `P1_READY_FOR_APPROVAL`.

## Unreleased — P0 PyPI packaging readiness

- Adds repeatable wheel and source-distribution builds with strict Twine
  metadata and README rendering checks.
- Installs both artifacts in isolated environments and verifies dependency,
  import, version, and console-entry-point behavior in CI.
- Adds PyPI-safe absolute README links and separates current checkout install,
  future index install, and non-uploading maintainer validation commands.
- Keeps runtime dependencies empty and records build/Twine as release tooling
  only.

No TestPyPI or PyPI upload, version reservation, new tag, or GitHub Release is
performed by P0. Initial index publication remains a separate Human-authorized
operation.

## v1.0.0

This section records the reviewed product changes prepared for the first stable
release. Publication remains a separate Human-authorized action.

### M7.4 Health Status migration

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

### M7.3 HRV migration

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

### M7.2 Sleep migration

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

### M7.1 FIT migration

- Aligns selected FIT Activity and FIT Lap field mappings with the authorized
  public migration source.
- Converts FIT invalid sentinels for migrated numeric metrics to null before
  applying scale factors.
- Extends synthetic unit and Run-All regression coverage for heart rate,
  cadence, power, ascent, stable identity, and lap provenance.
- Retains the existing safe discovery, content-derived FIT file identifiers,
  source-relative provenance, and exclusion of record coordinates and raw
  telemetry.

Complete FIT CRC validation and multi-session identity remain migration gaps.

### Stable release preparation

- Aligns package, CLI, bootstrap, and dataset-registry version declarations at
  `1.0.0` without narrowing the previously accepted registry lifecycle status.
- Adds supported-dataset and known-limitation references plus a release-ready
  `v1.0.0` note.
- Defines the documented CLI and versioned Run-All output contract as the
  stable `1.x` interface while retaining explicit library-level boundaries.
- Records the Human rights confirmation applicable to material included in the
  `v1.0.0` candidate.

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
