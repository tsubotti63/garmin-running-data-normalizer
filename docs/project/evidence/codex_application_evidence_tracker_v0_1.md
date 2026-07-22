# Codex for Open Source Application Evidence Tracker v0.1

## Tracker contract

- Status: Active
- Baseline: `v0.1.0-rc.2`
- Evidence scope: Public or public-safe repository evidence only
- Application state: Not submitted

Each entry must identify a verifiable source, factual result, privacy review,
and relevance. Absence of feedback, adoption, or Issue history is recorded as
absence; it is never replaced by a fabricated proxy.

## Baseline evidence

| ID | Category | Evidence | Status | Application relevance |
|---|---|---|---|---|
| E-001 | Release | GitHub prerelease `v0.1.0-rc.2`, exact commit `0996c4889ae807be0082ae83a26319a860f62c96` | Verified | First multi-family public prerelease |
| E-002 | CI | GitHub Actions `bootstrap-ci / test`, run `29896162447` | PASS | Exact-candidate automated validation |
| E-003 | Testing | unittest 39/39 and pytest 39/39 in clean clone | PASS | Reproducible implementation quality |
| E-004 | Public reproduction | Synthetic Golden Path and Golden Result comparison | PASS | First-time-user reproducibility |
| E-005 | Orchestration | Run-All repeat, fixed layout, exit codes, and no-overwrite behavior | PASS | Operational contract evidence |
| E-006 | Privacy | Tracked-file scan, key-free examples, no Release assets, stable-key sharing warning | PASS | Public/private boundary evidence |
| E-007 | Real-export validation | Public-safe aggregate statement: unchanged input, two byte-identical outputs, privacy PASS | Verified | Compatibility evidence without private disclosure |
| E-008 | Analysis | Analysis Handoff, prompt, Public Usage Example, catalog, and three synthetic examples | Verified | Reusable downstream value evidence |
| E-009 | Case study | Garmin export to reproducible analysis handoff Primary Case Study | Verified | End-to-end product narrative |
| E-010 | Governance | Platform alignment, Target reviews, explicit lifecycle and release authority separation | Verified | Evidence-driven AI collaboration |
| E-011 | Post-release validation | Tag clone, links, Release metadata, tests, validators, Issues, and assets | PASS | Release-operation quality |

## Ongoing evidence queues

### OSS operation

| Candidate evidence | Current state | Required proof |
|---|---|---|
| Additional releases | None after RC2 | Tag, Release, exact CI, validation report |
| Issue response history | No open Issues at RC2 validation | Genuine Issue URL, triage, resolution, verification |
| CI reliability history | Baseline established | Run links, failures and resolutions where applicable |
| Community feedback | None recorded | Public source and consent-safe summary |
| External contribution | None recorded | PR, review, merge/reject rationale |

### Analysis and case studies

| Candidate evidence | Current state | Required proof |
|---|---|---|
| Additional synthetic analysis cases | Three baseline examples | Input, formula, result, limitation, privacy scan |
| Additional Primary Case Study | One baseline case | Reproduction path and factual outcome |
| Product improvement from analysis | Not yet recorded | Evidence-to-change trace and validation |
| External-sharing workflow | Not implemented | Separate specification, implementation, tests, privacy review |

## Entry template

- Evidence ID:
- Date:
- Category:
- Public source:
- Exact commit/release/run/issue:
- Factual result:
- Privacy classification:
- Validation or review:
- Application claim supported:
- Limitations:
- Status: Proposed / Verified / Superseded / Rejected

## Evidence integrity rules

- Use stable public links and exact identifiers when available.
- Keep private raw evidence outside the public repository.
- Do not publish personal rows, dates, filenames, paths, identifiers, counts,
  coordinates, or fingerprints.
- Separate observations from interpretation and application messaging.
- Preserve failed or superseded evidence with accurate status when it is
  material to the operational history.
- Human approval is required before application material is finalized or sent.
