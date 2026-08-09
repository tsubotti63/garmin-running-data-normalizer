# Release Readiness Reference

## Current stable release

- Version: `1.3.1`
- Classification: patch release
- Scope: Product-owned public entry points, public-state validation, and
  documentation/platform-alignment consistency
- Product API, dataset, output, Snapshot, relationship, privacy, and runtime
  changes: none
- Source commit: `9fac26ee8f81f1db1273cac5984415e103e756b3`
- Annotated tag: `v1.3.1` (tag object
  `45cfc77d75f57d43224217294f2fead3fcd9d547`)
- GitHub Release: [Published, non-prerelease, and marked latest](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.3.1)
- Production PyPI: [Published](https://pypi.org/project/garmin-running-data-normalizer/1.3.1/)
  and exact-version clean-install verified
- TestPyPI: Not used for v1.3.1; it was not required by the approved patch
  release contract

## Current facts

- Repository publication: Public
- Default branch: `main`
- License: `Apache-2.0`
- CI: Operational
- Current source and package version: `1.3.1`
- Current Production PyPI version: `1.3.1`
- Latest GitHub Release: `v1.3.1`
- Release classification: Public, non-prerelease, and marked latest
- Release tag: Annotated `v1.3.1` on commit
  `9fac26ee8f81f1db1273cac5984415e103e756b3`
- PyPI packaging readiness: PASS on `main`
- Production PyPI `1.3.1`: Published and clean-install verified

Repository publication makes the source available for public maintenance. A Git
tag identifies a Git object, a GitHub Release is a separately created GitHub
artifact, and a versioned product release is a distinct project event. The
published earlier tags and Releases remain immutable. v1.3.1 was published from
the separately reviewed PR #15 Squash Commit without rewriting history or
renaming an earlier artifact.

## Release verification

- Release-candidate pytest: 210 passed
- Main CI run
  [`31295319603`](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/runs/31295319603):
  Ubuntu `test` and `windows-runtime` passed
- Production publish workflow
  [`31295493750`](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/runs/31295493750):
  exact-source build, approval gate, PyPI publication, and PyPI verification
  passed
- Public Product State, bootstrap, Platform Alignment, static policy, public
  command, public history, and relative-link validation: PASS
- Wheel SHA-256:
  `e314767194061d5c739bb767a4f9807297b7eb1752043759f6f634da05bea577`
- Source distribution SHA-256:
  `c54f1aabac2e81d9ce4750e35036521b8c46698c92eea6c74e43dd5f231d20b6`
- Clean Production PyPI install, version/import check, Synthetic Golden Path,
  repeated Synthetic Run-All, and 44-file deterministic comparison: PASS
- Target-specific TestPyPI and PyPI approval variables: returned to `false`

## Compatibility and historical context

v1.3.0 remains the immutable Wellness/Metrics feature release that established
the 17-dataset Product contract. v1.3.1 changes the public Product surface and
release validation only; it does not revise the v1.3.0 runtime or data
contracts.

Post-publication evidence also records one maintainer-owned physical Windows
clean install from Production PyPI. The Windows-only `tzdata` dependency was
installed automatically, `Asia/Tokyo` resolved, and the tracked Synthetic
Run-All completed with `PASS_WITH_WARNINGS`, exit 0, Activities detected=1 /
processed=1, and `run_summary.json` present. This is a bounded environment
result and not a claim of universal Windows compatibility.

The publication workflow remains manual-only and build-only by default. Upload
jobs require an exact reviewed source, target-specific approval variable,
protected GitHub Environment, and matching OIDC publisher. Successful candidate
validation does not create a tag, publish a GitHub Release, or authorize an
index upload. This reference records the current distinction; it does not
create standing release authority.
