# GUI Guide

> **In development for v2.0.0.** The GUI is not part of the current stable
> release, v1.7.1, and the `gui` command is not available yet. It is planned
> for the v2.0.0 release candidate on TestPyPI. Until then, use the command
> line as described in
> [Getting Started from Garmin Export](getting_started_from_garmin_export.md).
>
> The page described here is being rebuilt as one page with Snapshots and ZIP
> input, following the revised [v2.0.0 GUI Design](gui_design.md). This guide
> will be rewritten with it.

[日本語](gui_guide.ja.md)

The GUI runs the one-shot Run-All on a Garmin Account Data Export from a page
in your web browser. It uses the same processing as the command line: for the
same input and options, it writes the same output. Everything stays on your
computer.

## What you need

- The package installed with Python 3.11 or later. The GUI adds no
  dependency.
- A web browser on the same computer.
- A Garmin Account Data Export: the ZIP file downloaded from Garmin, or the
  folder extracted from it. See steps 1 and 2 of
  [Getting Started from Garmin Export](getting_started_from_garmin_export.md).
- Free space for a new output folder.

## Start the GUI

```bash
garmin-running-data-normalizer gui
```

The command prints the GUI's address and opens it in your default browser.

- The address contains a key for this launch only. Do not share it. A page
  without the key cannot use the GUI; if the page says so, open the address
  shown in the terminal.
- Keep the terminal open while you use the GUI.
- The page follows your browser's language. You can switch between English
  and Japanese under **Language** at the bottom of the page; the choice is
  kept for that browser tab.

## 1. Choose the export

1. Choose **Choose ZIP file…** for the ZIP file downloaded from Garmin, or
   **Choose extracted folder…** for the folder that you extracted from it.
   The system's own dialog opens. When the system has no such dialog, a list
   on the page opens instead; it shows folders and ZIP files, but no hidden
   items or links.
2. The page checks what you chose right away. This is the same check as the
   `doctor --input` command. It says whether the export can be normalized,
   how many Activities and FIT files it holds, and what to do next if it
   cannot. A large Export can take a while to check.
3. For an extracted folder, check that the extraction finished, and tick
   **I checked that the ZIP file was extracted completely and that nothing is missing**.
   If the extraction stopped partway, files are missing and the results
   change. A ZIP file needs no such check.

You can also paste the full path in **Place of the Garmin export** and choose
**Check the export**; the spaces around a pasted place are left out. Changing
the place clears the check, so check again before you start. The timezone is
checked when the run starts.

## 2. Choose the output

- **Where to create the output**: `GarminRunningData` in your home folder
  by default; if it is not there, it is made when you normalize. You can
  also pick a folder with **Choose…**, which opens the system's dialog for a
  folder, or a list of folder names when there is none. Any other folder
  must exist, and you must be able to write to it; the GUI checks this before
  the run starts. A folder that a cloud may copy, such as iCloud Drive,
  OneDrive, or the Documents and the Desktop of a Mac, is marked in yellow.
- **Name of the new folder**: proposed as
  `garmin-run-all-YYYYMMDD-HHMM` in local time, with `-2`, `-3`, and so on
  when a folder of that name is there already. Use a name that does not exist
  yet, with up to 200 letters and digits or 66 Japanese characters. It must
  not start with a dot or contain characters such as `/` or `:`. A name that
  you type and that is there already is shown in red before the run starts.
- **Timezone for local dates and times**: `Asia/Tokyo` by default. Use an
  IANA name such as `Europe/London`.
- **Also create a summary that can be given to an AI (dates to the month, distance, time, and so on)**:
  off by default. It is the same Activities-only pack, the External-safe Pack,
  as the command line's `--external-safe-pack`. Review it
  before you share it. After the run, the box names the file that the run
  made, and **Show where it is saved** shows it in its folder.

On Windows, keep the location and the name short. Unless long paths are
enabled, Windows limits a whole path to 260 characters, and the files inside
the output add about 40 characters to the path of the output folder. If the
paths would be too long, the GUI says so before the run starts.

The output folder appears only when the run finishes. Until then, Run-All
works in a hidden working folder next to it.

## 3. Run

- Choose **Run normalization**. Only one run can be active at a time.
- The page shows the stage of the run and the elapsed time. While FIT files
  are read, it shows how many have been read; files with the same content are
  read once. If nothing changes for 30 seconds, a note says so. Large Exports
  can take a while, and you can keep waiting.
- **Cancel** asks for confirmation. A run that is cancelled before it
  finishes creates no output folder. If the run finished just before the
  cancellation took effect, the output is kept, and the page says so.
- If a forced stop leaves a hidden working folder (`.<name>.run-all-…`) in the
  output location, the page shows its name. Delete it after checking that no
  run is active.

## 4. Read the result

The result says how the run ended, with the exit code that the command line
returns for the same result:

| Result | Exit code | Meaning |
|---|---|---|
| `PASS` | 0 | Finished without warnings |
| `PASS_WITH_WARNINGS` | 0 | Finished; the output can be used after you review the warnings |
| `PARTIAL_SUCCESS` | 3 | Normalized with part of the input left out, such as files that could not be read or rows without a required value; the output can be used |

A table lists each data family with its status, record count, and warnings,
then the warnings that belong to no family, and the total of the warnings.
From the second launch on, before you normalize, the table shows the counts
of the output before; after the run, the column **Since the output before**
shows the change of each family, and the fourth box says how many activities
more or fewer there are. The change shows only when both outputs were
normalized the same way (Snapshots, or this export alone), by the same
version of this app, and with the same timezone; otherwise a line says what
differs.

**Output check** runs by itself after the run, with the same checks as the
`validate-handoff` and `doctor --run-output` commands. It shows:

- the handoff check, with the number of datasets and links between datasets;
- whether the output can be used, and the next step;
- the warnings of the run: their total, and each warning with the data that
  it concerns, its count, and its code.

**Show the output folder** shows the folder in Finder on macOS, in File
Explorer on Windows, and with the file manager that `xdg-open` chooses on
Linux. **Open START_HERE.md** opens the file with the default application for
`.md` files. Start with `START_HERE.md`; it explains the output.

After a run, the page proposes a new name for the next one.

## 5. Make a Support Bundle when you need help

Under **If something is wrong**, **Output to check** chooses the output of
the check and of the Support Bundle: **The output of this run**, or
**An earlier output** from the list of the outputs that you made before, or
another folder with **Choose another output…**. **Check the output** checks
it as **Output check** does. An output that a version before 1.4 made has
none of the diagnostics of this version: use the result in its
`START_HERE.md`. An output that another version made cannot be checked by
this version; normalize again with this version.

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

## When something goes wrong

Every problem is shown as what happened, what to do next, and a code. Quote
the code when you ask for help. Do not attach your Export or output.

| Code | What happened | What to do |
|---|---|---|
| `PATH_NOT_ABSOLUTE` | The place is not a full path. | Choose it with a button that says Choose, or paste a place that starts with / on a Mac or Linux, or with a drive such as C:\\ on Windows. |
| `FOLDER_NOT_READABLE` | This app is not allowed to open this folder. | On a Mac, allow it when you are asked, or in System Settings > Privacy & Security. |
| `ACTIVITIES_NOT_FOUND` | The input holds no Activities file. | Select an Export that contains your Activities. |
| `OUTPUT_EXISTS` | The output folder is there already. | Choose another name for the output. |
| `OUTPUT_NAME_INVALID` | The output folder name is too long or cannot be used on every system. | Choose a name of at most 200 bytes that does not start with a dot, end with a dot or a space, hold any of <>:"/\\\|?*, or name a device of Windows. |
| `OUTPUT_PARENT_NOT_WRITABLE` | This app cannot write in the folder for the output. | Choose another folder, or allow this app to write in it. |
| `OUTPUT_PATH_TOO_LONG` | The output path is too long. | Choose a shorter folder or name, or on Windows turn on long paths. |
| `INPUT_CHANGED` | The input changed while it was read. | Press Run normalization again when no other app changes the Export. |
| `OUTPUT_PUBLISH_FAILED` | The output could not be written. | Check the free space and the permissions of the folder for the output, and press Run normalization again. |
| `HANDOFF_INVALID` | The folder is not the output of a normalization, or the files of the output do not pass their checks. | Choose the folder of an output; if it is one, do not change its files, and normalize again into a new folder. |
| `OUTPUT_OTHER_VERSION` | The output was made by another version of this app, which this version cannot check. | Normalize again with this version into a new folder. |
| `SUPPORT_BUNDLE_EXISTS` | A file or a link is there already in the place of the Support Bundle. | Move or rename it, or choose another place, and press the button again. |

For other codes, follow the next step on the page.

If the page says that this app is not responding, the GUI may have stopped, for
example because the terminal was closed. Start it again with the same command
and open the new address; each launch has a new address and key.

## Stop the GUI

- Choose **Quit** at the bottom of the page, or press `Ctrl+C` in the
  terminal.
- While a run is active, **Quit** is refused; cancel the run first. `Ctrl+C`
  cancels the run and then stops the GUI.
- When no page has used the GUI for 10 minutes and no run is active, the GUI
  stops by itself. Closing the browser tab does not stop it at once.

## Privacy

- Run-All output contains your personal data. It stays on this computer
  unless you share it.
- The GUI sends nothing over the network. It has no analytics, and the page
  loads nothing from outside the GUI.
- The External-safe Pack and the Support Bundle are made for sharing, but
  review them before you do.

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
- When a run ends, the focus moves to the result heading, unless you have
  moved to another part of the page.

## The GUI and the command line

The GUI runs the same Run-All as this command:

```bash
garmin-running-data-normalizer run-all --input /path/to/export --output /path/to/new-output --timezone Asia/Tokyo
```

When it imports the Export into the Snapshots, it runs the same as these
commands, with the time of the download as each time of the Export:

```bash
garmin-running-data-normalizer snapshot register --store /path/to/store --input /path/to/export --label 2030-01-01 --requested-at 2030-01-01T02:00:00+00:00 --downloaded-at 2030-01-01T02:00:00+00:00 --observed-at 2030-01-01T02:00:00+00:00 --confirm-complete
garmin-running-data-normalizer snapshot run-all --store /path/to/store --output /path/to/new-output --timezone Asia/Tokyo
```

Use the command line for automation and to check an output that was made
earlier:

```bash
garmin-running-data-normalizer validate-handoff --input /path/to/output
garmin-running-data-normalizer doctor --run-output /path/to/output
garmin-running-data-normalizer support-bundle --run-output /path/to/output --output /path/to/support-bundle.zip
```
