# Security and Privacy Boundary

## Sensitive by default

Garmin exports may contain identity, precise location, timestamps, routes,
health/wellness values, equipment, account identifiers, notes, and filenames
that reveal an email address. Treat every real export and derived output as
personal data.

## Required controls

- Local-only input by default; ignored by Git.
- Read-only intake and content-hash manifest.
- No telemetry or network upload by default.
- No credentials in config, logs, fixtures, or reports.
- Redact paths, emails, account/activity identifiers, and coordinates from
  portable evidence unless the user explicitly opts in.
- Synthetic test fixtures only.
- Stop on unsafe members of the Export ZIP file (paths outside the folder,
  links, encryption, or a compression ratio over the limit), on symbolic links
  in the input, on a damaged Export ZIP file, and over the limits on the
  totals of the Export ZIP file. Starting with v2.0.0, a ZIP file inside the
  Export with an unsafe member is left out with `DATA_FILE_LEFT_OUT` (see
  [Files that cannot be read](v2_data_handling.md#files-that-cannot-be-read)),
  files of a form that no dataset reads are not read and are listed in
  `run_manifest.json` (`files_not_read`; see
  [Files and fields that are not read](v2_data_handling.md#files-and-fields-that-are-not-read)),
  and a value of another form is left empty with `DATA_VALUE_INVALID` while
  its row stays (see
  [Rows and values with problems](v2_data_handling.md#rows-and-values-with-problems)).
- Open-Meteo is opt-in until coordinate disclosure and API-use policy are
  documented; raw responses are local/generated data and not committed.
- Temporary copies stay private and short-lived. Every ZIP file inside an
  Export ZIP file, and the input that `snapshot run-all` builds from the
  store, are written to a new folder in the operating system's temporary
  location (readable only by the user on macOS and Linux, and in the user's
  `%TEMP%` on Windows) whose name starts with `garmin-`. They are deleted when
  the command ends, including when it fails or is cancelled. A process that is
  forced to stop, or a power loss, can leave them behind; they contain
  personal data.

## Scanning

Before public release, scan tracked content for secrets, credentials, tokens,
cookies, emails, absolute host paths, coordinates, IDs, raw blobs, generated
datasets, and private Source references. A clean scan is necessary but not a
substitute for Human review.
