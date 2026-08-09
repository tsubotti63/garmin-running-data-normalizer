# Release Readiness

## v1.3.1 stable patch release

Version `1.3.1` is published as a documentation, GitHub public-surface,
Product-owned entry-point, Public Product State Validator, and Platform
Alignment patch. It changes no Product API, runtime behavior, dataset, schema,
stable key, output path, Snapshot policy, relationship contract, or privacy
boundary.

PR #15 was squash-merged as
`9fac26ee8f81f1db1273cac5984415e103e756b3`. The annotated `v1.3.1` tag,
stable GitHub Release, Production PyPI publication, and clean-install smoke
test are complete.

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
- Current source and package version: `1.3.1`
- Current Production PyPI version: `1.3.1`
- Latest GitHub Release: `v1.3.1`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.3.1`: Not used; not required by the approved patch release
  contract
- Production PyPI `1.3.1`: Published and exact-version clean-install verified
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.3.1 is the current stable release; its
tag, GitHub Release, and Production PyPI publication were recorded only after
the corresponding external state was observed.

## Current release assessment

The reviewed v1.3.1 source passed 210 pytest tests, repository validators,
relative-link checks, strict wheel and source-distribution metadata checks,
isolated artifact installs, Ubuntu and Windows CI, and the existing 44-file
deterministic comparison while preserving the stable `1.x` one-shot and
Snapshot contracts. Main CI run `31295319603` and Production publish workflow
run `31295493750` passed. Earlier tags, Releases, and package artifacts remain
immutable and are not renamed or reused.

The prior v1.3.0 feature release remains the immutable source of the 17-dataset
and 212-field Wellness/Metrics contract. The v1.3.1 patch does not alter that
contract.

Post-publication validation on one maintainer-owned physical Windows
environment clean-installed Production PyPI v1.2.1, installed `tzdata`
automatically, resolved `Asia/Tokyo`, and completed Synthetic Run-All with
`PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
`run_summary.json` present. This supplements, but does not generalize beyond,
the `windows-latest` CI evidence.
