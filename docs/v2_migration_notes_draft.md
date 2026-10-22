# v2.0.0 Migration Notes Draft

- Status: draft of the migration notes for v2.0.0, made at the stage A
  checkpoint from the
  [Migration notes outline](v2_data_handling.md#migration-notes-outline-v171-to-v200)
  and a comparison of v1.7.1 with the CLI of stage A on synthetic Exports. It
  covers the CLI and its outputs, with the changes that stage B made to the
  CLI for the GUI, and the `gui` command that stage D1 adds. It is checked
  with the release candidate v2.0.0rc3, which follows it (stage E). When
  v2.0.0 is released, its section moves into
  [Migration Notes](migration_notes.md), which describes the published
  version until then.
- Authority: [v2.0.0 Data Handling](v2_data_handling.md) gives every rule and
  each change by stage. This draft keeps what a user needs to change scripts
  and the readers of the outputs.

## v1.7.1 to v2.0.0

v2.0.0 does not require data migration. Existing Snapshot Stores load and
verify as before, and v1.7.1 still reads a store that v2.0.0 registered to,
but leaves out without a warning a ZIP file inside an Export that v2.0.0
stored without its members because it could not be read. Problems in the
data no longer stop a run: the run leaves out the file or row that has the
problem, or keeps the value empty and marked, finishes, and reports what it
did with warnings that carry codes and counts. Rerun Run-All into a new
folder; earlier outputs are not converted.

| Contract | v2.0.0 position |
|---|---|
| CLI commands and options | Two new commands: `gui`, which opens the local GUI and ends with exit 0 after its Quit button or `Ctrl+C` without a run, or 130 when `Ctrl+C` stopped a run, and with `--create-shortcut` first makes an icon that starts the GUI on macOS and Windows, with the picture of this app or, when it cannot be given, with one line that says so, or ends with exit 2 when it cannot make it, and `snapshot unlock --store <store> --confirm-no-other-command`, which removes the lock file that a stopped registration left; otherwise the same commands and options; `--input` also takes the downloaded Export ZIP file; for `run-all`, `snapshot run-all`, `snapshot build-input`, and `normalize-activities`, the folder for the output must exist and the name of a new output must be one that every system accepts; for `snapshot init`, the folder that holds the new store must exist, and for `support-bundle`, the folder of the bundle must exist and be outside the run output |
| Exit codes | The same `0 / 0 / 3 / 2` Product mapping; `PARTIAL_SUCCESS` (exit 3) covers every file or row left out, and many problems that stopped with exit 2 now finish with exit 3 or 0; `Ctrl+C` ends a command with exit 130 |
| Stops | Every `ERROR` line says what happened and then the next step of its code; some codes change (below) |
| Datasets, schemas, and stable keys | 17 datasets; 247 fields (224 in v1.7.1); ten fields become nullable; stable keys unchanged |
| Output paths | Four audit records added: `audit/activities.json`, `audit/gear.json`, `audit/activity_gear.json`, and `audit/personal_records.json`; `run_all_version` 2 |
| Analysis tables | Columns appended at the end: `analysis/activities.csv` gains `disagreeing_fields` and `start_time_source`, and `analysis/performance_metrics_daily.csv` gains `hill_disagreeing_fields` and `endurance_disagreeing_fields` |
| Snapshot lifecycle contract and policy registry | Unchanged `v1.0` and store format 1; existing Stores need no migration; the rules that merge the Snapshots have their own version, `garmin_snapshot_merge_rules:v2.17` |
| Relationships and privacy boundary | A link whose endpoint is not in the output is kept unresolved instead of removed; warnings carry codes and counts only; the External-safe Pack keeps its columns, and leaves the month of an Activity without a date empty, where v1.7.1 wrote `None` |

What can change:

- Runs that stopped now finish and report a warning:

  | Situation | v1.7.1 | v2.0.0 |
  |---|---|---|
  | A value of a form that its field does not take | Exit 2, such as `OUTPUT_EXPERIENCE_FAILED` | The value is empty, `DATA_VALUE_INVALID`, exit 0 |
  | Daily values of one day that disagree | Exit 2, `DAILY_METRICS_CONFLICT` | The value is empty and named in `disagreeing_fields`, `VALUES_DISAGREE`, exit 0 |
  | The same Activity twice | Exit 2, `RELATIONSHIP_CONTRACT_FAILED` | One row; fields that differ are empty with `VALUES_DISAGREE` |
  | A record without a usable identifier | Exit 2, such as `ACTIVITIES_NORMALIZATION_FAILED` | Left out, `DATA_ROW_LEFT_OUT`, exit 3 |
  | A link to a record that is not in the output | Exit 2, `RELATIONSHIP_CONTRACT_FAILED` | Kept unresolved, `RELATIONSHIP_UNRESOLVED_VALID_LINK` or `RELATIONSHIP_UNRESOLVED_INVALID_LINK`, exit 0 |
  | A JSON file that cannot be read, or a damaged ZIP file inside the Export | Exit 2, such as `DAILY_METRICS_NORMALIZATION_FAILED` or `INPUT_DISCOVERY_FAILED` | Left out and listed, `DATA_FILE_LEFT_OUT`, exit 3 |
  | The same Export given twice | Exit 2, `RELATIONSHIP_CONTRACT_FAILED` | Read once, `INPUT_DUPLICATE_SOURCES`, exit 0 |
  | An Activities file named in another letter case | Exit 2, `ACTIVITIES_EMPTY` | Read |
  | The downloaded Export ZIP file | Exit 2, `INPUT_NOT_DIRECTORY` | Read as the folder extracted from it |

- Runs that finished now stop with exit 2: an input that holds different
  Exports or the records of more than one account (`INPUT_MULTIPLE_EXPORTS`;
  v1.7.1 made one output of both), a folder of the input that this app is
  not allowed to open (`INPUT_NOT_READABLE`; v1.7.1 passed it over), a
  folder for the output that does not exist (`OUTPUT_PARENT_NOT_FOUND`;
  v1.7.1 made it), and an output name that starts with a dot or ends with a
  dot or a space, among others (`OUTPUT_NAME_INVALID`). `snapshot init`
  stops for a folder above the new store that does not exist
  (`SNAPSHOT_STORE_PARENT_NOT_FOUND`) and for a place inside another store
  (`SNAPSHOT_STORE_INSIDE_STORE`); v1.7.1 made the store there. On Windows
  without long paths, `snapshot init` also stops for a place whose files
  would be too long (`SNAPSHOT_STORE_PATH_TOO_LONG`), where v1.7.1 made a
  store that no registration could then write in.
- Runs that ended with exit 0 can end with exit 3: a daily row without its
  date that holds a value, which v1.7.1 left out with a count only, is now
  announced with `DATA_ROW_LEFT_OUT`.
- Codes that change for the same problem; a script that looks for a code
  looks for the new one:

  | Command and situation | v1.7.1 | v2.0.0 |
  |---|---|---|
  | `run-all`: a damaged Export ZIP file as the input | `INPUT_NOT_DIRECTORY` | `INPUT_ZIP_CORRUPT` |
  | `run-all`: Exports of more than one account that share Activities | `RELATIONSHIP_CONTRACT_FAILED` | `INPUT_MULTIPLE_EXPORTS` |
  | `normalize-activities`: a stop | `ERROR:` without a code | `ERROR [CODE]:`, such as `ACTIVITIES_NOT_FOUND` or `OUTPUT_EXISTS` |
  | Snapshot commands: a folder without a store, a store without a Snapshot | `SNAPSHOT_LIFECYCLE_FAILED` | `SNAPSHOT_STORE_NOT_FOUND`, `SNAPSHOT_STORE_EMPTY` |
  | Snapshot commands: a damaged store, a store that holds a link | `SNAPSHOT_LIFECYCLE_FAILED` | `SNAPSHOT_STORE_INVALID` |
  | Snapshot commands (`init`, `register`, `status`, `verify`, `build-input`, and `run-all`): a store that is a symbolic link | `SNAPSHOT_LIFECYCLE_FAILED` | `SNAPSHOT_STORE_SYMLINK` |
  | `snapshot init`: a place that is a file, or a folder that holds other files | `SNAPSHOT_LIFECYCLE_FAILED` | `SNAPSHOT_STORE_NOT_EMPTY` |
  | `snapshot init`: a folder that holds what a store writes, but not `store.json` | `SNAPSHOT_LIFECYCLE_FAILED` | `SNAPSHOT_STORE_INVALID` |
  | `snapshot register`: an input that is a link or not a folder or ZIP file | `SNAPSHOT_LIFECYCLE_FAILED` | `INPUT_SYMLINK`, `INPUT_NOT_DIRECTORY` |
  | `snapshot register`: a link inside the input | `SNAPSHOT_LIFECYCLE_FAILED` | `INPUT_DISCOVERY_FAILED` |
  | `snapshot register`: a label that this app does not take, a label that the store has, a time that cannot be read or times out of order, an input and a store that are the same folder or one inside the other | `SNAPSHOT_LIFECYCLE_FAILED` | `SNAPSHOT_LABEL_INVALID`, `SNAPSHOT_LABEL_EXISTS`, `SNAPSHOT_TIME_INVALID`, `SNAPSHOT_INPUT_INSIDE_STORE` |
  | `snapshot register`, on Windows without long paths: a store whose files would be too long | `RUN_ALL_FAILED` | `SNAPSHOT_STORE_PATH_TOO_LONG`, before the Export is read |
  | `snapshot build-input`: an output that is there already or a link | `SNAPSHOT_LIFECYCLE_FAILED` | `OUTPUT_EXISTS`, `OUTPUT_SYMLINK` |
  | `snapshot build-input`, `snapshot run-all`: no Activities record that can be kept | `SNAPSHOT_LIFECYCLE_FAILED` | `ACTIVITIES_EMPTY` |
  | `snapshot verify`: a folder without a store | A failed report, exit 2 | `SNAPSHOT_STORE_NOT_FOUND` |
  | `support-bundle`: a file or a link in the place of the bundle | `SUPPORT_BUNDLE_PATH_UNSAFE` | `SUPPORT_BUNDLE_EXISTS` |
  | `support-bundle`: a folder of the bundle that is not there | The folders are made | `SUPPORT_BUNDLE_PARENT_NOT_FOUND` |
  | `support-bundle`: a place inside the run output | The bundle is written there, and the output then fails `validate-handoff` | `SUPPORT_BUNDLE_INSIDE_OUTPUT` |
  | `support-bundle`: a folder that cannot be written | `COMMAND_FAILED` | `SUPPORT_BUNDLE_NOT_WRITTEN` |
  | `validate-handoff`, `doctor --run-output`, `support-bundle`: an output of 1.1 to 1.2, or one with `diagnostics/` of another version, such as any v1.4.0 to v1.7.1 output (an output of 1.0 names no version and stays as before) | `HANDOFF_INVALID`, `DOCTOR_AUTHORITY_INVALID`, `SUPPORT_BUNDLE_AUTHORITY_INVALID` | `OUTPUT_OTHER_VERSION`, with the version that made it |
  | Every command: `Ctrl+C` | A Python traceback | `RUN_CANCELLED` or `RUN_CANCELLED_AFTER_OUTPUT`, exit 130 |

  The [table of the stops](v2_data_handling.md#stops-and-next-steps) gives
  every code with its next step, and
  [Stops that remain](v2_data_handling.md#stops-that-remain) the other codes
  that stage A adds.
- Lines of the CLI: an `ERROR` line ends with the next step of its code.
  `run-all` and `snapshot run-all` print `warnings: N` after the exit code and
  `other warnings: candidate=a relationship=b input=c` after the lines of the
  families; `validate-handoff` prints `warnings: N`. `snapshot status` and
  `snapshot verify` can print `NOTE` lines about the store, and `doctor`'s
  report for a person gives each finding and the next step in words. The
  `ERROR` lines of `INPUT_NOT_READABLE` and `SNAPSHOT_STORE_NOT_READABLE`
  say that this app is not allowed to open a folder or file. The next step
  of `SNAPSHOT_STORE_LOCKED` names `snapshot unlock`, and the `ERROR` lines
  of `INPUT_MULTIPLE_EXPORTS` for an Export of another account than the
  Snapshots of a store, and for a store that holds the Exports of more than
  one account, give next steps of their own; the code is the same.
- Outputs of every run, also without any problem in the data:
  `disagreeing_fields` in every row of every dataset (`;` between names in the
  CSV files); `start_time_source` in Activities, `sleep_day_source` and
  `sleep_duration_source` in Sleep, `sub_sport_code` in the FIT sessions, and
  `activity_relationship_reason` and `gear_relationship_reason` in
  `activity_gear`; the four new audit records; Run Quality v2 (in the Support
  Bundle too) and the daily audit records v2; the texts of `START_HERE.md`,
  `DATASET_INVENTORY.md`, `ANALYSIS_HANDOFF.md`, and the Schema Catalog's
  field notes, which explain the new fields; and so every digest that covers
  them. HRV `dedupe_status` `review_required_same_day_differing_values` becomes
  `same_day_values_disagree`, and Run-All no longer gives
  `DAILY_METRICS_REVIEW_REQUIRED`.
- Identifiers: spaces and leading zeros are trimmed, as in v1.7.1; a whole
  number written with a decimal point, such as `123.0`, is the identifier
  `123` and is written as `123`, in its key too; and only the ASCII digits 0
  to 9 are digits, so an identifier written with other digits, such as the
  full-width `"１２３"`, which v1.7.1 read as `123`, is now text. A link that
  names an Activity in this way is a valid link whose endpoint is absent, and
  records that name their account in this way and as `123` name two
  accounts, which stops the run with `INPUT_MULTIPLE_EXPORTS`. A row whose
  identifier cannot be used, such as `1.5`, or 0 in Activities, Gear, and
  links, is left out with `DATA_ROW_LEFT_OUT`.
- The HRV audit record names its date basis
  `fit_end_local_date_from_message_370_field_253_timestamp`, with the
  timezone in `date_timezone`, where v1.7.1 wrote
  `fit_end_jst_date_from_message_370_field_253_timestamp` whatever the
  timezone.
- Nullable fields: the Hill and Endurance `overall_score`, the four Race
  Prediction times, `vo2max`, `training_status`,
  `personal_records.activity_id`, and `activity_gear.garmin_activity_key`. A
  reader that requires a value there takes the row's `disagreeing_fields`, or
  the unresolved status of its link, into account.
- New warning codes: `VALUES_DISAGREE`, `VALUES_UPDATED`,
  `RECORDS_NOT_IN_LATEST_SNAPSHOT`, `INPUT_DUPLICATE_SOURCES`,
  `DATA_FILE_LEFT_OUT`, `DATA_ROW_LEFT_OUT`, `DATA_VALUE_INVALID`,
  `DATA_TEXT_REPAIRED`, `RELATIONSHIP_UNRESOLVED_INVALID_LINK`, and
  `ACTIVITY_FIT_LINK_AMBIGUOUS`. `run_manifest.json` lists the files left out
  (`files_left_out`) and the files that a run does not read
  (`files_not_read`), and `START_HERE.md` gives their numbers.
- Snapshot runs: a Snapshot run of one Export gives what a one-shot run of it
  gives, but for what differs by design, such as the Snapshot files and the
  provenance fields. The counts of files, the audit records, and Source
  Completeness follow the Exports of the store, so the outputs of a store
  change where v1.7.1 counted the files of its build. Registering an Export
  that the store already holds reports the Snapshot that holds it
  (`same_content_as`) instead of adding one. The merge summaries change their
  counters, and the merge rules version is in the outputs.
- Changes across Snapshots: an Endurance Score or UDS day whose values differ
  between Snapshots, which v1.7.1 removed, stays with the differing fields
  empty (`VALUES_DISAGREE`), and a value that a later Snapshot does not give
  is absent, not a change. In Activities, Gear, `activity_gear`, and Personal
  Records, the latest Snapshot's values are current (`VALUES_UPDATED`), an
  explicit empty value removes the earlier value where v1.7.1 kept it, a
  record that the latest Snapshot does not contain is kept
  (`RECORDS_NOT_IN_LATEST_SNAPSHOT`), and the audit records keep every
  earlier value.
- Doctor: `doctor --input` reads the Activities files and reports
  `ACTIVITIES_EMPTY` when no Activities record can be kept, where v1.7.1
  passed such an Export and the run stopped. Its JSON report gains
  `input_counts` (the Activities records, the FIT files, and the files read,
  left out, and not read), and its report for a person a `Counts:` line; the
  report of `doctor --run-output` does not change. Its report for a person
  also names the Exports of a mixed input (`Export found:` lines) and the
  first folder or file that cannot be opened (`Cannot be opened:`), which
  its JSON report never holds. A name with a control character, a line
  break, or a character that turns the direction of the text is written as
  `(a name that cannot be shown)` there and in the `ERROR` lines of
  `INPUT_NOT_READABLE` and `SNAPSHOT_STORE_NOT_READABLE`. In the report for a person, a
  finding whose code is a stop gives the next step of that stop, as the run
  does; the JSON report keeps the `next_action_id` of each finding. For a
  run with exit 3, the report for a person and the words of the next step
  `REVIEW_EXCLUDED_FIT_EVIDENCE`, whose identifier stays, say that files,
  rows, or FIT data were left out, where v1.7.1 spoke of FIT files only.
- Earlier outputs: `validate-handoff`, `doctor --run-output`, and
  `support-bundle` refuse an output of v1.7.1, and those of v1.7.1 refuse an
  output of v2.0.0.
- Python API: see the Python API part of the
  [Migration notes outline](v2_data_handling.md#migration-notes-outline-v171-to-v200).

How to switch:

1. Upgrade the package in a new or existing Python 3.11+ environment when
   v2.0.0 is released:

   ```bash
   python -m pip install --upgrade garmin-running-data-normalizer==2.0.0
   python -m garmin_running_data_normalizer --version
   ```

2. Make the folder for the output of `run-all`, `snapshot run-all`,
   `snapshot build-input`, and `normalize-activities` before the command, and
   give a new output a name that every system accepts: at most 200 bytes, without a dot at its
   start, a dot or a space at its end, or any of `<>:"/\|?*`, and not the
   name of a Windows device.
3. Treat exit 3 as a finished run whose warnings name what was left out, and
   read the warnings in `run_summary.json` (`warnings`, `warning_count`).
4. In scripts that look for an `ERROR` code, use the codes above. A script
   that looks at the exit code only takes 130 as `Ctrl+C`: after
   `RUN_CANCELLED_AFTER_OUTPUT`, also exit 130, the output is complete and
   can be used, and running the command again into the same folder stops
   with `OUTPUT_EXISTS`.
5. Rerun Run-All and `snapshot run-all` into new folders. Stores need no
   migration.
