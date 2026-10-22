# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Generic authorization policy for Envoy's ext_authz filter.
#
# The policy contains no application specific values: paths, roles and resource identifiers come from
# `data.access_control` (see the examples' policy_data/data.json). A request is allowed if its path is canonical and
#   1. it is a public path, or
#   2. a server-level rule for the longest matching path prefix grants the method to one of the caller's roles, or
#   3. every resource identified in the path (via `routes`) is granted to one of the caller's roles by a resource rule.
package envoy.authz

import rego.v1

default allow := false

default config := {}

config := data.access_control

# --- request -------------------------------------------------------------------------------------------------------

attributes := object.get(input, "attributes", {})

http_request := object.get(object.get(attributes, "request", {}), "http", {})

# The OPA-Envoy plugin delivers these keys in camelCase; snake_case is kept as a fallback.
metadata_context := object.get(attributes, "metadataContext", object.get(attributes, "metadata_context", {}))

filter_metadata := object.get(metadata_context, "filterMetadata", object.get(metadata_context, "filter_metadata", {}))

claims := object.get(filter_metadata, ["envoy.filters.http.jwt_authn", "jwt_payload"], {})

request_path := split(object.get(http_request, "path", "/"), "?")[0]

request_method := upper(object.get(http_request, "method", ""))

# --- decision ------------------------------------------------------------------------------------------------------

allow if {
	valid_path
	public_path
}

allow if {
	valid_path
	some rule in effective_rules
	role_matches(rule)
}

allow if {
	valid_path
	not undecodable_resource_id
	count(requested_resources) > 0
	every resource in requested_resources {
		resource_allowed(resource)
	}
}

# --- canonical paths -----------------------------------------------------------------------------------------------

# Defense in depth: Envoy normalizes paths (normalize_path, merge_slashes), so these should never arrive here. If they
# do, the gateway is misconfigured and path-based rules cannot be trusted, so the request is denied.
valid_path if not invalid_path

invalid_path if contains(request_path, "//")

invalid_path if contains(request_path, "\\")

invalid_path if {
	some segment in split(request_path, "/")
	segment in {".", ".."}
}

invalid_path if regex.match(`(?i)%(2e|2f|5c|25)`, request_path)

# --- public paths --------------------------------------------------------------------------------------------------

public_path if request_path in object.get(config, "public_paths", [])

public_path if {
	some prefix in object.get(config, "public_path_prefixes", [])
	prefix_matches(prefix, request_path)
}

# --- server-level rules --------------------------------------------------------------------------------------------

# Rules matching method and path; only those with the longest path prefix count, so a specific rule (e.g. "/admin")
# overrides a broad one (e.g. "/").
matching_rules contains rule if {
	some rule in object.get(config, "rules", [])
	method_matches(rule)
	prefix_matches(object.get(rule, "path_prefix", "/"), request_path)
}

effective_rules contains rule if {
	some rule in matching_rules
	count(object.get(rule, "path_prefix", "/")) == max([count(object.get(r, "path_prefix", "/")) | some r in matching_rules])
}

# "/" matches every path; any other prefix matches itself and everything below it, but not "/repository-internal"
# for "/repository".
prefix_matches("/", _) := true

prefix_matches(prefix, path) if {
	prefix != "/"
	path == prefix
}

prefix_matches(prefix, path) if {
	prefix != "/"
	startswith(path, concat("", [prefix, "/"]))
}

# --- resource-level rules ------------------------------------------------------------------------------------------

# Each route is a path template; a placeholder such as "{aas}" names the resource type of that path segment. A route
# matches a request whose path starts with the template, so "/shells/{aas}" also covers "/shells/{aas}/submodel-refs".
# "{api_version}" is replaced by `api_version`. Identifiers in the path are base64url-encoded (AAS Part 2) and are
# compared in decoded form, so the rules contain readable identifiers.
api_version := object.get(config, "api_version", "")

route_segments contains segments if {
	some route in object.get(config, "routes", [])
	segments := split(trim_prefix(replace(route, "{api_version}", api_version), "/"), "/")
}

path_segments := split(trim_prefix(request_path, "/"), "/")

matched_placeholders contains [type, value] if {
	some segments in route_segments
	count(path_segments) >= count(segments)
	every i, segment in segments {
		segment_matches(segment, path_segments[i])
	}
	some i, segment in segments
	is_placeholder(segment)
	type := trim(segment, "{}")
	value := path_segments[i]
}

requested_resources contains {"type": type, "id": base64url.decode(value)} if {
	some placeholder in matched_placeholders
	[type, value] := placeholder
}

# An identifier that is not valid base64url cannot be checked against the rules, so the resource rules do not apply.
undecodable_resource_id if {
	some placeholder in matched_placeholders
	not base64url.decode(placeholder[1])
}

is_placeholder(segment) if {
	startswith(segment, "{")
	endswith(segment, "}")
}

# Placeholders never match empty segments or operation segments such as "$reference" or "$metadata".
segment_matches(segment, value) if {
	is_placeholder(segment)
	value != ""
	not startswith(value, "$")
}

segment_matches(segment, value) if {
	not is_placeholder(segment)
	segment == value
}

resource_allowed(resource) if {
	some rule in object.get(config, "resource_rules", [])
	rule.resource == resource.type
	method_matches(rule)
	role_matches(rule)
	id_matches(rule, resource.id)
}

id_matches(rule, _) if "*" in object.get(rule, "ids", [])

id_matches(rule, id) if id in object.get(rule, "ids", [])

id_matches(rule, id) if {
	some prefix in object.get(rule, "id_prefixes", [])
	startswith(id, prefix)
}

# --- roles ---------------------------------------------------------------------------------------------------------

method_matches(rule) if request_method in {upper(method) | some method in object.get(rule, "methods", [])}

role_matches(rule) if {
	some required_role in object.get(rule, "roles", [])
	required_role in token_roles
}

# Roles come only from the identity provider's role claim (`role_claim`, a dot-separated path into the token).
# OAuth scopes and group names are not roles: a client may request any scope it is allowed to, and a scope or group
# named like a role (e.g. "admin") must not grant that role's rights.
role_claim := split(object.get(config, "role_claim", "realm_access.roles"), ".")

token_roles contains role if {
	roles := object.get(claims, role_claim, [])
	is_array(roles)
	some role in roles
	is_string(role)
}
