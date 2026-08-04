from __future__ import annotations

import copy
import unittest

from garmin_running_data_normalizer.output_experience import (
    SchemaContractError,
    build_schema_catalog,
    validate_schema_contract,
)
from garmin_running_data_normalizer.run_all import DATASET_TABLE
from tests.test_output_experience import synthetic_projection_input


def _registry() -> dict:
    return {
        "datasets": [
            {
                "name": dataset["name"],
                "record_grain": dataset["record_grain"],
                "stable_key": list(dataset["stable_key"]),
                "provenance_required": True,
            }
            for dataset in DATASET_TABLE
        ]
    }


def _schema() -> dict:
    manifest, summary, _relationship_summary = synthetic_projection_input()
    return build_schema_catalog(
        manifest,
        summary,
        _registry(),
    )


def _representative_value(logical_type: str):
    return {
        "string": "synthetic",
        "integer": 1,
        "number": 1.5,
        "boolean": False,
        "array[string]": ["synthetic"],
        "integer|string": 1,
        "number|string": 1.5,
    }[logical_type]


def _valid_records(schema: dict) -> dict[str, list[dict]]:
    records: dict[str, list[dict]] = {}
    for dataset in schema["datasets"]:
        row = {}
        for descriptor in dataset["fields"]:
            if not descriptor["required"]:
                continue
            row[descriptor["field"]] = (
                _representative_value(descriptor["logical_type"])
                if not descriptor["nullable"]
                else None
            )
        records[dataset["dataset"]] = [row]
    return records


def _descriptor(schema: dict, dataset: str, field: str) -> dict:
    dataset_schema = next(
        item for item in schema["datasets"] if item["dataset"] == dataset
    )
    return next(item for item in dataset_schema["fields"] if item["field"] == field)


class SchemaContractTest(unittest.TestCase):
    def test_catalog_distinguishes_required_nullable_and_runtime_types(self) -> None:
        schema = _schema()
        self.assertEqual(
            _descriptor(schema, "activities", "duration_ms")["logical_type"],
            "number",
        )
        self.assertEqual(
            _descriptor(schema, "activities", "start_time_local_raw")[
                "logical_type"
            ],
            "number|string",
        )
        independent_key = _descriptor(
            schema,
            "personal_records",
            "garmin_activity_key",
        )
        self.assertTrue(independent_key["required"])
        self.assertTrue(independent_key["nullable"])
        optional_lap_timestamp = _descriptor(schema, "fit_laps", "timestamp")
        self.assertFalse(optional_lap_timestamp["required"])
        self.assertTrue(optional_lap_timestamp["nullable"])
        self.assertTrue(
            all(
                isinstance(field["required"], bool)
                and isinstance(field["nullable"], bool)
                for dataset in schema["datasets"]
                for field in dataset["fields"]
            )
        )

    def test_validator_accepts_declared_types_and_omitted_optional_fields(self) -> None:
        schema = _schema()
        records = _valid_records(schema)
        records["activities"][0]["duration_ms"] = 1
        records["activities"][0]["start_time_local_raw"] = "synthetic"
        result = validate_schema_contract(records, schema)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["dataset_count"], len(DATASET_TABLE))

    def test_validator_rejects_bool_number_null_and_missing_required(self) -> None:
        schema = _schema()
        records = _valid_records(schema)
        records["activities"][0]["duration_ms"] = True
        with self.assertRaisesRegex(SchemaContractError, "logical type"):
            validate_schema_contract(records, schema)

        records = _valid_records(schema)
        records["activities"][0]["garmin_activity_key"] = None
        with self.assertRaisesRegex(SchemaContractError, "null is not allowed"):
            validate_schema_contract(records, schema)

        records = _valid_records(schema)
        del records["activities"][0]["garmin_activity_key"]
        with self.assertRaisesRegex(SchemaContractError, "required field is missing"):
            validate_schema_contract(records, schema)

    def test_validator_rejects_undeclared_record_and_catalog_fields(self) -> None:
        schema = _schema()
        records = _valid_records(schema)
        records["activities"][0]["unexpected"] = "synthetic"
        with self.assertRaisesRegex(SchemaContractError, "undeclared fields"):
            validate_schema_contract(records, schema)

        invalid_schema = copy.deepcopy(schema)
        invalid_schema["datasets"][0]["fields"][0]["logical_type"] = "unknown"
        with self.assertRaisesRegex(SchemaContractError, "unsupported"):
            validate_schema_contract(_valid_records(schema), invalid_schema)

    def test_validator_rejects_grain_key_and_relationship_metadata_drift(
        self,
    ) -> None:
        schema = _schema()
        records = _valid_records(schema)

        invalid_schema = copy.deepcopy(schema)
        invalid_schema["datasets"][0]["record_grain"] = "unknown"
        with self.assertRaisesRegex(SchemaContractError, "record grain"):
            validate_schema_contract(records, invalid_schema)

        invalid_schema = copy.deepcopy(schema)
        invalid_schema["datasets"][0]["stable_key"] = ["activity_id"]
        with self.assertRaisesRegex(SchemaContractError, "stable key"):
            validate_schema_contract(records, invalid_schema)

        invalid_schema = copy.deepcopy(schema)
        invalid_schema["datasets"][0]["canonical"] = False
        with self.assertRaisesRegex(
            SchemaContractError,
            "relationship metadata is inconsistent",
        ):
            validate_schema_contract(records, invalid_schema)

        invalid_schema = copy.deepcopy(schema)
        hill = next(
            item
            for item in invalid_schema["datasets"]
            if item["dataset"] == "hill_score_daily"
        )
        hill["join_guidance"][0]["status"] = "explicit"
        with self.assertRaisesRegex(
            SchemaContractError,
            "relationship metadata is inconsistent",
        ):
            validate_schema_contract(records, invalid_schema)


if __name__ == "__main__":
    unittest.main()
