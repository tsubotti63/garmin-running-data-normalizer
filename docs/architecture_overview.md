# Architecture Overview

- Applies to: stable v1.3.0
- Compatibility family: stable 1.x
- Authority: human-readable architecture overview
- Last reviewed: 2026-08-09

## Current stable architecture

Garmin Running Data Normalizer is a local-first Python CLI. Stable v1.3.0 reads
a local Garmin Account Data Export, normalizes supported JSON and FIT sources,
and publishes a deterministic handoff with 17 stable normalized datasets plus
QA, audit, provenance, schema, and navigation artifacts.

```text
Local Garmin Account Data Export (read-only)
  -> discovery and bounded archive intake
  -> JSON and FIT parsers
  -> normalizers and dataset registry
  -> relationship, QA, and schema validation
  -> deterministic local output and provenance
  -> optional local Snapshot lifecycle or external-safe Analysis Pack
```

## Input and privacy boundary

The input is a user-controlled local Export directory. The normalizer does not
modify it and performs no network upload. Full normalized output can contain
personal metrics, identifiers, filenames, hashes, timestamps, and provenance,
so it remains a local trusted handoff. Public fixtures are synthetic. The
optional external-safe pack is an allowlist-only reduced derivative and is
never uploaded automatically.

## Discovery, archives, and manifests

Discovery uses exact supported source patterns and rejects unsafe paths,
symbolic-link escapes, encrypted archives, traversal, and bounded archive-limit
violations. Accepted inputs are recorded through source-relative provenance and
SHA-256 evidence. `run_manifest.json` inventories published payloads;
`run_summary.json` is written last as the completion marker.

## JSON and FIT parsers

JSON normalizers retain source-backed values and explicit missing or review
states rather than guessing. The FIT path validates file CRC and optional
header CRC, supports multi-session files only when lap allocation is provable,
converts selected protocol invalid sentinels to null, and records rejected or
partial files in audit evidence. It does not expose unsupported raw telemetry
as a stable dataset.

## Dataset registry and stable grains

The executable dataset table, generated schema catalog, and versioned manifest
define each dataset's grain, stable key, requirement state, and output path.
Stable v1.3.0 contains the seven core Activity, Gear, Personal Record, and FIT
datasets plus ten optional Wellness / Metrics datasets. Five v1.3 families
preserve source-observation grain instead of selecting a latest daily value.
Absent optional source families emit empty datasets and
`SKIPPED_NOT_PRESENT` evidence without adding a warning.

## Explicit relationship boundary

Six reviewed relationships connect Activity/Gear Links, Gear, Activities,
Personal Records, FIT Sessions, FIT Laps, and Activity/FIT Links. Stable keys
establish identity only within their declared grain. Date, timestamp, filename,
or similar values never authorize an undeclared join. V1.3 Wellness / Metrics
guidance permits only explicitly labelled contextual comparison and does not
promote those rows into Activity facts.

## Snapshot lifecycle

The additive v1.2 Snapshot lifecycle stores explicitly confirmed complete
Exports as immutable, account-bounded local evidence. Registration is
content-idempotent, missing from a later Export never means delete, and
dataset-specific merge policies either upsert stable daily state, preserve
source observations, or regenerate FIT-derived output from the cumulative blob
set. Integrity verification, coverage, lineage, review holds, and canonical
merge summaries remain auditable. The Snapshot Store is private local data, not
a public artifact or backup service.

## QA, audit, and provenance

Every completed Run-All publishes dataset QA, relationship QA, family audits,
artifact inventory, manifest, and summary evidence. Fatal validation fails
closed; disclosed non-fatal gaps remain warnings or partial evidence. Output
ordering and hashes support deterministic repeat comparison. Provenance is
source-relative and no private host path is required by the public contract.

## Human- and machine-readable analysis handoff

`START_HERE.md`, `DATASET_INVENTORY.md`, and `ANALYSIS_HANDOFF.md` guide a
reader. `ANALYSIS_CONTEXT.json` and `SCHEMA_CATALOG.json` provide the equivalent
machine-readable dataset, relationship, type, privacy, and prohibited-operation
contracts. These generated artifacts project executable authorities; they do
not redefine normalization semantics.

## Stable, candidate, and deferred scope

- Stable: the 17 normalized datasets listed in
  [Supported Datasets](supported_datasets.md), the `1.x` CLI and output paths,
  the six explicit relationships, Snapshot lifecycle, and deterministic
  handoff.
- Candidate: Lactate Threshold remains audit-only. Its machine stable key,
  units, timezone semantics, and promotion rules are not approved.
- Deferred: Health Status is library-level and is not in the v1.3 stable
  registry. Open-Meteo, Parquet output, hosted processing, automatic upload,
  coaching, and medical interpretation are not implemented product features.

## Packaging, release, and CI status

Version 1.3.0 is the current stable GitHub Release and Production PyPI package,
licensed under Apache-2.0 for Python 3.11 or later. Packaging metadata derives
the version from the package source. CI validates the repository on Ubuntu and
the installed runtime path on `windows-latest`; Windows receives `tzdata`
through a conditional dependency. This is bounded compatibility evidence, not
a universal platform guarantee.

## ACP adoption and Product authority

Embedded AI Collaboration Platform materials govern AI-assisted development,
review, and evidence handling for maintainers. They are not imported by the
Python package and are not a Product runtime dependency. Product behavior is
owned by the Product contracts, schemas, tests, executable registry, and stable
release. ACP governance does not redefine the CLI, dataset, or output contract.

## Open-Meteo status

Open-Meteo remains not implemented and deferred. The stable runtime performs no
weather request or enrichment. Any future adapter requires separate Product,
privacy, attribution, retention, and production-use decisions before it can be
described as supported.
