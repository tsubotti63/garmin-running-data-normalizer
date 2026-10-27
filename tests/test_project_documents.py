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


def test_the_project_documents_name_the_view_page_that_does_not_interpret() -> None:
    # Stage G4 of v2.1.0: the boundary and the charter, whose text the Human
    # maintainer decides, name the view page and the series command, which
    # show the numbers of an output without interpreting them; principle 5 of
    # the design puts the view page in the next tab (decision 20261026-11).
    boundary = flowing("docs/project/project_boundary.md")
    # The item of the autonomous scope, apart from the sentence of the
    # external systems, which names the view page as well.
    assert (
        "- The view page of v2.1.0, described in [v2.0.0 GUI Design](../gui_design.md#the-view-page-v210): "
        "a second page of the same local GUI"
    ) in boundary
    assert "shows its numbers as charts and tables, without interpreting them" in boundary
    assert "the `series` command of the CLI" in boundary
    assert "The view page of v2.1.0 is served in the same way and sends nothing either." in boundary
    charter = flowing("docs/project/project_charter.md")
    assert "From v2.1.0, the GUI also has a view page in the next tab" in charter
    assert "on the same machine and without interpreting them" in charter
    design = flowing("docs/gui_design.md")
    assert "Since v2.1.0, the view page is a second page in the next tab" in design


def test_a_release_candidate_sends_its_readers_to_the_stable_release() -> None:
    # v2.0.1 F4: while the source is a release candidate, the README names it
    # as a test version on TestPyPI, after the stable release and how to
    # install it, so that a reader of the stable release does not install the
    # candidate by mistake (the checker, 2026-10-24); the Japanese entry says
    # so too.
    from garmin_running_data_normalizer import __version__
    from scripts.validate_public_product_state import CURRENT_STABLE_VERSION

    if __version__ == CURRENT_STABLE_VERSION:
        return
    readme = flowing("README.md")
    stable = readme.index(f"Current stable release: **v{CURRENT_STABLE_VERSION}**")
    candidate = readme.index(f"Implementation candidate: **v{__version__}**")
    assert stable < candidate
    assert readme.index("### Try it") < candidate
    assert f"for normal use, install the stable release v{CURRENT_STABLE_VERSION}" in readme
    assert f"The release candidate v{__version__} is a test version" in readme
    japanese = flowing("README.ja.md")
    # Before the publication, it is for TestPyPI; after it, published there.
    assert (
        f"試しのバージョン **v{__version__}** は TestPyPI 向け" in japanese
        or f"試しのバージョン **v{__version__}** を TestPyPI に公開しました" in japanese
    )
    assert "ふつうは、上の安定版を入れてください" in japanese
