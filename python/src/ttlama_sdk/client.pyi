"""Stub for the TTLama SDK client."""
from typing import Any

import requests

from .resources import (
    AdminDevices,
    AdminLeases,
    Auth,
    CurrentUser,
    Profiles,
    Users,
)

class TTLLama:  # pylint: disable=C0115
    timeout: float
    lease_timeout: float
    session: requests.Session
    auth: Auth
    user: Users
    device: AdminDevices
    lease: AdminLeases
    profile: Profiles
    me: CurrentUser

    def __init__(
        self,
        base_url: str, # pylint: disable=W0613
        *,
        token: str | None = None, # pylint: disable=W0613
        timeout: float = 5.0, # pylint: disable=W0613
        lease_timeout: float = 60.0, # pylint: disable=W0613
    ) -> None: ...

    @property
    def token(self) -> str | None: ... # pylint: disable=C0116

    @token.setter
    def token(self, value: str | None) -> None: ... # pylint: disable=W0613

    def close(self) -> None: ... # pylint: disable=C0116
    def __enter__(self) -> TTLLama: ...
    def __exit__(self, *args: object) -> None: ...

    def request( # pylint: disable=C0116
        self,
        method: str, # pylint: disable=W0613
        path: str, # pylint: disable=W0613
        *,
        json: object = None, # pylint: disable=W0613
        params: object = None, # pylint: disable=W0613
        timeout: float | None = None, # pylint: disable=W0613
        authenticated: bool = True, # pylint: disable=W0613
        headers: dict[str, str] | None = None, # pylint: disable=W0613
    ) -> Any: ...

    def login(self, username: str, password: str) -> str: ... # pylint: disable=W0613, C0116
