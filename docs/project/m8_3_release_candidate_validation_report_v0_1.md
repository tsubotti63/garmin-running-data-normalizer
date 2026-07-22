# M8.3 Release Candidate Validation Report v0.1

- Candidate: `v1.0.0`
- Validated commit: `54a757d5e558a4676c7b1d15b3182b994439f763`
- Validation date: 2026-07-22
- Status: `PASS`
- Release boundary: `READY_FOR_HUMAN_APPROVAL`

## Candidate identity

The validated branch is `main`, local `HEAD` equals `origin/main`, and the
worktree is clean. The package, import, and CLI all report version `1.0.0`.
No `v1.0.0` tag or GitHub Release was created during M8.1-M8.3.

## Clean-state validation

An equivalent clean checkout was created from `git archive HEAD` in a temporary
directory. A new virtual environment installed the project with its test extra.
The clean candidate produced these results:

- editable installation: PASS
- package import and version: PASS (`1.0.0`)
- console entry point and `--version`: PASS (`1.0.0`)
- `unittest`: PASS (64 of 64)
- `pytest`: PASS (64 of 64)
- bootstrap validation: PASS (`STABLE_RELEASE_READY`)
- static policy scan after editable installation: PASS
- synthetic Run-All: `PASS_WITH_WARNINGS`, exit 0
- Platform alignment in the exact Git checkout: PASS
- public-history validation in CI mode: PASS

The clean archive intentionally contains no `.git` directory. Validators that
inspect Git refs or the tracked Platform file set were therefore run in the
exact clean working clone at the same commit.

## Distribution inspection

The source distribution and wheel built successfully from the clean candidate.
The wheel contains the package modules, console entry point, metadata, and
Apache-2.0 license. The package metadata declares no runtime dependency.

| Artifact | SHA-256 |
|---|---|
| `garmin_running_data_normalizer-1.0.0-py3-none-any.whl` | `2aa88443c43b03952ae2ab3804b139781db098c77afb25e0a81a99194683ac35` |
| `garmin_running_data_normalizer-1.0.0.tar.gz` | `6b1a659e55ea58b6ab95009c4afa6b2e56c7c39f4936a12967ea8deb65b60b6d` |

These local validation artifacts are evidence only. They were not attached to
a GitHub Release or published to a package index.

## CI correction and final workflow

The first M8.2 preparation run exposed one CI-only false positive: editable
installation generated `src/*.egg-info/PKG-INFO`, and the static policy scan
treated that generated metadata as product source. Commit
`54a757d5e558a4676c7b1d15b3182b994439f763` narrowly excludes `.egg-info`
components while regression coverage confirms ordinary product source remains
scanned.

GitHub Actions workflow `bootstrap-ci`, run
[`29926407948`](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/runs/29926407948),
completed successfully for that correction commit.

## Documentation, boundary, and regression assessment

- README installation, CLI, supported scope, and limitations match the
  implemented candidate.
- Supported-dataset and known-limitation references do not claim unsupported
  hosted, PyPI, weather, FIT CRC, or Run-All dataset behavior.
- Only synthetic fixtures and public-safe aggregate evidence are tracked.
- No secret, credential, raw private export, personal output, or private source
  history is required to install, test, or use the candidate.
- The complete local suite and the final GitHub Actions workflow passed after
  the correction; no product regression remains open.

## Remaining non-blocking gaps

Complete FIT CRC validation, multi-session FIT identity, hosted processing,
Open-Meteo integration, Parquet output, and PyPI publication remain documented
post-Stable or future-roadmap work. Sleep, HRV, and Health Status remain
library-level dataset families rather than Run-All inputs.

## Decision

M8.1, M8.2, and M8.3 are complete. The exact candidate is technically ready
for the separate Human decision on creating and pushing tag `v1.0.0`, publishing
the GitHub Release, and marking it as the latest release. This report does not
authorize any of those actions.
