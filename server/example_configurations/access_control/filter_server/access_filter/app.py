# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
The response filter as a WSGI application.

Envoy sends GET requests for the AAS servers here, after it has verified the token and OPA has allowed the request.
For each request the filter asks OPA (decision ``response_filter``) whether the response may pass unchanged. If not,
it reads the response from the server, asks OPA which of the resources in it are visible, removes the others and, for
collections, paginates the remaining entries itself.
"""
import base64
import binascii
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Final, Protocol
from urllib.parse import urlencode

import urllib3
from werkzeug.wrappers import Request, Response

from . import resources
from .config import Settings

# Headers that describe one connection and must not be forwarded (RFC 9110, section 7.6.1)
_HOP_BY_HOP: Final[frozenset[str]] = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding",
    "upgrade",
})


@dataclass(frozen=True)
class UpstreamResponse:
    status: int
    headers: list[tuple[str, str]]
    body: bytes


class Transport(Protocol):
    """Sends an HTTP request to a server or to OPA."""

    def request(self, method: str, url: str, headers: dict[str, str], body: bytes | None,
                timeout: float) -> UpstreamResponse: ...


class Urllib3Transport:
    def __init__(self) -> None:
        self._pool = urllib3.PoolManager(retries=False)

    def request(self, method: str, url: str, headers: dict[str, str], body: bytes | None,
                timeout: float) -> UpstreamResponse:
        response = self._pool.request(method, url, headers=headers, body=body, timeout=timeout, redirect=False)
        return UpstreamResponse(response.status, list(response.headers.items()), response.data)


@dataclass(frozen=True)
class Decision:
    #: A server-level rule grants the request: the response may pass unchanged
    unfiltered: bool
    #: Resources the caller may see
    visible: frozenset[resources.Resource]


class FilterError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class AccessFilter:
    def __init__(self, settings: Settings, transport: Transport) -> None:
        self.settings = settings
        self.transport = transport

    def __call__(self, environ: dict[str, Any], start_response: Any) -> Iterable[bytes]:
        return self.handle(Request(environ))(environ, start_response)

    def handle(self, request: Request) -> Response:
        if request.path == "/healthz":
            return Response("ok", mimetype="text/plain")
        try:
            if request.method != "GET":
                raise FilterError(405, "the response filter only handles GET requests")
            base_url = next((url for prefix, url in self.settings.upstreams.items()
                             if request.path == prefix or request.path.startswith(prefix + "/")), None)
            if base_url is None:
                raise FilterError(404, "no server configured for this path")
            # Path and query exactly as received, i.e. as Envoy passed them on after normalizing
            raw_uri = request.environ.get("RAW_URI") or request.environ.get("REQUEST_URI")
            if isinstance(raw_uri, str) and raw_uri.startswith("/"):
                target = raw_uri
            else:
                query = request.query_string.decode("latin-1")
                target = request.path + (f"?{query}" if query else "")
            claims = self._claims(request)
            if self._decide(target, claims, []).unfiltered:
                return _passthrough(self._fetch(base_url + target, request))
            collection = resources.collection_for(request.path)
            if collection is not None:
                return self._filtered_collection(request, base_url, target, claims, collection)
            return self._filtered_object(request, base_url, target, claims)
        except FilterError as error:
            # Same shape as the AAS API's error results
            body = {"messages": [{"messageType": "Error", "text": error.message, "code": str(error.status)}]}
            return _json_response(body, error.status)

    # --- filtering ------------------------------------------------------------------------------------------------

    def _filtered_object(self, request: Request, base_url: str, target: str, claims: dict[str, Any]) -> Response:
        upstream = self._fetch(base_url + target, request)
        payload = _json_payload(upstream)
        if payload is None:
            return _passthrough(upstream)
        found = resources.resources_in(payload, None)
        if not found:
            return _passthrough(upstream)
        visible = self._decide(target, claims, found).visible
        filtered = resources.filter_response(payload, None, lambda resource: resource in visible)
        return _json_response(filtered, upstream.status)

    def _filtered_collection(self, request: Request, base_url: str, target: str, claims: dict[str, Any],
                             collection: resources.Collection) -> Response:
        limit = _parse_limit(request.args.get("limit"))
        offset = _parse_cursor(request.args.get("cursor"))
        query = [(key, value) for key, value in request.args.items(multi=True) if key not in ("limit", "cursor")]
        path = target.split("?", 1)[0]

        entries: list[Any] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            page_query = query + [("limit", str(self.settings.upstream_page_size))]
            if cursor is not None:
                page_query.append(("cursor", cursor))
            upstream = self._fetch(f"{base_url}{path}?{urlencode(page_query)}", request)
            if upstream.status >= 400:
                return _passthrough(upstream)
            payload = _json_payload(upstream)
            if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
                raise FilterError(502, "unexpected collection response from the server")
            entries.extend(payload["result"])
            if len(entries) > self.settings.max_items:
                raise FilterError(502, f"collection has more than {self.settings.max_items} entries to filter")
            paging_metadata = payload.get("paging_metadata") or payload.get("pagingMetadata") or {}
            next_cursor = paging_metadata.get("cursor") if isinstance(paging_metadata, dict) else None
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                break
            cursor = next_cursor
            seen_cursors.add(cursor)

        listing = {"result": entries}
        visible = self._decide(target, claims, resources.resources_in(listing, collection)).visible
        kept = resources.filter_response(listing, collection, lambda resource: resource in visible)["result"]

        page = kept[offset:] if limit is None else kept[offset:offset + limit]
        next_offset = offset + len(page)
        paging: dict[str, str] = {}
        if next_offset < len(kept):
            paging["cursor"] = base64.urlsafe_b64encode(f"offset:{next_offset}".encode()).decode().rstrip("=")
        return _json_response({"paging_metadata": paging, "result": page}, 200)

    # --- collaborators ----------------------------------------------------------------------------------------------

    def _claims(self, request: Request) -> dict[str, Any]:
        """The JWT payload Envoy verified and forwarded; without it the caller has no roles."""
        encoded = request.headers.get(self.settings.claims_header, "")
        try:
            claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        except (binascii.Error, ValueError):
            return {}
        return claims if isinstance(claims, dict) else {}

    def _decide(self, target: str, claims: dict[str, Any], found: list[resources.Resource]) -> Decision:
        query = {"input": {
            "attributes": {
                "request": {"http": {"method": "GET", "path": target}},
                "metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
            },
            "items": [{"type": resource_type, "id": identifier} for resource_type, identifier in found],
        }}
        try:
            response = self.transport.request("POST", self.settings.opa_url, {"Content-Type": "application/json"},
                                              json.dumps(query).encode(), self.settings.timeout)
            result = json.loads(response.body).get("result") if response.status == 200 else None
        except (urllib3.exceptions.HTTPError, ValueError, AttributeError) as error:
            raise FilterError(503, "authorization service unavailable") from error
        if response.status != 200:
            raise FilterError(503, "authorization service unavailable")
        if not isinstance(result, dict):  # decision undefined: show nothing
            return Decision(False, frozenset())
        visible = frozenset(
            (item["type"], item["id"]) for item in result.get("visible", [])
            if isinstance(item, dict) and isinstance(item.get("type"), str) and isinstance(item.get("id"), str)
        )
        return Decision(result.get("unfiltered") is True, visible)

    def _fetch(self, url: str, request: Request) -> UpstreamResponse:
        headers = {
            name: value for name, value in request.headers.items()
            if name.lower() not in _HOP_BY_HOP
            and name.lower() not in ("host", "content-length", "accept-encoding", self.settings.claims_header)
        }
        try:
            return self.transport.request("GET", url, headers, None, self.settings.timeout)
        except urllib3.exceptions.HTTPError as error:
            raise FilterError(502, "server unavailable") from error


def create_app() -> AccessFilter:
    """Entry point for gunicorn: ``gunicorn 'access_filter.app:create_app()'``."""
    return AccessFilter(Settings.from_environment(), Urllib3Transport())


# --- helpers ----------------------------------------------------------------------------------------------------------

def _json_payload(response: UpstreamResponse) -> Any:
    content_type = next((value for name, value in response.headers if name.lower() == "content-type"), "")
    if response.status >= 400 or "json" not in content_type.lower():
        return None
    try:
        return json.loads(response.body)
    except ValueError:
        return None


def _parse_limit(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        limit = int(raw)
    except ValueError:
        raise FilterError(400, "limit must be a positive integer") from None
    if limit < 1:
        raise FilterError(400, "limit must be a positive integer")
    return limit


def _parse_cursor(raw: str | None) -> int:
    if not raw:
        return 0
    try:
        prefix, _, value = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode().partition(":")
        if prefix == "offset" and value.isdigit():
            return int(value)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        pass
    raise FilterError(400, "invalid cursor")


def _passthrough(upstream: UpstreamResponse) -> Response:
    headers = [
        (name, value) for name, value in upstream.headers
        if name.lower() not in _HOP_BY_HOP and name.lower() not in ("content-length", "content-encoding")
    ]
    return Response(upstream.body, status=upstream.status, headers=headers)


def _json_response(payload: Any, status: int) -> Response:
    return Response(json.dumps(payload), status=status, mimetype="application/json")
