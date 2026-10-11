# v2.0.0 Data Handling

- Status: design record for stage A of the [v2.0.0 GUI Design](gui_design.md),
  agreed by the Human maintainer on 2026-10-11. Stage A pull requests implement
  it; v1.7.1 behavior applies until they do.
- Applies to: the CLI and the GUI alike, and one-shot `run-all` and Snapshot
  runs alike.
- Authority: every stage A pull request follows these rules. A pull request
  that needs a different rule changes this document first, with the Human
  maintainer's approval. Warning and error code names marked provisional are
  settled by the pull request that adds them.

## Rules

These rules come from the Human maintainer's decisions of 2026-10-11:

1. Problems in the data do not stop the whole run. The run leaves out only the
   file or row that has the problem, or keeps it, finishes, and reports what it
   did in warnings and in the output's records. No value is dropped or chosen
   silently.
2. A run stops only for safety reasons, for a folder or ZIP file that is not an
   Export, and when the input mixes Exports or accounts, including when a mix
   cannot be ruled out.
3. Normalized datasets keep one row per stable key. Values that disagree are
   left empty and marked, and every observed value is kept in an audit record.
4. The CLI and the GUI behave the same, and Snapshot runs follow the same rules
   as one-shot runs.

## Terms

- **Left out**: an input file or row that contributes nothing to the normalized
  datasets. Every left-out item is counted by reason in an audit record.
- **Kept with a warning**: the item stays in the output, possibly with an empty
  value and a marker, and every observed value is kept in an audit record.
- **Disagreement**: observations that share a stable key and differ in a value,
  with no rule that says which one is current. This covers daily datasets
  within one Export and across Snapshots, and every dataset within one Export.
- **Update**: in Activities, Gear, `activity_gear`, and Personal Records, a
  later Snapshot's value for the same record. A later Export reflects the
  user's own edits in Garmin Connect, so its value is the current one. The
  product cannot tell which of two daily values is right, so daily values that
  differ are disagreements, not updates.
- **Not read**: a file type or source field outside the product's scope. It is
  recorded by name and count, never by value, and does not change the status.

## Statuses and exit codes

| Result | Status | Exit |
|---|---|---|
| Finished; nothing left out and no warning | `PASS` | 0 |
| Finished; nothing left out; values kept with warnings | `PASS_WITH_WARNINGS` | 0 |
| Finished after leaving out at least one file or row | `PARTIAL_SUCCESS` | 3 |
| Stopped | Fatal error | 2 |

- `PARTIAL_SUCCESS` takes precedence over `PASS_WITH_WARNINGS`. FIT files that
  cannot be read completely are left out as in v1.x, and the same status now
  covers every other left-out file or row.
- Because `PARTIAL_SUCCESS` now covers more than FIT files, stage B reviews
  the page's result texts, which describe it in v1.7.1 as complete Activities
  with some FIT files left out.
- Optional families that are absent keep the v1.x status `SKIPPED_NOT_PRESENT`
  and the warning `OPTIONAL_FAMILY_NOT_PRESENT`.

## Rules by situation

Each item gives the v1.7.1 behavior and the v2.0.0 behavior.

### Values that disagree

- v1.7.1: one-shot daily datasets stop with `DAILY_METRICS_CONFLICT` or
  `PERFORMANCE_METRICS_CONFLICT`; Personal Records stop with
  `DIVERGENT_DUPLICATE`; Sleep rows whose direct duration fields differ stop;
  Snapshot builds stop with `SNAPSHOT_LIFECYCLE_FAILED` and report counts only;
  differing Endurance Score and UDS values across Snapshots are kept in the
  audit record and the row is removed; HRV sets the value to null and keeps
  only counts.
- v2.0.0:
  - The normalized row stays, one per stable key. Each value field that differs
    between the observations is empty, and the row's `disagreeing_fields` lists
    those fields. Fields that agree keep their value.
  - The dataset's audit record lists, for each disagreeing key and field, every
    observed value, how many observations gave it, and, in Snapshot runs, the
    Snapshots that gave it by import number.
  - Warning `VALUES_DISAGREE` (provisional) per family, with the number of keys.
    Status `PASS_WITH_WARNINGS`.
  - Observation-grain datasets (Race Prediction, Acute Training Load, Training
    Readiness, VO2Max, and Training History) keep one row per observation; a
    disagreement is two observations with the same full stable key.

### Changes across Snapshots

These apply to Activities, Gear, `activity_gear`, and Personal Records.

- v1.7.1: each field takes the later Snapshot's value; an explicit null or
  empty value keeps the earlier value; a record missing from a later Export is
  kept; the per-field record is deleted after `snapshot run-all`, and no
  warning is given.
- v2.0.0:
  - Each field takes its value from the latest Snapshot, in import order, that
    contains the field.
  - An explicit null or empty value in a later Snapshot means that the value was
    removed, so the field becomes empty.
  - A field that a later Snapshot does not contain at all was not observed in
    that Snapshot, so the earlier value stays.
  - A record that a later Snapshot does not contain stays, and the audit record
    keeps the import number of the last Snapshot that contained it.
  - Every earlier value is kept in the dataset's audit record with the Snapshot
    that gave it. Warning `VALUES_UPDATED` (provisional) reports how many
    records changed, and `RECORDS_NOT_IN_LATEST_SNAPSHOT` (provisional) how many
    records the latest Snapshot does not contain. Status `PASS_WITH_WARNINGS`.
  - Within one Snapshot, two different values for one record are a
    disagreement.

### Duplicates

- v1.7.1: a repeated Activity, Gear record, or `activity_gear` link stops with
  `RELATIONSHIP_CONTRACT_FAILED`, even when the rows are identical; a repeated
  Personal Record stops with `DIVERGENT_DUPLICATE`; identical daily rows and FIT
  files are merged and counted.
- v2.0.0:
  - Records with the same stable key and the same values are merged into one
    row, and the audit record counts how often they appeared.
  - When whole files repeat, as when an Export is given twice or together with
    its extracted copy, warning `INPUT_DUPLICATE_SOURCES` (provisional) is given
    once per run. Status `PASS_WITH_WARNINGS`. Repeated records inside one file
    are counted without a warning.
  - Identifiers written in two ways, such as `" 123"` and `123`, are the same
    identifier, as in v1.7.1.

### Mixed input

- v1.7.1: a parent folder with several Exports passes the pre-run check and
  stops with `RELATIONSHIP_CONTRACT_FAILED`, which the GUI reports as an
  internal check.
- v2.0.0:
  - An input holds one Export. Several Exports with the same content are
    duplicates (above).
  - Several Exports with different content, or records from different accounts,
    stop the run with `INPUT_MULTIPLE_EXPORTS` (provisional). When the product
    cannot rule out a mix, it stops.
  - The pre-run check reports the same result as the run.
  - Stage A3 settles the evidence used to tell Exports and accounts apart. Any
    account evidence stays inside the run and is never written to an output.

### Files that cannot be read

- v1.7.1: a JSON file that is not UTF-8 or not JSON stops the run; a UTF-8 byte
  order mark stops the Activities, Gear, and Personal Records readers; a Snapshot
  build stops on any such JSON file; an unreadable ZIP file anywhere in the
  input stops the run; a JSON or FIT file over 128 MiB stops the run.
- v2.0.0:
  - A UTF-8 byte order mark is accepted everywhere.
  - A JSON file that cannot be read, a ZIP file inside the input that cannot be
    read, and a JSON or FIT file over the size limit are left out with a reason.
    Warning `DATA_FILE_LEFT_OUT` (provisional), status `PARTIAL_SUCCESS`.
  - A FIT file that cannot be read completely is left out as in v1.x
    (`FIT_PARSE_INCOMPLETE`).
  - If no Activities record remains, the run stops as an input that is not an
    Export.
  - A damaged Export ZIP file stops the run (`INPUT_ZIP_CORRUPT`); see
    [An Export given as a ZIP file](#an-export-given-as-a-zip-file).

### Rows and values with problems

- v1.7.1: a row without an identity stops the run for Activities, Gear, links,
  and Personal Records, and is counted without a warning in daily datasets; a
  passed-through value of an unexpected JSON type stops the run at the end with
  `OUTPUT_EXPERIENCE_FAILED`, or is set to null without a warning in daily
  datasets; text with a lone UTF-16 surrogate and timestamps out of range stop
  the run, some without an error code; a FIT sport field with an unexpected
  layout stops with `FIT_PROCESSING_FAILED`; a Race Prediction row that lacks
  one distance is removed.
- v2.0.0:
  - A row without a usable identity (no identifier and no fallback fields, an
    identifier of an unsupported type, or an Activity identifier of 0) or
    without a required value (such as a date) is left out with a reason.
    Warning `DATA_ROW_LEFT_OUT` (provisional), status `PARTIAL_SUCCESS`.
  - A value of an unexpected type becomes empty in the normalized row, and the
    raw value is kept in the audit record. Warning `DATA_VALUE_INVALID`
    (provisional), status `PASS_WITH_WARNINGS`.
  - A value that the source marks as invalid or absent, such as the FIT
    invalid value that an HRV reading carries when nothing was measured, is
    an absent value: the field is empty, the audit record counts it, and no
    warning is given, because such a value marks that nothing was measured,
    not a problem in the data. v1.7.1 counts the HRV ones in
    `DAILY_METRICS_REVIEW_REQUIRED`.
  - A timestamp out of range leaves the derived date and time empty and keeps
    the raw value, with the same warning.
  - Text with a lone UTF-16 surrogate, such as a truncated emoji, is written
    with U+FFFD in its place, and the field is counted. Warning
    `DATA_TEXT_REPAIRED` (provisional).
  - A FIT field with an unexpected layout is treated as an unknown value with
    the `DATA_VALUE_INVALID` warning; the FIT file is not left out.
  - A Race Prediction row keeps the predictions it has, and a missing one is
    empty.

### Relationships

- v1.7.1: a Personal Record, `activity_gear` link, or FIT lap whose valid link
  points to a record that is not in the output is removed, and only counts
  remain; a Personal Record whose activity link is missing or malformed stops
  the run.
- v2.0.0:
  - These rows stay in the normalized output with the relationship status
    `unresolved` and a reason. Warning `RELATIONSHIP_UNRESOLVED_VALID_LINK`, as
    in v1.x. Status `PASS_WITH_WARNINGS`.
  - A Personal Record whose activity link is missing or malformed stays with the
    status `unresolved`; an activity identifier of 0 stays `independent`.
  - Identifiers are compared after trimming spaces and leading zeros, and
    digit-only text identifiers in `activity_gear` are written as integers, as
    in v1.7.1; the Output Contract is corrected to say so.

### Values taken from several source fields

- v1.7.1: when a field has several source names, the first one present is used
  without a record (Sleep score and stages, UDS date, steps, and distance, and
  the Gear type); some values are filled from another field without a mark in
  the row (the Sleep day from the end time, the Activity start from
  `beginTimestamp`, and the Sleep duration from the stage sum or a direct
  field); an unknown FIT sub-sport code becomes null and the number is lost; an
  Activity without a date has the text `None` as its month in the External-safe
  Pack.
- v2.0.0:
  - When several source names are present with different values, the field is a
    disagreement. When they agree, or only one is present, it is used. A name
    whose value is null counts as absent.
  - Filled values are marked in the row: `sleep_day_source`,
    `sleep_duration_source`, and `start_time_source`.
  - HRV values that disagree follow
    [Values that disagree](#values-that-disagree): the values are kept in the
    audit record. Run Quality names the reason after the rule instead of
    `CONFLICT_PRESERVED_NO_WINNER`, and the HRV `date_basis` names the timezone
    that was used.
  - An unknown FIT sub-sport keeps its number in `sub_sport_code`; `sub_sport`
    stays empty.
  - The External-safe Pack leaves the month empty for an Activity without a
    date.

### Files and fields that are not read

- v1.7.1: files other than `.json`, `.fit`, and `.zip` (for example `.tcx`,
  `.gpx`, and `.csv`) and ZIP files inside ZIP files are skipped without a
  record; Activities, Gear, and Personal Records files whose names differ only
  in letter case are detected but not read; source fields outside each
  dataset's field list are dropped without a count; unknown FIT messages and
  developer fields are skipped, and the FIT audit always reports 0 for them.
- v2.0.0:
  - Files that are not read are listed in `run_manifest.json`, and their count
    appears in `START_HERE.md`. The status does not change.
  - File names are matched without regard to letter case.
  - Source fields outside a dataset's field list are counted by name in the
    dataset's audit record, without values.
  - Unknown FIT messages and developer fields are counted in the FIT audit as
    not read, and they do not make a FIT file incomplete.

### An Export given as a ZIP file

- v1.7.1: only an extracted folder is accepted. A ZIP file inside the folder is
  read one level deep, and every member counts against the archive limits,
  including members that are not read.
- v2.0.0 (stage A1):
  - `run-all`, `doctor --input`, `snapshot register`, and
    `normalize-activities` accept the downloaded Export ZIP file as well as the
    extracted folder. A file whose name ends in `.zip`, in any letter case, is
    a ZIP file; a folder with such a name is a folder. `INPUT_NOT_DIRECTORY`
    keeps its name and now means that the input is neither a folder nor a ZIP
    file; stage A5 reviews the name.
  - The Export's own files decide the result, not the form in which the
    Export is given: a run of the same Export gives the same outputs, the same
    recorded paths, and the same Snapshot content identity from a ZIP file as
    from a folder, however deeply it is wrapped in other folders. Only the
    limits on reading from a ZIP file, below, differ between the forms.
  - A ZIP file is read as the folder extracted from it: the same files at the
    same paths. ZIP files inside it are read one level deep and recorded as
    `inner.zip!member`, as in a folder; a ZIP file inside those is not read.
  - Folders around the Export are left out of the paths. While everything in
    the ZIP file, or in the selected folder, is inside one folder that is not
    part of the Export's own layout (`DI_CONNECT`, `DI-GOLF`, or a name that
    starts with `DI-Connect-`, in any letter case), the root moves into that
    folder, at any depth. Operating-system metadata such as `__MACOSX` and
    `.DS_Store` is ignored. v1.7.1 kept the names of such folders in the
    recorded paths, so for a folder given this way, the output changes from
    v1.7.1.
  - Every member is checked, including members that are not read: a path
    outside the folder, a link, or encryption stops the run.
  - The size limits apply only to what is read into memory or opened:
    - a JSON or FIT file: at most 128 MiB;
    - a ZIP file inside the Export: at most 100,000 files and 2 GiB read from
      it, and, inside an Export ZIP file, at most 2 GiB itself;
    - a compressed member that is read: a compression ratio of at most 200.

    Members that are not read do not count, in a ZIP file and in a folder
    alike. `snapshot register` reads every member of a ZIP file inside the
    Export, and copies the other files to the store without reading them into
    memory. A member that is read and exceeds one of these limits stops the
    run as unsafe input (`INPUT_DISCOVERY_FAILED` in `run-all`), as in v1.7.1.
  - From an Export ZIP file, at most 2 GiB and 400,000 files in total are read
    into memory; beyond that, the run stops with `INPUT_TOO_LARGE`, and the
    extracted folder can be used instead. A folder has no such limit. A later
    stage A pull request revises reading so that the whole Export does not
    have to be held in memory, and raises these limits.
  - A ZIP file inside the Export ZIP file is opened in memory up to 128 MiB; a
    larger one is copied to a private temporary folder, read, and deleted (see
    [Security and Privacy Boundary](security_and_privacy_boundary.md)).
  - An Export ZIP file that cannot be opened, ends early, or has a member that
    fails its CRC check stops the run with `INPUT_ZIP_CORRUPT`. A damaged ZIP
    file inside the Export still stops the run with `INPUT_DISCOVERY_FAILED`
    until stage A3 leaves it out with a reason.
  - The Snapshot Store format does not change.

### Stops that remain

The run stops with exit 2 and publishes no output for:

- Safety: unsafe ZIP members (paths outside the folder, links, or encryption),
  symbolic links in the input, a damaged Export ZIP file
  (`INPUT_ZIP_CORRUPT`), and exceeded limits on the size, number, or
  compression ratio of the members that are read, including the limits for the
  whole Export ZIP file (`INPUT_TOO_LARGE`).
- An input that is not an Export: no Activities (`ACTIVITIES_NOT_FOUND`) or no
  Activities records (`ACTIVITIES_EMPTY`).
- Mixed Exports or accounts (`INPUT_MULTIPLE_EXPORTS`).
- An Export that changes during the run (`INPUT_CHANGED`).
- The output: it already exists, it cannot be written, or its path is too long.
- The Snapshot Store: locked by an interrupted registration
  (`SNAPSHOT_STORE_LOCKED`, provisional) or failing verification.
- Internal checks that data cannot trigger.

Every stop has a specific code; errors that v1.7.1 reports only as
`RUN_ALL_FAILED` get their own codes.

## Output shape

- `run_all_version` becomes 2.
- Normalized datasets gain `disagreeing_fields` (a list of field names, empty
  when the row has no disagreement; written with `;` between names in CSV
  projections). Sleep gains `sleep_day_source` and `sleep_duration_source`,
  Activities gain `start_time_source`, and FIT sessions gain `sub_sport_code`.
  The relationship status fields gain the value `unresolved`.
- Audit records gain sections for disagreements, updates, left-out items by
  reason, merged duplicates, and source fields that were not read.
- New warning codes (provisional names): `VALUES_DISAGREE`, `VALUES_UPDATED`,
  `RECORDS_NOT_IN_LATEST_SNAPSHOT`, `INPUT_DUPLICATE_SOURCES`,
  `DATA_FILE_LEFT_OUT`, `DATA_ROW_LEFT_OUT`, `DATA_VALUE_INVALID`, and
  `DATA_TEXT_REPAIRED`. `DAILY_METRICS_REVIEW_REQUIRED` is replaced by them.
- New error codes: `INPUT_ZIP_CORRUPT` and `INPUT_TOO_LARGE` (stage A1), and
  `INPUT_MULTIPLE_EXPORTS` and `SNAPSHOT_STORE_LOCKED` (provisional names).
- Warnings carry codes and counts only: no paths, values, or identifiers.
  Snapshots are named by import number. User labels for Snapshots appear only in
  local output and never in the Support Bundle or the External-safe Pack.
- The External-safe Pack keeps its columns.

## Checks of earlier outputs

- `validate-handoff`, `doctor --run-output`, and `support-bundle` accept an
  output with `run_all_version` 2 when the installed version produced it.
- An output that contains `diagnostics/` and was produced by another version,
  including every v1.x output from v1.4.0 on, is rejected as in v1.x; rerun
  Run-All. Outputs produced before v1.4 keep the legacy handling.

## Snapshot Stores

- The store format stays at version 1. Existing stores load and verify without
  migration, and every registered Snapshot is used. If the format must change
  later, the change is an automatic migration that keeps the original data
  intact.
- Snapshot runs follow the one-shot rules in this document; a Snapshot build no
  longer stops for problems in the data. Sleep rows without `calendarDate` take
  the sleep day from the end time, as in one-shot runs, instead of being held
  back.
- Registering the same Export as a ZIP file or as its extracted folder gives
  the same content identity, however deeply it is wrapped in other folders; a
  test checks this from stage A1 on.
- A Snapshot that v1.7.1 registered from a folder inside such wrapping folders
  keeps their names in its paths, so registering the same Export again gives a
  different content identity, and the store holds a second Snapshot with the
  same files. The normalized datasets stay the same, because the records are
  the same, but the Snapshot lineage and the summaries count two Snapshots.
  Stage A3 recognizes the same Export by the content of its files rather than
  by its paths, so that such a Snapshot is not counted as a second Export.
- A test keeps a store in the v1.7.1 format as a fixed synthetic fixture, with
  the script that made it. Every stage A pull request checks that it loads
  without migration and that every Snapshot is used.

## Golden outputs and tests

- When a stage A pull request changes a golden output, its description explains
  why. A golden output for an input that the change does not concern stays
  byte-identical.
- At the stage A checkpoint, the CLI is checked on its own with the synthetic
  golden outputs, and the migration notes are drafted.

## Migration notes outline (v1.7.1 to v2.0.0)

- Exit codes: runs that stopped with exit 2 for problems in the data now finish
  with exit 3 or 0, and the warnings say what was left out or kept.
- Outputs: `run_all_version` 2, the new fields and audit sections, and the new
  warning codes. Rerun Run-All; earlier outputs are not converted.
- Snapshots: existing stores need no migration; rerun `snapshot run-all`.
- Input: the downloaded Export ZIP file can be used directly. A folder that
  holds only one folder outside the Export's layout is read from that folder.
- CLI: the pre-run checks that the GUI performed in v1.7.1 apply to the CLI,
  errors report what happened and the next step, and `Ctrl+C` reports the
  cancellation.
