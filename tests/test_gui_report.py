"""This computer's values of the GitHub report (stage B5c).

The help panel shows the values of the Bug report form before the person
opens it on GitHub, and the server gives the three that the page cannot know:
the operating system and its version, the version of Python, and the line
that ``--version`` prints. Only fixed sources are read, and each value goes
in only in a plain form, so that no name of the machine or of the person and
no place goes in.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.gui import report
from garmin_running_data_normalizer.gui.report import (
    MAX_OS_RELEASE_BYTES,
    VERSION_LINE,
    operating_system,
    os_release,
    report_values,
)

# The form in which the page takes a value of this computer.
PAGE_FORM = r"^[A-Za-z0-9 ._()+-]{1,80}$"


class ReportValuesTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def release(self, text: str | bytes, name: str = "os-release") -> Path:
        path = self.root / name
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return path

    def test_the_name_and_version_of_linux_come_from_os_release(self) -> None:
        cases = {
            'NAME="Ubuntu"\nVERSION_ID="24.04"\nID=ubuntu\n': ("Ubuntu", "24.04"),
            # Without NAME, its ID; quoted with either quote; without a version.
            "ID=debian\nVERSION_ID=12\n": ("debian", "12"),
            "NAME='Fedora Linux'\nVERSION_ID='40'\n": ("Fedora Linux", "40"),
            'NAME="Arch Linux"\n': ("Arch Linux", None),
            # The first of a name given twice.
            'NAME="Ubuntu"\nNAME="Other"\nVERSION_ID="24.04 LTS"\n': ("Ubuntu", "24.04 LTS"),
            # Characters outside the plain form, a quote left open, an
            # escaped line break, a letter outside ASCII, too long, or spaces
            # around: the value does not go in.
            'NAME="Ubuntu $(id)"\nID=ubuntu\nVERSION_ID="24.04\n': ("ubuntu", None),
            'NAME="Ubu\\nntu"\nVERSION_ID="2é4"\n': (None, None),
            f'NAME="{"A" * 41}"\nVERSION_ID="1"\n': (None, "1"),
            'NAME=" Ubuntu"\nVERSION_ID="24.04 "\n': (None, None),
            "": (None, None),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(os_release((self.release(text),)), expected)
        # The first place that is there; a file larger than 64 KiB, or none,
        # gives nothing.
        missing = self.root / "missing"
        self.assertEqual(os_release((missing, self.release('NAME="Debian"\n', "second"))), ("Debian", None))
        large = self.release(b'NAME="Ubuntu"\n' + b"#" * MAX_OS_RELEASE_BYTES, "large")
        self.assertEqual(os_release((large, self.release('NAME="Debian"\n', "third"))), (None, None))
        self.assertEqual(os_release((missing,)), (None, None))

    def test_the_operating_system_names_its_version_in_the_plain_form_only(self) -> None:
        cases = (
            ("Darwin", {"mac_ver": ("26.5", ("", "", ""), "arm64")}, "macOS 26.5"),
            ("Darwin", {"mac_ver": ("", ("", "", ""), "")}, "macOS"),
            ("Windows", {"version": "10.0.26100"}, "Windows 10.0.26100"),
            ("Windows", {"version": "10.0.26100\r\nD:\\Running Data"}, "Windows"),
            ("Linux", {"os_release": ("Ubuntu", "24.04")}, "Ubuntu 24.04"),
            ("Linux", {"os_release": ("Ubuntu", None)}, "Ubuntu"),
            ("Linux", {"os_release": (None, "24.04")}, "Linux"),
            ("FreeBSD", {}, "FreeBSD"),
            ("", {}, "Unknown"),
        )
        for name, answers, expected in cases:
            with self.subTest(system=name, answers=answers), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(report.platform, "system", return_value=name))
                for function, answer in answers.items():
                    owner = report if function == "os_release" else report.platform
                    stack.enter_context(patch.object(owner, function, return_value=answer))
                self.assertEqual(operating_system(), expected)

    def test_the_values_hold_no_name_of_the_machine_or_the_person_and_no_place(self) -> None:
        home = self.root / "synthetic-home-q7"
        home.mkdir()
        person = "synthetic-person-k4"
        environment = {"HOME": str(home), "USERPROFILE": str(home), "USER": person, "USERNAME": person, "LOGNAME": person}
        report_values.cache_clear()
        self.addCleanup(report_values.cache_clear)
        with patch.dict(os.environ, environment), patch.object(report.platform, "node", return_value="synthetic-machine-z9"):
            values = report_values()
        self.assertEqual(sorted(values), ["operating_system", "package_version", "python_version"])
        text = json.dumps(values)
        for private in ("synthetic", self.root.name, str(Path.home()), os.sep):
            with self.subTest(private=private):
                self.assertNotIn(private, text)
        for name, value in values.items():
            with self.subTest(name=name):
                self.assertRegex(value, PAGE_FORM)
        self.assertRegex(values["python_version"], r"^Python( [0-9][0-9A-Za-z.]*)?$")
        # The same values for the whole launch.
        self.assertIs(report_values(), report_values())

    def test_the_version_line_is_the_one_that_version_prints(self) -> None:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), self.assertRaises(SystemExit) as caught:
            runner.main(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(printed.getvalue(), f"{VERSION_LINE}\n")
        self.assertEqual(report_values()["package_version"], VERSION_LINE)


if __name__ == "__main__":
    unittest.main()
