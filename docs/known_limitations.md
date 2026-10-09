# Known Limitations

These limitations apply to the current stable v1.6.0 release published as the
latest GitHub Release and Production PyPI distribution. These remain explicit
Product boundaries.

## Input and orchestration

- Run-All requires a supported `summarizedActivities.json` asset.
- Gear, Personal Records, and FIT are optional and use exact filename or bounded
  FIT discovery rules.
- Existing output is never overwritten. A new output directory is required for
  each run.
- A detected but incompletely parsed FIT asset produces auditable
  `PARTIAL_SUCCESS` rather than silent omission.
- The compatible one-shot Run-All processes one supplied Export. It does not
  accumulate historical records across multiple Export downloads.
- A newer Export can omit files, periods, records, or fields observed in an
  older Export. Missing from the newer Export is not evidence of deletion.
  Retain every downloaded Export until the additive Snapshot lifecycle has
  registered and verified it.

## Local dates and times

- Local dates and times derived from UTC or FIT timestamps are computed in one
  IANA timezone for the whole run. The default is `Asia/Tokyo`, regardless of
  where an activity took place or where the command runs.
- Starting with v1.6.0, `run-all`, `snapshot run-all`, and
  `normalize-activities` accept `--timezone` with an IANA timezone name, such
  as `America/New_York`, and `doctor --input --timezone` checks that
  timezone's data. The name must match exactly; use the Area/Location form,
  because legacy aliases such as `Japan` are not available on every system.
  The timezone is recorded as `local_timezone` in `run_manifest.json`,
  `run_summary.json`, and `ANALYSIS_CONTEXT.json`. It is not added to the
  External-safe Pack or the Support Bundle.
- This applies to Activity `activity_datetime_local` and `activity_date_local`
  (and therefore the External-safe Pack month), FIT session
  `start_datetime_local` and lap `start_time`, Sleep `sleep_start_local` and
  `sleep_end_local` (and `sleep_day` when the source provides no
  `calendarDate`), and the dates of FIT-derived HRV values.
- One timezone applies to every record in a run, so an activity recorded while
  travelling uses the run's timezone rather than the local time where it took
  place. Garmin's per-activity `startTimeLocal` is retained as
  `start_time_local_raw` but is not used.
- When the run's timezone differs from where the records were made, a record
  near local midnight can fall on a different calendar date than the one shown
  by Garmin, which also affects documented same-day context comparisons.
  Garmin-provided daily `calendarDate` labels are used as provided and are not
  shifted.
- A Sleep row without `calendarDate` takes its day from its end time in the
  run's timezone, so changing the timezone can place it on the same day as
  another Sleep row. Differing rows for one day stop Run-All with
  `DAILY_METRICS_CONFLICT`, as for any other daily conflict, so the same Export
  can complete in one timezone and stop in another. FIT-derived HRV values that
  share a local date with different values become review rows instead of
  stopping the run; the timezone can change which values share a date.

## Diagnostics and handoff validation

- For a completed output that contains `diagnostics/` (produced by v1.4.0 or
  later), `validate-handoff`, `doctor --run-output`, and `support-bundle`
  accept the output only when the installed package version equals the version
  that produced it. After upgrading the package, rerun Run-All before using
  these commands on that output, or keep the producing version available.

## Snapshot lifecycle

- The v1.2.0 workflow stores complete, explicitly confirmed Export
  observations in one private local store per opaque account boundary.
- Canonical merge uses `missing_is_not_delete`; explicit null and empty values
  preserve the prior explicit value and become review holds. Daily datasets are
  the exception: when Exports differ for one daily key, including a null,
  empty, or missing field, `endurance_score_daily` and `uds_daily` keep
  observed variants, and the other daily datasets, including `sleep_daily`,
  stop.
- Automatic deletion, snapshot/blob deletion, and garbage collection are not
  implemented. Unknown and unsupported inputs are preserved as raw evidence,
  not promoted to normalized public datasets.
- A Snapshot Store is not a public artifact or a backup service. Back up only
  after integrity verification and verify again after restore.
- Starting with v1.5.0, new Snapshot Store directories and files are
  owner-only on Unix-like systems: directories `0700` (including missing parent
  directories created for a new store), immutable blobs, manifests, and
  inventories `0400`, and other files `0600`.
  `normalize-activities` creates a new output directory as `0700` with `0600`
  files. Existing stores and directories keep their permissions; tighten an
  older store with `chmod -R go-rwx <store>`. Windows ignores these modes.
- If `snapshot register` is interrupted, the store can keep
  `.single-writer.lock` and an incomplete registration journal. `register`
  then reports the lock and its recorded process ID, and `verify` reports
  `incomplete_registration_journal_present`. Confirm that no other snapshot
  command is running, delete `.single-writer.lock`, and rerun
  `snapshot register` with the same Export, or with another complete Export if
  the original is no longer available; it reconciles the journal before
  registering. The lock file is the only store file that may be deleted.
- When Snapshots disagree for the same stable key, `snapshot build-input` and
  `snapshot run-all` stop and report counts by dataset and conflict type,
  without dates, keys, or values. Excluding a Snapshot or choosing a value is
  not supported.
- Starting with v1.5.0, `Thumbs.db` inside a ZIP file is not registered, so a
  ZIP that contains it receives a different Snapshot content identity than in
  v1.4.1 or earlier. Re-registering such an Export with its original label
  fails, and a new label registers it as an additional Snapshot; do not
  re-register Exports already registered with an earlier version.
- Starting with v1.5.0, Snapshot Sleep keeps every Sleep field that Run-All
  reads from a single Export. Earlier versions dropped the direct duration
  aliases `durationInSeconds` and `sleepDuration`, the snake_case stage fields
  (`deep_sleep_seconds`, `light_sleep_seconds`, `rem_sleep_seconds`,
  `awake_sleep_seconds`), and the top-level `overallScore` and `sleepScore`,
  so `snapshot run-all` could return `null` where Run-All on the same Export
  returned a value. Sleep rows without these fields build the same Snapshot
  records as in v1.4.1.
- Snapshot Sleep stops when Exports differ for one `calendarDate` in a kept
  field, including a field that is present in one Export and absent in
  another. Because v1.5.0 keeps more fields, a store that v1.4.1 could build
  can stop with v1.5.0 when its Exports differ only in the added fields.
- Snapshot Sleep rows without `calendarDate` remain review holds and are not
  passed to Run-All, while Run-All on a single Export takes the sleep day from
  the sleep end time.

## FIT

- Only selected Activity session and lap fields are normalized.
- Starting with v1.7.0, `fit_sessions` and `fit_laps` include six FIT
  running-dynamics averages (vertical oscillation, stance time, stance time
  percent, stance time balance, vertical ratio, and step length) in the units
  defined by the FIT profile. `avg_stance_time_balance_percent` is the FIT
  `avg_stance_time_balance` value as recorded, in percent, and is not
  converted to a left or right side. Garmin's activity export also contains
  running-dynamics values under other names; the product uses the FIT values
  and does not read those activity-list values.
- Chained FIT payloads are rejected rather than merged.
- Multi-session FIT is normalized only when declared lap counts allocate every
  lap to exactly one session. Allocation conflicts exclude the whole file from
  normalized sessions/laps, remain explicit in FIT audit, and do not enter the
  eligible Activity/FIT Relationship Coverage population.
- Activity/FIT linkage is limited to the documented evidence-qualified eligible
  population; excluded and ambiguous candidates are not guessed.
- Record coordinates, raw telemetry, and arbitrary FIT message preservation are
  intentionally excluded from public output.

## Daily-metric boundaries

- v1.3 Sleep is not reconciled with FIT and does not
  recalculate scores, fill missing days, infer naps, shift days, or create an
  Activity relationship. A same-day `context_only` comparison must keep Sleep
  and Activity facts separate.
- The v1.3.3 Sleep contract derives ex-awake duration only from
  observed finite deep/light/REM stages when any are present. It never fills a
  missing stage with zero or subtracts awake time from the sleep window. When
  all stages are absent, only the approved direct aliases
  (`sleepTimeSeconds`, `totalSleepSeconds`, `durationInSeconds`,
  `sleepDuration`) may provide a value; conflicting aliases fail closed and no
  authoritative value remains `null`.
- Sleep `review_required_count` and `excluded_record_count` are separate audit
  concepts. Excluded-only evidence does not create a review-required warning;
  `needs_review` and excluded rows remain ineligible for Activity context use.
- The v1.3 HRV reference does not average conflicting same-date
  values. Garmin/FIT raw sentinel
  `65535` is excluded, and Health Status HRV is not asserted to be equivalent to
  nightly FIT HRV. It is `analysis_reference_only`, not a Source of Truth and
  not intended for daily coaching, medical, or readiness decisions.
- Health Status unknown metrics remain in long-form evidence; duplicate metric
  types are not silently overwritten.
- Race Prediction is a Garmin algorithm prediction, not a measured result.
  Acute load and readiness components are source-provided and are not
  recalculated. VO2Max source-series differences are not automatically
  explained or collapsed.
- Race Prediction, Acute Training Load, Training Readiness, VO2Max, and Training
  History preserve each source observation. Their day-level QA view is a
  non-canonical aggregate; the package does not choose a latest or preferred row.
- Snapshot-based Endurance and UDS values that differ for one calendar key are
  preserved as public-safe observed variants in the corresponding audit output.
  Their canonical daily interpretation remains unresolved, so no winner is
  emitted. Same-export malformed/divergent values remain fail-closed.
- Snapshot-aware relationship resolution can use earlier authoritative
  observations when a later Export omits an endpoint. Valid unresolved links
  remain auditable; malformed links remain fail-closed.
- Runtime processing sequence is diagnostic only. It cannot alter acquisition
  chronology, normalized truth, relationship classification, or candidate
  selection.
- Naive source timestamps are retained with timezone semantics explicitly
  unconfirmed. Epoch-millisecond timestamps are normalized as UTC, and the
  Activity VO2Max `timestampGmt` field is treated as UTC by its source-field name.
- The v1.3 daily datasets are included in stable v1.3.0. Health
  Status remains deferred, is not supported in v1.3, and is not present in the
  stable registry or Run-All.
- Wellness/Metrics datasets are not Activity facts. Their direct Activity
  relationships remain `not_yet_defined`; documented same-day comparison is
  context only and must not create row identity or imply causality.

## Distribution and integrations

- Hosted processing, Garmin authentication, Open-Meteo, JMA, Instagram,
  wellness/coaching interpretation, Parquet output, and automatic personal
  analysis are outside the stable scope.
- Stable v1.6.0 retains `tzdata` as a Windows-only runtime dependency and emits
  the bounded `TIMEZONE_DATA_UNAVAILABLE` diagnostic if IANA timezone data is
  unavailable in an incomplete environment. Validation covers GitHub Actions
  `windows-latest` and one maintainer-owned physical Windows Production PyPI
  clean install. This does not establish universal Windows compatibility.
- External-safe output is opt-in, month-granularity, Activities-only, and does
  not automatically upload or provide provider-specific privacy guarantees.
- Production PyPI `1.3.3` remains immutable. Its long description preserves the
  publication-time README snapshot, including pre-publication candidate
  wording. Production PyPI `1.4.0`, `1.4.1`, and `1.5.0` also remain
  immutable, and `1.6.0` is the current release artifact; current repository
  documentation is the maintained public truth for future builds.

The documented CLI and versioned Run-All output contract are stable for `1.x`.
Other Python modules are usable but are not all promoted to an independently
stable third-party API contract.

## Performance metrics and deferred promotion

- Hill Score Daily and Endurance Score Daily are stable v1.3 datasets.
- No Activity relationship is defined for either daily dataset. Date equality
  is not sufficient evidence for a join.
- Lactate Threshold is provided as candidate/audit infrastructure only. Stable
  public promotion is intentionally deferred until machine identity, units,
  timezone semantics, heart-rate authority, FTP/power authority, and public
  field/type rules are finalized. Fail-closed behavior is retained.
- Lactate source sequence may order records within its source family, but it is
  not identity and never authorizes latest-wins behavior.
- Power conflicts remain review evidence and are not averaged, converted, or
  silently resolved.
