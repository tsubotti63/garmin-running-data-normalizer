from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.validate_public_product_state import (
    DOCUMENTATION_PROBLEM_FORM,
    SYNTHETIC_VALIDATION_FORM,
    CS010_DOCUMENT,
    current_documents,
    validate,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION_SOURCE = "src/garmin_running_data_normalizer/__init__.py"


def _copy_validator_inputs(destination: Path) -> None:
    for relative in (*current_documents("1.4.0"), VERSION_SOURCE):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_repository_public_product_state_passes() -> None:
    version, findings = validate(ROOT)

    assert version == "1.4.0"
    assert findings == []


def test_obsolete_support_windows_state_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    support = tmp_path / "SUPPORT.md"
    support.write_text(
        support.read_text(encoding="utf-8")
        + "\nWindows is an intended supported platform with public validation in progress.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("public validation in progress" in item for item in findings)


def test_obsolete_support_windows_faq_anchor_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    support = tmp_path / "SUPPORT.md"
    support.write_text(
        support.read_text(encoding="utf-8").replace(
            "#was-the-v120-windows-timezone-data-issue-resolved",
            "#why-does-stable-v120-fail-with-activities_normalization_failed-on-windows",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("was-the-v120-windows-timezone-data-issue-resolved" in item for item in findings)


def test_fixed_bug_form_version_placeholder_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    bug_form = tmp_path / ".github/ISSUE_TEMPLATE/bug_report.yml"
    bug_form.write_text(
        bug_form.read_text(encoding="utf-8").replace(
            'placeholder: "Paste the exact output of garmin-running-data-normalizer --version"',
            'placeholder: "1.2.0"',
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("placeholder must be version-independent" in item for item in findings)


def test_current_fixed_bug_form_version_placeholder_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    bug_form = tmp_path / ".github/ISSUE_TEMPLATE/bug_report.yml"
    bug_form.write_text(
        bug_form.read_text(encoding="utf-8").replace(
            'placeholder: "Paste the exact output of garmin-running-data-normalizer --version"',
            'placeholder: "Example: 1.3.1"',
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("placeholder must be version-independent" in item for item in findings)


def test_bug_form_without_exact_version_output_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    bug_form = tmp_path / ".github/ISSUE_TEMPLATE/bug_report.yml"
    text = bug_form.read_text(encoding="utf-8").replace(
        "Paste the exact output of garmin-running-data-normalizer --version",
        "Enter the package version",
    )
    bug_form.write_text(
        text
        + "\n# Paste the exact output of garmin-running-data-normalizer --version\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("--version" in item for item in findings)


def test_bug_form_without_public_safe_boundaries_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    bug_form = tmp_path / ".github/ISSUE_TEMPLATE/bug_report.yml"
    bug_form.write_text(
        bug_form.read_text(encoding="utf-8")
        .replace(
            "Do not upload files or paste real Garmin data.",
            "Use a minimal reproduction.",
        )
        .replace(
            "account identifiers, stable keys, source filenames, private paths, hashes, and personal metrics",
            "private values",
        )
        .replace(
            "This report does not publicly disclose a suspected vulnerability or sensitive security detail.",
            "This report is ready to submit.",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("real Garmin data" in item for item in findings)
    assert any("account identifiers" in item for item in findings)
    assert any("sensitive security detail" in item for item in findings)


def test_synthetic_validation_form_without_privacy_confirmation_fails(
    tmp_path: Path,
) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / SYNTHETIC_VALIDATION_FORM
    form.write_text(
        form.read_text(encoding="utf-8").replace(
            "I confirm that this report does not contain real Garmin data, personal health data, account identifiers, local private paths, raw exports, private screenshots, or other sensitive information.",
            "I confirm that this report is complete.",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any(
        SYNTHETIC_VALIDATION_FORM in item and "real Garmin data" in item
        for item in findings
    )


def test_synthetic_validation_form_that_encourages_real_data_fails(
    tmp_path: Path,
) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / SYNTHETIC_VALIDATION_FORM
    form.write_text(
        form.read_text(encoding="utf-8").replace(
            "screenshots containing private metrics.**",
            "screenshots containing private metrics.**\n\n"
            "        Attach real Garmin data to help us investigate.",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("encourages public sharing of private data" in item for item in findings)


def test_synthetic_only_confirmation_must_be_required(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / SYNTHETIC_VALIDATION_FORM
    text = form.read_text(encoding="utf-8")
    marker = (
        "- label: I used only the documented Synthetic / fictional workflow for this report.\n"
        "          required: true"
    )
    form.write_text(
        text.replace(marker, marker.replace("required: true", "required: false")),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("required confirmation is missing or optional" in item for item in findings)


def test_synthetic_environment_field_must_be_required(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / SYNTHETIC_VALIDATION_FORM
    text = form.read_text(encoding="utf-8")
    field = (
        "  - type: dropdown\n"
        "    id: install_source\n"
        "    attributes:\n"
        "      label: Install source\n"
        "      options:\n"
        "        - PyPI\n"
        "        - Source checkout\n"
        "        - Other\n"
        "    validations:\n"
        "      required: true"
    )
    form.write_text(
        text.replace(field, field.replace("required: true", "required: false")),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("required field is optional: install_source" in item for item in findings)


def test_documentation_problem_form_without_bug_routing_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / DOCUMENTATION_PROBLEM_FORM
    form.write_text(
        form.read_text(encoding="utf-8").replace(
            "issues/new?template=bug_report.yml",
            "issues",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any(
        DOCUMENTATION_PROBLEM_FORM in item and "bug_report.yml" in item
        for item in findings
    )


def test_documentation_privacy_confirmation_must_be_required(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / DOCUMENTATION_PROBLEM_FORM
    text = form.read_text(encoding="utf-8")
    marker = (
        "- label: I confirm that this report does not contain real Garmin data, personal health data, account identifiers, local private paths, or other sensitive information.\n"
        "          required: true"
    )
    form.write_text(
        text.replace(marker, marker.replace("required: true", "required: false")),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("required confirmation is missing or optional" in item for item in findings)


@pytest.mark.parametrize(
    "form_path", (SYNTHETIC_VALIDATION_FORM, DOCUMENTATION_PROBLEM_FORM)
)
def test_feedback_form_fixed_version_placeholder_fails(
    tmp_path: Path, form_path: str
) -> None:
    _copy_validator_inputs(tmp_path)
    form = tmp_path / form_path
    form.write_text(
        form.read_text(encoding="utf-8").replace(
            'placeholder: "Paste the exact output of garmin-running-data-normalizer --version"',
            'placeholder: "Version 1.3.3"',
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any(
        form_path in item and "placeholder must be version-independent" in item
        for item in findings
    )


def test_readme_without_synthetic_validation_cta_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "issues/new?template=synthetic_validation_report.yml",
            "issues",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("README.md" in item and "synthetic_validation_report.yml" in item for item in findings)


def test_package_version_drift_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    version_source = tmp_path / VERSION_SOURCE
    version_source.write_text(
        version_source.read_text(encoding="utf-8").replace('"1.4.0"', '"1.4.1"'),
        encoding="utf-8",
    )

    version, findings = validate(tmp_path)

    assert version == "1.4.1"
    assert any(
        "implementation candidate marker is missing" in item
        for item in findings
    )


def test_obsolete_architecture_state_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    architecture = tmp_path / "docs/architecture_overview.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8")
        + "\nDeferred: a final Run-All command.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("Deferred: a final Run-All command" in item for item in findings)


def test_obsolete_sleep_boundary_fails_across_line_breaks(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    quick_start = tmp_path / "docs/product_quick_start.md"
    quick_start.write_text(
        quick_start.read_text(encoding="utf-8")
        + "\nLibrary-level `sleepData.json` normalization is implemented separately and\n"
        + "does not change the Run-All output contract.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("sleepData.json" in item for item in findings)


def test_unreleased_relationship_heading_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    relationships = tmp_path / "docs/dataset_relationships.md"
    relationships.write_text(
        relationships.read_text(encoding="utf-8").replace(
            "## Stable v1.3 context and observation catalog",
            "## Unreleased v1.3 context and observation catalog",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("Unreleased v1.3" in item for item in findings)


def test_missing_output_contract_marker_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    output_contract = tmp_path / "docs/output_contract.md"
    output_contract.write_text(
        output_contract.read_text(encoding="utf-8").replace(
            "- Compatibility family: stable 1.x",
            "- Compatibility family: unspecified",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("Compatibility family: stable 1.x" in item for item in findings)


@pytest.mark.parametrize(
    ("status", "expected_exit", "incorrect_exit"),
    (
        ("PASS", 0, 3),
        ("PASS_WITH_WARNINGS", 0, 3),
        ("PARTIAL_SUCCESS", 3, 0),
        ("Fatal error", 2, 0),
    ),
)
def test_status_exit_contract_table_drift_fails(
    tmp_path: Path,
    status: str,
    expected_exit: int,
    incorrect_exit: int,
) -> None:
    _copy_validator_inputs(tmp_path)
    output_contract = tmp_path / "docs/output_contract.md"
    correct_row = f"| `{status}` | {expected_exit} |" if status != "Fatal error" else f"| {status} | {expected_exit} |"
    incorrect_row = f"| `{status}` | {incorrect_exit} |" if status != "Fatal error" else f"| {status} | {incorrect_exit} |"
    output_contract.write_text(
        output_contract.read_text(encoding="utf-8").replace(
            correct_row,
            incorrect_row,
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any(correct_row in item for item in findings)


@pytest.mark.parametrize(
    ("status", "expected_exit", "incorrect_exit"),
    (
        ("PASS", 0, 3),
        ("PASS_WITH_WARNINGS", 0, 3),
        ("PARTIAL_SUCCESS", 3, 0),
        ("Fatal error", 2, 0),
    ),
)
@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("separator", ("/", "→", "->", ":", "="))
def test_contradictory_status_exit_pair_in_current_document_fails(
    tmp_path: Path,
    status: str,
    expected_exit: int,
    incorrect_exit: int,
    reverse: bool,
    separator: str,
) -> None:
    _copy_validator_inputs(tmp_path)
    readme = tmp_path / "README.md"
    contradiction = (
        f"exit {incorrect_exit} {separator} `{status}`"
        if reverse
        else f"`{status}` {separator} exit {incorrect_exit}"
    )
    readme.write_text(
        readme.read_text(encoding="utf-8") + f"\n{contradiction}\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any(
        f"{status} requires exit {expected_exit}, not exit {incorrect_exit}" in item
        for item in findings
    )


def test_partial_success_exit_zero_in_current_release_notes_fails(
    tmp_path: Path,
) -> None:
    _copy_validator_inputs(tmp_path)
    release_notes = tmp_path / "docs/release_notes/v1.4.0.md"
    release_notes.write_text(
        release_notes.read_text(encoding="utf-8").replace(
            "`PARTIAL_SUCCESS` / exit 3",
            "`PARTIAL_SUCCESS` / exit 0",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("PARTIAL_SUCCESS requires exit 3, not exit 0" in item for item in findings)


def test_partial_success_exit_zero_in_faq_table_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    faq = tmp_path / "docs/faq.md"
    correct_row = (
        "| `3` | `PARTIAL_SUCCESS` because detected FIT is auditably incomplete |"
    )
    faq.write_text(
        faq.read_text(encoding="utf-8").replace(
            correct_row,
            "| `0` | `PARTIAL_SUCCESS` because detected FIT is auditably incomplete |",
        ),
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any(correct_row in item for item in findings)


def test_candidate_marker_follows_package_version(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    version_source = tmp_path / VERSION_SOURCE
    version_source.write_text(
        version_source.read_text(encoding="utf-8").replace('"1.4.0"', '"1.4.1"'),
        encoding="utf-8",
    )

    version, findings = validate(tmp_path)

    assert version == "1.4.1"
    assert any(
        "implementation candidate marker is missing"
        in item
        for item in findings
    )


def test_obsolete_agents_phase_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8")
        + "\nPhase 0.1 — Platform alignment and safe local reuse\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("Phase 0.1" in item for item in findings)


def test_current_cs010_public_case_study_passes() -> None:
    version, findings = validate(ROOT)

    assert version == "1.4.0"
    assert not any(CS010_DOCUMENT in item for item in findings)


def test_general_review_word_in_cs010_passes(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    case_study = tmp_path / CS010_DOCUMENT
    case_study.write_text(
        case_study.read_text(encoding="utf-8")
        + "\nThe review process is described as historical context.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert not any("stale public pre-publication status" in item for item in findings)


def test_historical_branch_word_in_cs010_passes(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    case_study = tmp_path / CS010_DOCUMENT
    case_study.write_text(
        case_study.read_text(encoding="utf-8")
        + "\nHistorical branch names are retained only for context.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert not any("stale public pre-publication status" in item for item in findings)


def test_cs010_draft_candidate_phrase_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    case_study = tmp_path / CS010_DOCUMENT
    case_study.write_text(
        case_study.read_text(encoding="utf-8")
        + "\nThis draft is a candidate for Product review.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("stale public pre-publication status" in item for item in findings)


def test_cs010_review_branch_merge_phrase_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    case_study = tmp_path / CS010_DOCUMENT
    case_study.write_text(
        case_study.read_text(encoding="utf-8")
        + "\nThe presence on a review branch does not authorize merge.\n",
        encoding="utf-8",
    )

    _, findings = validate(tmp_path)

    assert any("stale public pre-publication status" in item for item in findings)
