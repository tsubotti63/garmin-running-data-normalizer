# P2 Initial PyPI Publication Readiness Report v1.0

## Status

- Phase: P2 initial PyPI publication
- Candidate version: `1.0.1`
- Candidate source at report freeze: uncommitted frozen candidate over base
  `ed9656c459de85dd278f7a5c046ba149c36bd028`; the final commit is assigned
  only after Target Core Review `PASS`
- Technical validation: `PASS`
- Unit Review at report freeze: `PASS`
- Target Core Review at report freeze: pending
- Tag/GitHub Release: not created
- External publication configuration: not changed
- TestPyPI/PyPI upload: not performed

## Starting evidence

At P2 intake on 2026-07-23:

- `main == origin/main`:
  `ed9656c459de85dd278f7a5c046ba149c36bd028`;
- P1 Target Core Review: `PASS`;
- P1 build-only publication rehearsal:
  workflow run `29989857313`, `success`;
- PyPI project JSON endpoint: HTTP 404;
- TestPyPI project JSON endpoint: HTTP 404;
- GitHub Environments: 0;
- GitHub Actions repository variables: 0;
- latest stable GitHub Release: `v1.0.0`, non-draft and non-prerelease; and
- stable `v1.0.0^{}` target:
  `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1`.

The HTTP responses are point-in-time observations and do not prove ownership
or reserve the project name. PyPI account-side publisher state is not
observable through the public project endpoint and is not claimed.

## Candidate scope

P2 prepares `1.0.1` as the recommended initial package-index patch:

- package, import, CLI, and exact-version test identities advance together;
- runtime code behavior and the stable `1.x` interface do not change;
- runtime dependencies remain empty;
- Apache-2.0 and predecessor-rights evidence remain unchanged;
- supported datasets, Run-All, privacy, and synthetic-only public evidence
  boundaries remain unchanged; and
- release notes and current-state documents distinguish the prepared candidate
  from the still-current `v1.0.0` GitHub Release.

## Validation plan

Before any irreversible or external operation:

1. run the complete unittest and pytest suites;
2. run Bootstrap, Platform Alignment, Static Policy, and Public History
   validators;
3. apply `actionlint` and `git diff --check`;
4. build one `1.0.1` wheel and one `1.0.1` source distribution from a clean
   snapshot;
5. run strict Twine checks;
6. install and exercise both artifacts in isolated Python 3.11 environments;
7. record exact filenames and SHA-256 values;
8. complete independent Unit Review and Target Core Review; and
9. commit, push, confirm CI, and run `perform_upload=false` from the exact
   reviewed commit.

## Human Approval Boundaries

P2 must stop before:

1. creating or pushing `v1.0.1`;
2. publishing a `v1.0.1` GitHub Release;
3. creating or changing GitHub Environments or approval variables;
4. creating or changing a TestPyPI/PyPI Trusted Publisher;
5. performing the initial TestPyPI upload; and
6. performing the initial production PyPI upload.

The recommended sequence after the candidate is ready:

1. approve the exact `1.0.1` source and tag/Release preparation;
2. approve protected `testpypi` and `pypi` Environments plus Trusted
   Publishers;
3. stop again for approval of the exact TestPyPI upload;
4. verify TestPyPI project metadata, artifact hashes, clean install, import,
   version, and CLI; and
5. stop again for the separate production PyPI upload approval.

No API Token fallback is prepared. Any fallback from Trusted Publishing
requires a separate credential-handling decision and review.

## Pre-review validation evidence

| Check | Result |
|---|---|
| `actionlint` for repository workflows | PASS |
| Full stdlib unittest | PASS, 74/74 |
| Full pytest | PASS, 74/74 |
| Bootstrap validator | PASS |
| Platform Alignment validator | PASS |
| Static Policy scan | PASS |
| Public History validator (`--ci`) | PASS |
| `git diff --check` and compileall | PASS |
| Clean-snapshot wheel and source-distribution build | PASS |
| Strict Twine check | PASS for both artifacts |
| Artifact count and version | PASS, one each at `1.0.1` |
| Isolated wheel install, `pip check`, metadata/import/CLI | PASS |
| Isolated sdist install, `pip check`, metadata/import/CLI | PASS |

Temporary build-only artifact SHA-256 values:

- `garmin_running_data_normalizer-1.0.1-py3-none-any.whl`:
  `11d7e7b7ff4e39229a38c0820b71caa4da32d2db3cdac979e93199527ba6e739`
- `garmin_running_data_normalizer-1.0.1.tar.gz`:
  `e42188e7be15b55f0fdbaee42b526a9e84625e33af5d796f2dbb9151fc56ceab`

These files are review evidence only. Approved publication artifacts must be
rebuilt from the final immutable source and independently matched before
upload.
