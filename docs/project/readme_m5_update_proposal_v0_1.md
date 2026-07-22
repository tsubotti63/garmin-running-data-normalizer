# README M5 Update Proposal v0.1

## Status

Proposal only. Do not modify `README.md` as part of M5. Apply this material only
after M5.5 verifies links, public wording, current release state, and privacy.

## Proposed section — Why this project matters

Recommended placement: after **Current status**.

> ## Why this project matters
>
> Garmin Running Data Normalizer creates a reviewable boundary between a local
> Garmin Account Export and downstream analysis. Run-All preserves the input,
> publishes a fixed deterministic output layout, records QA and provenance, and
> makes warnings or partial FIT processing explicit. Analysis remains a
> separate step governed by a reusable handoff contract.
>
> The [case study](docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md)
> shows how synthetic Run-All output becomes consistent evidence for analysis
> without publishing a real export or letting an AI make the user's decision.

## Proposed section — Reproducible analysis examples

Recommended placement: after **Run the minimum multi-family workflow**.

> ## Reproducible analysis examples
>
> Three public examples use fictional dates and synthetic values only:
>
> - [Monthly and Weekly Training Trends](examples/analysis/monthly_weekly_training_trends/README.md)
> - [Pace and Heart Rate Relationship](examples/analysis/pace_heart_rate_relationship/README.md)
> - [Training Consistency and Return Pattern](examples/analysis/training_consistency_return_pattern/README.md)
>
> Each example includes a CSV without stable keys, a reusable prompt, a reviewed
> result, explicit uncertainty, unsupported conclusions, and reproduction
> rules. Calculated facts are reproducible; generative wording is not claimed to
> be byte-identical.

## Proposed Analysis Handoff route

> Before analysis, review `run_summary.json`. For a trusted local environment,
> start with `analysis/activities.csv` and the
> [Analysis Handoff Specification](docs/project/analysis_handoff_spec_v0_1.md).
> Use the [prompt template](docs/project/analysis_prompt_template_v0_1.md) to
> separate facts, calculations, interpretation, and unknowns.

## Proposed reproducibility evidence

> The M2.1 snapshot completed a private real-export validation with status
> `PASS` and exit code `0`. The input remained unchanged, two independent runs
> produced byte-identical output, and the public-safe privacy check passed. No
> real rows, dates, filenames, paths, identifiers, counts, or private
> fingerprints are published.

## Proposed privacy boundary

> Real exports and generated output remain local. The current
> `garmin_activity_key` may incorporate a source activity ID and must be removed
> from any externally shared derivative. Review whether exact dates and times
> are necessary before transfer. Never upload normalized JSON, manifest, or FIT
> audit output to an external service without data-owner approval and a
> provider-specific privacy review.

## Current limitations to retain

- Activities are required; Gear, Personal Records, and FIT are optional.
- FIT output covers selected session and lap fields, not complete FIT behavior.
- Weather, Sleep, HRV, Parquet, dashboards, notebooks, and automatic Analysis
  Pack generation are not part of Run-All v1.
- Analysis is descriptive and does not provide medical or coaching conclusions.
- The package does not promise a stable third-party Python API.

## Existing wording to correct when applied

Replace the historical claim that Run-All has only synthetic validation. Keep
the distinction between public reproducible synthetic examples and private
public-safe real-export execution evidence. Qualify the current statement that
the Activities CSV excludes raw activity IDs: it has no separate `activity_id`
column, but the stable key may incorporate the source activity ID.

The Product Quick Start has related historical wording and should be aligned in
a separate reviewed documentation change if M5.5 confirms scope.

## M5.5 readiness

M5.5 should verify:

1. every proposed link from repository root;
2. every public-safe M3 claim;
3. the synthetic origin and arithmetic of all examples;
4. the current RC, package, and public repository status;
5. stable-key and date/time privacy language;
6. whether README and Product Quick Start changes should be one or two focused
   commits.
