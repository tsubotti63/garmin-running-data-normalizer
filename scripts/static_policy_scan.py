#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
BANNED_IMPORT_PREFIXES = ("running_platform", "phase" + "1_", "phase" + "2_")
BANNED_PRODUCTION_TERMS = re.compile(r"\b(jma|instagram|wellness|coaching)\b", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
HOST_PATH = re.compile(
    r"(?:/" + r"Users/[^/\s]+|/" + r"home/[^/\s]+|[A-Za-z]:\\\\" + r"Users\\\\[^\\\s]+)"
)
SECRET_ASSIGNMENT = re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]")


def production_imports() -> list[str]:
    violations: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.startswith(BANNED_IMPORT_PREFIXES):
                    violations.append(f"{relative}: banned import {name}")
    return violations


def content_violations() -> list[str]:
    violations: list[str] = []
    excluded = {".git", ".review", ".bootstrap_review", "__pycache__", ".pytest_cache"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() in {".pyc", ".fit", ".zip", ".parquet"}:
            continue
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        if EMAIL.search(text):
            violations.append(f"{relative}: email-like value")
        if HOST_PATH.search(text):
            violations.append(f"{relative}: host absolute path")
        if SECRET_ASSIGNMENT.search(text):
            violations.append(f"{relative}: secret-like assignment")
        if relative.startswith(("src/", "config/")) and BANNED_PRODUCTION_TERMS.search(text):
            violations.append(f"{relative}: non-Garmin production term")
    return violations


def main() -> None:
    violations = production_imports() + content_violations()
    result = {"status": "PASS" if not violations else "FAIL", "violations": violations}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if not violations else 1)


if __name__ == "__main__":
    main()
