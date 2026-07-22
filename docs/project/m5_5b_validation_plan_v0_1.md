# M5.5B Validation Plan v0.1

## Purpose

Define the independent validation required after repository finalization and
before any Release Candidate tag, GitHub Release, or M6 action.

M5.5B does not inherit a Go verdict from M5.5A. It returns one of:

- `GO`
- `REWORK`
- `HUMAN_DECISION_REQUIRED`

## Preconditions

- Human has selected the next RC identity.
- README, Product Quick Start, and approved navigation changes are applied.
- Version and new release metadata match the selected identity.
- M2–M5.5A candidate scope is committed.
- Worktree is clean.
- Candidate commit is pushed only if separately authorized.
- No candidate tag or GitHub Release exists before validation.

If preconditions are incomplete, M5.5B returns `REWORK` or
`HUMAN_DECISION_REQUIRED`; it does not repair or publish the candidate.

## Validation matrix

### Git and identity

- Branch is `main`.
- Exact candidate commit is recorded.
- Local HEAD equals `origin/main` after authorized push.
- No force-push, rebase, amend, or squash was used.
- Existing RC1 tag still points to its historical commit.
- Selected next RC tag does not yet exist.
- Git author and committer identity use the established GitHub noreply identity.

### Version and release records

- Git candidate label, Python package version, release note, Release Readiness,
  Product Change History, and README use the selected identity consistently.
- RC1 release note remains unchanged and historically accurate.
- New release note describes Run-All, M2.1, M3 public-safe evidence, M4/M5
  analysis value, privacy, and known limitations without overclaiming.
- Stable release and PyPI publication remain explicitly absent.

### Documentation and OSS usability

- New user can reach Product Quick Start from README.
- New user can reach Run-All, Analysis Handoff, all three examples, and Primary
  Case Study from README.
- All relative links resolve in a clean clone.
- README and Quick Start contain identical current-state and privacy wording.
- No historical Phase or RC1 record is incorrectly rewritten as current policy.

### Public contract

- Run-All command, required/optional families, fixed output layout, status,
  exit codes, no-overwrite behavior, and deterministic rerun claims match code
  and tests.
- Activities CSV columns match `ACTIVITIES_CSV_COLUMNS`.
- Stable-key privacy warning matches the current identity implementation.
- M4/M5 do not claim a new CLI, schema, normalizer, exporter, or dashboard.

### Privacy

- Only synthetic fixtures and examples are tracked.
- Analysis CSV samples have no `garmin_activity_key` or `activity_id`.
- No account ID, raw record, coordinate, real date combination, absolute user
  path, email, credential, token, cookie, private count, or private fingerprint
  appears in the candidate diff.
- M3 Evidence claims remain aggregate and public-safe.
- No CI artifact uploads generated personal output.

### Tests and validators

Run in a clean clone with Python 3.11:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m unittest discover -s tests
python -m pytest
python scripts/validate_bootstrap.py
python scripts/static_policy_scan.py
python scripts/validate_platform_alignment.py
python scripts/validate_public_history.py --ci
```

Also run:

- synthetic Golden Path byte comparison;
- Run-All activities-only example and repeat-run byte comparison;
- M5 analysis-example arithmetic recalculation;
- Markdown link and final-newline checks;
- staged/candidate path inventory and privacy scan.

### GitHub Actions

- Workflow: `bootstrap-ci`.
- Required job: `test`.
- Run head SHA exactly equals the candidate commit.
- Status is completed and conclusion is success.
- No skipped required step or unexpected annotation exists.

## Evidence package

Record:

- candidate version, commit, branch, and author/committer identity;
- local/remote equality;
- changed-file inventory and hashes;
- every test/validator result;
- clean-clone environment summary;
- GitHub Actions run ID, URL, head SHA, job, and conclusion;
- privacy and link-scan summaries;
- known limitations and deferred improvements;
- explicit confirmation that no tag or Release was created during validation.

## Verdict rules

### GO

All required checks pass, exact candidate CI succeeds, public/privacy boundaries
hold, no blocker remains, and any remaining improvements are demonstrably
non-blocking.

### REWORK

A bounded documentation, metadata, link, test, CI, or consistency defect can be
fixed without changing Human-owned values or scope.

### HUMAN_DECISION_REQUIRED

RC identity, release risk, rights, privacy boundary, scope, or authorization
cannot be resolved from existing decisions.

## Handoff after GO

GO means the exact candidate may be considered for separately authorized tag
and GitHub Release actions. It does not itself authorize those actions or M6
submission.
