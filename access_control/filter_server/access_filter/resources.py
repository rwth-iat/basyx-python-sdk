# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Where resources appear in AAS API responses (AAS Part 2), and how to remove the ones a caller may not see.

This module knows the shape of the responses, not the access rules: which resources are visible is decided elsewhere
and passed in as ``keep``.
"""
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

#: A resource as the policy sees it: (type, identifier), e.g. ("aas", "https://example.org/Test_AssetAdministrationShell")
Resource = tuple[str, str]


@dataclass(frozen=True)
class Collection:
    #: Resource type of the entries
    resource_type: str
    #: How an entry names its resource: "object" (``id`` attribute), "reference" (last key) or "identifier" (string)
    entry_kind: str


# Collection endpoints by their last path segment(s). Their responses are {"result": [...], "paging_metadata": {...}}.
_COLLECTIONS: dict[tuple[str, ...], Collection] = {
    ("shells",): Collection("aas", "object"),
    ("submodels",): Collection("submodel", "object"),
    ("submodel-refs",): Collection("submodel", "reference"),
    ("shell-descriptors",): Collection("aas", "object"),
    ("submodel-descriptors",): Collection("submodel", "object"),
    ("lookup", "shells"): Collection("aas", "identifier"),
}


def collection_for(path: str) -> Collection | None:
    """The collection a request path lists, or None if the path addresses something else."""
    segments = tuple(segment for segment in path.split("?", 1)[0].split("/") if segment)
    # Longest suffix first, so that ".../lookup/shells" is not taken for ".../shells".
    for suffix, collection in sorted(_COLLECTIONS.items(), key=lambda item: -len(item[0])):
        if segments[-len(suffix):] == suffix:
            return collection
    return None


def filter_response(payload: Any, collection: Collection | None, keep: Callable[[Resource], bool]) -> Any:
    """
    Return a copy of ``payload`` without the resources for which ``keep`` returns False.

    For a collection, entries are removed, and so are entries whose resource cannot be determined (fail closed).
    In every remaining object, references to submodels (``submodels`` of a shell) and nested submodel descriptors
    (``submodelDescriptors`` of a shell descriptor) are filtered as well.
    """
    if collection is not None:
        if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
            raise ValueError("collection response without a 'result' list")
        result = deepcopy(payload)
        result["result"] = [
            _filter_nested(entry, keep)
            for entry in payload["result"]
            if (resource := entry_resource(entry, collection)) is not None and keep(resource)
        ]
        return result
    return _filter_nested(payload, keep)


def resources_in(payload: Any, collection: Collection | None) -> list[Resource]:
    """All resources ``filter_response`` would ask about, in order and without duplicates."""
    found: dict[Resource, None] = {}

    def record(resource: Resource) -> bool:
        found[resource] = None
        return True

    filter_response(payload, collection, record)
    return list(found)


def entry_resource(entry: Any, collection: Collection) -> Resource | None:
    """The resource a collection entry stands for, or None if it cannot be determined."""
    if collection.entry_kind == "object":
        identifier = entry.get("id") if isinstance(entry, dict) else None
    elif collection.entry_kind == "reference":
        identifier = reference_target(entry)
    else:
        identifier = entry
    if isinstance(identifier, str) and identifier:
        return collection.resource_type, identifier
    return None


def reference_target(reference: Any) -> str | None:
    """The identifier a model reference points to: the value of its last key."""
    if not isinstance(reference, dict):
        return None
    keys = reference.get("keys")
    if not isinstance(keys, list) or not keys or not isinstance(keys[-1], dict):
        return None
    value = keys[-1].get("value")
    return value if isinstance(value, str) else None


def _filter_nested(value: Any, keep: Callable[[Resource], bool]) -> Any:
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if isinstance(value.get("submodels"), list):
        result["submodels"] = [
            reference for reference in value["submodels"]
            if (target := reference_target(reference)) is not None and keep(("submodel", target))
        ]
    if isinstance(value.get("submodelDescriptors"), list):
        result["submodelDescriptors"] = [
            descriptor for descriptor in value["submodelDescriptors"]
            if isinstance(descriptor, dict) and isinstance(descriptor.get("id"), str)
            and keep(("submodel", descriptor["id"]))
        ]
    return result
