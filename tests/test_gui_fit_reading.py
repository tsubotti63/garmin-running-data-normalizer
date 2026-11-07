"""The laps of one activity with the kinds that its FIT file records, read from
the Snapshot Store (stage X9c-1 of v2.3.0): gui.fit_reading.

The outputs and the stores are made as the CLI and the GUI make them: a
synthetic Export registered in a store, normalized from the store with
run_snapshot_all, the function that both call.
"""
from __future__ import annotations

import builtins
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
import struct
import sys
import tempfile
import threading
import time
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer.fit import lap_kinds
from garmin_running_data_normalizer.gui import fit_reading
from garmin_running_data_normalizer.gui.fit_reading import (
    LAPS,
    LINEAGE,
    LINKS,
    REASONS,
    SESSIONS,
    LapRow,
    Laps,
    activity_key,
    known_unavailable,
    read_laps,
)
from garmin_running_data_normalizer.output_check import OutputActionError
from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot import initialize_store, register_snapshot, run_snapshot_all
from garmin_running_data_normalizer.snapshot.store import SnapshotStoreError, check_store_metadata, load_store
from garmin_running_data_normalizer.view.data import Row, _manifest_entries
from tests.fit_fixture_factory import synthetic_fit
from tests.test_fit_running_dynamics import write_export

ACCOUNT = "synthetic-account-boundary"
# warmup, interval, recovery, interval, rest, cooldown
INTENSITIES = (2, 5, 4, 5, 1, 3)
NAMES = ["warmup", "interval", "recovery", "interval", "rest", "cooldown"]
WINDOWS = sys.platform == "win32"


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build(root: Path, intensities: tuple[int, ...] | None = INTENSITIES, *, store: bool = True) -> None:
    """A synthetic Export with one running activity and its FIT file, and its
    output (root/out), made from a store (root/store) unless ``store`` is
    false."""
    export = write_export(root / "export", synthetic_fit(lap_intensities=intensities))
    if not store:
        run_all(export, root / "out")
        return
    initialize_store(root / "store", ACCOUNT)
    register_snapshot(
        root / "store",
        export,
        snapshot_label="S1",
        export_requested_at="2030-01-01T00:00:00+00:00",
        export_downloaded_at="2030-01-01T01:00:00+00:00",
        export_observed_at="2030-01-01T02:00:00+00:00",
        confirm_complete=True,
    )
    run_snapshot_all(root / "store", root / "out")


def entries(output: Path) -> dict[str, tuple[int, str]]:
    """The sizes and SHA-256 of the files of an output, as the manifest of the
    view page's reading gives them."""
    return _manifest_entries(load(output / "run_manifest.json"))


def rewrite(output: Path, files: dict[str, tuple[int, str]], relative: str, value: object) -> None:
    """Write a file of the output again, with its new size and SHA-256 in
    ``files``, as a new reading of the output gives them."""
    data = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
    path = output / relative
    os.chmod(path, 0o600)
    path.write_bytes(data)
    files[relative] = (len(data), hashlib.sha256(data).hexdigest())


def blob(store: Path, digest: str) -> Path:
    return store / "blobs" / "sha256" / digest[:2] / digest


def writable(path: Path) -> Path:
    os.chmod(path, 0o600 if path.is_file() else 0o700)
    return path


def remove_folder(folder: Path) -> None:
    """Remove a folder of a copy of a store, whose blobs are read-only."""
    for path in folder.rglob("*"):
        writable(path)
    shutil.rmtree(folder)


def junction_in_place(folder: Path, target: Path) -> None:
    """Windows: make the empty ``folder`` itself a junction to ``target``
    (FSCTL_SET_REPARSE_POINT on the folder, as an attacker could while the
    reading holds it: the holding keeps it from being renamed, not from
    this)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    control = kernel32.DeviceIoControl
    control.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    control.restype = wintypes.BOOL
    close = kernel32.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    # GENERIC_WRITE; every sharing; OPEN_EXISTING; a folder, as itself.
    handle = create(str(folder), 0x40000000, 0x7, None, 3, 0x02000000 | 0x00200000, None)
    if handle is None or handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        substitute = ("\\??\\" + str(target)).encode("utf-16-le")
        shown = str(target).encode("utf-16-le")
        names = substitute + b"\x00\x00" + shown + b"\x00\x00"
        mount = struct.pack("<HHHH", 0, len(substitute), len(substitute) + 2, len(shown)) + names
        # IO_REPARSE_TAG_MOUNT_POINT, the size of its data, and a reserved word.
        data = struct.pack("<IHH", 0xA0000003, len(mount), 0) + mount
        buffer = ctypes.create_string_buffer(data, len(data))
        returned = wintypes.DWORD()
        # FSCTL_SET_REPARSE_POINT.
        if not control(handle, 0x000900A4, buffer, len(data), None, 0, ctypes.byref(returned), None):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        close(handle)


def pipe_releaser(path: Path) -> tuple[threading.Thread, threading.Event]:
    """A helper, started, that lets a reader that waits for a writer of the
    pipe at ``path`` go after 2.5 seconds, unless it is stopped first."""
    stop = threading.Event()

    def release() -> None:
        if stop.wait(2.5):
            return
        end = time.monotonic() + 3
        while time.monotonic() < end:
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            except OSError:
                time.sleep(0.05)
                continue
            os.close(descriptor)
            return

    helper = threading.Thread(target=release)
    helper.start()
    return helper, stop


def make_link(target: Path, link: Path, *, folder: bool) -> None:
    """A symbolic link, or the test is skipped where the system makes none."""
    try:
        os.symlink(target, link, target_is_directory=folder)
    except (OSError, NotImplementedError) as exc:
        raise unittest.SkipTest(f"no symbolic link here: {exc}") from exc


# Ways of the answer, each a change of a copy: (output, store, files, key, SHA-256 of the FIT file).
WAYS = {
    "laps": lambda o, s, f, k, d: None,
    "fit_missing": lambda o, s, f, k, d: writable(blob(s, d)).unlink(),
    "fit_changed": lambda o, s, f, k, d: writable(blob(s, d)).write_bytes(b"x"),
    "fit_too_large": lambda o, s, f, k, d: writable(blob(s, d)).write_bytes(b"x" * (32 * 1024 * 1024 + 1)),
    "other_store": lambda o, s, f, k, d: writable(s / "store.json").write_text(json.dumps({**load(s / "store.json"), "account_store_id": "another-account"}), encoding="utf-8"),
    "store_unreadable": lambda o, s, f, k, d: writable(s / "store.json").write_bytes(b"{"),
    "store_json_too_large": lambda o, s, f, k, d: writable(s / "store.json").write_bytes(b" " * (64 * 1024 + 1)),
    "no_store": lambda o, s, f, k, d: remove_folder(s),
    # What a store writes without its store.json: a damaged store, as load_store takes it (stage X9c-2).
    "store_json_missing": lambda o, s, f, k, d: writable(s / "store.json").unlink(),
    "no_link": lambda o, s, f, k, d: rewrite(o, f, LINKS, []),
    "laps_differ": lambda o, s, f, k, d: rewrite(o, f, LAPS, sorted(load(o / LAPS), key=lambda row: row["lap_ordinal_within_session"])[:-1]),
    "OUTPUT_CHANGED": lambda o, s, f, k, d: (o / LAPS).write_text("[]", encoding="utf-8"),
}


class Fixture(unittest.TestCase):
    """Each test reads a copy of outputs and stores made once."""

    built: dict[str, Path]

    @classmethod
    def setUpClass(cls) -> None:
        cls.built = {}
        cls._made = tempfile.TemporaryDirectory()
        made = Path(cls._made.name)
        for name, intensities, store in (
            ("kinds", INTENSITIES, True),
            ("no_kinds", None, True),
            ("other_codes", (6, 9, 0), True),
            ("no_laps", (), True),
            ("no_store", INTENSITIES, False),
        ):
            build(made / name, intensities, store=store)
            cls.built[name] = made / name

    @classmethod
    def tearDownClass(cls) -> None:
        cls._made.cleanup()

    def setUp(self) -> None:
        self._copies = tempfile.TemporaryDirectory()
        self.addCleanup(self._copies.cleanup)

    def copy(self, name: str = "kinds") -> tuple[Path, Path, dict[str, tuple[int, str]], str, str]:
        """The output, the store, the files of the output, the key of its
        activity, and the SHA-256 of its FIT file, of a copy of ``name``."""
        root = Path(self._copies.name) / f"{name}-{len(list(Path(self._copies.name).iterdir()))}"
        shutil.copytree(self.built[name], root, symlinks=True)
        output = root / "out"
        key = load(output / LINKS)[0]["garmin_activity_key"] if load(output / LINKS) else ""
        sessions = load(output / SESSIONS)
        return output, root / "store", entries(output), key, sessions[0]["source_sha256"] if sessions else ""

    def swapping(self, when, change):
        """A patch of os.open that makes ``change`` once, just before the
        first opening for which ``when`` holds."""
        real_open = os.open
        done: list[bool] = []

        def opening(path, flags, *args, **kwargs):
            if not done and when(path, kwargs):
                done.append(True)
                change()
            return real_open(path, flags, *args, **kwargs)

        return mock.patch.object(os, "open", side_effect=opening), done

    def assertReason(self, answer: Laps, reason: str) -> None:
        self.assertEqual((answer.status, answer.reason, answer.laps), ("unavailable", reason, ()))

    def assertStops(self, code: str, *args: object) -> None:
        with self.assertRaises(OutputActionError) as caught:
            read_laps(*args)
        self.assertEqual(caught.exception.code, code)


class ReadLapsTest(Fixture):
    def test_the_laps_of_an_activity_with_the_kinds_of_its_fit_file(self) -> None:
        output, store, files, key, _digest = self.copy()
        answer = read_laps(output, files, key, store)
        self.assertEqual((answer.status, answer.reason, answer.unknown_kind), ("laps", None, 0))
        self.assertEqual([lap.kind for lap in answer.laps], NAMES)
        rows = sorted(load(output / LAPS), key=lambda row: row["lap_ordinal_within_session"])
        self.assertEqual(
            list(answer.laps),
            [
                LapRow(
                    kind=name,
                    elapsed_s=row["total_elapsed_time"],
                    timer_s=row["total_timer_time"],
                    distance_m=row["total_distance"],
                    avg_heart_rate=row["avg_heart_rate"],
                    max_heart_rate=row["max_heart_rate"],
                    avg_cadence=row["avg_cadence"],
                    avg_speed=row["avg_speed"],
                )
                for name, row in zip(NAMES, rows)
            ],
        )
        # The values are those of the output, which the FIT file's agree with.
        self.assertEqual((answer.laps[0].elapsed_s, answer.laps[0].timer_s, answer.laps[0].distance_m), (3600.0, 3500.0, 10000.0))
        # The maximum heart rate too (stage X10 of v2.3.0), which the synthetic
        # FIT file records for every lap.
        self.assertTrue(all(lap.max_heart_rate is not None for lap in answer.laps))
        self.assertEqual([lap.max_heart_rate for lap in answer.laps], [row["max_heart_rate"] for row in rows])

    def test_laps_without_a_known_kind(self) -> None:
        output, store, files, key, _digest = self.copy("no_kinds")
        answer = read_laps(output, files, key, store)
        self.assertEqual(([lap.kind for lap in answer.laps], answer.unknown_kind), (["unknown"], 1))
        output, store, files, key, _digest = self.copy("other_codes")
        answer = read_laps(output, files, key, store)
        # other (6) and a number that the profile does not name are not known.
        self.assertEqual(([lap.kind for lap in answer.laps], answer.unknown_kind), (["unknown", "unknown", "active"], 2))

    def test_an_activity_without_laps(self) -> None:
        output, store, files, key, _digest = self.copy("no_laps")
        self.assertEqual(read_laps(output, files, key, store), Laps("laps"))

    def test_an_output_made_without_a_store(self) -> None:
        output, _store, files, key, _digest = self.copy("no_store")
        _output, store, _files, _key, _digest = self.copy()
        self.assertNotIn(LINEAGE, files)
        self.assertReason(read_laps(output, files, key, store), "not_from_store")
        self.assertReason(read_laps(output, files, key, None), "not_from_store")

    def test_no_key(self) -> None:
        output, store, files, _key, _digest = self.copy()
        self.assertReason(read_laps(output, files, "", store), "key_shared")

    def test_no_store_remembered_or_there(self) -> None:
        output, store, files, key, _digest = self.copy()
        self.assertReason(read_laps(output, files, key, None), "no_store")
        self.assertReason(read_laps(output, files, key, store.parent / "gone"), "no_store")
        (store.parent / "empty").mkdir()
        self.assertReason(read_laps(output, files, key, store.parent / "empty"), "no_store")

    def test_a_store_without_its_store_json(self) -> None:
        # A folder that holds what a store writes but not its store.json is a
        # damaged store, as load_store and the page take it: the reading does
        # not go on to its folder snapshots (stage X9c-2 of v2.3.0). Only the
        # names of the entries count, and the folder snapshots does not.
        output, store, files, key, _digest = self.copy()
        writable(store / "store.json").unlink()
        self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        output, store, files, key, _digest = self.copy()
        parent = store.parent / "chosen"
        parent.mkdir()
        (parent / "notes.txt").write_text("not of a store", encoding="utf-8")
        store.rename(parent / "snapshots")
        self.assertEqual(read_laps(output, files, key, parent).status, "laps")
        for name in sorted(fit_reading._STORE_ENTRY_NAMES):
            with self.subTest(name=name):
                (parent / name).mkdir() if name in ("blobs", "journal") else (parent / name).write_text("", encoding="utf-8")
                self.assertReason(read_laps(output, files, key, parent), "store_unreadable")
                (parent / name).rmdir() if name in ("blobs", "journal") else (parent / name).unlink()
        self.assertNotIn("snapshots", fit_reading._STORE_ENTRY_NAMES)

    @unittest.skipIf(WINDOWS, "symbolic links need a privilege on Windows")
    def test_a_link_of_a_name_that_a_store_writes_counts_as_itself(self) -> None:
        # The names are looked at as themselves (stage X9c-2): a link named as
        # what a store writes counts, also where it leads nowhere, and is not
        # followed.
        output, store, files, key, _digest = self.copy()
        folder = store.parent / "chosen"
        folder.mkdir()
        make_link(folder / "nowhere", folder / "blobs", folder=True)
        self.assertReason(read_laps(output, files, key, folder), "store_unreadable")

    def test_a_store_in_the_folder_snapshots_of_the_remembered_folder(self) -> None:
        output, store, files, key, _digest = self.copy()
        parent = store.parent / "chosen"
        parent.mkdir()
        store.rename(parent / "snapshots")
        self.assertEqual(read_laps(output, files, key, parent).status, "laps")
        self.assertEqual(read_laps(output, files, key, parent / "snapshots").status, "laps")

    def test_another_store(self) -> None:
        output, store, files, key, _digest = self.copy()
        metadata = load(store / "store.json")
        writable(store / "store.json").write_text(json.dumps({**metadata, "account_store_id": "another-account"}), encoding="utf-8")
        self.assertReason(read_laps(output, files, key, store), "other_store")

    def test_a_store_that_this_version_does_not_read(self) -> None:
        changes = {
            "newer": lambda m: {**m, "format": "garmin-running-data-normalizer-snapshot-store-v2"},
            "other version": lambda m: {**m, "format_version": 2},
            "not single writer": lambda m: {**m, "single_writer": False},
            "automatic deletion": lambda m: {**m, "automatic_deletion": True},
            "garbage collection": lambda m: {**m, "garbage_collection": True},
            "an id of another form": lambda m: {**m, "account_store_id": "x"},
            # load_store reads str(12345); the view page reads ids of text only.
            "an id of a number": lambda m: {**m, "account_store_id": 12345},
            "a time without its offset": lambda m: {**m, "created_at_utc": "2030-01-01T00:00:00"},
            # load_store stops with an OverflowError there; the view page tells it as a store not read.
            "a time that cannot be told in UTC": lambda m: {**m, "created_at_utc": "0001-01-01T00:00:00+01:00"},
            "not an object": lambda m: [m],
            "not JSON": lambda m: b"{",
            "not UTF-8": lambda m: b'{"a": "\xff"}',
            "nested too deeply": lambda m: {**m, "deep": json.loads("[" * 300 + "]" * 300)},
            "over its limit": lambda m: {**m, "padding": "a" * 70_000},
        }
        for name, change in changes.items():
            with self.subTest(name):
                output, store, files, key, _digest = self.copy()
                value = change(load(store / "store.json"))
                writable(store / "store.json").write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode("utf-8"))
                self.assertReason(read_laps(output, files, key, store), "store_unreadable")

    def test_store_json_at_its_limit(self) -> None:
        output, store, files, key, _digest = self.copy()
        metadata = load(store / "store.json")
        size = len(json.dumps({**metadata, "padding": ""}).encode("utf-8"))
        at_limit = json.dumps({**metadata, "padding": "a" * (64 * 1024 - size)}).encode("utf-8")
        self.assertEqual(len(at_limit), 64 * 1024)
        writable(store / "store.json").write_bytes(at_limit)
        self.assertEqual(read_laps(output, files, key, store).status, "laps")
        writable(store / "store.json").write_bytes(at_limit[:-1] + b' }')
        self.assertReason(read_laps(output, files, key, store), "store_unreadable")

    def test_the_link_of_the_activity(self) -> None:
        output, store, files, key, _digest = self.copy()
        link = load(output / LINKS)[0]
        other = {**link, "garmin_activity_key": "activity:another"}
        for name, rows, reason in (
            ("no link", [], "no_link"),
            ("two links", [link, link], "no_link"),
            ("two links of the activity to two sessions", [link, {**link, "fit_session_key": "fit_session:" + "0" * 64 + ":0"}], "no_link"),
            ("not explicit", [{**link, "match_status": "ambiguous"}], "no_link"),
            ("ambiguous", [{**link, "ambiguous": True}], "no_link"),
            ("ambiguous of another form", [{**link, "ambiguous": 0}], "no_link"),
            ("not eligible", [{**link, "eligibility_status": "excluded"}], "no_link"),
            ("the session linked to another activity too", [link, other], "no_link"),
            ("the other activity alone", [other], "no_link"),
        ):
            with self.subTest(name):
                rewrite(output, files, LINKS, rows)
                self.assertReason(read_laps(output, files, key, store), reason)
        for name, rows in (
            ("a session key of another form", [{**link, "fit_session_key": 1}]),
            ("a SHA-256 of another form", [{**link, "fit_source_sha256": None}]),
            ("not a list", {"rows": [link]}),
            ("a row of another form", [link, "row"]),
        ):
            with self.subTest(name):
                rewrite(output, files, LINKS, rows)
                self.assertStops("OUTPUT_CHANGED", output, files, key, store)

    def test_the_session_of_the_link(self) -> None:
        output, store, files, key, digest = self.copy()
        session = load(output / SESSIONS)[0]
        for name, rows in (
            ("no session", []),
            ("two sessions", [session, session]),
            ("a number of the session of another form", [{**session, "session_ordinal": True}]),
            ("a negative number", [{**session, "session_ordinal": -1}]),
            ("a key not made of the SHA-256 and the number", [{**session, "session_ordinal": 1}]),
            ("another SHA-256", [{**session, "source_sha256": "0" * 64}]),
            ("a SHA-256 of another form", [{**session, "source_sha256": digest.upper()}]),
        ):
            with self.subTest(name):
                rewrite(output, files, SESSIONS, rows)
                self.assertStops("OUTPUT_CHANGED", output, files, key, store)

    def craft(self, name: str, *, link: dict, session: dict, laps: dict) -> tuple[Path, Path, dict, str]:
        """A copy whose link, session, and laps are changed together, so that
        only one check of them can find the change."""
        output, store, files, key, _digest = self.copy(name)
        rewrite(output, files, LINKS, [{**row, **link} for row in load(output / LINKS)])
        rewrite(output, files, SESSIONS, [{**row, **session} for row in load(output / SESSIONS)])
        rewrite(output, files, LAPS, [{**row, **laps} for row in load(output / LAPS)])
        return output, store, files, key

    def test_a_session_changed_with_its_link_and_laps(self) -> None:
        zeros = "0" * 64
        for name, built, link, session, laps in (
            # The key agrees with a number that is a bool; the laps are of session 1.
            ("a bool number", "kinds", {"fit_session_key": "fit_session:{digest}:True"}, {"fit_session_key": "fit_session:{digest}:True", "session_ordinal": True}, {"fit_session_key": "fit_session:{digest}:True", "session_ordinal": 1}),
            # A negative number would take the last session of the FIT file.
            ("a negative number", "no_laps", {"fit_session_key": "fit_session:{digest}:-1"}, {"fit_session_key": "fit_session:{digest}:-1", "session_ordinal": -1}, {}),
            # The key of session 0 with the number 1, and laps of session 1.
            ("a key of another number", "kinds", {}, {"session_ordinal": 1}, {"session_ordinal": 1}),
            # The session of another SHA-256 than its link, whose laps are of the link's.
            ("another SHA-256 than the link's", "kinds", {"fit_session_key": f"fit_session:{zeros}:0"}, {"fit_session_key": f"fit_session:{zeros}:0", "source_sha256": zeros}, {"fit_session_key": f"fit_session:{zeros}:0"}),
            # A SHA-256 in capitals, the same in the link, the session, and the laps.
            ("a SHA-256 in capitals", "kinds", {"fit_session_key": "fit_session:{upper}:0", "fit_source_sha256": "{upper}"}, {"fit_session_key": "fit_session:{upper}:0", "source_sha256": "{upper}"}, {"fit_session_key": "fit_session:{upper}:0", "source_sha256": "{upper}"}),
            # A SHA-256 that leads out of the folder of the blobs.
            ("a way out of the blobs", "kinds", {"fit_session_key": "fit_session:../../store.json:0", "fit_source_sha256": "../../store.json"}, {"fit_session_key": "fit_session:../../store.json:0", "source_sha256": "../../store.json"}, {"fit_session_key": "fit_session:../../store.json:0", "source_sha256": "../../store.json"}),
        ):
            with self.subTest(name):
                # The SHA-256 of the FIT file of the output that is copied.
                digest = load(self.built[built] / "out" / SESSIONS)[0]["source_sha256"]

                def filled(values: dict) -> dict:
                    return {
                        field: value.format(digest=digest, upper=digest.upper()) if isinstance(value, str) else value
                        for field, value in values.items()
                    }

                output, store, files, key = self.craft(built, link=filled(link), session=filled(session), laps=filled(laps))
                self.assertStops("OUTPUT_CHANGED", output, files, key, store)

    def test_the_laps_of_the_session(self) -> None:
        output, store, files, key, _digest = self.copy()
        laps = sorted(load(output / LAPS), key=lambda row: row["lap_ordinal_within_session"])
        for name, rows in (
            ("a gap", laps[:2] + laps[3:]),
            ("a repeat", [*laps, laps[-1]]),
            ("a number of another form", [{**laps[0], "lap_ordinal_within_session": False}, *laps[1:]]),
            ("another SHA-256", [{**laps[0], "source_sha256": "0" * 64}, *laps[1:]]),
            ("another session", [{**laps[0], "session_ordinal": 1}, *laps[1:]]),
            ("a session number of another form", [{**laps[0], "session_ordinal": False}, *laps[1:]]),
        ):
            with self.subTest(name):
                rewrite(output, files, LAPS, rows)
                self.assertStops("OUTPUT_CHANGED", output, files, key, store)
        # In another order in their file, by their numbers.
        rewrite(output, files, LAPS, list(reversed(laps)))
        self.assertEqual([lap.kind for lap in read_laps(output, files, key, store).laps], NAMES)

    def test_laps_that_differ_from_those_of_the_fit_file(self) -> None:
        output, store, files, key, _digest = self.copy()
        laps = sorted(load(output / LAPS), key=lambda row: row["lap_ordinal_within_session"])

        def changed(**values: object) -> list[dict[str, object]]:
            return [{**laps[0], **values}, *laps[1:]]

        for name, rows in (
            ("a timer time", changed(total_timer_time=laps[0]["total_timer_time"] + 0.001)),
            ("an empty distance", changed(total_distance=None)),
            ("an elapsed time", changed(total_elapsed_time=0.0)),
            ("the start of another lap", changed(start_time=laps[1]["start_time"])),
            ("an empty start", changed(start_time=None)),
            ("a lap fewer", laps[:-1]),
        ):
            with self.subTest(name):
                rewrite(output, files, LAPS, rows)
                self.assertReason(read_laps(output, files, key, store), "laps_differ")
        # The same instant with another offset agrees.
        start = laps[0]["start_time"]
        other = datetime.fromisoformat(start).astimezone(timezone(timedelta(hours=5, minutes=45))).isoformat()
        self.assertNotEqual(other, start)
        rewrite(output, files, LAPS, changed(start_time=other))
        self.assertEqual(read_laps(output, files, key, store).status, "laps")

    def test_values_of_another_form_in_the_output(self) -> None:
        output, store, files, key, _digest = self.copy()
        laps = sorted(load(output / LAPS), key=lambda row: row["lap_ordinal_within_session"])
        for name, values in (
            ("a timer time of text", {"total_timer_time": "3500"}),
            ("a speed of true", {"avg_speed": True}),
            ("a heart rate that is not a number", {"avg_heart_rate": float("nan")}),
            ("a start without its offset", {"start_time": "1990-01-11T13:46:40"}),
            ("a start that is not a time", {"start_time": "start"}),
            ("a start of a number", {"start_time": 1}),
            ("a heart rate too large for a float", {"avg_heart_rate": 10**400}),
            ("a maximum heart rate of text", {"max_heart_rate": "150"}),
            ("a maximum heart rate that is not a number", {"max_heart_rate": float("nan")}),
            ("a timer time too large for a float", {"total_timer_time": 10**400}),
        ):
            with self.subTest(name):
                rewrite(output, files, LAPS, [{**laps[0], **values}, *laps[1:]])
                self.assertStops("OUTPUT_CHANGED", output, files, key, store)

    def test_files_of_the_output_unlike_its_manifest(self) -> None:
        output, store, files, key, _digest = self.copy()
        laps = load(output / LAPS)
        (output / LAPS).write_text(json.dumps(laps[::-1]), encoding="utf-8")
        self.assertStops("OUTPUT_CHANGED", output, files, key, store)
        output, store, files, key, _digest = self.copy()
        self.assertStops("OUTPUT_CHANGED", output, {k: v for k, v in files.items() if k != SESSIONS}, key, store)
        self.assertStops("OUTPUT_NOT_AVAILABLE", output, {**files, LINKS: (128 * 1024 * 1024 + 1, files[LINKS][1])}, key, store)
        rewrite(output, files, LINEAGE, {"account_store_id": 1})
        self.assertStops("OUTPUT_CHANGED", output, files, key, store)

    def test_the_fit_file_in_the_store(self) -> None:
        output, store, files, key, digest = self.copy()
        data = blob(store, digest).read_bytes()
        cases = {
            "removed": lambda path: writable(path).unlink(),
            "another content": lambda path: writable(path).write_bytes(data[:-1] + bytes([data[-1] ^ 1])),
            "cut short": lambda path: writable(path).write_bytes(data[: len(data) // 2]),
            "no folder of blobs": lambda path: remove_folder(path.parents[2]),
        }
        expected = {"removed": "fit_missing", "another content": "fit_changed", "cut short": "fit_changed", "no folder of blobs": "fit_missing"}
        for name, change in cases.items():
            with self.subTest(name):
                output, store, files, key, digest = self.copy()
                change(blob(store, digest))
                self.assertReason(read_laps(output, files, key, store), expected[name])

    def test_a_registration_writing_beside_the_blob(self) -> None:
        # A registration writes a blob under a name of its own first, and puts
        # it in place whole: that file is not read.
        output, store, files, key, digest = self.copy()
        path = blob(store, digest)
        temporary = path.with_name(f".{digest}.12345.tmp")
        temporary.write_bytes(path.read_bytes())
        self.assertEqual(read_laps(output, files, key, store).status, "laps")
        writable(path).unlink()
        self.assertReason(read_laps(output, files, key, store), "fit_missing")

    def test_the_limit_of_a_fit_file(self) -> None:
        output, store, files, key, digest = self.copy()
        size = blob(store, digest).stat().st_size
        self.assertEqual(fit_reading.MAX_FIT_BYTES, 32 * 1024 * 1024)
        with mock.patch.object(fit_reading, "MAX_FIT_BYTES", size):
            self.assertEqual(read_laps(output, files, key, store).status, "laps")
        with mock.patch.object(fit_reading, "MAX_FIT_BYTES", size - 1):
            self.assertReason(read_laps(output, files, key, store), "fit_too_large")

    def test_a_fit_file_not_read_as_an_activity(self) -> None:
        output, store, files, key, digest = self.copy()
        with mock.patch.object(lap_kinds, "MAX_LAPS", 2):
            self.assertReason(read_laps(output, files, key, store), "fit_not_activity")
        # A session that the FIT file does not have (its number 1 of one).
        session_key = f"fit_session:{digest}:1"
        rewrite(output, files, LINKS, [{**load(output / LINKS)[0], "fit_session_key": session_key}])
        rewrite(output, files, SESSIONS, [{**load(output / SESSIONS)[0], "fit_session_key": session_key, "session_ordinal": 1}])
        rewrite(output, files, LAPS, [{**row, "fit_session_key": session_key, "session_ordinal": 1} for row in load(output / LAPS)])
        self.assertReason(read_laps(output, files, key, store), "fit_not_activity")

    def test_fit_times_out_of_range(self) -> None:
        # As fit.parser gives them: no start (a field of 64 bits can hold them).
        for seconds in (2**64, 2**40, -(2**40)):
            with self.subTest(seconds):
                self.assertIsNone(fit_reading._fit_instant(seconds))
        self.assertEqual(fit_reading._fit_instant(0), datetime(1989, 12, 31, tzinfo=timezone.utc))

    def test_the_key_of_an_activity_of_a_reading(self) -> None:
        rows = tuple(Row(1, {}, frozenset(), {"key": key}) for key in ("a", "b", "b", ""))
        self.assertEqual([activity_key(rows, ref) for ref in range(4)], ["a", None, None, None])
        self.assertIsNone(activity_key((Row(1, {}, frozenset(), {}),), 0))

    def test_why_laps_cannot_be_shown_before_a_file_is_read(self) -> None:
        # Stage X10 of v2.3.0: what the output alone tells, in the order of the
        # server and read_laps: a key that the activity has not or shares
        # (as activity_key finds), then an output without its lineage.
        rows = tuple(Row(1, {}, frozenset(), {"key": key}) for key in ("a", "b", "b", "", "c"))
        rows += (Row(1, {}, frozenset(), {}),)
        refs = range(len(rows))
        shared = ["key_shared" if activity_key(rows, ref) is None else None for ref in refs]
        self.assertEqual(shared, [None, "key_shared", "key_shared", "key_shared", None, "key_shared"])
        self.assertEqual(known_unavailable({LINEAGE: (1, "0" * 64)}, rows, refs), dict(enumerate(shared)))
        self.assertEqual(
            known_unavailable({}, rows, refs),
            {ref: reason or "not_from_store" for ref, reason in enumerate(shared)},
        )
        # Only the places asked for, each once.
        self.assertEqual(known_unavailable({}, rows, [4, 1]), {4: "not_from_store", 1: "key_shared"})
        self.assertEqual(known_unavailable({}, rows, []), {})
        # The same as read_laps, which an output made without a store tells.
        output, store, files, key, _digest = self.copy("no_store")
        self.assertNotIn(LINEAGE, files)
        made = (Row(1, {}, frozenset(), {"key": key}),)
        self.assertEqual(known_unavailable(files, made, [0]), {0: read_laps(output, files, key, store).reason})
        self.assertEqual(read_laps(output, files, key, store).reason, "not_from_store")

    def test_the_answer_holds_no_place_digest_or_key(self) -> None:
        self.assertEqual(
            REASONS,
            (
                "not_from_store",
                "no_store",
                "other_store",
                "store_unreadable",
                "no_link",
                "key_shared",
                "fit_missing",
                "fit_too_large",
                "fit_changed",
                "fit_not_activity",
                "laps_differ",
            ),
        )
        names = lambda kind: [field for field in kind.__dataclass_fields__]  # noqa: E731
        self.assertEqual(names(Laps), ["status", "reason", "laps", "unknown_kind"])
        self.assertEqual(
            names(LapRow), ["kind", "elapsed_s", "timer_s", "distance_m", "avg_heart_rate", "max_heart_rate", "avg_cadence", "avg_speed"]
        )
        for name, change in WAYS.items():
            with self.subTest(name):
                output, store, files, key, digest = self.copy()
                change(output, store, files, key, digest)
                try:
                    answer = read_laps(output, files, key, store)
                except OutputActionError as exc:
                    text = repr(exc) + repr(exc.args)
                else:
                    text = repr(answer)
                    self.assertIn(answer.reason, (None, *REASONS))
                for secret in (str(store), str(output), digest, digest[:8], key, ACCOUNT):
                    self.assertNotIn(secret, text)


class LinksInTheStoreTest(Fixture):
    """A link, a junction, or another reparse point at any step of the way to
    store.json or the blob is refused, also where it leads to the same
    content, by both ways of opening."""

    def modes(self) -> list[bool]:
        return [True, False] if fit_reading._OPENS_AT else [False]

    def steps(self, store: Path, digest: str) -> list[Path]:
        return [
            store / "store.json",
            store / "blobs",
            store / "blobs" / "sha256",
            store / "blobs" / "sha256" / digest[:2],
            blob(store, digest),
        ]

    @unittest.skipIf(WINDOWS, "symbolic links need a privilege on Windows; its junctions are tested below")
    def test_a_symbolic_link_at_each_step(self) -> None:
        for mode in self.modes():
            for index in range(6):
                with self.subTest(dir_fd=mode, step=index), mock.patch.object(fit_reading, "_OPENS_AT", mode):
                    output, store, files, key, digest = self.copy()
                    if index == 0:
                        real = store.with_name("store-real")
                        store.rename(real)
                        make_link(real, store, folder=True)
                    else:
                        step = self.steps(store, digest)[index - 1]
                        real = step.with_name(step.name + "-real")
                        step.rename(real)
                        make_link(real, step, folder=real.is_dir())
                    self.assertReason(read_laps(output, files, key, store), "store_unreadable")

    @unittest.skipUnless(WINDOWS, "junctions are of Windows")
    def test_a_junction_at_each_folder(self) -> None:
        import _winapi

        for index in range(4):
            with self.subTest(step=index):
                output, store, files, key, digest = self.copy()
                step = store if index == 0 else self.steps(store, digest)[index]
                real = step.with_name(step.name + "-real")
                step.rename(real)
                _winapi.CreateJunction(str(real), str(step))
                self.assertReason(read_laps(output, files, key, store), "store_unreadable")

    def moved_store(self) -> tuple[Path, Path, dict[str, tuple[int, str]], str, Path, Path]:
        """A copy whose store is the folder snapshots of a folder elsewhere,
        and an empty folder to remember: the output, the empty folder, the
        files, the key, the folder elsewhere, and the store."""
        output, store, files, key, _digest = self.copy()
        empty = store.parent / "empty"
        empty.mkdir()
        elsewhere = store.parent / "elsewhere"
        elsewhere.mkdir()
        store.rename(elsewhere / "snapshots")
        return output, empty, files, key, elsewhere, elsewhere / "snapshots"

    @unittest.skipIf(WINDOWS, "symbolic links need a privilege on Windows; a junction made in place is tested below")
    def test_the_folder_snapshots_is_that_of_the_folder_opened(self) -> None:
        # Codex's second read of the diff of X9c-2: once the remembered folder
        # is found without store.json, it is put elsewhere, and a link to a
        # folder whose folder snapshots is a store of the output is put at its
        # place. The folder snapshots is that of the folder opened: there is
        # none (by descriptors), or the folder before it is not as it was (by
        # paths); the store elsewhere is never read.
        for mode in self.modes():
            with self.subTest(dir_fd=mode), mock.patch.object(fit_reading, "_OPENS_AT", mode):
                output, empty, files, key, elsewhere, store = self.moved_store()
                self.assertEqual(read_laps(output, files, key, elsewhere).status, "laps")
                real_read = fit_reading._Root.read
                moved: list[bool] = []

                def reading(root, parts, limit):
                    try:
                        return real_read(root, parts, limit)
                    except fit_reading._Missing:
                        if not moved:
                            moved.append(True)
                            empty.rename(empty.with_name("empty-old"))
                            make_link(elsewhere, empty, folder=True)
                        raise

                with mock.patch.object(fit_reading._Root, "read", autospec=True, side_effect=reading):
                    answer = read_laps(output, files, key, empty)
                self.assertEqual(moved, [True])
                self.assertReason(answer, "no_store" if mode else "store_unreadable")

    def test_a_remembered_folder_that_was_not_there_has_no_folder_in_it(self) -> None:
        # Codex's second read of the diff of X9c-2: a remembered folder that is
        # not there has no folder snapshots in it, also where a link (on
        # Windows a junction) to a folder whose folder snapshots is a store of
        # the output is put at its place right after.
        output, empty, files, key, elsewhere, store = self.moved_store()
        missing = empty.with_name("not-yet")
        real_enter = fit_reading._Root.__enter__
        made: list[bool] = []

        def entering(root):
            try:
                return real_enter(root)
            except fit_reading._Missing:
                if not made:
                    made.append(True)
                    if WINDOWS:
                        import _winapi

                        _winapi.CreateJunction(str(elsewhere), str(missing))
                    else:
                        make_link(elsewhere, missing, folder=True)
                raise

        with mock.patch.object(fit_reading._Root, "__enter__", new=entering):
            answer = read_laps(output, files, key, missing)
        self.assertEqual(made, [True])
        self.assertReason(answer, "no_store")

    @unittest.skipUnless(WINDOWS, "junctions are of Windows")
    def test_a_folder_made_a_junction_before_its_folder_snapshots_is_opened(self) -> None:
        # Codex's second read of the diff of X9c-2: the remembered folder, held
        # and found without store.json, made a junction in its place to a
        # folder whose folder snapshots is a store of the output. The system
        # has that folder snapshots elsewhere than in the folder held: refused
        # before a byte of it is read.
        output, empty, files, key, elsewhere, store = self.moved_store()
        real_read = fit_reading._Root.read
        made: list[bool] = []

        def reading(root, parts, limit):
            try:
                return real_read(root, parts, limit)
            except fit_reading._Missing:
                if not made:
                    made.append(True)
                    junction_in_place(empty, elsewhere)
                raise

        with mock.patch.object(fit_reading._Root, "read", autospec=True, side_effect=reading):
            answer = read_laps(output, files, key, empty)
        self.assertEqual(made, [True])
        self.assertReason(answer, "store_unreadable")

    @unittest.skipUnless(WINDOWS, "junctions are of Windows")
    def test_a_junction_put_in_place_of_a_folder_while_the_store_is_read(self) -> None:
        # Between the reading of store.json and that of the blob: a folder of
        # the way made a junction to a folder outside the store, which the
        # reading holds as itself and refuses before a byte outside is read;
        # the folder of the store, held, cannot be renamed (Codex's second to
        # fourth reads of the diff of X9c-1).
        import _winapi

        for step in ("blobs", "store"):
            with self.subTest(step=step):
                output, store, files, key, digest = self.copy()
                outside = store.parent / "outside"
                outside.mkdir()
                read: list[tuple[int, int]] = []
                real_fdopen, real_link = os.fdopen, fit_reading._link
                moved: list[bool] = []

                def reading(descriptor, *args, **kwargs):
                    status = os.fstat(descriptor)
                    read.append((status.st_dev, status.st_ino))
                    return real_fdopen(descriptor, *args, **kwargs)

                def linking(*args):
                    source = store / "blobs" if step == "blobs" else store
                    try:
                        source.rename(outside / source.name)
                    except PermissionError:
                        moved.append(False)
                    else:
                        moved.append(True)
                        _winapi.CreateJunction(str(outside / source.name), str(source))
                    return real_link(*args)

                with mock.patch.object(fit_reading, "_link", side_effect=linking), mock.patch.object(os, "fdopen", side_effect=reading):
                    answer = read_laps(output, files, key, store)
                if step == "blobs":
                    self.assertEqual(moved, [True])
                    self.assertReason(answer, "store_unreadable")
                    moved_blob = outside / "blobs" / "sha256" / digest[:2] / digest
                    status = os.stat(moved_blob)
                    self.assertNotIn((status.st_dev, status.st_ino), read)
                else:
                    self.assertEqual((moved, answer.status), ([False], "laps"))

    @unittest.skipUnless(WINDOWS, "junctions are of Windows")
    def test_a_folder_held_made_a_junction_in_its_place_while_the_store_is_read(self) -> None:
        # The folder of the blob, held and looked at, emptied and made itself
        # a junction to a folder outside the store just before the blob is
        # opened: the opening leads outside, which is refused before a byte
        # of the file there is read (Codex's fifth read of the diff of X9c-1).
        output, store, files, key, digest = self.copy()
        folder = blob(store, digest).parent
        outside = store.parent / "outside" / folder.name
        outside.mkdir(parents=True)
        read: list[tuple[int, int]] = []
        real_fdopen, real_open_file = os.fdopen, fit_reading._open_file
        changed: list[bool] = []

        def reading(descriptor, *args, **kwargs):
            status = os.fstat(descriptor)
            read.append((status.st_dev, status.st_ino))
            return real_fdopen(descriptor, *args, **kwargs)

        def opening(path, *args):
            if str(path).endswith(digest) and not changed:
                changed.append(True)
                os.replace(folder / digest, outside / digest)
                junction_in_place(folder, outside)
            return real_open_file(path, *args)

        with mock.patch.object(fit_reading, "_open_file", side_effect=opening), mock.patch.object(os, "fdopen", side_effect=reading):
            self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        status = os.stat(outside / digest)
        self.assertEqual(changed, [True])
        self.assertNotIn((status.st_dev, status.st_ino), read)

    @unittest.skipUnless(WINDOWS, "junctions are of Windows")
    def test_the_place_where_the_system_has_the_file(self) -> None:
        # A file opened through a junction is where the junction leads: it is
        # refused before a byte is read, where the place expected is that of
        # the junction and the name of the file.
        import _winapi

        output, store, files, key, digest = self.copy()
        real = blob(store, digest).parent
        link = store.parent / "through"
        _winapi.CreateJunction(str(real), str(link))
        held = fit_reading._hold(link)
        try:
            through = fit_reading._final_path(held) + "\\" + digest
        finally:
            fit_reading._close_handle(held)
        held = fit_reading._hold(real)
        try:
            here = fit_reading._final_path(held) + "\\" + digest
        finally:
            fit_reading._close_handle(held)
        self.assertNotEqual(through, here)
        descriptor = fit_reading._open_file(real / digest, here)
        os.close(descriptor)
        with self.assertRaises(fit_reading._Unavailable):
            fit_reading._open_file(link / digest, through)


class SwapsWhileReadTest(Fixture):
    """A file or a folder of the store put in place of another between the
    looks and the reading, by the way of opening by paths, which Windows
    takes: the changes are made without links, so that they run there too.
    On Windows the folders of the way are held from before they are looked
    at until the file is read: one cannot be renamed meanwhile, so that the
    store is read as it is (Codex's fourth read of the diff of X9c-1)."""

    def renamed(self, source: Path, target: Path) -> bool:
        """Rename, or tell that the reading holds the folder (Windows)."""
        try:
            source.rename(target)
        except PermissionError:
            if not WINDOWS:
                raise
            return False
        return True

    def opening_blob(self, digest: str, change):
        """A patch of fit_reading._open_file that makes ``change`` once, just
        before the opening of the blob, and the descriptors of the blob."""
        real = fit_reading._open_file
        opened: list[int] = []

        def opening(path, *args):
            if str(path).endswith(digest) and not opened:
                change()
                opened.append(real(path, *args))
                return opened[-1]
            return real(path, *args)

        return mock.patch.object(fit_reading, "_open_file", side_effect=opening), opened

    def test_by_path_a_blob_put_in_place_of_another(self) -> None:
        output, store, files, key, digest = self.copy()
        path = blob(store, digest)

        def change() -> None:
            # The same bytes and time in a new file: another identity only.
            new = path.with_name("new")
            new.write_bytes(path.read_bytes())
            before = os.stat(path)
            os.utime(new, ns=(before.st_atime_ns, before.st_mtime_ns))
            os.replace(new, writable(path))

        patch, opened = self.opening_blob(digest, change)
        with mock.patch.object(fit_reading, "_OPENS_AT", False), patch:
            self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        self.assertEqual(len(opened), 1)

    def test_by_path_a_blob_swapped_for_the_opening_only(self) -> None:
        # Another file at the opening, the blob again at the look after the
        # reading: only the comparison of the file opened with the one looked
        # at before sees it.
        output, store, files, key, digest = self.copy()
        path = blob(store, digest)
        kept = path.with_name("kept")
        real_close = os.close

        def change() -> None:
            os.replace(path, kept)
            path.write_bytes(kept.read_bytes())

        patch, opened = self.opening_blob(digest, change)

        def closing(descriptor):
            real_close(descriptor)
            if descriptor in opened and kept.exists():
                os.replace(kept, writable(path))

        with mock.patch.object(fit_reading, "_OPENS_AT", False), patch, mock.patch.object(os, "close", side_effect=closing):
            self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        self.assertEqual(len(opened), 1)
        self.assertFalse(kept.exists())

    def test_by_path_a_blob_put_in_place_of_another_after_it_was_read(self) -> None:
        output, store, files, key, digest = self.copy()
        path = blob(store, digest)
        real_close = os.close
        done: list[bool] = []
        patch, opened = self.opening_blob(digest, lambda: None)

        def closing(descriptor):
            real_close(descriptor)
            if descriptor in opened and not done:
                done.append(True)
                new = path.with_name("new")
                new.write_bytes(path.read_bytes())
                os.replace(new, writable(path))

        with mock.patch.object(fit_reading, "_OPENS_AT", False), patch, mock.patch.object(os, "close", side_effect=closing):
            self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        self.assertEqual(done, [True])

    def test_by_path_a_folder_copied_in_place_of_another(self) -> None:
        output, store, files, key, digest = self.copy()
        moved: list[bool] = []

        def change() -> None:
            moved.append(self.renamed(store / "blobs", store / "blobs-old"))
            if moved[-1]:
                shutil.copytree(store / "blobs-old", store / "blobs")

        patch, opened = self.opening_blob(digest, change)
        with mock.patch.object(fit_reading, "_OPENS_AT", False), patch:
            answer = read_laps(output, files, key, store)
        if WINDOWS:
            self.assertEqual((moved, answer.status), ([False], "laps"))
        else:
            self.assertEqual(moved, [True])
            self.assertReason(answer, "store_unreadable")

    def test_by_path_the_store_put_in_place_of_another_after_it_was_opened(self) -> None:
        output, store, files, key, digest = self.copy()
        real_link = fit_reading._link

        moved: list[bool] = []

        def linking(*args):
            # Between the reading of store.json and that of the blob.
            moved.append(self.renamed(store, store.with_name("store-old")))
            if moved[-1]:
                shutil.copytree(store.with_name("store-old"), store)
            return real_link(*args)

        with mock.patch.object(fit_reading, "_OPENS_AT", False), mock.patch.object(fit_reading, "_link", side_effect=linking):
            answer = read_laps(output, files, key, store)
        if WINDOWS:
            self.assertEqual((moved, answer.status), ([False], "laps"))
        else:
            self.assertEqual(moved, [True])
            self.assertReason(answer, "store_unreadable")

    def test_a_link_in_place_of_a_file_of_the_output_at_the_opening(self) -> None:
        # Not followed (O_NOFOLLOW; on Windows FILE_FLAG_OPEN_REPARSE_POINT):
        # Codex's fourth read of the diff of X9c-1.
        output, store, files, key, _digest = self.copy()
        path = output / LINEAGE
        real = fit_reading._open_output
        changed: list[bool] = []

        def opening(name):
            if Path(name) == path and not changed:
                changed.append(True)
                kept = path.with_name("lineage-kept")
                os.replace(path, kept)
                make_link(kept, path, folder=False)
            return real(name)

        with mock.patch.object(fit_reading, "_open_output", side_effect=opening):
            self.assertStops("OUTPUT_NOT_AVAILABLE", output, files, key, store)
        self.assertEqual(changed, [True])

    def test_the_same_place_letter_for_letter(self) -> None:
        # Two places that a folding of case takes for one are two places.
        place = "\\\\?\\C:\\Straße\\store\\blobs"
        self.assertTrue(fit_reading._same_place(place, place))
        for other in (place.replace("Straße", "STRASSE"), place.replace("store", "STORE")):
            with self.subTest(other):
                self.assertEqual(other.casefold(), place.casefold())
                self.assertFalse(fit_reading._same_place(other, place))

    def test_the_names_at_the_top_are_those_of_the_folder_opened(self) -> None:
        # Where a folder has no store.json, the names that a store writes are
        # looked at in the folder opened, by its descriptor where the system
        # looks so, not at its place again: a folder that holds what a store
        # writes, put at the place meanwhile, is not taken for it (stage
        # X9c-2). On Windows the folder is held, and cannot be renamed
        # meanwhile.
        output, store, files, key, _digest = self.copy()
        empty = store.parent / "empty"
        empty.mkdir()
        real_read = fit_reading._Root.read
        moved: list[bool] = []

        def reading(root, parts, limit):
            try:
                return real_read(root, parts, limit)
            except fit_reading._Missing:
                # Its store.json is not there: the folder is put elsewhere,
                # and one that holds a folder blobs is put at its place.
                if not moved:
                    moved.append(self.renamed(empty, empty.with_name("empty-old")))
                    if moved[-1]:
                        (empty / "blobs").mkdir(parents=True)
                raise

        with mock.patch.object(fit_reading._Root, "read", autospec=True, side_effect=reading):
            answer = read_laps(output, files, key, empty)
        self.assertEqual(moved, [False] if WINDOWS else [True])
        self.assertReason(answer, "no_store")

    def test_a_blob_that_changes_while_it_is_read(self) -> None:
        for mode in [True, False] if fit_reading._OPENS_AT else [False]:
            with self.subTest(dir_fd=mode):
                output, store, files, key, digest = self.copy()
                path = writable(blob(store, digest))
                real_fdopen = os.fdopen

                def reading(descriptor, *args, **kwargs):
                    handle = real_fdopen(descriptor, *args, **kwargs)
                    status = os.stat(path)
                    os.utime(path, ns=(status.st_atime_ns, status.st_mtime_ns + 1_000_000_000))
                    return handle

                with mock.patch.object(fit_reading, "_OPENS_AT", mode), mock.patch.object(os, "fdopen", side_effect=reading):
                    self.assertReason(read_laps(output, files, key, store), "store_unreadable")

    def test_files_and_folders_without_an_identity(self) -> None:
        # A system that gives no identity of a file (st_ino 0) could not tell
        # a file put in place of another for a moment: such a file or folder
        # is not read.
        real_fstat, real_lstat = os.fstat, os.lstat

        def without(status: os.stat_result) -> types.SimpleNamespace:
            values = {name: getattr(status, name) for name in dir(status) if name.startswith("st_")}
            return types.SimpleNamespace(**{**values, "st_ino": 0})

        for mode in [True, False] if fit_reading._OPENS_AT else [False]:
            with self.subTest(dir_fd=mode, step="every file"), mock.patch.object(fit_reading, "_OPENS_AT", mode):
                output, store, files, key, digest = self.copy()
                self.assertEqual(read_laps(output, files, key, store).status, "laps")
                with mock.patch.object(os, "fstat", side_effect=lambda descriptor: without(real_fstat(descriptor))):
                    self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        for name in ("store", "blobs", digest[:2], digest):
            with self.subTest(dir_fd=False, step=name), mock.patch.object(fit_reading, "_OPENS_AT", False):
                output, store, files, key, digest = self.copy()

                def looking(path, *args, **kwargs):
                    status = real_lstat(path, *args, **kwargs)
                    return without(status) if Path(path).name == name else status

                with mock.patch.object(os, "lstat", side_effect=looking):
                    self.assertReason(read_laps(output, files, key, store), "store_unreadable")


@unittest.skipIf(WINDOWS, "the changes are made with symbolic links")
class ChangesWhileReadTest(Fixture):
    """A step changed between the looks and the opening, with links and pipes."""

    def test_a_pipe_in_place_of_the_blob(self) -> None:
        # Not read, and not waited for: a pipe without a writer would hold
        # the reading, which holds the laps of the view page.
        for mode in [True, False] if fit_reading._OPENS_AT else [False]:
            with self.subTest(dir_fd=mode), mock.patch.object(fit_reading, "_OPENS_AT", mode):
                output, store, files, key, digest = self.copy()
                path = blob(store, digest)
                writable(path).unlink()
                os.mkfifo(path)
                helper, stop = pipe_releaser(path)
                started = time.monotonic()
                answer = read_laps(output, files, key, store)
                took = time.monotonic() - started
                stop.set()
                helper.join()
                self.assertReason(answer, "store_unreadable")
                self.assertLess(took, 2.0)

    def test_a_pipe_in_place_of_a_file_of_the_output(self) -> None:
        # Before the reading, and at the opening (Codex's second read of the
        # diff of X9c-1): refused as the output not available, not waited for.
        output, store, files, key, _digest = self.copy()
        path = output / LINEAGE
        os.replace(path, path.with_name("lineage-kept"))
        os.mkfifo(path)
        started = time.monotonic()
        self.assertStops("OUTPUT_NOT_AVAILABLE", output, files, key, store)
        self.assertLess(time.monotonic() - started, 2.0)
        output, store, files, key, _digest = self.copy()
        path = output / LINEAGE

        def change() -> None:
            os.replace(path, path.with_name("lineage-kept"))
            os.mkfifo(path)

        patch, done = self.swapping(lambda name, kwargs: Path(name) == path, change)
        helper, stop = pipe_releaser(path)
        started = time.monotonic()
        with patch:
            try:
                read_laps(output, files, key, store)
                got = "laps"
            except OutputActionError as exc:
                got = exc.code
        took = time.monotonic() - started
        stop.set()
        helper.join()
        self.assertEqual((done, got), ([True], "OUTPUT_NOT_AVAILABLE"))
        self.assertLess(took, 2.0)

    def test_by_path_a_folder_put_in_place_of_another(self) -> None:
        output, store, files, key, digest = self.copy()

        def change() -> None:
            (store / "blobs").rename(store / "blobs-real")
            make_link(store / "blobs-real", store / "blobs", folder=True)

        patch, done = self.swapping(lambda name, kwargs: str(name).endswith(digest), change)
        with mock.patch.object(fit_reading, "_OPENS_AT", False), patch:
            self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        self.assertEqual(done, [True])

    @unittest.skipUnless(fit_reading._OPENS_AT, "opens files in an open folder")
    def test_in_the_open_folder_a_link_put_in_place_of_a_folder(self) -> None:
        output, store, files, key, digest = self.copy()
        decoy, _decoy_store, _f, _k, _d = self.copy("no_kinds")

        def change() -> None:
            (store / "blobs").rename(store / "blobs-real")
            make_link(_decoy_store / "blobs", store / "blobs", folder=True)

        patch, done = self.swapping(lambda name, kwargs: name == "blobs" and kwargs.get("dir_fd") is not None, change)
        read: list[tuple[int, int]] = []
        real_fdopen = os.fdopen

        def reading(descriptor, *args, **kwargs):
            status = os.fstat(descriptor)
            read.append((status.st_dev, status.st_ino))
            return real_fdopen(descriptor, *args, **kwargs)

        with patch, mock.patch.object(os, "fdopen", side_effect=reading):
            self.assertReason(read_laps(output, files, key, store), "store_unreadable")
        self.assertEqual(done, [True])
        # No file of the other store was read.
        for path in _decoy_store.rglob("*"):
            if path.is_file():
                status = os.stat(path)
                self.assertNotIn((status.st_dev, status.st_ino), read)

    @unittest.skipUnless(fit_reading._OPENS_AT, "opens files in an open folder")
    def test_in_the_open_folder_the_store_moved_after_it_was_opened(self) -> None:
        # The files are read in the folder that was opened, not in what took
        # its place.
        output, store, files, key, digest = self.copy()
        _decoy_output, decoy_store, _f, _k, _d = self.copy("no_kinds")
        real_open = os.open
        moved: list[bool] = []

        def opening(path, flags, *args, **kwargs):
            descriptor = real_open(path, flags, *args, **kwargs)
            if not moved and Path(path) == store:
                moved.append(True)
                store.rename(store.with_name("store-moved"))
                make_link(decoy_store, store, folder=True)
            return descriptor

        read: list[tuple[int, int]] = []
        real_fdopen = os.fdopen

        def reading(descriptor, *args, **kwargs):
            status = os.fstat(descriptor)
            read.append((status.st_dev, status.st_ino))
            return real_fdopen(descriptor, *args, **kwargs)

        with mock.patch.object(os, "open", side_effect=opening), mock.patch.object(os, "fdopen", side_effect=reading):
            answer = read_laps(output, files, key, store)
        self.assertEqual(moved, [True])
        self.assertEqual([lap.kind for lap in answer.laps], NAMES)
        # No file of the store that took its place was read.
        for path in decoy_store.rglob("*"):
            if path.is_file():
                status = os.stat(path)
                self.assertNotIn((status.st_dev, status.st_ino), read)


class NothingWrittenTest(Fixture):
    """The reading writes nothing, prints nothing, and leaves the files of the
    store and of the output as they were, on every way of its answer."""

    WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def state(self, *folders: Path) -> list[tuple[str, int, int, int]]:
        found = []
        for folder in folders:
            for path in sorted(folder.rglob("*")):
                status = os.lstat(path)
                found.append((str(path), status.st_size, status.st_mtime_ns, status.st_ctime_ns))
        return found

    def test_every_file_opened_is_closed(self) -> None:
        real_open, real_close = os.open, os.close
        for mode in [True, False] if fit_reading._OPENS_AT else [False]:
            for name, change in WAYS.items():
                with self.subTest(dir_fd=mode, way=name):
                    output, store, files, key, digest = self.copy()
                    change(output, store, files, key, digest)
                    opened: list[int] = []
                    closed: list[int] = []

                    def opening(*args, **kwargs):
                        descriptor = real_open(*args, **kwargs)
                        opened.append(descriptor)
                        return descriptor

                    def closing(descriptor):
                        closed.append(descriptor)
                        return real_close(descriptor)

                    handles: list[int] = []
                    let_go: list[int] = []
                    files_opened: list[int] = []
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(mock.patch.object(fit_reading, "_OPENS_AT", mode))
                        stack.enter_context(mock.patch.object(os, "open", side_effect=opening))
                        stack.enter_context(mock.patch.object(os, "close", side_effect=closing))
                        if fit_reading._WINDOWS:
                            # The handles of Windows: each closed, or handed to a
                            # descriptor of a file, which os.close closes.
                            real_handle, real_close_handle = fit_reading._open_handle, fit_reading._close_handle

                            def handle_opening(*args):
                                handles.append(real_handle(*args))
                                return handles[-1]

                            def handle_closing(handle):
                                let_go.append(handle)
                                return real_close_handle(handle)

                            import msvcrt

                            real_handed = msvcrt.open_osfhandle

                            def handing(handle, flags):
                                files_opened.append(real_handed(handle, flags))
                                opened.append(files_opened[-1])
                                return files_opened[-1]

                            stack.enter_context(mock.patch.object(fit_reading, "_open_handle", side_effect=handle_opening))
                            stack.enter_context(mock.patch.object(fit_reading, "_close_handle", side_effect=handle_closing))
                            stack.enter_context(mock.patch.object(msvcrt, "open_osfhandle", side_effect=handing))
                        try:
                            read_laps(output, files, key, store)
                        except OutputActionError:
                            pass
                    if name == "laps":
                        self.assertTrue(opened)
                        self.assertEqual(bool(handles), fit_reading._WINDOWS)
                    self.assertEqual(sorted(closed), sorted(opened))
                    self.assertEqual(len(handles), len(let_go) + len(files_opened))

    def test_no_write_on_any_way(self) -> None:
        def broken(output: Path, store: Path, files, key: str, digest: str) -> None:
            return None

        ways = {
            "laps": broken,
            "fit_missing": lambda o, s, f, k, d: writable(blob(s, d)).unlink(),
            "fit_changed": lambda o, s, f, k, d: writable(blob(s, d)).write_bytes(b"x"),
            "other_store": lambda o, s, f, k, d: writable(s / "store.json").write_text(json.dumps({**load(s / "store.json"), "account_store_id": "another-account"}), encoding="utf-8"),
            "store_unreadable": lambda o, s, f, k, d: writable(s / "store.json").write_bytes(b"{"),
            "laps_differ": lambda o, s, f, k, d: rewrite(o, f, LAPS, sorted(load(o / LAPS), key=lambda row: row["lap_ordinal_within_session"])[:-1]),
            "OUTPUT_CHANGED": lambda o, s, f, k, d: (o / LAPS).write_text("[]", encoding="utf-8"),
        }
        real_open, real_builtin_open = os.open, builtins.open

        def checked_open(path, flags, *args, **kwargs):
            self.assertFalse(flags & self.WRITE_FLAGS, f"opened to write: {flags}")
            return real_open(path, flags, *args, **kwargs)

        def checked_builtin_open(file, mode="r", *args, **kwargs):
            self.assertIn(mode, ("r", "rb"), f"opened to write: {mode}")
            return real_builtin_open(file, mode, *args, **kwargs)

        refused = mock.Mock(side_effect=AssertionError("written"))
        for mode in [True, False] if fit_reading._OPENS_AT else [False]:
            for name, change in ways.items():
                with self.subTest(dir_fd=mode, way=name):
                    output, store, files, key, digest = self.copy()
                    change(output, store, files, key, digest)
                    before = self.state(store, output)
                    printed = io.StringIO()
                    with contextlib.ExitStack() as stack:
                        stack.enter_context(mock.patch.object(fit_reading, "_OPENS_AT", mode))
                        stack.enter_context(mock.patch.object(os, "open", side_effect=checked_open))
                        stack.enter_context(mock.patch.object(builtins, "open", side_effect=checked_builtin_open))
                        stack.enter_context(mock.patch.object(io, "open", side_effect=checked_builtin_open))
                        for module, names in (
                            (os, ("replace", "rename", "remove", "unlink", "rmdir", "mkdir", "makedirs", "chmod", "utime", "truncate", "write", "link", "symlink")),
                            (shutil, ("copyfile", "copy", "copy2", "move", "rmtree")),
                            (Path, ("write_bytes", "write_text", "touch", "mkdir", "unlink", "rename", "replace", "chmod")),
                        ):
                            for attribute in names:
                                if hasattr(module, attribute):
                                    stack.enter_context(mock.patch.object(module, attribute, refused))
                        stack.enter_context(contextlib.redirect_stdout(printed))
                        stack.enter_context(contextlib.redirect_stderr(printed))
                        try:
                            answer = read_laps(output, files, key, store)
                        except OutputActionError as exc:
                            answer = exc.code
                    self.assertEqual(answer if isinstance(answer, str) else (answer.reason or answer.status), name)
                    self.assertEqual(printed.getvalue(), "")
                    self.assertEqual(self.state(store, output), before)
        refused.assert_not_called()


class StoreMetadataTest(Fixture):
    """check_store_metadata is the check of load_store: the same error, in
    the same order (stage X9c-1 of v2.3.0)."""

    def test_the_same_error_as_load_store(self) -> None:
        changes = {
            "newer": {"format": "garmin-running-data-normalizer-snapshot-store-v2"},
            "not of this app": {"format": "another"},
            "other version": {"format_version": 2},
            "other contract": {"contract_version": "0"},
            "not single writer": {"single_writer": False},
            "automatic deletion": {"automatic_deletion": True},
            "garbage collection": {"garbage_collection": True},
            "an id of another form": {"account_store_id": "x"},
            "no id": {"account_store_id": None},
            "a time without its offset": {"created_at_utc": "2030-01-01T00:00:00"},
            # The first check that fails is told: the version before the policies.
            "two at once": {"format_version": 2, "single_writer": False},
            "the policies before the id": {"garbage_collection": True, "account_store_id": "x"},
        }
        for name, change in changes.items():
            with self.subTest(name):
                _output, store, _files, _key, _digest = self.copy()
                metadata = {**load(store / "store.json"), **change}
                if change.get("account_store_id", "") is None:
                    del metadata["account_store_id"]
                writable(store / "store.json").write_text(json.dumps(metadata), encoding="utf-8")
                with self.assertRaises(SnapshotStoreError) as loaded:
                    load_store(store)
                with self.assertRaises(SnapshotStoreError) as checked:
                    check_store_metadata(metadata)
                self.assertIs(type(checked.exception), type(loaded.exception))
                self.assertEqual((checked.exception.code, str(checked.exception)), (loaded.exception.code, str(loaded.exception)))
        # The order of the checks: the version, the policies, the id, the time.
        _output, store, _files, _key, _digest = self.copy()
        metadata = load(store / "store.json")
        for change, code, words in (
            ({"format_version": 2, "single_writer": False}, "SNAPSHOT_STORE_VERSION_UNSUPPORTED", "newer version"),
            ({"single_writer": False, "automatic_deletion": True}, "SNAPSHOT_STORE_INVALID", "single-writer"),
            ({"automatic_deletion": True, "garbage_collection": True}, "SNAPSHOT_STORE_INVALID", "automatic deletion"),
            ({"garbage_collection": True, "account_store_id": "x"}, "SNAPSHOT_STORE_INVALID", "garbage collection"),
            ({"account_store_id": "x", "created_at_utc": "then"}, "SNAPSHOT_STORE_INVALID", "account_store_id"),
            ({"created_at_utc": "then"}, "SNAPSHOT_STORE_INVALID", "created_at_utc"),
        ):
            with self.subTest(change):
                with self.assertRaises(SnapshotStoreError) as checked:
                    check_store_metadata({**metadata, **change})
                self.assertEqual(checked.exception.code, code)
                self.assertIn(words, str(checked.exception))

    def test_a_store_that_load_store_reads(self) -> None:
        _output, store, _files, _key, _digest = self.copy()
        _root, metadata = load_store(store)
        self.assertIsNone(check_store_metadata(metadata))


class FixtureBytesTest(unittest.TestCase):
    def test_the_synthetic_fit_files_of_earlier_tests_are_the_same(self) -> None:
        # Many tests and the comparison of deterministic outputs read these
        # bytes; stage X9c-1 added the laps' intensities only where asked.
        for options, digest in (
            ({}, "7ce53d5096be2bc48c2a19b03deb29fd3c67d5caf32614fa3bb9ca6f13c61877"),
            ({"sessions": 2}, "97572652cb12bc2e31ea3ea2395dddabdcf6f9031bd44d76e8b7968ef126a0f2"),
            (
                {"session_running_dynamics": (1, 2, 3, 4, 5, 6), "lap_running_dynamics": (1, 2, 3, 4, 5, 6)},
                "983129369cb5cf78e81865bf1a157b7c9a017cedf1a6c1302bf9a7a9e5d03b46",
            ),
        ):
            with self.subTest(options):
                self.assertEqual(hashlib.sha256(synthetic_fit(**options)).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
