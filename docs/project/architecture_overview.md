# Architecture Overview

```text
Local Garmin Export (read-only, ignored)
  -> intake.discovery
  -> intake.archive (path and size guards)
  -> JSON / FIT parsers
  -> normalizers
  -> stable identity + relative provenance
  -> dataset policy inspection
  -> deterministic QA
  -> optional allowlist-only Analysis Pack
```

The package is layered as `common`, `intake`, `normalizers`, `fit`, `policies`,
`qa`, and `export`. The core uses only Python's standard library. It never imports
the Source package, performs network calls, or writes outside caller-selected
output paths.

Open-Meteo is a future isolated adapter because coordinate handling, attribution,
retention, and production use tier require additional controls and Human input.
