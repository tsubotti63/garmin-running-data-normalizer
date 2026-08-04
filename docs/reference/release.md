# Release Readiness Reference

## Prepared next release

- Candidate source version: `1.3.0`
- Scope: additive Wellness/Metrics datasets and Output Experience expansion
- Review: Aggregate Product Review ready with Lactate field-level gates
- Merge, tag, GitHub Release, TestPyPI, Production PyPI: not performed

The candidate state does not replace the published facts below.

## Current facts

- Repository publication: Public
- Default branch: `main`
- License: `Apache-2.0`
- CI: Operational
- Prepared branch source version: `1.3.0`
- Current Production PyPI version: `1.2.1`
- Latest GitHub Release: `v1.2.1`
- Release classification: Public, non-prerelease, and marked latest
- Release tag: Annotated `v1.2.1` on the reviewed release commit
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.2.1`: Published and clean-install verified
- Production PyPI `1.2.1`: Published and clean-install verified

Repository publication makes the source available for public maintenance. A Git
tag identifies a Git object, a GitHub Release is a separately created GitHub
artifact, and a versioned product release is a distinct project event. The
published earlier tags and Releases remain immutable. v1.2.1 was published from
a separately reviewed release commit without rewriting history or renaming an
earlier artifact.

## Release readiness

The Human owner confirmed redistribution rights for the predecessor-derived
responsibilities retained by the reviewed implementation. v1.2.1 passed local
exact-source build, strict metadata, isolated installation, dependency,
privacy, static-policy, packaging, and installed-product gates. CI and each
external publication result were recorded only after they were observed.

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
