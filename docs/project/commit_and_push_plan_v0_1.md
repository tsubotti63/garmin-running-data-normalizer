# Commit and Push Plan v0.1

## Rules

- This is a plan, not authorization to run Git commands.
- Preserve existing M2 and M2.1 commits and GitHub noreply identity.
- Use exact staged-path review before every commit.
- One theme per commit; do not absorb incidental cleanup.
- No amend, rebase, squash, force-push, tag, or release.
- Push requires a separate explicit Human instruction.

## Existing commits to preserve

| Milestone | Commit | Action |
|---|---|---|
| M2 | `f268676c137154b54ce7bd03b0e732d417e0c033` | Preserve unchanged |
| M2.1 | `2d871ac9abcea853731ff3a1c191db415f974c31` | Preserve unchanged |

## Planned commit groups

### Commit A — M4 Analysis Handoff

Suggested message:

```text
docs: add analysis handoff and public usage guidance (M4)
```

Scope:

- `docs/project/analysis_handoff_spec_v0_1.md`
- `docs/project/analysis_prompt_template_v0_1.md`
- `docs/project/run_all_public_usage_example_v0_1.md`
- `docs/project/run_all_use_case_catalog_v0_1.md`
- `docs/project/m5_case_study_candidates_v0_1.md`
- `docs/project/readme_m4_update_proposal_v0_1.md`

### Commit B — M5 Analysis Value Case Study

Suggested message:

```text
docs: add reproducible analysis value case study (M5)
```

Scope:

- three complete directories under `examples/analysis/`;
- `docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md`;
- `docs/project/readme_m5_update_proposal_v0_1.md`;
- `docs/project/m5_analysis_value_evidence_index_v0_1.md`;
- `docs/project/m5_5_readiness_handoff_v0_1.md`.

### Commit C — M5.5 and M5.5A Readiness Planning

Suggested message:

```text
docs: record release candidate readiness and finalization plans
```

Scope:

- four M5.5 review documents;
- five M5.5A planning documents.

### Commit D — Public Documentation Alignment

Suggested message:

```text
docs: align public guidance with current Run-All
```

Scope only after separate review:

- `README.md`;
- `docs/product_quick_start.md`;
- optional `docs/README.md` and `examples/analysis/README.md` navigation files
  if approved as part of the same documentation theme.

### Commit E — Next RC Metadata

Create only after Human selects the RC identity.

Suggested message for the recommended identity:

```text
chore: prepare v0.1.0-rc.2 candidate
```

Expected scope:

- `pyproject.toml`;
- a new release note;
- `docs/release_readiness.md`;
- `docs/product_changelog.md`;
- any validator expectation that is demonstrably version-specific.

Do not change RC1 tag, RC1 release note, or historical changelog facts.

## Pre-commit checks for every group

1. `git status --short` contains only expected paths.
2. `git diff --cached --name-only` exactly matches the approved group.
3. `git diff --cached --check` passes.
4. Privacy scan passes on staged content.
5. Markdown links and final newlines pass for documentation groups.
6. No real output, private Evidence, generated artifact, or metadata file is
   staged.

## Candidate pre-push checklist

- [ ] All planned commits exist in the intended order.
- [ ] Branch is `main`.
- [ ] Worktree is clean.
- [ ] README and Product Quick Start reflect current Run-All and M3 evidence.
- [ ] Package version and new release note match the Human-selected identity.
- [ ] unittest PASS.
- [ ] pytest PASS in Python 3.11 with test extras installed.
- [ ] Bootstrap PASS.
- [ ] Static Policy PASS.
- [ ] Platform alignment PASS.
- [ ] Link/structure and synthetic arithmetic PASS.
- [ ] Privacy scan PASS.
- [ ] Clean-clone equivalent PASS.
- [ ] No new tag exists.
- [ ] Explicit Human push authorization is recorded.

## Push plan

After every pre-push item passes and Human authorizes the action:

1. Confirm `main` is ahead of `origin/main` only by the reviewed commits.
2. Push normally to `origin/main`.
3. Record the pushed commit ID.
4. Wait for the matching `bootstrap-ci / test` run.
5. If CI fails, stop without tag, release, or speculative extra push.
6. If CI passes, confirm local HEAD equals `origin/main` and worktree is clean.
7. Submit the exact snapshot to M5.5B.

Tag and GitHub Release actions require a later, separate Human instruction.
