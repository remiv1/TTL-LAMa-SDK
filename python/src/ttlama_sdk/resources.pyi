"""Stub for the TTLama SDK resources."""
from typing import Any, Protocol
from uuid import UUID

JSONObject = dict[str, Any]
UserID = str | UUID # pylint: disable=C0103

class _TTLLama(Protocol):
    timeout: float
    lease_timeout: float

    @property
    def token(self) -> str | None: ... # pylint: disable=C0116

    @token.setter
    def token(self, value: str | None) -> None: ...

    def request( # pylint: disable=C0116, R0913
        self,
        method: str,
        path: str,
        *,
        json: object = None,
        params: object = None,
        timeout: float | None = None,
        authenticated: bool = True,
        headers: dict[str, str] | None = None,
    ) -> Any: ...

class _Resource:
    def __init__(self, client: _TTLLama) -> None: ... # pylint: disable=W0613

class Auth(_Resource): # pylint: disable=C0115
    def csrf(self) -> JSONObject: ... # pylint: disable=C0116
    def logout(self) -> None: ... # pylint: disable=C0116
    def oidc_exchange(self, ticket: str) -> JSONObject: ... # pylint: disable=C0116, W0613
    def oidc_device(self) -> JSONObject: ... # pylint: disable=C0116
    def oidc_poll(self, device_code: str) -> JSONObject: ... # pylint: disable=C0116, W0613

class Users(_Resource): # pylint: disable=C0115
    def list(self, **filters: Any) -> list[JSONObject]: ... # pylint: disable=C0116, W0613
    def get(self, user_id: UserID) -> JSONObject: ... # pylint: disable=C0116, W0613
    def create(self, username: str, **fields: Any) -> JSONObject: ... # pylint: disable=C0116, W0613
    def update(self, user_id: UserID, **fields: Any) -> JSONObject: ... # pylint: disable=C0116, W0613
    def delete(self, user_id: UserID) -> None: ... # pylint: disable=C0116, W0613
    def profiles(self, user_id: UserID) -> list[JSONObject]: ... # pylint: disable=C0116, W0613
    def assign_profile(self, user_id: UserID, profile_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def unassign_profile(self, user_id: UserID, profile_id: int) -> None: ... # pylint: disable=C0116, W0613

class AdminDevices(_Resource): # pylint: disable=C0115
    def list(self, **filters: Any) -> list[JSONObject]: ... # pylint: disable=C0116, W0613
    def get(self, device_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def update(self, device_id: int, **fields: Any) -> JSONObject: ... # pylint: disable=C0116, W0613
    def block(self, device_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def delete(self, device_id: int) -> None: ... # pylint: disable=C0116, W0613

class AdminLeases(_Resource): # pylint: disable=C0115
    def list(self, **filters: Any) -> list[JSONObject]: ... # pylint: disable=C0116, W0613
    def get(self, lease_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def revoke(self, lease_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613

class Profiles(_Resource): # pylint: disable=C0115
    def list(self, **filters: Any) -> list[JSONObject]: ... # pylint: disable=C0116, W0613
    def get(self, profile_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def create(self, name: str, **policy: Any) -> JSONObject: ... # pylint: disable=C0116, W0613
    def update(self, profile_id: int, **fields: Any) -> JSONObject: ... # pylint: disable=C0116, W0613
    def delete(self, profile_id: int) -> None: ... # pylint: disable=C0116, W0613

class OwnedDevices(_Resource): # pylint: disable=C0115
    def list(self) -> list[JSONObject]: ... # pylint: disable=C0116
    def get(self, device_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def create(self, name: str, public_key: str) -> JSONObject: ... # pylint: disable=C0116, W0613
    def delete(self, device_id: int) -> None: ... # pylint: disable=C0116, W0613

class OwnedLeases(_Resource): # pylint: disable=C0115
    def list(self) -> list[JSONObject]: ... # pylint: disable=C0116
    def get(self, lease_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def create( # pylint: disable=C0116
        self,
        device_id: int, # pylint: disable=W0613
        profile_id: int, # pylint: disable=W0613
        *,
        duration: str | None = None, # pylint: disable=W0613
    ) -> JSONObject: ...
    def configuration(self, lease_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613
    def revoke(self, lease_id: int) -> JSONObject: ... # pylint: disable=C0116, W0613

class CurrentUser(_Resource): # pylint: disable=C0115
    devices: OwnedDevices
    leases: OwnedLeases

    def __init__(self, client: _TTLLama) -> None: ... # pylint: disable=C0116, W0613, W0231
    def get(self) -> JSONObject: ... # pylint: disable=C0116
    def overview(self) -> JSONObject: ... # pylint: disable=C0116
    def change_password(self, current_password: str, new_password: str) -> None: ... # pylint: disable=C0116, W0613
