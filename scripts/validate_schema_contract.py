#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from garmin_running_data_normalizer.output_experience import (
    SchemaContractError,
    validate_schema_contract,
)
from garmin_running_data_normalizer.run_all import DATASET_PATHS


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaContractError(f"{path.name}: readable JSON is required") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate normalized output against SCHEMA_CATALOG.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Completed Run-All output directory.",
    )
    args = parser.parse_args()
    output_root = args.output.resolve()
    try:
        if not output_root.is_dir():
            raise SchemaContractError("output must be a directory")
        records = {
            dataset: _load_json(output_root / relative_path)
            for dataset, relative_path in DATASET_PATHS.items()
        }
        schema_catalog = _load_json(output_root / "SCHEMA_CATALOG.json")
        if not isinstance(schema_catalog, dict):
            raise SchemaContractError("SCHEMA_CATALOG.json must contain an object")
        result = validate_schema_contract(records, schema_catalog)
    except SchemaContractError as exc:
        result = {"status": "FAIL", "error": str(exc)}
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
