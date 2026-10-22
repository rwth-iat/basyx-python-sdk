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


SHELL_ID = "https://example.org/Test_AssetAdministrationShell"
IDENTIFICATION_ID = "http://example.org/Submodels/Assets/TestAsset/Identification"
BILL_OF_MATERIAL_ID = "http://example.org/Submodels/Assets/TestAsset/BillOfMaterial"
TEST_SUBMODEL_ID = "https://example.org/Test_Submodel"
ALL_SUBMODEL_IDS = {IDENTIFICATION_ID, BILL_OF_MATERIAL_ID, TEST_SUBMODEL_ID}
# As listed in policy_data/data.json for the viewer
VIEWER_SUBMODEL_IDS = {IDENTIFICATION_ID, TEST_SUBMODEL_ID}

SHELL = _path_id(SHELL_ID)
IDENTIFICATION = _path_id(IDENTIFICATION_ID)
BILL_OF_MATERIAL = _path_id(BILL_OF_MATERIAL_ID)


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


def _request(method: str, raw_path: str, token: str | None = None,
             extra_headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    """Send a request with the path exactly as given (no client-side normalization of '..' or '//')."""
    connection = http.client.HTTPConnection(GATEWAY_URL.hostname or "localhost", GATEWAY_URL.port or 80, timeout=30)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    headers.update(extra_headers or {})
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

    def assertStatus(self, expected: int, method: str, path: str, user: str | None,
                     extra_headers: dict[str, str] | None = None) -> bytes:
        status, body = _request(method, path, self.tokens[user] if user else None, extra_headers)
        self.assertEqual(expected, status, f"{method} {path} as {user}: {body[:200]!r}")
        return body

    def ids(self, path: str, user: str, extra_headers: dict[str, str] | None = None) -> list[str]:
        """Identifiers of the entries of a collection, as the user sees them."""
        payload = json.loads(self.assertStatus(200, "GET", path, user, extra_headers))
        return [entry["id"] if isinstance(entry, dict) and "id" in entry else entry["keys"][-1]["value"]
                for entry in payload["result"]]

    def test_api_requires_token(self) -> None:
        self.assertStatus(401, "GET", f"{API}/shells", None)

    def test_editor_and_admin_see_everything(self) -> None:
        for user in ("editor", "admin"):
            with self.subTest(user=user):
                self.assertIn(SHELL_ID, self.ids(f"{API}/shells", user))
                self.assertEqual(ALL_SUBMODEL_IDS, set(self.ids(f"{API}/submodels", user)))
                shell = json.loads(self.assertStatus(200, "GET", f"{API}/shells/{SHELL}", user))
                self.assertIn(BILL_OF_MATERIAL_ID, [ref["keys"][-1]["value"] for ref in shell["submodels"]])

    def test_viewer_lists_only_visible_shells_and_submodels(self) -> None:
        self.assertEqual([SHELL_ID], self.ids(f"{API}/shells", "viewer"))
        self.assertEqual(VIEWER_SUBMODEL_IDS, set(self.ids(f"{API}/submodels", "viewer")))
        self.assertEqual(VIEWER_SUBMODEL_IDS, set(self.ids(f"{API}/shells/{SHELL}/submodel-refs", "viewer")))

    def test_viewer_sees_no_references_to_hidden_submodels(self) -> None:
        shell = json.loads(self.assertStatus(200, "GET", f"{API}/shells/{SHELL}", "viewer"))
        self.assertEqual(VIEWER_SUBMODEL_IDS, {ref["keys"][-1]["value"] for ref in shell["submodels"]})

    def test_viewer_pages_through_filtered_lists(self) -> None:
        first = json.loads(self.assertStatus(200, "GET", f"{API}/submodels?limit=1", "viewer"))
        self.assertEqual(1, len(first["result"]))
        cursor = first["paging_metadata"]["cursor"]
        second = json.loads(self.assertStatus(200, "GET", f"{API}/submodels?limit=1&cursor={cursor}", "viewer"))
        self.assertEqual(1, len(second["result"]))
        self.assertEqual({}, second["paging_metadata"])
        self.assertEqual(VIEWER_SUBMODEL_IDS, {first["result"][0]["id"], second["result"][0]["id"]})

    def test_viewer_cannot_list_types_without_rules(self) -> None:
        self.assertStatus(403, "GET", f"{API}/concept-descriptions", "viewer")

    def test_forged_claims_header_grants_nothing(self) -> None:
        # The response filter trusts the JWT payload Envoy forwards in x-jwt-payload; a client-supplied header with
        # that name must not let a viewer act as admin.
        forged = base64.urlsafe_b64encode(json.dumps({"realm_access": {"roles": ["admin"]}}).encode()).decode()
        headers = {"x-jwt-payload": forged.rstrip("=")}
        self.assertEqual(VIEWER_SUBMODEL_IDS, set(self.ids(f"{API}/submodels", "viewer", headers)))
        self.assertStatus(403, "GET", f"{API}/submodels/{BILL_OF_MATERIAL}", "viewer", headers)
        self.assertStatus(403, "DELETE", f"{API}/shells/{SHELL}", "viewer", headers)

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
            f"{API}/shells/{SHELL}/..",  # normalized to ".../shells/", which is not the (exact) collection path
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
