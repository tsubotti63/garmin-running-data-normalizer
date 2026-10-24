# Garmin Running Data Normalizer — Changelog

The authoritative product history is maintained in:

- [Product Changelog](docs/product_changelog.md)

Release-specific notes are available under:

- [`docs/release_notes/`](docs/release_notes/)

The AI Collaboration Platform changelog is maintained in the separate
canonical platform repository:

- [AI Collaboration Platform — CHANGELOG](https://github.com/tsubotti63/ai-collaboration-platform/blob/main/CHANGELOG.md)

## v2.0.1 — stable Production release

Published as the annotated `v2.0.1` tag, the latest stable
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v2.0.1),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/2.0.1/).

### Fixed

- The page of the GUI: **Quit** asks first, in the bar at the bottom of the
  page, and the page says while the app stops and when it has stopped; the
  bar at the bottom stays on the screen; after a run, a line says what
  pressing **Run normalization** again does; the Snapshot box no longer says
  that a Snapshot Store will be made when this Export alone is normalized; the
  help marks **Read the result** as done only once `START_HERE.md` is opened
  from the page; and a hint, the help of the timezone, and the English words
  for a folder or file that could not be opened are clearer.

### Changed

- The GUI Guide answers what a first reading of it asked: the installation in
  numbered steps, how to report a GUI that does not open, what to do when the
  icon could not be made, and more about updating, going back to an open GUI,
  stopping, and removing this app.

### Compatibility

- The processing, the 17 datasets, 247 fields, stable keys, output paths, the
  command line, the Snapshot Store format, and the Product exit mapping
  remain those of v2.0.0. Outputs record `2.0.1`; check an output of v2.0.0
  with v2.0.0. See the [v2.0.1 Release Notes](docs/release_notes/v2.0.1.md).

## v2.0.0 — stable Production release

Published on 2026-10-23 JST as the annotated `v2.0.0` tag, the latest stable
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v2.0.0),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/2.0.0/).

### Added

- A local GUI: `garmin-running-data-normalizer gui` opens a page in the
  browser of the same computer, listening on `127.0.0.1` only with the key of
  its launch. One page with four numbered boxes chooses the Export, the
  Snapshot Store, and the output, and normalizes, in English and Japanese.
  With `--create-shortcut`, it first makes an icon that starts the GUI on
  macOS and Windows.
- `snapshot unlock`, which removes the lock file that a stopped registration
  left.
- `--input` takes the downloaded Export ZIP file as it is.
- Four audit records, `disagreeing_fields` in every row, new warning codes,
  and `run_all_version` 2.

### Changed

- Problems in the data no longer stop a run: a file or row that cannot be used
  is left out with a warning (exit 3), values that disagree are kept empty and
  marked with every value in the audit records, and no value is dropped or
  chosen silently. Runs still stop for safety, for a folder that is not an
  Export, and for an input that mixes Exports or accounts.
- Every `ERROR` line ends with the next step of its code; some codes change.
- `Ctrl+C` ends every command with exit 130.
- `validate-handoff`, `doctor --run-output`, and `support-bundle` refuse an
  output of v1.7.1.

### Compatibility

- The 17 datasets and stable keys are unchanged; the field inventory grows
  from 224 to 247.
- The Snapshot lifecycle contract and policy registry stay `v1.0`, and the
  store format stays 1; existing Snapshot Stores need no migration.
- The Product exit mapping stays `0 / 0 / 3 / 2`.

See the [v2.0.0 Release Notes](docs/release_notes/v2.0.0.md) and the
[Migration Notes](docs/migration_notes.md#v171-to-v200).

## v1.7.1 — stable Production release

Published on 2026-10-11 JST as the annotated `v1.7.1` tag, the latest stable
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.7.1),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.7.1/).

### Fixed

- `snapshot run-all` now normalizes the Hill Score, Endurance Score, and VO2Max
  rows that `snapshot build-input` merges into `snapshot_HillScore.json`,
  `snapshot_EnduranceScore.json`, and `snapshot_vo2max.json`. From v1.3.0
  through v1.7.0, Run-All did not recognize those files, so the three datasets
  were always empty in `snapshot run-all` output, with no warning.

### Also included

- Internal changes toward v2.0.0 that add no user-facing feature: an optional
  keyword-only progress callback for `run_all` and `parse_fit_export`; version
  checks in `validate-handoff`, `doctor --run-output`, and `support-bundle`
  that accept Product major version 1 and later; and an internal `gui`
  package with its page files, which is in development and has no command.

### Compatibility

- One-shot `run-all` output, the 17 datasets, 224 fields, 6 explicit
  relationships, stable keys, output paths, Snapshot rules, the Snapshot Store
  format, and the Product exit mapping remain unchanged. Rerun
  `snapshot run-all` to obtain the missing rows; see the
  [v1.7.1 Release Notes](docs/release_notes/v1.7.1.md).

## v1.7.0 — stable Production release

Published on 2026-10-10 JST as the annotated `v1.7.0` tag,
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.7.0),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.7.0/).

### Added

- Six FIT running-dynamics averages in `fit_sessions` and `fit_laps`:
  `avg_vertical_oscillation_mm`, `avg_stance_time_ms`,
  `avg_stance_time_percent`, `avg_stance_time_balance_percent`,
  `avg_vertical_ratio_percent`, and `avg_step_length_mm`, in the units defined
  by the FIT profile.
- Ten columns at the end of `analysis/activities.csv`: elapsed and moving time,
  and `fit_*` columns with the running dynamics and total ascent and descent
  of the FIT session joined through an explicit `activity_fit_links` row.

### Compatibility

- The 17 datasets, 6 explicit relationships, stable keys, output paths,
  Snapshot rules, and Product exit mapping remain unchanged; the field
  inventory grows from 212 to 224.
- Tools that read `fit_sessions`, `fit_laps`, or `analysis/activities.csv`
  with a closed list of fields or columns must accept the new ones. See the
  [v1.7.0 Release Notes](docs/release_notes/v1.7.0.md).

## v1.6.0 — stable Production release

Published on 2026-10-09 JST as the annotated `v1.6.0` tag,
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.6.0),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.6.0/).

### Added

- `--timezone` on `run-all`, `snapshot run-all`, and `normalize-activities`
  selects the IANA timezone for local dates and times; `doctor --input
  --timezone` checks that timezone's data. The default remains `Asia/Tokyo`.
- `local_timezone` in `run_manifest.json`, `run_summary.json`, and
  `ANALYSIS_CONTEXT.json`, and the timezone lines in `START_HERE.md` and
  `ANALYSIS_HANDOFF.md`.
- `TIMEZONE_INVALID` (exit 2) for a name that is not an exact IANA timezone
  name.

### Compatibility

- Without `--timezone`, normalized values are unchanged. The 17 datasets, 212
  fields, 6 explicit relationships, stable keys, output paths, Snapshot rules,
  and Product exit mapping remain unchanged.
- With `--timezone`, the same Export can stop with `DAILY_METRICS_CONFLICT`
  when Sleep rows without `calendarDate` fall on the same day. See the
  [v1.6.0 Release Notes](docs/release_notes/v1.6.0.md).

## v1.5.0 — stable Production release

Published on 2026-10-07 JST as the annotated `v1.5.0` tag,
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.5.0),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.5.0/).

### Changed

- New Snapshot Stores and `normalize-activities` output are owner-only on
  Unix-like systems.
- `Thumbs.db` inside a ZIP file is skipped like other operating-system metadata
  files; such a ZIP receives a different Snapshot content identity.
- Snapshot Sleep keeps every Sleep field that Run-All reads.

### Fixed

- `snapshot run-all` no longer returns `null` for Sleep values that Run-All
  reads from the same Export.
- Snapshot stop conflicts report counts by dataset and conflict type, and an
  interrupted-registration lock reports its recovery step.

### Compatibility

- The 17 datasets, 212 fields, 6 explicit relationships, stable keys, output
  paths, and Product exit mapping remain unchanged; existing Snapshot Stores
  need no migration.
- A Store whose Exports differ only in the added Sleep fields can now stop.
  See the [v1.5.0 Release Notes](docs/release_notes/v1.5.0.md).

## v1.4.1 — stable Production patch release

Published on 2026-10-07 JST as the annotated `v1.4.1` tag,
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.4.1),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.4.1/).

### Fixed

- FIT session `sport` and `sub_sport` use FIT profile names, and the
  sub-sport no longer renames the sport.
- FIT-derived HRV is read only from FIT files that pass the FIT container
  checks, including the file CRC.
- `.DS_Store`, `Thumbs.db`, AppleDouble `._*` files, and `__MACOSX/` no
  longer break Export folder input or completed-output validation.

### Compatibility

- The 17 datasets, 212 fields, 6 explicit relationships, stable keys,
  Snapshot semantics, and Product exit mapping remain unchanged.
- FIT session values, Activity/FIT links, and `hrv_daily` can change for the
  same Export; rerun Run-All after upgrading. See the
  [v1.4.1 Release Notes](docs/release_notes/v1.4.1.md).

## v1.4.0 — stable Production release

Published on 2026-08-21 JST as the annotated `v1.4.0` tag,
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.4.0),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.4.0/).

### Added

- Export Evidence Doctor with deterministic pre-run and post-run projections.
- Source Completeness and Run Quality diagnostic artifacts for completed runs.
- A typed, public-safe, deterministic six-member Support Bundle that requires
  Human review and never uploads automatically.

### Compatibility

- The existing 17 datasets, 212 fields, 6 explicit relationships, stable keys,
  Snapshot behavior, normalized truth, External-safe Pack, and Product exit
  mapping remain unchanged.
- The release preserves the existing public output, stable-key, Snapshot,
  Run-All, and Product exit contracts.

## v1.3.3 — stable Production patch release

Published on 2026-08-13 JST as the annotated `v1.3.3` tag,
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.3.3),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.3.3/).

- Restores the approved observed Sleep-stage duration contract with direct
  fallback only when every stage is absent; missing stages remain missing,
  awake/window subtraction is not used, and conflicting direct aliases fail
  closed.
- Separates review-required counts from excluded-record evidence across daily
  metric summaries so excluded-only input does not create a review-required
  warning.
- Aligns the public Run-All and Python Sleep helper semantics and documents the
  available-only context boundary.

## v1.3.2 — stable Production patch release

Snapshot-aware relationship resolution, deterministic Sleep exact-duplicate
handling, observed-variant preservation for Endurance/UDS, Lactate candidate
preservation without winner selection, and acquisition-order separation were
published in v1.3.2. See the
[v1.3.2 Release Notes](docs/release_notes/v1.3.2.md),
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.3.2),
and [Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.3.2/).
