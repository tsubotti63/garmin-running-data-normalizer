# Migration, Sanitization, and Rollback Method

1. Keep the private predecessor and Platform source read-only.
2. Inspect candidate imports, dependencies, tests, paths, and data assumptions.
3. Select one Garmin-only responsibility and its smallest safe dependency set.
4. Rework it into the Target namespace using standard-library contracts.
5. Remove private workflow state, paths, environment evidence, identifiers,
   coordinates, JMA, and non-Garmin behavior.
6. Recreate behavior tests with visibly synthetic data.
7. Run tests, Platform validation, static scans, and full public-history scans;
   freeze Git-ignored evidence and obtain Target Project Core Review.

The public history was reconstructed as a fresh two-commit object database after
explicit Human authorization. Exact predecessor names, task references, private
paths, old public-candidate hashes, and operational handoff evidence were
removed or generalized without changing product implementation bytes.

Rollback uses external full-repository copies, complete reachable-history
bundles, byte/SHA manifests, and old/new commit mapping. These artifacts remain
outside the public Target path and must never be pushed. Future development uses
normal reviewed commits; another history reconstruction requires new explicit
Human authority and a fresh rollback artifact.
