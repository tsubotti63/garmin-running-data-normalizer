# Release Readiness

## Current repository state

- Public repository operation: Active
- Default branch: `main`
- License: `Apache-2.0`
- GitHub Actions: Operational
- Historical release candidate: `v0.1.0-rc.1` prerelease
- Latest published prerelease: `v0.1.0-rc.2`
- Python package candidate version on `main`: `1.0.1`
- Latest stable release: `v1.0.0`, published 2026-07-22
- GitHub Release: Public, stable, and marked latest
- Stable tag commit: `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1`
- Attached Release assets: None; GitHub-generated source archives only
- PyPI packaging readiness: PASS on `main`
- PyPI publish execution readiness: approved candidate; release and publisher
  configuration authorized, uploads not authorized
- PyPI distribution: None issued

The repository is public and under ongoing maintenance. `v1.0.0` is the first
stable release; its documented limitations remain active product boundaries.

## Current release assessment

`v0.1.0-rc.1` remains the bounded historical activities-only candidate.
`v0.1.0-rc.2` is the latest published prerelease for the multi-family Run-All,
M2.1 archive compatibility, private public-safe real-export evidence, Analysis
Handoff, and synthetic Case Study scope. Its tag points to the exact reviewed
commit and its GitHub Release contains no attached assets.

The Human owner confirmed the right to continue distributing the predecessor-
derived responsibilities included in this Target under Apache-2.0 and approved
the reviewed `v1.0.0` candidate for release. M8.4 publication and M8.5
post-release validation are complete. No PyPI publication was performed by this
workflow. Future releases still require their own current review and Human
authorization.

P0 adds repeatable wheel/source-distribution build, strict metadata and README
rendering checks, isolated artifact installation, and PyPI-safe README links.
These checks establish technical packaging readiness only. Selecting the first
PyPI version and source commit, configuring publisher trust, and uploading to an
index remain separate Human-authorized actions.

P1 adds a manual-only, build-only-by-default Trusted Publishing workflow and a
publication runbook. No GitHub Environment, approval variable, pending
publisher, API token, TestPyPI/PyPI project, or distribution was created.
Because the existing `v1.0.0` tag predates the P0 packaging changes, the
recommended first index release is a separately reviewed `1.0.1` patch. That
version/source choice, its tag and GitHub Release, external publisher
configuration, and each initial upload require explicit Product approval.

P2 prepared that `1.0.1` patch candidate without changing runtime behavior,
the stable `1.x` interface, runtime dependencies, or supported dataset scope.
The Human owner approved version `1.0.1` and candidate commit
`89677a78cd0e75c1ad168aca89b27724feb31013`, and authorized the final
release-state documentation, annotated tag, GitHub Release, protected GitHub
Environments, approval variables, and Trusted Publisher configuration.
TestPyPI upload is not yet authorized. Until the authorized tag and Release
operations complete, `v1.0.0` remains the latest stable GitHub Release; no
package-index distribution exists.
