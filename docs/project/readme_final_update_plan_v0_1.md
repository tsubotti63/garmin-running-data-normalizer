# README Final Update Plan v0.1

## Purpose

Consolidate the M4 and M5 proposals into one bounded edit plan for root README,
Product Quick Start, and optional navigation indexes. No file is edited by this
plan.

## Root README changes

### Current status

Replace synthetic-only validation wording with a precise two-part statement:

- public reproducibility uses wholly synthetic fixtures;
- M3 privately validated M2.1 against a local real export with status `PASS`,
  exit code `0`, unchanged input, two independent byte-identical outputs, and
  privacy PASS.

Do not publish real counts, dates, filenames, paths, records, or fingerprints.

### Why this project matters

Add a short section explaining that the project creates a reviewable boundary
between a complex local Garmin export and downstream analysis: deterministic
normalization, fixed output, QA/provenance, explicit warnings, and a separate
human-owned interpretation step.

Link:

- `docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md`

### Analysis Handoff

Add links to:

- `docs/project/analysis_handoff_spec_v0_1.md`
- `docs/project/analysis_prompt_template_v0_1.md`
- `docs/project/run_all_public_usage_example_v0_1.md`
- `docs/project/run_all_use_case_catalog_v0_1.md`

State that `analysis/activities.csv` plus `run_summary.json` is the normal
minimum only for a trusted local environment.

### Reproducible examples

Link the three `examples/analysis/` README files. State that inputs are
synthetic, key-free, and use fictional dates. Calculated results are
reproducible; generative wording is not claimed to be byte-identical.

### Privacy correction

Replace any unqualified statement that the Activities CSV excludes Garmin
activity IDs. Accurate wording:

> The CSV has no separate `activity_id` column, but the current
> `garmin_activity_key` may incorporate the source activity ID. Keep real CSV
> local and remove that key from any externally shared derivative. Review exact
> date/time granularity before transfer.

### Current limitations

Retain:

- Activities required; Gear, Personal Records, and FIT optional.
- Exact filename detection rules.
- Selected FIT session/lap fields only; incomplete CRC/invalid-sentinel scope.
- No Weather, Sleep, HRV, Parquet, dashboards, notebooks, PyPI, stable release,
  or stable third-party Python API.
- No medical, coaching, or personal-performance conclusions.

Remove only the obsolete synthetic-only validation limitation.

## Product Quick Start changes

### Preserve

- Clean clone and virtual environment steps.
- Activities-only `normalize-activities` Golden Path.
- Minimum Run-All command, fixed layout, exit-code contract, no-overwrite rule,
  local validation commands, and real-output privacy warnings.

### Correct

- Distinguish the activities-only Golden Path command from multi-family
  `run-all`; do not call the current runner activities-only.
- Replace “not validated against real Garmin data” with the same public-safe M3
  wording used in README.
- Correct stable-key privacy wording.
- Link the M4 Public Usage Example and Analysis Handoff.
- Link the Primary Case Study and three synthetic examples near the Run-All
  section or Known Limitations.

## Optional navigation files

- Add `examples/analysis/README.md` with links and one-line purposes for the
  three examples.
- Add Analysis Handoff, Analysis Examples, and Case Studies to `docs/README.md`.

These are recommended usability improvements. Include them with the public
documentation commit only if the final review confirms they remain a single
navigation theme.

## Acceptance checks

- No link targets are missing.
- README and Quick Start make identical M3 and privacy claims.
- RC1 historical release documents remain unchanged.
- No new implemented feature is claimed.
- No external-sharing-safe artifact is claimed to exist.
- Tests, validators, link checks, privacy scan, and clean-clone checks pass.
