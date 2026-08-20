# Getting Started from a Garmin Account Data Export

This guide takes a first-time user from an official Garmin Account Data Export
to a completed local Run-All handoff. It applies to the current stable v1.4.0
Garmin Running Data Normalizer release published on GitHub and Production PyPI.

Use this guide for a full Garmin Account Data Export. An individual Activity
GPX or TCX export is not the input described here.

## Before you begin

You need:

- Python 3.11 or later;
- enough private local storage for the original archive, extracted Export, and
  generated output;
- a new output path outside the Export directory; and
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

## 2. Preserve and extract the delivery

1. Keep the downloaded outer ZIP as immutable private evidence.
2. Copy or extract it into a dedicated local directory.
3. Extract the outer Garmin Account Data Export ZIP only.
4. Use the extracted directory as the Run-All input root.

Do not pass the outer ZIP itself to `--input`; direct ZIP input is unsupported.
ZIP assets discovered inside the input directory are handled by the product's
bounded archive intake. Do not keep both an inner ZIP and a separately
extracted duplicate of that same inner content in the input root.

Keep generated output outside the input root. Run-All reads the Export and does
not modify it.

## 3. Install the published baseline

Create an isolated environment if practical, then install the exact published
baseline from Production PyPI:

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install garmin-running-data-normalizer==1.4.0
.venv/bin/python -m garmin_running_data_normalizer --version
```

The version command for this guide should report `1.4.0`.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install garmin-running-data-normalizer==1.4.0
.\.venv\Scripts\python.exe -m garmin_running_data_normalizer --version
```

`python` must resolve to Python 3.11 or later. If multiple Python versions are
installed and the Windows Python launcher is available, you can use
`py -3.11 -m venv .venv` instead.

The v1.4.0 release installs `tzdata` automatically on Windows. Confirm both the
package version and the existing IANA timezone contract with:

```powershell
.\.venv\Scripts\python.exe -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Tokyo'))"
```

Earlier maintainer-owned physical Windows validation from Production PyPI
confirmed automatic `tzdata` installation and successful `Asia/Tokyo`
resolution without any manual dependency install. Current v1.4.0 CI covers the
packaged Windows path and the published v1.4.0 package retains this contract.
Both remain bounded evidence rather than a universal compatibility claim.

## 4. Run one-shot normalization first

Use the compatible one-shot path for your first real Export:

### macOS / Linux

```bash
python -m garmin_running_data_normalizer run-all \
  --input /path/to/extracted-garmin-export \
  --output /path/to/new-run-all-output
```

### Windows PowerShell

```powershell
python -m garmin_running_data_normalizer run-all --input "C:\Garmin\Export" --output "C:\Garmin\Output\run-all-01"
```

Replace both example paths. The input must be a directory containing a
supported filename ending in `summarizedActivities.json`. Activities are
required. Gear, Personal Records, and FIT are optional.

The output path:

- must not already exist;
- must not be a symbolic link; and
- must be outside the input directory.

Run-All fails closed instead of overwriting an existing result.

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
| `3` | `PARTIAL_SUCCESS`; Activities are valid and detected FIT is auditably incomplete |

`PASS_WITH_WARNINGS` requires review of the warnings. `PARTIAL_SUCCESS` is not
a complete FIT pass: limit FIT-derived analysis to the parsed subset and
disclose the warning.

You can validate a completed handoff later:

### macOS / Linux

```bash
python -m garmin_running_data_normalizer validate-handoff \
  --input /path/to/completed-run-all-output
```

### Windows PowerShell

```powershell
python -m garmin_running_data_normalizer validate-handoff --input "C:\Garmin\Output\run-all-01"
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
canonical cumulative input:

### macOS / Linux

```bash
python -m garmin_running_data_normalizer snapshot init \
  --store /path/to/private-snapshot-store \
  --account opaque-local-account

python -m garmin_running_data_normalizer snapshot register \
  --store /path/to/private-snapshot-store \
  --input /path/to/complete-garmin-export \
  --label S1 \
  --requested-at 2030-01-01T00:00:00+00:00 \
  --downloaded-at 2030-01-01T01:00:00+00:00 \
  --observed-at 2030-01-01T02:00:00+00:00 \
  --confirm-complete

python -m garmin_running_data_normalizer snapshot verify \
  --store /path/to/private-snapshot-store

python -m garmin_running_data_normalizer snapshot run-all \
  --store /path/to/private-snapshot-store \
  --output /path/to/new-snapshot-run-all-output
```

### Windows PowerShell

```powershell
python -m garmin_running_data_normalizer snapshot init --store "C:\Garmin\SnapshotStore" --account opaque-local-account
python -m garmin_running_data_normalizer snapshot register --store "C:\Garmin\SnapshotStore" --input "C:\Garmin\Export" --label S1 --requested-at 2030-01-01T00:00:00+00:00 --downloaded-at 2030-01-01T01:00:00+00:00 --observed-at 2030-01-01T02:00:00+00:00 --confirm-complete
python -m garmin_running_data_normalizer snapshot verify --store "C:\Garmin\SnapshotStore"
python -m garmin_running_data_normalizer snapshot run-all --store "C:\Garmin\SnapshotStore" --output "C:\Garmin\Output\snapshot-run-all-01"
```

Use one opaque account token per person/account boundary. Repeat only the
registration step for later complete Exports. Registration requires
timezone-aware lifecycle timestamps. The Store contains immutable private
evidence; restrict access, never commit it, and do not manually delete Store
internals. Automatic Snapshot/blob deletion and garbage collection are not
provided.

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
