# Supported Datasets

This document defines the supported Garmin dataset and interface scope prepared
for the stable `1.0.x` line. All processing is local-first. Public fixtures are
synthetic; real exports and generated personal output must remain local.

## Stable CLI and output scope

| Dataset | Source pattern | Interface | Record grain and key |
|---|---|---|---|
| Activities | `summarizedActivities.json` | `normalize-activities`, Run-All | activity; `garmin_activity_key` |
| Gear | `gear.json` | Run-All when present | gear; `gear_key` |
| Activity/Gear links | `gear.json` | Run-All when present | link; `gear_key`, `activity_id` |
| Personal Records | `personalRecord.json` | Run-All when present | personal record; `personal_record_id` |
| FIT Sessions | bounded `.fit` Activity files | Run-All when present | FIT file session; `fit_file_id` |
| FIT Laps | bounded `.fit` Activity files | Run-All when present | FIT file lap; `fit_file_id`, `lap_index` |

Run-All requires Activities. Gear, Personal Records, and FIT are optional and
produce explicit `SKIPPED_NOT_PRESENT` evidence when absent. The documented CLI,
exit-code behavior, fixed output paths, run completion marker, provenance, and
versioned Run-All manifest fields form the stable `1.x` interface.

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
[dataset registry](../config/dataset_registry.example.json).
