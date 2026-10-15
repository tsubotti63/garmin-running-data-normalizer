"""The source fields and FIT messages that a run does not read are counted
(stage A4c-1).

The audit records of Activities, Gear, activity_gear, and Personal Records
count by name the fields of the rows read that no field takes, without their
values; a name that is not a word may be a value, so such fields are counted
together without their names. The FIT audit counts, for each FIT file, the
messages of the numbers that no dataset reads and the developer fields; they
do not make the file incomplete. A Snapshot run of a store that holds one
Export counts as a one-shot run of it.
"""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.fit.parser import READ_MESSAGES, parse_fit_bytes
from garmin_running_data_normalizer.normalizers import activities, gear, personal_records
from garmin_running_data_normalizer.normalizers.activities import ACTIVITY_SOURCE_FIELDS
from garmin_running_data_normalizer.normalizers.gear import (
    GEAR_LINK_SOURCE_FIELDS,
    GEAR_SOURCE_FIELDS,
)
from garmin_running_data_normalizer.normalizers.personal_records import (
    PERSONAL_RECORD_SOURCE_FIELDS,
)
from garmin_running_data_normalizer.normalizers.unread_fields import (
    INTERNAL_FIELD_PREFIX,
    UnreadFields,
)
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.normalizers.records import SNAPSHOT_PROBE_FIELD
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    run_snapshot_all,
)
from tests.fit_fixture_factory import _definition, definition_with_developer_fields, synthetic_fit
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_parity import differences, runs
from tests.test_snapshot_record_updates import ACCOUNT, gear as gear_row, load, personal_record
from tests.test_snapshot_record_updates import register, write_export
from tests.test_unresolved_links import fit_activity, fit_export
from tests.test_zip_input import run_cli

# Names of another form than a word: a date, a number, words with spaces,
# and a name of 65 letters.
OTHER_NAMES = ("2030-01-31", "12345", "Private name with spaces", "P" * 65)


def audit(output: Path, dataset: str) -> dict[str, Any]:
    return load(output / f"audit/{dataset}.json")


def unread(output: Path, dataset: str) -> tuple[dict[str, int] | None, int | None]:
    record = audit(output, dataset)
    return record.get("unread_field_counts"), record.get("unread_other_name_count")


def export_with_fields(root: Path, name: str = "export", *, extra: bool = True) -> Path:
    """An Export whose rows of every dataset hold fields that no field takes;
    without ``extra``, the same Export without them."""

    def more(**fields: object) -> dict[str, object]:
        return fields if extra else {}

    source = write_export(
        root,
        name,
        [
            _activity("A1", **more(maxSpeed=3.5, calories=400, privateValue="Private-value-1")),
            _activity("A2", **more(maxSpeed=3.0)),
        ],
        records=[
            {**personal_record(1, "A1", 100.0), **more(prTypeLabelKey="Private-value-2")},
            personal_record(2, "A2", 200.0),
        ],
    )
    container = {
        "gearDTOS": [{**gear_row(1, "Shoe"), **more(gearStatusName="active", notified=False)}],
        "gearActivityDTOs": {
            "1": [{"activityId": "A1", **more(activityName="Private-value-3")}, {"activityId": "A2"}]
        },
    }
    (source / "DI-Connect-Fitness" / "synthetic_gear.json").write_text(
        json.dumps([container]), encoding="utf-8"
    )
    return source


class UnreadFieldsTest(unittest.TestCase):
    def test_the_fields_that_no_field_takes_are_counted_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(export_with_fields(root), output)
            self.assertEqual(
                {
                    dataset: unread(output, dataset)
                    for dataset in ("activities", "gear", "activity_gear", "personal_records")
                },
                {
                    # Each synthetic Activity also carries "synthetic".
                    "activities": (
                        {"calories": 1, "maxSpeed": 2, "privateValue": 1, "synthetic": 2},
                        None,
                    ),
                    "gear": ({"gearStatusName": 1, "notified": 1}, None),
                    "activity_gear": ({"activityName": 1}, None),
                    "personal_records": ({"prTypeLabelKey": 1}, None),
                },
            )
            # No value is written, and nothing else is announced: the run of
            # the same Export without these fields gives the same status,
            # warnings, and record counts.
            for dataset in ("activities", "activity_gear", "personal_records"):
                text = (output / f"audit/{dataset}.json").read_text(encoding="utf-8")
                self.assertNotIn("Private-value", text)
            plain = root / "plain-output"
            run_all(export_with_fields(root, "plain", extra=False), plain)
            for name in ("status", "warnings", "normalized_record_count", "family_results"):
                with self.subTest(field=name):
                    self.assertEqual(load(output / "run_summary.json")[name], load(plain / "run_summary.json")[name])
            self.assertEqual(unread(plain, "gear"), (None, None))

    def test_an_export_without_such_fields_writes_no_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = {key: value for key, value in _activity("A1").items() if key != "synthetic"}
            output = root / "output"
            run_all(write_export(root, "export", [row]), output)
            self.assertEqual(unread(output, "activities"), (None, None))

    def test_names_that_are_not_words_are_counted_without_their_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = _activity("A1", **{name: "Private-value" for name in OTHER_NAMES})
            output = root / "output"
            run_all(write_export(root, "export", [row]), output)
            self.assertEqual(unread(output, "activities"), ({"synthetic": 1}, len(OTHER_NAMES)))
            text = (output / "audit/activities.json").read_text(encoding="utf-8")
            for name in OTHER_NAMES:
                self.assertNotIn(name, text)

    def test_rows_left_out_and_items_that_are_not_records_are_not_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write_export(root, "export", [_activity("A1")])
            path = source / "DI-Connect-Fitness" / "synthetic_summarizedActivities.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            # A row without an identifier or fields for a key, and a number.
            payload[0]["summarizedActivitiesExport"] += [{"leftOutField": 1}, 7]
            path.write_text(json.dumps(payload), encoding="utf-8")
            output = root / "output"
            run_all(source, output)
            self.assertEqual(audit(output, "activities")["excluded_record_count"], 2)
            self.assertEqual(unread(output, "activities"), ({"synthetic": 1}, None))

    def test_each_copy_counts_and_a_snapshot_run_counts_as_a_one_shot_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = _activity("A1", maxSpeed=3.5)
            source = write_export(root, "export", [row, row, _activity("A2")])
            one_shot, snapshot = runs(root / "runs", source)
            self.assertEqual(differences(one_shot, snapshot), [])
            for output in (one_shot, snapshot):
                with self.subTest(run=output.name):
                    self.assertEqual(
                        unread(output, "activities"), ({"maxSpeed": 2, "synthetic": 3}, None)
                    )

    def test_copies_with_other_fields_count_as_in_a_one_shot_run(self) -> None:
        # An empty value and a missing field are alike when the build merges
        # the copies of a record within one Snapshot: it passes them as one
        # record only when they also hold the same fields.
        plain = _activity("A1")
        without_name = {key: value for key, value in plain.items() if key != "name"}
        with_extra = {"extraField": 1, "synthetic": 3}
        cases = {
            # A copy with a field that no dataset reads, and two without it.
            "null": ([_activity("A1", extraField=None), plain, plain], with_extra),
            "empty text": ([_activity("A1", extraField=""), plain, plain], with_extra),
            "empty list": ([_activity("A1", extraField=[]), plain, plain], with_extra),
            "empty object": ([_activity("A1", extraField={}), plain, plain], with_extra),
            "a value": ([_activity("A1", extraField=1), plain, plain], with_extra),
            # Two copies of one Activity and another Activity.
            "and another record": (
                [_activity("A1", extraNote=None), plain, _activity("A2")],
                {"extraNote": 1, "synthetic": 3},
            ),
            # A copy whose field read is null, and one without the field.
            "a field read, null": ([_activity("A1", name=None), without_name], {"synthetic": 2}),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label, (rows, expected) in cases.items():
                with self.subTest(copies=label):
                    folder = root / label.replace(" ", "-").replace(",", "")
                    one_shot, snapshot = runs(folder / "runs", write_export(folder, "export", rows))
                    self.assertEqual(differences(one_shot, snapshot), [])
                    for output in (one_shot, snapshot):
                        self.assertEqual(unread(output, "activities"), (expected, None))

    def test_a_snapshot_run_counts_the_fields_of_every_dataset_as_a_one_shot_run(self) -> None:
        # The build keeps the Gear key of a link under a name of its own, so
        # that the link is passed with the fields of the Export only.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one_shot, snapshot = runs(root / "runs", export_with_fields(root))
            self.assertEqual(differences(one_shot, snapshot), [])
            for dataset in ("activities", "gear", "activity_gear", "personal_records"):
                with self.subTest(dataset=dataset):
                    self.assertEqual(unread(snapshot, dataset), unread(one_shot, dataset))

    def test_a_snapshot_run_of_several_snapshots_counts_the_records_it_reads(self) -> None:
        # The first Snapshot holds the Activity twice with names that
        # disagree, and the second lacks the name: the build passes the
        # Activity of the second, with a field of the first that it lacks,
        # and probe records for the name, which are not counted.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_export(root, "first", [
                _activity("A1", maxSpeed=3.0, name="x"),
                _activity("A1", maxSpeed=3.0, name="y", earlierOnly=1),
            ])
            second = write_export(root, "second", [
                {key: value for key, value in _activity("A1", maxSpeed=3.0).items() if key != "name"}
            ])
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for day, source in enumerate((first, second), start=1):
                register(store, source, f"S{day}", day)
            build = root / "build"
            build_approved_input(store, build)
            rows = [
                row
                for path in build.rglob("*.json")
                if "ummarizedActivities" in path.name
                for item in load(path)
                for row in item.get("summarizedActivitiesExport", [])
            ]
            self.assertEqual(sum(SNAPSHOT_PROBE_FIELD in row for row in rows), 3)
            output = root / "snapshot"
            run_snapshot_all(store, output)
            self.assertEqual(
                unread(output, "activities"),
                ({"earlierOnly": 1, "maxSpeed": 1, "synthetic": 1}, None),
            )

    def test_the_field_states_of_a_snapshot_count_the_gear_key_of_a_link_once(self) -> None:
        # The field states of the merge summary count the Gear key that the
        # build keeps with a link as the link's gearPk, as before stage
        # A4c-1, also when the link holds a gearPk of its own: two values
        # for each link, its activityId and its Gear key.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for own_key in (False, True):
                with self.subTest(own_key=own_key):
                    folder = root / f"own-key-{own_key}"
                    source = write_export(
                        folder, "export", [_activity("A1"), _activity("A2")],
                        gear_rows=[gear_row(1, "Shoe")], links={"1": ["A1", "A2"]},
                    )
                    if own_key:
                        path = source / "DI-Connect-Fitness" / "synthetic_gear.json"
                        payload = load(path)
                        for row in payload[0]["gearActivityDTOs"]["1"]:
                            row["gearPk"] = 1
                        path.write_text(json.dumps(payload), encoding="utf-8")
                    one_shot, snapshot = runs(folder / "runs", source)
                    self.assertEqual(differences(one_shot, snapshot), [])
                    summary = load(snapshot / "snapshot/canonical_merge_summary.json")
                    self.assertEqual(
                        summary["datasets"]["activity_gear"]["presence_state_counts"],
                        {"explicit_value": 4, "field_absent": 0, "record_absent": 0},
                    )
                    # A Gear key of its own is a field that no dataset reads.
                    self.assertEqual(
                        unread(snapshot, "activity_gear"), ({"gearPk": 2} if own_key else None, None)
                    )

    def test_the_fields_of_the_build_are_not_counted(self) -> None:
        counter = UnreadFields(frozenset({"activityId"}))
        counter.add({"activityId": 1, f"{INTERNAL_FIELD_PREFIX}SnapshotNumbers": [1, 1], "extra": 1})
        counter.add({"activityId": 2, f"{INTERNAL_FIELD_PREFIX}SnapshotProbe": "name", "extra": 1})
        # The first record stands for two copies within one Snapshot; the
        # probe record is not an observation.
        self.assertEqual(counter.audit_fields(), {"unread_field_counts": {"extra": 2}})


class RecordingRow(dict):
    """A row that remembers the fields that are read from it, by name."""

    def __init__(self, *args: Any, touched: set[str], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.touched = touched

    def get(self, key: Any, default: Any = None) -> Any:
        self.touched.add(key)
        return super().get(key, default)

    def __getitem__(self, key: Any) -> Any:
        self.touched.add(key)
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        self.touched.add(key)  # type: ignore[arg-type]
        return super().__contains__(key)


def read_fields(touched: set[str]) -> set[str]:
    return {name for name in touched if not name.startswith(INTERNAL_FIELD_PREFIX)}


ASSET = SimpleNamespace(provenance_path="DI-Connect-Fitness/synthetic.json", sha256="0" * 64)


class FieldListTest(unittest.TestCase):
    """The field lists are the fields that the datasets read: the rows go
    through the normalizers, which may read any field, and the fields read
    are those of the list, in both directions."""

    def normalize(self, module: Any, function: str, payload: Any, **kwargs: Any) -> Any:
        with mock.patch.object(module, "load_json_assets", return_value=[(payload, ASSET)]):
            return getattr(module, function)("unused", assets=[], **kwargs)

    def test_activities(self) -> None:
        touched: set[str] = set()
        full = {name: 1 for name in ACTIVITY_SOURCE_FIELDS} | {"activityType": "running"}
        rows = [
            RecordingRow(full, touched=touched),
            # Without a start time, the start is read from beginTimestamp.
            RecordingRow({**full, "startTimeGmt": None}, touched=touched),
            # Without an identifier, the key is made from other fields.
            RecordingRow({key: value for key, value in full.items() if key != "activityId"}, touched=touched),
        ]
        self.normalize(
            activities,
            "normalize_activities",
            {"summarizedActivitiesExport": rows},
            unread=UnreadFields(ACTIVITY_SOURCE_FIELDS),
        )
        self.assertEqual(read_fields(touched), set(ACTIVITY_SOURCE_FIELDS))

    def test_gear_and_links(self) -> None:
        gear_touched: set[str] = set()
        link_touched: set[str] = set()
        full = {name: f"value-{name}" for name in GEAR_SOURCE_FIELDS} | {"gearPk": 1}
        rows = [
            RecordingRow(full, touched=gear_touched),
            # Without a type name, the type is read from gearType.
            RecordingRow({**full, "gearPk": 2, "gearTypeName": ""}, touched=gear_touched),
            RecordingRow({key: value for key, value in full.items() if key != "gearPk"}, touched=gear_touched),
        ]
        links = {"1": [RecordingRow({name: "A1" for name in GEAR_LINK_SOURCE_FIELDS}, touched=link_touched)]}
        self.normalize(
            gear,
            "normalize_gear",
            [{"gearDTOS": rows, "gearActivityDTOs": links}],
            unread={
                "gear": UnreadFields(GEAR_SOURCE_FIELDS),
                "activity_gear": UnreadFields(GEAR_LINK_SOURCE_FIELDS),
            },
        )
        self.assertEqual(read_fields(gear_touched), set(GEAR_SOURCE_FIELDS))
        self.assertEqual(read_fields(link_touched), set(GEAR_LINK_SOURCE_FIELDS))

    def test_personal_records(self) -> None:
        touched: set[str] = set()
        full = {name: 1 for name in PERSONAL_RECORD_SOURCE_FIELDS}
        rows = [
            RecordingRow(full, touched=touched),
            # Without an identifier, the key is made from other fields.
            RecordingRow(
                {key: value for key, value in full.items() if key != "personalRecordId"},
                touched=touched,
            ),
        ]
        self.normalize(
            personal_records,
            "normalize_personal_records",
            [{"personalRecords": rows}],
            unread=UnreadFields(PERSONAL_RECORD_SOURCE_FIELDS),
        )
        self.assertEqual(read_fields(touched), set(PERSONAL_RECORD_SOURCE_FIELDS))


def other_messages() -> bytes:
    """Records of messages that no dataset reads, after the session and lap
    of the synthetic FIT file: a file_id (0), and two events (21) with two
    developer fields each."""
    body = bytearray(_definition(2, 0, [(0, 1, 0x00)]))
    body.extend(bytes([2, 4]))
    body.extend(definition_with_developer_fields(3, 21, [(0, 1, 0x00)], [(0, 1, 0), (1, 2, 0)]))
    for _ in range(2):
        body.extend(bytes([3, 0]) + b"\x01\x02\x03")
    return bytes(body)


def hrv_message() -> bytes:
    """An HRV reading (370), which the HRV daily dataset reads."""
    return _definition(4, 370, [(1, 2, 0x84), (253, 4, 0x86)]) + bytes([4]) + struct.pack("<HI", 6400, 1_000_000)


def fit_entry(output: Path) -> dict[str, Any]:
    entries = load(output / "audit/fit_audit.json")
    assert len(entries) == 1
    return entries[0]


class FitMessagesNotReadTest(unittest.TestCase):
    def test_other_messages_and_developer_fields_are_counted(self) -> None:
        parsed = parse_fit_bytes(
            synthetic_fit(extra_body=other_messages() + hrv_message()), file_id="f", source_path="a.fit"
        )
        self.assertEqual(parsed["status"], "parsed_activity")
        self.assertEqual(parsed["not_read_message_counts"], {"0": 1, "21": 2})
        self.assertEqual(parsed["developer_field_count"], 4)
        self.assertEqual(parsed["unknown_records"], 0)
        # The HRV readings are read by the HRV daily dataset.
        self.assertNotIn("370", parsed["not_read_message_counts"])
        self.assertEqual(READ_MESSAGES, {12, 18, 19, 20, 370})

    def test_a_fit_file_without_an_activity_is_counted(self) -> None:
        # A FIT file with HRV readings and no session, as one of sleep.
        data = synthetic_fit(sessions=0, extra_body=other_messages() + hrv_message())
        parsed = parse_fit_bytes(data, file_id="f", source_path="a.fit")
        self.assertEqual(
            (parsed["status"], parsed["not_read_message_counts"], parsed["developer_field_count"]),
            ("parsed_non_activity", {"0": 1, "21": 2}, 4),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = fit_export(root, [_activity("A1")], {"sleep.fit": data})
            one_shot, snapshot = runs(root / "runs", source)
            self.assertEqual(differences(one_shot, snapshot), [])
            entry = fit_entry(one_shot)
            self.assertEqual(
                (entry["parse_status"], entry["not_read_message_counts"], entry["developer_field_count"]),
                ("parsed_non_activity", {"0": 1, "21": 2}, 4),
            )
            self.assertEqual(len(load(one_shot / "normalized/hrv_daily.json")), 1)

    def test_a_run_counts_them_without_calling_the_file_incomplete(self) -> None:
        # Both FIT files hold an HRV reading; one also holds the messages that
        # no dataset reads. Only the counts of the FIT audit tell them apart.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = {}
            for name, extra in (("plain", hrv_message()), ("others", other_messages() + hrv_message())):
                source = fit_export(root / name, [fit_activity("1001")], {"a.fit": synthetic_fit(extra_body=extra)})
                one_shot, snapshot = runs(root / name / "runs", source)
                self.assertEqual(differences(one_shot, snapshot), [])
                results[name] = one_shot
            entry = fit_entry(results["others"])
            self.assertEqual(
                (
                    entry["parse_status"],
                    entry["not_read_message_counts"],
                    entry["developer_field_count"],
                    entry["unknown_records"],
                ),
                ("parsed_activity", {"0": 1, "21": 2}, 4, 0),
            )
            self.assertNotIn("not_read_message_counts", fit_entry(results["plain"]))
            self.assertNotIn("developer_field_count", fit_entry(results["plain"]))
            plain, others = results["plain"], results["others"]
            self.assertEqual(
                load(others / "diagnostics/source_completeness.json"),
                load(plain / "diagnostics/source_completeness.json"),
            )
            for name in ("status", "warnings", "normalized_record_count", "family_results"):
                with self.subTest(field=name):
                    self.assertEqual(load(others / "run_summary.json")[name], load(plain / "run_summary.json")[name])
            self.assertEqual(load(others / "run_summary.json")["family_results"]["fit"]["incomplete_asset_count"], 0)
            self.assertEqual(len(load(others / "normalized/activity_fit_links.json")), 1)
            self.assertEqual(len(load(others / "normalized/hrv_daily.json")), 1)


class PrivacyTest(unittest.TestCase):
    def test_the_names_stay_in_the_audit_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ("PrivateFieldName", *OTHER_NAMES)
            source = write_export(root, "export", [_activity("A1", **{name: 1 for name in names})])
            output = root / "output"
            exit_code, console = run_cli(
                "run-all", "--input", str(source), "--output", str(output), "--external-safe-pack"
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(unread(output, "activities"), ({"PrivateFieldName": 1, "synthetic": 1}, len(OTHER_NAMES)))
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source, "S1", 1)
            snapshot = root / "snapshot"
            exit_code, snapshot_console = run_cli(
                "snapshot", "run-all", "--store", str(store), "--output", str(snapshot), "--external-safe-pack"
            )
            self.assertEqual(exit_code, 0)
            for run, text in ((output, console), (snapshot, snapshot_console)):
                bundle = root / f"support-{run.name}.zip"
                build_support_bundle(run, bundle)
                shared = [text, json.dumps(doctor_run_output(run))]
                for path in (bundle, run / "analysis/external_safe_handoff.zip"):
                    with zipfile.ZipFile(path) as archive:
                        shared.append(b"".join(archive.read(name) for name in archive.namelist()).decode("utf-8"))
                for name in names:
                    with self.subTest(run=run.name, name=name):
                        self.assertFalse(any(name in item for item in shared))


if __name__ == "__main__":
    unittest.main()
