"""The project documents say what the stable release has (stage E5)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_DOCUMENTS = (
    "docs/project/definition_of_done.md",
    "docs/project/project_charter.md",
    "docs/project/project_boundary.md",
)


def flowing(name: str) -> str:
    return " ".join((ROOT / name).read_text(encoding="utf-8").split())


def test_the_project_documents_do_not_call_the_gui_planned() -> None:
    # Stage E5, from an audit by Codex after the v2.0.0 publication: the GUI
    # is in v2.0.0, and the Definition of Done keeps the check by a person who
    # has not seen the GUI, with the exception that the Human maintainer
    # approved on 2026-10-20 (docs/gui_design.md, Testing).
    for name in PROJECT_DOCUMENTS:
        text = flowing(name)
        assert "planned v2.0.0" not in text, name
        assert "planned for v2.0.0" not in text, name
    done = flowing("docs/project/definition_of_done.md")
    assert "person who has not seen it before can select an Export and finish a normalization without instructions" in done
    assert "as the Human maintainer decided on 2026-10-20" in done
    assert "a person checks the GUI after v2.0.0 if one can be found" in done
    assert "Since v2.0.0, a local GUI is a second entry point to the same processing" in flowing(
        "docs/project/project_charter.md"
    )
