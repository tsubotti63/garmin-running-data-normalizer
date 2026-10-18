"""The values of this computer for a report on GitHub (stage B5c).

The help panel shows the values of the Bug report form before the person
opens it on GitHub, and the address carries only those values. This module
gives the three that the page cannot know: the operating system and its
version, the version of Python, and the line that ``--version`` prints.

Only fixed sources are read, and no name of the machine or of the person, no
place, and nothing that the person entered: the version of macOS, the version
of Windows, and for Linux the name and version in os-release, up to 64 KiB.
A value goes in only in a plain form (letters and digits of ASCII, spaces,
and ``.``, ``_``, and ``-``, up to 40 characters); otherwise only the name of
the system does.
"""
from __future__ import annotations

import platform
import re
from functools import cache
from pathlib import Path

from .. import __version__

# The line that ``--version`` prints, which the form asks for as it is.
VERSION_LINE = f"python -m garmin_running_data_normalizer {__version__}"
MAX_OS_RELEASE_BYTES = 64 * 1024
OS_RELEASE_PLACES = (Path("/etc/os-release"), Path("/usr/lib/os-release"))
PLAIN_VALUE = re.compile(r"[A-Za-z0-9 ._-]{1,40}")


def _plain(value: object) -> str | None:
    if isinstance(value, str) and PLAIN_VALUE.fullmatch(value) and value.strip() == value:
        return value
    return None


def _named(name: str, version: object) -> str:
    plain = _plain(version)
    return name if plain is None else f"{name} {plain}"


def os_release(places: tuple[Path, ...] = OS_RELEASE_PLACES) -> tuple[str | None, str | None]:
    """The name (NAME, else ID) and VERSION_ID of the first os-release that is
    there, each only in the plain form; nothing from a file larger than 64 KiB
    or one that cannot be read."""
    for place in places:
        try:
            with place.open("rb") as file:
                data = file.read(MAX_OS_RELEASE_BYTES + 1)
        except OSError:
            continue
        if len(data) > MAX_OS_RELEASE_BYTES:
            return None, None
        fields: dict[str, str] = {}
        for line in data.decode("utf-8", errors="replace").splitlines():
            key, separator, value = line.partition("=")
            if separator != "=" or key not in ("NAME", "ID", "VERSION_ID") or key in fields:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key] = value
        name = _plain(fields.get("NAME")) or _plain(fields.get("ID"))
        return name, _plain(fields.get("VERSION_ID"))
    return None, None


def operating_system() -> str:
    """The operating system and its version, as the form asks for them."""
    system = platform.system()
    if system == "Darwin":
        return _named("macOS", platform.mac_ver()[0])
    if system == "Windows":
        return _named("Windows", platform.version())
    if system == "Linux":
        name, version = os_release()
        return "Linux" if name is None else _named(name, version)
    return _plain(system) or "Unknown"


@cache
def report_values() -> dict[str, str]:
    """This computer's values of the report, the same for the whole launch."""
    return {
        "operating_system": operating_system(),
        "python_version": _named("Python", platform.python_version()),
        "package_version": VERSION_LINE,
    }
