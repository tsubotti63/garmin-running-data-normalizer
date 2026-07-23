# Release Readiness Reference

## Current facts

- Repository publication: Public
- Default branch: `main`
- License: `Apache-2.0`
- CI: Operational
- Initial release candidate: `v0.1.0-rc.1`
- Latest published prerelease: `v0.1.0-rc.2`
- Python package candidate version on `main`: `1.0.1`
- Latest stable release: `v1.0.0`
- Release classification: Public stable release, marked latest
- Stable tag commit: `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1`
- Attached assets: None; GitHub-generated source archives only
- PyPI packaging readiness: PASS on `main`
- PyPI publish execution readiness: P2 candidate preparation in progress;
  external operations not authorized
- PyPI distributions: None

Repository publication makes the source available for public maintenance. A Git
tag identifies a Git object, a GitHub Release is a separately created GitHub
artifact, and a versioned product release is a distinct project event. The
initial and latest Release Candidates remain prereleases and are not stable
releases. `v0.1.0-rc.2` was published from the exact reviewed commit after CI
and clean-clone validation, with no attached Release assets. `v1.0.0` is the
first stable release and is the current latest GitHub Release.

## Release readiness

The Human owner confirmed the redistribution rights applicable to predecessor-
derived responsibilities included in `v1.0.0` and approved the reviewed release
commit. M8.4 publication and M8.5 post-release validation are complete. Each
future release must still be assessed against the implementation, dependency
and notice inventory, rights position, security/privacy checks, review evidence,
and Human authorization applicable at that time. This status reference records
the current distinction; it does not create standing release authority.

The P0 packaging gate builds and validates both wheel and source distribution,
checks PyPI README rendering strictly, and installs each artifact in an isolated
environment. Passing that gate does not reserve the distribution name, choose a
publication version, configure credentials or Trusted Publishing, or authorize
an upload.

The P1 publication workflow is manual-only and defaults to build-only. Its
upload jobs require an exact reviewed source, target-specific Product approval
variable, protected GitHub Environment, and OIDC publisher match. These
repository controls are prepared but no external publisher/environment state
or package-index upload is authorized or completed.

P2 prepares `1.0.1` as the package-index patch candidate while keeping
`v1.0.0` as the current latest GitHub Release. The candidate does not itself
authorize its tag, GitHub Release, external publisher configuration, or either
initial package-index upload.
