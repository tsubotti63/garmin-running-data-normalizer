# Privacy and Security Reference

- Input is local and read-only; output destinations are caller-selected.
- ZIP paths must be relative, traversal-free, and within configured count/size
  limits before content is read.
- Provenance uses source-relative names and SHA-256, never host absolute paths.
- Synthetic fixtures use unmistakably fictitious identifiers and no coordinates.
- Analysis Packs include only explicit allowlisted files below an approved root.
- Network access and Open-Meteo are absent from the Phase 0.1 implementation.

Real exports, generated personal records, coordinates, emails, credentials, and
health interpretation must never be committed.
