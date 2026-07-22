# Release Candidate Checklist v0.1

Status values: `PASS`, `BLOCKED`, `PENDING`, `NOT_APPLICABLE`.

## Release readiness

| Check | Status | Evidence or required action |
|---|---|---|
| Run-All public contract matches implementation | PASS | Command, families, layout, status, and exit codes match the M2 specification |
| M3 real-export execution evidence | PASS | Public-safe status, immutability, rerun, and privacy facts are available |
| README reflects current validation | BLOCKED | Still says synthetic-only validation |
| Product Quick Start reflects current runner | BLOCKED | Still calls the current runner activities-only and real-data unvalidated |
| Analysis route from README | BLOCKED | Proposal exists but README is unchanged |
| Case Study route from README | BLOCKED | Proposal exists but README is unchanged |
| Current candidate is committed | BLOCKED | M4/M5 files are untracked |
| Current candidate is on `origin/main` | BLOCKED | Local main is two commits ahead before documentation |
| Exact candidate CI | BLOCKED | Latest public CI PASS covers an older remote commit |
| Public history for exact candidate | BLOCKED | Local `--ci` check reports origin/main does not match HEAD |
| Candidate version is unique | BLOCKED | Existing RC1 identifies an older snapshot; next version requires Human selection |
| Tag and release authorization | PENDING | Separate Human action after Go; no action in M5.5 |

## Quality

| Check | Status | Evidence or required action |
|---|---|---|
| unittest | PASS | 39/39 |
| pytest policy | PENDING | Current shell lacks pytest; exact candidate CI must install and run it |
| Bootstrap validation | PASS | Local validator PASS |
| Static policy | PASS | No violations |
| Platform alignment | PASS | No mismatches or metadata artifacts |
| Synthetic example arithmetic | PASS | Three examples independently recalculated |
| Markdown links in M4/M5 | PASS | No broken links in current worktree |
| Naming and required structure | PASS | Three four-file examples and all required Case Study sections exist |
| Historical RC1 documents remain truthful | PASS | They describe the tagged activities-only artifact |
| Current release-readiness wording | BLOCKED | Must distinguish RC1 history from the next candidate |

## Privacy

| Check | Status | Evidence or required action |
|---|---|---|
| Synthetic analysis samples only | PASS | All example dates and values are fictional |
| Stable key absent from examples | PASS | All three CSV headers verified |
| Raw/account IDs absent | PASS | Scan and header checks PASS |
| Absolute user paths absent | PASS | Scan result 0 |
| Email/credential patterns absent | PASS | Scan result 0 |
| Real data or private fingerprints tracked | PASS | None found |
| Entry-point stable-key warning | BLOCKED | README and Quick Start require corrected wording |
| External-sharing boundary | PASS | M4/M5 require approved key-free derivatives |

## OSS usability

| Check | Status | Evidence or required action |
|---|---|---|
| First-time installation path | PASS | Product Quick Start contains clone, venv, and editable install steps |
| Synthetic Golden Path | PASS | Documented and test-covered |
| Run-All path | PASS | Documented and test-covered; current wording requires corrections |
| Analysis examples | PASS | Three reusable examples |
| Decision-support value | PASS | One non-prescriptive example |
| Primary Case Study | PASS | Complete with reproduction steps |
| Root navigation | BLOCKED | README proposal not applied |
| Stable release claim avoided | PASS | Current materials retain prerelease boundary |

## Go checklist

- [ ] Apply README current-state, Analysis, and Case Study navigation updates.
- [ ] Align Product Quick Start with M2.1/M3 and stable-key privacy.
- [ ] Select a new prerelease identity without reusing RC1.
- [ ] Update package version and new release records consistently.
- [ ] Commit the complete reviewed candidate scope.
- [ ] Obtain separate authorization and push the candidate commit.
- [ ] Confirm `bootstrap-ci / test` PASS for the exact commit.
- [ ] Confirm public-history validation and local/remote commit equality.
- [ ] Obtain separate tag and GitHub Release authorization.

Until every pre-tag item is complete, the candidate remains `NO-GO`.
