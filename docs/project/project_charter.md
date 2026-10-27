# Garmin Running Data Normalizer Charter

## Mission

Normalize Garmin Account Export content locally into documented, deterministic,
privacy-safe records without requiring the private Source Project at runtime.

## Domain principles

- Preserve input provenance while never exposing host paths or personal data.
- Use stable keys, explicit merge semantics, deterministic QA, and fail-closed
  archive handling.
- Keep implemented, planned, blocked, and publication-ready states distinct.

## Non-goals

JMA, Instagram, wellness/coaching interpretation, personal analysis, non-Garmin
generalization, hosted services, and private Source reproduction are excluded.

## Success

A user can provide a local Garmin export and obtain reproducible normalized
records and reviewable QA using documented commands and synthetic-tested code.

## Interfaces

The command-line interface is the stable interface. Since v2.0.0, a local GUI
is a second entry point to the same processing, including Snapshots and ZIP
input: a page served on the loopback address for a browser on the same
machine, not a hosted service. See [v2.0.0 GUI Design](../gui_design.md) and
the [GUI Guide](../gui_guide.md). From v2.1.0, the GUI also has a view page in
the next tab, which shows the numbers of an output that this version made, on
the same machine and without interpreting them; the `series` command of the
CLI writes the same numbers to a CSV file. See
[The view page](../gui_design.md#the-view-page-v210).

## Human-owned decisions

OSS license, Source redistribution rights, publication/GitHub authorization,
remote/push/release, Open-Meteo production tier, and scope changes.
