# M5 Case Study Candidates v0.1

## Selection principles

An M5 case study should demonstrate practical OSS value without publishing a
real Garmin export or personal output. It should be reproducible from synthetic
input, keep normalization separate from analysis, and avoid implying features
that Run-All v1 does not provide.

## Candidate 1 — From Garmin export to a reproducible analysis handoff

- **Whose problem:** A runner or analyst who wants a transparent local path from
  an account export to analysis-ready data.
- **Problem solved:** Shows safe intake, deterministic normalization, completion
  review, reduced Activities CSV, and a disciplined AI-analysis handoff in one
  end-to-end narrative.
- **Run-All artifacts:** `analysis/activities.csv`, `run_summary.json`,
  `run_manifest.json`, and `qa/dataset_summary.json`.
- **Public viability:** High. Use the tracked synthetic fixture and synthetic
  results only; mention real-export validation as aggregate engineering
  evidence without publishing its data or fingerprints.
- **Reproducibility:** High. Readers can run the documented command twice and
  compare output bytes.
- **OSS application value:** High. Demonstrates privacy, deterministic output,
  auditability, and a practical downstream use rather than normalization alone.
- **Additional implementation:** None for a documentation-first case study.
- **M5 recommendation:** **Recommended.**

## Candidate 2 — Multi-family completeness and safe partial-success review

- **Whose problem:** A maintainer or data engineer who needs to know which
  Garmin families were detected and whether FIT-derived analysis is complete.
- **Problem solved:** Demonstrates family status, warning interpretation,
  `PARTIAL_SUCCESS`, FIT audit, and the difference between absence, empty
  output, and incomplete parsing.
- **Run-All artifacts:** `run_summary.json`, `audit/fit_audit.json`,
  `qa/dataset_summary.json`, FIT session/lap JSON, and optional-family JSON.
- **Public viability:** Medium to high if a dedicated synthetic all-family and
  incomplete-FIT scenario is used.
- **Reproducibility:** High with existing synthetic tests; a polished public
  narrative may require packaging a smaller synthetic demonstration fixture.
- **OSS application value:** High for engineering trust, but less immediately
  approachable for a general runner.
- **Additional implementation:** Not required for the concept. A new committed
  public fixture or CLI convenience would be a separate reviewed task.
- **M5 recommendation:** Strong secondary candidate.

## Candidate 3 — Archive safety at real-world scale without weakening limits

- **Whose problem:** An OSS user processing a large official export and a
  maintainer responsible for fail-closed archive handling.
- **Problem solved:** Explains why bounded archive validation must support large
  legitimate exports while still rejecting excessive counts, traversal,
  absolute paths, symlinks, malformed archives, and unsafe destinations.
- **Run-All artifacts:** Public-safe M3 execution evidence, Run-All completion
  state, and synthetic archive-regression results. No real output is published.
- **Public viability:** High when all examples remain synthetic and only bounded
  pass/fail evidence is reported.
- **Reproducibility:** Medium to high. Boundary tests are reproducible; the
  private real-export execution is evidence but not a public fixture.
- **OSS application value:** High for safety and engineering credibility, but it
  emphasizes compatibility more than downstream analysis value.
- **Additional implementation:** None. A benchmark or archive generator would
  be out of M5 scope unless separately approved.
- **M5 recommendation:** Supporting engineering sidebar or later case study.

## Recommended M5 direction

Select **Candidate 1: From Garmin export to a reproducible analysis handoff**.
It provides the clearest user journey, is fully demonstrable with synthetic
input, directly uses all M4 handoff artifacts, and balances product value with
privacy and reproducibility. Candidate 3 can supply a short trust-and-safety
sidebar without becoming the primary story.

M5 should not publish real row counts, dates, paths, filenames, identifiers,
hashes, or record content. Any claimed calculation should be reproducible from
the public synthetic fixture.
