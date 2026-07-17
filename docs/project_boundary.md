# Project Boundary

## In scope

- Garmin Account Export intake without rename or preprocessing.
- Dataset auto-detection and registry.
- Garmin JSON and FIT normalization.
- Stable keys, merge policy, provenance, deterministic QA.
- A single future Run-All command.
- Optional Open-Meteo integration with explicit attribution and API-use policy.
- Portable Analysis Pack ZIP containing only user-authorized generated output.
- Schema, configuration examples, tests, CI, runbook, and synthetic fixtures.

## Out of scope

- Real Garmin exports or generated personal outputs.
- JMA data or JMA-specific implementation.
- Instagram, coaching, personal wellness interpretation, sleep/HRV advice, or
  private analysis.
- Generalization to non-Garmin sources.
- Private runtime/governance documents and private Git history.
- GitHub creation, remote configuration, push, release, or license selection in
  this bootstrap.

## Prohibited public content

Credentials, tokens, cookies, email addresses, account IDs, real activity IDs,
precise coordinates, raw data, personal health data, host absolute paths, and
reversible private-history artifacts.

## Change control

Changes to scope, data semantics, source-of-truth policy, privacy boundary, or
license require Human approval. Boundary-local implementation and review fixes
may proceed autonomously.
