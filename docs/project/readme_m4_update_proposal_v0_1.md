# README M4 Update Proposal v0.1

## Status

Proposal only. This file does not modify `README.md` and does not change the
Run-All public contract. Apply it later as a focused documentation change after
reviewing README wording against the then-current repository state.

## Proposed additions

### 1. Add an "Analyze Run-All output" section

Recommended placement: after **Run the minimum multi-family workflow**.

Proposed text:

> ## Analyze Run-All output
>
> Run-All separates deterministic normalization from downstream analysis.
> Start with `run_summary.json` to confirm completion and warnings, then use
> `analysis/activities.csv` for descriptive activity-level aggregates. Keep
> `run_manifest.json` locally for provenance and reproducibility; it is not a
> default external upload.
>
> See the [public synthetic usage example](docs/project/run_all_public_usage_example_v0_1.md),
> [analysis handoff specification](docs/project/analysis_handoff_spec_v0_1.md),
> and [reusable analysis prompt](docs/project/analysis_prompt_template_v0_1.md).
> Missing values remain missing, partial FIT results must be labeled partial,
> and real output must remain local unless the data owner approves a separate
> privacy review. The current `garmin_activity_key` can incorporate a source
> activity ID and must be removed from an externally shared derivative.

### 2. Add a use-case link

Recommended placement: at the end of the proposed analysis section.

Proposed text:

> The [Run-All use-case catalog](docs/project/run_all_use_case_catalog_v0_1.md)
> documents supported descriptive questions, required files and fields,
> interpretation limits, and future-only concepts.

### 3. Add an M5 case-study preview

Recommended placement: near **Project map** or after the analysis section.

Proposed text:

> A future case study will demonstrate the synthetic, reproducible path from a
> Garmin export fixture to an analysis-ready handoff. It will not publish real
> Garmin data or imply medical or coaching interpretation. See the
> [M5 candidate assessment](docs/project/m5_case_study_candidates_v0_1.md).

### 4. Add concise execution evidence

Recommended placement: in **Current status**, after the Run-All implementation
statement.

Proposed text:

> The M2.1 Run-All snapshot also completed a private real-export validation:
> two independent runs returned `PASS`, preserved the input, produced
> byte-identical output, and passed the public-safe privacy check. The export
> and generated personal output remain private and are not repository fixtures.

This wording intentionally omits record counts, dates, paths, filenames,
identifiers, and private fingerprints.

## Proposed corrections to current wording

The current README states that Run-All has been validated only with synthetic
fixtures and repeats that limitation under **Known limitations**. After M3, that
statement is no longer current. Replace it with the concise evidence text above
while retaining the distinction between:

- public, reproducible synthetic fixtures; and
- private, public-safe real-export execution evidence.

Do not imply that every Garmin export variant is supported or that private
real-data output is available to users.

The current README also says the Activities CSV excludes raw Garmin activity
IDs. Qualify that statement: there is no separate `activity_id` column, but the
current `garmin_activity_key` may incorporate the source activity ID. The key
must remain private and be removed from any externally shared derivative.

The Product Quick Start contains the same historical "not validated against
real Garmin data" wording. It is outside this README-only proposal, but a later
documentation-alignment task should update it consistently rather than leaving
README and Quick Start contradictory.

## Current limitations text

Keep these limitations, with minimal wording adjustments if needed:

- Activities are required; Gear, Personal Records, and FIT are optional and
  use exact filename rules.
- FIT support covers selected session and lap fields, not complete FIT CRC or
  invalid-sentinel handling.
- Weather, Sleep, HRV, Parquet, dashboards, notebooks, automatic Analysis Pack
  generation, PyPI publication, and a stable release are not implemented.
- The package does not promise a stable third-party Python API.
- Descriptive analysis is downstream of Run-All; the project does not provide
  medical, coaching, or personal-performance conclusions.

## Evidence and link checks before application

Before updating README:

1. Confirm all five linked M4 documents are committed at the proposed paths.
2. Confirm the M3 public-safe evidence still supports the execution statement.
3. Confirm the current release, package, and CLI status has not changed.
4. Run the repository's Markdown/path, privacy, test, bootstrap, static-policy,
   Platform-alignment, and public-history checks required by that change.
5. Keep README editing separate from product code unless review proves a
   combined change is necessary.
