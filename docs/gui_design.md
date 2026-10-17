# v2.0.0 GUI Design

- Status: design revised on 2026-10-11; implementation in progress; the
  command-line interface does not expose the GUI yet
- Applies to: the v2.0.0 release in preparation; v1.7.1 remains the current
  stable release
- Authority: maintainer design record agreed by the Human maintainer on
  2026-10-10 and revised by the Human maintainer's decisions of 2026-10-11.
  Product contracts, tests, and the stable release remain the behavior
  authority until v2.0.0 changes them as described in
  [Data handling in 2.0.0](#data-handling-in-200).

## Purpose

Version 2.0.0 adds a local graphical interface so that people who are not
comfortable with a terminal can normalize a local Garmin Account Data Export,
keep each Export as a Snapshot, check the result, and prepare a Support Bundle.
The command-line interface stays the stable interface and the reference
implementation; the GUI is a second entry point to the same processing.

Version 2.0.0 also changes how the processing treats problems in the data, so
that one problem does not stop the whole run and no value is dropped or chosen
silently. These changes apply to the CLI and the GUI alike, and they change the
output and exit contracts.

## Principles

1. The CLI and the GUI behave the same. For the same input and options, they
   produce the same output, stop in the same cases, and report the same
   warnings.
2. Problems in the data do not stop the whole run. The run leaves out only the
   file or row that has the problem, or keeps it as it is, finishes, and reports
   what it did in warnings and in the output's records. Records that appear
   twice are merged into one, with a record of where they appeared. No value is
   dropped or chosen silently. A run stops only for safety reasons, for a
   folder that is not an Export, and when the input mixes Exports or accounts.
3. Snapshots are the default. Every registered Snapshot is used in every
   Snapshot run, and a Snapshot cannot be left out. The user can choose the
   Snapshot Store and can also normalize one Export without Snapshots.
4. An Export can be selected as the downloaded ZIP file or as the extracted
   folder, in the CLI and in the GUI.
5. The GUI is for desktop and laptop computers. It is one page that does not
   switch screens and does not use a step-by-step wizard. It offers every
   function in this design, and controls that cannot be used yet are shown
   disabled.

## Decisions

| Topic | Decision |
|---|---|
| Architecture | A browser page served by the installed package on the loopback address `127.0.0.1`. Processing runs in the local Python with the same functions as the CLI, and results are written directly to local folders. |
| Scope of 2.0.0 | The single-page GUI with Snapshots and ZIP input, and the data-handling and CLI changes in this document. |
| CLI | `gui` is the new command. `run-all`, `doctor --input`, and `snapshot register` also accept a ZIP file. Errors, pre-run checks, warning totals, and cancellation are aligned with the GUI. |
| Languages | English and Japanese at first, from message catalogs; more languages can be added as catalogs. CLI messages and generated output stay in English. |
| Dependencies | No new runtime dependency. The GUI uses the standard library, its own static files, a web browser on the same machine, and the operating system's own file dialog. |
| Code origin | The GUI is written for this repository under Apache-2.0. No code is copied from the private predecessor project. |
| Pre-release | A release candidate is published to TestPyPI before the stable 2.0.0. |
| Version timing | `main` keeps a 1.7 version until the release candidate, and the `gui` command is not exposed until then. A 1.7.x fix can be released from `main` only until the first stage A change is merged. After that, an urgent 1.7.x fix would require changing the main-only guard in `publish-pypi.yml`, which needs its own plan and review. |

## Out of scope for 2.0.0

- Leaving out individual Snapshots
- Viewing or analyzing the normalized data
- A hosted or no-install web version
- Any outbound network feature, including weather enrichment and Garmin sign-in
- Phones and tablets

## Page

The page has four areas, in order: 1 Export, 2 Snapshots, 3 Output, and
4 Normalize. Screen texts and layout details were settled in stage B0 with a
screen mockup and a list of every text on the page, which the Human maintainer
reviewed on 2026-10-17; the stage B pull requests follow them.

- 1 Export: a downloaded ZIP file or an extracted folder. For a folder, the user
  confirms that the Export was extracted completely; for a ZIP file, the checks
  in [Selecting an Export](#selecting-an-export) replace that confirmation.
- 2 Snapshots: create or choose the Snapshot Store, and choose how to
  normalize: import this Export and normalize it together with the existing
  Snapshots (recommended), normalize this Export only without Snapshots, or
  normalize the existing Snapshots again without importing.
- 3 Output: the parent folder, the output name, the timezone, and the optional
  External-safe Pack.
- 4 Normalize: the main button, progress, cancellation, the result table, the
  output check, and the Support Bundle.

The four areas stand in a row as boxes, in two columns on a window narrower
than 1280 pixels. One line above them says what to do now; a box with a
problem holds its own next step, and the line points at that box. Under the
boxes come the meaning of the colors and two tables: the steps of the run,
with the seconds of each step, and the results by data family (stage B1a).

- The main button is labeled "Run normalization".
- The headline of a finished run says what its exit code means: "Normalized
  with part of the input left out" (3), "Normalized" (0), or "Could not
  normalize" (2), with the exit code under it. A run cancelled before its
  output shows no exit code.
- The page shows no percentage of progress, because the stages of Run-All give
  none that is correct. It shows the current step and its number, and a bar
  while FIT files are read.
- Cancelling asks for confirmation in the fourth box, not in a dialog of the
  browser.
- "If something is wrong", with the output check and the Support Bundle, is
  folded to one line until it is opened.
- The page changes text with `textContent` only, never with HTML, so that a
  path or a name from the computer is never read as markup.

Progress through the areas:

- On the first launch, the user confirms areas 2 and 3 one at a time with a
  button that accepts their settings.
- On later launches, areas 2 and 3 are confirmed automatically while they keep
  their defaults. An area whose settings change becomes the current step again
  and must be confirmed before the run can start.

Colors have five meanings across the page: blue is the current step or a
running task, green is done or confirmed, yellow is a warning, red is a problem
to fix, and gray is absent or not yet. Only red fills a table row; yellow and
blue rows use a bar at the left edge, an icon, and words. Color is never the
only signal.

Explanations open from an information button (ⓘ) for the External-safe Pack
contents, the timezone, how to normalize, the Snapshot Store, and the output
check and Support Bundle. Before the External-safe Pack or the Support Bundle is
created, the page shows the name and location of the file that will be
created.

Stage A settled the codes `INPUT_ZIP_CORRUPT` (stage A1a),
`INPUT_MULTIPLE_EXPORTS` (stage A3a), and `SNAPSHOT_STORE_LOCKED` (stage
A3d-3b).

## Architecture

```text
Browser on the same machine
  -> http://127.0.0.1:<port>/  static page and message catalogs
  -> JSON API on the same origin
Local GUI server (standard library, started by the gui command)
  -> pre-run check, post-run checks, Support Bundle (same functions as the CLI)
  -> child process for each run (same functions as the CLI)
  -> the operating system's own file dialog, on request
Local Snapshot Store and new output folders
```

- Server: `http.server.ThreadingHTTPServer` bound to `127.0.0.1` with a port
  chosen by the operating system. The URL is printed in the terminal and
  opened with the default browser.
- Static files live under `src/garmin_running_data_normalizer/gui/static/` and
  are shipped as package data. No third-party libraries, CDN, web fonts, or
  build step are used. The server answers only the paths in a fixed table,
  which also fixes the content type of each file. `mimetypes` is not used,
  because Windows can map `.js` to `text/plain` through the registry, and
  `nosniff` then blocks the script.
- Runs (`run-all`, `snapshot register`, and `snapshot run-all`) run in a child
  process started from an argument list (`sys.executable`, `-P`, `-m`, an
  internal GUI module, and the same arguments that the CLI takes, with absolute
  paths) without a shell. `-P` keeps the current folder out of the child's
  module search path. The child calls the same functions as the CLI and reports
  progress events and the outcome as JSON lines; the server accepts only stage
  names, counts, statuses, and error codes from them, and discards the child's
  standard error. Short operations (Doctor, handoff validation, and Support
  Bundle) run in the server process.
- Progress: `run_all` has an optional keyword-only `progress` callback that the
  CLI never passes. Events carry only a stage (`discovering`, `normalizing`
  with a step such as `activities` or `fit`, `reading_fit`, `verifying_input`,
  `building_output`, and `writing_output`) and counts. `reading_fit` counts the
  FIT files with distinct content read out of the total, because a file
  repeated under another name is read once. Output is identical with and
  without the callback, and the callback must not raise. Snapshot runs add
  their stages in stage B. The server keeps the seconds of each stage, with the
  stage's name and the number only, for the steps table of the page (stage
  B1a).
- Cancellation stops the child process and its process group: `SIGINT` on
  POSIX, and `CTRL_BREAK_EVENT` with `CREATE_NEW_PROCESS_GROUP` on Windows,
  followed by termination after 10 seconds and a kill 5 seconds later.
  Run-All builds its output in memory and publishes it by renaming a hidden
  staging folder, so a run cancelled before that leaves no output folder. A
  cancellation that arrives after the rename is reported as a finished run,
  with its result. If a forced stop leaves a hidden staging folder, the GUI
  reports the one that this run created and does not delete anything; one
  that was there before the run started is not reported (stage A5c). A
  failure that the run reported before the cancellation arrived is shown as
  the failure, with its code (stage A5c).
- Only one run at a time. Other browser tabs show the running state. While a
  run is active, the Quit button is refused, and `Ctrl+C` cancels the run
  before the server stops and reports the outcome in the terminal.
- The server stops on `Ctrl+C`, on the page's Quit button, or after 10 minutes
  without an API request from the page while no run is active. The page sends
  a heartbeat every 30 seconds; the long margin covers browsers that slow the
  timers of background tabs to once a minute.

## Selecting an Export

The page offers the operating system's own dialog to choose a folder or a ZIP
file, and a path field where a path can be pasted.

- The dialog is opened with fixed scripts: `osascript` on macOS, PowerShell on
  Windows, and `zenity` or `kdialog` on Linux. When none is available, the page
  offers its own list of folder and ZIP file names, which leaves out hidden
  items, symbolic links, and Windows junctions.
- The scripts are fixed strings that never contain user input or paths. The
  returned path is validated as an absolute path. A dialog opens only for an
  API request with the launch key, only one dialog is open at a time, and a
  dialog that is not answered within a time limit counts as no selection.

A ZIP file is read directly:

- ZIP files inside the Export ZIP are read one level deep. A ZIP file inside
  such a nested ZIP is not read and is recorded.
- Limits on the uncompressed size and the number of files apply to each nested
  ZIP and to the whole Export, against ZIP bombs. They apply to the members
  that are read; members that are not read are recorded, not rejected.
- Nested members get the same checks as the outer ZIP: no paths outside the
  folder, no links, and no encryption.
- The central directory and the CRC of every member that is read are checked,
  so an incomplete or damaged download stops the run with a code instead of
  relying on the user's confirmation.
- Files are read one at a time, so that a large Export does not have to fit
  in memory at once.
- The values of the limits, the folder that serves as the root, and the
  temporary copies of nested ZIP files are in
  [v2.0.0 Data Handling](v2_data_handling.md#an-export-given-as-a-zip-file).

An extracted folder is read as in v1.x, except that folders around the Export
are left out of the paths as for a ZIP file, and the user confirms that the
Export was extracted completely.

## Output

The output is a new folder inside a chosen parent folder, with a proposed name.
The parent folder must exist, so that a mistyped path creates no folders, and
the name must be one portable folder name that does not start with a dot and
has at most 200 bytes in UTF-8, so that the hidden names derived from it stay
within the 255 bytes that many file systems allow for one name. Before a run
starts, an empty hidden folder is created and removed in the parent, which is
what Run-All does when it publishes, so that a parent that cannot be written is
reported at once instead of after the run. `os.access` is not used, because it
can report a read-only or protected location as writable. On Windows without
long paths, a run whose deepest paths inside the staging folder would reach the
limit of 260 characters for a file or 248 for a folder is refused before it
starts (`OUTPUT_PATH_TOO_LONG`). These checks move to shared code in stage A, so
that the CLI applies them too. After the Export is checked, the parent defaults
to the folder that contains the Export, and the proposed name is
`garmin-run-all-YYYYMMDD-HHMM` in local time; a second run in the same minute
adds `-2`, `-3`, and so on.

## After a run

- The output is checked as `validate-handoff` and `doctor --run-output` check
  it. The page shows the counts from the output (datasets, links between
  datasets, and warnings, with the total and the counts per family, and the
  warnings that belong to no family on a separate line), what the Doctor says
  about using the output, the next action, and one line for each registered
  warning code. A folder that changed after the run is reported by code. An
  earlier output can also be selected for the check.
- The Support Bundle is written by default next to the output as
  `<output name>-support-bundle.zip`, because inside the output it would
  contradict the manifest; the user can choose another location. An existing
  file is never replaced. The page explains the six members, that nothing is
  uploaded, and that the bundle needs review before it is shared.
- The page can show the output folder or open its `START_HERE.md` with the
  default application. The server checks that neither was replaced by a link
  or a junction and passes an absolute path without a shell: `open -R` for the
  folder and `open` for the file on macOS, `os.startfile` with the `explore`
  and `open` verbs on Windows, and `xdg-open` elsewhere.

## Data handling in 2.0.0

These rules apply to the CLI and the GUI. The exact lists and output shapes are
in [v2.0.0 Data Handling](v2_data_handling.md), which stage A follows.

| Result | Status | Exit |
|---|---|---|
| Finished; nothing left out and no warning | `PASS` | 0 |
| Finished; every value kept, with warnings | `PASS_WITH_WARNINGS` | 0 |
| Finished after leaving out part of the input (a file or rows) | `PARTIAL_SUCCESS` | 3 |
| Stopped | Fatal error | 2 |

Many cases that stop with exit 2 in v1.x finish with exit 0 or 3 in v2.0.0.

- Values that disagree: normalized datasets keep one row per stable key. When
  the sources, within one Export or across Snapshots, give different values for
  the same key, the row stays, its value is empty and marked, and every
  observed value is kept in the dataset's audit record together with the
  Snapshots that gave it. No value is chosen. In v1.x, differing Endurance Score
  and UDS values across Snapshots remove the row; v2.0.0 keeps it.
- Duplicates: records that appear more than once with the same values, for
  example the same Export given twice or a ZIP file together with its extracted
  folder, are merged into one, and where they appeared is recorded.
- Mixed input: an input that mixes different Exports or accounts stops the run
  (`INPUT_MULTIPLE_EXPORTS`). When the mix cannot be ruled out with confidence,
  the run stops. A mixed output is never produced silently.
- Problems in the data: a file that cannot be read, a value of an unexpected
  type, or a row without an identity is left out, or kept with its raw value,
  and is reported in warnings and records.
- Values that v1.x drops silently are kept or reported: conflicting HRV values;
  Personal Records, activity-gear links, and FIT laps whose linked record is
  missing; and files that the product does not read, which are recorded.
- Stops that v1.x reports without an error code, such as a truncated emoji
  character or an extreme timestamp, get a code and do not stop the run when
  they are problems in the data.
- Runs still stop for: unsafe ZIP members (paths outside the folder, links, or
  encryption), a damaged ZIP file (`INPUT_ZIP_CORRUPT`), exceeded limits, an
  Export that changes during the run, an output that cannot be written or
  already exists, a Snapshot Store left locked by an interrupted registration
  (`SNAPSHOT_STORE_LOCKED`) or failing verification, and an Export without
  Activities.
- Existing Snapshot Stores are read without migration. If the store format must
  change, the change is an automatic migration that keeps the original data
  intact.
- Warnings and other reported names identify Snapshots by number, 1, 2, and so
  on, in the order of their Exports' observation times (stage A2b-2; see
  [v2.0.0 Data Handling](v2_data_handling.md#changes-across-snapshots)). The
  labels that users give to Snapshots appear only in local output, never in
  the Support Bundle or the External-safe Pack.
- The documents that currently describe some behavior differently (see the
  last section of [Known Limitations](known_limitations.md)) are corrected
  together with these changes.

## CLI changes

- `gui` starts the GUI; it is exposed in stage D.
- `run-all`, `doctor --input`, and `snapshot register` accept a ZIP file.
- Warnings about values that disagree name the Snapshots by number.
- The pre-run checks that only the GUI performs in v1.7.1 (output name, an
  existing parent folder, the write check, and the Windows path length) apply
  to the CLI. Relative paths and `~` stay accepted by the CLI as a difference
  in how input is given.
- Errors report the same content in the CLI and the GUI: what happened, the
  next step, and the code.
- `Ctrl+C` reports the cancellation and anything left behind instead of a
  Python traceback.
- Warning totals report the total and the counts per family, with the warnings
  that belong to no family on a separate line.

Stage A5a applies the rules for the output's name and its existing parent
folder to `run-all`, `normalize-activities`, `snapshot build-input`, and
`snapshot run-all`, prints the warning totals in the CLI, passes them to the
GUI's run status, and makes the pre-run check read the Activities files as a
run does (see [v2.0.0 Data Handling](v2_data_handling.md#reports-of-a-run-in-the-cli-and-the-gui)).
Stage B sets the rules for the place of a new Snapshot Store and of a Support
Bundle with the controls that choose them, and the page shows the warning
totals.

Stage A5b gives every stop of the CLI what happened and its next step from
one table (`stops.STOPS`, see [Stops and next steps](v2_data_handling.md#stops-and-next-steps)),
gives the snapshot commands and the Support Bundle the codes of the same
problems in a run, and makes the GUI's server answer an unexpected error of
a check, of the Support Bundle, or of the opening of the output with the
CLI's `COMMAND_FAILED`. Stage B writes the page's texts from the table.

Stage A5c ends every command of the CLI that `Ctrl+C` cancels with
`ERROR [RUN_CANCELLED]`, or `ERROR [RUN_CANCELLED_AFTER_OUTPUT]` when the
output was already written, and exit 130, names what a second `Ctrl+C` left on
lines of their own, and leaves no part of an output on one `Ctrl+C` (see
[Cancellation](v2_data_handling.md#cancellation)). The GUI shows a failure that
came before a cancellation as the failure, reports only the staging folders
that this run made, prints the lines of the CLI in the terminal when `Ctrl+C`
stops the server during a run, and shows the result table for a run whose
cancellation came after its output.

## Security

Requests:

- The server listens on `127.0.0.1` only, so other machines cannot connect. It
  binds without address reuse, and on Windows for exclusive use, so that no
  other program can listen on the same port.
- Other accounts on the same machine can reach `127.0.0.1`, so every API request
  requires a per-launch secret. The secret is passed in the URL fragment, which
  browsers do not send to servers, and never in the query string. The page
  keeps it in memory and in the tab's `sessionStorage`, removes it from the
  address bar, and sends it in the `X-Launch-Key` header with every API
  request. The server compares it in constant time.
- No cookie is used. Browsers send the cookies of `127.0.0.1` to every port on
  it, including servers that other programs or accounts run.
- The `Host` header must be `127.0.0.1:<port>`, and the `Origin` header, when
  present, must match the page origin. This rejects DNS rebinding and
  cross-site requests.
- Every API request uses `POST` with `Content-Type: application/json` and a
  JSON object body of at most 64 KiB. Other methods and content types are
  rejected.
- Request logging is disabled, and errors are answered with short JSON codes
  that do not repeat the request, so that paths and secrets are not written to
  the terminal.

Response headers:

- `Content-Security-Policy` is sent as an HTTP header: same-origin scripts,
  styles, connections, and images only, no inline script or style, no external
  resources, and `frame-ancestors 'none'`, `base-uri 'none'`, and
  `form-action 'none'`.
- `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
  `X-Content-Type-Options: nosniff`, and `Cache-Control: no-store`.

Processing:

- Child processes and file dialogs are started from argument lists without a
  shell, with fixed scripts.
- ZIP files are read with the limits and checks in
  [Selecting an Export](#selecting-an-export).
- Output folders go through the same checks as the CLI.
- The page can open only an output folder and its `START_HERE.md`.

## Privacy

- No outbound network access and no external resources. No analytics or
  telemetry.
- Local paths are shown only to the local user. The server does not log
  requests, paths, or secrets, and errors are returned as codes.
- The page explains that Run-All output and the Snapshot Store contain personal
  data, that the External-safe Pack is opt-in and still needs human review
  before it is shared, and what the Support Bundle contains.
- Snapshot labels given by users stay out of the Support Bundle and the
  External-safe Pack.

## Internationalization

- Every visible string comes from a message catalog (`en.json` and `ja.json`);
  page code contains no user-facing text.
- The language follows the browser setting and can be switched on the page.
  The choice is kept for the browser tab only. Each launch uses a new port,
  which the browser treats as a new site, so the next launch follows the
  browser setting again. Missing translations fall back to English.
- Numbers and dates are formatted for the selected language.
- Timezone suggestions come from the browser's list of IANA names; the server
  checks the name that is entered.
- The server returns error codes, and the page turns them into messages in the
  selected language. Every error shows what happened, the next step, and the
  code to quote in a support request.
- The Japanese catalog uses these terms: 正規化, 取り込む, 既存のスナップショット,
  正規化のしかた, 問い合わせ用ファイル (the English term Support Bundle appears
  only inside its explanation), 目印のファイル (`.single-writer.lock`), 出力の確認
  and 確認済み, このアプリ, and バージョン. It does not use 貯めた, 道具, or 版.
- Tests check that every catalog has the same keys and placeholders and that no
  key is unused.
- CLI output and the generated Run-All documents stay in English.
- The GUI guide is written in English and Japanese:
  [GUI Guide](gui_guide.md) and [GUI の手引き](gui_guide.ja.md).

## Accessibility

The GUI supports keyboard operation, accessible names for controls, WCAG 2.1
AA contrast in the light and dark themes, no information conveyed by color
alone, and reduced motion.

- Progress counts change every second, so they stay out of live regions. A
  hidden live region speaks when the stage changes, when a run stalls or is
  being cancelled, and when it ends. Live regions change only when their text
  changes, so that screen readers do not repeat them.
- When a run ends, focus moves to the result heading; when it stops, to the
  heading of the stop in the box that it concerns (stage B1a). When a box is
  confirmed, focus moves to the next box. When a button that had focus stays
  disabled after its action, focus moves to the nearest heading.
- Losing the server is shown as an alert at the top of the page.
- Tests check labels, button names, heading order, live regions, focus
  targets, and the contrast of the stylesheet's colors. Keyboard-only use and
  a screen reader (VoiceOver on macOS) are checked by hand in stage C; a
  scripted browser test is not part of CI in 2.0.0.

## Repository constraints

- `scripts/static_policy_scan.py` reads every file under `src/`, including
  HTML, JavaScript, CSS, and message catalogs. GUI files must not contain the
  terms that the scan bans in production code, host-path-shaped examples (use
  `/path/to/...` instead), literal secret assignments, or email addresses.
- `pyproject.toml` ships the static files as package data, and the CI wheel and
  source-distribution installation checks verify that the GUI files are
  installed.

## Compatibility and versioning

- v2.0.0 changes the output and exit contracts as described in
  [Data handling in 2.0.0](#data-handling-in-200). The migration notes for
  v1.7.1 to v2.0.0 list every change.
- `validate-handoff`, `doctor --run-output`, and `support-bundle` accept
  Product major version 1 and later, as released in v1.7.1. Outputs that
  contain `diagnostics/` are accepted only when they were produced by the
  installed version, including pre-release versions such as `2.0.0rc1`.
- `run_all_version` becomes 2 if the output layout changes; stage A decides.
- Existing Snapshot Stores are read without migration, or with an automatic
  migration that keeps the original data intact.

## Testing

- Python tests cover the server request checks (secret, `Host`, `Origin`,
  method, content type, and response headers), the API (with the operating
  system's opener and file dialog replaced), byte-identical output between the
  GUI path and the CLI on synthetic Exports (with and without the External-safe
  Pack, the timezone option, Snapshots, and ZIP input, and with and without
  the progress callback), catalog completeness, package data, and the absence
  of outbound connections, with non-loopback network access blocked during the
  tests.
- JavaScript unit tests run with `node --test` for page logic that does not
  touch the DOM, in CI with the runner's preinstalled Node.
- The Windows CI job starts the server, runs the synthetic Export, and checks
  cancellation.
- At the end of stage A, the CLI changes are checked on their own with the
  synthetic golden outputs and a draft of the migration notes, before the GUI
  work of stage B.
- Each stage B pull request checks the screen texts and the points where a user
  may hesitate, not only the layout.
- Manual checks in stage C cover macOS (Chrome and Safari) and Windows (Edge
  and Chrome), including the release candidate on a physical Windows machine,
  and a person who has not seen the GUI before, who must be able to select an
  Export and finish a normalization without instructions. Linux is covered by
  CI only.
- The maintainer compares GUI and CLI output on a real Export by counts and
  identity only, as for earlier releases.

## Release plan

| Stage | Content |
|---|---|
| 0–4a (done) | The first GUI, for the one-shot Run-All (pull requests #62 to #72); its code is included, without a command, in v1.7.1 |
| 0 (revision) | This revision of the design and the related documents (documentation only) |
| A | The data-handling and CLI changes, in several pull requests, each planned and reviewed |
| A checkpoint | CLI-only verification with synthetic golden outputs and a draft of the migration notes |
| B | The single-page GUI, in several pull requests, each checked for screen texts and points of hesitation |
| C | Verification on Windows (including a physical machine), macOS, and browsers; the maintainer real-data check; and a first-time user who finishes a normalization without instructions |
| D | Release candidate on TestPyPI with the `gui` command exposed |
| E | Stable 2.0.0 release |

Installing the release candidate from TestPyPI uses Production PyPI as an
extra index for dependencies, such as `tzdata` on Windows, that TestPyPI may
not provide.

Each stage is reviewed before it is merged, and dates are not fixed.
