"""The layouts of the view page (internal; stage K1 of v2.2.0): the built-in
layouts, and the rules of the layouts that the person saves.

A layout holds the items that the view page shows and their order only; the
period, the grouping, and the activity types are remembered apart (settings).
The built-in layouts have fixed ids and items. Their names are the words of
the page (``view.layout.<id>`` in the catalogs), which the server reads from
the same files, so that each name is kept in one place. A layout of the person
has an id that the server gives ("u-" and eight hexadecimal digits), a name,
and one to six items.

A name is kept as the person gave it, in NFC and without the spaces around
it: one to 30 characters, without a control or direction character (the page
shows it as text only). Two names are compared in NFKC and casefold, so that
a full-width "ＲＵＮ" is the same name as "Run"; a name of the person cannot be
that of a built-in layout in either language, or that of another of the
person's layouts.

The changes are pure functions here; the settings read, change, and write the
file under one lock (settings.change_layouts_at), so that two tabs that change
the layouts at once keep both changes."""

from __future__ import annotations

import json
import re
import secrets
import unicodedata
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ..common.names import unsafe_character
from ..view.items import ITEMS_BY_KEY
from ..view.series import MAX_PANELS

BUILT_IN_LAYOUTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("run", ("dist", "pace", "hr")),
    ("sleep_hr", ("sleep", "sscore", "hrv", "rhr")),
    ("volume", ("dist", "time", "count", "asc")),
    ("form", ("cad", "sl", "vo", "gct")),
    ("load", ("load", "acute", "chronic", "acwr")),
    ("estimates", ("vo2", "phalf", "pfull", "endu")),
)
BUILT_IN_IDS = tuple(layout_id for layout_id, _items in BUILT_IN_LAYOUTS)
MAX_LAYOUTS = 20
MAX_LAYOUT_NAME_LENGTH = 30
USER_LAYOUT_ID = re.compile(r"u-[0-9a-f]{8}")
# The languages of the page's catalogs (server.LANGUAGES).
CATALOG_LANGUAGES = ("en", "ja")
LAYOUT_OPERATIONS = ("add", "rename", "overwrite", "move", "remove", "hide", "show", "reset")

# What a change of the layouts tells the page, codes only.
LAYOUT_NAME_INVALID = "LAYOUT_NAME_INVALID"
LAYOUT_NAME_TAKEN = "LAYOUT_NAME_TAKEN"
LAYOUT_NOT_FOUND = "LAYOUT_NOT_FOUND"
LAYOUTS_FULL = "LAYOUTS_FULL"
REQUEST_INVALID = "REQUEST_INVALID"


class LayoutChangeError(ValueError):
    """A change of the layouts that cannot be made, with its code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def layout_name(value: Any) -> str | None:
    """The name to keep of a name given: its NFC without the spaces around it,
    of one to MAX_LAYOUT_NAME_LENGTH characters, without a control or direction
    character; None otherwise."""
    if not isinstance(value, str):
        return None
    name = unicodedata.normalize("NFC", value).strip()
    if not 0 < len(name) <= MAX_LAYOUT_NAME_LENGTH or unsafe_character(name):
        return None
    return name


def name_key(name: str) -> str:
    """The form in which two names are compared."""
    return unicodedata.normalize("NFKC", name).casefold()


@lru_cache(maxsize=1)
def built_in_name_keys() -> frozenset[str]:
    """The names of the built-in layouts in every language of the page, as
    they are compared, from the page's own catalogs."""
    keys: set[str] = set()
    catalogs = files(__package__).joinpath("static").joinpath("i18n")
    for language in CATALOG_LANGUAGES:
        catalog = json.loads(catalogs.joinpath(f"{language}.json").read_text(encoding="utf-8"))
        for layout_id in BUILT_IN_IDS:
            name = catalog.get(f"view.layout.{layout_id}")
            if isinstance(name, str):
                keys.add(name_key(name))
    return frozenset(keys)


def layout_items(value: Any) -> list[str] | None:
    """The items of a layout as a request gives them: one to MAX_PANELS items
    that this version knows, each once; None otherwise."""
    if (
        not isinstance(value, list)
        or not 0 < len(value) <= MAX_PANELS
        or any(not isinstance(key, str) or key not in ITEMS_BY_KEY for key in value)
        or len(set(value)) != len(value)
    ):
        return None
    return list(value)


def kept_layouts(value: Any) -> list[dict[str, Any]] | None:
    """The layouts of the person as the settings keep them, or None when the
    value is not a list. A layout of another form is left out alone: an id of
    another form or one given twice, a name that is not kept, or no item that
    this version knows. The items that this version does not know (of a later
    version), those given twice, and those after the sixth are left out, as
    the items of the view page are (stage G3b); so are the layouts after the
    twentieth. Names are not compared with each other here: the changes keep
    them apart."""
    if not isinstance(value, list):
        return None
    layouts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in value:
        if len(layouts) == MAX_LAYOUTS:
            break
        if not isinstance(entry, dict):
            continue
        layout_id = entry.get("id")
        name = layout_name(entry.get("name"))
        items = entry.get("items")
        if not isinstance(layout_id, str) or not USER_LAYOUT_ID.fullmatch(layout_id) or layout_id in seen:
            continue
        if name is None or not isinstance(items, list):
            continue
        known = list(dict.fromkeys(key for key in items if isinstance(key, str) and key in ITEMS_BY_KEY))[:MAX_PANELS]
        if not known:
            continue
        seen.add(layout_id)
        layouts.append({"id": layout_id, "name": name, "items": known})
    return layouts


def kept_hidden(value: Any) -> list[str] | None:
    """The built-in layouts that the person hid, in their own order, or None
    when the value is not a list; other ids are left out."""
    if not isinstance(value, list):
        return None
    hidden = {layout_id for layout_id in value if isinstance(layout_id, str)}
    return [layout_id for layout_id in BUILT_IN_IDS if layout_id in hidden]


def built_in_answer() -> list[dict[str, Any]]:
    """The built-in layouts as the view page takes them: the id and the items
    of each, in their order; the page names them from its catalogs."""
    return [{"id": layout_id, "items": list(items)} for layout_id, items in BUILT_IN_LAYOUTS]


def new_layout_id(taken: set[str]) -> str:
    """An id for a new layout of the person that no other layout has."""
    while True:
        layout_id = f"u-{secrets.token_hex(4)}"
        if layout_id not in taken:
            return layout_id


def change_layouts(state: dict[str, Any], change: Any) -> dict[str, Any]:
    """The layouts after one change of the page: ``state`` holds the layouts of
    the person ("layouts"), the built-in layouts hidden ("hidden"), and the
    layout used last ("current", an id or None). LayoutChangeError tells why a
    change cannot be made.

    - add (name, items): a new layout last, which becomes the one used last.
    - rename (id, name), overwrite (id, items), move (id, direction "up" or
      "down"), remove (id): a layout of the person.
    - hide, show (id): a built-in layout (hiding the one used last forgets
      that it was used); reset shows them all."""
    if not isinstance(change, dict) or change.get("op") not in LAYOUT_OPERATIONS:
        raise LayoutChangeError(REQUEST_INVALID)
    operation = change["op"]
    layouts = [dict(layout) for layout in state.get("layouts", [])]
    hidden = list(state.get("hidden", []))
    current = state.get("current")

    def index_of() -> int:
        layout_id = change.get("id")
        for index, layout in enumerate(layouts):
            if layout["id"] == layout_id:
                return index
        raise LayoutChangeError(LAYOUT_NOT_FOUND)

    def name_given(index: int | None) -> str:
        name = layout_name(change.get("name"))
        if name is None:
            raise LayoutChangeError(LAYOUT_NAME_INVALID)
        key = name_key(name)
        if key in built_in_name_keys() or any(
            name_key(layout["name"]) == key for other, layout in enumerate(layouts) if other != index
        ):
            raise LayoutChangeError(LAYOUT_NAME_TAKEN)
        return name

    def items_given() -> list[str]:
        items = layout_items(change.get("items"))
        if items is None:
            raise LayoutChangeError(REQUEST_INVALID)
        return items

    if operation == "add":
        items = items_given()
        if len(layouts) >= MAX_LAYOUTS:
            raise LayoutChangeError(LAYOUTS_FULL)
        name = name_given(None)
        layout_id = new_layout_id({layout["id"] for layout in layouts})
        layouts.append({"id": layout_id, "name": name, "items": items})
        current = layout_id
    elif operation == "rename":
        index = index_of()
        layouts[index]["name"] = name_given(index)
    elif operation == "overwrite":
        index = index_of()
        layouts[index]["items"] = items_given()
        current = layouts[index]["id"]
    elif operation == "move":
        index = index_of()
        direction = change.get("direction")
        if direction not in ("up", "down"):
            raise LayoutChangeError(REQUEST_INVALID)
        other = index - 1 if direction == "up" else index + 1
        if 0 <= other < len(layouts):
            layouts[index], layouts[other] = layouts[other], layouts[index]
    elif operation == "remove":
        index = index_of()
        if layouts.pop(index)["id"] == current:
            current = None
    elif operation in ("hide", "show"):
        layout_id = change.get("id")
        if layout_id not in BUILT_IN_IDS:
            raise LayoutChangeError(LAYOUT_NOT_FOUND)
        chosen = set(hidden) | {layout_id} if operation == "hide" else set(hidden) - {layout_id}
        hidden = [built_in for built_in in BUILT_IN_IDS if built_in in chosen]
        # A layout hidden is not the one used last any more, as one removed.
        if operation == "hide" and current == layout_id:
            current = None
    else:
        hidden = []
    return {"layouts": layouts, "hidden": hidden, "current": current}


__all__ = [
    "BUILT_IN_IDS",
    "BUILT_IN_LAYOUTS",
    "CATALOG_LANGUAGES",
    "LAYOUTS_FULL",
    "LAYOUT_NAME_INVALID",
    "LAYOUT_NAME_TAKEN",
    "LAYOUT_NOT_FOUND",
    "LAYOUT_OPERATIONS",
    "MAX_LAYOUTS",
    "MAX_LAYOUT_NAME_LENGTH",
    "USER_LAYOUT_ID",
    "LayoutChangeError",
    "built_in_answer",
    "built_in_name_keys",
    "change_layouts",
    "kept_hidden",
    "kept_layouts",
    "layout_items",
    "layout_name",
    "name_key",
    "new_layout_id",
]
