# Garmin Running Data Normalizer Project Context

## Purpose

Create an independent, privacy-safe OSS candidate that turns an unmodified
Garmin Account Export into deterministic datasets with provenance and QA.

## Current state

Bootstrap governance and local implementation review are complete. Phase 0.1 aligns the repository to
the AI Collaboration Platform v0.9 structure and extracts a bounded local core
from a private Source after mechanical dependency and privacy review.

## Platform adoption

- Platform adoption status: Adopted; 54 Standard files verified byte-for-byte
  against the Human-supplied v0.9 pack
- Project maturity: Local implementation; not publication ready

## Stakeholders and authority

The Human owner controls license, Source redistribution rights, GitHub/public
release, remote/push/release actions, and Open-Meteo production use.

## Assets and constraints

The Target repository is writable. The Platform and Source repositories are
read-only references. Only synthetic fixtures and non-personal aggregate review
evidence may enter version control.

## Project Customization notice

This document is the project-specific source of truth. Platform Standard remains
unmodified under `docs/project_os/`, `docs/proofs/`, `templates/`, and standard
`runtime/` paths. Target product identity and customization remain in root
project files, `docs/project/`, `docs/reference/`, and the Runtime Addendum.
