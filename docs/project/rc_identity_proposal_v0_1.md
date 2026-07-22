# RC Identity Proposal v0.1

## Decision status

**HUMAN_DECISION_REQUIRED before version or release metadata changes.**

The existing `v0.1.0-rc.1` tag is immutable historical evidence for the
activities-only candidate. It must not be moved, deleted, recreated, or reused
for the current M2.1–M5 scope.

## Recommended identity

| Surface | Recommended value |
|---|---|
| Git tag | `v0.1.0-rc.2` |
| Python package version | `0.1.0rc2` |
| Release title | `v0.1.0-rc.2` |
| Stability | Prerelease, not stable |

## Why RC2 is recommended

- It preserves the existing v0.1.0 product line.
- It truthfully follows RC1 without rewriting history.
- M2 adds a formal multi-family Run-All workflow, which is material but still
  bounded and prerelease.
- M2.1 and M3 add real-export compatibility evidence without claiming universal
  Garmin-export support.
- M4/M5 add analysis handoff and public synthetic case-study value without
  changing the normalizer schema.
- Stable API, complete FIT behavior, PyPI publication, and stable-release
  readiness remain explicitly unresolved.

## Alternatives considered

### Keep `v0.1.0-rc.1`

Rejected. The tag already points to a different immutable commit and scope.

### Use `v0.2.0-rc.1`

Possible only if Human considers multi-family Run-All a new minor product line.
This adds avoidable version expansion while the project remains before its
first stable release.

### Use `v0.1.0`

Not recommended. Stable API, complete release readiness, and remaining
limitations do not support removing the prerelease boundary.

## Required Human decision

Choose one:

1. Adopt `v0.1.0-rc.2` / `0.1.0rc2` (recommended).
2. Select another new prerelease identity and state why.
3. Hold release preparation while keeping the current local implementation.

The decision authorizes only identity selection. It does not authorize commit,
push, tag, GitHub Release, or M6 submission.

## Metadata changes after selection

- `pyproject.toml` version.
- A new `docs/release_notes/<selected-version>.md` file.
- `docs/release_readiness.md` current-candidate section.
- `docs/product_changelog.md` factual M2–M5 entry.
- README current-status version wording if applicable.
- Version-specific validator expectations only if evidence proves they exist.

Historical RC1 files and tag remain untouched.
