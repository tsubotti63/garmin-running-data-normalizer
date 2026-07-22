# M8.1 Stable Readiness Report v0.1

- Candidate: `v1.0.0`
- Python version: `1.0.0`
- Review date: 2026-07-22
- Status: `PASS_TO_M8_2`

## Stable readiness decision

The repository preserves the public/private boundary, uses Apache-2.0, has no
third-party runtime package dependency, and has passing pre-M8 CI on `main`.
The Human owner confirmed authority to continue distributing the predecessor-
derived responsibilities included in this Target under Apache-2.0 and to
include them in `v1.0.0`. The prior legal/rights blocker is therefore resolved
for this candidate.

## Issue classification

| Finding | Classification | M8 disposition |
|---|---|---|
| Package, CLI, bootstrap, and registry identities referenced prerelease/local lifecycle states | Release-scoped fix | Align at `1.0.0` with backward-compatible registry acceptance |
| README lacked stable-candidate installation and compatibility boundary | Release-scoped fix | Update README and Product Quick Start |
| No consolidated supported-dataset or known-limitation reference | Release-scoped fix | Add both public references |
| No `v1.0.0` release-note draft | Release-scoped fix | Add tag-ready Markdown with tag-pinned links |
| Rights references retained an unresolved predecessor decision | Stable blocker, resolved by Human | Record candidate-specific confirmation while preserving future review |
| Complete FIT CRC and multi-session identity are absent | Post-Stable quality improvement | Document; do not expand release scope |
| Sleep/HRV/Health Status are not Run-All datasets | Future roadmap item | Preserve library-only classification |
| Open-Meteo, Parquet, hosted processing, and PyPI are absent | Future roadmap item | Preserve non-goal/limitation classification |

## Boundary and package assessment

- Only synthetic fixtures are tracked.
- No private project path, secret, credential, raw export, personal output, or
  predecessor Git history is required by the candidate.
- The root Platform `CHANGELOG.md` and `QUICK_START.md` remain byte-locked and
  are not product release assets; product changes live in
  `docs/product_changelog.md`.
- Release package inspection and clean-state installation belong to M8.3.
- Creating `v1.0.0`, publishing a GitHub Release, marking it latest, or changing
  visibility remains outside M8.1-M8.3 and requires separate Human approval.
