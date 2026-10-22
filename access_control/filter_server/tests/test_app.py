# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import base64
import json
import unittest
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

import urllib3
from access_filter.app import AccessFilter, UpstreamResponse
from access_filter.config import Settings
from werkzeug.test import Client

OPA_URL = "http://opa/v1/data/envoy/authz/response_filter"
REPOSITORY = "http://repository"
API = "/repository/api/v3.1"
SETTINGS = Settings(upstreams={"/repository": REPOSITORY}, opa_url=OPA_URL, upstream_page_size=2, max_items=10)


def shell(identifier: str, *submodels: str) -> dict[str, Any]:
    return {"id": identifier, "submodels": [
        {"type": "ModelReference", "keys": [{"type": "Submodel", "value": submodel}]} for submodel in submodels
    ]}


def claims_header(claims: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")


class FakeTransport:
    """Plays the AAS server (pages of shells) and OPA (a viewer who may see some identifiers)."""

    def __init__(self, shells: list[dict[str, Any]], visible: set[str], unfiltered_roles: set[str]) -> None:
        self.shells = shells
        self.visible = visible
        self.unfiltered_roles = unfiltered_roles
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.opa_inputs: list[dict[str, Any]] = []
        self.opa: Callable[[dict[str, Any]], UpstreamResponse] = self._opa

    def request(self, method: str, url: str, headers: dict[str, str], body: bytes | None,
                timeout: float) -> UpstreamResponse:
        self.calls.append((method, url, headers))
        if url == OPA_URL:
            query = json.loads(body or b"{}")
            self.opa_inputs.append(query["input"])
            return self.opa(query["input"])
        return self._server(url)

    def _opa(self, opa_input: dict[str, Any]) -> UpstreamResponse:
        claims = opa_input["attributes"]["metadataContext"]["filterMetadata"]["envoy.filters.http.jwt_authn"][
            "jwt_payload"]
        roles = set(claims.get("realm_access", {}).get("roles", []))
        result = {
            "unfiltered": bool(roles & self.unfiltered_roles),
            "visible": [item for item in opa_input["items"] if "viewer" in roles and item["id"] in self.visible],
        }
        return json_response({"result": result})

    def _server(self, url: str) -> UpstreamResponse:
        parts = urlsplit(url)
        if parts.path == f"{API}/shells":
            query = parse_qs(parts.query)
            start = int(query.get("cursor", ["0"])[0])
            limit = int(query.get("limit", [str(len(self.shells))])[0])
            page = self.shells[start:start + limit]
            paging = {"cursor": str(start + limit)} if start + limit < len(self.shells) else {}
            return json_response({"paging_metadata": paging, "result": page})
        if parts.path.startswith(f"{API}/shells/"):
            return json_response(self.shells[0])
        if parts.path == f"{API}/thumbnail":
            return UpstreamResponse(200, [("Content-Type", "image/png")], b"\x89PNG")
        return json_response({"messages": [{"text": "not found"}]}, 404)


def json_response(payload: Any, status: int = 200) -> UpstreamResponse:
    return UpstreamResponse(status, [("Content-Type", "application/json")], json.dumps(payload).encode())


VIEWER = {"x-jwt-payload": claims_header({"realm_access": {"roles": ["viewer"]}})}
EDITOR = {"x-jwt-payload": claims_header({"realm_access": {"roles": ["editor"]}})}


class AccessFilterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.shells = [shell(f"urn:aas:{i}", f"urn:sm:{i}") for i in range(5)]
        self.transport = FakeTransport(self.shells, visible={"urn:aas:1", "urn:aas:3", "urn:aas:4", "urn:sm:3"},
                                       unfiltered_roles={"editor"})
        self.client = Client(AccessFilter(SETTINGS, self.transport))

    def get(self, path: str, headers: dict[str, str]) -> Any:
        return self.client.get(path, headers=headers)

    def server_calls(self) -> list[str]:
        return [url for _, url, _ in self.transport.calls if url != OPA_URL]

    def test_unfiltered_caller_gets_the_server_response_unchanged(self) -> None:
        response = self.get(f"{API}/shells?limit=2", EDITOR)
        self.assertEqual(200, response.status_code)
        self.assertEqual(["urn:aas:0", "urn:aas:1"], [s["id"] for s in response.json["result"]])
        self.assertEqual({"cursor": "2"}, response.json["paging_metadata"])
        self.assertEqual([f"{REPOSITORY}{API}/shells?limit=2"], self.server_calls())
        self.assertEqual(1, len(self.transport.opa_inputs))

    def test_filtered_collection_reads_all_pages_and_keeps_visible_entries(self) -> None:
        response = self.get(f"{API}/shells", VIEWER)
        self.assertEqual(200, response.status_code)
        self.assertEqual(["urn:aas:1", "urn:aas:3", "urn:aas:4"], [s["id"] for s in response.json["result"]])
        self.assertEqual({}, response.json["paging_metadata"])
        self.assertEqual(3, len(self.server_calls()))  # 5 shells, page size 2

    def test_nested_references_are_filtered_in_collections(self) -> None:
        response = self.get(f"{API}/shells", VIEWER)
        submodels = {s["id"]: [r["keys"][0]["value"] for r in s["submodels"]] for s in response.json["result"]}
        self.assertEqual({"urn:aas:1": [], "urn:aas:3": ["urn:sm:3"], "urn:aas:4": []}, submodels)

    def test_filtered_collection_is_paginated_by_the_filter(self) -> None:
        first = self.get(f"{API}/shells?limit=2", VIEWER)
        self.assertEqual(["urn:aas:1", "urn:aas:3"], [s["id"] for s in first.json["result"]])
        cursor = first.json["paging_metadata"]["cursor"]
        second = self.get(f"{API}/shells?limit=2&cursor={cursor}", VIEWER)
        self.assertEqual(["urn:aas:4"], [s["id"] for s in second.json["result"]])
        self.assertEqual({}, second.json["paging_metadata"])

    def test_invalid_paging_parameters_are_rejected(self) -> None:
        for query in ("limit=0", "limit=x", "cursor=nonsense"):
            with self.subTest(query=query):
                self.assertEqual(400, self.get(f"{API}/shells?{query}", VIEWER).status_code)

    def test_single_shell_keeps_only_visible_submodel_references(self) -> None:
        self.shells[0] = shell("urn:aas:1", "urn:sm:3", "urn:sm:hidden")
        response = self.get(f"{API}/shells/abc", VIEWER)
        self.assertEqual(["urn:sm:3"], [r["keys"][0]["value"] for r in response.json["submodels"]])

    def test_non_json_responses_pass_unchanged(self) -> None:
        response = self.get(f"{API}/thumbnail", VIEWER)
        self.assertEqual(b"\x89PNG", response.data)
        self.assertEqual("image/png", response.headers["Content-Type"])

    def test_server_errors_pass_unchanged(self) -> None:
        self.assertEqual(404, self.get(f"{API}/unknown", VIEWER).status_code)

    def test_without_claims_nothing_is_visible(self) -> None:
        for headers in ({}, {"x-jwt-payload": "not base64 json"}):
            with self.subTest(headers=headers):
                response = self.get(f"{API}/shells", headers)
                self.assertEqual([], response.json["result"])

    def test_claims_header_is_not_forwarded_to_the_server(self) -> None:
        self.get(f"{API}/shells", VIEWER)
        for _, url, headers in self.transport.calls:
            if url != OPA_URL:
                self.assertNotIn("x-jwt-payload", {name.lower() for name in headers})

    def test_opa_receives_the_original_request(self) -> None:
        self.get(f"{API}/shells?limit=1", VIEWER)
        request = self.transport.opa_inputs[0]["attributes"]["request"]["http"]
        self.assertEqual({"method": "GET", "path": f"{API}/shells?limit=1"}, request)

    def test_unavailable_opa_fails_closed(self) -> None:
        def broken(_: dict[str, Any]) -> UpstreamResponse:
            raise urllib3.exceptions.NewConnectionError(None, "refused")  # type: ignore[arg-type]

        for opa in (broken, lambda _: json_response({}, 500), lambda _: UpstreamResponse(200, [], b"not json")):
            with self.subTest(opa=opa):
                self.transport.opa = opa
                self.assertEqual(503, self.get(f"{API}/shells", VIEWER).status_code)

    def test_undefined_decision_shows_nothing(self) -> None:
        self.transport.opa = lambda _: json_response({})
        response = self.get(f"{API}/shells", VIEWER)
        self.assertEqual([], response.json["result"])

    def test_too_large_collections_are_refused(self) -> None:
        self.shells.extend(shell(f"urn:aas:extra{i}") for i in range(10))
        self.assertEqual(502, self.get(f"{API}/shells", VIEWER).status_code)

    def test_only_get_is_handled(self) -> None:
        self.assertEqual(405, self.client.post(f"{API}/shells", headers=VIEWER).status_code)

    def test_unknown_prefix_is_rejected(self) -> None:
        self.assertEqual(404, self.get("/other/api/v3.1/shells", VIEWER).status_code)

    def test_health_endpoint(self) -> None:
        self.assertEqual(200, self.client.get("/healthz").status_code)


class SettingsTest(unittest.TestCase):
    def test_from_environment(self) -> None:
        settings = Settings.from_environment({
            "FILTER_UPSTREAMS": "/repository=http://repository:80/ /registry/=http://registry:80",
            "FILTER_OPA_URL": OPA_URL,
            "FILTER_MAX_ITEMS": "5",
        })
        self.assertEqual({"/repository": "http://repository:80", "/registry": "http://registry:80"},
                         settings.upstreams)
        self.assertEqual(5, settings.max_items)
        self.assertEqual("x-jwt-payload", settings.claims_header)

    def test_missing_or_invalid_settings_are_rejected(self) -> None:
        for environ in ({}, {"FILTER_UPSTREAMS": "/repository=http://r"}, {"FILTER_UPSTREAMS": "repository",
                                                                               "FILTER_OPA_URL": OPA_URL}):
            with self.subTest(environ=environ):
                with self.assertRaises(ValueError):
                    Settings.from_environment(environ)
