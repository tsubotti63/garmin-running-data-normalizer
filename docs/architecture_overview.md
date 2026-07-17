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

Open-Meteo, if enabled later, is an optional adapter. It must not introduce JMA
or private Source Project dependencies. Requests may contain coordinates and
therefore require explicit privacy documentation, minimum retention, and local
evidence controls.

## Repository responsibilities

- `src/`: future canonical product code only.
- `scripts/`: thin Human entry points and repository validation.
- `config/`: non-secret examples and defaults.
- `schemas/`: machine-readable public contracts.
- `tests/`: synthetic deterministic tests.
- `examples/`: visibly synthetic inputs and expected outputs.
- `docs/`: public product, governance, and operational documentation.
- `runtime/`: task bootstrap prompts; not product runtime state.

## Current implementation status

Only package identity and bootstrap validation exist. Parsers, normalizers,
Run-All, Open-Meteo, and Analysis Pack behavior are planned and unavailable.

## Source separation

The private Source Project is evidence and design input only. Current runtime
must not import it, shell out to it, reference its absolute path, or require its
generated artifacts.

