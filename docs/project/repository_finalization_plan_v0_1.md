# Repository Finalization Plan v0.1

## Purpose

Convert the current healthy local M2.1–M5.5 state into one reviewable Release
Candidate candidate without rewriting history, reusing the existing RC1 tag, or
performing an unauthorized Git or GitHub action.

## Current baseline

- Local `main` is two commits ahead of `origin/main`:
  - M2 Run-All implementation
  - M2.1 archive compatibility patch
- M4, M5, M5.5, and this M5.5A planning set are not yet committed.
- The public repository and Apache-2.0 license are active.
- `v0.1.0-rc.1` is an immutable historical tag for the older activities-only
  candidate.
- Local unit tests and repository validators pass, but the combined local state
  has not run in public CI.

## Finalization objectives

1. Preserve the existing M2 and M2.1 commits unchanged.
2. Turn M4/M5/M5.5 documentation and synthetic examples into reviewable,
   topic-bounded commits.
3. Apply the final README, Product Quick Start, and documentation-navigation
   corrections.
4. Obtain a Human decision for the next RC identity.
5. Align version and release metadata only after that decision.
6. Produce one exact candidate commit for clean-clone and GitHub Actions
   validation.
7. Keep push, tag, GitHub Release, and M6 submission as separately authorized
   lifecycle actions.

## Work sequence

### Stage 1 — Freeze the current planning inventory

- Record every M4–M5.5A path and SHA-256.
- Confirm no real export, generated personal output, private Evidence, or
  `.DS_Store` is present.
- Confirm M2 and M2.1 commit IDs have not changed.

### Stage 2 — Apply public documentation alignment

- Update root README using `readme_final_update_plan_v0_1.md`.
- Align Product Quick Start with current Run-All and M3 validation.
- Add Analysis and Case Study navigation without modifying Platform Standard
  documents.
- Correct stable-key privacy wording everywhere users may infer that the
  Activities CSV is externally shareable as-is.

### Stage 3 — Resolve RC identity

- Human selects the next prerelease identity.
- Recommended candidate: `v0.1.0-rc.2` / Python `0.1.0rc2`.
- Do not edit version files or release notes before that decision.
- Do not move, delete, or reuse `v0.1.0-rc.1`.

### Stage 4 — Align release metadata

- Update `pyproject.toml` to the selected Python version.
- Add a new release note for the selected candidate.
- Add factual M2–M5 changes to Product Change History.
- Update Release Readiness to distinguish historical RC1 from the new
  candidate.
- Preserve RC1 release notes and tag history unchanged.

### Stage 5 — Build the candidate snapshot

- Follow the bounded commit groups in `commit_and_push_plan_v0_1.md`.
- Review staged paths before every commit.
- Do not amend, rebase, squash, force-push, or tag.
- Stop if an unexpected tracked or untracked file enters a commit group.

### Stage 6 — Validate before any push

- Run unittest and pytest in the declared Python environment.
- Run Bootstrap, Static Policy, Platform alignment, link/structure, privacy,
  synthetic arithmetic, and diff checks.
- Validate in a clean clone or equivalent detached snapshot.
- Confirm working tree clean and branch `main`.

### Stage 7 — Push and public CI under separate authority

- Push only after explicit Human authorization.
- Push `main` without force.
- Wait for `bootstrap-ci / test` on the exact candidate commit.
- Confirm local HEAD equals `origin/main` and public-history validation passes.
- Do not create a tag or GitHub Release during the push step.

### Stage 8 — M5.5B review

M5.5B uses `m5_5b_validation_plan_v0_1.md` to return `GO`, `REWORK`, or
`HUMAN_DECISION_REQUIRED`. A CI PASS is required but does not alone authorize a
tag, GitHub Release, or M6 submission.

## Privacy and public boundary

- Only synthetic example rows may be tracked.
- Real M3 output remains local and Git-ignored.
- Public M3 claims remain limited to status, exit code, input immutability, two
  byte-identical runs, privacy PASS, and the bounded archive fix.
- `garmin_activity_key` may contain a source activity ID and must be removed
  from an externally shared derivative.
- No private path, filename, record count, date range, record value, or private
  fingerprint enters release documentation.

## Exit criteria

This finalization plan is complete when documentation alignment, RC identity,
release metadata, commit creation, clean-clone checks, authorized push, and
exact-candidate CI have all completed with evidence. Until then, Release
Candidate status remains No-Go.
