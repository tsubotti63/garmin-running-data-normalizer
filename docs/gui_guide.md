# GUI Guide

> **In development for v2.0.0.** The GUI is not part of the current stable
> release, v1.7.0, and the `gui` command is not available yet. It is planned
> for the v2.0.0 release candidate on TestPyPI. Until then, use the command
> line as described in
> [Getting Started from Garmin Export](getting_started_from_garmin_export.md).

[日本語](gui_guide.ja.md)

The GUI runs the one-shot Run-All on a Garmin Account Data Export from a page
in your web browser. It uses the same processing as the command line: for the
same input and options, it writes the same output. Everything stays on your
computer.

## What you need

- The package installed with Python 3.11 or later. The GUI adds no
  dependency.
- A web browser on the same computer.
- A Garmin Account Data Export, extracted from its ZIP into a folder. See
  steps 1 and 2 of
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

## 1. Choose the export folder

1. In **Export folder (full path)**, enter the full path of the extracted
   Export folder, or choose **Browse…** to pick it. The folder browser shows
   folder names only; hidden folders and links are not shown.
2. Choose **Check the folder**. This is the same check as the `doctor --input`
   command. It says whether a run can start, and what to do next if it
   cannot. A large Export can take a while to check.

Changing the folder or the timezone clears the check, so check again before
you start.

## 2. Choose the output

- **Folder to create the output in (full path)**: after a successful check,
  this is filled in with the folder that contains the Export, if it is empty.
  The folder must exist, and you must be able to write to it; the GUI checks
  this before the run starts.
- **Name of the new output folder**: proposed as
  `garmin-run-all-YYYYMMDD-HHMM` in local time. Use a name that does not exist
  yet, with up to 200 letters and digits or 66 Japanese characters. It must
  not start with a dot or contain characters such as `/` or `:`.
- **Timezone for local dates and times**: `Asia/Tokyo` by default. Use an
  IANA name such as `Europe/London`.
- **Also create the External-safe Pack**: off by default. It is the same
  Activities-only pack as the command line's `--external-safe-pack`. Review it
  before you share it.

On Windows, keep the location and the name short. Unless long paths are
enabled, Windows limits a whole path to 260 characters, and the files inside
the output add about 40 characters to the path of the output folder.

The output folder appears only when the run finishes. Until then, Run-All
works in a hidden working folder next to it.

## 3. Run

- Choose **Start Run-All**. Only one run can be active at a time.
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
| `PARTIAL_SUCCESS` | 3 | Finished; the activities are complete, but some FIT files could not be read completely and were left out |

A table lists each data family with its status, record count, and warnings.

**Output check** runs by itself after the run, with the same checks as the
`validate-handoff` and `doctor --run-output` commands. It shows:

- the handoff check, with the number of datasets, links between datasets, and
  warnings;
- whether the output can be used, and the next step;
- one line for each kind of warning, with its code.

**Show the output folder** shows the folder in Finder on macOS, in File
Explorer on Windows, and with the file manager that `xdg-open` chooses on
Linux. **Open START_HERE.md** opens the file with the default application for
`.md` files. Start with `START_HERE.md`; it explains the output.

After a run, the page proposes a new name for the next one.

## 5. Make a Support Bundle when you need help

**Make the Support Bundle** writes `<output name>-support-bundle.zip` next to
the output folder, as the `support-bundle` command does.

- It holds six summary files. It contains no rows of your records, paths, file
  names, identifiers, exact times, or coordinates. Nothing is uploaded.
- Review all six files before you share it. The counts in it can still show
  how much you use your device.
- An existing file with the same name is never replaced. Move or rename it
  first.

For what the bundle contains, see
[v1.4 Export Evidence and Diagnostics](v1_4_diagnostics.md#support-bundle).
For where to ask, see [Support](../SUPPORT.md).

## When something goes wrong

Every problem is shown as what happened, what to do next, and a code. Quote
the code when you ask for help. Do not attach your Export or output.

| Code | What happened | What to do |
|---|---|---|
| `PATH_NOT_ABSOLUTE` | The path is not a full path. | Enter a full path: it starts with `/` on macOS and Linux, and with a drive such as `C:\` on Windows. |
| `FOLDER_NOT_READABLE` | The folder cannot be opened. | On a Mac, allow access when asked, or in System Settings > Privacy & Security. |
| `ACTIVITIES_NOT_FOUND` | No activities were found. | Choose the folder extracted from the Export ZIP. |
| `OUTPUT_EXISTS` | A folder with this name already exists. | Choose another name. |
| `OUTPUT_NAME_INVALID` | The name cannot be used, or the path is too long. | Follow the name rules, or use a shorter name. |
| `OUTPUT_PARENT_NOT_WRITABLE` | The output location cannot be written. | Choose another folder, or check its permissions. |
| `INPUT_CHANGED` | Files in the Export changed during the run. | Run again when no other program is changing the folder. |
| `OUTPUT_PUBLISH_FAILED` | The output folder could not be written. | Check the free space and the permissions. On Windows, use a shorter location and name. |
| `HANDOFF_INVALID` | The output folder does not match what the run wrote. | If you did not change it, report the code. |
| `SUPPORT_BUNDLE_EXISTS` | A Support Bundle with this name already exists. | Move or rename the existing file. |

For other codes, follow the next step on the page.

If the page says that the GUI is not responding, the GUI may have stopped, for
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

Use the command line for automation, for Snapshot runs, and to check an output
that was made earlier:

```bash
garmin-running-data-normalizer validate-handoff --input /path/to/output
garmin-running-data-normalizer doctor --run-output /path/to/output
garmin-running-data-normalizer support-bundle --run-output /path/to/output --output /path/to/support-bundle.zip
```
