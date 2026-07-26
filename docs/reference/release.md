# Release Readiness Reference

## Current facts

- Repository publication: Public
- Default branch: `main`
- License: `Apache-2.0`
- CI: Operational
- Python package version on `main`: `1.2.0`
- Latest GitHub Release: `v1.2.0`
- Release classification: Public, non-prerelease, and marked latest
- Release tag: Annotated `v1.2.0` on the reviewed release commit
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.2.0`: Published and clean-install verified
- Production PyPI `1.2.0`: Published and clean-install verified

Repository publication makes the source available for public maintenance. A Git
tag identifies a Git object, a GitHub Release is a separately created GitHub
artifact, and a versioned product release is a distinct project event. The
published earlier tags and Releases remain immutable. v1.2.0 was published from
a separately reviewed release commit without rewriting history or renaming an
earlier artifact.

## Release readiness

The Human owner confirmed redistribution rights for the predecessor-derived
responsibilities retained by the reviewed implementation. v1.2.0 passed local
exact-source build, strict metadata, isolated installation, dependency,
privacy, static-policy, packaging, and installed-product gates. CI and each
external publication result were recorded only after they were observed.

The publication workflow remains manual-only and build-only by default. Upload
jobs require an exact reviewed source, target-specific approval variable,
protected GitHub Environment, and matching OIDC publisher. Successful candidate
validation does not create a tag, publish a GitHub Release, or authorize an
index upload. This reference records the current distinction; it does not
create standing release authority.
