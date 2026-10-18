"""The Snapshot Store and the default places on the GUI page (stage B4a).

The page opens a store and lists its Snapshots, checks the place of a new
store, and checks a store, without writing anything in it. The default place
is GarminRunningData in the home folder, which a run makes alone when it is
the folder for the output; a place that a cloud may copy is named. Every
test replaces the home folder, so that nothing is made in the real one
(synthetic data only).
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer.gui import places, runs, stores
from garmin_running_data_normalizer.gui.places import cloud_kind, make_default_folder
from garmin_running_data_normalizer.gui.runs import RunActiveError, RunRequestError
from garmin_running_data_normalizer.gui.stores import ANSWER_CODES, check_store, download_time, open_store, store_place
from garmin_running_data_normalizer.snapshot import initialize_store, register_snapshot
from garmin_running_data_normalizer.snapshot.store import LOCK_NAME
from tests.test_environment_stops import REAL_PERMISSIONS, REAL_SYMLINKS, permissions
from tests.test_gui_runs import SYNTHETIC_EXPORT, child_environment, request, stub_manager
from tests.test_gui_server import GuiServerTestCase
from tests.test_snapshot_store_environment import tree

ACCOUNT = "synthetic-account-boundary"
STAMP = "2030-01-01T02:00:00+00:00"
LATER = "2030-02-01T02:00:00+00:00"


class HomeTestCase(unittest.TestCase):
    """A home folder of its own for each test."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        patcher = patch.object(places, "home", lambda: self.home)
        patcher.start()
        self.addCleanup(patcher.stop)

    def register(self, store: Path, label: str = "S1", stamp: str = STAMP) -> None:
        register_snapshot(
            store,
            SYNTHETIC_EXPORT,
            snapshot_label=label,
            export_requested_at=stamp,
            export_downloaded_at=stamp,
            export_observed_at=stamp,
            confirm_complete=True,
        )


class DefaultPlaceTest(HomeTestCase):
    def test_the_default_places_are_in_the_home_folder(self) -> None:
        self.assertEqual(places.default_folder(), self.home / "GarminRunningData")
        self.assertEqual(places.default_store(), self.home / "GarminRunningData" / "snapshots")

    def test_only_the_default_folder_is_made_and_only_when_nothing_is_there(self) -> None:
        folder = self.home / "GarminRunningData"
        # Another folder is never made.
        make_default_folder(self.root / "elsewhere")
        make_default_folder(self.home / "garminrunningdata-other")
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["home"])
        self.assertEqual(list(self.home.iterdir()), [])
        make_default_folder(folder)
        self.assertTrue(folder.is_dir())
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
        # A folder that is there stays as it is.
        (folder / "kept.txt").write_text("synthetic", encoding="utf-8")
        make_default_folder(folder)
        self.assertEqual([path.name for path in folder.iterdir()], ["kept.txt"])

    def test_a_file_or_a_link_there_is_left_to_the_checks_of_the_output(self) -> None:
        folder = self.home / "GarminRunningData"
        folder.write_bytes(b"a file")
        make_default_folder(folder)
        self.assertTrue(folder.is_file())
        folder.unlink()
        if os.name != "nt":
            folder.symlink_to(self.root / "nowhere", target_is_directory=True)
            make_default_folder(folder)
            self.assertTrue(folder.is_symlink())
            self.assertFalse((self.root / "nowhere").exists())

    def test_no_home_folder_makes_nothing(self) -> None:
        shutil.rmtree(self.home)
        make_default_folder(self.home / "GarminRunningData")
        self.assertFalse(self.home.exists())


class CloudTest(HomeTestCase):
    def test_folders_that_a_cloud_app_keeps_on_a_mac(self) -> None:
        library = self.home / "Library"
        cases = {
            library / "Mobile Documents" / "com~apple~CloudDocs" / "Garmin": "cloud",
            library / "CloudStorage" / "OneDrive-Personal" / "Garmin": "cloud",
            library / "cloudstorage" / "GoogleDrive-someone" / "Garmin": "cloud",
            self.home / "Documents" / "Garmin": "desktop_documents",
            self.home / "Desktop": "desktop_documents",
            self.home / "documents": "desktop_documents",
            # A cloud app's folder inside Documents is a cloud's.
            self.home / "Documents" / "Dropbox" / "Garmin": "cloud",
            self.home / "GarminRunningData": None,
            self.home / "GarminRunningData" / "snapshots": None,
            self.home / "Downloads": None,
            self.home / "DocumentsOld": None,
        }
        for path, kind in cases.items():
            with self.subTest(path=path.relative_to(self.home).as_posix()):
                self.assertEqual(cloud_kind(path, "darwin"), kind)

    def test_folders_that_a_cloud_app_keeps_on_windows_and_linux(self) -> None:
        onedrive = self.root / "OneDriveFolder"
        with patch.dict(os.environ, {"OneDrive": str(onedrive)}):
            self.assertEqual(cloud_kind(onedrive / "Documents" / "Garmin", "win32"), "cloud")
            self.assertIsNone(cloud_kind(self.home / "Documents", "win32"))
        self.assertEqual(cloud_kind(self.home / "iCloudDrive" / "Garmin", "win32"), "cloud")
        self.assertEqual(cloud_kind(self.root / "OneDrive - Example Org" / "Garmin", "win32"), "cloud")
        self.assertEqual(cloud_kind(self.home / "Dropbox" / "Garmin", "linux"), "cloud")
        self.assertIsNone(cloud_kind(self.home / "Documents", "linux"))
        self.assertIsNone(cloud_kind(self.home / "GarminRunningData", "win32"))

    @REAL_SYMLINKS
    def test_a_link_into_a_cloud_folder_counts(self) -> None:
        cloud = self.home / "Library" / "Mobile Documents" / "Garmin"
        cloud.mkdir(parents=True)
        link = self.home / "GarminRunningData"
        link.symlink_to(cloud, target_is_directory=True)
        self.assertEqual(cloud_kind(link / "snapshots", "darwin"), "cloud")


class StoreAnswerTest(HomeTestCase):
    def assert_nothing_written(self, action: Any, *arguments: Any) -> dict[str, Any]:
        before = tree(self.root)
        answer = action(*arguments)
        self.assertEqual(tree(self.root), before)
        if answer.get("error_code") is not None:
            self.assertIn(answer["error_code"], ANSWER_CODES)
        for code in answer.get("notices", []):
            self.assertIn(code, ANSWER_CODES)
        return answer

    def test_a_store_and_its_snapshots(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        self.register(store, "LATER", LATER)
        self.register_other_export(store)
        answer = self.assert_nothing_written(open_store, store)
        self.assertEqual(answer["state"], "store")
        self.assertEqual(answer["path"], str(store))
        self.assertEqual(answer["notices"], [])
        self.assertIsNone(answer["cloud"])
        # In the order of the times of their exports, not of their imports.
        self.assertEqual([item["label"] for item in answer["snapshots"]], ["EARLIER", "LATER"])
        self.assertEqual([item["order"] for item in answer["snapshots"]], [1, 2])
        first = answer["snapshots"][0]
        self.assertEqual(sorted(first), ["files", "label", "observed_at", "order"])
        self.assertEqual(first["observed_at"], "2030-01-15T02:00:00+00:00")
        self.assertIsInstance(first["files"], int)
        self.assertGreater(first["files"], 0)

    def register_other_export(self, store: Path) -> None:
        other = self.root / "other-export"
        shutil.copytree(SYNTHETIC_EXPORT, other)
        (other / "notes.txt").write_text("another export", encoding="utf-8")
        register_snapshot(
            store,
            other,
            snapshot_label="EARLIER",
            export_requested_at="2030-01-15T02:00:00+00:00",
            export_downloaded_at="2030-01-15T02:00:00+00:00",
            export_observed_at="2030-01-15T02:00:00+00:00",
            confirm_complete=True,
        )

    def test_the_store_in_the_folder_snapshots_of_a_chosen_folder_opens(self) -> None:
        holder = self.root / "GarminRunningData"
        holder.mkdir()
        initialize_store(holder / "snapshots", ACCOUNT)
        (holder / "garmin-run-all-20301009-0930").mkdir()
        for action in (open_store, store_place):
            with self.subTest(action=action.__name__):
                answer = self.assert_nothing_written(action, holder)
                self.assertEqual((answer["state"], answer["path"]), ("store", str(holder / "snapshots")))
                self.assertEqual(answer["snapshots"], [])

    def test_the_problems_of_a_store(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(
            self.assert_nothing_written(open_store, empty),
            {"state": "error", "path": str(empty), "error_code": "SNAPSHOT_STORE_NOT_FOUND"},
        )
        damaged = self.root / "damaged"
        initialize_store(damaged, ACCOUNT)
        (damaged / "store.json").unlink()
        self.assertEqual(self.assert_nothing_written(open_store, damaged)["error_code"], "SNAPSHOT_STORE_INVALID")
        newer = self.root / "newer"
        initialize_store(newer, ACCOUNT)
        metadata = json.loads((newer / "store.json").read_text(encoding="utf-8"))
        metadata["format"] = "garmin-running-data-normalizer-snapshot-store-v9"
        (newer / "store.json").write_text(json.dumps(metadata), encoding="utf-8")
        self.assertEqual(
            self.assert_nothing_written(open_store, newer)["error_code"], "SNAPSHOT_STORE_VERSION_UNSUPPORTED"
        )

    @REAL_SYMLINKS
    def test_a_link_to_a_store_is_not_opened(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        link = self.root / "link"
        link.symlink_to(store, target_is_directory=True)
        for action in (open_store, store_place, check_store):
            with self.subTest(action=action.__name__):
                answer = self.assert_nothing_written(action, link)
                self.assertEqual(answer["error_code"], "SNAPSHOT_STORE_SYMLINK")

    @REAL_PERMISSIONS
    def test_a_store_that_cannot_be_opened_names_its_place(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        with permissions(store, 0o000):
            answer = open_store(store)
        self.assertEqual(answer["error_code"], "SNAPSHOT_STORE_NOT_READABLE")
        # "" is the store's folder itself, which the page names as such.
        self.assertEqual(answer["detail"], {"place": "", "more": 0, "store": True})

    def test_the_notices_of_a_store(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        (store / LOCK_NAME).write_text("12345\n", encoding="ascii")
        (store / "journal" / "registration.json").write_text("{}", encoding="utf-8")
        answer = self.assert_nothing_written(open_store, store)
        self.assertEqual(answer["notices"], ["SNAPSHOT_STORE_LOCKED", "SNAPSHOT_REGISTRATION_INCOMPLETE"])
        checked = self.assert_nothing_written(check_store, store)
        self.assertEqual(checked["error_code"], "SNAPSHOT_REGISTRATION_INCOMPLETE")

    def test_the_check_of_a_store(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        self.register(store)
        self.assertEqual(
            self.assert_nothing_written(check_store, store),
            {"state": "checked", "path": str(store), "snapshot_count": 1, "notices": []},
        )
        # A changed file of a Snapshot fails the check, as snapshot verify.
        blob = next(path for path in (store / "blobs" / "sha256").rglob("*") if path.is_file())
        blob.chmod(0o600)
        blob.write_bytes(b"changed")
        self.assertEqual(self.assert_nothing_written(check_store, store)["error_code"], "SNAPSHOT_STORE_INVALID")

    def test_the_place_of_a_new_store(self) -> None:
        chosen = self.root / "chosen"
        chosen.mkdir()
        (chosen / "other.txt").write_text("other files", encoding="utf-8")
        answer = self.assert_nothing_written(store_place, chosen)
        self.assertEqual(answer, {"state": "new", "path": str(chosen / "snapshots"), "cloud": None})
        # A folder named snapshots is the place itself.
        named = self.root / "snapshots"
        named.mkdir()
        self.assertEqual(self.assert_nothing_written(store_place, named)["path"], str(named))
        # Its folder snapshots holds other files.
        taken = self.root / "taken"
        (taken / "snapshots").mkdir(parents=True)
        (taken / "snapshots" / "other.txt").write_text("other files", encoding="utf-8")
        self.assertEqual(self.assert_nothing_written(store_place, taken)["error_code"], "SNAPSHOT_STORE_NOT_EMPTY")
        # Inside a store: its own folder snapshots, or a folder deeper in it.
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        for inside in (store / "snapshots", store / "blobs"):
            with self.subTest(inside=inside.name):
                self.assertEqual(
                    self.assert_nothing_written(store_place, inside)["error_code"], "SNAPSHOT_STORE_INSIDE_STORE"
                )
        # A store that is chosen is opened.
        self.assertEqual(self.assert_nothing_written(store_place, store)["state"], "store")

    def test_the_default_place_waits_for_its_folder(self) -> None:
        folder = self.home / "GarminRunningData"
        answer = self.assert_nothing_written(store_place, folder)
        self.assertEqual(answer, {"state": "new", "path": str(folder / "snapshots"), "cloud": None})
        # Something other than a folder there is checked as any place.
        folder.write_bytes(b"a file")
        self.assertEqual(
            self.assert_nothing_written(store_place, folder)["error_code"], "SNAPSHOT_STORE_PARENT_NOT_FOUND"
        )
        # Another place whose folder is missing is not made later.
        missing = self.root / "missing"
        self.assertEqual(
            self.assert_nothing_written(store_place, missing)["error_code"], "SNAPSHOT_STORE_PARENT_NOT_FOUND"
        )

    def test_a_cloud_that_may_copy_the_store_is_named(self) -> None:
        cloud = self.home / "Library" / "Mobile Documents" / "Garmin"
        cloud.mkdir(parents=True)
        with patch.object(stores, "cloud_kind", lambda path: cloud_kind(path, "darwin")):
            self.assertEqual(store_place(cloud)["cloud"], "cloud")
            documents = self.home / "Documents"
            documents.mkdir()
            initialize_store(documents / "snapshots", ACCOUNT)
            self.assertEqual(open_store(documents)["cloud"], "desktop_documents")


class RunStartTest(HomeTestCase):
    def setUp(self) -> None:
        super().setUp()
        patcher = patch.dict(os.environ, child_environment())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_run_makes_the_default_place_alone(self) -> None:
        folder = self.home / "GarminRunningData"
        manager = stub_manager("wait")
        self.addCleanup(manager.stop)
        status = manager.start(request(SYNTHETIC_EXPORT, folder))
        self.assertEqual(status["state"], "running")
        self.assertTrue(folder.is_dir())
        self.assertEqual(sorted(path.name for path in self.home.iterdir()), ["GarminRunningData"])

    def test_a_refused_request_makes_nothing(self) -> None:
        folder = self.home / "GarminRunningData"
        manager = stub_manager("wait")
        self.addCleanup(manager.stop)
        for extra, code in (
            ({"output_name": ".hidden"}, "OUTPUT_NAME_INVALID"),
            ({"timezone": ""}, "TIMEZONE_INVALID"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(RunRequestError) as raised:
                    manager.start({**request(SYNTHETIC_EXPORT, folder), **extra})
                self.assertEqual(raised.exception.code, code)
                self.assertFalse(folder.exists())
        # Another missing folder is refused, as before.
        with self.assertRaises(RunRequestError) as raised:
            manager.start(request(SYNTHETIC_EXPORT, self.root / "missing"))
        self.assertEqual(raised.exception.code, "OUTPUT_PARENT_NOT_FOUND")
        self.assertFalse((self.root / "missing").exists())
        # While a run is active, nothing is made either.
        other = stub_manager("wait")
        self.addCleanup(other.stop)
        parent = self.root / "outputs"
        parent.mkdir()
        other.start(request(SYNTHETIC_EXPORT, parent))
        with patch.object(runs.RunManager, "active", lambda manager: True):
            with self.assertRaises(RunActiveError):
                manager.start(request(SYNTHETIC_EXPORT, folder))
        self.assertFalse(folder.exists())

    def test_a_default_place_that_cannot_be_made_has_the_code_of_the_output(self) -> None:
        folder = self.home / "GarminRunningData"
        manager = stub_manager("wait")
        self.addCleanup(manager.stop)
        with patch.object(places.os, "mkdir", side_effect=PermissionError("denied")):
            with self.assertRaises(RunRequestError) as raised:
                manager.start(request(SYNTHETIC_EXPORT, folder))
        self.assertEqual(raised.exception.code, "OUTPUT_PARENT_NOT_WRITABLE")
        self.assertFalse(folder.exists())


class DownloadTimeTest(HomeTestCase):
    """The download time that an import proposes (stage B4b-1)."""

    START = 1893456000  # 2030-01-01T00:00:00+00:00

    def touch(self, path: Path, seconds: int) -> None:
        os.utime(path, (self.START + seconds, self.START + seconds))

    def test_the_time_of_a_zip_file(self) -> None:
        archive = self.root / "export.zip"
        archive.write_bytes(b"synthetic")
        self.touch(archive, 3600)
        self.assertEqual(download_time(archive), ("2030-01-01T01:00:00+00:00", "zip"))

    def test_the_time_of_the_newest_file_of_a_folder(self) -> None:
        folder = self.root / "export"
        shutil.copytree(SYNTHETIC_EXPORT, folder)
        files = sorted(path for path in folder.rglob("*") if path.is_file())
        for number, path in enumerate(files):
            self.touch(path, number * 60)
        newest = f"2030-01-01T00:{(len(files) - 1):02d}:00+00:00"
        # Hidden files and folders, and the folders' own times, do not count:
        # the folder has the time of the extraction.
        (folder / ".hidden").write_text("synthetic", encoding="utf-8")
        self.touch(folder / ".hidden", 86400)
        (folder / ".cache").mkdir()
        (folder / ".cache" / "file.json").write_text("{}", encoding="utf-8")
        self.touch(folder / ".cache" / "file.json", 86400)
        self.touch(folder, 86400)
        self.assertEqual(download_time(folder), (newest, "newest_file"))

    @REAL_SYMLINKS
    def test_a_link_is_passed_over(self) -> None:
        folder = self.root / "export"
        shutil.copytree(SYNTHETIC_EXPORT, folder)
        files = sorted(path for path in folder.rglob("*") if path.is_file())
        for path in files:
            self.touch(path, 0)
        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        self.touch(outside, 86400)
        (folder / "link.json").symlink_to(outside)
        # The link's own time, which POSIX systems can set, does not count.
        later = self.START + 86400
        os.utime(folder / "link.json", (later, later), follow_symlinks=False)
        self.assertEqual(download_time(folder), ("2030-01-01T00:00:00+00:00", "newest_file"))

    def test_no_time_without_a_file(self) -> None:
        empty = self.root / "empty"
        (empty / ".hidden").mkdir(parents=True)
        self.assertEqual(download_time(empty), (None, None))
        self.assertEqual(download_time(self.root / "missing"), (None, None))


class StoreApiTest(GuiServerTestCase):
    def setUp(self) -> None:
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        patcher = patch.object(places, "home", lambda: self.home)
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, body=body)
        return status, json.loads(answer)

    def test_the_store_answers_its_problems_and_refuses_requests_that_are_not_valid(self) -> None:
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        status, answer = self.post("/api/store/open", {"path": str(store)})
        self.assertEqual((status, answer["state"], answer["snapshots"]), (200, "store", []))
        status, answer = self.post("/api/store/check", {"path": str(store)})
        self.assertEqual((status, answer["state"]), (200, "checked"))
        status, answer = self.post("/api/store/open", {"path": str(self.root)})
        self.assertEqual((status, answer["error_code"]), (200, "SNAPSHOT_STORE_NOT_FOUND"))
        status, answer = self.post("/api/store/place", {"path": str(self.home / "GarminRunningData")})
        self.assertEqual((status, answer["state"]), (200, "new"))
        for route in ("/api/store/open", "/api/store/place", "/api/store/check", "/api/place"):
            for payload, code in (({}, "PATH_INVALID"), ({"path": "relative/place"}, "PATH_NOT_ABSOLUTE")):
                with self.subTest(route=route, code=code):
                    self.assertEqual(self.post(route, payload), (422, {"error": code}))
        with patch.object(stores, "snapshot_status", side_effect=RuntimeError("unexpected")):
            self.assertEqual(self.post("/api/store/open", {"path": str(store)}), (500, {"error": "COMMAND_FAILED"}))

    def test_the_folder_for_the_output(self) -> None:
        folder = self.home / "GarminRunningData"
        self.assertEqual(
            self.post("/api/place", {"path": str(folder)}),
            (200, {"default": True, "exists": False, "cloud": None}),
        )
        folder.mkdir()
        self.assertEqual(
            self.post("/api/place", {"path": str(folder)}),
            (200, {"default": True, "exists": True, "cloud": None}),
        )
        self.assertEqual(
            self.post("/api/place", {"path": str(self.root)}),
            (200, {"default": False, "exists": True, "cloud": None}),
        )


if __name__ == "__main__":
    unittest.main()
