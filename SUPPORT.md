# Support

Use GitHub Issues for reproducible, non-sensitive product questions, bug
reports, documentation problems, and public-safe platform validation.

Before reporting a problem:

1. check the [FAQ](docs/faq.md);
2. follow the [Product Quick Start](docs/product_quick_start.md) with the
   synthetic fixture; and
3. check [Known Limitations](docs/known_limitations.md).

## What to include

- operating system and version;
- shell and version;
- Python version;
- Garmin Running Data Normalizer version;
- installation source;
- command with private paths replaced by placeholders;
- exit code;
- public-safe error code or message;
- whether the tracked synthetic fixture reproduces the problem; and
- the guide and section that was unclear.

Use the repository's public bug-report Issue form. A minimal synthetic
reproduction is preferred.

## Current Windows status

Windows is an intended supported platform. Current evidence includes
`windows-latest` packaged-runtime CI and one maintainer-owned physical Windows
validation. This remains bounded evidence and does not establish universal
compatibility.

Public-safe Windows reports are welcome. Include whether
`ZoneInfo("Asia/Tokyo")` resolved and whether the tracked synthetic fixture
completed, but do not attach terminal screenshots that contain user names,
private paths, or unrelated desktop content. Linux automated CI runs on
`ubuntu-latest`; that is not a claim of manual characterization on every Linux
environment.

## Historical v1.2.0 timezone issue

For stable v1.2.0 timezone-data failures, follow the
[Windows FAQ](docs/faq.md#was-the-v120-windows-timezone-data-issue-resolved)
first. This troubleshooting record describes the superseded v1.2.0 incident,
not the current Windows support state.

## Never include personal data

Do not attach or paste:

- an original or extracted Garmin Export;
- a full Run-All or Snapshot output;
- real Activity rows;
- raw IDs or stable keys;
- source filenames, private paths, or hashes;
- exact dates, timestamps, routes, or locations;
- memo text; or
- screenshots containing any of the above.

Replace private paths and values with clear placeholders. If the issue cannot
be reproduced without sensitive material, do not open a public report
containing that material.

## Security-sensitive reports

Do not disclose a suspected vulnerability or sensitive security detail in a
public Issue. This repository does not currently publish a verified private
vulnerability-reporting route. Until the maintainer publishes one, retain the
details privately rather than posting them publicly.

## Scope of support

Support covers the documented local product, synthetic reproduction, output
contract, and public documentation. It does not provide medical diagnosis,
coaching advice, injury assessment, fatigue/readiness conclusions, or causal
interpretation of personal data.
