# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Unit tests for policy.rego, evaluated against the real policies/data.json.
# Run with: opa test policies/ -v
package envoy.authz_test

import rego.v1

import data.envoy.authz

# Input as the OPA-Envoy plugin delivers it (camelCase metadata, verified JWT payload).
request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
}}

role(name) := {"realm_access": {"roles": [name]}}

allowed(method, path, claims) if authz.allow with input as request(method, path, claims)

test_public_paths_need_no_token if {
	allowed("GET", "/health", {})
	allowed("GET", "/public/logo.png", {})
}

test_other_paths_need_a_role if {
	not allowed("GET", "/items", {})
}

test_reader_can_read if {
	allowed("GET", "/items", role("reader"))
	allowed("HEAD", "/items", role("reader"))
}

test_reader_cannot_write if {
	not allowed("POST", "/items", role("reader"))
}

test_writer_can_write_but_not_delete if {
	allowed("POST", "/items", role("writer"))
	allowed("PATCH", "/items/1", role("writer"))
	not allowed("DELETE", "/items/1", role("writer"))
}

test_admin_can_delete if {
	allowed("DELETE", "/items/1", role("admin"))
}

test_admin_paths_need_admin if {
	not allowed("GET", "/admin/settings", role("reader"))
	not allowed("GET", "/admin/settings", role("writer"))
	allowed("GET", "/admin/settings", role("admin"))
}

test_scopes_and_groups_are_not_roles if {
	not allowed("GET", "/admin/settings", {"scope": "openid admin"})
	not allowed("GET", "/admin/settings", {"groups": ["admin"]})
}

test_ambiguous_paths_are_denied if {
	not allowed("GET", "/items/../admin/settings", role("reader"))
	not allowed("GET", "/items/%2e%2e/admin/settings", role("reader"))
	not allowed("GET", "/items//1", role("reader"))
	not allowed("GET", "/public/../admin/settings", {})
}
