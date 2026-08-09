# AI Collaboration Platform v0.9 Adoption

The Human-supplied `ai-collaboration-platform.zip` is the structural reference.
The Target adopts the Standard layer at the Platform-defined locations:

- `docs/project_os/`
- `docs/proofs/`
- `templates/`
- standard `runtime/agents/`, `runtime/packages/`, and `runtime/work/`
- `examples/generic_reference_project/`
- `PLATFORM_EVOLUTION.md`

The adoption record preserves all 62 original Standard baseline entries from
the supplied ZIP, including their root-relative paths, bytes, SHA-256 values,
and the source ZIP SHA-256. Of those entries, 59 remain byte-locked Platform
Standard files.

By explicit Human decision, `QUICK_START.md`, `CHANGELOG.md`, and
`docs/README.md` are Product-owned public entry points. Their original ACP v0.9
bytes and hashes remain in `platform_standard_adoption_v0_9.json` as historical
adoption evidence, while the current files route readers to Garmin product
documentation. The Platform Alignment Validator recognizes only this exact
three-path override and fails closed on any unapproved addition or altered
baseline evidence.

Project Customization remains separate in root `README.md`, `AGENTS.md`,
`QUICK_START.md`, and `CHANGELOG.md`; `docs/README.md`; `docs/project/`;
`docs/reference/`; `runtime/project_runtime_addendum.md`; and product code,
configuration, schemas, tests, and scripts.

Platform repository identity files (`platform_manifest_v0_9.json`,
`platform_inventory_v0_9.csv`, and `platform_qa_v0_9.json`) are intentionally
not copied. The Target is a Platform-adopting product, not the Platform itself.
No Platform Git history, `.DS_Store`, or `__MACOSX` content is admitted.
