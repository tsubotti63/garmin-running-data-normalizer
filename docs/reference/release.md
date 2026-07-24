# Release Readiness Reference

## Current facts

- Repository publication: Public
- Default branch: `main`
- License: `Apache-2.0`
- CI: Operational
- Python package candidate version on `main`: `1.1.1`
- Latest GitHub Release: `v1.1.0`
- Release classification: Public, non-prerelease, and marked latest
- Latest Release tag commit:
  `821fbc9d41ea349aaf43613191555a14aed9735c`
- Attached assets: None; GitHub-generated source archives only
- PyPI packaging readiness: PASS on `main`
- TestPyPI: `1.1.0rc1` published and clean-install verified
- Production PyPI distributions: None
- `v1.1.1` tag, Release, TestPyPI upload, and Production PyPI upload:
  Separately Human-gated and not performed

Repository publication makes the source available for public maintenance. A Git
tag identifies a Git object, a GitHub Release is a separately created GitHub
artifact, and a versioned product release is a distinct project event. The
published `v1.1.0` tag and Release remain immutable even though their exact
source declares package version `1.1.0rc1`. Stable package publication therefore
uses a separately reviewed `1.1.1` source rather than rewriting history or
renaming rehearsal artifacts.

## Release readiness

The Human owner confirmed redistribution rights for the predecessor-derived
responsibilities retained by the reviewed v1.1 implementation. TestPyPI
`1.1.0rc1` passed exact-source build, strict metadata, isolated installation,
Trusted Publishing, and post-upload verification. The stable `1.1.1` candidate
changes release identity only and must pass the full current implementation,
dependency, privacy, static-policy, packaging, installed-product, and CI gates.

The publication workflow remains manual-only and build-only by default. Upload
jobs require an exact reviewed source, target-specific approval variable,
protected GitHub Environment, and matching OIDC publisher. Successful candidate
validation does not create a tag, publish a GitHub Release, or authorize an
index upload. This reference records the current distinction; it does not
create standing release authority.
