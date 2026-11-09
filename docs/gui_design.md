# v2.0.0 GUI Design

- Status: design revised on 2026-10-11; implemented in v2.0.0, whose `gui`
  command opens the GUI. The view page and the colors of the page are added
  in v2.1.0; the sections marked v2.1.0 describe them. What v2.2.0 adds to
  the view page, and the timezone that the settings remember, are described
  where the text says v2.2.0, and what v2.2.1 fixes where it says v2.2.1.
- Applies to: stable v2.2.1
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
| Scope of 2.2.0 | What the view page adds: layouts of items; comparing years in rows, overlaid, as running totals, as a calendar, and as a table, also by race day; marks and the list of activities; the other views (points, spread, a summary, by shoes); saving a chart as an SVG picture; and conditions on the activities. The view and the timezone of the normalization are remembered. Nothing is sent, and the numbers are not interpreted. |
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
  relating two items (v2.2.0 lays the years over each other, also by race day:
  see [The view page](#the-view-page-v210))
- Views by shoe or of personal records, the bands of the training status, and
  moving averages (v2.2.0 adds the view by shoes: see [The view
  page](#the-view-page-v210))
- Saving a chart as a picture or a file (v2.2.0 saves a chart as an SVG
  picture: see [The view page](#the-view-page-v210))
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
  settings does (v2.0.1, stage F2). From v2.2.1 (stage W2) each question is
  in a row of its own, its box ending where its button ends: CSS alone does
  not know where the button is, so the page measures the room right of the
  button as the question shows, at the end of each drawing, and as the
  window, the bar, or any part of the bar changes size (a part that grows or
  wraps may move the button while the bar keeps its size; such a change is
  measured in the next frame, so that what the measuring changes does not
  come back to the observer of the bar in the same frame); the box is at most
  as wide as the room left of the end of the button, and a room under 20rem
  leaves the box as wide as the bar. Both questions of the normalization
  page can show at once, each in its own row. While the server stops, the
  bar says so
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

From v2.2.1 (stage W4) forgetting also removes the temporary files that a
write leaves where this app stops in the middle of it
(`.<name>.<pid>.<8 hex>.tmp` of the settings and of the marks, in their
folder, each a copy of them): those of the server's own process, whose
writes are under the lock of the settings, of a process that is gone, by its
pid where the system tells it without harm (not on Windows, where `os.kill`
stops a process), and any older than ten minutes. A newer one of another
process that is alive, another launch in the middle of its write, stays, and
so does the folder with it. One that cannot be removed is told as its file
would be, and the button can be pressed while one is there. From v2.3.0
(stage X1) a newer one that stays counts as something to forget too, so that
the button can still be pressed (on Windows, one that a stop left stays until
it is ten minutes old): forgetting tells that it stayed (`TEMPORARY_LEFT`,
where the settings and the marks are gone, so the page drops the colors
remembered in the tab as well), and pressing again once it is ten
minutes old removes it. The status of a launch and forgetting count what
there is to forget alike. A folder that is
a link is never looked into, as the settings are never written into one; a
file is removed only while it is still the one looked at (a newer write or
another file in its place stays); and one that cannot be looked at, or a
folder that cannot be listed, is told as left.

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
numbers), the activity types counted (`view_types`) when the whole choice can
be kept: up to 64 names of up to 128 characters, each once, without a control
or direction character, and from stage L1 how one item is compared by year
(`view_compare_mode`: rows, overlay, or cumulative) and in which month
(`view_compare_month`: 1 to 12, an integer; none for the whole year), and from
stage T1 the conditions on the activities (`view_conditions`, in the form of a
request of the numbers: the words of the name as written, the distance in
whole metres, and the duration in whole minutes, each from and to), kept whole
or not at all. A request of the numbers takes any choice of the types of the
output, as 2.1.0 did; a choice that the settings cannot keep whole is not
remembered, and the one before is forgotten, so that the next opening counts
the types counted at first, never other types than those chosen. A value of
another form of one of these keys is left out alone, and of the layouts, the
one layout. A name of a layout is kept in NFC without the spaces around it,
without a control character, a separator of lines or paragraphs, or a
character that changes the direction of the text; two names are compared in
NFKC and casefold, and a name of the person cannot be that of a built-in
layout in either language or of another of the person's layouts. The layouts
change one at a time under the lock of the server: the page sends one change
(add, rename, overwrite, move, remove, hide, show, or reset), and the server
reads the file, changes it, and writes it, so that two tabs keep both changes.
A layout removed or hidden is no longer the one used last. Settings whose file
would be over 64 KiB are not written (a fix of 2.1.0, which wrote such a file
and then could not read it): the file before stays, and the page is told that
they were not remembered. 2.1.0 and 2.0.x take a file of format 2 as one of a
newer version: they do not use it and never write over it, and start as a
first launch, so that what 2.2.0 remembers is not lost by going back; their
"Forget the remembered settings…" removes it, with the layouts.

From stage U2 of v2.2.0 the settings have a generation: a whole number that
the server keeps from 0 for its launch, never in a file, under the lock of the
settings, and gives in `/api/status`, read at once with the settings and the
marks. Forgetting the settings moves it on by one, also when a file is left,
and its answer tells it; each change that a page asks (of the tips, the
colors, the view, the layouts, and the marks) names the generation of the
moment that the person made it. The server writes a change of the generation
now only. One of another generation, made before the settings were forgotten,
is answered `{"stale": true, "generation": n}` (200, which the page takes for
no error), before a file is read or a layout or a mark that the change names
is looked for, and one without a generation is refused (`REQUEST_INVALID`). So
a change that arrives after a forgetting writes nothing: one of the view sent
after its pause, one waiting for another, one with keepalive as the page
hides, and one of the normalization page around its own forgetting. A run that
ends remembers its places without a generation: the settings are not forgotten
while a run is active, and the server forgets them under the lock of the runs,
so that no run starts meanwhile (that lock is taken before the lock of the
settings, never after it). The two pages follow the generation alike
(`settingsFollower` in `flow.mjs`). A page moves on to a newer generation
once, at the first of what tells it (the message of another tab, a stale
answer, its own forgetting, or `/api/status`), takes the settings as the
server holds them then (the layouts and the marks of the files left, none
where they are gone; it keeps the layout in use where the layouts still offer
it, and whether the marks show), drops the answers of the changes asked
before, and does not send a change of before. As a page comes forward
(`visibilitychange` and `focus`), it reads `/api/status` again, so that a tab
that did not hear the message moves on before the person changes anything
there. A change of the person takes a stamp as it is made: it goes with the
generation that the reading on its way then reads, or else with that of its
moment, and not at all where the page heard of a forgetting by a message
since, as it was made before that forgetting; a reading that gives no answer
in 10 seconds is one that could not read. So "only a change of the person
writes them again" holds in every tab. One way is left: in a tab that did not
hear the message, a change made right after the page came forward can be
written with the generation after a forgetting done in another window while
the reading of the page waits on the server for seconds; by hand, the reading
ends first. The generation holds for one GUI, as the lock does: the page of
another launch cannot ask this server (its key is another), and two GUIs of
two processes are outside it.

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
  which carries the colors, and the generation of the settings after a
  forgetting (from stage U2 of v2.2.0; until then, the notice that they were
  forgotten), only; never the key.
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
  (`/api/settings/theme` and `/api/settings/view`); see [The view
  page](#the-view-page-v210). From v2.2.0 `/api/settings/view` also takes the
  layout used last, the period, the grouping, the activity types, how one item
  is compared by year and in which month, and the conditions on the
  activities, `/api/settings/layouts` changes the layouts one change at a
  time, and `/api/view/open` gives the built-in layouts by their ids and
  items.
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
- From v2.3.0 (stage X7, the Human's choice D of its samples), where the
  change shows, the fourth box also gives the numbers of the records that
  changed since the output before, under the lines of the result: the page
  asks `/api/changes` once for the finished run, with the number of the output
  before in the list of earlier outputs and the list's mark (a mark that is
  not the last one is `OUTPUT_LIST_CHANGED`). The server checks the summaries
  again (`change_reasons`: the same rule as the page's), reads the output of
  the run and the output before as the view page reads an output
  (`read_checked`: the same checks and limits for each, a change while reading
  is `OUTPUT_CHANGED`), keeps neither, and answers the numbers only
  (`view/changes.py` `change_counts`), with whether the view page can open
  them (the output of the run among the outputs remembered, with the same
  output before); an output that cannot be read answers its code, which the
  line says. Where a record changed and the view page can open them, **Compare
  on the view page** opens the view page on the output of the run with
  `show=changes` in the fragment of its address, read once and never
  remembered.
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
20261026-9 to 20261026-11). It reads outputs, sends nothing, and does not
interpret the numbers: it does not say what a value means, which item causes
another, or what to do. From v2.3.0 it also reads the FIT file of one
activity in the Snapshot Store that the GUI remembers, only when the laps of
that activity are asked for
([Laps of an activity (v2.3.0)](#laps-of-an-activity-v230)), and the FIT
files of the activities with shoes of a period, only when the work laps of
the shoes are counted
([Work laps of the shoes (v2.3.0)](#work-laps-of-the-shoes-v230)). The `series`
command of the CLI writes the same numbers to a CSV file, with the same
functions (stage G2); it takes no conditions on the activities, which the
page has from v2.2.0 (stage T1).

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
  size and SHA-256 with the manifest that it read before the checks. A file or
  a manifest that changed stops the reading with `OUTPUT_CHANGED`. A file over
  128 MiB, files over 512 MiB together, or a manifest over 256 MiB are not
  read, and stop it with `OUTPUT_NOT_AVAILABLE`. From v2.2.0 the view page
  (never the series command) also reads the two files of the shoes,
  `normalized/gear.json` and `normalized/activity_gear.json`, after those of
  the items and checked in the same way (one that the manifest leaves out, or
  that changed, stops the reading with `OUTPUT_CHANGED`), within what the
  items leave of those limits: where they do not fit, the shoes alone are left
  out and the page opens (see By shoes below). After the shoes, it reads the
  file of the names of the activities, `normalized/activities.json`, in the
  same way: where it does not fit what is left of the limits, the names alone
  are left out and the page opens; one that the manifest leaves out, of
  another form, or that changed after the checks stops the reading with
  `OUTPUT_CHANGED` (a change before them is `HANDOFF_INVALID`; see Conditions
  on the activities below). The series command parses neither the shoes nor
  the names (the checks before the reading read every file of the manifest
  whole).
- From v2.3.0 (stage X7) the server also reads the output before the output
  shown, for the records that changed (see Changes since the output before
  below), and the normalization page's server reads the output of the run and
  the output before it for their numbers: with the same checks and the same
  limits for each output, so that two outputs may take twice the memory of
  one, as two outputs opened one after the other do. The output before of the
  view page is kept with the output shown (one at a time) and read again where
  its stamp or the date of today changed, or where another output is the
  output before; the normalization page keeps neither.
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
- The activity types counted are those of running at first, the names that the
  link between an activity and a FIT session counts as running, and can be
  chosen again; they apply to the panels of the training and running-form
  items, and so, from v2.2.0, do the conditions on the activities (see
  Conditions on the activities below).
- The period is all the time, the last 10, 5, 3, or 1 years, a range, or the
  same length before or after. The grouping is Auto, day, week, month, or
  year; Auto groups by month for a period longer than three years, by week
  for one longer than a year, and by day otherwise. The first and the last
  period, cut by the period, are marked as partial.
- A total (distance, time, count) is that of the recorded activities: a period
  without one is 0 between the first and the last activity of the types
  counted (that meets the conditions, from v2.2.0), and empty before and after
  them; it is drawn as a light point, as is a period whose recorded values add
  up to 0. The 0 of a period without a record does not always mean that there
  was no run. The pace is the total time divided by the total distance of the
  activities with both; a mean of activities is weighted by their durations; a
  daily item is the mean of the days with a value, and a sleep counts only on
  the days that it may be used.
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
  filters (the output, the period, the grouping, and the activity types, with
  the button of the conditions on the activities in the heading of the types
  from v2.2.0) stay in one row from a width of 1366 in Japanese, so that the
  panels keep the height. The period and the grouping apply to every panel;
  the activity types and the conditions apply to the panels of the training
  and running-form items.
- The item shelf at the left lists the items with bars of the months that have
  data (for the training and running-form items, of the activities of the
  types counted that meet the conditions, over the whole output), finds them
  by name, and folds to a rail.
- Panels of at least 150 pixels stand on one time axis; when they do not fit,
  only the panels scroll. A panel names its item, unit, and kind, gives the
  period and the values at the cross line, a second line of counts and the
  lowest, highest, and latest values, and notes of what is left out, and can
  be shown as a table (newest first, 400 rows at a time), enlarged, moved, or
  removed; one panel enlarged makes the others low strips on the same axis.
  Panels of the same unit can share one scale on request. Acute and chronic
  training load are both Garmin's values as they are, but two columns of the
  same source, so they share it.
- The grounds of a period (stage X6 of v2.3.0, the person's choices "1" (A and
  D) and "(a)" of the samples): the answer of the panels gives each line
  `per_period`, the rows that it left out of each period by reason, as pairs
  of the index of a period and a count (no period of 0 is sent): `no_value`,
  `zero_value` (a pace whose distance or time is 0 or less), `disagree`,
  `no_duration`, `duration_disagree` (an average by time whose time was
  emptied as its values disagreed), `sleep_review`, and `sleep_other`; a panel
  gives `per_period_other`, those of the lines of a series that it does not
  draw, and a line of the activities gives `counted_days`, the first and the
  last day of the activities counted in the output (of the types and the
  conditions chosen). They add up to `left_out`, whose keys and counts are as
  before (`zero_value` in `no_value`, `duration_disagree` in `no_duration`;
  `no_date`, `after_today`, `zero_periods`, and `days_with_several_records`
  are not rows left out of a period), so the `series` command of the CLI
  writes what it did. Neither the rows of a period nor the days with several
  records are sent. The reading at the top right of a panel always holds two
  lines, so that its heading keeps its height as the cross line moves and
  while no period is chosen (a low strip beside an enlarged panel, which shows
  neither the summary nor the notes of a panel, keeps its reading on one line,
  so that its chart keeps its height): the reading, and the grounds of its
  period, the number left out first (kept whole) and the reasons in short (cut
  at their end where the line does not fit; the reasons never widen the
  reading, while the number counts in its width, so that it is never cut), or
  where a period with nothing counted and nothing left out is (between the
  first and the last activity counted, outside them, or without a record of
  the item); its whole, in the words of the notes of the panel, is its title
  and is said after the values by the live region of the cross line (in
  parentheses in Japanese, after a semicolon in English). The list of a period
  gives each row `left_out` (the reason that the panel left it out, or null)
  and its value `grounds`: the cell of the item of a row left out says why,
  and a line under the value says what the panel left out of the period. The
  notes of a panel tell a pace of a distance or a time of 0 or less apart from
  one without a value, and a time emptied as the values disagreed apart from
  one missing, by the grounds summed, and say the days and the records without
  a value. Only what the output holds is said: a value of another form, which
  normalization left empty and only `audit/` keeps, is one without a value, as
  the view page reads no `audit/`.
- The overview under the panels shows the whole output by month, of the first
  panel or of the one enlarged (by the activity types and the conditions for a
  training or running-form item), and frames the period shown. A drag chooses
  a period: the frame follows it, with its days in the label, and a drag
  shorter than a week changes nothing. Within 8 pixels of an edge of the
  frame, the pointer is a double arrow, and a drag moves that edge as far as
  the pointer moves, never under a week. Escape cancels a drag.
- Full screen shows the panels and the overview alone, under one line that
  names the output, the period, the activity types, and, from v2.2.0, the
  words of the conditions (never their counts), and from v2.2.0 (stage U1) a
  dash for the period of an answer without its days (`fullDays`), filling the
  screen where the browser allows it and the window where it does not. Escape,
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
  this version does not know, names given twice, and those after the sixth are
  left out. From v2.2.0 (stage K2) they also remember the period, the
  grouping, the activity types counted, and the layout used last, and from
  stage T1 the conditions on the activities. Nothing is remembered for each
  output: the same values apply to every output. The page writes them 0.8
  seconds after the last change (a change within that time waits again), at
  once before it quits the app, and, when the page hides, in a request that
  outlives it (`keepalive`). Before the normalization page quits the app, it
  asks the view page on the quit channel to write what waits (`{ flush: true
  }`) and waits for its answer (`{ flushed: true }`) for 0.5 seconds at most;
  a value not written by then is given up, and the settings keep what they
  had. Once the app stopped, nothing more is written. After the other tab
  forgot the settings, only a change of the person writes them again.
- When an output opens (stage K2), a period such as the last year stays as it
  is. A range goes to the server as it is, which limits it to the days of the
  output as before; a range that does not overlap them at all opens all the
  time. The activity types counted are those remembered that the output has,
  and its running types, as at first, when it has none of them. The conditions
  on the activities stay as they are (stage T1).
- The layouts (stage K2) are cards above the item shelf, in two columns: the
  built-in layouts not hidden, in their order, then those of the person, in
  theirs. A card shows its name (a name of the person as text), "(changed)"
  once the panels are other items or in another order, and "Items with values
  n/m" when the output has no value at all for some of its items (counted over
  the whole output, not the period, from the bars of the item shelf, so that
  the activity types and the conditions count). Choosing a card shows its
  items, in its order, and remembers it as the one used last. "Save the panels
  as a layout…" names a new layout, which becomes the one used last;
  "Overwrite the layout" puts the panels into a changed layout of the person;
  "Manage layouts…" opens a small window that renames, moves, overwrites, and
  removes the person's layouts (a removal asks first, with "Keep it" as the
  default button), and hides or shows the built-in ones. A layout moves by Up
  and Down, by the arrow keys on its grip, or by a drag of the grip, which
  sends one change with the place of the layout (`to`). A change that the
  server refuses says why in one line where it was asked, and a layout that
  another tab removed reads the layouts again. On the folded shelf, "Layouts"
  opens the cards in a small window. The help panel of the view page gives the
  layouts in one item, after the item shelf (stage K3).
- Comparing one item by year (stage L1): each panel has "Compare years" (not
  for an output without days). The comparison shows one item of the output
  by year, in rows, laid over one another, or as a running total (totals and
  counts only), over the whole year or one month of each year, the newest
  four years at first and six at most; an item of several lines (VO2 Max)
  compares one of them. The periods of each year have their places on one
  axis: a week by its order from the week of 1 January, or of the first day
  of the month chosen (Monday weeks, up to 54), a day by its month and day on a leap year, a month by its number, and
  over one month the days of its longest month among the years chosen. The
  value of a year (or a month) is a period of the server: the page asks for
  the whole output grouped by year (or by month), and for each year by the
  grouping chosen, as one generation whose older answers are dropped and
  whose stop shows under its bar. A running total is added on the page from
  the values of the server, goes on after a period without a value, and has
  no counts. While comparing, the panels, the period, and the grouping of the
  page are kept for the way back; the period, its range, the shelf, the
  layouts, and the groupings Auto and Year (and Month over one month) are
  grayed, with a line under the filters that says so, and the overview is
  not shown. The settings remember the way and the month. The help panel
  gives it in one item, after the layouts (stage L2). From v2.2.1 (stage W3)
  the table of a comparison names its first column by the grouping, heads
  the counts in English with one short word, "Count" (a screen reader hears
  the whole heading), says under the table what was counted, and wraps its
  places and headings, English at spaces and never inside a word, Japanese
  between its characters too (it has no spaces), so that six years or six
  races fit its box. From v2.3.0 (stage X2) the name of a race in a heading
  may wrap between any two characters where it does not fit (`raceHeadParts`),
  so that six names of thirty letters with no space fit too; the other
  words of the headings wrap as before.
- Marks (stage M1): the person's own events, each a kind (race, injury, shoes,
  or other), a name of 1 to 30 characters (checked as the name of a layout),
  and a day or a span of days from 1 January 1900; 200 at most, ordered by
  their days. They are kept in `gui-marks.json`, next to the settings and
  under the same lock, written as the settings are (never more than 64 KiB),
  and never in an output, the support bundle, or the text of a report: the
  files of the support bundle and the report never read them. A file that
  cannot be read, or that a newer version wrote, is used for nothing and never
  written over; a mark that is not of its form is left out alone. "Marks…"
  adds, changes, and removes them, one change at a time
  (`/api/settings/marks`), and "Show marks" (remembered with the view) hides
  them. Every panel draws them in the colors of the text, the kind by the form
  of the line (a race a full line in the color of the text, shoes a dotted
  line, another mark a dashed line, an injury a line of dashes and dots; a
  span a light band whose edges are the line of its kind); the overview draws
  a short plain line at its top for each, whatever its kind (a span at its
  first day); the top chart names them, or counts them where their names would
  meet, and its label says up to 10 of them. Marks never change the numbers.
  Forgetting the settings removes their file too; 2.1.0, which does not know
  it, removes only the file of the settings, so that `gui-marks.json` and the
  folder of the settings stay after "Forget the remembered settings…" of
  2.1.0.
- Comparing by race day (stage M2): within the comparison, "Compare [item] by
  [year | race day]"; race day with two race marks or more whose days from the
  Monday 24 weeks before the week of the race to the race day overlap the days
  of the output, from its first to its last (a race after its last day too;
  always 24 weeks, whatever the span chosen, and whether or not those days
  have activities). Each race asks from the Monday of the week some weeks (2
  and 4 from stage X3, 8, 12, 16 at first, 20, or 24) before its week to its
  day, so that every race has as many weeks, placed by their order to the week
  of the race (by week; by day, see stage X3), which ends on the race day: a period cut short (as a year's ends are) where the race is
  not on a Sunday or the output ends within that week, as the server marks it.
  The value of the whole span is a period of a grouping that only the requests
  of the view page take, `range`: the CLI and the settings keep their
  groupings. The comparison follows the marks: a race removed or changed is
  asked again or no longer chosen, and with fewer than two races it goes back
  to the years; the page compares the marks with its last request, so that an
  answer on its way for the marks before is dropped. The settings remember
  what it compares by and the weeks; the races chosen are not remembered. The
  server keeps the bars of the item shelf with an output (up to eight sets of
  activity types, and from stage T1 of conditions) and up to 64 connections
  waiting to be taken.
- Comparing by race day by day (stage X3 of v2.3.0, the person's choice B of
  the samples): by race day, the grouping takes the day too (the week at
  first, in every way; not remembered, and kept where the way or the item
  changes, while the cross line starts again as before), and the span 2 and
  4 weeks too. By day, the days of a race are those of its span by week (from
  the Monday some weeks before its week to its day), so that the value of its
  whole span stays the same, placed by their days before the race day, which
  every race has at the last place (7 × weeks + 6). The span of a race not on
  a Sunday begins after the first place, and the places before it are not in
  its span ("Not in span" in the table and the readings, with a note under
  the table), whether or not the output reaches their days, as they are never
  asked for; the days of a span that the output does not reach are outside
  the output, as by week. A mark of a
  span has its first day as its race day, as by week. The axis is marked every
  7, 14, or 28 days before the race day (spans up to 4, up to 12, or of more
  weeks); by week, a span of 4 weeks or less is marked every week. The line
  under a picture says the grouping, as that of the years; the name of its
  file does not. The keys move the cross line as before (12 places with Page
  Up and Page Down). The settings keep 2 and 4 weeks: a version before 2.3.0
  leaves them out of its settings (that field only) and opens its page with
  16 weeks.
- The highest of each year (stage X4 of v2.3.0, the person's choice "C and
  range 2" of the samples): in a comparison of years (or of races), the period
  of the highest value of each year (or race) is that of the server's summary
  of the line compared (`summary.highest` of the answer of that year, as on
  the second line of a panel: of a total, among the periods with records; of
  equal values, the earliest; decided before rounding), never looked for again
  in the page, and never taken from the summary of every line of a panel.
  Every item has it (the highest of a pace is its slowest period). In the
  table (of every way but the running total, whose values are added up) its
  value is bold, with a triangle ▲ for the eye and its word for the ear, and a
  note under the table after that of * and — (of the year, of the month
  chosen, or of the span of a race). The heading of a row (by year, or by
  race) says "▼Highest <value> (<period>)" in the words of the second line of
  a panel, in one span of the class of the value of the year, so that a
  picture takes its words whole; a small triangle ▼ stands above the highest
  bar (or point) of the row, in its plot and above its cross line: 3 above the
  top of a bar, and 8 above the middle of anything else drawn there (a point
  of a line, the hollow dot of a 0, which stands on the baseline, or the
  records of a day, whose highest it stands above too: the value of such a
  day is the mean of its records), clear of the point or the dot, its ring,
  and the dot of the cross line. Overlay, running totals, and calendars
  draw none. Where the heading of a row has no room, the words of the highest
  shrink from the period, for the eye only; the name of a race (up to 16em, as
  before) and its day are kept. Where even that is not enough, the end of the
  heading is cut, as before (the reading on its right first, then the
  highest). Nothing is remembered, and the server is unchanged.
- The activities of a period (stage M3): a period of a chart of the training
  or the running form opens, by a click or by Enter or Space, the list of its
  activities under its panel, one at a time (`/api/view/activities`, under the
  checks of the numbers: the ticket, the activity types of the output, and the
  size of the answer). The server chooses the rows with the function that
  counts the panel (the types counted, from stage T1 the conditions, the days
  of the period cut to the output, as one period of `range`), up to 500 (more
  gives their number only), and gives the value of the panel and the count of
  the activities that it counted, from the same numbers; the page never counts
  them again. From v2.2.1 (stage W3) the sentences of the list name its
  period by its grouping ("the week chosen"), with the same placeholders in
  both languages. The columns are those of the output: the local date and time as
  the output writes them (not needed: an output without the column opens),
  from stage T1 the name where the names were read, the type, seven values,
  and the item of the panel where it is none of them. The page orders the rows
  by a column (rows without a value last either way; the date and time as they
  show, before their offset), draws the frame of the period on the chart, and
  closes the list when what the panels count or show changes, never while
  numbers are on their way, with the answer of its last request only. The list
  is never remembered and never written to a file.
- Comparing years as a calendar (stage N1): a fourth way to compare years,
  for amounts in rows and for the order of the days in a calendar: a strip of
  each year chosen, the weeks across from the week of 1 January (Monday weeks,
  up to 54 columns) and the days of the week down, each day of the output in
  one of up to six steps of one hue. The steps are
  the ticks of one scale over the days of all the years shown, made as a
  panel makes its scale (from 0 for a total, the units of the page, the
  clocks), each holding its left tick and not its right one; fewer steps are
  spread over the six colors, and the legend names them. A day of a total or
  a count without a recorded activity (0 with no activity) is an outline, a
  recorded 0 (activities of 0 km) is in the first step, and a day without a
  value or outside the output is not drawn. It goes by day only and uses no
  month: the month remembered stays (grayed) and comes back with the other
  ways, which ask again where the month that they use changes. It is grayed
  for the nine estimates that can have several records a day (the kind
  `obs`), with its reason behind an info button, and while comparing by race
  day, where a calendar remembered shows one row per race. The numbers are
  those of comparing years (each year by day, and the value of each year from
  the whole output by year), and a calendar is drawn only from an answer of
  whole years by day. The day chosen is one day of the year in every strip
  (28 February for 29 February of a common year, and the nearest day of the
  output outside it); a click, ← and → (a week), ↑ and ↓ (a day), and Home
  and End (the first and last day of the year in the output) move it, stop at
  the ends, and say it with its value, as the focus coming to a strip does.
  The strips have their own size (the squares 11 to 16 px apart, as the years
  chosen fit), the table is that of comparing years by day, and in forced
  colors the steps are one color by their opacity. The settings remember the
  calendar as a way. No new API.
- Other views (stages O1, P1, and S1): **Other views** in the row above the
  panels is a menu: Enter, Space, or Down opens it on its first item, Up and
  Down (round), Home, and End move in it, Esc closes it to its button, and Tab
  or a click elsewhere closes it; the row, and the menu with it, is not shown
  while comparing years or while another view shows. An item that cannot be
  chosen (**By shoes**, where no activity of the output has shoes, or their
  files were too large to read) says why under its name, stays in the way of
  the arrow keys (`aria-disabled`), and does nothing when pressed. Another
  view takes the place of the panels as a comparison of years does: the item
  shelf, the layouts, and the grouping are not used, with a line that says so;
  the period, its arrows (which go by the answer of the view), a custom range,
  the activity types, and (from stage T1) the conditions are the page's, and a
  change of them stays for the panels, which ask again on the way back, the
  focus on the menu. Each view asks for its answer under the checks of the
  numbers (the ticket, the activity types of the output, the size of the
  answer, and an output that changed); its activities are those of the types
  counted that meet the conditions in the days of the period, chosen by the
  function that chooses the rows of the list of a period, and a value is one
  that the list writes (the pace by the time over the distance). The items of
  two items plotted and of a distribution are the 15 of one activity (the
  kinds `act`, but the count, and `fit`); the settings remember those chosen
  while the page has panels, as the rest of the view (`view_plot`, a pair kept
  whole or not at all, and `view_spread`); the view by shoes always shows the
  distance by month, and nothing of it is remembered. The answers are of one
  generation: an older answer, or one of another pair or item, is never drawn,
  an output that opens drops those on their way, a ticket that the server no
  longer keeps opens the output again once, and an output that stops closes
  the view; while an answer of the same pair or item is on its way, the chart
  before stays, dimmed.
- Two items plotted (stage O1): `/api/view/points` gives each activity with a
  value of both items as a point, the newest `MAX_POINTS` (5,000) at most,
  oldest first in the order of their dates and times as they show, with how
  many activities the period has, how many have both values, and how many do
  not. The page draws a scale for each item over its values (never from 0, and
  the pace with a smaller value lower or further left, as the panels draw it),
  in the units and the clocks of the page, a point an activity, and always the
  words that this app shows no relation or cause between the two items. The
  first pair is the average pace across and the average heart rate up; an item
  chosen in one list is disabled in the other, with why. The reading at the
  top right gives the date and time with the year, the type, the two values,
  and how many more have the same values; the pointer chooses the nearest
  point within 12 px, and a click, ← and → (by the order of the dates and
  times), Home, and End choose a point and say it. The table gives a row an
  activity, newest first at first, ordered by its heads, 400 rows at a time.
- The distribution of one item (stage P1): `/api/view/spread` counts the
  activities with a value of the item in ranges of the width of the item
  (`SPREAD_RANGES`: a scale and a width in the units of the output, which the
  guides give as a table in the units of the page, tied to it by a test), each
  holding its left end and not its right one, from the first range with an
  activity to the last; at most `MAX_RANGES` (200) ranges, the width times the
  first of 2, 5, 10, 20, ... that is enough, counted from the numbers of the
  ranges, never from the span of the values (the server stops where more would
  be made). A value is counted as the output writes it, never rounded: an
  exact fraction of its decimal text, the pace by its time times 1000 over its
  distance, and the number of its range cut toward the smaller number as an
  integer of Python, so that a value shown rounded can be in the range below
  (10,999.6 m, shown as 11.0 km, is in the range from 10 to 11 km, as the
  guides say). The answer gives `first`, `width`, and `scale`, from which
  alone the page writes the ends; an end that the page cannot write (a range
  number past 2^53, two ends that it cannot tell apart, or a value of 1e15 or
  more in the units of the page) is a dash. The page draws a bar a range with
  an activity, placed by the order of the range only, in the first color, with
  a gap of 2 px between bars of 8 px or more; the counts on whole ticks from
  0; the ends in words where they are far enough apart; and the pace faster to
  the left, which a line says. The reading gives the range and its count ("10
  km or more, under 11 km: 42"); a click, ← and → (one range, those of no
  activity among them), Home, and End choose a range and say it, framed as
  high as the chart. The table gives a row a range, those of no activity among
  them. In forced colors, the bars are in the color of the text and the range
  chosen in the highlight.
- By shoes (stage S1): **By shoes**, the third item of **Other views**, shows
  a panel for each pair of shoes with its distance by month in the place of
  the panels, as the rows of comparing years do: one color, one scale for all,
  on one time axis over the period chosen, as bars up to 220 months and as a
  line above (`MAX_BARS`). Only the view page reads the shoes (see Reading an
  output above). The links join as the output declares them: by
  `garmin_activity_key`, both ends `explicit`, a gear key as a token of
  `common.identity`, the first record of a key. Gear of the type `shoes` or
  `running_shoes` (in lower case) are shoes; an activity with no link to shoes
  is not known to have shoes where it has no key, or links to gear not in the
  output or of a type not known; links to other gear are left out. A name is
  the `display_name`, else the `custom_make_model`, else none. The answers of
  opening and of the numbers say how many pairs link to an activity of the
  output up to today, of any type and never by the conditions, or that their
  files were too large (`shoe_count`); with none, or too large, the item
  cannot be chosen, and the page keeps what the answer asked for last says.
  `POST /api/view/shoes` `{view, period, types}` (and from stage T1
  `conditions`), checked as the numbers are, answers (`shoe_answer`), for the
  activities of the period and the types counted that meet the conditions, how
  many have shoes (and of those, how many have two or more and how many have
  no distance), are not known, and are without; and for each pair with an
  activity in the period, the newest last use first (then the order of
  `gear.json`): its distance by month (0 between its first and last use in
  the output, of the types counted that meet the conditions, also outside the
  period, as on the panels: stage U2), in the whole period (from its
  activities, never the sum of the months), its activities by month, its
  first and last days in the period, what Garmin sets (start, end,
  and maximum distance in meters), and what tells it from the shoes of the
  same name (the day of its start where it is theirs alone, else its number).
  Pairs without an activity in the period are counted only; with no pair in
  the period, the page says so in the place of the panels and cannot save a
  picture. A long name is cut with an ellipsis, never what tells it apart. A
  cross line, moved by the pointer over a row or by Left, Right, Home, and End
  on a row, reads the month of every row, and the row of the keys says it.
  **Show as a table** gives a table of the shoes and one by month, whose
  months stay at the left while it scrolls. The notes say what Garmin sets and
  each count of 1 or more. A picture saved holds every row, also those
  scrolled out of the screen, the axis, the notes, and the footer, never the
  cross line; its file is named by the period and the key of the distance,
  never by a name, and the window says before saving that the names of all the
  shoes show. The names are written in no log, setting, or file name. Nothing
  is said from the values that Garmin sets.
- The summary of the panels (stage Q1): `/api/view/series` with `"previous":
  true` (a truth value, with the whole period `RANGE_GRAIN` only) also gives
  the days chosen, before the output cuts them, and whether the output holds
  them, and the panels of the period of the same length just before, counted
  by `item_series` from the same reading with the same types and conditions:
  the years of `LAST_YEARS` back from the day before the period (the day after
  the same day n years before, as `period_bounds` counts them), the same
  number of days before a range, and none for all time; an end before 1
  January of the year 1 is null, and a period wholly outside the output has no
  panels. **Summary…** after **Other views** opens a window that is not modal
  at the place of the window of the marks (one of the two at a time), its
  title taking the focus: a row for each item of the panels (a row for each
  series, in the order of the server, named as the lines of a panel), the
  value of each period, and their difference, that of the two values as
  written, with a sign only where it does not read as 0, and a dash where a
  value is missing or the output cuts a period, whose values are marked * with
  a note. It shows and asks only with panels, outside a comparison of years
  and the other views, and not in the graphs only; an answer is drawn only for
  what it was asked for (the ticket, the period, the types, the conditions,
  and the items), and the answers on their way are dropped where the window
  hides and where an output starts opening. The windows under the row above
  the panels end above the bar at the bottom of the page.
- Saving as an image (stages R1 and R2): **Save as image…** after **Summary…**
  in the row above the panels, and after **Show as a table** in the bars of
  comparing years, two items plotted, and a distribution, opens a window that
  is not modal under the row of its button (one of the windows of the marks,
  the summary, and saving at a time), its title taking the focus, with the
  first choices each time (all the panels, the light colors, no marks), which
  nothing remembers. The page copies the charts shown into a box out of the
  page (`.save-stage`, in the light colors where they are chosen), writes the
  colors and the fonts that its CSS gives into each shape (`writeSaveStyles`),
  leaves out what lies on top of the charts to show a choice (the cross line,
  the frame of the day chosen, and the point and the range chosen:
  `SAVE_LEFT_OUT_VIEWS`), and makes one SVG file: the headings with the keys
  of their lines, the charts, the axis, the words that the page shows under
  them, and a line of the period or of the years or race days compared, the
  grouping or the width of a range, the activity types counted, the conditions
  on the activities where there are some (their words as written, that they
  apply to the training and running-form items only, and, where the names
  could not be read, that the words of the name were not used), and the name
  and version of this app. The file is handed to the browser as a download
  from a `blob:` address by a link with `download`, in the press of **Save**
  with nothing between; the page cannot know whether or where the browser
  saves it, so the bar at the bottom says that it was handed. The name of the
  file holds dates (or years) and the keys of the items only (`saveFileName`,
  `saveViewFileName`), never the names of races or marks or the words of the
  conditions; where the conditions have words of the name, the window says
  that they show. The window says why it cannot save (a table, an answer on
  its way, a stop, two items plotted or a distribution without values, a chart
  without room, a panel chosen that went, every panel a table), and the press
  checks again the name and whether it can save. From v2.2.0 (stage U1), a
  press that can no longer save keeps no reason that the window says by itself
  (`saveSays`, `savePress`), so that the reason goes with what the window
  says, and the focus goes to the title of the window where **Save** cannot be
  pressed, while the window shows; an answer without its days (a period that
  the output does not reach) has no line under its picture and no name of a
  file. Nothing is sent to the server or anywhere else, and the
  Content-Security-Policy stays as it is. Before v2.3.0 only SVG was made (a
  PNG from stage X5, below); other formats are out of scope. From v2.3.0
  (stage X2) the window says what it
  saves and then the line before a saving, above its choices; the names of
  the marks that the choice of the panels puts in are said under that
  choice, so that a press does not move it; its end, why it cannot save
  and the buttons (`.save-end`), stays at the bottom of the window while it
  scrolls, where at 1366 × 650 the buttons were hidden in it; and the
  window opens at its top each time, also where it was scrolled before it
  closed.
- A PNG of the size of a post (stage X5 of v2.3.0, the person's choice "B and
  list 1" of the samples): the window has **Format** (SVG first, or PNG) and,
  for PNG, **Size** (4:5 portrait 1080 × 1350 first, 1:1 square 1080 × 1080,
  or 9:16 portrait 1080 × 1920), chosen again each time it opens, with the
  note "PNG, in the sizes of social media posts seen on a phone."
  (sizes only: nothing is sent to or joined with a service). For a PNG the
  picture is laid out in a frame about as large as the screen of a phone (432
  wide; 540, 432, or 768 high: `SAVE_SIZES`), and its charts are drawn again
  there, when **Save** is pressed only, by the functions that draw them on the
  page, given a copy of their panel or row with a box out of the page in place
  of their plot, or the box and a size: the page keeps its own, and the
  numbers are those of its answers; only the room they are drawn in changes.
  A first layout with charts 100 high (a plot or a distribution 120, the
  least it is drawn at) measures the rest of the picture, and a second one
  makes the charts fill the frame (`saveFrameHeights`); a chart
  lower than 40 (120 for two items plotted or a distribution, the least they
  are drawn at) does not fit, and the window says so (fewer panels, or a
  taller size; for 9:16, fewer panels). The strips of a calendar get squares
  as far apart as fit the width of the frame (7), never more than on the page,
  nor less: nearer, the outlines of the days without a record turn to dots
  and the names of the months meet, so a calendar higher than its frame does
  not fit. The words of a picture wrap where a line may end
  (`saveLines`): before a space, but not one between a figure and a unit or a
  count (as in "16 週" or "700.1 km"; before hiragana, as in "10–20 は", it
  may), and, in Japanese, next to its letters, but never inside a word
  of Latin letters or figures, after an opening bracket or quotation mark or
  the triangle of a highest, or before a closing one, a mark of punctuation,
  or a small kana (from X5; before, a line of Japanese with no space ended after its
  last letter that fit, also inside a word such as "Garmin", which the narrow
  frame of a PNG showed). The marks of an axis drawn again are thinned at
  even steps where their words would meet, the first one kept and naming its
  year, as the first one kept of each new year (`thinTicks`); the page keeps
  its own axes. The picture is painted on a canvas out of the page, 2.5 times
  as large (1080 wide), in the middle of its frame on its ground (`paintPlan`,
  `paintItems`): the shapes that a picture holds (svg, g, path, line, rect
  with its round corners, circle, and text, its words as SVG shows them) at
  the places of their view boxes, with the properties that they take; an
  element with an opacity below 1 (the years not highlighted) is painted on a
  layer of its own and laid on with that opacity; any other element stops the
  saving. The PNG is made at once (`toDataURL`; `toBlob` would wait), so that
  it is handed to the browser in the press of **Save** as the SVG is; nothing
  is loaded as an image, so the Content-Security-Policy stays as it is. A
  canvas keeps no width of figures (`font-variant-numeric`), so figures may be
  a little narrower or wider than in the SVG. The name of the file is that of
  the SVG with the size and `.png` (`savePictureName`). The line under a
  picture keeps the space after its separator in English (`saveFooterPieces`,
  U+00A0, as SVG drops the spaces at the end of a text; from R1 the next words
  stood at the dot), in the SVG as in the PNG.
- The colors of the years compared and a year highlighted (stage L3): the
  lines of the years laid over one another or as running totals take colors of
  their own (`--year1` to `--year6` in styles.css), apart from the six steps
  of one hue of the calendar (`--y1` to `--y6`): of the years (or the races)
  chosen, newest first, the purple of the page, orange, teal, and navy (a
  light gray on dark), then indigo and sky blue (brick and yellow on dark),
  each 3:1 or more on the surface. They go by the order among the years
  chosen, not by the year, so that the first four, the most apart, are always
  used: taking out the newest year makes the next one purple. As a guide for
  the design, not a promise that thin lines are told apart, the closest pair
  of the first four is 15 or more apart under normal vision and 8 or more
  under protanopia and deuteranopia (OKLab ΔE ×100 in linear sRGB, simulated
  with the matrices of Machado and others (2009) at severity 1, clipped to 0
  to 1): 23.2, 10.9, and 18.1 on light, and 22.4, 13.7, and 14.1 on dark.
  Tritanopia is left out of the guide: on light, the purple and the teal are
  6.7 apart and both are full lines; a year hard to follow there is followed
  by highlighting it. The 5th and 6th years are dashed too, as in forced
  colors, where every year but the newest is; a dash is cut square (butt) as
  long as its round end drew it until L3, so that a thicker line keeps its
  gaps. A press on a year in the legend (a button for each year that the chart
  draws, with aria-pressed, bold in an edge of the color of the text when
  pressed; by race day, it says the whole name and the days of its race to the
  ear, as the buttons of the races do), or on the chart within 8 px of what
  the line of a year draws (the pieces of its line, never across a break, and
  its dots from their edge; the names at the ends of the lines first; a tie
  goes to the year drawn on top), highlights it: its line 3.5 px wide and
  drawn last, and the other years at 0.28 opacity; a press on it again, or Esc
  on the chart or on a key, puts it back. The chart is not drawn again: the
  marks of its shapes and keys change, so that a key keeps the focus. A year
  highlighted lasts while the chart draws it, and is never remembered. While a
  year is highlighted, the other lines fall under 3:1 on the surface (1.35 : 1
  on light and 1.26 : 1 on dark for the lowest): it is a passing state that
  the person chooses and ends with one press or Esc, and the readings of every
  year stay at full strength in the box beside the cross line. In forced
  colors no year fades; the year highlighted only gets thicker. A picture
  saved shows the highlight as the page does (the marks are on the shapes
  themselves, which the box of a picture keeps), with the key of the year in
  bold.
- Conditions on the activities (stage T1): **Conditions…** at the right of the
  heading of **Activity types counted** opens a window that is not modal, as
  that of the types (one of the two at a time; closed by Esc and **Close**,
  never by a click outside, and when an output opens and when a comparison of
  years, another view, or the full screen starts), its focus in its first box
  that can be used: the words of the name, a distance in kilometres (up to
  three decimals, made into whole metres from the digits), and a duration in
  whole minutes, each from and to. A box applies on Enter (never while an IME
  composes) or on a change when it is left, after the page checks it by the
  rules of the server (`conditionsFromBoxes`): the same conditions ask nothing
  again, and conditions that cannot be used say why in the window and change
  nothing. `Conditions` (`view/series.py`) holds the words as written and as
  compared (`condition_words`: in NFKC, split at `、` and `,`, without the
  spaces at their ends that `str.strip` takes, case folded, without the empty
  and the same words; up to 60 code points and 10 words, without a control or
  direction character), the distance in whole metres (up to 1,000 km), and the
  duration in whole minutes (up to 6,000). An activity meets them where its
  name holds one of the words, if there are words and the names were read, and
  its distance and duration, as the panels count them, are within the bounds,
  both ends included (the minutes times 60 against the seconds); without a
  name where the words are used, or without the value of a bound given, it
  does not. They choose after the activity types in `_activity_rows`, so that
  every view takes them: the panels, the period before of the summary, the
  bars of the item shelf (kept by the types and the conditions), the list of a
  period, the points, the distribution, and the shoes; `series` takes none.
  The five routes of the views take `"conditions"`, and another form is
  `CONDITIONS_INVALID` (422, a stop of the numbers, which the page checks
  before it sends). Each answer with conditions gives them back (`asked`),
  with the activities of the types counted in its days (`counted`), those of
  them that meet (`met`), and whether the words of the name were used
  (`name`); every answer of a view, and the opening, say whether the names
  were read (`names`). A line under the filters says the conditions as
  written, that they apply to the training and running-form items only, and
  the counts of the answer drawn where that answer is of these conditions
  (none while there is no panel), and where the words of the name were not
  used; in the full screen, their words go into the line at the top, and from
  v2.2.0 (stage U1) that the words of the name were not used where the answer
  of the panels, of these conditions, says so (`conditionsUnread`). The list
  has a column of the names (each in `<bdi>`, wrapping in 16em) where the
  names were read. The names: after the shoes, the view page (never `series`)
  reads `normalized/activities.json`, checked as the other files are, within
  what those leave of the limits (see Reading an output); a file over them is
  not parsed, and the page opens without the names, where the words are not
  used and the line says so. Only the declared key of an activity and its name
  are kept (a text with something besides spaces, cut at 200 code points,
  which are what the words are compared with, and shown with an ellipsis); a
  key that two records hold has no name; the memo, the place, and the hash of
  the same records are never kept. The settings keep the conditions in the
  form of a request (`view_conditions`), whole or not at all, apart from the
  layouts. The view page writes the names into no file, and the words of the
  conditions only into the settings and into a picture that the person saves:
  never into a log, an error, or a file name.
- An output that changes while the view page is open is read again at the next
  request (and so is any output when the date changes), so that a comparison,
  a list, the summary, or another view asked right after a new normalization
  can come from another reading than the panels beside it; asking again uses
  the new reading. Back from another view, the panels ask again where the
  period, the activity types, or the conditions changed while it showed
  (`panelsStale`), and from v2.2.0 (stage U1) where an answer of that view was
  of another reading than the panels, so that otherwise they show the reading
  before. Each reading of an output has a number of one count for the whole
  server, given with its data in the answers of `/api/view/series`,
  `/api/view/points`, `/api/view/spread`, and `/api/view/shoes` (`read`; from
  v2.3.0 also in those of `/api/view/activities` and `/api/view/laps`, which
  the page does not compare with that of the panels: the list gives it so
  that the laps of its rows are asked of the same reading); the page compares
  that of the panels with that of an answer of another view
  taken after the check of its generation, and a number missing counts as
  another reading. From v2.2.1 (stage W1), the answer of `/api/view/open`
  gives the number of its reading too, and those four answers give the facts
  of their reading of the output (`output`: its first and last days, its
  activity types with their counts, and whether it is partial). An answer of
  the ticket shown, of a newer reading whose facts differ from those of the
  output opened, is not used: the page opens the output again by itself, as
  **Choose another output…** with the same folder does, by the ticket that
  reads it (`{"output": "view", "view": ticket}`, so that a run or the list of
  earlier outputs, which can name another output by then, is not asked; the
  place is not told, and a ticket that the server no longer keeps opens the
  target chosen), unless an output is being opened; a newer reading of the
  same facts only moves the reading known on, and the overview keeps the
  number of its reading in its signature. A request of the ticket shown that
  is refused with `REQUEST_INVALID`, as for an activity type that the output
  read again no longer has, opens the output again by itself once, until a
  newer reading than the one that it opened is seen; the overview too. An
  opening by itself drops the answers of the output before (those of the
  panels too), writes no settings, keeps a date being typed and the windows
  of the activity types and the conditions, and gives the focus back where it
  was only where the focus was lost meanwhile. The guides say this in one
  place.

### Laps of an activity (v2.3.0)

From v2.3.0 the view page can show the laps of one activity with the kind of
each lap that its FIT file records, so that the pace of the hard parts can be
seen apart from the rests (the decision of the Human maintainer at stage X8,
which widens what the page reads; stages X9b to X9c-2). An output does not
hold these kinds, so the server reads them, only when the laps of one
activity are asked for, from the FIT file of that activity in the Snapshot
Store that the GUI remembers (`fit/lap_kinds.py` reads the kinds,
`gui/fit_reading.py` the files). The window of the laps on the page, and the
words of the reasons why laps are not shown, are stage X10.

- The request: `POST /api/view/laps` `{view, read, ref}`, under the checks of
  the other requests of the view page. `ref` is the place of the activity
  among the activities of a reading and `read` the number of that reading,
  which the list of a period gives (`read`, and `ref` with each row; never
  the key of an activity). Both are whole numbers, not truth values, and
  `ref` is one of the activities of the reading; otherwise `REQUEST_INVALID`,
  and a ticket that the server does not keep gives `VIEW_NOT_OPEN`.
- The output of the ticket is taken as for the other requests (read again
  where it changed, or the date did), and a `read` of another reading is
  answered as stale, with the number of the reading now, so that the page
  asks for the list again: the places of one reading are never taken for
  those of another. Then one reading of a store at a time for the whole
  server: another request is answered at once that it is busy. The lock is
  taken without waiting once the output is read and the activity found, and
  held around the reading of the store only, so that a reading of an output
  that waits keeps no other laps busy.
- The store is the one that the settings remember (`store`, which a Snapshot
  run writes), read at each request; there is none where the settings are
  missing, cannot be read, are of another form, or are of a newer version. It
  is opened at that place, or else in its folder `snapshots`, as the page
  opens a store; a folder that holds what a store writes without its
  `store.json` is a damaged store, as `load_store` takes it, and the next
  place is not tried. The folder `snapshots` is opened in the folder opened
  at the remembered place, which stays open until the reading ends (on
  Windows it is held, and the system must have the folder `snapshots` in
  it), and a remembered folder that is not there has none, so that a folder
  put at the remembered place meanwhile is not followed.
- What is read: the files of the output that tie the activity to its FIT file
  (`snapshot/snapshot_lineage.json`, `normalized/activity_fit_links.json`,
  `normalized/fit_sessions.json`, and `normalized/fit_laps.json`), each read
  once and compared with the size and the SHA-256 that the manifest of the
  reading gives; the `store.json` of the store, up to 64 KiB, which must be
  that of the store in the lineage of the output; where a folder has no
  `store.json`, whether it holds the other names that a store writes, each
  looked at alone at its top (no file is opened, and no other name is read);
  and the FIT file of the activity among the blobs of the store, by the
  SHA-256 that the output records, read once up to 32 MiB and used only
  where the SHA-256 of its bytes is that one and its sessions and laps are
  those of the output. Nothing else of the store is read, and nothing is
  written, kept, or sent.
- Links: the folder of the store is opened once, and every step from it
  without following a link. On macOS and Linux each folder of the way is
  opened from the one before it, by its descriptor, and the file with
  `O_NOFOLLOW` and `O_NONBLOCK`; on Windows, which has no such openings, the
  folders of the way are held from before they are looked at until the file
  is read, so that none can be renamed or removed meanwhile, the file is
  opened as itself, and it is read only where its final place is, letter for
  letter, that of the held folder and the way. A link, a junction, another
  reparse point, a pipe, or a file or a folder without an identity is
  refused; each step is looked at again after the reading, and the files of
  the output are opened without waiting and as themselves. The folders above
  the remembered folder are not looked at, as `load_store` does not look at
  them.
- The answer (200): `{status: "laps", laps, counts, read, output}`, each lap
  with its `kind` from the FIT file (`active`, `rest`, `warmup`, `cooldown`,
  `recovery`, `interval`, or `unknown`) and its values from the output
  (`elapsed_s`, `timer_s`, `distance_m`, `avg_heart_rate`, `max_heart_rate`
  from stage X10, `avg_cadence`, and `avg_speed`; none read anew from the
  store), and `counts` the number of the laps and of those of an
  unknown kind; or `{status: "unavailable", reason, read, output}`, where
  `reason` is one of thirteen (`LAP_REASONS` of `gui/server.py`):
  `not_from_store`, `no_store`, `other_store`, `store_unreadable`, `no_link`,
  `key_shared` (a key that another activity has too, or none), `fit_missing`,
  `fit_too_large`, `fit_changed`, `fit_not_activity`, `laps_differ`,
  `read_stale`, and `busy`. `output` gives the facts of the reading, as the
  other answers do. No place, SHA-256, key of an activity, or position is in
  an answer.
- From stage X10, the list of a period gives with each row, besides `ref`,
  why the laps of that activity cannot be shown where the output alone tells
  it before a file is read (`laps_unavailable`): `key_shared` where the
  activity has no key or another activity has it too, else `not_from_store`
  where the manifest of the reading has no `snapshot/snapshot_lineage.json`,
  else `null`. Asking for the laps tells the same, in the same order, and
  the other reasons only then. The list of `view.series` and the CSV file of
  the command `series` do not have it.
- A file of the output that is not as its manifest gives it, or of a form
  that this version does not write, gives the code of the check of the
  output (such as `OUTPUT_CHANGED`), and an answer of any status over 4 MiB
  gives `VIEW_ANSWER_TOO_LARGE`.
- The cadence in steps per minute (stage X10, the choice of the Human
  maintainer): Garmin's files record the cadence of a run of one foot
  (strides per minute, the `avg_running_cadence` of the FIT profile), half of
  what the watch shows (steps per minute, both feet). The page writes the
  item `cad` (Garmin's `avgRunCadence`) doubled, in `spm`: in
  `ITEM_FORMATS` of `view_flow.mjs` it is the one item whose factor is not
  that of its unit (2), so that the panels, their scales, the list, the
  summary and its differences, the comparisons, the plot, the distribution,
  and the saved pictures show steps per minute; the window of the laps
  doubles the cadence of the laps of a running type the same way, and shows
  none for another type. That the doubled value is the watch's was checked
  with the running types; a value of another type is doubled too. The answers
  of the server, the output, and the CSV file of `series` keep the values as
  recorded (the output contract says to keep the basis of a source value).
  The widths of the ranges of the distribution stay those of the server (5
  as recorded, 10 steps per minute on the page).

### Work laps of the shoes (v2.3.0)

From v2.3.0 the view by shoes can count, for each pair of shoes, the laps of
its activities in the period whose kind, as their FIT files record it, is
Active or Interval (the work laps), so that the average pace of a pair is not
pulled down by its rests (the Human's choice of the samples of stage X11: the
table of the work laps above the table of the shoes, and the kinds Active and
Interval). The server reads them with the guards of the laps of an activity
(`gui/fit_reading.py` `read_many_laps`) and adds them up by pair
(`gui/shoe_work.py`), a request of the page at a time; the page adds the
requests up.

- Before reading: the answer of the shoes (`/api/view/shoes`) gives `work`:
  `{runs, known, limit, reason}`, the activities with shoes of the view, those
  known not to be read before a file is read (`key_shared`, as
  `laps_unavailable` of the list), the most of one counting (5,000), and
  `not_from_store` where the manifest of the reading has no
  `snapshot/snapshot_lineage.json` (else `null`). No file is read for it. The
  page says how many activities it reads before it reads them, and greys its
  button where none can be read.
- The request: `POST /api/view/shoes/work`
  `{view, read, period, types, conditions, from}`, the period, the activity
  types, and the conditions as for the shoes, `read` the number of the
  reading whose shoes the page shows, and `from` the place, among the
  activities with shoes of the view in the order of the output, where the
  request starts (a whole number, not a truth value, at most the number of
  those activities); otherwise `REQUEST_INVALID`. A `read` of another reading
  is answered as stale, and the lock of the laps of an activity is taken as
  for them: another reading of a store is answered at once as busy (the page
  asks once more after a second, then stops).
- One request reads the files of the output that tie the activities to their
  FIT files once, and the activities from `from` with the checks of the laps
  of an activity (a link of an activity is checked against all the links of
  the output), each FIT file once by its SHA-256, until it has done 100
  activities or the next FIT file would bring the bytes that it read past
  32 MiB (by the size of the file as it was opened, before a byte of it is
  read; the first FIT file of a request is read within the 32 MiB of one
  file). A FIT file that is read counts, whether or not it is then found as
  the output says. A FIT file of two activities whose requests differ is read
  in each.
  Of each FIT file only the kinds of its laps are kept, until the request
  ends.
- The answer (200): `{status: "work", runs, from, next, pairs, counts, read,
  output}`: `runs` the activities with shoes of the view, `next` the place of
  the next request (`null` after the last), `pairs` the sums of each pair in
  the order of the view, and `counts` those of the period, which count an
  activity of two pairs once (`two_pairs`). A sum holds the work laps, the
  time and the laps that have one, the distance and the laps that have one,
  the time and the distance of the laps that have both (a distance above 0)
  for the average pace, the heart rate weighted by the time and that time
  (all of them whole numbers: milliseconds, centimetres, and beats a minute
  times milliseconds, the units of the FIT file, so that the sums of the
  requests add up to those of one request exactly, wherever they end), and
  the activities: counted, counted with no work lap where all their laps
  are of a known kind, counted with their laps of no known kind left out (and
  those laps), counted with no work lap of a pace, and not counted by reason
  (`unknown_kinds` where an activity has no work lap and some laps of no
  known kind, `no_laps`, and those of the laps of an activity that are of one
  activity: `key_shared`, `no_link`, `fit_missing`, `fit_too_large`,
  `fit_changed`, `fit_not_activity`, `laps_differ`, and `store_unreadable`
  where a FIT file cannot be read). An activity of two pairs counts for each
  pair, with its distance, time, and heart rate. Or `{status: "unavailable",
  reason, read, output}` for all: `not_from_store`, `no_store`, `other_store`,
  `store_unreadable` (the `store.json`), `too_many` (more than 5,000
  activities), `read_stale`, or `busy`. No place, SHA-256, or key of an
  activity is in an answer, and an answer over 4 MiB gives
  `VIEW_ANSWER_TOO_LARGE`.
- The page: "Count the work laps…" in the bar of the shoes shows the tables,
  says what it reads, and reads on "Read", one request at a time, saying how
  many activities it read; "Stop" asks no more, and the answer of the request
  on its way is dropped. The table of the work laps (a row a pair: work
  distance, time, average pace, average heart rate, activities counted and
  not) shows above the table of the shoes, with two lines under the tables
  and the rest of the counts behind an info button. A reason, a stale
  reading, a stop, or an answer of another form drops all that was read;
  another period, activity types, conditions, or reading drops the counting.
  The table is not in a saved picture (a table is not saved).

### Changes since the output before (v2.3.0)

From v2.3.0 the view page can compare the output shown with the output before
it (stage X7, the Human's choice D of the samples: the lists on the view page
only, and the numbers on the normalization page). **Compare with the output
before**, the last item of **Other views**, shows in the place of the panels
the activities new, changed (by field, before and now), with their shoes
changed only, and in the output before only, and the pairs of shoes new,
changed, and in the output before only, each list newest first and of up to
500 rows (`MAX_CHANGE_ROWS`; the older ones are counted).

The output before is the first output after the output shown among those that
the settings remember (newest first) that is there as a plain folder and whose
summary can be read (`gui/outputs.py` `output_before`), the rule of the output
before a run; `earlier_outputs` is not used, as it gives the outputs newer
than an older one shown too. The two are compared only where `change_reasons`
gives none (the way of normalizing, the version and the version of Run-All,
and the timezone); otherwise, and where the settings do not remember the
output shown (`not_remembered`) or no output is after it (`none`), the item of
the menu says why under its name and cannot be chosen. The answer of opening
an output gives it (`changes`), and the answer of the changes again.

The comparison (`view/changes.py`) reads nothing: it takes two readings
(`ViewData`). The activities are matched by their declared key; an activity
without one, or with one that another activity of the same output holds, is
counted apart for each output. The fields compared are those of the list of a
period (`LIST_ITEMS` without the pace, which the distance and the time make),
the date and time, the activity type, the name, and the shoes (the pairs that
an activity links to, and whether it has a link that tells no shoe); a value
against none differs. The names are compared only where both readings read
them, and the shoes (their links and the pairs) only where both read them, so
that a file left out of one reading never makes every record look changed; the
answer says which reading left them out. Rows without a date or after today
are not compared, as no view shows them.

The answer never gives the declared keys nor the places of the outputs: the
values as numbers, which the page writes as the list of a period does (the
dates with their years, as the lists go across the periods), the names of the
activities and of the shoes, the shoes by their places in the lists of the
shoes of each output (named as the view by shoes names them), and the names of
the two outputs; it is refused over `MAX_ANSWER_BYTES`. A reading of the
output before that fails answers its code, and the output shown stays open. No
period, activity types, or conditions are used, and the view is not saved as a
picture; nothing is remembered (it is not a key of the view settings) or
written.

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
  [Stops and next steps](v2_data_handling.md#stops-and-next-steps). It takes
  no conditions on the activities (stage T1 of v2.2.0): its numbers are those
  of the page without conditions.

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
- The messages between the tabs of a launch (`BroadcastChannel`, v2.1.0) carry
  the colors, the generation of the settings after a forgetting (from stage U2
  of v2.2.0; until then, the notice that they were forgotten), and the notice
  that the app stopped; never the key. The view page reads outputs, and from
  v2.3.0 FIT files in the Snapshot Store that the GUI remembers (that of one
  activity when its laps are asked for, and those of the activities with
  shoes of a period when their work laps are counted), through the server
  only, and opens nothing outside the page.

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
- The settings of an earlier launch hold the names of places only (stage B4c),
  stay on this computer, and are never part of the Support Bundle; "Forget the
  remembered settings…" removes them, as on a shared computer. From v2.1.0
  they also hold the colors of the page, and the names of the items that the
  view page showed and whether its shelf was open. From v2.2.0 they also hold
  the timezone of the last run that made its output, the layouts that the
  person named, and the period, the grouping, the activity types, and the
  conditions on the activities (with the words of the name as written) of the
  view page.
- From v2.2.0 the marks of the view page, the person's own words and events,
  are kept in a file of their own next to the settings (`gui-marks.json`),
  never in an output, the Support Bundle, or the text of a report.
  "Forget the remembered settings…" removes them too; 2.1.0 removes the file
  of the settings only, so that after going back to it the file of the marks
  and the folder of the settings stay until 2.2.0 forgets them or the folder
  is removed. The list of the activities of a period shows the dates and
  times of the output on the page only.
- From v2.2.0 a picture saved from the view page shows the dates and values of
  its charts, and the names of the marks where they are put in and by race
  day; the page makes it and hands it to the browser as a download, sending
  nothing anywhere. The name of its file holds only dates (or years) and the
  keys of the items (and, from v2.3.0, the size of a PNG). A picture saved is
  the person's own file, which "Forget
  the remembered settings…" does not remove. From v2.3.0 (stage X5) a PNG is
  made in the page the same way, painted from the picture, with no place or
  other data of the machine in it.
- From v2.2.0 the names of the shoes, which may be the person's own words,
  show on the view page and in a picture saved from the view by shoes (its
  window says so before saving); they are written in no file name, log, or
  setting.
- From v2.2.0 (stage T1) the names of the activities and the words of the
  conditions on them may be the person's own words. The names show only in the
  list of the activities of a period and, from v2.3.0 (stage X7), in the lists
  of the changes since the output before, and the view page writes them into no
  file. The words of the conditions show in the window of the conditions, in
  the line under the filters, and in the line at the top of the full screen,
  and go into the settings and into a picture saved (its line under the
  charts; the window says so before saving); they are never in a log, an
  answer of an error, a file name, the Support Bundle, or the text of a
  report.
- From v2.3.0 (stage X7) the view page and the normalization page read the
  output before an output for the records that changed, as they read an
  output; the answer of the view page holds the names and the values of the
  activities that changed and the names of their shoes, as the list of a
  period and the view by shoes do, and the names of the two outputs, never
  their places nor the declared keys; the normalization page gets their
  numbers only. Nothing of it is written or remembered.
- The view page (v2.1.0) writes nothing in an output. The server keeps what
  it read in memory only, under a ticket that holds no place.
- From v2.3.0 the view page also reads, only when the laps of one activity are
  asked for, the `store.json` and the one FIT file of that activity in the
  Snapshot Store that the GUI remembers (where a folder has no `store.json`,
  only whether it holds the other names that a store writes). It writes nothing
  in the store, keeps nothing of the FIT file, and its answer holds the kinds
  and the values of the laps only: no place, SHA-256, key of an activity, or
  position (see [Laps of an activity (v2.3.0)](#laps-of-an-activity-v230)).
  Only when the work laps of the shoes of a period are counted, it reads the
  `store.json` and the FIT files of the activities with shoes of that period,
  in the same way and within the limits of
  [Work laps of the shoes (v2.3.0)](#work-laps-of-the-shoes-v230); it keeps
  nothing of a FIT file or of the sums after a request, and its answers hold
  sums and counts only.
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
- Tests check that every catalog has the same keys and placeholders and that
  no key is unused. From v2.2.0 (stage U1), an English message with a whole
  number of things counted has words for a count of one (`ONE_KEYS` and
  `countKey` of `i18n.mjs`, the same Japanese), chosen by the number before it
  is written with separators, or is one that needs none, which a test lists
  with why: a count that the code never fills with 1, or words that are right
  with 1, such as a count after a label.
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
| `CONDITIONS_INVALID` | the conditions could not be read | check the words of the name, the distance, and the duration in the window of “Conditions…” |
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
- An information button of the normalization page is a disclosure. Its name
  starts with its visible word and adds what it explains, such as "About
  Timezone for local dates and times". When it opens, a hidden live region
  says the text of its explanation once, and focus stays on the button
  (stage C1).
- An information button of the view page is a disclosure too, without that
  live region: opening or closing it changes `aria-expanded` and shows or
  hides its text, so a screen reader says the state of the button, and the
  text is read where it opens, after the button. The live regions of the
  view page speak for the cross line, the list, loading, and the states of
  the page, never for an explanation that opens (this design follows the
  page in v2.2.0).
- The view page (v2.1.0) names each chart and moves its cross line with the
  keys, and a hidden live region speaks only when the keys move the line (see
  [The view page](#the-view-page-v210)). Its buttons that show only an icon
  have names, and Escape closes what the page opened.
- From v2.3.0 (stage X1) a question of a page (quitting, forgetting the
  settings, and cancelling a run) closes by Escape wherever the focus is while
  it shows, as its safe answer does: one for each Escape, the one that holds
  the focus, else the one that opened last. A part of the page that closes by
  Escape takes it first, and an Escape while a text is composed (an IME)
  closes no question (a window closes by it as before). On the view page
  Escape cancels a drag first, and graphs only, which hide the bar and a
  question left open in it, are left by it.
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
| K1–U3 (v2.2.0) | What the view page adds, in pull requests #177 to #202 and #205: the layouts, comparing years and the calendar, marks, race days, and the list of activities, the other views and the summary, saving a picture, by shoes, conditions on the activities, and the words and looks that the checks of the release candidate found |
| K4–K7 (v2.2.0) | Two release candidates on TestPyPI: 2.2.0rc1, checked on macOS and a physical Windows machine and read and used by new AI sessions, and 2.2.0rc2, with those words and looks, checked on macOS; then the documents that users read, the version 2.2.0, its publication, and its record |
| V1–W5 (v2.2.1) | Fixes after 2.2.0, in pull requests #210 to #214, #216, and #217: the guides answer a third new reader (V1); the view page opens the output again when it finds that the output changed (W1); the questions of the bar end at their buttons, and a way chosen in Compare years brings back its chart (W2); the words of the view page and the table of six years (W3); forgetting also removes the half-written files of a write (W4); `standalone` can be the first module imported (W4b); and the publish workflow checks what it builds and publishes (W5) |
| W6 (v2.2.1) | A release candidate on TestPyPI, 2.2.1rc1, checked on macOS; then the documents that users read, the version 2.2.1, its publication, and its record |

Installing a release candidate from TestPyPI used Production PyPI as an
extra index for dependencies, such as `tzdata` on Windows, that TestPyPI may
not provide. The stable release is installed from Production PyPI.

Each stage is reviewed before it is merged, and dates are not fixed.
