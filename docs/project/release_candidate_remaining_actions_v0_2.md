# Release Candidate Remaining Actions v0.2

## Purpose

Record the bounded actions remaining after the `v0.1.0-rc.2` Phase 3 `GO`
decision. This file is an execution handoff, not standing authorization for an
external action.

## Required before publication

- [x] Human authorizes creation of tag `v0.1.0-rc.2` through M6 instruction
  v0.3.
- [x] Immediately before tagging, confirm `main`, clean candidate worktree, local
  `HEAD == origin/main`, exact commit
  `0996c4889ae807be0082ae83a26319a860f62c96`, successful GitHub Actions run
  `29896162447`, and absence of an existing RC2 tag.
- [x] Create the RC2 tag at that exact commit without changing or moving
  `v0.1.0-rc.1`.
- [x] M6 instruction v0.3 authorizes GitHub Release publication.
- [x] Publish the GitHub Release using the reviewed final RC2 body, mark it as a
  prerelease, and attach no generated personal data or unreviewed artifact.

No code, documentation, commit, push, CI rerun, rebase, amend, squash, or force
push is required by the Phase 3 validation result.

## Required after publication

- [x] Confirm the Git tag resolves to the exact validated commit.
- [x] Confirm the GitHub Release is marked prerelease and targets the RC2 tag.
- [x] Confirm Release links resolve from the tag snapshot.
- [x] Confirm no unintended binary, generated output, or personal-data asset
  was attached.
- [x] Confirm the validated tag snapshot remains unchanged.
- [x] Record the Release URL and publication time in the appropriate M6
  evidence without rewriting the Phase 3 evidence.

## Minor improvements

These are non-blocking and should use separate, reviewed work units:

- Add `*.egg-info/` to the Python repository-hygiene ignore policy so an
  editable install does not leave visible untracked build metadata.
- Decide whether the legacy Bootstrap `implementation_status` vocabulary
  should be renamed for post-public operation; keep the existing lifecycle and
  safety checks intact until that Human/governance decision is made.
- Consider adding an explicit Run-All repeat command to Product Quick Start,
  although deterministic rerun behavior is already stated and independently
  validated.
- Refresh release-reference wording after RC2 publication while preserving
  RC1 as historical truth.

## Next RC or stable-release candidates

- Expand FIT conformance only through a separately specified and tested scope,
  including CRC and invalid-sentinel decisions.
- Decide whether to provide an explicit external-sharing-safe derivative
  exporter that removes keys and controls date/time granularity.
- Define a stable third-party Python API before claiming API stability.
- Reassess dependency, notice, rights, privacy, and packaging requirements
  before any stable release or PyPI publication.
- Preserve local-first behavior, no-overwrite semantics, deterministic QA,
  provenance, archive fail-closed protections, and synthetic public fixtures.

## Codex for Open Source handoff

The evidence set suitable for a later application includes:

- exact RC2 candidate commit and version identity;
- successful GitHub Actions run `29896162447`;
- 39/39 unittest and pytest results;
- Bootstrap, Static Policy, Platform, and Public History PASS results;
- clean-clone Golden Path and Run-All reproduction evidence;
- deterministic digests and explicit no-overwrite/exit-code behavior;
- Public Contract and Privacy Boundary assessment;
- public-safe private-real-export validation statement;
- Analysis Handoff, prompt template, Public Usage Example, use-case catalog,
  three synthetic Analysis Examples, and Primary Case Study;
- Apache-2.0 license, prerelease classification, and known limitations.

An application must not include private exports, output rows, identifiers,
paths, counts, fingerprints, or generated personal artifacts. Application
submission remains a separate Human-authorized action.
