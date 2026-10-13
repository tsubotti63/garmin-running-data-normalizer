"""Snapshots leave out the files that a run cannot read, as a one-shot run does (stage A3c-2)."""

from __future__ import annotations

import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.intake.archive import ArchiveLimits
from garmin_running_data_normalizer.intake.discovery import read_export
from garmin_running_data_normalizer.run_all import (
    ACTIVITIES_NOT_READABLE_MESSAGE,
    RunAllError,
    run_all,
)
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    verify_store,
)
from garmin_running_data_normalizer.snapshot.merge import ActivitiesNotReadableError
from garmin_running_data_normalizer.snapshot.store import load_manifests
from tests.fit_fixture_factory import synthetic_fit
from tests.test_repeated_records import day, table
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT, gear, load, personal_record, write_export
from tests.test_unreadable_files import (
    NOT_JSON,
    NOT_ZIP,
    UPLOADED,
    big_json,
    export,
    padding,
    write,
    zip_with,
)
from tests.test_zip_input import flip_member_byte, mark_encrypted, run_cli

# A limit for one file that synthetic files can exceed, for runs, for
# registration, and for the build.
SMALL = 64 * 1024
TABLES = (
    "activities",
    "gear",
    "activity_gear",
    "personal_records",
    "fit_sessions",
    "uds_daily",
    "sleep_daily",
    "vo2max_daily",
)


def register(store: Path, source: Path, label: str = "S1", number: int = 1) -> dict[str, Any]:
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=day(number),
        export_downloaded_at=day(number),
        export_observed_at=day(number),
        confirm_complete=True,
    )


def small_limits() -> "_Patches":
    """Lower the limit for one file in runs, in registration, and in the build."""
    limits = ArchiveLimits(max_member_bytes=SMALL)
    patches = [
        mock.patch(
            "garmin_running_data_normalizer.run_all.read_export",
            side_effect=lambda path: read_export(path, limits),
        ),
        mock.patch(
            "garmin_running_data_normalizer.snapshot.store.open_export",
            side_effect=lambda path: _open_export(path, limits),
        ),
        mock.patch("garmin_running_data_normalizer.snapshot.merge.SOURCE_FILE_MAX_BYTES", SMALL),
    ]
    return _Patches(patches)


def _open_export(path: Path, limits: ArchiveLimits) -> Any:
    from garmin_running_data_normalizer.intake.roots import open_export

    return open_export(path, limits)


class _Patches:
    def __init__(self, patches: list[Any]) -> None:
        self.patches = patches

    def __enter__(self) -> None:
        for patch in self.patches:
            patch.start()

    def __exit__(self, *exc_info: object) -> None:
        for patch in reversed(self.patches):
            patch.stop()


def export_zip(folder: Path) -> Path:
    """The Export as a ZIP file, stored without compression, so that no
    member of the Export ZIP file exceeds the compression ratio."""
    target = folder.parent / "export.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(folder).as_posix())
    return target


def one_snapshot(root: Path, source: Path, name: str = "snapshot") -> Path:
    store = root / f"{name}-store"
    initialize_store(store, ACCOUNT)
    register(store, source)
    output = root / name
    run_snapshot_all(store, output)
    return output


def listed(output: Path, key: str) -> list[dict[str, Any]]:
    return list(load(output / "run_manifest.json").get(key, []))


def without_snapshot(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        ({field: value for field, value in item.items() if field != "snapshot"} for item in items),
        key=lambda item: item["source_path"],
    )


def outcome(output: Path) -> dict[str, Any]:
    """What a run of one Export gives, whatever the form of the run."""
    summary = load(output / "run_summary.json")
    return {
        "status": summary["status"],
        "warnings": sorted(
            (item["code"], item.get("family", ""), item.get("count", 1))
            for item in summary["warnings"]
        ),
        "files_left_out": without_snapshot(listed(output, "files_left_out")),
        "files_not_read": without_snapshot(listed(output, "files_not_read")),
        "tables": {dataset: table(output, dataset) for dataset in TABLES},
    }


def cases(root: Path) -> dict[str, Path]:
    """Exports with files that cannot be read, as folders and as ZIP files."""
    built: dict[str, Path] = {}

    def case(name: str) -> Path:
        source = export(root / "cases" / name)
        built[name] = source
        return source

    source = case("JSON that is not JSON")
    write(source / "DI-Connect-Fitness/other_summarizedActivities.json", NOT_JSON)
    source = case("JSON nested too deeply")
    write(source / "DI-Connect-Aggregator/UDSFile_deep.json", b"[" * 100_000 + b"]" * 100_000)
    source = case("JSON with a number with too many digits")
    write(source / "DI-Connect-Aggregator/UDSFile_long.json", b"[" + b"1" * 5_000 + b"]")
    source = case("JSON that is not UTF-8")
    write(
        source / "DI-Connect-Fitness/other_gear.json",
        '[{"gearDTOS": [{"gearPk": 9, "displayName": "Caf\xe9"}]}]'.encode("latin-1"),
    )
    source = case("JSON that no dataset reads and that is not JSON")
    write(source / "DI-Connect-User/synthetic_settings.json", NOT_JSON)
    source = case("ZIP file that is not a ZIP file")
    write(source / f"{UPLOADED}/UploadedFiles_broken_Part1.zip", NOT_ZIP)
    source = case("ZIP file with a damaged member")
    valid = zip_with(root / "valid.zip", {"synthetic-session-1.fit": synthetic_fit()})
    write(
        source / f"{UPLOADED}/UploadedFiles_damaged_Part1.zip",
        flip_member_byte(valid, "synthetic-session-1.fit", root / "damaged.zip").read_bytes(),
    )
    source = case("ZIP file with an unsafe member")
    zip_with(source / f"{UPLOADED}/UploadedFiles_unsafe_Part1.zip", {"../synthetic-escape.fit": synthetic_fit()})
    source = case("ZIP file with an encrypted member")
    write(
        source / f"{UPLOADED}/UploadedFiles_encrypted_Part1.zip",
        mark_encrypted(
            zip_with(root / "plain.zip", {"synthetic-session-1.fit": synthetic_fit()}),
            "synthetic-session-1.fit",
            root / "encrypted.zip",
        ).read_bytes(),
    )
    source = case("ZIP file with a link")
    link = zipfile.ZipInfo("synthetic-link.fit")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    zip_with(source / f"{UPLOADED}/UploadedFiles_link_Part1.zip", {link: b"synthetic-session-1.fit"})
    folders = dict(built)
    for name, folder in folders.items():
        built[f"{name}, in an Export ZIP file"] = export_zip(folder)
    return built


def size_cases(root: Path) -> dict[str, Path]:
    """Exports with files over the small limit for one file."""
    built: dict[str, Path] = {}

    def case(name: str) -> Path:
        source = export(root / "size-cases" / name)
        built[name] = source
        return source

    source = case("FIT file over the limit")
    write(source / f"{UPLOADED}/synthetic_big.fit", synthetic_fit() + padding(70 * 1024))
    source = case("JSON file of a dataset over the limit")
    write(
        source / "DI-Connect-Aggregator/UDSFile_big.json",
        big_json([{"calendarDate": "2030-02-02", "totalSteps": 2}]),
    )
    source = case("JSON file that no dataset reads over the limit")
    write(source / "DI-Connect-User/synthetic_big_user.json", big_json([]))
    source = case("members of a ZIP file over the limit")
    zip_with(
        source / f"{UPLOADED}/UploadedFiles_big_Part1.zip",
        {
            "synthetic-session-1.fit": synthetic_fit(),
            "synthetic-big.fit": synthetic_fit() + padding(70 * 1024),
            "synthetic-big-notes.json": big_json([]),
            "synthetic-big-video.mp4": padding(70 * 1024),
        },
    )
    folders = dict(built)
    for name, folder in folders.items():
        built[f"{name}, in an Export ZIP file"] = export_zip(folder)
    return built


class SnapshotLeftOutTest(unittest.TestCase):
    def test_one_export_gives_the_same_outcome_in_both_forms_of_run(self) -> None:
        # Decision 20261011-25: the same Export gives the same status,
        # warnings, lists of files, and tables, as one Snapshot or in a
        # one-shot run.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (name, source) in enumerate(cases(root).items()):
                with self.subTest(case=name):
                    one_shot = root / f"one-shot-{index}"
                    run_all(source, one_shot)
                    snapshot = one_snapshot(root, source, f"snapshot-{index}")
                    self.assertEqual(outcome(snapshot), outcome(one_shot))
                    # A JSON file that no dataset reads is not read, in
                    # either form; every other case leaves a file out.
                    left_out = listed(snapshot, "files_left_out")
                    self.assertEqual(
                        bool(left_out),
                        not name.startswith("JSON that no dataset reads"),
                    )
                    self.assertTrue(all(item["snapshot"] == 1 for item in left_out))

    def test_files_over_the_limit_give_the_same_outcome_in_both_forms_of_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (name, source) in enumerate(size_cases(root).items()):
                with self.subTest(case=name), small_limits():
                    one_shot = root / f"one-shot-{index}"
                    run_all(source, one_shot)
                    snapshot = one_snapshot(root, source, f"snapshot-{index}")
                    self.assertEqual(outcome(snapshot), outcome(one_shot))
                    self.assertTrue(
                        listed(snapshot, "files_left_out") or listed(snapshot, "files_not_read")
                    )

    def test_registration_keeps_a_zip_file_whole_with_the_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            built = cases(root)
            expected = {
                "ZIP file that is not a ZIP file": ("UploadedFiles_broken_Part1.zip", "zip_not_readable"),
                "ZIP file with a damaged member": ("UploadedFiles_damaged_Part1.zip", "zip_not_readable"),
                "ZIP file with an unsafe member": ("UploadedFiles_unsafe_Part1.zip", "zip_unsafe_member"),
                "ZIP file with an encrypted member": ("UploadedFiles_encrypted_Part1.zip", "zip_unsafe_member"),
                "ZIP file with a link": ("UploadedFiles_link_Part1.zip", "zip_unsafe_member"),
            }
            for index, (name, (zip_name, reason)) in enumerate(expected.items()):
                with self.subTest(case=name):
                    store = root / f"store-{index}"
                    initialize_store(store, ACCOUNT)
                    register(store, built[name])
                    rows = load_manifests(store)[0]["objects"]
                    zip_rows = [row for row in rows if zip_name in row["relative_path"]]
                    # The ZIP file is stored whole, without its members.
                    self.assertEqual(
                        [(row["object_kind"], row["relative_path"], row["parser_state"]) for row in zip_rows],
                        [("file", f"{UPLOADED}/{zip_name}", reason)],
                    )
                    self.assertEqual(verify_store(store)["status"], "PASS")
            # An Export without such files is registered as before.
            store = root / "plain-store"
            initialize_store(store, ACCOUNT)
            register(store, export(root, "plain"))
            self.assertEqual(
                {row["parser_state"] for row in load_manifests(store)[0]["objects"]},
                {"parser_unsupported"},
            )

    def test_registration_does_not_list_members_over_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = size_cases(root)["members of a ZIP file over the limit"]
            store = root / "store"
            initialize_store(store, ACCOUNT)
            with small_limits():
                register(store, source)
            paths = {
                row["relative_path"]: row["parser_state"] for row in load_manifests(store)[0]["objects"]
            }
            container = f"{UPLOADED}/UploadedFiles_big_Part1.zip"
            self.assertEqual(paths[container], "parser_unsupported")
            self.assertIn(f"{container}!synthetic-session-1.fit", paths)
            for member in ("synthetic-big.fit", "synthetic-big-notes.json", "synthetic-big-video.mp4"):
                self.assertNotIn(f"{container}!{member}", paths)

    def test_files_are_listed_by_snapshot_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for number in (1, 2):
                source = export(root / f"export-{number}")
                write(source / f"{UPLOADED}/UploadedFiles_broken_Part1.zip", NOT_ZIP + bytes([number]))
                write(source / f"DI-Connect-Aggregator/UDSFile_other_{number}.json", NOT_JSON)
                register(store, source, f"S{number}", number)
            output = root / "output"
            exit_code, console = run_cli("snapshot", "run-all", "--store", str(store), "--output", str(output))
            self.assertEqual(exit_code, 3)
            self.assertIn("STATUS: PARTIAL_SUCCESS", console)
            self.assertEqual(
                [(item["snapshot"], item["source_path"], item["family"], item["reason"]) for item in listed(output, "files_left_out")],
                [
                    (1, "DI-Connect-Aggregator/UDSFile_other_1.json", "uds", "json_not_readable"),
                    (1, f"{UPLOADED}/UploadedFiles_broken_Part1.zip", "unclassified", "zip_not_readable"),
                    (2, "DI-Connect-Aggregator/UDSFile_other_2.json", "uds", "json_not_readable"),
                    (2, f"{UPLOADED}/UploadedFiles_broken_Part1.zip", "unclassified", "zip_not_readable"),
                ],
            )
            summary = load(output / "run_summary.json")
            self.assertIn(
                {
                    "code": "DATA_FILE_LEFT_OUT",
                    "count": 4,
                    "message": (
                        "one or more files could not be read and were left out; "
                        "run_manifest.json lists them with the reason"
                    ),
                },
                summary["warnings"],
            )
            self.assertIn(
                "- Files left out: 4, which could not be read",
                (output / "START_HERE.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ("DATA_FILE_LEFT_OUT", "WARNING"),
                [(item["code"], item["severity"]) for item in doctor_run_output(output)["findings"]],
            )

    def test_records_of_a_file_left_out_of_an_earlier_snapshot(self) -> None:
        # The latest Snapshot's records are used, as when the earlier
        # Snapshot did not hold the file; nothing is marked.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            earlier = write_export(root, "earlier", [_activity("A1")])
            write(earlier / "DI-Connect-Fitness/synthetic_summarizedActivities.json", NOT_JSON)
            write(
                earlier / "DI-Connect-Fitness/other_summarizedActivities.json",
                json.dumps([{"summarizedActivitiesExport": [_activity("A0")]}]).encode("utf-8"),
            )
            register(store, earlier, "S1", 1)
            register(store, write_export(root, "latest", [_activity("A1", name="latest")]), "S2", 2)
            output = root / "output"
            run_snapshot_all(store, output)
            names = {row["garmin_activity_key"]: row["name"] for row in load(output / "normalized/activities.json")}
            self.assertEqual(names["garmin_activity:A1"], "latest")
            missing = load(output / "audit/activities.json")["not_in_latest_snapshot"]
            self.assertEqual([item.get("latest_file_left_out") for item in missing], [None])
            self.assertNotIn("not_in_latest_file_left_out_count", load(output / "run_summary.json"))

    def test_records_of_a_file_left_out_of_the_latest_snapshot_are_kept_and_marked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for number in (1, 2):
                source = write_export(
                    root,
                    f"export-{number}",
                    [_activity("A1"), _activity("A2")],
                    gear_rows=[gear(1, "Synthetic Shoe")],
                    links={"1": ["A1"]},
                    records=[personal_record(1, "A1", 1.0)],
                )
                register(store, source, f"S{number}", number)
            # The latest Export shows Gear 1 without its link to A1.
            latest = write_export(
                root,
                "export-3",
                [_activity("A3")],
                gear_rows=[gear(1, "Synthetic Shoe")],
                links={"1": []},
                records=[personal_record(1, "A1", 1.0)],
            )
            # The latest Export's Activities file that held A1 and A2 cannot be read.
            write(latest / "DI-Connect-Fitness/other_summarizedActivities.json", NOT_JSON)
            register(store, latest, "S3", 3)
            output = root / "output"
            run_snapshot_all(store, output)
            keys = sorted(row["garmin_activity_key"] for row in load(output / "normalized/activities.json"))
            self.assertEqual(keys, ["garmin_activity:A1", "garmin_activity:A2", "garmin_activity:A3"])
            missing = load(output / "audit/activities.json")["not_in_latest_snapshot"]
            self.assertEqual(len(missing), 2)
            self.assertTrue(all(item["latest_file_left_out"] is True for item in missing))
            # The link stays: the latest Snapshot does not show its Activity.
            self.assertEqual(len(load(output / "normalized/activity_gear.json")), 1)
            summary = load(output / "run_summary.json")
            codes = {item["code"] for item in summary["warnings"]}
            self.assertTrue({"DATA_FILE_LEFT_OUT", "RECORDS_NOT_IN_LATEST_SNAPSHOT"} <= codes)
            self.assertEqual(summary["not_in_latest_file_left_out_count"], 2)
            self.assertIn(
                "- Records kept with their values from earlier Snapshots: 2, because a file "
                "of the latest Snapshot was left out; the audit records mark them",
                (output / "START_HERE.md").read_text(encoding="utf-8"),
            )

    def test_activities_files_that_all_cannot_be_read_stop_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / "DI-Connect-Fitness/synthetic_summarizedActivities.json", NOT_JSON)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source)
            with self.assertRaises(RunAllError) as raised:
                run_snapshot_all(store, root / "output")
            self.assertEqual(
                (raised.exception.code, raised.exception.safe_message),
                ("ACTIVITIES_EMPTY", ACTIVITIES_NOT_READABLE_MESSAGE),
            )
            self.assertFalse((root / "output").exists())
            with self.assertRaisesRegex(ActivitiesNotReadableError, "the Activities files could not be read"):
                build_approved_input(store, root / "build")

    def test_accounts_of_a_file_left_out_are_not_compared(self) -> None:
        # As in a run: a file that is left out or not read names no account,
        # also when it can be parsed.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            for path, account in (
                ("DI-Connect-Fitness/big_summarizedActivities.json", 1234567),
                ("DI-Connect-Fitness/other_summarizedActivities.json", 7654321),
            ):
                write(
                    source / path,
                    big_json([{"summarizedActivitiesExport": [{"activityId": "A9", "userProfileId": account}]}]),
                )
            write(
                source / "DI-Connect-Fitness/synthetic_summarizedActivities.json",
                json.dumps(
                    [{"summarizedActivitiesExport": [_activity("A1", userProfileId=1111111)]}]
                ).encode("utf-8"),
            )
            store = root / "store"
            initialize_store(store, ACCOUNT)
            with small_limits():
                register(store, source)
                output = root / "output"
                self.assertEqual(run_snapshot_all(store, output)["status"], "PARTIAL_SUCCESS")
            self.assertEqual(
                [(item["source_path"], item["reason"]) for item in listed(output, "files_left_out")],
                [
                    ("DI-Connect-Fitness/big_summarizedActivities.json", "file_too_large"),
                    ("DI-Connect-Fitness/other_summarizedActivities.json", "file_too_large"),
                ],
            )

    def test_the_names_of_left_out_files_stay_in_the_local_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / f"{UPLOADED}/Private-left-out_Part1.zip", NOT_ZIP)
            write(source / "DI-Connect-Fitness/Private-left-out_summarizedActivities.json", NOT_JSON)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register_snapshot(
                store,
                source,
                snapshot_label="Private-label",
                export_requested_at=day(1),
                export_downloaded_at=day(1),
                export_observed_at=day(1),
                confirm_complete=True,
            )
            output = root / "output"
            exit_code, console = run_cli(
                "snapshot", "run-all", "--store", str(store), "--output", str(output), "--external-safe-pack"
            )
            self.assertEqual(exit_code, 3)
            self.assertNotIn("Private-left-out", console)
            self.assertEqual(len(listed(output, "files_left_out")), 2)
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with self.subTest(file=path.name), zipfile.ZipFile(path) as archive:
                    content = b"".join(archive.read(name) for name in archive.namelist())
                    self.assertNotIn(b"Private-left-out", content)
                    self.assertNotIn(b"Private-label", content)


if __name__ == "__main__":
    unittest.main()
