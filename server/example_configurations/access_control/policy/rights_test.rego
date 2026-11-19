# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Unit tests for the mapping of AAS API operations to rights (rights.rego).
# Run with: opa test policy/ -v
package envoy.authz_test

import rego.v1

import data.envoy.authz

rights_fixture := {
	"api_version": "v3",
	"api_base_paths": ["/repository/api/{api_version}", "/registry/api/{api_version}", "/discovery/api/{api_version}"],
}

rights(method, path) := rights_with(rights_fixture, method, path)

rights_with(config, method, path) := result if {
	result := authz.required_rights with input as request(method, path, {}) with data.access_control as config
}

no_operation(method, path) if {
	not authz.operation with input as request(method, path, {}) with data.access_control as rights_fixture
}

# --- the table ---------------------------------------------------------------------------------------------------------

test_table_contains_every_operation_of_the_annex if {
	count(authz.annex_operations) == 235
}

test_table_has_one_operation_per_method_and_path if {
	keys := {[op.method, op.path] | some op in authz.annex_operations}
	count(keys) == count(authz.annex_operations)
}

test_table_uses_only_rights_of_part_4 if {
	every op in authz.annex_operations {
		every right in op.rights {
			right in {"CREATE", "READ", "UPDATE", "DELETE", "EXECUTE", "VIEW"}
		}
	}
}

test_only_bulk_results_have_no_fixed_right if {
	{op.name | some op in authz.annex_operations; count(op.rights) == 0} == {"BulkGetAsyncStatus", "BulkGetAsyncResult"}
}

# --- repository --------------------------------------------------------------------------------------------------------

test_reading_shells_is_read if {
	rights("GET", "/repository/api/v3/shells") == {"READ"}
	rights("GET", "/repository/api/v3/shells/c2hlbGw") == {"READ"}
}

test_references_and_paths_are_view if {
	rights("GET", "/repository/api/v3/shells/$reference") == {"VIEW"}
	rights("GET", "/repository/api/v3/submodels/c20/$path") == {"VIEW"}
	rights("GET", "/repository/api/v3/shells/c2hlbGw/submodel-refs") == {"VIEW"}
}

test_posting_is_create if {
	rights("POST", "/repository/api/v3/shells") == {"CREATE"}
	rights("POST", "/repository/api/v3/submodels/c20/submodel-elements/A.B") == {"CREATE"}
}

test_put_on_a_client_addressable_resource_is_create_or_update if {
	rights("PUT", "/repository/api/v3/shells/c2hlbGw") == {"CREATE", "UPDATE"}
	rights("PUT", "/repository/api/v3/submodels/c20") == {"CREATE", "UPDATE"}
	rights("PUT", "/repository/api/v3/submodels/c20/submodel-elements/A.B") == {"CREATE", "UPDATE"}
	rights("PUT", "/repository/api/v3/concept-descriptions/Y2Q") == {"CREATE", "UPDATE"}
}

test_put_on_a_part_of_a_resource_is_update if {
	rights("PUT", "/repository/api/v3/shells/c2hlbGw/asset-information") == {"UPDATE"}
	rights("PUT", "/repository/api/v3/submodels/c20/submodel-elements/A/attachment") == {"UPDATE"}
}

test_patch_is_update_and_delete_is_delete if {
	rights("PATCH", "/repository/api/v3/submodels/c20") == {"UPDATE"}
	rights("DELETE", "/repository/api/v3/shells/c2hlbGw") == {"DELETE"}
}

test_operations_are_execute if {
	rights("POST", "/repository/api/v3/submodels/c20/submodel-elements/Op/invoke") == {"EXECUTE"}
	rights("GET", "/repository/api/v3/submodels/c20/submodel-elements/Op/operation-status/aGFuZGxl") == {"EXECUTE"}
}

test_id_short_paths_with_dots_and_indices_are_one_segment if {
	rights("GET", "/repository/api/v3/submodels/c20/submodel-elements/Collection.List[2].Prop") == {"READ"}
}

test_modifier_segments_are_not_taken_for_identifiers if {
	rights("GET", "/repository/api/v3/submodels/c20/submodel-elements/$reference") == {"VIEW"}
	no_operation("GET", "/repository/api/v3/shells/$unknown")
}

test_description_is_read_on_every_service if {
	rights("GET", "/repository/api/v3/description") == {"READ"}
	rights("GET", "/registry/api/v3/description") == {"READ"}
	rights("GET", "/discovery/api/v3/description") == {"READ"}
}

# --- registry and discovery --------------------------------------------------------------------------------------------

test_reading_descriptors_is_view if {
	rights("GET", "/registry/api/v3/shell-descriptors") == {"VIEW"}
	rights("GET", "/registry/api/v3/shell-descriptors/c2hlbGw/submodel-descriptors/c20") == {"VIEW"}
}

test_put_on_a_descriptor_is_create_or_update if {
	rights("PUT", "/registry/api/v3/submodel-descriptors/c20") == {"CREATE", "UPDATE"}
}

test_discovery_lookups_are_view if {
	rights("GET", "/discovery/api/v3/lookup/shells") == {"VIEW"}
	rights("POST", "/discovery/api/v3/lookup/shellsByAssetLink") == {"VIEW"}
}

test_posting_asset_links_is_create_or_update if {
	rights("POST", "/discovery/api/v3/lookup/shells/c2hlbGw") == {"CREATE", "UPDATE"}
}

# --- request handling --------------------------------------------------------------------------------------------------

test_a_trailing_slash_addresses_the_same_operation if {
	rights("GET", "/discovery/api/v3/lookup/shells/") == {"VIEW"}
}

test_head_has_the_rights_of_get if {
	rights("HEAD", "/repository/api/v3/shells") == {"READ"}
}

test_unknown_endpoints_and_methods_have_no_operation if {
	no_operation("GET", "/repository/api/v3/unknown")
	no_operation("OPTIONS", "/repository/api/v3/shells")
	no_operation("POST", "/repository/api/v3/shells/c2hlbGw")
}

test_paths_outside_the_api_base_paths_have_no_operation if {
	no_operation("GET", "/shells")
	no_operation("GET", "/repository/api/v2/shells")
	no_operation("GET", "/repository/api/v3")
	no_operation("GET", "/repository-internal/api/v3/shells")
}

test_bulk_results_require_no_fixed_right if {
	rights("GET", "/registry/api/v3/bulk/status/aGFuZGxl") == set()
}

test_additional_operations_extend_the_table if {
	config := object.union(rights_fixture, {"additional_operations": [
		{"name": "GetThing", "method": "GET", "path": "/things/{thing}", "rights": ["READ"]},
	]})
	rights_with(config, "GET", "/repository/api/v3/things/dGhpbmc") == {"READ"}
}
