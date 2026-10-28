"""Names that the GUI keeps and shows (stage K1 of v2.2.0): the names that the
person gives to layouts, and the names of activity types from an output.

A name that holds a control character, a line or paragraph separator, or a
character that changes the direction of the text around it is not kept: such
a character can make a name read as another one, as a place inside the input
that cannot be shown (stage B3c). These also count the marks of direction
(U+200E, U+200F, U+061C). The page shows names as text only."""

from __future__ import annotations

import unicodedata

# The marks, embeddings, overrides, and isolates that change the direction of
# text.
DIRECTION_CHARACTERS = frozenset(
    chr(code) for code in (0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A))
)


def unsafe_character(text: str) -> bool:
    """Whether ``text`` holds a control character, a line or paragraph
    separator, or a character that changes the direction of text."""
    return any(
        unicodedata.category(character) in ("Cc", "Zl", "Zp") or character in DIRECTION_CHARACTERS
        for character in text
    )


__all__ = ["DIRECTION_CHARACTERS", "unsafe_character"]
