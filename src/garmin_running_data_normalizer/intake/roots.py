"""Find the Exports in an input and choose the one to read.

A root is a folder that holds the Export's own layout folders (DI_CONNECT,
DI-GOLF, DI-Connect-...), or a ZIP file in the input that holds them. An input
with no root or with one root holds one Export. An input with several roots
holds one Export only when every root holds the same files with the same
content, as when an Export ZIP file sits next to the folder extracted from it;
the first root in path order is then read. Otherwise the input holds different
Exports, and reading it stops (MixedExportsError).

A root is read as if it were given alone: the paths of its files are counted
from the root, and an Export ZIP file is read as when it is selected directly,
with the ZIP files inside it read one level deep. When the input has a root,
the files of the kinds that the product reads that lie outside every root are
not read; they are returned so that a run can list them.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO, ContextManager, Iterator, Union
from zipfile import ZipFile

from .archive import ArchiveLimits, MemberTooLargeError
from .source import (
    DAMAGED_ZIP_ERRORS,
    ExportFile,
    ExportSource,
    InputNotReadableError,
    is_layout_folder,
)


# Files of these kinds outside every root are listed as not read.
READ_SUFFIXES = frozenset({".json", ".fit", ".zip"})
OUTSIDE_EXPORT_ROOT = "outside_export_root"


# Fixed messages, which never name a folder, a file, or an account.
# The CLI adds the next step of INPUT_MULTIPLE_EXPORTS from the table of
# stops (stage A5b).
MIXED_INPUT_MESSAGE = (
    "the input holds more than one Export, or Exports of more than one account"
)
OTHER_ACCOUNT_MESSAGE = (
    "the Export belongs to another account than the Snapshots in this Snapshot Store"
)
MIXED_STORE_MESSAGE = "the Snapshot Store holds the Exports of more than one account"


@dataclass(frozen=True)
class FoundExport:
    """One Export that a mixed input holds (stage B3c).

    ``place`` is where it sits in the input, as ``ExportRoot.location``
    names it ("" is the input itself), and ``same_as`` the place of the first
    Export found with the same files, or None.
    """

    place: str
    is_zip: bool
    same_as: str | None = None


class MixedExportsError(ValueError):
    """Raised when an input holds different Exports, or Exports of different accounts.

    ``safe_message`` says where the mix was found; the CLI adds the next
    step of its code (stage A5b). ``found`` lists the Exports of an input
    that holds different ones, for where the check is started only, never
    written to an output; a mix of accounts names none (stage B3c).
    """

    code = "INPUT_MULTIPLE_EXPORTS"

    def __init__(
        self, safe_message: str = MIXED_INPUT_MESSAGE, found: list[FoundExport] | None = None
    ) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message
        self.found = list(found or [])


@dataclass(frozen=True, order=True)
class ExportRoot:
    """Where one Export sits in the input: a folder, or an Export ZIP file.

    ``location`` is the path in the input, counted from the input's own root;
    "" is the input itself.
    """

    location: str
    is_zip: bool


class RootView:
    """The files of one folder root, with their paths counted from the root.

    Every other use goes to the input's source with the file as the input
    lists it, so that two roots never share a ZIP file that the source opened.
    """

    def __init__(self, source: ExportSource, files: list[tuple[ExportFile, ExportFile]]) -> None:
        self._source = source
        self._files = [view for view, _ in files]
        self._original = dict(files)
        self.limits = source.limits
        self.is_zip = source.is_zip

    def files(self) -> list[ExportFile]:
        return list(self._files)

    def read(self, item: ExportFile) -> bytes:
        return self._source.read(self._original[item])

    def digest(self, item: ExportFile) -> tuple[str, int]:
        return self._source.digest(self._original[item])

    def open_stream(self, item: ExportFile) -> ContextManager[BinaryIO]:
        return self._source.open_stream(self._original[item])

    def archive(self, item: ExportFile) -> ZipFile:
        return self._source.archive(self._original[item])

    def local_path(self, item: ExportFile) -> Path:
        return self._source.local_path(self._original[item])

    def count_read(self, size: int) -> None:
        self._source.count_read(size)

    def place_of(self, item: ExportFile) -> str:
        return self._source.place_of(self._original[item])


ExportView = Union[ExportSource, RootView]


@dataclass
class OpenedExport:
    """The Export chosen in an input.

    ``source`` lists and reads its files. ``same_export_count`` is the number
    of other roots that hold the same Export and are not read, and
    ``outside_files`` are the files outside every root, as (path, bytes).
    """

    source: ExportView
    same_export_count: int = 0
    outside_files: list[tuple[str, int]] = field(default_factory=list)


def _holds_export(source: ExportSource, item: ExportFile) -> bool:
    """Whether a ZIP file in the input holds the layout folders of an Export.

    A ZIP file that cannot be opened holds no Export; reading leaves it out
    (stage A3c), as it does one too large to copy out of an Export ZIP file.
    Copying it out still stops the run when the Export ZIP file itself is
    damaged or unsafe.
    """
    try:
        source.local_path(item)
        names = [info.filename for info in source.archive(item).infolist()]
    except (MemberTooLargeError, *DAMAGED_ZIP_ERRORS):
        return False
    except PermissionError as exc:
        # A ZIP file that this app may not open stops the reading (stage A3d-3a).
        raise InputNotReadableError([source.place_of(item)]) from exc
    return any(
        any(is_layout_folder(part) for part in PurePosixPath(name).parts[:-1])
        for name in names
    )


def _find_roots(
    source: ExportSource,
) -> tuple[list[ExportRoot], dict[ExportRoot, list[ExportFile]], list[ExportFile]]:
    """Return the roots, the files of each folder root, and the files outside every root."""
    files = source.files()
    folder_roots: set[str] = set()
    zip_roots: set[str] = set()
    for item in files:
        parts = PurePosixPath(item.relative_path).parts
        index = next(
            (position for position, part in enumerate(parts[:-1]) if is_layout_folder(part)),
            None,
        )
        if index is not None:
            folder_roots.add(PurePosixPath(*parts[:index]).as_posix() if index else "")
        elif item.suffix == ".zip" and _holds_export(source, item):
            zip_roots.add(item.relative_path)
    roots = sorted(
        [ExportRoot(location, False) for location in folder_roots]
        + [ExportRoot(location, True) for location in zip_roots]
    )
    members: dict[ExportRoot, list[ExportFile]] = {root: [] for root in roots if not root.is_zip}
    outside: list[ExportFile] = []
    for item in files:
        if item.relative_path in zip_roots:
            continue
        holders = [
            location
            for location in folder_roots
            if location == "" or item.relative_path.startswith(location + "/")
        ]
        if holders:
            members[ExportRoot(max(holders, key=len), False)].append(item)
        elif roots and item.suffix in READ_SUFFIXES:
            outside.append(item)
    return roots, members, outside


@contextmanager
def _open_root(
    source: ExportSource,
    root: ExportRoot,
    members: list[ExportFile],
) -> Iterator[ExportView]:
    if root.is_zip:
        item = next(entry for entry in source.files() if entry.relative_path == root.location)
        with ExportSource(source.local_path(item), source.limits) as nested:
            yield nested
        return
    prefix = len(root.location) + 1 if root.location else 0
    yield RootView(
        source,
        [
            (
                ExportFile(item.relative_path[prefix:], item.size, path=item.path, member=item.member),
                item,
            )
            for item in members
        ],
    )


def _fingerprint(view: ExportView) -> tuple[tuple[str, tuple[int, str | None]], ...]:
    """The files of one root: their paths, sizes, and, for those read, digests."""
    from .discovery import SUPPORTED_SUFFIXES, ExportReading

    reading = ExportReading(view, keep_data=False)
    entries: dict[str, tuple[int, str | None]] = {
        asset.provenance_path: (asset.size_bytes, asset.sha256) for asset in reading.assets
    }
    # A file that is not read because of its size is compared by its path
    # and size, as the files of the kinds that are not read (stage A3c).
    for path, size, _reason in (*reading.left_out, *reading.not_read):
        entries.setdefault(path, (size, None))
    for item in view.files():
        if item.suffix not in SUPPORTED_SUFFIXES:
            entries.setdefault(item.relative_path, (item.size, None))
    return tuple(sorted(entries.items()))


@contextmanager
def open_export(root: str | Path, limits: ArchiveLimits = ArchiveLimits()) -> Iterator[OpenedExport]:
    """Open an Export folder or Export ZIP file and choose the Export to read."""
    with ExitStack() as stack:
        source = stack.enter_context(ExportSource(root, limits))
        roots, members, outside = _find_roots(source)
        if not roots or (roots == [ExportRoot("", False)] and not outside):
            yield OpenedExport(source)
            return
        views = [
            stack.enter_context(_open_root(source, item, members.get(item, [])))
            for item in roots
        ]
        if len(views) > 1:
            fingerprints = [_fingerprint(view) for view in views]
            if any(value != fingerprints[0] for value in fingerprints[1:]):
                # Every root, with the first one that holds the same files.
                first: dict[tuple[tuple[str, tuple[int, str | None]], ...], str] = {}
                found = []
                for item, fingerprint in zip(roots, fingerprints):
                    same = first.setdefault(fingerprint, item.location)
                    found.append(
                        FoundExport(item.location, item.is_zip, None if same == item.location else same)
                    )
                raise MixedExportsError(found=found)
        yield OpenedExport(
            views[0],
            same_export_count=len(views) - 1,
            outside_files=[(item.relative_path, item.size) for item in outside],
        )


__all__ = [
    "ExportRoot",
    "ExportView",
    "FoundExport",
    "MIXED_INPUT_MESSAGE",
    "MIXED_STORE_MESSAGE",
    "MixedExportsError",
    "OTHER_ACCOUNT_MESSAGE",
    "OUTSIDE_EXPORT_ROOT",
    "OpenedExport",
    "RootView",
    "open_export",
]
