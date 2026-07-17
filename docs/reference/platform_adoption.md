# AI Collaboration Platform v0.9 Adoption

The Human-supplied `ai-collaboration-platform.zip` is the structural reference.
The Target adopts the Standard layer at the Platform-defined locations:

- `docs/project_os/`
- `docs/proofs/`
- `templates/`
- standard `runtime/agents/`, `runtime/packages/`, and `runtime/work/`
- `examples/generic_reference_project/`
- `QUICK_START.md`, `PLATFORM_EVOLUTION.md`, and `CHANGELOG.md`

The adopted 54 Standard files match the supplied ZIP byte-for-byte. Their
root-relative paths, bytes, SHA-256 values, and source ZIP SHA-256 are recorded
in `platform_standard_adoption_v0_9.json`.

Project Customization remains separate in root `README.md`/`AGENTS.md`,
`docs/project/`, `docs/reference/`, `runtime/project_runtime_addendum.md`, product
code, configuration, schemas, tests, and scripts.

Platform repository identity files (`platform_manifest_v0_9.json`,
`platform_inventory_v0_9.csv`, and `platform_qa_v0_9.json`) are intentionally
not copied. The Target is a Platform-adopting product, not the Platform itself.
No Platform Git history, `.DS_Store`, or `__MACOSX` content is admitted.
