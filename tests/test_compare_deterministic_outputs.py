from __future__ import annotations

import json
from pathlib import Path

from scripts.compare_deterministic_outputs import compare_output_directories


def _write_output(root: Path, *, digest: str = "same", value: str = "same") -> None:
    root.mkdir()
    (root / "normalized").mkdir()
    (root / "normalized" / "activities.json").write_text(value, encoding="utf-8")
    (root / "run_summary.json").write_text(
        json.dumps(
            {
                "status": "PASS_WITH_WARNINGS",
                "deterministic_output_digest": digest,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_identical_outputs_pass(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_output(first)
    _write_output(second)

    result = compare_output_directories(first, second)

    assert result["status"] == "PASS"
    assert result["findings"] == []
    assert result["file_count"] == 2


def test_byte_difference_fails(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_output(first)
    _write_output(second, value="different")

    result = compare_output_directories(first, second)

    assert result["status"] == "FAIL"
    assert "byte content differs: ['normalized/activities.json']" in result["findings"]


def test_digest_difference_fails(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_output(first)
    _write_output(second, digest="different")

    result = compare_output_directories(first, second)

    assert result["status"] == "FAIL"
    assert "deterministic output digests differ" in result["findings"]
