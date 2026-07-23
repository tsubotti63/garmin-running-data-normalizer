# Synthetic FIT Fixture Foundation

The FIT tests generate their binary fixtures at runtime with
`tests/fit_fixture_factory.py`. No Garmin export, device file, user identifier,
coordinate, or private source artifact is used.

The generator covers:

- a valid single-session file;
- a valid multi-session file;
- 12-byte and 14-byte headers;
- valid header and file CRC values;
- invalid header CRC;
- invalid file CRC;
- truncation;
- unsupported chained content; and
- invalid metric sentinels.

Expected session, lap, audit, identity, and CRC outcomes are asserted in
`tests/test_fit_and_analysis_pack.py`. The byte generator uses the public FIT
CRC algorithm and visibly synthetic timestamps and measurements. Fixtures are
created only in temporary test directories and are not distributed as user
data samples.
