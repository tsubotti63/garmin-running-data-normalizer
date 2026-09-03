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
GARMIN_WELLNESS_SOURCE_NAME = re.compile(r"DI-Connect-Wellness", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
HOST_PATH = re.compile(
    r"(?:/" + r"Users/[^/\s]+|/" + r"home/[^/\s]+|[A-Za-z]:\\\\" + r"Users\\\\[^\\\s]+)"
)
SECRET_ASSIGNMENT = re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]")
CI_WORKFLOW = Path(".github/workflows/ci.yml")
PUBLISH_WORKFLOW = Path(".github/workflows/publish-pypi.yml")


def _workflow_job_blocks(workflow: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    in_jobs = False
    for line in workflow.splitlines(keepends=True):
        if line == "jobs:\n":
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if line and not line[0].isspace():
            break
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*(?:#.*)?$", line.rstrip("\n"))
        if match:
            current = match.group(1)
            blocks[current] = [line]
        elif current is not None:
            blocks[current].append(line)
    return {name: "".join(lines) for name, lines in blocks.items()}


def _workflow_step_headers(job_block: str) -> list[str]:
    return re.findall(r"^      - (?:name|uses|run):.*$", job_block, re.MULTILINE)


def _contains_active_line(block: str, expected: str) -> bool:
    return bool(
        re.search(
            rf"^[ \t]*{re.escape(expected)}[ \t]*$",
            block,
            re.MULTILINE,
        )
    )


def _workflow_key_blocks(workflow: str, key: str, *, indent: int = 0) -> list[str]:
    lines = workflow.splitlines()
    prefix = " " * indent
    target_key = rf"(?:{re.escape(key)}|['\"]{re.escape(key)}['\"])"
    sibling_key = r"""(?:[A-Za-z_][A-Za-z0-9_-]*|['"][A-Za-z_][A-Za-z0-9_-]*['"])"""
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(rf"^{re.escape(prefix)}{target_key}\s*:", line)
    ]
    blocks: list[str] = []
    for start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if re.match(
                rf"^{re.escape(prefix)}{sibling_key}\s*:",
                lines[index],
            ):
                end = index
                break
        blocks.append("\n".join(lines[start:end]).rstrip())
    return blocks


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
    excluded = {
        ".git",
        ".review",
        ".bootstrap_review",
        ".venv",
        "__pycache__",
        ".pytest_cache",
    }
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(
            part in excluded or part.endswith(".egg-info") for part in path.parts
        ):
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
        policy_text = GARMIN_WELLNESS_SOURCE_NAME.sub("DI-Connect-GarminSource", text)
        if relative.startswith(("src/", "config/")) and BANNED_PRODUCTION_TERMS.search(policy_text):
            violations.append(f"{relative}: non-Garmin production term")
    return violations


def workflow_security_violations() -> list[str]:
    violations: list[str] = []
    ci_path = ROOT / CI_WORKFLOW
    publish_path = ROOT / PUBLISH_WORKFLOW

    for path in (ci_path, publish_path):
        if not path.is_file():
            violations.append(f"{path.relative_to(ROOT).as_posix()}: required workflow missing")
    if violations:
        return violations

    ci = ci_path.read_text(encoding="utf-8")
    publish = publish_path.read_text(encoding="utf-8")

    expected_top_level_permissions = ["permissions:\n  contents: read"]
    for path, workflow in ((CI_WORKFLOW, ci), (PUBLISH_WORKFLOW, publish)):
        if (
            _workflow_key_blocks(workflow, "permissions")
            != expected_top_level_permissions
        ):
            violations.append(
                f"{path.as_posix()}: top-level permissions must be exactly contents: read"
            )

    if re.search(r"^\s+ref:\s*\$\{\{\s*inputs\.", publish, re.MULTILINE):
        violations.append(f"{PUBLISH_WORKFLOW.as_posix()}: workflow input controls checkout ref")
    source_sha_expressions = re.findall(
        r"\$\{\{[^}\n]*source_sha[^}\n]*\}\}",
        publish,
    )
    if source_sha_expressions != ["${{ inputs.source_sha }}"] * 2:
        violations.append(
            f"{PUBLISH_WORKFLOW.as_posix()}: source_sha may appear only in both trusted identity guards"
        )
    active_git_lines = [
        line.strip()
        for line in publish.splitlines()
        if not re.match(r"^[ \t]*#", line) and re.search(r"\bgit\b", line)
    ]
    expected_git_lines = [
        'test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"',
        'test -z "$(git status --porcelain)"',
    ]
    if active_git_lines != expected_git_lines:
        violations.append(
            f"{PUBLISH_WORKFLOW.as_posix()}: git usage must be limited to both trusted identity checks"
        )
    checkout_steps = re.findall(
        r"^      - uses: actions/checkout@[^\n]+$", publish, re.MULTILINE
    )
    if len(checkout_steps) != 1:
        violations.append(
            f"{PUBLISH_WORKFLOW.as_posix()}: exactly one trusted checkout is required"
        )
    checkout_pattern = re.compile(
        r"^      - uses: actions/checkout@[0-9a-f]{40}(?: #.*)?\n"
        r"        with:\n"
        r"          ref: \$\{\{ github\.sha \}\}\n"
        r"          persist-credentials: false$",
        re.MULTILINE,
    )
    if not checkout_pattern.search(publish):
        violations.append(
            f"{PUBLISH_WORKFLOW.as_posix()}: checkout must use github.sha without persisted credentials"
        )

    dispatch_guards = (
        "WORKFLOW_GIT_REF: ${{ github.ref }}",
        "WORKFLOW_REF: ${{ github.workflow_ref }}",
        "WORKFLOW_SHA: ${{ github.sha }}",
        'test "$WORKFLOW_GIT_REF" = "refs/heads/main"',
        'test "$WORKFLOW_REF" = "tsubotti63/garmin-running-data-normalizer/'
        '.github/workflows/publish-pypi.yml@refs/heads/main"',
        'test "$WORKFLOW_SHA" = "$SOURCE_SHA"',
    )
    identity_guards = (
        "SOURCE_SHA: ${{ inputs.source_sha }}",
        "WORKFLOW_SHA: ${{ github.sha }}",
        'test "$WORKFLOW_SHA" = "$SOURCE_SHA"',
        'test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"',
        'test -z "$(git status --porcelain)"',
    )
    job_blocks = _workflow_job_blocks(publish)
    ci_job_blocks = _workflow_job_blocks(ci)
    if any(_workflow_key_blocks(block, "permissions", indent=4) for block in ci_job_blocks.values()):
        violations.append(
            f"{CI_WORKFLOW.as_posix()}: job-level permissions must not override the read-only workflow default"
        )
    build = job_blocks.get("build", "")
    step_headers = _workflow_step_headers(build)
    expected_prefix = (
        "      - name: Verify trusted dispatch source",
        "      - uses: actions/checkout@",
        "      - name: Verify checked-out source identity",
        "      - uses: actions/setup-python@",
    )
    if len(step_headers) < len(expected_prefix) or any(
        not step_headers[index].startswith(expected)
        for index, expected in enumerate(expected_prefix)
    ):
        violations.append(
            f"{PUBLISH_WORKFLOW.as_posix()}: trusted-source guards must surround checkout and precede repository code execution"
        )
    else:
        dispatch_start = build.find("      - name: Verify trusted dispatch source")
        checkout_start = build.find("      - uses: actions/checkout@")
        identity_start = build.find("      - name: Verify checked-out source identity")
        setup_start = build.find("      - uses: actions/setup-python@")
        dispatch_block = build[dispatch_start:checkout_start]
        identity_block = build[identity_start:setup_start]
        for guard in dispatch_guards:
            if not _contains_active_line(dispatch_block, guard):
                violations.append(
                    f"{PUBLISH_WORKFLOW.as_posix()}: missing pre-checkout guard {guard}"
                )
        expected_dispatch_block = (
            "      - name: Verify trusted dispatch source\n"
            "        env:\n"
            "          SOURCE_SHA: ${{ inputs.source_sha }}\n"
            "          WORKFLOW_GIT_REF: ${{ github.ref }}\n"
            "          WORKFLOW_REF: ${{ github.workflow_ref }}\n"
            "          WORKFLOW_SHA: ${{ github.sha }}\n"
            "        run: |\n"
            '          if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then\n'
            '            echo "source_sha must be a full lowercase 40-character commit SHA" >&2\n'
            "            exit 1\n"
            "          fi\n"
            '          test "$WORKFLOW_GIT_REF" = "refs/heads/main"\n'
            '          test "$WORKFLOW_REF" = "tsubotti63/garmin-running-data-normalizer/'
            '.github/workflows/publish-pypi.yml@refs/heads/main"\n'
            '          test "$WORKFLOW_SHA" = "$SOURCE_SHA"\n'
        )
        if dispatch_block != expected_dispatch_block:
            violations.append(
                f"{PUBLISH_WORKFLOW.as_posix()}: pre-checkout dispatch step may contain only the ordered trust guards"
            )
        for guard in identity_guards:
            if not _contains_active_line(identity_block, guard):
                violations.append(
                    f"{PUBLISH_WORKFLOW.as_posix()}: missing post-checkout guard {guard}"
                )
        expected_identity_block = (
            "      - name: Verify checked-out source identity\n"
            "        env:\n"
            "          SOURCE_SHA: ${{ inputs.source_sha }}\n"
            "          WORKFLOW_SHA: ${{ github.sha }}\n"
            "        run: |\n"
            '          test "$WORKFLOW_SHA" = "$SOURCE_SHA"\n'
            '          test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"\n'
            '          test -z "$(git status --porcelain)"\n'
        )
        if identity_block != expected_identity_block:
            violations.append(
                f"{PUBLISH_WORKFLOW.as_posix()}: post-checkout identity step may contain only the ordered trust guards"
            )

    expected_oidc_jobs = {"publish-testpypi", "publish-pypi"}
    expected_oidc_permission_block = ["    permissions:\n      id-token: write"]
    invalid_job_permissions = {
        name
        for name, block in job_blocks.items()
        if _workflow_key_blocks(block, "permissions", indent=4)
        != (expected_oidc_permission_block if name in expected_oidc_jobs else [])
    }
    oidc_permission = re.compile(
        r"^    permissions:\n      id-token: write\n(?=    [A-Za-z])",
        re.MULTILINE,
    )
    oidc_jobs = {
        name for name, block in job_blocks.items() if oidc_permission.search(block)
    }
    noncomment_oidc_lines = re.findall(
        r"^\s+id-token:\s*write\s*$", publish, re.MULTILINE
    )
    if (
        invalid_job_permissions
        or oidc_jobs != expected_oidc_jobs
        or len(noncomment_oidc_lines) != 2
    ):
        violations.append(
            f"{PUBLISH_WORKFLOW.as_posix()}: OIDC permission must be exclusive to both publish jobs"
        )
    if not re.search(
        r"perform_upload:\n(?:        .*\n)+?        default: false\n",
        publish,
        re.MULTILINE,
    ):
        violations.append(f"{PUBLISH_WORKFLOW.as_posix()}: upload is not disabled by default")
    return violations


def main() -> None:
    violations = (
        production_imports() + content_violations() + workflow_security_violations()
    )
    result = {"status": "PASS" if not violations else "FAIL", "violations": violations}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if not violations else 1)


if __name__ == "__main__":
    main()
