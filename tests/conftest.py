"""What every test shares (stage B4c): the settings of the GUI are kept in a
folder of the test, never in the place of the person who runs the tests.

The GUI keeps the settings of an earlier launch in one file, which only
``places.settings_file`` names, and from v2.2.0 (stage M1) the marks of the
view page in another file next to it. Each test gets that function replaced
with a place in its own temporary folder, and the run ends with an error
when the real places changed while the tests ran.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from garmin_running_data_normalizer.gui import places
from garmin_running_data_normalizer.gui.places import MARKS_FILE_NAME, SETTINGS_FILE_NAME, SETTINGS_FOLDER_NAME


def _looked_at(path: Path) -> tuple[int, int, int] | None:
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return None
    return (status.st_mode, status.st_size, status.st_mtime_ns)


@pytest.fixture(autouse=True, scope="session")
def _real_settings_stay() -> Iterator[None]:
    real = places.settings_file()
    marks = real.with_name(MARKS_FILE_NAME)
    before = (_looked_at(real.parent), _looked_at(real), _looked_at(marks))
    yield
    after = (_looked_at(real.parent), _looked_at(real), _looked_at(marks))
    assert after == before, "a test changed the settings of the GUI of the person who runs the tests"


@pytest.fixture(autouse=True)
def _settings_of_the_test(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path_factory.mktemp("settings") / SETTINGS_FOLDER_NAME / SETTINGS_FILE_NAME
    monkeypatch.setattr(places, "settings_file", lambda: path)
    return path
