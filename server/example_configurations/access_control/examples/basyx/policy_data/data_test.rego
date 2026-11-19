# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Tests of this example's rules (policy_data/data.json) with the shared policy.
# Run from access_control/: opa test policy/ examples/basyx/policy_data/ -v
package basyx_example_test

import rego.v1

import data.envoy.authz

api := "/repository/api/v3.1"

# Path identifiers of the objects in example_data/example_aas.json
shell := base64url.encode_no_pad("https://example.org/Test_AssetAdministrationShell")

identification := base64url.encode_no_pad("http://example.org/Submodels/Assets/TestAsset/Identification")

bill_of_material := base64url.encode_no_pad("http://example.org/Submodels/Assets/TestAsset/BillOfMaterial")

# Input as the OPA-Envoy plugin delivers it (camelCase metadata, verified JWT payload).
request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
}}

role(name) := {"realm_access": {"roles": [name]}}

allowed(method, path, claims) if authz.allow with input as request(method, path, claims)

# --- public paths -------------------------------------------------------------------------------------------------

test_ui_is_public if {
	allowed("GET", "/", {})
	allowed("GET", "/ui/index.html", {})
}

test_api_is_not_public if {
	not allowed("GET", sprintf("%s/shells", [api]), {})
	not allowed("GET", "/registry/api/v3.1/shell-descriptors", {})
}

# --- server-level rules -------------------------------------------------------------------------------------------

test_editor_and_admin_can_list_shells if {
	allowed("GET", sprintf("%s/shells", [api]), role("editor"))
	allowed("GET", sprintf("%s/shells", [api]), role("admin"))
}

test_viewer_cannot_list_shells_without_the_response_filter if {
	not allowed("GET", sprintf("%s/shells", [api]), role("viewer"))
}

# A request on a route that Envoy sends through the response filter.
filtered_request(method, path, claims) := object.union(
	request(method, path, claims),
	{"attributes": {"contextExtensions": {"response_filter": "true"}}},
)

allowed_filtered(method, path, claims) if authz.allow with input as filtered_request(method, path, claims)

test_viewer_can_list_through_the_response_filter if {
	allowed_filtered("GET", sprintf("%s/shells", [api]), role("viewer"))
	allowed_filtered("GET", sprintf("%s/submodels", [api]), role("viewer"))
	allowed_filtered("GET", sprintf("%s/shells/%s/submodel-refs", [api, shell]), role("viewer"))
	allowed_filtered("GET", "/registry/api/v3.1/shell-descriptors", role("viewer"))
	allowed_filtered("GET", "/registry/api/v3.1/submodel-descriptors", role("viewer"))
	allowed_filtered("GET", "/discovery/api/v3.1/lookup/shells", role("viewer"))
}

test_viewer_cannot_list_concept_descriptions if {
	not allowed_filtered("GET", sprintf("%s/concept-descriptions", [api]), role("viewer"))
}

test_unauthenticated_cannot_list_through_the_response_filter if {
	not allowed_filtered("GET", sprintf("%s/shells", [api]), {})
}

test_response_filter_hides_unlisted_submodel if {
	items := [
		{"type": "submodel", "id": "http://example.org/Submodels/Assets/TestAsset/Identification"},
		{"type": "submodel", "id": "http://example.org/Submodels/Assets/TestAsset/BillOfMaterial"},
		{"type": "submodel", "id": "https://example.org/Test_Submodel"},
	]
	query := object.union(request("GET", sprintf("%s/submodels", [api]), role("viewer")), {"items": items})
	decision := authz.response_filter with input as query
	decision.unfiltered == false
	decision.visible == [items[0], items[2]]
}

test_response_filter_passes_editor_unfiltered if {
	query := object.union(request("GET", sprintf("%s/submodels", [api]), role("editor")), {"items": []})
	decision := authz.response_filter with input as query
	decision.unfiltered == true
}

test_editor_can_write_but_not_delete if {
	allowed("PUT", sprintf("%s/shells/%s", [api, shell]), role("editor"))
	allowed("PATCH", sprintf("%s/submodels/%s", [api, identification]), role("editor"))
	allowed("POST", "/discovery/api/v3.1/lookup/shellsByAssetLink", role("editor"))
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), role("editor"))
}

test_admin_can_delete if {
	allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), role("admin"))
}

test_head_follows_get if {
	allowed("HEAD", sprintf("%s/shells", [api]), role("editor"))
	allowed("HEAD", sprintf("%s/shells/%s", [api, shell]), role("viewer"))
}

# --- resource-level rules for the viewer --------------------------------------------------------------------------

test_viewer_can_read_listed_shell_in_every_service if {
	allowed("GET", sprintf("%s/shells/%s", [api, shell]), role("viewer"))
	allowed("GET", sprintf("%s/shells/%s?level=deep", [api, shell]), role("viewer"))
	allowed("GET", sprintf("/registry/api/v3.1/shell-descriptors/%s", [shell]), role("viewer"))
	allowed("GET", sprintf("/discovery/api/v3.1/lookup/shells/%s", [shell]), role("viewer"))
}

test_viewer_can_read_listed_submodel if {
	allowed("GET", sprintf("%s/submodels/%s", [api, identification]), role("viewer"))
	allowed("GET", sprintf("%s/shells/%s/submodels/%s", [api, shell, identification]), role("viewer"))
	allowed("GET", sprintf("/registry/api/v3.1/submodel-descriptors/%s", [identification]), role("viewer"))
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

test_viewer_cannot_use_other_api_versions if {
	not allowed("GET", sprintf("/repository/api/v3.0/shells/%s", [shell]), role("viewer"))
}

# --- role sources -------------------------------------------------------------------------------------------------

test_scopes_groups_and_top_level_roles_are_not_roles if {
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), {"scope": "openid admin"})
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), {"groups": ["admin", "/admin"]})
	not allowed("DELETE", sprintf("%s/shells/%s", [api, shell]), {"roles": ["admin"]})
}

# --- path bypass regressions (reproduced against the running stack in phase 0) -------------------------------------

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

test_bypass_paths_are_denied_for_every_role if {
	every path in bypass_paths {
		not allowed("GET", path, role("viewer"))
		not allowed("GET", path, role("admin"))
	}
}

test_similar_prefix_is_not_matched if {
	not allowed("GET", "/repository-internal/api/v3.1/shells", role("editor"))
}

# --- rights of the operations -------------------------------------------------------------------------------------

rights(method, path) := result if {
	result := authz.required_rights with input as request(method, path, {})
}

# Every route of the BaSyx repository, registry and discovery server, with sample path identifiers (the redirect
# routes /shells/{aasIdentifier}/submodels/{submodelIdentifier}/... are covered by the annex rows they redirect for).
server_routes := [
	["GET", "/repository/api/v3.1/concept-descriptions"],
	["POST", "/repository/api/v3.1/concept-descriptions"],
	["GET", "/repository/api/v3.1/concept-descriptions/Y2Q"],
	["PUT", "/repository/api/v3.1/concept-descriptions/Y2Q"],
	["DELETE", "/repository/api/v3.1/concept-descriptions/Y2Q"],
	["GET", "/repository/api/v3.1/description"],
	["GET", "/repository/api/v3.1/serialization"],
	["GET", "/repository/api/v3.1/shells"],
	["POST", "/repository/api/v3.1/shells"],
	["GET", "/repository/api/v3.1/shells/$reference"],
	["GET", "/repository/api/v3.1/shells/c2hlbGw"],
	["PUT", "/repository/api/v3.1/shells/c2hlbGw"],
	["DELETE", "/repository/api/v3.1/shells/c2hlbGw"],
	["GET", "/repository/api/v3.1/shells/c2hlbGw/$reference"],
	["GET", "/repository/api/v3.1/shells/c2hlbGw/asset-information"],
	["PUT", "/repository/api/v3.1/shells/c2hlbGw/asset-information"],
	["GET", "/repository/api/v3.1/shells/c2hlbGw/asset-information/thumbnail"],
	["PUT", "/repository/api/v3.1/shells/c2hlbGw/asset-information/thumbnail"],
	["DELETE", "/repository/api/v3.1/shells/c2hlbGw/asset-information/thumbnail"],
	["GET", "/repository/api/v3.1/shells/c2hlbGw/submodel-refs"],
	["POST", "/repository/api/v3.1/shells/c2hlbGw/submodel-refs"],
	["DELETE", "/repository/api/v3.1/shells/c2hlbGw/submodel-refs/c20"],
	["GET", "/repository/api/v3.1/shells/c2hlbGw/submodels/c20"],
	["PUT", "/repository/api/v3.1/shells/c2hlbGw/submodels/c20"],
	["DELETE", "/repository/api/v3.1/shells/c2hlbGw/submodels/c20"],
	["GET", "/repository/api/v3.1/submodels"],
	["POST", "/repository/api/v3.1/submodels"],
	["GET", "/repository/api/v3.1/submodels/$metadata"],
	["GET", "/repository/api/v3.1/submodels/$path"],
	["GET", "/repository/api/v3.1/submodels/$reference"],
	["GET", "/repository/api/v3.1/submodels/$value"],
	["GET", "/repository/api/v3.1/submodels/c20"],
	["PUT", "/repository/api/v3.1/submodels/c20"],
	["PATCH", "/repository/api/v3.1/submodels/c20"],
	["DELETE", "/repository/api/v3.1/submodels/c20"],
	["GET", "/repository/api/v3.1/submodels/c20/$metadata"],
	["PATCH", "/repository/api/v3.1/submodels/c20/$metadata"],
	["GET", "/repository/api/v3.1/submodels/c20/$path"],
	["GET", "/repository/api/v3.1/submodels/c20/$reference"],
	["GET", "/repository/api/v3.1/submodels/c20/$value"],
	["PATCH", "/repository/api/v3.1/submodels/c20/$value"],
	["GET", "/repository/api/v3.1/submodels/c20/qualifiers"],
	["POST", "/repository/api/v3.1/submodels/c20/qualifiers"],
	["GET", "/repository/api/v3.1/submodels/c20/qualifiers/cXVhbA"],
	["PUT", "/repository/api/v3.1/submodels/c20/qualifiers/cXVhbA"],
	["DELETE", "/repository/api/v3.1/submodels/c20/qualifiers/cXVhbA"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/$metadata"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/$path"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/$reference"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/$value"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B"],
	["PUT", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B"],
	["PATCH", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B"],
	["DELETE", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/$metadata"],
	["PATCH", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/$metadata"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/$path"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/$reference"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/$value"],
	["PATCH", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/$value"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/attachment"],
	["PUT", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/attachment"],
	["DELETE", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/attachment"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/invoke"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/invoke/$value"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/invoke-async"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/invoke-async/$value"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/operation-results/aGFuZGxl"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/operation-results/aGFuZGxl/$value"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/operation-status/aGFuZGxl"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/qualifiers"],
	["POST", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/qualifiers"],
	["GET", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/qualifiers/cXVhbA"],
	["PUT", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/qualifiers/cXVhbA"],
	["DELETE", "/repository/api/v3.1/submodels/c20/submodel-elements/A.B/qualifiers/cXVhbA"],
	["GET", "/registry/api/v3.1/description"],
	["GET", "/registry/api/v3.1/shell-descriptors"],
	["POST", "/registry/api/v3.1/shell-descriptors"],
	["GET", "/registry/api/v3.1/shell-descriptors/c2hlbGw"],
	["PUT", "/registry/api/v3.1/shell-descriptors/c2hlbGw"],
	["DELETE", "/registry/api/v3.1/shell-descriptors/c2hlbGw"],
	["GET", "/registry/api/v3.1/shell-descriptors/c2hlbGw/submodel-descriptors"],
	["POST", "/registry/api/v3.1/shell-descriptors/c2hlbGw/submodel-descriptors"],
	["GET", "/registry/api/v3.1/shell-descriptors/c2hlbGw/submodel-descriptors/c20"],
	["PUT", "/registry/api/v3.1/shell-descriptors/c2hlbGw/submodel-descriptors/c20"],
	["DELETE", "/registry/api/v3.1/shell-descriptors/c2hlbGw/submodel-descriptors/c20"],
	["GET", "/registry/api/v3.1/submodel-descriptors"],
	["POST", "/registry/api/v3.1/submodel-descriptors"],
	["GET", "/registry/api/v3.1/submodel-descriptors/c20"],
	["PUT", "/registry/api/v3.1/submodel-descriptors/c20"],
	["DELETE", "/registry/api/v3.1/submodel-descriptors/c20"],
	["GET", "/discovery/api/v3.1/description"],
	["GET", "/discovery/api/v3.1/lookup/shells/"],
	["GET", "/discovery/api/v3.1/lookup/shells/c2hlbGw"],
	["POST", "/discovery/api/v3.1/lookup/shells/c2hlbGw"],
	["DELETE", "/discovery/api/v3.1/lookup/shells/c2hlbGw"],
	["POST", "/discovery/api/v3.1/lookup/shellsByAssetLink"],
]

test_every_server_route_requires_a_right if {
	every route in server_routes {
		count(rights(route[0], route[1])) > 0
	}
}

test_qualifiers_have_the_rights_of_submodel_elements if {
	rights("GET", sprintf("%s/submodels/c20/qualifiers", [api])) == {"READ"}
	rights("POST", sprintf("%s/submodels/c20/submodel-elements/A/qualifiers", [api])) == {"CREATE"}
	rights("PUT", sprintf("%s/submodels/c20/qualifiers/cXVhbA", [api])) == {"UPDATE"}
	rights("DELETE", sprintf("%s/submodels/c20/submodel-elements/A/qualifiers/cXVhbA", [api])) == {"DELETE"}
}
