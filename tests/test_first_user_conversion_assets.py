from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.generate_first_user_conversion_assets import generate
from garmin_running_data_normalizer.standalone import StandaloneHandoffError


ROOT = Path(__file__).resolve().parents[1]
ASSET_NAMES = (
    "product-flow.svg",
    "synthetic-output-preview.svg",
    "synthetic-monthly-distance.svg",
)


def _build_synthetic_run_all(output: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "garmin_running_data_normalizer",
            "run-all",
            "--input",
            str(ROOT / "examples/synthetic/garmin_export"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "STATUS: PASS_WITH_WARNINGS" in completed.stdout


def test_generated_conversion_assets_are_deterministic_and_public_safe(
    tmp_path: Path,
) -> None:
    run_all_output = tmp_path / "run-all"
    first = tmp_path / "first"
    second = tmp_path / "second"
    analysis_csv = (
        ROOT / "examples/analysis/monthly_weekly_training_trends/input_sample.csv"
    )

    _build_synthetic_run_all(run_all_output)
    generate(run_all_output, analysis_csv, first)
    generate(run_all_output, analysis_csv, second)

    assert sorted(path.name for path in first.iterdir()) == sorted(ASSET_NAMES)
    for name in ASSET_NAMES:
        first_bytes = (first / name).read_bytes()
        assert first_bytes == (second / name).read_bytes()
        assert first_bytes == (
            ROOT / "docs/assets/first-user-conversion" / name
        ).read_bytes()
        text = first_bytes.decode("utf-8")
        root = ET.fromstring(text)
        assert root.attrib["role"] == "img"
        assert root.attrib["aria-labelledby"] == "title desc"
        assert root.find("{http://www.w3.org/2000/svg}title") is not None
        assert root.find("{http://www.w3.org/2000/svg}desc") is not None
        assert "Synthetic / fictional data" in text
        assert "<script" not in text
        assert "foreignObject" not in text
        assert "<image" not in text
        assert "/" + "Users/" not in text
        assert "@" not in text


def test_output_preview_uses_actual_synthetic_run_all_evidence(
    tmp_path: Path,
) -> None:
    run_all_output = tmp_path / "run-all"
    assets = tmp_path / "assets"
    _build_synthetic_run_all(run_all_output)

    generate(
        run_all_output,
        ROOT / "examples/analysis/monthly_weekly_training_trends/input_sample.csv",
        assets,
    )

    preview = (assets / "synthetic-output-preview.svg").read_text(encoding="utf-8")
    assert "PASS_WITH_WARNINGS" in preview
    assert "1 Activity record" in preview
    assert "3 warnings • 0 errors" in preview
    assert "17 dataset entries" in preview
    assert "44 generated files" in preview
    assert "START_HERE.md" in preview
    assert "DATASET_INVENTORY.md" in preview
    assert "ANALYSIS_HANDOFF.md" in preview
    root = ET.fromstring(preview)
    description = root.find("{http://www.w3.org/2000/svg}desc")
    assert description is not None
    assert "44 generated files" in (description.text or "")
    assert (
        "first-read order START_HERE.md, DATASET_INVENTORY.md, then "
        "ANALYSIS_HANDOFF.md"
    ) in (description.text or "")


def test_monthly_chart_uses_tracked_fictional_analysis_values(
    tmp_path: Path,
) -> None:
    run_all_output = tmp_path / "run-all"
    assets = tmp_path / "assets"
    _build_synthetic_run_all(run_all_output)

    generate(
        run_all_output,
        ROOT / "examples/analysis/monthly_weekly_training_trends/input_sample.csv",
        assets,
    )

    chart = (assets / "synthetic-monthly-distance.svg").read_text(encoding="utf-8")
    assert "2030-01" in chart
    assert "37.0 km" in chart
    assert "2030-02" in chart
    assert "47.0 km" in chart
    assert chart.count(">4 activities<") == 2


def test_readme_uses_stable_absolute_asset_urls() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    raw_base = (
        "https://raw.githubusercontent.com/tsubotti63/"
        "garmin-running-data-normalizer/main/docs/assets/first-user-conversion/"
    )

    for name in ASSET_NAMES:
        assert readme.count(raw_base + name) == 1
        assert readme.count(
            "https://github.com/tsubotti63/garmin-running-data-normalizer/"
            f"blob/main/docs/assets/first-user-conversion/{name}"
        ) == 1
    assert "Current stable release: **v1.3.1**" in readme
    assert "## Start here" in readme
    assert "### Who this is for" in readme
    assert "### What you get" in readme
    assert "### Try it" in readme
    assert "### See the result" in readme
    assert "one Activity record, three warnings, zero errors" in readme
    assert "four activities and 37.0 km" in readme
    assert "four activities and 47.0 km" in readme
    assert "Human review" in readme


def test_japanese_readme_remains_a_short_noncanonical_summary() -> None:
    readme = (ROOT / "README.ja.md").read_text(encoding="utf-8")

    assert len(readme) < 5_000
    assert not re.search(r"\bv\d+\.\d+\.\d+\b", readme)
    assert "|---" not in readme
    assert "英語の契約文書が正本です" in readme
    assert "[Supported Datasets](docs/supported_datasets.md)" in readme
    assert "[Run-All Output Contract](docs/output_contract.md)" in readme


def test_generator_rejects_an_unreviewed_analysis_csv(tmp_path: Path) -> None:
    run_all_output = tmp_path / "run-all"
    unreviewed_csv = tmp_path / "unreviewed.csv"
    _build_synthetic_run_all(run_all_output)
    unreviewed_csv.write_text(
        "activity_date_local,distance_m\n2030-01-01,9999\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError, match="does not match the reviewed fictional sample"
    ):
        generate(run_all_output, unreviewed_csv, tmp_path / "assets")


def test_generator_rejects_tampered_synthetic_handoff(tmp_path: Path) -> None:
    run_all_output = tmp_path / "run-all"
    _build_synthetic_run_all(run_all_output)
    summary_path = run_all_output / "run_summary.json"
    original = summary_path.read_bytes()
    summary = json.loads(original)

    summary["status"] = "REVIEW_BYPASSED"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(StandaloneHandoffError, match="status"):
        generate(
            run_all_output,
            ROOT / "examples/analysis/monthly_weekly_training_trends/input_sample.csv",
            tmp_path / "status-assets",
        )

    summary_path.write_bytes(original)
    summary = json.loads(original)
    summary["family_results"]["activities"]["record_count"] = 999
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="summary does not match"):
        generate(
            run_all_output,
            ROOT / "examples/analysis/monthly_weekly_training_trends/input_sample.csv",
            tmp_path / "count-assets",
        )
