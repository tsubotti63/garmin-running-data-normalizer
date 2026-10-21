"""The JSON Schemas of the daily datasets describe the rows of v2.0.0 (stage E1b).

`schemas/<dataset>.schema.json` describes `normalized/<dataset>.json`. Each one
follows the Schema Catalog that a run writes (its fields, their types, whether
they can be null, and whether they are required), and every row of synthetic
runs that take each way to an empty field validates against it: values that
disagree, values of another form, absent values, and the marks of Sleep, in
one-shot and Snapshot runs. The Lactate Threshold candidates validate against
their schema too.

A small validator in this file checks the keywords that the schemas use and
fails on any other keyword, so that no schema rule goes unchecked and no new
dependency is needed. It checks `format: date` as a date, which is stricter
than JSON Schema 2020-12, where `format` is only an annotation.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any

from garmin_running_data_normalizer.normalizers.performance_metrics import (
    collect_lactate_threshold_candidates,
)
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import initialize_store, run_snapshot_all
from tests.test_performance_metrics import _asset
from tests.test_remaining_wellness_metrics import fit_timestamp, hrv_fit
from tests.test_rows_left_out import FILES, KEPT, both_forms, export_with
from tests.test_snapshot_values_disagree import ACCOUNT, register, write_export
from tests.test_values_disagree import (
    DISAGREEING,
    write_agreeing_export,
    write_disagreeing_export,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
DAILY = (
    "acute_training_load_daily",
    "endurance_score_daily",
    "hill_score_daily",
    "hrv_daily",
    "race_prediction_daily",
    "sleep_daily",
    "training_history_daily",
    "training_readiness_daily",
    "uds_daily",
    "vo2max_daily",
)
HRV_FILE = "DI-Connect-Metrics/synthetic_hrv.fit"
NO_HRV_VALUE = 65535

# The keywords that the validator below checks; any other keyword fails.
KEYWORDS = frozenset(
    {
        "$schema",
        "title",
        "description",
        "type",
        "items",
        "required",
        "properties",
        "additionalProperties",
        "const",
        "enum",
        "minimum",
        "format",
    }
)
TYPES = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
    "array": lambda value: isinstance(value, list),
    "object": lambda value: isinstance(value, dict),
}
DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")
# The Schema Catalog's logical types, as JSON Schema types.
CATALOG_TYPES = {
    "string": ["string"],
    "integer": ["integer"],
    "number": ["number"],
    "boolean": ["boolean"],
    "array[string]": ["array"],
    "integer|string": ["integer", "string"],
    "number|string": ["number", "string"],
}


def _same(value: object, expected: object) -> bool:
    """JSON equality: true is not 1, and 1 is 1.0."""
    if isinstance(value, bool) or isinstance(expected, bool):
        return isinstance(value, bool) and isinstance(expected, bool) and value == expected
    return value == expected


def problems(schema: dict[str, Any], value: object, path: str = "$") -> list[str]:
    """What makes `value` fail `schema`, by the keywords that the schemas use."""
    unknown = set(schema) - KEYWORDS
    if unknown:
        return [f"{path}: keywords this check does not know: {sorted(unknown)}"]
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        return [f"{path}: additionalProperties is checked only as true or false"]
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(TYPES[name](value) for name in types):
            return [f"{path}: {type(value).__name__} is not {types}"]
    found: list[str] = []
    if "const" in schema and not _same(value, schema["const"]):
        found.append(f"{path}: not {schema['const']!r}")
    if "enum" in schema and not any(_same(value, item) for item in schema["enum"]):
        found.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if "minimum" in schema and TYPES["number"](value) and value < schema["minimum"]:
        found.append(f"{path}: {value!r} is below {schema['minimum']}")
    if schema.get("format") == "date" and isinstance(value, str):
        try:
            valid = bool(DATE_TEXT.fullmatch(value)) and date.fromisoformat(value) is not None
        except ValueError:
            valid = False
        if not valid:
            found.append(f"{path}: {value!r} is not a date")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                found.append(f"{path}.{name}: required")
        properties = schema.get("properties", {})
        for name, item in value.items():
            if name in properties:
                found.extend(problems(properties[name], item, f"{path}.{name}"))
            elif schema.get("additionalProperties") is False:
                found.append(f"{path}.{name}: not allowed")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            found.extend(problems(schema["items"], item, f"{path}[{index}]"))
    return found


def schema_of(dataset: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / f"{dataset}.schema.json").read_text(encoding="utf-8"))


def rows_of(output: Path, dataset: str) -> list[dict[str, Any]]:
    return json.loads((output / "normalized" / f"{dataset}.json").read_text(encoding="utf-8"))


def hrv_readings() -> bytes:
    """One reading, a repeated reading, readings that differ, and no value."""
    one = fit_timestamp("2030-02-11T12:00:00Z")
    repeated = fit_timestamp("2030-02-12T12:00:00Z")
    differing = fit_timestamp("2030-02-13T12:00:00Z")
    absent = fit_timestamp("2030-02-14T12:00:00Z")
    return hrv_fit(
        (70 * 128, one),
        (72 * 128, repeated),
        (72 * 128, repeated),
        (74 * 128, differing),
        (76 * 128, differing),
        (NO_HRV_VALUE, absent),
    )


# Rows of each daily dataset that leave fields empty in each way: values of
# another form (DATA_VALUE_INVALID), an explicit null beside a value, and the
# fields that a row does not give. KEPT gives one value of each dataset. A
# row without the value that a dataset needs, such as the overall score of
# Hill and Endurance Scores, is left out instead (DATA_ROW_LEFT_OUT), so the
# empty values here are in the other fields.
EMPTY_FIELDS = {
    FILES["hill_score_daily"]: [
        KEPT["hill_score_daily"],
        {"calendarDate": "2030-02-02", "overallScore": 61, "strengthScore": "61"},
        {"calendarDate": "2030-02-03", "overallScore": 62, "strengthScore": None},
    ],
    FILES["endurance_score_daily"]: [
        KEPT["endurance_score_daily"],
        {"calendarDate": "2030-02-02", "overallScore": 6001, "classification": "abc"},
        {"calendarDate": "2030-02-03", "overallScore": 6002, "classification": None},
    ],
    FILES["race_prediction_daily"]: [
        KEPT["race_prediction_daily"],
        {**KEPT["race_prediction_daily"], "calendarDate": "2030-02-02", "timestamp": "2030-02-02T06:00:00", "raceTime5K": "abc"},
        {"calendarDate": "2030-02-03", "timestamp": "2030-02-03T06:00:00", "raceTime10K": None, "raceTimeHalf": 4800},
    ],
    FILES["sleep_daily"]: [
        KEPT["sleep_daily"],
        # A day that comes from the end time.
        {
            "sleepStartTimestampGMT": "2030-02-01T14:00:00Z",
            "sleepEndTimestampGMT": "2030-02-01T21:30:00Z",
            "deepSleepSeconds": 3600,
        },
        # Values of another form: a start out of range and a duration as text.
        {
            "calendarDate": "2030-02-03",
            "sleepStartTimestampGMT": "9999-12-31T23:59:59Z",
            "sleepEndTimestampGMT": "2030-02-02T21:00:00Z",
            "sleepTimeSeconds": "abc",
        },
        # Two sleeps of one day whose windows and durations differ: the
        # duration is null and so is its mark.
        {
            "calendarDate": "2030-02-05",
            "sleepStartTimestampGMT": "2030-02-04T14:00:00Z",
            "sleepEndTimestampGMT": "2030-02-04T21:00:00Z",
            "sleepTimeSeconds": 25200,
        },
        {
            "calendarDate": "2030-02-05",
            "sleepStartTimestampGMT": "2030-02-04T15:00:00Z",
            "sleepEndTimestampGMT": "2030-02-04T22:00:00Z",
            "sleepTimeSeconds": 24000,
        },
    ],
    FILES["uds_daily"]: [
        KEPT["uds_daily"],
        {"calendarDate": "2030-02-02", "totalSteps": "5", "restingHeartRate": 50},
        {"calendarDate": "2030-02-03", "totalSteps": None, "restingHeartRate": 49},
    ],
    FILES["acute_training_load_daily"]: [
        KEPT["acute_training_load_daily"],
        {"calendarDate": "2030-02-02", "timestamp": "2030-02-02T06:00:00", "dailyTrainingLoadAcute": "abc", "dailyTrainingLoadChronic": 5},
        {"calendarDate": "2030-02-03", "timestamp": "2030-02-03T06:00:00", "dailyTrainingLoadAcute": None, "dailyTrainingLoadChronic": 6},
    ],
    FILES["training_readiness_daily"]: [
        KEPT["training_readiness_daily"],
        {"calendarDate": "2030-02-02", "timestamp": "2030-02-02T06:00:00", "score": [1], "validSleep": True},
        {"calendarDate": "2030-02-03", "timestamp": "2030-02-03T06:00:00", "score": None, "validSleep": False},
    ],
    FILES["vo2max_daily"]: [
        KEPT["vo2max_daily"],
        {**KEPT["vo2max_daily"], "calendarDate": "2030-02-02", "updateTimestamp": "2030-02-02T06:00:00", "maxMet": "abc"},
        {"calendarDate": "2030-02-03", "updateTimestamp": "2030-02-03T06:00:00", "vo2MaxValue": 52, "maxMet": None, "sport": "RUNNING"},
    ],
    FILES["training_history_daily"]: [
        KEPT["training_history_daily"],
        {**KEPT["training_history_daily"], "calendarDate": "2030-02-02", "timestamp": "2030-02-02T06:00:00", "sport": 5},
        {"calendarDate": "2030-02-03", "timestamp": "2030-02-03T06:00:00", "trainingStatus": "PEAKING", "sport": None},
    ],
}


class OutputSchemasTest(unittest.TestCase):
    """Synthetic runs, written once for every test of this class."""

    outputs: dict[str, Path]

    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        root = Path(cls._directory.name)
        cls.outputs = {}
        for name, writer in (("agreeing", write_agreeing_export), ("disagreeing", write_disagreeing_export)):
            output = root / f"{name}-output"
            run_all(writer(root / f"{name}-export"), output)
            cls.outputs[name] = output
        source = export_with(root, "empty-fields-export", EMPTY_FIELDS)
        (source / HRV_FILE).parent.mkdir(parents=True, exist_ok=True)
        (source / HRV_FILE).write_bytes(hrv_readings())
        cls.outputs["empty fields"] = both_forms(unittest.TestCase(), root, source, "empty-fields")
        cls.outputs["empty fields, one Snapshot"] = root / "empty-fields-snapshot"
        cls.outputs["Snapshots that disagree"] = cls._snapshots_that_disagree(root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    @staticmethod
    def _snapshots_that_disagree(root: Path) -> Path:
        """Two Snapshots whose values of every daily dataset differ."""
        store = root / "store"
        initialize_store(store, ACCOUNT)
        for day, use_change in ((1, False), (2, True)):
            files: dict[str, object] = {}
            for dataset, relative in FILES.items():
                _name, row, change, _field, _values = DISAGREEING[dataset]
                files[relative] = [{**row, **change} if use_change else row]
            source = write_export(root, f"snapshot-source-{day}", files)
            hrv = fit_timestamp("2030-02-01T12:00:00Z")
            (source / HRV_FILE).parent.mkdir(parents=True, exist_ok=True)
            (source / HRV_FILE).write_bytes(hrv_fit(((75 if use_change else 70) * 128, hrv)))
            register(store, source, f"S{day}", day)
        output = root / "snapshots-output"
        run_snapshot_all(store, output)
        return output

    def every_row(self, dataset: str) -> list[tuple[str, dict[str, Any]]]:
        return [(name, row) for name, output in self.outputs.items() for row in rows_of(output, dataset)]

    def test_each_schema_follows_the_schema_catalog(self) -> None:
        catalog = json.loads((self.outputs["agreeing"] / "SCHEMA_CATALOG.json").read_text(encoding="utf-8"))
        by_dataset = {item["dataset"]: item for item in catalog["datasets"]}
        self.assertEqual(
            sorted(path.name.removesuffix(".schema.json") for path in SCHEMAS.glob("*_daily.schema.json")),
            sorted(DAILY),
        )
        for dataset in DAILY:
            with self.subTest(dataset=dataset):
                items = schema_of(dataset)["items"]
                fields = by_dataset[dataset]["fields"]
                self.assertEqual(list(items["properties"]), [field["field"] for field in fields])
                self.assertEqual(items["required"], [field["field"] for field in fields if field["required"]])
                self.assertIs(items["additionalProperties"], False)
                for field in fields:
                    with self.subTest(field=field["field"]):
                        rule = items["properties"][field["field"]]
                        wanted = CATALOG_TYPES[field["logical_type"]] + (["null"] if field["nullable"] else [])
                        if "type" in rule:
                            found = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
                            self.assertEqual(sorted(found), sorted(wanted))
                        else:
                            # A fixed set of values stands for the type.
                            values = [rule["const"]] if "const" in rule else rule["enum"]
                            self.assertTrue(all(TYPES[wanted[0]](value) for value in values))
                            self.assertNotIn("null", wanted)
                        if field["logical_type"] == "array[string]":
                            self.assertEqual(rule["items"], {"type": "string"})
                        self.assertEqual(
                            rule.get("format"),
                            "date" if field["unit_or_domain"] == "ISO-8601-date" else None,
                        )

    def test_only_the_fixed_values_of_hrv_stand_for_a_type(self) -> None:
        # vo2max_source_series is text: a series that the source names is
        # kept as given, so a list of values would not describe the rows.
        fixed = {
            (dataset, name)
            for dataset in DAILY
            for name, rule in schema_of(dataset)["items"]["properties"].items()
            if "const" in rule or "enum" in rule
        }
        self.assertEqual(
            fixed,
            {
                ("hrv_daily", "semantics_status"),
                ("hrv_daily", "analysis_role"),
                ("hrv_daily", "dedupe_status"),
            },
        )

    def test_every_row_of_the_synthetic_runs_validates(self) -> None:
        for dataset in DAILY:
            with self.subTest(dataset=dataset):
                rows = self.every_row(dataset)
                self.assertTrue(rows, "no row to check")
                schema = schema_of(dataset)
                for name in self.outputs:
                    self.assertEqual(problems(schema, rows_of(self.outputs[name], dataset)), [], name)

    def test_the_rows_take_each_way_to_an_empty_field(self) -> None:
        for dataset in DAILY:
            with self.subTest(dataset=dataset):
                rows = [row for _name, row in self.every_row(dataset)]
                fields = schema_of(dataset)["items"]["properties"]
                nullable = {name for name, rule in fields.items() if "null" in (rule.get("type") or [])}
                # Values that disagree are null and named.
                self.assertTrue(any(row["disagreeing_fields"] for row in rows))
                for row in rows:
                    for name in row["disagreeing_fields"]:
                        self.assertIsNone(row[name], (dataset, name))
                # Some nullable field is null in a row without a disagreement,
                # but in HRV: a reading without a value is counted and gives
                # no row, so its value is null only when readings disagree.
                if dataset != "hrv_daily":
                    self.assertTrue(
                        any(row[name] is None for row in rows if not row["disagreeing_fields"] for name in nullable)
                    )

    def test_values_of_another_form_left_fields_empty(self) -> None:
        summary = json.loads((self.outputs["empty fields"] / "run_summary.json").read_text(encoding="utf-8"))
        datasets = {item.get("dataset") for item in summary["warnings"] if item["code"] == "DATA_VALUE_INVALID"}
        expected = set(DAILY) - {"hrv_daily"}
        self.assertEqual(datasets & expected, expected)

    def test_the_fixed_values_of_hrv_are_those_that_its_rows_take(self) -> None:
        properties = schema_of("hrv_daily")["items"]["properties"]
        statuses = {row["dedupe_status"] for _name, row in self.every_row("hrv_daily")}
        self.assertEqual(statuses, set(properties["dedupe_status"]["enum"]))
        self.assertEqual(len(properties["dedupe_status"]["enum"]), 3)
        audit = json.loads((self.outputs["empty fields"] / "audit/hrv_daily.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["absent_value_counts"], {"hrv_value": 1})

    def test_the_marks_of_sleep_take_their_values(self) -> None:
        rows = [row for _name, row in self.every_row("sleep_daily")]
        durations = {row["sleep_duration_source"] for row in rows}
        self.assertIn(None, durations)
        self.assertTrue({"stage_derived", "direct_fallback"} <= durations)
        # The mark of the day names the stable key, which never disagrees,
        # so these runs give it a value in every row.
        self.assertEqual(
            {row["sleep_day_source"] for row in rows}, {"calendarDate", "sleepEndTimestampGMT"}
        )

    def test_the_lactate_threshold_candidates_validate(self) -> None:
        audit = collect_lactate_threshold_candidates(
            [
                _asset(
                    "DI-Connect-Wellness/synthetic_userBioMetrics.json",
                    [
                        {"metaData": {"calendarDate": "2026-07-12T00:00:00", "sequence": 2}, "lactateThresholdSpeed": 0.386, "functionalThresholdPower": 290},
                        {"metaData": {"calendarDate": "2026-07-11", "sequence": 1}, "lactateThresholdSpeed": None},
                    ],
                ),
                _asset("DI-Connect-Wellness/synthetic_bioMetrics_latest.json", [{"lactateThresholdSpeed": 0.395, "lactateThresholdHeartRate": 164, "functionalThresholdPower": 151}]),
                _asset("DI-Connect-Wellness/synthetic_userBioMetricProfileData.json", [{"lactateThresholdHeartRate": 165, "functionalThresholdPower": 290}]),
                _asset("DI-Connect-Wellness/synthetic_heartRateZones.json", [{"trainingMethod": "LACTATE_THRESHOLD", "lactateThresholdHeartRateUsed": 163}]),
            ]
        )
        self.assertTrue(audit["candidates"])
        schema = json.loads((SCHEMAS / "lactate_threshold_candidate.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(problems(schema, audit), [])
        for name, output in self.outputs.items():
            with self.subTest(output=name):
                written = json.loads((output / "audit/lactate_threshold_candidates.json").read_text(encoding="utf-8"))
                self.assertEqual(problems(schema, written), [])


class ValidatorTest(unittest.TestCase):
    """The validator fails each rule that the schemas use."""

    SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["day", "count", "status"],
            "properties": {
                "day": {"type": "string", "format": "date"},
                "count": {"type": ["integer", "null"], "minimum": 1},
                "status": {"enum": ["a", "b"]},
                "role": {"const": "fixed"},
                "names": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
    }
    GOOD = {"day": "2030-02-01", "count": 1, "status": "a", "role": "fixed", "names": ["x"]}

    def test_a_good_row_passes(self) -> None:
        self.assertEqual(problems(self.SCHEMA, [self.GOOD, {**self.GOOD, "count": None}]), [])

    def test_each_rule_fails(self) -> None:
        cases = {
            "not allowed": {**self.GOOD, "other": 1},
            "required": {key: value for key, value in self.GOOD.items() if key != "count"},
            "is not ['integer', 'null']": {**self.GOOD, "count": 1.5},
            "bool is not": {**self.GOOD, "count": True},
            "below": {**self.GOOD, "count": 0},
            "is not one of": {**self.GOOD, "status": "c"},
            "not 'fixed'": {**self.GOOD, "role": "other"},
            "is not a date": {**self.GOOD, "day": "2030-02-30"},
            "is not ['string']": {**self.GOOD, "names": [1]},
        }
        for words, row in cases.items():
            with self.subTest(case=words):
                found = problems(self.SCHEMA, [row])
                self.assertTrue(any(words in item for item in found), found)

    def test_an_unknown_keyword_fails(self) -> None:
        self.assertIn("keywords this check does not know", problems({"pattern": "x"}, "x")[0])
        self.assertIn("checked only as true or false", problems({"additionalProperties": {}}, {})[0])

    def test_a_date_must_be_a_date_in_its_form(self) -> None:
        schema = {"type": "string", "format": "date"}
        self.assertEqual(problems(schema, "2030-02-28"), [])
        for text in ("2030-2-28", "20300228", "2030-02-28T00:00:00", "2030-13-01"):
            with self.subTest(text=text):
                self.assertTrue(problems(schema, text))


if __name__ == "__main__":
    unittest.main()
