"""Tests for the SDK transport and authentication."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import Mock

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError

from ttlama_sdk import (
    APIError, AuthenticationError, AuthorizationError, ConflictError, NotFoundError,
    ProvisioningError, TTLLama, ValidationError,
)


def test_login_preserves_csrf_session_and_uses_bearer() -> None:
    """Test that login preserves CSRF token, session, and uses bearer token."""
    client = TTLLama("https://example.test")
    session = Mock()
    session.request.side_effect = [
        Mock(ok=True, status_code=200, json=Mock(return_value={"csrf_token": "csrf"})),
        Mock(ok=True, status_code=200, json=Mock(return_value={"access_token": "token"})),
        Mock(ok=True, status_code=200, json=Mock(return_value={"id": "user"})),
    ]
    client.session = session

    assert client.login("alice", "secret") == "token"
    assert client.request("GET", "/users/me") == {"id": "user"}
    assert session.request.call_args_list[0].args[:2] == ("GET", "https://example.test/api/v1/csrf")
    assert session.request.call_args_list[1].kwargs["headers"] == {"X-CSRFToken": "csrf"}
    assert session.request.call_args_list[2].kwargs["headers"] == {"Authorization": "Bearer token"}


def response(payload: object = None, status: int = 200) -> Mock:
    """Create a mock response with the given payload and status code."""
    return Mock(ok=status < 400, status_code=status, json=Mock(return_value=payload))


def test_missing_csrf_stops_login() -> None:
    """Test that missing CSRF token stops the login process."""
    client = TTLLama("https://example.test")
    client.session = Mock()
    client.session.request.return_value = response({"csrf_token": ""})
    with pytest.raises(APIError):
        client.login("alice", "secret")
    assert client.session.request.call_count == 1
    assert client.token is None


@pytest.mark.parametrize("status,error_type", [
    (400, ValidationError), (401, AuthenticationError), (403, AuthorizationError),
    (404, NotFoundError), (409, ConflictError), (503, ProvisioningError), (500, APIError),
])
def test_http_errors_are_typed_and_do_not_leak_response(
    status: int,
    error_type: type[APIError],
) -> None:
    """Test that HTTP errors are correctly typed and do not leak sensitive response information."""
    client = TTLLama("https://example.test", token="token")
    client.session = Mock()
    client.session.request.return_value = response({"error": "secret", "lease_id": 9}, status)
    with pytest.raises(error_type) as caught:
        client.me.leases.create(1, 2)
    assert caught.value.status_code == status
    assert caught.value.lease_id == 9
    assert "secret" not in str(caught.value)
    assert client.session.request.call_count == 1
    assert client.session.request.call_args.kwargs["timeout"] == 60.0


def test_network_and_non_json_errors() -> None:
    """Test that network errors and non-JSON responses are handled correctly."""
    client = TTLLama("https://example.test")
    client.session = Mock()
    client.session.request.side_effect = RequestsConnectionError("failure")
    with pytest.raises(APIError, match="Unable to reach"):
        client.me.get()
    client.session.request.side_effect = None
    invalid = response()
    invalid.json.side_effect = ValueError("bad JSON")
    client.session.request.return_value = invalid
    with pytest.raises(APIError, match="invalid JSON"):
        client.me.get()


def test_generated_password_and_explicit_password_are_preserved() -> None:
    """Test that generated passwords and explicitly provided passwords are preserved correctly."""
    client = TTLLama("https://example.test", token="token")
    client.session = Mock()
    client.session.request.side_effect = [
        response({"user": {"id": "uuid"}, "generated_password": "generated"}, 201),
        response({"id": "uuid"}, 201),
    ]
    assert client.user.create("alice")["generated_password"] == "generated"
    assert client.user.create("bob", password="password") == {"id": "uuid"}
    assert client.session.request.call_args.kwargs["json"] == {
        "username": "bob", "password": "password",
    }


def test_assignment_and_removal() -> None:
    """Test that profile assignment and removal work correctly."""
    client = TTLLama("https://example.test", token="token")
    client.session = Mock()
    client.session.request.side_effect = [response({"id": 4}), response(status=204)]
    assert client.user.assign_profile("uuid", 3) == {"id": 4}
    assert client.user.unassign_profile("uuid", 3) is None
    assert client.session.request.call_args.args == (
        "DELETE", "https://example.test/api/v1/admin/users/uuid/profiles/3",
    )


def test_oidc_stores_token_only_on_success() -> None:
    """Test that OIDC authentication only stores the token on successful responses."""
    client = TTLLama("https://example.test")
    client.session = Mock()
    client.session.request.side_effect = [
        response({"device_code": "device", "interval": 5}),
        response({"status": "pending"}),
        response({"status": "complete", "access_token": "token", "token_type": "Bearer"}),
        response({"access_token": "ticket-token", "token_type": "Bearer"}),
    ]
    assert client.auth.oidc_device()["device_code"] == "device"
    assert client.auth.oidc_poll("device")["status"] == "pending"
    assert client.token is None
    assert client.auth.oidc_poll("device")["status"] == "complete"
    assert client.token == "token"
    client.auth.oidc_exchange("ticket")
    assert client.token == "ticket-token"
    assert all(not call.kwargs["headers"] for call in client.session.request.call_args_list)


@pytest.mark.parametrize("action", ["logout", "change_password"])
def test_revoking_current_session_forgets_token(action: str) -> None:
    """Test that revoking the current session forgets the token."""
    client = TTLLama("https://example.test", token="token")
    client.session = Mock()
    client.session.request.return_value = response(status=204)
    if action == "logout":
        client.auth.logout()
    else:
        client.me.change_password("old", "new")
    assert client.token is None


@pytest.mark.parametrize(
    "url",
    [
        "example.test",
        "https://user:secret@example.test",
        "https://example.test/path",
    ]
)
def test_rejects_invalid_server_origins(url: str) -> None:
    """Test that invalid server origins are rejected."""
    with pytest.raises(ValueError):
        TTLLama(url)


def test_real_http_session_sends_csrf_cookie_and_bearer() -> None:
    """Test that the real HTTP session sends the CSRF cookie and bearer token correctly."""
    class Handler(BaseHTTPRequestHandler):
        """HTTP request handler for testing CSRF and bearer token behavior."""
        def send_json(
                self,
                status: int,
                payload: dict[str, object],
                *,
                cookie: bool = False,
            ) -> None:
            """Send a JSON response with the given status, payload, and optional cookie."""
            encoded = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            if cookie:
                self.send_header("Set-Cookie", "session=csrf-session; Path=/; HttpOnly")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:   # pylint: disable=C0103
            """Handle GET requests for CSRF token and user info."""
            if self.path == "/api/v1/csrf":
                self.send_json(200, {"csrf_token": "csrf"}, cookie=True)
            elif (
                self.path == "/api/v1/users/me"
                and self.headers.get("Authorization") == "Bearer token"
            ):
                self.send_json(200, {"user": {"username": "alice"}})
            else:
                self.send_json(401, {"error": "unauthorized"})

        def do_POST(self) -> None:   # pylint: disable=C0103
            """Handle POST requests for authentication."""
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size))
            if (self.path == "/api/v1/auth"
                    and self.headers.get("Cookie") == "session=csrf-session"
                    and self.headers.get("X-CSRFToken") == "csrf"
                    and body == {"username": "alice", "password": "password"}):
                self.send_json(200, {"access_token": "token"})
            else:
                self.send_json(400, {"error": "invalid request"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with TTLLama(f"http://127.0.0.1:{server.server_port}") as client:
            assert client.login("alice", "password") == "token"
            assert client.me.get()["user"]["username"] == "alice"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
