from __future__ import annotations

import contextlib
import http.client
import inspect
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch, call

from garmin_running_data_normalizer import __version__
from garmin_running_data_normalizer.common.time import DEFAULT_TIMEZONE
from garmin_running_data_normalizer.gui import chooser, outputs, places
from garmin_running_data_normalizer.gui.chooser import Chooser
from garmin_running_data_normalizer.gui.report import report_values
from garmin_running_data_normalizer.gui.runs import RunManager
from garmin_running_data_normalizer.gui.server import (
    API_ROUTES,
    HOST,
    LAUNCH_KEY_HEADER,
    MAX_REQUEST_BYTES,
    STATIC_FILES,
    GuiRequestHandler,
    GuiServer,
    serve_until_stopped,
)
from tests.test_gui_runs import (
    PRIVATE_TEXT,
    SYNTHETIC_EXPORT,
    child_environment,
    run_cli,
    stub_manager,
    wait_until,
)
from tests.test_run_all_progress import tree_bytes
from tests.v1_3_outputs import as_release, as_v1_3


ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "src/garmin_running_data_normalizer/gui/static"

# Pinned here instead of read from the server module, so that any change to the
# response policy or to a content type fails these tests.
EXPECTED_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'"
    ),
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}
EXPECTED_CONTENT_TYPES = {
    "/": "text/html; charset=utf-8",
    "/app.mjs": "text/javascript; charset=utf-8",
    "/flow.mjs": "text/javascript; charset=utf-8",
    "/i18n.mjs": "text/javascript; charset=utf-8",
    "/theme.js": "text/javascript; charset=utf-8",
    "/styles.css": "text/css; charset=utf-8",
    # The view page and what both pages share (stage G3b).
    "/launch.mjs": "text/javascript; charset=utf-8",
    "/view": "text/html; charset=utf-8",
    "/view.mjs": "text/javascript; charset=utf-8",
    "/view_flow.mjs": "text/javascript; charset=utf-8",
    "/view_chart.mjs": "text/javascript; charset=utf-8",
    "/view.css": "text/css; charset=utf-8",
    "/i18n/en.json": "application/json",
    "/i18n/ja.json": "application/json",
    "/favicon.svg": "image/svg+xml",
    "/favicon.png": "image/png",
}

Headers = list[tuple[str, str]]
Response = tuple[int, http.client.HTTPMessage, bytes]

_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex


def _require_loopback(address: object) -> None:
    host = address[0] if isinstance(address, tuple) else address
    if host != HOST:
        raise ConnectionRefusedError("only 127.0.0.1 may be reached during GUI tests")


def _loopback_connect(sock: socket.socket, address: object) -> None:
    _require_loopback(address)
    return _REAL_CONNECT(sock, address)


def _loopback_connect_ex(sock: socket.socket, address: object) -> int:
    _require_loopback(address)
    return _REAL_CONNECT_EX(sock, address)


def without(headers: Iterable[tuple[str, str]], name: str) -> Headers:
    return [(key, value) for key, value in headers if key.lower() != name.lower()]


def replaced(headers: Iterable[tuple[str, str]], name: str, value: str) -> Headers:
    return [*without(headers, name), (name, value)]


class GuiServerTestCase(unittest.TestCase):
    """Run a GUI server per test; only 127.0.0.1 can be reached meanwhile."""

    # None means that the test starts its own server.
    idle_timeout: float | None = 600.0

    def setUp(self) -> None:
        for name, replacement in (
            ("connect", _loopback_connect),
            ("connect_ex", _loopback_connect_ex),
        ):
            patcher = patch.object(socket.socket, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.stderr = io.StringIO()
        redirect = contextlib.redirect_stderr(self.stderr)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        if self.idle_timeout is not None:
            self.start_server(self.idle_timeout)

    def start_server(
        self, idle_timeout: float, runs: RunManager | None = None, dialogs: Chooser | None = None
    ) -> None:
        self.server = GuiServer(idle_timeout=idle_timeout, runs=runs, chooser=dialogs)
        self.port = self.server.server_port
        self.origin = f"http://{HOST}:{self.port}"
        self.thread = threading.Thread(
            target=serve_until_stopped,
            args=(self.server,),
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self._stop_server)

    def _stop_server(self) -> None:
        if self.thread.is_alive():
            self.server.shutdown()
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.stderr.getvalue(), "", "the GUI server wrote to standard error")

    def host_header(self) -> tuple[str, str]:
        return ("Host", f"{HOST}:{self.port}")

    def api_headers(self, body: bytes = b"{}") -> Headers:
        return [
            self.host_header(),
            ("Origin", self.origin),
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            (LAUNCH_KEY_HEADER, self.server.launch_key),
        ]

    def request(
        self,
        method: str,
        path: str,
        headers: Iterable[tuple[str, str]],
        body: bytes | None = None,
    ) -> Response:
        connection = http.client.HTTPConnection(HOST, self.port, timeout=10)
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for name, value in headers:
                connection.putheader(name, value)
            connection.endheaders(body)
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

    def get(self, path: str, headers: Iterable[tuple[str, str]] | None = None) -> Response:
        return self.request("GET", path, [self.host_header()] if headers is None else headers)

    def post_api(
        self,
        path: str,
        headers: Iterable[tuple[str, str]] | None = None,
        body: bytes = b"{}",
    ) -> Response:
        return self.request(
            "POST", path, self.api_headers(body) if headers is None else headers, body
        )

    def raw_request(self, data: bytes) -> bytes:
        with socket.create_connection((HOST, self.port), timeout=10) as connection:
            connection.sendall(data)
            chunks = []
            while chunk := connection.recv(65536):
                chunks.append(chunk)
        return b"".join(chunks)

    def assert_security_headers(self, headers: http.client.HTTPMessage) -> None:
        for name, value in EXPECTED_SECURITY_HEADERS.items():
            self.assertEqual(headers.get_all(name), [value], name)
        self.assertIsNone(headers.get("Set-Cookie"))


class GuiServerListeningTest(GuiServerTestCase):
    def test_listens_on_loopback_on_a_port_chosen_by_the_system(self) -> None:
        host, port = self.server.server_address[:2]
        self.assertEqual(host, HOST)
        self.assertNotEqual(port, 0)
        self.assertEqual(self.server.url, f"http://{HOST}:{port}/#key={self.server.launch_key}")
        self.assertGreaterEqual(len(self.server.launch_key), 43)

        requested = []
        real_bind = socket.socket.bind

        def recording_bind(sock: socket.socket, address: object) -> None:
            requested.append(address)
            real_bind(sock, address)

        with patch.object(socket.socket, "bind", recording_bind):
            other = GuiServer()
        try:
            self.assertEqual(requested, [(HOST, 0)])
            self.assertNotEqual(other.server_port, port)
            self.assertNotEqual(other.launch_key, self.server.launch_key)
        finally:
            other.server_close()

    def test_listening_port_cannot_be_shared(self) -> None:
        listening = self.server.socket
        self.assertEqual(listening.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.assertNotEqual(
                listening.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE), 0
            )
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as other:
            other.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            with self.assertRaises(OSError):
                other.bind((HOST, self.port))

    def test_non_loopback_connections_fail_during_these_tests(self) -> None:
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection(("192.0.2.1", 9), timeout=1)


class GuiApiRequestTest(GuiServerTestCase):
    def test_api_requires_the_launch_key_header(self) -> None:
        key = self.server.launch_key
        other_key = key[:-1] + ("A" if key[-1] != "A" else "B")
        cases = {
            "missing": without(self.api_headers(), LAUNCH_KEY_HEADER),
            "empty": replaced(self.api_headers(), LAUNCH_KEY_HEADER, ""),
            "different": replaced(self.api_headers(), LAUNCH_KEY_HEADER, other_key),
            "longer": replaced(self.api_headers(), LAUNCH_KEY_HEADER, key + "A"),
            "duplicated": [*self.api_headers(), (LAUNCH_KEY_HEADER, key)],
        }
        for name, headers in cases.items():
            for path in API_ROUTES:
                with self.subTest(name, path=path):
                    status, _, body = self.post_api(path, headers)
                    self.assertEqual(status, 403)
                    self.assertEqual(json.loads(body), {"error": "FORBIDDEN"})

        home = Path(tempfile.gettempdir()).resolve() / "synthetic-home"
        with patch.object(places, "home", lambda: home):
            status, _, body = self.post_api("/api/status")
        self.assertEqual(status, 200)
        # The page takes the product's default timezone from here (stage A5a),
        # the default places, which only the GUI has (stage B4a), the
        # settings of an earlier launch, none in a test's own place (stage
        # B4c), and this computer's values of the GitHub report (stage B5c).
        self.assertEqual(
            json.loads(body),
            {
                "default_output_parent": str(home / "GarminRunningData"),
                "default_store": str(home / "GarminRunningData" / "snapshots"),
                "default_timezone": DEFAULT_TIMEZONE,
                "languages": ["en", "ja"],
                "product_version": __version__,
                "report": report_values(),
                "settings": {
                    "launch": "first",
                    "store": None,
                    "output_parent": None,
                    "hints": None,
                    "theme": None,
                    "view_items": None,
                    "view_shelf": None,
                    "view_layouts": [],
                    "view_layouts_hidden": [],
                    "view_layout": None,
                    "view_period": None,
                    "view_grain": None,
                    "view_types": None,
                    "timezone": None,
                    "notice": None,
                    "present": False,
                },
            },
        )
        status, _, body = self.post_api("/api/heartbeat")
        self.assertEqual((status, json.loads(body)), (200, {"status": "ok"}))

    def test_cookies_are_neither_accepted_nor_issued(self) -> None:
        key = self.server.launch_key
        headers = [
            *without(self.api_headers(), LAUNCH_KEY_HEADER),
            ("Cookie", f"key={key}; {LAUNCH_KEY_HEADER}={key}"),
        ]
        self.assertEqual(self.post_api("/api/status", headers)[0], 403)
        for status, response_headers, _ in (
            self.get("/"),
            self.post_api("/api/status"),
            self.post_api("/api/heartbeat"),
        ):
            self.assertEqual(status, 200)
            self.assertIsNone(response_headers.get("Set-Cookie"))

    def test_requests_for_another_host_are_rejected(self) -> None:
        for host in (
            f"localhost:{self.port}",
            f"evil.example:{self.port}",
            HOST,
            f"{HOST}:{self.port + 1}",
            f"[::1]:{self.port}",
        ):
            with self.subTest(host=host):
                self.assertEqual(self.get("/", [("Host", host)])[0], 403)
                headers = replaced(self.api_headers(), "Host", host)
                self.assertEqual(self.post_api("/api/status", headers)[0], 403)
        self.assertEqual(self.get("/", [])[0], 403)
        self.assertEqual(self.get("/", [self.host_header(), self.host_header()])[0], 403)
        self.assertEqual(
            self.post_api("/api/status", without(self.api_headers(), "Host"))[0], 403
        )

    def test_api_requests_from_another_origin_are_rejected(self) -> None:
        for origin in (
            f"http://localhost:{self.port}",
            f"http://{HOST}:{self.port + 1}",
            f"https://{HOST}:{self.port}",
            f"http://{HOST}:{self.port}/",
            "http://evil.example",
            "null",
        ):
            with self.subTest(origin=origin):
                headers = replaced(self.api_headers(), "Origin", origin)
                self.assertEqual(self.post_api("/api/status", headers)[0], 403)
        duplicated = [*self.api_headers(), ("Origin", self.origin)]
        self.assertEqual(self.post_api("/api/status", duplicated)[0], 403)
        self.assertEqual(
            self.post_api("/api/status", without(self.api_headers(), "Origin"))[0], 200
        )

    def test_api_accepts_only_post(self) -> None:
        for path in API_ROUTES:
            with self.subTest(path=path):
                status, headers, body = self.get(
                    path, [self.host_header(), (LAUNCH_KEY_HEADER, self.server.launch_key)]
                )
                self.assertEqual(status, 405)
                self.assertEqual(headers["Allow"], "POST")
                self.assertEqual(json.loads(body), {"error": "METHOD_NOT_ALLOWED"})
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
            with self.subTest(method=method):
                self.assertEqual(self.request(method, "/api/status", [self.host_header()])[0], 501)
        self.assertTrue(self.thread.is_alive())

    def test_api_accepts_only_json_objects(self) -> None:
        for content_type in (
            "text/plain",
            "application/x-www-form-urlencoded",
            "multipart/form-data; boundary=x",
            "application/json-patch+json",
        ):
            with self.subTest(content_type=content_type):
                headers = replaced(self.api_headers(), "Content-Type", content_type)
                status, _, body = self.post_api("/api/status", headers)
                self.assertEqual(status, 415)
                self.assertEqual(json.loads(body), {"error": "UNSUPPORTED_MEDIA_TYPE"})
        headers = without(self.api_headers(), "Content-Type")
        self.assertEqual(self.post_api("/api/status", headers)[0], 415)
        for content_type in ("application/json; charset=utf-8", "Application/JSON"):
            with self.subTest(content_type=content_type):
                headers = replaced(self.api_headers(), "Content-Type", content_type)
                self.assertEqual(self.post_api("/api/status", headers)[0], 200)

        # An object with a value more than 256 deep, and JSON that Python 3.11
        # cannot read by recursion, as every version reads them (stage E2d).
        deep = (b'{"padding": ' + b"[" * 300 + b"]" * 300 + b"}", b"[" * 30_000 + b"]" * 30_000)
        for body in (b"", b"not json", b"[]", b'"text"', b"\xff\xfe", *deep):
            with self.subTest(body=body[:30]):
                status, _, answer = self.post_api("/api/status", self.api_headers(body), body)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(answer), {"error": "BAD_REQUEST"})

        no_length = without(self.api_headers(), "Content-Length")
        status, _, answer = self.request("POST", "/api/status", no_length)
        self.assertEqual((status, json.loads(answer)), (411, {"error": "LENGTH_REQUIRED"}))
        for length in ("abc", "-1", "+2", "1e2"):
            with self.subTest(length=length):
                headers = replaced(self.api_headers(), "Content-Length", length)
                self.assertEqual(self.request("POST", "/api/status", headers)[0], 400)
        headers = [*self.api_headers(), ("Content-Length", "2")]
        self.assertEqual(self.request("POST", "/api/status", headers)[0], 400)
        headers = replaced(self.api_headers(), "Content-Length", str(MAX_REQUEST_BYTES + 1))
        status, _, answer = self.request("POST", "/api/status", headers)
        self.assertEqual((status, json.loads(answer)), (413, {"error": "REQUEST_TOO_LARGE"}))

    def test_unknown_paths_are_not_found(self) -> None:
        self.assertEqual(self.post_api("/api/unknown")[0], 404)
        for path in ("/api", "/api/", "/api/unknown"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)
        for path in ("/", "/app.mjs"):
            with self.subTest(path=path):
                status, headers, _ = self.post_api(path)
                self.assertEqual(status, 405)
                self.assertEqual(headers["Allow"], "GET")

    def test_unexpected_errors_answer_a_code_without_output(self) -> None:
        with patch.object(
            GuiRequestHandler, "_api_status", side_effect=RuntimeError("unexpected")
        ):
            status, headers, body = self.post_api("/api/status")
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body), {"error": "INTERNAL_ERROR"})
        self.assert_security_headers(headers)


class GuiResponseTest(GuiServerTestCase):
    def test_every_response_has_the_security_headers(self) -> None:
        responses = {
            "page": self.get("/"),
            "script": self.get("/app.mjs"),
            "catalog": self.get("/i18n/ja.json"),
            "not found": self.get("/missing"),
            "another host": self.get("/", [("Host", f"localhost:{self.port}")]),
            "API by GET": self.get("/api/status"),
            "API": self.post_api("/api/status"),
            "API without key": self.post_api(
                "/api/status", without(self.api_headers(), LAUNCH_KEY_HEADER)
            ),
            "API with text": self.post_api(
                "/api/status", replaced(self.api_headers(), "Content-Type", "text/plain")
            ),
            "API with a broken body": self.post_api("/api/status", self.api_headers(b"["), b"["),
            "unsupported method": self.request("PUT", "/", [self.host_header()]),
        }
        for name, (_, headers, _) in responses.items():
            with self.subTest(name):
                self.assert_security_headers(headers)

        # Requests that the standard library rejects while reading them.
        host = f"Host: {HOST}:{self.port}\r\n".encode("ascii")
        malformed = {
            "broken request line": (
                b"GET /a b HTTP/1.1\r\n" + host + b"\r\n",
                "400",
                "BAD_REQUEST",
            ),
            "no version": (b"GET /\r\n" + host + b"\r\n", "400", "BAD_REQUEST"),
            "one word": (b"GARBAGE\r\n\r\n", "400", "BAD_REQUEST"),
            "HTTP/2.0": (
                b"GET / HTTP/2.0\r\n" + host + b"\r\n",
                "505",
                "HTTP_VERSION_NOT_SUPPORTED",
            ),
            "HTTP/0.9": (
                b"GET / HTTP/0.9\r\n" + host + b"\r\n",
                "505",
                "HTTP_VERSION_NOT_SUPPORTED",
            ),
            "HTTP/1.2": (
                b"GET / HTTP/1.2\r\n" + host + b"\r\n",
                "505",
                "HTTP_VERSION_NOT_SUPPORTED",
            ),
            # Exactly one byte over the request line limit, so that nothing is
            # left unread when the server closes the connection.
            "long request line": (b"GET /" + b"a" * 65532, "414", "URI_TOO_LONG"),
        }
        for name, (data, status, code) in malformed.items():
            with self.subTest(name):
                head, _, body = self.raw_request(data).partition(b"\r\n\r\n")
                status_line, *header_lines = head.decode("latin-1").split("\r\n")
                self.assertEqual(status_line.split()[1], status)
                raw_headers = dict(line.split(": ", 1) for line in header_lines)
                for header, value in EXPECTED_SECURITY_HEADERS.items():
                    self.assertEqual(raw_headers.get(header), value, header)
                self.assertEqual(json.loads(body), {"error": code})

    def test_static_files_have_fixed_content_types(self) -> None:
        self.assertEqual(
            {path: content_type for path, (_, content_type) in STATIC_FILES.items()},
            EXPECTED_CONTENT_TYPES,
        )
        # A system type map, such as the Windows registry, must not matter.
        with patch("mimetypes.guess_type", return_value=("text/plain", None)):
            for path, content_type in EXPECTED_CONTENT_TYPES.items():
                with self.subTest(path=path):
                    status, headers, body = self.get(path)
                    self.assertEqual(status, 200)
                    self.assertEqual(headers.get_all("Content-Type"), [content_type])
                    self.assertEqual(body, (STATIC_ROOT / STATIC_FILES[path][0]).read_bytes())

    def test_paths_outside_the_static_table_are_not_served(self) -> None:
        for path in (
            "/../pyproject.toml",
            "/%2e%2e/pyproject.toml",
            "/%2E%2E%2Fpyproject.toml",
            "/..%2fpyproject.toml",
            "/i18n/../app.mjs",
            "/static/index.html",
            "/index.html",
            "/app.mjs/",
            "/app.mjs?v=1",
            "/%61pp.mjs",
            "/server.py",
            "/__init__.py",
            "/I18N/en.json",
            "/i18n/",
            "/i18n/de.json",
        ):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                self.assertEqual(status, 404)
                self.assertEqual(json.loads(body), {"error": "NOT_FOUND"})
        # The standard library reduces a leading "//" to "/" before the table
        # lookup, so this is the same file and nothing outside the table.
        self.assertEqual(self.get("//app.mjs")[2], self.get("/app.mjs")[2])

    def test_aborted_requests_write_nothing(self) -> None:
        with socket.create_connection((HOST, self.port), timeout=10):
            pass
        with socket.create_connection((HOST, self.port), timeout=10) as connection:
            connection.sendall(
                f"POST /api/status HTTP/1.1\r\nHost: {HOST}:{self.port}\r\n"
                "Content-Type: application/json\r\nContent-Length: 10\r\n\r\n".encode("ascii")
            )
            connection.shutdown(socket.SHUT_WR)
            connection.recv(65536)
        with socket.create_connection((HOST, self.port), timeout=10) as connection:
            connection.sendall(
                f"GET / HTTP/1.1\r\nHost: {HOST}:{self.port}\r\n\r\n".encode("ascii")
            )
        self.assertEqual(self.get("/")[0], 200)


class GuiPageScriptTest(unittest.TestCase):
    """Stage G3a: the colors that the person chose are set before the page is
    drawn, from the fragment of the address, where the key is too."""

    def test_the_colors_are_set_by_a_classic_script_before_the_page_is_drawn(self) -> None:
        # A classic script in the head runs before anything is drawn; the
        # module runs later. The policy allows no script in the page, so it is
        # a file of its own. The view page too (stage G3b).
        for page, stylesheets, module in (
            ("index.html", ("/styles.css",), "/app.mjs"),
            ("view.html", ("/styles.css", "/view.css"), "/view.mjs"),
        ):
            with self.subTest(page=page):
                head = (STATIC_ROOT / page).read_text(encoding="utf-8").split("</head>", 1)[0]
                self.assertIn('\n<script src="/theme.js"></script>\n', head)
                for stylesheet in stylesheets:
                    self.assertLess(head.index('src="/theme.js"'), head.index(f'href="{stylesheet}"'))
                self.assertLess(head.index('src="/theme.js"'), head.index(f'src="{module}"'))

    def test_the_page_reads_the_key_alone_and_removes_the_whole_fragment(self) -> None:
        # The fragment holds the key and the colors, separated by "&". The
        # page reads the key with fragmentValue of flow.mjs, which the node
        # tests check, and leaves only the path in the address bar; both pages
        # read it with launch.mjs (stage G3b).
        source = (STATIC_ROOT / "launch.mjs").read_text(encoding="utf-8")
        reading = source.split("export function readLaunchKey() {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn('fragmentValue(window.location.hash, "key")', reading)
        self.assertIn('window.history.replaceState(null, "", window.location.pathname);', reading)
        self.assertNotIn("location.hash.", reading)

    def test_both_pages_take_the_key_and_the_api_from_launch_mjs(self) -> None:
        # Stage G3b: the rules of the key are written once, in launch.mjs,
        # whose header is the server's; neither page has a key, a header, or
        # a request of its own.
        launch = (STATIC_ROOT / "launch.mjs").read_text(encoding="utf-8")
        self.assertIn(f'export const LAUNCH_KEY_HEADER = "{LAUNCH_KEY_HEADER}";', launch)
        self.assertEqual(launch.count("fetch("), 1)
        for page in ("app.mjs", "view.mjs"):
            with self.subTest(page=page):
                source = (STATIC_ROOT / page).read_text(encoding="utf-8")
                imported = re.search(r'import \{([^}]*)\} from "\./launch\.mjs";', source)
                assert imported is not None
                names = {name.strip() for name in imported.group(1).split(",")}
                self.assertLessEqual({"ApiError", "callWithKey", "readLaunchKey"}, names)
                for own in ("X-Launch-Key", "LAUNCH_KEY", '"launchKey"', "sessionStorage", "replaceState", "location.hash"):
                    self.assertNotIn(own, source)
                # Every request of the API goes through callWithKey; the only
                # fetch of a page is that of its catalogs.
                self.assertEqual(source.count("fetch("), 1)
                self.assertIn("fetch(`/i18n/${language}.json`", source)
                self.assertIn("return callWithKey(state.launchKey, path, payload);", source)

    def test_a_tab_opened_again_with_an_address_reads_it_and_clears_it(self) -> None:
        # Stage G3b: the normalization page opens the view page again in its
        # tab, with the key and the output in the fragment of the address,
        # which only changes the fragment of the page that is open; the view
        # page reads them then, and leaves only the path again.
        source = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.assertIn('window.addEventListener("hashchange", addressChanged);', source)
        changed = re.search(r"async function addressChanged\(\) \{(.*?)\n\}", source, re.DOTALL)
        assert changed is not None
        self.assertLess(changed.group(1).index('addressValue("output")'), changed.group(1).index("readLaunchKey()"))
        started = re.search(r"async function start\(\) \{(.*?)\n\}", source, re.DOTALL)
        assert started is not None
        self.assertLess(started.group(1).index('addressValue("output")'), started.group(1).index("readLaunchKey()"))
        # The tabs find each other by their names.
        app = (STATIC_ROOT / "app.mjs").read_text(encoding="utf-8")
        self.assertIn('const VIEW_TAB = "garmin-running-view";', app)
        self.assertIn('const NORMALIZE_TAB = "garmin-running-normalize";', app)
        self.assertIn("window.name = NORMALIZE_TAB;", app)
        self.assertIn('const VIEW_TAB = "garmin-running-view";', source)
        self.assertIn('const NORMALIZE_TAB = "garmin-running-normalize";', source)
        self.assertIn("window.name = VIEW_TAB;", source)
        # The addresses are those of flow.mjs, which the node tests check.
        self.assertIn("window.open(viewPageAddress(state.launchKey, state.theme, withOutput), VIEW_TAB)?.focus();", app)
        self.assertIn('window.open("", NORMALIZE_TAB);', source)
        to_normalize = re.search(r"function toNormalize\(\) \{(.*?)\n\}", source, re.DOTALL)
        assert to_normalize is not None
        for line in (
            "const address = normalizePageAddress(href, state.launchKey, state.theme);",
            "if (address !== null) {\n    tab.location.href = address;\n  }",
            "tab.focus();",
        ):
            self.assertIn(line, to_normalize.group(1))
        # The fourth box gives the output of its run; the bar opens the page.
        self.assertIn('ui.viewOutput.addEventListener("click", () => openViewPage(true));', app)
        self.assertIn('ui.openView.addEventListener("click", () => openViewPage(false));', app)
        self.assertIn('if (opening === "run" && state.runOutput !== null) {', source)

    def test_the_view_page_keeps_the_app_running(self) -> None:
        # Stage G3b: the view page alone keeps the server from stopping when
        # no request comes, as the normalization page does.
        source = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.assertIn("const HEARTBEAT_INTERVAL_MS = 30000;", source)
        self.assertIn('callApi("/api/heartbeat")', source)
        started = re.search(r"async function start\(\) \{(.*?)\n\}", source, re.DOTALL)
        assert started is not None
        self.assertIn("startHeartbeat();", started.group(1))

    def test_quitting_in_one_tab_stops_the_other(self) -> None:
        # Stage G3b: a page that quit the app tells the other tab, which then
        # says that the app stopped rather than that it lost it; nothing else
        # goes on that channel.
        for page in ("app.mjs", "view.mjs"):
            with self.subTest(page=page):
                source = (STATIC_ROOT / page).read_text(encoding="utf-8")
                self.assertIn("new BroadcastChannel(QUIT_CHANNEL)", source)
                self.assertEqual(source.count("quitChannel?.postMessage("), 1)
                self.assertIn("quitChannel?.postMessage({ stopped: true });", source)
                # Each page listens, and takes only that message.
                self.assertIn('quitChannel?.addEventListener("message", quitHeard);', source)
                heard = re.search(r"function quitHeard\(event\) \{(.*?)\n\}", source, re.DOTALL)
                assert heard is not None
                self.assertIn("if (stoppedMessage(event.data)) {", heard.group(1))

    def test_a_ticket_that_the_server_no_longer_keeps_opens_the_output_once(self) -> None:
        # Stage G3b: a request refused with VIEW_NOT_OPEN opens the output
        # again and asks once more, only if no newer request was made since;
        # the second refusal is a stop of the panels.
        source = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        self.assertIn(
            "if (await reopen()) {\n"
            "        if (seq !== state.seriesSeq) {\n"
            "          return;\n"
            "        }\n"
            "        state.loading = false;\n"
            "        requestSeries(false);\n"
            "        return;\n"
            "      }",
            source,
        )
        self.assertIn('error.code === "VIEW_NOT_OPEN" && again && state.target !== null', source)

    def test_the_view_page_writes_no_settings_that_the_other_tab_forgot(self) -> None:
        # The checker's review of stage G3b-2: after the normalization page
        # forgot the settings, the view page keeps what it shows, forgets what
        # it remembered, and writes its items and its shelf again only when
        # the person changes them, not when an output opens.
        source = (STATIC_ROOT / "view.mjs").read_text(encoding="utf-8")
        heard = re.search(r"function themeHeard\(event\) \{(.*?)\n\}", source, re.DOTALL)
        assert heard is not None
        self.assertIn("state.settings = settingsAfterForget(state.settings);", heard.group(1))
        self.assertIn("state.forgotten = true;", heard.group(1))
        remember = re.search(r"function rememberItems\(byPerson = false\) \{(.*?)\n\}", source, re.DOTALL)
        assert remember is not None
        self.assertIn("if (byPerson) {\n    state.forgotten = false;\n  }", remember.group(1))
        self.assertIn("if (state.forgotten || !state.items.length) {\n    return;\n  }", remember.group(1))
        # An output that opens remembers by itself; the person's changes of
        # the items and the shelf by the person.
        self.assertEqual(source.count("rememberItems();"), 1)
        opened = re.search(r"async function openOutput\(target, focus = false\) \{(.*?)\n\}", source, re.DOTALL)
        assert opened is not None
        self.assertIn("rememberItems();", opened.group(1))
        self.assertEqual(source.count("rememberItems(true);"), 3)


class GuiServerLifecycleTest(GuiServerTestCase):
    idle_timeout = None

    def test_shutdown_api_stops_the_server(self) -> None:
        self.start_server(600.0)
        status, _, body = self.post_api("/api/shutdown")
        self.assertEqual((status, json.loads(body)), (200, {"status": "stopping"}))
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.server.socket.fileno(), -1)

    def test_server_stops_when_no_request_arrives(self) -> None:
        started = time.monotonic()
        self.start_server(0.4)
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        self.assertGreaterEqual(time.monotonic() - started, 0.4)
        self.assertEqual(self.server.socket.fileno(), -1)

    def test_heartbeats_keep_the_server_running(self) -> None:
        self.start_server(1.0)
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline:
            self.assertEqual(self.post_api("/api/heartbeat")[0], 200)
            time.sleep(0.2)
        self.assertTrue(self.thread.is_alive())
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())

    def test_the_server_waits_an_hour_and_the_help_says_so(self) -> None:
        # As the Human maintainer decided on 2026-10-27 (stage G5p): Safari
        # stops the timers of a window hidden with Command-H a few minutes
        # later, and with 10 minutes the GUI stopped about 14 minutes after
        # Safari was hidden; an hour keeps a page that is hidden for a while.
        # The answer of the help about a closed window names the same minutes.
        from garmin_running_data_normalizer.gui import server as gui_server

        self.assertEqual(gui_server.IDLE_TIMEOUT_SECONDS, 3600.0)
        self.assertEqual(
            inspect.signature(GuiServer.__init__).parameters["idle_timeout"].default,
            gui_server.IDLE_TIMEOUT_SECONDS,
        )
        minutes = int(gui_server.IDLE_TIMEOUT_SECONDS // 60)
        catalogs = Path(gui_server.__file__).parent / "static" / "i18n"
        answers = {
            language: json.loads((catalogs / f"{language}.json").read_text(encoding="utf-8"))["faq.window_a"]
            for language in ("en", "ja")
        }
        self.assertIn(f"no window has been connected for {minutes} minutes", answers["en"])
        self.assertIn(f"どの窓からも {minutes} 分つながりが無いと", answers["ja"])
        self.assertNotIn("10 minutes", answers["en"])
        self.assertNotIn("10 分", answers["ja"])

    def test_requests_without_the_launch_key_do_not_keep_the_server_running(self) -> None:
        started = time.monotonic()
        self.start_server(0.6)
        unauthorized = without(self.api_headers(), LAUNCH_KEY_HEADER)
        while self.thread.is_alive() and time.monotonic() - started < 10:
            try:
                self.assertEqual(self.get("/")[0], 200)
                self.assertEqual(self.post_api("/api/heartbeat", unauthorized)[0], 403)
            except OSError:
                break
            time.sleep(0.1)
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        self.assertLess(time.monotonic() - started, 10)


class GuiRunApiTest(GuiServerTestCase):
    idle_timeout = None

    def setUp(self) -> None:
        super().setUp()
        environment = patch.dict(os.environ, child_environment())
        environment.start()
        self.addCleanup(environment.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.parent = self.root / "outputs"
        self.parent.mkdir()

    def call(self, path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def run_request(self, name: str = "output") -> dict[str, object]:
        return {
            "input": str(SYNTHETIC_EXPORT),
            "output_parent": str(self.parent),
            "output_name": name,
            "timezone": "Asia/Tokyo",
        }

    def wait_for_state(self, states: set[str], timeout: float = 60.0) -> dict[str, object]:
        result: dict[str, object] = {}

        def reached() -> bool:
            nonlocal result
            result = self.call("/api/run/status", {})[1]
            return result["state"] in states

        self.assertTrue(wait_until(reached, timeout))
        return result

    def test_folders_are_listed_by_name(self) -> None:
        self.start_server(600.0)
        (self.root / "Visible").mkdir()
        (self.root / "file.txt").write_text("synthetic", encoding="utf-8")
        status, answer = self.call("/api/folders", {"path": str(self.root)})
        self.assertEqual(status, 200)
        self.assertEqual(answer["folders"], ["outputs", "Visible"])
        status, answer = self.call("/api/folders", {"path": "relative"})
        self.assertEqual((status, answer), (422, {"error": "PATH_NOT_ABSOLUTE"}))
        # The list for the Export also names the ZIP files (stage B3a).
        (self.root / "export.zip").write_bytes(b"synthetic")
        status, answer = self.call("/api/folders", {"path": str(self.root), "zips": True})
        self.assertEqual((status, answer["folders"], answer["zips"]), (200, ["outputs", "Visible"], ["export.zip"]))
        for zips in (False, "true", 1):
            with self.subTest(zips=zips):
                status, answer = self.call("/api/folders", {"path": str(self.root), "zips": zips})
                self.assertNotIn("zips", answer)

    def without_download_time(self, answer: dict[str, Any], source: str | None) -> dict[str, Any]:
        """The answer without the download time that an import proposes,
        after checking that it is a time in UTC from the source given (stage
        B4b-1)."""
        answer = dict(answer)
        downloaded_at = answer.pop("downloaded_at")
        self.assertEqual(answer.pop("downloaded_from"), source)
        if source is None:
            self.assertIsNone(downloaded_at)
        else:
            self.assertEqual(datetime.fromisoformat(downloaded_at).utcoffset(), timedelta(0))
        return answer

    def test_the_input_check_returns_codes_only(self) -> None:
        self.start_server(600.0)
        status, answer = self.call("/api/check-input", {"input": str(SYNTHETIC_EXPORT)})
        self.assertEqual(status, 200)
        self.assertEqual(
            self.without_download_time(answer, "newest_file"),
            {
                "ready": True,
                "input_kind": "folder",
                # The counts of the input, numbers only (stage B3b).
                "counts": {
                    "activity_records": 1,
                    "fit_files": 0,
                    "files_read": 1,
                    "files_left_out": 0,
                    "files_not_read": 0,
                },
                "exports_found": [],
                "not_readable": None,
                "findings": [
                    {
                        "code": "RUN_ALL_NOT_EVALUATED",
                        "severity": "INFO",
                        "message_id": "INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT",
                        "next_action_id": "RUN_ALL",
                    }
                ],
            },
        )
        status, answer = self.call("/api/check-input", {"input": str(self.root / "missing")})
        self.assertEqual(status, 200)
        self.assertFalse(answer["ready"])
        self.assertEqual([item["code"] for item in answer["findings"]], ["INPUT_DIRECTORY_INVALID"])
        self.assertIsNone(answer["input_kind"])
        self.assertIsNone(answer["counts"])
        self.without_download_time(answer, None)
        self.assertNotIn(str(self.root), json.dumps(answer))
        for payload, code in (
            ({"input": "relative"}, "PATH_NOT_ABSOLUTE"),
            ({"input": str(SYNTHETIC_EXPORT), "timezone": "Not/A_Zone"}, "TIMEZONE_INVALID"),
            ({"input": str(SYNTHETIC_EXPORT), "timezone": 5}, "TIMEZONE_INVALID"),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/check-input", payload), (422, {"error": code}))

    def test_the_input_check_reads_the_activities_as_a_run_does(self) -> None:
        # The check reads the Activities files as the run reads them, so it
        # tells before the run that the run would stop (stage A5a).
        self.start_server(600.0)
        for label, content, finding in (
            (
                "not JSON",
                "{",
                {
                    "code": "ACTIVITIES_EMPTY",
                    "severity": "ERROR",
                    "message_id": "ACTIVITIES_FILES_CANNOT_BE_READ",
                    "next_action_id": "OBTAIN_COMPLETE_READABLE_EXPORT",
                },
            ),
            (
                "no record",
                json.dumps([{"summarizedActivitiesExport": []}]),
                {
                    "code": "ACTIVITIES_EMPTY",
                    "severity": "ERROR",
                    "message_id": "ACTIVITIES_FILES_HOLD_NO_RECORDS",
                    "next_action_id": "SELECT_EXPORT_WITH_ACTIVITIES",
                },
            ),
        ):
            with self.subTest(label):
                export = self.root / label
                shutil.copytree(SYNTHETIC_EXPORT, export)
                for path in export.rglob("*summarizedActivities.json"):
                    path.write_text(content, encoding="utf-8")
                status, answer = self.call("/api/check-input", {"input": str(export)})
                self.assertEqual(status, 200)
                self.assertFalse(answer["ready"])
                self.assertEqual(answer["findings"][-1], finding)

    def test_the_input_check_reports_mixed_and_repeated_exports(self) -> None:
        self.start_server(600.0)
        mixed = self.root / "mixed"
        for name, activity_id in (("export-a", "SYNTHETIC-A1"), ("export-b", "SYNTHETIC-B1")):
            fitness = mixed / name / "DI_CONNECT" / "DI-Connect-Fitness"
            fitness.mkdir(parents=True)
            (fitness / "synthetic_summarizedActivities.json").write_text(
                json.dumps(
                    [
                        {
                            "summarizedActivitiesExport": [
                                {
                                    "activityId": activity_id,
                                    "activityType": "running",
                                    "startTimeGmt": 1893456000000,
                                }
                            ]
                        }
                    ]
                ),
                encoding="utf-8",
            )
        status, answer = self.call("/api/check-input", {"input": str(mixed)})
        self.assertEqual(status, 200)
        self.assertEqual(
            self.without_download_time(answer, "newest_file"),
            {
                "ready": False,
                "input_kind": "folder",
                # Mixed Exports are not counted.
                "counts": None,
                # The Exports found, each with the full place to choose it,
                # for the page only (stage B3c).
                "exports_found": [
                    {"place": "export-a", "zip": False, "same_as": None, "path": str(mixed / "export-a")},
                    {"place": "export-b", "zip": False, "same_as": None, "path": str(mixed / "export-b")},
                ],
                "not_readable": None,
                "findings": [
                    {
                        "code": "INPUT_MULTIPLE_EXPORTS",
                        "severity": "ERROR",
                        "message_id": "INPUT_HOLDS_MORE_THAN_ONE_EXPORT",
                        "next_action_id": "SELECT_ONE_EXPORT_OR_USE_SNAPSHOTS",
                    }
                ],
            },
        )
        repeated = self.root / "repeated"
        for name in ("copy-a", "copy-b"):
            shutil.copytree(SYNTHETIC_EXPORT, repeated / name)
        status, answer = self.call("/api/check-input", {"input": str(repeated)})
        self.assertEqual(status, 200)
        self.assertEqual(
            self.without_download_time(answer, "newest_file"),
            {
                "ready": True,
                "input_kind": "folder",
                # One copy of the same Export is read.
                "counts": {
                    "activity_records": 1,
                    "fit_files": 0,
                    "files_read": 1,
                    "files_left_out": 0,
                    "files_not_read": 0,
                },
                "exports_found": [],
                "not_readable": None,
                "findings": [
                    {
                        "code": "INPUT_DUPLICATE_SOURCES",
                        "severity": "WARNING",
                        "message_id": "INPUT_HOLDS_THE_SAME_EXPORT_MORE_THAN_ONCE",
                        "next_action_id": "RUN_ALL",
                    },
                    {
                        "code": "RUN_ALL_NOT_EVALUATED",
                        "severity": "INFO",
                        "message_id": "INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT",
                        "next_action_id": "RUN_ALL",
                    },
                ],
            },
        )
        self.assertNotIn(str(self.root), json.dumps(answer))

    def test_the_exports_found_can_be_chosen_only_in_a_chosen_folder(self) -> None:
        # Stage B3c: in a ZIP file, the page names the Exports found and
        # offers none to choose.
        from tests.test_mixed_and_duplicate_exports import activity, other_export
        from tests.test_zip_input import zip_export

        self.start_server(600.0)
        mixed = self.root / "mixed"
        other_export(mixed / "export-a", activity("A1"))
        other_export(mixed / "export-b", activity("B1"))
        archive = zip_export(mixed, self.root / "mixed.zip")
        status, answer = self.call("/api/check-input", {"input": str(archive)})
        self.assertEqual(status, 200)
        self.assertEqual(
            answer["exports_found"],
            [
                {"place": "export-a", "zip": False, "same_as": None, "path": None},
                {"place": "export-b", "zip": False, "same_as": None, "path": None},
            ],
        )

    def test_a_full_place_is_made_inside_the_chosen_folder_only(self) -> None:
        from garmin_running_data_normalizer.gui.server import _choosable_path

        folder = self.root
        self.assertEqual(_choosable_path(folder, "export-a"), str(folder / "export-a"))
        self.assertEqual(_choosable_path(folder, "inner/export.zip"), str(folder / "inner" / "export.zip"))
        for place in ("", "/export", "../export", "a/../export", "a//b", "./a"):
            with self.subTest(place=place):
                self.assertIsNone(_choosable_path(folder, place))
        self.assertIsNone(_choosable_path(folder / "missing", "export-a"))

    def test_a_name_that_cannot_be_shown_goes_to_the_page_as_none(self) -> None:
        # Stage B3c: the page shows it as a name that cannot be shown, with
        # no button; the counts stay.
        from garmin_running_data_normalizer.gui.server import _exports_found, _not_readable

        found = [
            {"place": "line\nbreak", "zip": False, "same_as": None},
            {"place": "export-b", "zip": True, "same_as": "line\nbreak"},
        ]
        self.assertEqual(
            _exports_found(self.root, found),
            [
                {"place": None, "zip": False, "same_as": None, "path": None},
                {"place": "export-b", "zip": True, "same_as": 0, "path": str(self.root / "export-b")},
            ],
        )
        self.assertEqual(_not_readable(["a\u2028b", "c"]), {"place": None, "more": 1})
        self.assertEqual(_not_readable([]), None)

    def test_a_mix_of_accounts_is_reported_without_their_values(self) -> None:
        self.start_server(600.0)
        accounts = ("9876543210123", "1234509876543")
        mixed = self.root / "accounts"
        fitness = mixed / "DI_CONNECT" / "DI-Connect-Fitness"
        fitness.mkdir(parents=True)
        (fitness / "synthetic_summarizedActivities.json").write_text(
            json.dumps(
                [
                    {
                        "summarizedActivitiesExport": [
                            {
                                "activityId": f"SYNTHETIC-A{index}",
                                "activityType": "running",
                                "startTimeGmt": 1893456000000,
                                "userProfileId": int(account),
                            }
                            for index, account in enumerate(accounts)
                        ]
                    }
                ]
            ),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status, check = self.call("/api/check-input", {"input": str(mixed)})
            self.assertEqual(status, 200)
            self.assertEqual(
                [item["code"] for item in check["findings"]], ["INPUT_MULTIPLE_EXPORTS"]
            )
            # A mix of accounts is not counted (stage B3b).
            self.assertIsNone(check["counts"])
            request = {**self.run_request("accounts-output"), "input": str(mixed)}
            self.assertEqual(self.call("/api/run/start", request)[0], 200)
            answer = self.wait_for_state({"failed"})
        self.assertEqual(answer["error_code"], "INPUT_MULTIPLE_EXPORTS")
        for value in accounts:
            with self.subTest(account=value):
                self.assertNotIn(value, json.dumps(check))
                self.assertNotIn(value, json.dumps(answer))
                self.assertNotIn(value, stdout.getvalue())

    @unittest.skipIf(
        os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
        "permission bits do not stop this user here",
    )
    def test_a_folder_that_cannot_be_opened_is_named_on_the_page_only(self) -> None:
        # The run stops, and the page names the folder; the server's log does
        # not (stage A3d-3a). From stage B3c, the check before the run names
        # it to the page too, as the run does.
        self.start_server(600.0)
        source = self.root / "closed"
        shutil.copytree(SYNTHETIC_EXPORT, source)
        closed = source / "DI-Connect-Fitness" / "synthetic-private-folder"
        closed.mkdir()
        closed.chmod(0o000)
        self.addCleanup(closed.chmod, 0o700)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status, check = self.call("/api/check-input", {"input": str(source)})
            self.assertEqual(status, 200)
            self.assertIn("INPUT_NOT_READABLE", [item["code"] for item in check["findings"]])
            request = {**self.run_request("closed-output"), "input": str(source)}
            self.assertEqual(self.call("/api/run/start", request)[0], 200)
            answer = self.wait_for_state({"failed"})
        self.assertEqual(answer["error_code"], "INPUT_NOT_READABLE")
        self.assertEqual(
            answer["error_detail"],
            {"place": "DI-Connect-Fitness/synthetic-private-folder", "more": 0},
        )
        self.assertEqual(
            check["not_readable"], {"place": "DI-Connect-Fitness/synthetic-private-folder", "more": 0}
        )
        self.assertNotIn("synthetic-private-folder", json.dumps(check["findings"]))
        self.assertNotIn("synthetic-private-folder", stdout.getvalue())

    def test_a_run_blocks_a_second_run_and_shutdown_until_it_ends(self) -> None:
        self.start_server(600.0, runs=stub_manager("wait"))
        status, answer = self.call("/api/run/start", self.run_request())
        self.assertEqual((status, answer["state"]), (200, "running"))
        self.assertEqual(self.call("/api/run/start", self.run_request("second")), (409, {"error": "RUN_ACTIVE"}))
        self.assertEqual(self.call("/api/shutdown", {}), (409, {"error": "RUN_ACTIVE"}))
        self.wait_for_state({"running"})
        self.assertTrue(wait_until(lambda: bool(self.call("/api/run/status", {})[1]["progress"])))
        status, answer = self.call("/api/run/cancel", {})
        self.assertEqual((status, answer["state"]), (200, "cancelling"))
        self.assertEqual(self.wait_for_state({"cancelled"})["staging_folders"], [])
        self.assertEqual(self.call("/api/shutdown", {}), (200, {"status": "stopping"}))
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())

    def test_run_requests_are_checked_before_a_child_starts(self) -> None:
        self.start_server(600.0, runs=stub_manager("wait"))
        for payload, code in (
            ({**self.run_request(), "output_name": ".hidden"}, "OUTPUT_NAME_INVALID"),
            ({**self.run_request(), "output_parent": str(self.root / "missing")}, "OUTPUT_PARENT_NOT_FOUND"),
            ({**self.run_request(), "input": "relative"}, "PATH_NOT_ABSOLUTE"),
        ):
            with self.subTest(code=code):
                self.assertEqual(self.call("/api/run/start", payload), (422, {"error": code}))
        self.assertEqual(self.call("/api/run/status", {}), (200, {"state": "idle"}))

    def test_the_server_stays_up_while_a_run_is_active(self) -> None:
        self.start_server(0.4, runs=stub_manager("wait"))
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        time.sleep(1.5)
        self.assertTrue(self.thread.is_alive())
        self.server.runs.cancel()
        self.thread.join(timeout=30)
        self.assertFalse(self.thread.is_alive())

    def test_stopping_the_server_cancels_an_active_run(self) -> None:
        runs = stub_manager("wait")
        self.start_server(600.0, runs=runs)
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        self.assertTrue(wait_until(lambda: bool(runs.status()["progress"])))
        self.server.shutdown()
        self.thread.join(timeout=30)
        self.assertFalse(self.thread.is_alive())
        # serve_until_stopped records the cancelled run before it returns.
        self.assertFalse(runs.active())
        self.assertEqual(runs.status()["state"], "cancelled")

    def test_child_messages_and_errors_stay_out_of_answers_and_output(self) -> None:
        self.start_server(600.0, runs=stub_manager("noise"))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.call("/api/run/start", self.run_request())
            answer = self.wait_for_state({"failed"})
        self.assertEqual(answer["error_code"], "RUN_ALL_FAILED")
        self.assertNotIn(PRIVATE_TEXT, json.dumps(answer))
        self.assertEqual(stdout.getvalue(), "")

    def test_output_actions_need_a_finished_run(self) -> None:
        self.start_server(600.0, runs=stub_manager("wait"))
        routes = ("/api/check-output", "/api/support-bundle", "/api/open-output")
        for route in routes:
            with self.subTest(route=route, state="idle"):
                self.assertEqual(self.call(route, {"target": "folder"}), (409, {"error": "NO_FINISHED_OUTPUT"}))
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        for route in routes:
            with self.subTest(route=route, state="running"):
                self.assertEqual(self.call(route, {"target": "folder"}), (409, {"error": "NO_FINISHED_OUTPUT"}))
        self.call("/api/run/cancel", {})
        self.wait_for_state({"cancelled"})
        for route in routes:
            with self.subTest(route=route, state="cancelled"):
                self.assertEqual(self.call(route, {"target": "folder"}), (409, {"error": "NO_FINISHED_OUTPUT"}))
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_unexpected_errors_of_checks_and_output_actions_answer_command_failed(self) -> None:
        # The code with which the CLI's commands stop for an unexpected error
        # (stage A5b-2); the server's own errors answer INTERNAL_ERROR.
        self.start_server(600.0, runs=stub_manager("publish-then-wait"))
        unexpected = RuntimeError(str(self.root))
        with patch("garmin_running_data_normalizer.gui.server.doctor_input", side_effect=unexpected):
            self.assertEqual(
                self.call("/api/check-input", {"input": str(SYNTHETIC_EXPORT)}),
                (500, {"error": "COMMAND_FAILED"}),
            )
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        self.assertTrue(wait_until(lambda: (self.parent / "output").is_dir()))
        self.call("/api/run/cancel", {})
        self.wait_for_state({"finished_after_cancel"})
        for route, name in (
            ("/api/check-output", "check_output"),
            ("/api/support-bundle", "make_support_bundle"),
            ("/api/open-output", "open_output"),
        ):
            with self.subTest(route=route), patch(
                f"garmin_running_data_normalizer.gui.server.{name}", side_effect=unexpected
            ):
                self.assertEqual(self.call(route, {"target": "folder"}), (500, {"error": "COMMAND_FAILED"}))
        self.assertEqual(sorted(path.name for path in self.parent.iterdir()), ["output"])

    def test_output_actions_report_an_incomplete_output_by_code(self) -> None:
        # The stub publishes an empty folder, as a run whose cancellation came
        # too late would leave a folder that this server did not check.
        self.start_server(600.0, runs=stub_manager("publish-then-wait"))
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        self.assertTrue(wait_until(lambda: (self.parent / "output").is_dir()))
        self.call("/api/run/cancel", {})
        self.wait_for_state({"finished_after_cancel"})
        self.assertEqual(self.call("/api/check-output", {}), (422, {"error": "HANDOFF_INVALID"}))
        self.assertEqual(
            self.call("/api/support-bundle", {}),
            (422, {"error": "SUPPORT_BUNDLE_AUTHORITY_INVALID"}),
        )
        with patch.object(outputs, "_launch") as launch:
            self.assertEqual(self.call("/api/open-output", {"target": "folder"}), (200, {"status": "opened"}))
            self.assertEqual(
                self.call("/api/open-output", {"target": "start_here"}),
                (422, {"error": "OUTPUT_NOT_AVAILABLE"}),
            )
            for payload in ({}, {"target": "x"}, {"target": str(self.root)}, {"path": str(self.root)}):
                with self.subTest(payload=payload):
                    self.assertEqual(self.call("/api/open-output", payload), (422, {"error": "REQUEST_INVALID"}))
        launch.assert_called_once_with(self.parent / "output", folder=True, reveal=False)
        self.assertEqual(sorted(path.name for path in self.parent.iterdir()), ["output"])

    def test_a_real_run_can_be_checked_bundled_and_opened(self) -> None:
        self.start_server(600.0)
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        self.assertEqual(self.wait_for_state({"finished", "failed"})["state"], "finished")
        output = self.parent / "output"
        status, answer = self.call("/api/check-output", {})
        self.assertEqual(status, 200)
        self.assertEqual(answer, outputs.check_output(output))
        self.assertEqual(answer["doctor"]["usability_scope"], "USABLE_WITH_DISCLOSED_WARNINGS")
        self.assertNotIn(str(SYNTHETIC_EXPORT), json.dumps(answer))
        self.assertNotIn(str(self.root), json.dumps(answer))
        bundle = self.parent / "output-support-bundle.zip"
        self.assertEqual(
            self.call("/api/support-bundle", {}),
            (200, {"path": str(bundle), "member_count": 6, "human_review_required": True}),
        )
        self.assertTrue(bundle.is_file())
        self.assertEqual(self.call("/api/support-bundle", {}), (422, {"error": "SUPPORT_BUNDLE_EXISTS"}))
        with patch.object(outputs, "_launch") as launch:
            self.assertEqual(
                self.call("/api/open-output", {"target": "start_here"}),
                (200, {"status": "opened"}),
            )
            # The bundle that this server made, shown where it is saved; the
            # page sends no place (stage B5a). The run made no pack.
            self.assertEqual(self.call("/api/open-output", {"target": "bundle"}), (200, {"status": "opened"}))
            self.assertEqual(self.call("/api/open-output", {"target": "safe_pack"}), (422, {"error": "OUTPUT_NOT_AVAILABLE"}))
            self.assertEqual(
                self.call("/api/open-output", {"target": "bundle", "path": str(self.root)}),
                (200, {"status": "opened"}),
            )
        self.assertEqual(
            launch.call_args_list,
            [
                call(output / "START_HERE.md", folder=False, reveal=False),
                call(bundle, folder=False, reveal=True),
                call(bundle, folder=False, reveal=True),
            ],
        )
        # In a chosen folder, which the CLI's checks of the place take.
        chosen = self.root / "chosen"
        chosen.mkdir()
        status, answer = self.call("/api/support-bundle", {"folder": str(chosen)})
        self.assertEqual((status, answer["path"]), (200, str(chosen / "output-support-bundle.zip")))
        with patch.object(outputs, "_launch") as launch:
            self.call("/api/open-output", {"target": "bundle"})
        launch.assert_called_once_with(chosen / "output-support-bundle.zip", folder=False, reveal=True)
        for folder, code in (
            (output, "SUPPORT_BUNDLE_INSIDE_OUTPUT"),
            (output / "analysis", "SUPPORT_BUNDLE_INSIDE_OUTPUT"),
            (self.root / "missing", "SUPPORT_BUNDLE_PARENT_NOT_FOUND"),
        ):
            with self.subTest(code=code, folder=folder.name):
                self.assertEqual(self.call("/api/support-bundle", {"folder": str(folder)}), (422, {"error": code}))
        for folder, code in (("relative", "PATH_NOT_ABSOLUTE"), (3, "PATH_INVALID"), ("", "PATH_INVALID")):
            with self.subTest(code=code, folder=folder):
                self.assertEqual(self.call("/api/support-bundle", {"folder": folder}), (422, {"error": code}))
        self.assertFalse((self.root / "missing").exists())

    def test_earlier_outputs_are_chosen_by_their_number_in_a_list(self) -> None:
        # Stage B5b: the outputs that the settings remember, newest first and
        # only those that are there, by their number in the last list given
        # and its mark; and the one before, with the counts that the page
        # compares a run with.
        from garmin_running_data_normalizer.gui import settings as gui_settings
        from garmin_running_data_normalizer.run_all import RUN_ALL_VERSION, run_all

        older, newer = self.parent / "older", self.parent / "newer"
        result = run_all(SYNTHETIC_EXPORT, older, timezone_name="Asia/Tokyo")
        shutil.copytree(older, newer)
        for output in (self.parent / "gone", older, newer):
            self.assertIsNone(gui_settings.remember_run_at(places.settings_file(), output, None))
        self.start_server(600.0)
        status, answer = self.call("/api/outputs", {})
        self.assertEqual(status, 200)
        self.assertEqual(answer["list"], 1)
        self.assertEqual(
            answer["outputs"],
            [{"index": 0, "name": "newer", "path": str(newer)}, {"index": 1, "name": "older", "path": str(older)}],
        )
        families = {family: details["record_count"] for family, details in result["family_results"].items()}
        self.assertEqual(
            answer["previous"],
            {
                "index": 0,
                "name": "newer",
                "families": families,
                "snapshots": False,
                "version": __version__,
                "run_all_version": RUN_ALL_VERSION,
                "timezone": "Asia/Tokyo",
            },
        )
        self.assertEqual(answer["current"], {"version": __version__, "run_all_version": RUN_ALL_VERSION})
        # The check and the Support Bundle of an earlier output.
        earlier = {"output": "earlier", "index": 1, "list": 1}
        self.assertEqual(self.call("/api/check-output", earlier), (200, outputs.check_output(older)))
        self.assertEqual(
            self.call("/api/support-bundle", earlier),
            (200, {"path": str(self.parent / "older-support-bundle.zip"), "member_count": 6, "human_review_required": True}),
        )
        # The same list given again, as to the other tab, keeps its mark, so
        # that the numbers of this one still name the same outputs (stage
        # G3b: the view page is always another tab).
        self.assertEqual(self.call("/api/outputs", {})[1]["list"], 1)
        self.assertEqual(self.call("/api/check-output", earlier), (200, outputs.check_output(older)))
        # A list that changed since makes the numbers of this one refused.
        latest = self.parent / "latest"
        shutil.copytree(older, latest)
        self.assertIsNone(gui_settings.remember_run_at(places.settings_file(), latest, None))
        answer = self.call("/api/outputs", {})[1]
        self.assertEqual((answer["list"], [entry["name"] for entry in answer["outputs"]]), (2, ["latest", "newer", "older"]))
        self.assertEqual(self.call("/api/check-output", earlier), (409, {"error": "OUTPUT_LIST_CHANGED"}))
        for payload in (
            {"output": "earlier", "index": 3, "list": 2},
            {"output": "earlier", "index": "0", "list": 2},
            {"output": "earlier", "index": True, "list": 2},
            {"output": "earlier", "index": 0, "list": None},
            {"output": "another"},
            {"output": ["run"]},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/check-output", payload), (422, {"error": "REQUEST_INVALID"}))
        # A folder that the person chose, which the check takes or refuses.
        self.assertEqual(self.call("/api/check-output", {"output": "chosen", "path": str(newer)}), (200, outputs.check_output(newer)))
        self.assertEqual(self.call("/api/check-output", {"output": "chosen", "path": "relative"}), (422, {"error": "PATH_NOT_ABSOLUTE"}))
        self.assertEqual(self.call("/api/check-output", {"output": "chosen", "path": str(self.root)}), (422, {"error": "HANDOFF_INVALID"}))
        # An output of 1.3, and one that another version made, with that version.
        legacy = self.parent / "legacy"
        shutil.copytree(older, legacy)
        as_v1_3(legacy)
        status, answer = self.call("/api/check-output", {"output": "chosen", "path": str(legacy)})
        self.assertEqual((status, answer["doctor"]["legacy"], answer["doctor"]["product_version"]), (200, True, "1.3.3"))
        other = self.parent / "other"
        shutil.copytree(older, other)
        written = json.loads((other / "run_summary.json").read_text(encoding="utf-8"))["generated_paths"]
        # A version that is not this one: the stable release before it,
        # 2.0.1 (stage E2b, v2.1.0 G6a).
        as_release(other, "2.0.1", tuple(written), RUN_ALL_VERSION)
        chosen = {"output": "chosen", "path": str(other)}
        self.assertEqual(self.call("/api/check-output", chosen), (422, {"error": "OUTPUT_OTHER_VERSION", "version": "2.0.1"}))
        self.assertEqual(self.call("/api/support-bundle", chosen), (422, {"error": "OUTPUT_OTHER_VERSION", "version": "2.0.1"}))
        self.assertFalse((self.parent / "other-support-bundle.zip").exists())
        # Without a run of this launch, its own output is not there.
        self.assertEqual(self.call("/api/check-output", {}), (409, {"error": "NO_FINISHED_OUTPUT"}))
        self.assertEqual(self.call("/api/check-output", {"output": "run"}), (409, {"error": "NO_FINISHED_OUTPUT"}))

    def test_the_output_of_this_launch_is_not_an_earlier_output(self) -> None:
        self.start_server(600.0)
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        self.assertEqual(self.wait_for_state({"finished", "failed"})["state"], "finished")
        # The run remembered its output (stage B4c), which is this launch's.
        answer = self.call("/api/outputs", {})[1]
        self.assertEqual((answer["outputs"], answer["previous"]), ([], None))

    def test_a_real_run_through_the_api_matches_the_cli(self) -> None:
        self.start_server(600.0)
        self.assertEqual(self.call("/api/run/start", self.run_request())[0], 200)
        answer = self.wait_for_state({"finished", "failed"})
        self.assertEqual(answer["state"], "finished")
        self.assertEqual(answer["result"]["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(answer["result"]["families"]["vo2max"]["status"], "SKIPPED_NOT_PRESENT")
        cli_output = self.root / "cli-output"
        self.assertEqual(run_cli("--input", str(SYNTHETIC_EXPORT), "--output", str(cli_output)).returncode, 0)
        self.assertEqual(tree_bytes(self.parent / "output"), tree_bytes(cli_output))



class GuiChooserApiTest(GuiServerTestCase):
    # Stage B3a: small programs stand in for the system's dialogs; no test
    # opens a real one.
    idle_timeout = None

    def call(self, path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        body = json.dumps(payload).encode("utf-8")
        status, _, answer = self.post_api(path, self.api_headers(body), body)
        return status, json.loads(answer)

    def serve(self, *command: str, **options: float) -> None:
        self.start_server(
            600.0, dialogs=Chooser(find_command=lambda kind, platform: list(command), **options)
        )

    def wait_for_answer(self) -> dict[str, object]:
        result: dict[str, object] = {}

        def closed() -> bool:
            nonlocal result
            status, result = self.call("/api/choose/status", {})
            self.assertEqual(status, 200)
            return result["state"] != "open"

        self.assertTrue(wait_until(closed, 30))
        return result

    def test_the_request_returns_at_once_and_the_page_asks_for_the_answer(self) -> None:
        place = os.path.join(os.path.abspath(tempfile.gettempdir()), "選んだ export.zip")
        self.serve(
            sys.executable, "-c", f"import sys, time; time.sleep(0.3); sys.stdout.buffer.write({(place + chr(10)).encode()!r})"
        )
        self.assertEqual(self.call("/api/choose/status", {}), (200, {"state": "idle"}))
        self.assertEqual(self.call("/api/choose", {"kind": "zip"}), (200, {"state": "open"}))
        self.assertEqual(self.wait_for_answer(), {"state": "closed", "path": place})
        # The answer is given once.
        self.assertEqual(self.call("/api/choose/status", {}), (200, {"state": "idle"}))

    def test_requests_that_open_no_dialog_are_refused_with_codes(self) -> None:
        self.serve(sys.executable, "-c", "import time; time.sleep(60)")
        self.assertEqual(self.call("/api/choose", {"kind": "folder"}), (200, {"state": "open"}))
        for payload, answer in (
            ({"kind": "zip"}, (409, {"error": "CHOOSER_BUSY"})),
            ({"kind": "other"}, (422, {"error": "REQUEST_INVALID"})),
            ({}, (422, {"error": "REQUEST_INVALID"})),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/choose", payload), answer)
        self.assertEqual(self.call("/api/choose/status", {}), (200, {"state": "open"}))

    def test_a_system_without_a_dialog_says_so(self) -> None:
        self.start_server(600.0, dialogs=Chooser(find_command=lambda kind, platform: None))
        self.assertEqual(self.call("/api/choose", {"kind": "zip"}), (422, {"error": "CHOOSER_NOT_AVAILABLE"}))

    def test_a_dialog_that_is_still_open_closes_with_the_server(self) -> None:
        started: list[subprocess.Popen[bytes]] = []
        real_popen = subprocess.Popen

        def recording_popen(*arguments: object, **options: object) -> subprocess.Popen[bytes]:
            process = real_popen(*arguments, **options)  # type: ignore[call-overload]
            started.append(process)
            return process

        self.serve(sys.executable, "-c", "import time; time.sleep(60)")
        with patch.object(chooser.subprocess, "Popen", recording_popen):
            self.assertEqual(self.call("/api/choose", {"kind": "zip"}), (200, {"state": "open"}))
        self.server.shutdown()
        self.thread.join(timeout=10)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(len(started), 1)
        self.assertTrue(wait_until(lambda: started[0].poll() is not None, 10))


if __name__ == "__main__":
    unittest.main()
