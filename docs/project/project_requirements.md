# Garmin Running Data Normalizer Requirements

## Primary goal

Provide a deterministic, local, Garmin-only normalization core with no private
runtime dependency.

## Functional requirements

- Discover JSON, FIT, and ZIP inputs without modifying the export.
- Reject unsafe ZIP members and enforce member/count/size limits.
- Normalize activities, gear, personal records, FIT sessions, and FIT laps.
- Attach stable keys and source-relative provenance.
- Validate merge policies and inspect duplicate/null-key conflicts.
- Produce deterministic QA summaries and allowlist-only Analysis Pack ZIPs.

## Quality requirements

- Python 3.11+ and standard library only for the current core.
- Synthetic tests runnable with `unittest`; pytest-compatible test discovery.
- Production imports contain no Source package or phase-specific modules.
- Static scans detect secrets, PII markers, absolute host paths, JMA, and
  non-Garmin implementation references.

## Out of scope for Phase 0.1

Open-Meteo, Parquet/pandas integration, a final CLI Run-All workflow, real-data
validation, license selection, GitHub, release, and publication.
