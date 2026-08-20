#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UUID = re.compile(rb"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
EMAIL = re.compile(rb"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
HOST_PATH = re.compile(
    b"/" + rb"Users/[^/\s]+|/" + rb"home/[^/\s]+|[A-Za-z]:\\" + rb"Users\\[^\\\s]+"
)
SECRET = re.compile(
    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|"
    rb"gh[pousr]_[A-Za-z0-9_]{20,}|AIza[0-9A-Za-z_-]{20,}|"
    rb"xox[baprs]-[A-Za-z0-9-]+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|"
    rb"(?:Cookie|Set-Cookie):"
)
SYNTHETIC_TEST_PATH = "tests/test_v14_diagnostics.py"
SYNTHETIC_PRIVATE_KEY_LINE = (
    b'"PN-09-private-key": b"-----BEGIN PRIVATE KEY-----",'
)
INTERNAL = {
    "private_source_name": re.compile(rb"running[_-]data[_-]platform[_-]garmin[_-]mvp[_-]verified", re.IGNORECASE),
    "task_reference": re.compile((b"codex" + b"-task:"), re.IGNORECASE),
    "private_phase": re.compile(rb"Phase(?:1\.3|2\.0)|" + b"phase1" + b"_3|" + b"phase2" + b"_", re.IGNORECASE),
    "private_source_path": re.compile(rb"src/" + b"running_platform/|scripts/" + b"phase1_", re.IGNORECASE),
    "private_workflow_status": re.compile(
        (b"WAITING" + b"_FOR_BOOTSTRAP_REVIEW|READY" + b"_FOR_IMPLEMENTATION|"
         b"TARGET_PROJECT" + b"_OWNED_IMPLEMENTATION|NOT_AVAILABLE" + b"_SOURCE_NOT_GIT|"
         b"RECORDED_EXTERNALLY" + b"_AFTER_COMMIT"),
        re.IGNORECASE,
    ),
    "pre_sanitization_commit": re.compile(
        (b"f63914fa" + b"f2414b9c28bf552542e23aa8521bb6d1|"
         b"43389709" + b"c063c3765071ae0671a943c5de80c650"),
        re.IGNORECASE,
    ),
    "private_gate_id": re.compile(rb"PLATFORM-ALIGNMENT-AND-REUSE-[0-9-]+|GITHUB-INITIAL-REGISTRATION-READINESS-C[0-9]+", re.IGNORECASE),
}
APPROVED_IDENTITY = re.compile(r"^[0-9]+\+[A-Za-z0-9-]+@users\.noreply\.github\.com$")
APPROVED_GITHUB_COMMITTERS = frozenset(
    {
        ("GitHub", "noreply" + "@github.com"),
    }
)
REQUIRED_CI_REFS = frozenset(
    {
        "refs/heads/main",
        "refs/remotes/origin/HEAD",
        "refs/remotes/origin/main",
    }
)
PRIVATE_REF_MARKER = re.compile(r"(?:^|[/_.-])(?:private|internal)(?:$|[/_.-])", re.IGNORECASE)
SANITIZED_BASE_COMMITS = (
    "de53b0999b32064168bb69ed5afe3695be5a9564",
    "8404a6900402a88e07e3cc66a534a285f45cd7d5",
)


def git(*args: str, binary: bool = False):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=not binary)


def _is_synthetic_private_key_marker(
    data: bytes,
    match: re.Match[bytes],
    *,
    allow_synthetic_canary: bool,
) -> bool:
    """Allow only the exact historical synthetic fixture marker.

    The public-history scan must keep rejecting real credential material. The
    exception is deliberately narrow: it applies only when the caller has
    already established that the blob is the v1.4 diagnostics test fixture,
    the match is the exact private-key marker, and the fixture contains that
    exact canary declaration once.
    """
    return (
        allow_synthetic_canary
        and match.group(0) == b"-----BEGIN PRIVATE KEY-----"
        and data.count(match.group(0)) == 1
        and SYNTHETIC_PRIVATE_KEY_LINE in data
    )


def scan(
    label: str,
    data: bytes,
    *,
    allow_email: bool = False,
    allow_synthetic_canary: bool = False,
) -> list[str]:
    findings = []
    for name, pattern in INTERNAL.items():
        if pattern.search(data):
            findings.append(f"{label}: {name}")
    if UUID.search(data):
        findings.append(f"{label}: task_or_internal_uuid")
    if HOST_PATH.search(data):
        findings.append(f"{label}: host_absolute_path")
    if any(
        not _is_synthetic_private_key_marker(
            data,
            match,
            allow_synthetic_canary=allow_synthetic_canary,
        )
        for match in SECRET.finditer(data)
    ):
        findings.append(f"{label}: credential_or_token")
    if not allow_email and EMAIL.search(data):
        findings.append(f"{label}: email")
    return findings


def is_approved_committer(
    author_name: str,
    author_email: str,
    committer_name: str,
    committer_email: str,
) -> bool:
    if (author_name, author_email) == (committer_name, committer_email):
        return True
    return (committer_name, committer_email) in APPROVED_GITHUB_COMMITTERS


def validate_commit_identities(
    records: list[tuple[str, str, str, str, str]],
) -> list[str]:
    findings: list[str] = []
    author_emails: list[str] = []
    for commit, author_name, author_email, committer_name, committer_email in records:
        author_emails.append(author_email)
        if not APPROVED_IDENTITY.fullmatch(author_email):
            findings.append(f"commit {commit}: unapproved public identity")
        if not is_approved_committer(
            author_name,
            author_email,
            committer_name,
            committer_email,
        ):
            findings.append(f"commit {commit}: unapproved committer identity")
    # GitHub profile display names are mutable metadata. The verified noreply
    # email identifies the account and must remain consistent across history.
    if author_emails and len(set(author_emails)) != 1:
        findings.append("commit metadata: author identities are not consistent")
    return findings


def is_allowed_ci_ref(ref: str) -> bool:
    return (
        ref in REQUIRED_CI_REFS
        or ref.startswith("refs/tags/")
        or ref.startswith("refs/remotes/origin/")
    )


def validate_ci_refs(refs: list[str], remotes: list[str]) -> list[str]:
    findings: list[str] = []
    missing_refs = sorted(REQUIRED_CI_REFS - set(refs))
    unexpected_refs = sorted(ref for ref in refs if not is_allowed_ci_ref(ref))
    if missing_refs:
        findings.append(f"refs: missing {missing_refs}")
    if unexpected_refs:
        findings.append(f"refs: unexpected {unexpected_refs}")
    if remotes != ["origin"]:
        findings.append(f"remote: expected origin only, found {remotes}")
    for ref in refs:
        findings.extend(scan(f"ref {ref}", ref.encode("utf-8")))
        if PRIVATE_REF_MARKER.search(ref):
            findings.append(f"ref {ref}: private_or_internal_marker")
    return findings


def validate_repository_guards(
    *,
    is_shallow: bool,
    sanitized_base_ancestors: dict[str, bool],
) -> list[str]:
    findings: list[str] = []
    if is_shallow:
        findings.append("history: shallow repository")
    for base_commit, is_ancestor in sanitized_base_ancestors.items():
        if not is_ancestor:
            findings.append(f"history: sanitized base {base_commit} is not an ancestor of HEAD")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true", help="allow a normal public clone with origin refs")
    args = parser.parse_args()
    findings: list[str] = []
    refs = sorted(line for line in git("for-each-ref", "--format=%(refname)").splitlines() if line)
    remotes = sorted(line for line in git("remote").splitlines() if line)
    if args.ci:
        findings.extend(validate_ci_refs(refs, remotes))
        head = git("rev-parse", "HEAD").strip()
        for ref in ("refs/heads/main", "refs/remotes/origin/main"):
            try:
                value = git("rev-parse", ref).strip()
            except subprocess.CalledProcessError:
                findings.append(f"refs: missing {ref}")
            else:
                if value != head:
                    findings.append(f"refs: {ref} does not match HEAD")
        try:
            origin_head = git("symbolic-ref", "refs/remotes/origin/HEAD").strip()
        except subprocess.CalledProcessError:
            findings.append("refs: origin/HEAD is not symbolic")
        else:
            if origin_head != "refs/remotes/origin/main":
                findings.append(f"refs: origin/HEAD targets {origin_head}")
        commits = [line for line in git("rev-list", "--all").splitlines() if line]
    else:
        if refs != ["refs/heads/main"]:
            findings.append(f"refs: unexpected {refs}")
        if remotes:
            findings.append(f"remote: configured {remotes}")
        commits = [line for line in git("rev-list", "--all").splitlines() if line]
    sanitized_base_ancestors: dict[str, bool] = {}
    for base_commit in SANITIZED_BASE_COMMITS:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_commit, "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        sanitized_base_ancestors[base_commit] = ancestor.returncode == 0
    findings.extend(
        validate_repository_guards(
            is_shallow=git("rev-parse", "--is-shallow-repository").strip() != "false",
            sanitized_base_ancestors=sanitized_base_ancestors,
        )
    )

    identity_records: list[tuple[str, str, str, str, str]] = []
    for commit in commits:
        fields = git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%s%x00%b", commit).split("\0")
        if len(fields) < 6:
            findings.append(f"commit {commit}: malformed metadata")
            continue
        author_name, author_email, committer_name, committer_email, subject, body = fields[:6]
        identity_records.append((commit, author_name, author_email, committer_name, committer_email))
        findings.extend(scan(f"commit-message {commit}", (subject + "\n" + body).encode("utf-8")))
        paths = git("ls-tree", "-r", "--name-only", commit).splitlines()
        for path in paths:
            findings.extend(scan(f"path {commit}:{path}", path.encode("utf-8")))
    findings.extend(validate_commit_identities(identity_records))

    object_paths: dict[str, list[str]] = {}
    for line in git("rev-list", "--all", "--objects").splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            object_paths.setdefault(parts[0], []).append(parts[1])

    listing = git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)")
    scanned_objects = 0
    for line in listing.splitlines():
        oid, object_type = line.split()
        if object_type not in {"blob", "commit", "tag"}:
            continue
        scanned_objects += 1
        data = git("cat-file", object_type, oid, binary=True)
        findings.extend(
            scan(
                f"object {oid} ({object_type})",
                data,
                allow_email=object_type in {"commit", "tag"},
                allow_synthetic_canary=(
                    object_type == "blob"
                    and object_paths.get(oid, [])
                    and all(
                        path == SYNTHETIC_TEST_PATH
                        for path in object_paths[oid]
                    )
                ),
            )
        )

    result = {
        "status": "PASS" if not findings else "FAIL",
        "mode": "ci" if args.ci else "pre-registration",
        "reachable_commit_count": len(commits),
        "ref_count": len(refs),
        "object_count_scanned": scanned_objects,
        "findings": sorted(set(findings)),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if not findings else 1)


if __name__ == "__main__":
    main()
