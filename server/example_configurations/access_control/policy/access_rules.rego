# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Evaluation of access rules in the JSON serialization of the AAS Access Rule Model (IDTA-01004 v3.1):
# https://industrialdigitaltwin.io/aas-specifications/IDTA-01004/v3.1/access-rule-model.html
#
# The rules are the document `{"AllAccessPermissionRules": ...}` in the policy data. A rule applies to a request if
#   - its ACL has ACCESS "ALLOW",
#   - its ATTRIBUTES fit the caller: every CLAIM is in the token, and there is a CLAIM or GLOBAL ANONYMOUS,
#   - its FORMULA is true.
# It then grants its RIGHTS on its OBJECTS. Rules only allow; what is not granted is denied.
#
# Supported subset (anything else makes a rule never apply, so unsupported rules can only deny, never allow):
#   - DEFATTRIBUTES, DEFACLS, DEFOBJECTS and DEFFORMULAS, used through USEATTRIBUTES, USEACL, USEOBJECTS and USEFORMULA
#     (definitions that use other definitions are not supported)
#   - OBJECTS: ROUTE, IDENTIFIABLE and DESCRIPTOR (not REFERABLE and FRAGMENT)
#   - FORMULA: $and, $or, $not, $boolean, and the comparisons $eq, $ne, $gt, $ge, $lt, $le, $contains,
#     $starts-with, $ends-with and $regex of $strVal, $numVal, $boolean and CLAIM attributes, with up to six nested
#     logical operators
#   - Rules with FILTER or FILTERLIST never apply: without the filter they would grant more than intended.
package envoy.authz

import rego.v1

default access_rules := {}

access_rules := data.AllAccessPermissionRules

# --- applicable rules ----------------------------------------------------------------------------------------------

applicable_rules contains {"rights": rule_rights(acl), "objects": objects} if {
	some rule in object.get(access_rules, "rules", [])
	not "FILTER" in object.keys(rule)
	not "FILTERLIST" in object.keys(rule)
	acl := rule_acl(rule)
	acl.ACCESS == "ALLOW"
	subject_matches(acl_attributes(acl))
	objects := rule_objects(rule)
	formula_holds(rule_formula(rule))
}

# A named definition (`DEFACLS`, ...) must exist exactly once.
definition(kind, name, field) := values[0] if {
	values := [def[field] |
		some def in object.get(access_rules, kind, [])
		def.name == name
	]
	count(values) == 1
}

rule_acl(rule) := rule.ACL if "ACL" in object.keys(rule)

rule_acl(rule) := definition("DEFACLS", rule.USEACL, "acl") if not "ACL" in object.keys(rule)

acl_attributes(acl) := array.concat(object.get(acl, "ATTRIBUTES", []), used_attributes(acl))

used_attributes(acl) := [] if not "USEATTRIBUTES" in object.keys(acl)

used_attributes(acl) := definition("DEFATTRIBUTES", acl.USEATTRIBUTES, "attributes")

rule_objects(rule) := array.concat(object.get(rule, "OBJECTS", []), used_objects(rule))

used_objects(rule) := [] if not "USEOBJECTS" in object.keys(rule)

used_objects(rule) := [item | some group in groups; some item in group] if {
	groups := [definition("DEFOBJECTS", name, "objects") | some name in rule.USEOBJECTS]
	count(groups) == count(rule.USEOBJECTS)
}

rule_formula(rule) := rule.FORMULA if "FORMULA" in object.keys(rule)

rule_formula(rule) := definition("DEFFORMULAS", rule.USEFORMULA, "formula") if not "FORMULA" in object.keys(rule)

# --- rights --------------------------------------------------------------------------------------------------------

# The rights of the AAS Access Rule Model; "ALL" stands for all of them.
all_rights := {"CREATE", "READ", "UPDATE", "DELETE", "EXECUTE", "VIEW"}

rule_rights(acl) := {right |
	some granted in acl.RIGHTS
	some right in expand_right(granted)
}

expand_right("ALL") := all_rights

expand_right(right) := {right} if right in all_rights

# --- attributes ----------------------------------------------------------------------------------------------------

# The rule needs a subject: a CLAIM or GLOBAL ANONYMOUS. Every CLAIM must be in the token. A rule for ANONYMOUS grants
# public access, so it applies to callers with and without a token. Time attributes may be listed but do not identify
# a subject; other attributes (REFERENCE) are not supported.
subject_matches(items) if {
	every attribute in items {
		attribute_available(attribute)
	}
	some attribute in items
	subject_attribute(attribute)
}

attribute_available(attribute) if attribute.CLAIM in object.keys(claims)

attribute_available(attribute) if attribute.GLOBAL in {"ANONYMOUS", "LOCALNOW", "UTCNOW", "CLIENTNOW"}

subject_attribute(attribute) if is_string(attribute.CLAIM)

subject_attribute(attribute) if attribute.GLOBAL == "ANONYMOUS"

# --- objects -------------------------------------------------------------------------------------------------------

# A ROUTE is the path of an API operation below the API base path (see `api_path` in rights.rego), e.g. "/shells".
# It matches that path exactly; ending in "*", it matches every path that starts with the part before the "*" (so
# "/shells/*" does not match "/shells" itself); "*" alone matches every route.
route_matches(route, path) if {
	not endswith(route, "*")
	route == path
}

route_matches(route, path) if {
	endswith(route, "*")
	startswith(path, trim_right(route, "*"))
}

# IDENTIFIABLE and DESCRIPTOR objects name a type (e.g. "$aas") and an identifier, or "*" for all of that type.
object_scopes := {
	"IDENTIFIABLE": {"$aas", "$sm", "$cd"},
	"DESCRIPTOR": {"$aasdesc", "$smdesc"},
}

parsed_object(item) := {"type": match[1], "id": match[2]} if {
	some kind, literal in item
	is_string(literal)
	[match] := regex.find_all_string_submatch_n(`^(\$[a-z]+)\("(.+)"\)$`, literal, 1)
	match[1] in object_scopes[kind]
}

object_covers(item, resource) if {
	target := parsed_object(item)
	target.type == resource.type
	target.id in {"*", resource.id}
}

# Rights granted by applicable rules with a ROUTE that matches the request
route_rights contains right if {
	some rule in applicable_rules
	some item in rule.objects
	route_matches(item.ROUTE, api_path)
	some right in rule.rights
}

# Rights granted by applicable rules on one resource ({"type": ..., "id": ...})
resource_rights(resource) := {right |
	some rule in applicable_rules
	some item in rule.objects
	object_covers(item, resource)
	some right in rule.rights
}

# Rights granted by applicable rules on at least one resource of a type
type_rights(type) := {right |
	some rule in applicable_rules
	some item in rule.objects
	parsed_object(item).type == type
	some right in rule.rights
}

# --- formulas ------------------------------------------------------------------------------------------------------

# Rego has no recursion, so each level evaluates the logical operators whose operands the level below evaluates. A
# formula that uses anything unsupported, refers to a missing claim or compares values of different types has no
# value and therefore does not hold, as the specification requires for invalid formulas.
formula_holds(formula) if formula_value_6(formula) == true

formula_value_0(e) := leaf_value(e)

formula_value_1(e) := leaf_value(e)

formula_value_1(e) := value if {
	[operator, operands] := logical_operation(e)
	value := combine(operator, operands, [formula_value_0(x) | some x in operands])
}

formula_value_2(e) := leaf_value(e)

formula_value_2(e) := value if {
	[operator, operands] := logical_operation(e)
	value := combine(operator, operands, [formula_value_1(x) | some x in operands])
}

formula_value_3(e) := leaf_value(e)

formula_value_3(e) := value if {
	[operator, operands] := logical_operation(e)
	value := combine(operator, operands, [formula_value_2(x) | some x in operands])
}

formula_value_4(e) := leaf_value(e)

formula_value_4(e) := value if {
	[operator, operands] := logical_operation(e)
	value := combine(operator, operands, [formula_value_3(x) | some x in operands])
}

formula_value_5(e) := leaf_value(e)

formula_value_5(e) := value if {
	[operator, operands] := logical_operation(e)
	value := combine(operator, operands, [formula_value_4(x) | some x in operands])
}

formula_value_6(e) := leaf_value(e)

formula_value_6(e) := value if {
	[operator, operands] := logical_operation(e)
	value := combine(operator, operands, [formula_value_5(x) | some x in operands])
}

# $and and $or take at least two operands, $not one.
logical_operation(e) := [operator, operands] if {
	count(e) == 1
	some operator, operands in e
	operator in {"$and", "$or"}
	is_array(operands)
	count(operands) >= 2
}

logical_operation(e) := ["$not", [e["$not"]]] if count(e) == 1

# Every operand must have a value.
combine(operator, operands, values) := logical_value(operator, values) if count(values) == count(operands)

logical_value("$and", values) := false if false in values

logical_value("$and", values) if not false in values

logical_value("$or", values) if true in values

logical_value("$or", values) := false if not true in values

logical_value("$not", [value]) := not_value(value)

not_value(true) := false

not_value(false) := true

leaf_value(e) := e["$boolean"] if {
	count(e) == 1
	is_boolean(e["$boolean"])
}

leaf_value(e) := comparison_value(operator, left, right) if {
	count(e) == 1
	some operator, operands in e
	is_array(operands)
	[left_operand, right_operand] := operands
	left := operand_values(left_operand)
	right := operand_values(right_operand)
	comparable(operator, left | right)
	valid_patterns(operator, right)
}

# A list-valued claim (e.g. the roles of the caller) stands for each of its values: $eq holds if any value is equal,
# $ne if none is, and the other comparisons if they hold for any value.
comparison_value("$ne", left, right) := false if any_holds("$eq", left, right)

comparison_value("$ne", left, right) if not any_holds("$eq", left, right)

comparison_value(operator, left, right) if {
	operator != "$ne"
	any_holds(operator, left, right)
}

comparison_value(operator, left, right) := false if {
	operator != "$ne"
	not any_holds(operator, left, right)
}

any_holds(operator, left, right) if {
	some x in left
	some y in right
	holds(operator, x, y)
}

holds("$eq", x, y) if x == y

holds("$gt", x, y) if x > y

holds("$ge", x, y) if x >= y

holds("$lt", x, y) if x < y

holds("$le", x, y) if x <= y

holds("$contains", x, y) if contains(x, y)

holds("$starts-with", x, y) if startswith(x, y)

holds("$ends-with", x, y) if endswith(x, y)

holds("$regex", x, y) if regex.match(y, x)

# All values of a comparison must have the same type, and a type the operator applies to.
comparable(operator, values) if {
	types := {type_name(value) | some value in values}
	count(types) <= 1
	every type in types {
		type in operator_types[operator]
	}
}

operator_types := {
	"$eq": {"string", "number", "boolean"},
	"$ne": {"string", "number", "boolean"},
	"$gt": {"string", "number"},
	"$ge": {"string", "number"},
	"$lt": {"string", "number"},
	"$le": {"string", "number"},
	"$contains": {"string"},
	"$starts-with": {"string"},
	"$ends-with": {"string"},
	"$regex": {"string"},
}

valid_patterns(operator, _) if operator != "$regex"

valid_patterns("$regex", patterns) if {
	every pattern in patterns {
		regex.is_valid(pattern)
	}
}

operand_values(v) := {v["$strVal"]} if {
	count(v) == 1
	is_string(v["$strVal"])
}

operand_values(v) := {v["$numVal"]} if {
	count(v) == 1
	is_number(v["$numVal"])
}

operand_values(v) := {v["$boolean"]} if {
	count(v) == 1
	is_boolean(v["$boolean"])
}

operand_values(v) := claim_values(v["$attribute"].CLAIM) if {
	count(v) == 1
	count(v["$attribute"]) == 1
}

claim_values(name) := {value} if {
	value := claims[name]
	is_scalar(value)
}

claim_values(name) := values if {
	is_array(claims[name])
	values := {value | some value in claims[name]; is_scalar(value)}
	count(values) == count({value | some value in claims[name]})
}

is_scalar(value) if type_name(value) in {"string", "number", "boolean"}
