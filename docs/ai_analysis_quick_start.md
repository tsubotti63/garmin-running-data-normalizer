# AI Analysis Quick Start

This guide explains how to begin a bounded descriptive analysis from Garmin
Running Data Normalizer `v1.2.1` output. The default path is local or otherwise
trusted analysis. The product never uploads data automatically.

“AI-ready” means the handoff includes data-contract context. It does not
guarantee that an AI answer is correct.

## 1. Confirm a completed run

Require:

```text
<output>/run_summary.json
```

This file is written last and is the completion marker. Accept only:

- `PASS`;
- `PASS_WITH_WARNINGS`, after reviewing the warnings; or
- deliberately reviewed `PARTIAL_SUCCESS`.

Exit code `2` does not publish a completed handoff. With
`PARTIAL_SUCCESS`, limit FIT-derived analysis to the parsed subset and label the
result partial.

## 2. Follow the handoff navigation

Read the generated files in this order:

1. `START_HERE.md`
2. `DATASET_INVENTORY.md`
3. `ANALYSIS_HANDOFF.md`
4. `ANALYSIS_CONTEXT.json` when machine-readable context is useful
5. `SCHEMA_CATALOG.json` for field types, units, origins, and sensitivity

Start with `analysis/activities.csv` only when its activity-level columns fit
the question. Detailed normalized, audit, QA, and manifest files remain
personal local output and should be added only when required.

## 3. Ask one descriptive question

Define:

- one question;
- the represented population and time range;
- grouping and explicit formulas;
- the denominator for every aggregate;
- missing-value handling; and
- the smallest authorized file set.

Use the canonical
[Analysis Prompt Template](project/analysis_prompt_template_v0_1.md) instead of
creating a competing prompt contract. The
[Analysis Handoff Specification](project/analysis_handoff_spec_v0_1.md)
defines the receiving rules, and the
[Run-All Use Case Catalog](project/run_all_use_case_catalog_v0_1.md) gives
bounded examples.

## 4. Preserve evidence boundaries

Apply these rules:

```text
missing != zero
blank != zero
unresolved != error
excluded != failed
coverage != success rate
```

- Report included, excluded, and missing row counts.
- Use only explicit relationships declared by the handoff.
- Do not join by date, timestamp, label, or filename similarity.
- Do not infer unavailable identity, location, unit, or source meaning.
- Keep observed facts, calculations, interpretations, and unknowns separate.
- Treat anomaly candidates as Human Review prompts, not conclusions.

The project does not provide medical diagnosis, coaching prescriptions,
injury, fatigue, readiness, motivation, fitness, or causal conclusions.

## 5. Prefer local or trusted analysis

Full output can contain raw IDs, stable keys, exact timestamps,
source-relative paths, hashes, memo text, and filenames containing
email-shaped personal identifiers. Keep it local and uncommitted.

Do not upload the whole Run-All directory merely because a service accepts ZIP
or JSON files. A receiving environment requires a separate provider, plan,
workspace, retention, training-use, history, memory, and deletion review.

## 6. Optional external-safe pack

When limited month-level Activity volume/count context is sufficient, opt in:

### macOS / Linux

```bash
python -m garmin_running_data_normalizer run-all \
  --input /path/to/extracted-garmin-export \
  --output /path/to/new-run-all-output \
  --external-safe-pack
```

### Windows PowerShell

```powershell
python -m garmin_running_data_normalizer run-all --input "C:\Garmin\Export" --output "C:\Garmin\Output\external-safe-01" --external-safe-pack
```

The stable Snapshot path supports the same option:

### macOS / Linux

```bash
python -m garmin_running_data_normalizer snapshot run-all \
  --store /path/to/private-snapshot-store \
  --output /path/to/new-snapshot-run-all-output \
  --external-safe-pack
```

### Windows PowerShell

```powershell
python -m garmin_running_data_normalizer snapshot run-all --store "C:\Garmin\SnapshotStore" --output "C:\Garmin\Output\snapshot-safe-01" --external-safe-pack
```

The generated file is:

```text
<output>/analysis/external_safe_handoff.zip
```

Its reviewed contract contains exactly five files:

```text
README.md
manifest.json
safe/ANALYSIS_CONTEXT.json
safe/SCHEMA_CATALOG.json
safe/activities_monthly.csv
```

The CSV has exactly six columns:

```text
activity_month
activity_type
sport_type
distance_m
duration_sec
lap_count
```

Despite its name, `activities_monthly.csv` is not pre-aggregated. Its grain is
one Activity per row; only the date is reduced to `YYYY-MM`. Compute monthly
counts, distance, and duration using explicit formulas.

The pack excludes identifiers, keys, paths, hashes, memo text, coordinates,
exact dates/times, heart rate, power, cadence, training effect/load, Gear,
Personal Records, FIT detail, and Activity/FIT relationships. Its relationship
list is empty, so it does not authorize cross-dataset joins.

The pack reduces the data surface but is not automatically safe for every
provider or question. A Human must inspect the five-file list, six-column
header, receiving environment, and exact transfer before upload.

## 7. Understand Snapshot lifecycle evidence

A Snapshot Run-All handoff additionally contains:

```text
snapshot/snapshot_lineage.json
snapshot/snapshot_coverage.json
snapshot/canonical_merge_summary.json
```

These files explain the accumulated input lifecycle and canonical build. They
do not create a new analytical join authority. Dataset joins still require the
explicit relationships declared by the Run-All handoff.

Snapshot semantics preserve distinctions such as:

- absent;
- null;
- empty;
- malformed;
- unsupported;
- retained; and
- promoted.

Absence alone is not deletion, and automatic deletion or garbage collection is
not provided.

[CS-007](case_studies/cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md)
reports bounded evidence from four repeated complete Exports from one account,
not four independent datasets. Within the reviewed set and merge policy, 6/6
pairwise comparisons, 24/24 tested registration orders, and 13/13 specified
failure/recovery checks passed. Those results are not universal,
zero-defect, statistical, or external-adoption claims.

## 8. Review the result

Before adopting an analysis:

- confirm the files, row grain, columns, represented range, and run warnings;
- verify formulas, denominators, and missing counts;
- separate observed facts, calculations, interpretations, and unknowns;
- confirm only explicit relationships were used;
- reject invented facts, unsupported units, or causal conclusions;
- check that identifiers and private details are not repeated in the answer;
  and
- record the Human reviewer and privacy decision.

A generative answer is not claimed to be byte-identical. Preserve the original
completed Run-All output as read-only local evidence and save the analysis as a
separate artifact.

## Related documents

- [Getting Started from a Garmin Export](getting_started_from_garmin_export.md)
- [Analysis Handoff Specification](project/analysis_handoff_spec_v0_1.md)
- [Analysis Prompt Template](project/analysis_prompt_template_v0_1.md)
- [Public Usage Example](project/run_all_public_usage_example_v0_1.md)
- [Run-All Use Case Catalog](project/run_all_use_case_catalog_v0_1.md)
- [CS-001: Real Export handoff](case_studies/cs-001-real-garmin-export-to-auditable-ai-ready-handoff.md)
- [CS-002: Relationship Coverage](case_studies/cs-002-relationship-coverage-as-evidence-boundary.md)
- [CS-007: Snapshot Accumulation](case_studies/cs-007-preserving-garmin-history-across-incomplete-repeated-exports.md)
- [FAQ](faq.md)
- [Support](../SUPPORT.md)
