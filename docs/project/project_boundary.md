# Garmin Running Data Normalizer Boundary

## Autonomous scope

- Garmin export discovery and read-only intake.
- Safe ZIP member filtering and bounded reads.
- Garmin JSON/FIT normalization using synthetic tests.
- Stable keys, provenance, dataset policy, deterministic QA, and allowlist-only
  local Analysis Pack generation.
- The planned v2.0.0 local GUI described in
  [v2.0.0 GUI Design](../gui_design.md): a page served by the installed package
  on the loopback address for a browser on the same machine, running the same
  processing as the CLI.
- Project documentation, runtime assets, tests, sanitization QA, and Git-ignored
  review evidence.

## Prohibited without Human decision

- License selection or public redistribution of predecessor-derived work.
- GitHub creation, remote configuration, push, tag, release, publishing, or
  public/commercial Open-Meteo deployment.
- Scope, semantic source-of-truth, privacy boundary, or DoD changes.

## Prohibited content

Raw/generated personal data, coordinates, emails, account/activity identifiers,
credentials, host absolute paths, JMA, Instagram, wellness/coaching/personal
analysis, private evidence, private workflow identifiers, and predecessor Git
history.

## External systems

The implementation performs no outbound network access. The planned v2.0.0 GUI
listens only on the loopback address `127.0.0.1` so that a browser on the same
machine can reach it; it sends nothing to other hosts and loads no external
resources. Open-Meteo is deferred.

## Rollback

Pre-sanitization repositories and complete reachable-history bundles are kept
outside the public Target path with byte/SHA manifests. The sanitized repository
records old/new commit mapping in Git-ignored review evidence. A rollback is a
verified directory-level restoration from that external evidence; rollback
artifacts must never be added to a public remote.
