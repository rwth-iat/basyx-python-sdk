# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Unit tests for the generic policy, against a small fixture instead of an example's data.
# Run with: opa test policy/ -v
package envoy.authz_test

import rego.v1

import data.envoy.authz

fixture := {
	"api_version": "v1",
	"public_paths": ["/"],
	"public_path_prefixes": ["/ui"],
	"rules": [
		{"path_prefix": "/api", "methods": ["GET"], "roles": ["reader", "admin"]},
		{"path_prefix": "/api/v1/admin", "methods": ["GET"], "roles": ["admin"]},
	],
	"routes": [
		"/api/{api_version}/things/{thing}",
		"/api/{api_version}/things/{thing}/parts/{part}",
	],
	"collections": [
		{"path": "/api/{api_version}/things", "resource": "thing"},
		{"path": "/api/{api_version}/things/{thing}/parts", "resource": "part"},
	],
	"resource_rules": [
		{"resource": "thing", "ids": ["urn:thing:1"], "methods": ["GET"], "roles": ["guest"]},
		{"resource": "thing", "id_prefixes": ["urn:open:"], "methods": ["GET"], "roles": ["guest"]},
		{"resource": "part", "ids": ["urn:part:1"], "methods": ["GET"], "roles": ["guest"]},
		{"resource": "part", "ids": ["*"], "methods": ["GET"], "roles": ["auditor"]},
		{"resource": "thing", "ids": ["*"], "methods": ["GET"], "roles": ["auditor"]},
	],
}

# Input as the OPA-Envoy plugin delivers it (camelCase metadata, verified JWT payload).
request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
}}

role(name) := {"realm_access": {"roles": [name]}}

allowed(method, path, claims) if {
	authz.allow with input as request(method, path, claims) with data.access_control as fixture
}

allowed_with(config, method, path, claims) if {
	authz.allow with input as request(method, path, claims) with data.access_control as config
}

thing(id) := concat("", ["/api/v1/things/", base64url.encode_no_pad(id)])

# --- public paths -----------------------------------------------------------------------------------------------------

test_public_path_is_exact if {
	allowed("GET", "/", {})
	not allowed("GET", "/api/v1/things", {})
}

test_public_prefix_covers_subpaths if {
	allowed("GET", "/ui", {})
	allowed("GET", "/ui/assets/app.js", {})
	not allowed("GET", "/uix", {})
}

# --- server-level rules -----------------------------------------------------------------------------------------------

test_rule_grants_method_to_role if {
	allowed("GET", "/api/v1/things", role("reader"))
	not allowed("POST", "/api/v1/things", role("reader"))
	not allowed("GET", "/api/v1/things", role("guest"))
}

test_longest_prefix_wins if {
	not allowed("GET", "/api/v1/admin/settings", role("reader"))
	allowed("GET", "/api/v1/admin/settings", role("admin"))
}

test_prefix_stops_at_segment_boundary if {
	not allowed("GET", "/api-internal/x", role("reader"))
}

test_method_is_case_insensitive if {
	allowed("get", "/api/v1/things", role("reader"))
}

# --- resource rules ---------------------------------------------------------------------------------------------------

test_listed_id_is_allowed if {
	allowed("GET", thing("urn:thing:1"), role("guest"))
}

test_unlisted_id_is_denied if {
	not allowed("GET", thing("urn:thing:2"), role("guest"))
}

test_id_prefix_is_allowed if {
	allowed("GET", thing("urn:open:anything"), role("guest"))
	not allowed("GET", thing("urn:closed:anything"), role("guest"))
}

test_wildcard_id_is_allowed if {
	allowed("GET", thing("urn:thing:42"), role("auditor"))
}

test_route_covers_subpaths if {
	allowed("GET", concat("", [thing("urn:thing:1"), "/attributes"]), role("guest"))
}

test_every_resource_in_path_must_be_allowed if {
	allowed("GET", concat("", [thing("urn:thing:1"), "/parts/", base64url.encode_no_pad("urn:part:1")]), role("guest"))
	not allowed("GET", concat("", [thing("urn:thing:1"), "/parts/", base64url.encode_no_pad("urn:part:2")]), role("guest"))
	not allowed("GET", concat("", [thing("urn:thing:2"), "/parts/", base64url.encode_no_pad("urn:part:1")]), role("guest"))
}

test_resource_rule_checks_method if {
	not allowed("DELETE", thing("urn:thing:1"), role("guest"))
}

test_padded_and_unpadded_ids_are_equal if {
	allowed("GET", concat("", ["/api/v1/things/", base64url.encode("urn:thing:1")]), role("guest"))
}

test_undecodable_id_is_denied if {
	not allowed("GET", "/api/v1/things/!!!", role("auditor"))
	not allowed("GET", concat("", [thing("urn:thing:1"), "/parts/!!!"]), role("guest"))
}

test_operation_segments_are_not_resources if {
	not allowed("GET", "/api/v1/things/$reference", role("auditor"))
}

test_list_without_resource_is_denied if {
	not allowed("GET", "/api/v1/things", role("auditor"))
}

test_api_version_from_config if {
	not allowed("GET", concat("", ["/api/v2/things/", base64url.encode_no_pad("urn:thing:1")]), role("guest"))
	config := object.union(fixture, {"api_version": "v2"})
	allowed_with(config, "GET", concat("", ["/api/v2/things/", base64url.encode_no_pad("urn:thing:1")]), role("guest"))
}

test_api_version_from_environment_overrides_config if {
	path := concat("", ["/api/v2/things/", base64url.encode_no_pad("urn:thing:1")])
	authz.allow with input as request("GET", path, role("guest"))
		with data.access_control as fixture
		with opa.runtime as {"env": {"ACCESS_CONTROL_API_VERSION": "v2"}}
	not authz.allow with input as request("GET", thing("urn:thing:1"), role("guest"))
		with data.access_control as fixture
		with opa.runtime as {"env": {"ACCESS_CONTROL_API_VERSION": "v2"}}
}

# --- roles ------------------------------------------------------------------------------------------------------------

test_scopes_groups_and_top_level_roles_are_not_roles if {
	not allowed("GET", "/api/v1/things", {"scope": "openid reader"})
	not allowed("GET", "/api/v1/things", {"groups": ["reader", "/reader"]})
	not allowed("GET", "/api/v1/things", {"roles": ["reader"]})
}

test_role_claim_is_configurable if {
	claims := {"resource_access": {"app": {"roles": ["reader"]}}}
	not allowed("GET", "/api/v1/things", claims)
	allowed_with(object.union(fixture, {"role_claim": "resource_access.app.roles"}), "GET", "/api/v1/things", claims)
}

test_role_claim_from_environment_overrides_config if {
	claims := {"resource_access": {"app": {"roles": ["reader"]}}}
	authz.allow with input as request("GET", "/api/v1/things", claims)
		with data.access_control as fixture
		with opa.runtime as {"env": {"ACCESS_CONTROL_ROLE_CLAIM": "resource_access.app.roles"}}
}

test_malformed_role_claim_is_ignored if {
	not allowed("GET", "/api/v1/things", {"realm_access": {"roles": "reader"}})
	not allowed("GET", "/api/v1/things", {"realm_access": {"roles": [{"name": "reader"}]}})
}

test_missing_token_has_no_roles if {
	not allowed("GET", "/api/v1/things", {})
	not authz.allow with input as {"attributes": {"request": {"http": {"method": "GET", "path": "/api/v1/things"}}}}
		with data.access_control as fixture
}

# --- canonical paths --------------------------------------------------------------------------------------------------

ambiguous_paths := [
	"/api/v1/things/../admin/settings",
	"/api/v1/things/./x",
	"/api/v1//things",
	"/api/v1/things/%2e%2e/admin",
	"/api/v1/things/%2E%2E/admin",
	"/api/v1/things%2Fadmin",
	"/api/v1/things%252F..",
	"/api/v1/things\\..\\admin",
	"/ui/../api/v1/admin/settings",
]

test_ambiguous_paths_are_denied_for_every_role if {
	every path in ambiguous_paths {
		not allowed("GET", path, role("admin"))
		not allowed("GET", path, {})
	}
}

test_query_string_does_not_change_the_decision if {
	allowed("GET", concat("", [thing("urn:thing:1"), "?level=deep"]), role("guest"))
	not allowed("GET", "/api/v1/things?x=/ui", {})
}

test_fails_closed_without_config if {
	not authz.allow with input as request("GET", "/api/v1/things", role("admin")) with data.access_control as {}
}

# --- filtered collections ---------------------------------------------------------------------------------------------

# A request on a route that Envoy sends through the response filter.
filtered_request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
	"contextExtensions": {"response_filter": "true"},
}}

allowed_filtered(method, path, claims) if {
	authz.allow with input as filtered_request(method, path, claims) with data.access_control as fixture
}

test_collection_needs_the_response_filter if {
	allowed_filtered("GET", "/api/v1/things", role("guest"))
	not allowed("GET", "/api/v1/things", role("guest"))
}

test_collection_needs_a_resource_rule_for_its_type if {
	not allowed_filtered("GET", "/api/v1/things", role("nobody"))
	not allowed_filtered("GET", "/api/v1/things", {})
}

test_collection_is_read_only if {
	not allowed_filtered("POST", "/api/v1/things", role("guest"))
	not allowed_filtered("DELETE", "/api/v1/things", role("guest"))
}

test_collection_matches_exactly if {
	not allowed_filtered("GET", "/api/v1/things/", role("guest"))
	not allowed_filtered("GET", "/api/v1/other", role("guest"))
}

test_collection_below_a_resource_needs_that_resource if {
	allowed_filtered("GET", concat("", [thing("urn:thing:1"), "/parts"]), role("guest"))
	not allowed_filtered("GET", concat("", [thing("urn:thing:2"), "/parts"]), role("guest"))
}

test_collection_path_must_be_canonical if {
	not allowed_filtered("GET", "/api/v1/things/../things", role("guest"))
}

filter_decision(path, claims, items) := decision if {
	query := object.union(request("GET", path, claims), {"items": items})
	decision := authz.response_filter with input as query with data.access_control as fixture
}

test_response_filter_lists_visible_items if {
	items := [
		{"type": "thing", "id": "urn:thing:1"},
		{"type": "thing", "id": "urn:thing:2"},
		{"type": "thing", "id": "urn:open:3"},
		{"type": "part", "id": "urn:part:1"},
	]
	decision := filter_decision("/api/v1/things", role("guest"), items)
	decision.unfiltered == false
	decision.visible == [items[0], items[2], items[3]]
}

test_response_filter_passes_server_level_grants_unfiltered if {
	decision := filter_decision("/api/v1/things", role("reader"), [{"type": "thing", "id": "urn:thing:2"}])
	decision.unfiltered == true
}

test_response_filter_shows_nothing_without_roles if {
	decision := filter_decision("/api/v1/things", {}, [{"type": "thing", "id": "urn:thing:1"}])
	decision.unfiltered == false
	decision.visible == []
}
