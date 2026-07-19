# Post-Public Alignment Backlog

## Metadata

- Status: Active
- Scope: Post-public repository alignment
- Created: 2026-07
- Repository state:
  - Public
  - Default branch: `main`
  - License: `Apache-2.0`
  - CI: Passing at backlog creation
- Source: Post-public repository inventory

## Purpose

This backlog records bounded improvements needed to align repository documents,
validators, and runtime contracts with post-public operation. Work should
normally follow a one-theme, one-commit model. Changes that require a Human
decision are not implemented until that decision is recorded.

This document is a planning and progress-tracking aid. It is not the source of
truth for product requirements or current repository state, and it does not
replace release notes or an issue tracker.

## Operating Rules

- Consider dependencies between items as well as priority.
- Reconfirm the exact scope and current repository state before implementing an
  item.
- Run the relevant deterministic checks and obtain Target Project Core Review
  after each change when required by project governance.
- Keep one theme in one commit unless review evidence justifies a different
  split.
- Do not absorb unrelated discoveries into the active commit; record them for a
  later bounded change.
- Distinguish historical records and negative tests from statements that claim
  to describe the current repository.
- Do not change Human-decision items until the required decision is complete.

## Priority Backlog

### High Priority

#### A. Align license and GitHub status references

Primary scope:

- [`docs/dependency_license_inventory.md`](../dependency_license_inventory.md)
- [`docs/github_public_readiness_checklist.md`](../github_public_readiness_checklist.md)
- [`docs/reference/license.md`](../reference/license.md)
- Directly related reference documents confirmed during implementation

Remove or contextualize current-state claims that the license is unselected,
the GitHub repository does not exist, pushes are prohibited, or public release
has not been authorized. Preserve accurate historical statements. Correcting
those old factual claims does not grant standing permission for future pushes,
tags, releases, or publication; each such action remains subject to the current
project rules and any required Human authorization.

Planned commit: `docs: align license and GitHub status references`

#### B. Align release readiness with public repository

Primary scope:

- [`docs/release_readiness.md`](../release_readiness.md)
- Roadmap documents under `docs/` and `docs/project/`
- Handoff references under `docs/reference/`
- Source inspection summaries and closely related readiness documents

Replace current-state assumptions such as public candidate, GitHub approval
pending, or license selection pending with language that reflects an already
public and licensed repository. Keep future release readiness distinct from
initial repository publication.

Planned commit: `docs: align release readiness with public repository`

#### C. Align public history validation documentation

Primary scope:

- [`README.md`](../../README.md)
- [`scripts/validate_public_history.py`](../../scripts/validate_public_history.py)
- Directly related validation documentation

Make the documented validation command succeed for the current public history
and clearly distinguish pre-registration validation from post-public
validation. During implementation, decide from the reviewed diff whether the
README update should remain with the validator change or be a separate
documentation commit.

Planned commit: `ci: make public history validation lifecycle-aware`

### Medium Priority

#### D. Separate bootstrap and post-public runtime workflows

Primary scope:

- [`runtime/project_core_review_initial_prompt.md`](../../runtime/project_core_review_initial_prompt.md)
- Implementation and review runtime prompts
- Workflow display names when they express a bootstrap-only lifecycle

Separate bootstrap-era prohibitions and gates from normal post-public
operation. Preserve bootstrap contracts as historical or lifecycle-specific
controls instead of rewriting their original meaning.

Planned commit: `runtime: separate bootstrap and post-public workflows`

#### E. Review remaining recommended documentation updates

Process the documents classified as recommended by the post-public inventory in
small thematic changes. Reconfirm the candidate paths and their present wording
before implementation; the inventory is evidence for planning, not authority
to update every matching string.

Planned commit: To be selected for each bounded documentation theme.

## Human Decision Backlog

The following items remain unchanged until a Human decision is recorded. After
that decision, all affected documents, configuration, schemas, code, and tests
must be updated together where required.

- `AGENTS.md` Current Phase: decide whether Phase 0.1 remains the active control
  or becomes historical.
- Post-public phase name: select the canonical lifecycle name before using it in
  governance or runtime documents.
- Maturity vocabulary: define wording that separates implementation maturity,
  public availability, release readiness, and production readiness.
- [`docs/project/definition_of_done.md`](definition_of_done.md): decide whether
  the current DoD remains Phase 0.1-specific or must be superseded.
- "No external resource" interpretation: clarify whether it is a historical
  bootstrap condition, a product-runtime constraint, or both.
- Implementation status contract name: decide whether the existing status name
  should be retained, aliased, or replaced for post-public operation.
- Config/schema/code/test propagation: authorize and define the coordinated
  change only after the status-contract decision is complete.

## Explicit Non-Targets

The following are not automatic correction targets:

- Phase documents that accurately record a past state
- Contracts that explicitly describe the bootstrap period
- Migration history
- Negative tests and intentionally invalid test fixtures
- AI Collaboration Platform Standard files
- Generic templates
- The local-only input data boundary
- Human-owned decision and authority principles

## Recommended Execution Order

1. License and GitHub status references
2. Release readiness
3. Public History validation
4. Bootstrap and post-public runtime separation
5. Human decision items
6. Medium- and low-priority cleanup

Increase an item's priority if a new CI failure or a material public-facing
contradiction is confirmed.

## Progress Tracking

- [ ] Align license and GitHub status references
  - Priority: High
  - Scope: License, GitHub, publication, and push status references
  - Decision required: No; preserve accurate historical records
  - Planned commit: `docs: align license and GitHub status references`
  - Completion evidence: Reviewed diff, relevant checks, Core Review verdict,
    and commit ID
- [ ] Align release readiness with public repository
  - Priority: High
  - Scope: Release readiness, roadmaps, handoff, and inspection summaries
  - Decision required: No; do not redefine release policy
  - Planned commit: `docs: align release readiness with public repository`
  - Completion evidence: Reviewed diff, relevant checks, Core Review verdict,
    and commit ID
- [ ] Align public history validation documentation
  - Priority: High
  - Scope: README, validator lifecycle behavior, and related documentation
  - Decision required: Review-time decision on one or two commits
  - Planned commit: `ci: make public history validation lifecycle-aware`
  - Completion evidence: Pre-registration and post-public validation results,
    tests, Core Review verdict, and commit ID
- [ ] Separate bootstrap and post-public runtime workflows
  - Priority: Medium
  - Scope: Runtime prompts and lifecycle-specific workflow labels
  - Decision required: No, unless the change requires a phase or governance
    redefinition
  - Planned commit: `runtime: separate bootstrap and post-public workflows`
  - Completion evidence: Runtime consistency review, relevant checks, Core
    Review verdict, and commit ID
- [ ] Review remaining recommended documentation updates
  - Priority: Medium
  - Scope: Inventory candidates reconfirmed before each bounded change
  - Decision required: Determined per candidate
  - Planned commit: Selected per theme
  - Completion evidence: Candidate-specific diff, checks, review verdict, and
    commit ID
- [ ] Decide the `AGENTS.md` Current Phase
  - Priority: Human decision
  - Scope: Active project controls and the status of Phase 0.1
  - Decision required: Yes
  - Planned commit: Defined after the Human decision
  - Completion evidence: Recorded decision and `AGENTS.md` consistency
- [ ] Select the canonical post-public phase name
  - Priority: Human decision
  - Scope: Lifecycle naming across project and runtime documents
  - Decision required: Yes; coordinate with the Current Phase decision
  - Planned commit: Defined after the Human decision
  - Completion evidence: Recorded phase-name decision and cross-document
    consistency
- [ ] Define post-public maturity vocabulary
  - Priority: Human decision
  - Scope: Implementation, publication, release, and production status terms
  - Decision required: Yes
  - Planned commit: Defined after the Human decision
  - Completion evidence: Recorded vocabulary decision and aligned documents
- [ ] Decide the future of the current Definition of Done
  - Priority: Human decision
  - Scope: `docs/project/definition_of_done.md`
  - Decision required: Yes
  - Planned commit: Defined after the Human decision
  - Completion evidence: Recorded decision and reviewed DoD update, if any
- [ ] Clarify the "no external resource" contract
  - Priority: Human decision
  - Scope: Bootstrap history and current runtime boundary
  - Decision required: Yes
  - Planned commit: Defined after the Human decision
  - Completion evidence: Recorded interpretation and aligned contracts
- [ ] Decide the implementation status contract name
  - Priority: Human decision
  - Scope: Canonical status terminology
  - Decision required: Yes
  - Planned commit: Defined after the Human decision
  - Completion evidence: Recorded status-contract decision
- [ ] Apply an approved status-contract change across affected assets
  - Priority: Human decision dependency
  - Scope: Config, schema, code, tests, validators, and related documents
  - Decision required: Yes; depends on the status-contract decision
  - Planned commit: Defined after impact analysis and Human approval
  - Completion evidence: Migration evidence, tests, validators, Core Review
    verdict, and commit ID

## Completed Context

The following work was completed before this backlog was created and is not an
open backlog item:

- Initial post-public wording refinement in the README
- Removal of the Public History Validator's fixed reachable-commit-count
  assumption
- Addition of Apache License 2.0
- Bootstrap Validator support for the post-public licensed state

## Creation-Time Base Snapshot

This snapshot records the clean base immediately before the backlog file was
created. It is historical evidence for this planning change, not a continuously
updated claim about the repository after later commits.

- Branch: `main`
- Base HEAD: `c33db1c63d6a9cc56a600ccc319eb1f3e535f71d`
- Base HEAD equaled `origin/main`
- Worktree: Clean immediately before backlog creation
- Latest `bootstrap-ci` at the base HEAD: PASS
