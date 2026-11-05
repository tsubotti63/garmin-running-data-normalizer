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


def test_the_stable_release_keeps_no_paragraph_of_a_candidate() -> None:
    # v2.2.0 K6a (the checker's opinion on the partial guard of K6a): the tests
    # of a release candidate here return early for the stable release, so the
    # stable release checks that the README and its Japanese entry keep no
    # paragraph of a release candidate and no line that installs from TestPyPI.
    from garmin_running_data_normalizer import __version__
    from scripts.validate_public_product_state import CURRENT_STABLE_VERSION

    if __version__ != CURRENT_STABLE_VERSION:
        return
    readme = flowing("README.md")
    japanese = flowing("README.ja.md")
    for text in (readme, japanese):
        assert "test.pypi.org" not in text
        assert "TestPyPI" not in text
    assert "Implementation candidate" not in readme
    assert "試しのバージョン" not in japanese


def test_the_lines_that_install_a_version_install_the_current_stable_release() -> None:
    # v2.2.0 K6a (the checker's opinion A on the second run of the partial
    # guard of K6a): the lines of the READMEs, the guides, Getting Started,
    # and the Quick Start that install a version of this app install the
    # current stable release, so that a user is not given an earlier one; the
    # history of the migration notes is not read. While the source is a
    # release candidate, the README installs that candidate from TestPyPI too
    # (stage K4), and only its line is left out: any other candidate is wrong
    # (Codex's review of the diff of K6a). The whole version is read, up to a
    # space, a mark of Markdown, or the end of a statement, so that 2.2.0-rc2
    # or 2.2.0+local is never read as 2.2.0 (its second review).
    import re

    from garmin_running_data_normalizer import __version__
    from scripts.validate_public_product_state import CURRENT_STABLE_VERSION

    found = []
    for name in (
        "README.md",
        "README.ja.md",
        "docs/gui_guide.md",
        "docs/gui_guide.ja.md",
        "docs/getting_started_from_garmin_export.md",
        "docs/product_quick_start.md",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        for version in re.findall(r"garmin-running-data-normalizer==([^\s`'\"<>()\[\]{}|,;&]+)", text):
            version = version.rstrip(".")
            if version == __version__ and version != CURRENT_STABLE_VERSION:
                continue
            found.append((name, version))
    assert found
    assert [item for item in found if item[1] != CURRENT_STABLE_VERSION] == []


def test_the_readme_says_which_release_candidate_it_is() -> None:
    # v2.2.0 K4d: the paragraph of the candidate says which release candidate
    # of its version it is ("the first", "the second"), as the number after rc
    # does, so that the words of one candidate cannot stay in the next one
    # (Codex's objection 2 to the plan of 2.2.0rc2). It names the ordinals up
    # to the tenth, and says so for a later one (Codex's review of the diff).
    import re

    from garmin_running_data_normalizer import __version__
    from scripts.validate_public_product_state import CURRENT_STABLE_VERSION

    if __version__ == CURRENT_STABLE_VERSION:
        return
    match = re.fullmatch(r"(\d+\.\d+\.\d+)rc(\d+)", __version__)
    assert match, __version__
    ordinals = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth")
    number = int(match.group(2))
    assert 1 <= number <= len(ordinals), f"name the ordinal of rc{number} in this test"
    ordinal = ordinals[number - 1]
    assert f"**v{__version__}** (the {ordinal} release candidate of v{match.group(1)}," in flowing("README.md")


def test_a_release_candidate_says_how_to_try_it_beside_the_stable_release() -> None:
    # v2.2.0 K4a: while the source is a release candidate, the README and the
    # Japanese entry say how to try it once it is published (a virtual
    # environment of its own, started by its Python, no icon; the Japanese
    # entry by a link, since it stays short), what the two
    # versions share and what each one's Forget removes, and how far the
    # candidate is the same as the stable release (the checker's reviews and
    # Codex's objections 3, 6, 7, and 8 to the plan of K4).
    from garmin_running_data_normalizer import __version__
    from scripts.validate_public_product_state import CURRENT_STABLE_VERSION as stable

    if __version__ == stable:
        return
    rc = __version__
    mac = (
        "python3 -m venv ~/garmin-normalizer-rc && ~/garmin-normalizer-rc/bin/python -m pip install "
        "--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "
        f"garmin-running-data-normalizer=={rc} && ~/garmin-normalizer-rc/bin/python -m garmin_running_data_normalizer gui"
    )
    windows = (
        'py -m venv "$HOME\\garmin-normalizer-rc"; if ($?) { & "$HOME\\garmin-normalizer-rc\\Scripts\\python.exe" -m pip '
        "install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "
        f'garmin-running-data-normalizer=={rc}; if ($?) {{ & "$HOME\\garmin-normalizer-rc\\Scripts\\python.exe" '
        "-m garmin_running_data_normalizer gui } }"
    )
    readme = flowing("README.md")
    japanese = flowing("README.ja.md")
    # The Japanese entry, which stays short, gives the lines by a link to
    # Install of the README.
    assert mac in readme and windows in readme
    for name in ("README.md", "README.ja.md"):
        lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
        assert not [line for line in lines if "garmin-normalizer-rc" in line and "--create-shortcut" in line], name
    for sentence in (
        f"for the same input, timezone, and options, the normalization, its outputs, and the Snapshot Store are those of v{stable}.",
        "make no icon from this environment: those lines work on `garmin-normalizer`,",
        "Both versions use one settings file, `gui-settings.json` in the folder `garmin-running-data-normalizer`",
        "The lines give Production PyPI too, so that pip finds the dependencies that TestPyPI may not provide, "
        "such as `tzdata` on Windows; pip looks for each package on both.",
        f"To keep the settings of v{stable} as they are, copy the file before you try it, and put it back with both GUIs "
        "stopped; do not open the two GUIs at the same time.",
    ):
        assert sentence in readme, sentence
    # The settings file of format 2 and the marks are new in 2.2.0, so that
    # only a candidate of 2.2.0 says what v2.1.0 does with them; a later
    # candidate that keeps the format says otherwise (Codex's review of the
    # diff of K6a).
    first_of_format_2 = rc.startswith("2.2.0rc")
    for sentence in (
        f"Once v{rc} saves its settings, v{stable} does not use them and starts as at a first launch, without writing over them; "
        f"v{rc} also remembers the timezone of the last run that made an output.",
        f"**Forget the remembered settings…** of v{stable} removes that file, with what v{rc} remembered; that of v{rc} "
        "also removes the marks, which cannot be restored. Neither removes the Snapshot Store or the outputs.",
    ) if first_of_format_2 else ():
        assert sentence in readme, sentence
    for sentence in (
        f"同じ入力・タイムゾーン・オプションなら、正規化・出力・保管場所は v{stable} と同じです。",
        "この環境からアイコンも作らないで",
        "その 1 行 （Mac と Windows PowerShell）は、英語の README の [Install](README.md#install) にあります。",
        "2 つのバージョンは、設定のファイルを 1 つ使います",
        # The file to copy, and where the guide says it is (Codex's review
        # of the diff of W6a).
        "[2 回目からの起動](docs/gui_guide.ja.md#2-回目からの起動)にある `gui-settings.json`",
        "保管場所と出力は消しません。",
        f"v{stable} の設定を残したいときは、試す前にそのファイルの写しを取り、",
        "2 つの GUI を止めてから戻してください。2 つの GUI を同時に開かないでください。",
    ):
        assert sentence in japanese, sentence
    for sentence in (
        f"v{rc} が設定を保存すると、v{stable} はその設定を使わず、初めての起動のように始まります。",
        f"上書きはしません。v{rc} は、出力を作れた最後の正規化のタイムゾーンも覚えます。",
        f"v{stable} の「覚えた設定を消す…」はそのファイルを消し、v{rc} が覚えたものも消えます。",
        f"v{rc} のものは見るページの印も消し、印は元に戻せません。",
    ) if first_of_format_2 else ():
        assert sentence in japanese, sentence
    # A later candidate, of the same form of settings, says instead that each
    # version reads what the other saves, that it does not open an output of
    # the stable release, and to copy the marks too (stage W6a of v2.2.1,
    # Codex's objection 7 to the plan of W6).
    for sentence in (
        "in the same form: each version reads what the other saves.",
        f"v{rc} does not open an output that v{stable} made, as no version opens the output of another:",
        "Copy `gui-marks.json` too to keep the marks.",
    ) if not first_of_format_2 else ():
        assert sentence in readme, sentence
    for sentence in (
        f"v{rc} は v{stable} の出力を開きません。",
        "印も残すなら `gui-marks.json` の写しも取ってください。",
    ) if not first_of_format_2 else ():
        assert sentence in japanese, sentence
    # Forget removes the half-written files of a write from 2.2.1 (stage W4),
    # on Windows only those ten minutes old, so that only a candidate of 2.2.1
    # says so beside v2.2.0 (Codex's review of the diff of W6a).
    first_with_temporaries = rc.startswith("2.2.1rc")
    for sentence in (
        f"that of v{rc} also removes the half-written files that a write leaves when the app stops in the middle of it "
        "(on Windows, once they are ten minutes old).",
    ) if first_with_temporaries else ():
        assert sentence in readme, sentence
    for sentence in (
        f"v{rc} のものは、落ちたときに残る書きかけのファイルも消します（Windows では 10 分たってから）。",
    ) if first_with_temporaries else ():
        assert sentence in japanese, sentence


def test_the_readme_says_whether_the_candidate_is_published_as_the_contract_does() -> None:
    # v2.2.0 K4c: the output contract marks the candidate "(not published)"
    # until its publication and "(TestPyPI only)" after it, and the README and
    # its Japanese entry say the same, so that the record of the publication
    # leaves none of the words of before (Codex's objection 13 to the plan of
    # K4: the public checks pass with either mark).
    from garmin_running_data_normalizer import __version__
    from scripts.validate_public_product_state import CURRENT_STABLE_VERSION

    rc = __version__
    if rc == CURRENT_STABLE_VERSION:
        return
    contract = (ROOT / "docs/output_contract.md").read_text(encoding="utf-8")
    published = f"- Implementation candidate: v{rc} (TestPyPI only)" in contract
    assert published or f"- Implementation candidate: v{rc} (not published)" in contract
    before = {
        "README.md": (
            "for TestPyPI; Production PyPI",
            "says how to try it once it is published.",
            "Once it is published on TestPyPI, install it",
        ),
        "README.ja.md": (
            f"試しのバージョン **v{rc}** は TestPyPI 向け",
            f"試しのバージョン v{rc} は、TestPyPI に公開したあとに入れられます。",
        ),
    }
    after = {
        "README.md": (
            "published on TestPyPI; Production PyPI",
            "**Install** below says how to try it.",
            "It is published on TestPyPI. Install it",
        ),
        "README.ja.md": (
            f"試しのバージョン **v{rc}** を TestPyPI に公開しました。",
            f"試しのバージョン v{rc} は、TestPyPI から入れられます。",
        ),
    }
    for name in ("README.md", "README.ja.md"):
        text = flowing(name)
        for words in (after if published else before)[name]:
            assert words in text, (name, words)
        for words in (before if published else after)[name]:
            assert words not in text, (name, words)
