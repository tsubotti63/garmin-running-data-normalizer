from __future__ import annotations

import shutil
from pathlib import Path

from garmin_running_data_normalizer import __version__
from scripts.validate_public_command_examples import PUBLIC_DOCUMENTS, validate
from scripts.validate_public_product_state import CURRENT_STABLE_VERSION


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
        quick_start.read_text(encoding="utf-8").replace("v2.1.0", "v9.9.9"),
        encoding="utf-8",
    )

    assert (
        "docs/product_quick_start.md: current stable v2.1.0 is not identified"
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


# A release candidate after this release, which is installed from TestPyPI
# (stage D2); the stable release is installed from Production PyPI only
# (stage E2b).
CANDIDATE = "2.1.1rc1"


def _as_candidate(root: Path) -> None:
    init = root / "src/garmin_running_data_normalizer/__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace(f'__version__ = "{__version__}"', f'__version__ = "{CANDIDATE}"'),
        encoding="utf-8",
    )
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + f"\nImplementation candidate: **v{CANDIDATE}**\n",
        encoding="utf-8",
    )
    assert validate(root) == []


def _as_stable(root: Path) -> None:
    # The source as the stable release that is published, whatever version
    # it has now (v2.0.1 F4): its version, and a README that has no release
    # candidate to install from TestPyPI.
    init = root / "src/garmin_running_data_normalizer/__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace(
            f'__version__ = "{__version__}"', f'__version__ = "{CURRENT_STABLE_VERSION}"'
        ),
        encoding="utf-8",
    )
    readme = root / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines()
    readme.write_text("\n".join(line for line in lines if "test.pypi.org" not in line) + "\n", encoding="utf-8")
    assert validate(root) == []


def test_the_stable_release_is_not_installed_from_testpypi(tmp_path: Path) -> None:
    _copy_validator_inputs(tmp_path)
    _as_stable(tmp_path)
    _add_install_line(
        tmp_path,
        "docs/gui_guide.md",
        "python -m pip install --index-url https://test.pypi.org/simple/ "
        f"--extra-index-url https://pypi.org/simple/ garmin-running-data-normalizer=={CURRENT_STABLE_VERSION}",
    )

    assert validate(tmp_path) == [
        f"docs/gui_guide.md: the stable release {CURRENT_STABLE_VERSION} installs from Production PyPI, not TestPyPI"
    ]


def test_a_testpypi_install_takes_its_dependencies_from_production_pypi(tmp_path: Path) -> None:
    # Stage D2: TestPyPI may not provide a dependency, such as tzdata on
    # Windows, so Production PyPI is the extra index.
    _copy_validator_inputs(tmp_path)
    _as_candidate(tmp_path)
    _add_install_line(
        tmp_path,
        "docs/gui_guide.md",
        "python -m pip install --index-url https://test.pypi.org/simple/ "
        f"garmin-running-data-normalizer=={CANDIDATE}",
    )

    assert validate(tmp_path) == [
        "docs/gui_guide.md: TestPyPI install does not take its dependencies from Production PyPI"
    ]


def test_a_testpypi_install_names_the_package_version(tmp_path: Path) -> None:
    # Without the exact version, the stable release on Production PyPI is
    # installed instead of the release candidate.
    _copy_validator_inputs(tmp_path)
    _as_candidate(tmp_path)
    for name in ("garmin-running-data-normalizer", "garmin-running-data-normalizer==0.0.0"):
        _add_install_line(
            tmp_path,
            "README.md",
            "python -m pip install --index-url https://test.pypi.org/simple/ "
            f"--extra-index-url https://pypi.org/simple/ {name}",
        )

    assert validate(tmp_path) == [
        f"README.md: TestPyPI install does not name the package version {CANDIDATE}"
    ] * 2


def test_getting_started_gives_series_in_windows_powershell(tmp_path: Path) -> None:
    # v2.1.0 G6a: Getting Started gives the series command of v2.1.0 in
    # Windows PowerShell, as it gives run-all, validate-handoff, and snapshot.
    _copy_validator_inputs(tmp_path)
    guide = tmp_path / "docs/getting_started_from_garmin_export.md"
    text = guide.read_text(encoding="utf-8")
    start = text.index("```powershell\n.\\.venv\\Scripts\\python.exe -m garmin_running_data_normalizer series ")
    end = text.index("```", start + 3) + 3
    guide.write_text(text[:start] + text[end:], encoding="utf-8")

    assert validate(tmp_path) == [
        "docs/getting_started_from_garmin_export.md: PowerShell series example is missing"
    ]


def test_a_testpypi_install_may_end_a_statement_of_windows_powershell(tmp_path: Path) -> None:
    # Stage E1i: in the line of Windows PowerShell, the next part follows the
    # install after ";", inside an "if" of its own; the version must still be
    # the exact one.
    _copy_validator_inputs(tmp_path)
    _as_candidate(tmp_path)
    install = "python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/"
    _add_install_line(tmp_path, "README.md", f"{install} garmin-running-data-normalizer=={CANDIDATE}; if ($?) {{ gui }}")
    assert validate(tmp_path) == []
    _add_install_line(tmp_path, "README.md", f"{install} garmin-running-data-normalizer=={CANDIDATE}0; if ($?) {{ gui }}")
    assert validate(tmp_path) == [f"README.md: TestPyPI install does not name the package version {CANDIDATE}"]
