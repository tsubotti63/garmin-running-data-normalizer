#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", "AGENTS.md", "docs/README.md",
    "docs/project/project_context.md", "docs/project/project_charter.md",
    "docs/project/project_governance.md", "docs/project/project_boundary.md",
    "docs/project/project_requirements.md", "docs/project/definition_of_done.md",
    "docs/project/architecture_overview.md", "docs/project/roadmap.md",
    "docs/project/phases/phase0_1/kickoff.md",
    "docs/project/phases/phase0_1/reading_order.md",
    "docs/project/phases/phase0_1/intake_gate.md",
    "docs/reference/reuse_matrix.md", "docs/reference/platform_adoption.md",
    "docs/reference/platform_standard_adoption_v0_9.json",
    "docs/project_os/governance/platform_charter_v0_9.md",
    "docs/project_os/architecture/ai_collaboration_architecture_v0_9.md",
    "docs/project_os/operation/project_core_gate_protocol_v0_9.md",
    "docs/proofs/task_collaboration_poc_v0_9.md", "templates/README.md",
    "QUICK_START.md", "PLATFORM_EVOLUTION.md", "CHANGELOG.md", "runtime/README.md",
    "runtime/project_runtime_addendum.md", "runtime/work/task_creation/README.md",
    "runtime/work/implementation/README.md", "runtime/work/review/README.md",
    "runtime/agents/README.md", "runtime/packages/README.md", "packages/README.md",
    "config/dataset_registry.example.json", "schemas/dataset_registry.schema.json",
)
RESPONSIBILITY_DIRS = (
    "docs", "docs/reference", "runtime", "runtime/work", "runtime/work/task_creation",
    "runtime/work/implementation", "runtime/work/review", "runtime/agents",
    "runtime/packages", "packages", "docs/project_os", "docs/proofs", "templates",
)


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    empty_responsibilities = [name for name in RESPONSIBILITY_DIRS if not any((ROOT / name).iterdir())]
    forbidden = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and path.suffix.lower() in {".fit", ".parquet"}
    ]
    placeholders = []
    for name in REQUIRED_FILES:
        path = ROOT / name
        if path.is_file() and "<PROJECT_" in path.read_text(encoding="utf-8", errors="ignore"):
            placeholders.append(name)
    result = {
        "status": "PASS" if not missing and not empty_responsibilities and not forbidden and not placeholders else "FAIL",
        "implementation_status": "LOCAL_IMPLEMENTATION_NOT_PUBLICATION_READY",
        "missing": missing,
        "empty_responsibility_directories": empty_responsibilities,
        "forbidden_binary_paths": forbidden,
        "unresolved_template_placeholders": placeholders,
        "license_selected": (ROOT / "LICENSE").is_file(),
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" and not result["license_selected"] else 1)


if __name__ == "__main__":
    main()
