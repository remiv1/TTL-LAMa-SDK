"""Resource operations for the TTL-LAMa API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from urllib.parse import quote
from uuid import UUID

from .errors import APIError

if TYPE_CHECKING:
    from .client import TTLLama

JSONObject = dict[str, Any]
UserID = str | UUID


def _id(value: str | int | UUID) -> str:
    return quote(str(value), safe="")


class _Resource:
    def __init__(self, client: TTLLama) -> None:
        self._client = client

    def _object(self, method: str, path: str, **kwargs: Any) -> JSONObject:
        result = self._client.request(method, path, **kwargs)
        if not isinstance(result, dict):
            raise APIError("TTL-LAMa API returned an invalid object")
        return cast(JSONObject, result)

    def _list(self, path: str, **params: Any) -> list[JSONObject]:
        result = self._client.request("GET", path, params=params)
        if not isinstance(result, list):
            raise APIError("TTL-LAMa API returned an invalid list")
        items = cast(list[object], result)
        if any(not isinstance(item, dict) for item in items):
            raise APIError("TTL-LAMa API returned an invalid list")
        return cast(list[JSONObject], items)


class Auth(_Resource):
    """Authentication and OIDC operations."""

    def csrf(self) -> JSONObject:
        """Get a CSRF token and retain its associated session cookie."""
        return self._object("GET", "/csrf", authenticated=False)

    def logout(self) -> None:
        """Revoke the current session and forget its token on success."""
        self._client.request("POST", "/auth/logout")
        self._client.token = None

    def oidc_exchange(self, ticket: str) -> JSONObject:
        """Exchange a single-use OIDC ticket and store the returned token."""
        result = self._object("POST", "/auth/oidc/exchange", json={"ticket": ticket},
                              authenticated=False)
        self._save_token(result)
        return result

    def oidc_device(self) -> JSONObject:
        """Start OIDC device authorization."""
        return self._object("POST", "/auth/oidc/device", json={}, authenticated=False)

    def oidc_poll(self, device_code: str) -> JSONObject:
        """Poll device authorization and store the token upon completion."""
        result = self._object("POST", "/auth/oidc/device/poll",
                              json={"device_code": device_code}, authenticated=False)
        if result.get("status") == "complete":
            self._save_token(result)
        return result

    def _save_token(self, result: JSONObject) -> None:
        token = result.get("access_token")
        if not isinstance(token, str) or not token:
            raise APIError("TTL-LAMa API returned an invalid access token")
        self._client.token = token


class Users(_Resource):
    """Administrative user operations."""

    def list(self, **filters: Any) -> list[JSONObject]:
        """List users using optional relationship filters."""
        return self._list("/admin/users", **filters)

    def get(self, user_id: UserID) -> JSONObject:
        """Get a user by UUID."""
        return self._object("GET", f"/admin/users/{_id(user_id)}")

    def create(self, username: str, **fields: Any) -> JSONObject:
        """Create a user; preserve any generated password in the response."""
        return self._object("POST", "/admin/users", json={"username": username, **fields})

    def update(self, user_id: UserID, **fields: Any) -> JSONObject:
        """Update the supplied user fields."""
        return self._object("PATCH", f"/admin/users/{_id(user_id)}", json=fields)

    def delete(self, user_id: UserID) -> None:
        """Disable a user and revoke dependent access."""
        self._client.request("DELETE", f"/admin/users/{_id(user_id)}")

    def profiles(self, user_id: UserID) -> list[JSONObject]:
        """List profiles assigned to the user."""
        return self._list(f"/admin/users/{_id(user_id)}/profiles")

    def assign_profile(self, user_id: UserID, profile_id: int) -> JSONObject:
        """Assign a profile to a user."""
        return self._object("PUT", f"/admin/users/{_id(user_id)}/profiles/{_id(profile_id)}")

    def unassign_profile(self, user_id: UserID, profile_id: int) -> None:
        """Remove an assignment and revoke its leases."""
        self._client.request("DELETE", f"/admin/users/{_id(user_id)}/profiles/{_id(profile_id)}")


class AdminDevices(_Resource):
    """Administrative device operations."""

    def list(self, **filters: Any) -> list[JSONObject]:
        """List devices using optional relationship filters."""
        return self._list("/admin/devices", **filters)

    def get(self, device_id: int) -> JSONObject:
        """Get a device."""
        return self._object("GET", f"/admin/devices/{_id(device_id)}")

    def update(self, device_id: int, **fields: Any) -> JSONObject:
        """Update a device name or public key."""
        return self._object("PATCH", f"/admin/devices/{_id(device_id)}", json=fields)

    def block(self, device_id: int) -> JSONObject:
        """Block a device and revoke its leases."""
        return self._object("POST", f"/admin/devices/{_id(device_id)}/block")

    def delete(self, device_id: int) -> None:
        """Revoke a device."""
        self._client.request("DELETE", f"/admin/devices/{_id(device_id)}")


class AdminLeases(_Resource):
    """Administrative lease operations."""

    def list(self, **filters: Any) -> list[JSONObject]:
        """List leases using optional filters."""
        return self._list("/admin/leases", **filters)

    def get(self, lease_id: int) -> JSONObject:
        """Get a lease."""
        return self._object("GET", f"/admin/leases/{_id(lease_id)}")

    def revoke(self, lease_id: int) -> JSONObject:
        """Revoke a lease and wait for VPN confirmation."""
        return self._object("POST", f"/admin/leases/{_id(lease_id)}/revoke",
                            timeout=self._client.lease_timeout)


class Profiles(_Resource):
    """Administrative access profile operations."""

    def list(self, **filters: Any) -> list[JSONObject]:
        """List profiles using optional relationship filters."""
        return self._list("/admin/profiles", **filters)

    def get(self, profile_id: int) -> JSONObject:
        """Get a profile and its policy."""
        return self._object("GET", f"/admin/profiles/{_id(profile_id)}")

    def create(self, name: str, **policy: Any) -> JSONObject:
        """Create a profile with its complete policy."""
        return self._object("POST", "/admin/profiles", json={"name": name, **policy})

    def update(self, profile_id: int, **fields: Any) -> JSONObject:
        """Update a profile or its policy."""
        return self._object("PATCH", f"/admin/profiles/{_id(profile_id)}", json=fields)

    def delete(self, profile_id: int) -> None:
        """Revoke a profile and dependent access."""
        self._client.request("DELETE", f"/admin/profiles/{_id(profile_id)}")


class OwnedDevices(_Resource):
    """Devices belonging to the authenticated user."""

    def list(self) -> list[JSONObject]:
        """List owned devices."""
        return self._list("/users/me/devices")

    def get(self, device_id: int) -> JSONObject:
        """Get an owned device."""
        return self._object("GET", f"/users/me/devices/{_id(device_id)}")

    def create(self, name: str, public_key: str) -> JSONObject:
        """Register a device using its public key only."""
        return self._object(
            "POST",
            "/users/me/devices",
            json={
                "name": name,
                "public_key": public_key,
            },
        )

    def delete(self, device_id: int) -> None:
        """Revoke an owned device and its leases."""
        self._client.request("DELETE", f"/users/me/devices/{_id(device_id)}")


class OwnedLeases(_Resource):
    """Leases belonging to the authenticated user."""

    def list(self) -> list[JSONObject]:
        """List owned leases."""
        return self._list("/users/me/leases")

    def get(self, lease_id: int) -> JSONObject:
        """Get an owned lease."""
        return self._object("GET", f"/users/me/leases/{_id(lease_id)}")

    def create(self, device_id: int, profile_id: int, *, duration: str | None = None) -> JSONObject:
        """Create a lease and wait for VPN confirmation."""
        payload: JSONObject = {"device_id": device_id, "profile_id": profile_id}
        if duration is not None:
            payload["duration"] = duration
        return self._object("POST", "/users/me/leases", json=payload,
                            timeout=self._client.lease_timeout)

    def configuration(self, lease_id: int) -> JSONObject:
        """Get public WireGuard parameters for an active lease."""
        return self._object("GET", f"/users/me/leases/{_id(lease_id)}/configuration")

    def revoke(self, lease_id: int) -> JSONObject:
        """Revoke an owned lease and wait for VPN confirmation."""
        return self._object("POST", f"/users/me/leases/{_id(lease_id)}/revoke",
                            timeout=self._client.lease_timeout)


class CurrentUser(_Resource):
    """Account and resources of the authenticated user."""

    def __init__(self, client: TTLLama) -> None:
        super().__init__(client)
        self.devices = OwnedDevices(client)
        self.leases = OwnedLeases(client)

    def get(self) -> JSONObject:
        """Get the authenticated identity and session expirations."""
        return self._object("GET", "/users/me")

    def overview(self) -> JSONObject:
        """Get the authenticated identity and its resources."""
        return self._object("GET", "/users/me/overview")

    def change_password(self, current_password: str, new_password: str) -> None:
        """Change the internal password and forget the revoked session token."""
        self._client.request("PATCH", "/users/me/password", json={
            "current_password": current_password, "new_password": new_password,
        })
        self._client.token = None
