# M7.2 Sleep Migration PoC Report

## Status and scope

M7.2 migrates Garmin `sleepData.json` normalization into the public Target as a
dependency-free library capability. The implementation uses only the Stable
Release Migration Roadmap and the authorized Public Edition Source Tree
`00_shared/` and `20_wellness_platform/` packs. The original private project
was not accessed.

HRV, Health Status, Weather, Instagram, JMA, and future roadmap capabilities
remain outside this phase.

## Implemented behavior

- Discover exact `sleepData.json` suffixes in safe directories and ZIP inputs.
- Support list payloads and the documented `sleepData`, `data`, `records`, and
  `items` wrappers.
- Attribute `sleep_day` to `sleep_end_date_jst`; retain the source
  `calendarDate` separately.
- Normalize sleep window, stage, score, and availability fields without pandas
  or Parquet dependencies.
- Derive record identity from source content SHA-256 plus source record index,
  and retain source-relative path and SHA-256 provenance.
- Preserve duplicate days as `needs_review` instead of dropping rows.
- Preserve missing fields and invalid intervals as `needs_review` without time
  shifting or inference.
- Preserve empty retro-only records as `excluded_empty_record` QA evidence.
- Keep score absence explicit while retaining an otherwise valid sleep window.

## Public contract boundary

The M7.2 Roadmap requires normalization but does not require Run-All
integration. The authorized Phase 1.3 Sleep candidate explicitly excludes
Run-All integration, and adding a Sleep dataset to the current Run-All fixed
layout and registry would change a reviewed public contract. M7.2 therefore
adds a library-level normalizer only and uses the complete Run-All suite as a
regression check. A future lifecycle decision must separately authorize any
Run-All dataset, stable-key, schema, CLI, or output-layout extension.

## Validation contract

Completion evidence must include synthetic Sleep unit tests, the complete
Run-All regression suite, bootstrap/static-policy/Platform/public-history
validators, production import and public-boundary scans, independent Unit
Review, Target Project Core Review, and GitHub Actions for the reviewed commit.

## Migration gaps and ambiguities

1. The Source Tree contains an older normalizer that attributes and deduplicates
   by source `calendarDate`, and a later dedicated candidate that attributes by
   `sleep_end_date_jst` and retains duplicates for review. M7.2 uses the later,
   Sleep-specific Phase 1.3 candidate.
2. No normative manifest states which Sleep asset version supersedes the older
   implementation.
3. The Source Tree lacks dependency-free synthetic `sleepData.json` fixtures
   with byte-stable expected public JSON output.
4. Sleep record identity before daily promotion is not explicitly defined.
   M7.2 uses content/provenance identity and does not promote a daily registry
   stable key.
5. Run-All integration, schema evolution, and daily deduplication/promotion
   require a separate public-contract decision.

## PoC evaluation and recommendations

The authorized Source Tree is sufficient to implement bounded Sleep
normalization without private references. The dedicated Phase 1.3 inventory and
normalization assets clearly define the later attribution, status, no-filling,
and no-inference behavior. Ambiguity remains because older competing assets are
not marked historical.

Future packs should include a phase manifest identifying normative,
informative, historical, and excluded assets; dependency-free synthetic raw and
expected-output fixtures; explicit field aliases; a stable-identity decision;
and a lifecycle statement covering whether Run-All and registry contracts must
change.

## Explicit non-targets

M7.2 does not implement Sleep FIT extraction, FIT/JSON reconciliation, Garmin
app revalidation, score recalculation, missing-day filling, day-shift inference,
nap merging, activity joins, analysis-ready promotion, coaching, HRV, Health
Status, Weather, Instagram, or JMA.
