# Release Candidate Readiness Review v0.1

## Review scope

This review integrates the current local implementation through M2.1, the
public-safe M3 execution evidence, the uncommitted M4/M5 documentation and
synthetic examples, the public README and Product Quick Start, the existing
release records, license, CI configuration, local tests, and repository
validators.

Reviewed local implementation snapshot:

- Branch: `main`
- HEAD: `2d871ac9abcea853731ff3a1c191db415f974c31`
- Existing release tag: `v0.1.0-rc.1`, pointing to an older activities-only
  snapshot
- Local branch state: two commits ahead of `origin/main`
- M4/M5 state: 22 new public documentation/example files not yet committed

## Executive finding

**Verdict: NO-GO. The current combined M2.1–M5 state is not yet a publishable
Release Candidate snapshot.**

The product implementation, synthetic examples, and privacy controls reviewed
here are healthy. The blockers are release integration and public contract
alignment: current work is not represented by one committed and CI-tested
public snapshot, entry-point documentation contains obsolete or misleading
statements, and the existing RC tag identifies a different product scope.

## Evidence that passed

### Implementation and local quality

- Standard-library unit suite: 39/39 passed.
- Bootstrap validation: PASS.
- Static policy scan: PASS.
- Platform alignment: PASS.
- M3 public-safe evidence records status `PASS`, exit code `0`, unchanged input,
  two independent byte-identical outputs, and privacy check PASS.
- M2.1 resolved the observed archive compatibility gap without removing the
  remaining bounded archive safety controls.

The current shell environment does not have pytest installed. This is not a
test failure: the unittest suite passed, and the public CI workflow installs the
test extra before running pytest. The current local combined snapshot still
requires a fresh CI run after it is committed and pushed.

### M4 and M5 value artifacts

- Three analysis examples contain only synthetic future dates and key-free CSV
  samples.
- Each example separates Observed Facts, Interpretation, Uncertainty,
  Unsupported Conclusions, and Possible Next Questions.
- The decision-support example lists human-owned options without medical,
  coaching, injury, overtraining, or readiness claims.
- Primary Case Study, Analysis Handoff, prompt template, Evidence Index, and
  README proposal are mutually linked and structurally complete.
- Independent arithmetic checks passed for all three examples.

### Privacy and license

- New M4/M5 files contain no absolute user path, email pattern, credential
  pattern, known private real-data count, raw activity/account ID, or real
  record content.
- Example CSVs contain neither `garmin_activity_key` nor `activity_id`.
- Apache License 2.0 is present and the Python project declares no runtime
  dependency.
- No real Run-All output or M3 private fingerprint is tracked.

## Release blockers

### B1 — No committed, public, CI-tested candidate snapshot

The local branch is two commits ahead of `origin/main`, and the M4/M5 artifacts
are untracked. The latest public `bootstrap-ci` run succeeded for the current
remote `main`, not for M2, M2.1, M4, or M5. Local public-history validation also
fails because `origin/main` does not match local HEAD.

Required resolution:

1. Complete the documentation corrections below.
2. Commit the reviewed M4/M5 and release-preparation scope intentionally.
3. Push only under separate Human authorization.
4. Require the resulting `bootstrap-ci / test` job to pass for that exact
   candidate commit.
5. Confirm local HEAD, `origin/main`, and the reviewed commit are identical
   before any tag or GitHub Release action.

### B2 — Public entry-point documentation is not current

README and Product Quick Start conflict with the implemented and evidenced
state:

- README says Run-All was validated only with synthetic fixtures.
- README repeats that real-export validation has not occurred.
- Product Quick Start calls the current runner activities-only even though the
  formal Run-All command supports Activities plus optional Gear, Personal
  Records, and bounded FIT sessions/laps.
- Product Quick Start says the workflows have not been validated against real
  Garmin data.
- README and Product Quick Start say the Activities CSV excludes Garmin
  activity IDs without explaining that `garmin_activity_key` may incorporate
  the source activity ID.
- README has no route to the Analysis Handoff, three analysis examples, or
  Primary Case Study.

Required resolution:

- Apply the reviewed M5 README proposal in a focused documentation change.
- Align Product Quick Start with the same current Run-All, M3 evidence, and
  stable-key privacy wording.
- Preserve the distinction between public synthetic reproduction and private
  public-safe real-export evidence.
- Re-run link, privacy, test, and repository validation after the edits.

### B3 — Existing RC identity does not describe the current candidate

`v0.1.0-rc.1` and its release note correctly describe the older activities-only
snapshot. The tag points to that historical commit and must not be moved or
reused. Current M2.1 and M4/M5 work is newer and materially expands the formal
workflow and documentation.

Required resolution:

- Human selects the next prerelease identity, normally a new RC identifier
  rather than reusing `v0.1.0-rc.1`.
- Update package version, release readiness, product change history, and a new
  release note consistently for the selected identity.
- Preserve the existing RC1 release note as historical truth.
- Tag and GitHub Release remain separate, Human-authorized actions after exact
  candidate CI PASS.

## Documentation quality findings

The Run-All specification and current implementation agree on command shape,
required and optional families, fixed output layout, status/exit-code boundary,
input immutability, and deterministic rerun behavior.

M4 correctly identifies a privacy nuance not reflected in current entry-point
documentation: `garmin_activity_key` may contain the source activity ID. The M4
and M5 handoff rules mitigate this by keeping real CSV local and requiring the
key to be removed from any externally shared derivative. RC documentation must
adopt the same wording.

Version-specific RC1 release notes and changelog entries are not obsolete; they
are accurate historical records for the tagged artifact. They should not be
rewritten to describe M2.1.

## Minor improvements

- Add a small `examples/analysis/README.md` index if direct directory discovery
  should work independently of the root README.
- Add Case Studies and Analysis Examples to `docs/README.md` after the final
  repository paths are committed.
- Consider consolidating the M4 and M5 README proposals into one application
  checklist to avoid duplicate wording during the actual README edit.
- Record the exact clean-clone test environment and pytest result in the future
  candidate review pack.
- Decide later whether a dedicated external-sharing-safe derivative exporter is
  worth specifying; it is not required for the current local-first contract.

## OSS usability assessment

The synthetic Quick Start command remains runnable, and the M5 examples make
the downstream value understandable. Once the blockers are resolved, a new
user will have a clear route from installation to Run-All, completion review,
analysis handoff, synthetic examples, and the Case Study.

## Conclusion

The current implementation does not require a feature-code fix for RC
readiness. Documentation alignment, release identity selection, snapshot
creation, public CI, and release authorization are required. M6 must not begin
public release or application actions until the Go conditions in
`release_candidate_go_no_go_v0_1.md` are met.
