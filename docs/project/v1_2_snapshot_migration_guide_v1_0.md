# v1.2 Snapshot Accumulation Migration Guide

Status: Draft for the v1.2 release candidate
Compatibility baseline: v1.1.1

## Compatibility promise

The existing one-shot `run-all` command remains supported and keeps its v1.1.1
input and output contract. Snapshot accumulation is an additive lifecycle for
users who want multiple complete Garmin Account Export deliveries to contribute
to one canonical Run-All input.

No migration is required for one-shot users.

## When to adopt Snapshot Accumulation

Adopt the Snapshot lifecycle when all of the following are true:

- each input is a complete Garmin Account Export delivery;
- the deliveries belong to one account boundary;
- export request, download, and observation timestamps are known;
- the raw deliveries can remain private, immutable local evidence; and
- the operator accepts that missing from a later delivery is not deletion.

Do not combine exports from different accounts in one Store.

## Migration procedure

1. Back up the raw exports and choose a private Store location outside every
   export directory.
2. Create one opaque account token. It must not be an email address, Garmin
   identifier, or other personal identifier.
3. Initialize the Store:

   ```text
   garmin-normalizer snapshot init --store PRIVATE_STORE --account OPAQUE_ACCOUNT
   ```

4. Register each complete delivery with an operator label and timezone-aware
   lifecycle timestamps:

   ```text
   garmin-normalizer snapshot register \
     --store PRIVATE_STORE \
     --input PRIVATE_EXPORT \
     --label S1 \
     --requested-at 2030-01-01T00:00:00+09:00 \
     --downloaded-at 2030-01-01T01:00:00+09:00 \
     --observed-at 2030-01-01T01:00:00+09:00 \
     --confirm-complete
   ```

5. Verify the Store before every canonical build:

   ```text
   garmin-normalizer snapshot verify --store PRIVATE_STORE
   ```

6. Inspect a canonical input when needed:

   ```text
   garmin-normalizer snapshot build-input \
     --store PRIVATE_STORE \
     --output PRIVATE_CANONICAL_BUILD
   ```

7. Run the existing normalizer over the accumulated evidence:

   ```text
   garmin-normalizer snapshot run-all \
     --store PRIVATE_STORE \
     --output PRIVATE_OUTPUT
   ```

## Operational differences from one-shot Run-All

- Registration order does not define logical order; `observed-at` does.
- Missing records and fields never trigger automatic deletion.
- Explicit null or empty values do not silently erase a prior explicit value;
  they create review holds.
- Unknown or unsupported objects remain preserved evidence and are not promoted
  into a canonical dataset.
- FIT blobs are accumulated by content and reparsed with the current installed
  parser. Activity/FIT relationships are regenerated from the accumulated
  evidence.
- Store paths, account tokens, source paths, raw rows, and content hashes are
  private local artifacts and must not be copied into public review evidence.

## Rollback and recovery

Snapshot accumulation never edits the raw export directories. Keep an external
backup of the Store before upgrades. A failed registration is reconciled from
the Store journal on the next write, and `snapshot verify` must pass before the
Store is used.

There is no automatic delete or garbage collection in v1.2. To stop using the
Snapshot lifecycle, retain the Store as evidence and return to the unchanged
one-shot `run-all` command. Do not manually edit Store manifests, inventories,
or content-addressed blobs.

## Output review

The cumulative output adds `snapshot/` lineage, coverage, and merge-summary
artifacts. Start with `START_HERE.md`, then review the Snapshot Accumulation
section and the referenced machine-readable evidence before analysis.
