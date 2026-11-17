"""Tests for the SDK resource methods and their HTTP contracts."""

from collections.abc import Callable
from unittest.mock import Mock

import pytest

from ttlama_sdk import APIError, TTLLama


RESOURCE_CASES: list[tuple[Callable[[TTLLama], object], str, str, object]] = [
    (lambda c: c.auth.csrf(), "GET", "/csrf", {}),
    (lambda c: c.me.get(), "GET", "/users/me", {}),
    (lambda c: c.me.overview(), "GET", "/users/me/overview", {}),
    (lambda c: c.me.devices.list(), "GET", "/users/me/devices", []),
    (lambda c: c.me.devices.get(2), "GET", "/users/me/devices/2", {}),
    (lambda c: c.me.devices.create("name", "key"), "POST", "/users/me/devices", {}),
    (lambda c: c.me.devices.delete(2), "DELETE", "/users/me/devices/2", None),
    (lambda c: c.me.leases.list(), "GET", "/users/me/leases", []),
    (lambda c: c.me.leases.get(2), "GET", "/users/me/leases/2", {}),
    (lambda c: c.me.leases.create(2, 3), "POST", "/users/me/leases", {}),
    (lambda c: c.me.leases.configuration(2), "GET", "/users/me/leases/2/configuration", {}),
    (lambda c: c.me.leases.revoke(2), "POST", "/users/me/leases/2/revoke", {}),
    (lambda c: c.user.list(device=2), "GET", "/admin/users", []),
    (lambda c: c.user.get("uuid"), "GET", "/admin/users/uuid", {}),
    (lambda c: c.user.create("alice"), "POST", "/admin/users", {}),
    (lambda c: c.user.update("uuid", enabled=False), "PATCH", "/admin/users/uuid", {}),
    (lambda c: c.user.delete("uuid"), "DELETE", "/admin/users/uuid", None),
    (lambda c: c.user.profiles("uuid"), "GET", "/admin/users/uuid/profiles", []),
    (lambda c: c.user.assign_profile("uuid", 2), "PUT", "/admin/users/uuid/profiles/2", {}),
    (lambda c: c.user.unassign_profile("uuid", 2), "DELETE", "/admin/users/uuid/profiles/2", None),
    (lambda c: c.device.list(), "GET", "/admin/devices", []),
    (lambda c: c.device.get(2), "GET", "/admin/devices/2", {}),
    (lambda c: c.device.update(2, name="new"), "PATCH", "/admin/devices/2", {}),
    (lambda c: c.device.block(2), "POST", "/admin/devices/2/block", {}),
    (lambda c: c.device.delete(2), "DELETE", "/admin/devices/2", None),
    (lambda c: c.lease.list(), "GET", "/admin/leases", []),
    (lambda c: c.lease.get(2), "GET", "/admin/leases/2", {}),
    (lambda c: c.lease.revoke(2), "POST", "/admin/leases/2/revoke", {}),
    (lambda c: c.profile.list(), "GET", "/admin/profiles", []),
    (lambda c: c.profile.get(2), "GET", "/admin/profiles/2", {}),
    (lambda c: c.profile.create("name", lease_target="wg0"), "POST", "/admin/profiles", {}),
    (lambda c: c.profile.update(2, name="new"), "PATCH", "/admin/profiles/2", {}),
    (lambda c: c.profile.delete(2), "DELETE", "/admin/profiles/2", None),
]


@pytest.mark.parametrize("operation,method,path,result", RESOURCE_CASES)
def test_resource_routes(
    operation: Callable[[TTLLama], object],
    method: str,
    path: str,
    result: object,
) -> None:
    """Test that the resource routes generate the correct HTTP requests."""
    client = TTLLama("https://example.test", token="token")
    request_mock = Mock(return_value=result)
    client.request = request_mock
    assert operation(client) == result
    assert request_mock.call_args.args == (method, path)


def test_list_filters_and_lease_payloads() -> None:
    """Test that list filters and lease payloads are correctly handled."""
    client = TTLLama("https://example.test", lease_timeout=75)
    request_mock = Mock(return_value=[])
    client.request = request_mock
    client.lease.list(status="active", user="uuid")
    assert request_mock.call_args.kwargs["params"] == {"status": "active", "user": "uuid"}
    request_mock.return_value = {"id": 3}
    client.me.leases.create(1, 2, duration="1h")
    assert request_mock.call_args.kwargs == {
        "json": {"device_id": 1, "profile_id": 2, "duration": "1h"}, "timeout": 75,
    }
    client.me.leases.create(1, 2)
    assert "duration" not in request_mock.call_args.kwargs["json"]
    client.lease.revoke(3)
    assert request_mock.call_args.kwargs["timeout"] == 75


def test_invalid_resource_shape() -> None:
    """Test that invalid resource shapes raise APIError."""
    client = TTLLama("https://example.test")
    client.request = Mock(return_value=["not an object"])
    with pytest.raises(APIError, match="invalid list"):
        client.user.list()
    with pytest.raises(APIError, match="invalid object"):
        client.user.get("uuid")
