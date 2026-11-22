# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Generic authorization policy for Envoy's ext_authz filter.
#
# The policy contains no application specific values. Who may do what is set by access rules of the AAS Access Rule
# Model (IDTA-01004, see access_rules.rego); paths and resource types come from `data.access_control` (see the
# examples' policy_data). The rights a request requires follow from the operation it calls (see rights.rego). A request
# is allowed if its path is canonical and
#   1. it is a public path, or
#   2. rules with a ROUTE that matches the request grant the required rights, or
#   3. for every resource identified in the path (via `routes`), rules with a matching IDENTIFIABLE or DESCRIPTOR grant
#      the required rights, or
#   4. it reads a collection (via `collections`) through the response filter, which removes the entries the caller
#      may not see (see `response_filter`).
package envoy.authz

import rego.v1

default allow := false

default config := {}

config := data.access_control

# The API version may differ per environment: ACCESS_CONTROL_API_VERSION in the environment of the OPA process takes
# precedence over `api_version` in data.access_control.
runtime_env := object.get(opa.runtime(), "env", {})

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
	grants(route_rights)
}

allow if {
	valid_path
	not undecodable_resource_id
	count(requested_resources) > 0
	every resource in requested_resources {
		resource_allowed(resource)
	}
}

allow if {
	valid_path
	filtered_collection_allowed
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

# "/" matches every path; any other prefix matches itself and everything below it, but not "/uix" for "/ui".
prefix_matches("/", _) := true

prefix_matches(prefix, path) if {
	prefix != "/"
	path == prefix
}

prefix_matches(prefix, path) if {
	prefix != "/"
	startswith(path, concat("", [prefix, "/"]))
}

# --- resources -----------------------------------------------------------------------------------------------------

# Each route is a path template; a placeholder such as "{$aas}" names the object type of that path segment, as in
# IDENTIFIABLE ("$aas", "$sm", "$cd") and DESCRIPTOR ("$aasdesc", "$smdesc") objects of the access rules. A route
# matches a request whose path starts with the template, so "/shells/{$aas}" also covers "/shells/{$aas}/submodel-refs".
# "{api_version}" is replaced by `api_version`. Identifiers in the path are base64url-encoded (AAS Part 2) and are
# compared in decoded form, so the rules contain readable identifiers.
api_version := object.get(runtime_env, "ACCESS_CONTROL_API_VERSION", object.get(config, "api_version", ""))

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

resource_allowed(resource) if grants(resource_rights(resource))

# --- filtered collections ------------------------------------------------------------------------------------------

# A collection endpoint (e.g. GET /shells) returns many resources at once. A caller with the required rights on at
# least some resources of its type may call it, but only on routes where Envoy sends the request through the response
# filter and marks it with the context extension response_filter=true; the filter then removes what the caller may not
# see. Without that mark, e.g. after a routing mistake, this does not apply and the request is denied.
context_extensions := object.get(attributes, "contextExtensions", object.get(attributes, "context_extensions", {}))

through_response_filter if object.get(context_extensions, "response_filter", "") == "true"

filtered_collection_allowed if {
	through_response_filter
	request_method == "GET"
	some collection in object.get(config, "collections", [])
	collection_matches(collection.path)
	not undecodable_resource_id
	every resource in requested_resources {
		resource_allowed(resource)
	}
	grants(type_rights(collection.resource))
}

# Unlike routes, a collection path matches only exactly (no subpaths).
collection_matches(template) if {
	segments := split(trim_prefix(replace(template, "{api_version}", api_version), "/"), "/")
	count(segments) == count(path_segments)
	every i, segment in segments {
		segment_matches(segment, path_segments[i])
	}
}

# Decision for the response filter. The filter sends the original request in the same shape as Envoy, plus `items`:
# the resources found in the response, as {"type": ..., "id": ...}. With "unfiltered", a rule with a matching ROUTE
# grants the request and the response may pass unchanged; otherwise only the items in "visible" may be shown.
response_filter := {"unfiltered": unfiltered, "visible": visible_items}

default unfiltered := false

unfiltered if {
	valid_path
	grants(route_rights)
}

visible_items := [item |
	some item in object.get(input, "items", [])
	resource_allowed(item)
]

# --- rights --------------------------------------------------------------------------------------------------------

# Granted rights must cover every right the operation requires. A request that addresses no operation requires no
# right and is never granted. For operations that require CREATE or UPDATE depending on whether the resource exists,
# the existence is not checked yet, so both are required.
grants(rights) if {
	count(required_rights) > 0
	every right in required_rights {
		right in rights
	}
}
