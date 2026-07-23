# v1.1 Release Candidate Validation Report

## Status

- Candidate: `1.1.0rc1`
- Scope: FIT quality, explicit relationships, Output Experience, standalone
  handoff, privacy-safe handoff, and distribution readiness
- Publication: not performed
- Unit Review: `PASS`
- Target Project Core Review: pending
- Gate: `TARGET_CORE_REVIEW_PENDING`

## Inheritance and adaptation

The implementation extends the existing Target-owned Garmin parser,
normalizers, deterministic QA, Run-All, and allowlist Analysis Pack builder.
Private references were used read-only to verify behavior and aggregate
acceptance metrics. No private row, identifier, filename, path, hash,
coordinate, or generated personal artifact is included in the repository.

## FIT quality

- Complete FIT file CRC is validated.
- Fourteen-byte header CRC is validated when nonzero; zero remains the
  protocol-compatible omitted state.
- Twelve-byte headers remain supported.
- Bad header/file CRC, truncation, chained payloads, undefined local messages,
  and session/lap allocation conflicts are auditable incomplete states.
- `fit_file_id` remains the content-derived compatible file identity.
- `fit_session_key` combines content identity with `session_ordinal`.
- `fit_lap_key` is unique within its parent `fit_session_key`.
- Synthetic single-session, multi-session, invalid CRC, truncated, chained,
  sentinel, conservation, and conflict fixtures are covered.

## Activity/FIT eligibility contract

A relationship is emitted only for a mutual unique evidence-qualified
candidate:

1. exact local start plus compatible sport, distance within 200 metres, or
   duration within 5 seconds; or
2. start within 60 seconds plus compatible sport, distance within 1 metre,
   and duration within 1 second.

Timestamp-only matches are prohibited. Eligibility is defined independently
of candidate search: the record must have a valid timezone-aware local start,
and positive distance or duration. Sport compatibility remains candidate
evidence rather than an eligibility prerequisite. Ties, conflicts, and
eligible records without qualified evidence remain unresolved and reduce
coverage; structurally ineligible records are excluded with a reason.

### Public-safe private-reference metrics

| Metric | Result |
|---|---:|
| Activities reviewed | 3,466 |
| FIT Sessions reviewed | 3,704 |
| Explicit one-to-one links | 3,463 |
| Exact-start links with corroboration | 3,461 |
| Near-start links with exact metrics | 2 |
| Structurally eligible Activities | 3,466 |
| Structurally eligible FIT Sessions | 3,466 |
| Eligible Activity coverage | 99.9134% |
| Eligible FIT Session coverage | 99.9134% |
| Evidence-candidate Activity promotion | 100% |
| Evidence-candidate FIT Session promotion | 100% |
| Ambiguous | 0 |
| Duplicate mappings | 0 |
| Unresolved eligible Activities | 3 |
| Unresolved eligible FIT Sessions | 3 |
| Structurally excluded Activities | 0 |
| Structurally excluded FIT Sessions | 238 |

The structurally excluded FIT Sessions lack a usable start time and do not
enter candidate search. The remaining independently eligible unmatched
records have no qualifying link under the approved evidence rules; their
relationship is not guessed or promoted. This means the original 100%
eligible-population acceptance condition is not reproduced under a
non-circular definition, even though every evidence-qualified candidate is
promoted without ambiguity or duplicate mapping.

The predecessor final relationship QA used a different legacy population and
contract: 3,468 summary Activities, 2,664 FIT Activities, 2,130 promoted links,
and 1,338 summary-only records. It did not define the v1.1 independent eligible
population and does not establish either 3,463/3,466 or complete Activity/FIT
coverage. The public-safe metrics above are a separate read-only validation
obtained by applying the v1.1 contract to the later Run-All normalized
population. The v1.1 report therefore keeps independent source-scope coverage
separate from candidate-promotion coverage. The link rules were not relaxed.

The private reference output predates the v1.1 session-key contract. For this
read-only business-link acceptance check, each reference session received a
non-persisted ordinal surrogate in memory only; no private value was copied or
published. Physical `fit_session_key` and `fit_lap_key` behavior is verified
separately by the synthetic single- and multi-session identity tests.

## Other relationship gates

- Activity/Gear to Activities: explicit, non-null source identity, fail-closed
  orphan/duplicate/type checks.
- Activity/Gear to Gear: explicit, fail-closed orphan/duplicate/type checks.
- Personal Records to Activities: nonzero identity must resolve;
  `activity_id = 0` remains explicitly independent.
- FIT Laps to FIT Sessions: every `fit_session_key` must resolve and every
  `fit_lap_key` must be unique.
- Activity/FIT: separate auditable link dataset; physical FIT identity is
  retained.

## Output Experience

Run-All deterministically emits:

- `START_HERE.md`
- `DATASET_INVENTORY.md`
- `ANALYSIS_HANDOFF.md`
- `ANALYSIS_CONTEXT.json`
- `SCHEMA_CATALOG.json`
- `artifact_inventory.json`

The handoff declares the first-read file, run status, datasets, schemas,
explicit relationships, prohibited operations, warning/partial behavior,
privacy mode, and reproducibility rules without repository or Internet access.
`START_HERE.md`, `ANALYSIS_HANDOFF.md`, and `ANALYSIS_CONTEXT.json` additionally
project Relationship Coverage for every explicit relationship, including
eligible population, explicit links, coverage, unresolved, ambiguous, and
duplicate counts, inference state, primary unresolved reason, and QA
references. Coverage is evidence rather than a success score.

## Privacy-safe handoff

`--external-safe-pack` adds a deterministic allowlist-only ZIP. Its month-level
Activities projection excludes source paths, filenames, hashes, raw IDs/stable
keys, memo text, coordinates, exact dates/timestamps, health detail, and
unlisted files. Run-All never uploads the pack.

## Current source validation

- `unittest`: 104/104 PASS
- `pytest`: 104/104 PASS
- Bootstrap Validation: PASS
- Static Policy Scan: PASS
- Platform Alignment: PASS
- Diff check: PASS
- Private-reference validation: aggregate metrics only; no private rows,
  identifiers, paths, filenames, or hashes were copied into the repository

## Current distribution validation

The final candidate was rebuilt from an isolated source copy and passed build,
strict metadata checks, clean wheel and sdist installation, installed Run-All,
standalone handoff validation, wheel/sdist output byte comparison, and
suspicious-entry scanning.

- Wheel: `garmin_running_data_normalizer-1.1.0rc1-py3-none-any.whl`
- Wheel SHA-256:
  `f18a600965386fdccb764699078e4209383f3beb557321d44d9a34f02c8f6dfa`
- sdist: `garmin_running_data_normalizer-1.1.0rc1.tar.gz`
- sdist SHA-256:
  `cf950fd2a88a1ca030beee7dd83d41d60c17b0bab524a4a1937296bbcec88bcf`
- Installed version: `1.1.0rc1`
- Installed Run-All and standalone validation: PASS
- Wheel/sdist installed handoff outputs: byte-identical

## Publication boundary

Commit, push, and CI validation are authorized for this work package. Tag
creation, GitHub Release publication, TestPyPI upload, Production PyPI upload,
Trusted Publisher/Environment changes, visibility changes, and published
history changes require a new Human approval.
