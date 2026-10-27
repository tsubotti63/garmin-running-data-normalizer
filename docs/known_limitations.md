# Known Limitations

These limitations describe v2.1.0, the current stable release. v1.7.1 and
earlier releases are described by the documents at their tags, such as
`v1.7.1`. These remain explicit Product boundaries. The rules for problems in
the data, which v2.0.0 changed, are in
[v2.0.0 Data Handling](v2_data_handling.md).

## Input and orchestration

- Run-All requires a supported `summarizedActivities.json` asset.
- Gear, Personal Records, and FIT are optional. Their files are found by name
  without regard to letter case, and FIT files by bounded discovery rules.
  Files of a form that no dataset reads, and ZIP files inside ZIP files, are
  not read; `run_manifest.json` lists them (see
  [Files and fields that are not read](v2_data_handling.md#files-and-fields-that-are-not-read)).
- Existing output is never overwritten. A new output directory is required for
  each run, and the folder that holds it must exist: the command stops with
  `OUTPUT_PARENT_NOT_FOUND` before it reads the input (see
  [Stops that remain](v2_data_handling.md#stops-that-remain)).
- A file or a row that cannot be used is left out with a warning, and the run
  finishes as `PARTIAL_SUCCESS` (exit 3) rather than omitting it silently: a
  FIT asset that is detected but not parsed completely, a file that cannot be
  read, or a row with a value but without a usable key or date or, in some
  datasets, a usable value (see
  [Files that cannot be read](v2_data_handling.md#files-that-cannot-be-read)
  and [Rows and values with problems](v2_data_handling.md#rows-and-values-with-problems)).
- The compatible one-shot Run-All processes one supplied Export. It does not
  accumulate historical records across multiple Export downloads.
- A newer Export can omit files, periods, records, or fields observed in an
  older Export. A record or a field missing from the newer Export is not
  evidence of deletion, and the Snapshot lifecycle keeps the earlier value;
  an explicit empty value in a later Snapshot of Activities, Gear,
  `activity_gear`, or Personal Records removes the value, and an
  `activity_gear` link that the newer Export does not hold can be removed
  (see [Snapshot lifecycle](#snapshot-lifecycle)).
  Retain every downloaded Export until the Snapshot lifecycle has registered
  and verified it.

## Identifiers

- Identifiers are compared after trimming spaces and leading zeros. Only the
  ASCII digits 0-9 count as digits, so full-width digits are text, and a
  number written as `123.0` is the identifier `123`.
  `normalized/activity_gear.json` writes digit-only `gear_key` and
  `activity_id` text as integers. A row whose identifier cannot be used, such
  as `1.5`, and a row of Activities, Gear, or the links whose identifier is
  `0`, is left out with the warning `DATA_ROW_LEFT_OUT` (see
  [Rows and values with problems](v2_data_handling.md#rows-and-values-with-problems)).

## Local dates and times

- Local dates and times derived from UTC or FIT timestamps are computed in one
  IANA timezone for the whole run. The default is `Asia/Tokyo`, regardless of
  where an activity took place or where the command runs.
- Starting with v1.6.0, `run-all`, `snapshot run-all`, and
  `normalize-activities` accept `--timezone` with an IANA timezone name, such
  as `America/New_York`, and `doctor --input --timezone` checks that
  timezone's data; the GUI sets it in the box of the output. The name must
  match exactly; use the Area/Location form, because legacy aliases such as
  `Japan` are not available on every system. The timezone is recorded as
  `local_timezone` in `run_manifest.json`, `run_summary.json`, and
  `ANALYSIS_CONTEXT.json`, and as `date_timezone` in the HRV audit. It is not
  added to the External-safe Pack or the Support Bundle.
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
  another Sleep row. When such rows differ, the fields that differ are left
  empty and listed in `disagreeing_fields`, the values stay in the audit
  record, and the warning `VALUES_DISAGREE` counts the day (see
  [Values that disagree](v2_data_handling.md#values-that-disagree)), so the
  same Export can leave different fields empty in different timezones. The
  same holds for FIT-derived HRV values that share a local date.

## Diagnostics and handoff validation

- For a completed output that contains `diagnostics/` (produced by v1.4.0 or
  later), `validate-handoff`, `doctor --run-output`, `support-bundle`, and the
  GUI's check of an earlier output accept the output only when the installed
  package version equals the version that produced it, a release candidate
  such as `2.0.0rc2` included. Otherwise they stop with
  `OUTPUT_OTHER_VERSION` and name the version that produced it, and the GUI
  shows no change since such an output (see
  [Checks of earlier outputs](v2_data_handling.md#checks-of-earlier-outputs)).
  After upgrading the package, rerun Run-All before using these commands on
  that output, or keep the producing version available.
- The view page of the GUI and `series` (v2.1.0) read only outputs that the
  installed version produced. They stop for an output of another version
  with `OUTPUT_OTHER_VERSION`, and for an output of v1.3, which passes the
  checks, with `SERIES_OUTPUT_OTHER_VERSION`. Normalize the Export again with
  the installed version into a new folder to look at its numbers.

## Snapshot lifecycle

- The v1.2.0 workflow stores complete, explicitly confirmed Export
  observations in one private local store per opaque account boundary.
- Snapshots are ordered by the observation times of their Exports, and
  Snapshots observed at the same time are one time point. In Activities, Gear,
  `activity_gear`, and Personal Records, each field takes its value from the
  latest Snapshot that contains it, an explicit empty value removes the value,
  and every earlier value stays in the dataset's audit record with the warning
  `VALUES_UPDATED`; values that differ within one time point leave the field
  empty and listed in `disagreeing_fields`. A record that the latest Snapshot
  does not contain stays, with the warning `RECORDS_NOT_IN_LATEST_SNAPSHOT`,
  except an `activity_gear` link: it is removed when the latest Snapshot has
  Gear links (`gearActivityDTOs`, even empty) and contains both the link's
  Activity and its Gear, as when the Activity's shoes were changed, and the
  audit record keeps it in `removed_links` (see
  [Changes across Snapshots](v2_data_handling.md#changes-across-snapshots)).
  In the daily datasets, the observations of a key in all Snapshots are
  compared together: a value that a later Snapshot leaves null or out stays,
  and values that differ leave the field empty and listed in
  `disagreeing_fields`, with the values and the Snapshots that gave them in
  the audit record and the warning `VALUES_DISAGREE` (see
  [Values that disagree](v2_data_handling.md#values-that-disagree)). A daily
  value or record that the user deleted in Garmin Connect therefore stays from
  the earlier Snapshot.
- Automatic deletion, snapshot/blob deletion, and garbage collection are not
  implemented: no command removes a Snapshot, and every normalization of the
  Snapshots uses all of them. Excluding a Snapshot or choosing a value is not
  supported. Unknown and unsupported inputs are preserved as raw evidence, not
  promoted to normalized public datasets.
- A Snapshot Store is not a public artifact or a backup service. Back up only
  after integrity verification and verify again after restore.
- Starting with v1.5.0, new Snapshot Store directories and files are
  owner-only on Unix-like systems: directories `0700` (including missing parent
  directories created for a new store), immutable blobs, manifests, and
  inventories `0400`, and other files `0600`.
  `normalize-activities` creates a new output directory as `0700` with `0600`
  files. Existing stores and directories keep their permissions; tighten an
  older store with `chmod -R go-rwx <store>`. Windows ignores these modes.
- If `snapshot register` is interrupted, the store can keep its lock file
  `.single-writer.lock` and an incomplete registration journal. While the lock
  file is there, `snapshot register` stops with `SNAPSHOT_STORE_LOCKED`; while
  the journal is incomplete, `snapshot verify`, `snapshot build-input`, and
  `snapshot run-all` stop with `SNAPSHOT_REGISTRATION_INCOMPLETE` (see
  [Snapshot Stores](v2_data_handling.md#snapshot-stores)). Confirm that no
  other normalization or snapshot command uses the store, remove the lock
  file with `snapshot unlock --store <store> --confirm-no-other-command`,
  which the GUI offers too, and rerun `snapshot register` with the same
  Export, or with another complete Export if the original is no longer
  available; it completes the store before registering. The lock file is the
  only store file that may be removed.
- From v1.3.0 through v1.7.0, `snapshot run-all` produced no
  `hill_score_daily`, `endurance_score_daily`, or `vo2max_daily` rows, with no
  warning, because Run-All did not recognize the merged files that
  `snapshot build-input` writes for them; the three families reported
  `SKIPPED_NOT_PRESENT`. v1.7.1 reads them. Rerun `snapshot run-all` with
  v1.7.1 or later to obtain the rows; the Snapshot Store needs no migration.
- Starting with v1.5.0, `Thumbs.db` inside a ZIP file is not registered, so a
  ZIP that contains it receives a different Snapshot content identity than in
  v1.4.1 or earlier. Re-registering such an Export with its original label
  stops with `SNAPSHOT_LABEL_EXISTS`, and a new label registers it as an
  additional Snapshot; do not re-register Exports already registered with an
  earlier version.
- Starting with v1.5.0, Snapshot Sleep keeps every Sleep field that Run-All
  reads from a single Export. Earlier versions dropped the direct duration
  aliases `durationInSeconds` and `sleepDuration`, the snake_case stage fields
  (`deep_sleep_seconds`, `light_sleep_seconds`, `rem_sleep_seconds`,
  `awake_sleep_seconds`), and the top-level `overallScore` and `sleepScore`,
  so `snapshot run-all` could return `null` where Run-All on the same Export
  returned a value. Sleep rows without these fields build the same Snapshot
  records as in v1.4.1.
- From v1.5.0 through v1.7.1, Snapshot Sleep stopped when Exports differed for
  one `calendarDate` in a kept field, including a field present in one Export
  and absent in another. v2.0.0 leaves the fields that differ empty instead,
  as for every daily dataset, and a field absent in one Export is not a
  difference.
- Snapshot Sleep rows without `calendarDate` take their sleep day from the
  sleep end time, as Run-All on a single Export does; a row without either is
  left out (see [Snapshot Stores](v2_data_handling.md#snapshot-stores)).

## FIT

- Only selected Activity session and lap fields are normalized.
- Starting with v1.7.0, `fit_sessions` and `fit_laps` include six FIT
  running-dynamics averages (vertical oscillation, stance time, stance time
  percent, stance time balance, vertical ratio, and step length) in the units
  defined by the FIT profile. `avg_stance_time_balance_percent` is the FIT
  `avg_stance_time_balance` value as recorded, in percent, and is not
  converted to a left or right side. Garmin's activity export also contains
  running-dynamics values under other names; the product uses the FIT values
  and does not read those activity-list values. `analysis/activities.csv`
  repeats the session values as `fit_*` columns only for activities with an
  explicit Activity/FIT link.
- Chained FIT payloads are rejected rather than merged.
- Multi-session FIT is normalized only when declared lap counts allocate every
  lap to exactly one session. Allocation conflicts exclude the whole file from
  normalized sessions/laps, remain explicit in FIT audit, and do not enter the
  eligible Activity/FIT Relationship Coverage population.
- Activity/FIT linkage is limited to the documented evidence-qualified eligible
  population; excluded and ambiguous candidates are not guessed, and the
  warning `ACTIVITY_FIT_LINK_AMBIGUOUS` counts the ambiguous ones.
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
  `sleepDuration`) may provide a value; when they disagree, the duration stays
  empty, the audit record counts it in `direct_aliases_disagree_count`, and no
  value is chosen.
- Sleep keys that need review (`review_key_count`) and rows left out
  (`excluded_record_count`) are counted apart in the audit. A row that holds
  a value but cannot be used is left out with the
  warning `DATA_ROW_LEFT_OUT`, and the run finishes as `PARTIAL_SUCCESS`
  (exit 3); a row without any value is only counted as an empty record.
  `needs_review` and excluded rows remain ineligible for Activity context use.
- The v1.3 HRV reference does not average values that differ for one date:
  the value is empty and listed in `disagreeing_fields`, and the audit record
  keeps the values. A reading without a value, such as the Garmin/FIT raw
  sentinel `65535`, is counted in `absent_value_counts` without a warning.
  Health Status HRV is not asserted to be equivalent to nightly FIT HRV. It is
  `analysis_reference_only`, not a Source of Truth and not intended for daily
  coaching, medical, or readiness decisions.
- Health Status unknown metrics remain in long-form evidence; duplicate metric
  types are not silently overwritten.
- Race Prediction is a Garmin algorithm prediction, not a measured result.
  Acute load and readiness components are source-provided and are not
  recalculated. VO2Max source-series differences are not automatically
  explained or collapsed.
- Race Prediction, Acute Training Load, Training Readiness, VO2Max, and Training
  History preserve each source observation. Their day-level QA view is a
  non-canonical aggregate; the package does not choose a latest or preferred row.
- Daily values that differ for one key, across Snapshots or within one Export,
  Endurance Score and UDS included, leave the field empty and listed in
  `disagreeing_fields`; the audit record keeps the values, with the Snapshots
  that gave them in Snapshot runs, and no winner is emitted. A value of
  another form is left out with its row or kept with the warning
  `DATA_VALUE_INVALID` (see
  [Rows and values with problems](v2_data_handling.md#rows-and-values-with-problems)).
- Snapshot-aware relationship resolution can use earlier authoritative
  observations when a later Export omits an endpoint. A link whose record is
  not in the output, or that is missing, malformed, or disagrees, stays with
  its relationship `unresolved` and a reason, with the warning
  `RELATIONSHIP_UNRESOLVED_VALID_LINK` or
  `RELATIONSHIP_UNRESOLVED_INVALID_LINK`; a row without a usable identifier is
  left out (see [Relationships](v2_data_handling.md#relationships)).
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

## The GUI, the view page, and `series`

- The GUI stops by itself when none of its pages has asked it anything for an
  hour and no run is active. A browser can stop the requests of a page that it
  hides: Safari stops them a few minutes after its window is hidden with
  Command-H, so that the GUI stops about an hour later, and it keeps running
  while Safari is only behind other windows. Start the GUI again from the icon
  or with the command.
- The `gui` command does not look for a GUI that is running. Started again
  within the hour after a page was closed, it starts a second GUI beside the
  first, on a port of its own, and the first one stops by itself an hour after
  the last request of its page. On Windows, the window of a GUI started from
  the icon is minimized, which makes the first one easy to miss.
- **Go to the normalization page** of the view page asks the browser for the
  tab of the normalization page by its name. A browser that does not give it,
  as a browser pane inside another app may not, leaves the button doing
  nothing; switch to that tab by hand then.
- `series` writes its CSV file as readable by its owner only on macOS and
  Linux. On Windows, the file takes the permissions of its folder.
- The view page and `series` give numbers to look at and to count: they do not
  say what causes what, or what to do, and a value that Garmin did not record
  stays empty.

## Distribution and integrations

- Hosted processing, Garmin authentication, Open-Meteo, JMA, Instagram,
  wellness/coaching interpretation, Parquet output, and automatic personal
  analysis are outside the stable scope.
- Stable v2.1.0 retains `tzdata` as a Windows-only runtime dependency and emits
  the bounded `TIMEZONE_DATA_UNAVAILABLE` diagnostic if IANA timezone data is
  unavailable in an incomplete environment. Validation covers GitHub Actions
  `windows-latest` with Python 3.11 and 3.15, one maintainer-owned physical
  Windows Production PyPI clean install of v1.2.1, and the release candidates
  v2.0.0rc1, v2.0.0rc4, v2.0.1rc1, and v2.1.0rc1 on one physical Windows 11 x64
  machine. This does not establish universal Windows compatibility.
- External-safe output is opt-in, month-granularity, Activities-only, and does
  not automatically upload or provide provider-specific privacy guarantees.
- Production PyPI `1.3.3` remains immutable. Its long description preserves the
  publication-time README snapshot, including pre-publication candidate
  wording. Production PyPI `1.4.0`, `1.4.1`, `1.5.0`, `1.6.0`, `1.7.0`,
  `1.7.1`, `2.0.0`, and `2.0.1` also remain immutable, and `2.1.0` is the
  current release artifact; current repository documentation is the
  maintained public truth for future builds.

The documented CLI and versioned Run-All output contract are stable for `2.x`.
Other Python modules are usable but are not all promoted to an independently
stable third-party API contract.

## Performance metrics and deferred promotion

- Hill Score Daily and Endurance Score Daily are stable v1.3 datasets.
- No Activity relationship is defined for either daily dataset. Date equality
  is not sufficient evidence for a join.
- Lactate Threshold is provided as candidate/audit infrastructure only: its
  candidates stay in the audit output and are not promoted to a public
  dataset until machine identity, units, timezone semantics, heart-rate
  authority, FTP/power authority, and public field/type rules are finalized.
- Lactate source sequence may order records within its source family, but it is
  not identity and never authorizes latest-wins behavior.
- Power conflicts remain review evidence and are not averaged, converted, or
  silently resolved.
