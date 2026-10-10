# v2.0.0 GUI Design

- Status: implementation in progress; the command-line interface does not
  expose the GUI yet
- Applies to: the v2.0.0 release in preparation; v1.7.0 remains the current
  stable release
- Authority: maintainer design record agreed by the Human maintainer on
  2026-10-10. Product contracts, tests, and the stable release remain the
  behavior authority; this document does not change any existing CLI or output
  contract.

## Purpose

Version 2.0.0 adds a local graphical interface so that people who are not
comfortable with a terminal can run the one-shot Run-All on a local Garmin
Account Data Export, check the result, and prepare a Support Bundle. The
command-line interface stays the stable interface and the reference
implementation; the GUI is a second entry point to the same processing.

The major version marks the addition of the GUI. This design does not change
the CLI commands and options, the Run-All output layout (`run_all_version` 1),
the 17 datasets, stable keys, the `0 / 0 / 3 / 2` Product exit mapping, or the
Snapshot lifecycle contract.

## Decisions

| Topic | Decision |
|---|---|
| Architecture | A browser page served by the installed package on the loopback address `127.0.0.1`. Processing runs in the local Python with the same functions as the CLI, and results are written directly to a new local folder. |
| Scope of 2.0.0 | The one-shot Run-All workflow: pre-run Doctor check, run, post-run handoff validation and Doctor review, optional External-safe Pack, timezone choice, and Support Bundle. |
| CLI | Kept unchanged; `gui` is the only new command. For the same input and options, the GUI and the CLI produce byte-identical output. |
| Languages | English and Japanese at first, from message catalogs; more languages can be added as catalogs. CLI messages and generated output stay in English. |
| Dependencies | No new runtime dependency. The GUI uses the standard library, its own static files, and a web browser on the same machine. |
| Code origin | The GUI is written for this repository under Apache-2.0. No code is copied from the private predecessor project. |
| Pre-release | A release candidate is published to TestPyPI before the stable 2.0.0. |
| Version timing | `main` keeps the 1.7 version until the release candidate (stage 5), and the `gui` command is not exposed until then, so that an urgent 1.7.x fix can still be released from `main`. After the release candidate, 1.7.x fixes wait for 2.0.0. |

## Out of scope for 2.0.0

- Snapshot lifecycle screens (considered for a later 2.x release)
- Passing a ZIP file instead of the extracted folder (the CLI does not support
  it either)
- Viewing or analyzing the normalized data
- A hosted or no-install web version
- Any outbound network feature, including weather enrichment and Garmin sign-in

## Architecture

```text
Browser on the same machine
  -> http://127.0.0.1:<port>/  static page and message catalogs
  -> JSON API on the same origin
Local GUI server (standard library, started by the gui command)
  -> pre-run check, post-run checks, Support Bundle (same functions as the CLI)
  -> child process for Run-All (same run_all function as the CLI)
New local output folder (published atomically by Run-All)
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
- Run-All runs in a child process started from an argument list
  (`sys.executable`, `-P`, `-m`, an internal GUI module, and the same
  arguments that the CLI takes, with absolute paths) without a shell. `-P`
  keeps the current folder out of the child's module search path. The child
  calls the same `run_all` function as the CLI and reports progress events
  and the outcome as JSON lines; the server accepts only stage names, counts,
  statuses, and error codes from them, and discards the child's standard
  error. Short operations (Doctor, handoff validation, and Support Bundle)
  run in the server process.
- Progress: `run_all` has an optional keyword-only `progress` callback that the
  CLI never passes. Events carry only a stage (`discovering`, `normalizing`
  with a step such as `activities` or `fit`, `reading_fit`, `verifying_input`,
  `building_output`, and `writing_output`) and counts. `reading_fit` counts the
  FIT files with distinct content read out of the total, because a file
  repeated under another name is read once. Output is identical with and
  without the callback, and the callback must not raise.
- Cancellation stops the child process and its process group: `SIGINT` on
  POSIX, and `CTRL_BREAK_EVENT` with `CREATE_NEW_PROCESS_GROUP` on Windows,
  followed by termination after 10 seconds and a kill 5 seconds later.
  Run-All builds its output in memory and publishes it by renaming a hidden
  staging folder, so a run cancelled before that leaves no output folder. A
  cancellation that arrives after the rename is reported as a finished run,
  because the output was checked to be absent when the run started. If a
  forced stop leaves a hidden staging folder, the GUI reports it and does not
  delete anything.
- Only one run at a time. Other browser tabs show the running state. While a
  run is active, the Quit button is refused, and `Ctrl+C` cancels the run
  before the server stops.
- The server stops on `Ctrl+C`, on the page's Quit button, or after 10 minutes
  without an API request from the page while no run is active. The page sends
  a heartbeat every 30 seconds; the long margin covers browsers that slow the
  timers of background tabs to once a minute.

## Folder selection

Browsers do not reveal local folder paths, so the GUI offers:

- a path field where a folder path can be pasted, and
- a folder browser served by the GUI server that returns directory names only,
  starting from the home directory. It never returns file names or contents,
  and it leaves out hidden folders, symbolic links, and Windows junctions.

The export folder is checked with the pre-run Doctor. The output is a new folder
inside a chosen parent folder, with a proposed name, and it is validated by the
same rules as the CLI (it must not exist yet). The GUI also requires the parent
folder to exist, so that a mistyped path creates no folders, and the name to be
one portable folder name that does not start with a dot. After a successful
check, the parent defaults to the folder that contains the export, and the
proposed name is `garmin-run-all-YYYYMMDD-HHMM` in local time. Native
operating-system dialogs are not used in 2.0.0.

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

- Child processes are started from an argument list without a shell.
- The folder browser returns directory names only.
- Output folders go through the same checks as the CLI.

## Privacy

- No outbound network access and no external resources. No analytics or
  telemetry.
- Local paths are shown only to the local user. The server does not log
  requests, paths, or secrets, and errors are returned as codes.
- The page explains that Run-All output is personal data, that the
  External-safe Pack is opt-in and still needs human review before it is
  shared, and what the Support Bundle contains.

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
  selected language.
- Tests check that every catalog has the same keys and placeholders and that no
  key is unused.
- CLI output and the generated Run-All documents stay in English, so the output
  contract does not change.
- The GUI guide is written in English and Japanese.

## Accessibility

The GUI supports keyboard operation, accessible names for controls, progress
announced in a live region, WCAG 2.1 AA contrast, no information conveyed by
color alone, and reduced motion. Tests check names, roles, and contrast.

## Repository constraints

- `scripts/static_policy_scan.py` reads every file under `src/`, including
  HTML, JavaScript, CSS, and message catalogs. GUI files must not contain the
  terms that the scan bans in production code, host-path-shaped examples (use
  `/path/to/...` instead), literal secret assignments, or email addresses.
- `pyproject.toml` gains package-data settings for the static files, and the CI
  wheel and source-distribution installation checks verify that the GUI files
  are installed.

## Compatibility and versioning

- `validate-handoff`, `doctor --run-output`, and `support-bundle` currently
  accept only 1.x output versions. They will accept major version 1 and later.
  Outputs produced before 1.4 keep the current legacy handling, and outputs
  with diagnostics are accepted only when they were produced by the installed
  version, including pre-release versions such as `2.0.0rc1`.
- `run_all_version` stays 1 because the output layout does not change.
- Documents that describe the stable 1.x family are updated at release
  preparation, together with migration notes for v1.7.0 to v2.0.0.

## Testing

- Python tests cover the server request checks (secret, `Host`, `Origin`,
  method, content type, and response headers), the API, byte-identical output
  between the GUI path and the CLI on the synthetic Export (with and without
  the External-safe Pack and the timezone option, and with and without the
  progress callback), catalog
  completeness, package data, and the absence of outbound connections, with
  non-loopback network access blocked during the tests.
- JavaScript unit tests run with `node --test` for page logic that does not
  touch the DOM, in CI with the runner's preinstalled Node.
- The Windows CI job starts the server, runs the synthetic Export, and checks
  cancellation.
- Manual checks cover macOS (Chrome and Safari) and Windows (Edge and Chrome),
  including the release candidate on a physical Windows machine. Linux is
  covered by CI only.
- The maintainer compares GUI and CLI output on a real Export by counts and
  identity only, as for earlier releases.

## Release plan

| Stage | Content |
|---|---|
| 0 | This design and the related boundary, charter, Definition of Done, and roadmap updates (documentation only) |
| 1 | Server security, an empty page, language switching, package data, and version checks for any major version; the GUI is not exposed |
| 2 | Run-All workflow: folders, pre-run check, run, progress, cancellation, and result; GUI and CLI output parity |
| 3 | Post-run checks and Support Bundle from the page, failure screens, accessibility, and English and Japanese guides |
| 4 | Verification on Windows, macOS, and browsers, and the maintainer real-data check |
| 5 | Release candidate on TestPyPI with the `gui` command exposed |
| 6 | Stable 2.0.0 release |

Installing the release candidate from TestPyPI uses Production PyPI as an
extra index for dependencies, such as `tzdata` on Windows, that TestPyPI may
not provide.

Each stage is reviewed before it is merged, and dates are not fixed. Exact
screen texts, the granularity of progress events, and whether to add a scripted
browser test to CI are settled in stages 1 to 3.
