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
review, and CI evidence passed. `v1.0.0` is published as the first stable and
latest GitHub Release. Its annotated tag remains fixed on the reviewed release
commit. Future releases and package-index publication still require their own
current review and Human authorization.

## Post-Stable / v1.1 entry points

- Complete FIT CRC validation and multi-session FIT identity.
- Evaluate Run-All integration for Sleep, HRV, and Health Status without
  silently expanding the stable `1.x` output contract.
- Review hosted processing, Open-Meteo, and Parquet as separately gated
  capabilities. PyPI packaging and repository-controlled publish execution
  readiness are complete; the first version/source, TestPyPI policy, external
  publisher configuration, tag/Release, and each initial upload remain
  separately Human-gated.
- Update GitHub Actions dependencies before the Node.js 20 compatibility shim
  is removed from hosted runners.

## P2 — initial package-index publication

Prepare `1.0.1` as a packaging-only patch from post-P1 `main`, preserving the
stable `1.x` interface and all current privacy and dependency boundaries. After
the candidate passes Target review and CI, stop for explicit Human approval
before tag/Release creation, external Trusted Publishing configuration,
TestPyPI upload, and production PyPI upload.

The active product boundaries are listed in `docs/known_limitations.md`.
