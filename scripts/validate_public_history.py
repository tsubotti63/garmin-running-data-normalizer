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
SANITIZED_BASE_COMMITS = (
    "de53b0999b32064168bb69ed5afe3695be5a9564",
    "8404a6900402a88e07e3cc66a534a285f45cd7d5",
)


def git(*args: str, binary: bool = False):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=not binary)


def scan(label: str, data: bytes, *, allow_email: bool = False) -> list[str]:
    findings = []
    for name, pattern in INTERNAL.items():
        if pattern.search(data):
            findings.append(f"{label}: {name}")
    if UUID.search(data):
        findings.append(f"{label}: task_or_internal_uuid")
    if HOST_PATH.search(data):
        findings.append(f"{label}: host_absolute_path")
    if SECRET.search(data):
        findings.append(f"{label}: credential_or_token")
    if not allow_email and EMAIL.search(data):
        findings.append(f"{label}: email")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true", help="allow a normal public clone with origin refs")
    args = parser.parse_args()
    findings: list[str] = []
    refs = sorted(line for line in git("for-each-ref", "--format=%(refname)").splitlines() if line)
    remotes = sorted(line for line in git("remote").splitlines() if line)
    if args.ci:
        expected_refs = {
            "refs/heads/main",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/main",
        }
        if set(refs) != expected_refs:
            findings.append(f"refs: expected {sorted(expected_refs)}, found {refs}")
        if remotes != ["origin"]:
            findings.append(f"remote: expected origin only, found {remotes}")
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
        commits = [line for line in git("rev-list", "HEAD").splitlines() if line]
    else:
        if refs != ["refs/heads/main"]:
            findings.append(f"refs: unexpected {refs}")
        if remotes:
            findings.append(f"remote: configured {remotes}")
        commits = [line for line in git("rev-list", "--all").splitlines() if line]
    if git("rev-parse", "--is-shallow-repository").strip() != "false":
        findings.append("history: shallow repository")
    for base_commit in SANITIZED_BASE_COMMITS:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_commit, "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        if ancestor.returncode != 0:
            findings.append(f"history: sanitized base {base_commit} is not an ancestor of HEAD")

    identities = []
    for commit in commits:
        fields = git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%s%x00%b", commit).split("\0")
        if len(fields) < 6:
            findings.append(f"commit {commit}: malformed metadata")
            continue
        author_name, author_email, committer_name, committer_email, subject, body = fields[:6]
        identities.append((author_name, author_email, committer_name, committer_email))
        if author_name != committer_name or author_email != committer_email:
            findings.append(f"commit {commit}: author/committer identity mismatch")
        if not APPROVED_IDENTITY.fullmatch(author_email):
            findings.append(f"commit {commit}: unapproved public identity")
        findings.extend(scan(f"commit-message {commit}", (subject + "\n" + body).encode("utf-8")))
        paths = git("ls-tree", "-r", "--name-only", commit).splitlines()
        for path in paths:
            findings.extend(scan(f"path {commit}:{path}", path.encode("utf-8")))
    if identities and len(set(identities)) != 1:
        findings.append("commit metadata: identities are not consistent")

    listing = git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)")
    scanned_objects = 0
    for line in listing.splitlines():
        oid, object_type = line.split()
        if object_type not in {"blob", "commit", "tag"}:
            continue
        scanned_objects += 1
        data = git("cat-file", object_type, oid, binary=True)
        findings.extend(scan(f"object {oid} ({object_type})", data, allow_email=object_type == "commit"))

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
