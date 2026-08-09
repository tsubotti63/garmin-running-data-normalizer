#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_SOURCE = "src/garmin_running_data_normalizer/__init__.py"
CURRENT_DOCUMENTS = (
    "README.md",
    "docs/architecture_overview.md",
    "docs/dataset_relationships.md",
    "docs/product_quick_start.md",
    "docs/output_contract.md",
    "AGENTS.md",
)


def _package_version(root: Path) -> str:
    path = root / VERSION_SOURCE
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, str):
            return value
    raise ValueError("literal __version__ assignment is missing")


def _contains_whitespace_normalized(text: str, phrase: str) -> bool:
    pattern = r"\s+".join(re.escape(part) for part in phrase.split())
    return re.search(pattern, text) is not None


def validate(root: Path = ROOT) -> tuple[str | None, list[str]]:
    findings: list[str] = []
    contents: dict[str, str] = {}
    for relative in CURRENT_DOCUMENTS:
        path = root / relative
        if not path.is_file():
            findings.append(f"{relative}: required current-state document is missing")
            continue
        contents[relative] = path.read_text(encoding="utf-8")

    try:
        version = _package_version(root)
    except (FileNotFoundError, SyntaxError, ValueError):
        findings.append(f"{VERSION_SOURCE}: package version is missing or invalid")
        version = None

    if version is not None:
        required_version_markers = {
            "README.md": f"Current stable release: **v{version}**",
            "docs/architecture_overview.md": f"- Applies to: stable v{version}",
            "docs/product_quick_start.md": f"currently serve stable v{version}",
            "docs/output_contract.md": f"- Current stable contract: v{version}",
            "AGENTS.md": f"Stable v{version} maintenance and public-surface alignment",
        }
        for relative, marker in required_version_markers.items():
            if not _contains_whitespace_normalized(contents.get(relative, ""), marker):
                findings.append(
                    f"{relative}: current stable marker does not match package v{version}"
                )

    stable_run_all_marker = (
        f"Sleep Daily and HRV Daily are optional stable v{version} Run-All datasets."
        if version is not None
        else "Sleep Daily and HRV Daily are optional stable Run-All datasets."
    )
    required_markers = {
        "README.md": ("17 stable normalized datasets",),
        "docs/architecture_overview.md": (
            "- Compatibility family: stable 1.x",
            "17 stable normalized datasets",
            "Open-Meteo remains not implemented and deferred.",
        ),
        "docs/dataset_relationships.md": (
            "## Stable v1.3 context and observation catalog",
        ),
        "docs/product_quick_start.md": (
            "The root `QUICK_START.md` is a short router to the product guides.",
            stable_run_all_marker,
            "Health Status remains library-level / deferred.",
            "Lactate Threshold remains candidate / audit only.",
        ),
        "docs/output_contract.md": (
            "- Compatibility family: stable 1.x",
            "## Core stable 1.x layout",
            "## Additive v1.1 relationship handoff",
            "## Additive v1.2 Snapshot lifecycle",
            "## Additive v1.3 Wellness / Metrics",
        ),
        "AGENTS.md": (
            "Audience**: AI-assisted development tasks and maintainers",
            "Product contracts own Product behavior.",
            "ACP documents own AI-assisted development governance.",
        ),
    }
    for relative, markers in required_markers.items():
        text = contents.get(relative, "")
        for marker in markers:
            if not _contains_whitespace_normalized(text, marker):
                findings.append(f"{relative}: required marker is missing: {marker}")

    obsolete_phrases = {
        "docs/architecture_overview.md": (
            "Deferred: a final Run-All command",
            "those facts do not imply that a versioned release exists",
        ),
        "docs/dataset_relationships.md": (
            "## Unreleased v1.3 context and observation catalog",
        ),
        "docs/product_quick_start.md": (
            "Library-level `sleepData.json` normalization is implemented separately and does not change the Run-All output contract.",
            "Library-level HRV normalization is also separate",
        ),
        "AGENTS.md": (
            "Phase 0.1 — Platform alignment and safe local reuse",
            "docs/project/phases/phase0_1/reading_order.md",
        ),
    }
    for relative, phrases in obsolete_phrases.items():
        text = contents.get(relative, "")
        for phrase in phrases:
            if _contains_whitespace_normalized(text, phrase):
                findings.append(f"{relative}: obsolete current-state phrase remains: {phrase}")

    return version, findings


def main() -> None:
    version, findings = validate()
    result = {
        "status": "PASS" if not findings else "FAIL",
        "product_version": version,
        "documents_checked": list(CURRENT_DOCUMENTS),
        "findings": findings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if not findings else 1)


if __name__ == "__main__":
    main()
