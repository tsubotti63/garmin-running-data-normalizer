# Synthetic Snapshot Store Written by v1.7.1

`store_files.json` holds the folders and files of a Snapshot Store exactly as
version 1.7.1 wrote them, with the modes that it set: text files as text and
other files in Base64. `tests/test_snapshot_store_v1_7_1.py` writes the store
from it and checks that the current version loads and verifies it without
migration, uses every Snapshot in it, and registers a new Snapshot into it, as
[v2.0.0 Data Handling](../../../docs/v2_data_handling.md#snapshot-stores)
requires of every stage A pull request.

The store holds two Snapshots of synthetic Exports in the layout of a real
Export:

- Activities, one of which only the first Snapshot contains, one of which only
  the second contains, and one whose name changes between them;
- a Gear record with its Activity links, and a Personal Record;
- a FIT file inside a ZIP file inside the Export;
- Hill Score and Sleep records for days that both Snapshots contain and for a
  day that only the second contains; and
- a file that the product does not read.

`make_store.py` wrote it with garmin-running-data-normalizer 1.7.1 installed
from PyPI. The store records fixed times, so that version writes the same bytes
each time. The fixture is not regenerated with a later version: its purpose is
to keep what version 1.7.1 wrote. No Garmin Export, device file, user
identifier, coordinate, or private source artifact is used.
