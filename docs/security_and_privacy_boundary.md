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
- Fail closed on unknown archive members, unsafe paths, or unexpected schemas.
- Open-Meteo is opt-in until coordinate disclosure and API-use policy are
  documented; raw responses are local/generated data and not committed.

## Scanning

Before public release, scan tracked content for secrets, credentials, tokens,
cookies, emails, absolute host paths, coordinates, IDs, raw blobs, generated
datasets, and private Source references. A clean scan is necessary but not a
substitute for Human review.

