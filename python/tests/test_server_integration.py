"""Optional SDK integration test against the local TTL-LAMa application."""

from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server
from ttlama_sdk import TTLLama

from api.config import DatabaseSettings, FlaskSettings

pytest.importorskip("api.bootstrap", reason="TTL-LAMa server sources are not installed")

from api.bootstrap import create_app    # pylint: disable=C0413



def test_internal_login_user_and_profile_workflow(tmp_path: Path) -> None:
    """Test the internal login, user creation, profile assignment, and user workflow."""
    settings = FlaskSettings.model_validate({
        "AUTH_MODE": "internal",
        "FLASK_ENV": "testing",
        "SECRET_KEY": "test-secret-key-with-more-than-thirty-two-characters",
        "ADMIN_USERNAME": "sdk-admin",
        "ADMIN_PASSWORD": "test-password",
        "ENFORCE_SECURE_CONNECTION": False,
        "SESSION_COOKIE_SECURE": False,
    })
    application = create_app(settings, DatabaseSettings(DB_PATH=str(tmp_path / "sdk.db")))
    application.config["BACKEND_LEASE_TARGETS"] = {"wg0"}
    server = make_server("127.0.0.1", 0, application)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        with TTLLama(url) as admin:
            admin.login("sdk-admin", "test-password")
            created = admin.user.create("sdk-user")
            profile = admin.profile.create(
                "sdk-profile", default_duration="1h", maximum_duration="8h",
                lease_target="wg0", networks=["10.0.0.0/24"],
                address_pools=["10.250.0.0/24"], endpoint="vpn.example.test:51820",
                public_key="server-key",
            )
            assignment = admin.user.assign_profile(created["user"]["id"], profile["id"])
            assert assignment["profile_id"] == profile["id"]
            assert admin.user.get(created["user"]["id"])["username"] == "sdk-user"
            with TTLLama(url) as user:
                user.login("sdk-user", created["generated_password"])
                assert user.me.overview()["profiles"][0]["id"] == profile["id"]
                user.auth.logout()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        application.extensions["database_config"].close()
