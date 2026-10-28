"""The settings of an earlier launch of the GUI (internal; stage B4c).

The GUI remembers, in one file on this computer (decision 20261017-15): the
Snapshot Store and the folder for the output of the last run that made its
output, the outputs that runs made (the latest ten), whether the tips show,
the colors of the page when the person chose Light or Dark (stage G3a), and
the items that the view page showed and whether its item shelf was open
(stage G3b), by the names of the items only. Only the names of places are
kept, never what is in them, and never the place of an Export. The CLI
remembers nothing.

The file is the person's own: an owner-only folder and file, written whole
through a temporary file in the same folder, so that no half-written file is
left. It is read with care: a link, a folder, a file over 64 KiB, or a file
of another form is not used, and the next settings replace it; a file of a
newer version is not used and never written over, so that going back to an
older version leaves the newer settings as they are. Keys that this version
does not know are left out, and so is a value of another form of a key that
2.1.0 added (the colors, the items, the shelf), so that the other settings are
still used; of the items, the names that this version does not know, the
names given twice, and those after the sixth are left out. Places
read from it are absolute places of this system without control characters,
and the server checks them again as it checks places that the page sends.

The settings change one at a time: a change reads the file, adds its
value, and writes it whole under one lock, so that a run that ends while the
person switches the tips or the colors keeps both. The lock holds for the
threads of one server only; two GUIs that write at the same moment can still
keep only one of the two values.

From v2.2.0 (stage K1) the file is of format 2, which an earlier version does
not use and never writes over, so that going back to 2.1.0 keeps what 2.2.0
remembers; format 1 is still read, and written as format 2. The settings also
remember the layouts of the view page (the person's layouts, the built-in
layouts hidden, and the one used last; gui/layouts.py), its period, grouping,
and activity types, and the timezone of the last run that made its output. A
value of another form of these keys is left out alone, and of the layouts,
the one layout. Settings whose file would be over 64 KiB are not written: the
file before stays, and the page is told that they were not remembered.
"""
from __future__ import annotations

import json
import os
import secrets
import stat
import threading
from pathlib import Path
from typing import Any

from ..common.json_depth import check_json_depth
from ..common.private_files import PRIVATE_DIRECTORY_MODE, PRIVATE_FILE_MODE
from ..common.time import MAX_TIMEZONE_LENGTH, TimezoneDataUnavailableError, TimezoneNameInvalidError, resolve_timezone_name
from ..view.items import ITEMS_BY_KEY
from ..view.series import MAX_PANELS, MAX_TYPES, type_name_ok
from . import places
from .layouts import BUILT_IN_IDS, kept_hidden, kept_layouts
from .layouts import change_layouts as _changed_layouts
from .views import grain_ok, period_choice

SETTINGS_FORMAT = "garmin-running-data-normalizer-gui-settings-v2"
_FORMAT_PREFIX = "garmin-running-data-normalizer-gui-settings-v"
_FORMAT_VERSION = 2
# The formats that this version reads: format 1 of 2.0.x and 2.1.0 too.
_READ_VERSIONS = (1, 2)
MAX_SETTINGS_BYTES = 64 * 1024
MAX_RECENT_OUTPUTS = 10
MAX_PLACE_LENGTH = 4096
PLACE_KEYS = ("store", "output_parent")
# The colors that the person can choose; without one, the page follows the
# colors that the browser reports (stage G3a).
THEMES = ("light", "dark")
# Whether the item shelf of the view page is open (stage G3b).
SHELF_STATES = ("open", "closed")
# One change of the settings at a time: each reads the file and writes it
# whole, so that two at once would keep only one of them.
_CHANGE_LOCK = threading.Lock()

# What the settings tell the page, codes only.
SETTINGS_INVALID = "SETTINGS_INVALID"
SETTINGS_NEWER = "SETTINGS_NEWER"
SETTINGS_NOT_WRITTEN = "SETTINGS_NOT_WRITTEN"
SETTINGS_NOT_REMOVED = "SETTINGS_NOT_REMOVED"


def _place(value: Any) -> str | None:
    """A place as the file may hold it: an absolute place of this system, of
    a sensible length, without control characters; None otherwise."""
    if not isinstance(value, str) or not 0 < len(value) <= MAX_PLACE_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return None
    try:
        # A name that the system gave in bytes that are not UTF-8 cannot be
        # kept in the file.
        value.encode("utf-8")
    except UnicodeEncodeError:
        return None
    return value if Path(value).is_absolute() else None


def _version(value: Any) -> int | None:
    if isinstance(value, str) and value.startswith(_FORMAT_PREFIX):
        number = value[len(_FORMAT_PREFIX):]
        if number.isascii() and number.isdigit():
            return int(number)
    return None


def _known(data: Any) -> dict[str, Any] | None:
    """The values that this version knows, or None when one of them is not
    of its form; other keys are left out."""
    if not isinstance(data, dict):
        return None
    values: dict[str, Any] = {}
    for key in PLACE_KEYS:
        if data.get(key) is not None:
            place = _place(data[key])
            if place is None:
                return None
            values[key] = place
    if data.get("recent_outputs") is not None:
        outputs = data["recent_outputs"]
        if not isinstance(outputs, list) or len(outputs) > MAX_RECENT_OUTPUTS:
            return None
        found = [_place(item) for item in outputs]
        if any(place is None for place in found) or len(set(found)) != len(found):
            return None
        values["recent_outputs"] = found
    if data.get("hints") is not None:
        if not isinstance(data["hints"], bool):
            return None
        values["hints"] = data["hints"]
    # A key that 2.1.0 added is left out alone when it is of another form,
    # such as a color of a later version (stage G3a).
    if data.get("theme") in THEMES:
        values["theme"] = data["theme"]
    # The items that the view page showed (stage G3b): the names of the items
    # that this version knows, each once, six at most.
    if isinstance(data.get("view_items"), list):
        names = [name for name in data["view_items"] if isinstance(name, str) and name in ITEMS_BY_KEY]
        values["view_items"] = list(dict.fromkeys(names))[:MAX_PANELS]
    if data.get("view_shelf") in SHELF_STATES:
        values["view_shelf"] = data["view_shelf"]
    values.update(_view_values(data))
    timezone = timezone_kept(data.get("timezone"))
    if timezone is not None:
        values["timezone"] = timezone
    return values


def _view_values(data: dict[str, Any]) -> dict[str, Any]:
    """The values of the view page that v2.2.0 added (stage K1), each left out
    alone when it is of another form: the layouts of the person (one at a
    time), the built-in layouts hidden, the layout used last (a built-in one or
    one of the person's), the period, the grouping, and the activity types
    (only a choice that is kept whole: types_kept)."""
    values: dict[str, Any] = {}
    layouts = kept_layouts(data.get("view_layouts"))
    if layouts is not None:
        values["view_layouts"] = layouts
    hidden = kept_hidden(data.get("view_layouts_hidden"))
    if hidden is not None:
        values["view_layouts_hidden"] = hidden
    current = data.get("view_layout")
    if isinstance(current, str) and (current in BUILT_IN_IDS or any(layout["id"] == current for layout in layouts or [])):
        values["view_layout"] = current
    period = data.get("view_period")
    if period_choice(period) is not None:
        values["view_period"] = period if isinstance(period, str) else {"from": period["from"], "to": period["to"]}
    if grain_ok(data.get("view_grain")):
        values["view_grain"] = data["view_grain"]
    types = types_kept(data.get("view_types"))
    if types is not None:
        values["view_types"] = types
    return values


def types_kept(value: Any) -> list[str] | None:
    """The activity types counted that the settings keep: the whole choice,
    or None when it cannot be kept whole (more than MAX_TYPES names, a name
    given twice, or a name that type_name_ok does not take). Such a choice is
    not remembered, so that the next opening counts the types counted at
    first, never other types than those chosen; no types counted ([]) is a
    choice of its own."""
    if (
        not isinstance(value, list)
        or len(value) > MAX_TYPES
        or any(not type_name_ok(name) for name in value)
        or len(set(value)) != len(value)
    ):
        return None
    return list(value)


def timezone_kept(value: Any) -> str | None:
    """A timezone that the settings keep: a name of up to MAX_TIMEZONE_LENGTH
    characters that the CLI takes for --timezone (resolve_timezone_name), so
    that the third box never takes a name that a run would refuse."""
    if not isinstance(value, str) or not 0 < len(value) <= MAX_TIMEZONE_LENGTH:
        return None
    try:
        return resolve_timezone_name(value)
    except (TimezoneNameInvalidError, TimezoneDataUnavailableError):
        return None


def _read_all(descriptor: int) -> bytes | None:
    """The bytes of an open file, or None when there are more than the limit."""
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = os.read(descriptor, MAX_SETTINGS_BYTES + 1 - size)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_SETTINGS_BYTES:
            return None


def read_settings(path: Path) -> tuple[dict[str, Any], str | None]:
    """The settings at ``path``, and what to tell of the file: nothing when
    there is none or it is used, SETTINGS_INVALID for a file that cannot be
    read or is not of this form, and SETTINGS_NEWER for a file of a newer
    version. A file that is not used gives no settings."""
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return {}, None
    except OSError:
        return {}, SETTINGS_INVALID
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SETTINGS_BYTES:
        return {}, SETTINGS_INVALID
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return {}, SETTINGS_INVALID
    try:
        content = _read_all(descriptor)
    except OSError:
        content = None
    finally:
        os.close(descriptor)
    if content is None:
        return {}, SETTINGS_INVALID
    try:
        data = json.loads(content.decode("utf-8"))
        check_json_depth(data)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return {}, SETTINGS_INVALID
    version = _version(data.get("format")) if isinstance(data, dict) else None
    if version is not None and version > _FORMAT_VERSION:
        return {}, SETTINGS_NEWER
    values = _known(data) if version in _READ_VERSIONS else None
    return ({}, SETTINGS_INVALID) if values is None else (values, None)


def _make_folder(folder: Path, own: bool) -> None:
    """Make a missing folder, owner-only. One that is there keeps its
    permissions; this app's own folder must be a folder itself, not a link."""
    try:
        os.mkdir(folder, PRIVATE_DIRECTORY_MODE)
    except FileExistsError:
        if own and not stat.S_ISDIR(os.lstat(folder).st_mode):
            raise NotADirectoryError(str(folder)) from None
        if not own and not folder.is_dir():
            raise NotADirectoryError(str(folder)) from None
        return
    # The umask cannot widen it.
    folder.chmod(PRIVATE_DIRECTORY_MODE)


def write_settings(path: Path, values: dict[str, Any], makeable: tuple[Path, ...] = ()) -> str | None:
    """Write ``values`` as the settings at ``path``, whole, through a
    temporary file in the same folder: None when they are written, or
    SETTINGS_NOT_WRITTEN. This app's folder is made when it is missing, and
    the folders of ``makeable`` above it; no other folder is made."""
    known = _known(values)
    if known is None:
        return SETTINGS_NOT_WRITTEN
    content = (
        json.dumps({"format": SETTINGS_FORMAT, **known}, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")
    # A file over the limit would not be read again, and every setting in it
    # would be lost (stage K1 of v2.2.0): it is not written, and the file
    # before stays.
    if len(content) > MAX_SETTINGS_BYTES:
        return SETTINGS_NOT_WRITTEN
    folder = path.parent
    temporary = folder / f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    written = False
    try:
        for parent in makeable:
            _make_folder(parent, own=False)
        _make_folder(folder, own=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(temporary, flags, PRIVATE_FILE_MODE)
        written = True
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, PRIVATE_FILE_MODE)
            view = memoryview(content)
            while view:
                view = view[os.write(descriptor, view):]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
    except OSError:
        if written:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        return SETTINGS_NOT_WRITTEN
    return None


def settings_present(path: Path) -> bool:
    """Whether anything is at the place of the settings (stage C1): a file,
    a link, or something that forgetting them would report. True when the
    place cannot be looked at, so that the page lets the person try."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def remove_settings(path: Path) -> str | None:
    """Forget the settings: remove the file at ``path`` (a link there is
    removed, not what it points to) and this app's folder when nothing else
    is in it. None when there is no file now, or SETTINGS_NOT_REMOVED."""
    with _CHANGE_LOCK:
        try:
            status = os.lstat(path)
        except FileNotFoundError:
            status = None
        except OSError:
            return SETTINGS_NOT_REMOVED
        if status is not None:
            if stat.S_ISDIR(status.st_mode):
                return SETTINGS_NOT_REMOVED
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
            except OSError:
                return SETTINGS_NOT_REMOVED
        try:
            os.rmdir(path.parent)
        except OSError:
            pass
        return None


def remember_run_at(
    path: Path,
    output: Path,
    store: Path | None,
    timezone: str | None = None,
    makeable: tuple[Path, ...] = (),
) -> str | None:
    """Remember the places of a run that made its output: the folder for the
    output, the output first in the latest ones, and the store of a Snapshot
    run (a run of this Export alone keeps the store that was remembered); and
    from v2.2.0 the timezone of the run (stage K1), which the third box takes
    at the next launch. None when they are written, or a code: SETTINGS_NEWER
    leaves the file of a newer version as it is."""
    with _CHANGE_LOCK:
        current, notice = read_settings(path)
        if notice == SETTINGS_NEWER:
            return SETTINGS_NEWER
        made = str(output)
        recent = [made, *(item for item in current.get("recent_outputs", []) if item != made)]
        values = {**current, "output_parent": str(output.parent), "recent_outputs": recent[:MAX_RECENT_OUTPUTS]}
        if store is not None:
            values["store"] = str(store)
        if timezone_kept(timezone) is not None:
            values["timezone"] = timezone
        return write_settings(path, values, makeable)


def remember_hints_at(path: Path, on: bool, makeable: tuple[Path, ...] = ()) -> str | None:
    """Remember whether the tips show, as the person switched them."""
    with _CHANGE_LOCK:
        current, notice = read_settings(path)
        if notice == SETTINGS_NEWER:
            return SETTINGS_NEWER
        return write_settings(path, {**current, "hints": on}, makeable)


def remember_theme_at(path: Path, theme: str | None, makeable: tuple[Path, ...] = ()) -> str | None:
    """Remember the colors that the person chose (stage G3a): one of THEMES,
    or None to follow the colors that the browser reports."""
    with _CHANGE_LOCK:
        current, notice = read_settings(path)
        if notice == SETTINGS_NEWER:
            return SETTINGS_NEWER
        values = {key: value for key, value in current.items() if key != "theme"}
        if theme is not None:
            values["theme"] = theme
        return write_settings(path, values, makeable)


# The values of the view page that a request may give with its items, and
# their keys in the file (stage K1 of v2.2.0).
VIEW_KEYS = {"layout": "view_layout", "period": "view_period", "grain": "view_grain", "types": "view_types"}


def remember_view_at(
    path: Path,
    items: list[str],
    shelf: str,
    view: dict[str, Any] | None = None,
    makeable: tuple[Path, ...] = (),
) -> str | None:
    """Remember the items that the view page shows and whether its item shelf
    is open (stage G3b), by the names of the items only; and from v2.2.0 the
    values of ``view`` that are given (VIEW_KEYS): None takes a value away (no
    layout used last, or the activity types counted at first), and a value not
    given stays as it is."""
    with _CHANGE_LOCK:
        current, notice = read_settings(path)
        if notice == SETTINGS_NEWER:
            return SETTINGS_NEWER
        values = {**current, "view_items": list(items), "view_shelf": shelf}
        for name, value in (view or {}).items():
            key = VIEW_KEYS[name]
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
        return write_settings(path, values, makeable)


def change_layouts_at(
    path: Path, change: Any, makeable: tuple[Path, ...] = ()
) -> tuple[dict[str, Any], str | None]:
    """Change the layouts of the person once (stage K1 of v2.2.0): read the
    file, change, and write it under one lock. The layouts after the change
    and None when they are written; otherwise the layouts as they were, and a
    code (SETTINGS_NEWER or SETTINGS_NOT_WRITTEN). A change that cannot be made
    raises layouts.LayoutChangeError, and nothing is written."""
    with _CHANGE_LOCK:
        current, notice = read_settings(path)
        before = {
            "layouts": current.get("view_layouts", []),
            "hidden": current.get("view_layouts_hidden", []),
            "current": current.get("view_layout"),
        }
        if notice == SETTINGS_NEWER:
            return before, SETTINGS_NEWER
        after = _changed_layouts(before, change)
        values = {**current, "view_layouts": after["layouts"], "view_layouts_hidden": after["hidden"]}
        values.pop("view_layout", None)
        if after["current"] is not None:
            values["view_layout"] = after["current"]
        notice = write_settings(path, values, makeable)
        return (after, None) if notice is None else (before, notice)


def launch_answer(values: dict[str, Any], notice: str | None, *, present: bool) -> dict[str, Any]:
    """What the page takes from the settings when it starts: a later launch
    when a place is remembered (the tips alone do not make one), the places,
    the tips, the colors (stage G3a), the items and the shelf of the view page
    (stage G3b), what to tell of the file, and whether there is a file to
    forget (stage C1)."""
    store = values.get("store")
    parent = values.get("output_parent")
    return {
        "launch": "later" if store is not None or parent is not None else "first",
        "store": store,
        "output_parent": parent,
        "hints": values.get("hints"),
        "theme": values.get("theme"),
        "view_items": values.get("view_items"),
        "view_shelf": values.get("view_shelf"),
        # The layouts and the view that v2.2.0 remembers (stage K1).
        "view_layouts": values.get("view_layouts", []),
        "view_layouts_hidden": values.get("view_layouts_hidden", []),
        "view_layout": values.get("view_layout"),
        "view_period": values.get("view_period"),
        "view_grain": values.get("view_grain"),
        "view_types": values.get("view_types"),
        "timezone": values.get("timezone"),
        "notice": notice,
        "present": present,
    }


def _target() -> tuple[Path, tuple[Path, ...]]:
    # The place is asked for each time, so that a test's place is used.
    path = places.settings_file()
    return path, places.makeable_settings_folders(path)


def launch_settings() -> dict[str, Any]:
    path, _makeable = _target()
    return launch_answer(*read_settings(path), present=settings_present(path))


def launch_theme() -> str | None:
    """The colors that the settings remember, for the address that a launch
    opens (stage G3a); None when there are none or the file is not used."""
    path, _makeable = _target()
    return read_settings(path)[0].get("theme")


def recent_outputs() -> list[str]:
    """The outputs that the settings remember, newest first (stage B5b); none
    when there are no settings or they are not used."""
    path, _makeable = _target()
    values, _notice = read_settings(path)
    return list(values.get("recent_outputs", []))


def remember_run(output: Path, store: Path | None, timezone: str | None = None) -> str | None:
    path, makeable = _target()
    return remember_run_at(path, output, store, timezone, makeable)


def remember_hints(on: bool) -> str | None:
    path, makeable = _target()
    return remember_hints_at(path, on, makeable)


def remember_theme(theme: str | None) -> str | None:
    path, makeable = _target()
    return remember_theme_at(path, theme, makeable)


def remember_view(items: list[str], shelf: str, view: dict[str, Any] | None = None) -> str | None:
    path, makeable = _target()
    return remember_view_at(path, items, shelf, view, makeable)


def change_layouts(change: Any) -> tuple[dict[str, Any], str | None]:
    path, makeable = _target()
    return change_layouts_at(path, change, makeable)


def forget_settings() -> tuple[str | None, bool]:
    """Forget the settings: what to tell (None when no file is left), and
    whether there was anything to forget (stage C1)."""
    path, _makeable = _target()
    present = settings_present(path)
    return remove_settings(path), present


__all__ = [
    "MAX_PLACE_LENGTH",
    "MAX_RECENT_OUTPUTS",
    "MAX_SETTINGS_BYTES",
    "SETTINGS_FORMAT",
    "SETTINGS_INVALID",
    "SETTINGS_NEWER",
    "SETTINGS_NOT_REMOVED",
    "SETTINGS_NOT_WRITTEN",
    "SHELF_STATES",
    "THEMES",
    "VIEW_KEYS",
    "change_layouts",
    "change_layouts_at",
    "forget_settings",
    "launch_answer",
    "launch_settings",
    "launch_theme",
    "read_settings",
    "recent_outputs",
    "remember_hints",
    "remember_hints_at",
    "remember_run",
    "remember_run_at",
    "remember_theme",
    "remember_theme_at",
    "remember_view",
    "remember_view_at",
    "remove_settings",
    "settings_present",
    "timezone_kept",
    "types_kept",
    "write_settings",
]
