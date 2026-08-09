from __future__ import annotations

import shutil
from pathlib import Path

from scripts.validate_public_product_state import CURRENT_DOCUMENTS, validate


ROOT = Path(__file__).resolve().parents[1]
VERSION_SOURCE = "src/garmin_running_data_normalizer/__init__.py"


def _copy_validator_inputs(destination: Path) -> None:
    for relative in (*CURRENT_DOCUMENTS, VERSION_SOURCE):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_repository_public_product_state_passes() -> None:
    version, findings = validate(ROOT)

    assert version == "1.3.1"
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


def test_package_version_drift_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    version_source = tmp_path / VERSION_SOURCE
    version_source.write_text(
        version_source.read_text(encoding="utf-8").replace('"1.3.1"', '"1.3.2"'),
        encoding="utf-8",
    )

    version, findings = validate(tmp_path)

    assert version == "1.3.2"
    assert any(
        "current stable marker does not match package v1.3.2" in item
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
