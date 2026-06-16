import base64
import json
import os
from copy import deepcopy
from typing import Any
from urllib.parse import urlencode

import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

UPSTREAM_REPOSITORY_URL = os.getenv("UPSTREAM_REPOSITORY_URL", "http://repository:80").rstrip("/")
POLICY_DATA_PATH = os.getenv("POLICY_DATA_PATH", "/policies/data.json")
PORT = int(os.getenv("PORT", "8080"))
UPSTREAM_PAGE_LIMIT = int(os.getenv("UPSTREAM_PAGE_LIMIT", "500"))
MAX_UPSTREAM_PAGES = int(os.getenv("MAX_UPSTREAM_PAGES", "100"))

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _load_access_control() -> dict[str, Any]:
    with open(POLICY_DATA_PATH, encoding="utf-8") as policy_file:
        return json.load(policy_file).get("access_control", {})


def _decode_unverified_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        return json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}


def _token_claims() -> dict[str, Any]:
    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        return {}
    return _decode_unverified_jwt(auth_header[len(prefix) :])


def _token_roles() -> set[str]:
    claims = _token_claims()
    roles: set[str] = set()

    roles.update(claims.get("realm_access", {}).get("roles", []))
    roles.update(claims.get("roles", []))

    for group in claims.get("groups", []):
        roles.add(group)
        if isinstance(group, str) and group.startswith("/"):
            roles.add(group[1:])

    roles.update(scope for scope in claims.get("scope", "").split(" ") if scope)
    return roles


def _method_matches(rule: dict[str, Any], method: str) -> bool:
    return method.upper() in {item.upper() for item in rule.get("methods", [])}


def _role_matches(rule: dict[str, Any], roles: set[str]) -> bool:
    return any(role in roles for role in rule.get("roles", []))


def _path_prefix_matches(prefix: str, path: str) -> bool:
    normalized_prefix = prefix.rstrip("/") or "/"
    normalized_path = path.rstrip("/") or "/"
    return (
        normalized_path == normalized_prefix
        or normalized_path.startswith(f"{normalized_prefix}/")
    )


def _path_allowed_by_rule(access_control: dict[str, Any], path: str, roles: set[str]) -> bool:
    for rule in access_control.get("rules", []):
        if not _method_matches(rule, "GET") or not _role_matches(rule, roles):
            continue
        path_prefix = rule.get("path_prefix")
        if (
            isinstance(path_prefix, str)
            and path_prefix
            and _path_prefix_matches(path_prefix, path)
        ):
            return True
    return False


def _filtered_collection(path: str, access_control: dict[str, Any]) -> dict[str, Any] | None:
    normalized_path = path.rstrip("/") or "/"
    for collection in access_control.get("filtered_collections", []):
        collection_path = collection.get("path", "").rstrip("/") or "/"
        if normalized_path == collection_path:
            return collection
    return None


def _allowed_ids_for_template(
    access_control: dict[str, Any],
    item_path_template: str,
    roles: set[str],
) -> tuple[bool, set[str]]:
    allowed_ids: set[str] = set()
    allow_all = False
    for rule in access_control.get("resource_rules", []):
        if not _method_matches(rule, "GET") or not _role_matches(rule, roles):
            continue
        if item_path_template not in rule.get("path_templates", []):
            continue

        ids = set(rule.get("ids", []))
        if "*" in ids:
            allow_all = True
        allowed_ids.update(ids)

    return allow_all, allowed_ids


def _to_path_id(identifier: str) -> str:
    return base64.urlsafe_b64encode(identifier.encode("utf-8")).decode("ascii").rstrip("=")


def _id_allowed(identifier: str, allow_all: bool, allowed_ids: set[str]) -> bool:
    return allow_all or identifier in allowed_ids or _to_path_id(identifier) in allowed_ids


def _item_allowed(item: Any, allow_all: bool, allowed_ids: set[str]) -> bool:
    if allow_all:
        return True
    if not isinstance(item, dict):
        return False

    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        return False

    return _id_allowed(item_id, allow_all, allowed_ids)


def _submodel_reference_id(reference: Any) -> str | None:
    if not isinstance(reference, dict):
        return None

    keys = reference.get("keys")
    if not isinstance(keys, list):
        return None

    for key in reversed(keys):
        if not isinstance(key, dict):
            continue
        key_type = key.get("type")
        value = key.get("value")
        if (
            isinstance(key_type, str)
            and key_type.lower() == "submodel"
            and isinstance(value, str)
            and value
        ):
            return value

    return None


def _submodel_reference_allowed(reference: Any, allow_all: bool, allowed_ids: set[str]) -> bool:
    if allow_all:
        return True

    submodel_id = _submodel_reference_id(reference)
    if not submodel_id:
        return False

    return _id_allowed(submodel_id, allow_all, allowed_ids)


def _configured_submodel_path_templates(access_control: dict[str, Any]) -> set[str]:
    path_templates = access_control.get("submodel_reference_path_templates", [])
    if not isinstance(path_templates, list):
        return set()
    return {template for template in path_templates if isinstance(template, str)}


def _template_targets_submodel(path_template: Any) -> bool:
    return isinstance(path_template, str) and "{submodel" in path_template.lower()


def _rule_targets_submodel(rule: dict[str, Any], configured_templates: set[str]) -> bool:
    path_templates = rule.get("path_templates", [])
    if not isinstance(path_templates, list):
        return False
    if configured_templates:
        return any(template in configured_templates for template in path_templates)
    return any(_template_targets_submodel(template) for template in path_templates)


def _resource_rule_submodel_access(
    access_control: dict[str, Any],
    roles: set[str],
) -> tuple[bool, set[str]]:
    allowed_ids: set[str] = set()
    allow_all = False
    configured_templates = _configured_submodel_path_templates(access_control)

    for rule in access_control.get("resource_rules", []):
        if not _method_matches(rule, "GET") or not _role_matches(rule, roles):
            continue
        if not _rule_targets_submodel(rule, configured_templates):
            continue

        ids = set(rule.get("ids", []))
        if "*" in ids:
            allow_all = True
        allowed_ids.update(ids)

    return allow_all, allowed_ids


def _submodel_reference_access(
    access_control: dict[str, Any],
    roles: set[str],
    request_path: str,
) -> tuple[bool, set[str]]:
    allow_all, allowed_ids = _resource_rule_submodel_access(access_control, roles)
    if allow_all or allowed_ids:
        return allow_all, allowed_ids
    if _path_allowed_by_rule(access_control, request_path, roles):
        return True, set()
    return False, set()


def _has_submodel_references(item: Any) -> bool:
    return isinstance(item, dict) and isinstance(item.get("submodels"), list)


def _filter_aas_submodel_references(item: Any, allow_all: bool, allowed_ids: set[str]) -> Any:
    if not _has_submodel_references(item):
        return item

    filtered_item = deepcopy(item)
    filtered_item["submodels"] = [
        reference
        for reference in item["submodels"]
        if _submodel_reference_allowed(reference, allow_all, allowed_ids)
    ]
    return filtered_item


def _request_query_without_paging() -> list[tuple[str, str]]:
    query_items: list[tuple[str, str]] = []
    for key in request.args:
        if key in {"limit", "cursor"}:
            continue
        for value in request.args.getlist(key):
            query_items.append((key, value))
    return query_items


def _upstream_url(path: str, query_items: list[tuple[str, str]] | None = None) -> str:
    url = f"{UPSTREAM_REPOSITORY_URL}/{path.lstrip('/')}"
    if query_items:
        return f"{url}?{urlencode(query_items)}"
    return url


def _forward_headers() -> dict[str, str]:
    headers = {}
    for name, value in request.headers.items():
        lower_name = name.lower()
        if lower_name in HOP_BY_HOP_HEADERS or lower_name == "host":
            continue
        headers[name] = value
    return headers


def _response_headers(upstream_response: requests.Response) -> dict[str, str]:
    headers = {}
    for name, value in upstream_response.headers.items():
        lower_name = name.lower()
        if lower_name in HOP_BY_HOP_HEADERS:
            continue
        if lower_name in {"content-length", "content-encoding"}:
            continue
        headers[name] = value
    return headers


def _extract_items(payload: Any) -> list[Any]:
    if isinstance(payload, dict) and isinstance(payload.get("result"), list):
        return payload["result"]
    if isinstance(payload, list):
        return payload
    return []


def _next_upstream_cursor(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    paging_metadata = payload.get("paging_metadata") or payload.get("pagingMetadata") or {}
    cursor = paging_metadata.get("cursor")
    return cursor if isinstance(cursor, str) and cursor else None


def _fetch_collection(path: str) -> tuple[Any, list[Any], int]:
    query_items = _request_query_without_paging()
    cursor = None
    first_payload: Any = None
    items: list[Any] = []
    status_code = 200

    for _ in range(MAX_UPSTREAM_PAGES):
        page_query = list(query_items)
        page_query.append(("limit", str(UPSTREAM_PAGE_LIMIT)))
        if cursor:
            page_query.append(("cursor", cursor))

        upstream_response = requests.get(
            _upstream_url(path, page_query),
            headers=_forward_headers(),
            timeout=30,
        )
        status_code = upstream_response.status_code
        upstream_response.raise_for_status()

        payload = upstream_response.json()
        if first_payload is None:
            first_payload = payload

        page_items = _extract_items(payload)
        items.extend(page_items)

        cursor = _next_upstream_cursor(payload)
        if not cursor or not page_items:
            break

    return first_payload, items, status_code


def _requested_limit(default_size: int) -> int:
    raw_limit = request.args.get("limit")
    if raw_limit is None:
        return default_size
    try:
        return max(0, int(raw_limit))
    except ValueError:
        return default_size


def _encode_cursor(offset: int) -> str:
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"filtered:{token}"


def _decode_cursor() -> int:
    raw_cursor = request.args.get("cursor", "")
    prefix = "filtered:"
    if not raw_cursor.startswith(prefix):
        return 0

    token = raw_cursor[len(prefix) :]
    token += "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        return max(0, int(payload.get("offset", 0)))
    except (ValueError, json.JSONDecodeError):
        return 0


def _paginate_items(items: list[Any]) -> tuple[list[Any], str | None]:
    offset = _decode_cursor()
    limit = _requested_limit(len(items))
    if limit == 0:
        return [], None

    page = items[offset : offset + limit]
    next_offset = offset + len(page)
    next_cursor = _encode_cursor(next_offset) if next_offset < len(items) else None
    return page, next_cursor


def _filtered_payload(original_payload: Any, filtered_items: list[Any]) -> Any:
    page_items, cursor = _paginate_items(filtered_items)

    if isinstance(original_payload, dict):
        payload = deepcopy(original_payload)
        payload["result"] = page_items
        payload.pop("pagingMetadata", None)
        if cursor:
            payload["paging_metadata"] = {"cursor": cursor}
        else:
            payload["paging_metadata"] = {}
        return payload

    return page_items


def _handle_filtered_collection(path: str, collection: dict[str, Any], access_control: dict[str, Any]) -> Response:
    roles = _token_roles()
    original_payload, items, status_code = _fetch_collection(path)
    allow_all, allowed_ids = _allowed_ids_for_template(
        access_control,
        collection.get("item_path_template", ""),
        roles,
    )
    request_path = "/" + path.strip("/")
    submodel_allow_all, submodel_allowed_ids = _submodel_reference_access(
        access_control,
        roles,
        request_path,
    )
    filtered_items = [
        _filter_aas_submodel_references(item, submodel_allow_all, submodel_allowed_ids)
        for item in items
        if _item_allowed(item, allow_all, allowed_ids)
    ]

    payload = _filtered_payload(original_payload, filtered_items)
    return jsonify(payload), status_code


def _proxy_request(path: str, access_control: dict[str, Any]) -> Response:
    upstream_response = requests.request(
        request.method,
        _upstream_url(path, list(request.args.items(multi=True))),
        headers=_forward_headers(),
        data=request.get_data(),
        timeout=30,
    )

    if request.method == "GET" and upstream_response.status_code < 400:
        try:
            payload = upstream_response.json()
        except ValueError:
            pass
        else:
            if _has_submodel_references(payload):
                roles = _token_roles()
                request_path = "/" + path.strip("/")
                submodel_allow_all, submodel_allowed_ids = _submodel_reference_access(
                    access_control,
                    roles,
                    request_path,
                )
                filtered_payload = _filter_aas_submodel_references(
                    payload,
                    submodel_allow_all,
                    submodel_allowed_ids,
                )
                return jsonify(filtered_payload), upstream_response.status_code

    return Response(
        upstream_response.content,
        status=upstream_response.status_code,
        headers=_response_headers(upstream_response),
    )


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
def repository_proxy(path: str) -> Response:
    access_control = _load_access_control()
    normalized_path = f"/{path.strip('/')}"
    collection = _filtered_collection(normalized_path, access_control)

    if request.method == "GET":
        if collection:
            try:
                return _handle_filtered_collection(path, collection, access_control)
            except requests.HTTPError as exc:
                response = exc.response
                return Response(
                    response.content,
                    status=response.status_code,
                    headers=_response_headers(response),
                )

    return _proxy_request(path, access_control)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
