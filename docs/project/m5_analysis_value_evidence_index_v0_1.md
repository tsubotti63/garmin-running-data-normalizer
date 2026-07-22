# M5 Analysis Value Evidence Index v0.1

## Purpose

This index connects the private execution evidence, public-safe handoff
contracts, synthetic analysis examples, and M5.5 review targets. It does not
publish a real export or generated personal output.

| Path or reference | Purpose | Public-safe | Reproducible | M5.5 relevance |
|---|---|---|---|---|
| External local `run_all_execution_report_v0_1.json` | Machine-readable M3 pass facts | Yes; reviewed aggregate only, not tracked | Yes; records two executions and integrity verdicts | Verify claims against the local evidence without copying private data |
| External local `run_all_execution_note_v0_1.md` | Human-readable M3 execution note | Yes; reviewed aggregate only, not tracked | Yes | Verify public wording and private-evidence boundary |
| `docs/project/analysis_handoff_spec_v0_1.md` | Defines files, grains, missingness, privacy, responsibility, and reproducibility | Yes | Yes; versioned contract | Review stable-key and external-transfer language |
| `docs/project/analysis_prompt_template_v0_1.md` | Reusable fact/interpretation prompt structure | Yes | Same response structure; prose may vary | Confirm unsupported-conclusion rules |
| `docs/project/run_all_public_usage_example_v0_1.md` | Synthetic end-to-end usage | Yes | Yes | Verify commands and links |
| `docs/project/run_all_use_case_catalog_v0_1.md` | Supported and future-only analysis questions | Yes | N/A; design catalog | Verify every field against the public contract |
| `examples/analysis/monthly_weekly_training_trends/` | Calendar aggregation example | Yes; synthetic, key-free | Yes; fixed CSV, formulas, prompt, reviewed result | Recalculate arithmetic and review uncertainty |
| `examples/analysis/pace_heart_rate_relationship/` | Derived pace and observed heart-rate example | Yes; synthetic, key-free | Yes | Recalculate pace and verify non-causal wording |
| `examples/analysis/training_consistency_return_pattern/` | Human-owned decision-support example | Yes; synthetic, key-free | Yes | Verify no diagnosis or prescriptive decision |
| `docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md` | Primary public case study | Yes | Yes through linked synthetic steps | Review evidence chain and OSS-value claims |
| `docs/project/readme_m5_update_proposal_v0_1.md` | README link and wording proposal | Yes | N/A; proposal | Decide application scope after link and state review |
| `docs/project/m5_5_readiness_handoff_v0_1.md` | M5.5 intake snapshot | Yes | N/A; status document | Primary M5.5 starting point |

## Privacy verification

- All committed example values are deliberately fictional and use future dates.
- Samples contain no `garmin_activity_key`, raw ID, account identifier, path,
  hash, coordinate, email, credential, or real record content.
- Case-study execution claims are limited to the public-safe M3 verdicts.
- Private input/output fingerprints and concrete real-data counts are excluded.

## Reproduction index

Each analysis directory contains `README.md`, `prompt.md`, `result.md`, and
`input_sample.csv`. Its README defines formulas and denominators. The Primary
Case Study connects those examples to the synthetic Run-All command and M4
handoff contracts.

## M5.5 open checks

- Independent recalculation of all synthetic results.
- Full Markdown link and repository structure validation.
- Public privacy scan of the complete proposed change.
- Confirmation that M3 public-safe claims still match local Evidence.
- Review of the current RC tag versus the newer local implementation snapshot.
- Decision on applying README and Product Quick Start wording updates.
- Confirmation that no code implementation is needed for the selected M5/M5.5
  documentation path.
