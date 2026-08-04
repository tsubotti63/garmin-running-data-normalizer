# Product Change History

This file records factual Garmin Running Data Normalizer product changes. The
root `CHANGELOG.md` belongs to the byte-locked AI Collaboration Platform v0.9
Standard adopted by this repository.

## v1.3.0 — prepared stable release source

Status: prepared for final Product authorization; not yet tagged, released, or
published to PyPI.

### Added

- Adds ten optional normalized Run-All datasets: Hill Score Daily, Endurance
  Score Daily, Race Prediction, Sleep Daily, UDS Daily, Acute Training Load,
  Training Readiness, VO2Max, HRV Daily, and Training History.
- Expands the stable registry and generated Output Experience to 17 normalized
  datasets and 212 documented public fields.
- Adds per-dataset Snapshot policies for daily-state upsert,
  immutable-observation union, or FIT-derived regeneration.
- Adds human- and machine-readable relationship guidance for every new dataset,
  including grain, stable key, semantic role, cardinality, allowed use,
  forbidden joins, and derived-projection status.

### Changed

- Generated `START_HERE.md`, `DATASET_INVENTORY.md`, `ANALYSIS_HANDOFF.md`,
  `ANALYSIS_CONTEXT.json`, and `SCHEMA_CATALOG.json` now describe the expanded
  dataset catalog.
- Run-All emits additive normalized JSON and audit/QA artifacts when the
  corresponding optional Garmin source families are present.
- Package version metadata now derives from the package `__version__` source so
  the distribution and runtime identity cannot drift through duplicate manual
  version declarations.

### Fixed

- Daily-metric collisions no longer imply an unsupported latest-wins record;
  source-observation families preserve every stable observation and derived
  day summaries keep `selection_rule: null`.
- HRV conflicts remain explicit review rows rather than being averaged or
  silently selected.

### Compatibility

- The CLI, existing dataset IDs, existing stable keys, existing output paths,
  exit codes, package imports, six explicit relationship contracts, Snapshot
  missing-is-not-delete behavior, and privacy boundary are unchanged.
- All v1.3 outputs are additive; absent optional families remain
  `SKIPPED_NOT_PRESENT` and do not add a warning.

### Known Limitations

- HRV Daily is `analysis_reference_only`, not a daily coaching or medical
  Source of Truth, and is not interchangeable with Health Status HRV.
- New Wellness/Metrics datasets remain separate from Activity facts. Same-day
  comparison is context only; direct Activity relationships are not defined.

### Deferred

- Lactate Threshold remains candidate/audit-only until its machine stable key,
  units, timezone, heart-rate authority, FTP/power authority, and public field
  types are approved.
- Health Status is not a v1.3 supported dataset.

## v1.2.1 — stable Production release

- Adds the `tzdata` runtime dependency on Windows only so clean package
  installations can resolve the existing IANA `Asia/Tokyo` timezone contract.
  macOS and Linux continue to use their system timezone data.
- Adds the bounded `TIMEZONE_DATA_UNAVAILABLE` diagnostic while preserving the
  general Activities normalization error boundary and avoiding traceback or
  personal-data exposure in normal CLI output.
- Adds Windows PowerShell onboarding, cross-platform public-command validation,
  and a `windows-latest` CI job.
- Verifies editable, wheel, and source-distribution installs on Windows,
  including automatic `tzdata` installation, timezone resolution, repeated
  Synthetic Run-All, and deterministic output comparison.
- Publishes the reviewed source as the immutable annotated `v1.2.1` tag,
  current stable GitHub Release, verified TestPyPI distribution, and verified
  Production PyPI distribution after their separate Human approval gates.
- Confirms a clean Production PyPI v1.2.1 installation on one
  maintainer-owned physical Windows environment: `tzdata` was installed
  automatically, `Asia/Tokyo` resolved, and Synthetic Run-All completed with
  `PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
  `run_summary.json` present. This is bounded evidence, not a universal claim.

## v1.2.0 — stable Production release

- Adds an immutable, account-bounded local Snapshot Store with explicit
  completeness confirmation, content-addressed file/member preservation,
  arbitrary historical insertion, idempotent registration, integrity
  verification, single-writer locking, and journal recovery.
- Adds versioned per-dataset merge policy, seven-state missing-value evidence,
  previous-only retention, new/reappeared/changed reporting, field provenance,
  null/empty review holds, and fail-closed conflict handling.
- Materializes the cumulative unique FIT blob set, reparses it with the current
  stable parser/key contracts, and regenerates Activity/FIT relationships
  without timestamp-only inference.
- Adds lifecycle CLI commands and Snapshot lineage, coverage, and Canonical
  merge evidence while preserving the stable one-shot Run-All behavior.
- Keeps real Snapshot Stores and four-Snapshot validation private/local; public
  tests and examples remain synthetic.
- Publishes the reviewed release commit as the immutable `v1.2.0` annotated
  tag, stable GitHub Release, TestPyPI distribution, and Production PyPI
  distribution after their separate approval and verification gates passed.
- Links the bounded, public-safe validation evidence in
  [CS-007: Preserving Garmin History Across Incomplete Repeated Exports](case_studies/cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md).

## v1.1.1 — stable Production release

- Promotes the package metadata, import version, CLI version, generated
  product version, exact-version tests, and PyPI maturity classifier from
  `1.1.0rc1` to `1.1.1`.
- Carries the reviewed v1.1 FIT integrity, relationship coverage, privacy, and
  Output Experience implementation without changing runtime behavior or the
  stable `1.x` interface.
- Preserves the published `v1.1.0` tag and GitHub Release as immutable history;
  their `1.1.0rc1` package artifacts were not renamed or reused for stable
  Production publication.
- Publishes the reviewed source as the distinct `v1.1.1` tag, GitHub Release,
  and Production PyPI distribution after their separate Human Approval
  Boundaries were satisfied.

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
