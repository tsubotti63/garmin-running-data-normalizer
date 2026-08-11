#!/usr/bin/env python3
"""Generate deterministic, public-safe first-user conversion SVG assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from html import escape
from pathlib import Path

from garmin_running_data_normalizer.standalone import validate_standalone_handoff


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_CSV = (
    ROOT / "examples/analysis/monthly_weekly_training_trends/input_sample.csv"
)
DEFAULT_OUTPUT_DIR = ROOT / "docs/assets/first-user-conversion"
DISCLOSURE = "Synthetic / fictional data"
EXPECTED_SYNTHETIC_RUN_DIGEST = (
    "f67ac0787884b4df8bb25f578525176f64c1a1e0a3a9670df16f9b04403a27bb"
)
EXPECTED_SYNTHETIC_SUMMARY_SHA256 = (
    "9a878407360ccee4b5081b0b639169c099ce3560b807462431ae31aabf41693c"
)
EXPECTED_ANALYSIS_CSV_SHA256 = (
    "0d7a05e99d21dc68b91853acd1d428e8b02ce0f374da9a5cb39e071db01d9f7b"
)


def _svg_document(
    *, title: str, description: str, height: int, body: str
) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <style>
    .bg {{ fill: #f7fafc; }}
    .panel {{ fill: #ffffff; stroke: #8fa3b8; stroke-width: 2; }}
    .accent {{ fill: #0f766e; }}
    .accent2 {{ fill: #075985; }}
    .ink {{ fill: #102a43; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .muted {{ fill: #486581; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .inverse {{ fill: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .line {{ stroke: #0f766e; stroke-width: 4; fill: none; }}
  </style>
  <rect class="bg" width="1200" height="{height}" rx="24"/>
{body}
</svg>
"""


def _disclosure(y: int = 28) -> str:
    return f"""  <rect x="930" y="{y}" width="230" height="38" rx="19" class="accent"/>
  <text x="1045" y="{y + 25}" text-anchor="middle" class="inverse" font-size="16" font-weight="700">{DISCLOSURE}</text>"""


def product_flow_svg() -> str:
    boxes = (
        (30, "Garmin Account", "Export"),
        (266, "Deterministic", "Run-All"),
        (502, "17 stable", "datasets"),
        (738, "QA / Audit", "/ Provenance"),
        (974, "Reusable", "analysis context"),
    )
    body = [
        '  <text x="40" y="54" class="ink" font-size="28" font-weight="700">From Export to reusable analysis</text>',
        _disclosure(),
        '  <text x="40" y="90" class="muted" font-size="18">A local-first, reviewable product flow</text>',
    ]
    for index, (x, line1, line2) in enumerate(boxes):
        body.extend(
            [
                f'  <rect x="{x}" y="145" width="196" height="150" rx="18" class="panel"/>',
                f'  <circle cx="{x + 98}" cy="178" r="17" class="accent2"/>',
                f'  <text x="{x + 98}" y="184" text-anchor="middle" class="inverse" font-size="16" font-weight="700">{index + 1}</text>',
                f'  <text x="{x + 98}" y="224" text-anchor="middle" class="ink" font-size="19" font-weight="700">{escape(line1)}</text>',
                f'  <text x="{x + 98}" y="252" text-anchor="middle" class="ink" font-size="19" font-weight="700">{escape(line2)}</text>',
            ]
        )
        if index < len(boxes) - 1:
            arrow_x = x + 203
            body.extend(
                [
                    f'  <path d="M {arrow_x} 220 H {arrow_x + 28}" class="line"/>',
                    f'  <path d="M {arrow_x + 20} 210 L {arrow_x + 32} 220 L {arrow_x + 20} 230" class="line"/>',
                ]
            )
    body.extend(
        [
            '  <rect x="30" y="330" width="1140" height="56" rx="14" fill="#e6fffa"/>',
            '  <text x="600" y="365" text-anchor="middle" class="ink" font-size="18">Downstream: bounded descriptive analysis → Human review</text>',
        ]
    )
    return _svg_document(
        title="Garmin Running Data Normalizer synthetic product flow",
        description=(
            "Synthetic and fictional diagram showing Garmin Account Export flowing "
            "through deterministic Run-All into 17 stable datasets, QA, audit, "
            "provenance, and reusable analysis context. Downstream bounded "
            "descriptive analysis ends in Human review."
        ),
        height=420,
        body="\n".join(body),
    )


def _inventory_dataset_count(inventory_text: str) -> int:
    return sum(
        1
        for line in inventory_text.splitlines()
        if line.startswith("| `") and "normalized/" in line
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_preview_svg(run_all_output: Path) -> str:
    required = (
        "run_summary.json",
        "START_HERE.md",
        "DATASET_INVENTORY.md",
        "ANALYSIS_HANDOFF.md",
    )
    missing = [name for name in required if not (run_all_output / name).is_file()]
    if missing:
        raise ValueError(f"Run-All output is incomplete; missing: {', '.join(missing)}")

    validation = validate_standalone_handoff(run_all_output)
    summary_path = run_all_output / "run_summary.json"
    if _sha256(summary_path) != EXPECTED_SYNTHETIC_SUMMARY_SHA256:
        raise ValueError(
            "Run-All summary does not match the reviewed tracked synthetic fixture"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("deterministic_output_digest") != EXPECTED_SYNTHETIC_RUN_DIGEST:
        raise ValueError(
            "Run-All output does not match the reviewed tracked synthetic fixture"
        )
    start_here = (run_all_output / "START_HERE.md").read_text(encoding="utf-8")
    inventory = (run_all_output / "DATASET_INVENTORY.md").read_text(
        encoding="utf-8"
    )
    handoff = (run_all_output / "ANALYSIS_HANDOFF.md").read_text(encoding="utf-8")

    if not start_here.startswith("# Start Here"):
        raise ValueError("START_HERE.md does not have the expected title")
    if not handoff.startswith("# Analysis Handoff"):
        raise ValueError("ANALYSIS_HANDOFF.md does not have the expected title")

    status = str(validation["run_status"])
    activities = json.loads(
        (run_all_output / "normalized/activities.json").read_text(encoding="utf-8")
    )
    if not isinstance(activities, list):
        raise ValueError("normalized Activities payload is not a list")
    records = len(activities)
    warnings = int(validation["warning_count"])
    errors = len(summary.get("errors", []))
    dataset_count = _inventory_dataset_count(inventory)
    if dataset_count != int(validation["dataset_count"]):
        raise ValueError("dataset inventory count does not match validated context")
    generated_count = len(summary["generated_paths"])

    cards = (
        (
            40,
            "START_HERE.md",
            status,
            f"{records} Activity record",
            f"{warnings} warnings • {errors} errors",
        ),
        (
            420,
            "DATASET_INVENTORY.md",
            f"{dataset_count} dataset entries",
            f"{generated_count} generated files",
            "grain • stable key • privacy",
        ),
        (
            800,
            "ANALYSIS_HANDOFF.md",
            "Receiving rules",
            "explicit relationships only",
            "facts • calculations • unknowns",
        ),
    )
    body = [
        '  <text x="40" y="54" class="ink" font-size="28" font-weight="700">What a Synthetic Run-All gives you</text>',
        _disclosure(),
        '  <text x="40" y="90" class="muted" font-size="18">Preview generated from an actual run of the tracked synthetic fixture</text>',
    ]
    for x, name, line1, line2, line3 in cards:
        body.extend(
            [
                f'  <rect x="{x}" y="130" width="340" height="270" rx="18" class="panel"/>',
                f'  <rect x="{x}" y="130" width="340" height="58" rx="18" class="accent2"/>',
                f'  <rect x="{x}" y="170" width="340" height="18" class="accent2"/>',
                f'  <text x="{x + 24}" y="166" class="inverse" font-size="20" font-weight="700">{escape(name)}</text>',
                f'  <text x="{x + 24}" y="235" class="ink" font-size="22" font-weight="700">{escape(line1)}</text>',
                f'  <text x="{x + 24}" y="282" class="muted" font-size="18">{escape(line2)}</text>',
                f'  <text x="{x + 24}" y="326" class="muted" font-size="17">{escape(line3)}</text>',
                f'  <rect x="{x + 24}" y="350" width="292" height="2" fill="#bcccdc"/>',
                f'  <text x="{x + 24}" y="378" class="muted" font-size="15">human-readable handoff</text>',
            ]
        )
    body.extend(
        [
            '  <rect x="40" y="432" width="1100" height="56" rx="14" fill="#e6fffa"/>',
            '  <text x="590" y="467" text-anchor="middle" class="ink" font-size="18">Read in order: Start Here → Dataset Inventory → Analysis Handoff</text>',
        ]
    )
    return _svg_document(
        title="Synthetic Run-All output preview",
        description=(
            f"Synthetic and fictional output preview showing {status}, {records} "
            f"Activity record, {warnings} warnings, {errors} errors, {dataset_count} "
            f"dataset inventory entries, {generated_count} generated files, and "
            "the first-read order START_HERE.md, DATASET_INVENTORY.md, then "
            "ANALYSIS_HANDOFF.md."
        ),
        height=530,
        body="\n".join(body),
    )


def _monthly_distance(analysis_csv: Path) -> list[tuple[str, int, float]]:
    totals: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"count": 0, "distance_m": 0.0}
    )
    with analysis_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"activity_date_local", "distance_m"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("analysis CSV is missing required columns")
        for row in reader:
            month = row["activity_date_local"][:7]
            totals[month]["count"] = int(totals[month]["count"]) + 1
            totals[month]["distance_m"] = float(totals[month]["distance_m"]) + float(
                row["distance_m"]
            )
    return [
        (month, int(values["count"]), float(values["distance_m"]) / 1000.0)
        for month, values in sorted(totals.items())
    ]


def monthly_distance_svg(analysis_csv: Path) -> str:
    if _sha256(analysis_csv) != EXPECTED_ANALYSIS_CSV_SHA256:
        raise ValueError("analysis CSV does not match the reviewed fictional sample")
    rows = _monthly_distance(analysis_csv)
    if not rows:
        raise ValueError("analysis CSV contains no rows")
    max_distance = max(distance for _, _, distance in rows)
    axis_max = max(10, int(math.ceil(max_distance / 10.0) * 10))
    chart_left = 110
    chart_top = 140
    chart_height = 330
    chart_bottom = chart_top + chart_height
    chart_width = 960

    body = [
        '  <text x="40" y="54" class="ink" font-size="28" font-weight="700">Monthly activity distance</text>',
        _disclosure(),
        '  <text x="40" y="90" class="muted" font-size="18">Tracked fictional analysis example • all activity types</text>',
    ]
    for tick in range(0, axis_max + 1, 10):
        y = chart_bottom - (tick / axis_max) * chart_height
        body.extend(
            [
                f'  <line x1="{chart_left}" y1="{y:.1f}" x2="{chart_left + chart_width}" y2="{y:.1f}" stroke="#d9e2ec" stroke-width="1"/>',
                f'  <text x="{chart_left - 18}" y="{y + 6:.1f}" text-anchor="end" class="muted" font-size="15">{tick}</text>',
            ]
        )
    body.append(
        f'  <text x="35" y="{chart_top + chart_height / 2}" transform="rotate(-90 35 {chart_top + chart_height / 2})" text-anchor="middle" class="ink" font-size="17">Distance (km)</text>'
    )

    slot_width = chart_width / len(rows)
    bar_width = min(220, slot_width * 0.5)
    for index, (month, count, distance) in enumerate(rows):
        center = chart_left + slot_width * (index + 0.5)
        bar_height = distance / axis_max * chart_height
        x = center - bar_width / 2
        y = chart_bottom - bar_height
        body.extend(
            [
                f'  <rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="10" class="accent2"/>',
                f'  <text x="{center:.1f}" y="{y - 14:.1f}" text-anchor="middle" class="ink" font-size="20" font-weight="700">{distance:.1f} km</text>',
                f'  <text x="{center:.1f}" y="{chart_bottom + 34}" text-anchor="middle" class="ink" font-size="18">{escape(month)}</text>',
                f'  <text x="{center:.1f}" y="{chart_bottom + 58}" text-anchor="middle" class="muted" font-size="15">{count} activities</text>',
            ]
        )
    body.append(
        '  <text x="110" y="580" class="muted" font-size="15">Source: examples/analysis/monthly_weekly_training_trends/input_sample.csv</text>'
    )
    return _svg_document(
        title="Synthetic monthly activity distance chart",
        description=(
            "Synthetic and fictional bar chart showing monthly total activity "
            "distance: "
            + ", ".join(
                f"{month}: {distance:.1f} kilometres across {count} activities"
                for month, count, distance in rows
            )
            + "."
        ),
        height=620,
        body="\n".join(body),
    )


def generate(run_all_output: Path, analysis_csv: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = {
        "product-flow.svg": product_flow_svg(),
        "synthetic-output-preview.svg": output_preview_svg(run_all_output),
        "synthetic-monthly-distance.svg": monthly_distance_svg(analysis_csv),
    }
    for name, content in assets.items():
        (output_dir / name).write_text(content, encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-all-output",
        required=True,
        type=Path,
        help="completed tracked Synthetic Run-All output directory",
    )
    parser.add_argument(
        "--analysis-csv",
        type=Path,
        default=DEFAULT_ANALYSIS_CSV,
        help="tracked fictional analysis CSV",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="destination for generated SVG assets",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generate(
        args.run_all_output.resolve(),
        args.analysis_csv.resolve(),
        args.output_dir.resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
