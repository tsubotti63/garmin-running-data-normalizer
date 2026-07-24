# Release Readiness

## Current repository state

- Public repository operation: Active
- Default branch: `main`
- License: `Apache-2.0`
- GitHub Actions: Operational
- Python package candidate version on `main`: `1.1.1`
- Latest GitHub Release: `v1.1.0`, published 2026-07-24
- Latest GitHub Release tag commit:
  `821fbc9d41ea349aaf43613191555a14aed9735c`
- GitHub Release: Public, non-prerelease, and marked latest
- Attached Release assets: None; GitHub-generated source archives only
- PyPI packaging readiness: PASS on `main`
- TestPyPI: `1.1.0rc1` published and clean-install verified by workflow
  `30067134651`
- Production PyPI distribution: None; the project endpoint returned 404 at
  `v1.1.1` preparation intake
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use
- `v1.1.1` tag, GitHub Release, TestPyPI upload, and Production PyPI upload:
  Not performed and separately Human-gated

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. The `v1.1.1` candidate is the first
stable Production package candidate for the reviewed v1.1 implementation.

## Current release assessment

The reviewed v1.1 implementation passed tests, validators, public/private
boundary checks, real-export acceptance, packaging checks, and Target review.
The `v1.1.0` tag and GitHub Release were then published from commit
`821fbc9d41ea349aaf43613191555a14aed9735c`. That tagged source declares package
version `1.1.0rc1`. The tag and Release remain immutable and are not rewritten
to manufacture a stable package artifact.

TestPyPI publication of `1.1.0rc1` passed exact-source build, strict metadata,
wheel and sdist installation, Trusted Publishing, and post-upload clean-install
verification. Those files are rehearsal evidence only and are not reused or
renamed as stable artifacts.

The Human owner therefore selected `1.1.1` for stable Production package
preparation. This version-finalization change updates declared identity and
release metadata without changing runtime behavior or the stable `1.x`
interface. Full tests, package builds, isolated installs, installed Run-All,
validators, review, commit, push, and CI are required before requesting
`v1.1.1` publication approval.

Passing those checks does not create the `v1.1.1` tag or GitHub Release and does
not authorize either package-index upload. Each remains a separate Human
Approval Boundary.
