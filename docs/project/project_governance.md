# Project Governance

## Decision model

- Human decisions govern license, rights, publication, external systems, and
  Charter/Boundary/DoD changes.
- Implementation proceeds autonomously inside the approved Work Package.
- Unit Review evaluates implementation evidence read-only.
- Project Core Review independently evaluates boundary, architecture,
  cross-artifact consistency, and gate readiness.

## Evidence model

Claims require actual files, deterministic test output, scans, inventory,
manifest, and hashes. Planned or unperformed work is never marked complete.

## Gate model

All implementation and Project Core Gate decisions belong to the
`GARMINデータ正規化` project. Review Packages are submitted directly from the
Target Implementation task to the Target Project Core Review task. The prior
Source extraction review is historical handoff evidence only and is not a gate.
No implementation commit is created until Target Project Core Review returns
`PASS` and Target rules permit the commit.

## Change control

Review `REWORK` inside the boundary is fixed in a new review cycle. Only an
unresolved Human-owned decision returns `HUMAN_DECISION_REQUIRED`.
