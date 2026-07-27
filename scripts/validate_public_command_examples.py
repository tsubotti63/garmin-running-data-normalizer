#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCUMENTS = (
    "README.md",
    "docs/product_quick_start.md",
    "docs/getting_started_from_garmin_export.md",
    "docs/ai_analysis_quick_start.md",
    "docs/project/run_all_public_usage_example_v0_1.md",
    "docs/faq.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
)
REQUIRED_PLATFORM_SECTIONS = (
    "README.md",
    "docs/product_quick_start.md",
    "docs/getting_started_from_garmin_export.md",
    "docs/project/run_all_public_usage_example_v0_1.md",
)


def _fenced_blocks(text: str) -> Iterable[tuple[str, str]]:
    pattern = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(text):
        yield match.group(1).strip().lower(), match.group(2)


def validate(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    contents: dict[str, str] = {}
    for relative in PUBLIC_DOCUMENTS:
        path = root / relative
        if not path.is_file():
            findings.append(f"{relative}: required public document is missing")
            continue
        contents[relative] = path.read_text(encoding="utf-8")

    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        findings.append("pyproject.toml: missing")
    elif '"tzdata; platform_system == \'Windows\'"' not in pyproject.read_text(
        encoding="utf-8"
    ):
        findings.append("pyproject.toml: Windows conditional tzdata dependency is missing")

    for relative in REQUIRED_PLATFORM_SECTIONS:
        text = contents.get(relative, "")
        if "macOS / Linux" not in text:
            findings.append(f"{relative}: macOS / Linux section is missing")
        if "Windows PowerShell" not in text:
            findings.append(f"{relative}: Windows PowerShell section is missing")

    quick_start = contents.get("docs/product_quick_start.md", "")
    if "diff -ru" in quick_start:
        findings.append(
            "docs/product_quick_start.md: repeatability depends on Unix diff -ru"
        )
    if "scripts/compare_deterministic_outputs.py" not in quick_start:
        findings.append(
            "docs/product_quick_start.md: cross-platform repeatability validator is missing"
        )

    public_usage = contents.get(
        "docs/project/run_all_public_usage_example_v0_1.md", ""
    )
    if "python - <<'PY'" in public_usage:
        findings.append(
            "docs/project/run_all_public_usage_example_v0_1.md: Bash heredoc remains"
        )

    for relative, text in contents.items():
        for language, block in _fenced_blocks(text):
            if language not in {"powershell", "pwsh"}:
                continue
            if any(line.rstrip().endswith("\\") for line in block.splitlines()):
                findings.append(f"{relative}: PowerShell block uses Bash continuation")
            if "/path/to/" in block:
                findings.append(f"{relative}: PowerShell block uses a Unix placeholder path")

    for relative in ("README.md", "docs/product_quick_start.md"):
        text = contents.get(relative, "")
        if "v1.2.0" not in text:
            findings.append(f"{relative}: current stable v1.2.0 is not identified")
        if "python -m pip install tzdata" not in text:
            findings.append(f"{relative}: v1.2.0 Windows workaround is missing")
        if "patch release" not in text.lower():
            findings.append(f"{relative}: unreleased patch status is missing")
        if re.search(r"(?:current|stable)[^\n]*v1\.2\.1", text, re.IGNORECASE):
            findings.append(f"{relative}: unreleased v1.2.1 is presented as stable")

    getting_started = contents.get("docs/getting_started_from_garmin_export.md", "")
    for command in ("run-all", "validate-handoff", "snapshot"):
        if not re.search(
            rf"```powershell\n(?:(?!```).)*\b{re.escape(command)}\b",
            getting_started,
            re.DOTALL,
        ):
            findings.append(
                "docs/getting_started_from_garmin_export.md: "
                f"PowerShell {command} example is missing"
            )

    ai_quick_start = contents.get("docs/ai_analysis_quick_start.md", "")
    for option in ("--external-safe-pack", "snapshot"):
        if not re.search(
            rf"```powershell\n(?:(?!```).)*{re.escape(option)}",
            ai_quick_start,
            re.DOTALL,
        ):
            findings.append(
                f"docs/ai_analysis_quick_start.md: PowerShell {option} example is missing"
            )

    return findings


def main() -> int:
    findings = validate()
    print(
        json.dumps(
            {"status": "PASS" if not findings else "FAIL", "findings": findings},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
