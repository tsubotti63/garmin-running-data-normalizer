"""Text with a lone UTF-16 surrogate, such as a truncated emoji (stage A3d-2c-1).

JSON can write one half of a UTF-16 surrogate pair, such as ``"\\ud83d"``, and
Python reads it as a lone surrogate: text that UTF-8 cannot write, so the
outputs could not be written. A whole pair reads as one character. Only such
an escape gives a lone surrogate: UTF-8 bytes cannot hold one, and a file with
such bytes is not readable (stage A3c).
"""

from __future__ import annotations

import re
from typing import Any

REPLACEMENT_CHARACTER = "�"
# The escape of a surrogate, with small or capital hexadecimal digits.
_SURROGATE_ESCAPE = re.compile(r"\\u[dD][89a-fA-F]")
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def may_hold_lone_surrogates(text: str) -> bool:
    """Whether the text of a JSON file may give a lone surrogate once read."""
    return _SURROGATE_ESCAPE.search(text) is not None


def repair_text(value: Any) -> tuple[Any, int]:
    """Return the value with each lone surrogate in its texts and in the names
    of its objects replaced by U+FFFD, and the number of texts and names that
    were repaired, however many surrogates each held.

    When two names of one object read alike once repaired, the later value is
    kept, as JSON keeps the later of two equal names.
    """
    if isinstance(value, str):
        repaired, replaced = _LONE_SURROGATE.subn(REPLACEMENT_CHARACTER, value)
        return repaired, int(bool(replaced))
    if isinstance(value, list):
        items: list[Any] = []
        count = 0
        for item in value:
            repaired_item, item_count = repair_text(item)
            items.append(repaired_item)
            count += item_count
        return items, count
    if isinstance(value, dict):
        repaired_object: dict[str, Any] = {}
        count = 0
        for name, item in value.items():
            repaired_name, name_count = repair_text(name)
            repaired_item, item_count = repair_text(item)
            repaired_object[repaired_name] = repaired_item
            count += name_count + item_count
        return repaired_object, count
    return value, 0


def repair_json_text(text: str, value: Any) -> tuple[Any, int]:
    """Repair the value read from the text of a JSON file; a text without the
    escape of a surrogate is not searched."""
    if not may_hold_lone_surrogates(text):
        return value, 0
    return repair_text(value)


__all__ = [
    "REPLACEMENT_CHARACTER",
    "may_hold_lone_surrogates",
    "repair_json_text",
    "repair_text",
]
