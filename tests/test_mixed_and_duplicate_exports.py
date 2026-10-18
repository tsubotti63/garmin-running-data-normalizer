"""Inputs that hold more than one Export, or the same Export twice (stage A3a)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    verify_store,
)
from garmin_running_data_normalizer.snapshot.store import (
    _inventory_content_id,
    _inventory_document,
    _sha256_bytes,
    _stable_json_bytes,
    _write_registry,
    load_manifests,
)
from garmin_running_data_normalizer.intake.archive import ArchiveLimits
from garmin_running_data_normalizer.intake.roots import (
    MIXED_STORE_MESSAGE,
    OTHER_ACCOUNT_MESSAGE,
    FoundExport,
    MixedExportsError,
    open_export,
)
from garmin_running_data_normalizer.intake.source import ExportSource
from garmin_running_data_normalizer.stops import MIX_STOPS
from tests.test_snapshot_store_v1_7_1 import extract_store
from tests.test_zip_input import SYNTHETIC_NOT_READ, run_cli, write_export, zip_export

ACCOUNT = "synthetic-account-boundary"
# Long account numbers, which a SHA-256 written in hexadecimal does not hold
# by chance.
FIRST_ACCOUNT = 9876543210123
OTHER_ACCOUNT = 1234509876543


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def normalized(output: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((output / "normalized").glob("*.json"))}


def activity(activity_id: str, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "activityId": activity_id,
        "activityType": "running",
        "sportType": "running",
        "distance": 500000,
        "duration": 1800000,
        "startTimeGmt": 1893456000000,
        "startTimeLocal": "2030-01-01T09:00:00",
        "name": f"Synthetic {activity_id}",
    }
    row.update(fields)
    return row


def other_export(root: Path, *rows: dict[str, object]) -> Path:
    """Write a small Export with the given Activities."""
    fitness = root / "DI_CONNECT" / "DI-Connect-Fitness"
    fitness.mkdir(parents=True)
    (fitness / "synthetic_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": list(rows)}]), encoding="utf-8"
    )
    return root


def register(store: Path, source: Path, label: str, day: int) -> dict[str, object]:
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
        confirm_complete=True,
    )


def finding_codes(source: Path) -> list[str]:
    return [item["code"] for item in doctor_input(source)["findings"]]


class MixedExportsTest(unittest.TestCase):
    def test_different_exports_in_one_folder_stop_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = {
                "two accounts without shared activities": (
                    lambda parent: (
                        other_export(parent / "account-a", activity("A1")),
                        other_export(parent / "account-b", activity("B1")),
                    )
                ),
                # One Export holds only part of the other: a mix cannot be
                # ruled out.
                "one export and part of it": (
                    lambda parent: (
                        write_export(parent / "full"),
                        other_export(parent / "part", activity("SYNTHETIC-RUN-0001")),
                    )
                ),
            }
            for name, build in cases.items():
                with self.subTest(case=name):
                    parent = root / name.replace(" ", "-")
                    build(parent)
                    if name == "two accounts without shared activities":
                        # The same two Exports inside one ZIP file.
                        archive = zip_export(parent, root / "two-accounts.zip")
                        with self.assertRaises(RunAllError) as raised:
                            run_all(archive, root / "zip-output")
                        self.assertEqual(raised.exception.code, "INPUT_MULTIPLE_EXPORTS")
                    with self.assertRaises(RunAllError) as raised:
                        run_all(parent, root / f"{parent.name}-output")
                    self.assertEqual(raised.exception.code, "INPUT_MULTIPLE_EXPORTS")
                    self.assertFalse((root / f"{parent.name}-output").exists())
                    exit_code, console = run_cli(
                        "run-all", "--input", str(parent), "--output", str(root / f"{parent.name}-cli")
                    )
                    self.assertEqual(exit_code, 2)
                    self.assertIn("ERROR [INPUT_MULTIPLE_EXPORTS]", console)
                    self.assertNotIn(str(parent), console)
                    self.assertEqual(finding_codes(parent), ["INPUT_MULTIPLE_EXPORTS"])

    def test_records_of_two_accounts_in_one_export_stop_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mixed = other_export(
                root / "mixed",
                activity("A1", userProfileId=FIRST_ACCOUNT),
                activity("A2", userProfileId=FIRST_ACCOUNT),
            )
            metrics = mixed / "DI_CONNECT" / "DI-Connect-Aggregator"
            metrics.mkdir()
            (metrics / "UDSFile_synthetic.json").write_text(
                json.dumps(
                    [{"calendarDate": "2030-01-01", "totalSteps": 1000, "userProfilePK": OTHER_ACCOUNT}]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RunAllError) as raised:
                run_all(mixed, root / "output")
            self.assertEqual(raised.exception.code, "INPUT_MULTIPLE_EXPORTS")
            self.assertEqual(finding_codes(mixed), ["INPUT_MULTIPLE_EXPORTS"])
            exit_code, console = run_cli("run-all", "--input", str(mixed), "--output", str(root / "cli"))
            self.assertEqual(exit_code, 2)
            # No message names the accounts: not the error, the CLI, or the
            # pre-run check.
            for value in (FIRST_ACCOUNT, OTHER_ACCOUNT):
                self.assertNotIn(str(value), str(raised.exception))
                self.assertNotIn(str(value), raised.exception.safe_message)
                self.assertNotIn(str(value), console)
                self.assertNotIn(str(value), json.dumps(doctor_input(mixed)))
            # The same account written as a number and as text is one account,
            # and a run that does not stop writes the account nowhere.
            same = other_export(
                root / "same",
                activity("A1", userProfileId=FIRST_ACCOUNT),
                activity("A2", userProfileId=f" {FIRST_ACCOUNT}"),
            )
            run_all(same, root / "same-output")
            for path in (root / "same-output").rglob("*"):
                if path.is_file():
                    with self.subTest(file=path.name):
                        self.assertNotIn(str(FIRST_ACCOUNT).encode(), path.read_bytes())

    def test_the_same_export_twice_is_read_once_with_a_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alone = write_export(root / "alone" / "export")
            run_all(alone, root / "alone-output")
            expected = normalized(root / "alone-output")
            zip_and_folder = root / "zip-and-folder"
            folder = write_export(zip_and_folder / "export")
            zip_export(folder, zip_and_folder / "export.zip")
            # Finder adds metadata files to an extracted folder.
            (folder / ".DS_Store").write_bytes(b"synthetic metadata")
            (folder / "DI_CONNECT" / "._synthetic").write_bytes(b"synthetic metadata")
            two_folders = root / "two-folders"
            write_export(two_folders / "copy-a")
            write_export(two_folders / "copy-b")
            # The downloaded ZIP file kept inside the folder extracted from it.
            zip_inside = write_export(root / "zip-inside")
            zip_export(zip_inside, root / "download.zip")
            shutil.move(root / "download.zip", zip_inside / "download.zip")
            for parent in (zip_and_folder, two_folders, zip_inside):
                with self.subTest(input=parent.name):
                    output = root / f"{parent.name}-output"
                    result = run_all(parent, output)
                    self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
                    summary = load(output / "run_summary.json")
                    duplicates = [item for item in summary["warnings"] if item["code"] == "INPUT_DUPLICATE_SOURCES"]
                    self.assertEqual(duplicates, [{
                        "code": "INPUT_DUPLICATE_SOURCES",
                        "count": 1,
                        "message": "the input holds the same Export more than once; it was read once",
                    }])
                    self.assertEqual(summary["input_warning_count"], 1)
                    # Paths are counted from the Export, so the normalized
                    # datasets are those of the Export given alone.
                    self.assertEqual(normalized(output), expected)
                    self.assertEqual(
                        finding_codes(parent), ["INPUT_DUPLICATE_SOURCES", "RUN_ALL_NOT_EVALUATED"]
                    )
                    self.assertTrue(doctor_input(parent)["findings"][0]["severity"] == "WARNING")

    def test_an_export_zip_in_a_folder_is_read_as_when_selected_directly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "direct").mkdir()
            archive = zip_export(write_export(root / "export"), root / "direct" / "export.zip")
            run_all(archive, root / "direct-output")
            holder = root / "holder"
            holder.mkdir()
            shutil.copyfile(archive, holder / "export.zip")
            run_all(holder, root / "holder-output")
            direct = tree(root / "direct-output")
            held = tree(root / "holder-output")
            # The uploaded FIT files inside the Export ZIP file are read too.
            self.assertTrue(load(root / "holder-output/normalized/fit_sessions.json"))
            self.assertEqual(held, direct)

    def test_files_outside_the_export_are_listed_and_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent"
            write_export(parent / "export")
            (parent / "Outside-private-name.fit").write_bytes(b"synthetic outside")
            (parent / "Outside-private-notes.json").write_text("[]", encoding="utf-8")
            (parent / "Outside-private-readme.txt").write_text("synthetic", encoding="utf-8")
            output = root / "output"
            run_all(parent, output, external_safe_pack=True)
            run_all(parent / "export", root / "alone")
            self.assertEqual(normalized(output), normalized(root / "alone"))
            manifest = load(output / "run_manifest.json")
            # The files outside the Export of a form that a run reads come
            # first; one of another form is not listed. The Export's own
            # files of a form not read follow (stage A4b), as when the Export
            # is given alone.
            alone = load(root / "alone/run_manifest.json")["files_not_read"]
            self.assertEqual(
                manifest["files_not_read"],
                [
                    {"source_path": "Outside-private-name.fit", "bytes": 17, "reason": "outside_export_root"},
                    {"source_path": "Outside-private-notes.json", "bytes": 2, "reason": "outside_export_root"},
                    *alone,
                ],
            )
            self.assertEqual(
                [(item["source_path"], item["reason"]) for item in alone], SYNTHETIC_NOT_READ
            )
            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn(
                f"- Files not read: {2 + len(alone)}; `run_manifest.json` lists them with the reason",
                start_here,
            )
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with self.subTest(file=path.name), zipfile.ZipFile(path) as archive:
                    content = b"".join(archive.read(name) for name in archive.namelist())
                    self.assertNotIn(b"Outside-private", content)


class MixedExportPlacesTest(unittest.TestCase):
    """The Exports of a mixed input are named where the check is started:
    in the report for a person and on the page, never in the JSON report or
    an output (stage B3c)."""

    def mixed(self, root: Path) -> Path:
        """Two different Exports, and a ZIP file of the first one."""
        parent = root / "input"
        other_export(parent / "export-a", activity("A1"))
        zip_export(parent / "export-a", parent / "export-a.zip")
        other_export(parent / "export-b", activity("B1"))
        return parent

    def test_the_exports_found_are_named_with_the_same_files(self) -> None:
        from garmin_running_data_normalizer.diagnostics.doctor import render_doctor_human

        with tempfile.TemporaryDirectory() as directory:
            parent = self.mixed(Path(directory))
            with self.assertRaises(MixedExportsError) as raised:
                with open_export(parent):
                    pass
            self.assertEqual(
                raised.exception.found,
                [
                    FoundExport("export-a", False, None),
                    FoundExport("export-a.zip", True, "export-a"),
                    FoundExport("export-b", False, None),
                ],
            )
            details: dict[str, object] = {}
            report = doctor_input(parent, details=details)
            self.assertEqual(
                details["exports_found"],
                [
                    {"place": "export-a", "zip": False, "same_as": None},
                    {"place": "export-a.zip", "zip": True, "same_as": "export-a"},
                    {"place": "export-b", "zip": False, "same_as": None},
                ],
            )
            # The report holds no place, as before.
            for name in ("export-a", "export-b"):
                self.assertNotIn(name, json.dumps(report))
            lines = render_doctor_human(report, details).splitlines()
            index = lines.index(next(line for line in lines if line.startswith("Finding: INPUT_MULTIPLE_EXPORTS")))
            self.assertEqual(
                lines[index + 1 : index + 4],
                [
                    "Export found: export-a",
                    "Export found: export-a.zip (ZIP file) (the same Export as export-a)",
                    "Export found: export-b",
                ],
            )
            self.assertNotIn("Export found", render_doctor_human(report))
            # The CLI names them in the report for a person only.
            exit_code, console = run_cli("doctor", "--input", str(parent))
            self.assertEqual(exit_code, 0)
            self.assertIn("Export found: export-a.zip (ZIP file) (the same Export as export-a)", console)
            exit_code, console = run_cli("doctor", "--input", str(parent), "--format", "json")
            self.assertEqual(exit_code, 0)
            for name in ("export-a", "export-b"):
                self.assertNotIn(name, console)

    def test_a_mix_without_places_names_no_export(self) -> None:
        from garmin_running_data_normalizer.diagnostics.doctor import render_doctor_human

        with tempfile.TemporaryDirectory() as directory:
            source = other_export(
                Path(directory) / "accounts",
                activity("A1", userProfileId=FIRST_ACCOUNT),
                activity("A2", userProfileId=OTHER_ACCOUNT),
            )
            details: dict[str, object] = {}
            report = doctor_input(source, details=details)
            self.assertEqual([item["code"] for item in report["findings"]], ["INPUT_MULTIPLE_EXPORTS"])
            self.assertEqual(details, {})
            self.assertNotIn("Export found", render_doctor_human(report, details))
            self.assertEqual(MixedExportsError().found, [])

    @unittest.skipIf(os.name == "nt", "Windows takes no line break in a name")
    def test_a_name_that_cannot_be_shown_is_not_written(self) -> None:
        from garmin_running_data_normalizer.diagnostics.doctor import render_doctor_human

        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "input"
            other_export(parent / "export-a", activity("A1"))
            other_export(parent / "line\nbreak", activity("B1"))
            other_export(parent / "turned\u202eexport", activity("C1"))
            zip_export(parent / "line\nbreak", parent / "same\tcontent.zip")
            details: dict[str, object] = {}
            report = doctor_input(parent, details=details)
            text = render_doctor_human(report, details)
            self.assertIn("Export found: (a name that cannot be shown)\n", text + "\n")
            self.assertIn(
                "Export found: (a name that cannot be shown) (ZIP file) (the same Export as (a name that cannot be shown))",
                text,
            )
            self.assertNotIn("line\nbreak", text)
            self.assertNotIn("same\tcontent", text)
            self.assertNotIn("\u202e", text)

    def test_many_exports_are_named_up_to_twenty(self) -> None:
        from garmin_running_data_normalizer.diagnostics.doctor import render_doctor_human

        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "input"
            for number in range(22):
                other_export(parent / f"export-{number:02d}", activity(f"A{number}"))
            details: dict[str, object] = {}
            report = doctor_input(parent, details=details)
            lines = [line for line in render_doctor_human(report, details).splitlines() if line.startswith("Export found: ")]
            self.assertEqual(len(details["exports_found"]), 22)
            self.assertEqual(len(lines), 21)
            self.assertEqual(lines[-1], "Export found: and 2 more")

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs a folder that cannot be opened")
    def test_a_folder_that_cannot_be_opened_is_named_by_the_check(self) -> None:
        from garmin_running_data_normalizer.diagnostics.doctor import render_doctor_human

        with tempfile.TemporaryDirectory() as directory:
            source = write_export(Path(directory) / "export")
            closed = source / "DI_CONNECT" / "DI-Connect-Fitness" / "synthetic-private-folder"
            closed.mkdir()
            closed.chmod(0)
            details: dict[str, object] = {}
            try:
                report = doctor_input(source, details=details)
            finally:
                closed.chmod(0o700)
            self.assertEqual([item["code"] for item in report["findings"]], ["INPUT_NOT_READABLE"])
            self.assertEqual(details["not_readable_places"], ["DI_CONNECT/DI-Connect-Fitness/synthetic-private-folder"])
            self.assertNotIn("synthetic-private-folder", json.dumps(report))
            lines = render_doctor_human(report, details).splitlines()
            self.assertIn("Cannot be opened: DI_CONNECT/DI-Connect-Fitness/synthetic-private-folder", lines)


class SnapshotRegistrationTest(unittest.TestCase):
    def test_registration_refuses_different_exports_and_keeps_one_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            mixed = root / "mixed"
            other_export(mixed / "a", activity("A1"))
            other_export(mixed / "b", activity("B1"))
            with self.assertRaises(MixedExportsError):
                register(store, mixed, "S1", 1)
            exit_code, console = run_cli(
                "snapshot", "register", "--store", str(store), "--input", str(mixed), "--label", "S1",
                "--requested-at", "2030-01-01T00:00:00+00:00", "--downloaded-at", "2030-01-01T01:00:00+00:00",
                "--observed-at", "2030-01-01T02:00:00+00:00", "--confirm-complete",
            )
            self.assertEqual(exit_code, 2)
            self.assertIn("ERROR [INPUT_MULTIPLE_EXPORTS]", console)
            self.assertEqual(load_manifests(store), [])
            # The same Export twice is registered once, as the Export alone.
            pair = root / "pair"
            folder = write_export(pair / "export")
            zip_export(folder, pair / "export.zip")
            result = register(store, pair, "S1", 1)
            self.assertEqual(result["same_export_count"], 1)
            alone_store = root / "alone-store"
            initialize_store(alone_store, ACCOUNT)
            register(alone_store, write_export(root / "alone"), "S1", 1)
            self.assertEqual(
                load_manifests(store)[0]["snapshot_content_id"],
                load_manifests(alone_store)[0]["snapshot_content_id"],
            )
            # An Export ZIP file in a folder is registered as the ZIP file alone.
            holder = root / "holder"
            holder.mkdir()
            zip_export(write_export(root / "zipped"), holder / "export.zip")
            holder_store = root / "holder-store"
            initialize_store(holder_store, ACCOUNT)
            register(holder_store, holder, "S1", 1)
            self.assertEqual(
                load_manifests(holder_store)[0]["snapshot_content_id"],
                load_manifests(alone_store)[0]["snapshot_content_id"],
            )

    def test_the_same_export_registered_again_is_not_a_new_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = extract_store(root / "store")
            first = load_manifests(store)[0]
            # The first Snapshot's Export, written again from the store,
            # inside wrapping folders and as a ZIP file.
            export = root / "again" / "wrapper" / "export"
            for row in first["objects"]:
                if row["object_kind"] != "file":
                    continue
                path = export / row["relative_path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(store / row["blob_relative_path"], path)
            archive = zip_export(export, root / "again.zip", wrapper="Garmin Export")
            for source, label, day in ((root / "again", "AGAIN", 9), (archive, "ZIPPED", 10)):
                with self.subTest(source=source.name):
                    result = register(store, source, label, day)
                    self.assertTrue(result["registration_was_idempotent"])
                    self.assertEqual(result["same_content_as"], {"snapshot_label": "S1", "logical_order": 1})
                    self.assertEqual(len(load_manifests(store)), 2)
            self.assertEqual(verify_store(store)["status"], "PASS")

    def test_snapshots_with_the_same_content_are_counted_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = extract_store(root / "store")
            manifests = load_manifests(store)
            # A Snapshot that v1.7.1 registered from inside a wrapping folder:
            # the first Snapshot's files under other paths, observed last.
            copy = json.loads(json.dumps(manifests[0]))
            for row in copy["objects"]:
                row["relative_path"] = f"Wrapper/{row['relative_path']}"
                if row.get("container_relative_path"):
                    row["container_relative_path"] = f"Wrapper/{row['container_relative_path']}"
            copy["snapshot_label"] = "S1-WRAPPED"
            copy["export_requested_at"] = "2030-01-09T00:00:00+00:00"
            copy["export_downloaded_at"] = "2030-01-09T01:00:00+00:00"
            copy["export_observed_at"] = "2030-01-09T02:00:00+00:00"
            copy["snapshot_content_id"] = _inventory_content_id(copy["objects"])
            copy["snapshot_id"] = "snapshot-" + _sha256_bytes(
                _stable_json_bytes(
                    {
                        "account_store_id": copy["account_store_id"],
                        "export_observed_at": copy["export_observed_at"],
                        "snapshot_content_id": copy["snapshot_content_id"],
                    }
                )
            )
            folder = store / "snapshots" / copy["snapshot_id"]
            folder.mkdir()
            (folder / f"{copy['snapshot_id']}.inventory.json").write_text(
                json.dumps(_inventory_document(copy), indent=2, sort_keys=True), encoding="utf-8"
            )
            (folder / "manifest.json").write_text(json.dumps(copy, indent=2, sort_keys=True), encoding="utf-8")
            _write_registry(store, load_manifests(store))
            self.assertEqual(len(load_manifests(store)), 3)
            build = build_approved_input(store, root / "build")
            self.assertEqual(build["lineage"]["snapshot_count"], 2)
            self.assertEqual(build["lineage"]["same_content_snapshot_count"], 1)
            self.assertEqual(
                build["lineage"]["same_content_snapshots"],
                [{"snapshot_label": "S1-WRAPPED", "same_as_snapshot_number": 1}],
            )
            output = root / "output"
            run_snapshot_all(store, output)
            # The Export registered again later is not the latest Snapshot: the
            # second Snapshot's name stays.
            activities = {row["activity_id"]: row for row in load(output / "normalized/activities.json")}
            self.assertEqual(activities["SYNTHETIC-A2"]["name"], "Synthetic A2 after")
            start_here = (output / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("- Snapshots with the same content as an earlier one, counted once: 1", start_here)

    def test_a_store_holds_the_exports_of_one_account(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, other_export(root / "first", activity("A1", userProfileId=FIRST_ACCOUNT)), "S1", 1)
            other = other_export(root / "other", activity("B1", userProfileId=OTHER_ACCOUNT))
            with self.assertRaises(MixedExportsError) as refused:
                register(store, other, "S2", 2)
            self.assertEqual(len(load_manifests(store)), 1)
            # The next step is a store for the other account, not a Snapshot.
            exit_code, console = run_cli(
                "snapshot", "register", "--store", str(store), "--input", str(other), "--label", "S2",
                "--requested-at", "2030-01-02T00:00:00+00:00", "--downloaded-at", "2030-01-02T01:00:00+00:00",
                "--observed-at", "2030-01-02T02:00:00+00:00", "--confirm-complete",
            )
            self.assertEqual(exit_code, 2)
            # Each case of a mix says what to do (stage B4b-2).
            self.assertEqual(refused.exception.kind, "other_account")
            self.assertIn(
                f"ERROR [INPUT_MULTIPLE_EXPORTS]: {OTHER_ACCOUNT_MESSAGE}; {MIX_STOPS['other_account'].next_step}",
                console,
            )
            # A store that already holds two accounts, as one registered before
            # stage A3a could, stops the build.
            with mock.patch(
                "garmin_running_data_normalizer.snapshot.store._snapshot_accounts",
                return_value=set(),
            ):
                register(store, other, "S2", 2)
            with self.assertRaises(MixedExportsError) as stopped:
                build_approved_input(store, root / "build")
            exit_code, console = run_cli("snapshot", "run-all", "--store", str(store), "--output", str(root / "out"))
            self.assertEqual(exit_code, 2)
            self.assertEqual(stopped.exception.kind, "store")
            self.assertIn(
                f"ERROR [INPUT_MULTIPLE_EXPORTS]: {MIXED_STORE_MESSAGE}; {MIX_STOPS['store'].next_step}",
                console,
            )
            for value in (FIRST_ACCOUNT, OTHER_ACCOUNT):
                self.assertNotIn(str(value), console)
                self.assertNotIn(str(value), str(refused.exception))
                self.assertNotIn(str(value), str(stopped.exception))
            # The store keeps the Exports' files as they are, but writes the
            # accounts in none of its own records.
            for path in store.rglob("*.json"):
                with self.subTest(file=path.name):
                    for value in (FIRST_ACCOUNT, OTHER_ACCOUNT):
                        self.assertNotIn(str(value).encode(), path.read_bytes())


    def test_registration_compares_accounts_within_the_limits_of_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, other_export(root / "first", activity("A1", userProfileId=FIRST_ACCOUNT)), "S1", 1)
            # An Activities file beyond the size limit of a run is not read
            # whole to compare its accounts: the run reports that file.
            large = other_export(
                root / "large", activity("B1", userProfileId=OTHER_ACCOUNT, description="x" * 4000)
            )
            limits = ArchiveLimits(max_member_bytes=2000)
            reads: list[str] = []
            original = ExportSource.read

            def record_read(export: ExportSource, item: object) -> bytes:
                reads.append(item.relative_path)
                return original(export, item)

            with mock.patch(
                "garmin_running_data_normalizer.snapshot.store.open_export",
                side_effect=lambda path: open_export(path, limits),
            ), mock.patch.object(ExportSource, "read", record_read):
                result = register(store, large, "S2", 2)
            self.assertEqual(reads, [])
            self.assertFalse(result["registration_was_idempotent"])
            self.assertEqual(len(load_manifests(store)), 2)


if __name__ == "__main__":
    unittest.main()
