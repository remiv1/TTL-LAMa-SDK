# TTL-LAMa Python SDK

This synchronous client supports TTL-LAMa API v1 authentication, users, devices, profiles and leases. It does not depend on the CLI. Global configuration and web routes are outside its scope.

See [README.fr.md](README.fr.md) for the French guide.

## Install

Use Python 3.12 or newer in a virtual environment:

```sh
python -m pip install ./sdk/python
```

From the SDK repository root, install the development dependencies with `python -m pip install -e './python[test]'` and run `python -m pytest python/tests`.

## Usage

```python
from getpass import getpass
from ttlama_sdk import TTLLama

with TTLLama("https://ttl-lama.example") as ttl:
    ttl.login("admin", getpass("Password: "))
    user = ttl.user.get("USER_UUID")
    ttl.user.assign_profile(user["id"], 1)
    ttl.auth.logout()
```

Alternatively, pass an existing token with `TTLLama(url, token=token)`. Internal login handles the CSRF token and associated cookie, then uses a Bearer token. The token remains in memory and is available as `ttl.token`; callers must keep it secret. Closing the client does not revoke the session. Logout revokes the current session; changing the password revokes all of the user's sessions.

Administrator operations are available on `ttl.user`, `ttl.device`, `ttl.lease`, and `ttl.profile`. The current user's account and resources are available on `ttl.me`, `ttl.me.devices`, and `ttl.me.leases`. List methods accept API filters as keyword arguments. Create and update methods accept API fields as keyword arguments. Results are JSON dictionaries or lists, and `204` responses return `None`. User creation without a supplied password in internal mode returns `user` and `generated_password`; an explicitly supplied password is not returned.

For OIDC device authorization, use `ttl.auth.oidc_device()` and poll with `ttl.auth.oidc_poll(device_code)` at the provider's interval. Increase the interval for `slow_down`; `denied` and `expired` end the flow. A completed poll stores the token automatically. `ttl.auth.oidc_exchange(ticket)` exchanges a one-time CLI ticket. The application is responsible for displaying the user code and verification URL, opening a browser if needed, and polling.

Register only the client's WireGuard public key. Keep the private key local and fill the returned configuration template locally. Destination filtering by profile requires appropriate external network configuration.

Errors inherit from `TTLamaError`. `APIError` exposes `status_code` and an optional `lease_id`; HTTP 400, 401, 403, 404, 409 and 503 map to `ValidationError`, `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ConflictError` and `ProvisioningError`. Default timeouts are 5 seconds for ordinary requests and 60 seconds for lease provisioning; configure them using `timeout` and `lease_timeout`. Mutations are never retried automatically: after a timeout or `503`, inspect the lease state before retrying.
