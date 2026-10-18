"""The Snapshot runs of the GUI (stage B4b-1).

The progress of the snapshot functions, which the CLI does not pass; the
checks of a registration, which the server makes before a child starts with
the same functions; the child's three ways to normalize; and the same output
as the CLI's ``snapshot init``, ``register``, and ``run-all``.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.gui import places, run_worker
from garmin_running_data_normalizer.gui.runs import RunActiveError, RunManager, RunRequestError
from garmin_running_data_normalizer.run_all import PROGRESS_STAGES
from garmin_running_data_normalizer.snapshot import store as store_module
from garmin_running_data_normalizer.snapshot.lifecycle import (
    SNAPSHOT_PROGRESS_STAGES,
    run_snapshot_all,
    verify_store,
)
from garmin_running_data_normalizer.snapshot.store import (
    LABEL_RE,
    LOCK_NAME,
    SnapshotStoreError,
    check_input_apart,
    check_label_free,
    initialize_store,
    load_manifests,
    new_snapshot_label,
    register_snapshot,
    registration_times,
)
from tests.test_gui_runs import (
    SYNTHETIC_EXPORT,
    WORKER,
    child_environment,
    request,
    stub_manager,
    wait_until,
)
from tests.test_mixed_and_duplicate_exports import activity, other_export
from tests.test_run_all_progress import tree_bytes


ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "src/garmin_running_data_normalizer/gui/static/flow.mjs"
ACCOUNT = "gui-0123456789abcdef01234567"
STAMP = "2030-01-03T02:00:00+00:00"
EARLIER = "2030-01-01T02:00:00+00:00"
NOW = "2030-02-01T00:00:00+00:00"
EVENT_FIELDS = {"stage", "step", "done", "total", "snapshots"}
# The stages of a registration (stage B4b-1).
IMPORT_STAGES = ("reading_export", "importing")
SERVER_ACCOUNT = re.compile(r"--new-store-account=gui-[0-9a-f]{24}")


def older_export(root: Path) -> Path:
    """An Export of other content, older than the synthetic one."""
    return other_export(root, activity("SYNTHETIC-OLDER-1", startTimeGmt=1893369600000))


def register(store: Path, source: Path, label: str, stamp: str, **options: Any) -> dict[str, Any]:
    # The page asks for the download time only, and gives the request and the
    # observation the same time (decision 20261017-16).
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=stamp,
        export_downloaded_at=stamp,
        export_observed_at=stamp,
        confirm_complete=True,
        **options,
    )


def worker(*args: str) -> tuple[int, list[dict[str, Any]], str]:
    completed = subprocess.run(
        [sys.executable, "-P", "-m", WORKER, *args],
        capture_output=True,
        text=True,
        env=child_environment(),
        timeout=180,
    )
    messages = [json.loads(line) for line in completed.stdout.splitlines()]
    return completed.returncode, messages, completed.stdout + completed.stderr


def cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "garmin_running_data_normalizer", *map(str, args)],
        capture_output=True,
        text=True,
        env=child_environment(),
        timeout=180,
    )


def events(messages: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [message for message in messages if message["event"] == name]


def stages(messages: list[dict[str, Any]]) -> list[str]:
    """The stages in the order they began."""
    found: list[str] = []
    for message in events(messages, "progress"):
        if not found or found[-1] != message["stage"]:
            found.append(message["stage"])
    return found


class SnapshotChecksTest(unittest.TestCase):
    """The checks of a registration, public for the server (stage B4b-1)."""

    def assert_code(self, code: str, check: Any, *args: Any) -> None:
        with self.assertRaises(SnapshotStoreError) as caught:
            check(*args)
        self.assertEqual(caught.exception.code, code)

    def test_the_label_of_a_new_snapshot(self) -> None:
        for label in ("S1", "2030-01-03", "2030-01-03-2", "a", "A" * 64, "x.y_z-1"):
            with self.subTest(label=label):
                self.assertEqual(new_snapshot_label(label), label)
        for label in ("", "-a", ".a", "_a", "A" * 65, "名前", "a b", " a", "a/b", None, 5):
            with self.subTest(label=label):
                self.assert_code("SNAPSHOT_LABEL_INVALID", new_snapshot_label, label)

    def test_the_page_takes_the_labels_that_the_store_takes(self) -> None:
        # The page checks a name before it is sent with the same pattern.
        found = re.search(r"const SNAPSHOT_LABEL = /(.+)/;", FLOW.read_text(encoding="utf-8"))
        assert found is not None
        self.assertEqual(found.group(1), LABEL_RE.pattern)

    def test_the_times_of_an_export(self) -> None:
        self.assertEqual(
            registration_times("2030-01-03T11:00:00+09:00", STAMP, "2030-01-03T02:00:00Z"),
            ("2030-01-03T02:00:00+00:00",) * 3,
        )
        for times in (
            ("2030-01-03 02:00", STAMP, STAMP),
            (STAMP, "2030-01-03T02:00:00", STAMP),
            (STAMP, STAMP, "not a time"),
            (None, STAMP, STAMP),
            (NOW, STAMP, STAMP),
            (STAMP, NOW, STAMP),
        ):
            with self.subTest(times=times):
                self.assert_code("SNAPSHOT_TIME_INVALID", registration_times, *times)

    def test_the_export_and_the_store_are_apart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            check_input_apart(root / "export", root / "store")
            check_input_apart(root / "store-2", root / "store")
            for source, store in (
                (root / "store", root / "store"),
                (root / "store" / "export", root / "store"),
                (root / "export", root / "export" / "store"),
            ):
                with self.subTest(source=source.name, store=store.name):
                    self.assert_code("SNAPSHOT_INPUT_INSIDE_STORE", check_input_apart, source, store)

    def test_a_label_that_the_store_has(self) -> None:
        manifests = [{"snapshot_label": "S1", "snapshot_id": "snapshot-1"}]
        check_label_free(manifests, "S2")
        check_label_free(manifests, "S1", "snapshot-1")
        self.assert_code("SNAPSHOT_LABEL_EXISTS", check_label_free, manifests, "S1")
        self.assert_code("SNAPSHOT_LABEL_EXISTS", check_label_free, manifests, "S1", "snapshot-2")


class SnapshotProgressTest(unittest.TestCase):
    """The progress of a registration and of a Snapshot run (stage B4b-1)."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        # The store records when it was made and when each Snapshot was
        # registered; the same clock makes two stores comparable.
        patcher = patch.object(store_module, "_now_utc", return_value=NOW)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.older = older_export(self.root / "older")

    def build(self, name: str, progress: Any) -> tuple[Path, Path]:
        store = self.root / f"{name}-store"
        output = self.root / f"{name}-output"
        initialize_store(store, ACCOUNT)
        options = {} if progress is None else {"progress": progress}
        register(store, SYNTHETIC_EXPORT, "S2", STAMP, **options)
        register(store, self.older, "S1", EARLIER, **options)
        run_snapshot_all(store, output, **options)
        return store, output

    def test_the_store_and_the_output_are_the_same_with_and_without_progress(self) -> None:
        received: list[dict[str, Any]] = []
        plain = self.build("plain", None)
        followed = self.build("followed", received.append)
        self.assertTrue(received)
        self.assertEqual(tree_bytes(plain[0]), tree_bytes(followed[0]))
        self.assertEqual(tree_bytes(plain[1]), tree_bytes(followed[1]))

    def test_the_events_carry_stage_names_and_numbers_only(self) -> None:
        received: list[dict[str, Any]] = []
        self.build("followed", received.append)
        text = json.dumps(received)
        for private in (str(self.root), self.root.name, "S1", "S2", ACCOUNT, "SYNTHETIC"):
            self.assertNotIn(private, text)
        for event in received:
            with self.subTest(event=event):
                self.assertLessEqual(set(event), EVENT_FIELDS)
                self.assertIn(event["stage"], (*SNAPSHOT_PROGRESS_STAGES, *PROGRESS_STAGES))
                for field in EVENT_FIELDS - {"stage", "step"}:
                    if field in event:
                        self.assertIs(type(event[field]), int)
        # Each registration reads the Export, then copies its files; each
        # stage counts from 0 to all.
        for stage in IMPORT_STAGES:
            counted = [(event["done"], event["total"]) for event in received if event["stage"] == stage]
            with self.subTest(stage=stage):
                self.assertEqual(counted[0][0], 0)
                self.assertEqual(sum(1 for done, total in counted if done == total), 2)
                self.assertTrue(all(0 <= done <= total for done, total in counted))
        after = [event for event in received if event["stage"] not in IMPORT_STAGES]
        self.assertEqual(after[:2], [{"stage": "checking_store"}, {"stage": "building_snapshots", "snapshots": 2}])
        self.assertEqual(after[2], {"stage": "discovering"})

    def test_an_exception_from_the_callback_leaves_a_store_that_works(self) -> None:
        # A failure of the page's side, or a cancellation, while the files
        # are copied: the lock and the record of the registration are taken
        # back as for any stop, and the Export can be registered again.
        for error in (RuntimeError("callback"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                store = self.root / f"store-{type(error).__name__}"
                initialize_store(store, ACCOUNT)

                def fail(event: dict[str, Any], error: BaseException = error) -> None:
                    if event["stage"] == "importing":
                        raise error

                with self.assertRaises(type(error)):
                    register(store, SYNTHETIC_EXPORT, "S1", STAMP, progress=fail)
                self.assertFalse((store / LOCK_NAME).exists())
                self.assertEqual(load_manifests(store), [])
                result = register(store, SYNTHETIC_EXPORT, "S1", STAMP)
                self.assertEqual((result["registration_was_idempotent"], result["snapshot_count"]), (False, 1))
                self.assertEqual(verify_store(store)["status"], "PASS")


class SnapshotWorkerTest(unittest.TestCase):
    """The child's ways to normalize with a Snapshot Store (stage B4b-1)."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.store = self.root / "store"

    def snapshots(self, source: Path, output: str, label: str, stamp: str, *extra: str) -> tuple[int, list[dict[str, Any]], str]:
        return worker(
            "--how=snapshots",
            f"--input={source}",
            f"--output={self.root / output}",
            f"--store={self.store}",
            f"--label={label}",
            f"--downloaded-at={stamp}",
            *extra,
        )

    def test_the_three_ways_with_a_new_store(self) -> None:
        code, messages, text = self.snapshots(SYNTHETIC_EXPORT, "first", "S2", STAMP, f"--new-store-account={ACCOUNT}")
        self.assertEqual(code, 0, text)
        self.assertEqual(
            stages(messages)[:6],
            ["creating_store", "reading_export", "importing", "checking_store", "building_snapshots", "discovering"],
        )
        self.assertEqual(events(messages, "imported"), [{"event": "imported", "order": 1, "same_content": False, "snapshot_count": 1}])
        self.assertIn({"event": "progress", "stage": "building_snapshots", "snapshots": 1}, messages)
        finished = messages[-1]
        self.assertEqual((finished["event"], finished["snapshot_count"]), ("finished", 1))
        for private in (str(self.root), "S2", ACCOUNT):
            self.assertNotIn(private, text)
        self.assertEqual(json.loads((self.store / "store.json").read_text(encoding="utf-8"))["account_store_id"], ACCOUNT)
        # The download time is recorded as each time of the Export.
        manifest = load_manifests(self.store)[0]
        self.assertEqual(
            [manifest[field] for field in ("export_requested_at", "export_downloaded_at", "export_observed_at")],
            [STAMP] * 3,
        )
        # The same Export again, under another name: no new Snapshot.
        code, messages, text = self.snapshots(SYNTHETIC_EXPORT, "again", "S3", STAMP)
        self.assertEqual(code, 0, text)
        self.assertEqual(events(messages, "imported"), [{"event": "imported", "order": 1, "same_content": True, "snapshot_count": 1}])
        # It is read, and nothing is copied.
        self.assertEqual(stages(messages)[:2], ["reading_export", "checking_store"])
        # An older Export, imported later, comes first in the order of the
        # times of the Exports.
        code, messages, text = self.snapshots(older_export(self.root / "older"), "older-output", "S1", EARLIER)
        self.assertEqual(code, 0, text)
        self.assertEqual(events(messages, "imported"), [{"event": "imported", "order": 1, "same_content": False, "snapshot_count": 2}])
        self.assertEqual(messages[-1]["snapshot_count"], 2)
        # Normalizing again imports nothing.
        code, messages, text = worker("--how=rerun", f"--output={self.root / 'rerun'}", f"--store={self.store}")
        self.assertEqual(code, 0, text)
        self.assertEqual(events(messages, "imported"), [])
        self.assertEqual(stages(messages)[:3], ["checking_store", "building_snapshots", "discovering"])
        self.assertEqual(messages[-1]["snapshot_count"], 2)

    def test_a_stop_after_the_import_comes_after_its_result(self) -> None:
        (self.root / "taken").mkdir()
        code, messages, text = self.snapshots(SYNTHETIC_EXPORT, "taken", "S1", STAMP, f"--new-store-account={ACCOUNT}")
        self.assertEqual(code, 2, text)
        self.assertEqual(
            [message for message in messages if message["event"] != "progress"],
            [
                {"event": "imported", "order": 1, "same_content": False, "snapshot_count": 1},
                {"event": "failed", "code": "OUTPUT_EXISTS"},
            ],
        )
        self.assertEqual(len(load_manifests(self.store)), 1)

    def test_the_child_stops_with_the_codes_of_the_cli(self) -> None:
        initialize_store(self.store, ACCOUNT)
        cases = [
            ("SNAPSHOT_LABEL_INVALID", ("--how=snapshots", f"--input={SYNTHETIC_EXPORT}", "--label=名前", f"--downloaded-at={STAMP}")),
            ("SNAPSHOT_TIME_INVALID", ("--how=snapshots", f"--input={SYNTHETIC_EXPORT}", "--label=S1", "--downloaded-at=2030-01-03 02:00")),
            ("SNAPSHOT_INPUT_INSIDE_STORE", ("--how=snapshots", f"--input={self.store}", "--label=S1", f"--downloaded-at={STAMP}")),
            ("SNAPSHOT_STORE_EMPTY", ("--how=rerun",)),
        ]
        for expected, args in cases:
            with self.subTest(code=expected):
                code, messages, text = worker(*args, f"--output={self.root / 'output'}", f"--store={self.store}")
                self.assertEqual(code, 2, text)
                self.assertEqual(messages[-1], {"event": "failed", "code": expected})
                self.assertFalse((self.root / "output").exists())
        register(self.store, SYNTHETIC_EXPORT, "S1", STAMP)
        code, messages, text = self.snapshots(older_export(self.root / "older"), "output", "S1", EARLIER)
        self.assertEqual(messages[-1], {"event": "failed", "code": "SNAPSHOT_LABEL_EXISTS"})
        (self.store / LOCK_NAME).write_text("424242\n", encoding="ascii")
        code, messages, text = self.snapshots(older_export(self.root / "older-2"), "output", "S0", EARLIER)
        self.assertEqual(messages[-1], {"event": "failed", "code": "SNAPSHOT_STORE_LOCKED"})

    def test_an_error_that_no_code_describes_is_that_of_the_phase(self) -> None:
        # As the CLI's commands say: the registration, or Run-All.
        args = [
            "--how=snapshots", f"--input={SYNTHETIC_EXPORT}", f"--output={self.root / 'output'}",
            f"--store={self.store}", "--label=S1", f"--downloaded-at={STAMP}", f"--new-store-account={ACCOUNT}",
        ]
        for name, expected in (("register_snapshot", "COMMAND_FAILED"), ("run_snapshot_all", "RUN_ALL_FAILED")):
            with self.subTest(function=name):
                written = io.StringIO()
                with patch.object(run_worker, name, side_effect=RuntimeError(str(self.root))), redirect_stdout(written):
                    self.assertEqual(run_worker.main(args), 2)
                messages = [json.loads(line) for line in written.getvalue().splitlines()]
                self.assertEqual(messages[-1], {"event": "failed", "code": expected})
                self.assertNotIn(str(self.root), written.getvalue())


class SnapshotWorkerMatchesCliTest(unittest.TestCase):
    """A Snapshot run of the page writes what the CLI writes (stage B4b-1).

    The CLI's ``init`` is given the account of the store that the page made:
    it is in the records of the build, and so in the output."""

    def test_the_output_matches_the_snapshot_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            older = older_export(root / "older")
            gui_store, cli_store = root / "gui-store", root / "cli-store"
            self.assertEqual(cli("snapshot", "init", "--store", cli_store, "--account", ACCOUNT).returncode, 0)
            imports = ((SYNTHETIC_EXPORT, "S2", STAMP), (older, "S1", EARLIER))
            for number, (source, label, stamp) in enumerate(imports, start=1):
                for option_name, option in (("default", []), ("pack", ["--external-safe-pack"])):
                    with self.subTest(snapshots=number, option=option_name):
                        gui_output = root / f"gui-{number}-{option_name}"
                        cli_output = root / f"cli-{number}-{option_name}"
                        new_store = [f"--new-store-account={ACCOUNT}"] if not gui_store.exists() else []
                        code, _messages, text = worker(
                            "--how=snapshots", f"--input={source}", f"--output={gui_output}",
                            f"--store={gui_store}", f"--label={label}", f"--downloaded-at={stamp}",
                            *new_store, *option,
                        )
                        self.assertEqual(code, 0, text)
                        registered = cli(
                            "snapshot", "register", "--store", cli_store, "--input", source, "--label", label,
                            "--requested-at", stamp, "--downloaded-at", stamp, "--observed-at", stamp,
                            "--confirm-complete",
                        )
                        self.assertEqual(registered.returncode, 0, registered.stderr)
                        ran = cli("snapshot", "run-all", "--store", cli_store, "--output", cli_output, *option)
                        self.assertEqual(ran.returncode, 0, ran.stderr)
                        self.assertEqual(tree_bytes(gui_output), tree_bytes(cli_output))
            # Normalizing again matches the CLI's run-all of the same store.
            gui_output, cli_output = root / "gui-rerun", root / "cli-rerun"
            code, _messages, text = worker("--how=rerun", f"--output={gui_output}", f"--store={gui_store}", "--timezone=UTC")
            self.assertEqual(code, 0, text)
            ran = cli("snapshot", "run-all", "--store", cli_store, "--output", cli_output, "--timezone", "UTC")
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(tree_bytes(gui_output), tree_bytes(cli_output))
            # A store that the page made works with the CLI without an init.
            status = cli("snapshot", "status", "--store", gui_store)
            self.assertEqual(status.returncode, 0, status.stderr)


class SnapshotRunRequestTest(unittest.TestCase):
    """The server's checks of a Snapshot run before its child starts."""

    def setUp(self) -> None:
        patcher = patch.dict(os.environ, child_environment())
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.parent = self.root / "outputs"
        self.parent.mkdir()
        self.store = self.root / "store"
        initialize_store(self.store, ACCOUNT)
        self.empty = self.root / "empty-store"
        initialize_store(self.empty, ACCOUNT)
        register(self.store, SYNTHETIC_EXPORT, "S1", STAMP)

    def snapshot_request(self, name: str = "output", **extra: Any) -> dict[str, Any]:
        snapshot = {"how": "snapshots", "store": str(self.store), "label": "S2", "downloaded_at": STAMP}
        return request(SYNTHETIC_EXPORT, self.parent, name, **{**snapshot, **extra})

    def started_args(self, manager: RunManager, case: dict[str, Any]) -> list[str]:
        self.addCleanup(manager.stop)
        manager.start(case)
        assert manager._run is not None
        args = [str(item) for item in manager._run.process.args]
        manager.stop()
        return args

    def test_requests_are_checked_before_a_child_starts(self) -> None:
        manager = stub_manager("wait")
        self.addCleanup(manager.stop)
        (self.root / "taken").mkdir()
        (self.root / "taken" / "file.txt").write_text("synthetic", encoding="utf-8")
        rerun = {**request(SYNTHETIC_EXPORT, self.parent), "how": "rerun", "store": str(self.empty)}
        rerun.pop("input")
        cases: list[tuple[dict[str, Any], str]] = [
            (self.snapshot_request(how="both"), "REQUEST_INVALID"),
            (self.snapshot_request(store=7), "PATH_INVALID"),
            (self.snapshot_request(store="relative/store"), "PATH_NOT_ABSOLUTE"),
            (self.snapshot_request(new_store="yes"), "REQUEST_INVALID"),
            ({**rerun, "new_store": True}, "REQUEST_INVALID"),
            (self.snapshot_request(label="名前"), "SNAPSHOT_LABEL_INVALID"),
            (self.snapshot_request(label=None), "SNAPSHOT_LABEL_INVALID"),
            (self.snapshot_request(downloaded_at="2030-01-03 02:00"), "SNAPSHOT_TIME_INVALID"),
            (self.snapshot_request(downloaded_at=None), "SNAPSHOT_TIME_INVALID"),
            (self.snapshot_request(store=str(SYNTHETIC_EXPORT / "store"), new_store=True), "SNAPSHOT_INPUT_INSIDE_STORE"),
            (self.snapshot_request(store=str(self.root / "missing")), "SNAPSHOT_STORE_NOT_FOUND"),
            (self.snapshot_request(label="S1"), "SNAPSHOT_LABEL_EXISTS"),
            (rerun, "SNAPSHOT_STORE_EMPTY"),
            (self.snapshot_request(store=str(self.root / "taken"), new_store=True), "SNAPSHOT_STORE_NOT_EMPTY"),
            (self.snapshot_request(store=str(self.root / "missing" / "store"), new_store=True), "SNAPSHOT_STORE_PARENT_NOT_FOUND"),
            (self.snapshot_request(store=str(self.store / "inner"), new_store=True), "SNAPSHOT_STORE_INSIDE_STORE"),
        ]
        for case, code in cases:
            with self.subTest(code=code, case=case):
                with self.assertRaises(RunRequestError) as caught:
                    manager.start(case)
                self.assertEqual(caught.exception.code, code)
        self.assertEqual(manager.status(), {"state": "idle"})
        self.assertEqual(list(self.parent.iterdir()), [])
        self.assertFalse((self.root / "missing").exists())

    def test_an_active_run_comes_before_the_store(self) -> None:
        # The store is read once no run is active, since that run may be
        # writing in it: a second request is told that a run is active.
        manager = stub_manager("wait")
        self.addCleanup(manager.stop)
        manager.start(self.snapshot_request())
        with self.assertRaises(RunActiveError):
            manager.start(self.snapshot_request("second", label="S1"))
        with self.assertRaises(RunRequestError) as caught:
            manager.start(self.snapshot_request("third", label="名前"))
        self.assertEqual(caught.exception.code, "SNAPSHOT_LABEL_INVALID")

    def test_the_child_is_given_the_way_and_the_checked_values(self) -> None:
        args = self.started_args(stub_manager("wait"), self.snapshot_request(downloaded_at="2030-01-03T11:00:00+09:00"))
        self.assertIn("--how=snapshots", args)
        self.assertIn(f"--store={self.store}", args)
        self.assertIn("--label=S2", args)
        # The time as the registration records it, in UTC.
        self.assertIn(f"--downloaded-at={STAMP}", args)
        self.assertFalse(any(arg.startswith("--new-store-account") for arg in args))
        rerun = {**request(SYNTHETIC_EXPORT, self.parent, "rerun"), "how": "rerun", "store": str(self.store)}
        rerun.pop("input")
        args = self.started_args(stub_manager("wait"), rerun)
        self.assertIn("--how=rerun", args)
        self.assertFalse(any(arg.startswith(("--input", "--label", "--downloaded-at")) for arg in args))

    def test_the_server_gives_a_new_store_its_own_account(self) -> None:
        # Never one that the page sends; each new store has another.
        tokens = []
        for number in (1, 2):
            case = self.snapshot_request(
                f"output-{number}", store=str(self.root / f"new-{number}"), new_store=True, account="page-account"
            )
            args = self.started_args(stub_manager("wait"), case)
            found = [arg for arg in args if arg.startswith("--new-store-account=")]
            self.assertEqual(len(found), 1)
            self.assertRegex(found[0], SERVER_ACCOUNT)
            tokens.append(found[0])
            self.assertNotIn("page-account", " ".join(args))
        self.assertNotEqual(tokens[0], tokens[1])

    def test_a_new_store_in_the_default_place_makes_the_default_folder(self) -> None:
        home = self.root / "home"
        home.mkdir()
        with patch.object(places, "home", return_value=home):
            case = self.snapshot_request(store=str(places.default_store()), new_store=True)
            self.started_args(stub_manager("wait"), case)
            self.assertTrue(places.default_folder().is_dir())
            # The store itself is made by the child.
            self.assertFalse(places.default_store().exists())

    def test_the_real_worker_imports_through_the_manager(self) -> None:
        manager = RunManager()
        self.addCleanup(manager.stop)
        manager.start(self.snapshot_request(store=str(self.root / "new-store"), new_store=True, label="S1"))
        self.assertTrue(wait_until(lambda: not manager.active(), 120.0))
        status = manager.status()
        self.assertEqual(status["state"], "finished", status)
        self.assertEqual(status["how"], "snapshots")
        self.assertEqual(status["imported"], {"order": 1, "same_content": False, "snapshot_count": 1})
        self.assertEqual(status["result"]["snapshot_count"], 1)
        self.assertEqual(
            list(status["stage_seconds"])[:5],
            ["creating_store", "reading_export", "importing", "checking_store", "building_snapshots"],
        )
        self.assertNotIn(str(self.root), json.dumps({key: value for key, value in status.items() if key != "output_path"}))

    def test_only_validated_snapshot_messages_reach_the_status(self) -> None:
        manager = stub_manager("snapshot-noise")
        self.addCleanup(manager.stop)
        manager.start(self.snapshot_request())
        self.assertTrue(wait_until(lambda: not manager.active()))
        status = manager.status()
        self.assertEqual(status["progress"], {"stage": "importing", "done": 1, "total": 2})
        self.assertEqual(status["imported"], {"order": 1, "same_content": False, "snapshot_count": 2})
        self.assertEqual(status["error_code"], "SNAPSHOT_STORE_NOT_READABLE")
        self.assertEqual(status["error_detail"], {"place": "snapshots", "more": 0, "store": True})
        self.assertNotIn("/path/to/private", json.dumps(status))


if __name__ == "__main__":
    unittest.main()
