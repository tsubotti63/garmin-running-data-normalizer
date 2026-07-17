# Project Charter

## Identity

- Work Project: `GARMINデータ正規化`
- Product / OSS: `Garmin Running Data Normalizer`
- Repository: `garmin-running-data-normalizer`

## Purpose

Build an independent, privacy-safe OSS tool that discovers datasets in an
unmodified Garmin Account Export, normalizes them deterministically, preserves
provenance, validates outputs, and can create a portable Analysis Pack.

## Bootstrap objective

This initial repository establishes governance, architecture, extraction
boundaries, synthetic examples, and review/implementation task contracts. It
does not deliver the product implementation.

## Success principles

- One Garmin-focused public scope.
- No dependency on the private Source Project at runtime.
- No real user data, identifiers, coordinates, health analysis, or private Git
  history.
- Deterministic behavior and fail-closed QA.
- Accurate documentation that separates implemented, planned, and blocked work.

## Human authority

The Human owner retains authority over OSS license selection, publication,
GitHub repository creation, remote/push, release, and any expansion beyond the
Garmin-focused boundary.

