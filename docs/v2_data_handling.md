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
- Because `PARTIAL_SUCCESS` now covers more than FIT files, stage B reviewed
  the texts that described it in v1.7.1 as complete Activities with some FIT
  files left out: stage B1a the page's result texts, and stage B2b the
  Doctor's next step for a completed run (`REVIEW_EXCLUDED_FIT_EVIDENCE`,
  whose identifier stays) and the sentence of its report for a person, which
  now say that files, rows, or FIT data were left out.
- Optional families that are absent keep the v1.x status `SKIPPED_NOT_PRESENT`
  and the warning `OPTIONAL_FAMILY_NOT_PRESENT`.

## Reports of a run in the CLI and the GUI

From stage A5a, the CLI and the GUI report the warnings of a run alike:

- The total: the number of warnings of the run (`warning_count` in
  `run_summary.json`), each a code with the count of what it names.
- The count of each family, as in the family results.
- On a line of their own, the warnings that belong to no family, by the
  counts of the run summary: `candidate` (the Lactate Threshold candidates,
  `candidate_warning_count`), `relationship` (`relationship_warning_count`),
  and `input` (`input_warning_count`). The total is the sum of the counts of
  the families and these three, as the checks of an output require.

`run-all` and `snapshot run-all` print `warnings: N` after the exit code, and
`other warnings: candidate=a relationship=b input=c` after the lines of the
families, also when the counts are 0; `validate-handoff` prints
`warnings: N`. Until stage A5a, the CLI printed the counts of the families
only, and the GUI's page could show a sum of the families that was not the
total of its check of the output. The GUI's run status carries the total and
the three counts as `warning_count` and `other_warning_counts`, and the page
shows them from stage B. `run_all` returns them as `warning_totals`. The
output files do not change.

From stage B2c, `run_all` also returns each warning on its own as
`warning_items`: its code, the family and the dataset that it concerns, and
its count, without the words of its message; a warning of the input names no
family, and `OPTIONAL_FAMILY_NOT_PRESENT` and `OPTIONAL_FAMILY_EMPTY` give no
count. The GUI's run status carries them, and the page lists each with its
count under the total, while the result table takes its totals from the
counts above, never from the items. The GUI's server keeps only items of a
registered code with plain names and counts, and leaves out any other item
alone. The CLI prints the totals as before.

From stage B3b, the pre-run check (`doctor --input`, which the GUI uses) also
gives counts of the input, as numbers only, in `input_counts` of its JSON
report and on a line of its report for a person (`Counts: activities=N
fit_files=N files_read=N files_left_out=N files_not_read=N`):

- `activity_records`: the Activities records that a run keeps, after it
  keeps one row of an activity that the files give more than once, as the
  run counts them; `null` without the timezone data, when the check counts
  no Activities (`activities=not_counted`). Until stage B3b, the check
  counted the rows before that, and did not report the count.
- `fit_files`: the FIT files, as the run counts them for the family `fit`
  (`detected_asset_count`).
- `files_read`: the JSON and FIT files that the run reads
  (`input_asset_count` in `run_summary.json`).
- `files_left_out`: the files that the check finds it cannot read: a file
  over the limit, a ZIP file inside the Export that cannot be opened, and an
  Activities file that is not JSON. The run leaves out these, and also the
  JSON files of the other datasets that are not JSON, which only the run
  reads, so this number can be smaller than that of `files_left_out` in
  `run_manifest.json`.
- `files_not_read`: the files that are not read, as `files_not_read` in
  `run_manifest.json` lists them.

`input_counts` is `null` when the Export could not be read, such as a place
that is not an Export, a damaged ZIP file, or mixed Exports. The report after
a run (`doctor --run-output`) has no counts, so the Support Bundle, which
takes that report, does not change, and the format and the schema version of
the reports stay. The check does not count the families: whether the FIT
files hold HRV readings is known only when the run reads them.

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
    `ACTIVITIES_EMPTY` as an error. Until stage A5a, it did not parse JSON
    content, so when every Activities file was a JSON file that cannot be
    read, the check passed and the run stopped with `ACTIVITIES_EMPTY`.
  - From stage A5a, the pre-run check reads the Activities files as the run
    reads them, and keeps only the number of their records, so that it tells
    the stops of the run that need no Activities record:
    - An Activities file that cannot be read, such as one that is not JSON,
      is reported with warning `DATA_FILE_LEFT_OUT`, as the run leaves it out.
    - When no Activities record can be kept, the check reports
      `ACTIVITIES_EMPTY` as an error, as the run stops: with the message that
      the Activities files cannot be read (`ACTIVITIES_FILES_CANNOT_BE_READ`)
      when an Activities file was left out, and otherwise with the new message
      that they hold no Activities record that can be used
      (`ACTIVITIES_FILES_HOLD_NO_RECORDS`, with the next action
      `SELECT_EXPORT_WITH_ACTIVITIES`), such as an empty list, or only rows
      without a usable identifier. From stage B2b, the report for a person
      gives the next step of the stop `ACTIVITIES_EMPTY` for both messages.
    - It does not read them for mixed Exports or without the timezone data,
      which stop the run before it reads them. The files of the other
      datasets are not parsed: the run leaves out what it cannot read of them
      and goes on, so a JSON file of another dataset that cannot be read is
      still reported by the run only. The GUI's check of the input gives the
      same answer.
  - A damaged Export ZIP file stops the run (`INPUT_ZIP_CORRUPT`); see
    [An Export given as a ZIP file](#an-export-given-as-a-zip-file).
  - A folder or file of the input that this app is not allowed to open, such
    as a folder that the operating system's privacy settings protect, is not
    a problem of the data: its records would be missing without a word. From
    stage A3d-3a it stops the run, the pre-run check, `normalize-activities`,
    and `snapshot register` with `INPUT_NOT_READABLE` (exit 2), and so do the
    input itself and its Activities folder when they cannot be opened
    (until then `INPUT_DISCOVERY_FAILED` and `ACTIVITIES_NOT_FOUND`). Until
    stage A3d-3a, such a folder was passed over without a word, as Python's
    `Path.rglob` passes over it, and its family was reported as not present.
    - The CLI's message names the first folder or file that cannot be opened,
      by its path inside the input, and how many more there are; the GUI's
      page names them in the same way. The pre-run check, the run's outputs,
      the Support Bundle, the server's log, and the error's message itself
      never name them.
    - The next step: allow this app to read the input (on a Mac, in System
      Settings > Privacy & Security; on Windows, in the Security tab of the
      folder's Properties), or select the Export folder itself.
    - The folders that an operating system keeps at the top of a drive and
      that its users may not open (`System Volume Information`,
      `$RECYCLE.BIN`, `.Spotlight-V100`, `.Trashes`, `.fseventsd`,
      `.TemporaryItems`, and `.DocumentRevisions-V100`), directly in the
      selected folder, and the folders of Finder's and AppleDouble's
      metadata (`__MACOSX`) at any depth, are passed over as before when
      they cannot be opened: they never hold an Export, and a drive that
      holds an Export can be selected. Deeper in the input, a folder with
      one of those names stops the run like any other folder.
    - A file or folder that goes away while the input is read is a changed
      input (`INPUT_CHANGED`).
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
    in v1.x. Status `PASS_WITH_WARNINGS`. Stage A4a does this:
    - An `activity_gear` link stays with the status of each endpoint:
      `activity_relationship_status` and `gear_relationship_status` are
      `explicit` or `unresolved`, and `activity_relationship_reason` and
      `gear_relationship_reason` give `source_activity_id` and
      `source_gear_key` for an endpoint that is followed, or
      `missing_activity_endpoint` and `missing_gear_endpoint` for one that
      is not in the output. Its `garmin_activity_key` is empty when its
      Activity is not in the output; it is the only field of
      `activity_gear` that may be empty. The links of each Gear are ordered
      by their Activity, and those whose Activity is not in the output
      follow, by the activity identifier.
    - A Personal Record whose valid link points to an Activity that is not
      in the output, such as an Activity left out, stays as one whose link
      cannot be followed does: status `unresolved`, reason
      `missing_activity_endpoint`, `garmin_activity_key` empty, and its
      `activity_id` as the Export gave it.
    - A FIT lap is read with its session from one FIT file, so its session
      is always in the output; a lap whose session were not would stay,
      counted, without a field of its own for it.
  - `qa/relationship_summary.json` counts each endpoint of an
    `activity_gear` link by itself, as the statuses of the rows give it
    (stage A4a): `activity_gear_to_activities` counts in `link_count` the
    links whose Activity is followed, and in `unresolved_count` and
    `orphan_count` those whose Activity is not in the output, and
    `activity_gear_to_gear` does the same for the Gear;
    `relationship_snapshot_resolved` of each entry counts the links whose
    endpoint an earlier Snapshot followed; and `eligible_count` counts each
    link once. Until stage A4a, a link with either endpoint not in the
    output was unresolved for both, as it was removed, and `eligible_count`
    counted a link with neither endpoint in the output twice. The totals do
    not change: `relationship_resolved` counts the links whose both
    endpoints are followed, `relationship_snapshot_resolved` those of them
    that an earlier Snapshot followed, `relationship_unresolved` and the
    count of warning `RELATIONSHIP_UNRESOLVED_VALID_LINK` each endpoint
    that is not in the output, and `relationship_total` is
    `relationship_resolved`, `relationship_unresolved`,
    `relationship_malformed`, and `relationship_conflict` together, so a
    link with neither endpoint counts twice in it.
  - Activities and FIT sessions with more than one equally matching
    candidate are not linked, as before, and the audit record
    (`audit/activity_fit_linkage.json`) gives the reason
    `ambiguous_candidate`; their candidates may stay unlinked too, with the
    reason `one_to_one_conflict`. Warning `ACTIVITY_FIT_LINK_AMBIGUOUS`
    (stage A4a) gives the number of such Activities and FIT sessions
    (`ambiguous_count` of the relationship summary), with `family`
    `relationships`; status `PASS_WITH_WARNINGS` (exit 0). A FIT file whose
    content is in the Export twice is read once (stage A3a), so it does not
    tie. `relationship_warning_count` in `run_summary.json` counts it as
    the third relationship warning.
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
    relationship warnings, three from stage A4a.
  - From stage A4a, the two kinds of Personal Records are alike: one whose
    link cannot be followed and one whose valid link points to an Activity
    that is not in the output both stay, unresolved, with their reason.
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
  - From stage A4d-1, this applies to the UDS date (`calendarDate` and
    `date`), steps (`totalSteps` and `steps`), and distance
    (`totalDistanceMeters` and `distanceMeters`); the Sleep score (the
    `overallScore` and the `overall` value of `sleepScores`, `overallScore`,
    and `sleepScore`), each Sleep stage and the time awake (for example
    `deepSleepSeconds` and `deep_sleep_seconds`); and the Gear type
    (`gearTypeName` and `gearType`). A field whose names disagree is empty
    and listed in `disagreeing_fields`, the audit record keeps the values in
    `disagreements`, and `VALUES_DISAGREE` names the family; the audit record
    of UDS, Sleep, or Gear also counts such rows, by field, in
    `aliases_disagree_counts`, only when there are any. Values are compared
    as values, so 5 and 5.0 are one value, and dates as days, so
    `2030-03-01` and `2030-03-01T00:00:00` are one day. A value of another
    form is no value of the field: the audit record keeps it and
    `DATA_VALUE_INVALID` names it, while the field can still hold the value
    of another name. A UDS record whose names of the date give different
    days has no one day, so it is left out with the reason
    `calendar_date_aliases_disagree`, as a record without a usable date is.
    When a Sleep stage disagrees, the stages give no sum, so the duration is
    empty too, without being listed as disagreeing: the audit record counts
    such rows as `stage_aliases_disagree` in `sleep_duration_source_counts`.
    A Snapshot run reads the names as a one-shot run does. The build passes
    every daily observation with all its names. Across the time points of a
    store, a Gear record that uses both names of its type has them as one
    field: the last time point that holds either name gives the names that
    go on, with their value, the other name is not carried from an earlier
    time point, and a change is an update listed once, under
    `gearTypeName|gearType` (merge rules v2.16). A Gear record that uses one
    name is merged as before.
  - Filled values are marked in the row: `sleep_day_source`,
    `sleep_duration_source`, and `start_time_source`. From stage A4d-2, a mark
    names the source field that actually gives the value: `sleep_day_source`
    is `calendarDate`, or `sleepEndTimestampGMT` when the calendar date cannot
    be read and the end time gives the day in the run's timezone;
    `start_time_source` is `startTimeGmt`, or `beginTimestamp` when
    `startTimeGmt` holds no number, and null when neither does; and
    `sleep_duration_source` names how the duration was made, as the audit
    record counts it (`stage_derived`, `direct_fallback`, `null_fallback`,
    `direct_aliases_disagree`, or `stage_aliases_disagree`). A start of
    another form in `startTimeGmt` is no value there: `beginTimestamp` fills
    the start, and the audit record keeps the value of another form, as
    `DATA_VALUE_INVALID` names it; the key of an Activity without an
    identifier is made from its fields as before, so it does not change.
    Copies of a record are compared without their marks, so they count as
    before, and the merged row takes the best-ranked mark, the source field
    itself first (`calendarDate`, `startTimeGmt`, then `stage_derived` and
    `direct_fallback`); when the copies disagree in the field whose source a
    mark names, that field is empty and listed in `disagreeing_fields`, and
    the mark is null. Across the time points of a Snapshot store, the two
    names of the start are one field, as the names of the Gear type are
    (merge rules v2.17): the last time point that holds either gives the
    start and its mark, and a change is an update listed once, under
    `startTimeGmt|beginTimestamp`. `analysis/activities.csv` gains
    `start_time_source` as its last column.
  - HRV values that disagree follow
    [Values that disagree](#values-that-disagree): the values are kept in the
    audit record, and Run Quality names the reason `VALUES_DISAGREE` instead of
    `CONFLICT_PRESERVED_NO_WINNER` (stage A2a). The HRV `date_basis` names the
    timezone that was used: from stage A4d-2, the HRV audit record gives the
    basis as `fit_end_local_date_from_message_370_field_253_timestamp` and the
    timezone in `date_timezone`, also for the default timezone, where v1.7.1
    wrote `fit_end_jst_date_from_message_370_field_253_timestamp` whatever the
    timezone.
  - An unknown FIT sub-sport keeps its number in `sub_sport_code`; `sub_sport`
    stays empty. From stage A4d-2, every FIT session gives `sub_sport_code`,
    the number as recorded, also when `sub_sport` has a name for it; it is
    null when the session has none or the number is of another form.
  - The External-safe Pack leaves the month empty for an Activity without a
    date (from stage A4d-2); such Activities come last, as before.

### Daily dates

- v1.7.1 and v2.0.0 read the date of a daily row the same way (stage A4d-2
  writes this down): text gives the ISO date of its first ten characters
  (`2030-03-01T06:00:00` is `2030-03-01`), and a number is a time in
  milliseconds since 1970-01-01 UTC, whose UTC date is the date. A row whose
  date can be read in neither way is left out (`DATA_ROW_LEFT_OUT` when it
  holds a value). An eight-digit number written as a date, such as
  `20300301`, is read as milliseconds, so it gives a date in January 1970.

### Files and fields that are not read

- v1.7.1: files other than `.json`, `.fit`, and `.zip` (for example `.tcx`,
  `.gpx`, and `.csv`) and ZIP files inside ZIP files are skipped without a
  record; Activities, Gear, and Personal Records files whose names differ only
  in letter case are detected but not read; source fields outside each
  dataset's field list are dropped without a count; unknown FIT messages and
  developer fields are skipped, and the FIT audit always reports 0 for them.
- v2.0.0:
  - Files that are not read are listed in `run_manifest.json`, and their count
    appears in `START_HERE.md`. The status does not change. Stage A4b lists,
    under `files_not_read`, a file of a form that no dataset reads, in the
    Export or in one of its ZIP files, with the reason `format_not_read`, and
    a ZIP file inside a ZIP file of the Export with the reason `zip_in_zip`;
    a member is named `inner.zip!member`, and each entry gives its size
    (`bytes`). Operating-system metadata files are not Export files and are
    not listed. Files outside the Export stay listed only when they are JSON,
    FIT, or ZIP files (see [Mixed input](#mixed-input)), so that the names of
    other files in a selected folder are not written. An input without the
    layout folders of an Export is read whole as the Export, so every file of
    another form in it is listed. As for the other files listed, the names
    never reach the Support Bundle or the External-safe Pack.
  - A Snapshot run lists the same files by Snapshot number (stage A4b), and
    neither run reads a ZIP file inside a ZIP file. Until stage A4b, and in
    v1.7.1, a Snapshot run read one as a ZIP file of the Export, unlike a
    one-shot run, and could stop (see [Snapshot Stores](#snapshot-stores)).
    Files outside the Export are not registered, so a Snapshot run does not
    list them.
  - File names are matched without regard to letter case.
  - Source fields outside a dataset's field list are counted by name in the
    dataset's audit record, without values. From stage A4c-1, the audit
    records of Activities, Gear, `activity_gear`, and Personal Records give
    `unread_field_counts`: for each field outside the list, the number of
    rows read that hold it (for the daily datasets, see below).
    A row read is a row kept in the dataset, before its repeated records are
    merged; the rows left out and the items that are not records are not
    counted. Only the names of the fields at the top of a row are counted,
    never their values or the names inside them, and the keys of the objects
    that hold the lists of records, such as `summarizedActivitiesExport` or
    `gearActivityDTOs`, are not counted, since they are not records. A name
    that is not a word of up to 64 letters, digits, and underscores starting
    with a letter, such as a date or a number, may be a value: such fields
    are counted together in `unread_other_name_count`, without their names.
    Both appear only when there is something to count, so the audit records
    of an Export without such fields do not change. The status and the
    warnings do not change, and the names never reach the console, Doctor,
    the Support Bundle, or the External-safe Pack. The fields that each
    dataset reads: Activities `activityId`, `name`, `description`,
    `activityType`, `sportType`, `startTimeGmt`, `beginTimestamp`,
    `startTimeLocal`, `distance`, `duration`, `elapsedDuration`,
    `movingDuration`, `avgHr`, `maxHr`, `avgPower`, `maxPower`,
    `avgRunCadence`, `trainingEffectLabel`, `activityTrainingLoad`, and
    `lapCount`; Gear `gearPk`, `uuid`, `displayName`, `customMakeModel`,
    `gearTypeName`, `gearType`, `dateBegin`, `dateEnd`, and `maximumMeters`;
    an `activity_gear` link `activityId`, its Gear key coming from the Gear
    links object; and Personal Records `personalRecordId`, `activityId`,
    `personalRecordType`, `value`, `prStartTimeGMT`, `createdDate`,
    `current`, and `confirmed`.
  - From stage A4c-2, the audit records of the daily datasets give the same
    counts: those of UDS, Sleep, Training Readiness, Acute Training Load,
    Training History, Hill Score, Endurance Score, VO2max, and Race
    Prediction, and that of the Lactate Threshold candidates, for the rows
    that become candidates; a Lactate Threshold row without a value, neither
    a number nor the type that the method of a heart-rate zones row gives,
    which only the number of source rows counts, is not counted. The fields
    that a daily dataset reads are the source fields of its values, aliases
    included, its date, and its time where it has one. VO2max reads the time
    of its series, `timestampGmt` for that of an Activity and
    `updateTimestamp` for the other, and `observationTimestamp` when that one
    is empty, so each series counts the time of the other; the Lactate
    Threshold candidates read `metaData` from the history files and
    `trainingMethod` from the heart-rate zones. The private fields of Hill
    and Endurance are counted apart, in
    `excluded_private_field_presence_counts`, and not again. The HRV daily
    dataset reads FIT files only, whose messages the FIT audit counts.
  - A Snapshot run counts the fields of the records that the build passes,
    each copy within one Snapshot as in a one-shot run, so a Snapshot run of
    a store that holds one Export gives the counts of a one-shot run of it:
    the build passes the copies of a record within one Snapshot as one record
    only when they also hold the same fields, since an empty value and a
    missing field are alike when it compares them.
    With several Snapshots, the build passes the record of each key's last
    time point, with the fields that only earlier time points hold, so the
    counts differ from those of one-shot runs of all the Exports; the probe
    records that the build passes for values that disagreed at an earlier
    time point are not counted (merge rules v2.14). The build passes the
    records of the daily datasets and the Lactate Threshold candidates
    narrowed to the fields of their dataset, so it counts the fields that
    their dataset does not read itself, from the rows that Run-All keeps, as
    it counts the private fields of Hill and Endurance: a row with the same
    content in several Snapshots once, and each copy within one Snapshot;
    Run-All takes these counts from it (merge rules v2.15). A Snapshot run of
    a store that holds one Export gives the counts of a one-shot run of it;
    with several Snapshots, a row whose content changed counts for each
    Snapshot that gave it, so the counts are neither those of the output rows
    nor those of reading all the Exports once.
  - Unknown FIT messages and developer fields are counted in the FIT audit as
    not read, and they do not make a FIT file incomplete. From stage A4c-1,
    each entry of `audit/fit_audit.json` gives `not_read_message_counts`, the
    number of messages of each message number that no dataset reads (all but
    sport 12, session 18, lap 19, record 20, and the HRV readings 370, which
    the HRV daily dataset reads from every FIT file), and
    `developer_field_count`, the number of developer field values; both
    appear only when there is something to count. Message 370 is never
    counted as not read, since the HRV readings read it, and a FIT file
    without an activity, such as one of sleep, is counted as any other.
    `unknown_records` keeps its
    meaning, and the FIT family's state and Source Completeness do not
    change. The fields of sessions and laps outside their field lists are not
    counted.

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
    `inner.zip!member`, as in a folder; a ZIP file inside those is not read,
    and from stage A4b it is listed as not read (`zip_in_zip`).
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

The run stops with exit 2 and publishes no output for the problems below.
From stage A3d-3a, each has a code and a next step, in the CLI and the GUI
alike, and the CLI checks the place of the output before it reads the input,
as the GUI does, instead of after the whole run: the folder for the output
does not exist or is not a folder (`OUTPUT_PARENT_NOT_FOUND`), this app
cannot write there (`OUTPUT_PARENT_NOT_WRITABLE`), there is no free space
there (`OUTPUT_SPACE_INSUFFICIENT`), the output name cannot be used on every
system (`OUTPUT_NAME_INVALID`, see below), the output path is too long
(`OUTPUT_PATH_TOO_LONG`), a folder or file of the input cannot be opened
(`INPUT_NOT_READABLE`), and the input changed during the run, for every
family (`INPUT_CHANGED`). [Stops and next steps](#stops-and-next-steps), at
the end of this section, gives every code with what it means and its next
step.

- The place of the output is checked by creating a hidden folder in it and
  removing it at once, as the staging folder will be created; folders above
  the output that are missing are still made only when the output is
  written. A write that fails at the end gives the same codes; another
  failure is `OUTPUT_PUBLISH_FAILED`, as before. One rule tells that a disk
  has no free space, for the output and the temporary folder alike.
- `snapshot run-all` checks its output before it builds the Snapshots, which
  can take long.
- From stage A5a, the CLI takes the GUI's rules for the place of a new output
  folder, in `run-all`, `snapshot run-all`, `snapshot build-input`, and
  `normalize-activities`:
  - Its name must be one folder name that every system takes: at most 200
    bytes in UTF-8, so that the hidden names made from it stay within the
    255 bytes that many file systems allow, without a dot at its start, a dot
    or a space at its end, a control character, or any of `<>:"/\|?*`, and
    not a name of a Windows device such as `CON` or `nul.txt`. The name is
    checked as it was given, before the system looks at the path, because
    Windows drops a dot or a space at the end of a name when it resolves a
    path. `normalize-activities` writes in an empty output folder that is
    there already, as before, whatever its name. From stage A5b-2, `.`,
    `..`, and a root name a folder that is there, not a new one, and the
    rule does not apply to them (see below).
  - The folder for the output must exist: no command makes the folders above
    its output any more, so that a mistyped path makes no folders. Until
    stage A5a, the CLI made them when it wrote, while the GUI refused them.
    The folder is checked before the run starts; if it is removed while the
    run goes on, the run makes it again when it writes its output, so that
    the work of a long run is not lost.
  - The GUI and the CLI make these checks with the same functions
    (`output_location.valid_output_name` and `check_output_location`).
  - The place of a new Snapshot Store (`snapshot init`) and of a Support
    Bundle (`support-bundle`) are not checked so yet; stage B sets their
    rules with the controls that choose them.
- `normalize-activities` (the Golden Path) gives every stop a code, with
  Run-All's code for the same problem: the problems above, `INPUT_SYMLINK`,
  `INPUT_NOT_DIRECTORY`, `OUTPUT_SYMLINK`, `OUTPUT_INSIDE_INPUT`,
  `OUTPUT_EXISTS`, `ACTIVITIES_NOT_FOUND`, `ACTIVITIES_EMPTY`,
  `PROVENANCE_MISMATCH`, and `OUTPUT_CONTRACT_INVALID`. The problems in the
  data that Run-All reports and goes on with, which its output has no place
  for (an Activities file that cannot be read, a row without a usable
  identifier, an item that is not a record, a value of another form, and
  text with a broken character), stop it with `GOLDEN_PATH_DATA_NEEDS_RUN_ALL`
  and a message that names the problem; the next step is `run-all`. It
  writes its output in a staging folder first, as Run-All does, so a stop
  leaves no part of an output; an empty output folder that is there already
  keeps its permissions. Until stage A3d-3a, it printed `ERROR: ...`
  without a code and could leave some of its files.
- An error that no code describes stops with `RUN_ALL_FAILED` (Run-All and
  `snapshot run-all`), `GOLDEN_PATH_FAILED` (the Golden Path), or
  `COMMAND_FAILED` (the other commands, which said "Golden Path failed"
  until stage A3d-3a, and the other snapshot commands, which said "Run-All
  failed" until stage A3d-3b).
- In the CLI, a line that starts with `ERROR [` is a stop (exit 2), and a
  line that starts with `NOTE [` is a notice that does not stop (stage
  A3d-3b). A program that reads the CLI's output can take only the first for
  a stop. From stage A5c, an `ERROR [` line also ends a command that `Ctrl+C`
  cancelled (exit 130), and lines that start with `left ` name what such a
  command left (see [Cancellation](#cancellation)).
- From stage A5b, every stop of the CLI reads `ERROR [CODE]: <what happened>;
  <next step>`. The message of the stop says what happened, with the details
  that it may give, such as the place inside the input that cannot be opened
  or the names of the failures of `snapshot verify`, and it holds no `;`; the
  next step comes from one table of the codes (`stops.STOPS`), so that it is
  the same wherever a command stops with the code. The table also gives each
  code's meaning in one sentence, for the GUI's texts in stage B. A `NOTE`
  line gives the meaning and the next step of the stop of the same code.
  - The stops of the input, the output, and the Snapshot Store keep the next
    steps that their messages gave; where one code had several, one text
    covers them (for example, `INPUT_MULTIPLE_EXPORTS` says to select one
    Export, or to register each Export into a Snapshot Store for its own
    account).
  - The internal checks, which data cannot trigger, say that no output was
    written and that the code should be reported: every stop of Run-All comes
    before its output is published. `RUN_ALL_FAILED`, `GOLDEN_PATH_FAILED`,
    and `COMMAND_FAILED`, which said "verify the input and output contract"
    until stage A5b, say to run the command again, and to report the code if
    it stops again.
  - `SNAPSHOT_LIFECYCLE_FAILED` says to correct the command or its input as
    the message says, and to run it again. From stage A5b-2, it is left only
    to the stops of the store's contract that no other code describes, such
    as an argument that is not valid, a store that is a link, a new store
    whose folder is not empty, an input and a store that overlap, a store of
    another account, and an input without files; a damaged store always
    stops with `SNAPSHOT_STORE_INVALID`, so the next step no longer speaks of
    `snapshot verify`, as it did in stage A5b-1.
  - `doctor --input` and `doctor --run-output` print, after each finding and
    after the next action of the report, the next step in words (for
    example, `Finding: ACTIVITIES_NOT_FOUND (next: select an Export that
    contains your Activities)`); the identifiers stay first, and the JSON
    report does not change.
  - From stage B2b, a finding whose code is a stop gives the next step of
    that stop, as the run's `ERROR` line does, so that the check and the run
    say the same about the same problem; the GUI's check of the input does
    the same. The JSON report keeps the `next_action_id` of each finding, so
    that two findings name there another step than their words:
    `INPUT_DISCOVERY_FAILED` keeps `OBTAIN_COMPLETE_READABLE_EXPORT`, whose
    words speak of an Export with Activities, and gives the next step of the
    stop, to download or extract the Export again; and `ACTIVITIES_EMPTY` for
    Activities files that hold no record that can be used
    (`ACTIVITIES_FILES_HOLD_NO_RECORDS`) keeps
    `SELECT_EXPORT_WITH_ACTIVITIES` and gives the next step of the stop, to
    obtain a complete, readable Export that contains the Activities.
- `normalize-activities` writes in an empty output folder that is there
  already by moving its three files into it; from stage A5b, when it cannot
  move one, it removes those that it moved, so that a stop leaves no part of
  an output there either.
- From stage A5b-2, the snapshot commands, `support-bundle`, and the GUI's
  checks give the code of the same problem in a run, with the same message:
  - `snapshot build-input` stops for an output that is there already
    (`OUTPUT_EXISTS`) or that is a link (`OUTPUT_SYMLINK`), and with
    `snapshot run-all` for a build without an Activities record that can be
    kept (`ACTIVITIES_EMPTY`).
  - `snapshot register` stops for an input that is a link (`INPUT_SYMLINK`),
    that is not an existing folder or ZIP file (`INPUT_NOT_DIRECTORY`), or
    that this app is not allowed to open (`INPUT_NOT_READABLE`). It reads the
    input as a run reads it: a member of the Export ZIP file that fails a
    safety check, a symbolic link inside the input, and a ZIP file inside the
    Export that cannot be copied out or whose members cannot be read stop it
    with `INPUT_DISCOVERY_FAILED`, or with `INPUT_CHANGED` when a file went
    away; a member that cannot be read when it is copied, after it was read
    whole, is a change of the input (`INPUT_CHANGED`); and an Export ZIP file
    that is too large to read directly stops it with `INPUT_TOO_LARGE` also
    when it holds the same Export twice, whose roots are read to compare them.
  - A registration that meets a symbolic link inside the store, or a
    registered Snapshot whose identity does not match its content, stops
    with `SNAPSHOT_STORE_INVALID`, as for other damage; `snapshot verify`
    names them among its failures, as before. A damaged record of a
    Snapshot has given `SNAPSHOT_STORE_INVALID` since stage A3d-3b.
  - A folder that holds no store, none of the files and folders that a store
    writes, stops every snapshot command but `snapshot init` with
    `SNAPSHOT_STORE_NOT_FOUND`, whose next step says to check `--store` or to
    run `snapshot init` first; a store that lost `store.json` but holds the
    rest is damaged (`SNAPSHOT_STORE_INVALID`, "store.json is missing"), so
    that it is never sent to `snapshot init`. A store without a Snapshot
    stops `snapshot build-input` and `snapshot run-all` with
    `SNAPSHOT_STORE_EMPTY`, whose next step says to register an Export first;
    `snapshot status` and `snapshot verify` show it with no Snapshot and do
    not stop, as before.
  - `support-bundle` refuses a file or a link in the place of the bundle with
    `SUPPORT_BUNDLE_EXISTS`, the code that the GUI gave, and never replaces
    it; `SUPPORT_BUNDLE_PATH_UNSAFE` is for a run output that is a link or
    not an existing folder. The GUI leaves the check to the same function.
  - The output `.`, `..` (also as in `foo/..`), or a root names a folder that
    is there: the rules of stage A5a for the name of a new folder do not
    apply to it, and `run-all`, `snapshot run-all`, and `snapshot
    build-input` stop with `OUTPUT_EXISTS`, as in v1.7.1;
    `normalize-activities` writes in it when it is empty, as before.
  - `validate-handoff` says to check first that the folder is the output of
    Run-All, since a folder that is not one stops it with `HANDOFF_INVALID`
    too.
  - The GUI's checks of the input and of the output, its Support Bundle, and
    the opening of the output answer an unexpected error with
    `COMMAND_FAILED` (HTTP 500), the code with which the CLI's commands stop
    for one, instead of `INTERNAL_ERROR`; the page shows its text for an
    error that it does not know: reload the page and try again, and report
    the code if it happens again. The server's own errors stay
    `INTERNAL_ERROR`.

From stage A3d-3b, the stops of the Snapshot Store and its build have their
own codes and next steps too, instead of `RUN_ALL_FAILED` or
`SNAPSHOT_LIFECYCLE_FAILED`, which remains for the stops of the store's
contract, such as an argument that is not valid: this app cannot write in the
store or create it there (`SNAPSHOT_STORE_NOT_WRITABLE`), there is no free
space for the store (`SNAPSHOT_STORE_SPACE_INSUFFICIENT`), a registration
holds the lock or one stopped and left it (`SNAPSHOT_STORE_LOCKED`), a
registration was interrupted (`SNAPSHOT_REGISTRATION_INCOMPLETE`), a folder
or file of the store cannot be opened (`SNAPSHOT_STORE_NOT_READABLE`), the
store is damaged or a Snapshot that it lists is missing
(`SNAPSHOT_STORE_INVALID`), and a newer version of this app made the store
(`SNAPSHOT_STORE_VERSION_UNSUPPORTED`). An Export that changes while it is
registered stops with `INPUT_CHANGED`, the build of `snapshot run-all`
without free space in the temporary folder with `TEMP_SPACE_INSUFFICIENT`,
and the output of `snapshot build-input` with the codes of the place of an
output. For `snapshot init`, the codes of writing and of free space are those
of the place of the new store, for which another folder can be chosen.
[Stops and next steps](#stops-and-next-steps) gives their next steps.

- A registration finds that the store cannot be written when it creates its
  lock, before it reads the Export. Before it writes, it compares the free
  space with the size of the files that the store does not hold yet; a later
  Export shares most of its files with the earlier ones, and those are not
  counted, so that a registration is never stopped for them. A write that
  finds no space or no permission stops with the same codes; a file that was
  not copied whole is removed at once, and the journal stays for the next
  registration, which completes the store as before. A `snapshot init` that
  stops removes what it wrote, so that it can be run again.
- At its start, with the lock held, a registration removes the temporary
  files that a write to the store left when it stopped: only the names that
  this app gives them, in the folders where it writes them (a blob's only in
  the folder named after the first two characters of its SHA-256), without
  following a link. Its result gives their number
  (`temporary_files_removed`) when there are some. This app never removes the
  lock or the journal.
- `snapshot status` and `snapshot verify` tell of the lock, and `status` of an
  interrupted registration, in `notices` and with a `NOTE` line, only when
  there is one, and do not fail for them. When `snapshot verify` fails, it
  still prints its report and adds an `ERROR` line:
  `SNAPSHOT_REGISTRATION_INCOMPLETE` when the next registration completes the
  store (the journal, and the lists that the interrupted registration did
  not write again), and otherwise `SNAPSHOT_STORE_INVALID` with the names of
  the failures. `snapshot build-input` and `snapshot run-all` stop with the
  same code and message. For a store that it cannot open, that a newer
  version made, or that is not a store, `snapshot verify` prints no report
  and stops as the other commands do.
- A folder or file of the store that cannot be opened stops `status`,
  `verify`, a registration, and the build, and the CLI names the first place
  inside the store and how many more. `status` no longer counts fewer
  Snapshots, and a registration no longer writes the registry without the
  Snapshots that it cannot read. A registration also stops, with
  `SNAPSHOT_STORE_INVALID`, when the registry lists a Snapshot whose files are
  missing, for example because its folder was deleted by hand or removed by a
  sync app; no command removes a Snapshot. It writes the registry again
  before it removes a journal, so that a stop leaves the journal.
- The build of `snapshot run-all` is written in the temporary folder, and
  that of `snapshot build-input` in its output, which is checked as the
  output of a run before the store is read. Before the build starts, the
  free space there is compared with the size of the FIT files that it copies,
  the least that it needs.

The problems:

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
- The temporary folder: not enough free space to read an Export ZIP file or
  to build the Snapshots (`TEMP_SPACE_INSUFFICIENT`).
- The Snapshot Store: it cannot be written or opened, it is locked, a
  registration was interrupted, it fails verification, or a newer version
  made it (see the second table).
- Internal checks that data cannot trigger.

Every stop has a specific code; errors that v1.7.1 reports only as
`RUN_ALL_FAILED` get their own codes.

#### Stops and next steps

Every code with which a command of the CLI can stop, with what it means and
its next step, as an `ERROR` line gives them after the message of the stop
(`stops.STOPS`, stage A5b). The rows are made from the table of the code, in
its order, and a test checks that they are the same. The GUI's page gives the
same content in its own words from stage B; the codes that only the GUI
gives, for its entries and controls, are not in this table.

| Code | What happened | Next step |
|---|---|---|
| `INPUT_SYMLINK` | the input is a symbolic link | select the Export folder or ZIP file itself, not a link to it |
| `INPUT_NOT_DIRECTORY` | the input is not an existing folder or ZIP file | select the Export folder, or the ZIP file downloaded from Garmin |
| `INPUT_NOT_READABLE` | this app is not allowed to open a folder or file of the input | allow this app to read it (on a Mac, in System Settings > Privacy & Security; on Windows, in the Security tab of its Properties), or select the Export folder itself |
| `INPUT_CHANGED` | the input changed while it was read | run the command again when no other program changes the input |
| `INPUT_ZIP_CORRUPT` | the Export ZIP file is damaged or incomplete | download the Export ZIP file again; if it is damaged again, request a new Export from Garmin |
| `INPUT_TOO_LARGE` | the Export ZIP file is too large to read directly | extract it, and select the extracted folder |
| `INPUT_MULTIPLE_EXPORTS` | the input holds more than one Export, or Exports of more than one account | select one Export, or register each Export into a Snapshot Store for its own account |
| `INPUT_DISCOVERY_FAILED` | the input could not be read safely | download or extract the Export again; if it stops again, please report the code |
| `TEMP_SPACE_INSUFFICIENT` | the temporary folder does not have enough free space | free some space on its drive; an Export ZIP file can also be extracted and its folder selected |
| `TIMEZONE_INVALID` | the timezone is not an exact IANA timezone name | give an exact IANA timezone name, such as Asia/Tokyo or America/New_York |
| `TIMEZONE_DATA_UNAVAILABLE` | the timezone data is not installed | reinstall the package in a clean environment, so that the timezone data is installed |
| `ACTIVITIES_NOT_FOUND` | the input holds no Activities file | select an Export that contains your Activities |
| `ACTIVITIES_EMPTY` | the input holds no Activities record that can be kept | obtain a complete, readable Export that contains your Activities |
| `GOLDEN_PATH_DATA_NEEDS_RUN_ALL` | the Activities hold data that normalize-activities has no place for | use run-all, which goes on and reports what it leaves out, keeps, or repairs |
| `OUTPUT_SYMLINK` | the output is a symbolic link | choose a new folder for the output, not a link |
| `OUTPUT_EXISTS` | the output folder is there already | choose another name for the output |
| `OUTPUT_INSIDE_INPUT` | the output is inside the input | choose a place for the output outside the Export |
| `OUTPUT_PARENT_NOT_FOUND` | the folder for the output does not exist or is not a folder | choose an existing folder for the output, or create it first |
| `OUTPUT_PARENT_NOT_WRITABLE` | this app cannot write in the folder for the output | choose another folder, or allow this app to write in it |
| `OUTPUT_NAME_INVALID` | the output folder name is too long or cannot be used on every system | choose a name of at most 200 bytes that does not start with a dot, end with a dot or a space, hold any of <>:"/\\\|?*, or name a device of Windows |
| `OUTPUT_PATH_TOO_LONG` | the output path is too long | choose a shorter folder or name, or on Windows turn on long paths |
| `OUTPUT_SPACE_INSUFFICIENT` | the place for the output does not have enough free space | free some space, or choose another folder |
| `OUTPUT_PUBLISH_FAILED` | the output could not be written | check the free space and the permissions of the folder for the output, and run the command again |
| `SNAPSHOT_STORE_NOT_WRITABLE` | this app cannot write in the Snapshot Store, or create it there | allow this app to write in its folder, or for a new store choose another folder; then run the command again |
| `SNAPSHOT_STORE_SPACE_INSUFFICIENT` | the drive of the Snapshot Store does not have enough free space | free some space, or for a new store choose another folder; then run the command again |
| `SNAPSHOT_STORE_LOCKED` | the Snapshot Store has a lock file (.single-writer.lock): a registration is running, or one stopped before it ended | if no snapshot command is running, delete that file, then run the command again |
| `SNAPSHOT_REGISTRATION_INCOMPLETE` | a registration in the Snapshot Store was interrupted | register the same Export, or another complete Export, again, which completes the store |
| `SNAPSHOT_STORE_NOT_READABLE` | this app is not allowed to open a folder or file of the Snapshot Store | allow this app to read it (on a Mac, in System Settings > Privacy & Security; on Windows, in the Security tab of its Properties); this app must be able to read the whole store folder |
| `SNAPSHOT_STORE_INVALID` | the Snapshot Store is damaged, or a Snapshot that it lists is missing | do not change the files inside the store; restore it from a backup that passed snapshot verify, or make a new store and register the Exports again |
| `SNAPSHOT_STORE_VERSION_UNSUPPORTED` | a newer version of this app made the Snapshot Store | use a newer version of this app, and do not change the files inside the store |
| `SNAPSHOT_STORE_NOT_FOUND` | there is no Snapshot Store in the folder given for it | check the folder given with --store; for a new store, run snapshot init first |
| `SNAPSHOT_STORE_EMPTY` | the Snapshot Store holds no Snapshot yet | register an Export with snapshot register first |
| `SNAPSHOT_LIFECYCLE_FAILED` | a snapshot command cannot do what it was asked | correct the command or its input as the message says, and run it again |
| `HANDOFF_INVALID` | the folder is not the output of a run, or the files of the output do not pass their checks | check that the folder is the output of Run-All; if it is, do not change its files, and run Run-All again into a new folder |
| `DOCTOR_AUTHORITY_INVALID` | the diagnostics of the output are missing, invalid, or disagree | do not change the files of an output; run Run-All again into a new folder |
| `DOCTOR_UNREGISTERED_DIAGNOSTIC` | the output holds a diagnostic code that this version of the app does not know | use the version of this app that made the output, or run Run-All again into a new folder |
| `DOCTOR_VERSION_UNSUPPORTED` | a version of this app that this version does not know made the output | use the version of this app that made the output, or run Run-All again into a new folder |
| `SUPPORT_BUNDLE_PATH_UNSAFE` | the run output is a link or not an existing folder | give the folder of a completed run |
| `SUPPORT_BUNDLE_EXISTS` | a file or a link is there already in the place of the Support Bundle | move or rename it, or give another file for the Support Bundle |
| `SUPPORT_BUNDLE_AUTHORITY_INVALID` | the diagnostics of the run output do not allow a Support Bundle | run Run-All again into a new folder, and make the Support Bundle from it |
| `SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED` | the Support Bundle did not pass its check after it was written | the Support Bundle was not made; please report the code |
| `SUPPORT_BUNDLE_MEMBER_SET_INVALID` | the Support Bundle would not hold exactly its six members | the Support Bundle was not made; please report the code |
| `SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED` | the privacy scan of the Support Bundle found a forbidden text | the Support Bundle was not made; please report the code |
| `SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED` | the Support Bundle would be larger than its limit | the Support Bundle was not made; please report the code |
| `SUPPORT_BUNDLE_UNCLASSIFIED_FIELD` | the Support Bundle would hold a field that is not classified as safe | the Support Bundle was not made; please report the code |
| `SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC` | the Support Bundle would hold a diagnostic code that is not registered | the Support Bundle was not made; please report the code |
| `ACTIVITIES_NORMALIZATION_FAILED` | the Activities could not be normalized | no output was written; this is a defect of this app, so please report the code |
| `GEAR_NORMALIZATION_FAILED` | the Gear could not be normalized | no output was written; this is a defect of this app, so please report the code |
| `PERSONAL_RECORDS_NORMALIZATION_FAILED` | the Personal Records could not be normalized | no output was written; this is a defect of this app, so please report the code |
| `DAILY_METRICS_NORMALIZATION_FAILED` | the daily datasets could not be normalized | no output was written; this is a defect of this app, so please report the code |
| `PERFORMANCE_METRICS_NORMALIZATION_FAILED` | the performance metrics could not be normalized | no output was written; this is a defect of this app, so please report the code |
| `FIT_PROCESSING_FAILED` | the FIT files could not be audited | no output was written; this is a defect of this app, so please report the code |
| `DATASET_TABLE_INVALID` | the table of the datasets of this app is invalid | no output was written; this is a defect of this app, so please report the code |
| `DATASET_NOT_SERIALIZABLE` | a normalized dataset could not be written as JSON | no output was written; this is a defect of this app, so please report the code |
| `DIVERGENT_DUPLICATE` | a normalized dataset holds two rows with the same key | no output was written; this is a defect of this app, so please report the code |
| `STABLE_KEY_MISSING` | a normalized row has no stable key | no output was written; this is a defect of this app, so please report the code |
| `RELATIONSHIP_CONTRACT_FAILED` | a relationship between the datasets failed its check | no output was written; this is a defect of this app, so please report the code |
| `PROVENANCE_MISMATCH` | the provenance of the output does not match the input that was read | no output was written; this is a defect of this app, so please report the code |
| `OUTPUT_CONTRACT_INVALID` | the output does not match its contract | no output was written; this is a defect of this app, so please report the code |
| `OUTPUT_EXPERIENCE_FAILED` | the documents of the output could not be made | no output was written; this is a defect of this app, so please report the code |
| `SNAPSHOT_CONTEXT_INVALID` | the input built from the Snapshot Store does not match the build | no output was written; this is a defect of this app, so please report the code |
| `COMMAND_UNSUPPORTED` | the command is not supported | no output was written; this is a defect of this app, so please report the code |
| `RUN_CANCELLED` | the command was cancelled with Ctrl+C before it finished | run the command again when you need its result, and when no command runs, delete what the lines after this one name, if any |
| `RUN_CANCELLED_AFTER_OUTPUT` | the command was cancelled with Ctrl+C after it wrote its output, which is complete | use the output as it is, and check it first with validate-handoff if it is the output of a run; running the command again stops with OUTPUT_EXISTS |
| `RUN_ALL_FAILED` | Run-All stopped unexpectedly | run the command again; if it stops again, please report the code |
| `GOLDEN_PATH_FAILED` | normalize-activities stopped unexpectedly | run the command again; if it stops again, please report the code |
| `COMMAND_FAILED` | the command stopped unexpectedly | run the command again; if it stops again, please report the code |

### Cancellation

From stage A5c, `Ctrl+C` ends every command of the CLI with one line and exit
130, as a shell gives it for `SIGINT`, instead of a Python traceback. The exit
code of a stop stays 2.

- `ERROR [RUN_CANCELLED]: <command> was cancelled with Ctrl+C; <next step>`:
  the command did not finish; run it again when you need its result.
- `ERROR [RUN_CANCELLED_AFTER_OUTPUT]: <command> was cancelled with Ctrl+C
  after it wrote its output; <next step>`: the cancellation came after the new
  output of `run-all`, `snapshot run-all`, `snapshot build-input`,
  `normalize-activities`, or `support-bundle` was put in its place, so the
  output is complete. The exit code is 130 here too, and running the command
  again stops with `OUTPUT_EXISTS`: a script that reads only the exit code
  checks the output first, for example with `validate-handoff`, instead of
  running the command again. `snapshot init` and `snapshot register` give the
  same result when they run again, so they end with `RUN_CANCELLED` only.
- One `Ctrl+C` leaves no part of an output: Run-All, the build of the
  Snapshots, `normalize-activities` (also in an empty output folder that is
  there already), the Support Bundle, and a new Snapshot Store remove what
  they wrote. Until stage A5c, `snapshot build-input` left its hidden staging
  folder next to its output, `normalize-activities` left the files that it
  had moved into an empty output folder, and `support-bundle` left its hidden
  temporary file.
- A cancelled registration leaves its journal, as any registration that
  stops does, and says so with `NOTE [SNAPSHOT_REGISTRATION_INCOMPLETE]`
  after the `ERROR` line: the next registration completes the store.
- A second `Ctrl+C` while a command cleans up can stop the cleanup. The lines
  after the `ERROR` line then name what the command left, one on a line and
  by name only, never by path: `left next to the output: <name>` for a hidden
  folder or file that it made next to its output, `left in the output folder:
  <name>` for one in an empty output folder of `normalize-activities`, and
  `left in the store folder: <name>` for a part of a new store; a lock that a
  registration left gives `NOTE [SNAPSHOT_STORE_LOCKED]`. Only what was not
  there before the command started is named. Delete it when no command runs.
  A temporary folder of the system (`garmin-export-zip-…` or
  `garmin-snapshot-run-all-…`) that such a stop leaves is not named, because
  it cannot be told from those of other runs; it can be deleted when no
  command runs.
- After the first `Ctrl+C`, and while a command that finished prints its
  result, `Ctrl+C` is ignored until the command has printed its lines, as the
  GUI's run does once its output is published, so that a command never ends
  with a traceback. The handling of `Ctrl+C` is given back when the command
  returns.
- The GUI: a failure that the run reported before a cancellation arrived is
  shown as the failure, with its code, where until stage A5c the
  cancellation was shown; a staging folder is reported only when this run
  made it; when `Ctrl+C` stops the GUI's server while a run is active, the
  terminal shows the lines that the CLI prints for the same end of a run
  (`gui.server.cancel_report`); and the page shows the result table also for
  a run whose cancellation came after its output, when its result is known.

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
- The texts of every output, also of a one-shot run, explain these rules:
  from stage A2a, `START_HERE.md` (Recommended Reading Order),
  `DATASET_INVENTORY.md` (Interpretation Rules), and `ANALYSIS_HANDOFF.md`
  (Receiving Rules) say what a field named in `disagreeing_fields` means,
  and the notes of the fields of the daily datasets in the Schema Catalog say
  that a value that differs between the observations of one stable key is
  null and named in `disagreeing_fields`; from stage A2b-2, the same
  documents say how a Snapshot run updates Activities, Gear, `activity_gear`,
  and Personal Records. These files, and the digests that cover them, change
  for every run.
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
- Stage A4b adds to `files_not_read` the files of a form that no dataset
  reads (`format_not_read`) and the ZIP files inside the ZIP files of the
  Export (`zip_in_zip`), and the `START_HERE.md` line about the files not
  read no longer gives an example: `Files not read: N; run_manifest.json
  lists them with the reason`. The outputs of an Export that holds such
  files change; those of an Export without them do not, except that
  Snapshot outputs give the merge rules version v2.13.
- Stage A4a keeps in `normalized/activity_gear.json` and
  `normalized/personal_records.json` the rows whose valid link points to a
  record that is not in the output (see [Relationships](#relationships)), so
  their record counts grow by those rows. `activity_gear` gains
  `activity_relationship_reason` and `gear_relationship_reason`, never
  empty, and its `garmin_activity_key` may be empty: the schema catalog, the
  dataset inventory, and the digests made from them change for every run,
  also without such links, and the synthetic diagnostics vector counts 243
  fields. The relationship summary counts each endpoint of an
  `activity_gear` link by itself, which changes its two `activity_gear`
  entries, and the Run Quality and Support Bundle figures taken from them,
  only for an Export with a link that misses an endpoint; a link that misses
  both is no longer counted twice in their `eligible_count`. The totals of
  the summary do not change. Warning
  `ACTIVITY_FIT_LINK_AMBIGUOUS` is new, and `relationship_warning_count`
  counts it; the GUI's text for `RELATIONSHIP_UNRESOLVED_VALID_LINK` says
  that the rows stay.
- Stage A4c-1 adds `unread_field_counts` and `unread_other_name_count` to the
  audit records of Activities, Gear, `activity_gear`, and Personal Records,
  and `not_read_message_counts` and `developer_field_count` to the entries of
  `audit/fit_audit.json`, only when there is something to count (see [Files
  and fields that are not read](#files-and-fields-that-are-not-read)). The
  audit records of an Export whose rows hold such fields change, and so do
  the Run Quality digests made from them; the synthetic example Export's
  Activity holds one (`synthetic`), so its Run Quality digest and the
  first-user conversion digests change. Snapshot outputs give the merge
  rules version v2.14.
- Stage A4c-2 adds `unread_field_counts` and `unread_other_name_count` to the
  audit records of the daily datasets and of the Lactate Threshold
  candidates, only when there is something to count. Snapshot outputs give
  the merge rules version v2.15; the records that the build passes do not
  change.
- Stage A4d-2 adds `start_time_source` to Activities and as the last column
  of `analysis/activities.csv`, `sleep_day_source` and
  `sleep_duration_source` to Sleep, and `sub_sport_code` to the FIT sessions:
  the Schema Catalog goes from 243 to 247 fields. The HRV audit record gives
  `date_basis` under a new name and `date_timezone`. Snapshot outputs give
  the merge rules version v2.17.
- Stage A4d-1 adds `aliases_disagree_counts` to the audit records of UDS,
  Sleep, and Gear, only when the names of a field disagree. The UDS audit
  record can count the reason `calendar_date_aliases_disagree`, and the Sleep
  audit record the duration source `stage_aliases_disagree`. Snapshot outputs
  give the merge rules version v2.16, and the updates of a Gear record whose
  Snapshots use both names of its type list them as `gearTypeName|gearType`.
- New error codes: `INPUT_ZIP_CORRUPT`, `INPUT_TOO_LARGE`, and
  `TEMP_SPACE_INSUFFICIENT` (stage A1), `INPUT_MULTIPLE_EXPORTS` (stage A3a),
  `INPUT_NOT_READABLE`, `OUTPUT_SPACE_INSUFFICIENT`,
  `GOLDEN_PATH_DATA_NEEDS_RUN_ALL`, `GOLDEN_PATH_FAILED`, and
  `COMMAND_FAILED` (stage A3d-3a), and `SNAPSHOT_STORE_LOCKED`,
  `SNAPSHOT_STORE_NOT_WRITABLE`, `SNAPSHOT_STORE_SPACE_INSUFFICIENT`,
  `SNAPSHOT_REGISTRATION_INCOMPLETE`, `SNAPSHOT_STORE_INVALID`,
  `SNAPSHOT_STORE_NOT_READABLE`, and `SNAPSHOT_STORE_VERSION_UNSUPPORTED`
  (stage A3d-3b). From stage A3d-3a, Run-All and the Golden Path also give the codes
  for the place of the output that only the GUI gave until then
  (`OUTPUT_PARENT_NOT_FOUND`, `OUTPUT_PARENT_NOT_WRITABLE`,
  `OUTPUT_NAME_INVALID`, and `OUTPUT_PATH_TOO_LONG`); see
  [Stops that remain](#stops-that-remain). The pre-run check gains the
  finding `INPUT_NOT_READABLE`, and the GUI's run status gains
  `error_detail`, which names, for `INPUT_NOT_READABLE`, the first place
  that cannot be opened and how many more.
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
  records. With them, the merge summary of each dataset, wherever it is given
  (also in `ANALYSIS_CONTEXT.json` and the files of a build), loses the
  counters of the observed variants and the policy of the variants
  (`observed_variant_count`, `single_variant_key_count`,
  `multi_variant_key_count`, `canonicalization_unresolved_count`,
  `malformed_count`, and `variant_policy`), and the summary of each daily
  dataset gains `distinct_record_count` (its records with a stable key),
  `exact_repeat_count`, and `automatic_winner`, which is false: no value is
  chosen. In `canonical/record_provenance.json`, a record of a daily dataset
  is kept whole as an observation (`observation_kept`, or `exact_duplicate`
  for a copy of it), where v1.7.1 gave its fields to a merged record
  (`field_contributor`), so `canonical/field_provenance.json` lists the
  fields of the other datasets only. The same Activity twice with different
  values in one Snapshot, or in two Snapshots observed at the same time,
  stopped until stage A3b, which
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
  not records to Run-All, and `garmin_snapshot_merge_rules:v2.10` from stage
  A3d-4b, which keeps the activity of a VO2max record from the files of
  either series, and `garmin_snapshot_merge_rules:v2.11` from stage A3d-4c-1,
  which tells the files of an Export as a one-shot run tells them, and
  `garmin_snapshot_merge_rules:v2.12` from stage A3d-4c-2, which writes a
  record of Activities, Gear, links, or Personal Records with the Snapshots
  that hold it and leaves the observations of Source Completeness to Run-All,
  and `garmin_snapshot_merge_rules:v2.13` from stage A4b, which lists the
  files that a run does not read by Snapshot number and writes a ZIP file
  inside a ZIP file under a name that Run-All does not open, and
  `garmin_snapshot_merge_rules:v2.14` from stage A4c-1, which keeps the Gear
  key of a link under a name of its own and writes the link with the fields
  of the Export only, and `garmin_snapshot_merge_rules:v2.15` from stage
  A4c-2, which counts for Run-All the fields of the daily rows and the
  Lactate Threshold candidates that their dataset does not read, and
  `garmin_snapshot_merge_rules:v2.16` from stage A4d-1, which merges the two
  names of the Gear type as one field across time points when a record uses
  both, and `garmin_snapshot_merge_rules:v2.17` from stage A4d-2, which does
  so for the two names of the start of an Activity, in
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
- Stage A3d-3b: the stops of a store have their own codes and next steps (see
  [Stops that remain](#stops-that-remain)); a registration removes the
  temporary files that a stopped write left, and `status` and `verify` tell of
  a lock or an interrupted registration in `notices`. The format of a store,
  and what a registration writes, do not change.
- Stage A3d-4a: a Snapshot run counts the files of each family as a one-shot
  run of each Export counts them, with the rule of stage A3b: the same
  content in two Snapshots once, and each copy within one Snapshot. These
  counts give `detected_asset_count` and `processed_asset_count` in the
  family results, `detected_asset_count` in the audit records of the daily
  datasets, `source_count` in the dataset summary, and the places of each FIT
  file in its audit (`source_alias_count` and
  `duplicate_source_alias_count`), where a Snapshot run counted the one file
  of each family that the build writes, and each FIT file once. A family
  whose files hold no record is `PROCESSED_EMPTY` with
  `OPTIONAL_FAMILY_EMPTY`, as in a one-shot run, where a Snapshot run gave
  `SKIPPED_NOT_PRESENT`. For a store that holds one Export, these counts are
  those of a one-shot run of it. The build passes the counts to Run-All at
  run time only; what it writes does not change.
- Stage A3d-4b: the audit records and the summaries of a Snapshot run hold
  what a one-shot run of each Export holds.
  - The Lactate Threshold audit counts the files and rows of the Exports
    (`family_asset_counts` and `family_source_record_counts`), also the rows
    that are not candidates, which the build does not pass, and no longer
    holds the nine figures of the build that a Snapshot run copied to it and
    to `candidate_features` in `run_summary.json`, `run_manifest.json`, and
    `ANALYSIS_CONTEXT.json` (`candidate_rows`, `distinct_candidate_count`,
    `exact_repeat_count`, `multiple_candidate_group_count`,
    `authority_unresolved_count`, `malformed_count`, `candidate_status`,
    `candidate_review_required`, and `stable_promotion_available`); they stay
    in the build's merge summary.
  - The Hill and Endurance audit records count the private fields of the
    rows (`excluded_private_field_presence_counts`), which the build leaves
    out of what it writes.
  - A VO2max record of the `MetricsMaxMetData` files keeps its activity
    (`source_activity_id`), which the build dropped (merge rules v2.10).
  - `qa/relationship_summary.json` gives the counters `relationship_*` and
    `unresolved_links` when a link is not followed, as a one-shot run does,
    or when an earlier Snapshot resolved one, instead of always.
  - The files of Activities, Gear, and Personal Records are told by one
    rule, whatever the case of their names, when the input is classified,
    when a one-shot run and the Golden Path read them, and when the build
    reads them. A one-shot run read `summarizedActivities.json` but passed
    over `summarizedactivities.json`, which it counted as an Activities file,
    and stopped with `ACTIVITIES_EMPTY` when no other file held Activities,
    where a Snapshot run read it. Two names that differ only in case, which
    a ZIP file, or a folder where names are case-sensitive, can hold, are
    both read, and the same record in both is a copy.
  The counts follow the rule of stage A3b for more Exports, as above.
- Stage A3d-4c-1: a Snapshot run tells and counts the files of the Exports as
  a one-shot run of each Export does (merge rules v2.11).
  - The build tells a file of an Export by the rule of a one-shot run
    (`classify_source_name`), a member of a ZIP file by its name within the
    ZIP file, to count it and to read it. It told a member by the name of
    its ZIP file and its own, so that the start of the name of a member at
    the top of a ZIP file was the ZIP file's: a UDS file there was counted
    as a file of no family, and a Hill or Endurance file there was not read.
    It told a daily file by a mark anywhere in its name, such as `udsfile`
    in `Copy of UDSFile_1.json`, which a one-shot run does not read: it read
    the rows of such a file, and from stage A3d-4a, which counts the files
    as a one-shot run does, a Snapshot run stopped with
    `OUTPUT_EXPERIENCE_FAILED`. Such a file is no longer read in either run,
    and counts as unknown evidence.
  - `input_asset_count` in `run_summary.json` counts the JSON and FIT files
    of the Exports that a run of each Export reads, with the rule of stage
    A3b, where it counted the files of the build.
  - The unknown evidence of Source Completeness counts, for each Snapshot,
    the JSON and FIT files of no family, as a one-shot run counts them,
    where it also counted the other objects that the build does not read,
    such as a text file. `snapshot/snapshot_coverage.json` gives their
    number in all Snapshots (`unknown_evidence_count`) next to the number of
    the objects that the build does not read
    (`unknown_or_unsupported_object_count`).
  - Source Completeness counts each FIT file in each place where it is
    found, with the status of its content, as it counts the FIT files, in
    both runs. A one-shot run counted the status of each content once, so
    that an Export that holds a FIT file in two places gave the FIT family
    `AMBIGUOUS` with `FIT_CLASSIFICATION_INCOMPLETE`, however readable its
    files were; it now gives the state of the files, such as `PRESENT`.
- Stage A3d-4c-2: the observations of Source Completeness
  (`source_observation_count`) of each Snapshot are the output rows of each
  family that the Snapshot observed, as a one-shot run counts the rows of
  its Export (merge rules v2.12). Run-All counts them, from the Snapshots
  that the build gives each record: a daily record carries those that gave
  it, and a record of Activities, Gear, links, or Personal Records those that
  hold it, at any time point; the rows of a FIT file, its sessions, laps,
  links, and HRV dates, belong to the Snapshots that hold the file. The build
  counted the rows that it read, also the repeated rows and those that
  Run-All leaves out, and, for FIT, the per-second records of the files,
  which gave a family the wrong state, such as `EMPTY` for FIT files whose
  sessions and laps a one-shot run counts. Run-All writes the counts into
  `snapshot/snapshot_coverage.json`, whose observations the output check
  reads, and the check compares them with the rows of each family: no more,
  and, for one Snapshot, all of them. `snapshot build-input` alone writes
  the observations without them.
- With stage A3d-4c-2, a Snapshot run of a store that holds one Export gives
  every output of a one-shot run of that Export, but for what differs by
  design; `tests/test_snapshot_parity.py` checks every output file of
  synthetic Exports of many kinds against this list, field by field. What
  differs by design:
  - The names of the scope: `observation_scope` in the audit records and in
    `diagnostics/source_completeness.json`, and its `observation_ref`,
    `evidence_references`, and `authority_references`, which name the
    Snapshots and the Snapshot files.
  - The provenance of the build's files: the provenance fields of the
    normalized tables (`source_path`, `source_sha256`, `source_record_index`,
    `activity_source_path`, `activity_source_sha256`, `fit_source_path`, and
    `fit_source_sha256`), `source_path` in the FIT audit, `input_assets` in
    `run_manifest.json`, and the digests made from them or from the outputs:
    `records_sha256`, the `provenance_references` and
    `authority_evidence_digest` of Run Quality, `deterministic_output_digest`,
    and `manifest_sha256`.
  - The Snapshot numbers that a Snapshot run gives a value of the audit
    records (`snapshots`) and a file of the lists of files of
    `run_manifest.json` (`snapshot`).
  - The files of a Snapshot run only (`snapshot/`), the lists of the output
    files that name them (`outputs` in `run_manifest.json`,
    `generated_paths` in `run_summary.json`, and `artifact_inventory.json`),
    the `snapshot_lifecycle` sections of `run_summary.json`,
    `run_manifest.json`, and `ANALYSIS_CONTEXT.json`, and the Snapshot
    Accumulation section of `START_HERE.md`, `DATASET_INVENTORY.md`, and
    `ANALYSIS_HANDOFF.md`.
  - The files outside the Export, which registration does not store: the
    entries of `files_not_read` whose reason is `outside_export_root`, and
    their number in the `START_HERE.md` line about the files not read
    (stage A4b).
- Stage A4b: the build lists the stored files that a run does not read, by
  Snapshot number, as a one-shot run lists them: the files and ZIP members of
  a form that no dataset reads, among them the members over the limit for
  one file that the stored ZIP file holds, and the ZIP files inside the ZIP
  files of the Export (merge rules v2.13). It writes a ZIP file inside a ZIP
  file into its approved input under a name that Run-All does not open
  (`.bin`, as an unknown object with an unusual extension). Until then, and
  in v1.7.1, Run-All read such a ZIP file as a ZIP file of the Export, which
  a one-shot run does not read: a Snapshot run read rows that a one-shot run
  does not, and could stop, with `RELATIONSHIP_CONTRACT_FAILED` when they
  repeated records of the Export, and, from stage A3d-4a, with
  `OUTPUT_EXPERIENCE_FAILED` when they were of a family that the build found
  no file of. A Snapshot run stops with `SNAPSHOT_CONTEXT_INVALID` when its
  approved input holds a file that the build should have left out or
  listed; the unknown objects of a form not read that the build writes there
  do not stop it.
- Stage A4c-1: Run-All counts the fields that it does not read from the
  records that the build passes (see [Files and fields that are not
  read](#files-and-fields-that-are-not-read)). The build keeps the Gear key
  of a link under a name of its own, which starts with
  `garminRunningDataNormalizer` as the other fields that it adds, and writes
  the link into its approved input with the fields of the Export only, and it
  passes the copies of a record within one Snapshot as one record only when
  they also hold the same fields (merge rules v2.14). Until then, it wrote the
  key into the link as `gearPk`, which Run-All does not read there, and
  passed as one record the copies that differed only in a field that one of
  them held with an empty value. The field states of the merge summaries
  still count the Gear key of a link as its field `gearPk`, once, also when
  the link holds a `gearPk` of its own, so they do not change.
- Stage A4c-2: the build passes the daily records, the Hill and Endurance
  records, and the Lactate Threshold candidates narrowed to the fields of
  their dataset, as before. It counts by name the fields of these rows that
  their dataset does not read, from the rows that Run-All keeps (it tells
  them with the rules of Run-All: the reasons for which a daily row is left
  out, and the rule of a candidate), as it counts the private fields of Hill
  and Endurance, and Run-All takes the counts from it, applying the rule of
  the names (merge rules v2.15). The records that it passes do not change,
  and neither do the counts of the merge summaries and of the copies.
- Stage A4d-1: a Gear record whose Snapshots write its type under both
  names, `gearTypeName` and `gearType`, has them as one field across time
  points: the last time point that holds either name gives the names that
  go on, with their value; the other name is neither carried from an earlier
  time point nor written as a probe; and a change is listed once in the
  record's updates, under `gearTypeName|gearType` (merge rules v2.16).
  Before, the build carried the name that the last time point lacked, so
  Run-All read both names in one row. A record that uses one name, and the
  daily records, are merged as before.
- Stage A4d-2: the two names of the start of an Activity, `startTimeGmt` and
  `beginTimestamp`, are one field across time points in the same way (merge
  rules v2.17), so the last time point that holds either gives the start and
  its mark. An Activity whose Snapshots hold both names changes its start in
  one update, `startTimeGmt|beginTimestamp`, where it was two, one for each
  name, so `updated_field_count` counts one.

## Golden outputs and tests

- When a stage A pull request changes a golden output, its description explains
  why. A golden output for an input that the change does not concern stays
  byte-identical.
- At the stage A checkpoint, the CLI is checked on its own with the synthetic
  golden outputs, and the migration notes are drafted
  ([v2.0.0 Migration Notes Draft](v2_migration_notes_draft.md)).

## Migration notes outline (v1.7.1 to v2.0.0)

The [v2.0.0 Migration Notes Draft](v2_migration_notes_draft.md) gives users
what this outline means for their scripts and readers, from the comparison of
v1.7.1 with the CLI at the stage A checkpoint.

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
  `disagreement_key_count`. From stage A3d-4c-1, Source Completeness counts
  each FIT file in each place where it is found: an Export that holds a FIT
  file in two places no longer gives the FIT family `AMBIGUOUS` with
  `FIT_CLASSIFICATION_INCOMPLETE` for that alone, its `readable_asset_count`
  and `state_counts` count the files, and the state counts of Run Quality
  and the Source Completeness of the Support Bundle follow. From stage A4a,
  an `activity_gear` link or a Personal Record whose valid link points to a
  record that is not in the output stays, unresolved, where v1.7.1 removed
  it; `activity_gear` gains `activity_relationship_reason` and
  `gear_relationship_reason`, and its `garmin_activity_key` may be empty;
  the relationship summary counts each endpoint of an `activity_gear` link
  by itself, where v1.7.1 counted a link with either endpoint missing as
  unresolved for both; and warning `ACTIVITY_FIT_LINK_AMBIGUOUS` announces
  the Activities and FIT sessions whose candidates tie, which v1.7.1 left
  unlinked without a warning. From stage A4c-1, the audit records count by
  name the source fields of Activities, Gear, `activity_gear`, and Personal
  Records that no dataset reads, and the FIT audit counts the FIT messages
  and developer fields that no dataset reads, which v1.7.1 dropped without
  a count; from stage A4c-2, so do the audit records of the daily datasets
  and of the Lactate Threshold candidates. From stage A4d-1, a value that a
  later name holds while an earlier one is null, empty, or of another form
  fills the field (v1.7.1 left the UDS steps and distance empty when
  `totalSteps` or `totalDistanceMeters` was null, and read the Sleep score
  and stages and the Gear type from the first name only), and values that
  differ make the field disagree. A UDS record whose `calendarDate` cannot
  be read but whose `date` can is kept with that day, where v1.7.1 left it
  out, and one whose two dates differ is left out. `DATA_VALUE_INVALID` can
  name a value of another form while its field holds the value of another
  name. An Export without a second name gives the same output. From stage
  A4d-2, Activities, Sleep, and the FIT sessions gain their marks and
  `sub_sport_code`, and `analysis/activities.csv` gains `start_time_source`
  as its last column, so their digests change for every Export; the Golden
  Path output gains `start_time_source` too. An Activity whose
  `startTimeGmt` is of another form takes its start from `beginTimestamp`,
  where v1.7.1 left it empty, and keeps its key. The HRV audit record names
  its timezone in `date_timezone` and its basis without one, also for the
  default timezone. The External-safe Pack leaves the month of an Activity
  without a date empty, where v1.7.1 wrote `None`.
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
  reads the Lactate Threshold candidates as a run does. From stage A3d-4a,
  the counts of files in the family results, the audit records, the dataset
  summary, and the FIT audit are those of the Exports, and a family whose
  files hold no record is `PROCESSED_EMPTY` with `OPTIONAL_FAMILY_EMPTY`, as
  in a one-shot run, instead of `SKIPPED_NOT_PRESENT`. From stage A3d-4b,
  the Lactate Threshold, Hill, and Endurance audit records count the files,
  rows, and private fields of the Exports, the nine figures of the build
  leave the Lactate Threshold audit and `candidate_features` for the build's
  merge summary, a VO2max record of the `MetricsMaxMetData` files keeps its
  activity, and the counters of `qa/relationship_summary.json` are given
  when a link is not followed or an earlier Snapshot resolved one, as in a
  one-shot run. From stage A3d-4c-1, a Snapshot run, too, tells the files of
  an Export by the beginning of their names, and a member of a ZIP file by
  its name within the ZIP file: a Hill or Endurance file at the top of a ZIP
  file is read, and a file with the mark of a family elsewhere in its name,
  such as `Copy of UDSFile_1.json`, is no longer read, as in a one-shot run,
  and counts as unknown evidence. `input_asset_count` counts the files of
  the Exports instead of those of the build, the unknown evidence of Source
  Completeness only the JSON and FIT files of no family, and
  `snapshot/snapshot_coverage.json` gives their number
  (`unknown_evidence_count`). From stage A3d-4c-2, the observations of
  Source Completeness are the output rows that each Snapshot observed, which
  Run-All counts and writes into `snapshot/snapshot_coverage.json`, so that a
  family's state follows its rows as in a one-shot run; the coverage that
  `snapshot build-input` writes alone has no such counts. A Snapshot run of
  one Export now gives every output of a one-shot run of it but for what
  differs by design (see [Snapshot Stores](#snapshot-stores)). From stage
  A4b, a Snapshot run no longer reads a ZIP file inside a ZIP file of an
  Export, which v1.7.1 read as a ZIP file of the Export and which could stop
  the run, and lists the files that a run does not read by Snapshot number.
  From stage A4c-1, the build writes a link with the fields of the Export
  only, from stage A4c-2, it counts for Run-All the fields that it leaves
  out of the daily rows, from stage A4d-1, it merges the two names of the
  Gear type as one field across time points, and from stage A4d-2, those of
  the start of an Activity. The merge rules v2.17 are published in
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
  order mark is accepted in every file. From stage A4b, the files of a form
  that no dataset reads, such as `.tcx`, `.gpx`, and `.csv` files, and the ZIP
  files inside the ZIP files of the Export, which v1.7.1 skipped without a
  record, are listed as not read.
- CLI: the pre-run checks that the GUI performed in v1.7.1 apply to the CLI,
  errors report what happened and the next step, and `Ctrl+C` reports the
  cancellation. `normalize-activities` stops on an Activities row without a
  usable identifier, which v1.7.1 wrote with a key made from the value when
  the value had an invalid form, and on an Activities value of a form that
  its field does not take, which v1.7.1 wrote as it was. From stage A3d-3a,
  `run-all` and `normalize-activities` check the place of the output before
  they read the input; stops that said `RUN_ALL_FAILED`,
  `INPUT_DISCOVERY_FAILED`, `ACTIVITIES_NOT_FOUND`, or "Golden Path failed"
  give their own codes (see [Stops that remain](#stops-that-remain));
  `normalize-activities` prints `ERROR [CODE]: ...` and leaves no part of an
  output when it stops; and a folder of the input that this app may not
  open, which v1.7.1 passed over and finished with exit 0, stops with
  `INPUT_NOT_READABLE` (exit 2). From stage A3d-3b, the snapshot commands
  give the stops of the store their own codes instead of `RUN_ALL_FAILED`
  and `SNAPSHOT_LIFECYCLE_FAILED`; `snapshot status` and `snapshot verify`
  can print `NOTE` lines, and `snapshot verify` an `ERROR` line after its
  report; a folder of the store that cannot be opened stops `snapshot status`
  and `snapshot register`, which v1.7.1 passed over (exit 0), counting fewer
  Snapshots or writing the registry without them; and `snapshot build-input`
  checks its output before it reads the store. From stage A3d-4b, `run-all`
  and `normalize-activities` read the files of Activities, Gear, and Personal
  Records whatever the case of their names, as the input is classified: a
  file named `summarizedactivities.json`, which v1.7.1 counted and passed
  over, stopping with `ACTIVITIES_EMPTY` when it was the only one, is read.
  From stage A5a, `run-all`, `snapshot run-all`, `snapshot build-input`, and
  `normalize-activities` (for an output folder that it makes) stop with
  `OUTPUT_NAME_INVALID` for an output name that the GUI refuses, such as one
  that starts with a dot or ends with a dot or a space, and with
  `OUTPUT_PARENT_NOT_FOUND` when the folder for the output does not exist,
  which v1.7.1 made; a script that relied on that makes the folder first.
  `run-all` and `snapshot run-all` print the total of the warnings and the
  warnings that belong to no family, and `validate-handoff` the total (see
  [Reports of a run in the CLI and the GUI](#reports-of-a-run-in-the-cli-and-the-gui)).
  `doctor --input` reads the Activities files and reports `ACTIVITIES_EMPTY`
  when no Activities record can be kept, where v1.7.1 passed such an Export
  and the run stopped, and from stage B3b it gives the counts of the input
  in `input_counts` and on a `Counts:` line (see
  [Reports of a run in the CLI and the GUI](#reports-of-a-run-in-the-cli-and-the-gui)).
  From stage A5b, every `ERROR` line gives the next
  step of its code after what happened (see
  [Stops that remain](#stops-that-remain)): the messages of some stops are
  worded anew, such as that of `TIMEZONE_INVALID`, and those of
  `RUN_ALL_FAILED`, `GOLDEN_PATH_FAILED`, and `COMMAND_FAILED` no longer say
  to verify the input and output contract; `doctor`'s report for a person
  gives the next steps in words. From stage A5b-2, the code itself changes
  in the cases below, to the code of the same problem in a run (see
  [Stops that remain](#stops-that-remain)), so that a script that looks for
  a code finds here what to change:
  - `snapshot build-input` with an output that is there already or a link:
    `OUTPUT_EXISTS` or `OUTPUT_SYMLINK`, and `snapshot build-input` and
    `snapshot run-all` without an Activities record that can be kept:
    `ACTIVITIES_EMPTY`, where they said `SNAPSHOT_LIFECYCLE_FAILED`.
  - `snapshot register` with an input that is a link or not an existing
    folder or ZIP file: `INPUT_SYMLINK` or `INPUT_NOT_DIRECTORY`, where it
    said `SNAPSHOT_LIFECYCLE_FAILED`, and with one that this app may not look
    at: `INPUT_NOT_READABLE`, where it stopped as an unexpected error; with a
    member of the Export ZIP file that fails a safety check, a symbolic link
    inside the input, or a ZIP file inside the Export that cannot be copied
    out or read: `INPUT_DISCOVERY_FAILED`, or `INPUT_CHANGED` when a file went
    away or could not be read again, and with an Export ZIP file that is too
    large to read directly and holds the same Export twice:
    `INPUT_TOO_LARGE`, where it said `SNAPSHOT_LIFECYCLE_FAILED`.
  - `snapshot register` with a store that holds a symbolic link, or a
    registered Snapshot whose identity does not match its content:
    `SNAPSHOT_STORE_INVALID`, where it said `SNAPSHOT_LIFECYCLE_FAILED`.
  - Every snapshot command but `snapshot init` with a folder that holds no
    store: `SNAPSHOT_STORE_NOT_FOUND`, and with a store that lost
    `store.json` but holds the rest: `SNAPSHOT_STORE_INVALID`; `snapshot
    build-input` and `snapshot run-all` with a store without a Snapshot:
    `SNAPSHOT_STORE_EMPTY`. The first and the last are new codes; each of
    these said `SNAPSHOT_LIFECYCLE_FAILED`.
  - `support-bundle` with a file or a link in the place of the bundle:
    `SUPPORT_BUNDLE_EXISTS`, where it said `SUPPORT_BUNDLE_PATH_UNSAFE`.
  - The GUI, for an unexpected error of a check, of the Support Bundle, or of
    the opening of the output: `COMMAND_FAILED`, where it said
    `INTERNAL_ERROR`.
  Without a change of code, these texts change from stage A5b-2: the
  message of `INPUT_DISCOVERY_FAILED` says "the input could not be read
  safely", in a one-shot run too, where it said "input discovery or archive
  safety validation failed"; the messages of the stops in the list above are
  those of the same problems in a run; the next step of
  `SNAPSHOT_LIFECYCLE_FAILED` no longer speaks of `snapshot verify`; and
  `HANDOFF_INVALID` says to check first that the folder is the output of
  Run-All. `run-all`, `snapshot run-all`, and `snapshot build-input` keep
  the `OUTPUT_EXISTS` of v1.7.1 for the output `.` or `..`, which stage A5a
  had made `OUTPUT_NAME_INVALID`. From stage A5c, `Ctrl+C` ends every command
  with `ERROR [RUN_CANCELLED]`, or `ERROR [RUN_CANCELLED_AFTER_OUTPUT]` when
  the output was already written, and exit 130, where v1.7.1 printed a Python
  traceback and ended as `SIGINT` does (exit 130 from a shell on POSIX,
  0xC000013A on Windows); see [Cancellation](#cancellation). One `Ctrl+C` no
  longer leaves the hidden staging folder of `snapshot build-input`, the
  files that `normalize-activities` moved into an empty output folder, or the
  hidden temporary file of `support-bundle`. From stage B2b, `doctor`'s
  report for a person gives a finding of a stop the next step of that stop
  (see [Stops that remain](#stops-that-remain)), and its sentence and next
  step for exit 3 no longer speak of FIT files only; the `ERROR` lines of
  `INPUT_NOT_READABLE` and `SNAPSHOT_STORE_NOT_READABLE` say that this app is
  not allowed to open a folder or file, where they said that it may not open
  one. The JSON report does not change.
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
  From stage A3d-3a, `read_export` and the other readers of an Export raise
  `InputNotReadableError` (`intake.source`, with the places inside the
  input) for a folder or file that this app may not open; `walk_paths` and
  `is_disk_full` in `intake.source` and the module `output_location` are
  new; `RunAllError` takes the keyword `places`; `GoldenPathError` takes a
  code as its second argument and has `code`; and `run_snapshot_all`
  checks its output before the build. From stage A3d-3b,
  `SnapshotStoreError` (`SnapshotLifecycleError`) has `code` and `places`;
  `snapshot_status` and `verify_store` can return `notices`; `verify_store`
  raises for a store that it cannot open, that a newer version made, or that
  is not a store, where it returned a failed report; `register_snapshot` can
  return `temporary_files_removed`; `build_approved_input` checks its output
  before the store and raises `SnapshotBuildOutputError`, with the code of
  the place of the output, when it cannot write the build; and the snapshot
  package gains `NOTICE_MESSAGES`, `shown_store_message`, and
  `verification_error`. The build's result gains these keys, which
  `run_snapshot_all` passes to Run-All and `snapshot build-input` prints with
  the rest of the result: `fit_snapshot_numbers` (stage A2b-1),
  `record_changes` (stage A2b-2), `files_left_out` and `files_not_read`
  (stage A3c-2), `files_with_repaired_text` (stage A3d-2c-1),
  `family_file_counts` (stage A3d-4a), `lactate_threshold_counts`, which
  holds `family_asset_counts` and `family_source_record_counts`, and
  `private_field_counts` (stage A3d-4b), `input_file_count` (stage
  A3d-4c-1), and `unread_field_counts` (stage A4c-2).
  From stage A3d-4b, `load_json_assets` in `intake.discovery` takes a
  record `family`, which `normalize_activities`, `normalize_gear`, and
  `normalize_personal_records` pass instead of a name suffix;
  `diagnostics.detector` gains `reads_record_file` and
  `RECORD_FILE_SUFFIXES`, and `normalizers.performance_metrics` gains
  `PRIVATE_FIELD_NAMES`. From stage A3d-4c-1, the build's result gains
  `input_file_count`, which `run_snapshot_all` passes to Run-All, and
  `build_source_completeness` (`diagnostics.completeness`) counts each FIT
  file in each place when it is given `fit_audit` for one Export, whose
  default is now `None`. From stage A3d-4c-2, `RecordMerge`,
  `DailyMetricResult`, and `DailyNormalizationResult` gain
  `row_snapshot_numbers`, the Snapshots that observed each row of a Snapshot
  run (empty in a one-shot run), `normalize_hrv_daily_assets` returns them
  as `row_snapshot_numbers` when it is given `snapshot_numbers`, and
  `normalizers.daily_metrics` gains `SNAPSHOT_PRESENCE_FIELD`,
  `snapshot_presence`, and `observed_snapshots`; the per-Snapshot
  observations of `build_source_completeness` take the FIT rows from their
  `source_observation_counts` instead of the per-second records of the FIT
  audit. From stage A5a, `run_all` (and `run_snapshot_all`) return
  `warning_totals`, made by the new `run_all.warning_totals`, and from stage
  B2c also `warning_items`, made by the new `run_all.warning_items`;
  `output_location` gains `valid_output_name`, `MAX_OUTPUT_NAME_BYTES`,
  `INVALID_NAME_CHARACTERS`, and `WINDOWS_RESERVED_NAMES`, which
  `gui.runs` gave until then and still imports; `check_output_location`
  stops with `OUTPUT_NAME_INVALID` for a name that the GUI refuses and with
  `OUTPUT_PARENT_NOT_FOUND` for a folder of the output that does not exist,
  where it tried the nearest folder that existed; and `doctor_input` reads
  the Activities files. From stage A5b, the new module `stops` gives the
  table of the stops (`STOPS`), the next steps of the reports of `doctor`
  (`NEXT_ACTIONS`), `stop_line`, and `stop_text`; the messages of the
  exceptions say what happened only (`RunAllError`, `GoldenPathError`,
  `SnapshotStoreError`, `MixedExportsError`, the timezone errors, and the
  constants of their messages, of which `INPUT_NOT_READABLE_NEXT_STEP`,
  `STORE_INVALID_NEXT_STEP`, and `STORE_NOT_READABLE_NEXT_STEP` are removed),
  and `NOTICE_MESSAGES` gives the meaning and the next step of the code.
  From stage A5b-2, `build_support_bundle` raises `SupportBundleError` with
  `SUPPORT_BUNDLE_EXISTS` for a file or a link in the place of the bundle,
  and `make_support_bundle` (`gui.outputs`) leaves that check to it;
  `SnapshotStoreError` (`SnapshotLifecycleError`) has the codes of the stops
  above; `stops` gains `SNAPSHOT_STORE_NOT_FOUND`, `SNAPSHOT_STORE_EMPTY`,
  and `SUPPORT_BUNDLE_EXISTS`; `output_location` gains `names_folder_itself`;
  `run_all` gains `ACTIVITIES_EMPTY_MESSAGE`; and `snapshot.store` gains
  `STORE_NOT_FOUND_MESSAGE` and `INPUT_DISCOVERY_MESSAGE`. From stage A5c,
  `stops` gains `RUN_CANCELLED` and `RUN_CANCELLED_AFTER_OUTPUT`, and
  `runner` `CANCELLED_EXIT_CODE`; `build_approved_input` removes its staging
  folder, and `build_support_bundle` its temporary file, also when
  `KeyboardInterrupt` passes through them, and `build_support_bundle` no
  longer removes a file in the place of the bundle after it fails to put the
  bundle there: it puts the bundle there in one step, so a file there then is
  not its own; `gui.server.serve_until_stopped`
  returns the status of the run that `Ctrl+C` cancelled, and the new
  `gui.server.cancel_report` gives its lines.
- Schema: the fields that a disagreement can leave empty are nullable (the
  Hill and Endurance `overall_score`, the four Race Prediction times,
  `vo2max`, and `training_status`), and so is `personal_records.activity_id`
  for a link that cannot be followed; every dataset gains `disagreeing_fields`
  (224 to 241 fields), and readers of `analysis/activities.csv` and
  `analysis/performance_metrics_daily.csv` that rely on the column count see
  the new last columns.
