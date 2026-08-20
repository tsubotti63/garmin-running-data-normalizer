# Release Readiness

## v1.3.3 stable patch release

Version `1.3.3` is published as the Sleep contract restoration patch. It keeps
the 17-dataset/212-field inventory, stable keys, schemas, relationships, and
the compatible `1.x` output contract unchanged while restoring observed-stage
duration semantics and separating review-required from excluded evidence.

The release source is `cf7e44c18d77adda4c908207361e6f6f5f2b682c`.
The annotated `v1.3.3` tag, latest stable GitHub Release, Production PyPI
publication through Trusted Publishing/OIDC, exact-version clean install,
Synthetic Run-All, and Sleep contract smoke are complete.

## v1.3.2 stable patch release

Version `1.3.2` is published as a Snapshot correctness and
evidence-preservation patch. Snapshot-aware relationship resolution, exact
Sleep duplicate handling, Endurance/UDS observed-variant preservation, Lactate
candidate preservation, and acquisition/processing-order separation retain
observed evidence without selecting an unsupported winner.

The release source is `c6f7737aa24d099b30e897cef0840f0189fb1d7b`.
The annotated `v1.3.2` tag, latest stable GitHub Release, Production PyPI
publication, and exact-version clean-install smoke test are complete.

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
- Current source and package version: `1.3.3`
- Current Production PyPI version: `1.3.3`
- Latest GitHub Release: `v1.3.3`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.3.3`: Not used; not required by the approved patch release
  contract
- Production PyPI `1.3.3`: Published and exact-version clean-install verified
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.3.3 is the historical patch release; its
tag, GitHub Release, and Production PyPI publication were recorded only after
the corresponding external state was observed.

## Current release assessment

The reviewed v1.3.3 source passed 274 pytest tests, 219 unittest checks,
repository validators, strict wheel and source-distribution metadata checks,
isolated artifact installs, and Ubuntu and Windows CI while preserving the
stable `1.x` one-shot and Snapshot contracts. Main CI run `31648832233` and
Production publish workflow run `31653110586` passed. Clean Production PyPI
installation, version/import checks, `pip check`, Synthetic Run-All, and its
17-dataset/6-relationship handoff passed; the Production Sleep smoke passed
11/11 checks. Earlier tags, Releases, and package artifacts remain immutable
and are not renamed or reused.

The prior v1.3.0 feature release remains the immutable source of the 17-dataset
and 212-field Wellness/Metrics contract. The v1.3.1, v1.3.2, and v1.3.3 patches
do not change that contract.

Post-publication validation on one maintainer-owned physical Windows
environment clean-installed Production PyPI v1.2.1, installed `tzdata`
automatically, resolved `Asia/Tokyo`, and completed Synthetic Run-All with
`PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
`run_summary.json` present. This supplements, but does not generalize beyond,
the `windows-latest` CI evidence.
