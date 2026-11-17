"""Exercise the SDK against isolated TTL-LAMa, WireGuard and Dex services."""

import base64
import os
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import pytest
import requests

from ttlama_sdk import ConflictError, TTLLama, ValidationError

_REQUIRED_ENVIRONMENT = (
    "TTLAMA_TEST_SERVER_URL",
    "TTLAMA_TEST_ADMIN_USERNAME",
    "TTLAMA_TEST_ADMIN_PASSWORD",
    "TTLAMA_TEST_OIDC_SERVER_URL",
    "TTLAMA_TEST_OIDC_USERNAME",
    "TTLAMA_TEST_OIDC_PASSWORD",
)
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(name) for name in _REQUIRED_ENVIRONMENT),
    reason="Integration tests require the SDK Compose environment",
)


class _Forms(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form":
            self.current = {"action": attributes.get("action") or ""}
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            name = attributes.get("name")
            if name:
                self.current[name] = attributes.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.current = None


def _forms(response: requests.Response) -> list[dict[str, str]]:
    response.raise_for_status()
    parser = _Forms()
    parser.feed(response.text)
    return parser.forms


@pytest.fixture
def server_url() -> str:
    """Return the internal-auth test server URL."""
    return os.environ["TTLAMA_TEST_SERVER_URL"]


def test_wireguard_lease_lifecycle(server_url: str) -> None:    # pylint: disable=W0621
    """Create and revoke an actual WireGuard lease through the SDK."""
    username = f"sdk-user-{uuid4().hex[:12]}"
    password = "sdk-integration-user-password"
    public_key = base64.b64encode(os.urandom(32)).decode("ascii")
    with TTLLama(server_url) as admin:
        admin.login(os.environ["TTLAMA_TEST_ADMIN_USERNAME"],
                    os.environ["TTLAMA_TEST_ADMIN_PASSWORD"])
        user = admin.user.create(username, password=password)
        profile = next(profile for profile in admin.profile.list()
                       if profile["name"] == "Administrator")
        admin.user.assign_profile(user["id"], profile["id"])

        with TTLLama(server_url) as client:
            client.login(username, password)
            device = client.me.devices.create("sdk-test-device", public_key)
            lease = client.me.leases.create(device["id"], profile["id"], duration="1h")
            assert lease["status"] == "active"
            configuration = client.me.leases.configuration(lease["id"])
            assert configuration["device_public_key"] == public_key
            assert configuration["active_lease_ids"] == [lease["id"]]
            assert configuration["addresses"]
            assert configuration["allowed_ips"]
            assert "REPLACE_WITH_LOCAL_PRIVATE_KEY" in configuration["configuration_template"]
            assert client.me.leases.revoke(lease["id"])["status"] == "revoked"
            with pytest.raises(ConflictError):
                client.me.leases.configuration(lease["id"])
            client.me.devices.delete(device["id"])
            client.auth.logout()
        admin.user.delete(user["id"])


def test_oidc_device_authorization_with_dex() -> None:
    """Complete real Dex device authorization and create an SDK session."""
    with TTLLama(os.environ["TTLAMA_TEST_OIDC_SERVER_URL"]) as client:
        device = client.auth.oidc_device()
        assert device["device_code"]
        assert device["user_code"]
        assert device["verification_uri"]
        assert device["interval"] > 0
        poll_started = time.monotonic()
        assert client.auth.oidc_poll(device["device_code"])["status"] == "pending"
        assert client.token is None
        with pytest.raises(ValidationError):
            client.auth.oidc_poll("")

        with requests.Session() as browser:
            page = browser.get(device["verification_uri_complete"], timeout=10)
            form = _forms(page)[0]
            page = browser.post(urljoin(page.url, form["action"]),
                                data={"user_code": device["user_code"]}, timeout=10)
            form = _forms(page)[0]
            page = browser.post(urljoin(page.url, form["action"]), data={
                "login": os.environ["TTLAMA_TEST_OIDC_USERNAME"],
                "password": os.environ["TTLAMA_TEST_OIDC_PASSWORD"],
            }, timeout=10)
            approval_forms = [form for form in _forms(page) if form.get("approval") == "approve"]
            if approval_forms:
                form = approval_forms[0]
                action = form.pop("action")
                page = browser.post(urljoin(page.url, action or page.url), data=form, timeout=10)
                page.raise_for_status()
            assert urlsplit(page.url).path == "/dex/device/callback"

        time.sleep(max(0, device["interval"] - (time.monotonic() - poll_started)))
        result = client.auth.oidc_poll(device["device_code"])
        assert result["status"] == "complete"
        assert client.token
        assert client.me.get()["user"]["username"] == "admin"
        client.auth.logout()
