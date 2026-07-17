# Sample Data Policy

Only wholly synthetic data may be committed during bootstrap and initial
implementation. Anonymized real exports are not accepted because route,
timestamp, health, identifier, filename, and free-text combinations can remain
re-identifiable.

Synthetic fixtures must:

- use visibly fictional identifiers;
- avoid real coordinates, emails, and account/activity IDs;
- avoid copying unique sequences from a real person;
- carry `synthetic: true` where the format permits;
- document generation logic and expected results;
- pass privacy and secret scans before commit.
