#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def compare_output_directories(first: Path, second: Path) -> dict[str, Any]:
    findings: list[str] = []
    if not first.is_dir():
        findings.append("first output directory does not exist")
    if not second.is_dir():
        findings.append("second output directory does not exist")
    if findings:
        return {"status": "FAIL", "findings": findings}

    first_files = _files(first)
    second_files = _files(second)
    if set(first_files) != set(second_files):
        missing_from_first = sorted(set(second_files) - set(first_files))
        missing_from_second = sorted(set(first_files) - set(second_files))
        if missing_from_first:
            findings.append(f"files missing from first output: {missing_from_first}")
        if missing_from_second:
            findings.append(f"files missing from second output: {missing_from_second}")

    mismatched = sorted(
        path
        for path in set(first_files) & set(second_files)
        if first_files[path] != second_files[path]
    )
    if mismatched:
        findings.append(f"byte content differs: {mismatched}")

    summary_path = "run_summary.json"
    if summary_path in first_files or summary_path in second_files:
        if summary_path not in first_files or summary_path not in second_files:
            findings.append("run_summary.json must exist in both outputs")
        else:
            try:
                first_summary = json.loads((first / summary_path).read_text(encoding="utf-8"))
                second_summary = json.loads((second / summary_path).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                findings.append(f"run_summary.json is not readable JSON: {type(exc).__name__}")
            else:
                for label, summary in (
                    ("first", first_summary),
                    ("second", second_summary),
                ):
                    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
                        findings.append(f"{label} output status is not successful")
                    if not summary.get("deterministic_output_digest"):
                        findings.append(f"{label} output has no deterministic digest")
                if first_summary.get("deterministic_output_digest") != second_summary.get(
                    "deterministic_output_digest"
                ):
                    findings.append("deterministic output digests differ")

    return {
        "status": "PASS" if not findings else "FAIL",
        "file_count": len(first_files),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two generated output directories without shell-specific tools."
    )
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()
    result = compare_output_directories(args.first, args.second)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
