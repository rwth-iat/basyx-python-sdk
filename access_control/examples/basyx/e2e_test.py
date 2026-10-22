# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
End-to-end tests for the secured BaSyx stack.

The tests talk to a running stack (``docker compose up``) through Envoy, exactly like a client would. They only send
requests that read data or are expected to be denied, so the example data stays unchanged.

Run from this directory, with the stack running::

    python -m unittest e2e_test -v

The endpoints are read from the ``.env`` file next to this test, the same file Docker Compose uses. Environment
variables of the same name take precedence.
"""
import base64
import http.client
import json
import os
import re
import socket
import time
import unittest
import urllib.parse
import urllib.request


def _load_settings() -> dict[str, str]:
    """Read KEY=VALUE lines of .env, expanding ${OTHER} like Docker Compose does; the environment wins."""
    settings: dict[str, str] = {}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            settings[key] = re.sub(r"\$\{(\w+)\}", lambda match: settings.get(match.group(1), ""), value)
    settings.update({key: value for key, value in os.environ.items() if key in settings})
    return settings


SETTINGS = _load_settings()
GATEWAY_URL = urllib.parse.urlsplit(SETTINGS["PUBLIC_URL"])
TOKEN_URL = f"{SETTINGS['OIDC_ISSUER']}/protocol/openid-connect/token"
API = f"/repository/api/{SETTINGS['API_VERSION']}"


def _path_id(identifier: str) -> str:
    return base64.urlsafe_b64encode(identifier.encode()).decode().rstrip("=")


SHELL = _path_id("https://example.org/Test_AssetAdministrationShell")
IDENTIFICATION = _path_id("http://example.org/Submodels/Assets/TestAsset/Identification")
BILL_OF_MATERIAL = _path_id("http://example.org/Submodels/Assets/TestAsset/BillOfMaterial")


def _token(user: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "password", "client_id": SETTINGS["OIDC_CLIENT_ID"], "username": user, "password": user,
    }).encode()
    last_error: Exception | None = None
    for _ in range(30):  # Keycloak needs some seconds after start-up
        try:
            with urllib.request.urlopen(TOKEN_URL, data=body, timeout=5) as response:
                return str(json.load(response)["access_token"])
        except OSError as error:
            last_error = error
            time.sleep(2)
    raise RuntimeError(f"Could not get a token from {TOKEN_URL}; is the stack running?") from last_error


def _request(method: str, raw_path: str, token: str | None = None) -> tuple[int, bytes]:
    """Send a request with the path exactly as given (no client-side normalization of '..' or '//')."""
    connection = http.client.HTTPConnection(GATEWAY_URL.hostname or "localhost", GATEWAY_URL.port or 80, timeout=10)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        connection.request(method, raw_path, headers=headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


class SecuredStackTest(unittest.TestCase):
    tokens: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = {user: _token(user) for user in ("viewer", "editor", "admin")}

    def assertStatus(self, expected: int, method: str, path: str, user: str | None) -> bytes:
        status, body = _request(method, path, self.tokens[user] if user else None)
        self.assertEqual(expected, status, f"{method} {path} as {user}: {body[:200]!r}")
        return body

    def test_api_requires_token(self) -> None:
        self.assertStatus(401, "GET", f"{API}/shells", None)

    def test_editor_and_admin_can_list_shells(self) -> None:
        for user in ("editor", "admin"):
            with self.subTest(user=user):
                body = self.assertStatus(200, "GET", f"{API}/shells", user)
                ids = [shell["id"] for shell in json.loads(body)["result"]]
                self.assertIn("https://example.org/Test_AssetAdministrationShell", ids)

    def test_viewer_cannot_list_shells(self) -> None:
        self.assertStatus(403, "GET", f"{API}/shells", "viewer")

    def test_viewer_reads_only_listed_objects(self) -> None:
        self.assertStatus(200, "GET", f"{API}/shells/{SHELL}", "viewer")
        self.assertStatus(200, "GET", f"{API}/submodels/{IDENTIFICATION}", "viewer")
        self.assertStatus(403, "GET", f"{API}/submodels/{BILL_OF_MATERIAL}", "viewer")

    def test_editor_cannot_delete(self) -> None:
        self.assertStatus(403, "DELETE", f"{API}/shells/{SHELL}", "editor")

    def test_path_bypasses_are_blocked(self) -> None:
        # Each of these returned the foreign object or the full list before Envoy normalized paths.
        blocked = [
            f"{API}/shells/{SHELL}/../../submodels/{BILL_OF_MATERIAL}",
            f"{API}/shells/{SHELL}/..",
            f"{API}/shells/{SHELL}/%2e%2e/%2e%2e/submodels/{BILL_OF_MATERIAL}",
            f"{API.replace('/repository/', '/repository//')}/submodels/{BILL_OF_MATERIAL}",
            f"{API}/submodels/{BILL_OF_MATERIAL}/",
        ]
        for path in blocked:
            with self.subTest(path=path):
                self.assertStatus(403, "GET", path, "viewer")
        with self.subTest(path="encoded slash"):
            self.assertStatus(400, "GET", f"{API}/shells/{SHELL}%2F..%2F..%2Fsubmodels%2F{BILL_OF_MATERIAL}", "viewer")

    def test_opa_is_not_published(self) -> None:
        for port in (8181, 9191, 9901):
            with self.subTest(port=port):
                with self.assertRaises(OSError):
                    socket.create_connection((GATEWAY_URL.hostname or "localhost", port), timeout=2).close()


if __name__ == "__main__":
    unittest.main()
