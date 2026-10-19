from __future__ import annotations

import errno
import hashlib
import json
import ntpath
import os
import re
import shutil
import stat
from collections import Counter
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, ContextManager, Iterator
from zipfile import ZipFile, ZipInfo

from ..common.private_files import (
    PRIVATE_DIRECTORY_MODE,
    ensure_private_directory,
    open_private_file,
)
from ..intake.accounts import account_values, names_account
from ..intake.archive import (
    ArchiveLimitError,
    ArchiveLimits,
    MemberTooLargeError,
    UnsafeArchiveError,
    digest_member,
    validated_members,
)
from ..intake.discovery import ZIP_NOT_READABLE, ZIP_TOO_LARGE, ZIP_UNSAFE_MEMBER
from ..intake.roots import (
    OTHER_ACCOUNT_MESSAGE,
    ExportView,
    MixedExportsError,
    OpenedExport,
    open_export,
)
from ..intake.source import (
    DAMAGED_ZIP_ERRORS,
    HIDDEN_PLACE,
    CorruptArchiveError,
    ExportFile,
    ExportTooLargeError,
    InputNotReadableError,
    TempSpaceError,
    is_disk_full,
    is_zip_input,
    place_can_be_shown,
    walk_paths,
)
from ..output_location import (
    WINDOWS_MAX_FILE_PATH,
    WINDOWS_MAX_FOLDER_PATH,
    long_paths_enabled,
    utf16_length,
)
from ..stops import STOPS, stop_text
from .policies import CONTRACT_VERSION, REGISTRY_VERSION


STORE_FORMAT = "garmin-running-data-normalizer-snapshot-store-v1"
# Every format of this app's stores starts so; another version is newer.
STORE_FORMAT_FAMILY = "garmin-running-data-normalizer-snapshot-store-"
STORE_FORMAT_VERSION = 1
IMMUTABLE_FILE_MODE = stat.S_IRUSR
ACCOUNT_STORE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LOCK_NAME = ".single-writer.lock"


class SnapshotStoreError(ValueError):
    """Fail-closed snapshot store contract error.

    ``code`` names the problem (stage A3d-3b); the stops of the store's
    contract, such as an argument that is not valid, keep
    ``SNAPSHOT_LIFECYCLE_FAILED``. ``places`` name, for
    ``SNAPSHOT_STORE_NOT_READABLE``, what cannot be opened inside the store.
    They are not part of the message: they are shown only where the command
    is started.
    """

    def __init__(
        self,
        message: str,
        code: str = "SNAPSHOT_LIFECYCLE_FAILED",
        *,
        places: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.places = list(places) if places is not None else None


# The stops of the Snapshot Store say what happened (stage A3d-3b); the CLI
# adds the next step of their code from the table of stops (stage A5b).
STORE_NOT_WRITABLE_MESSAGE = "this app cannot write in the Snapshot Store"
STORE_SPACE_MESSAGE = "the drive of the Snapshot Store does not have enough free space"
NEW_STORE_NOT_WRITABLE_MESSAGE = "this app cannot create the Snapshot Store there"
NEW_STORE_SPACE_MESSAGE = "the place for the Snapshot Store does not have enough free space"
REGISTRATION_INCOMPLETE_MESSAGE = STOPS["SNAPSHOT_REGISTRATION_INCOMPLETE"].what
SNAPSHOT_MISSING_MESSAGE = (
    "the Snapshot Store lists a Snapshot whose files are missing, for example "
    "because its folder was deleted by hand or removed by a sync app"
)
STORE_VERSION_MESSAGE = "the Snapshot Store was made by a newer version of this app"
STORE_NOT_FOUND_MESSAGE = STOPS["SNAPSHOT_STORE_NOT_FOUND"].what
# The place of the store (stage B4a): every snapshot command refuses a link,
# and ``snapshot init`` makes no folder above a new store.
STORE_SYMLINK_MESSAGE = STOPS["SNAPSHOT_STORE_SYMLINK"].what
NEW_STORE_PARENT_MESSAGE = STOPS["SNAPSHOT_STORE_PARENT_NOT_FOUND"].what
NEW_STORE_NOT_EMPTY_MESSAGE = STOPS["SNAPSHOT_STORE_NOT_EMPTY"].what
NEW_STORE_INSIDE_STORE_MESSAGE = STOPS["SNAPSHOT_STORE_INSIDE_STORE"].what
# The deepest paths that a registration writes inside a store (stage B6c):
# the temporary file of the inventory of a Snapshot, whose name holds the id
# of the Snapshot ("snapshot-" and 64 characters) and the number of the
# process (up to 10 digits), in the folder of the Snapshot, and that folder.
# Windows without long paths refuses them for a store of more than about 70
# characters; until stage B6c, the registration stopped with COMMAND_FAILED
# after it had copied part of the Export.
SNAPSHOT_ID_LENGTH = len("snapshot-") + 64
DEEPEST_STORE_FILE = (
    len("snapshots/") + SNAPSHOT_ID_LENGTH + len("/.") + SNAPSHOT_ID_LENGTH
    + len(".inventory.json.") + 10 + len(".tmp")
)
DEEPEST_STORE_FOLDER = len("snapshots/") + SNAPSHOT_ID_LENGTH
PATH_TOO_LONG_MESSAGE = STOPS["SNAPSHOT_STORE_PATH_TOO_LONG"].what
# The store.json of a store above a new one is read up to this size; a
# larger file is not one that this app wrote.
MAX_STORE_METADATA_BYTES = 64 * 1024
# A registration (stage B4b-1): until then, these stopped with
# SNAPSHOT_LIFECYCLE_FAILED.
LABEL_INVALID_MESSAGE = STOPS["SNAPSHOT_LABEL_INVALID"].what
LABEL_EXISTS_MESSAGE = STOPS["SNAPSHOT_LABEL_EXISTS"].what
TIME_INVALID_MESSAGE = STOPS["SNAPSHOT_TIME_INVALID"].what
INPUT_INSIDE_STORE_MESSAGE = STOPS["SNAPSHOT_INPUT_INSIDE_STORE"].what
# The lock file of a registration holds the number of its process and a line
# break, which Windows writes as CR LF, and nothing while it is being made; a
# file of another form or size is not this app's lock, and is never removed
# (stage B4b-2).
MAX_LOCK_BYTES = 64
LOCK_CONTENT_RE = re.compile(rb"[0-9]{0,20}\r?\n?")
UNLOCK_NOT_CONFIRMED_MESSAGE = STOPS["SNAPSHOT_UNLOCK_NOT_CONFIRMED"].what
LOCK_NOT_FOUND_MESSAGE = STOPS["SNAPSHOT_LOCK_NOT_FOUND"].what
LOCK_INVALID_MESSAGE = STOPS["SNAPSHOT_LOCK_INVALID"].what
# The input of a registration that cannot be read safely, as a run says it
# (stage A5b-2).
INPUT_DISCOVERY_MESSAGE = STOPS["INPUT_DISCOVERY_FAILED"].what
REGISTRATION_INPUT_CHANGED_MESSAGE = "the Export changed while it was registered"
# What a store holds that does not stop a command but should be known; the
# CLI prints each as a NOTE line, which never means a stop, with the meaning
# and the next step of the stop of the same code (stage A5b).
NOTICE_MESSAGES = {
    "SNAPSHOT_STORE_LOCKED": stop_text("SNAPSHOT_STORE_LOCKED"),
    "SNAPSHOT_REGISTRATION_INCOMPLETE": stop_text("SNAPSHOT_REGISTRATION_INCOMPLETE"),
    "SNAPSHOT_STORE_PATH_TOO_LONG": stop_text("SNAPSHOT_STORE_PATH_TOO_LONG"),
}


def windows_store_paths_too_long(store_root: str) -> bool:
    """Return whether the deepest paths that a registration writes inside
    the store at ``store_root`` reach the limits of Windows without long
    paths (stage B6c). ``store_root`` is measured in its absolute Windows
    form, in UTF-16 units, as the place of an output is."""
    base = ntpath.abspath(store_root)
    if base.startswith("\\\\?\\"):
        return False  # Such paths have no MAX_PATH limit.
    length = utf16_length(base) + 1
    return (
        length + DEEPEST_STORE_FILE >= WINDOWS_MAX_FILE_PATH
        or length + DEEPEST_STORE_FOLDER >= WINDOWS_MAX_FOLDER_PATH
    )


def store_paths_too_long(store_root: str | Path) -> bool:
    """Return whether a registration could not write the files of a store
    at ``store_root`` on this system: on Windows without long paths only."""
    if os.name != "nt" or long_paths_enabled():
        return False
    return windows_store_paths_too_long(str(store_root))


def check_store_paths(store_root: str | Path) -> None:
    """Stop with SNAPSHOT_STORE_PATH_TOO_LONG before anything is written,
    for a new store and for a registration alike (stage B6c)."""
    if store_paths_too_long(store_root):
        raise SnapshotStoreError(PATH_TOO_LONG_MESSAGE, "SNAPSHOT_STORE_PATH_TOO_LONG")


def store_not_readable_message(places: list[str] | None = None) -> str:
    """The message of ``SNAPSHOT_STORE_NOT_READABLE``. With ``places``, for
    where the command is started, it names the first folder or file that
    cannot be opened and how many more; without them, it names none."""
    if places is None:
        return STOPS["SNAPSHOT_STORE_NOT_READABLE"].what
    first = places[0] if places and places[0] else "the Snapshot Store folder itself"
    # A name that could change the line, as the check shows it (stage B3c).
    if not place_can_be_shown(first):
        first = HIDDEN_PLACE
    more = len(places) - 1
    named = first if more <= 0 else f"{first} and {more} more"
    return f"{STOPS['SNAPSHOT_STORE_NOT_READABLE'].what}: {named}"


def shown_store_message(exc: SnapshotStoreError) -> str:
    """The message of a store error where the command is started: with the
    places that cannot be opened, when there are some."""
    if exc.code == "SNAPSHOT_STORE_NOT_READABLE" and exc.places is not None:
        return store_not_readable_message(exc.places)
    return str(exc)


def _place(root: Path, path: Path) -> str:
    """Where a path is inside the store, as the CLI names it."""
    if path == root:
        return ""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def not_readable_error(root: Path, *paths: Path) -> SnapshotStoreError:
    """The error for folders or files of the store that cannot be opened."""
    return SnapshotStoreError(
        store_not_readable_message(),
        "SNAPSHOT_STORE_NOT_READABLE",
        places=[_place(root, path) for path in paths],
    )


def invalid_store_error(detail: str) -> SnapshotStoreError:
    """The error for a store whose files are damaged or were changed."""
    return SnapshotStoreError(f"the Snapshot Store is damaged: {detail}", "SNAPSHOT_STORE_INVALID")


def _input_changed() -> SnapshotStoreError:
    return SnapshotStoreError(REGISTRATION_INPUT_CHANGED_MESSAGE, "INPUT_CHANGED")


def _write_error(error: OSError, *, new_store: bool = False) -> SnapshotStoreError | None:
    """The error for one met while the store was written: no free space, or no
    permission; None for any other."""
    if is_disk_full(error):
        message = NEW_STORE_SPACE_MESSAGE if new_store else STORE_SPACE_MESSAGE
        return SnapshotStoreError(message, "SNAPSHOT_STORE_SPACE_INSUFFICIENT")
    if isinstance(error, PermissionError) or error.errno == errno.EROFS:
        message = NEW_STORE_NOT_WRITABLE_MESSAGE if new_store else STORE_NOT_WRITABLE_MESSAGE
        return SnapshotStoreError(message, "SNAPSHOT_STORE_NOT_WRITABLE")
    return None


@contextmanager
def _writing(*, new_store: bool = False) -> Iterator[None]:
    """Give an error met while the store is written its code. Only writes to
    the store go inside, so that an error of the input is never taken for one
    of the store."""
    try:
        yield
    except OSError as exc:
        error = _write_error(exc, new_store=new_store)
        if error is None:
            raise
        raise error from exc


def _exists(root: Path, path: Path, *, follow: bool = True) -> bool:
    """Whether a path inside the store exists, following a link as
    ``Path.exists`` does unless ``follow`` is false; one that cannot be
    looked at stops instead of reading as absent."""
    try:
        os.stat(path) if follow else os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except PermissionError as exc:
        raise not_readable_error(root, root if path == root else path.parent) from exc
    return True


def _open_folder(root: Path, folder: Path) -> list[os.DirEntry[str]]:
    """The entries of a folder of the store, sorted by name; none when it is
    missing, and a stop when it cannot be opened."""
    try:
        with os.scandir(folder) as entries:
            return sorted(entries, key=lambda entry: entry.name)
    except (FileNotFoundError, NotADirectoryError):
        return []
    except PermissionError as exc:
        raise not_readable_error(root, folder) from exc


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_store_symlink_components(root: Path, path: Path) -> None:
    # A store that holds a link, or a path that leads outside it, is damaged
    # (stage A5b-2); verification names the failure instead.
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise invalid_store_error("a path in it leads outside its folder") from exc
    current = root
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except PermissionError as exc:
            raise not_readable_error(root, current.parent) from exc
        if stat.S_ISLNK(mode):
            raise invalid_store_error("it holds a symbolic link")


def _temporary_name(path: Path) -> Path:
    """The temporary file that a write to the store fills before it takes the
    place of ``path``; ``_remove_temporary_files`` knows these names."""
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def _atomic_write(path: Path, data: bytes) -> None:
    ensure_private_directory(path.parent)
    temporary = _temporary_name(path)
    try:
        with open_private_file(temporary) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        # A file that was not written whole is removed at once (stage A3d-3b).
        with suppress(OSError):
            temporary.unlink()
        raise


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_write(path, _json_bytes(value))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_aware_iso(value: str, label: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SnapshotStoreError(f"{label} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SnapshotStoreError(f"{label} must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc).isoformat()


def _logical_time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _validate_account_store_id(value: str) -> str:
    if not ACCOUNT_STORE_ID_RE.fullmatch(value):
        raise SnapshotStoreError(
            "account_store_id must be an opaque 3-128 character token"
        )
    return value


def _validate_label(value: str) -> str:
    if not LABEL_RE.fullmatch(value):
        raise SnapshotStoreError(
            "snapshot label must use 1-64 letters, digits, dot, underscore, or hyphen"
        )
    return value


# The checks of a registration, which the GUI makes with the same functions
# before it starts one (stage B4b-1). The checks of a store's records keep
# their own words above, as a damaged store names them.
def new_snapshot_label(value: Any) -> str:
    """The label of a new Snapshot, or SNAPSHOT_LABEL_INVALID."""
    if not isinstance(value, str) or not LABEL_RE.fullmatch(value):
        raise SnapshotStoreError(LABEL_INVALID_MESSAGE, "SNAPSHOT_LABEL_INVALID")
    return value


def registration_times(requested: Any, downloaded: Any, observed: Any) -> tuple[str, str, str]:
    """The times of an Export in UTC, each with its offset, requested no
    later than downloaded and downloaded no later than observed; or
    SNAPSHOT_TIME_INVALID, with what is wrong."""
    try:
        times = (
            _require_aware_iso(requested, "export_requested_at"),
            _require_aware_iso(downloaded, "export_downloaded_at"),
            _require_aware_iso(observed, "export_observed_at"),
        )
    except SnapshotStoreError as exc:
        raise SnapshotStoreError(f"{TIME_INVALID_MESSAGE}: {exc}", "SNAPSHOT_TIME_INVALID") from exc
    if not (_logical_time(times[0]) <= _logical_time(times[1]) <= _logical_time(times[2])):
        raise SnapshotStoreError(
            f"{TIME_INVALID_MESSAGE}: snapshot timestamps must be requested <= downloaded <= observed",
            "SNAPSHOT_TIME_INVALID",
        )
    return times


def check_input_apart(source: Path, root: Path) -> None:
    """An Export and a store, both resolved, are separate folders; or
    SNAPSHOT_INPUT_INSIDE_STORE."""
    if source == root or root in source.parents or source in root.parents:
        raise SnapshotStoreError(INPUT_INSIDE_STORE_MESSAGE, "SNAPSHOT_INPUT_INSIDE_STORE")


def check_label_free(manifests: list[dict[str, Any]], label: str, snapshot_id: str | None = None) -> None:
    """No other Snapshot of the store has ``label``; or
    SNAPSHOT_LABEL_EXISTS. The Snapshot ``snapshot_id`` itself may have it."""
    if any(item["snapshot_label"] == label and item["snapshot_id"] != snapshot_id for item in manifests):
        raise SnapshotStoreError(LABEL_EXISTS_MESSAGE, "SNAPSHOT_LABEL_EXISTS")


def _load_json(path: Path, root: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except PermissionError as exc:
        raise not_readable_error(root, path) from exc
    except OSError as exc:
        raise invalid_store_error(f"invalid snapshot store metadata: {path.name}") from exc
    try:
        value = json.loads(data.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise invalid_store_error(f"invalid snapshot store metadata: {path.name}") from exc
    if not isinstance(value, dict):
        raise invalid_store_error(f"snapshot store metadata must be an object: {path.name}")
    return value


def _store_root(store_root: str | Path) -> Path:
    requested = Path(store_root)
    try:
        is_link = requested.is_symlink()
    except PermissionError as exc:
        raise SnapshotStoreError(
            store_not_readable_message(), "SNAPSHOT_STORE_NOT_READABLE", places=[""]
        ) from exc
    if is_link:
        # Until stage B4a, SNAPSHOT_LIFECYCLE_FAILED.
        raise SnapshotStoreError(STORE_SYMLINK_MESSAGE, "SNAPSHOT_STORE_SYMLINK")
    return requested.resolve()


def _check_store_version(metadata: dict[str, Any]) -> None:
    """A store that this version knows, one that a newer version made, or
    one that is not a store of this app (stage A3d-3b). Every earlier
    version wrote the format that this version reads, so another version of
    this app's format is newer."""
    if (
        metadata.get("format") == STORE_FORMAT
        and metadata.get("format_version") == STORE_FORMAT_VERSION
        and metadata.get("contract_version") == CONTRACT_VERSION
        and metadata.get("policy_registry_version") == REGISTRY_VERSION
    ):
        return
    if str(metadata.get("format", "")).startswith(STORE_FORMAT_FAMILY):
        raise SnapshotStoreError(STORE_VERSION_MESSAGE, "SNAPSHOT_STORE_VERSION_UNSUPPORTED")
    raise invalid_store_error("snapshot store format is not supported")


def load_store(store_root: str | Path) -> tuple[Path, dict[str, Any]]:
    root = _store_root(store_root)
    metadata_path = root / "store.json"
    # The store's folder is opened first, so that one that cannot be opened is
    # named instead of reading as a folder without a store.
    entries = _open_folder(root, root)
    try:
        is_file = stat.S_ISREG(os.stat(metadata_path).st_mode)
    except (FileNotFoundError, NotADirectoryError):
        is_file = False
    except PermissionError as exc:
        raise not_readable_error(root, root) from exc
    if not is_file:
        # A folder that holds what a store writes, but not store.json, is a
        # damaged store; any other folder holds no store, which has its own
        # code, whose next step says how to make one (stage A5b-2).
        if any(entry.name in _STORE_ENTRY_NAMES for entry in entries):
            raise invalid_store_error("store.json is missing")
        raise SnapshotStoreError(STORE_NOT_FOUND_MESSAGE, "SNAPSHOT_STORE_NOT_FOUND")
    metadata = _load_json(metadata_path, root)
    _check_store_version(metadata)
    if metadata.get("single_writer") is not True:
        raise invalid_store_error("snapshot store single-writer policy is not enabled")
    if metadata.get("automatic_deletion") is not False:
        raise invalid_store_error("snapshot store enables automatic deletion")
    if metadata.get("garbage_collection") is not False:
        raise invalid_store_error("snapshot store enables garbage collection")
    try:
        _validate_account_store_id(str(metadata.get("account_store_id", "")))
        _require_aware_iso(str(metadata.get("created_at_utc", "")), "created_at_utc")
    except SnapshotStoreError as exc:
        raise invalid_store_error(str(exc)) from exc
    return root, metadata


# The files that ``snapshot init`` writes at the top of a new store.
_STORE_FILE_NAMES = (
    "store.json",
    "registry.json",
    "snapshot_registry.json",
    "snapshot_family_coverage.json",
)
_STORE_FOLDERS = ("blobs/sha256", "blobs", "snapshots", "journal")
# What a store holds at its top besides store.json (stage A5b-2), which tells
# a damaged store from a folder without one. The folder snapshots does not
# count from stage B4a: a folder that holds a store in its folder snapshots,
# as the GUI's default place does, is not a store itself.
_STORE_ENTRY_NAMES = frozenset(
    {name for name in _STORE_FILE_NAMES if name != "store.json"}
    | {relative.split("/", 1)[0] for relative in _STORE_FOLDERS if relative != "snapshots"}
    | {LOCK_NAME}
)


def _remove_new_store(root: Path, made_root: bool) -> None:
    """Remove what a ``snapshot init`` that stopped wrote, by the names that
    it uses, so that it can be run again (stage A3d-3b). The folder was empty
    before; a folder is removed only when it is empty."""
    for name in _STORE_FILE_NAMES:
        for path in (root / name, _temporary_name(root / name)):
            with suppress(OSError):
                if stat.S_ISREG(os.lstat(path).st_mode):
                    path.unlink()
    for relative in _STORE_FOLDERS:
        with suppress(OSError):
            (root / relative).rmdir()
    if made_root:
        with suppress(OSError):
            root.rmdir()


def _store_above(root: Path) -> bool:
    """Whether a folder above ``root`` holds a store of this app. The walk
    ends at the top of the file system. A folder that cannot be opened is
    passed over, and a store.json counts only when it is a regular file of
    at most MAX_STORE_METADATA_BYTES whose format is one of this app's
    stores."""
    for folder in root.parents:
        path = folder / "store.json"
        try:
            status = os.lstat(path)
            if not stat.S_ISREG(status.st_mode) or status.st_size > MAX_STORE_METADATA_BYTES:
                continue
            with open(path, "rb") as handle:
                data = handle.read(MAX_STORE_METADATA_BYTES + 1)
        except OSError:
            continue
        if len(data) > MAX_STORE_METADATA_BYTES:
            continue
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            continue
        if isinstance(value, dict) and str(value.get("format", "")).startswith(STORE_FORMAT_FAMILY):
            return True
    return False


def check_new_store_place(store_root: str | Path) -> Path:
    """Check, without writing, that a new store can be made at
    ``store_root``, and return its place (stage B4a). ``snapshot init`` and
    the GUI share these rules: the place is not a link, it is not inside
    another store, the folder that holds it exists, so that a mistyped place
    makes no folders, and it is new or an empty folder. A folder that holds
    what a store writes, but not store.json, is a damaged store. The caller
    has found no store.json at the place."""
    root = _store_root(store_root)
    if _store_above(root):
        raise SnapshotStoreError(NEW_STORE_INSIDE_STORE_MESSAGE, "SNAPSHOT_STORE_INSIDE_STORE")
    try:
        parent_is_folder = stat.S_ISDIR(os.stat(root.parent).st_mode)
    except (FileNotFoundError, NotADirectoryError):
        parent_is_folder = False
    except PermissionError as exc:
        raise not_readable_error(root, root) from exc
    if not parent_is_folder:
        raise SnapshotStoreError(NEW_STORE_PARENT_MESSAGE, "SNAPSHOT_STORE_PARENT_NOT_FOUND")
    check_store_paths(root)
    try:
        mode = os.stat(root).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return root
    except PermissionError as exc:
        raise not_readable_error(root, root) from exc
    if not stat.S_ISDIR(mode):
        raise SnapshotStoreError(NEW_STORE_NOT_EMPTY_MESSAGE, "SNAPSHOT_STORE_NOT_EMPTY")
    entries = _open_folder(root, root)
    if any(entry.name in _STORE_ENTRY_NAMES for entry in entries):
        raise invalid_store_error("store.json is missing")
    if entries:
        raise SnapshotStoreError(NEW_STORE_NOT_EMPTY_MESSAGE, "SNAPSHOT_STORE_NOT_EMPTY")
    return root


def initialize_store(
    store_root: str | Path,
    account_store_id: str,
) -> dict[str, Any]:
    account_id = _validate_account_store_id(account_store_id)
    root = _store_root(store_root)
    metadata_path = root / "store.json"
    if _exists(root, metadata_path):
        existing_root, existing = load_store(root)
        if existing["account_store_id"] != account_id:
            raise SnapshotStoreError("initialized store belongs to another account boundary")
        return {
            "status": "PASS",
            "initialized": False,
            "account_store_id": account_id,
            "snapshot_count": len(load_manifests(existing_root)),
        }
    # Until stage B4a, a non-empty place stopped with
    # SNAPSHOT_LIFECYCLE_FAILED, and the missing folders above a new store
    # were made.
    check_new_store_place(root)
    made_root = not _exists(root, root)
    metadata = {
        "format": STORE_FORMAT,
        "format_version": STORE_FORMAT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "policy_registry_version": REGISTRY_VERSION,
        "account_store_id": account_id,
        "created_at_utc": _now_utc(),
        "single_writer": True,
        "automatic_deletion": False,
        "garbage_collection": False,
    }
    try:
        with _writing(new_store=True):
            if made_root:
                # The folder that holds it was there when it was checked.
                try:
                    root.mkdir(mode=PRIVATE_DIRECTORY_MODE)
                except FileNotFoundError as exc:
                    raise SnapshotStoreError(
                        NEW_STORE_PARENT_MESSAGE, "SNAPSHOT_STORE_PARENT_NOT_FOUND"
                    ) from exc
            root.chmod(PRIVATE_DIRECTORY_MODE)
            for relative in ("blobs/sha256", "snapshots", "journal"):
                ensure_private_directory(root / relative)
            # store.json last: a store that could not be written whole holds
            # none, and what was written is removed (stage A3d-3b).
            _write_registry(root, [])
            _atomic_json(metadata_path, metadata)
    except BaseException:
        _remove_new_store(root, made_root)
        raise
    return {
        "status": "PASS",
        "initialized": True,
        "account_store_id": account_id,
        "snapshot_count": 0,
    }


def _lock_held_message(lock_path: Path) -> str:
    holder = "an unknown process"
    if not lock_path.is_symlink():
        try:
            recorded = lock_path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            recorded = ""
        if recorded.isdigit():
            holder = f"pid {recorded}"
    return f"the Snapshot Store is locked by another writer ({lock_path.name}, held by {holder})"


@contextmanager
def _store_lock(root: Path) -> Iterator[None]:
    lock_path = root / LOCK_NAME
    try:
        # Creating the lock is the first write of a registration: a store that
        # cannot be written stops here, before the input is read.
        with _writing():
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SnapshotStoreError(_lock_held_message(lock_path), "SNAPSHOT_STORE_LOCKED") from exc
    try:
        with _writing():
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
            os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock_path.unlink(missing_ok=True)


def lock_created_at(store_root: str | Path) -> str | None:
    """When the lock file of a store was written, in UTC to the second, for
    the person who decides whether a registration still runs (stage B4b-2);
    None when the store has none, or one that is not a regular file."""
    try:
        status = os.lstat(Path(store_root) / LOCK_NAME)
    except OSError:
        return None
    if not stat.S_ISREG(status.st_mode):
        return None
    return datetime.fromtimestamp(status.st_mtime, timezone.utc).isoformat(timespec="seconds")


def _same_file(first: os.stat_result, second: os.stat_result) -> bool:
    """Whether two looks at a lock file saw the same file: its kind, size, and
    time, and its identity where the system gives one in both (some ways of
    looking on Windows give none)."""
    if (stat.S_IFMT(first.st_mode), first.st_size, first.st_mtime_ns) != (
        stat.S_IFMT(second.st_mode),
        second.st_size,
        second.st_mtime_ns,
    ):
        return False
    if first.st_ino and second.st_ino:
        return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
    return True


def remove_lock(store_root: str | Path, *, confirmed: bool) -> dict[str, Any]:
    """Remove the lock file that a stopped registration left (stage B4b-2),
    for ``snapshot unlock`` and the GUI alike: only when the person confirmed
    that no snapshot command uses the store, only in a store, and only a
    regular file of this app's form, which is looked at once more just before
    it is removed. Nothing else of the store is touched; the next
    registration completes one that was interrupted."""
    if confirmed is not True:
        raise SnapshotStoreError(UNLOCK_NOT_CONFIRMED_MESSAGE, "SNAPSHOT_UNLOCK_NOT_CONFIRMED")
    root, _metadata = load_store(store_root)
    path = root / LOCK_NAME
    try:
        before = os.lstat(path)
    except FileNotFoundError as exc:
        raise SnapshotStoreError(LOCK_NOT_FOUND_MESSAGE, "SNAPSHOT_LOCK_NOT_FOUND") from exc
    except PermissionError as exc:
        raise not_readable_error(root, path) from exc
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_LOCK_BYTES:
        raise SnapshotStoreError(LOCK_INVALID_MESSAGE, "SNAPSHOT_LOCK_INVALID")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as exc:
        raise SnapshotStoreError(LOCK_NOT_FOUND_MESSAGE, "SNAPSHOT_LOCK_NOT_FOUND") from exc
    except PermissionError as exc:
        raise not_readable_error(root, path) from exc
    except OSError as exc:
        # A link put in its place since, which O_NOFOLLOW refuses.
        raise SnapshotStoreError(LOCK_INVALID_MESSAGE, "SNAPSHOT_LOCK_INVALID") from exc
    try:
        opened = os.fstat(descriptor)
        content = os.read(descriptor, MAX_LOCK_BYTES + 1)
    finally:
        os.close(descriptor)
    if not _same_file(before, opened) or not LOCK_CONTENT_RE.fullmatch(content):
        raise SnapshotStoreError(LOCK_INVALID_MESSAGE, "SNAPSHOT_LOCK_INVALID")
    # Once more just before it is removed: a file put in its place since,
    # such as the lock of a registration that started, is not removed.
    try:
        again = os.lstat(path)
    except FileNotFoundError as exc:
        raise SnapshotStoreError(LOCK_NOT_FOUND_MESSAGE, "SNAPSHOT_LOCK_NOT_FOUND") from exc
    if not _same_file(before, again):
        raise SnapshotStoreError(LOCK_INVALID_MESSAGE, "SNAPSHOT_LOCK_INVALID")
    with _writing():
        os.unlink(path)
    return {"status": "PASS", "removed": LOCK_NAME}


def _there(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def lock_exists(store_root: str | Path) -> bool:
    """Whether a store has a lock file now, as a command looks before it
    starts, to tell later of one that it left (stage A5c)."""
    return _there(Path(store_root) / LOCK_NAME)


def cancel_notices(store_root: str | Path, lock_before: bool) -> list[str]:
    """The notices of a store that a cancelled registration leaves (stage
    A5c, shared with the GUI from stage B4b-2): an interrupted registration,
    and a lock file that was not there before it started. Codes only."""
    root = Path(store_root)
    found = []
    if _there(root / "journal" / "registration.json"):
        found.append("SNAPSHOT_REGISTRATION_INCOMPLETE")
    if not lock_before and lock_exists(root):
        found.append("SNAPSHOT_STORE_LOCKED")
    return found


def _registered_ids(root: Path) -> set[str]:
    """The Snapshots that the registry lists; none when it is missing or
    damaged, as a registration then writes it again from the Snapshots."""
    path = root / "registry.json"
    if not _exists(root, path):
        return set()
    try:
        registry = _load_json(path, root)
    except SnapshotStoreError as exc:
        if exc.code != "SNAPSHOT_STORE_INVALID":
            raise
        return set()
    snapshots = registry.get("snapshots")
    if not isinstance(snapshots, list):
        return set()
    return {
        str(item["snapshot_id"])
        for item in snapshots
        if isinstance(item, dict) and item.get("snapshot_id")
    }


def _manifests_to_write(root: Path) -> list[dict[str, Any]]:
    """The Snapshots, read before the registry is written again. Every
    Snapshot that the registry lists must be there, so that a registration
    never takes one out of it (stage A3d-3b): a registration writes a
    Snapshot before it lists it, so a listed Snapshot without its files was
    removed from the store."""
    manifests = load_manifests(root)
    present = {str(item["snapshot_id"]) for item in manifests}
    if not _registered_ids(root) <= present:
        raise SnapshotStoreError(SNAPSHOT_MISSING_MESSAGE, "SNAPSHOT_STORE_INVALID")
    return manifests


def _recover_journal(root: Path) -> str:
    journal_path = root / "journal" / "registration.json"
    if not _exists(root, journal_path):
        return "not_required"
    journal = _load_json(journal_path, root)
    snapshot_id = str(journal.get("snapshot_id", ""))
    manifests = _manifests_to_write(root)
    committed = any(str(item["snapshot_id"]) == snapshot_id for item in manifests)
    # The registry is written again before the journal is removed, so that a
    # stop on the way leaves the journal for the next registration
    # (stage A3d-3b).
    with _writing():
        _write_registry(root, manifests)
        journal_path.unlink()
    return "completed_commit_reconciled" if committed else "incomplete_registration_reconciled"


def _manifest_paths(root: Path) -> list[Path]:
    """The manifests of the Snapshots. The folders are listed here, instead
    of with ``glob``, which passes over a folder that cannot be opened
    (stage A3d-3b); such a folder stops the command. A folder without a
    manifest is what an interrupted registration leaves, and is passed over
    as before."""
    snapshots_dir = root / "snapshots"
    paths: list[Path] = []
    not_opened: list[Path] = []
    for entry in _open_folder(root, snapshots_dir):
        folder = snapshots_dir / entry.name
        try:
            if not entry.is_dir():
                continue
            os.stat(folder / "manifest.json")
        except (FileNotFoundError, NotADirectoryError):
            continue
        except PermissionError:
            not_opened.append(folder)
            continue
        paths.append(folder / "manifest.json")
    if not_opened:
        raise not_readable_error(root, *not_opened)
    return paths


def _check_manifest(manifest: dict[str, Any], path: Path) -> None:
    required = {
        "snapshot_id",
        "snapshot_content_id",
        "snapshot_label",
        "account_store_id",
        "export_requested_at",
        "export_downloaded_at",
        "export_observed_at",
        "registered_at",
        "file_count",
        "archive_member_count",
        "total_bytes",
        "objects",
    }
    if not required.issubset(manifest):
        raise SnapshotStoreError("snapshot manifest is missing required metadata")
    if manifest.get("snapshot_id") != path.parent.name:
        raise SnapshotStoreError("snapshot directory and manifest identity differ")
    _validate_label(str(manifest["snapshot_label"]))
    _validate_account_store_id(str(manifest["account_store_id"]))
    for field in (
        "export_requested_at",
        "export_downloaded_at",
        "export_observed_at",
        "registered_at",
    ):
        _require_aware_iso(str(manifest[field]), field)
    if not isinstance(manifest["objects"], list) or any(
        not isinstance(item, dict) for item in manifest["objects"]
    ):
        raise SnapshotStoreError("snapshot manifest objects must be a list of objects")
    if manifest.get("export_completion_confirmed") is not True:
        raise SnapshotStoreError("snapshot manifest lacks complete-export confirmation")
    if manifest.get("immutable") is not True:
        raise SnapshotStoreError("snapshot manifest is not immutable")
    if manifest.get("automatic_deletion") is not False:
        raise SnapshotStoreError("snapshot manifest enables automatic deletion")


def load_manifests(root: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in _manifest_paths(root):
        manifest = _load_json(path, root)
        # A manifest that breaks the store's contract is a damaged store
        # (stage A3d-3b); the message says what is wrong.
        try:
            _check_manifest(manifest, path)
        except SnapshotStoreError as exc:
            raise invalid_store_error(str(exc)) from exc
        manifests.append(manifest)
    try:
        return sorted(
            manifests,
            key=lambda item: (
                _logical_time(str(item["export_observed_at"])),
                str(item["snapshot_id"]),
            ),
        )
    except (TypeError, ValueError) as exc:
        raise invalid_store_error("snapshot logical ordering metadata is invalid") from exc


def _inventory_document(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "garmin-running-data-normalizer-snapshot-inventory-v1",
        "contract_version": CONTRACT_VERSION,
        "snapshot_id": manifest["snapshot_id"],
        "objects": manifest["objects"],
    }


def _registry_documents(
    manifests: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshots = []
    for logical_order, manifest in enumerate(manifests, start=1):
        snapshots.append(
            {
                "snapshot_id": manifest["snapshot_id"],
                "snapshot_label": manifest["snapshot_label"],
                "logical_order": logical_order,
                "export_requested_at": manifest["export_requested_at"],
                "export_downloaded_at": manifest["export_downloaded_at"],
                "export_observed_at": manifest["export_observed_at"],
                "registered_at": manifest["registered_at"],
                "snapshot_content_id": manifest["snapshot_content_id"],
                "file_count": manifest["file_count"],
                "archive_member_count": manifest["archive_member_count"],
                "total_bytes": manifest["total_bytes"],
                "export_completion_confirmed": True,
                "manifest_sha256": _sha256_bytes(_stable_json_bytes(manifest)),
                "inventory_sha256": _sha256_bytes(
                    _stable_json_bytes(_inventory_document(manifest))
                ),
            }
        )
    registry = {
        "format": "garmin-running-data-normalizer-snapshot-registry-v1",
        "contract_version": CONTRACT_VERSION,
        "snapshots": snapshots,
    }
    family_coverage: dict[str, dict[str, Any]] = {}
    for logical_order, manifest in enumerate(manifests, start=1):
        for family, count in manifest.get("family_counts", {}).items():
            entry = family_coverage.setdefault(
                str(family),
                {
                    "snapshot_presence": [],
                    "object_count": 0,
                },
            )
            entry["snapshot_presence"].append(logical_order)
            entry["object_count"] += int(count)
    coverage = {
        "format": "garmin-running-data-normalizer-snapshot-family-coverage-v1",
        "contract_version": CONTRACT_VERSION,
        "snapshot_count": len(manifests),
        "families": {
            family: {
                **details,
                "presence_pattern": "".join(
                    "1" if index in details["snapshot_presence"] else "0"
                    for index in range(1, len(manifests) + 1)
                ),
            }
            for family, details in sorted(family_coverage.items())
        },
    }
    return registry, coverage


def _write_registry(root: Path, manifests: list[dict[str, Any]]) -> None:
    registry, coverage = _registry_documents(manifests)
    _atomic_json(root / "registry.json", registry)
    _atomic_json(root / "snapshot_registry.json", registry)
    _atomic_json(root / "snapshot_family_coverage.json", coverage)


def _source_family(relative_path: str) -> str:
    for part in Path(relative_path.replace("!", "/")).parts:
        if part.startswith("DI-Connect-") or part == "DI-GOLF":
            return part
    return "unknown"


def _blob_relative_path(digest: str) -> str:
    return f"blobs/sha256/{digest[:2]}/{digest}"


def _validate_inventory_object(row: dict[str, Any]) -> tuple[str, int, str]:
    digest = str(row.get("sha256", ""))
    if not SHA256_RE.fullmatch(digest):
        raise SnapshotStoreError("snapshot inventory contains an invalid SHA-256")
    byte_count = row.get("bytes")
    if (
        isinstance(byte_count, bool)
        or not isinstance(byte_count, int)
        or byte_count < 0
    ):
        raise SnapshotStoreError("snapshot inventory contains an invalid byte count")
    blob_relative_path = str(row.get("blob_relative_path", ""))
    if blob_relative_path != _blob_relative_path(digest):
        raise SnapshotStoreError("snapshot inventory blob path is not content-derived")
    relative_path = str(row.get("relative_path", ""))
    normalized = PurePosixPath(relative_path.replace("!", "/"))
    if (
        not relative_path
        or normalized.is_absolute()
        or ".." in normalized.parts
    ):
        raise SnapshotStoreError("snapshot inventory source path is unsafe")
    if row.get("object_kind") not in {"file", "archive_member"}:
        raise SnapshotStoreError("snapshot inventory object kind is unsupported")
    return digest, byte_count, blob_relative_path


@dataclass(frozen=True)
class _StreamedFile:
    """A file of the snapshot input, copied to its blob without holding it in memory."""

    open: Callable[[], ContextManager[BinaryIO]]
    size: int


def _preserve_blob(root: Path, digest: str, source: Path | _StreamedFile, size: int) -> bool:
    """Copy one file of the input to the store, unless the store holds it.

    The input is read again here: a file that cannot be read now, or whose
    content differs, changed after it was listed (stage A3d-3b). A file that
    was not copied whole is removed at once.
    """
    destination = root / _blob_relative_path(digest)
    _reject_store_symlink_components(root, destination)
    if _exists(root, destination):
        try:
            same = destination.stat().st_size == size and sha256_file(destination) == digest
        except PermissionError as exc:
            raise not_readable_error(root, destination) from exc
        if not same:
            raise invalid_store_error("existing immutable blob failed integrity validation")
        return False
    with _writing():
        ensure_private_directory(destination.parent)
    _reject_store_symlink_components(root, destination)
    temporary = _temporary_name(destination)
    _reject_store_symlink_components(root, temporary)
    try:
        with _writing():
            handle = open_private_file(temporary)
        with handle, ExitStack() as reading:
            try:
                opened = source.open() if isinstance(source, _StreamedFile) else source.open("rb")
                input_handle = reading.enter_context(opened)
            except OSError as exc:
                raise _input_changed() from exc
            while True:
                try:
                    chunk = input_handle.read(1024 * 1024)
                except OSError as exc:
                    raise _input_changed() from exc
                if not chunk:
                    break
                with _writing():
                    handle.write(chunk)
            with _writing():
                handle.flush()
                os.fsync(handle.fileno())
        if sha256_file(temporary) != digest:
            raise _input_changed()
        with _writing():
            os.replace(temporary, destination)
            destination.chmod(IMMUTABLE_FILE_MODE)
    except BaseException:
        with suppress(OSError):
            temporary.unlink()
        raise
    return True


def _input_read_error(error: BaseException) -> SnapshotStoreError:
    """The error for an input that cannot be read safely, as a run gives it
    (stage A5b-2): one that went away changed, and any other is
    ``INPUT_DISCOVERY_FAILED``."""
    if isinstance(error, FileNotFoundError):
        return _input_changed()
    return SnapshotStoreError(INPUT_DISCOVERY_MESSAGE, "INPUT_DISCOVERY_FAILED")


@contextmanager
def _open_member(archive: ZipFile, info: ZipInfo) -> Iterator[BinaryIO]:
    """Open a member of a ZIP file inside the snapshot input, to copy it.

    The member was read whole when the input was listed, so one that cannot
    be read now changed, as any file of the input that cannot be read again
    (stage A5b-2)."""
    try:
        with archive.open(info, "r") as handle:
            yield handle
    except DAMAGED_ZIP_ERRORS as exc:
        raise _input_changed() from exc


@contextmanager
def _open_snapshot_input(source: Path) -> Iterator[OpenedExport]:
    """Open the input and choose its Export, as a run does.

    Raises ``MixedExportsError`` when the input holds different Exports.
    """
    if not is_zip_input(source):
        # A folder that this app may not open stops the registration, as it
        # stops a run, instead of a Snapshot without its files (stage A3d-3a).
        try:
            paths, not_opened = walk_paths(source)
        except FileNotFoundError as exc:
            raise _input_changed() from exc
        for path in paths:
            if path.is_symlink():
                # As a run stops for it (stage A5b-2).
                raise SnapshotStoreError(INPUT_DISCOVERY_MESSAGE, "INPUT_DISCOVERY_FAILED")
        if not_opened:
            raise InputNotReadableError(
                ["" if path == source else path.relative_to(source).as_posix() for path in not_opened]
            )
    with ExitStack() as stack:
        try:
            opened = stack.enter_context(open_export(source))
        except InputNotReadableError:
            raise
        # The problems of the Export ZIP file itself keep their codes, as in
        # a run: an Export ZIP file that is too large to read directly is an
        # UnsafeArchiveError too (stage A5b-2).
        except (CorruptArchiveError, ExportTooLargeError, TempSpaceError):
            raise
        except PermissionError as exc:
            raise InputNotReadableError([""]) from exc
        except (*DAMAGED_ZIP_ERRORS, OSError, UnsafeArchiveError) as exc:
            raise _input_read_error(exc) from exc
        yield opened


def _scan_members(
    relative: str,
    item: ExportFile,
    export: ExportView,
    inventory: list[dict[str, Any]],
    payloads: dict[str, Path | _StreamedFile],
) -> str | None:
    """List and hash the members of one ZIP file in the Export.

    Return None when the members are listed, or why they cannot be, as a run
    leaves the ZIP file out (stage A3c-2): it cannot be read, a member fails a
    safety check, or it exceeds the limits for one ZIP file. The members are
    then not listed. A member over the limit for one file is not listed
    alone; the stored ZIP file holds it. Problems of the Export ZIP file
    itself still stop the registration.
    """
    try:
        export.local_path(item)
    except MemberTooLargeError:
        return ZIP_TOO_LARGE
    except (CorruptArchiveError, ExportTooLargeError, TempSpaceError):
        raise
    except PermissionError as exc:
        raise InputNotReadableError([export.place_of(item)]) from exc
    except (*DAMAGED_ZIP_ERRORS, OSError, UnsafeArchiveError) as exc:
        raise _input_read_error(exc) from exc
    members: list[dict[str, Any]] = []
    member_payloads: dict[str, _StreamedFile] = {}
    try:
        # Members are hashed now and copied to the store later, in parts
        # both times, from the ZIP file that the input keeps open.
        archive = export.archive(item)
        for info in validated_members(archive, export.limits, oversize=[]):
            member_digest, member_bytes = digest_member(archive, info, export.limits)
            export.count_read(member_bytes)
            member_payloads.setdefault(
                member_digest,
                _StreamedFile(
                    lambda archive=archive, info=info: _open_member(archive, info),
                    member_bytes,
                ),
            )
            logical_path = f"{relative}!{info.filename}"
            members.append(
                {
                    "object_kind": "archive_member",
                    "relative_path": logical_path,
                    "container_relative_path": relative,
                    "archive_member_path": info.filename,
                    "sha256": member_digest,
                    "bytes": member_bytes,
                    "source_family": _source_family(logical_path),
                    "extension": Path(info.filename).suffix.lower(),
                    "blob_relative_path": _blob_relative_path(member_digest),
                    "parser_state": "parser_unsupported",
                }
            )
    except (CorruptArchiveError, ExportTooLargeError, TempSpaceError):
        raise
    except DAMAGED_ZIP_ERRORS:
        return ZIP_NOT_READABLE
    except ArchiveLimitError:
        return ZIP_TOO_LARGE
    except UnsafeArchiveError:
        return ZIP_UNSAFE_MEMBER
    except PermissionError as exc:
        raise InputNotReadableError([export.place_of(item)]) from exc
    except OSError as exc:
        raise _input_read_error(exc) from exc
    inventory.extend(members)
    for digest, payload in member_payloads.items():
        payloads.setdefault(digest, payload)
    return None


def _archive_state(source: Path) -> tuple[int, int]:
    """The size and time of an Export ZIP file; one that went away changed."""
    try:
        status = source.stat()
    except FileNotFoundError as exc:
        raise _input_changed() from exc
    return status.st_size, status.st_mtime_ns


def _scan_source(
    source: Path,
    export: ExportView,
    report: Callable[[int, int], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Path | _StreamedFile], set[str]]:
    """List the Export's files and archive members, and the accounts its records name.

    The accounts are compared during registration only and never stored.
    ``report``, when given, receives the number of files read and of all.
    """
    inventory: list[dict[str, Any]] = []
    payloads: dict[str, Path | _StreamedFile] = {}
    accounts: set[str] = set()
    files = export.files()
    if not files:
        raise SnapshotStoreError("snapshot input contains no files")
    archive_before = _archive_state(source) if is_zip_input(source) else None
    for done, item in enumerate(files):
        if report is not None:
            report(done, len(files))
        relative = item.relative_path
        if (
            item.suffix == ".json"
            and names_account(relative)
            and item.size <= export.limits.max_member_bytes
        ):
            # Read within the limits of a run; a file beyond them is left to
            # the run, which reports it, and is not compared here.
            try:
                data = export.read(item)
            except UnsafeArchiveError:
                data = None
            except PermissionError as exc:
                raise InputNotReadableError([export.place_of(item)]) from exc
            except FileNotFoundError as exc:
                raise _input_changed() from exc
            if data is not None:
                accounts |= account_values([(relative, data)])
        if item.path is not None:
            path = item.path
            try:
                before = (path.stat().st_size, path.stat().st_mtime_ns)
                digest = sha256_file(path)
                after = (path.stat().st_size, path.stat().st_mtime_ns)
            except PermissionError as exc:
                raise InputNotReadableError([export.place_of(item)]) from exc
            except FileNotFoundError as exc:
                raise _input_changed() from exc
            if before != after:
                raise _input_changed()
            byte_count = before[0]
            payloads.setdefault(digest, path)
        else:
            hasher = hashlib.sha256()
            byte_count = 0
            with export.open_stream(item) as handle:
                while chunk := handle.read(1024 * 1024):
                    hasher.update(chunk)
                    byte_count += len(chunk)
            if byte_count != item.size:
                raise CorruptArchiveError("the Export ZIP file is damaged or incomplete")
            # Every file of an Export ZIP file counts against the totals for
            # one reading of it; a folder has no totals.
            export.count_read(byte_count)
            digest = hasher.hexdigest()
            payloads.setdefault(
                digest,
                _StreamedFile(lambda item=item: export.open_stream(item), item.size),
            )
        row = {
            "object_kind": "file",
            "relative_path": relative,
            "container_relative_path": None,
            "sha256": digest,
            "bytes": byte_count,
            "source_family": _source_family(relative),
            "extension": item.suffix,
            "blob_relative_path": _blob_relative_path(digest),
            "parser_state": "parser_unsupported",
        }
        inventory.append(row)
        if item.suffix != ".zip":
            continue
        reason = _scan_members(relative, item, export, inventory, payloads)
        if reason is not None:
            # The ZIP file is stored whole, without its members, and the
            # build leaves it out for this reason (stage A3c-2).
            row["parser_state"] = reason
    if report is not None:
        report(len(files), len(files))
    if archive_before is not None and archive_before != _archive_state(source):
        raise _input_changed()
    if not inventory:
        raise SnapshotStoreError("snapshot input contains no accepted files")
    return inventory, payloads, accounts


def content_multiset(objects: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """The content of a Snapshot, whatever the paths: its files and members as
    (SHA-256, bytes), with repeats."""
    return sorted((str(row["sha256"]), int(row["bytes"])) for row in objects)


def _snapshot_accounts(root: Path, manifest: dict[str, Any]) -> set[str]:
    """Read again, from the store, the accounts that a Snapshot's records name."""
    files: list[tuple[str, bytes]] = []
    for row in manifest.get("objects", []):
        relative = str(row.get("relative_path", ""))
        if (
            str(row.get("extension", "")).lower() != ".json"
            or not names_account(relative)
            or int(row["bytes"]) > ArchiveLimits().max_member_bytes
        ):
            continue
        blob = root / str(row["blob_relative_path"])
        try:
            data = blob.read_bytes()
        except PermissionError as exc:
            raise not_readable_error(root, blob) from exc
        except OSError as exc:
            raise invalid_store_error("immutable snapshot blob failed verification") from exc
        if len(data) != row["bytes"] or _sha256_bytes(data) != row["sha256"]:
            raise invalid_store_error("immutable snapshot blob failed verification")
        files.append((relative, data))
    return account_values(files)


def _inventory_content_id(inventory: list[dict[str, Any]]) -> str:
    identity_rows = [
        {
            "object_kind": row["object_kind"],
            "relative_path": row["relative_path"],
            "sha256": row["sha256"],
            "bytes": row["bytes"],
        }
        for row in sorted(
            inventory,
            key=lambda item: (item["object_kind"], item["relative_path"]),
        )
    ]
    return f"content:{_sha256_bytes(_stable_json_bytes(identity_rows))}"


# A temporary file of a write to the store: ".<name>.<process ID>.tmp", next
# to the file that it replaces (``_temporary_name``).
_TEMPORARY_NAME = re.compile(r"^\.(?P<name>.+)\.[0-9]+\.tmp$")
_BLOB_FOLDER_NAME = re.compile(r"^[0-9a-f]{2}$")


def _remove_temporary_files(root: Path) -> int:
    """Remove the temporary files that writes to the store left when they
    stopped, and return how many (stage A3d-3b).

    Called with the lock held, so that no write of this app is under way.
    Only the names that this app gives them are removed, in the folders where
    it writes them: the files at the top of the store, the journal, the
    manifest and inventory of a Snapshot, and a blob in the folder of the
    first two characters of its SHA-256. A link is never followed or
    removed, and the lock and the journal are kept.
    """
    removed = 0

    def remove(folder: Path, accepts: Callable[[str], bool]) -> None:
        nonlocal removed
        for entry in _open_folder(root, folder):
            match = _TEMPORARY_NAME.fullmatch(entry.name)
            if match is None or not accepts(match["name"]):
                continue
            if not entry.is_file(follow_symlinks=False):
                continue
            with _writing():
                os.unlink(folder / entry.name)
            removed += 1

    def folders(parent: Path) -> list[Path]:
        return [
            parent / entry.name
            for entry in _open_folder(root, parent)
            if entry.is_dir(follow_symlinks=False)
        ]

    remove(root, lambda name: name in _STORE_FILE_NAMES)
    remove(root / "journal", lambda name: name == "registration.json")
    for folder in folders(root / "snapshots"):
        remove(
            folder,
            lambda name, snapshot_id=folder.name: name
            in {"manifest.json", f"{snapshot_id}.inventory.json"},
        )
    for folder in folders(root / "blobs" / "sha256"):
        if _BLOB_FOLDER_NAME.fullmatch(folder.name) is None:
            continue
        remove(
            folder,
            lambda name, prefix=folder.name: SHA256_RE.fullmatch(name) is not None
            and name[:2] == prefix,
        )
    return removed


def _check_space(root: Path, payloads: dict[str, Path | _StreamedFile], sizes: dict[str, int]) -> None:
    """Stop before anything is written when the drive of the store cannot hold
    the files that the store does not hold yet (stage A3d-3b). Only these are
    counted, so that a registration is never stopped for nothing: a later
    Export shares most of its files with the earlier ones. The small files
    that list the Snapshot are not counted; a write that finds no space stops
    with the same code."""
    needed = sum(
        sizes[digest]
        for digest in payloads
        if not _exists(root, root / _blob_relative_path(digest))
    )
    try:
        free = shutil.disk_usage(root).free
    except OSError:
        return
    if needed > free:
        raise SnapshotStoreError(STORE_SPACE_MESSAGE, "SNAPSHOT_STORE_SPACE_INSUFFICIENT")


def register_snapshot(
    store_root: str | Path,
    input_root: str | Path,
    *,
    snapshot_label: str,
    export_requested_at: str,
    export_downloaded_at: str,
    export_observed_at: str,
    confirm_complete: bool,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Register a complete Export as a Snapshot. ``progress``, when given,
    receives the files done and all (``done`` and ``total``) of two stages
    (stage B4b-1): ``reading_export``, while the Export is read, and
    ``importing``, while its files that the store does not hold yet are
    copied, which an Export that the store holds already never reaches. The
    events never carry a place, a name, or a value, and the store is the same
    with or without them. The CLI passes none."""
    if confirm_complete is not True:
        raise SnapshotStoreError("snapshot registration requires --confirm-complete")

    def report(stage: str) -> Callable[[int, int], None] | None:
        if progress is None:
            return None
        return lambda done, total: progress({"stage": stage, "done": done, "total": total})

    root, store_metadata = load_store(store_root)
    # A store whose files would be too long stops before the Export is read
    # (stage B6c).
    check_store_paths(root)
    # The input stops with the codes of a run (stage A5b-2).
    requested_source = Path(input_root)
    try:
        if requested_source.is_symlink():
            raise SnapshotStoreError("input must not be a symbolic link", "INPUT_SYMLINK")
        source = requested_source.resolve()
        is_input = source.is_dir() or is_zip_input(source)
    except OSError as exc:
        if isinstance(exc, PermissionError):
            raise InputNotReadableError([""]) from exc
        raise SnapshotStoreError(
            "input must be an existing folder or ZIP file", "INPUT_NOT_DIRECTORY"
        ) from exc
    if not is_input:
        raise SnapshotStoreError("input must be an existing folder or ZIP file", "INPUT_NOT_DIRECTORY")
    check_input_apart(source, root)
    label = new_snapshot_label(snapshot_label)
    requested_at, downloaded_at, observed_at = registration_times(
        export_requested_at, export_downloaded_at, export_observed_at
    )

    # The input stays open until its files are copied to the store.
    with _store_lock(root), ExitStack() as stack:
        store_notes: dict[str, int] = {}
        removed = _remove_temporary_files(root)
        if removed:
            store_notes["temporary_files_removed"] = removed
        recovery_status = _recover_journal(root)
        opened = stack.enter_context(_open_snapshot_input(source))
        inventory, payloads, accounts = _scan_source(source, opened.source, report("reading_export"))
        if len(accounts) > 1:
            raise MixedExportsError()
        input_notes: dict[str, int] = {}
        if opened.same_export_count:
            input_notes["same_export_count"] = opened.same_export_count
        if opened.outside_files:
            input_notes["files_not_registered_count"] = len(opened.outside_files)
        manifests = _manifests_to_write(root)
        # The same Export registered again, under any path, label, or time, is
        # not a new Snapshot (stage A3a).
        target = content_multiset(inventory)
        for index, existing in enumerate(manifests, start=1):
            if content_multiset(list(existing.get("objects", []))) == target:
                with _writing():
                    _write_registry(root, manifests)
                return {
                    "status": "PASS",
                    "snapshot_id": existing["snapshot_id"],
                    "registration_was_idempotent": True,
                    "same_content_as": {
                        "snapshot_label": existing["snapshot_label"],
                        "logical_order": index,
                    },
                    "snapshot_count": len(manifests),
                    "logical_order": index,
                    "recovery_status": recovery_status,
                    **input_notes,
                    **store_notes,
                }
        if accounts and manifests:
            latest_accounts = _snapshot_accounts(root, manifests[-1])
            if latest_accounts and latest_accounts != accounts:
                raise MixedExportsError(OTHER_ACCOUNT_MESSAGE, kind="other_account")
        content_id = _inventory_content_id(inventory)
        snapshot_digest = _sha256_bytes(
            _stable_json_bytes(
                {
                    "account_store_id": store_metadata["account_store_id"],
                    "export_observed_at": observed_at,
                    "snapshot_content_id": content_id,
                }
            )
        )
        snapshot_id = f"snapshot-{snapshot_digest}"
        manifest_path = root / "snapshots" / snapshot_id / "manifest.json"
        check_label_free(manifests, label, snapshot_id)
        existing = next(
            (item for item in manifests if item["snapshot_id"] == snapshot_id),
            None,
        )
        if existing is not None:
            if existing["snapshot_content_id"] != content_id:
                # The identity of a Snapshot is made from its content, so a
                # registered one whose content differs is damaged (stage A5b-2).
                raise invalid_store_error(
                    "the identity of a registered Snapshot does not match its content"
                )
            expected_metadata = {
                "snapshot_label": label,
                "export_requested_at": requested_at,
                "export_downloaded_at": downloaded_at,
                "export_observed_at": observed_at,
            }
            if any(existing.get(field) != value for field, value in expected_metadata.items()):
                raise SnapshotStoreError(
                    "idempotent registration metadata must match the original"
                )
            with _writing():
                _write_registry(root, manifests)
            return {
                "status": "PASS",
                "snapshot_id": snapshot_id,
                "registration_was_idempotent": True,
                "snapshot_count": len(manifests),
                "logical_order": manifests.index(existing) + 1,
                "recovery_status": recovery_status,
                **store_notes,
            }

        sizes = {str(row["sha256"]): int(row["bytes"]) for row in inventory}
        _check_space(root, payloads, sizes)
        with _writing():
            _atomic_json(
                root / "journal" / "registration.json",
                {
                    "format": "snapshot-registration-journal-v1",
                    "snapshot_id": snapshot_id,
                    "phase": "preserving_blobs",
                },
            )
        added = 0
        reused = 0
        copying = report("importing")
        for done, digest in enumerate(sorted(payloads)):
            if copying is not None:
                copying(done, len(payloads))
            if _preserve_blob(root, digest, payloads[digest], sizes[digest]):
                added += 1
            else:
                reused += 1
        if copying is not None:
            copying(len(payloads), len(payloads))
        family_counts = Counter(row["source_family"] for row in inventory)
        manifest = {
            "format": "garmin-running-data-normalizer-snapshot-manifest-v1",
            "contract_version": CONTRACT_VERSION,
            "policy_registry_version": REGISTRY_VERSION,
            "snapshot_id": snapshot_id,
            "snapshot_content_id": content_id,
            "snapshot_label": label,
            "account_store_id": store_metadata["account_store_id"],
            "export_requested_at": requested_at,
            "export_downloaded_at": downloaded_at,
            "export_observed_at": observed_at,
            "registered_at": _now_utc(),
            "export_completion_confirmed": True,
            "file_count": sum(row["object_kind"] == "file" for row in inventory),
            "archive_member_count": sum(
                row["object_kind"] == "archive_member" for row in inventory
            ),
            "total_bytes": sum(int(row["bytes"]) for row in inventory),
            "family_counts": dict(sorted(family_counts.items())),
            "objects": inventory,
            "immutable": True,
            "automatic_deletion": False,
        }
        inventory_path = manifest_path.parent / f"{snapshot_id}.inventory.json"
        with _writing():
            _atomic_json(inventory_path, _inventory_document(manifest))
            _atomic_json(manifest_path, manifest)
            inventory_path.chmod(IMMUTABLE_FILE_MODE)
            manifest_path.chmod(IMMUTABLE_FILE_MODE)
        manifests.append(manifest)
        manifests = sorted(
            manifests,
            key=lambda item: (
                _logical_time(str(item["export_observed_at"])),
                str(item["snapshot_id"]),
            ),
        )
        with _writing():
            _write_registry(root, manifests)
            (root / "journal" / "registration.json").unlink()
        return {
            "status": "PASS",
            "snapshot_id": snapshot_id,
            "registration_was_idempotent": False,
            "snapshot_count": len(manifests),
            "logical_order": manifests.index(manifest) + 1,
            "blob_added_count": added,
            "blob_reused_count": reused,
            "recovery_status": recovery_status,
            **input_notes,
            **store_notes,
        }


def _notices(root: Path, *, journal: bool) -> list[str]:
    """What a store holds that does not stop a command but should be known
    (stage A3d-3b): the lock of a registration that runs or stopped, and,
    with ``journal``, the journal of one that was interrupted."""
    notices = []
    if _exists(root, root / LOCK_NAME, follow=False):
        notices.append("SNAPSHOT_STORE_LOCKED")
    if journal and _exists(root, root / "journal" / "registration.json"):
        notices.append("SNAPSHOT_REGISTRATION_INCOMPLETE")
    return notices


def snapshot_status(store_root: str | Path) -> dict[str, Any]:
    root, metadata = load_store(store_root)
    manifests = load_manifests(root)
    result: dict[str, Any] = {
        "status": "PASS",
        "account_store_id": metadata["account_store_id"],
        "snapshot_count": len(manifests),
        "automatic_deletion": False,
        "snapshots": [
            {
                "logical_order": index,
                "snapshot_label": manifest["snapshot_label"],
                "export_observed_at": manifest["export_observed_at"],
                "file_count": manifest["file_count"],
                "archive_member_count": manifest["archive_member_count"],
            }
            for index, manifest in enumerate(manifests, start=1)
        ],
    }
    notices = _notices(root, journal=True)
    # A store whose files a registration could not write here (stage B6c):
    # a NOTE, which an import makes a stop.
    if store_paths_too_long(root):
        notices.append("SNAPSHOT_STORE_PATH_TOO_LONG")
    if notices:
        result["notices"] = notices
    return result


def _blob_whole(blob: Path, byte_count: int, digest: str) -> bool:
    """Whether a blob is a regular file of its size and SHA-256. Raises
    ``PermissionError`` when it cannot be opened."""
    try:
        status = os.stat(blob)
    except (FileNotFoundError, NotADirectoryError):
        return False
    return (
        stat.S_ISREG(status.st_mode)
        and status.st_size == byte_count
        and sha256_file(blob) == digest
    )


def verify_store(store_root: str | Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        root, metadata = load_store(store_root)
        manifests = load_manifests(root)
    except SnapshotStoreError as exc:
        # A store that cannot be opened, that a newer version made, or that is
        # not a store stops verification; a damaged store fails it
        # (stage A3d-3b).
        if exc.code != "SNAPSHOT_STORE_INVALID":
            raise
        return {
            "status": "FAIL",
            "snapshot_count": 0,
            "referenced_blob_count": 0,
            "unreferenced_blob_count": 0,
            "failure_count": 1,
            "failures": ["snapshot_store_metadata_failure"],
            "automatic_deletion": False,
            "garbage_collection_performed": False,
        }
    # The places that cannot be opened stop verification at its end, all named.
    not_opened: list[str] = []

    def load(path: Path) -> dict[str, Any] | None:
        try:
            return _load_json(path, root)
        except SnapshotStoreError as exc:
            if exc.code != "SNAPSHOT_STORE_NOT_READABLE":
                raise
            not_opened.extend(exc.places or [])
            return None

    referenced: set[str] = set()
    if _exists(root, root / "journal" / "registration.json"):
        failures.append("incomplete_registration_journal_present")
    for manifest in manifests:
        if manifest.get("account_store_id") != metadata["account_store_id"]:
            failures.append("account_boundary_mismatch")
        try:
            objects = list(manifest.get("objects", []))
            for row in objects:
                _validate_inventory_object(row)
            expected_content = _inventory_content_id(objects)
            if expected_content != manifest.get("snapshot_content_id"):
                failures.append("snapshot_content_id_mismatch")
            expected_snapshot_digest = _sha256_bytes(
                _stable_json_bytes(
                    {
                        "account_store_id": metadata["account_store_id"],
                        "export_observed_at": manifest["export_observed_at"],
                        "snapshot_content_id": expected_content,
                    }
                )
            )
            if manifest["snapshot_id"] != f"snapshot-{expected_snapshot_digest}":
                failures.append("snapshot_identity_mismatch")
        except SnapshotStoreError:
            failures.append("snapshot_inventory_contract_failure")
        for row in manifest.get("objects", []):
            try:
                digest, byte_count, blob_relative_path = _validate_inventory_object(
                    row
                )
            except SnapshotStoreError:
                failures.append("snapshot_inventory_contract_failure")
                continue
            referenced.add(digest)
            blob = root / blob_relative_path
            try:
                _reject_store_symlink_components(root, blob)
                blob_valid = _blob_whole(blob, byte_count, digest)
            except PermissionError:
                not_opened.append(_place(root, blob))
                continue
            except SnapshotStoreError as exc:
                if exc.code == "SNAPSHOT_STORE_NOT_READABLE":
                    not_opened.extend(exc.places or [])
                    continue
                failures.append("immutable_blob_symlink_failure")
                blob_valid = False
            if not blob_valid:
                failures.append("immutable_blob_integrity_failure")
    try:
        registry = load(root / "registry.json")
        expected_registry, expected_family_coverage = _registry_documents(manifests)
        if registry is not None and registry != expected_registry:
            failures.append("registry_manifest_binding_mismatch")
        public_registry = load(root / "snapshot_registry.json")
        if registry is not None and public_registry is not None and public_registry != registry:
            failures.append("snapshot_registry_alias_mismatch")
        family_coverage = load(root / "snapshot_family_coverage.json")
        if family_coverage is not None and family_coverage != expected_family_coverage:
            failures.append("snapshot_family_coverage_binding_mismatch")
    except SnapshotStoreError:
        failures.append("snapshot_registry_metadata_failure")
    for manifest in manifests:
        inventory_path = (
            root
            / "snapshots"
            / str(manifest["snapshot_id"])
            / f"{manifest['snapshot_id']}.inventory.json"
        )
        try:
            inventory = load(inventory_path)
            if inventory is not None and inventory != _inventory_document(manifest):
                failures.append("snapshot_inventory_mismatch")
        except SnapshotStoreError:
            failures.append("snapshot_inventory_metadata_failure")
    # The blobs are walked as ``rglob`` lists them, with the folders that
    # cannot be opened, which ``rglob`` passes over (stage A3d-3b).
    blob_root = root / "blobs" / "sha256"
    blob_tree: list[Path] = []
    try:
        _reject_store_symlink_components(root, blob_root)
        if _exists(root, blob_root):
            blob_tree, closed = walk_paths(blob_root)
            not_opened.extend(_place(root, folder) for folder in closed)
    except SnapshotStoreError as exc:
        if exc.code != "SNAPSHOT_STORE_NOT_READABLE":
            failures.append("immutable_blob_symlink_failure")
        else:
            not_opened.extend(exc.places or [])
    all_blobs: set[str] = set()
    symlink_found = False
    for path in blob_tree:
        try:
            mode = os.lstat(path).st_mode
        except FileNotFoundError:
            continue
        except PermissionError:
            not_opened.append(_place(root, path.parent))
            continue
        if stat.S_ISLNK(mode):
            symlink_found = True
        elif stat.S_ISREG(mode):
            all_blobs.add(path.name)
    if symlink_found:
        failures.append("immutable_blob_symlink_failure")
    if not_opened:
        raise SnapshotStoreError(
            store_not_readable_message(),
            "SNAPSHOT_STORE_NOT_READABLE",
            places=list(dict.fromkeys(not_opened)),
        )
    result: dict[str, Any] = {
        "status": "PASS" if not failures else "FAIL",
        "snapshot_count": len(manifests),
        "referenced_blob_count": len(referenced),
        "unreferenced_blob_count": len(all_blobs - referenced),
        "failure_count": len(failures),
        "failures": sorted(Counter(failures)),
        "automatic_deletion": False,
        "garbage_collection_performed": False,
    }
    notices = _notices(root, journal=False)
    if notices:
        result["notices"] = notices
    return result


# The failures that the next registration completes after one was
# interrupted: its journal, and the registry that it did not write again.
_COMPLETED_BY_REGISTRATION = frozenset(
    {
        "incomplete_registration_journal_present",
        "registry_manifest_binding_mismatch",
        "snapshot_registry_alias_mismatch",
        "snapshot_family_coverage_binding_mismatch",
    }
)


def verification_error(
    verification: dict[str, Any],
    error_class: type[SnapshotStoreError] = SnapshotStoreError,
) -> SnapshotStoreError:
    """The error of a store that failed verification (stage A3d-3b): an
    interrupted registration, which the next one completes, or a damaged
    store, with the names of its failures."""
    failures = [str(item) for item in verification.get("failures", [])]
    if (
        "incomplete_registration_journal_present" in failures
        and set(failures) <= _COMPLETED_BY_REGISTRATION
    ):
        return error_class(REGISTRATION_INCOMPLETE_MESSAGE, "SNAPSHOT_REGISTRATION_INCOMPLETE")
    return error_class(
        f"the Snapshot Store failed verification ({', '.join(failures)})",
        "SNAPSHOT_STORE_INVALID",
    )


__all__ = [
    "NOTICE_MESSAGES",
    "SnapshotStoreError",
    "cancel_notices",
    "check_input_apart",
    "check_label_free",
    "check_new_store_place",
    "check_store_paths",
    "content_multiset",
    "initialize_store",
    "invalid_store_error",
    "load_manifests",
    "load_store",
    "lock_created_at",
    "lock_exists",
    "new_snapshot_label",
    "not_readable_error",
    "register_snapshot",
    "registration_times",
    "remove_lock",
    "sha256_file",
    "shown_store_message",
    "snapshot_status",
    "store_not_readable_message",
    "store_paths_too_long",
    "verification_error",
    "verify_store",
    "windows_store_paths_too_long",
]
