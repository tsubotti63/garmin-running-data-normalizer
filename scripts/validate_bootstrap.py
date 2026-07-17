#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "AGENTS.md",
    "docs/project_charter.md",
    "docs/project_boundary.md",
    "docs/roadmap.md",
    "docs/architecture_overview.md",
    "docs/existing_asset_reuse_matrix.md",
    "docs/migration_notes.md",
    "docs/github_public_readiness_checklist.md",
    "runtime/implementation_task_initial_prompt.md",
    "runtime/project_core_review_initial_prompt.md",
)


def main() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    forbidden = [path for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in {".fit", ".parquet", ".zip"}]
    result = {
        "status": "PASS" if not missing and not forbidden else "FAIL",
        "bootstrap_only": True,
        "missing": missing,
        "forbidden_binary_paths": [path.relative_to(ROOT).as_posix() for path in forbidden],
        "license_selected": False,
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

