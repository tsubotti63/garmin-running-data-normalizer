# Run-All Gap Assessment v0.1

## Status

- Assessment status: complete
- Baseline branch: `main`
- Baseline commit: `cbaa9f8c8eff257ed79c8c8ab3d79681fe21219f`
- Scope: M0 current-state assessment and M2 blocker identification
- Data used: tracked synthetic fixtures only
- Reference: `garmin_run_all_roadmap_v0_3.md`

This assessment identifies only gaps that affect the minimum Run-All workflow.
It does not redesign the existing normalization core or assess future dataset
families.

## Current State

### Existing execution paths

The only formal end-user entry point is:

```bash
python -m garmin_running_data_normalizer normalize-activities \
  --input <export-directory> \
  --output <absent-or-empty-output-directory>
```

`src/garmin_running_data_normalizer/__main__.py` delegates to
`runner.main()`. `runner.py` owns the subcommand parser, path safety checks, the
activities-only orchestration, deterministic JSON serialization, output hashes,
and the CLI exit boundary. There is no console-script entry point, shell script,
or second combined workflow.

### Current input flow

`intake.discovery.discover_export()` recursively inspects a directory without
modifying it. It accepts direct `.json` and `.fit` files and supported members
inside `.zip` files. Archive members are validated before use for traversal,
absolute paths, symbolic links, encryption, member count, member size, expanded
size, and compression ratio. Provenance is source-relative and content is
hashed with SHA-256.

Current family detection is based on these exact logical filename suffixes:

| Family | Detection rule | Current callable |
|---|---|---|
| Activities | `summarizedActivities.json` | `normalize_activities()` |
| Gear and activity-gear links | `gear.json` | `normalize_gear()` |
| Personal records | `personalRecord.json` | `normalize_personal_records()` |
| FIT sessions, laps, and audit | any `.fit` asset | `parse_fit_export()` |

The normalizers accept the export root, rediscover matching inputs, and return
sorted record dictionaries. They are independently usable but are not connected
to one combined command.

### Current output flow

The activities Golden Path writes exactly:

- `normalized_activities.json`
- `qa_summary.json`
- `run_manifest.json`

The output must be outside the input directory and absent or empty. A non-empty
output is rejected, files are created exclusively, and the input is not changed.
The manifest contains source-relative provenance, input hashes, output hashes,
record grain, stable key, and a deterministic record digest.

There is no Run-All output layout, cross-family manifest, run summary, partial
success status, or completion marker. The Analysis Pack builder is a separate,
explicit-allowlist ZIP utility and is not an orchestrator.

### Tests and CI

The repository contains 29 synthetic, dependency-free unit tests. The formal
activities command is checked for deterministic bytes, reviewed Golden Result
equality, input immutability, unsafe archive rejection, provenance consistency,
and no overwrite. Gear, personal records, FIT parsing, dataset policy, QA, and
Analysis Pack behavior have component tests.

The `bootstrap-ci` workflow installs `.[test]`, runs repository validators, and
runs pytest on Python 3.11. The latest checked public run for baseline commit
`cbaa9f8` completed successfully.

### Public and private boundary

The runtime has no network or private predecessor dependency. Only Python's
standard library is required by the normalization core. Tracked fixtures are
synthetic. Real exports and generated outputs are ignored and must remain local.
Open-Meteo, JMA, Instagram, wellness/coaching interpretation, and personal
analysis are outside Run-All.

## Reused Assets

M2 should compose these assets without replacing their established contracts:

| Existing asset | Run-All responsibility |
|---|---|
| `__main__.py` and `runner.build_parser()` | Preserve the package entry point and subcommand model |
| `runner._validate_paths()` safety behavior | Preserve read-only input and output-outside-input checks |
| `discover_export()` and archive guards | Discover once for the run inventory and reject unsafe input |
| Activity, gear, and personal-record normalizers | Produce existing normalized record shapes and stable keys |
| `parse_fit_export()` | Produce bounded FIT sessions/laps plus auditable parse status |
| `summarize_records()` and dataset policy inspection | Produce deterministic dataset QA and expose key conflicts |
| `config/dataset_registry.example.json` | Reference stable keys, record grain, merge policy, and provenance requirements |
| Existing deterministic JSON conventions | Serialize sorted, UTF-8, newline-terminated JSON |
| Existing Golden Path fixture and test helpers | Seed Run-All synthetic tests and immutability checks |
| Analysis Pack builder | Remain available for later packaging; not required by minimum Run-All |

The example registry is a repository contract, not installed package runtime
data. M2 must not make normal execution depend on finding the repository-level
`config/` directory.

## Blockers

The following five blockers are ordered by implementation dependency.

### B1. No combined orchestration entry point

- Target: `runner.py` and a new Run-All orchestration module
- Symptom: the CLI exposes activities only.
- Cause: component normalizers were intentionally released before final
  orchestration.
- Minimum response: add the `run-all` subcommand while retaining
  `normalize-activities` unchanged.
- Reuse: yes; retain `__main__.py`, argparse, existing path rules, normalizers,
  FIT parser, and QA.
- Resolution: implement in M2. The command and entry point are fixed in the
  minimum specification.

### B2. No cross-family detection and required/optional decision

- Target: Run-All orchestration policy
- Symptom: no single run distinguishes required data from optional data or
  records why a family was skipped.
- Cause: discovery and normalizers operate independently.
- Minimum response: snapshot discovered assets, classify them by exact filename
  rules, require Activities, and treat Gear, Personal Records, and FIT as
  optional.
- Reuse: yes; reuse `discover_export()` and existing suffix rules.
- Resolution: policy is fixed in M1; implement in M2.

### B3. No Run-All status, warning/error boundary, or partial success contract

- Target: Run-All result model and CLI exit handling
- Symptom: the existing command has only PASS or fatal error and cannot expose
  an incomplete detected optional family.
- Cause: the Golden Path covers one required family.
- Minimum response: implement `PASS`, `PASS_WITH_WARNINGS`,
  `PARTIAL_SUCCESS`, and `ERROR`; reserve a distinct exit code for partial
  success; never downgrade unsafe input, required-family loss, malformed
  detected JSON, or unresolved key conflicts to warnings.
- Reuse: partial; reuse component exceptions and FIT audit statuses.
- Resolution: semantics are fixed in M1; implement in M2.

### B4. No deterministic cross-family output, analysis CSV, or completion signal

- Target: Run-All output writer
- Symptom: library results are not emitted by a combined workflow and the
  existing activities output has no stable analysis table for the full run.
- Cause: no orchestrator owns output layout or run-level evidence.
- Minimum response: write the fixed JSON layout, a stable activities CSV,
  per-dataset QA, input/output hashes, and `run_summary.json` last as the
  completion marker.
- Reuse: yes for record shapes, deterministic JSON, hashes, and QA; a small
  stdlib CSV writer and run-level manifest are new.
- Resolution: output contract is fixed in M1; implement in M2.

### B5. No Run-All rerun and failure-atomicity test contract

- Target: Run-All output staging and tests
- Symptom: component tests do not prove that a multi-family failure leaves no
  apparently complete output or that reruns are non-destructive.
- Cause: no Run-All workflow exists.
- Minimum response: require an absent destination, stage under the output
  parent, publish only after all fatal checks pass, write the summary last, and
  refuse an existing destination. Add the four roadmap tests plus an explicit
  partial-success test.
- Reuse: yes; reuse the Golden Path's output rejection, tree hashing, and input
  immutability patterns.
- Resolution: behavior is fixed in M1; implement in M2.

## Non-Blockers

| Item | Why it does not block M2 | Follow-up |
|---|---|---|
| Local pytest is not installed | Dependency-free `unittest` passes; CI installs pytest | Use CI or an isolated test environment when M2 is implemented |
| Local Platform alignment sees ignored `.DS_Store` files | They are untracked local metadata and are absent from a clean CI clone | Remove separately if desired; do not mix with Run-All work |
| FIT CRC and invalid-sentinel completeness | Existing parser exposes bounded status and audit records | Retain as a documented limitation |
| No Parquet implementation | A deterministic stdlib CSV satisfies minimum analysis handoff | Consider Parquet only after Run-All evidence exists |
| No PyPI package | `python -m` works from a local install or source checkout | Packaging is independent of Run-All |
| Normalizers rediscover input | Content hashes and a final inventory comparison can detect changes | Optimize only if real-data evidence shows a need |
| Analysis Pack is not automatic | Stable local JSON/CSV is sufficient for M2 | Connect the allowlist ZIP in a later milestone |
| Registry lifecycle wording is stale | Stable-key and grain fields remain usable; runtime must not depend on this example file | Resolve lifecycle vocabulary separately |

## Out of Scope

- New dataset families, Open-Meteo, JMA, Instagram, wellness, coaching, or
  personal analysis
- Real Garmin data and real-data performance evidence
- Hosted execution or network access
- Parquet/pandas and automatic Analysis Pack creation
- FIT record coordinates or raw telemetry
- Large refactoring of normalizer record shapes
- Community Standards, stable release work, or README restructuring
- Cleanup of ignored local caches or operating-system metadata

## M2 Implementation Scope

### Product code

- Add `src/garmin_running_data_normalizer/run_all.py` for orchestration, family
  classification, result state, deterministic writers, CSV export, staging, and
  run-level evidence.
- Modify `src/garmin_running_data_normalizer/runner.py` only to register and
  dispatch `run-all`, translate result status to exit codes, and preserve the
  current `normalize-activities` behavior.
- If necessary, extract the existing path validation into
  `src/garmin_running_data_normalizer/common/paths.py`; this extraction must be
  behavior-preserving and used by both commands.

### Tests and synthetic evidence

- Add `tests/test_run_all.py` using only synthetic or dynamically generated
  inputs.
- Reuse the tracked activities fixture for the optional-family-missing case.
- Generate small gear, personal-record, and FIT inputs inside temporary test
  directories rather than committing personal or opaque binary data.
- Add a reviewed Run-All Golden Result only if the implementation needs a
  byte-level contract beyond direct deterministic assertions.

### Minimal documentation after the command works

- Update only the Run-All sections of `README.md` and
  `docs/product_quick_start.md` with the tested command, output layout, exit
  codes, privacy boundary, and current limitations.
- Do not change Platform Standard files or broaden the product roadmap.

No configuration/schema migration is required for M2. If implementation shows
that the example registry must become installed runtime data, stop that change
and treat it as a separate packaging decision rather than silently adding a
repository-path dependency.

## M2 Test Scope

1. Full synthetic success: all four input families are detected; all fixed
   outputs exist; summary and manifest agree; input tree is unchanged.
2. Optional data missing: activities-only input completes with
   `PASS_WITH_WARNINGS`, empty optional outputs, recorded skip reasons, and exit
   code 0.
3. Invalid input: missing required activities, unsafe archive, malformed
   detected JSON, output-inside-input, and existing output fail closed with exit
   code 2 and no completion marker.
4. Rerun: a second invocation against the same destination is rejected without
   modifying it; a new destination produces byte-identical output.
5. Partial success: a detected FIT family with one or more auditable rejected
   files or unknown-record stops produces `PARTIAL_SUCCESS`, exit code 3,
   explicit counts, and a completion marker, including when no FIT session can
   be emitted.
6. Privacy regression: committed fixture/output contains no real identifier,
   email, coordinate, host path, credential, or raw Garmin data; console output
   does not echo record values or host paths.

## Risks

- A real export may contain filename variants not represented by synthetic
  fixtures. M2 intentionally preserves the exact existing suffix contract; M3
  may add evidence-driven aliases without changing this minimum spec silently.
- Source-relative provenance can contain sensitive local names. It is allowed
  only in local normalized output and manifests, not console logs, committed
  examples, or CI artifacts.
- FIT audit can report supported partial parsing. The distinct summary status
  and exit code prevent this from looking like a complete run.
- A process crash can leave an internal staging directory. It must not create
  `run_summary.json` or the final destination, and a later run may safely clean
  only its own positively identified staging directory.

## Decision Log

| Decision | Rationale |
|---|---|
| Extend the existing package CLI with `run-all` | Lowest-cost path; preserves the public entry point and current command |
| Require Activities | It is the only formal end-user dataset and the minimum useful analysis table |
| Keep Gear, Personal Records, and FIT optional | Exports vary; their absence must not block available-data processing |
| Use CSV rather than Parquet | Standard-library implementation and direct Chat handoff |
| Refuse existing Run-All destinations | Clear, non-destructive rerun behavior with no silent overwrite |
| Use `run_summary.json` as the completion marker | One file provides status and avoids a redundant marker |
| Use exit code 3 for partial success | Automation cannot mistake incomplete detected input for full success |
| Keep Analysis Pack outside minimum Run-All | It is packaging, not necessary for end-to-end normalization evidence |
