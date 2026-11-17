# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import unittest

from access_filter import resources
from access_filter.resources import Resource

API = "/repository/api/v3.1"


def submodel_reference(identifier: str) -> dict:
    return {"type": "ModelReference", "keys": [{"type": "Submodel", "value": identifier}]}


SHELL = {
    "id": "urn:aas:1",
    "modelType": "AssetAdministrationShell",
    "submodels": [submodel_reference("urn:sm:visible"), submodel_reference("urn:sm:hidden")],
}


def keep_visible(resource: Resource) -> bool:
    return resource[1] in ("urn:aas:1", "urn:sm:visible", "urn:aas:visible")


class CollectionForTest(unittest.TestCase):
    def test_collections_by_path(self) -> None:
        cases = {
            f"{API}/shells": ("aas", "object"),
            f"{API}/shells?limit=2": ("aas", "object"),
            f"{API}/submodels": ("submodel", "object"),
            f"{API}/shells/abc/submodel-refs": ("submodel", "reference"),
            "/registry/api/v3.1/shell-descriptors": ("aas", "object"),
            "/registry/api/v3.1/shell-descriptors/abc/submodel-descriptors": ("submodel", "object"),
            "/registry/api/v3.1/submodel-descriptors": ("submodel", "object"),
            "/discovery/api/v3.1/lookup/shells": ("aas", "identifier"),
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                collection = resources.collection_for(path)
                assert collection is not None
                self.assertEqual(expected, (collection.resource_type, collection.entry_kind))

    def test_single_objects_are_not_collections(self) -> None:
        for path in (f"{API}/shells/abc", f"{API}/submodels/abc/submodel-elements/x", f"{API}/description"):
            with self.subTest(path=path):
                self.assertIsNone(resources.collection_for(path))


class FilterResponseTest(unittest.TestCase):
    def test_collection_entries_and_nested_references_are_filtered(self) -> None:
        payload = {"paging_metadata": {}, "result": [SHELL, {"id": "urn:aas:2", "submodels": []}]}
        collection = resources.collection_for(f"{API}/shells")
        filtered = resources.filter_response(payload, collection, keep_visible)
        self.assertEqual(["urn:aas:1"], [shell["id"] for shell in filtered["result"]])
        self.assertEqual([submodel_reference("urn:sm:visible")], filtered["result"][0]["submodels"])

    def test_input_is_not_modified(self) -> None:
        payload = {"result": [SHELL]}
        resources.filter_response(payload, resources.collection_for(f"{API}/shells"), keep_visible)
        self.assertEqual(2, len(SHELL["submodels"]))

    def test_single_shell_keeps_only_visible_submodel_references(self) -> None:
        filtered = resources.filter_response(SHELL, None, keep_visible)
        self.assertEqual("urn:aas:1", filtered["id"])
        self.assertEqual([submodel_reference("urn:sm:visible")], filtered["submodels"])

    def test_shell_descriptor_keeps_only_visible_submodel_descriptors(self) -> None:
        descriptor = {"id": "urn:aas:1", "submodelDescriptors": [{"id": "urn:sm:visible"}, {"id": "urn:sm:hidden"}]}
        filtered = resources.filter_response(descriptor, None, keep_visible)
        self.assertEqual([{"id": "urn:sm:visible"}], filtered["submodelDescriptors"])

    def test_submodel_refs_and_discovery_identifiers(self) -> None:
        refs = {"result": [submodel_reference("urn:sm:visible"), submodel_reference("urn:sm:hidden")]}
        filtered = resources.filter_response(refs, resources.collection_for(f"{API}/shells/x/submodel-refs"),
                                             keep_visible)
        self.assertEqual([submodel_reference("urn:sm:visible")], filtered["result"])
        ids = {"result": ["urn:aas:visible", "urn:aas:hidden"]}
        filtered = resources.filter_response(ids, resources.collection_for("/discovery/api/v3.1/lookup/shells"),
                                             keep_visible)
        self.assertEqual(["urn:aas:visible"], filtered["result"])

    def test_entries_without_identifier_are_dropped(self) -> None:
        payload = {"result": [{"idShort": "no id"}, {"id": ""}, "not an object", SHELL]}
        filtered = resources.filter_response(payload, resources.collection_for(f"{API}/shells"), lambda _: True)
        self.assertEqual(["urn:aas:1"], [shell["id"] for shell in filtered["result"]])

    def test_malformed_references_are_dropped(self) -> None:
        references = [{"keys": []}, {"keys": "x"}, "x", submodel_reference("urn:sm:visible")]
        shell = {"id": "urn:aas:1", "submodels": references}
        filtered = resources.filter_response(shell, None, lambda _: True)
        self.assertEqual([submodel_reference("urn:sm:visible")], filtered["submodels"])

    def test_collection_without_result_list_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            resources.filter_response({"messages": []}, resources.collection_for(f"{API}/shells"), keep_visible)

    def test_resources_in_lists_entries_and_nested_resources_once(self) -> None:
        payload = {"result": [SHELL, SHELL]}
        found = resources.resources_in(payload, resources.collection_for(f"{API}/shells"))
        self.assertEqual([("aas", "urn:aas:1"), ("submodel", "urn:sm:visible"), ("submodel", "urn:sm:hidden")], found)

    def test_other_objects_pass_unchanged(self) -> None:
        submodel = {"id": "urn:sm:1", "submodelElements": [{"idShort": "x"}]}
        self.assertEqual(submodel, resources.filter_response(submodel, None, lambda _: False))
        self.assertEqual([1, 2], resources.filter_response([1, 2], None, lambda _: False))
