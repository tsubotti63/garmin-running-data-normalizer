# Security Policy

## Supported Versions

Security guidance applies to the current stable release, v1.3.3. Users should
reproduce a report against the latest stable version when it is safe to do so.
Older releases may not receive a separate fix.

## Private Vulnerability Reporting

Report a suspected vulnerability through GitHub Private Vulnerability Reporting:

https://github.com/tsubotti63/garmin-running-data-normalizer/security/advisories/new

If that private route is unavailable, do not open a public Issue and do not send
sensitive details through another public channel. Retain the details privately
until the private route is available. This project does not publish a backup email
address or promise a fixed response time.

## Choose the Right Route

- Security-sensitive behavior or disclosure risk: use
  [Private Vulnerability Reporting](https://github.com/tsubotti63/garmin-running-data-normalizer/security/advisories/new).
- A reproducible Product failure that can be described with public Synthetic data:
  use the [Bug report](https://github.com/tsubotti63/garmin-running-data-normalizer/issues/new?template=bug_report.yml).
- Unclear or incomplete public guidance: use the
  [Documentation problem](https://github.com/tsubotti63/garmin-running-data-normalizer/issues/new?template=documentation_problem.yml).
- A successful run of the documented Synthetic workflow: use the
  [Synthetic validation report](https://github.com/tsubotti63/garmin-running-data-normalizer/issues/new?template=synthetic_validation_report.yml).

If a report includes security-sensitive reproduction details, it belongs in the
private route even when it also looks like a Product bug.

## Do Not Post Publicly

Do not put vulnerability details, proof-of-concept payloads, credentials, tokens,
real Garmin exports, health data, screenshots containing personal information, or
private filesystem paths in a public Issue, Discussion, or Pull Request.

## Scope

Relevant reports can include:

- credential or token exposure;
- unsafe archive extraction or path traversal;
- raw Garmin or health-data leakage;
- private local path, account, or device identifier exposure;
- integrity or provenance bypass;
- publishing or release-authorization bypass;
- dependency or supply-chain concerns; and
- unsafe handling of malicious or malformed Garmin exports.

## Non-Scope

The security route is not for ordinary support questions, documentation feedback,
successful Synthetic validation, medical interpretation, coaching, or requests for
Garmin-official meaning guarantees. Use the public-safe route above where
applicable. Do not move security-sensitive details into a public route.

## Privacy Boundary

Use the smallest sanitized reproduction that demonstrates the issue. Do not attach
real Garmin Export, FIT, JSON, or CSV data. Do not include row-level health data,
account identifiers, device identifiers, secrets, private paths, or unrelated
screenshots. Additional evidence should be shared only through the private advisory
and only when explicitly requested.

## Response Boundary

Reports are assessed on a best-effort basis. The maintainer may ask for a bounded,
privacy-safe reproduction, verify the affected release, and prepare a narrowly
scoped fix and regression evidence. No response or remediation SLA is promised.

## Disclosure / Human Approval Boundary

Public disclosure, release publication, and any statement about impact require
explicit maintainer approval. Opening a private report does not authorize a public
Issue, public proof of concept, release, or publication of private evidence.
