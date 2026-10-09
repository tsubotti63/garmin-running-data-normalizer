# Release Readiness

## v1.7.0 stable release

Version `1.7.0` is published as the FIT running dynamics release. It adds six
FIT running-dynamics averages (vertical oscillation, stance time, stance time
percent, stance time balance, vertical ratio, and step length) to
`fit_sessions` and `fit_laps`, read from the FIT session and lap messages in
the units defined by the FIT profile, and appends elapsed and moving time and
the linked FIT session's values to `analysis/activities.csv`, while keeping
the 17 datasets, stable keys, output paths, the Snapshot lifecycle contract
and policy registry `v1.0`, and the `0 / 0 / 3 / 2` Product exit contract
unchanged; the field inventory grows from 212 to 224.

The release source is the `main` commit that merges the v1.7.0 release
preparation pull request. Its annotated tag, GitHub Release, and publish
workflow evidence are recorded in this section after publication.

## v1.6.0 stable release

Version `1.6.0` is published as the local timezone release. It adds
`--timezone` to `run-all`, `snapshot run-all`, `normalize-activities`, and
`doctor --input`, records the timezone used as `local_timezone`, and stops with
`TIMEZONE_INVALID` for a name that is not an exact IANA timezone name, while
keeping the default `Asia/Tokyo`, the 17-dataset/212-field inventory, stable
keys, the Snapshot lifecycle contract and policy registry `v1.0`, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `877f42289f99acd7eb1fc2adea0379c040cb772e` (#56).
The annotated `v1.6.0` tag (tag object
`1bfb75e1b7e3ae94e8742ae8c33ad10e76c2b0df`), the then-latest stable GitHub
Release published on 2026-10-09 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.5.0 stable release

Version `1.5.0` is published as the Snapshot and output hardening release. It
creates new Snapshot Stores and `normalize-activities` output owner-only,
reports Snapshot stop conflicts by dataset and type with lock recovery
guidance, skips `Thumbs.db` inside ZIP files, and keeps every Sleep field that
Run-All reads in Snapshot input, while keeping the 17-dataset/212-field
inventory, stable keys, the Snapshot lifecycle contract and policy registry
`v1.0`, and the `0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `e5970fa398fbd9711b395fbe4cc212df0bcbb98e` (#53).
The annotated `v1.5.0` tag (tag object
`55ebfd97ce46654f2732bc2ebb746f78fc6ed61b`), the then-latest stable GitHub
Release published on 2026-10-07 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.4.1 stable patch release

Version `1.4.1` is published as the FIT correctness and metadata-file patch
release. It corrects FIT session sport names to the FIT profile, checks FIT
containers before reading FIT-derived HRV, and ignores operating-system
metadata files in Export folders and completed outputs, while keeping the
17-dataset/212-field inventory, stable keys, Snapshot semantics, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `9e3bd6d3d7faa64f6961547756559703158ae0b2` (#49).
The annotated `v1.4.1` tag (tag object
`402ec6cbff2af618f2f10233ce5f5cc704da21c6`), the then-latest stable GitHub
Release published on 2026-10-07 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

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
- Current source and package version: `1.7.0`
- Current Production PyPI version: `1.7.0`
- Latest GitHub Release: `v1.7.0`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.7.0`: Not used; the release publishes directly to Production
  PyPI through the protected `pypi` Environment
- Production PyPI `1.7.0`: Published through Trusted Publishing; the publish
  workflow verifies the exact-version install
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.7.0 is the current stable release;
v1.6.0, v1.5.0, v1.4.1, v1.4.0, and v1.3.3 are historical releases. The
v1.6.0, v1.5.0, v1.4.1, v1.4.0, and v1.3.3 tag, GitHub Release, and Production
PyPI publication evidence was recorded only after the corresponding external
state was observed; the v1.7.0 publication evidence is added to this document
after it is observed.

## Current release assessment

The v1.7.0 release assessment is recorded here after publication, from the
release source's main CI run and the Production publish workflow run.

### v1.6.0 release assessment (historical)

The v1.6.0 release source passed main CI run `37905835932` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `37905835352`. A build-only publish workflow
run (`37912699868`) on the release source passed with every upload job
skipped. Production publish workflow run `37912868187` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The publication
sequence ran under one Human approval given after its values were shown. The
`pypi` Environment deployment was Human-authorized, and the approval was
submitted through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`5aae3599c609a7470b6806320b3b962d34ee1336cc069236f56ec4a67511d8bb` and source
distribution `fa164c2c11b189b8a743a578641c225c492b671a301762dc9df611a813f1bfc2`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`, recorded `America/New_York` as
`local_timezone` with `--timezone America/New_York`, and stopped with
`TIMEZONE_INVALID` (exit 2) without creating output for `asia/tokyo`.

### v1.5.0 release assessment (historical)

The v1.5.0 release source passed main CI run `37587836756` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `37587836696`. A build-only publish workflow
run (`37588024918`) on the release source passed with every upload job
skipped. Production publish workflow run `37588284218` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The publication
sequence ran under one Human approval given after its values were shown. The
`pypi` Environment deployment was Human-authorized, and the approval was
submitted through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`6d17b79e3fee5c9cbeb9a80c66c69213c5b29e6f15f7e9294f7c949c5b2c2b7a` and source
distribution `873171db165c5d79fd7db0f54336d62e167b96f82774535ea55b801cfac464da`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`.

### v1.4.1 release assessment (historical)

The v1.4.1 release source passed main CI run `37563843781` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `37563843505`. A build-only publish workflow
run (`37563874206`) on the release source passed with every upload job
skipped. Production publish workflow run `37566440958` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The `pypi`
Environment deployment was Human-authorized, and the approval was submitted
through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`703926f16e6dde1a6a515b04e44cc6090823dc9fcd0c5d4a8a71e09443564ee5` and source
distribution `76e04d70421f0dbe9b12a3a451d285de534fe1519ad1401d99e362b95114a428`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`.

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
