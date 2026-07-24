# Garmin Running Data Normalizer

**Turn a local Garmin Account Export into deterministic, auditable datasets and
analysis context—without uploading the export.**

Garmin Running Data Normalizer is a local-first Python package that normalizes
Garmin Activities, Gear, Personal Records, FIT Sessions and Laps, and their
reviewed relationships. Run-All emits normalized data together with QA, audit,
provenance, explicit warnings, and human- and machine-readable analysis context.

Current stable release: **v1.1.1** · Python **3.11+** · Apache License 2.0

- [Install from PyPI](https://pypi.org/project/garmin-running-data-normalizer/)
- [Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_quick_start.md)
- [Supported Datasets](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/supported_datasets.md)
- [Known Limitations](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/known_limitations.md)
- [GitHub Release v1.1.1](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.1.1)

## Why this project

A Garmin Account Export is useful but is not automatically analysis-ready. It
can contain multiple dataset families, archive layers, JSON records, and FIT
assets with different grains and relationship boundaries. Ad hoc preprocessing
can change columns, identifiers, filters, joins, and assumptions from one
analysis to the next.

Run-All creates a reviewable boundary between that local export and downstream
analysis: deterministic normalization, fixed output, QA and provenance,
explicit relationships, visible warnings, and a separate human-owned
interpretation step. Unknown relationships and incomplete input are not guessed
away; unresolved, excluded, and warning states remain visible as evidence.

The package does not send the export to a hosted processing service. Public
reproduction uses only synthetic fixtures.

## Install

```bash
python -m pip install garmin-running-data-normalizer
garmin-running-data-normalizer --version
```

The equivalent module command is
`python -m garmin_running_data_normalizer --version`. The project has no
third-party runtime package dependency.

Maintainers can reproduce the packaging gate without uploading anything:

```bash
python -m pip install -e '.[test,release]'
python -m build
python -m twine check --strict dist/*
```

## Try the synthetic workflow

No Garmin account or real export is required. Clone the repository so the
tracked synthetic fixture is available, then install the checkout:

```bash
git clone https://github.com/tsubotti63/garmin-running-data-normalizer.git
cd garmin-running-data-normalizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
garmin-running-data-normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all
```

Use a new output directory for every run. Run-All never uploads the export.
Start with `START_HERE.md` in the generated output. The tracked fixture contains
Activities only, so this tested example returns `PASS_WITH_WARNINGS` with exit
code 0 and records the absent optional families.

For the bounded activities-only Golden Path and its byte-for-byte Golden Result,
follow the complete
[Product Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_quick_start.md).

## A handoff, not just converted files

Run-All includes the context needed to review and analyze the result without
reverse-engineering the data model.

**Human-readable**

- `START_HERE.md`
- `DATASET_INVENTORY.md`
- `ANALYSIS_HANDOFF.md`

**Machine-readable**

- `ANALYSIS_CONTEXT.json`
- `SCHEMA_CATALOG.json`
- `artifact_inventory.json`
- `run_manifest.json`
- `run_summary.json`

The handoff describes dataset roles, grain, stable keys, explicit relationships,
warnings, missing-value semantics, privacy boundaries, and prohibited
operations. “AI-ready” means that this context is supplied; it does not
guarantee that an AI answer is correct.

Exit code 0 means `PASS` or `PASS_WITH_WARNINGS`; exit code 2 is a fatal
contract, input, QA, or publication error; exit code 3 means `PARTIAL_SUCCESS`
because detected FIT input has an auditable incomplete parse. Existing output
is never overwritten, and identical input produces byte-identical output.

Add `--external-safe-pack` to create a deterministic, reviewable ZIP containing
an allowlisted month-level Activities projection. Run-All creates the pack
locally and never uploads it.

## Supported datasets and interfaces

| Dataset or output | Implemented scope | Formal CLI support |
|---|---|---|
| Activities | `summarizedActivities.json` normalization with activity grain, `garmin_activity_key`, provenance, QA, and manifest | Yes |
| Gear and activity-gear links | `gear.json` normalizer | Run-All |
| Personal records | `personalRecord.json` normalizer | Run-All |
| FIT sessions and laps | CRC-validated multi-session parser with `fit_session_key` and `fit_lap_key`; record coordinates and raw telemetry are not emitted | Run-All |
| Activity/FIT links | Auditable evidence-qualified links with exclusions and relationship QA | Run-All |
| Sleep | `sleepData.json` daily normalization with review states and provenance; no filling or inference | No; library level only |
| HRV | FIT Message 370 / Field 1 daily candidate with invalid-sentinel handling and non-promotional JSON consistency evidence | No; library level only |
| Health Status | Exact-suffix `healthStatusData.json` long metrics and fixed daily schema with explicit dedupe/review evidence | No; library level only |
| Analysis Pack | Deterministic allowlist-only ZIP; optional external-safe profile is limited to month-level activity volume/count and removes identifiers, provenance, exact timestamps, and unneeded health/performance detail | Run-All opt-in |

The dataset registry documents stable keys, record grain, merge policy, and
provenance requirements. See
[Supported Datasets](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/supported_datasets.md)
for the stable CLI/output boundary and library-level scope.

## Reviewed real-user validation

Version `1.1.1` was validated locally on **one real-user dataset** spanning
approximately **11.1 years**, with **3,468 Activities**, **3,684 FIT Sessions**,
and **37,432 FIT Laps**. These figures describe that validation dataset; they are
not a guarantee for every Garmin export or proof of continuous coverage.

The validation run completed with `PARTIAL_SUCCESS`: **0 errors** and
**1 `FIT_PARSE_INCOMPLETE` warning**. Twenty incomplete FIT assets
(19 session/lap allocation conflicts and 1 unsupported chained asset) were
retained as auditable partial evidence instead of being guessed. FIT-derived
analysis is therefore limited to the parsed subset.

Under the same input, Production package, and host, three repeated runs produced
the same digest and byte-identical **20/20 output files** in every repeat. The
repeat condition was same-host with cache state `warm_or_unknown`; this is not a
cross-machine performance guarantee. Private rows, paths, identifiers,
filenames, hashes, and detailed output remain unpublished.

Read
[CS-001: From a Real Garmin Export to an Auditable AI-Ready Handoff](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/case_studies/cs-001-real-garmin-export-to-auditable-ai-ready-handoff.md).

## Explicit relationships—unknown stays unknown

Relationship Coverage reports the boundary that can be linked by explicit
evidence; it is **not a success score**.

In the same one-user validation dataset, Run-All established 3,464 explicit
Activity–FIT relationships: 3,464 of 3,468 Activities and 3,464 of 3,465 eligible
FIT Sessions. Four Activities and one eligible FIT Session remained unresolved
rather than being guessed; ambiguous matches were 0, duplicate matches were 0,
and inference was not performed. Activity-side and FIT Session-side
denominators remain separate.

Read
[CS-002: Relationship Coverage as an Evidence Boundary](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/case_studies/cs-002-relationship-coverage-as-evidence-boundary.md).

## Analyze Run-All output

Review generated `START_HERE.md` first. In a trusted local environment, follow
`DATASET_INVENTORY.md` and `ANALYSIS_HANDOFF.md`, then start with
`analysis/activities.csv` and the
[Analysis Handoff Specification](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/project/analysis_handoff_spec_v0_1.md).

The
[Run-All Output Contract](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/output_contract.md),
[Dataset Catalog](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/supported_datasets.md),
and
[Dataset Relationship Catalog](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/dataset_relationships.md)
explain artifact
authority, dataset roles, and the explicit v1.1 joins. The
[prompt template](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/project/analysis_prompt_template_v0_1.md),
[public usage example](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/project/run_all_public_usage_example_v0_1.md),
and
[use-case catalog](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/project/run_all_use_case_catalog_v0_1.md)
separate facts,
calculations, interpretation, and unknowns.

Three key-free synthetic examples are available:

- [Monthly and Weekly Training Trends](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/examples/analysis/monthly_weekly_training_trends/README.md)
- [Pace and Heart Rate Relationship](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/examples/analysis/pace_heart_rate_relationship/README.md)
- [Training Consistency and Return Pattern](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/examples/analysis/training_consistency_return_pattern/README.md)

Calculated facts are reproducible; generative wording is not claimed to be
byte-identical. The current `garmin_activity_key` may incorporate a source
activity ID. Keep real CSV local, remove that key from any externally shared
derivative, and review exact date/time granularity before transfer.

## Privacy and interpretation boundaries

Real Garmin exports and full Run-All outputs are personal local data. Full
normalized JSON, manifests, and audit files can contain identifiers, exact
timestamps, source-relative paths, hashes, memo text, or source filenames that
include email-shaped personal identifiers. Do not commit or upload real rows,
stable keys, raw IDs, memo text, coordinates, source filenames, private paths,
or raw private hashes.

Public examples use synthetic data or reviewed aggregate evidence only. The
optional external-safe pack removes identifiers, keys, paths, hashes, memo text,
coordinates, exact dates/times, heart rate, power, cadence, training effect/load,
and other unneeded health or performance detail; it still requires human review
before transfer.

The project does not provide medical, diagnostic, coaching, readiness, or
causal conclusions. A human remains responsible for privacy approval, context,
value judgment, and final interpretation.

## Local verification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/validate_bootstrap.py
python3 scripts/static_policy_scan.py
python3 scripts/validate_platform_alignment.py
python3 scripts/validate_public_history.py --ci
```

The public-history command assumes a normal public clone whose `origin/HEAD`
points to `origin/main`. Only synthetic fixtures may be committed. Real Garmin
exports and generated personal output belong in ignored local directories.

## Activities Golden Path guarantees

- The documented Golden Path produces byte-identical JSON for identical input.
- Input is read-only; output must be absent or empty and is never silently
  overwritten.
- ZIP input is validated for traversal, links, encryption, entry count, size,
  total size, and compression-ratio limits.
- Stable keys, activity record grain, source-relative provenance, hashes, and
  deterministic QA are included in the reviewed output contract.
- Unsupported or unsafe Golden Path input fails closed with a non-zero exit
  status.

## Known limitations

Run-All v1 requires Activities; Gear, Personal Records, and FIT are optional.
Sleep, HRV, and Health Status are library-level interfaces and are not Run-All
outputs. Hosted processing, Open-Meteo, Parquet, and automatic upload are not
included. The documented CLI and versioned Run-All output contract are the
stable `1.x` interface; other Python modules may evolve compatibly as their
contracts mature. See
[Known Limitations](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/known_limitations.md)
for the
precise boundaries.

## Non-goals

Hosted processing, Garmin account authentication, JMA or Instagram ingestion,
wellness/coaching interpretation, personal analysis, and non-Garmin data
platform generalization are outside the project scope.

See the
[Product Change History](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_changelog.md)
for factual product
changes. The root `CHANGELOG.md` is the byte-locked change log of the adopted AI
Collaboration Platform v0.9 Standard, not a Garmin product release history.

## Project map

- `docs/project_os/`: unmodified AI Collaboration Platform v0.9 Standard
- `docs/project/`: Project Customization and current phase controls
- `docs/proofs/`: Platform capability evidence
- `docs/reference/`: reuse, privacy, licensing, release, and handoff references
- `templates/`: unmodified Platform project/operation templates
- `runtime/`: unmodified Platform runtime plus Target Runtime Addendum
- `src/garmin_running_data_normalizer/`: public product implementation
- `tests/`: synthetic, dependency-free unit tests
- `packages/`: tracked package policy; review packs are generated under ignored
  `.review/`

This project is licensed under the
[Apache License 2.0](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.1.1/LICENSE).
