"""Local HTTP server for the GUI.

The server listens on 127.0.0.1 only, on a port chosen by the operating
system. It serves the packaged page from a fixed table and answers a small JSON
API. Every API request must carry the per-launch key in the X-Launch-Key
header. The key reaches the page in the URL fragment, which browsers never send
to a server. No cookie is used, because browsers send the cookies of a host to
every port on it, including servers that other programs or accounts run.
"""
from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from .. import __version__
from ..common.time import DEFAULT_TIMEZONE
from ..diagnostics.doctor import DoctorError, doctor_input
from .folders import FolderError, list_folders
from .runs import (
    MAX_TIMEZONE_LENGTH,
    RunActiveError,
    RunManager,
    RunRequestError,
    absolute_path,
)


HOST = "127.0.0.1"
LAUNCH_KEY_HEADER = "X-Launch-Key"
LANGUAGES = ("en", "ja")
# The page sends a heartbeat every 30 seconds. Browsers may slow the timers of
# background tabs to once a minute, so the server waits much longer than that.
IDLE_TIMEOUT_SECONDS = 600.0
MAX_REQUEST_BYTES = 64 * 1024
REQUEST_TIMEOUT_SECONDS = 30.0

# Content types are fixed here instead of coming from mimetypes: Windows can
# map .js to text/plain through the registry, and nosniff then blocks scripts.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
    "/i18n.mjs": ("i18n.mjs", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/i18n/en.json": ("i18n/en.json", "application/json"),
    "/i18n/ja.json": ("i18n/ja.json", "application/json"),
}

SECURITY_HEADERS = (
    (
        "Content-Security-Policy",
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'",
    ),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("Cache-Control", "no-store"),
)

ERROR_CODES = {
    HTTPStatus.BAD_REQUEST: "BAD_REQUEST",
    HTTPStatus.FORBIDDEN: "FORBIDDEN",
    HTTPStatus.NOT_FOUND: "NOT_FOUND",
    HTTPStatus.METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    HTTPStatus.LENGTH_REQUIRED: "LENGTH_REQUIRED",
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: "REQUEST_TOO_LARGE",
    HTTPStatus.REQUEST_URI_TOO_LONG: "URI_TOO_LONG",
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE: "HEADERS_TOO_LARGE",
    HTTPStatus.INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    HTTPStatus.NOT_IMPLEMENTED: "NOT_IMPLEMENTED",
    HTTPStatus.HTTP_VERSION_NOT_SUPPORTED: "HTTP_VERSION_NOT_SUPPORTED",
}

API_ROUTES = {
    "/api/status": "_api_status",
    "/api/heartbeat": "_api_heartbeat",
    "/api/shutdown": "_api_shutdown",
    "/api/folders": "_api_folders",
    "/api/check-input": "_api_check_input",
    "/api/run/start": "_api_run_start",
    "/api/run/status": "_api_run_status",
    "/api/run/cancel": "_api_run_cancel",
}


class ApiError(Exception):
    """An API answer other than 200, given to the page as a short code."""

    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


def load_static_files() -> dict[str, tuple[bytes, str]]:
    """Read every file in STATIC_FILES from the installed package."""
    root = files(__package__).joinpath("static")
    loaded: dict[str, tuple[bytes, str]] = {}
    for url_path, (resource, content_type) in STATIC_FILES.items():
        node = root
        for part in resource.split("/"):
            node = node.joinpath(part)
        loaded[url_path] = (node.read_bytes(), content_type)
    return loaded


def _json_object(body: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


class GuiServer(ThreadingHTTPServer):
    """Serve one GUI launch on 127.0.0.1 with a port chosen by the operating system."""

    daemon_threads = True

    def __init__(
        self,
        *,
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
        runs: RunManager | None = None,
    ) -> None:
        if idle_timeout <= 0:
            raise ValueError("idle_timeout must be positive")
        self.static_files = load_static_files()
        self.runs = runs if runs is not None else RunManager()
        self.launch_key = secrets.token_urlsafe(32)
        self.idle_timeout = idle_timeout
        self._last_request = time.monotonic()
        self._lock = threading.Lock()
        super().__init__((HOST, 0), GuiRequestHandler)
        self.origin = f"http://{HOST}:{self.server_port}"
        self.expected_host = f"{HOST}:{self.server_port}"

    @property
    def url(self) -> str:
        """Return the address to open; the key stays in the fragment."""
        return f"{self.origin}/#key={self.launch_key}"

    def server_bind(self) -> None:
        # Bind without address reuse, and on Windows for exclusive use, so that
        # no other program can listen on the same port. The host name lookup in
        # HTTPServer.server_bind is skipped; the address is always 127.0.0.1.
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        self.server_name = HOST
        self.server_port = self.server_address[1]

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Ignore connection errors; the server writes nothing to the terminal."""

    def record_request(self) -> None:
        with self._lock:
            self._last_request = time.monotonic()

    def idle_seconds(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_request

    def stop_soon(self) -> None:
        """Stop serve_forever from a request thread without waiting for it."""
        threading.Thread(target=self.shutdown, daemon=True).start()


class GuiRequestHandler(BaseHTTPRequestHandler):
    """Answer the requests of one GuiServer; every response has SECURITY_HEADERS."""

    server: GuiServer
    timeout = REQUEST_TIMEOUT_SECONDS
    # An error found before the request line gives a version is answered as
    # HTTP/1.0, so that it also has a status line and SECURITY_HEADERS.
    default_request_version = "HTTP/1.0"

    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        if len(self.requestline.split()) != 3:
            status = HTTPStatus.BAD_REQUEST
        elif self.request_version not in ("HTTP/1.0", "HTTP/1.1"):
            status = HTTPStatus.HTTP_VERSION_NOT_SUPPORTED
        else:
            return True
        # An HTTP/0.9 answer has no status line or headers, so a refused
        # request is always answered as HTTP/1.0.
        self.request_version = self.default_request_version
        self.send_error(status)
        return False

    def log_message(self, format: str, *args: Any) -> None:
        """Write nothing, so that paths and keys never reach the terminal."""

    def end_headers(self) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        super().end_headers()

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        """Answer an error with a short JSON code; request text is never echoed."""
        self._send_json(code, {"error": ERROR_CODES.get(code, "HTTP_ERROR")}, close=True)

    def do_GET(self) -> None:
        if not self._host_allowed():
            self.send_error(HTTPStatus.FORBIDDEN)
        elif self.path in self.server.static_files:
            body, content_type = self.server.static_files[self.path]
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in API_ROUTES:
            self._method_not_allowed("POST")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        body = self._read_body()
        if body is None:
            return
        if not self._host_allowed():
            self.send_error(HTTPStatus.FORBIDDEN)
        elif self.path in self.server.static_files:
            self._method_not_allowed("GET")
        elif self.path not in API_ROUTES:
            self.send_error(HTTPStatus.NOT_FOUND)
        elif not (self._origin_allowed() and self._launch_key_valid()):
            self.send_error(HTTPStatus.FORBIDDEN)
        elif not self._json_content_type():
            self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        else:
            payload = _json_object(body)
            if payload is None:
                self.send_error(HTTPStatus.BAD_REQUEST)
            else:
                self._answer_api(payload)

    def _host_allowed(self) -> bool:
        return self.headers.get_all("Host") == [self.server.expected_host]

    def _origin_allowed(self) -> bool:
        origins = self.headers.get_all("Origin")
        return origins is None or origins == [self.server.origin]

    def _launch_key_valid(self) -> bool:
        values = self.headers.get_all(LAUNCH_KEY_HEADER) or []
        return len(values) == 1 and hmac.compare_digest(
            values[0].encode("utf-8"), self.server.launch_key.encode("ascii")
        )

    def _json_content_type(self) -> bool:
        content_type = self.headers.get("Content-Type") or ""
        return content_type.split(";", 1)[0].strip().lower() == "application/json"

    def _read_body(self) -> bytes | None:
        """Return the request body, or answer the error and return None.

        The body is read before any other check: closing a connection with
        unread data can reset it and cut off the error answer. A body over
        MAX_REQUEST_BYTES is not read, so its sender may see a reset instead of
        413; the page itself sends only small bodies.
        """
        lengths = self.headers.get_all("Content-Length") or []
        if not lengths:
            self.send_error(HTTPStatus.LENGTH_REQUIRED)
            return None
        if len(lengths) != 1 or not (lengths[0].isascii() and lengths[0].isdigit()):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return None
        length = int(lengths[0])
        if length > MAX_REQUEST_BYTES:
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return None
        return self.rfile.read(length)

    def _answer_api(self, payload: dict[str, Any]) -> None:
        self.server.record_request()
        try:
            result = getattr(self, API_ROUTES[self.path])(payload)
        except ApiError as exc:
            self._send_json(exc.status, {"error": exc.code})
            return
        except Exception:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json(HTTPStatus.OK, result)
        if self.path == "/api/shutdown":
            self.server.stop_soon()

    def _api_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"languages": list(LANGUAGES), "product_version": __version__}

    def _api_heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok"}

    def _api_shutdown(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.server.runs.active():
            raise ApiError(HTTPStatus.CONFLICT, "RUN_ACTIVE")
        return {"status": "stopping"}

    def _api_folders(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return list_folders(payload.get("path"))
        except FolderError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc

    def _api_check_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        timezone_name = payload.get("timezone", DEFAULT_TIMEZONE)
        if (
            not isinstance(timezone_name, str)
            or not timezone_name
            or len(timezone_name) > MAX_TIMEZONE_LENGTH
        ):
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "TIMEZONE_INVALID")
        try:
            input_path = absolute_path(payload.get("input"), "INPUT_PATH_INVALID")
            report = doctor_input(input_path, timezone_name=timezone_name)
        except (RunRequestError, DoctorError) as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        findings = [
            {
                "code": finding["code"],
                "severity": finding["severity"],
                "message_id": finding["safe_message_id"],
                "next_action_id": finding["next_action_id"],
            }
            for finding in report["findings"]
        ]
        return {
            "ready": all(finding["severity"] != "ERROR" for finding in findings),
            "findings": findings,
        }

    def _api_run_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.server.runs.start(payload)
        except RunActiveError as exc:
            raise ApiError(HTTPStatus.CONFLICT, exc.code) from exc
        except RunRequestError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        except OSError as exc:
            raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "RUN_START_FAILED") from exc

    def _api_run_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.server.runs.status()

    def _api_run_cancel(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.server.runs.cancel()

    def _method_not_allowed(self, allow: str) -> None:
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {"error": ERROR_CODES[HTTPStatus.METHOD_NOT_ALLOWED]},
            allow=allow,
            close=True,
        )

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        allow: str | None = None,
        close: bool = False,
    ) -> None:
        body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if allow is not None:
            self.send_header("Allow", allow)
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def serve_until_stopped(server: GuiServer, *, poll_interval: float = 0.5) -> None:
    """Serve until Ctrl+C, /api/shutdown, or idle_timeout without an API request.

    The server does not stop for idleness while a run is active, and
    /api/shutdown is refused then. On Ctrl+C an active run is cancelled
    first. The listening socket is closed before this function returns.
    """
    finished = threading.Event()

    def stop_when_idle() -> None:
        check_interval = min(server.idle_timeout / 4, 5.0)
        while not finished.wait(check_interval):
            # A run keeps the server alive even when no page asks for news.
            if server.idle_seconds() > server.idle_timeout and not server.runs.active():
                server.shutdown()
                return

    threading.Thread(target=stop_when_idle, daemon=True).start()
    try:
        server.serve_forever(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass
    finally:
        finished.set()
        server.runs.stop()
        server.server_close()


__all__ = [
    "GuiServer",
    "IDLE_TIMEOUT_SECONDS",
    "LANGUAGES",
    "LAUNCH_KEY_HEADER",
    "STATIC_FILES",
    "load_static_files",
    "serve_until_stopped",
]
