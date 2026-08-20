# v1.4 Export Evidence and Diagnostics

Status: implementation candidate for local review; not a published stable
release. The current published stable release remains v1.3.3.

## First-user journey

1. Complete the [Synthetic Quick Start](product_quick_start.md) and confirm its
   documented `PASS_WITH_WARNINGS / exit 0` example.
2. Follow [Getting Started from Garmin Export](getting_started_from_garmin_export.md)
   to run a real Export locally.
3. Read the unchanged Product status and exit code using the
   [Run-All Output Contract](output_contract.md). `PARTIAL_SUCCESS / exit 3`
   is completed with bounded exclusions; it is not Fatal.
4. Run Doctor on the completed output, then inspect Source Completeness and
   Run Quality under `diagnostics/`.
5. If support is needed, generate the public-safe Support Bundle below and
   review all six members before sharing it.

## Run-All diagnostic artifacts

Every completed v1.4 Run-All output adds:

```text
diagnostics/source_completeness.json
diagnostics/run_quality.json
```

These are read-only projections of existing Product evidence. They do not
change normalized records, infer missing values, select a winner, or create a
new relationship.

For one-shot Run-All, Source Completeness reports the supplied Export as one
opaque observation. For Snapshot Run-All, it reports every registered Snapshot
independently in authoritative acquisition order (`snapshot-1`, `snapshot-2`,
and so on). A later `ABSENT` observation never deletes an earlier `PRESENT`
observation and is never interpreted as zero.

## Doctor

```bash
garmin-running-data-normalizer doctor --input /path/to/DI_CONNECT
garmin-running-data-normalizer doctor --run-output /path/to/completed-output
```

Use `--format json` for deterministic machine output. Doctor exit code 0 means
the diagnostic report completed; it does not replace the Product Run-All exit
code recorded in that report. Doctor returns 2 only when Doctor itself cannot
validate its authorities, and never returns 3.

## Support Bundle

```bash
garmin-running-data-normalizer support-bundle \
  --run-output /path/to/completed-output \
  --output /path/to/support-bundle.zip
```

The new destination must not already exist. The archive contains exactly six
typed, deterministic members and performs no upload. It excludes raw rows,
paths, filenames, identifiers, exact timestamps, coordinates, private evidence
digests, environment inventory, and free-form exceptions. Review it before
sharing; exact aggregate counts can still reveal usage volume.

The Support Bundle is not the optional Activities-only External-safe Analysis
Pack. Security-sensitive reports belong in GitHub Private Vulnerability
Reporting. Neither artifact provides medical or coaching interpretation.
