#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import tomllib
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
    "docs/known_limitations.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
)
REQUIRED_PLATFORM_SECTIONS = (
    "README.md",
    "docs/product_quick_start.md",
    "docs/getting_started_from_garmin_export.md",
    "docs/project/run_all_public_usage_example_v0_1.md",
)
WINDOWS_SETUP_DOCUMENTS = (
    "README.md",
    "docs/product_quick_start.md",
    "docs/getting_started_from_garmin_export.md",
    "docs/project/run_all_public_usage_example_v0_1.md",
    "CONTRIBUTING.md",
)
CURRENT_STABLE_DOCUMENTS = (
    "README.md",
    "docs/product_quick_start.md",
    "docs/getting_started_from_garmin_export.md",
    "docs/faq.md",
    "docs/known_limitations.md",
)
WINDOWS_SOURCE_CONTROL_COMMANDS = re.compile(
    r"(?im)^\s*git\s+(?:clone|fetch|checkout|pull)\b"
)


def _project_version(root: Path, pyproject_data: dict[str, object]) -> str:
    project = pyproject_data["project"]
    if not isinstance(project, dict):
        raise TypeError("project must be a table")
    static_version = project.get("version")
    if isinstance(static_version, str):
        return static_version

    tool = pyproject_data["tool"]
    if not isinstance(tool, dict):
        raise TypeError("tool must be a table")
    setuptools = tool["setuptools"]
    if not isinstance(setuptools, dict):
        raise TypeError("tool.setuptools must be a table")
    dynamic = setuptools["dynamic"]
    if not isinstance(dynamic, dict):
        raise TypeError("tool.setuptools.dynamic must be a table")
    version_config = dynamic["version"]
    if not isinstance(version_config, dict):
        raise TypeError("dynamic version must be a table")
    attr = version_config["attr"]
    if not isinstance(attr, str):
        raise TypeError("dynamic version attr must be a string")

    module_name, attribute = attr.rsplit(".", 1)
    module_path = root / "src" / Path(*module_name.split("."))
    source_path = module_path.with_suffix(".py")
    if not source_path.is_file():
        source_path = module_path / "__init__.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == attribute
            for target in targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, str):
            return value
    raise ValueError("dynamic version attribute is missing or non-literal")


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
    current_version: str | None = None
    if not pyproject.is_file():
        findings.append("pyproject.toml: missing")
    else:
        pyproject_text = pyproject.read_text(encoding="utf-8")
        try:
            current_version = _project_version(
                root, tomllib.loads(pyproject_text)
            )
        except (
            FileNotFoundError,
            KeyError,
            SyntaxError,
            TypeError,
            ValueError,
            tomllib.TOMLDecodeError,
        ):
            findings.append("pyproject.toml: project version is missing or invalid")
        if '"tzdata; platform_system == \'Windows\'"' not in pyproject_text:
            findings.append(
                "pyproject.toml: Windows conditional tzdata dependency is missing"
            )

    for relative in REQUIRED_PLATFORM_SECTIONS:
        text = contents.get(relative, "")
        if "macOS / Linux" not in text:
            findings.append(f"{relative}: macOS / Linux section is missing")
        if "Windows PowerShell" not in text:
            findings.append(f"{relative}: Windows PowerShell section is missing")

    for relative in WINDOWS_SETUP_DOCUMENTS:
        powershell_blocks = [
            block
            for language, block in _fenced_blocks(contents.get(relative, ""))
            if language in {"powershell", "pwsh"}
        ]
        if not any("python -m venv .venv" in block for block in powershell_blocks):
            findings.append(
                f"{relative}: Windows setup must use python -m venv .venv"
            )
        if any(
            WINDOWS_SOURCE_CONTROL_COMMANDS.search(block)
            for block in powershell_blocks
        ):
            findings.append(
                f"{relative}: Windows runtime instructions must not perform Git source acquisition"
            )

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

    for relative in CURRENT_STABLE_DOCUMENTS:
        text = contents.get(relative, "")
        if current_version is not None:
            version_pattern = re.escape(current_version)
            if not re.search(
                rf"(?:(?:current|stable)[^\n]*v?{version_pattern}|"
                rf"v?{version_pattern}[^\n]*(?:current|stable))",
                text,
                re.IGNORECASE,
            ):
                findings.append(
                    f"{relative}: current stable v{current_version} is not identified"
                )
        if re.search(
            r"(?:patch release is being prepared|unreleased patch|"
            r"manual(?:ly)? install(?:ing)? `?tzdata`?|"
            r"python -m pip install tzdata)",
            text,
            re.IGNORECASE,
        ):
            findings.append(
                f"{relative}: obsolete v1.2.0 Windows workaround or pending-patch wording remains"
            )

    for relative in ("README.md", "docs/product_quick_start.md"):
        text = contents.get(relative, "")
        if "automatically" not in text or "`tzdata`" not in text:
            findings.append(
                f"{relative}: current Windows automatic tzdata behavior is missing"
            )

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
