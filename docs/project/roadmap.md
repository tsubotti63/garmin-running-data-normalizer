# Roadmap

## Phase 0.1 — current

Platform v0.9 alignment, bounded safe Source reuse, synthetic tests,
deterministic evidence, and Target Project Core Review.

## Milestone 1 — complete the local intake contract

Expand synthetic Garmin export shapes, define public schemas, add streaming
limits, and stabilize the dataset registry.

## Milestone 2 — local orchestration

Add a phase-independent Run-All command, deterministic file outputs, provenance
manifest, and reproducibility checks.

## Milestone 3 — optional adapters and packaging

Review Open-Meteo privacy/use-tier controls and finalize Analysis Pack contracts.

## Milestone 4 — versioned stable release — complete

Rights for the predecessor-derived responsibilities included in `v1.0.0` were
Human-confirmed. Dependency/license, security/privacy, clean-state package,
review, and CI evidence passed. `v1.0.0` remains the first stable release and
its annotated tag remains fixed on the reviewed release commit. Later releases
do not change that historical fact. Every future release and package-index
publication still requires its own current review and Human authorization.

## Post-Stable / v1.1 context

- FIT CRC validation and multi-session FIT identity were completed for v1.1.
- Evaluate Run-All integration for Sleep, HRV, and Health Status without
  silently expanding the stable `1.x` output contract.
- Review hosted processing, Open-Meteo, and Parquet as separately gated
  capabilities.
- PyPI packaging, repository-controlled publish execution, protected
  Environments, Trusted Publisher configuration, and the initial TestPyPI and
  Production PyPI publications were completed through their separate Human
  gates. Future publications remain separately gated.
- Update GitHub Actions dependencies before the Node.js 20 compatibility shim
  is removed from hosted runners.

## v1.2 — Snapshot Accumulation and Canonical Merge Foundation

Implementation adapts the reviewed predecessor Snapshot Store, candidate,
dataset-policy, diff, full-rebuild, and QA contracts to the public package.
The change is additive: the v1.1.1 one-shot Run-All contract remains compatible.
v1.2.1 is the current stable release. v1.2.0 release preparation completed full
synthetic validation, private four-Snapshot validation, clean package-installed
flows, and review evidence; TestPyPI, the annotated tag, GitHub Release, and
Production PyPI were then completed and verified in their gated order.

## P2 — initial package-index publication — historical complete

Version `1.0.1` was the packaging-only patch used for the initial package-index
publication while preserving the stable `1.x` interface and its privacy and
dependency boundaries. Release-state documentation, tag/Release creation,
protected GitHub Environments, approval variables, Trusted Publisher
configuration, TestPyPI, and Production PyPI were completed under their
separate approvals. The resulting tag and package-index artifacts remain
immutable history.

The active product boundaries are listed in `docs/known_limitations.md`.
