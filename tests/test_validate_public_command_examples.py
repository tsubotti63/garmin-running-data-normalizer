from __future__ import annotations

import shutil
from pathlib import Path

from scripts.validate_public_command_examples import PUBLIC_DOCUMENTS, validate


ROOT = Path(__file__).resolve().parents[1]


def _copy_validator_inputs(destination: Path) -> None:
    for relative in (
        *PUBLIC_DOCUMENTS,
        "pyproject.toml",
        "src/garmin_running_data_normalizer/__init__.py",
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_repository_public_command_examples_pass() -> None:
    assert validate(ROOT) == []


def test_missing_windows_section_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("Windows PowerShell", "Windows"),
        encoding="utf-8",
    )

    assert "README.md: Windows PowerShell section is missing" in validate(tmp_path)


def test_missing_conditional_dependency_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            '"tzdata; platform_system == \'Windows\'",', ""
        ),
        encoding="utf-8",
    )

    assert (
        "pyproject.toml: Windows conditional tzdata dependency is missing"
        in validate(tmp_path)
    )


def test_py_launcher_only_windows_setup_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "python -m venv .venv", "py -3.11 -m venv .venv", 1
        ),
        encoding="utf-8",
    )

    assert (
        "README.md: Windows setup must use python -m venv .venv"
        in validate(tmp_path)
    )


def test_windows_runtime_instructions_reject_git_source_acquisition(
    tmp_path: Path,
) -> None:
    _copy_validator_inputs(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "```powershell\nSet-Location",
            "```powershell\ngit clone https://example.invalid/project.git\nSet-Location",
            1,
        ),
        encoding="utf-8",
    )

    assert (
        "README.md: Windows runtime instructions must not perform Git source acquisition"
        in validate(tmp_path)
    )


def test_obsolete_windows_workaround_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + "\nTemporary workaround: `python -m pip install tzdata`.\n",
        encoding="utf-8",
    )

    assert (
        "README.md: obsolete v1.2.0 Windows workaround or pending-patch wording remains"
        in validate(tmp_path)
    )


def test_stale_stable_version_fails(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    quick_start = tmp_path / "docs/product_quick_start.md"
    quick_start.write_text(
        quick_start.read_text(encoding="utf-8").replace("1.3.0", "9.9.9"),
        encoding="utf-8",
    )

    assert (
        "docs/product_quick_start.md: current stable v1.3.0 is not identified"
        in validate(tmp_path)
    )
