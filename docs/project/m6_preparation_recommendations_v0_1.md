# M6 Preparation Recommendations v0.1

## Purpose

This document orders the work required to convert the current healthy local
M2.1–M5 state into a reviewable Release Candidate. It does not authorize Git,
GitHub, tag, release, or application actions.

## Recommended sequence

### 1. Align public entry-point documentation

- Apply the reviewed M5 README proposal.
- Update Product Quick Start to remove synthetic-only and activities-only claims
  that no longer describe current Run-All.
- Correct Activities CSV privacy wording: no separate `activity_id` column
  exists, but `garmin_activity_key` may incorporate the source activity ID.
- Link Analysis Handoff, all three examples, and the Primary Case Study.
- Preserve the private-real-evidence versus public-synthetic-example boundary.

Expected ownership: Work/documentation task. No feature code required.

### 2. Select the next Release Candidate identity

The existing `v0.1.0-rc.1` tag is immutable historical evidence for an older
scope. Human must select a new prerelease identity before version files are
changed. Do not move, delete, or reuse RC1.

Expected ownership: Human decision, followed by a bounded release-preparation
task.

### 3. Align release metadata after the decision

- Update the Python package version for the selected candidate.
- Add a new release note; do not rewrite RC1 history.
- Add factual M2/M2.1/M3/M4/M5 entries to Product Change History.
- Update Release Readiness to distinguish the historical RC1 from the new
  candidate.
- Confirm dependency and license statements remain current.

Expected ownership: bounded configuration/documentation task. No new product
feature is implied.

### 4. Create one reviewable candidate snapshot

- Include the reviewed M2/M2.1 commits and M4/M5 artifacts.
- Include only the approved README, Quick Start, and release-metadata changes.
- Verify no unrelated files enter the candidate.
- Run unittest, pytest in the project test environment, Bootstrap, Static
  Policy, Platform alignment, link/structure checks, privacy scan, and synthetic
  arithmetic checks.

Commit remains subject to current Target governance and Human/review authority.

### 5. Validate the exact public candidate

After separate push authorization:

- push without force, amend, rebase, or tag;
- wait for `bootstrap-ci / test` on the exact commit;
- stop on any failure without speculative additional release action;
- confirm local HEAD equals `origin/main` and public-history validation passes;
- submit the frozen candidate evidence for a final Release Candidate review.

### 6. Separate tag, GitHub Release, and M6 application authority

A candidate CI PASS does not itself authorize a tag, GitHub Release, or M6
application. Each action requires explicit Human direction. The selected tag
must point to the exact reviewed commit and must not be created before CI PASS.

## Recommended M6 evidence set

- Exact candidate commit and version.
- GitHub Actions run URL and successful job conclusion.
- Local/remote equality and public-history PASS.
- Test and validator results.
- Public-safe M3 execution report and note.
- M4 Analysis Handoff and Public Usage Example.
- Three synthetic M5 examples and verified arithmetic.
- Primary Case Study and README navigation.
- License, dependency, privacy, and known-limitation statements.
- Explicit record that real exports and output remain private.

## Minor improvements that may be deferred

- Add `examples/analysis/README.md`.
- Add Analysis and Case Study sections to `docs/README.md`.
- Consolidate duplicate README proposal wording after application.
- Evaluate an external-sharing-safe derivative exporter as a future feature.

These items should not be bundled into candidate preparation unless they remain
small, reviewed, and do not delay blocker resolution.

## Current M6 readiness

**Not ready.** Resolve the three integration classes first: public documentation
alignment, new RC identity, and exact candidate commit/CI verification.
