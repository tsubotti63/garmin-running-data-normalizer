# Run-All Public Usage Example v0.1

This example uses only the repository's visibly synthetic Garmin fixture. It
does not contain or describe a real person's export.

## 1. Prepare a local environment

```bash
git clone https://github.com/tsubotti63/garmin-running-data-normalizer.git
cd garmin-running-data-normalizer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The input fixture is already available at
`examples/synthetic/garmin_export`. Use a new output directory; Run-All never
overwrites an existing destination.

## 2. Run the workflow

```bash
python -m garmin_running_data_normalizer run-all \
  --input examples/synthetic/garmin_export \
  --output workspace/run-all-example
```

The tracked fixture contains Activities only. A successful example therefore
reports `PASS_WITH_WARNINGS` with exit code `0` and records the absent optional
families rather than inventing records for them.

## 3. Inspect the fixed output layout

```text
workspace/run-all-example/
  normalized/
    activities.json
    gear.json
    activity_gear.json
    personal_records.json
    fit_sessions.json
    fit_laps.json
  audit/fit_audit.json
  analysis/activities.csv
  qa/dataset_summary.json
  run_manifest.json
  run_summary.json
```

`run_summary.json` is written last and is the completion marker. Do not treat a
directory without that file as a valid completed handoff.

## 4. Review `activities.csv`

The CSV is the reduced, activity-grain table intended for descriptive analysis.
It has no separate `activity_id` column and excludes memo text, paths, hashes,
and coordinates. Its `garmin_activity_key` can contain the source activity ID,
so that column remains private and must be removed from any externally shared
derivative.

Print the header and synthetic rows with the standard library:

```bash
python - <<'PY'
import csv
from pathlib import Path

path = Path("workspace/run-all-example/analysis/activities.csv")
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
print("columns:", list(rows[0]) if rows else [])
print("row_count:", len(rows))
for row in rows:
    print(row["activity_date_local"], row["activity_type"], row["distance_m"])
PY
```

For real local output, avoid printing rows into shared terminals or logs.

## 5. Review `run_summary.json`

Check completion and warnings before analyzing any metric:

```bash
python - <<'PY'
import json
from pathlib import Path

summary = json.loads(
    Path("workspace/run-all-example/run_summary.json").read_text(encoding="utf-8")
)
print("status:", summary["status"])
print("warning_count:", summary["warning_count"])
for family, result in summary["family_results"].items():
    print(family, result["status"])
PY
```

- `PASS` means every detected family completed without warnings.
- `PASS_WITH_WARNINGS` is valid output with non-fatal warnings that must be
  disclosed.
- `PARTIAL_SUCCESS` means Activities are valid but detected FIT processing is
  incomplete; FIT-derived analysis must be labeled partial.
- Exit code `2` is fatal and does not produce a valid final output.

## 6. Understand `run_manifest.json`

The manifest records dataset grains, stable keys, source counts, record counts,
output hashes, and a deterministic output digest. It supports local provenance
and rerun verification. Because it includes source-relative provenance and
hashes, it is verification evidence, not a default file to share externally.

## 7. Read warnings and audit evidence

Start with `run_summary.json`. For FIT-specific warnings, inspect
`audit/fit_audit.json` locally and distinguish successfully parsed, incomplete,
and non-activity files. Never silently discard an incomplete detected family.
The tracked Activities-only example has no FIT records and records that absence
as an optional-family warning.

## 8. Prepare an analysis handoff

For a trusted local analysis tool, the minimum normal set is:

- `analysis/activities.csv`
- `run_summary.json`

Keep `run_manifest.json` locally for verification. Add a normalized or audit
file only if the question cannot be answered from the minimum set. For an
external AI service, do not upload real output without explicit data-owner
approval and a provider-specific privacy review. Prefer synthetic data or a
reviewed aggregate. A reviewed row-level derivative must at minimum drop
`garmin_activity_key` and assess whether date/time granularity is needed.

Use [`analysis_prompt_template_v0_1.md`](analysis_prompt_template_v0_1.md) and
the rules in
[`analysis_handoff_spec_v0_1.md`](analysis_handoff_spec_v0_1.md).

## 9. Example analyses

With the synthetic CSV, a consumer can calculate:

- activity count by month or activity type;
- total distance and duration by month;
- coverage and descriptive ranges for heart rate, power, cadence, or training
  load when those fields are present;
- candidate outliers for human review;
- whether a repeated Run-All execution produced byte-identical output.

These are descriptive calculations. The output does not establish training
intent, health status, causality, or coaching advice.

## Privacy notes

- Never commit a real Garmin export or generated personal output.
- Stable keys are private local join values and may incorporate source IDs;
  they must not appear in public examples.
- Normalized JSON, manifest, and audit files can contain source-relative paths,
  hashes, and record-level personal data.
- Keep real output local, use the smallest necessary file set, and publish only
  synthetic or separately reviewed anonymous results.

## Current limitations

- Activities are required; Gear, Personal Records, and FIT are optional.
- FIT parsing is bounded to selected session and lap fields and does not provide
  complete FIT CRC or invalid-sentinel handling.
- Units and semantics not defined by the output contract must not be inferred.
- Weather, Sleep, HRV, Parquet, dashboards, notebooks, and automatic Analysis
  Pack generation are not part of Run-All v1.
- The package does not promise a stable third-party Python API.
