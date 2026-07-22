# v0.1.0-rc.2

## Release summary

This prerelease expands Garmin Running Data Normalizer from the RC1
activities-only Golden Path to a bounded multi-family Run-All workflow and a
reproducible analysis handoff. It remains a Release Candidate, does not claim a
stable third-party Python API, and is not published to PyPI.

The Git tag is `v0.1.0-rc.2`; the Python package version is `0.1.0rc2`.

## Included

- Activities-required Run-All with optional Gear, Personal Records, and bounded
  FIT sessions/laps
- Fixed deterministic output layout, QA, provenance manifest, completion
  summary, and explicit partial-success behavior
- Bounded large-archive compatibility with traversal, link, encryption, count,
  size, total-size, and compression-ratio controls retained
- Private public-safe real-export execution evidence without publishing private
  rows, paths, identifiers, counts, or fingerprints
- Analysis Handoff, reusable prompt, public synthetic usage example, three
  key-free Analysis Examples, and a Primary Case Study

## Quick Start

Follow the tag-pinned
[Product Quick Start](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v0.1.0-rc.2/docs/product_quick_start.md).

Run the synthetic Activities Golden Path:

```bash
python -m garmin_running_data_normalizer normalize-activities \
  --input examples/synthetic/garmin_export \
  --output workspace/golden-path
```

Run the minimum multi-family workflow:

```bash
python -m garmin_running_data_normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all
```

## Analysis and case study

- [Analysis Handoff Specification](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v0.1.0-rc.2/docs/project/analysis_handoff_spec_v0_1.md)
- [Public Usage Example](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v0.1.0-rc.2/docs/project/run_all_public_usage_example_v0_1.md)
- [Analysis Example Index](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v0.1.0-rc.2/examples/analysis/README.md)
- [Primary Case Study](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v0.1.0-rc.2/docs/case_studies/from_garmin_export_to_reproducible_analysis_handoff_v0_1.md)

Calculated facts in the synthetic examples are reproducible. Generative wording
is not claimed to be byte-identical.

## Reproducibility and validation

The exact release commit passed:

- 39 standard-library unit tests and 39 pytest tests
- Bootstrap Validation
- Static Policy
- Platform Alignment
- Public History validation
- Synthetic Golden Result comparison and byte-identical repeat execution
- Minimum Run-All and byte-identical repeat execution
- Existing-output rejection with exit code 2
- Public-contract, privacy, documentation-link, and clean-clone review

GitHub Actions run
[`29896162447`](https://github.com/tsubotti63/garmin-running-data-normalizer/actions/runs/29896162447)
completed successfully for commit
`0996c4889ae807be0082ae83a26319a860f62c96`.

## Safety and privacy

Public reproduction uses synthetic fixtures only. Real Garmin exports and
generated output remain local and must not be committed or attached to CI or a
Release.

The Activities CSV has no separate `activity_id` column, but its
`garmin_activity_key` may incorporate a source activity ID. Remove that key
from externally shared derivatives and review date/time granularity before
transfer.

## Known limitations

- Activities are required; optional families use the documented exact filename
  rules.
- FIT support covers selected session/lap fields and does not implement complete
  CRC or invalid-sentinel handling.
- Weather, Sleep, HRV, Parquet, dashboards, notebooks, automatic Analysis Pack
  generation, stable API guarantees, stable release, and PyPI publication are
  absent.
- Analysis examples are descriptive and do not provide medical or coaching
  conclusions.

## License and feedback

The project is available under the
[Apache License 2.0](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v0.1.0-rc.2/LICENSE).

Report reproducible problems through
[GitHub Issues](https://github.com/tsubotti63/garmin-running-data-normalizer/issues).
