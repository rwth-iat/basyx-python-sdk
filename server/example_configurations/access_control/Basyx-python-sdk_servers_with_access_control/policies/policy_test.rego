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

api := "/repository/api/v3.1"

# base64url identifiers from example_data/example_aas.json
shell := "aHR0cHM6Ly9leGFtcGxlLm9yZy9UZXN0X0Fzc2V0QWRtaW5pc3RyYXRpb25TaGVsbA"

identification := "aHR0cDovL2V4YW1wbGUub3JnL1N1Ym1vZGVscy9Bc3NldHMvVGVzdEFzc2V0L0lkZW50aWZpY2F0aW9u"

bill_of_material := "aHR0cDovL2V4YW1wbGUub3JnL1N1Ym1vZGVscy9Bc3NldHMvVGVzdEFzc2V0L0JpbGxPZk1hdGVyaWFs"

# Input as the OPA-Envoy plugin delivers it (camelCase metadata, verified JWT payload).
request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
}}

role(name) := {"realm_access": {"roles": [name]}}

allowed(method, path, claims) if authz.allow with input as request(method, path, claims)

# --- public paths -------------------------------------------------------------

test_ui_is_public if {
	allowed("GET", "/", {})
	allowed("GET", "/ui/index.html", {})
}

test_api_is_not_public if {
	not allowed("GET", sprintf("%s/shells", [api]), {})
}

# --- server-level rules ---------------------------------------------------------

test_editor_and_admin_can_list_shells if {
	allowed("GET", sprintf("%s/shells", [api]), role("editor"))
	allowed("GET", sprintf("%s/shells", [api]), role("admin"))
}

test_viewer_cannot_list_shells if {
	not allowed("GET", sprintf("%s/shells", [api]), role("viewer"))
}

test_editor_can_write_but_not_delete if {
	allowed("PUT", sprintf("%s/shells/%s", [api, shell]), role("editor"))
	allowed("PATCH", sprintf("%s/submodels/%s", [api, identification]), role("editor"))
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), role("editor"))
}

test_admin_can_delete if {
	allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), role("admin"))
}

test_head_follows_get if {
	allowed("HEAD", sprintf("%s/shells", [api]), role("editor"))
	allowed("HEAD", sprintf("%s/shells/%s", [api, shell]), role("viewer"))
}

# --- resource-level rules for the viewer -----------------------------------------

test_viewer_can_read_listed_shell if {
	allowed("GET", sprintf("%s/shells/%s", [api, shell]), role("viewer"))
	allowed("GET", sprintf("%s/shells/%s?level=deep", [api, shell]), role("viewer"))
}

test_viewer_can_read_listed_submodel if {
	allowed("GET", sprintf("%s/submodels/%s", [api, identification]), role("viewer"))
	allowed("GET", sprintf("%s/shells/%s/submodels/%s", [api, shell, identification]), role("viewer"))
}

test_viewer_cannot_read_unlisted_submodel if {
	not allowed("GET", sprintf("%s/submodels/%s", [api, bill_of_material]), role("viewer"))
	not allowed("GET", sprintf("%s/shells/%s/submodels/%s", [api, shell, bill_of_material]), role("viewer"))
}

test_viewer_cannot_write if {
	not allowed("PUT", sprintf("%s/shells/%s", [api, shell]), role("viewer"))
	not allowed("PATCH", sprintf("%s/submodels/%s", [api, identification]), role("viewer"))
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), role("viewer"))
}

# --- role sources -----------------------------------------------------------------

test_scopes_are_not_roles if {
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), {"scope": "openid admin"})
}

test_groups_are_not_roles if {
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), {"groups": ["admin", "/admin"]})
}

test_top_level_roles_claim_is_ignored if {
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), {"roles": ["admin"]})
}

# --- path bypass regressions (reproduced against the running stack) ---------------

bypass_paths := [
	sprintf("%s/shells/%s/../%s", [api, shell, bill_of_material]),
	sprintf("%s/shells/%s/../../submodels/%s", [api, shell, bill_of_material]),
	sprintf("%s/shells/%s/..", [api, shell]),
	sprintf("%s/shells/%s/./", [api, shell]),
	sprintf("%s/shells/%s/%%2e%%2e/%s", [api, shell, bill_of_material]),
	sprintf("%s/shells/%s/%%2E%%2E/%s", [api, shell, bill_of_material]),
	sprintf("%s/shells/%s%%2F..%%2F%s", [api, shell, bill_of_material]),
	sprintf("%s/shells/%s%%252F..", [api, shell]),
	sprintf("%s/shells/%s\\..\\%s", [api, shell, bill_of_material]),
	sprintf("/repository//api/v3.1/shells/%s", [bill_of_material]),
]

test_viewer_bypass_paths_are_denied if {
	every path in bypass_paths {
		not allowed("GET", path, role("viewer"))
	}
}

test_ambiguous_paths_are_denied_for_every_role if {
	every path in bypass_paths {
		not allowed("GET", path, role("admin"))
	}
}

test_similar_prefix_is_not_matched if {
	not allowed("GET", "/repository-internal/api/v3.1/shells", role("editor"))
}
