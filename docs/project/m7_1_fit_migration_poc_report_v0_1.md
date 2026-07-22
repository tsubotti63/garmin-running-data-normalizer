# M7.1 FIT Migration PoC Report

## Status and scope

M7.1 migrates FIT Activities and FIT Laps into the existing public Run-All
architecture. The implementation is intentionally limited to the authorized
public migration references in `00_shared/` and `10_fit_normalization/`.

The migration preserves the Target repository's safe asset discovery,
content-derived `fit_file_id`, source-relative provenance, bounded parser, and
non-emission of FIT record coordinates and raw telemetry. It does not migrate
private paths, private fixtures, phase-specific orchestration, pandas/Parquet
dependencies, or source-project module names.

Sleep, HRV, Health Status, Weather, Instagram, and JMA remain explicitly out of
scope.

## Implemented mapping

The dependency-free parser now uses the authorized FIT Session and Lap field
numbers for elapsed and timer time, distance, speed, heart rate, cadence,
power, ascent, descent, calories, and lap count. The normalized FIT Activity
output includes heart rate, cadence, power, ascent, and descent. FIT Lap output
retains these selected decoded metrics plus file identity and provenance.

Invalid sentinels for the selected numeric metrics are converted to null before
scaling. Synthetic tests cover valid metrics, invalid values, stable
content-derived identity, provenance, rejected input audit, and Run-All output.

## Validation contract

Completion evidence must include:

- the complete synthetic unit-test suite;
- the Run-All success, warning, partial-success, safety, rerun, and privacy
  regression suite;
- bootstrap, static-policy, Platform-alignment, and public-history validators;
- a production import scan excluding `running_platform` and phase modules;
- Target Unit Review and Target Project Core Review; and
- GitHub Actions for the reviewed commit before M7.1 is declared complete.

## Migration gaps

1. **Multi-session identity:** the public source assets contain both a
   one-session-per-file contract and later physical-session ordinal logic. The
   shared dataset key remains file-based. Changing the Target public key without
   an explicit contract decision would be unsafe, so M7.1 retains the existing
   one-activity-per-file behavior.
2. **Complete FIT CRC validation:** the self-contained candidate parser does not
   provide a complete CRC implementation, although other source evidence refers
   to SDK-level CRC checks. M7.1 keeps the existing structural and size checks
   and records complete CRC validation as a gap.
3. **Public runnable fixtures:** the source tests depend on non-public fixture
   names and data-processing dependencies. The Target therefore recreates
   visibly synthetic FIT bytes and assertions instead of copying those tests.
4. **Output schema authority:** preview headers and shared dictionaries are
   informative, but no single versioned manifest identifies the authoritative
   M7.1 input, output, and acceptance-test contract.

## PoC evaluation

### Source Tree sufficiency

The Source Tree is sufficient for the selected Session/Lap field mappings,
scale rules, invalid-sentinel semantics, and the boundary between migrated and
excluded functionality. The migration can be implemented without accessing the
original private project.

### Missing assets

Future phases would benefit from a self-contained synthetic FIT fixture set,
expected public JSON outputs, and a dependency-free acceptance command. A CRC
reference implementation or an explicit deferral decision is also missing.

### Roadmap clarity and ambiguity

The Roadmap clearly identifies FIT Activities and FIT Laps as the M7.1 scope.
It does not identify which candidate or later ordinal implementation is
authoritative, whether multi-session files change the stable-key contract, or
whether complete CRC validation is required in M7.1.

### Recommendations

- Add a phase manifest listing authoritative source files, public contracts,
  exclusions, and acceptance commands.
- Include dependency-free synthetic fixtures and byte-stable expected outputs.
- Mark assets as normative, informative, historical, or excluded.
- State whether each phase preserves or changes public stable keys and record
  grain.
- Make CRC and multi-session requirements explicit rather than leaving them to
  inference from multiple source assets.

## Release boundary

This report records an implementation PoC, not a stable release. A passing local
suite is not CI evidence, and M7.1 must not be committed before Target Project
Core Review PASS or described as released before the reviewed commit passes the
required GitHub Actions workflow.
