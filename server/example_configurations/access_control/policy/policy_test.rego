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
	"api_base_paths": ["/api/{api_version}"],
	# Operations of a made-up API, in the shape of the operation table in rights.rego
	"additional_operations": [
		{"name": "GetAllThings", "method": "GET", "path": "/things", "rights": ["READ"]},
		{"name": "PostThing", "method": "POST", "path": "/things", "rights": ["CREATE"]},
		{"name": "GetThing", "method": "GET", "path": "/things/{thing}", "rights": ["READ"]},
		{"name": "PutThing", "method": "PUT", "path": "/things/{thing}", "rights": ["CREATE", "UPDATE"]},
		{"name": "DeleteThing", "method": "DELETE", "path": "/things/{thing}", "rights": ["DELETE"]},
		{"name": "GetThing-Reference", "method": "GET", "path": "/things/{thing}/$reference", "rights": ["VIEW"]},
		{"name": "GetThingAttributes", "method": "GET", "path": "/things/{thing}/attributes", "rights": ["READ"]},
		{"name": "GetAllParts", "method": "GET", "path": "/things/{thing}/parts", "rights": ["READ"]},
		{"name": "GetPart", "method": "GET", "path": "/things/{thing}/parts/{part}", "rights": ["READ"]},
		{"name": "GetSettings", "method": "GET", "path": "/admin/settings", "rights": ["READ"]},
		{"name": "GetInfo", "method": "GET", "path": "/info", "rights": ["READ"]},
	],
	"public_paths": ["/"],
	"public_path_prefixes": ["/ui"],
	"routes": [
		"/api/{api_version}/things/{$aas}",
		"/api/{api_version}/things/{$aas}/parts/{$sm}",
	],
	"collections": [
		{"path": "/api/{api_version}/things", "resource": "$aas"},
		{"path": "/api/{api_version}/things/{$aas}/parts", "resource": "$sm"},
	],
}

# The caller has the role `name` if the token's "roles" claim contains it.
role_is(name) := {"$eq": [{"$attribute": {"CLAIM": "roles"}}, {"$strVal": name}]}

role_rule(name, rights, objects) := {
	"ACL": {"ATTRIBUTES": [{"CLAIM": "roles"}], "RIGHTS": rights, "ACCESS": "ALLOW"},
	"OBJECTS": objects,
	"FORMULA": role_is(name),
}

rules := {"AllAccessPermissionRules": {
	"DEFATTRIBUTES": [{"name": "roles", "attributes": [{"CLAIM": "roles"}]}],
	"DEFACLS": [{"name": "read", "acl": {"USEATTRIBUTES": "roles", "RIGHTS": ["READ"], "ACCESS": "ALLOW"}}],
	"DEFOBJECTS": [{"name": "whole_api", "objects": [{"ROUTE": "*"}]}],
	"DEFFORMULAS": [{"name": "reader", "formula": role_is("reader")}],
	"rules": [
		{"USEACL": "read", "USEOBJECTS": ["whole_api"], "USEFORMULA": "reader"},
		role_rule("admin", ["READ"], [{"ROUTE": "/admin/*"}]),
		role_rule("owner", ["ALL"], [{"ROUTE": "*"}]),
		role_rule("creator", ["CREATE"], [{"ROUTE": "*"}]),
		role_rule("updater", ["UPDATE"], [{"ROUTE": "*"}]),
		role_rule("lister", ["READ"], [{"ROUTE": "/things"}]),
		role_rule("prefixer", ["READ"], [{"ROUTE": "/things/*"}]),
		role_rule("guest", ["READ"], [{"IDENTIFIABLE": "$aas(\"urn:thing:1\")"}, {"IDENTIFIABLE": "$sm(\"urn:part:1\")"}]),
		role_rule("auditor", ["READ"], [{"IDENTIFIABLE": "$aas(\"*\")"}, {"IDENTIFIABLE": "$sm(\"*\")"}]),
		role_rule("viewer", ["VIEW"], [{"IDENTIFIABLE": "$aas(\"urn:thing:1\")"}]),
		role_rule("describer", ["READ"], [{"DESCRIPTOR": "$aasdesc(\"*\")"}]),
		{
			"ACL": {"ATTRIBUTES": [{"GLOBAL": "ANONYMOUS"}], "RIGHTS": ["READ"], "ACCESS": "ALLOW"},
			"OBJECTS": [{"ROUTE": "/info"}],
			"FORMULA": {"$boolean": true},
		},
	],
}}

# Input as the OPA-Envoy plugin delivers it (camelCase metadata, verified JWT payload).
request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
}}

# A request without a token: Envoy adds no JWT metadata.
anonymous_request(method, path) := {"attributes": {"request": {"http": {"method": method, "path": path}}}}

role(name) := {"roles": [name]}

roles(names) := {"roles": names}

allowed(method, path, claims) if {
	authz.allow with input as request(method, path, claims)
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

allowed_with(config, method, path, claims) if {
	authz.allow with input as request(method, path, claims)
		with data.access_control as config
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

# Whether a single rule lets the caller GET /api/v1/things
rule_allows(rule, claims) if {
	authz.allow with input as request("GET", "/api/v1/things", claims)
		with data.access_control as fixture
		with data.AllAccessPermissionRules as {"rules": [rule]}
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

# --- rights -----------------------------------------------------------------------------------------------------------

test_rule_grants_its_rights if {
	allowed("GET", "/api/v1/things", role("reader"))
	not allowed("POST", "/api/v1/things", role("reader"))
	not allowed("GET", "/api/v1/things", role("guest"))
}

test_all_grants_every_right if {
	allowed("POST", "/api/v1/things", role("owner"))
	allowed("DELETE", thing("urn:thing:7"), role("owner"))
	allowed("GET", concat("", [thing("urn:thing:7"), "/$reference"]), role("owner"))
}

test_unknown_rights_grant_nothing if {
	not rule_allows(role_rule("x", ["read", "WRITE"], [{"ROUTE": "*"}]), role("x"))
}

# The rights come from the operation, not from the method: a request that addresses no operation is denied even
# for a role with all rights.
test_request_without_operation_is_denied if {
	not allowed("GET", "/api/v1/unknown", role("owner"))
	not allowed("DELETE", "/api/v1/things", role("owner"))
	not allowed("GET", "/api", role("owner"))
}

# Until it is checked whether the resource exists, PUT requires both CREATE and UPDATE. Rights of several rules add up.
test_create_or_update_requires_both_for_now if {
	not allowed("PUT", thing("urn:thing:7"), role("creator"))
	not allowed("PUT", thing("urn:thing:7"), role("updater"))
	allowed("PUT", thing("urn:thing:7"), roles(["creator", "updater"]))
	allowed("PUT", thing("urn:thing:7"), role("owner"))
}

# As in AAS Part 4, rules only allow: a more specific rule cannot take away what a broader one grants.
test_any_applicable_rule_grants if {
	allowed("GET", "/api/v1/admin/settings", role("reader"))
	allowed("GET", "/api/v1/admin/settings", role("admin"))
	not allowed("GET", "/api/v1/things", role("admin"))
}

test_method_is_case_insensitive if {
	allowed("get", "/api/v1/things", role("reader"))
}

# --- ROUTE objects ----------------------------------------------------------------------------------------------------

test_route_is_relative_to_the_api_base_path if {
	allowed("GET", "/api/v1/things", role("lister"))
	not rule_allows(role_rule("x", ["READ"], [{"ROUTE": "/api/v1/things"}]), role("x"))
}

test_route_without_asterisk_matches_exactly if {
	not allowed("GET", thing("urn:thing:1"), role("lister"))
	allowed("GET", "/api/v1/things/", role("lister"))
}

test_route_with_asterisk_matches_its_prefix if {
	allowed("GET", thing("urn:thing:1"), role("prefixer"))
	allowed("GET", concat("", [thing("urn:thing:1"), "/parts"]), role("prefixer"))
	not allowed("GET", "/api/v1/things", role("prefixer"))
}

# --- IDENTIFIABLE and DESCRIPTOR objects ------------------------------------------------------------------------------

test_listed_id_is_allowed if {
	allowed("GET", thing("urn:thing:1"), role("guest"))
}

test_unlisted_id_is_denied if {
	not allowed("GET", thing("urn:thing:2"), role("guest"))
}

test_wildcard_id_is_allowed if {
	allowed("GET", thing("urn:thing:42"), role("auditor"))
}

test_object_type_must_match if {
	not allowed("GET", thing("urn:thing:1"), role("describer"))
	not rule_allows(role_rule("x", ["READ"], [{"IDENTIFIABLE": "$aasdesc(\"*\")"}]), role("x"))
	not rule_allows(role_rule("x", ["READ"], [{"DESCRIPTOR": "$aas(\"*\")"}]), role("x"))
}

test_route_covers_subpaths if {
	allowed("GET", concat("", [thing("urn:thing:1"), "/attributes"]), role("guest"))
}

test_every_resource_in_path_must_be_allowed if {
	allowed("GET", concat("", [thing("urn:thing:1"), "/parts/", base64url.encode_no_pad("urn:part:1")]), role("guest"))
	not allowed("GET", concat("", [thing("urn:thing:1"), "/parts/", base64url.encode_no_pad("urn:part:2")]), role("guest"))
	not allowed("GET", concat("", [thing("urn:thing:2"), "/parts/", base64url.encode_no_pad("urn:part:1")]), role("guest"))
}

test_resource_rule_checks_right if {
	not allowed("DELETE", thing("urn:thing:1"), role("guest"))
}

# VIEW only shows that an object exists (e.g. its reference); it does not include READ, and READ does not include it.
test_view_and_read_are_separate_rights if {
	allowed("GET", concat("", [thing("urn:thing:1"), "/$reference"]), role("viewer"))
	not allowed("GET", thing("urn:thing:1"), role("viewer"))
	not allowed("GET", concat("", [thing("urn:thing:1"), "/$reference"]), role("guest"))
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

test_unsupported_objects_grant_nothing if {
	not rule_allows(role_rule("x", ["READ"], [{"REFERABLE": "$sme(\"*\").a"}]), role("x"))
	not rule_allows(role_rule("x", ["READ"], [{"FRAGMENT": "$aas#idShort"}]), role("x"))
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
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
		with opa.runtime as {"env": {"ACCESS_CONTROL_API_VERSION": "v2"}}
	not authz.allow with input as request("GET", thing("urn:thing:1"), role("guest"))
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
		with opa.runtime as {"env": {"ACCESS_CONTROL_API_VERSION": "v2"}}
}

# --- attributes -------------------------------------------------------------------------------------------------------

# Only the claim the rules name counts: scopes, groups or roles under another claim are not the "roles" claim.
test_only_the_named_claim_counts if {
	not allowed("GET", "/api/v1/things", {"scope": "openid reader"})
	not allowed("GET", "/api/v1/things", {"groups": ["reader", "/reader"]})
	not allowed("GET", "/api/v1/things", {"realm_access": {"roles": ["reader"]}})
}

test_single_valued_claim_is_compared_directly if {
	allowed("GET", "/api/v1/things", {"roles": "reader"})
}

test_malformed_claim_is_ignored if {
	not allowed("GET", "/api/v1/things", {"roles": [{"name": "reader"}]})
	not allowed("GET", "/api/v1/things", {"roles": ["reader", {"name": "x"}]})
}

# Every CLAIM of the ACL must be in the token, even if the formula does not use it.
test_every_listed_claim_must_be_present if {
	rule := {
		"ACL": {"ATTRIBUTES": [{"CLAIM": "roles"}, {"CLAIM": "email"}], "RIGHTS": ["READ"], "ACCESS": "ALLOW"},
		"OBJECTS": [{"ROUTE": "*"}],
		"FORMULA": {"$boolean": true},
	}
	rule_allows(rule, {"roles": [], "email": "a@b.c"})
	not rule_allows(rule, {"roles": []})
}

acl_rule(attributes) := {
	"ACL": {"ATTRIBUTES": attributes, "RIGHTS": ["READ"], "ACCESS": "ALLOW"},
	"OBJECTS": [{"ROUTE": "*"}],
	"FORMULA": {"$boolean": true},
}

test_rule_needs_a_subject if {
	not rule_allows(acl_rule([]), role("x"))
	not rule_allows(acl_rule([{"GLOBAL": "UTCNOW"}]), role("x"))
	not rule_allows(acl_rule([{"REFERENCE": "$sm(\"a\")#idShort"}]), role("x"))
	rule_allows(acl_rule([{"GLOBAL": "UTCNOW"}, {"CLAIM": "roles"}]), role("x"))
}

# A rule for ANONYMOUS grants public access: to callers without a token, and to callers with one.
test_anonymous_rule_applies_with_and_without_token if {
	authz.allow with input as anonymous_request("GET", "/api/v1/info")
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
	allowed("GET", "/api/v1/info", role("guest"))
	not authz.allow with input as anonymous_request("GET", "/api/v1/things")
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

test_missing_token_has_no_claims if {
	not allowed("GET", "/api/v1/things", {})
	not authz.allow with input as anonymous_request("GET", "/api/v1/things")
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

# --- rule structure ---------------------------------------------------------------------------------------------------

test_disabled_rule_is_ignored if {
	rule := role_rule("x", ["READ"], [{"ROUTE": "*"}])
	rule_allows(rule, role("x"))
	not rule_allows(object.union(rule, {"ACL": object.union(rule.ACL, {"ACCESS": "DISABLED"})}), role("x"))
}

# Without its filter, a rule with FILTER would grant more than intended.
test_rule_with_filter_is_ignored if {
	rule := role_rule("x", ["READ"], [{"ROUTE": "*"}])
	condition := {"$boolean": true}
	not rule_allows(object.union(rule, {"FILTER": {"FRAGMENT": "$aas#idShort", "CONDITION": condition}}), role("x"))
	not rule_allows(object.union(rule, {"FILTERLIST": [{"FRAGMENT": "$aas#idShort", "CONDITION": condition}]}), role("x"))
}

# Whether the rules document `access_rules` lets a reader GET /api/v1/things
reader_allowed_by(access_rules) if {
	authz.allow with input as request("GET", "/api/v1/things", role("reader"))
		with data.access_control as fixture
		with data.AllAccessPermissionRules as access_rules
}

test_definitions_are_resolved if {
	use_rule := {"USEACL": "read", "USEOBJECTS": ["whole_api"], "USEFORMULA": "reader"}
	definitions := object.remove(rules.AllAccessPermissionRules, ["rules"])
	reader_allowed_by(object.union(definitions, {"rules": [use_rule]}))
}

test_unknown_or_duplicate_definitions_are_ignored if {
	use_rule := {"USEACL": "read", "USEOBJECTS": ["whole_api"], "USEFORMULA": "reader"}
	definitions := object.remove(rules.AllAccessPermissionRules, ["rules"])
	unknown_acl := object.union(use_rule, {"USEACL": "unknown"})
	unknown_objects := object.union(use_rule, {"USEOBJECTS": ["whole_api", "unknown"]})
	not reader_allowed_by(object.union(definitions, {"rules": [unknown_acl]}))
	not reader_allowed_by(object.union(definitions, {"rules": [unknown_objects]}))
	not reader_allowed_by(object.union(definitions, {
		"DEFOBJECTS": array.concat(definitions.DEFOBJECTS, definitions.DEFOBJECTS),
		"rules": [use_rule],
	}))
}

test_rule_without_formula_is_ignored if {
	not rule_allows(object.remove(role_rule("x", ["READ"], [{"ROUTE": "*"}]), ["FORMULA"]), role("x"))
}

test_fails_closed_without_config_or_rules if {
	not authz.allow with input as request("GET", "/api/v1/things", role("owner"))
		with data.access_control as {}
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
	not authz.allow with input as request("GET", "/api/v1/things", role("owner"))
		with data.access_control as fixture
		with data.AllAccessPermissionRules as {}
}

# --- formulas ---------------------------------------------------------------------------------------------------------

holds(formula, claims) if {
	authz.formula_holds(formula) with input as request("GET", "/", claims)
}

claim(name) := {"$attribute": {"CLAIM": name}}

str(value) := {"$strVal": value}

num(value) := {"$numVal": value}

true_formula := {"$boolean": true}

false_formula := {"$boolean": false}

test_logical_operators if {
	holds({"$and": [true_formula, true_formula]}, {})
	not holds({"$and": [true_formula, false_formula]}, {})
	holds({"$or": [false_formula, true_formula]}, {})
	not holds({"$or": [false_formula, false_formula]}, {})
	holds({"$not": false_formula}, {})
	not holds({"$not": true_formula}, {})
}

test_comparisons if {
	claims := {"email": "user1@company.com", "level": 3}
	holds({"$eq": [claim("email"), str("user1@company.com")]}, claims)
	holds({"$ne": [claim("email"), str("other@company.com")]}, claims)
	holds({"$gt": [claim("level"), num(2)]}, claims)
	holds({"$le": [claim("level"), num(3)]}, claims)
	not holds({"$lt": [claim("level"), num(3)]}, claims)
	holds({"$contains": [claim("email"), str("@company")]}, claims)
	holds({"$starts-with": [claim("email"), str("user1")]}, claims)
	holds({"$ends-with": [claim("email"), str(".com")]}, claims)
	holds({"$regex": [claim("email"), str(`^[\w\.]+@company\.com$`)]}, claims)
	not holds({"$regex": [claim("email"), str(`^admin@`)]}, claims)
}

test_list_claim_stands_for_each_value if {
	claims := roles(["viewer", "editor"])
	holds({"$eq": [claim("roles"), str("editor")]}, claims)
	not holds({"$eq": [claim("roles"), str("admin")]}, claims)
	holds({"$ne": [claim("roles"), str("admin")]}, claims)
	not holds({"$ne": [claim("roles"), str("editor")]}, claims)
	holds({"$ne": [claim("roles"), str("admin")]}, roles([]))
	not holds({"$eq": [claim("roles"), str("admin")]}, roles([]))
}

# Invalid formulas (missing claims, mixed types, unsupported operators or operands, invalid patterns, too deep
# nesting) do not hold, and neither does their negation.
test_invalid_formulas_do_not_hold if {
	invalid := [
		{"$eq": [claim("missing"), str("x")]},
		{"$eq": [claim("level"), str("3")]},
		{"$gt": [{"$boolean": true}, {"$boolean": false}]},
		{"$contains": [claim("level"), num(3)]},
		{"$eq": [{"$field": "$sm#idShort"}, str("x")]},
		{"$eq": [{"$attribute": {"GLOBAL": "UTCNOW"}}, str("x")]},
		{"$match": [{"$eq": [{"$field": "$sm#idShort"}, str("x")]}]},
		{"$regex": [claim("email"), str("(")]},
		{"$and": [true_formula]},
		{"$eq": [str("x")]},
		{"$boolean": "true"},
		{"$and": [true_formula, true_formula], "$or": [true_formula, true_formula]},
	]
	every formula in invalid {
		not holds(formula, {"level": 3, "email": "a@b.c"})
		not holds({"$not": formula}, {"level": 3, "email": "a@b.c"})
	}
}

test_an_invalid_operand_invalidates_the_whole_formula if {
	not holds({"$or": [true_formula, {"$eq": [claim("missing"), str("x")]}]}, {})
}

not_not(formula) := {"$not": {"$not": formula}}

test_six_nested_operators_are_supported if {
	six := not_not(not_not(not_not(true_formula)))
	holds(six, {})
	not holds({"$not": six}, {})
	not holds(not_not(six), {})
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
		not allowed("GET", path, role("owner"))
		not allowed("GET", path, {})
	}
}

test_query_string_does_not_change_the_decision if {
	allowed("GET", concat("", [thing("urn:thing:1"), "?level=deep"]), role("guest"))
	not allowed("GET", "/api/v1/things?x=/ui", {})
}

# --- filtered collections ---------------------------------------------------------------------------------------------

# A request on a route that Envoy sends through the response filter.
filtered_request(method, path, claims) := {"attributes": {
	"request": {"http": {"method": method, "path": path}},
	"metadataContext": {"filterMetadata": {"envoy.filters.http.jwt_authn": {"jwt_payload": claims}}},
	"contextExtensions": {"response_filter": "true"},
}}

allowed_filtered(method, path, claims) if {
	authz.allow with input as filtered_request(method, path, claims)
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

test_collection_needs_the_response_filter if {
	allowed_filtered("GET", "/api/v1/things", role("guest"))
	not allowed("GET", "/api/v1/things", role("guest"))
}

test_collection_needs_a_rule_for_its_type if {
	not allowed_filtered("GET", "/api/v1/things", role("nobody"))
	not allowed_filtered("GET", "/api/v1/things", role("describer"))
	not allowed_filtered("GET", "/api/v1/things", {})
}

test_collection_needs_the_required_right if {
	not allowed_filtered("GET", "/api/v1/things", role("viewer"))
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
	decision := authz.response_filter with input as query
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

test_response_filter_lists_visible_items if {
	items := [
		{"type": "$aas", "id": "urn:thing:1"},
		{"type": "$aas", "id": "urn:thing:2"},
		{"type": "$sm", "id": "urn:part:1"},
		{"type": "$aasdesc", "id": "urn:thing:1"},
	]
	decision := filter_decision("/api/v1/things", role("guest"), items)
	decision.unfiltered == false
	decision.visible == [items[0], items[2]]
}

test_response_filter_passes_route_grants_unfiltered if {
	decision := filter_decision("/api/v1/things", role("reader"), [{"type": "$aas", "id": "urn:thing:2"}])
	decision.unfiltered == true
}

# The response filter treats a response as a collection only if the policy says so, by the same `collections`.
test_response_filter_is_told_whether_the_path_is_a_collection if {
	filter_decision("/api/v1/things", role("guest"), []).collection == true
	filter_decision(concat("", [thing("urn:thing:1"), "/parts"]), role("guest"), []).collection == true
	filter_decision(thing("urn:thing:1"), role("guest"), []).collection == false
	filter_decision("/api/v1/things/", role("guest"), []).collection == false
	filter_decision(concat("", [thing("urn:thing:1"), "/attributes/things"]), role("guest"), []).collection == false
}

test_response_filter_shows_nothing_without_claims if {
	decision := filter_decision("/api/v1/things", {}, [{"type": "$aas", "id": "urn:thing:1"}])
	decision.unfiltered == false
	decision.visible == []
}

# --- response to Envoy ------------------------------------------------------------------------------------------------

envoy_result(request_input) := result if {
	result := authz.result with input as request_input
		with data.access_control as fixture
		with data.AllAccessPermissionRules as rules.AllAccessPermissionRules
}

test_allowed_request_passes if {
	envoy_result(anonymous_request("GET", "/api/v1/info")) == {"allowed": true}
	envoy_result(request("GET", "/api/v1/things", role("reader"))) == {"allowed": true}
}

# RFC 6750, section 3: a request without credentials gets 401 and a challenge, so the client knows to log in.
test_denied_request_without_token_asks_for_one if {
	envoy_result(anonymous_request("GET", "/api/v1/things")) == {
		"allowed": false,
		"http_status": 401,
		"headers": {"WWW-Authenticate": "Bearer"},
	}
}

test_denied_request_with_token_is_forbidden if {
	envoy_result(request("GET", "/api/v1/things", role("nobody"))) == {"allowed": false, "http_status": 403}

	# A verified token without claims is still a token
	envoy_result(request("GET", "/api/v1/things", {})) == {"allowed": false, "http_status": 403}
}
