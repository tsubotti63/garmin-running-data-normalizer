# Garmin Running Data Normalizer — Changelog

The authoritative product history is maintained in:

- [Product Changelog](docs/product_changelog.md)

Release-specific notes are available under:

- [`docs/release_notes/`](docs/release_notes/)

The AI Collaboration Platform changelog is maintained in the separate
canonical platform repository:

- [AI Collaboration Platform — CHANGELOG](https://github.com/tsubotti63/ai-collaboration-platform/blob/main/CHANGELOG.md)

## v1.3.3 — stable Production patch release

Published on 2026-08-13 JST as the annotated `v1.3.3` tag, the latest stable
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.3.3),
and the verified
[Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.3.3/).

- Restores the approved observed Sleep-stage duration contract with direct
  fallback only when every stage is absent; missing stages remain missing,
  awake/window subtraction is not used, and conflicting direct aliases fail
  closed.
- Separates review-required counts from excluded-record evidence across daily
  metric summaries so excluded-only input does not create a review-required
  warning.
- Aligns the public Run-All and Python Sleep helper semantics and documents the
  available-only context boundary.

## v1.3.2 — stable Production patch release

Snapshot-aware relationship resolution, deterministic Sleep exact-duplicate
handling, observed-variant preservation for Endurance/UDS, Lactate candidate
preservation without winner selection, and acquisition-order separation were
published in v1.3.2. See the
[v1.3.2 Release Notes](docs/release_notes/v1.3.2.md),
[GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.3.2),
and [Production PyPI distribution](https://pypi.org/project/garmin-running-data-normalizer/1.3.2/).
