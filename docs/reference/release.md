# Release Readiness Reference

## Historical release reference: v1.3.2

This page records the v1.3.2 publication snapshot. The current stable release
is v1.4.0; use the root README and current release notes for current truth.

- Version at this historical snapshot: `1.3.2`
- Classification: patch release
- Scope: Snapshot correctness and evidence preservation
- Product API, dataset count, stable keys, grains, output paths, privacy, and
  exit-code changes: none
- Source commit: `c6f7737aa24d099b30e897cef0840f0189fb1d7b`
- Annotated tag: `v1.3.2` (tag object
  `7d539cbf7851c24bc592c8aae1f17ad2361c77ed`)
- GitHub Release: [Published, non-prerelease, and marked latest](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.3.2)
- Production PyPI: [Published](https://pypi.org/project/garmin-running-data-normalizer/1.3.2/)
  and exact-version clean-install verified
- TestPyPI: Not used for v1.3.2; it was not required by the approved patch
  release contract

## Historical facts at the v1.3.2 snapshot

- Repository publication: Public
- Default branch: `main`
- License: `Apache-2.0`
- CI: Operational
- Current source and package version: `1.3.2`
- Current Production PyPI version: `1.3.2`
- Latest GitHub Release: `v1.3.2`
- Release classification: Public, non-prerelease, and marked latest
- Release tag: Annotated `v1.3.2` on commit
  `c6f7737aa24d099b30e897cef0840f0189fb1d7b`
- PyPI packaging readiness: PASS on `main`
- Production PyPI `1.3.2`: Published and clean-install verified

Repository publication makes the source available for public maintenance. A Git
tag identifies a Git object, a GitHub Release is a separately created GitHub
artifact, and a versioned product release is a distinct project event. The
published earlier tags and Releases remain immutable. v1.3.1 was published from
the separately reviewed PR #15 Squash Commit without rewriting history or
renaming an earlier artifact. v1.3.2 was subsequently published from the exact
reviewed source commit shown above through its separate tag, Release, and
Trusted Publishing gates.

## Release verification

- Release-source pytest: 251 passed; unittest: 208 passed
- Main CI run
  [`31405707069`](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/runs/31405707069):
  Ubuntu `test` and `windows-runtime` passed
- Production publish workflow
  [`31407525307`](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/runs/31407525307):
  exact-source build, approval gate, PyPI publication, and PyPI verification
  passed
- Public Product State, bootstrap, Platform Alignment, static policy, public
  command, public history, and relative-link validation: PASS
- Wheel SHA-256:
  `612a16bb269983972294d20bdb5c6507422bacd4a3daf62ac5cd52f383272624`
- Source distribution SHA-256:
  `88b1e3fa3af63cc9a037cba8134a95aa4504f397ef9d014b1853e58da1772a4c`
- Clean Production PyPI install, version/import check, `pip check`, Synthetic
  Run-All, 44-file output, and 17-dataset/6-relationship handoff: PASS
- Target-specific TestPyPI and PyPI approval variables: returned to `false`

## Compatibility and historical context

v1.3.0 remains the immutable Wellness/Metrics feature release that established
the 17-dataset Product contract. v1.3.1 changed the public Product surface and
release validation only. v1.3.2 improves Snapshot correctness and evidence
preservation without changing the v1.3.0 dataset count, stable keys, grains, or
privacy boundary.

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
