# From a Real Garmin Export to an Auditable AI-Ready Handoff

## Summary

Garmin Account Export contains multiple data families, archives, JSON records,
and FIT assets. Garmin Running Data Normalizer `v1.1.1` processed one real-user
dataset locally and emitted deterministic normalized datasets, explicit
relationship evidence, QA/audit artifacts, and human- and machine-readable
analysis context.

The validation covered approximately 11.1 years, 3,468 Activities, 3,684 FIT
Sessions, and 37,432 FIT Laps. The run retained `PARTIAL_SUCCESS`, 0 errors, and
one `FIT_PARSE_INCOMPLETE` warning rather than guessing incomplete FIT data.
Three same-host repeats produced the same digest and byte-identical 20/20 output
files in every repeat. The private source and detailed output remain
unpublished; only reviewed aggregate evidence is used here.

These results describe one real-user validation dataset. They are not a
guarantee for every Garmin export or proof of continuous export coverage.

## The user problem

A Garmin export is useful but is not automatically ready for reproducible
analysis. It may contain nested archives, multiple JSON families, FIT assets,
different record grains, and relationships that cannot be established from
similarity alone. One-off preprocessing can change columns, filters, keys,
joins, and assumptions from task to task.

A normalized file by itself also does not explain:

- what was discovered and processed;
- which datasets and relationships are authoritative;
- which warnings affect downstream use;
- which values are missing rather than zero;
- which data may leave the local environment;
- which conclusions remain unsupported.

The project therefore treats normalization as an auditable handoff rather than
a file-conversion step.

## Local and privacy boundary

Run-All processes a user-controlled export locally. It does not require a hosted
processing service and never uploads the export or generated output.

Real exports and full Run-All outputs are personal local data. They can contain
stable keys, raw identifiers, exact timestamps, memo text, coordinates,
source-relative filenames, paths, hashes, and health/performance detail. None of
those private values are published in this case study.

Public reproduction uses the repository's synthetic fixtures. Real-user
validation is represented only by reviewed aggregates and state classifications.

## Run-All workflow

```text
Garmin Account Export
        ↓ local discovery and bounded archive intake
Normalized datasets and explicit relationships
        ↓
QA, audit, provenance, warnings, and completion state
        ↓
Human-readable and machine-readable analysis context
        ↓
Human-governed downstream analysis
```

A synthetic reproduction command is:

```bash
python -m garmin_running_data_normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all-case-study
```

The destination must be new and outside the input. Input is snapshotted before
processing and checked again before publication. `run_summary.json` is written
last as the completion marker.

## Output Experience

Run-All produces normalized data and explicit review context.

### Human-readable

- `START_HERE.md`
- `DATASET_INVENTORY.md`
- `ANALYSIS_HANDOFF.md`

### Machine-readable

- `ANALYSIS_CONTEXT.json`
- `SCHEMA_CATALOG.json`
- `artifact_inventory.json`
- `run_manifest.json`
- `run_summary.json`

The handoff records dataset roles, grain, stable keys, relationship contracts,
warnings, missing-value semantics, privacy boundaries, and prohibited
operations. “AI-ready” means that this context is supplied; it does not mean an
AI answer is guaranteed to be correct.

## Reviewed validation scale

The `v1.1.1` validation used one real-user dataset with:

| Measure | Reviewed aggregate |
|---|---:|
| Represented running-history span | approximately 11.1 years |
| Activities | 3,468 |
| FIT Sessions | 3,684 |
| FIT Laps | 37,432 |

The span is a validation scale, not proof that every day or every real-world
activity is present.

## Visible partial state instead of silent guessing

The validation result was:

| Field | Value |
|---|---:|
| Run status | `PARTIAL_SUCCESS` |
| Errors | 0 |
| Warnings | 1 × `FIT_PARSE_INCOMPLETE` |
| Incomplete FIT assets | 20 |
| Session/lap allocation conflicts | 19 |
| Unsupported chained assets | 1 |

The incomplete assets were retained as auditable partial evidence. They were not
silently omitted, converted to `PASS`, or repaired through inference. FIT-derived
analysis is limited to the parsed subset.

This behavior preserves useful output while making the boundary visible to the
user and to downstream tools.

## Deterministic reproducibility

Three repeated runs used the same input, Production package, and host.

| Check | Result |
|---|---:|
| Output digest | 3/3 same |
| Output files | 20/20 byte-identical in every repeat |
| Manifest | 3/3 same |
| Run Summary | 3/3 same |

The repeat condition was same-host with cache state `warm_or_unknown`. This is
reproducibility evidence for the stated environment, not a cold-run or
cross-machine performance guarantee. Private digest and hash values remain
unpublished.

## Relationship integrity

The validation established explicit Activity–FIT relationships without
converting unresolved candidates into guessed joins. Activity-side and eligible
FIT Session-side denominators remain separate, and unresolved, excluded,
independent, ambiguous, and duplicate states remain visible.

The detailed model and reviewed aggregates are documented in
[CS-002: Relationship Coverage as an Evidence Boundary](cs-002-relationship-coverage-as-evidence-boundary.md).

## Human–AI responsibility boundary

The product separates four responsibilities:

- **Normalizer:** safe discovery, deterministic records, provenance, QA,
  relationship evidence, completion state, and immutable publication.
- **Analysis context:** authorized files, grain, keys, formulas, missing-value
  semantics, and prohibited operations.
- **AI or approved analysis tool:** calculation, organization, and drafting
  within the supplied boundary.
- **Human:** privacy approval, context, value judgment, release, claims, and
  final interpretation.

AI assistance does not replace the human approval boundary.

## Why this matters for open source

The project demonstrates more than a parser. It provides an inspectable chain
from heterogeneous private input to deterministic output, explicit QA,
relationship evidence, privacy-aware analysis context, and synthetic public
reproduction.

A reviewer can inspect:

- what the stable interface accepts and emits;
- how unsafe archives and incomplete FIT input are handled;
- which relationships are explicit and which remain unknown;
- how repeat runs are compared;
- which fields and artifacts are private;
- which conclusions the system does not support.

The dependency-free runtime and synthetic fixtures lower the barrier to
independent review.

## Reproduce the public workflow

1. Follow the [Product Quick Start](../product_quick_start.md).
2. Run the synthetic `run-all` command into a new destination.
3. Review `run_summary.json` before inspecting data.
4. Read `START_HERE.md` and `ANALYSIS_HANDOFF.md`.
5. Inspect relationship QA before joining datasets.
6. Repeat into another new destination and compare the output bytes.
7. Do not replace the synthetic fixture with real rows in a public reproduction.

## Limitations

- The evidence comes from one real-user dataset and does not characterize every
  Garmin export.
- FIT analysis is limited to the parsed subset when status is
  `PARTIAL_SUCCESS`.
- Same-host repeated output does not establish cross-machine performance.
- Full real-user output remains private.
- Sleep, HRV, and Health Status are library-level interfaces, not Run-All output
  families in v1.1.
- The project does not provide medical, diagnostic, coaching, readiness, or
  causal conclusions.

See [Known Limitations](../known_limitations.md) for the current product boundary.
