from __future__ import annotations

from pathlib import Path

from scripts import validate_public_history as validator


APPROVED_AUTHOR = (
    "tsubotti63",
    "305696068+tsubotti63" + "@users.noreply.github.com",
)
GITHUB_COMMITTER = ("GitHub", "noreply" + "@github.com")
REQUIRED_REFS = sorted(validator.REQUIRED_CI_REFS)


def identity_record(
    commit: str,
    *,
    author: tuple[str, str] = APPROVED_AUTHOR,
    committer: tuple[str, str] = APPROVED_AUTHOR,
) -> tuple[str, str, str, str, str]:
    return (commit, author[0], author[1], committer[0], committer[1])


def test_approved_author_committer_identity_passes() -> None:
    assert validator.validate_commit_identities([identity_record("same")]) == []


def test_confirmed_github_committer_passes() -> None:
    records = [identity_record("squash", committer=GITHUB_COMMITTER)]
    assert validator.validate_commit_identities(records) == []


def test_unknown_committer_fails() -> None:
    records = [
        identity_record(
            "unknown",
            committer=("Automation", "automation" + "@example.invalid"),
        )
    ]
    assert validator.validate_commit_identities(records) == [
        "commit unknown: unapproved committer identity"
    ]


def test_unapproved_author_email_fails() -> None:
    unapproved = ("tsubotti63", "maintainer" + "@example.invalid")
    findings = validator.validate_commit_identities(
        [identity_record("author", author=unapproved, committer=unapproved)]
    )
    assert findings == ["commit author: unapproved public identity"]


def test_multiple_author_identities_fail() -> None:
    other = ("other", "123+other" + "@users.noreply.github.com")
    findings = validator.validate_commit_identities(
        [
            identity_record("first"),
            identity_record("second", author=other, committer=other),
        ]
    )
    assert "commit metadata: author identities are not consistent" in findings


def test_required_ci_refs_pass() -> None:
    assert validator.validate_ci_refs(REQUIRED_REFS, ["origin"]) == []


def test_origin_feature_ref_passes() -> None:
    refs = REQUIRED_REFS + ["refs/remotes/origin/feature/example"]
    assert validator.validate_ci_refs(refs, ["origin"]) == []


def test_tag_ref_passes() -> None:
    refs = REQUIRED_REFS + ["refs/tags/v1.1.1"]
    assert validator.validate_ci_refs(refs, ["origin"]) == []


def test_local_feature_ref_fails() -> None:
    refs = REQUIRED_REFS + ["refs/heads/feature/example"]
    findings = validator.validate_ci_refs(refs, ["origin"])
    assert "refs: unexpected ['refs/heads/feature/example']" in findings


def test_non_origin_remote_ref_fails() -> None:
    refs = REQUIRED_REFS + ["refs/remotes/upstream/main"]
    findings = validator.validate_ci_refs(refs, ["origin", "upstream"])
    assert "refs: unexpected ['refs/remotes/upstream/main']" in findings
    assert "remote: expected origin only, found ['origin', 'upstream']" in findings


def test_private_or_internal_ref_fails() -> None:
    refs = REQUIRED_REFS + ["refs/remotes/origin/feature/private-evidence"]
    findings = validator.validate_ci_refs(refs, ["origin"])
    assert (
        "ref refs/remotes/origin/feature/private-evidence: private_or_internal_marker"
        in findings
    )


def test_missing_required_ref_fails() -> None:
    refs = [ref for ref in REQUIRED_REFS if ref != "refs/remotes/origin/HEAD"]
    findings = validator.validate_ci_refs(refs, ["origin"])
    assert "refs: missing ['refs/remotes/origin/HEAD']" in findings


def test_pr1_squash_merge_history_passes_identity_policy() -> None:
    records = [
        identity_record("ordinary"),
        identity_record(
            "abe0281b2e8a713ad1b4bb44aa6adcca2b0f6445",
            committer=GITHUB_COMMITTER,
        ),
    ]
    assert validator.validate_commit_identities(records) == []


def test_public_feature_commit_identity_is_still_fail_closed() -> None:
    feature_author = ("external", "external" + "@example.invalid")
    findings = validator.validate_commit_identities(
        [
            identity_record("main"),
            identity_record(
                "feature",
                author=feature_author,
                committer=feature_author,
            ),
        ]
    )
    assert "commit feature: unapproved public identity" in findings
    assert "commit metadata: author identities are not consistent" in findings


def test_existing_sensitive_content_scans_still_fail() -> None:
    assert "fixture: credential_or_token" in validator.scan(
        "fixture",
        b"ghp_" + b"ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
    )
    assert "fixture: host_absolute_path" in validator.scan(
        "fixture",
        b"/" + b"Users/example/private/file.json",
    )
    assert "fixture: private_source_name" in validator.scan(
        "fixture",
        b"running_" + b"data_platform_garmin_mvp_verified",
    )


def test_shallow_repository_fails() -> None:
    findings = validator.validate_repository_guards(
        is_shallow=True,
        sanitized_base_ancestors={base: True for base in validator.SANITIZED_BASE_COMMITS},
    )
    assert "history: shallow repository" in findings


def test_missing_sanitized_base_ancestor_fails() -> None:
    ancestors = {base: True for base in validator.SANITIZED_BASE_COMMITS}
    missing = validator.SANITIZED_BASE_COMMITS[0]
    ancestors[missing] = False
    findings = validator.validate_repository_guards(
        is_shallow=False,
        sanitized_base_ancestors=ancestors,
    )
    assert f"history: sanitized base {missing} is not an ancestor of HEAD" in findings


def test_ci_runs_on_pull_request_head() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "github.event.pull_request.head.sha" in workflow
