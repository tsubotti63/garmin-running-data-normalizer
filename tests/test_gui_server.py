from __future__ import annotations

import contextlib
import http.client
import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from collections.abc import Iterable
from pathlib import Path
from unittest.mock import patch

from garmin_running_data_normalizer import __version__
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
    "/i18n.mjs": "text/javascript; charset=utf-8",
    "/styles.css": "text/css; charset=utf-8",
    "/i18n/en.json": "application/json",
    "/i18n/ja.json": "application/json",
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

    def start_server(self, idle_timeout: float, runs: RunManager | None = None) -> None:
        self.server = GuiServer(idle_timeout=idle_timeout, runs=runs)
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

        status, _, body = self.post_api("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(body), {"languages": ["en", "ja"], "product_version": __version__}
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

        for body in (b"", b"not json", b"[]", b'"text"', b"\xff\xfe"):
            with self.subTest(body=body):
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

    def test_the_input_check_returns_codes_only(self) -> None:
        self.start_server(600.0)
        status, answer = self.call("/api/check-input", {"input": str(SYNTHETIC_EXPORT)})
        self.assertEqual(status, 200)
        self.assertEqual(
            answer,
            {
                "ready": True,
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
        self.assertNotIn(str(self.root), json.dumps(answer))
        for payload, code in (
            ({"input": "relative"}, "PATH_NOT_ABSOLUTE"),
            ({"input": str(SYNTHETIC_EXPORT), "timezone": "Not/A_Zone"}, "TIMEZONE_INVALID"),
            ({"input": str(SYNTHETIC_EXPORT), "timezone": 5}, "TIMEZONE_INVALID"),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.call("/api/check-input", payload), (422, {"error": code}))

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
        self.assertFalse(runs.active())
        self.assertTrue(wait_until(lambda: runs.status()["state"] == "cancelled", 10.0))

    def test_child_messages_and_errors_stay_out_of_answers_and_output(self) -> None:
        self.start_server(600.0, runs=stub_manager("noise"))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.call("/api/run/start", self.run_request())
            answer = self.wait_for_state({"failed"})
        self.assertEqual(answer["error_code"], "RUN_ALL_FAILED")
        self.assertNotIn(PRIVATE_TEXT, json.dumps(answer))
        self.assertEqual(stdout.getvalue(), "")

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


if __name__ == "__main__":
    unittest.main()
