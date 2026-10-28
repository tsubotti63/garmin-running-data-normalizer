# v2.0.0 GUI Design

- Status: design revised on 2026-10-11; implemented in v2.0.0, whose `gui`
  command opens the GUI. The view page and the colors of the page are added
  in v2.1.0; the sections marked v2.1.0 describe them.
- Applies to: stable v2.1.0
- Authority: maintainer design record agreed by the Human maintainer on
  2026-10-10 and revised by the Human maintainer's decisions of 2026-10-11.
  Product contracts, tests, and the stable release remain the behavior
  authority; v2.0.0 changes them as described in
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
5. The GUI is for desktop and laptop computers. The normalization page is one
   page that does not switch screens and does not use a step-by-step wizard.
   Since v2.1.0, the view page is a second page in the next tab, and it does
   not switch screens either (decision 20261026-11).
   Each page offers every function in this design, and controls that cannot
   be used yet are shown disabled.

## Decisions

| Topic | Decision |
|---|---|
| Architecture | A browser page served by the installed package on the loopback address `127.0.0.1`. Processing runs in the local Python with the same functions as the CLI, and results are written directly to local folders. |
| Scope of 2.0.0 | The single-page GUI with Snapshots and ZIP input, and the data-handling and CLI changes in this document. |
| Scope of 2.1.0 | The view page in the tab next to the normalization page, which shows the numbers of an output that this version made as panels on one time axis; the `series` command, which writes the same numbers to a CSV file; and the colors of the page. Nothing is sent, and the numbers are not interpreted (decisions 20261026-9, 20261026-10, and 20261026-11). |
| CLI | `gui` is the new command. `run-all`, `doctor --input`, and `snapshot register` also accept a ZIP file. Errors, pre-run checks, warning totals, and cancellation are aligned with the GUI. |
| Languages | English and Japanese at first, from message catalogs; more languages can be added as catalogs. CLI messages and generated output stay in English. |
| Dependencies | No new runtime dependency. The GUI uses the standard library, its own static files, a web browser on the same machine, and the operating system's own file dialog. |
| Code origin | The GUI is written for this repository under Apache-2.0. No code is copied from the private predecessor project. |
| Pre-release | A release candidate is published to TestPyPI before the stable 2.0.0. |
| Version timing | `main` keeps a 1.7 version until the release candidate, and the `gui` command is not exposed until then. A 1.7.x fix can be released from `main` only until the first stage A change is merged. After that, an urgent 1.7.x fix would require changing the main-only guard in `publish-pypi.yml`, which needs its own plan and review. |

## Out of scope for 2.0.0

- Leaving out individual Snapshots
- Viewing or analyzing the normalized data (v2.1.0 adds viewing, without
  interpreting: see [The view page](#the-view-page-v210))
- A hosted or no-install web version
- Any outbound network feature, including weather enrichment and Garmin sign-in
- Phones and tablets

## Out of scope for 2.1.0

- Laying the years over each other, aligning the starts of periods, and
  relating two items
- Views by shoe or of personal records, the bands of the training status, and
  moving averages
- Saving a chart as a picture or a file
- Outputs of other versions on the view page
- Interpreting the numbers, and coaching
- Any outbound network feature; weather enrichment (Open-Meteo) stays deferred
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
- Quitting asks for confirmation in the bar at the bottom, as forgetting the
  settings does (v2.0.1, stage F2). While the server stops, the bar says so
  and the page takes no action; once it stopped, the line above the boxes
  says that the app has stopped and how to start it again. A connection lost
  on the way is told as any lost connection. The language and the help
  panel keep working, since they do not use the server; "Show tips" and,
  from v2.1.0, the colors of the page, whose choices the server remembers,
  do not.
- The bar at the bottom stays on the screen, so that Quit and the language
  can be reached without scrolling (v2.0.1, stage F2).
- After a run that finished, while no box changed, "Run normalization" can
  be pressed again, and a line under it says that it normalizes again with
  the name in the name field and that the output stays; in the way that
  imports, that the same Export is not imported twice, since the
  registration knows it by its content (v2.0.1, stage F2).
- "If something is wrong", with the output check and the Support Bundle, is
  folded to one line until it is opened.
- The page changes text with `textContent` only, never with HTML, so that a
  path or a name from the computer is never read as markup.

Progress through the areas:

- On the first launch, the user confirms areas 2 and 3 one at a time with a
  button that accepts their settings.
- On later launches, areas 2 and 3 are confirmed automatically while they keep
  the places that the settings of the earlier launch remembered (stage B4c):
  area 2 when the remembered store opens without a problem, and area 3 when
  the remembered folder is there or is the default place; their summaries end
  with "(as last time)". An area whose settings change, also when another
  store is opened or the place of a new one is chosen, becomes the current
  step again and must be confirmed before the run can start. A launch is a
  later one when its settings remember a store or a folder for the output.
  Without a remembered store, area 2 is confirmed as on a first launch, so
  that no store is made unseen.

The settings of an earlier launch (stage B4c, decision 20261017-15): the GUI
remembers, in one file, the store and the folder for the output of the last
run that made its output (also one whose cancellation came after it), the
outputs that runs made (the latest ten, for the check of an earlier output in
stage B5), and whether the tips show, as the person last switched them. Only
the names of places are kept, never what is in them, and never the place of an
Export; the output name, the language, and the way to normalize are not
remembered (from v2.2.0 the timezone is; see below). Places are remembered when a run makes its output, not
when they are chosen, so that a place opened by mistake does not come back.
The file is `gui-settings.json` in this app's folder
`garmin-running-data-normalizer`, in the place that the system keeps for each
person's application data: `Library/Application Support` in the home folder
on a Mac, `LOCALAPPDATA` on Windows (or `AppData/Local` in the home folder),
and `XDG_STATE_HOME` elsewhere (or `.local/state` in the home folder, which
is made with `.local` when they are missing, as the XDG Base Directory
Specification asks; folders that are there keep their permissions). Only this
app's folder is made besides, owner-only. A remembered store that is not
found makes area 2 red with "Open another store…", "Look again", and "Create
a new store…", and a remembered folder for the output that is not found makes
area 3 red with "Choose…" and "Look again"; neither is made again, except the
default place `GarminRunningData`, which a run makes as on a first launch,
since an output is always a new folder. "Forget the remembered settings…" in
the bar at the bottom asks first, and then removes the file only, never while
a run is active; the stores and the outputs stay, and the next launch is a
first one. A file that cannot be used is told in the bar, and the launch is a
first one: one of another form is replaced by the next settings, and one of a
newer version is never written over. The CLI remembers nothing.

From v2.1.0 the settings also remember the colors of the page when the person
chose Light or Dark (`theme`), and the items that the view page showed and
whether its item shelf was open (`view_items` and `view_shelf`, by the names
of the items only); a value of another form of one of these keys is left out
alone, and the other settings are still used. "Forget the remembered
settings…" forgets them too, and says so in a sentence after the words of
2.0.x. The settings change one at a time under a lock of the server, so that
a run that ends while the person switches the tips or the colors keeps both
(a fix of 2.0.x); two GUIs of two processes that write at the same moment can
still keep only one of the two values, and the other keeps the value that it
had before.

From v2.2.0 (stage K1) the file is of format 2. It also remembers the timezone
of the last run that made its output (`timezone`), which box 3 takes at the
next launch in place of the default, so that a later launch decides box 3 by
itself with that timezone ("(as last time)"); only a name that the CLI takes
for `--timezone` is kept. For the view page it remembers the layouts of the
person (`view_layouts`: an id that the server gives, a name of 1 to 30
characters, and one to six items; up to 20), the built-in layouts hidden
(`view_layouts_hidden`), the layout used last (`view_layout`), the period and
the grouping (`view_period` and `view_grain`, by the rules of a request of the
numbers), and the activity types counted (`view_types`) when the whole choice
can be kept: up to 64 names of up to 128 characters, each once, without a
control or direction character. A request of the numbers takes any choice of
the types of the output, as 2.1.0 did; a choice that the settings cannot keep
whole is not remembered, and the one before is forgotten, so that the next
opening counts the types counted at first, never other types than those
chosen. A value of another form of one of these keys is left out alone, and
of the layouts, the one layout. A name of a layout is kept in NFC without the
spaces around it, without a control character, a separator of lines or
paragraphs, or a character that changes the direction of the text; two names
are compared in NFKC and casefold, and a name of the person cannot be that of
a built-in layout in either language or of another of the person's layouts.
The layouts change one at a time under the lock of the server: the page sends
one change (add, rename, overwrite, move, remove, hide, show, or reset), and
the server reads the file, changes it, and writes it, so that two tabs keep
both changes. A layout removed or hidden is no longer the one used last.
Settings whose file would be over 64 KiB are not written (a fix of 2.1.0,
which wrote such a file and then could not read it): the file before stays,
and the page is told that they were not remembered. 2.1.0 and 2.0.x take a
file of format 2 as one of a newer version: they do not use it and never write
over it, and start as a first launch, so that what 2.2.0 remembers is not lost
by going back; their "Forget the remembered settings…" removes it, with the
layouts.

The Snapshot Store (stage B4a): the second box shows the place of the store
and its Snapshots, in the order of the times of their Exports, with the
number of files of each. At launch the page looks at the default place,
`GarminRunningData/snapshots` in the home folder: it opens the store there,
or says that there is none yet. "Open a store in use…" and "Open another
store…" open a store that the user chooses, or the one in the folder
`snapshots` of the chosen folder. "Choose where to create it…" and "Create a
new store…" choose the folder in which a new store will be made, as its
folder `snapshots`, or the chosen folder itself when it is named `snapshots`;
a store there is opened instead. The place is checked as `snapshot init`
checks it, but nothing is made until a run imports an Export into it.
"Check the Snapshots" checks the store as `snapshot verify` does. The page
reads a store with the functions of the CLI's snapshot commands; only a run
writes in it. Each button opens the system's dialog for a folder, or the
page's own folder list without one. On Windows without long paths, the
files of a store add up to 189 characters to its path (stage B6b), so the
place of a new store and an import are checked against the limits before
anything is written, as an output is, and stop with
`SNAPSHOT_STORE_PATH_TOO_LONG` in `snapshot init`, `snapshot register`, and
the page alike; `snapshot status` tells it of an open store, which the page
then shows in red for an import, and in yellow for the other ways (stage
B6c; until then, the import stopped with `COMMAND_FAILED`).

Importing (stage B4b-1): the second box offers three ways to normalize.

- Import this Export into the Snapshots and normalize them together, the
  default and recommended way. A new store is made at the chosen place when
  the run starts. The first box then asks for the name of the Snapshot and
  the time of the download. The name is the date of the download by
  default, with `-2`, `-3`, and so on when the store has it, and takes 1 to
  64 letters, digits, dots, underscores, or hyphens, starting with a letter
  or a digit; the page checks it before the button can be pressed. The time
  is that of the ZIP file, which the browser set when it downloaded it, or
  that of the newest file of an extracted folder, which is near the time
  when the Export was made; a line says which, and the user can change it.
  The registration records the same time as the request and the
  observation of the Export. The two fields are for the next import: once a
  run has finished, they are hidden until something changes, and the second
  box shows what the run imported (stage B6a, so that a proposed name that
  no Snapshot took is not read as one). They show again, with the reason,
  while the name or the time keeps a run from starting, and after an import
  the page proposes the next name again, also when the person typed the one
  that the import took.
- Normalize this Export only, without the Snapshots. The parts of the store
  turn gray, and a note says that this way does not use the store; the
  store's line that a new store is made there does not show then (v2.0.1,
  stage F2).
- Normalize the existing Snapshots again, without an Export, for example
  with a new version or other settings of the output. A link under the first
  box chooses it when the store has Snapshots; the first box then takes no
  Export, and "Choose an export instead" goes back.

The list of the Snapshots says which will be used: all of them, with a state
column (imported before, to import now, imported now), in the order of the
times of their Exports, never in the order of their import; for those imported
on this page, the time is the time of the download. While it holds the Export
to import and a Snapshot to compare it with, a line under it says that an
Export of the same content adds no new Snapshot, which the import finds out
(stage B6a: the checkpoint of stage B saw "the second Snapshot, to import now"
before a run of the same Export). As in the mockup, a narrow box leaves out
the column of the times, and a narrower one that of the numbers of files. The
steps of a run follow the way, as the mockup gives them: the import reads and
checks the Export, then makes the store and imports it as the first Snapshot,
or imports it as the Nth; the Snapshots are checked, and the one Snapshot is
read, or the N are built into one input; Run-All follows. Normalizing again
starts at the check of the Snapshots and builds the existing ones. The result
says where the Export came in the order, or that the store held the same
Export already, so that no Snapshot was added; a run that stops after its
import says that the import is done, so that the same Export adds no Snapshot
when the run is started again. While the way uses the store, a problem of the
store, or of the name or the time, turns its box red and stops the run before
it starts; for this Export only, the store's lines show it as in stage B4a, in
red, or in yellow for a lock file or an interrupted import, and nothing stops.
A cancelled import takes its lock back as the CLI does, and the next
registration completes an interrupted one; a lock file that a forced stop left
stops the next import with `SNAPSHOT_STORE_LOCKED`, and the store's lines say
how to remove it, as `snapshot status` does.

When things go wrong with the store (stage B4b-2): under the stop of a lock
file, for an import, the page says when the lock file was written, so that a
lock that an import holds now can be told from one that a stopped import left,
and offers "Remove the lock file" after the person checks "I checked that no
other normalization or snapshot command is running". It removes the lock file
only, with the function of `snapshot unlock`, never while a run of this app is
active, and the import starts again with "Run normalization", so that it never
starts before the third box is set (the mockup's button also started the
import). Cancelling an import asks with the words of the text book (the next
import completes the store), and a cancelled import, also one that was stopped
by force, tells in the fourth box what it left in the store, as the CLI does
after a cancelled registration. The three cases of a mix have the words of the
text book: the input itself in the first box, and an Export of another account
than the Snapshots, or a store that holds the Exports of more than one
account, in the second box.

Colors have five meanings across the page: blue is the current step or a
running task, green is done or confirmed, yellow is a warning, red is a problem
to fix, and gray is absent or not yet. Only red fills a table row; yellow and
blue rows use a bar at the left edge, an icon, and words. Color is never the
only signal.

Explanations open from an information button (ⓘ) under the control that they
explain, and stay open until the button is pressed again or Escape is pressed;
nothing opens on hover. Stage B1b places them at how to normalize, the
timezone, the External-safe Pack contents, the exit code, and the output check
and Support Bundle; stage B4a adds the Snapshot Store and the default place.
Before the External-safe Pack or the Support Bundle is created, the page
shows the name and location of the file that will be created.

The Help button at the top right opens a help panel at the right of the window
(stage B1b). The panel pushes the page aside instead of covering it, and the
boxes fold to two columns while it is open on a window narrower than 1680
pixels. It has five parts: how to use, in which each step lights up its box,
and whose last step, reading the result, is the step to do after a run that
finished and is done once START_HERE.md was opened from the page, which only
the page remembers, until the next run (v2.0.1, stage F2);
questions; words; using the normalized data with an AI, with example
questions that can be copied; and "If something is wrong", which reports a
problem on GitHub (stage B5c). Close or Escape closes it, and focus returns to
the button that opened it, or to the Help button when that button is no longer
shown. "Show tips" shows one line under each box heading. It is on at a
first launch and off at later ones, and the settings remember the person's
choice (stage B4c). The help panel, the tips, and the information
buttons say only what the page can do at its stage.

The GitHub report (stage B5c), as the Human maintainer decided on 2026-10-18:
the line "If this does not solve it, report it on GitHub (you can check the
values before it opens)." ends the explanation of a stop in the red boxes, in
the check of the Export and the Snapshot Store, and in the output check and
under the buttons of the fourth box; a note under a field (the name and the
folder of the output, or the name and time of an import) has none, as the
mockup v10 has it. In the first and second box, the line comes after the
buttons that fix the stop: the choice of one Export of a mixed input, and the
check and the button that remove the lock file (stage B6a). "Report on
GitHub…" ends "If something is wrong" of the fourth box. Either opens "If
something is wrong" in the help panel, which shows first the values that go in
the Bug report form of the repository
(`.github/ISSUE_TEMPLATE/bug_report.yml`), and "Open on GitHub" opens the form
with them in a new tab. The values are English, as the form is, in the order
of its fields: the title `[Bug]: <code> in the GUI`, the part of the page or
its button, the operating system and its version, `None (run from the GUI)` as
the shell, the version of Python, the line that `--version` prints, whether
this launch is the first, the kind of the Export and the way to normalize, the
exit code (2 for a stop, or 0 or 3 for a finished run), and the code. A report
from a stop is about that stop; one from the fourth box or the help panel is
about the first stop that the page shows, or else the last run. The person
writes the problem, chooses whether the synthetic data shows it, and ticks the
four checks of privacy on GitHub. No place, name, count, date, time, timezone,
account, or key goes in; the server gives the three values of the computer in
a plain form only (see [Privacy](#privacy)). The table and the address come
from the same rows, so that the address carries what the table shows. The
panel says that the values reach GitHub when the form opens and are public
only when the report is submitted, that GitHub may ask the person to sign in
first, and that a vulnerability goes to the private channel of the repository
instead.

The help panel also links to the GUI guide of its language and to other
documents of the repository at the tag of this version (`v<version>`), so
that they describe the version that is installed, to the private channel,
and to the data management page of Garmin. In development the version keeps
the name of the last release, whose tag has no GUI guide; those links open
once the tag of v2.0.0 is made.

Stage A settled the codes `INPUT_ZIP_CORRUPT` (stage A1a),
`INPUT_MULTIPLE_EXPORTS` (stage A3a), and `SNAPSHOT_STORE_LOCKED` (stage
A3d-3b).

## Colors of the page (v2.1.0)

The bar at the bottom of both pages offers Appearance: Match this computer,
Light, or Dark (stage G3a, decision 20261026-10). Match this computer uses the
colors that the browser reports, as 2.0.x does. The settings remember Light
and Dark as `theme` (Match this computer is no key), in the file of format 1,
so that 2.0.x still reads the file and leaves the colors out.

- The page never shows the other colors first. `theme.js`, a classic script in
  the head of both pages, sets `data-theme` on the root element before the
  page is drawn, from this tab's `sessionStorage`, or, on the first page of a
  launch, from the address: the launch puts the colors after the key in the
  fragment (`#key=…&theme=dark`), which the browser never sends, and the
  values there are separated by `&` and read as the key is read. It also
  keeps a choice from the address in this tab's `sessionStorage`, since a
  reload has no fragment; it writes nothing else, and the page removes the
  fragment with the key.
- The dark colors are one set, in two blocks of `styles.css`: one for the
  browser's dark (`prefers-color-scheme: dark`) unless Light was chosen, and
  one for Dark. A test checks that the two blocks are the same, and that both
  set every color. Light keeps the light colors also where the browser is
  dark.
- A change is told to the other tabs of the launch with a `BroadcastChannel`,
  which carries the colors, and the notice that the settings were forgotten,
  only; never the key.
- Where the system forces its own colors, the page takes the system's colors,
  and the radio buttons of Appearance still show.
- While the page has no connection to the server, the choice cannot be
  changed, as "Show tips" cannot.

## Architecture

```text
Browser on the same machine
  -> http://127.0.0.1:<port>/  static page and message catalogs
  -> http://127.0.0.1:<port>/view  the view page in the next tab (v2.1.0)
  -> JSON API on the same origin
Local GUI server (standard library, started by the gui command)
  -> pre-run check, post-run checks, Support Bundle (same functions as the CLI)
  -> child process for each run (same functions as the CLI)
  -> the operating system's own file dialog, on request
Local Snapshot Store and new output folders
```

- Server: `http.server.ThreadingHTTPServer` bound to `127.0.0.1` with a port
  chosen by the operating system. The URL is printed in the terminal and
  opened with the default browser. From the icon of `gui --create-shortcut`
  (stage E1d), the terminal is the window that the icon opens: the Terminal on
  macOS, and a console minimized in the taskbar on Windows.
- Static files live under `src/garmin_running_data_normalizer/gui/static/` and
  are shipped as package data. No third-party libraries, CDN, web fonts, or
  build step are used. The server answers only the paths in a fixed table,
  which also fixes the content type of each file. `mimetypes` is not used,
  because Windows can map `.js` to `text/plain` through the registry, and
  `nosniff` then blocks the script. From v2.1.0 the table also has `/view`
  (`view.html`) with `view.css`, `view.mjs`, `view_flow.mjs`, and
  `view_chart.mjs`; `launch.mjs`, which holds the key of a launch and the
  calls of the API for both pages; and `theme.js`.
- From v2.1.0 the server also opens an output for the view page and answers
  its numbers in its own process (`/api/view/open` and `/api/view/series`),
  and remembers the colors and the items of the view page
  (`/api/settings/theme` and `/api/settings/view`); see
  [The view page](#the-view-page-v210). From v2.2.0 `/api/settings/view` also
  takes the layout used last, the period, the grouping, and the activity
  types, `/api/settings/layouts` changes the layouts one change at a time, and
  `/api/view/open` gives the built-in layouts by their ids and items.
- Runs (`run-all`, `snapshot register`, and `snapshot run-all`) run in a child
  process started from an argument list (`sys.executable`, `-P`, `-m`, an
  internal GUI module, and the same arguments that the CLI takes, with absolute
  paths) without a shell. `-P` keeps the current folder out of the child's
  module search path. The child calls the same functions as the CLI and reports
  progress events and the outcome as JSON lines; the server accepts only stage
  names, counts, statuses, and error codes from them, and discards the child's
  standard error. Short operations (Doctor, handoff validation, and Support
  Bundle, and from stage B4a opening, listing, and checking a Snapshot Store
  and checking the place of a new one, and from stage B4b-2 removing its
  lock file) run in the server process.
- From stage B4b-1 the child has three ways: this Export only (`run_all`),
  importing it (`initialize_store` for a new store, `register_snapshot`, then
  `run_snapshot_all`), and normalizing the Snapshots again
  (`run_snapshot_all`). After an import it reports where the Snapshot came in
  the order, whether the store held the same Export, and the number of
  Snapshots, before the run goes on. It stops with the codes with which the
  CLI stops (`runner.stop_of`), and for an error that no code describes, with
  `COMMAND_FAILED` during the import and `RUN_ALL_FAILED` after it, as the
  CLI's commands do. From stage B4b-2 a stop of `INPUT_MULTIPLE_EXPORTS`
  names its case (the input, an Export of another account, or a store of
  more than one account), and after a cancelled import the server gives the
  notices of the store with the function of the CLI's cancelled
  registration: codes only. The server checks the request before the child starts
  with the functions that the registration and the store use, so that each
  rule is written once: the name of the Snapshot, the time, the Export and
  the store apart, the name free in the store, a store with Snapshots to
  normalize again, and the place of a new store; an existing store is read
  only when no run is active. A new store at the default place makes
  `GarminRunningData` as for the output. The page and the server refuse a
  name that the store has before the Export is read, while the CLI reads the
  Export first and takes the same Export again under any name, one that the
  store has included: with another name, the outcome is the same.
- The account boundary of a store that the page makes is the server's own:
  `gui-` and 24 hexadecimal digits from `secrets`, never a value that the
  page sends, and the page never shows it. It is in `store.json`, the
  manifests, and the records of the build (the lineage and the build's
  hash), and so in the output. The CLI uses such a store without
  `snapshot init`: `snapshot register`, `status`, `verify`, and `run-all`
  take it as it is, and `snapshot init` with another `--account` stops,
  since the store belongs to another account boundary. To compare the output
  of the page with that of the CLI, `snapshot init` is given the same
  boundary.
- Progress: `run_all` has an optional keyword-only `progress` callback that the
  CLI never passes. Events carry only a stage (`discovering`, `normalizing`
  with a step such as `activities` or `fit`, `reading_fit`, `verifying_input`,
  `building_output`, and `writing_output`) and counts. `reading_fit` counts the
  FIT files with distinct content read out of the total, because a file
  repeated under another name is read once. Output is identical with and
  without the callback, and the callback must not raise. From stage B4b-1,
  `register_snapshot` and `run_snapshot_all` take the same optional callback,
  and a Snapshot run reports its stages before those of Run-All:
  `creating_store`, which the child reports before it makes a new store,
  `reading_export` and `importing`, with the files of the Export read, then
  copied, out of all (an Export that the store holds already is not copied),
  `checking_store`, and `building_snapshots` with the number of Snapshots.
  The store and the output are identical with and without the
  callback, and a stop or a cancellation in the callback takes back the lock
  and the record of the registration as any stop does. The server keeps the
  seconds of each stage, with the stage's name and the number only, for the
  steps table of the page (stage B1a).
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
- The server stops on `Ctrl+C`, on the page's Quit button, or after 60 minutes
  (10 minutes before v2.1.0) without an API request from the page while no run
  is active. The page sends a heartbeat every 30 seconds; the long margin
  covers browsers that slow the timers of background tabs to once a minute,
  and Safari, which stops them a few minutes after its window is hidden with
  Command-H: in a check on 2026-10-27 with 10 minutes, the GUI stopped about
  14 minutes after Safari was hidden, and kept running while Safari was only
  behind other windows, with the normalization page alone and with the view
  page as well. A page that was closed leaves the server running for up to an
  hour, and the help says so. The `gui` command does not look for a GUI that
  is running, so launching it again within that hour starts a second server
  beside the first, on a port of its own; the first one stops by itself an
  hour after the last request of its page.

## Selecting an Export

The first box has two buttons, "Choose ZIP file…" and "Choose extracted
folder…", because the dialogs of the three systems choose either a file or a
folder, not both (stage B3a). Each opens the operating system's own dialog,
and the page checks the chosen place at once. A path can also be pasted in the
field and checked with "Check the export". The page leaves out the spaces
around a pasted path, and uses a chosen path as it is.

- The dialog is opened with fixed scripts: `osascript` on macOS, PowerShell on
  Windows (with `-STA` and output in UTF-8, so that names in Japanese reach
  the server intact), and `zenity` or `kdialog` on Linux with a display. When
  none is available (`CHOOSER_NOT_AVAILABLE`), the page offers its own list of
  folder and ZIP file names instead, which leaves out hidden items, symbolic
  links, and Windows junctions. A ZIP file in the list is chosen with one
  press, and a folder with "Use this folder".
- The scripts are fixed strings that never contain user input or paths; the
  request names only the kind, `zip` or `folder`. The returned path is
  validated as an absolute path on one line. A dialog opens only for an API
  request with the launch key, and only one dialog is open at a time: another
  request is refused at once (`CHOOSER_BUSY`).
- The request returns when the dialog opens, and the page asks for its answer
  every half second, so that no request waits for the user; browsers end a
  request that waits for minutes. A dialog that is not answered within 10
  minutes counts as no selection, and its program is stopped
  (`CHOOSER_TIMEOUT`). A dialog that is still open when the server stops is
  closed.
- For an extracted folder, the user confirms that the Export was extracted
  completely, with a check box that is empty again at every check. The page
  tells a folder from a ZIP file by the answer of the check, not by the name.
  Only the page asks for this confirmation, as help for the user: the server
  does not, and neither does `run-all` of the CLI. The CLI's confirmation is
  `snapshot register --confirm-complete`, for a Snapshot.
- The first box gives the answer of the check red first, then yellow, then
  green (stage B3b): the findings that stop a run, the notes that do not,
  such as the files that cannot be read with their number, and what the
  check found: for a ZIP file that it is not damaged, with the files to
  read, for a folder that it can be normalized, and the numbers of
  Activities and FIT files. Each line has a mark and a bar of its color.
  The page does not count the families before a run: whether the FIT files
  hold HRV readings is known only when the run reads them, and the result
  table says which families the run found. Without the timezone data, the
  check counts no Activities: the third box shows the missing data, and the
  first box waits.
- When the input holds different Exports, the first box names each one by
  its place inside the input, counting those with the same files once, and
  offers a button to choose each one that is in the selected folder; the
  page checks the chosen one at once (stage B3c). The two buttons at the top
  of the box choose anything else, so the box has no other button for that.
  The first folder or file that cannot be opened is named as after a run.
  A name with a control character, a line break, or a character that turns
  the direction of the text shows as a name that cannot be shown, without a
  button, in the check and after a run alike.
- A stop of a run in the first box hides the lines of the check before it,
  which would read as the answer to it. After the page is loaded again, the
  first box shows no summary until its field holds a place; the settings never
  remember the Export (stage B4c).

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
that the CLI applies them too. The proposed name is
`garmin-run-all-YYYYMMDD-HHMM` in local time; a second run in the same minute
adds `-2`, `-3`, and so on. From stage B5a, the page asks the server about
the name before the run, with the checks that the start of a run makes: the
name's rule first, so that nothing outside the folder is told of, and then
whether something of that name is there. The page's own proposal moves on to
a free name with `-2`, `-3`, as the name of a Snapshot does (decision
20261018-10), so that a launch again within the same minute is not stopped;
a name that the person gave and that is there already makes the third box
red with the words of `OUTPUT_EXISTS` before the run. The start of the run
checks again.

The parent defaults to the folder `GarminRunningData` in the home folder
(stage B4a; until then, the folder that contains the Export), which also
holds the default Snapshot Store, so that personal data stays out of
Documents and the Desktop, which iCloud Drive or OneDrive may copy to the
cloud, and out of Downloads, where Exports and outputs would mix. Only the
GUI has a default place; the CLI takes every place as an argument. When the
folder is not there, the third box says that it is made when the user
normalizes: when a run starts, once its request is valid and no run is
active, the server makes that folder alone, owner-only, with one `mkdir`,
when the requested parent is the default place as the server names it, not
as the page says, and nothing is there. A folder, a link, or a file there,
or a missing home folder, is left to the checks above, and any other parent
that is not there is refused (`OUTPUT_PARENT_NOT_FOUND`), as before. A
parent that cannot be made has the codes of a parent that cannot be written.
The folder stays when the run then stops before its output, empty, and the
next run uses it. On a later launch, the field holds the folder that the
settings remembered (stage B4c).
"Choose…" opens the system's dialog for a folder, as the first box does, or
the page's own folder list without one (stage B4a).

## After a run

- The output is checked as `validate-handoff` and `doctor --run-output` check
  it. The page shows the counts from the output (datasets and links between
  datasets), what the Doctor says about using the output, and the next
  action. The warnings of the run follow, also while the check runs or after
  it stopped: their total, made of the warnings of the families and those of
  no family, and then each warning with the family that it concerns, or its
  group of no family (the Lactate Threshold candidates, the links between
  datasets, or the export), what it means with its count, and its code (stage
  B2c). The result table ends with the row of the warnings of no family and
  the total of the warnings. A folder that changed after the run is reported
  by code.
- The check and the Support Bundle of "If something is wrong" are for the
  output that the person chooses there (stage B5b): the output of this run,
  once it is made, or an earlier output, from the outputs that the settings
  remember that are there as plain folders, newest first, or from another
  folder chosen with the system's dialog ("Choose another output…"). The
  server keeps the list and gives each output a number in it, with a mark of
  the list; the page sends the number and the mark, or the place that the
  dialog gave, and a mark that is not the last one is refused
  (`OUTPUT_LIST_CHANGED`), so that a list given to another tab never makes a
  number name another output. An output that is not found is not listed,
  and stays remembered. An output of 1.3 is checked as v1.4 through v1.7.1
  checked it, and the page says that it has none of the diagnostics of this
  version and that the result that it recorded is the one to use; an output
  of another version is told by its code and its version
  (`OUTPUT_OTHER_VERSION`, see
  [v2.0.0 Data Handling](v2_data_handling.md#checks-of-earlier-outputs)).
- Before a run on a later launch, the result table shows the counts of the
  output before: the newest earlier output whose summary can be read. After
  a run, it has a column of the change of the records of each family since
  that output, and the fourth box says the change of the activities, but
  only when both were normalized the same way (Snapshots, or this Export
  alone), by the same version, and with the same timezone, as the Human
  maintainer decided on 2026-10-18; otherwise a line says which of them
  differ. A line says that it is the change when both were normalized from
  the same Snapshot Store, which an output does not record. The CLI shows no
  change: it remembers no output to compare with, and each output's
  `run_summary.json` holds its counts.
- The Support Bundle is written by default next to the output as
  `<output name>-support-bundle.zip`, because inside the output it would
  contradict the manifest; the user can choose another folder with
  "Choose…" (stage B5a). Before it is made, the page shows the file and its
  place; its place follows the CLI's rules (see
  [v2.0.0 Data Handling](v2_data_handling.md#stops-and-next-steps)): a
  folder that is there, outside the output, and nothing to replace. The page
  explains the six members, that nothing is uploaded, and that the bundle
  needs review before it is shared.
- The page can show the output folder or open its `START_HERE.md` with the
  default application, and show the Support Bundle that this launch made, or
  the External-safe Pack of the output, in its folder ("Show where it is
  saved", stage B5a); the third box names the pack that the run made, apart
  from the file of the next run. The server checks that none was replaced by
  a link or a junction and passes an absolute path without a shell: `open -R`
  for the folder and the files that it shows and `open` for `START_HERE.md`
  on macOS; `os.startfile` with the `explore` and `open` verbs, and
  `explorer.exe` with `/select,"<file>"` for the files that it shows, on
  Windows, as one command line with the place alone in quotes, which is how
  File Explorer reads it (a list of arguments would quote the whole
  `/select` of a place with a space); and `xdg-open` elsewhere, with the
  folder that holds a file that it shows. The page sends no place to open.

## The view page (v2.1.0)

Version 2.1.0 adds a page that shows the numbers of an output that this
version made, as panels on one time axis (stages G1 to G3b-2, decisions
20261026-9 to 20261026-11). It reads outputs only, sends nothing, and does
not interpret the numbers: it does not say what a value means, which item
causes another, or what to do. The `series` command of the CLI writes the
same numbers to a CSV file, with the same functions (stage G2).

Place and tabs:

- The view page is `/view`, in the tab next to the normalization page. The
  two pages are named tabs (`garmin-running-normalize` and
  `garmin-running-view`) and find each other with `window.open("", name)`, so
  that a page that is open comes to the front instead of a new tab; a tab
  that opens empty is given the address of the launch, with the key in the
  fragment.
- The normalization page opens the view page from "View this output" in its
  fourth box, with the output of its run, and from "Open the view page" in its
  bar; the view page goes back with "Go to the normalization page".
- Quitting one page tells the other through a `BroadcastChannel` that carries
  `{stopped: true}` only, and the other page says that the app has stopped,
  not that the connection was lost.

Which outputs:

- Only outputs that this version made, since how normalization makes the
  numbers can change between versions. An output of another version stops
  with `OUTPUT_OTHER_VERSION`, and one of 1.3, which the checks pass, with
  `SERIES_OUTPUT_OTHER_VERSION`; the red box offers to normalize again on the
  normalization page.
- The page opens the latest output, this launch's or the newest earlier one,
  with the items shown last time, and at first with Distance, Resting heart
  rate, and VO2 Max. Another output comes from the list of earlier outputs of
  [After a run](#after-a-run), with its mark, or from the system's dialog.
  The list keeps its mark while it holds the same outputs, so that the
  numbers given to another tab still name the same outputs (a fix of 2.0.x in
  stage G3b-1); until the list first holds an output, its mark is 0.
- An output is named by its name and the version that made it. No date of
  normalization is shown: an output holds none, so that the same input gives
  the same bytes, and the times of a folder change when it is copied.

Reading an output:

- The server checks the output with the checks of the GUI, and reads only the
  dates and the values of the items, of ten files at most, each compared by
  size and SHA-256 with the manifest that it read before the checks. A file
  or a manifest that changed stops the reading with `OUTPUT_CHANGED`. A file
  over 128 MiB, files over 512 MiB together, or a manifest over 256 MiB are
  not read, and stop it with `OUTPUT_NOT_AVAILABLE`.
- Rows without a date, and rows dated after today in the output's timezone,
  are counted and left out: one date far ahead, from a wrong clock, would
  stretch the time axis and leave the last years empty.
- The server keeps what it read in memory, under a ticket of random
  characters that holds no place, for four outputs at most; the one used
  longest ago leaves first. Every request for numbers looks at the output
  again by the size, the time of change, and the inode of its folder and of
  the files that the page reads, and by the date of today; when one of them
  changed, the output is checked and read again. The contents (their
  SHA-256) are checked when an output is opened and when it is read again,
  not at every request, so a file rewritten with the same size and an
  earlier time of change is not noticed; this is accepted for the person's
  own output on the same computer.
- An answer of numbers is at most 4 MiB (`VIEW_ANSWER_TOO_LARGE`; six panels
  by day over 15 years take about 2 MiB). A ticket that the server no longer
  keeps is `VIEW_NOT_OPEN`, and the page opens the output again once. Reading
  an output writes nothing, not even a temporary file; the settings keep the
  items and the shelf, and from v2.2.0 the view and the layouts, as the person
  changes them.

Items and numbers:

- 38 items in four groups (Training (per activity), Running form (FIT), Body
  (daily), and Garmin estimates), with the months that have data. Up to six
  panels are shown.
- The activity types counted are those of running at first, the names that
  the link between an activity and a FIT session counts as running, and can
  be chosen again; they apply to every panel.
- The period is all the time, the last 10, 5, 3, or 1 years, a range, or the
  same length before or after. The grouping is Auto, day, week, month, or
  year; Auto groups by month for a period longer than three years, by week
  for one longer than a year, and by day otherwise. The first and the last
  period, cut by the period, are marked as partial.
- A total (distance, time, count) is that of the recorded activities: a
  period without one is 0 between the first and the last activity of the
  types counted, and empty before and after them. 0 means no record, not
  that there was no run, and it is drawn as a light point. The pace is the
  total time divided by the total distance of the activities with both; a
  mean of activities is weighted by their durations; a daily item is the
  mean of the days with a value, and a sleep counts only on the days that it
  may be used.
- An item with several records a day, such as VO2 Max, shows every record at
  the grain of a day, and otherwise the mean of all the records, so that a
  day with more records weighs more; the second line of its panel counts the
  days with more than one record. The two series of VO2 Max (the activity
  record and MaxMet) stay in separate lines, told apart by color by the name
  of the series and never by their order, and the sports by a dashed line or
  hollow points.
- Values that are missing are never filled, carried, or made 0, and what is
  left out is counted in the notes of the panel. The numbers are rounded only
  when they are shown.

The page (the Human maintainer's mockup v2, and the check in Safari on
2026-10-27):

- The bar of the app is one row, with the line of what to do next in it. The
  filters (the output, the period, the grouping, and the activity types)
  apply to every panel and stay in one row from a width of 1366 in Japanese,
  so that the panels keep the height.
- The item shelf at the left lists the items with bars of the months that
  have data, finds them by name, and folds to a rail.
- Panels of at least 150 pixels stand on one time axis; when they do not fit,
  only the panels scroll. A panel names its item, unit, and kind, gives the
  period and the values at the cross line, a second line of counts and the
  lowest, highest, and latest values, and notes of what is left out, and can
  be shown as a table (newest first, 400 rows at a time), enlarged, moved, or
  removed; one panel enlarged makes the others low strips on the same axis.
  Panels of the same unit can share one scale on request. Acute and chronic
  training load are both Garmin's values as they are, but two columns of the
  same source, so they share it.
- The overview under the panels shows the whole output by month, of the first
  panel or of the one enlarged, and frames the period shown. A drag chooses a
  period: the frame follows it, with its days in the label, and a drag
  shorter than a week changes nothing. Within 8 pixels of an edge of the
  frame, the pointer is a double arrow, and a drag moves that edge as far as
  the pointer moves, never under a week. Escape cancels a drag.
- Full screen shows the panels and the overview alone, under one line that
  names the output, the period, and the activity types, filling the screen
  where the browser allows it and the window where it does not. Escape,
  Back, or the browser's own end of its full screen goes back, with the focus
  on the button that went there; in the browser's full screen, the browser
  takes the first Escape, which also ends a drag. A stop shows the whole page
  again, with the focus on its heading. Full screen is not remembered.
- Each chart is an image named by its item and its period, which the
  keyboard can reach. The arrow keys move the cross line by one period,
  PageUp and PageDown by twelve, and Home and End to the ends, and a hidden
  live region says the period and the value of each line, with the line
  named; the mouse moves the line without making it speak.
- The charts use two colors, violet (`#6250d6`, and `#9085e9` in dark) and
  orange (`#eb6834`, and `#d95926` in dark), which pass the checks for color
  vision deficiencies on the surface of the panels (`#ffffff`, and `#1c1f24`
  in dark). The charts are always drawn on that surface, since the orange on
  the page's background (`#e8ebf0`) has a contrast of 2.68. Four colors for
  the four lines of VO2 Max did not pass, so the color tells the series and
  the dash the sport. Where the system forces its own colors, the marks take
  the colors of the text, of links, and of gray text, and stay apart.
- The settings remember the items shown and whether the shelf is open
  (`view_items` and `view_shelf`), by the names of the items only; names that
  this version does not know, names given twice, and those after the sixth
  are left out. From v2.2.0 (stage K2) they also remember the period, the
  grouping, the activity types counted, and the layout used last. Nothing is
  remembered for each output: the same values apply to every output. The
  page writes them 0.8 seconds after the last change (a change within that
  time waits again), at once before it quits the app, and, when the page
  hides, in a request that outlives it (`keepalive`). Before the
  normalization page quits the app, it asks the view page on the quit channel
  to write what waits (`{ flush: true }`) and waits for its answer
  (`{ flushed: true }`) for 0.5 seconds at most; a value not written by then
  is given up, and the settings keep what they had. Once the app stopped,
  nothing more is written. After the other tab forgot the settings, only a
  change of the person writes them again.
- When an output opens (stage K2), a period such as the last year stays as it
  is. A range goes to the server as it is, which limits it to the days of the
  output as before; a range that does not overlap them at all opens all the
  time. The activity types counted are those remembered that the output has,
  and its running types, as at first, when it has none of them.
- The layouts (stage K2) are cards above the item shelf, in two columns: the
  built-in layouts not hidden, in their order, then those of the person, in
  theirs. A card shows its name (a name of the person as text), "(changed)"
  once the panels are other items or in another order, and "Items with values
  n/m" when the output has no value at all for some of its items (counted
  over the whole output, not the period). Choosing a card shows its items, in
  its order, and remembers it as the one used last. "Save the panels as a
  layout…" names a new layout, which becomes the one used last; "Overwrite the
  layout" puts the panels into a changed layout of the person; "Manage
  layouts…" opens a small window that renames, moves, overwrites, and removes
  the person's layouts (a removal asks first, with "Keep it" as the default
  button), and hides or shows the built-in ones. A layout moves by Up and
  Down, by the arrow keys on its grip, or by a drag of the grip, which sends
  one change with the place of the layout (`to`). A change that the server
  refuses says why in one line where it was asked, and a layout that another
  tab removed reads the layouts again. On the folded shelf, "Layouts" opens
  the cards in a small window.

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

- `gui` starts the GUI (stage D1): it prints the address with the launch key,
  opens it in the default browser unless `--no-browser` is given, and ends
  with exit 0 after the Quit button or after `Ctrl+C` without a run, or, when
  `Ctrl+C` stopped a run, with the CLI's lines and exit code for a cancelled
  command, 130.
- `gui --create-shortcut` (stage E1d, decision 20261021-1) first makes an icon
  that starts the GUI with the Python that runs the command: a file on the
  desktop that the Terminal runs on macOS, and a shortcut on the desktop and
  in the Start menu whose console opens minimized on Windows. The icon keeps
  the terminal's window, so that a run, its cancellation, and the stop work as
  from the command; an icon without a window, which needs another way to
  cancel the child of a run on Windows, waits until after 2.0.0. The command
  replaces only an icon that it made, and when it cannot make one it stops
  with exit 2 (`SHORTCUT_NOT_SUPPORTED`, `SHORTCUT_PLACE_TAKEN`, or
  `SHORTCUT_NOT_CREATED`) before the GUI opens. Linux has no icon.
  The icon shows the picture of this app (stage E1i, the Human maintainer's
  choice of 2026-10-22): on macOS, `osascript` gives the file the picture of
  `assets/icon.icns` and hides its extension; on Windows, the shortcut points
  to `assets/icon.ico`. When the picture cannot be given, the command says so
  in one line, not as a stop, and the icon still starts the GUI. The page
  shows the same picture in the tab of the browser (`favicon.svg`, and
  `favicon.png` for a browser without SVG there).
  `scripts/generate_app_icons.py` makes the pictures on macOS from the SVG
  files of `assets/`, which draw the letters with lines and arcs instead of a
  typeface.
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
- `series` (v2.1.0, stage G2) writes the numbers of the view page of an output
  to a new CSV file, with the same functions as the page and the rules of a
  new file beside an output that the Support Bundle follows; its stops are in
  [Stops and next steps](v2_data_handling.md#stops-and-next-steps).

Stage A5a applies the rules for the output's name and its existing parent
folder to `run-all`, `normalize-activities`, `snapshot build-input`, and
`snapshot run-all`, prints the warning totals in the CLI, passes them to the
GUI's run status, and makes the pre-run check read the Activities files as a
run does (see [v2.0.0 Data Handling](v2_data_handling.md#reports-of-a-run-in-the-cli-and-the-gui)).
Stage B sets the rules for the place of a new Snapshot Store and of a Support
Bundle with the controls that choose them (stage B5a for the Support Bundle),
and the page shows the warning totals. Stage B4a sets those of a new store:
`snapshot init` and the page make a new store only where the folder that
holds it exists
(`SNAPSHOT_STORE_PARENT_NOT_FOUND`; until then, `snapshot init` made the
missing folders above it), in a new or empty folder (`SNAPSHOT_STORE_NOT_EMPTY`
for a file or a folder that holds other files; `SNAPSHOT_STORE_INVALID` for
one that holds what a store writes but not `store.json`), and not inside
another store (`SNAPSHOT_STORE_INSIDE_STORE`), and every snapshot command
refuses a store that is a symbolic link with `SNAPSHOT_STORE_SYMLINK`
(until then, `SNAPSHOT_LIFECYCLE_FAILED`).

Stage B also changed the CLI where the page needed it, with the same
functions in both (see [v2.0.0 Data Handling](v2_data_handling.md) and the
[Migration Notes](migration_notes.md#v171-to-v200)). The `ERROR` lines of
`INPUT_NOT_READABLE` and `SNAPSHOT_STORE_NOT_READABLE` say that this app is
not allowed to open a folder or file, and the report of `doctor` for a
person gives the next step of a finding whose code is a stop (stage B2b).
`doctor --input` gives the counts of the input (stage B3b), and its report
for a person names the Exports of a mixed input and the first place that
cannot be opened (stage B3c). The four stops of `snapshot register` that the
page checks before a run have codes of their own, `SNAPSHOT_LABEL_INVALID`,
`SNAPSHOT_LABEL_EXISTS`, `SNAPSHOT_TIME_INVALID`, and
`SNAPSHOT_INPUT_INSIDE_STORE` (stage B4b-1). `snapshot unlock
--confirm-no-other-command` removes the lock file that a stopped
registration left, and the three cases of `INPUT_MULTIPLE_EXPORTS` have next
steps of their own (stage B4b-2). `support-bundle` stops for a folder that
cannot be written with `SUPPORT_BUNDLE_NOT_WRITTEN` (stage B5a), and
`validate-handoff`, `doctor --run-output`, and `support-bundle` tell an
output of another version with `OUTPUT_OTHER_VERSION` and the version that
made it (stage B5b).

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
- The requests of the view page (v2.1.0) are API requests as the others, with
  the same key and the same checks; both pages take the key and the calls of
  the API from `launch.mjs`. An answer of numbers is at most 4 MiB.

Response headers:

- `Content-Security-Policy` is sent as an HTTP header: same-origin scripts,
  styles, connections, and images only, no inline script or style, no external
  resources, and `frame-ancestors 'none'`, `base-uri 'none'`, and
  `form-action 'none'`. The view page (v2.1.0) has the same policy.
- `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
  `X-Content-Type-Options: nosniff`, and `Cache-Control: no-store`.

Processing:

- Child processes and file dialogs are started from argument lists without a
  shell, with fixed scripts.
- ZIP files are read with the limits and checks in
  [Selecting an Export](#selecting-an-export).
- Output folders go through the same checks as the CLI.
- The page can open only an output folder and its `START_HERE.md`, and show
  the Support Bundle that this launch made or the External-safe Pack of the
  output in its folder (stage B5a); any other place is refused.
- The links of the page (stage B5c) have no address in the page itself: the
  script gives each one from fixed strings, under
  `https://github.com/tsubotti63/garmin-running-data-normalizer/` or the data
  management page of Garmin, and each opens in a new tab with
  `rel="noopener noreferrer"`, only when it is pressed. The
  Content-Security-Policy is unchanged; following a link is not a request of
  the page.
- The settings of an earlier launch (stage B4c) are read without following a
  link, up to 64 KiB, and only in their form; the places in them are absolute
  places without control characters, and the server checks them again as it
  checks the places that the page sends. They are written whole through a
  temporary file in an owner-only folder and file. Only the tests' own place
  is used by the tests.
- The messages between the tabs of a launch (`BroadcastChannel`, v2.1.0)
  carry the colors, the notice that the settings were forgotten, and the
  notice that the app stopped; never the key. The view page reads outputs
  through the server only, and opens nothing outside the page.

## Privacy

- No outbound network access and no external resources. No analytics or
  telemetry. Copying an example question of the help panel uses the clipboard
  of this computer only. A link opens a page outside only when the person
  presses it (stage B5c), and the address of the GitHub report carries only
  the values that the help panel shows first, which reach GitHub when the
  form opens.
- The values of this computer in the report are read from fixed sources
  only: the version of macOS, the version of Windows, the name and version
  in os-release on Linux (up to 64 KiB), and the version of Python, each
  only in a plain form (letters and digits of ASCII, spaces, `.`, `_`, and
  `-`, up to 40 characters), and otherwise the name of the system alone;
  never the name of the machine or of the person, or a place.
- Local paths are shown only to the local user. The server does not log
  requests, paths, or secrets, and errors are returned as codes.
- The page explains that Run-All output and the Snapshot Store contain personal
  data, that the External-safe Pack is opt-in and still needs human review
  before it is shared, and what the Support Bundle contains.
- Snapshot labels given by users stay out of the Support Bundle and the
  External-safe Pack.
- The settings of an earlier launch hold the names of places only (stage
  B4c), stay on this computer, and are never part of the Support Bundle;
  "Forget the remembered settings…" removes them, as on a shared computer.
  From v2.1.0 they also hold the colors of the page, and the names of the
  items that the view page showed and whether its shelf was open. From v2.2.0
  they also hold the timezone of the last run that made its output, the
  layouts that the person named, and the period, the grouping, and the
  activity types of the view page.
- The view page (v2.1.0) writes nothing in an output. The server keeps what
  it read in memory only, under a ticket that holds no place.
- A Snapshot Store or a folder for the output in a folder that a cloud may
  copy is marked in yellow, without a stop (stage B4a): a folder that a cloud
  app keeps (on a Mac, iCloud Drive in `Library/Mobile Documents` and the
  apps in `Library/CloudStorage`; on Windows, the OneDrive folders that the
  system names and `iCloudDrive`; and a folder named Dropbox, OneDrive,
  Google Drive, or iCloud Drive anywhere), and the Documents and Desktop of a
  Mac, with the condition that iCloud copies them when its setting for them
  is on. Only these fixed names are compared, as the place is given and as
  its links lead; no program is asked, so the page says "may be".

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
  code to quote in a support request. Each code has words of its own (stage
  B2a). The English words come from the tables of `stops.py`: the CLI's
  table of stops, the table of the codes that only the GUI gives (below), and
  the page's wording for the codes whose words in the CLI's table name a
  command, Run-All, registering, a file to give, or what the page cannot do
  yet. The Japanese words come from the text book of stage B0. Tests check the
  catalogs against the tables, and the stops that the GUI guides quote against
  the catalogs.
- A finding of the check of the Export says what a run would stop with in the
  words of the stop of its code, and gives the next step of that stop, as the
  CLI's `doctor --input` does in its report for a person (stage B2b). A
  finding whose code is not a stop, or that does not stop a run, has words of
  its own, and the page shows nothing for the finding that the Export is
  ready, since it says so itself. The check of the output gives what the
  Doctor says about using the output, and the next step in the words of the
  CLI's Doctor; tests check the English against the CLI's table of next steps.
- The Japanese catalog uses these terms: 正規化, 取り込む, 既存のスナップショット,
  正規化のしかた, 問い合わせ用ファイル (the English term Support Bundle appears
  only inside its explanation), 目印のファイル (`.single-writer.lock`), 出力の確認
  and 確認済み, このアプリ, and バージョン. It does not use 貯めた, 道具, or 版.
- Tests check that every catalog has the same keys and placeholders and that no
  key is unused.
- CLI output and the generated Run-All documents stay in English.
- The GUI guide is written in English and Japanese:
  [GUI Guide](gui_guide.md) and [GUI の手引き](gui_guide.ja.md).

### Codes that only the GUI gives

The GUI's server, its folder list, and the actions on a finished output give
these codes; the CLI never stops with them. The table is made from
`stops.PAGE_STOPS`.

Starting with v2.1.0, `OUTPUT_CHANGED` and `OUTPUT_NOT_AVAILABLE` are also
codes of the CLI, whose series command reads an output as the view page
reads it; they are in the table of the stops of the CLI
([Data handling of v2](v2_data_handling.md)), and the page keeps its words
for them.

Starting with v2.1.0, the view page also gives `VIEW_NOT_OPEN`, for an
output that the server no longer keeps, and `VIEW_ANSWER_TOO_LARGE`, for
numbers over the limit of the size of an answer.

| Code | What it means | Next step |
|---|---|---|
| `PATH_NOT_ABSOLUTE` | the place is not a full path | choose it with a button that says Choose, or paste a place that starts with / on a Mac or Linux, or with a drive such as C:\\ on Windows |
| `PATH_INVALID` | the entries could not be read | check the entries and press the button again |
| `INPUT_PATH_INVALID` | the entries could not be read | check the entries and press the button again |
| `OUTPUT_PARENT_INVALID` | the entries could not be read | check the entries and press the button again |
| `REQUEST_INVALID` | the entries could not be read | check the entries and press the button again |
| `FOLDER_NOT_FOUND` | the folder does not exist | check the place, or choose the folder with Choose… |
| `NOT_A_FOLDER` | this is a file, not a folder | choose a folder |
| `FOLDER_NOT_READABLE` | this app is not allowed to open this folder | on a Mac, allow it when you are asked, or in System Settings > Privacy & Security |
| `RUN_ACTIVE` | a normalization is running in another tab or window | wait for it to finish, or cancel it |
| `RUN_START_FAILED` | the normalization could not be started | press Run normalization again; if it stops again, please report the code |
| `NO_FINISHED_OUTPUT` | there is no finished output to check yet | normalize first, or choose an earlier output |
| `OUTPUT_LIST_CHANGED` | the list of earlier outputs changed since the page showed it | choose the output again from the list |
| `VIEW_NOT_OPEN` | the output that the page shows is no longer open in this app | choose the output again |
| `VIEW_ANSWER_TOO_LARGE` | there are too many numbers to show at once | choose a shorter period, or group by week or month |
| `OPEN_NOT_AVAILABLE` | no program to open it (xdg-open) was found | open the output folder from your file manager, such as Finder or File Explorer |
| `OPEN_FAILED` | this computer could not open it | open the output folder from your file manager, such as Finder or File Explorer |
| `CHOOSER_NOT_AVAILABLE` | this system's dialog to choose could not be opened | choose from the list below, or paste the place |
| `CHOOSER_TIMEOUT` | the dialog to choose was not answered in time | press Choose ZIP file… or Choose extracted folder… again |
| `CHOOSER_BUSY` | another dialog to choose is open | choose in it or close it, and press the button again |

## Accessibility

The GUI supports keyboard operation, accessible names for controls, WCAG 2.1
AA contrast in the light and dark themes, no information conveyed by color
alone, and reduced motion.

- Progress counts change every second, so they stay out of live regions. A
  hidden live region speaks when the stage changes, when a run stalls or is
  being cancelled, and when it ends. Live regions change only when their text
  changes, so that screen readers do not repeat them. The stage is spoken
  only after a run has gone on for two seconds, so that a run that ends at
  once speaks only its end; a message given to a live region is spoken even
  after a later one (stage C1).
- The result heading is named with hidden words before its visible ones,
  such as "Normalization result: Waiting", because a screen reader may list
  headings alone (stage C1).
- One button at most is filled with the accent color, the next step: after a
  run that made its output, until a box changes, the button that shows the
  output; otherwise Use these settings in the second or third box while it
  is the current one, and then Normalize. A button that cannot be pressed is
  not filled (stage C1).
- When a run ends, focus moves to the result heading; when it stops, to the
  heading of the stop in the box that it concerns (stage B1a). When a box is
  confirmed, focus moves to the next box. When a button that had focus stays
  disabled after its action, focus moves to the nearest heading.
- Losing the server is shown as an alert at the top of the page.
- The help panel is a complementary landmark, not a dialog, because it does
  not cover the page. Opening it, or one of its parts, moves focus to the
  heading of that part; Escape inside it closes it (stage B1b).
- An information button is a disclosure. Its name starts with its visible
  word and adds what it explains, such as "About Timezone for local dates and
  times". When it opens, a hidden live region says the text of its
  explanation once, and focus stays on the button (stage C1).
- The view page (v2.1.0) names each chart and moves its cross line with the
  keys, and a hidden live region speaks only when the keys move the line (see
  [The view page](#the-view-page-v210)). Its buttons that show only an icon
  have names, and Escape closes what the page opened.
- Tests check labels, button names, heading order, live regions, focus
  targets, and the contrast of the stylesheet's colors. Keyboard-only use and
  a screen reader (VoiceOver on macOS) are checked by hand in stage C; a
  scripted browser test is not part of CI in 2.0.0.

## Repository constraints

- `scripts/static_policy_scan.py` reads every file under `src/`, including
  HTML, JavaScript, CSS, and message catalogs. GUI files must not contain the
  terms that the scan bans in production code, host-path-shaped examples (use
  `/path/to/...` instead), literal secret assignments, or email addresses.
- `pyproject.toml` ships the static files and the pictures of the icon as
  package data, and the CI wheel and source-distribution installation checks
  verify that the GUI files are installed.

## Compatibility and versioning

- v2.0.0 changes the output and exit contracts as described in
  [Data handling in 2.0.0](#data-handling-in-200). The
  [migration notes for v1.7.1 to v2.0.0](migration_notes.md#v171-to-v200)
  list every change.
- `validate-handoff`, `doctor --run-output`, and `support-bundle` accept
  Product major version 1 and later, as released in v1.7.1. Outputs that
  contain `diagnostics/` are accepted only when they were produced by the
  installed version, including pre-release versions such as `2.0.0rc1`.
- `run_all_version` becomes 2 if the output layout changes; stage A decides.
- Existing Snapshot Stores are read without migration, or with an automatic
  migration that keeps the original data intact.
- v2.1.0 keeps the settings file in format 1, with three more keys (`theme`,
  `view_items`, and `view_shelf`). 2.0.x reads the file and leaves the keys
  out, and drops them when it writes the file again, so that going back to
  2.0.x and then to 2.1.0 forgets the colors and the items and the shelf of
  the view page.
- v2.2.0 writes the settings file in format 2, with the timezone and the keys
  of the layouts and the view (above). 2.1.0 and 2.0.x do not use a file of
  format 2 and never write over it: going back starts as a first launch, and
  their "Forget the remembered settings…" removes the file with the layouts.
  2.2.0 reads format 1 and writes it again as format 2 with its keys.
- The view page reads outputs of the installed version only; the checks of
  earlier outputs stay as above.

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
- Manual checks in stage C cover macOS (Chrome and Safari), with the keyboard
  and VoiceOver. No person who had not seen the GUI before checked a release
  candidate before the stable release, because none could be found. Instead,
  as the Human maintainer decided on 2026-10-20, new AI sessions that had
  never seen the GUI finished a normalization of the synthetic Export with no
  instructions: two with v2.0.0rc1, whose findings stage D6 made clearer in
  the texts of v2.0.0rc2, and one with v2.0.0rc2, which read the clearer
  texts without hesitating there; the five things that it found new are left
  for after the stable release. An AI session does not hesitate as a person
  does, so this check finds unclear words and next steps, and is weaker than
  a check by a person. A person checks the GUI after the stable release if
  one can be found. v2.0.0rc1 was checked on a physical Windows machine (x64,
  Edge and Chrome, with the keyboard) with synthetic data; from v2.0.0rc1,
  v2.0.0rc2 changed only the page texts and the version, so Windows was not
  checked by hand again. A Windows 11 on Arm64 virtual machine was planned as
  well; the Human maintainer decided on 2026-10-20 to leave it out once the
  physical machine covered its checks. Windows on Arm64 is not checked by
  hand. Linux is covered by CI only.
- The maintainer compares GUI and CLI output on a real Export by counts and
  identity only, as for earlier releases.
- v2.1.0 (stages G1 to G3b-2): node tests of the view page's rules and charts
  (`launch`, `view_flow`, and `view_chart`); pytest of the numbers
  (`test_view_data`), the `series` command (`test_series`), the view page's
  server and page (`test_gui_view_api`, `test_gui_view_page`, and
  `test_gui_accessibility`); a script read the settings with the tags of
  2.0.x, each in a process of its own (stage G3a). The tests of the
  numbers, of the CSV file, and of the view page's server also run as the
  last steps of the two Windows jobs, for the files on Windows. Each stage
  broke one thing at a time in a copy to see the tests fail. The view page
  was checked with Chrome without a window, driven by a script, at widths
  from 1366 to 3008 pixels, light and dark, in English and Japanese, and with
  forced colors, and by the Human maintainer in Safari and Chrome on macOS;
  VoiceOver was not used. The maintainer compared the numbers of real
  outputs by counts only.

## Release plan

| Stage | Content |
|---|---|
| 0–4a (done) | The first GUI, for the one-shot Run-All (pull requests #62 to #72); its code is included, without a command, in v1.7.1 |
| 0 (revision) | This revision of the design and the related documents (documentation only) |
| A | The data-handling and CLI changes, in several pull requests, each planned and reviewed |
| A checkpoint | CLI-only verification with synthetic golden outputs and a draft of the migration notes |
| B | The single-page GUI, in several pull requests, each checked for screen texts and points of hesitation |
| C | Verification on macOS and browsers, with the keyboard and VoiceOver, and the maintainer real-data check |
| D | Release candidates on TestPyPI with the `gui` command exposed, before the stable release: v2.0.0rc1, checked on a physical Windows machine (x64) with synthetic data and by two new AI sessions in place of a first-time user; and v2.0.0rc2, with the texts that they found unclear made clearer, checked on macOS with synthetic and real data and by a new AI session |
| E | Stable 2.0.0 release: the documents of v2.0.0; the icon and the line that installs this app (v2.0.0rc3); the pictures of the icon and of the tab of the browser, and the guides that answer what a first reader asked (v2.0.0rc4, also checked on a physical Windows machine); the answers of the guides, Python 3.15 in the CI, and the limit of the nesting of JSON (v2.0.0rc5); and the version 2.0.0 |
| G0–G4 (v2.1.0) | The view page: its design and texts (G0), its numbers (G1, #165), the `series` command (G2, #166), the colors of the page (G3a, #167), its server (G3b-1, #168) and its page (G3b-2, #169), and this design (G4) |
| G5–G7 (v2.1.0) | An hour before the server stops by itself, after a check in Safari (G5p); a release candidate on TestPyPI, checked on macOS and a physical Windows machine and read by a new AI session; then the documents that users read, the version 2.1.0, its publication, and its record |

Installing a release candidate from TestPyPI used Production PyPI as an
extra index for dependencies, such as `tzdata` on Windows, that TestPyPI may
not provide. The stable release is installed from Production PyPI.

Each stage is reviewed before it is merged, and dates are not fixed.
