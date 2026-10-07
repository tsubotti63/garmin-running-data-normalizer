# Release Readiness

## v1.4.1 stable patch release

Version `1.4.1` is published as the FIT correctness and metadata-file patch
release. It corrects FIT session sport names to the FIT profile, checks FIT
containers before reading FIT-derived HRV, and ignores operating-system
metadata files in Export folders and completed outputs, while keeping the
17-dataset/212-field inventory, stable keys, Snapshot semantics, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is the `main` commit that merges the v1.4.1 release
preparation pull request. Its annotated tag, GitHub Release, and publish
workflow evidence are recorded in this section after publication.

## v1.4.0 stable release

Version `1.4.0` is published as the Export Evidence and Diagnostics release. It
adds the Export Evidence Doctor, the read-only
`diagnostics/source_completeness.json` and `diagnostics/run_quality.json`
projections, and the Human-reviewed public-safe Support Bundle while keeping
the 17-dataset/212-field inventory, stable keys, Snapshot semantics, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `ae9cb28a60c450897284fd1023b1e4e7c02d127e`.
The annotated `v1.4.0` tag, then-latest stable GitHub Release, Production PyPI
publication through Trusted Publishing/OIDC, and the publish workflow's
exact-version PyPI install verification are complete.

## v1.3.3 stable patch release

Version `1.3.3` is published as the Sleep contract restoration patch. It keeps
the 17-dataset/212-field inventory, stable keys, schemas, relationships, and
the compatible `1.x` output contract unchanged while restoring observed-stage
duration semantics and separating review-required from excluded evidence.

The release source is `cf7e44c18d77adda4c908207361e6f6f5f2b682c`.
The annotated `v1.3.3` tag, then-latest stable GitHub Release, Production PyPI
publication through Trusted Publishing/OIDC, exact-version clean install,
Synthetic Run-All, and Sleep contract smoke are complete.

## v1.3.2 stable patch release

Version `1.3.2` is published as a Snapshot correctness and
evidence-preservation patch. Snapshot-aware relationship resolution, exact
Sleep duplicate handling, Endurance/UDS observed-variant preservation, Lactate
candidate preservation, and acquisition/processing-order separation retain
observed evidence without selecting an unsupported winner.

The release source is `c6f7737aa24d099b30e897cef0840f0189fb1d7b`.
The annotated `v1.3.2` tag, then-latest stable GitHub Release, Production PyPI
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
- Current source and package version: `1.4.1`
- Current Production PyPI version: `1.4.1`
- Latest GitHub Release: `v1.4.1`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.4.1`: Not used; the patch release publishes directly to
  Production PyPI through the protected `pypi` Environment
- Production PyPI `1.4.1`: Published through Trusted Publishing; the publish
  workflow verifies the exact-version install
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.4.1 is the current stable release;
v1.4.0 and v1.3.3 are historical releases. The v1.4.0 and v1.3.3 tags, GitHub
Releases, and Production PyPI publications were recorded only after the
corresponding external state was observed; the v1.4.1 publication evidence is
added to this document after it is observed.

## Current release assessment

The v1.4.1 release assessment is recorded here after publication, from the
release source's main CI run and the Production publish workflow run.

### v1.4.0 release assessment (historical)

The v1.4.0 release source passed main CI run `32388440076` (Ubuntu `test` and
`windows-runtime`) and Production publish workflow run `32389085934`. In that
publish run, the exact-source build and validation, Production PyPI
publication, and exact-version PyPI install verification succeeded, and the
TestPyPI jobs were skipped. The SHA-256 checksums recorded by the run match the
Production PyPI wheel and source distribution, which carry PEP 740 publish
attestations. A later publish workflow run on 2026-09-03 (`33726686281`,
source `a97a4ec`) was a build-only validation of the hardened workflow; its
upload and verification jobs were skipped and it published nothing. Earlier
tags, Releases, and package artifacts remain immutable and are not renamed or
reused.

### v1.3.3 release assessment (historical)

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
and the v1.4.0 release do not change that contract.

Post-publication validation on one maintainer-owned physical Windows
environment clean-installed Production PyPI v1.2.1, installed `tzdata`
automatically, resolved `Asia/Tokyo`, and completed Synthetic Run-All with
`PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
`run_summary.json` present. This supplements, but does not generalize beyond,
the `windows-latest` CI evidence.
