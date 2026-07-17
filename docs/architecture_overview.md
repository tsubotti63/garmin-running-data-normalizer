# Architecture Overview

## Target design

```text
Human Garmin Export (local, ignored)
  -> Intake Discovery (read-only)
  -> Input Manifest / hashes
  -> Parsers (JSON / FIT)
  -> Normalizers
  -> Dataset Registry + Merge Policies
  -> Deterministic Validators
  -> Normalized Output + Provenance
  -> Optional Analysis Pack
```

Open-Meteo remains a deferred optional adapter. It must not introduce JMA or
private predecessor dependencies. Coordinate handling, attribution, retention,
and production use tier require separate privacy and Human decisions.

## Repository responsibilities

- `src/`: canonical local product implementation.
- `scripts/`: repository validation and public-history safety checks.
- `config/`: non-secret examples and defaults.
- `schemas/`: machine-readable public contracts.
- `tests/`: synthetic deterministic tests.
- `examples/`: visibly synthetic inputs and expected outputs.
- `docs/`: public product, governance, and operational documentation.
- `runtime/`: public task bootstrap prompts; not runtime state or review evidence.

## Current implementation status

Implemented locally: safe export discovery and archive filtering, activity,
gear, personal-record and FIT session/lap normalization, stable identity,
dataset policy, deterministic QA, and an allowlist-only Analysis Pack builder.

Deferred: a final Run-All command, FIT CRC/invalid-sentinel completeness,
Open-Meteo, real-data validation, packaging completion, license selection, and
public release.

## Predecessor separation

A private predecessor was used only for responsibility-level design evidence.
The Target has fresh sanitized Git history and must not import the predecessor,
reference its private paths or task identifiers, or require its generated data.
