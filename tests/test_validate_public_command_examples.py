from __future__ import annotations

import shutil
from pathlib import Path

from garmin_running_data_normalizer import __version__
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
        quick_start.read_text(encoding="utf-8").replace("v1.7.1", "v9.9.9"),
        encoding="utf-8",
    )

    assert (
        "docs/product_quick_start.md: current stable v1.7.1 is not identified"
        in validate(tmp_path)
    )


def test_the_gui_guides_are_checked_as_public_documents(tmp_path: Path) -> None:
    # Stage D2: a PowerShell example in a guide of the GUI follows the rules
    # of the other public documents.
    _copy_validator_inputs(tmp_path)
    for relative in ("docs/gui_guide.md", "docs/gui_guide.ja.md"):
        guide = tmp_path / relative
        guide.write_text(
            guide.read_text(encoding="utf-8")
            + "\n```powershell\ngarmin-running-data-normalizer gui `\n  --no-browser \\\n```\n",
            encoding="utf-8",
        )
        assert f"{relative}: PowerShell block uses Bash continuation" in validate(tmp_path)


def _add_install_line(root: Path, relative: str, line: str) -> None:
    document = root / relative
    document.write_text(
        document.read_text(encoding="utf-8") + f"\n```bash\n{line}\n```\n",
        encoding="utf-8",
    )


def test_a_testpypi_install_takes_its_dependencies_from_production_pypi(tmp_path: Path) -> None:
    # Stage D2: TestPyPI may not provide a dependency, such as tzdata on
    # Windows, so Production PyPI is the extra index.
    _copy_validator_inputs(tmp_path)
    _add_install_line(
        tmp_path,
        "docs/gui_guide.md",
        "python -m pip install --index-url https://test.pypi.org/simple/ "
        f"garmin-running-data-normalizer=={__version__}",
    )

    assert validate(tmp_path) == [
        "docs/gui_guide.md: TestPyPI install does not take its dependencies from Production PyPI"
    ]


def test_a_testpypi_install_names_the_package_version(tmp_path: Path) -> None:
    # Without the exact version, the stable release on Production PyPI is
    # installed instead of the release candidate.
    _copy_validator_inputs(tmp_path)
    for name in ("garmin-running-data-normalizer", "garmin-running-data-normalizer==0.0.0"):
        _add_install_line(
            tmp_path,
            "README.md",
            "python -m pip install --index-url https://test.pypi.org/simple/ "
            f"--extra-index-url https://pypi.org/simple/ {name}",
        )

    assert validate(tmp_path) == [
        f"README.md: TestPyPI install does not name the package version {__version__}"
    ] * 2
