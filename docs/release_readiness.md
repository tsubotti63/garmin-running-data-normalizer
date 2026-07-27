# Release Readiness

## Current repository state

- Public repository operation: Active
- Default branch: `main`
- License: `Apache-2.0`
- GitHub Actions: Operational
- Python package version on `main`: `1.2.1`
- Latest GitHub Release: `v1.2.1`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.2.1`: Published and clean-install verified
- Production PyPI `1.2.1`: Published and clean-install verified
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.2.1 is the current stable release; its
tag, GitHub Release, TestPyPI publication, and Production PyPI publication were
recorded only after the corresponding external state was observed.

## Current release assessment

The reviewed v1.2.1 implementation passed tests, validators, packaging checks,
the Ubuntu and Windows CI jobs, and isolated package installs while preserving
the stable `1.x` one-shot and Snapshot contracts. Earlier tags, Releases, and
package artifacts remain immutable and are not renamed or reused. TestPyPI,
the annotated tag, GitHub Release, and Production PyPI verification passed for
version `1.2.1`.

Post-publication validation on one maintainer-owned physical Windows
environment clean-installed Production PyPI v1.2.1, installed `tzdata`
automatically, resolved `Asia/Tokyo`, and completed Synthetic Run-All with
`PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
`run_summary.json` present. This supplements, but does not generalize beyond,
the `windows-latest` CI evidence.
