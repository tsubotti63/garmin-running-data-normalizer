#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a privacy-bounded structural summary of Run-All output."
    )
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    summary_path = args.output / "run_summary.json"
    activities_path = args.output / "analysis" / "activities.csv"
    if not summary_path.is_file() or not activities_path.is_file():
        print("ERROR: completed Run-All output files are missing")
        return 1

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with activities_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        row_count = sum(1 for _ in reader)
        columns = reader.fieldnames or []

    print("status:", summary.get("status"))
    print("warning_count:", summary.get("warning_count"))
    print("activity_columns:", columns)
    print("activity_row_count:", row_count)
    for family, result in sorted(summary.get("family_results", {}).items()):
        print("family:", family, result.get("status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
