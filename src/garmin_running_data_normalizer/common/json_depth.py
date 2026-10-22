"""The limit of the nesting of the JSON that the product reads (stage E2d).

How deep ``json.loads`` can go depends on the version of Python and on the
system: Python 3.11 stops near its recursion limit, while Python 3.15 on Linux
read JSON nested 100,000 deep, so that a file that is left out elsewhere as
nested too deeply was read there, and failed later (stage E2c). The product
counts the nesting of the value that it read, without recursion, and refuses
more than ``MAX_JSON_DEPTH`` levels, on every version and system. The limit is
far below the recursion limit of 1000, so that a value within it can also be
followed by recursion, as the repair of lone surrogates and ``json.dumps`` do.
"""

from __future__ import annotations

from typing import Any

# The JSON of the synthetic Export nests at most 4 deep.
MAX_JSON_DEPTH = 256


def check_json_depth(value: Any, limit: int = MAX_JSON_DEPTH) -> None:
    """Raise ValueError when lists and objects nest more than ``limit`` deep
    in the value: a scalar is 0 deep, ``[]`` and ``{}`` are 1 deep, and
    ``[[]]`` is 2 deep. A caller that leaves out JSON that is not JSON leaves
    this out in the same way."""
    pending = [(value, 1)] if isinstance(value, (dict, list)) else []
    while pending:
        container, level = pending.pop()
        if level > limit:
            raise ValueError(f"JSON nested more than {limit} deep")
        children = container.values() if isinstance(container, dict) else container
        pending.extend((child, level + 1) for child in children if isinstance(child, (dict, list)))


__all__ = ["MAX_JSON_DEPTH", "check_json_depth"]
