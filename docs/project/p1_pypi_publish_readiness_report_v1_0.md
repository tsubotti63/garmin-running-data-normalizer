# P1 PyPI Publish Readiness Report v1.0

## Status

- Technical result: `PASS`
- P1 result: `P1_READY_FOR_APPROVAL`
- Upload workflow: prepared, manual-only, default build-only
- Recommended publication path: reviewed patch release, TestPyPI rehearsal,
  then PyPI through Trusted Publishing
- PyPI/TestPyPI upload: not performed
- External publisher/environment/approval-variable changes: not performed
- Tag or GitHub Release operation: not performed

## Goal assessment

P1 establishes the repository-controlled portion of a safe initial
package-index publication:

- an exact-source, exact-version build contract;
- a reversible build-only rehearsal;
- target-specific Product approval variables;
- protected GitHub Environment boundaries;
- tokenless OIDC publish jobs;
- automated post-publication install verification;
- explicit execution and failure-handling procedures; and
- a decision packet for the remaining Human-owned choices.

The workflow cannot upload by default. External approval configuration and each
initial upload remain outside autonomous authority.

## Current external state

At intake on 2026-07-23:

- PyPI project JSON endpoint: HTTP 404;
- TestPyPI project JSON endpoint: HTTP 404;
- GitHub Environments: none;
- latest P0 `bootstrap-ci`: run `29987671951`, `success`;
- `main == origin/main`:
  `29f1b0b811ae9657dd8a94c70c31e12ec1643437`;
- existing `v1.0.0` tag target:
  `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1`; and
- current public stable GitHub Release: unchanged.

No claim is made about unobservable PyPI account configuration. HTTP 404 and
the absence of GitHub Environments prove neither ownership nor reservation of
the package name.

## Safety properties

- No automatic push, pull-request, tag, or schedule trigger.
- Upload defaults to `false`.
- Full lowercase 40-character source SHA is required and verified after
  checkout.
- Upload fails unless both `github.ref` and the complete `github.workflow_ref`
  identify the reviewed workflow on `refs/heads/main`.
- Expected version is checked against both distribution filenames.
- Tests, build, strict Twine, isolated artifact installs, and SHA-256 logging
  precede any upload.
- The build artifact is created in a separate job and retained for one day.
- TestPyPI and PyPI have separate approval variables, environments, publish
  jobs, and verification jobs.
- Upload jobs use only `id-token: write`; no token/secret path exists.
- Actions are pinned to reviewed commit SHAs.
- Duplicate-version bypass through `skip-existing` is prohibited.

## Validation evidence

The uncommitted P1 candidate was overlaid on a clean archive of P0 `main` and
validated without dispatching the workflow or contacting an upload endpoint.

| Check | Result |
|---|---|
| Workflow YAML parse | PASS |
| `actionlint` v1.7.12 with verified download checksum | PASS |
| Workflow safety unit tests | PASS, 7/7 |
| Full unittest and pytest | PASS, 74/74 |
| Bootstrap, Platform, Static Policy, Public History | PASS |
| `git diff --check` and compileall | PASS |
| Clean-snapshot wheel and sdist build | PASS |
| Strict Twine check | PASS for both artifacts |
| Expected distribution count/version | PASS, one each at `1.0.0` |
| Isolated wheel/sdist install and `pip check` | PASS |
| Metadata/library version and console command | PASS, `1.0.0` |
| TestPyPI/PyPI upload or workflow dispatch | NOT PERFORMED |

Build-only validation artifact SHA-256 values:

- wheel:
  `4a6d9fd600b2fc449e75c1c80d5c1f6c8eef5525e925d6aa27cdb96739847926`
- sdist:
  `ac41bc0792bb3d855a113e295fe1aa22f2b2a5b970d13c00fda5986a945808a4`

These temporary files are readiness evidence only. They are not approved
publication artifacts, and a future approved immutable source must be rebuilt
and checked independently.

## Exit criteria

| Criterion | Result |
|---|---|
| Publication procedure established | PASS |
| Ready for execution after Product decisions/configuration | PASS |
| Post-publication checks defined and automated | PASS |
| Documentation updated | PASS |
| Stable API/product behavior preserved | PASS |
| Packaging metadata/artifacts changed by P1 | NO |
| Irreversible operation performed | NO |

## Human Approval Boundary

P1 stops before:

1. selecting `1.0.0` source divergence versus the recommended `1.0.1` patch;
2. requiring or waiving a TestPyPI rehearsal;
3. selecting Trusted Publishing versus an API Token fallback;
4. creating GitHub Environments or changing approval variables;
5. creating pending PyPI/TestPyPI publishers;
6. changing version, tag, or GitHub Release state; and
7. performing either initial upload.

The recommended decision is:

- create a separately reviewed `1.0.1` patch from post-P0 `main`;
- use a new immutable tag and aligned GitHub Release after approval;
- configure Trusted Publishing with protected `testpypi` and `pypi`
  Environments;
- require TestPyPI PASS before a separately approved production upload; and
- record the exact uploaded hashes and attestations.

## Decision

The repository-controlled publication mechanism and operating procedure are
ready for independent review. P1 is `P1_READY_FOR_APPROVAL`, not published.
The next event must be an explicit Product decision covering the exact
version/source, TestPyPI requirement, authentication/configuration, and the
specific irreversible upload.
