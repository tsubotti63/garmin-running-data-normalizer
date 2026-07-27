from __future__ import annotations

import shutil
from pathlib import Path

from scripts.validate_public_command_examples import PUBLIC_DOCUMENTS, validate


ROOT = Path(__file__).resolve().parents[1]


def _copy_validator_inputs(destination: Path) -> None:
    for relative in (*PUBLIC_DOCUMENTS, "pyproject.toml"):
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
