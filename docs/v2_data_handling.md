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
- v2.0.0 (stage A2a for one-shot runs and stage A2b-1 for daily datasets in
  Snapshot runs; Activities, Gear, `activity_gear`, and Personal Records
  follow in stage A3 within one Export or Snapshot, and their values across
  Snapshots are updates, see
  [Changes across Snapshots](#changes-across-snapshots)):
  - The normalized row stays, one per stable key. Each value field that differs
    between the observations is empty, and the row's `disagreeing_fields` lists
    those fields. Fields that agree keep their value.
  - The dataset's audit record lists, for each disagreeing key and field, every
    observed value, how many observations gave it, and, in Snapshot runs, the
    Snapshots that gave it by number. In a Snapshot run, each time a Snapshot
    gives a value counts as one observation, and `snapshots` lists the
    Snapshot numbers, for example `{"value": 80, "observation_count": 2,
    "snapshots": [1, 3]}`; user labels never appear there. Snapshots are
    numbered in the order of their Exports' observation times (see
    [Changes across Snapshots](#changes-across-snapshots)).
  - Warning `VALUES_DISAGREE` per family, with the number of keys. Status
    `PASS_WITH_WARNINGS`. Stage A2a settles the name.
  - Observation-grain datasets (Race Prediction, Acute Training Load, Training
    Readiness, VO2Max, and Training History) keep one row per observation; a
    disagreement is two observations with the same full stable key.
  - Within one Export, a null or missing value is absent: the field takes the
    value of the observations that have one, and the audit record counts the
    observations without one in `absent_value_counts`. Only two different
    values are a disagreement, so a Sleep row whose source field is missing and
    one where it is null no longer differ.
  - Daily datasets apply the same rule across Snapshots (stage A2b-1): all the
    Snapshots' observations of a key are compared together, whatever their
    order, so a value that a later Snapshot leaves null or leaves out stays,
    and the audit record counts the observation without it. In Activities,
    Gear, `activity_gear`, and Personal Records, an explicit null in a later
    Snapshot means instead that the value was removed (see
    [Changes across Snapshots](#changes-across-snapshots)). The rules differ
    because those records reflect the user's own edits in Garmin Connect, so
    the order of Snapshots means something, while daily values are computed by
    Garmin and the product cannot tell which of two is right: a null says only
    that this observation has no value.
  - As a consequence, a daily value or record that the user deleted in Garmin
    Connect stays in the normalized output from the earlier Snapshot: the
    deletion is not shown, because the product cannot tell a deletion from a
    value that Garmin left out of one Export. The earlier value and the
    Snapshots that gave it are kept in the audit record.
  - Each field is compared on its normalized value, including a field computed
    from others, such as the Sleep duration from the stage minutes. When every
    observation gives the same computed value, it stays, even if the fields it
    comes from disagree: for deep 60 and light 120 minutes against deep 90 and
    light 90 minutes, the stage minutes are empty and the duration of 180
    minutes stays. Every observation shows that value, so none is chosen, and
    an empty field means unknown, not zero. When the computed values differ,
    the field is empty and listed like any other.
  - Flags and statuses describe the merged row. A UDS `raw_has_*` flag is true
    when any observation had that source group. The Sleep flags follow the
    merged values, and a Sleep row whose start, end, or window disagrees has
    the status `needs_review`, the limitation `values_disagree`, and the reason
    `sleep_interval_values_disagree_no_selection`.
  - The audit record's `disagreements` section has one entry per key with the
    `key`, its `observation_count`, and its `fields`; each field lists its
    `values`, each with the `value` and the `observation_count` of the
    observations that gave it, numbers by size and other values by their JSON
    text. `disagreement_key_count` counts the keys, in the audit record and in
    the run summary's family results.
  - Run Quality counts the keys in `conflict_summary` with the reason
    `VALUES_DISAGREE`, which replaces `CONFLICT_PRESERVED_NO_WINNER`. A
    disagreement is not a review item, so `DAILY_METRICS_REVIEW_REQUIRED` no
    longer counts it.
  - The Support Bundle and the External-safe Pack carry counts only; the
    observed values stay in the audit records of the local output.
  - `DAILY_METRICS_CONFLICT` and `PERFORMANCE_METRICS_CONFLICT` are removed.
    HRV rows whose values disagree have the `dedupe_status`
    `same_day_values_disagree` instead of
    `review_required_same_day_differing_values`.

### Changes across Snapshots

These apply to Activities, Gear, `activity_gear`, and Personal Records.

- v1.7.1: each field takes the later Snapshot's value; an explicit null or
  empty value keeps the earlier value; a record missing from a later Export is
  kept; the per-field record is deleted after `snapshot run-all`, and no
  warning is given.
- v2.0.0 (stage A2b-2, merge rules v2.1):
  - Snapshots are ordered, and numbered from 1, by the observation times of
    their Exports (`export_observed_at`), not by the order of registration.
    The numbers are given again in every run, so an older Export registered
    later changes the numbers after it: after Exports from January and March,
    an Export from February registered later becomes Snapshot 2, and the March
    Export becomes Snapshot 3. This applies to the daily datasets as well.
  - Each top-level field takes its value from the latest Snapshot that
    contains the field. A nested object or list is one value and is replaced
    whole.
  - An explicit empty value in a later Snapshot, that is null, an empty
    string, an empty list `[]`, or an empty object `{}`, means that the value
    was removed: the field takes that empty value.
  - A field that a later Snapshot does not contain at all was not observed in
    that Snapshot, so the earlier value stays.
  - A record that a later Snapshot does not contain stays, and the audit record
    keeps the number of the last Snapshot that contained it. As a consequence,
    when Garmin gives a Personal Record a new `personalRecordId` each time it
    is improved, the earlier record stays, with the values of the last
    Snapshot that contained it, `current` included.
  - An `activity_gear` link that the latest Snapshot does not contain is
    removed from the normalized dataset when the latest Snapshot has Gear
    links, that is a Gear file with the `gearActivityDTOs` object, even an
    empty one, and contains both the link's Activity and its Gear: the
    Activity's Gear was changed or removed, for example from shoe A to shoe
    B, and keeping the earlier link would count the Activity for both shoes.
    The audit record keeps the removed link with the last Snapshot that
    contained it. When the latest Snapshot has no Gear file, a Gear file
    without `gearActivityDTOs`, or lacks the Activity or the Gear, for
    example because the Gear was deleted, the product cannot tell a change
    from a record that the Export left out, so the link stays like any other
    record that the latest Snapshot does not contain.
  - A record with a removed value is normalized as a one-shot run normalizes
    the same row: a removed start time of an Activity leaves its local date
    and time empty. Until stage A3, a removed value that the normalized
    dataset does not accept stops the run as it does in a one-shot run: an
    empty string for a number, an empty list or object for a single value
    (`OUTPUT_EXPERIENCE_FAILED`), or a null Activity of a Personal Record
    (`RELATIONSHIP_CONTRACT_FAILED`), all with exit 2. From stage A3, such a
    row is left out and counted by reason (exit 3).
  - Every earlier value is kept in the dataset's audit record:
    `audit/activities.json`, `audit/gear.json`, `audit/activity_gear.json`,
    and `audit/personal_records.json` (format
    `garmin-running-data-normalizer-dataset-audit-v1`). `updates` lists each
    record whose values changed, by its `key` as the normalized dataset names
    it, with each changed field, its `values` in Snapshot order, and the
    `snapshots` that gave each value, for example `name` "Morning run" in
    Snapshot 1, then "Morning run 10k" in Snapshots 2 to 4. A removed value is
    listed as the empty value that removed it. Fields keep their names in the
    Export, because the earlier values are what the Export said: the Export's
    `description`, for example, is the normalized `memo_text_raw`.
    `not_in_latest_snapshot` lists the records kept although the latest
    Snapshot does not contain them, with their `last_seen_snapshot`, and
    `removed_links` (in `activity_gear` only) the removed links.
  - Every run writes these four audit records. A one-shot run reads one
    Export, so its records have the `observation_scope`
    `ONE_EXPORT_OBSERVATION`, the `record_count` of the normalized dataset,
    zero counts, and empty lists, and the same Export always gives the same
    bytes. Snapshot runs have `REGISTERED_SNAPSHOT_OBSERVATIONS`.
  - Warning `VALUES_UPDATED` gives, per family, the number of records whose
    values changed: a field that changed from one value to another, from a
    value to an empty value, or from an empty value to a value counts, and a
    field that only appears in or disappears from a Snapshot does not.
    Values that differ only in how they are written are the same value: every
    empty value (null, `""`, `[]`, or `{}`) is one empty value, and numbers
    are compared by their value, so `1000` and `1000.0` are the same, also
    inside lists and objects; a boolean is not a number. Such a difference
    neither counts nor starts a new entry in the audit record's `values`, an
    entry shows the value of its latest Snapshot, and the normalized dataset
    keeps the latest Snapshot's value as it was written.
    An `activity_gear` link removed as above counts for the Gear family.
    Warning `RECORDS_NOT_IN_LATEST_SNAPSHOT` gives, per family, the number of
    records kept although the latest Snapshot does not contain them. The run
    summary's family results carry the two counts as `updated_record_count`
    and `not_in_latest_snapshot_count`. Status `PASS_WITH_WARNINGS` (exit 0).
    Stage A2b-2 settles both names.
  - Run Quality binds the four audit records by digest, as it does the daily
    audit records. Their values stay in the local output: the Support Bundle,
    the External-safe Pack, and the merge summaries carry counts only.
  - Within one Snapshot, or in two Snapshots observed at the same time, two
    different values for one record still stop the build until stage A3,
    which makes them a disagreement.

### Duplicates

- v1.7.1: a repeated Activity, Gear record, or `activity_gear` link stops with
  `RELATIONSHIP_CONTRACT_FAILED`, even when the rows are identical; a repeated
  Personal Record stops with `DIVERGENT_DUPLICATE`; identical daily rows and FIT
  files are merged and counted.
- v2.0.0:
  - Records with the same stable key and the same values are merged into one
    row, and the audit record counts how often they appeared.
  - When the input holds the same Export more than once, as when an Export is
    given twice or together with its extracted copy, it is read once, and
    warning `INPUT_DUPLICATE_SOURCES` is given once per run with the number of
    copies not read (stage A3a, which settles the name; see
    [Mixed input](#mixed-input)). Status `PASS_WITH_WARNINGS`. Repeated records
    inside one file are counted without a warning, and so are files with the
    same content at different places in one Export, such as several files
    that hold an empty list: they are not a repeated Export.
  - Identifiers written in two ways, such as `" 123"` and `123`, are the same
    identifier, as in v1.7.1.

### Mixed input

- v1.7.1: a parent folder with several Exports passes the pre-run check and
  stops with `RELATIONSHIP_CONTRACT_FAILED`, which the GUI reports as an
  internal check.
- v1.7.1 and stage A1 also produce one output from two Exports that share no
  Activity, as when the Exports of two accounts sit in one folder, and leave
  out the uploaded FIT files of an Export ZIP file that sits in the selected
  folder.
- v2.0.0 (stage A3a):
  - An input holds one Export. An Export's root is the folder that holds its
    own layout folders (`DI_CONNECT`, `DI-GOLF`, or a name that starts with
    `DI-Connect-`, in any letter case), or a ZIP file in the input that holds
    them. An input with no root or with one root holds one Export.
  - Several roots hold the same Export when they hold the same files: the same
    paths and sizes, counted from each root, including the files that are not
    read, and the same content for the files that are read. Operating-system
    metadata, such as `.DS_Store`, is left out, as when the files are read.
    The Export is then read once, from the first root in path order, with
    warning `INPUT_DUPLICATE_SOURCES` (see [Duplicates](#duplicates)).
  - Roots that differ in any file, including a root that holds only part of
    another, are different Exports: the run stops with
    `INPUT_MULTIPLE_EXPORTS` (exit 2) and publishes nothing, and the next step
    is to select one Export, or to register each Export as a Snapshot. Stage
    A3a settles the name.
  - The records of one Export name one account: Activities in
    `userProfileId`, and Gear, Hill Score, and the other daily metrics in
    `userProfilePk` or `userProfilePK`. Only these files are used, because
    other files of an Export, such as those about connections, groups, or
    challenges, name other people's accounts. Values are compared as numbers,
    so `" 123"` and `123` are one account. Records that name two or more
    accounts stop the run with `INPUT_MULTIPLE_EXPORTS`; an Export whose
    records name no account is not stopped for that reason. The accounts are
    compared within the run only and never appear in an output, a Snapshot
    Store, a warning, an error message, the GUI, or a log.
  - A root is read as if it were given alone: the paths of its files are
    counted from the root, so an Export gives the same outputs however it is
    given. An Export ZIP file in the selected folder is read as when it is
    selected directly, with the ZIP files inside it.
  - Files inside a root are part of that Export and are read, as before: a FIT
    file placed next to `DI_CONNECT` in the selected Export folder is read. A
    FIT file names no account, so such a file of someone else cannot be told
    apart.
  - When the input has a root, the JSON, FIT, and ZIP files outside every root
    are not read, because they may belong to someone else. `run_manifest.json`
    lists them under `files_not_read` with the reason `outside_export_root`,
    and `START_HERE.md` gives their number; the status does not change. Their
    names never reach the Support Bundle or the External-safe Pack. An input
    without a root is read as before.
  - The pre-run check (`doctor --input`, which the GUI uses) reports the same
    result as the run: `INPUT_MULTIPLE_EXPORTS` as an error, and
    `INPUT_DUPLICATE_SOURCES` as a warning that does not block the run.
  - `normalize-activities` and `snapshot register` choose the Export in the
    same way; see [Snapshot Stores](#snapshot-stores) for registration.
  - Warnings and errors name no folder or file. The accounts are compared
    again for each run, which reads the account files once more.

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
    whose value is null counts as absent. Stage A2a applies this to the direct
    Sleep duration fields, which stopped the run in v1.7.1; the audit record
    counts such rows in `direct_aliases_disagree_count`. Stage A4 applies it to
    the other fields.
  - Filled values are marked in the row: `sleep_day_source`,
    `sleep_duration_source`, and `start_time_source`.
  - HRV values that disagree follow
    [Values that disagree](#values-that-disagree): the values are kept in the
    audit record, and Run Quality names the reason `VALUES_DISAGREE` instead of
    `CONFLICT_PRESERVED_NO_WINNER` (stage A2a). The HRV `date_basis` names the
    timezone that was used.
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
    From stage A3a, an Export ZIP file in the selected folder is read as when
    it is selected directly (see [Mixed input](#mixed-input)).
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
  - Files are read one at a time, in a folder and in a ZIP file alike. Each
    file is read once at the start of a run for its size and digest, again
    when a normalizer uses it, and once more at the end to check that the
    input did not change; a file whose content differs from the first reading
    stops the run with `INPUT_CHANGED`. Memory use therefore follows the size
    of the output, that is, the normalized records and the files written, not
    the size of the Export.
  - The size limits apply only to what is read or opened:
    - a JSON or FIT file: at most 128 MiB;
    - a ZIP file inside the Export: at most 100,000 files and 2 GiB read from
      it, and, inside an Export ZIP file, at most 2 GiB itself;
    - a compressed member that is read: a compression ratio of at most 200.

    Members that are not read do not count, in a ZIP file and in a folder
    alike. `snapshot register` reads every member of a ZIP file inside the
    Export. A member that is read and exceeds one of these limits stops the
    run as unsafe input (`INPUT_DISCOVERY_FAILED` in `run-all`), as in v1.7.1.
  - From an Export ZIP file, one reading reads at most 64 GiB and 4,000,000
    files in total; beyond that, the run stops with `INPUT_TOO_LARGE`, and the
    extracted folder can be used instead. These totals are far above what an
    Export holds. They bound how long a reading of a damaged or malicious ZIP
    file takes and how much it copies to the temporary folder, not memory. A
    folder is already on disk and has no such totals.
  - Every ZIP file inside an Export ZIP file is copied, when it is first used,
    to a private temporary folder, stays there until the run ends, and is then
    deleted (see [Security and Privacy Boundary](security_and_privacy_boundary.md)).
    Before the first copy, the free space of the temporary folder is checked
    against the size of all these ZIP files. When it is too small, or runs out
    while copying, the run stops with `TEMP_SPACE_INSUFFICIENT`; the next step
    is to free some space or to use the extracted folder. A ZIP file inside a
    folder is read where it is.
  - An Export ZIP file that cannot be opened, ends early, or has a member that
    fails its CRC check stops the run with `INPUT_ZIP_CORRUPT`. A damaged ZIP
    file inside the Export still stops the run with `INPUT_DISCOVERY_FAILED`
    until stage A3c leaves it out with a reason.
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
- The temporary folder: not enough free space to read an Export ZIP file
  (`TEMP_SPACE_INSUFFICIENT`).
- The Snapshot Store: locked by an interrupted registration
  (`SNAPSHOT_STORE_LOCKED`, provisional) or failing verification.
- Internal checks that data cannot trigger.

Every stop has a specific code; errors that v1.7.1 reports only as
`RUN_ALL_FAILED` get their own codes.

## Output shape

- `run_all_version` becomes 2 (stage A2a).
- Normalized datasets gain `disagreeing_fields` (a list of field names, empty
  when the row has no disagreement; written with `;` between names in CSV
  projections). Sleep gains `sleep_day_source` and `sleep_duration_source`,
  Activities gain `start_time_source`, and FIT sessions gain `sub_sport_code`.
  The relationship status fields gain the value `unresolved`.
- Stage A2a adds `disagreeing_fields` to every row of the 17 datasets: the
  Schema Catalog declares it as a list of strings that is always present and
  never null, and the field count goes from 224 to 241.
  `analysis/activities.csv` gains the last column `disagreeing_fields`, and
  `analysis/performance_metrics_daily.csv` the last columns
  `hill_disagreeing_fields` and `endurance_disagreeing_fields`.
- A field that a disagreement can leave empty is nullable in the Schema
  Catalog. v1.7.1 declared these non-null: the Hill and Endurance
  `overall_score`, the four Race Prediction times, `vo2max`, and
  `training_status`.
- `normalize-activities` (the Golden Path) keeps the v1 shape: its output has
  no `disagreeing_fields`, which only Run-All adds.
- Run Quality's format and schema version become v2
  (`garmin-running-data-normalizer-run-quality-v2`, `garmin-run-quality:v2`),
  and so does the Support Bundle's copy of it, because the closed list of
  reasons changes (stage A2a). Source Completeness and Doctor keep v1.
- The daily audit records become v2 (`daily-metric-audit-v2`,
  `performance-daily-audit-v2`, and `hrv-daily-audit-v2`) with
  `disagreement_key_count`, `disagreements`, and `absent_value_counts`;
  `divergent_duplicate_count`, the Hill and Endurance
  `divergent_duplicate_key_count`, and the HRV `same_day_conflict_count` are
  removed (stage A2a).
- Audit records gain sections for disagreements, updates, left-out items by
  reason, merged duplicates, and source fields that were not read.
- Stage A2b-2 adds the audit records `audit/activities.json`,
  `audit/gear.json`, `audit/activity_gear.json`, and
  `audit/personal_records.json` to every run, so the synthetic Run-All output
  grows from 46 to 50 files, and Run Quality's authority evidence and the
  Support Bundle's copy of Run Quality name them.
- New warning codes: `VALUES_DISAGREE` (stage A2a), `VALUES_UPDATED` and
  `RECORDS_NOT_IN_LATEST_SNAPSHOT` (stage A2b-2), `INPUT_DUPLICATE_SOURCES`
  (stage A3a), and, with provisional names, `DATA_FILE_LEFT_OUT`,
  `DATA_ROW_LEFT_OUT`, `DATA_VALUE_INVALID`, and `DATA_TEXT_REPAIRED`.
- Stage A3a adds `files_not_read` to `run_manifest.json` and
  `input_warning_count` to `run_summary.json`, each only when there is
  something to report, so the outputs of an input with one Export and no files
  outside it do not change.
  `DAILY_METRICS_REVIEW_REQUIRED` is replaced by them.
- New error codes: `INPUT_ZIP_CORRUPT`, `INPUT_TOO_LARGE`, and
  `TEMP_SPACE_INSUFFICIENT` (stage A1), `INPUT_MULTIPLE_EXPORTS` (stage A3a),
  and `SNAPSHOT_STORE_LOCKED` (provisional name).
- Warnings carry codes and counts only: no paths, values, or identifiers.
  Snapshots are named by number. User labels for Snapshots appear only in
  local output and never in the Support Bundle or the External-safe Pack.
- The External-safe Pack keeps its columns.

## Checks of earlier outputs

- `validate-handoff`, `doctor --run-output`, and `support-bundle` accept an
  output with `run_all_version` 2 when the installed version produced it
  (stage A2a).
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
  back (stage A2b-1); the end time identifies the same sleep across Snapshots,
  and a row with neither is still held back until stage A3.
- Stage A2b-1 removes the stops for daily datasets: values that differ across
  Snapshots, within one Snapshot, or between two Snapshots observed at the same
  time follow [Values that disagree](#values-that-disagree), with the Snapshot
  numbers. Endurance Score and UDS no longer remove the day, and
  `snapshot/canonical_merge_summary.json` and `run_summary.json` no longer hold
  the observed values (`observed_variants`); the values stay only in the audit
  records. The same Activity twice with different values in one Snapshot, or
  in two Snapshots observed at the same time, still stops until stage A3, as a
  repeated Activity does in a one-shot run; so do a malformed Lactate
  Threshold candidate and a JSON file that cannot be read.
- Stage A2b-2 makes an explicit empty value in Activities, Gear,
  `activity_gear`, and Personal Records an update instead of a review hold, so
  the merge summaries no longer count review holds such as
  `explicit_null_preserved_previous` for these datasets, and the explicit null
  and empty reviews and review holds that `START_HERE.md` reports can be
  lower. Their dataset entries in the merge summaries gain
  `updated_record_count`, and `activity_gear` gains `removed_link_count`;
  `START_HERE.md` shows both totals under "Snapshot Accumulation".
- Two versions with different roles: the store records
  `policy_registry_version` and `contract_version`, which stay at v1.0, so that
  a store stays readable without migration, also by v1.7.1. The v1.0 policy
  registry (`config/garmin_snapshot_dataset_merge_policies_v1.json`) stays
  unchanged as the record of the v1.0 rules. The rules for merging the
  Snapshots into one Run-All input have their own version and file from stage
  A2b-1: `garmin_snapshot_merge_rules:v2.0` for the daily datasets,
  `garmin_snapshot_merge_rules:v2.1` from stage A2b-2, which adds the rules
  for Activities, Gear, `activity_gear`, and Personal Records, and
  `garmin_snapshot_merge_rules:v2.2` from stage A3a, which adds the rules for
  Snapshots with the same content and for accounts, in
  `config/garmin_snapshot_merge_rules_v2.json`. For these datasets they
  replace the merge fields of the v1.0 registry; the other datasets follow the
  v1.0 registry until stage A3. A build records
  `merge_rules_version` in `snapshot/snapshot_lineage.json`, the approved input
  manifest, the merge summary, and the build digest; a store never records it.
  v1.7.1 still reads a store that v2.0.0 registered to, and builds it with the
  v1.7.1 rules.
- Registering the same Export as a ZIP file or as its extracted folder gives
  the same content identity, however deeply it is wrapped in other folders; a
  test checks this from stage A1 on.
- A Snapshot that v1.7.1 registered from a folder inside such wrapping folders
  keeps their names in its paths, so its content identity differs from the
  same Export registered again. Up to stage A2b-2, the store then held a
  second Snapshot with the same files, and the Snapshot lineage and the
  summaries counted two Snapshots.
- Stage A3a recognizes the same Export by the content of its files rather than
  by their paths: the SHA-256 digests and sizes of its files and archive
  members, with repeats.
  - `snapshot register` does not register an Export that the store already
    holds, whatever its paths, wrapping folders, label, or times: it reports
    the Snapshot that holds it in `same_content_as`, with its label and
    number, and exits 0.
  - A build counts Snapshots with the same content once and uses the earliest
    observed one, so that an Export registered again later never becomes the
    latest Snapshot. `snapshot/snapshot_lineage.json` gives their number and
    labels (`same_content_snapshot_count` and `same_content_snapshots`), the
    merge summary their number, and `START_HERE.md` their number under
    "Snapshot Accumulation".
- Stage A3a: `snapshot register` chooses the Export in its input as a run does
  (see [Mixed input](#mixed-input)). It refuses different Exports or accounts
  with `INPUT_MULTIPLE_EXPORTS`, registers the same Export given twice once
  (`same_export_count` in its result), and does not register the files
  outside the Export (`files_not_registered_count`).
- A store holds the Exports of one account. `snapshot register` compares the
  accounts that the new Export's records name with those of the latest
  Snapshot, read again from the store, and refuses another account with
  `INPUT_MULTIPLE_EXPORTS`; the store never records the accounts. A store that
  already holds the Exports of two accounts, as one registered before stage
  A3a could, stops the build with the same code. The CLI names the next step
  for each case: to register the Export into a store for its account, or to
  create a new store for each account. The GUI gains Snapshots, and these
  texts, in stage B.
- To compare the accounts, `snapshot register` reads the files whose records
  name their account within the limits of a run (a JSON file of at most
  128 MiB, and the compression ratio of a ZIP member); a file beyond them is
  not compared, and the run reports it.
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
- Outputs: `run_all_version` 2, the new fields, audit records, and audit
  sections, and the new warning codes. The synthetic Run-All output grows from
  46 to 50 files with the audit records of Activities, Gear, `activity_gear`,
  and Personal Records. Rerun Run-All; earlier outputs are not converted. Renamed in
  stage A2a: the HRV `dedupe_status` `review_required_same_day_differing_values`
  becomes `same_day_values_disagree`, the Run Quality reason
  `CONFLICT_PRESERVED_NO_WINNER` becomes `VALUES_DISAGREE` in Run Quality v2,
  and the daily audit counters `divergent_duplicate_count`,
  `divergent_duplicate_key_count`, and `same_day_conflict_count` give way to
  `disagreement_key_count`.
- Snapshots: existing stores need no migration; rerun `snapshot run-all`.
  Daily values that differ across Snapshots no longer stop the build, the
  Endurance Score and UDS days that v1.7.1 removed come back with the
  differing fields empty, and the merge summaries no longer hold observed
  values or count review holds for null daily fields, so the explicit null
  reviews and review holds that `START_HERE.md` reports can be lower; the
  audit records count such fields in `absent_value_counts`. In Activities,
  Gear, `activity_gear`, and Personal Records, an explicit empty value in a
  later Snapshot now removes the earlier value instead of keeping it, every
  earlier value is kept in the new audit records, and an `activity_gear` link
  is removed when the latest Snapshot shows its Activity and Gear without it.
  Snapshots are numbered in the order of their Exports' observation times.
  Registering an Export that the store already holds reports the Snapshot
  that holds it instead of adding one, a build counts Snapshots with the same
  content once, and a store that holds the Exports of two accounts stops the
  build. The merge rules v2.2 are published in
  `config/garmin_snapshot_merge_rules_v2.json`; the v1.0 policy registry does
  not change.
- Input: the downloaded Export ZIP file can be used directly. Folders around
  the Export, in a ZIP file or a folder, are left out of the recorded paths.
  An input that holds different Exports, or the records of more than one
  account, stops with `INPUT_MULTIPLE_EXPORTS`; v1.7.1 stopped with
  `RELATIONSHIP_CONTRACT_FAILED` when the Exports shared Activities and
  otherwise produced one output from both. The same Export given twice is
  read once, with warning `INPUT_DUPLICATE_SOURCES`. An Export ZIP file in the
  selected folder is read as when it is selected directly, with its uploaded
  FIT files and with paths counted from the Export inside it, and files
  outside the Export are listed instead of read.
- CLI: the pre-run checks that the GUI performed in v1.7.1 apply to the CLI,
  errors report what happened and the next step, and `Ctrl+C` reports the
  cancellation.
- Python API: `DiscoveredAsset` is a plain class instead of a frozen
  dataclass. Its fields, its constructor, and the content that
  `discover_export` returns are unchanged, but dataclass equality, hashing,
  `dataclasses.asdict`, and immutability no longer apply. `read_export` lists
  an Export's files without keeping their content. The daily normalizers no
  longer raise `DailyMetricConflictError` or `PerformanceMetricsConflictError`,
  which are removed; their rows carry `disagreeing_fields`; and
  `normalize_uds`, `normalize_endurance_score`, and `finalize_daily` lose the
  keyword arguments `preserve_observed_variants` and `variant_lineage`, which
  no command used, and `finalize_daily` loses `signature_factory`.
- Schema: the fields that a disagreement can leave empty are nullable (the
  Hill and Endurance `overall_score`, the four Race Prediction times,
  `vo2max`, and `training_status`), every dataset gains `disagreeing_fields`
  (224 to 241 fields), and readers of `analysis/activities.csv` and
  `analysis/performance_metrics_daily.csv` that rely on the column count see
  the new last columns.
