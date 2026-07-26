# Garmin Running Data Normalizer

[![PyPI version](https://img.shields.io/pypi/v/garmin-running-data-normalizer.svg)](https://pypi.org/project/garmin-running-data-normalizer/)
[![Python versions](https://img.shields.io/pypi/pyversions/garmin-running-data-normalizer.svg)](https://pypi.org/project/garmin-running-data-normalizer/)
[![CI](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/tsubotti63/garmin-running-data-normalizer.svg)](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/LICENSE)

**Turn a local Garmin Account Export into deterministic, auditable datasets and
reusable analysis context—without uploading the export.**

Garmin Running Data Normalizer is a local-first Python package that normalizes
Garmin Activities, Gear, Personal Records, FIT Sessions and Laps, and their
reviewed relationships. Run-All emits normalized data together with QA, audit,
provenance, explicit warnings, and human- and machine-readable analysis context.

```text
Garmin Account Data Export
  ↓
Deterministic Run-All
  ↓
Normalized datasets
+ QA
+ audit
+ provenance
+ explicit relationships
+ analysis context
  ↓
Reusable descriptive analysis
  ↓
Human review
```

Current stable release: **v1.2.0** · Python **3.11+** · Apache License 2.0

- [Install from PyPI](https://pypi.org/project/garmin-running-data-normalizer/)
- [Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_quick_start.md)
- [Getting Started with a Garmin Export](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/getting_started_from_garmin_export.md)
- [AI Analysis Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/ai_analysis_quick_start.md)
- [FAQ](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/faq.md)
- [Supported Datasets](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/supported_datasets.md)
- [Known Limitations](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/known_limitations.md)
- [Release Notes v1.2.0](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.2.0)

## Why this project

A Garmin Account Export is useful but is not automatically analysis-ready. It
can contain multiple dataset families, archive layers, JSON records, and FIT
assets with different grains and relationship boundaries. Ad hoc preprocessing
can change columns, identifiers, filters, joins, and assumptions from one
analysis to the next.

Without a stable handoff, repeated AI-assisted analysis can begin with the same
preparation work each time:

```text
Read the Export again
  → inspect the structure again
  → rebuild preprocessing
  → redefine missing-value rules
  → reconsider joins
  → finally begin the analysis
```

Run-All creates a reviewable boundary between that local export and downstream
analysis: deterministic normalization, fixed output, QA and provenance,
explicit relationships, visible warnings, and a separate human-owned
interpretation step. Unknown relationships and incomplete input are not guessed
away; unresolved, excluded, and warning states remain visible as evidence.

```text
Normalize locally
  → reuse the reviewed output
  → ask a specific descriptive question
  → keep facts, calculations, interpretation, and unknowns separate
```

The package does not send the export to a hosted processing service. Public
reproduction uses only synthetic fixtures.

### Built from a runner's own workflow

The project was created by a full-marathon runner who has achieved sub-3:15 and
is now working toward sub-3. It grew from repeated use of Garmin data for
long-term running review: the goal is not only to convert files, but to make the
same reviewed data foundation reusable across later analysis.

This runner story is supporting context, not a substitute for the product
contract, tests, limitations, or published evidence.

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

Use a new output path that does not already exist for every run. Run-All never
uploads the export. Start with `START_HERE.md` in the generated output. The
tracked fixture contains Activities only, so this tested example returns
`PASS_WITH_WARNINGS` with exit code 0 and records the absent optional families.

For the bounded activities-only Golden Path and its byte-for-byte Golden Result,
follow the complete
[Product Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/product_quick_start.md).

## Platform validation status

| Platform | Validation status | Current position |
|---|---|---|
| macOS | Maintainer validated | Primary development and validation environment |
| Windows | Validation pending | Intended supported platform; reproducible community reports are welcome |
| Linux | Automated CI validated | Full tests, validators, builds, and isolated installs run on `ubuntu-latest`; manual environment characterization is not yet claimed |

Windows is not excluded from the project. The current limitation is validation
evidence, not product intent. Reports should include the OS, shell, Python
version, package version, command, exit code, and public-safe error details.
Never attach a real Garmin Export or full personal Run-All output.

## Accumulate multiple Garmin Exports (v1.2.0)

The compatible one-shot command processes one supplied Export and does not
accumulate records across separate downloads. A later Garmin Export can omit
files, periods, records, or fields seen previously; that absence is not proof
of deletion. Keep every downloaded Export until it has been registered in a
verified Snapshot Store.

The additive Snapshot workflow in v1.2.0 keeps immutable local
observations, builds a cumulative approved input, and then reuses the existing
Run-All parser and output contract:

```bash
garmin-running-data-normalizer snapshot init \
  --store workspace/snapshot-store \
  --account local-account-01

garmin-running-data-normalizer snapshot register \
  --store workspace/snapshot-store \
  --input /path/to/complete-garmin-export \
  --label S1 \
  --requested-at 2030-01-01T00:00:00+00:00 \
  --downloaded-at 2030-01-01T01:00:00+00:00 \
  --observed-at 2030-01-01T02:00:00+00:00 \
  --confirm-complete

garmin-running-data-normalizer snapshot verify \
  --store workspace/snapshot-store

garmin-running-data-normalizer snapshot run-all \
  --store workspace/snapshot-store \
  --output workspace/snapshot-run-all
```

Use one opaque account token per person/account boundary. Snapshot Stores and
their Run-All outputs are private local data: place them outside synchronized
or shared folders where practical, restrict directory permissions (for example,
`chmod 700 workspace/snapshot-store` on a single-user Unix-like system), and
never commit them. Back up a store only after `snapshot verify` reports `PASS`;
verify it again after restoration. Snapshot and blob deletion, automatic
garbage collection, and automatic deletion inference are not provided.

Public-safe aggregate validation used four repeated Garmin Account Data Export
snapshots from the same account. It confirmed deterministic cumulative rebuilds,
missing-value state handling, FIT content deduplication without duplicate
decode, and all 13 specified failure/recovery checks, with zero modification of
the source Exports.

These were four repeated complete Exports from one account, not four
independent datasets. Within the reviewed Snapshot set and merge policy, all
6/6 pairwise comparisons, 24/24 tested registration-order permutations, and
13/13 specified failure/recovery checks passed. Seven materially distinct
missing/value states were preserved, and the reviewed validation reported
source mutation 0. These are bounded validation results, not a statistical,
universal order-independence, zero-defect, or external-adoption claim.

Read
[CS-007: Preserving Garmin History Across Incomplete Repeated Exports](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/case_studies/cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md).

Snapshot Accumulation is one data-integrity capability within the broader
analysis-ready foundation; it is not the entire product.

See the
[v1.2 migration guide](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/project/v1_2_snapshot_migration_guide_v1_0.md)
for adoption, backup, rollback, and one-shot compatibility guidance.

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
- `--input` must be a directory; passing a ZIP file directly is unsupported.
  ZIP assets discovered inside that directory are validated for traversal,
  links, encryption, entry count, size, total size, and compression-ratio
  limits.
- Stable keys, activity record grain, source-relative provenance, hashes, and
  deterministic QA are included in the reviewed output contract.
- Unsupported or unsafe Golden Path input fails closed with a non-zero exit
  status.

## Known limitations

Run-All v1 requires Activities; Gear, Personal Records, and FIT are optional.
Sleep, HRV, and Health Status are library-level interfaces and are not Run-All
outputs. Hosted processing, Open-Meteo, Parquet, and automatic upload are not
included. One-shot processing does not combine separate Export
downloads; retain each Export until the additive Snapshot lifecycle has
registered and verified it. Missing from a later Export is not a deletion
instruction. The documented CLI and versioned Run-All output contract are the
stable `1.x` interface; other Python modules may evolve compatibly as their
contracts mature. See
[Known Limitations](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/known_limitations.md)
for the
precise boundaries.

## Non-goals

Hosted processing, Garmin account authentication, JMA or Instagram ingestion,
wellness/coaching interpretation, personal analysis, and non-Garmin data
platform generalization are outside the project scope.

## Community

- [Contributing](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/CONTRIBUTING.md)
- [Support and public-safe bug reports](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/SUPPORT.md)
- [Frequently Asked Questions](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/main/docs/faq.md)

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
[Apache License 2.0](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v1.2.0/LICENSE).
