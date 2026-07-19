#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
APPROVED_LICENSES = {
    "APACHE_2_0": "c72bf424aba4feebd7352bd33966434a58bcadc47fce0e07bb75006e51b0909e",
}
LICENSE_STATE_BY_LIFECYCLE = {
    "pre-public": "UNSELECTED",
    "post-public": "APACHE_2_0",
}


def license_state() -> str:
    license_path = ROOT / "LICENSE"
    if not license_path.is_file():
        return "UNSELECTED"
    digest = hashlib.sha256(license_path.read_bytes()).hexdigest()
    return next(
        (name for name, approved_digest in APPROVED_LICENSES.items() if digest == approved_digest),
        "UNAPPROVED",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lifecycle-state",
        choices=tuple(LICENSE_STATE_BY_LIFECYCLE),
        default="post-public",
    )
    args = parser.parse_args()
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
    current_license_state = license_state()
    required_license_state = LICENSE_STATE_BY_LIFECYCLE[args.lifecycle_state]
    invalid_license = current_license_state != required_license_state
    result = {
        "status": (
            "PASS"
            if not missing and not empty_responsibilities and not forbidden and not placeholders and not invalid_license
            else "FAIL"
        ),
        "implementation_status": "LOCAL_IMPLEMENTATION_NOT_PUBLICATION_READY",
        "missing": missing,
        "empty_responsibility_directories": empty_responsibilities,
        "forbidden_binary_paths": forbidden,
        "unresolved_template_placeholders": placeholders,
        "lifecycle_state": args.lifecycle_state,
        "required_license_state": required_license_state,
        "license_state": current_license_state,
        "license_selected": current_license_state != "UNSELECTED",
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
