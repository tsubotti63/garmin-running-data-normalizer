# From Garmin Export to a Reproducible Analysis Handoff

## 1. Summary

Garmin Running Data Normalizer turns a user-controlled Garmin Account Export
into a fixed, local, deterministic set of normalized datasets, QA evidence, and
an analysis-ready Activities CSV. A separate handoff contract then shows a
human or approved analysis tool how to calculate descriptive results without
confusing normalization facts with interpretation.

**After:** one Run-All command produces a consistent output layout without
modifying the input; summary and manifest files make completion reviewable;
independent runs from identical input can be compared byte for byte; and a
reusable prompt makes the structure of downstream analysis repeatable.

## 2. User Problem

A Garmin export is useful but not automatically analysis-ready. It can contain
multiple dataset families, archive layers, JSON records, and FIT files. A user
who repeatedly creates one-off preprocessing steps may get different columns,
filters, identifiers, and assumptions each time. The same instability can carry
into AI prompts, making results hard to review or reproduce.

## 3. Before

- Export structure and supported files had to be rediscovered for each task.
- Multiple dataset families were mixed with different record grains.
- Analysis preprocessing was difficult to reuse.
- The input handed to an AI could change from one request to the next.
- Input discovery, normalization, analysis, and interpretation could become
  one unreviewable step.
- It was difficult to prove that rerunning the workflow preserved the input and
  produced the same result.

## 4. Constraints

- Processing must stay local and must not require a hosted service.
- A real export and generated personal output must never be committed.
- Archive safety cannot be weakened merely to accept a large legitimate export.
- Output must be deterministic and must never overwrite an existing destination.
- Missing values, warnings, and incomplete FIT processing must remain visible.
- Descriptive analysis must not become medical or coaching advice.

## 5. Input Boundary

Run-All accepts an existing, non-symlink export directory containing extracted
Garmin files, supported ZIP archives, or both. Activities are required. Gear,
Personal Records, and FIT are optional. Input is snapshotted before processing
and checked again before output publication. Paths, archive members, sizes,
compression, encryption, and links are bounded by fail-closed safety rules.

Public reproduction uses only the repository's visibly synthetic fixture. The
private real-export validation is represented only by approved aggregate pass
facts, never by rows, filenames, paths, dates, counts, or fingerprints.

## 6. Run-All Workflow

```bash
python -m garmin_running_data_normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all-case-study
```

Run-All discovers supported assets, normalizes detected families, validates
stable keys and provenance, performs deterministic QA, creates the reduced
Activities CSV, verifies the input snapshot, writes to a staging directory,
and atomically publishes a new destination. `run_summary.json` is written last
as the completion marker.

## 7. Normalized Outputs

The fixed output includes normalized Activities, Gear, activity-gear links,
Personal Records, FIT sessions and laps, FIT audit evidence, dataset QA,
`analysis/activities.csv`, `run_manifest.json`, and `run_summary.json`.

The CSV provides activity-grain descriptive fields such as local date, activity
type, distance, duration, heart rate, power, cadence, training effect, load, and
lap count when available. It omits memo text, paths, hashes, and coordinates.
Its stable key may incorporate a source activity ID and therefore remains
private; it must be removed from an externally shared derivative.

## 8. Analysis Handoff

Normalization and analysis remain separate responsibilities:

- **Normalizer:** safe discovery, deterministic records, provenance, QA,
  completion status, and immutable output publication.
- **Analysis prompt:** authorized columns, formulas, grouping, missing-value
  policy, and separation of facts from interpretation.
- **Human:** privacy approval, context, value judgment, and the final decision.

For a trusted local analysis environment, the usual minimum is
`analysis/activities.csv` plus `run_summary.json`. `run_manifest.json` remains
local verification evidence. External transfer requires a separately reviewed
derivative with the stable key removed and date/time granularity assessed.

See the
[`Analysis Handoff Specification`](../project/analysis_handoff_spec_v0_1.md)
and [`Analysis Prompt Template`](../project/analysis_prompt_template_v0_1.md).

## 9. Reproducibility Evidence

The private M3 execution established only these public-safe facts:

- Run-All completed against a local real export with status `PASS` and exit
  code `0`.
- The input was unchanged.
- Two independent executions produced byte-identical output.
- The privacy check passed.
- A discovered archive-compatibility gap was fixed by raising a bounded member
  limit while preserving the remaining archive safety controls.
- Synthetic tests and repository validations passed for the snapshot.

No private counts, dates, filenames, paths, records, or hashes are needed to
support those claims.

## 10. Privacy Boundary

Real Run-All output is personal local data. Normalized JSON, manifest, and audit
files can contain identifiers, exact dates, source-relative paths, hashes, or
record-level metrics. They are not public artifacts. Public examples use
fictional future dates and synthetic values, omit stable keys, and explain only
the analysis structure.

Byte-identical verification is performed locally. Private input or output
fingerprints are not published. An external AI receives only a data-owner-
approved derivative or aggregate, never the unreviewed Run-All tree.

## 11. Example Analysis

M5 includes three separate, reproducible examples:

1. [Monthly and Weekly Training Trends](../../examples/analysis/monthly_weekly_training_trends/README.md)
2. [Pace and Heart Rate Relationship](../../examples/analysis/pace_heart_rate_relationship/README.md)
3. [Training Consistency and Return Pattern](../../examples/analysis/training_consistency_return_pattern/README.md)

Each example contains a synthetic CSV, reusable prompt, reviewed result, and
reproduction rules. Calculated facts are expected to match; generative prose is
not claimed to be byte-deterministic.

## 12. Decision-Support Value

The consistency example organizes a visible gap and a lower-volume return
segment into reviewable facts and human-owned options. It does not choose an
option or infer injury, fatigue, readiness, or recovery.

> Normalized history does not make the decision. It makes the evidence used for
> the decision consistent, reviewable, and reusable.

The normalizer guarantees the input/output contract. The prompt structures the
analysis. The human supplies missing context and owns the decision.

## 13. What This Does Not Do

- It does not diagnose health, injury risk, overtraining, or readiness.
- It does not create coaching recommendations.
- It does not infer Sleep, HRV, weather, fatigue, intent, or missing activities.
- It does not provide record-level FIT telemetry or coordinates.
- It does not make a real export or generated output public.
- It does not turn generative text into a deterministic product artifact.

## 14. Why This Matters for Open Source

The project demonstrates more than a parser. It provides an inspectable chain
from unsafe and heterogeneous local input to deterministic normalized output,
explicit QA, privacy-aware analysis handoff, and reproducible public examples.
Users can review what was processed, which warnings matter, which calculations
were applied, and which conclusions remain unsupported. The standard-library-
first implementation and synthetic examples lower the barrier to independent
verification.

## 15. Reproduction Steps

1. Create a clean local environment and install the package.
2. Run the synthetic Run-All command into a new destination.
3. Review `run_summary.json` before inspecting data.
4. Keep `run_manifest.json` for local provenance and output verification.
5. Choose one analysis example and use its exact `input_sample.csv` and
   `prompt.md`.
6. Compare calculated facts with its `result.md`.
7. Repeat Run-All into another new destination and compare output bytes.
8. Do not substitute real rows into any public reproduction.

The complete synthetic workflow is described in the
[`Public Usage Example`](../project/run_all_public_usage_example_v0_1.md).

## 16. Known Limitations

Activities are required. Optional-family coverage depends on exact filename
rules. FIT parsing is bounded to selected session and lap fields and does not
implement complete FIT CRC or invalid-sentinel handling. Weather, Sleep, HRV,
Parquet, dashboards, notebooks, automatic Analysis Pack generation, and a
stable third-party Python API are outside the current contract. The examples
are descriptive and deliberately small.

## 17. Next Milestones

- M5.5: independently review public safety, link integrity, factual accuracy,
  release-state wording, and readiness to apply README changes.
- Apply README changes only through a separately reviewed documentation task.
- Decide whether an external-sharing-safe derivative exporter is valuable; if
  adopted, specify and implement it separately.
- Keep M6 application wording distinct from product evidence and release state.
