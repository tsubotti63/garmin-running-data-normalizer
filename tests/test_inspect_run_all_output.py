from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import inspect_run_all_output


def test_inspector_prints_structure_without_row_values(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    output = tmp_path / "output"
    (output / "analysis").mkdir(parents=True)
    (output / "run_summary.json").write_text(
        json.dumps(
            {
                "status": "PASS_WITH_WARNINGS",
                "warning_count": 1,
                "family_results": {"activities": {"status": "PROCESSED"}},
            }
        ),
        encoding="utf-8",
    )
    with (output / "analysis" / "activities.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["private_key", "distance_m"])
        writer.writeheader()
        writer.writerow({"private_key": "must-not-print", "distance_m": "1000"})

    monkeypatch.setattr(
        "sys.argv",
        ["inspect_run_all_output.py", str(output)],
    )

    assert inspect_run_all_output.main() == 0
    result = capsys.readouterr().out
    assert "PASS_WITH_WARNINGS" in result
    assert "activity_row_count: 1" in result
    assert "must-not-print" not in result
