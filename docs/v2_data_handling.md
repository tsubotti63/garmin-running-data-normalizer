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
  datasets. Every left-out item is recorded with its reason: a file in the
  list `files_left_out` of `run_manifest.json`, and a row as a count by reason
  in an audit record.
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
- **Empty record**: a daily row that lacks a required value, such as a date,
  and holds no value of its dataset either, such as a Sleep record with only
  its `retro` flag. Nothing is missing from the datasets, so it is only
  counted: `empty_record_count` in the dataset's audit record, apart from the
  rows left out, with no warning and no change of the status (stage A3d-1).
  So is an item of a list of records that is an empty value, such as null,
  in every dataset (stage A3d-2c-2).

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
  the texts that describe it in v1.7.1 as complete Activities with some FIT
  files left out: the page's result texts, and the Doctor's next step for a
  completed run (`REVIEW_EXCLUDED_FIT_EVIDENCE`) and its text.
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
  follow in stage A3b within one Export or one time point of a Snapshot
  run, and their values across Snapshots are updates, see
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
  - Stage A3b applies these rules to Activities, Gear, `activity_gear`, and
    Personal Records within one Export, and within one time point of a
    Snapshot run (see [Changes across Snapshots](#changes-across-snapshots)).
    - The rows of one record are compared on every normalized field except
      the provenance fields, whose names start with `source_`, and the
      fields that name the record, which come from the first row: the first
      in path order, then in record order within a file, and in a Snapshot
      run after the Snapshot number.
    - Values that differ only in how they are written are one value, as for
      updates across Snapshots: every empty value is the same empty value,
      and numbers are compared by their value, so `100` and `100.0` agree;
      the row keeps the first row's form. An empty value (null, `""`, `[]`,
      or `{}`) or a missing field is no value, so an empty memo next to a
      memo is not a disagreement; when no row has a value, the field keeps
      the first row's empty value. The activity of a Personal Record is
      compared as an identifier (see [Duplicates](#duplicates)), and
      `memo_present` is set when any row has a memo, as a UDS `raw_has_*`
      flag, so it is never empty.
    - Their audit records (`audit/activities.json`, `audit/gear.json`,
      `audit/activity_gear.json`, and `audit/personal_records.json`) gain
      `disagreement_key_count` and `disagreements` in the form of the daily
      audit records, with the Snapshot numbers in Snapshot runs, and
      `absent_value_counts`, each only when there is something to count
      (see [Output shape](#output-shape)). Warning `VALUES_DISAGREE` gives
      the number of keys per family, `activity_gear` counting for Gear; the
      run summary's family results and Run Quality's `conflict_summary`
      count them too.
    - A disagreement in a field that a relationship uses leaves the
      relationship as an empty value does: an Activity whose start time
      disagrees gets no FIT link, and the linkage audit names the reason.
      From stage A3d-1b, a Personal Record whose activity disagrees stays
      with its relationship `unresolved` and the reason
      `activity_link_values_disagree` (see [Relationships](#relationships));
      until then it stopped the run as a missing activity did
      (`RELATIONSHIP_CONTRACT_FAILED`; v1.7.1 stopped with
      `DIVERGENT_DUPLICATE`).

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
    and time empty, and, from stage A3d-1b, a Personal Record whose Activity
    was removed stays with its relationship `unresolved` (see
    [Relationships](#relationships)); until then it stopped the run
    (`RELATIONSHIP_CONTRACT_FAILED`). A removed value that the field does
    not take, such as an empty string for a number or an empty list or
    object for a single value, is no value, as every empty value is: from
    stage A3d-2a, the field is empty without a warning, as in a one-shot run
    of the row, and `updates` keeps the earlier value; until then such a
    value stopped the run (`OUTPUT_EXPERIENCE_FAILED`, exit 2). A later
    value of another form, such as text for a number, replaces the earlier
    value as any value does, so the field is empty and the earlier correct
    value is no longer in the dataset; Run-All keeps the value of another
    form with warning `DATA_VALUE_INVALID` (see
    [Rows and values with problems](#rows-and-values-with-problems)), and
    `updates` keeps both values.
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
  - Stage A3b (merge rules v2.3): Snapshots observed at the same time are one
    time point, and the Snapshots of the last time point are together the
    latest Snapshot. A record in any of them is in the latest Snapshot, and
    an `activity_gear` link is removed only when one of them has Gear
    links, one has the link's Activity, one has its Gear, and none has the
    link. Which of them is numbered first means nothing; until stage A3b,
    the Snapshot with the last identifier was the latest one, and two
    different values for one record stopped the build.
  - At each time point, a field's value is the value of the observations
    that contain the field, compared as within one Export: an empty value
    is no value there, unless every observation that contains the field
    leaves it empty, which removes the value, and two or more values
    disagree. Each field takes the value of the last time point that
    contains it. When that time point's values disagree, the field is
    empty and listed in `disagreeing_fields`, and the audit record's
    `disagreements` lists the values with the Snapshots that gave them, as
    in [Values that disagree](#values-that-disagree). This holds also for
    a field that the record's last time point does not contain: its earlier
    values that disagree stay a disagreement.
  - An update is a difference between time points: a field counts for
    `VALUES_UPDATED` when its value, or its set of values that disagree, at
    a time point that contains it differs from the previous one;
    differences within one time point are disagreements only. In
    `updates`, the values follow the time points: a time point with one
    value continues the entry of the same value before it, and a time point
    whose values disagree lists each value, numbers by size and other
    values by their JSON text, with the Snapshots that gave it, apart from
    the entries before and after it. For example, Snapshots 1 and 2 observed
    at one time with the names "A" and "B", then Snapshot 3 with "B",
    give the values `[{"value": "A", "snapshots": [1]}, {"value": "B",
    "snapshots": [2]}, {"value": "B", "snapshots": [3]}]`, one updated
    record, and no disagreement, because the last time point has one value.
  - Updates are compared on the Export's values, as in stage A2b-2, and
    disagreements on the normalized values, as in a one-shot run. A
    difference only in a source field that no normalized field holds can
    therefore make an earlier time point's values a set, and count as an
    update, without a disagreement; the normalized values stay correct.

### Duplicates

- v1.7.1: a repeated Activity, Gear record, or `activity_gear` link stops with
  `RELATIONSHIP_CONTRACT_FAILED`, even when the rows are identical; a repeated
  Personal Record stops with `DIVERGENT_DUPLICATE`; identical daily rows and FIT
  files are merged and counted.
- v2.0.0 (stage A3b for repeated records):
  - Records with the same stable key and the same values are merged into one
    row, and the audit record counts the further copies
    (`same_value_duplicate_count`), without a warning. Activities, Gear,
    `activity_gear`, and Personal Records are compared on their normalized
    values, so a difference only in a source field that no normalized field
    holds is not counted; records whose values differ are a disagreement
    (see [Values that disagree](#values-that-disagree)).
  - When the input holds the same Export more than once, as when an Export is
    given twice or together with its extracted copy, it is read once, and
    warning `INPUT_DUPLICATE_SOURCES` is given once per run with the number of
    copies not read (stage A3a, which settles the name; see
    [Mixed input](#mixed-input)). Status `PASS_WITH_WARNINGS`. Repeated records
    inside one file are counted without a warning, and so are files with the
    same content at different places in one Export, such as several files
    that hold an empty list: they are not a repeated Export.
  - Identifiers written in two ways, such as `" 123"`, `"0123"`, and `123`,
    are the same identifier, as in v1.7.1, and name one record (stage A3b);
    the row keeps the first row's form. From stage A3d-1b, so is `123.0`,
    which is written as `123`, and only the ASCII digits 0 to 9 are digits
    (see [Rows and values with problems](#rows-and-values-with-problems)).
  - A Snapshot run counts the copies within one Snapshot as a one-shot run
    of that Export counts them: in these four datasets, in the daily audit
    records, and in the HRV record and file counts (stage A3b), so that one
    Export gives the same counts either way. The same record in two
    Snapshots is not a copy, even when they are observed at the same time:
    every Export holds the earlier days again.

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
    so `" 123"` and `123` are one account; from stage A3d-1b, they are read
    as every identifier is (see
    [Rows and values with problems](#rows-and-values-with-problems)), so
    `123.0` is that account too, the full-width `"１２３"` is another
    account, and a value that cannot be an identifier, such as a text of
    more than 4,300 digits, names no account instead of stopping the run.
    Records that name two or more
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
  - The pre-run check (`doctor --input`, which the GUI uses) reports these as
    the run does: `INPUT_MULTIPLE_EXPORTS` as an error, and
    `INPUT_DUPLICATE_SOURCES` as a warning that does not block the run. It
    does not parse the content of JSON files; see
    [Files that cannot be read](#files-that-cannot-be-read).
  - `normalize-activities` and `snapshot register` choose the Export in the
    same way; see [Snapshot Stores](#snapshot-stores) for registration.
  - Warnings and errors name no folder or file. The accounts are compared
    again for each run, which reads the account files once more.

### Files that cannot be read

- v1.7.1: a JSON file that is not UTF-8 or not JSON stops the run; a UTF-8 byte
  order mark stops the Activities, Gear, and Personal Records readers; a Snapshot
  build stops on any such JSON file; an unreadable ZIP file anywhere in the
  input stops the run; a JSON or FIT file over 128 MiB stops the run.
- v2.0.0 (stage A3c):
  - A UTF-8 byte order mark is accepted everywhere.
  - A file that cannot be read is left out with a reason, and the run goes on
    with the other files, including the other files of the same family:
    - `json_not_readable`: a JSON file that the run reads and that is not
      UTF-8, is not JSON, is nested too deeply, or has a number with too many
      digits. Only these four errors leave a file out; any other error is a
      defect of the product and stops the run.
    - `zip_not_readable`: a ZIP file inside the Export that cannot be opened,
      ends early, or has a member that is read and is damaged.
    - `zip_unsafe_member`: a ZIP file inside the Export with a member that
      fails a safety check (a path outside the folder, a link, encryption, or
      a compression ratio over the limit). Its members are read in memory and
      never written, so leaving it out is safe. A member of the Export ZIP
      file itself that fails a check still stops the run: rule 2 stops for an
      unsafe container, and one unsafe container inside it is left out.
    - `zip_too_large`: a ZIP file inside the Export over the limits on the
      number of files or the bytes read from it, or, inside an Export ZIP
      file, over the limit on its own size.
    - `file_too_large`: a JSON or FIT file that the run reads, in a folder or
      in a ZIP file, over the limit for one file (128 MiB).
  - `run_manifest.json` lists the files left out under `files_left_out`, each
    with its path from the Export's root (`inner.zip!member` for a member of
    a ZIP file inside the Export), its size, its family, and the reason, and
    `START_HERE.md` gives their number. Warning `DATA_FILE_LEFT_OUT` gives the
    number once per run, and the status is `PARTIAL_SUCCESS` (exit 3). The
    names never reach the Support Bundle or the External-safe Pack. With no
    file left out, the outputs do not change.
  - A JSON file over the limit for one file that no dataset reads adds
    nothing to the datasets, so it is not read rather than left out:
    `run_manifest.json` lists it under `files_not_read` with the reason
    `file_too_large`, `START_HERE.md` counts it with the files not read, and
    the status does not change.
  - To tell whether two roots hold the same Export (see
    [Mixed input](#mixed-input)), a file that is not read because of its
    size, or a ZIP file that is left out, is compared by its path and size
    only, as the files of the kinds that are not read.
  - A FIT file that cannot be read completely is left out as in v1.x
    (`FIT_PARSE_INCOMPLETE`).
  - Records that point to an Activity whose file was left out do not stop the
    run: the Gear links and Personal Records that point to it leave the
    tables, counted with warning `RELATIONSHIP_UNRESOLVED_VALID_LINK` as in
    v1.7.1, and FIT sessions stay without a link. Stage A4 keeps such rows as
    unresolved.
  - If no Activities record remains because every Activities file was left
    out, the run stops with `ACTIVITIES_EMPTY` and says that the Activities
    files could not be read; the next step is a complete, readable Export.
  - The pre-run check (`doctor --input`) reports, as warning
    `DATA_FILE_LEFT_OUT`, the files that it can tell are unreadable without
    reading their content: the ZIP files and the files over the limit that
    the run leaves out. When every Activities file is among them, it reports
    `ACTIVITIES_EMPTY` as an error. It does not parse JSON content, which
    takes long for a large Export, so a JSON file that cannot be read is
    reported by the run; when every Activities file is such a file, the check
    passes and the run stops with `ACTIVITIES_EMPTY`.
  - A damaged Export ZIP file stops the run (`INPUT_ZIP_CORRUPT`); see
    [An Export given as a ZIP file](#an-export-given-as-a-zip-file).
  - `normalize-activities` reads only Activities files, and its output has
    no list of left-out files, so it stops when an Activities file cannot be
    read, instead of leaving its records out; the other files that cannot be
    read do not concern it.
  - Snapshots follow the same rules (stage A3c-2), so one Export gives the
    same status, warnings, lists of files, and normalized datasets as one
    Snapshot or in a one-shot run:
    - `snapshot register` stores every file, as before. A ZIP file inside the
      Export whose members cannot be listed or read within the limits of a
      run is stored whole, without its members, and the reason is kept in
      its row (`parser_state`). A member over the limit for one file is not
      listed; the stored ZIP file holds it. The store format stays at
      version 1, and the content identity of a Snapshot does not change.
    - The build leaves out, or does not read, the stored files as a run
      does. It does not open a ZIP file stored with a reason; of the other
      ZIP files it reads only the list of members, to find the members over
      the limit. The accounts that a file left out names are not compared.
    - `run_manifest.json` gives each listed file the number of the Snapshot
      that held it (`snapshot`); a file left out of several Snapshots is
      listed once for each.
    - The records of a file left out of a Snapshot are missing from that
      Snapshot. When the file was left out of the latest Snapshot, the
      records that it lacks are kept with their earlier values and warning
      `RECORDS_NOT_IN_LATEST_SNAPSHOT`, as any record missing from the latest
      Snapshot, and the audit record marks them (`latest_file_left_out`);
      `START_HERE.md` gives their number. A link is removed only when the
      latest Snapshot shows its Gear and its Activity, so such a link stays.
    - When no Activities record remains because every Activities file was
      left out, `snapshot run-all` stops with `ACTIVITIES_EMPTY`, as a
      one-shot run does, and `snapshot build-input` stops with
      `SNAPSHOT_LIFECYCLE_FAILED` and the same message.
    - One difference remains. Registration counts every member of a ZIP
      file inside the Export against the limits for one ZIP file (100,000
      files and 2 GiB), and a run counts only the members that it reads. A
      ZIP file over those limits only because of members that are not read
      is therefore left out of a Snapshot build (`zip_too_large`, exit 3)
      while a one-shot run reads it. Counting differently would change the
      content identity of the Snapshots already registered.

### Rows and values with problems

- v1.7.1: a row without an identity stops the run for Activities, Gear, links,
  and Personal Records, and is counted without a warning in daily datasets; a
  passed-through value of an unexpected JSON type stops the run at the end with
  `OUTPUT_EXPERIENCE_FAILED`, or is set to null without a warning in daily
  datasets; text with a lone UTF-16 surrogate and timestamps out of range stop
  the run, some without an error code; a FIT sport field with an unexpected
  layout stops with `FIT_PROCESSING_FAILED`; a Race Prediction row that lacks
  one distance is removed; an item of a list of records that is not an
  object is passed over without a count, and a number in the place of the
  list of Gear, of the links of one Gear, or of Personal Records stops a
  one-shot run with `GEAR_NORMALIZATION_FAILED` or
  `PERSONAL_RECORDS_NORMALIZATION_FAILED`, while a Snapshot run passes over
  it.
- v2.0.0:
  - A row without a usable identity (no identifier and no fallback fields, an
    identifier of an unsupported type, or an identifier of 0 in Activities,
    Gear, and links) or without a required value (such as a date) is left
    out with a reason. Warning `DATA_ROW_LEFT_OUT`, status `PARTIAL_SUCCESS`.
  - Stage A3d-1 does this for the daily datasets other than HRV, stage
    A3d-1b for Activities, Gear, links, and Personal Records, and stage
    A3d-2b for HRV (see the rules for an HRV reading below). The rules for a
    daily row:
    - The reasons are those of v1.7.1, which the dataset's audit record counts
      in `excluded_record_count` and `excluded_reason_counts`. The run gives
      one warning `DATA_ROW_LEFT_OUT` for each dataset with rows left out, with
      `family`, `dataset`, and the number of rows (`count`); the family result
      gains `left_out_row_count`, and `START_HERE.md` a line with the number
      for each dataset.
    - A row that holds no value of its dataset is an empty record (see
      [Terms](#terms)). A value is what one of the dataset's value fields is
      made from: each normalizer lists the source fields of each value field,
      and names the fields that hold no value of a row (its key, date, and
      states), and a test checks that every field of the Schema Catalog is in
      one of the two lists. An empty value (null, `""`, `[]`, or `{}`) holds
      nothing; 0, false, and a value of an unexpected type are values. Source
      fields that no value field is made from, such as Sleep's `retro`, are
      not looked at, and only the rows that are left out are: a row with its
      key and no value stays in the dataset, as in v1.7.1.
    - Copies of a row within one Snapshot count as rows, as in a one-shot run
      of that Export (stage A3b).
    - Source Completeness gives the family `MALFORMED` when a row that holds
      a value is left out; empty records leave it valid.
  - The rules for an HRV reading (stage A3d-2b), which v1.7.1 counted in
    `DAILY_METRICS_REVIEW_REQUIRED` or dropped without a record:
    - Each reading of FIT message 370 is an observation of the local date of
      its time (field 253), and its value (field 1) is what the reading is
      for. Both are read as integers, by the rule for values below, so a
      whole number written with a decimal point, such as `6400.0`, is read.
    - A reading whose date cannot be made, because its time is missing,
      FIT's invalid value, of another form, or out of range, is left out with
      the reason `missing_or_invalid_reading_timestamp` when it holds a
      value, also one of another form, and is an empty record when it holds
      none.
    - A reading with a date whose value is of another form, such as a number
      with a fraction, NaN, or a list, is left out with the reason
      `missing_or_invalid_hrv_value`, as a VO2max row whose value is of
      another form is, and the audit record does not keep the value. HRV
      therefore gives no `DATA_VALUE_INVALID`: a reading has no other value.
    - A reading without a value, which FIT's invalid value 65535 or a
      missing value field gives, is counted in `absent_value_counts` when it
      has a date (see the values that the source marks as absent below) and
      is an empty record when it has none; neither is announced. A date has
      a row only when one of its readings has a value, as in v1.7.1.
    - Run Quality counts the readings left out in `excluded`, as it counts
      the rows left out of the other daily datasets; v1.7.1 counted the
      readings without a date in `missing` and every reading that needed a
      review in `review_required`.
    - HRV belongs to the FIT family of Source Completeness, which the state
      of each FIT file alone decides, so a reading left out does not change
      Source Completeness.
  - The rules for an identifier (stage A3d-1b):
    - One rule reads every identifier: in the normalizers, in the checks of
      relationships, when repeated records are merged, in the Snapshot
      build, and when the accounts are compared (see
      [Mixed input](#mixed-input)). A value is an identifier, missing, or
      invalid.
    - An identifier is an integer, such as `123`; a number written with a
      decimal point or an exponent whose value is a whole number of at most
      2^53 − 1 in size, such as `123.0`; or a text that is not blank.
      Identifiers written in two ways are one identifier: the spaces around
      a text are left out,
      and a text of the ASCII digits 0 to 9 only is read without its
      leading zeros, so `123`, `123.0`, `"123"`, and `" 0123"` name one
      record, and so do `-5` and `"-5"`. Other digits, such as `"²"`,
      full-width digits, or Arabic-Indic digits, are text, so `"１２３"` is
      not `123`.
    - Missing: absent, null, `""`, or spaces only. The record then takes a
      key made from its other fields, as v1.7.1 did for an identifier that
      was absent, null, or `""`: an Activity from its
      start time, distance, duration, and type, a Gear record from its
      `uuid`, `displayName`, and `dateBegin`, and a Personal Record from its
      activity, type, value, and start time. A row without any of these
      fields is left out with the reason `identity_missing`. An
      `activity_gear` link has no such fields: a link without its Gear key
      or its Activity is left out with the same reason.
    - Invalid: a boolean, a list, an object, a number written with a
      decimal point or an exponent that is not a whole number of at most
      2^53 − 1 in size, such as `1.5` or `1e20`, NaN or an infinity, a text
      of more than 4,300 ASCII digits, or a value of another type; and 0 in
      Activities, Gear, and links, where it names no record. The row is left
      out with the reason `identity_invalid`, also when it has the fields
      for a key, so that it is never taken for another record. The limit of
      4,300 digits is the product's own, so that every machine reads the
      same identifiers whatever its Python settings. The identifier of a
      Personal Record can be 0, as in v1.7.1.
    - The normalized rows write each identifier as the Export does, as in
      v1.7.1, except that a whole number written with a decimal point, such
      as `123.0`, is written as the integer `123`, and the key made from it
      is, for example, `garmin_activity:123`. In `activity_gear`, a Gear key
      or an Activity of the ASCII digits is written as an integer, as in
      v1.7.1; other text, such as `"²"`, stays text.
    - The audit records of the four datasets count the rows left out in
      `excluded_record_count` and `excluded_reason_counts`, with the copies
      within one Snapshot, as the daily audit records count theirs. The run
      gives one warning `DATA_ROW_LEFT_OUT` for each of the four datasets
      with rows left out, so the Gear family can give two, one for Gear and
      one for `activity_gear`, and its `left_out_row_count` is their sum;
      `START_HERE.md` gives the number for each dataset in the same line as
      for the daily datasets. Source Completeness gives the family
      `MALFORMED`, and Run Quality counts the rows in `excluded`.
    - Empty records (see [Terms](#terms)) are a rule of the daily datasets:
      a row of these four datasets without a usable identifier is left out
      with the warning, whatever else it holds.
    - A link or a Personal Record that points to an Activity or a Gear
      record that was left out has a valid link whose endpoint is absent
      (see [Relationships](#relationships)).
    - When every Activities row is left out, the run stops with
      `ACTIVITIES_EMPTY`, as when every Activities file is left out.
    - `normalize-activities` (the Golden Path) stops when an Activities row
      has no usable identifier, because its output has no place for the
      count, as it stops for an Activities file that cannot be read; stage
      A3d-3 gives the stop its code. v1.7.1 stopped there without a code
      for a row with neither an identifier nor the fields for a key, and
      wrote a row whose identifier is invalid with a key made from the
      value, such as `garmin_activity:True`.
  - A value of a form that its field does not take becomes empty in the
    normalized row, and the audit record keeps the value. Warning
    `DATA_VALUE_INVALID`, status `PASS_WITH_WARNINGS` (exit 0): the row stays,
    so nothing is left out. Stage A3d-2a does this for every dataset but HRV
    and settles the name; an HRV reading has no other value than the one it
    is for, so a reading whose value is of another form is left out instead
    (stage A3d-2b, see the rules for an HRV reading above):
    - One rule reads every value (`common.values.read_value`): the
      normalizers use it as they read a source field or make a value from
      it, and Run-All checks every value of Activities, Gear, `activity_gear`,
      Personal Records, and the FIT sessions and laps against the logical
      type of its field in the Schema Catalog.
    - A number is finite and at most 2^53 − 1 in size: NaN, an infinity, and
      a larger number, such as 10^400, are of another form. A whole number
      written with a decimal point is an integer, so 3.0 is 3 in an integer
      field. Text is never a number, so `"5"` is of another form in a number
      field: until stage A3d-2a, UDS, Sleep, Acute Training Load, Training
      Readiness, VO2max, and Race Prediction read such text as a number, and
      Hill and Endurance Score left it empty without a record. A boolean is
      never a number, and a number is never text.
    - An empty value (null, `""`, `[]`, or `{}`) is no value, as when values
      are compared: a field that does not take it is empty without a
      warning, and a text field keeps `""` as before.
    - Values are checked before the rows of one key are merged (see
      [Values that disagree](#values-that-disagree)), so a value of another
      form is no value there: two rows of one day with the steps 5 and
      `"abc"` give 5, without a disagreement.
    - A value that a row needs, such as its date or a Hill or Endurance
      overall score, leaves the row out when it is of another form, as when
      it is missing (stage A3d-1); the audit record then counts the row by
      reason and does not keep the value.
    - The identifiers, including the activity of a Personal Record, follow
      their own rules (stage A3d-1b; see [Relationships](#relationships)).
    - The audit record of the dataset gains `invalid_value_counts`, by
      field, and `invalid_values`, each with the key of its row, the field,
      the value, `observation_count`, and, in a Snapshot run, the Snapshot
      numbers. A number that is not finite is kept as an object that names
      it, such as `{"non_finite_number": "NaN"}`, so that every output file
      is strict JSON; v1.7.1 wrote NaN into the normalized datasets. The FIT
      sessions and laps have no audit record of their own: the entry of
      their FIT file in `audit/fit_audit.json` keeps their values, with each
      field named after its dataset, such as `fit_sessions.sport`. The run
      gives one warning for each dataset, with `family`, `dataset`, and
      `count`; the family result gains `invalid_value_count`, and
      `START_HERE.md` a line with the number for each dataset. Source
      Completeness counts files and rows and does not change, so that a
      Snapshot run, whose build does not read values, gives the same.
    - `normalize-activities` (the Golden Path) stops when an Activities
      value is of another form, as for a row without a usable identifier,
      because its output has no place to keep the value; stage A3d-3 gives
      the stop its code.
  - A value that the source marks as invalid or absent, such as the FIT
    invalid value that an HRV reading carries when nothing was measured, is
    an absent value: the field is empty, the audit record counts it, and no
    warning is given, because such a value marks that nothing was measured,
    not a problem in the data. v1.7.1 counts the HRV ones in
    `DAILY_METRICS_REVIEW_REQUIRED`; from stage A3d-2b, the HRV audit record
    counts a reading with this value in `absent_value_counts` when it has a
    date and as an empty record when it has none.
  - A timestamp out of range leaves the derived date and time empty and keeps
    the raw value, with the same warning (stage A3d-2a): the start time of an
    Activity, a FIT session, or a FIT lap that a date cannot hold, and a
    Sleep start or end time that cannot be read. A date or an observation
    time that a daily row needs leaves the row out instead, as a missing one
    does. On some platforms, such as macOS, such a time stopped the run with
    an error that it did not catch.
  - Text with a lone UTF-16 surrogate, such as a truncated emoji, is written
    with U+FFFD in its place as its file is read (stage A3d-2c-1). JSON
    gives such text only with an escape, such as `\ud83d` or `\uD83D`; a
    whole pair, such as `\ud83d\ude00`, reads as one character and stays.
    v1.7.1 stopped with `RUN_ALL_FAILED` when such text reached a table, and
    a Snapshot run also when it was in a field that no table uses or in the
    name of a field.
    - Each JSON file that Run-All reads, one of a family that a dataset
      reads, counts its texts and names of fields repaired, however many
      surrogates each held: in the records, in the fields that no table
      uses, and in the objects around the records alike. A one-shot run
      reads such a file for the count even when no normalizer parses it, as
      a file whose name differs in case only. When two names of one object
      read alike once repaired, the later value is kept, as JSON keeps the
      later of two equal names, and the earlier value is dropped.
    - Warning `DATA_TEXT_REPAIRED` for each family, with `family` and
      `count`, status `PASS_WITH_WARNINGS` (exit 0): nothing is left out.
      The Lactate Threshold files give it as a candidate warning. The family
      result gains `repaired_text_count`, `run_manifest.json` lists the
      files in `files_with_repaired_text` with their family and count, and
      `START_HERE.md` gains a line; each only when there is something to
      report. The Support Bundle and the External-safe Pack carry the code
      and the count only.
    - The Snapshot build repairs and counts the same files as it reads them
      and lists them by Snapshot number, as it lists the files left out, so
      one Export gives the same in a one-shot run and as one Snapshot; a
      file that two Snapshots hold is listed for each. The approved input
      holds the repaired text (merge rules v2.8).
    - `normalize-activities` (the Golden Path) stops when an Activities file
      holds such text, also in a field that no table uses, because its
      output has no place for the report; stage A3d-3 gives the stop its
      code.
  - An item of a list of records that is not an object, such as a number
    among the Activities, and a value of another form in the place of a
    list of records, such as a number where the list of Gear belongs, are
    left out with a reason (stage A3d-2c-2):
    - The lists of records are those that a run reads, listed below: the
      list of records of each kind of file, the links of each Gear record,
      and the top list of a file. A list inside a record, such as the value
      of a field, is no list of records; its value follows the rule for
      values above.
    - An item that is not an object is left out with the reason
      `not_an_object`. An item that is an empty value (null, `""`, or `[]`)
      is an empty record (see [Terms](#terms)): the audit record counts it
      in `empty_record_count`, with no warning.
    - A value in the place of a list of records that is neither a list nor
      an empty value (null, `""`, `[]`, and `{}` hold no records) is left
      out as one item with the reason `records_not_readable`, since how
      many records it stood for cannot be known. So is a `gearActivityDTOs`
      that is not an object, and a file whose value is neither a list nor
      an object, such as a number.
    - Warning `DATA_ROW_LEFT_OUT` and status `PARTIAL_SUCCESS` (exit 3), as
      for the other rows left out, with the reasons in the dataset's audit
      record; the dataset's warning and the `START_HERE.md` line then say
      that items that are not records were left out. An item of a file's
      top list counts for the dataset of its file: Activities, Gear, or
      Personal Records. The audit records of Activities, Gear,
      `activity_gear`, and Personal Records gain `empty_record_count` when
      there is an empty item.
    - The Lactate Threshold candidates count theirs in their audit record
      (`excluded_record_count`, `excluded_reason_counts`, and
      `empty_record_count`), and the run gives warning `DATA_ROW_LEFT_OUT`
      for the family `lactate_threshold`, without `dataset`, as a candidate
      warning, which bounds the run as the rows left out of a dataset do.
    - When every Activities item is left out, the run stops with
      `ACTIVITIES_EMPTY`, also in a Snapshot run, which stopped with
      `SNAPSHOT_LIFECYCLE_FAILED` before.
    - The Snapshot build reads the records of a file with the functions of
      a run (`normalizers.source_records`) and passes each such item to
      Run-All in its place as a record without a key, so that Run-All counts
      it as a one-shot run of the same Export does: copies within one
      Snapshot count, and the same item in two Snapshots once, as for the
      daily records without a stable key. No output names such an item or
      holds its value, an account named inside it is not read, as a run
      does not read it, and it has no updates (merge rules v2.9).
    - `normalize-activities` (the Golden Path) stops when an Activities file
      holds an item left out in this way, because its output has no place
      for the count; an item that is an empty value is passed over, as
      before. Stage A3d-3 gives the stop its code.
    - The lists of records that a run and the Snapshot build read, by kind
      of file:
      - Activities: each `summarizedActivitiesExport` list, and the objects
        with an `activityId` found in the other objects and lists of the
        file, as in v1.7.1. The items of the file's top list that are
        neither objects nor lists are items of a list of records; a list in
        the top list, a `summarizedActivitiesExport` that is an object, and
        the other lists are searched for records, and their other items are
        not counted.
      - Gear: the top object, or each object of the top list, with its
        `gearDTOS` list and its `gearActivityDTOs` object, whose value for
        each Gear key is the list of its links.
      - Personal Records: the top object, or each object of the top list,
        with its `personalRecords` list.
      - The daily datasets other than HRV: the top list; or the first list
        that the top object holds under `data`, `items`, `records`,
        `values`, `summaries`, or `sleepData`, in this order; or the top
        object itself.
      - Hill Score, Endurance Score, and the Lactate Threshold candidates:
        the top list; or the first list that the top object holds under
        `records`, `items`, or `data`; or the top object itself. Until stage
        A3d-2c-2, the Snapshot build read the candidates only in the top
        object or the objects of the top list.
  - A FIT field with an unexpected layout, such as a sport given as an
    array, is treated as an unknown value with the `DATA_VALUE_INVALID`
    warning; the FIT file is not left out (stage A3d-2a).
  - A Race Prediction row keeps the predictions it has, and a missing one is
    empty (stage A3d-1). A row without any prediction is an empty record.
    From stage A3d-2a, a prediction given in a form that is not a positive
    number is empty with warning `DATA_VALUE_INVALID`, and the row stays;
    until then it left the row out.
  - The Lactate Threshold candidates keep their values of another form in
    their audit record (`audit/lactate_threshold_candidates.json`), with
    warning `DATA_VALUE_INVALID` for the family `lactate_threshold` and
    without `dataset`, since the candidates are no normalized dataset; the
    run summary counts it in `candidate_warning_count`.
    `review_condition_counts` counts them as before, and no longer counts
    an empty value (stage A3d-2a).

### Relationships

- v1.7.1: a Personal Record, `activity_gear` link, or FIT lap whose valid link
  points to a record that is not in the output is removed, and only counts
  remain; a Personal Record whose activity link is missing or malformed stops
  the run.
- v2.0.0:
  - These rows stay in the normalized output with the relationship status
    `unresolved` and a reason. Warning `RELATIONSHIP_UNRESOLVED_VALID_LINK`, as
    in v1.x. Status `PASS_WITH_WARNINGS`. Stage A4 does this; until then,
    they are removed and counted as in v1.7.1.
  - A Personal Record whose activity link cannot be followed stays with the
    relationship status `unresolved` and a reason (stage A3d-1b):
    `activity_link_missing` when the link is absent, null, `""`, or spaces
    only; `activity_link_invalid` when it cannot be an identifier (see
    [Rows and values with problems](#rows-and-values-with-problems)); and
    `activity_link_values_disagree` when the rows of the record disagree on
    it (see [Values that disagree](#values-that-disagree)). Its
    `garmin_activity_key` is empty, and so is its `activity_id`: null, or,
    for a missing link, the value that the Export gave, such as `""`. An
    activity identifier of 0 stays `independent`, as in v1.7.1.
  - Warning `RELATIONSHIP_UNRESOLVED_INVALID_LINK` gives the number of such
    Personal Records. Status `PASS_WITH_WARNINGS` (exit 0): the record stays,
    so nothing is missing. Stage A3d-1b settles the name.
  - `qa/relationship_summary.json` counts these Personal Records for
    `personal_records_to_activities` in `eligible_count` and
    `unresolved_count`, and in `relationship_malformed` (missing or
    invalid) and `relationship_conflict` (values that disagree), which
    v1.7.1 always gave as 0. `relationship_unresolved` and `orphan_count`
    still count only the valid links whose endpoint is absent, so
    `RELATIONSHIP_UNRESOLVED_VALID_LINK` keeps its meaning;
    `primary_unresolved_reason` names the most frequent reason; and
    `relationship_warning_count` in `run_summary.json` counts each of the
    two warnings.
  - Until stage A4, the two kinds of Personal Records differ: one whose link
    cannot be followed stays, while one whose valid link points to an
    Activity that is not in the output, such as an Activity left out, is
    removed and counted.
  - Identifiers are compared after trimming spaces and leading zeros, and
    text identifiers of the ASCII digits in `activity_gear` are written as
    integers, as in v1.7.1; the Output Contract is corrected to say so.

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
    Export. From stage A3c, `run-all` leaves out a file over its limit, and a
    ZIP file inside the Export over its limits or with a member over the
    compression ratio, with a reason (see
    [Files that cannot be read](#files-that-cannot-be-read)); a member of the
    Export ZIP file itself over the compression ratio stops the run. From
    stage A3c-2, `snapshot register` stores such a ZIP file whole, without
    its members, and the Snapshot build leaves it out in the same way.
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
    fails its CRC check stops the run with `INPUT_ZIP_CORRUPT`. From stage
    A3c, `run-all` leaves out a damaged ZIP file inside the Export with a
    reason.
  - The Snapshot Store format does not change.

### Stops that remain

The run stops with exit 2 and publishes no output for:

- Safety: members of the Export ZIP file that fail a safety check (paths
  outside the folder, links, encryption, or a compression ratio over the
  limit), symbolic links in the input, a damaged Export ZIP file
  (`INPUT_ZIP_CORRUPT`), and the totals for the whole Export ZIP file
  (`INPUT_TOO_LARGE`). A file over the limit for one file, and a ZIP file
  inside the Export that is damaged, too large, or holds an unsafe member,
  are left out instead (see [Files that cannot be read](#files-that-cannot-be-read)).
- An input that is not an Export: no Activities (`ACTIVITIES_NOT_FOUND`) or no
  Activities records (`ACTIVITIES_EMPTY`), also when every Activities file,
  row, or item was left out.
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
  (stage A3a), `DATA_FILE_LEFT_OUT` (stage A3c), `DATA_ROW_LEFT_OUT` (stage
  A3d-1), `DATA_VALUE_INVALID` (stage A3d-2a), and `DATA_TEXT_REPAIRED`
  (stage A3d-2c-1). `DAILY_METRICS_REVIEW_REQUIRED` is replaced by them:
  from stage A3d-2b, no dataset of Run-All gives it. The code stays known
  with the review items of the daily datasets, which the library keeps and
  no dataset of Run-All uses.
- Stage A3b adds to the audit records of Activities, Gear, `activity_gear`,
  and Personal Records `same_value_duplicate_count`, `absent_value_counts`,
  `disagreement_key_count`, and `disagreements`, each only when there is
  something to count, so the outputs of an Export without repeated records
  do not change. `updates` names a field as the Export does, and
  `disagreements` as the normalized dataset does, as each row's
  `disagreeing_fields`: an Activity's memo is `description` in `updates`
  and `memo_text_raw` in `disagreements`.
- Stage A3a adds `files_not_read` to `run_manifest.json` and
  `input_warning_count` to `run_summary.json`, each only when there is
  something to report, so the outputs of an input with one Export and no files
  outside it do not change.
- Stage A3c adds `files_left_out` to `run_manifest.json`, with `source_path`,
  `bytes`, `family`, and `reason` for each file, and warning
  `DATA_FILE_LEFT_OUT` with the number of files, which `input_warning_count`
  counts; both appear only when a file is left out, so the outputs of an
  Export without such files do not change. `files_not_read` gains the reason
  `file_too_large`.
- Stage A3c-2 adds, each only when there is something to report, the number
  of the Snapshot (`snapshot`) to the entries of `files_left_out` and
  `files_not_read` in a Snapshot run, `latest_file_left_out` to the entries
  of `not_in_latest_snapshot` in the record audits, and
  `not_in_latest_file_left_out_count` to `run_summary.json`. In a Snapshot
  store, the row of a ZIP file stored without its members has the
  `parser_state` `zip_not_readable`, `zip_unsafe_member`, or `zip_too_large`.
- Stage A3d-1 adds, each only when there is something to report,
  `empty_record_count` to the daily audit records, `left_out_row_count` to
  the family results of `run_summary.json`, a `START_HERE.md` line with the
  number of rows left out for each dataset, and warning `DATA_ROW_LEFT_OUT`
  with `family`, `dataset`, and `count`; Run Quality and the Support Bundle
  keep its `dataset`, since a family can hold two datasets. The merge
  summaries of a Snapshot run gain `keyless_observation_count` and
  `keyless_record_count` for each daily dataset.
- Stage A3d-1b adds, each only when there is something to report,
  `excluded_record_count` and `excluded_reason_counts` to the audit records
  of Activities, Gear, `activity_gear`, and Personal Records, warning
  `DATA_ROW_LEFT_OUT` for each of these datasets, and warning
  `RELATIONSHIP_UNRESOLVED_INVALID_LINK` with `family` `relationships` and
  `count`. The merge summaries of a Snapshot run give
  `keyless_observation_count` and `keyless_record_count` for these datasets
  too, as for the daily datasets. The Schema Catalog lets
  `personal_records.activity_id` be null, and the texts about the links of
  Personal Records in `SCHEMA_CATALOG.json`, `ANALYSIS_CONTEXT.json`,
  `START_HERE.md`, `DATASET_INVENTORY.md`, and `ANALYSIS_HANDOFF.md` now
  cover the unresolved ones, so these files and the digests that cover
  them change in every run.
- The External-safe Pack lists each warning with its `code`, `family`, and
  `count` only, as before. The Gear family can therefore list two
  `DATA_ROW_LEFT_OUT` warnings, one for Gear and one for `activity_gear`,
  whose counts add up to the family's rows left out.
- Stage A3d-2a adds, each only when there is something to report,
  `invalid_value_counts` and `invalid_values` to the audit records of the
  datasets other than HRV, to the entries of `audit/fit_audit.json`, and to
  `audit/lactate_threshold_candidates.json`; `invalid_value_count` to the
  family results; warning `DATA_VALUE_INVALID` with `family`, `dataset`, and
  `count` (the Lactate Threshold candidates without `dataset`), which Run
  Quality and the Support Bundle copy without values; and a `START_HERE.md`
  line with the number for each dataset. A whole number written with a
  decimal point in an integer field, such as a lap count of 3.0, is written
  as an integer, and an empty value in a field that does not take it as
  null. An empty text `""` stays as before: Activities, Gear, `activity_gear`,
  Personal Records, and the FIT sessions and laps write it as `""`, and the
  daily datasets write it as null. The outputs of an Export without such
  values do not change, except that Snapshot outputs give the merge rules
  version v2.7.
- Stage A3d-2b gives the HRV audit record (`audit/hrv_daily.json`) the form
  of the other daily audit records: it loses `invalid_value_count`,
  `missing_date_count`, `review_required_count`, and `review_item_count`,
  and gains `excluded_record_count`, `excluded_reason_counts`,
  `absent_value_counts`, and, when there is something to count,
  `empty_record_count`. Its `status` is always `PASS`, and so are the
  `status` of `qa/daily_metrics_summary.json` and its HRV `audit_status`,
  which HRV readings without a value made `PASS_WITH_REVIEW_ITEMS`. Run
  Quality counts the HRV readings left out in `excluded` with the reason
  `EXCLUDED_BY_EXISTING_AUTHORITY` instead of in `missing`
  (`OBSERVED_REQUIRED_VALUE_MISSING`) and `review_required`. Every
  run writes the HRV audit record, so the digests that name it, in
  `diagnostics/run_quality.json`, `run_manifest.json`, and
  `run_summary.json`, change for every Export; the normalized datasets and
  the documents do not.
- Stage A3d-2c-1 adds, each only when text was repaired, warning
  `DATA_TEXT_REPAIRED`, `repaired_text_count` to the family results,
  `files_with_repaired_text` to `run_manifest.json`, and a `START_HERE.md`
  line. The outputs of an Export without such text do not change, except
  that Snapshot outputs give the merge rules version v2.8.
- Stage A3d-2c-2 adds the reasons `not_an_object` and
  `records_not_readable` to the audit records; `empty_record_count` to the
  audit records of Activities, Gear, `activity_gear`, and Personal Records;
  `excluded_record_count`, `excluded_reason_counts`, and
  `empty_record_count` to `audit/lactate_threshold_candidates.json`; and
  warning `DATA_ROW_LEFT_OUT` for the family `lactate_threshold`, which
  `candidate_warning_count` counts; each only when there is something to
  count. The warning about the rows left out of a dataset that left out
  such an item, and the `START_HERE.md` line about the rows left out, name
  these items too. The outputs of an Export without such items do not
  change, except that Snapshot outputs give the merge rules version v2.9.
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
  and from stage A3d-1 a row with neither is left out by Run-All, as below.
- Stage A3d-1: a daily record without a stable key, such as one without a
  date, is no longer held back. The build writes each distinct one once,
  after the records with a key, with the number of each Snapshot that gave
  it, also one in an earlier Snapshot only, and Run-All leaves it out, or
  counts it as an empty record, as a one-shot run does: copies within one
  Snapshot count as rows, and the same record in two Snapshots once. The
  merge summary counts these records (`keyless_observation_count` and
  `keyless_record_count`) instead of review holds, so the review holds that
  `START_HERE.md` reports can be lower, and a run whose store holds such a
  record that holds a value ends with exit 3 where it ended with 0. A family
  whose records all lack a key gives `OPTIONAL_FAMILY_EMPTY` as in a one-shot
  run, instead of being absent. The build reads Hill and Endurance files as
  Run-All does (records under `records`, `items`, or `data`), and counts a
  Snapshot's daily family as malformed in Source Completeness when Run-All
  leaves out a record of it that holds a value.
- Stage A3d-1b: a record of Activities, Gear, `activity_gear`, or Personal
  Records without a usable identifier (see
  [Rows and values with problems](#rows-and-values-with-problems)) is passed
  to Run-All in the same way, and Run-All leaves it out with warning
  `DATA_ROW_LEFT_OUT`, as a one-shot run does. Until then, the build held
  back without a warning a record without an identifier and the fields for
  a key, a link without its Gear key or Activity, and a Personal Record
  whose identifier had an invalid form; it gave the other records with an
  invalid identifier a key, and Run-All then stopped. Such a record has no
  key, so it has no updates and is never listed in
  `not_in_latest_snapshot`. The merge summary counts these records as for
  the daily datasets, so the review holds that `START_HERE.md` reports can
  be lower, and a run whose store holds such a record ends with exit 3
  where it ended with 0 or 2. A link is written under its Gear key as the
  Export gave it, also an empty one, which the build dropped before. The
  build reads identifiers as Run-All does, so `123` and `123.0` name one
  record in any order of the files, and a text of more than 4,300 ASCII
  digits or a Gear key such as `"²"` no longer stops the build. When every
  Activities record lacks a usable identifier, `snapshot build-input`
  writes them for Run-All, and `snapshot run-all` stops with
  `ACTIVITIES_EMPTY`, as a one-shot run does.
- Stage A3d-2c-2: the build reads the records of each file with the
  functions of a run, and passes the items that are not records and the
  lists of records of another form to Run-All as records without a key
  (see [Rows and values with problems](#rows-and-values-with-problems)), so
  a run whose store holds one that is not an empty value ends with exit 3,
  where it ended with 0. Such a record takes no part in the changes across
  Snapshots, and the accounts are not read in it; the merge summary counts
  it in `keyless_observation_count` and `keyless_record_count`, except for
  the Lactate Threshold candidates, whose summary counts candidates only.
  The build now reads the Lactate Threshold candidates as Run-All does.
- Stage A2b-1 removes the stops for daily datasets: values that differ across
  Snapshots, within one Snapshot, or between two Snapshots observed at the same
  time follow [Values that disagree](#values-that-disagree), with the Snapshot
  numbers. Endurance Score and UDS no longer remove the day, and
  `snapshot/canonical_merge_summary.json` and `run_summary.json` no longer hold
  the observed values (`observed_variants`); the values stay only in the audit
  records. The same Activity twice with different values in one Snapshot, or
  in two Snapshots observed at the same time, stopped until stage A3b, which
  makes it a disagreement; a malformed Lactate Threshold candidate stopped
  until stage A3d-2a, which passes it to Run-All, and a JSON file that cannot
  be read stopped until stage A3c-2, which leaves it out. A Snapshot build
  does not read values: it passes them to Run-All as the Export gave them,
  and Run-All checks them as in a one-shot run (stage A3d-2a).
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
  Snapshots with the same content and for accounts, and
  `garmin_snapshot_merge_rules:v2.3` from stage A3b, which makes Snapshots
  observed at the same time one time point and compares the repeated
  records within a time point as a one-shot run does, and
  `garmin_snapshot_merge_rules:v2.4` from stage A3c-2, which leaves out the
  files that a run cannot read, and `garmin_snapshot_merge_rules:v2.5` from
  stage A3d-1, which passes the daily records without a stable key to
  Run-All, and `garmin_snapshot_merge_rules:v2.6` from stage A3d-1b, which
  reads identifiers as Run-All does and passes the records of Activities,
  Gear, `activity_gear`, and Personal Records without a usable identifier
  to Run-All, and `garmin_snapshot_merge_rules:v2.7` from stage A3d-2a,
  which passes the values of another form to Run-All and no longer stops
  on a Lactate Threshold candidate with such a value, and
  `garmin_snapshot_merge_rules:v2.8` from stage A3d-2c-1, which repairs
  text with a lone surrogate as a run does and lists the files by Snapshot
  number, and `garmin_snapshot_merge_rules:v2.9` from stage A3d-2c-2, which
  reads the records of a file as a run does and passes the items that are
  not records to Run-All, in
  `config/garmin_snapshot_merge_rules_v2.json`. For these
  datasets they replace the merge fields of the v1.0 registry; the other
  datasets follow the v1.0 registry until stage A3d. A build records
  `merge_rules_version` in `snapshot/snapshot_lineage.json`, the approved input
  manifest, the merge summary, and the build digest; a store never records it.
  v1.7.1 still reads a store that v2.0.0 registered to, and builds it with the
  v1.7.1 rules. A ZIP file that v2.0.0 stored without its members (stage
  A3c-2) is then left out without a warning, since v1.7.1 does not read the
  reason; `snapshot verify`, `snapshot status`, and `snapshot run-all` of
  v1.7.1 pass on such a store.
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
  with exit 3 or 0, and the warnings say what was left out or kept. A daily
  row without a required value, such as a date, which v1.7.1 left out with a
  count only, now gives warning `DATA_ROW_LEFT_OUT` and exit 3 when it holds
  a value; a row that holds no value is counted as an empty record. A row of
  Activities, Gear, `activity_gear`, or Personal Records without a usable
  identifier, which stopped v1.7.1, is left out with the same warning and
  exit 3, and a Personal Record whose activity link is missing, malformed,
  or disagrees is kept unresolved with warning
  `RELATIONSHIP_UNRESOLVED_INVALID_LINK` and exit 0. A value of a form that
  its field does not take, which stopped v1.7.1 in Activities, Gear,
  Personal Records, and FIT files, and which the daily datasets left empty
  without a record, is empty with warning `DATA_VALUE_INVALID` and exit 0;
  so is a number that is not finite, which v1.7.1 wrote as NaN into the
  outputs, and a time out of range, which stopped v1.7.1 on some
  platforms. Text such as `"5"` in a number field is no longer read as a
  number, and a Race Prediction with a distance that is not a positive
  number keeps its row, where v1.7.1 left the row out. An HRV reading
  without a date that holds a value, which v1.7.1 counted in
  `DAILY_METRICS_REVIEW_REQUIRED` with exit 0, and an HRV reading whose
  value is of another form, which v1.7.1 dropped without a record, are left
  out with warning `DATA_ROW_LEFT_OUT` and exit 3; an HRV reading without a
  value is counted and no longer announced. Text with a lone surrogate,
  which stopped v1.7.1 (exit 2) when it reached a table, and a Snapshot run
  also when no table used it, is written with U+FFFD and announced with
  warning `DATA_TEXT_REPAIRED` (exit 0). An item of a list of records that
  is not an object, which v1.7.1 passed over, and a value of another form in
  the place of a list of records, which stopped a one-shot run of v1.7.1 for
  a number among the Gear and Personal Records lists (exit 2) and was passed
  over otherwise, are left out with warning `DATA_ROW_LEFT_OUT` (exit 3); an
  item that is an empty value is counted as an empty record.
- Outputs: `run_all_version` 2, the new fields, audit records, and audit
  sections, and the new warning codes. The synthetic Run-All output grows from
  46 to 50 files with the audit records of Activities, Gear, `activity_gear`,
  and Personal Records. Repeated Activities, Gear records, links, and
  Personal Records become one row, and their differing fields are empty. An
  identifier written as a whole number with a decimal point, such as
  `123.0`, is written as `123`, in its key too. Only the ASCII digits 0 to
  9 are digits: an identifier written with other digits, such as the
  full-width `"１２３"`, which v1.7.1 read as `123`, is now text, so a link
  that names an Activity in this way is a valid link whose endpoint is
  absent, and records that name their account in this way and as `123`
  name two accounts, which stops the run with `INPUT_MULTIPLE_EXPORTS`.
  Rerun Run-All; earlier outputs are not converted. Renamed in stage A2a:
  the HRV `dedupe_status` `review_required_same_day_differing_values` becomes
  `same_day_values_disagree`, the Run Quality reason
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
  build. Repeated records within one Snapshot, or in Snapshots observed at
  the same time, no longer stop the build: their differing fields are
  empty, and Snapshots observed at the same time are together the latest
  Snapshot. Registration no longer stops on a ZIP file inside the Export
  that cannot be read, holds an unsafe member, or exceeds the limits, and
  builds leave out the files that a run cannot read, as one-shot runs do.
  Daily records without a stable key are no longer held back: Run-All leaves
  them out with warning `DATA_ROW_LEFT_OUT`, or counts them as empty
  records, as in a one-shot run. So are the records of Activities, Gear,
  `activity_gear`, and Personal Records without a usable identifier, which
  were held back or stopped the build. A Lactate Threshold candidate with a
  value of another form no longer stops the build, and neither does text
  with a lone surrogate. An item of a list of records that is not an
  object, and a list of records of another form, which a Snapshot build
  passed over, are left out by Run-All as in a one-shot run, and the build
  reads the Lactate Threshold candidates as a run does. The merge rules v2.9
  are published in
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
  outside the Export are listed instead of read. A file that cannot be read,
  such as a JSON file that is not UTF-8 or not JSON, a damaged ZIP file
  inside the Export, or a JSON or FIT file over 128 MiB that the run reads,
  is left out and listed in `run_manifest.json`, with warning
  `DATA_FILE_LEFT_OUT` and exit 3, instead of stopping the run; a JSON file
  over 128 MiB that no dataset reads is listed as not read; and a UTF-8 byte
  order mark is accepted in every file.
- CLI: the pre-run checks that the GUI performed in v1.7.1 apply to the CLI,
  errors report what happened and the next step, and `Ctrl+C` reports the
  cancellation. `normalize-activities` stops on an Activities row without a
  usable identifier, which v1.7.1 wrote with a key made from the value when
  the value had an invalid form, and on an Activities value of a form that
  its field does not take, which v1.7.1 wrote as it was.
- Python API: `DiscoveredAsset` is a plain class instead of a frozen
  dataclass. Its fields, its constructor, and the content that
  `discover_export` returns are unchanged, but dataclass equality, hashing,
  `dataclasses.asdict`, and immutability no longer apply. `read_export` lists
  an Export's files without keeping their content. From stage A3c,
  `read_export` and `discover_export` leave out a file that cannot be read
  instead of raising, and `ExportReading.left_out` lists it with the reason;
  a member whose data does not match its ZIP header raises `BadZipFile`
  instead of `UnsafeArchiveError`. The daily normalizers no
  longer raise `DailyMetricConflictError` or `PerformanceMetricsConflictError`,
  which are removed; their rows carry `disagreeing_fields`; and
  `normalize_uds`, `normalize_endurance_score`, and `finalize_daily` lose the
  keyword arguments `preserve_observed_variants` and `variant_lineage`, which
  no command used, and `finalize_daily` loses `signature_factory`.
  `normalize_activities`, `normalize_gear`, and `normalize_personal_records`
  gain an optional `left_out` counter, which counts the rows without a
  usable identifier by reason (stage A3d-1b); without it, they raise
  `ValueError` for such a row, also for an identifier of an invalid form or
  of 0 in Activities and Gear, which v1.7.1 accepted. The daily helpers
  `number`, `text`, and `boolean` read values as their fields take them
  (stage A3d-2a): `number` no longer reads text such as `"5"` as a number.
  `normalize_hrv_daily_assets` follows the rules for an HRV reading and
  gives the HRV audit record in its new form (stage A3d-2b); `fit.hrv`
  gains `read_fit_hrv_messages`, which `parse_fit_hrv_bytes` now uses, and
  the HRV functions that Run-All does not use, such as `normalize_hrv`,
  keep their outputs. `parse_json_asset` writes text with a lone surrogate
  with U+FFFD in its place, and `DiscoveredAsset.repaired_text_count` and
  `repaired_text_count` in `intake.discovery` give the texts and names
  repaired (stage A3d-2c-1); new public names: `common.text` and
  `json_read_by_run_all` in `diagnostics.detector`. From stage A3d-2c-2, the
  records of a file are read by the new module `normalizers.source_records`,
  and `load_rows` in `normalizers.daily_metrics` and `metric_rows` in
  `normalizers.performance_metrics` return a mark in the place of an item
  that is not a record; `normalize_activities`, `normalize_gear`, and
  `normalize_personal_records` count such items in `left_out`, and an item
  that is an empty value under `EMPTY_RECORD` (`normalizers.records`), and
  without the counter raise `ValueError` for one that is not an empty
  value, which v1.7.1 passed over, or for which it raised `TypeError`.
- Schema: the fields that a disagreement can leave empty are nullable (the
  Hill and Endurance `overall_score`, the four Race Prediction times,
  `vo2max`, and `training_status`), and so is `personal_records.activity_id`
  for a link that cannot be followed; every dataset gains `disagreeing_fields`
  (224 to 241 fields), and readers of `analysis/activities.csv` and
  `analysis/performance_metrics_daily.csv` that rely on the column count see
  the new last columns.
