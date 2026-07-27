# CS-008: Windows Timezone Hotfix from Field Report to Production Validation

## Question

Can a public failure report be converted into a bounded, reproducible package
fix without weakening the product's timezone or privacy contracts?

## Incident

One third-party Windows environment reproduced a missing IANA timezone-data
failure on stable v1.2.0. `ZoneInfo("Asia/Tokyo")` raised
`ZoneInfoNotFoundError`, and Run-All surfaced the general
`ACTIVITIES_NORMALIZATION_FAILED` boundary. Installing `tzdata` manually in
that environment restored the tracked Synthetic Run-All:

- status: `PASS_WITH_WARNINGS`;
- exit code: `0`;
- Activities detected: `1`;
- Activities processed: `1`; and
- `run_summary.json`: generated.

This external discovery record contains no person name, host identifier,
private path, screenshot, or Garmin data.

## Root cause and fix

Stable v1.2.0 declared no runtime dependency. Windows Python installations do
not necessarily include an IANA timezone database. v1.2.1 therefore:

- declares `tzdata` only when `platform_system == "Windows"`;
- preserves the IANA `Asia/Tokyo` contract instead of replacing it with a fixed
  offset;
- emits the bounded `TIMEZONE_DATA_UNAVAILABLE` diagnostic when timezone data
  is still unavailable; and
- validates Windows package and Synthetic Run-All paths in GitHub Actions.

The normalization schema, stable keys, output layout, deterministic digest,
Snapshot policy, and exit-code contract did not change.

## Maintainer-owned physical Windows evidence

After v1.2.1 was published, one maintainer-owned physical Windows environment
performed a clean Production PyPI installation. The repository was used only
to supply the tracked synthetic fixture.

Observed results:

- installed product: `garmin-running-data-normalizer 1.2.1`;
- automatically installed dependency: `tzdata 2026.3`;
- dependency relationship: `Required-by: garmin-running-data-normalizer`;
- `ZoneInfo("Asia/Tokyo")`: resolved;
- Synthetic Run-All status: `PASS_WITH_WARNINGS`;
- exit code: `0`;
- Activities detected / processed: `1 / 1`; and
- `run_summary.json`: present.

The procedure did not use manual `pip install tzdata`, `pip install .`, or
`pip install -e .`. These facts prove the reviewed Production PyPI install path
in that physical environment. They do not prove compatibility with every
Windows version, Python distribution, shell configuration, or machine.

## Cross-platform evidence

| Platform | Evidence |
|---|---|
| macOS | Maintainer-validated development and release preparation |
| Linux | GitHub Actions `ubuntu-latest` tests, validators, builds, and package installation |
| Windows | GitHub Actions `windows-latest` plus the bounded physical validation above |

## Result

The incident was closed by a conditional package dependency, safe diagnostic,
cross-platform onboarding, Windows CI, and a post-publication physical check.
The result is a bounded interoperability claim, not a universal Windows support
claim.
