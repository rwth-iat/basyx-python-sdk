package envoy.authz

import rego.v1

default allow := false

attributes := object.get(input, "attributes", {})
http_request := object.get(object.get(attributes, "request", {}), "http", {})
metadata_context := object.get(attributes, "metadataContext", object.get(attributes, "metadata_context", {}))
filter_metadata := object.get(metadata_context, "filterMetadata", object.get(metadata_context, "filter_metadata", {}))
jwt_metadata := object.get(filter_metadata, "envoy.filters.http.jwt_authn", {})
claims := object.get(jwt_metadata, "jwt_payload", {})

raw_path := object.get(http_request, "path", "/")
request_path := split(raw_path, "?")[0]
request_method := upper(object.get(http_request, "method", ""))

allow if {
	public_path
}

allow if {
	count(matching_rules) > 0
	some rule in effective_rules
	role_matches(rule)
}

allow if {
	count(requested_resources) > 0
	not denied_requested_resource
}

public_path if {
	some prefix in object.get(data.access_control, "public_path_prefixes", [])
	prefix_matches(prefix)
	not protected_api_path
}

protected_api_path if {
	some rule in data.access_control.rules
	path_matches(rule)
}

matching_rules contains rule if {
	rule := data.access_control.rules[_]
	method_matches(rule)
	path_matches(rule)
}

effective_rules contains rule if {
	some rule in matching_rules
	count(object.get(rule, "path_prefix", "/")) == max_prefix_length
}

max_prefix_length := max([count(object.get(rule, "path_prefix", "/")) | some rule in matching_rules])

method_matches(rule) if {
	some method in object.get(rule, "methods", [])
	upper(method) == request_method
}

path_matches(rule) if {
	prefix := object.get(rule, "path_prefix", "/")
	prefix_matches(prefix)
}

prefix_matches(prefix) if {
	prefix == "/"
	request_path == "/"
}

prefix_matches(prefix) if {
	prefix != "/"
	request_path == prefix
}

prefix_matches(prefix) if {
	prefix != "/"
	startswith(request_path, sprintf("%s/", [prefix]))
}

role_matches(rule) if {
	some required_role in object.get(rule, "roles", [])
	required_role in token_roles
}

token_roles contains role if {
	role := object.get(object.get(claims, "realm_access", {}), "roles", [])[_]
}

token_roles contains role if {
	role := object.get(claims, "roles", [])[_]
}

token_roles contains group if {
	group := object.get(claims, "groups", [])[_]
}

token_roles contains role if {
	group := object.get(claims, "groups", [])[_]
	startswith(group, "/")
	role := substring(group, 1, -1)
}

token_roles contains scope if {
	scope := split(object.get(claims, "scope", ""), " ")[_]
	scope != ""
}

denied_requested_resource if {
	some requested_resource in requested_resources
	not requested_resource_allowed(requested_resource)
}

requested_resource_allowed(requested_resource) if {
	some rule in object.get(data.access_control, "resource_rules", [])
	method_matches(rule)
	role_matches(rule)
	some template in object.get(rule, "path_templates", [])
	requested_resource.template == template
	requested_resource.id in object.get(rule, "ids", [])
}

requested_resource_allowed(requested_resource) if {
	some rule in object.get(data.access_control, "resource_rules", [])
	method_matches(rule)
	role_matches(rule)
	"*" in object.get(rule, "ids", [])
	some template in object.get(rule, "path_templates", [])
	requested_resource.template == template
}

path_segments := split(request_path, "/")

requested_resources contains {"template": "/repository/api/v3.1/shells/{aas_id}", "id": id} if {
	path_segments[1] == "repository"
	path_segments[4] == "shells"
	id := path_segments[5]
	id != "$reference"
}

requested_resources contains {"template": "/repository/api/v3.1/shells/{aas_id}/submodels/{submodel_id}", "id": id} if {
	path_segments[1] == "repository"
	path_segments[4] == "shells"
	path_segments[6] == "submodels"
	id := path_segments[7]
}

requested_resources contains {"template": "/repository/api/v3.1/submodels/{submodel_id}", "id": id} if {
	path_segments[1] == "repository"
	path_segments[4] == "submodels"
	id := path_segments[5]
	not startswith(id, "$")
}

requested_resources contains {"template": "/registry/api/v3.1/shell-descriptors/{aas_id}", "id": id} if {
	path_segments[1] == "registry"
	path_segments[4] == "shell-descriptors"
	id := path_segments[5]
}

requested_resources contains {"template": "/registry/api/v3.1/shell-descriptors/{aas_id}/submodel-descriptors/{submodel_id}", "id": id} if {
	path_segments[1] == "registry"
	path_segments[4] == "shell-descriptors"
	path_segments[6] == "submodel-descriptors"
	id := path_segments[7]
}

requested_resources contains {"template": "/registry/api/v3.1/submodel-descriptors/{submodel_id}", "id": id} if {
	path_segments[1] == "registry"
	path_segments[4] == "submodel-descriptors"
	id := path_segments[5]
}

requested_resources contains {"template": "/discovery/api/v3.1/lookup/shells/{aas_id}", "id": id} if {
	path_segments[1] == "discovery"
	path_segments[4] == "lookup"
	path_segments[5] == "shells"
	id := path_segments[6]
}
