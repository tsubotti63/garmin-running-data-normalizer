# Release Candidate Validation Report v0.2

## Validation target

- Candidate: `v0.1.0-rc.2`
- Python package version: `0.1.0rc2`
- Commit: `0996c4889ae807be0082ae83a26319a860f62c96`
- Branch: `main`
- Validation date: 2026-07-22
- Result: **PASS**

The validation target was the exact public `origin/main` commit. The working
tree was clean before this report was created, local `HEAD` equaled
`origin/main`, `v0.1.0-rc.1` remained on its historical commit, and no
`v0.1.0-rc.2` tag or GitHub Release existed.

## Validation environments

1. A new clone made through the public HTTPS repository URL on macOS, using
   Python 3.11.9 and pytest 8.4.2.
2. GitHub Actions workflow `bootstrap-ci`, job `test`, on the exact candidate
   commit.
3. The maintained local checkout for tracked-file, history, identity, and
   privacy inspection.

No real Garmin export was used. All executable reproduction used tracked
synthetic fixtures.

## Executed validation

| Area | Check | Result |
|---|---|---|
| Repository | `main`, exact `HEAD`, `origin/main` equality, clean pre-report worktree | PASS |
| Identity | Git author and committer use the established GitHub noreply identity | PASS |
| Release lifecycle | RC1 preserved; RC2 tag and GitHub Release absent | PASS |
| Installation | Fresh virtual environment and editable install with test extra | PASS |
| Unit tests | Standard-library discovery, 39 tests | PASS |
| Pytest | pytest 8.4.2, 39 tests | PASS |
| Bootstrap | `scripts/validate_bootstrap.py` | PASS |
| Static policy | `scripts/static_policy_scan.py` | PASS |
| Platform | `scripts/validate_platform_alignment.py` | PASS |
| Public history | `scripts/validate_public_history.py --ci`; 22 reachable commits, 279 objects, 4 refs | PASS |
| Golden Path | Synthetic Activities command and reviewed Golden Result comparison | PASS |
| Golden repeat | Independent second output matched byte-for-byte | PASS |
| Run-All | Activities-only tracked fixture returned `PASS_WITH_WARNINGS`, exit 0 | PASS |
| Run-All repeat | Independent second output matched byte-for-byte | PASS |
| No overwrite | Reuse of the populated Run-All destination was rejected with exit 2 | PASS |
| Output layout | Eleven documented files, including last-written `run_summary.json` | PASS |
| Documentation links | 39 relative links across 11 entry-point, analysis, example, case-study, and RC documents | PASS |
| RC1 history | RC1 release-note bytes unchanged at the candidate commit | PASS |

The clean-clone Run-All digest was
`b07f035e4017bc88642c1c9e8e8598681e7b52cacf6e4662585df44ff7ae211e`.
The Golden Path records digest was
`30718efb955f05568178b6d9f2395a10a3dd44508d3658e3090ee6975d4cbaf6`.

## Public Contract assessment

**PASS.** The implementation, tests, README, Product Quick Start, Analysis
Handoff, and RC2 release note agree on the following bounded contract:

- Activities remain the required Golden Path and Run-All family.
- Gear, Personal Records, and bounded FIT sessions/laps are optional Run-All
  families.
- Stable keys, record grain, source-relative provenance, deterministic QA, and
  manifests are present and test-covered.
- Run-All publishes a fixed layout and writes `run_summary.json` last.
- Exit 0 represents `PASS` or `PASS_WITH_WARNINGS`, exit 2 is fatal, and exit 3
  is auditable `PARTIAL_SUCCESS` for incomplete FIT parsing.
- Existing output is not silently overwritten.
- Archive traversal, link, encryption, count, per-member size, total size, and
  compression-ratio protections remain covered by negative tests.
- Hosted processing, account authentication, complete FIT support, weather,
  Parquet, automatic Analysis Pack generation, stable API guarantees, stable
  release, and PyPI publication are not claimed.

## Privacy assessment

**PASS.** The 186 tracked files were inspected together with the candidate
diff and public examples.

- No absolute user or home path was found.
- No email address, credential/token prefix, known private count, or private
  fingerprint was found.
- No raw Garmin export, generated personal output, FIT file, or ZIP export is
  tracked.
- The three public Analysis CSV samples omit `garmin_activity_key` and
  `activity_id`; their headers are key-free and no coordinate-like value was
  found.
- The repository and examples state that real exports and outputs remain
  local, and that `garmin_activity_key` and date/time granularity require
  review before external sharing.
- The Analysis Pack builder accepts only an explicit caller allowlist and the
  `.csv`, `.json`, and `.md` suffixes.
- The GitHub workflow contains no artifact-upload step for generated output.
- Public-history validation passed for the exact public candidate.

## CI assessment

**PASS.** GitHub Actions run `29896162447` executed workflow `bootstrap-ci` on
`0996c4889ae807be0082ae83a26319a860f62c96`. Job `test` completed successfully.
Checkout, installation, Bootstrap, Platform alignment, Static Policy, Public
History, and pytest steps all succeeded. No failed or skipped required
validation remained.

## Clean Clone assessment

**PASS.** A normal public clone could follow the documented setup, execute the
Golden Path, compare the Golden Result, perform a deterministic repeat, run the
minimum multi-family workflow, inspect its fixed layout and completion marker,
and observe the documented non-overwrite behavior and exit codes.

Editable installation creates an untracked
`src/garmin_running_data_normalizer.egg-info/` directory because that standard
build metadata path is not currently ignored. This does not affect package
execution, tracked content, validators, deterministic product output, or the
source candidate. It is a minor repository-hygiene improvement, not a release
blocker.

## Documentation and analysis routes

**PASS.** The root README gives a first-time user direct routes to current
status, supported datasets, the Synthetic Golden Path, Run-All, Product Quick
Start, the Primary Case Study, Analysis Handoff, all three Analysis Examples,
local verification, known limitations, non-goals, the Apache-2.0 license, and
the project map.

The Product Quick Start contains copyable setup and synthetic commands, Golden
Result comparison, repeat validation, Run-All layout and exit behavior,
privacy guidance, and limitations. The Analysis Handoff Specification, prompt
template, Public Usage Example, use-case catalog, and three examples separate
facts/calculations from interpretation and unknowns. They do not claim
byte-identical generative prose.

## Residual risks

- FIT support remains intentionally bounded and does not implement complete
  CRC or invalid-sentinel behavior.
- The editable-install `*.egg-info/` ignore gap is minor repository hygiene.
- Bootstrap output retains the legacy
  `LOCAL_IMPLEMENTATION_NOT_PUBLICATION_READY` implementation-status label
  while separately reporting lifecycle `post-public`, license `APACHE_2_0`,
  and overall `PASS`. Renaming that governance contract requires a separate
  lifecycle decision and is not a product-quality blocker for this RC.
- No stable release, stable third-party Python API, PyPI publication, hosted
  service, or external-sharing-safe derivative exporter is included.

## Conclusion

No release-blocking product, contract, privacy, CI, clean-clone, or
documentation defect was found. The exact candidate satisfies the M5.5B Phase
3 `GO` criteria. Tag creation and GitHub Release publication remain separate
Human-owned actions.
