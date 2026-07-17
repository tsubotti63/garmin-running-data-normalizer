#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ADOPTION_RECORD = ROOT / "docs/reference/platform_standard_adoption_v0_9.json"
ZIP_PREFIX = "ai-collaboration-platform/"
STANDARD_PREFIXES = (
    "docs/project_os/", "docs/proofs/", "templates/", "runtime/agents/",
    "runtime/packages/", "runtime/work/",
)
STANDARD_FILES = {
    "runtime/README.md", "packages/README.md",
    "docs/README.md", "examples/generic_reference_project/README.md", "QUICK_START.md",
    "PLATFORM_EVOLUTION.md", "CHANGELOG.md",
}
PROJECT_FILES = (
    "README.md", "AGENTS.md", "docs/README.md", "docs/project/project_context.md",
    "docs/project/project_charter.md", "docs/project/project_governance.md",
    "docs/project/project_boundary.md", "docs/project/project_requirements.md",
    "docs/project/definition_of_done.md", "runtime/project_runtime_addendum.md",
)
PLATFORM_IDENTITY_FILES = (
    "platform_manifest_v0_9.json", "platform_inventory_v0_9.csv", "platform_qa_v0_9.json",
)
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".toml", ".yaml", ".yml"}
TEXT_FILENAMES = {".gitattributes", ".gitignore"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selected(path: str) -> bool:
    return path in STANDARD_FILES or path.startswith(STANDARD_PREFIXES)


def target_text_files(standard_paths: set[str]) -> list[Path]:
    """Return tracked and untracked Target-owned text files, excluding Standard bytes."""
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    paths: list[Path] = []
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8")
        if relative in standard_paths or relative.startswith((".review/", ".bootstrap_review/")):
            continue
        path = ROOT / relative
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name in TEXT_FILENAMES):
            paths.append(path)
    return sorted(paths)


def create_record(zip_path: Path) -> dict[str, object]:
    entries = []
    with ZipFile(zip_path) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith(ZIP_PREFIX) or name.endswith("/"):
                continue
            relative = name[len(ZIP_PREFIX):]
            if not selected(relative):
                continue
            data = archive.read(name)
            entries.append({"path": relative, "bytes": len(data), "sha256": digest(data)})
    return {
        "record_type": "target_platform_standard_adoption",
        "platform_version": "0.9",
        "source_artifact": zip_path.name,
        "source_sha256": digest(zip_path.read_bytes()),
        "standard_file_count": len(entries),
        "standard_files": entries,
        "excluded_platform_identity_files": list(PLATFORM_IDENTITY_FILES),
    }


def validate(record: dict[str, object]) -> dict[str, object]:
    missing: list[str] = []
    mismatched: list[str] = []
    for entry in record.get("standard_files", []):
        path = ROOT / str(entry["path"])
        if not path.is_file():
            missing.append(str(entry["path"]))
            continue
        data = path.read_bytes()
        if len(data) != entry["bytes"] or digest(data) != entry["sha256"]:
            mismatched.append(str(entry["path"]))
    missing_project = [path for path in PROJECT_FILES if not (ROOT / path).is_file()]
    identity_leaks = [path for path in PLATFORM_IDENTITY_FILES if (ROOT / path).exists()]
    metadata_artifacts = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.name == ".DS_Store" or "__MACOSX" in path.parts
    )
    nested_git = sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob(".git")
        if path != ROOT / ".git"
    )
    placeholders = []
    for relative in PROJECT_FILES:
        path = ROOT / relative
        if path.is_file() and "<PROJECT_" in path.read_text(encoding="utf-8", errors="ignore"):
            placeholders.append(relative)
    standard_paths = {str(entry["path"]) for entry in record.get("standard_files", [])}
    final_newline_violations = []
    for path in target_text_files(standard_paths):
        data = path.read_bytes()
        if not data.endswith(b"\n") or data.endswith(b"\n\n"):
            final_newline_violations.append(path.relative_to(ROOT).as_posix())
    expected_count = int(record.get("standard_file_count", -1))
    actual_count = len(record.get("standard_files", []))
    passed = not (
        missing or mismatched or missing_project or identity_leaks or placeholders
        or metadata_artifacts or nested_git or final_newline_violations
    ) and expected_count == actual_count
    return {
        "status": "PASS" if passed else "FAIL",
        "standard_file_count": actual_count,
        "missing_standard_files": missing,
        "mismatched_standard_files": mismatched,
        "missing_project_customization": missing_project,
        "platform_identity_files_not_adopted": not identity_leaks,
        "unexpected_platform_identity_files": identity_leaks,
        "unwanted_metadata_artifacts": metadata_artifacts,
        "nested_git_paths": nested_git,
        "unresolved_project_placeholders": placeholders,
        "target_final_newline_violations": final_newline_violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-from-zip", type=Path)
    args = parser.parse_args()
    if args.record_from_zip:
        record = create_record(args.record_from_zip)
        ADOPTION_RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not ADOPTION_RECORD.is_file():
        raise SystemExit("Platform adoption record is missing")
    result = validate(json.loads(ADOPTION_RECORD.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
