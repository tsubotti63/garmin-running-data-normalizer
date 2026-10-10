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

The command-line interface is the stable interface. A local GUI is planned for
v2.0.0 as a second entry point to the same processing: a page served on the
loopback address for a browser on the same machine, not a hosted service. See
[v2.0.0 GUI Design](../gui_design.md).

## Human-owned decisions

OSS license, Source redistribution rights, publication/GitHub authorization,
remote/push/release, Open-Meteo production tier, and scope changes.
