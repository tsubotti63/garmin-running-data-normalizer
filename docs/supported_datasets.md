# Supported Datasets

This document defines the supported Garmin dataset and interface scope prepared
for the stable `1.0.x` line. All processing is local-first. Public fixtures are
synthetic; real exports and generated personal output must remain local.

## Stable CLI and output scope

This section is the human-readable Dataset Catalog for the stable Run-All v1
families. The executable dataset definitions and versioned registry remain the
machine authorities.

| Dataset | Source / interface | Role and authority | Grain | Stable key | Required | Provenance | Analysis suitability |
|---|---|---|---|---|---:|---|---|
| `activities` | `summarizedActivities.json`; `normalize-activities`, Run-All | Authoritative normalized activity records | activity | `garmin_activity_key` | yes | `source_path`, `source_sha256`, confidence | Detailed local activity analysis; use the reduced CSV when its columns are sufficient |
| `gear` | `gear.json`; Run-All | Authoritative normalized gear records | gear | `gear_key` | no | `source_path`, `source_sha256` | Local gear attribute analysis; cross-dataset use requires the relationship catalog |
| `activity_gear` | `gear.json`; Run-All | Authoritative normalized link records, not an activity Source of Truth | activity-gear link | `gear_key`, `activity_id` | no | `source_path`, `source_sha256` | Link inspection only until each cross-dataset relationship is explicit |
| `personal_records` | `personalRecord.json`; Run-All | Authoritative normalized personal-record entries | personal record | `personal_record_id` | no | `source_path`, `source_sha256`, confidence | Independent local reference; activity relationship is `not_yet_defined` |
| `fit_sessions` | bounded Activity `.fit`; Run-All | Authoritative bounded FIT session summaries | FIT file session | `fit_file_id` | no | `source_path`, `source_sha256` | Local bounded session analysis after audit review |
| `fit_laps` | bounded Activity `.fit`; Run-All | Authoritative bounded FIT lap summaries | FIT file lap | `fit_file_id`, `lap_index` | no | `source_path`, `source_sha256` | Local lap analysis; explicit child of the bounded FIT session via `fit_file_id` |

Run-All requires Activities. Gear, Personal Records, and FIT are optional and
produce explicit `SKIPPED_NOT_PRESENT` evidence when absent. The documented CLI,
exit-code behavior, fixed output paths, run completion marker, provenance, and
versioned Run-All manifest fields form the stable `1.x` interface.

The deterministic `analysis/activities.csv` is a reduced one-row-per-activity
projection of `normalized/activities.json`. It is the existing analysis handoff
entry point, but it is not a separate Source of Truth. QA, audit, manifest, and
summary files are evidence or navigation artifacts rather than normalized
datasets.

Cross-dataset joins are governed by the [Dataset Relationship
Catalog](dataset_relationships.md). Stable keys establish identity within their
declared grain; they do not independently authorize a cross-dataset join.

## Library-level scope

| Dataset or output | Implemented behavior | Stable CLI/Run-All status |
|---|---|---|
| Sleep | Daily normalization, review states, content identity, provenance | Library only |
| HRV | Bounded FIT Message 370 candidate and JSON consistency evidence | Library only |
| Health Status | Complete long metrics and fixed daily schema | Library only |
| Analysis Pack | Deterministic allowlist-only ZIP builder | Library only |

Library-level support means the implementation and synthetic tests are present,
but the dataset is not a promised Run-All output. These interfaces may evolve
compatibly as their normative contracts mature.

## Registry lifecycle

The example registry is version `1.0.0` with status `stable_release_ready`.
Validation continues to accept the previous
`local_implementation_not_publication_ready` status so existing registries are
not invalidated by this release.

See [Known Limitations](known_limitations.md), the
[Product Quick Start](product_quick_start.md), and the
[dataset registry](../config/dataset_registry.example.json). The consolidated
[Run-All Output Contract](output_contract.md) defines authority, completion,
status, compatibility, and privacy behavior.
