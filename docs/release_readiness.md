# Release Readiness

## v1.3.0 stable release

PR #10 was merged as `d2aca48b9a5b0bee732fa3f004c25289972e7e15`.
Version `1.3.0` is published as an annotated tag, a stable GitHub Release, and a
verified Production PyPI distribution. The release includes 17 normalized
datasets, reviewed Snapshot policies, expanded Output Experience, and
lifecycle-aware relationship guidance. The remaining Lactate Threshold gates
apply only to a future stable promotion and do not reopen v1.3 scope.

## Current repository state

- Public repository operation: Active
- Default branch: `main`
- License: `Apache-2.0`
- GitHub Actions: Operational
- Current source and package version: `1.3.0`
- Current Production PyPI version: `1.3.0`
- Latest GitHub Release: `v1.3.0`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.3.0`: Not used; not required by the approved release contract
- Production PyPI `1.3.0`: Published and exact-version clean-install verified
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.3.0 is the current stable release; its
tag, GitHub Release, and Production PyPI publication were recorded only after
the corresponding external state was observed.

## Current release assessment

The reviewed v1.3.0 implementation passed 199 pytest tests, 170 unittest tests,
validators, packaging checks, 17-dataset / 212-field schema validation, 44-file
deterministic comparison, Ubuntu and Windows CI, and isolated package installs
while preserving the stable `1.x` one-shot and Snapshot contracts. Earlier
tags, Releases, and package artifacts remain immutable and are not renamed or
reused. The annotated tag, GitHub Release, and Production PyPI verification
passed for version `1.3.0`.

Post-publication validation on one maintainer-owned physical Windows
environment clean-installed Production PyPI v1.2.1, installed `tzdata`
automatically, resolved `Asia/Tokyo`, and completed Synthetic Run-All with
`PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
`run_summary.json` present. This supplements, but does not generalize beyond,
the `windows-latest` CI evidence.
