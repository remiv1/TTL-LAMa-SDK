"""HTTP transport and authentication for the TTL-LAMa API."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlsplit

import requests

from .errors import (
    APIError, AuthenticationError, AuthorizationError, ConflictError,
    NotFoundError, ProvisioningError, ValidationError,
)
from .resources import AdminDevices, AdminLeases, Auth, CurrentUser, Profiles, Users


class TTLLama:
    """A synchronous client for one TTL-LAMa server.

    :param base_url: Server origin, including its scheme and optional port.
    :param token: Optional existing TTL-LAMa Bearer token.
    :param timeout: Default HTTP timeout in seconds.
    :param lease_timeout: HTTP timeout for VPN provisioning operations.
    """

    def __init__(self, base_url: str, *, token: str | None = None,
                 timeout: float = 5.0, lease_timeout: float = 60.0) -> None:
        parts = urlsplit(base_url)
        if (parts.scheme not in {"http", "https"} or not parts.netloc
                or parts.username is not None or parts.password is not None
                or parts.path not in {"", "/"} or parts.query or parts.fragment):
            raise ValueError("base_url must be an HTTP(S) server origin")
        if timeout <= 0 or lease_timeout <= 0:
            raise ValueError("Timeouts must be positive")
        if token is not None and not token.strip():
            raise ValueError("Token must not be empty")
        self._api_url = base_url.rstrip("/") + "/api/v1"
        self._token: str | None = token
        self.timeout = timeout
        self.lease_timeout = lease_timeout
        self.session = requests.Session()
        self.auth = Auth(self)
        self.user = Users(self)
        self.device = AdminDevices(self)
        self.lease = AdminLeases(self)
        self.profile = Profiles(self)
        self.me = CurrentUser(self)

    @property
    def token(self) -> str | None:
        """Return the current Bearer token, if authenticated."""
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        if value is not None and not value.strip():
            raise ValueError("Token must not be empty")
        self._token = value

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> TTLLama:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(self, method: str, path: str, *, json: object = None,
                 params: object = None, timeout: float | None = None,
                 authenticated: bool = True, headers: dict[str, str] | None = None) -> Any:
        """Send an API request and return its decoded JSON or ``None``.

        :param method: HTTP method.
        :param path: Path relative to ``/api/v1``, beginning with ``/``.
        :param json: Optional JSON request body.
        :param params: Optional query parameters.
        :param timeout: Override for the request timeout in seconds.
        :param authenticated: Whether to send the current Bearer token.
        :param headers: Optional additional HTTP headers.
        :returns: The decoded response or ``None`` for HTTP 204.
        :raises APIError: If the request fails or its response is invalid.
        """
        request_headers = dict(headers or {})
        if authenticated and self._token is not None:
            request_headers["Authorization"] = f"Bearer {self._token}"
        try:
            response = self.session.request(
                method, self._api_url + path, json=cast(Any, json), params=cast(Any, params),
                headers=request_headers, timeout=timeout if timeout is not None else self.timeout,
            )
        except requests.RequestException as error:
            raise APIError("Unable to reach the TTL-LAMa API") from error
        if not response.ok:
            lease_id: int | None = None
            try:
                payload: object = response.json()
                if isinstance(payload, dict):
                    error_data = cast(dict[str, object], payload)
                    error_lease_id = error_data.get("lease_id")
                    if isinstance(error_lease_id, int):
                        lease_id = error_lease_id
            except ValueError:
                pass
            error_type = {
                400: ValidationError,
                401: AuthenticationError,
                403: AuthorizationError,
                404: NotFoundError,
                409: ConflictError,
                503: ProvisioningError,
            }.get(response.status_code, APIError)
            raise error_type(f"TTL-LAMa API returned HTTP {response.status_code}",
                             status_code=response.status_code, lease_id=lease_id)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise APIError("TTL-LAMa API returned invalid JSON",
                           status_code=response.status_code) from error

    def login(self, username: str, password: str) -> str:
        """Authenticate internally and store the returned Bearer token.

        :param username: Internal username.
        :param password: Internal password.
        :returns: The session token.
        :raises APIError: If authentication or the API response fails.
        """
        csrf: object = self.request("GET", "/csrf", authenticated=False)
        csrf_token = cast(
            dict[str, object],
            csrf
        ).get("csrf_token") if isinstance(csrf, dict) else None
        if not isinstance(csrf_token, str) or not csrf_token:
            raise APIError("TTL-LAMa API returned an invalid CSRF token")
        payload: object = self.request(
            "POST", "/auth", json={"username": username, "password": password},
            authenticated=False, headers={"X-CSRFToken": csrf_token},
        )
        access_token = cast(
            dict[str, object],
            payload
        ).get("access_token") if isinstance(payload, dict) else None
        if not isinstance(access_token, str) or not access_token:
            raise APIError("TTL-LAMa API returned an invalid access token")
        self._token = access_token
        return access_token
