# Getting Started from a Garmin Account Data Export

This guide takes a first-time user from an official Garmin Account Data Export
to a completed local Run-All handoff with the CLI. It applies to the current
stable v2.0.0 Garmin Running Data Normalizer release published on GitHub and
Production PyPI. To normalize from a page in the browser instead, see the
[GUI Guide](gui_guide.md).

Use this guide for a full Garmin Account Data Export. An individual Activity
GPX or TCX export is not the input described here.

This guide uses commands. Starting with v2.0.0, you can instead normalize on a
page in your browser: see the [GUI guide](gui_guide.md)
([日本語](gui_guide.ja.md)). The GUI runs the same processing as these
commands.

## Before you begin

You need:

- Python 3.11 or later;
- enough private local storage for the original archive, an extracted copy if
  you extract it, and generated output;
- a new output path outside the Export, in a folder that exists; and
- permission to process the Garmin data.

Run the repository's synthetic
[Product Quick Start](product_quick_start.md) first if you want to verify the
installation without personal data.

## 1. Request the Export from Garmin

Open Garmin's official
[Data Management page](https://www.garmin.com/account/datamanagement/) and
request a complete Account Data Export. Garmin prepares the download
asynchronously. Follow the current instructions shown by Garmin and retain the
notification until the archive has been downloaded.

The product does not sign in to Garmin or request the Export for you.

## 2. Preserve the delivery

1. Keep the downloaded ZIP file unchanged as private evidence.
2. Use it as the input as it is, or extract it into a dedicated local
   directory and use that directory.

Starting with v2.0.0, `--input` takes the downloaded Export ZIP file directly.
The product checks that it is complete and undamaged, and reads the ZIP files
inside it one level deep (see
[An Export given as a ZIP file](v2_data_handling.md#an-export-given-as-a-zip-file)).
If you extract it instead, check that the extraction finished before you run.
An input that holds the same Export twice, such as a ZIP file and its
extracted copy, is read once with the warning `INPUT_DUPLICATE_SOURCES`.

Keep generated output outside the input. Run-All reads the Export and does not
modify it.

## 3. Install the published baseline

Create an isolated environment if practical, then install the exact published
baseline from Production PyPI:

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install garmin-running-data-normalizer==2.0.0
.venv/bin/python -m garmin_running_data_normalizer --version
```

The version command for this guide should report `2.0.0`.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install garmin-running-data-normalizer==2.0.0
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer --version
```

`python` must resolve to Python 3.11 or later. If multiple Python versions are
installed and the Windows Python launcher is available, you can use
`py -3.11 -m venv .venv` instead.

The remaining commands in this guide call the environment's Python directly,
so activating the environment is not required. Run them from the directory
that contains `.venv`.

The v2.0.0 release installs `tzdata` automatically on Windows. Confirm both the
package version and the existing IANA timezone contract with:

```powershell
.\.venv\Scripts\python.exe -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Tokyo'))"
```

Earlier maintainer-owned physical Windows validation from Production PyPI
confirmed automatic `tzdata` installation and successful `Asia/Tokyo`
resolution without any manual dependency install. Current v2.0.0 CI covers the
packaged Windows path and the published v2.0.0 package retains this contract.
Both remain bounded evidence rather than a universal compatibility claim.

## 4. Run one-shot normalization first

Use the compatible one-shot path for your first real Export:

### macOS / Linux

```bash
mkdir -p /path/to/outputs
.venv/bin/python -m garmin_running_data_normalizer run-all \
  --input /path/to/garmin-export.zip \
  --output /path/to/outputs/run-all-01
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force "C:\Garmin\Output" | Out-Null
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer run-all --input "C:\Garmin\garmin-export.zip" --output "C:\Garmin\Output\run-all-01"
```

Replace the example paths. The input is the downloaded Export ZIP file or an
extracted Export folder, with a supported filename ending in
`summarizedActivities.json`. Activities are required. Gear, Personal Records,
and FIT are optional.

Local dates and times use the IANA timezone `Asia/Tokyo` by default. If your
records were made in another timezone, add `--timezone` with an exact
Area/Location name, such as `--timezone America/New_York`. `START_HERE.md` and
the run records state the timezone used. See
[Local dates and times](known_limitations.md#local-dates-and-times).

The output path:

- must not already exist;
- must not be a symbolic link;
- must be outside the input; and
- must be in a folder that exists: starting with v2.0.0, the command does not
  create it and stops with `OUTPUT_PARENT_NOT_FOUND` before it reads the
  input.

Run-All stops with `OUTPUT_EXISTS` instead of overwriting an existing result.

## 5. Confirm completion

The completion marker is:

```text
<output>/run_summary.json
```

A directory without that file is not a completed handoff. After checking the
status and warnings, read:

```text
<output>/START_HERE.md
```

The exit contract is:

| Exit code | Result |
|---:|---|
| `0` | `PASS` or `PASS_WITH_WARNINGS` |
| `2` | Fatal contract, input, QA, or publication error; no completed output |
| `3` | `PARTIAL_SUCCESS`; Activities are valid, and a file or row was left out; the warnings name it |

`PASS_WITH_WARNINGS` requires review of the warnings. `PARTIAL_SUCCESS` means
that a file, a row, or FIT data was left out: read the warnings and
`START_HERE.md`, limit analysis of the affected datasets to what was kept, and
disclose the warning.

You can validate a completed handoff later:

### macOS / Linux

```bash
.venv/bin/python -m garmin_running_data_normalizer validate-handoff \
  --input /path/to/completed-run-all-output
```

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer validate-handoff --input "C:\Garmin\Output\run-all-01"
```

## 6. Keep the result private

Real Exports and full Run-All outputs are personal local data. They can contain
identifiers, exact timestamps, source-relative paths, hashes, memo text, and
source filenames containing email-shaped personal identifiers.

Do not commit or attach:

- the original or extracted Export;
- full generated output;
- real Activity rows;
- IDs or stable keys;
- filenames, paths, or hashes;
- exact dates, routes, or locations; or
- memo text.

Run-All never uploads the Export or output. For a bounded external analysis
workflow, read the [AI Analysis Quick Start](ai_analysis_quick_start.md).

## 7. Optionally accumulate later complete Exports

One-shot Run-All processes one supplied Export. It does not combine separate
downloads. A later Export can omit files, periods, records, or fields seen
earlier:

```text
absence from a later Export != evidence of deletion
```

Keep each original Export. In `v1.2.0`, the optional Snapshot lifecycle can
register repeated complete Exports from one account boundary and build a
canonical cumulative input. Starting with v2.0.0, `snapshot register` also
takes the Export ZIP file, and the folder that holds a new store must exist
(`SNAPSHOT_STORE_PARENT_NOT_FOUND`):

### macOS / Linux

```bash
mkdir -p /path/to/private /path/to/outputs
.venv/bin/python -m garmin_running_data_normalizer snapshot init \
  --store /path/to/private/snapshot-store \
  --account opaque-local-account

.venv/bin/python -m garmin_running_data_normalizer snapshot register \
  --store /path/to/private/snapshot-store \
  --input /path/to/complete-garmin-export.zip \
  --label S1 \
  --requested-at 2030-01-01T00:00:00+00:00 \
  --downloaded-at 2030-01-01T01:00:00+00:00 \
  --observed-at 2030-01-01T02:00:00+00:00 \
  --confirm-complete

.venv/bin/python -m garmin_running_data_normalizer snapshot verify \
  --store /path/to/private/snapshot-store

.venv/bin/python -m garmin_running_data_normalizer snapshot run-all \
  --store /path/to/private/snapshot-store \
  --output /path/to/outputs/snapshot-run-all-01
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force "C:\Garmin\Output" | Out-Null
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer snapshot init --store "C:\Garmin\SnapshotStore" --account opaque-local-account
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer snapshot register --store "C:\Garmin\SnapshotStore" --input "C:\Garmin\garmin-export.zip" --label S1 --requested-at 2030-01-01T00:00:00+00:00 --downloaded-at 2030-01-01T01:00:00+00:00 --observed-at 2030-01-01T02:00:00+00:00 --confirm-complete
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer snapshot verify --store "C:\Garmin\SnapshotStore"
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer snapshot run-all --store "C:\Garmin\SnapshotStore" --output "C:\Garmin\Output\snapshot-run-all-01"
```

Use one opaque account token per person/account boundary. Repeat only the
registration step for later complete Exports. Registration requires
timezone-aware lifecycle timestamps. The Store contains immutable private
evidence; restrict access, never commit it, and do not manually delete Store
internals. When an interrupted registration left the lock file
`.single-writer.lock`, check that no other normalization or snapshot command
uses the store, and remove it with
`snapshot unlock --store <store> --confirm-no-other-command`, which the GUI
offers too; see [Known Limitations](known_limitations.md#snapshot-lifecycle).
Automatic Snapshot/blob deletion and garbage collection are not provided.

Read the
[v1.2 Snapshot Migration Guide](project/v1_2_snapshot_migration_guide_v1_0.md)
before adoption. The bounded public-safe validation is documented in
[CS-007](case_studies/cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md).

## Platform status

| Platform | Current evidence |
|---|---|
| macOS | Maintainer validated |
| Windows | GitHub Actions `windows-latest` plus one maintainer-owned physical Windows clean Production PyPI v1.2.1 install; `tzdata` installed automatically, `Asia/Tokyo` resolved, and Synthetic Run-All completed with `PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1 |
| Linux | GitHub Actions validated on `ubuntu-latest`; manual environment characterization is not claimed |

The Windows evidence does not claim that every Windows version, Python
distribution, shell configuration, or installation environment is compatible.

For a public-safe report, include the OS and version, shell, Python and package
versions, sanitized command, exit code, and public-safe error. Never attach
personal Garmin data. See [Support](../SUPPORT.md).

## Next steps

- Review the [Run-All Output Contract](output_contract.md).
- Check [Supported Datasets](supported_datasets.md) and
  [Known Limitations](known_limitations.md).
- Use the [AI Analysis Quick Start](ai_analysis_quick_start.md) for a bounded
  descriptive question.
- See the [FAQ](faq.md) for short answers and canonical links.
