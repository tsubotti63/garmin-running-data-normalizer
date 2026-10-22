# GUI Guide

> **Release candidate of v2.0.0.** The GUI is in v2.0.0rc4, the release
> candidate of v2.0.0 for TestPyPI; the current stable release, v1.7.1, does
> not have it. [What you need](#what-you-need) says how to install v2.0.0rc4
> once it is published.
> With v1.7.1, use the command line as described in
> [Getting Started from Garmin Export](getting_started_from_garmin_export.md).

[日本語](gui_guide.ja.md)

The GUI normalizes a Garmin Account Data Export from a page in your web
browser. By default it keeps each Export as a Snapshot and normalizes the
Snapshots together, so that the output also holds what earlier Exports held;
it can also normalize one Export alone. It uses the same processing as the
command line: for the same input and options, it writes the same output.
Everything stays on your computer.

## What you need

- The release candidate v2.0.0rc4, installed with Python 3.11 or later. The
  GUI adds no dependency. Once v2.0.0rc4 is published on TestPyPI, install it
  in a virtual environment of its own, so that an installed v1.7.1 stays as
  it is. The line below takes the dependencies that TestPyPI may not
  provide, such as `tzdata` on Windows, from Production PyPI, so that you
  add nothing yourself.

  First install Python from [python.org](https://www.python.org/downloads/);
  this app is not checked with the Python of the Microsoft Store. To see
  whether Python 3.11 or later is installed, run `python3 --version` in the
  Terminal on macOS, or `py --version` in PowerShell on Windows. When it says
  3.10 or earlier, or that the command is not found, install Python with the
  **Download Python** button of the page of python.org. On macOS, open the
  Terminal again after you install Python.

  Then one line makes the virtual environment `garmin-normalizer` in your
  home folder, installs v2.0.0rc4 in it, makes the icon that starts the GUI
  ([Start the GUI from an icon](#start-the-gui-from-an-icon)), and opens the
  GUI. Each part runs only after the one before it has succeeded. When the
  line makes the icon, macOS may ask whether the Terminal may use the
  desktop; choose **Allow**. Keep the terminal window open while you use the
  GUI.

  macOS:

  ```bash
  python3 -m venv ~/garmin-normalizer && ~/garmin-normalizer/bin/python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ garmin-running-data-normalizer==2.0.0rc4 && ~/garmin-normalizer/bin/python -m garmin_running_data_normalizer gui --create-shortcut
  ```

  Windows PowerShell, whose version 5.1 has no `&&`, so that the parts are
  joined with `if ($?)`, one inside the other:

  ```powershell
  py -m venv "$HOME\garmin-normalizer"; if ($?) { & "$HOME\garmin-normalizer\Scripts\python.exe" -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ garmin-running-data-normalizer==2.0.0rc4; if ($?) { & "$HOME\garmin-normalizer\Scripts\python.exe" -m garmin_running_data_normalizer gui --create-shortcut } }
  ```

  - When the line succeeds, the GUI opens in your browser at its end. On the
    way, pip may say that a new release of pip is available; you need not
    mind it.
  - When the line stops on the way, with a line of an error and no page,
    read that line and set it right, and then run the same line again. When
    you ran the line before you installed Python, or when it stops at the
    same place again, first move the folder `garmin-normalizer` that it made
    in your home folder to the Trash (the Recycle Bin on Windows), and then
    run it again.
  - To update to a new version, run the line of the guide of that version in
    the same way: it installs into the same virtual environment
    `garmin-normalizer` and makes the icon again. On Windows, stop the GUI
    first ([Stop the GUI](#stop-the-gui)): while it runs, the Python of the
    virtual environment is in use, and the line may stop on the way.

  On Linux, which has no icon, leave out `--create-shortcut`. When you no
  longer use this app, see [Remove this app](#remove-this-app).

- A web browser on the same computer, in a window of a desktop or laptop
  computer. The page is not made for phones or tablets.
- A Garmin Account Data Export: the ZIP file downloaded from Garmin, or the
  folder extracted from it. **How to use** in the help panel says how to get
  one; see also steps 1 and 2 of
  [Getting Started from Garmin Export](getting_started_from_garmin_export.md).
  Garmin may take some time after your request before you can download the
  Export, so request it early.
- Free space for the Snapshot Store, which keeps a copy of the files of each
  Export (a file that an earlier Export had is kept once), and for a new
  output folder.

## Start the GUI

When the line in [What you need](#what-you-need) installed this app, it is in
that virtual environment: double-click the icon
([Start the GUI from an icon](#start-the-gui-from-an-icon)), or run this
command with the Python of the virtual environment, as the icon does.

macOS:

```bash
~/garmin-normalizer/bin/python -m garmin_running_data_normalizer gui
```

Windows PowerShell:

```powershell
& "$HOME\garmin-normalizer\Scripts\python.exe" -m garmin_running_data_normalizer gui
```

When you installed this app in another way and the command
`garmin-running-data-normalizer` works, for example in a virtual environment
that you activated, this command also starts the GUI:

```bash
garmin-running-data-normalizer gui
```

The command prints the GUI's address and opens it in your default browser.
With `--no-browser`, it only prints the address, for you to open.

- The address contains a key for this launch only. Do not share it. A page
  without the key cannot use the GUI; if the page says so, open the address
  shown in the terminal.
- Keep the terminal open while you use the GUI, and use the GUI in one tab of
  the browser.
- The page follows your browser's language. You can switch between English
  and Japanese under **Language** in the bar at the bottom of the page; the
  choice is kept for that browser tab.

The page has four boxes, numbered in the order in which you set them:
1 **This export**, 2 **Snapshots**, 3 **Output**, and 4 **Normalize**. The
line **Next:** at the top says what to do now, and the box to work on is
marked **Now**. **Use these settings** sets the second and the third box; in
the box to work on, it is filled blue, as the button to press next. A
box that is set is marked **Set** and says in one line what the run will do
with it. Under the boxes come **Colors**, the meaning of the colors of the
page, and two tables: **Steps**, the steps of a run with the time of each, and
**Results by data family**.

## Start the GUI from an icon

On macOS and Windows, `--create-shortcut` makes an icon that starts the GUI,
and then opens the GUI as the command does without it. The line in
[What you need](#what-you-need) makes the icon in this way too. To make the
icon again, for example after you replaced Python or the virtual
environment, or moved the icon to the Trash, run this command with the Python
of the virtual environment when the line installed this app.

macOS:

```bash
~/garmin-normalizer/bin/python -m garmin_running_data_normalizer gui --create-shortcut
```

Windows PowerShell:

```powershell
& "$HOME\garmin-normalizer\Scripts\python.exe" -m garmin_running_data_normalizer gui --create-shortcut
```

When the command `garmin-running-data-normalizer` works, this command also
makes it:

```bash
garmin-running-data-normalizer gui --create-shortcut
```

- macOS: the file **Garmin Running Data Normalizer.command** on the desktop,
  which shows the picture of this app, a blue tile with GR over DN, and its
  name without ".command".
  Double-click it: the Terminal opens a window, which shows the address, and
  the GUI opens in your default browser. When the command writes the file,
  macOS may ask whether the Terminal may use the desktop: choose **Allow**, or
  the icon is not made. After **Don't Allow**, macOS does not ask again: turn
  on **Desktop Folder** under **Terminal** in **Privacy & Security** >
  **Files & Folders** of System Settings, and then run the command that makes
  the icon again. Later, macOS asks the same for the folders that you choose
  from, such as Downloads, as it does when you start the GUI from the
  Terminal.
- Windows: the shortcut **Garmin Running Data Normalizer** on the desktop and
  in the Start menu, which shows the same picture. Its window opens
  minimized, in the taskbar.
- The tab of the browser shows the same picture.
- When the picture cannot be given to the icon, the command says "The picture
  of the icon could not be set; the icon still starts the GUI." and goes on:
  the icon starts the GUI with the look of a plain file.
- Keep the window that the icon opens open while you use the GUI: closing it
  stops the GUI, as closing the terminal does.
- The icon starts the Python that ran the command. After you update this app
  with pip, the icon starts the new version. After you replace Python (for
  example 3.13 with 3.14) or the virtual environment, run the command again to
  make the icon again. The icon holds no key: each launch makes its own.
- The command replaces only an icon that it made. Another file of the same
  name stops it with `SHORTCUT_PLACE_TAKEN`; an icon that cannot be made stops
  it with `SHORTCUT_NOT_CREATED`, and other systems with
  `SHORTCUT_NOT_SUPPORTED`. The GUI does not open then; without
  `--create-shortcut`, the command opens it.
- When your desktop is synchronized with iCloud or OneDrive, the icon also
  appears on your other computers, where it may not start, because Python is
  in another place there, and may come without its picture.
- To remove the icon, move it to the Trash (the Recycle Bin on Windows, also
  the one in the Start menu: [Remove this app](#remove-this-app)).
  `pip uninstall` does not remove it.
- Linux has no icon: start the GUI with the command.

## Box 1: This export

1. Choose **Choose ZIP file…** for the ZIP file downloaded from Garmin, or
   **Choose extracted folder…** for the folder that you extracted from it.
   The ZIP file can be used as it is, without extracting it. The system's
   own dialog opens. When the system has no such dialog, a list on the page
   opens instead: it shows folders and ZIP files, but no hidden items or
   links. Press a folder to open it, and press a ZIP file, or
   **Use this folder**, to choose it.
2. The page checks what you chose right away, as the `doctor --input`
   command does. It shows first, in red, what keeps a run from starting;
   then, in yellow, notes that do not, such as files that cannot be read and
   are left out; and then, in green, that the export can be normalized, with
   the numbers of Activities and FIT files. A large export can take a while
   to check. Which kinds of data the export holds is known only after a run:
   **Results by data family** shows them.
3. For an extracted folder, check that the extraction finished, and tick
   **I checked that the ZIP file was extracted completely and that nothing is missing**.
   If the extraction stopped partway, files are missing and the results
   change. A ZIP file needs no such check: the page checks that it is
   complete and not damaged.

You can also paste the full path in **Place of the Garmin export** and choose
**Check the export**; the spaces around a pasted place are left out. Changing
the place clears the check, so check again before you start.

When the folder that you chose holds more than one Export, or the Exports of
more than one account, the page names each one by its place in the folder,
counting the same Export once, with a button to choose each one, and checks
the one that you choose.

When the second box imports into the Snapshots, as it does by default, this
box also asks for two values of the import:

- **Name of the Snapshot**: the date of the download by default, with `-2`,
  `-3`, and so on when the store has that name already. It takes up to 64
  letters, digits, dots, underscores, or hyphens, starting with a letter or a
  digit, and no Japanese.
- **Download time**: filled in from the time of the ZIP file, or for an
  extracted folder from its newest file, which is near the time when the
  export was made; the line under it says which. It is in the local time of
  this computer, such as `2030-01-01 02:00`. The Snapshots are in the order of
  these times, so change it only when its place among the other Snapshots is
  not the real one.

The page checks both before the run can start. They are for the next import:
once a run has finished, they are hidden until you change something, and
they show again, with the reason, while the name or the time keeps a run from
starting.

When the store holds Snapshots, **Normalize the existing Snapshots again** at
the foot of the box normalizes them again without an export, for example
with a new version of this app or with other settings of the output. The box
then takes no export; **Choose an export instead** goes back.

## Box 2: Snapshots

A Snapshot is a copy of one export, and the Snapshot Store is the folder that
keeps the Snapshots. Every normalization with the Snapshots uses all the
Snapshots in the store together, so that the output includes what earlier
exports held; none can be left out.

**How to normalize** has two choices:

- **Import into the Snapshots and normalize them together (recommended)**:
  copies this export into the store, then normalizes it together with the
  existing Snapshots.
- **Normalize this export only (no import)**: normalizes this export alone,
  without the store. The parts of the store turn gray. When there is no store
  yet, they still say "It is created here when you normalize.", but this
  way creates no store.

The third way, normalizing the existing Snapshots again, is chosen in the
first box.

**Snapshot Store** is the folder `snapshots` in `GarminRunningData` in your
home folder by default. At a first launch, the page opens the store there,
or says that there is none yet and that it is created there when you
normalize.

- **Open a store in use…** opens a store that you use already, such as one
  made with the command line, or the store in the folder `snapshots` of the
  folder that you choose.
- **Choose where to create it…** chooses the folder in which a new store is
  made, as its folder `snapshots`, or the chosen folder itself when it is
  named `snapshots`; a store that is there already is opened instead. Nothing
  is made until a run imports an export into it.
- Once a store is open, **Open another store…** and **Create a new store…** do
  the same, and **Check the Snapshots** checks the store as the
  `snapshot verify` command does.

Each button opens the system's dialog for a folder, or the page's own folder
list without one. A store in a folder that a cloud may copy, such as iCloud
Drive, OneDrive, or the Documents and the Desktop of a Mac, is marked in
yellow.

The list of the Snapshots shows all of them as the run will use them, in the
order of the times of their exports, with the number of files of each. The
export that the run will import stands in its place as **To import now**, and
after the run as **Imported now**; the others are **Imported**. If the export
has the same content as a Snapshot in the store, the import finds that out and
adds no new Snapshot, and the result says which Snapshot it is.

Press **Use these settings** to set the box.

The store holds your personal data. This app never changes the files of an
imported Snapshot, and never deletes them by itself. Keep the store on this
computer, in a place that only you can read, and back it up with Time Machine
or the like: check it with **Check the Snapshots** before you back it up, and
again after you restore it.

When an import stopped before it ended, for example because the computer was
turned off, the store keeps its lock file, `.single-writer.lock`, and the next
import stops with `SNAPSHOT_STORE_LOCKED`. The box says how long ago the lock
file was made: one made less than a minute ago may belong to an import that is
running. If no other normalization or snapshot command is running, in a
terminal or in another tab, tick
**I checked that no other normalization or snapshot command is running** and
press **Remove the lock file**. Only that file is removed, and the Snapshots
stay; press **Run normalization** to import again.

On Windows, keep the place of the store short. Unless long paths are enabled,
Windows limits a whole path to 260 characters, and the files inside the store
add about 190 characters to the path of the store, so that the path of the
store can have about 70 characters at most. The page checks this when you
choose where to create a store and before an import, and stops with
`SNAPSHOT_STORE_PATH_TOO_LONG`, as the command line's `snapshot init` and
`snapshot register` do; for a store that is open already, the box says so in
red when it would import. The default place is usually short enough.

## Box 3: Output

- **Where to create the output**: `GarminRunningData` in your home folder
  by default; if it is not there, it is made when you normalize. Each output
  is a new folder in it. **Choose…** picks another folder, with the system's
  dialog for a folder, or a list of folder names when there is none. Any
  other folder must exist, and this app must be able to write in it; the GUI
  checks this before the run starts. A folder that a cloud may copy is marked
  in yellow, as for the store.
- **Name of the new folder**: proposed as
  `garmin-run-all-YYYYMMDD-HHMM` in local time, with `-2`, `-3`, and so on
  when a folder of that name is there already. Use a name that does not exist
  yet, with up to 200 letters and digits or 66 Japanese characters. It must
  not start with a dot or contain characters such as `/` or `:`. A name that
  you type and that is there already is shown in red before the run starts.
- **Timezone for local dates and times**: `Asia/Tokyo` by default. Use an
  IANA name such as `Europe/London`. One normalization gives all dates and
  times in one timezone, so records made while travelling are not in the
  local time of that place, and another timezone can move the day of records
  that span midnight, such as sleep. To compare with an earlier output, use
  the same timezone.
- **Also create a summary that can be given to an AI (dates to the month, distance, time, and so on)**:
  off by default. It is the External-safe Pack of the command line's
  `--external-safe-pack`: one ZIP file, `analysis/external_safe_handoff.zip`
  in the output folder, with a table of one row per activity and six
  columns, the month, the activity type, the sport type, the distance, the
  duration, and the number of laps. **What is in it** lists what is in it and
  what is not. Review it before you share it. After the run, the box names
  the file that the run made, and **Show where it is saved** shows it in its
  folder.

Press **Use these settings** to set the box.

On Windows, keep the location and the name short. Unless long paths are
enabled, Windows limits a whole path to 260 characters, and the files inside
the output add about 40 characters to the path of the output folder. If the
paths would be too long, the GUI says so before the run starts.

The output folder appears only when the run finishes. Until then, Run-All
works in a hidden working folder next to it.

## Box 4: Normalize

**Run normalization** can be pressed once the boxes before it are set; until
then, a line under it names the boxes that are left. Only one run can be
active at a time.

- The box shows the current step and its number, and the elapsed time;
  **Steps** shows the time of each step. While FIT files are read, a bar
  shows how many have been read; files with the same content are read once.
  If nothing changes for 30 seconds, a note says so. Large exports can take
  a while, and you can keep waiting.
- Keep the terminal open. If you close the window, the run goes on; open the
  same address again to see it. While the computer sleeps, the run does not
  progress.
- **Cancel** asks first, in the box: **Cancel the normalization** or
  **Continue**. A run that is cancelled before it finishes creates no output
  folder, and an import that was under way is completed by the next import.
  If the run finished just before the cancellation took effect, the output is
  kept, and the page says so: read `START_HERE.md` before you use it, or
  delete the output folder if you do not need it; it is not deleted
  automatically.
- If a forced stop leaves a hidden working folder (`.<name>.run-all-…`) in the
  output location, the page shows its name. Delete it after checking that no
  run is active.

The headline of the box says how the run ended, with the exit code that the
command line returns for the same result under it; **Meaning** explains the
code.

| Result | Exit code | Meaning |
|---|---|---|
| `PASS` | 0 | **Normalized**: finished without warnings |
| `PASS_WITH_WARNINGS` | 0 | **Normalized**: finished; the output can be used after you review the warnings |
| `PARTIAL_SUCCESS` | 3 | **Normalized with part of the input left out**, such as files that could not be read or rows without a required value; the output can be used |
| Stopped | 2 | **Could not normalize**: no output folder was created; the box with the problem says why and what to do next |

When the run imported, the box also says where the export came in the order
of the Snapshots, or that the store held the same export already, so that no
Snapshot was added. A run that stops after its import keeps the import: when
you press **Run normalization** again, the same export is normalized without
a new Snapshot.

**Results by data family** lists each kind of data with its record count, its
status, and its warnings, then the warnings that belong to no kind, and the
total of the warnings. Yellow rows are warnings. Of the families shown as
**Not in the export**, Gear, Personal records, and FIT files add a warning; the
daily records, such as Sleep, HRV, and VO2 max, are often not in an export, so
they add none.

**Output check** runs by itself after the run, under **Steps**, with the same
checks as the `validate-handoff` and `doctor --run-output` commands. It
shows:

- the handoff check, with the number of datasets and links between datasets;
- whether the output can be used, and the next step;
- the warnings of the run: their total, and each warning with the data that
  it concerns, its count, and its code.

Under **Next**, **Show the output folder** shows the folder in Finder on
macOS, in File Explorer on Windows, and with the file manager that
`xdg-open` chooses on Linux. **Open START_HERE.md** opens the file with the
default application for `.md` files. Start with `START_HERE.md`; it explains
the output, what was left out, and the warnings.
**Use the normalized data with AI** opens the part of the help panel about
using the output with an AI.

After a run, the page proposes a new name for the next one.

## Later launches

From the second launch on, the GUI uses the settings that it remembered.

- Once the first box has checked the export, the second box is set by
  itself if the store that the GUI remembered opens without a problem, and
  then the third box if the folder for the output that it remembered is
  there or is the default place: the boxes are set in their order. Their
  summaries end with "(as last time)". If you change a box, for example by
  opening another store, press **Use these settings** in it again before the
  run. Without a remembered store, the second box asks to be set as on a
  first launch, so that no store is made unseen.
- **Show tips** is off, until you switch it; the GUI remembers your choice.
- Before you normalize, **Results by data family** shows the counts of the
  output before. After the run, the column **Since the output before** shows
  the change of each kind of data, and the fourth box says how many
  activities more or fewer there are. The change shows only when both
  outputs were normalized the same way (Snapshots, or this export alone), by
  the same version of this app, and with the same timezone; otherwise a line
  says what differs. It is the change when both were normalized from the same
  Snapshot Store, which an output does not record.

The GUI remembers the places of the Snapshot Store, of the folder for the
output, and of the outputs that runs made (the latest 10), and whether
**Show tips** is on. Only the names of the places are kept, never what is in
them, and never the place of an export; the name of the output, the timezone,
the language, and the way to normalize are not remembered. The places are
remembered when a run makes its output, so that a place opened by mistake
does not come back. The file is `gui-settings.json` in the folder
`garmin-running-data-normalizer` of this app: in `Library/Application Support`
in your home folder on a Mac, in `LOCALAPPDATA` on Windows, and in
`XDG_STATE_HOME`, or `.local/state` in your home folder, on Linux.

When a remembered place is not found, for example because it was moved or
its external disk is disconnected, its box turns red. The second box offers
**Open another store…**, **Look again**, and **Create a new store…**, and the
third box **Choose…** and **Look again**. Neither place is made again, except
the default folder `GarminRunningData` for the output.

**Forget the remembered settings…** in the bar at the bottom asks first, and
then removes the file of the settings only, never while a run is active. It
can be pressed only while there are remembered settings. The
store and the outputs stay, and the next launch goes as a first launch; a
store that is not in the default place must then be opened again. When the
file cannot be read, the bar says so, and the launch goes as a first one.

## If something is wrong

**If something is wrong** is the last part of the fourth box. It is folded to
one line until you press it, and holds **Open “Questions” in Help**, the
check of an output, the Support Bundle, and the report on GitHub. For the red
boxes of a stop, see [When something goes wrong](#when-something-goes-wrong).

**Output to check** chooses the output of the check and of the Support
Bundle: **The output of this run**, or **An earlier output** from the list of
the outputs that the GUI remembers and that are still there, newest first, or
another folder with **Choose another output…** at the end of the list.
**Check the output** checks it as **Output check** does. An output that a
version before 1.4 made has none of the diagnostics of this version: use the
result in its `START_HERE.md`. An output that another version made cannot be
checked by this version; normalize again with this version.

**Make the Support Bundle** writes
`<output name>-support-bundle.zip`, as the `support-bundle` command does.
**Where the Support Bundle is saved** is next to the output folder by
default; **Choose…** picks another folder, which must exist and be outside
the output folder. The page shows the file and its place before you press
the button.

- It holds six summary files. It contains no rows of your records, paths, file
  names, identifiers, exact times, or coordinates. Nothing is uploaded.
- Review all six files before you share it. The counts in it can still show
  how much you use your device.
- An existing file with the same name is never replaced. Move or rename it,
  or choose another place.
- **Show where it is saved** shows the bundle in Finder on macOS and in File
  Explorer on Windows, and opens its folder with the file manager that
  `xdg-open` chooses on Linux.

For what the bundle contains, see
[v1.4 Export Evidence and Diagnostics](v1_4_diagnostics.md#support-bundle).
For where to ask, see [Support](../SUPPORT.md).

### Report a problem on GitHub

If the next step does not solve it, press **report it on GitHub** in the line
that ends the explanation of a stop, after the buttons that fix it, or
**Report on GitHub…** at the end of **If something is wrong**. Either opens
**If something is wrong** in the help panel with the values that go in the Bug
report form of the repository first: the title with the code, the part of the
page, the operating system and its version, the version of Python, the line
that `--version` prints, how this launch normalizes, the exit code, and the
code. No paths, names, counts, dates, times, or timezone go in.
**Open on GitHub** opens the form in a new tab of the browser; the values
reach GitHub then, and they are public only when you submit the report. If
you are not signed in to GitHub, its sign-in page comes first. Write what
happened yourself, choose whether the synthetic data shows the problem, and
tick the four checks that no personal data is in it. Do not attach any file.
Tell a vulnerability through the private channel instead, as
[Security](../SECURITY.md) says.

The help panel also links to the guides and other documents of the
repository at the tag of this version, and to the data management page of
Garmin. A link opens in a new tab only when you press it. In development,
the version keeps the name of the last release, whose tag has no GUI guide,
so the links to this guide open once v2.0.0 is released.

## Help and tips

**Help** at the top right opens the help panel at the right of the window. It
pushes the page aside instead of covering it, and has five parts:

- **How to use**: how to get the export from Garmin, and the four boxes;
  press a step to light up its box. It links to this guide and to
  Getting Started from Garmin Export.
- **Questions**: answers to common questions, such as whether the ZIP file
  can be used as it is, what this app remembers, and why a date can be one
  day off from Garmin Connect.
- **Words**: what normalization, a Snapshot, the Snapshot Store, and the
  other words of the page mean.
- **Use with AI**: how to use the output with an AI, with example questions
  that **Copy** copies: for this computer or an AI you trust, and one for an
  outside AI with the summary that can be given to an AI.
- **If something is wrong**: the report on GitHub, as above.

**Close** or Escape closes the panel.

**Show tips** at the top shows one line of tips under the heading of each
box. It is on at a first launch and off at later launches, until you switch
it; the GUI remembers your choice.

An information button next to what it explains, **About**,
**What is in it**, or **Meaning**, opens the explanation under it. It is at
how to normalize, the Snapshot Store, the place of the output, the timezone,
the summary for an AI, the exit code, and **If something is wrong**. The
explanation stays open until you press the button again or press Escape;
nothing opens when you only point at it. With a screen reader, the
explanation is read once when it opens, and focus stays on the button.

**Colors** under the boxes gives the five colors of the page: blue is what to
do now, or a task that is running; green is done or set; yellow is a warning,
which can be used but should be checked; red is a problem to fix; and gray is
absent or not yet, which is not a problem. Color is never the only sign: the
page says it in words too.

## When something goes wrong

When the page cannot go on, the box with the problem turns red and says what
happened, what to do next, and a code, and the line **Next:** points at that
box. A run that stops creates no output folder. Quote the code when you ask
for help. Do not attach your export or output. The table follows the boxes,
from the first to the fourth, and then **If something is wrong**.

| Code | What happened | What to do |
|---|---|---|
| `PATH_NOT_ABSOLUTE` | The place is not a full path. | Choose it with a button that says Choose, or paste a place that starts with / on a Mac or Linux, or with a drive such as C:\\ on Windows. |
| `FOLDER_NOT_READABLE` | This app is not allowed to open this folder. | On a Mac, allow it when you are asked, or in System Settings > Privacy & Security. |
| `CHOOSER_BUSY` | Another dialog to choose is open. | Choose in it or close it, and press the button again. |
| `INPUT_ZIP_CORRUPT` | The Export ZIP file is damaged or incomplete. | Download the Export ZIP file again; if it is damaged again, request a new Export from Garmin. |
| `INPUT_MULTIPLE_EXPORTS` | The input holds more than one Export, or Exports of more than one account. | Select one Export to normalize. |
| `ACTIVITIES_NOT_FOUND` | The input holds no Activities file. | Select an Export that contains your Activities. |
| `INPUT_CHANGED` | The input changed while it was read. | Press Run normalization again when no other app changes the Export. |
| `SNAPSHOT_LABEL_EXISTS` | Another Snapshot in the store has this name. | Change the name of the Snapshot. |
| `SNAPSHOT_STORE_NOT_FOUND` | There is no Snapshot Store in the chosen folder. | Choose the folder of the store, or choose where to create a new one. |
| `SNAPSHOT_STORE_LOCKED` | The Snapshot Store has a lock file (.single-writer.lock): an import is running, or one stopped before it ended. | If no other normalization or snapshot command is running, check the box below and press Remove the lock file; only that file is removed, and the Snapshots stay. |
| `SNAPSHOT_STORE_PATH_TOO_LONG` | The paths inside the Snapshot Store would be too long for this computer. | Choose a store in a shorter folder, or on Windows turn on long paths. |
| `OUTPUT_EXISTS` | The output folder is there already. | Choose another name for the output. |
| `OUTPUT_NAME_INVALID` | The output folder name is too long or cannot be used on every system. | Choose a name of at most 200 bytes that does not start with a dot, end with a dot or a space, hold any of <>:"/\\\|?*, or name a device of Windows. |
| `OUTPUT_PARENT_NOT_WRITABLE` | This app cannot write in the folder for the output. | Choose another folder, or allow this app to write in it. |
| `OUTPUT_PATH_TOO_LONG` | The output path is too long. | Choose a shorter folder or name, or on Windows turn on long paths. |
| `TIMEZONE_INVALID` | The timezone is not an exact IANA timezone name. | Give an exact IANA timezone name, such as Asia/Tokyo or America/New_York. |
| `RUN_ACTIVE` | A normalization is running in another tab or window. | Wait for it to finish, or cancel it. |
| `OUTPUT_PUBLISH_FAILED` | The output could not be written. | Check the free space and the permissions of the folder for the output, and press Run normalization again. |
| `COMMAND_FAILED` | This app stopped unexpectedly while it did this. | Press the button again; if it stops again, please report the code. |
| `HANDOFF_INVALID` | The folder is not the output of a normalization, or the files of the output do not pass their checks. | Choose the folder of an output; if it is one, do not change its files, and normalize again into a new folder. |
| `OUTPUT_OTHER_VERSION` | The output was made by another version of this app, which this version cannot check. | Normalize again with this version into a new folder. |
| `SUPPORT_BUNDLE_EXISTS` | A file or a link is there already in the place of the Support Bundle. | Move or rename it, or choose another place, and press the button again. |

For other codes, follow the next step on the page. If it does not solve the
problem, see [Report a problem on GitHub](#report-a-problem-on-github).

A mix of Exports is told where it is: a mix in the input in the first box,
and in the second box an export of another account than the Snapshots of the
store, or a store that holds the Exports of more than one account, each with a
next step of its own.

Use the GUI in one tab. Only one dialog to choose can be open at a time, for
all tabs: when another tab, or this page before you loaded it again, has one
open, the page says `CHOOSER_BUSY`; close that dialog and press the button
again. When two tabs choose at the same time, one of them can get no answer,
as if nothing was chosen; press its button again. A run that another tab
started shows in every tab, and another run cannot start until it ends
(`RUN_ACTIVE`).

If the page says that this app is not responding, the GUI may have stopped, for
example because the terminal window was closed, or because nothing used it for
10 minutes. When the icon started it, double-click the icon again; when you
started it in the terminal, start it again with the same command; then open
the new address. Each launch has a new address and key.

## Stop the GUI

While you use the GUI, the terminal window (the window that the icon opened,
when the icon started the GUI) shows the address and seems to stand still.
That is as it should be.

- Choose **Quit** at the bottom of the page, or press `Ctrl+C` in the
  terminal. When the icon started the GUI, its window is the terminal. When
  the GUI stops, the terminal shows "GUI stopped."; you may then close the
  window.
- While a run is active, **Quit** is refused; cancel the run first. `Ctrl+C`
  cancels the run and then stops the GUI.
- The `gui` command ends with exit code 0 after **Quit**, or after `Ctrl+C`
  when no run is active. When `Ctrl+C` cancels a run, the terminal shows what
  the command line shows for a cancelled command, and the code is 130. A
  second `Ctrl+C` while the GUI stops a run does nothing; the GUI stops once
  the run has ended.
- When no page has used the GUI for 10 minutes and no run is active, the GUI
  stops by itself. Closing the browser tab does not stop it at once.

## Remove this app

When you no longer use this version, stop the GUI, and then move these to the
Trash (the Recycle Bin on Windows):

- The folder `garmin-normalizer` in your home folder: the virtual environment
  that the line in [What you need](#what-you-need) made. This app is in it.
- The icon: on macOS, **Garmin Running Data Normalizer** on the desktop; on
  Windows, the shortcuts **Garmin Running Data Normalizer** on the desktop
  and in the Start menu. The one in the Start menu is in the folder that
  opens when you type `shell:programs` in the address bar of File Explorer.
- The Snapshot Store and the outputs, by default in `GarminRunningData` in
  your home folder: they hold your personal data and the copies of your
  Exports. Keep them while you still use them.
- Before you stop the GUI, **Forget the remembered settings…** in the bar at
  the bottom of the page removes what the GUI remembers. The place of its
  file is in [Later launches](#later-launches).

When you installed this app in another way,
`pip uninstall garmin-running-data-normalizer` removes it. That does not
remove the icon.

## Privacy

- Run-All output and the Snapshot Store contain your personal data. They stay
  on this computer unless you share them.
- The GUI sends nothing over the network by itself. It has no analytics,
  and the page loads nothing from outside the GUI. A link of the help panel
  opens a page in a new tab only when you press it, and **Open on GitHub**
  gives GitHub only the values that the page shows you first.
- The External-safe Pack and the Support Bundle are made for sharing, but
  review them before you do. The names of your Snapshots are never in them.
- The remembered settings hold the names of places only, stay on this
  computer, and are never in the Support Bundle. On a computer that others
  use, remove them with **Forget the remembered settings…**.

See [Security and Privacy Boundary](security_and_privacy_boundary.md).

## How the GUI is protected

- It listens on `127.0.0.1` only, so other computers cannot connect.
- Every request needs the key from this launch's address. Other programs and
  other accounts on the same computer cannot use the GUI without it.
- It uses no cookies, and it does not log requests or paths.

## Keyboard and screen readers

- Every control can be used with the keyboard, and the focus is always
  visible.
- Screen readers announce the stage of a run, a stalled run, a cancellation,
  and the end. Counts that change every second are not read out.
- When you set a box, the focus moves to the next box. When a run ends, the
  focus moves to the result heading, or when it stops, to the heading of the
  stop in its box, unless you have moved to another part of the page.
- The help panel stands beside the page; it is not a dialog. Opening it, or
  one of its parts, moves the focus to its heading, and Escape inside it
  closes it.

## The GUI and the command line

The GUI runs the same processing as the command line. For this export only,
it is the same as this command:

```bash
garmin-running-data-normalizer run-all --input /path/to/export --output /path/to/new-output --timezone Asia/Tokyo
```

To import the export into the Snapshots and normalize them together:

```bash
garmin-running-data-normalizer snapshot register --store /path/to/store --input /path/to/export --label 2030-01-01 --requested-at 2030-01-01T02:00:00+00:00 --downloaded-at 2030-01-01T02:00:00+00:00 --observed-at 2030-01-01T02:00:00+00:00 --confirm-complete
garmin-running-data-normalizer snapshot run-all --store /path/to/store --output /path/to/new-output --timezone Asia/Tokyo
```

Normalizing the existing Snapshots again runs the second command alone. With
the summary for an AI, each run adds `--external-safe-pack`.

The page gives the download time as all three times of the export,
`--requested-at`, `--downloaded-at`, and `--observed-at`. The command line
takes each of them, so one store can hold Snapshots that the command line
imported with the time when the export was requested from Garmin, and
Snapshots that the page imported with the time of the download. The
Snapshots are in the order of their times of `--observed-at`, which are the
download times for those that the page imported. The page also checks the
name of the Snapshot before it reads the export, and stops for a name that
the store has; the command line reads the export first, and an export that
the store holds already adds no Snapshot, under any name.

A store that the page made can be used with the command line as it is,
without `snapshot init`. The page reads a store as these commands do, and
removes its lock file as `snapshot unlock` does:

```bash
garmin-running-data-normalizer snapshot status --store /path/to/store
garmin-running-data-normalizer snapshot verify --store /path/to/store
garmin-running-data-normalizer snapshot unlock --store /path/to/store --confirm-no-other-command
```

The check of the export, the output check, and the Support Bundle are these
commands:

```bash
garmin-running-data-normalizer doctor --input /path/to/export
garmin-running-data-normalizer validate-handoff --input /path/to/output
garmin-running-data-normalizer doctor --run-output /path/to/output
garmin-running-data-normalizer support-bundle --run-output /path/to/output --output /path/to/support-bundle.zip
```

The command line takes every place as an argument and has no default place.
It remembers nothing between commands and shows no change since an earlier
output; the `run_summary.json` of each output holds its counts. Use it for
automation.
