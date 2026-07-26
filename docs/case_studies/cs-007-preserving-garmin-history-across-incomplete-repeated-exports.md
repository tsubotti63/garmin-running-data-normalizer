# Preserving Garmin History Across Incomplete Repeated Exports

Garmin Running Data Normalizer v1.2.0 introduces snapshot accumulation for
people who receive more than one Garmin Account Data Export over time.

## The Problem

A later Garmin Account Data Export can omit records that appeared earlier.
Treating the newest export as a complete replacement can therefore remove
previously observed history without evidence that Garmin deleted it.

## The Product Contract

v1.2.0 preserves immutable observations and rebuilds a canonical cumulative
view in which absence alone is not treated as deletion.

The workflow:

1. registers each accepted export as an immutable observation;
2. keeps record provenance through candidate construction;
3. applies dataset-aware merge policy;
4. distinguishes seven materially different value states;
5. rebuilds a deterministic canonical view;
6. emits QA and recovery evidence.

The seven states are absent, null, empty, malformed, unsupported, retained, and
promoted. Keeping them distinct prevents a generic missing-value shortcut from
silently deleting or inventing data.

## How It Was Validated

The release was privately validated with four repeated complete exports from
the same Garmin account. They are repeated observations, not four independent
datasets.

Within that reviewed set and policy:

- all 6 pairwise snapshot comparisons passed;
- all 24 tested registration-order permutations passed;
- all 13 failure and recovery scenarios passed;
- incremental rebuild matched full rebuild;
- deterministic cumulative rebuild passed;
- source mutation was 0;
- public/private exposure findings were 0.

The release source also passed 124/124 `unittest` checks, 142/142 `pytest`
checks, GitHub Actions, and release-candidate review.

## Release Outcome

v1.2.0 was published as a GitHub Release and as clean-install-verified packages
on TestPyPI and Production PyPI. The publication path used manual dispatch,
exact source identity, approval gates, protected Environments, and OIDC Trusted
Publishing. The post-publication audit found no active gate bypass.

## Why It Matters

Snapshot accumulation changes the unit of trust from “the latest file” to
“reviewed observations plus explicit merge policy.” Users retain a cumulative,
auditable history while the tool remains conservative about what an omission
means.

## Boundaries

The evidence applies to one account, four repeated exports, the reviewed merge
policy, and the v1.2.0 release scope. It does not claim:

- validation across four independent datasets;
- recovery of every possible omission;
- automatic deletion;
- universal order independence;
- zero defects or zero future failures;
- statistical generalization;
- external adoption.

Private source details and rows were not included in this case study.

Public product behavior can be explored using the repository's synthetic
fixtures. The four-export results reported here are reviewed private aggregate
evidence.

## Evidence Identity

- Case Study: `CS-007`
- Claims: `CLM-017`–`CLM-025`
- Achievements: `ACH-013`–`ACH-016`

The reported results apply to one account, four repeated exports, the reviewed
merge policy, and the v1.2.0 release scope. Publication of this page does not
authorize a future product release.

## Related Documentation

- [Garmin Running Data Normalizer](../../README.md)
- [Product Quick Start](../product_quick_start.md)
- [v1.2 Snapshot Accumulation Migration Guide](../project/v1_2_snapshot_migration_guide_v1_0.md)
- [Known Limitations](../known_limitations.md)
- [Product Change History](../product_changelog.md)
- [v1.2.0 GitHub Release](https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.2.0)

External publication still requires separate Human approval.
