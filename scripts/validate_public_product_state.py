#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_SOURCE = "src/garmin_running_data_normalizer/__init__.py"
CS010_DOCUMENT = (
    "docs/case_studies/"
    "cs-010-from-real-data-edge-cases-to-evidence-preserving-snapshot-semantics.md"
)
CURRENT_DOCUMENTS = (
    "README.md",
    "SUPPORT.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    "docs/architecture_overview.md",
    "docs/dataset_relationships.md",
    "docs/faq.md",
    "docs/getting_started_from_garmin_export.md",
    "docs/product_quick_start.md",
    "docs/output_contract.md",
    "AGENTS.md",
    CS010_DOCUMENT,
)
CURRENT_RELEASE_NOTES_TEMPLATE = "docs/release_notes/v{version}.md"

STATUS_EXIT_CONTRACT_MARKERS = (
    "| `PASS` | 0 |",
    "| `PASS_WITH_WARNINGS` | 0 |",
    "| `PARTIAL_SUCCESS` | 3 |",
    "| Fatal error | 2 |",
)

STATUS_EXIT_CONTRACT = (
    ("PASS_WITH_WARNINGS", 0),
    ("PARTIAL_SUCCESS", 3),
    ("Fatal error", 2),
    ("PASS", 0),
)

STATUS_EXIT_SEPARATOR = (
    r"(?:/|,|→|->|:|=|\bwith\b|\band\b|\breturns?\b|\bfor\b|\bwhen\b|\bmeans\b)"
)
EXIT_LABEL = r"(?:exit(?:\s+code)?|process\s+return(?:\s+code)?)"

CS010_STALE_PUBLIC_STATUS_PHRASES = (
    "This draft is a candidate for Product review",
    "presence on a review branch does not authorize merge",
    "draft is a candidate for Product review",
    "review branch does not authorize merge",
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


def current_documents(version: str | None) -> tuple[str, ...]:
    if version is None:
        return CURRENT_DOCUMENTS
    release_notes = CURRENT_RELEASE_NOTES_TEMPLATE.format(version=version)
    return (*CURRENT_DOCUMENTS, release_notes)


def _status_exit_contradictions(text: str) -> list[tuple[str, int, int]]:
    contradictions: list[tuple[str, int, int]] = []
    for status, expected_exit in STATUS_EXIT_CONTRACT:
        status_pattern = re.escape(status).replace(r"\ ", r"\s+")
        patterns = (
            re.compile(
                rf"`?{status_pattern}`?\s*{STATUS_EXIT_SEPARATOR}\s*"
                rf"(?:an?\s+)?{EXIT_LABEL}\s*`?([0-9]+)`?\b",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{EXIT_LABEL}\s*`?([0-9]+)`?\s*{STATUS_EXIT_SEPARATOR}\s*"
                rf"`?{status_pattern}`?\b",
                re.IGNORECASE,
            ),
        )
        for pattern in patterns:
            for match in pattern.finditer(text):
                observed_exit = int(match.group(1))
                if observed_exit != expected_exit:
                    contradictions.append((status, expected_exit, observed_exit))
    return contradictions


def _issue_form_field_block(text: str, field_id: str) -> str | None:
    lines = text.splitlines()
    id_line = f"id: {field_id}"
    try:
        id_index = next(
            index for index, line in enumerate(lines) if line.strip() == id_line
        )
    except StopIteration:
        return None

    start = id_index
    while start >= 0 and not lines[start].startswith("  - type:"):
        start -= 1
    if start < 0:
        return None

    end = id_index + 1
    while end < len(lines) and not lines[end].startswith("  - type:"):
        end += 1
    return "\n".join(lines[start:end])


def _has_fixed_version_placeholder(field_block: str) -> bool:
    fixed_version = re.compile(
        r"v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?"
    )
    for line in field_block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("placeholder:"):
            continue
        value = stripped.split(":", 1)[1].strip().strip("\"'").strip()
        return fixed_version.search(value) is not None
    return False


def validate(root: Path = ROOT) -> tuple[str | None, list[str]]:
    findings: list[str] = []
    try:
        version = _package_version(root)
    except (FileNotFoundError, SyntaxError, ValueError):
        findings.append(f"{VERSION_SOURCE}: package version is missing or invalid")
        version = None

    documents = current_documents(version)
    contents: dict[str, str] = {}
    for relative in documents:
        path = root / relative
        if not path.is_file():
            findings.append(f"{relative}: required current-state document is missing")
            continue
        contents[relative] = path.read_text(encoding="utf-8")

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
        "SUPPORT.md": (
            "## Current Windows status",
            "Windows is an intended supported platform.",
            "Current evidence includes `windows-latest` packaged-runtime CI and one maintainer-owned physical Windows validation.",
            "does not establish universal compatibility.",
            "## Historical v1.2.0 timezone issue",
            "docs/faq.md#was-the-v120-windows-timezone-data-issue-resolved",
        ),
        ".github/ISSUE_TEMPLATE/bug_report.yml": (
            "Do not upload files or paste real Garmin data.",
            "account identifiers, stable keys, source filenames, private paths, hashes, and personal metrics",
            "This report does not publicly disclose a suspected vulnerability or sensitive security detail.",
        ),
        "docs/architecture_overview.md": (
            "- Compatibility family: stable 1.x",
            "17 stable normalized datasets",
            "Open-Meteo remains not implemented and deferred.",
        ),
        "docs/dataset_relationships.md": (
            "## Stable v1.3 context and observation catalog",
        ),
        "docs/faq.md": (
            "### Was the v1.2.0 Windows timezone-data issue resolved?",
            "| `0` | `PASS` or `PASS_WITH_WARNINGS` |",
            "| `2` | Fatal contract, input, QA, or publication error |",
            "| `3` | `PARTIAL_SUCCESS` because detected FIT is auditably incomplete |",
        ),
        "docs/getting_started_from_garmin_export.md": (
            "| `0` | `PASS` or `PASS_WITH_WARNINGS` |",
            "| `2` | Fatal contract, input, QA, or publication error; no completed output |",
            "| `3` | `PARTIAL_SUCCESS`; Activities are valid and detected FIT is auditably incomplete |",
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
            *STATUS_EXIT_CONTRACT_MARKERS,
            "`product_status`",
            "`product_exit_code`",
            "`harness_exit_code`",
        ),
        "AGENTS.md": (
            "Audience**: AI-assisted development tasks and maintainers",
            "Product contracts own Product behavior.",
            "ACP documents own AI-assisted development governance.",
        ),
    }
    if version is not None:
        release_notes = CURRENT_RELEASE_NOTES_TEMPLATE.format(version=version)
        required_markers[release_notes] = (
            f"# Garmin Running Data Normalizer v{version}",
            "`PARTIAL_SUCCESS` / exit 3",
        )
    for relative, markers in required_markers.items():
        text = contents.get(relative, "")
        for marker in markers:
            if not _contains_whitespace_normalized(text, marker):
                findings.append(f"{relative}: required marker is missing: {marker}")

    for relative, text in contents.items():
        for status, expected_exit, observed_exit in _status_exit_contradictions(text):
            findings.append(
                f"{relative}: contradictory status-to-exit mapping remains: "
                f"{status} requires exit {expected_exit}, not exit {observed_exit}"
            )

    bug_form_path = ".github/ISSUE_TEMPLATE/bug_report.yml"
    package_version_block = _issue_form_field_block(
        contents.get(bug_form_path, ""), "package_version"
    )
    if package_version_block is None:
        findings.append(f"{bug_form_path}: package_version field is missing")
    else:
        version_command = (
            "Paste the exact output of garmin-running-data-normalizer --version"
        )
        if not _contains_whitespace_normalized(
            package_version_block, version_command
        ):
            findings.append(
                f"{bug_form_path}: package_version field must request exact --version output"
            )
        if _has_fixed_version_placeholder(package_version_block):
            findings.append(
                f"{bug_form_path}: package_version placeholder must be version-independent"
            )

    obsolete_phrases = {
        "SUPPORT.md": (
            "Windows is an intended supported platform with public validation in progress.",
        ),
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

    cs010_text = contents.get(CS010_DOCUMENT, "")
    for phrase in CS010_STALE_PUBLIC_STATUS_PHRASES:
        if _contains_whitespace_normalized(cs010_text, phrase):
            findings.append(
                f"{CS010_DOCUMENT}: stale public pre-publication status phrase remains: {phrase}"
            )

    return version, findings


def main() -> None:
    version, findings = validate()
    result = {
        "status": "PASS" if not findings else "FAIL",
        "product_version": version,
        "documents_checked": list(current_documents(version)),
        "findings": findings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if not findings else 1)


if __name__ == "__main__":
    main()
