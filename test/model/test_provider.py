# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import unittest
from typing import List, Optional, Any

from basyx.aas import model
from basyx.aas.model import Protocol
from basyx.aas.backend import backends
from unittest import mock


class ExampleRefereableWithNamespace(model.Referable, model.UniqueIdShortNamespace):
    def __init__(self):
        super().__init__()


class MockBackend(backends.ObjectBackend):
    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Any) -> None: ...

    @classmethod
    def commit_object(cls,
                      committed_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Any) -> None: ...

    update_object = mock.Mock()
    commit_object = mock.Mock()


class ExampleIdentifiable(model.Identifiable):
    def __init__(self):
        super().__init__()


def generate_example_referable_tree() -> model.Referable:
    """
    Generates an example referable tree, built like this:

        example_grandparent -> example_parent -> example_referable -> example_child -> example_grandchild
        example_grandparent and example_grandchild both have a nonempty source, pointing to the mock-backend

    :return: example_referable
    """

    def generate_example_referable_with_namespace(id_short: model.NameType,
                                                  child: Optional[model.Referable] = None) -> model.Referable:
        """
        Generates an example referable with a namespace.

        :param id_short: id_short of the referable created
        :param child: Child to be added to the namespace sets of the Referable
        :return: The generated Referable
        """
        referable = ExampleRefereableWithNamespace()
        referable.id_short = id_short
        if child:
            namespace_set = model.NamespaceSet(parent=referable, attribute_names=[("id_short", True)],
                                               items=[child])
        return referable

    example_submodel = model.Submodel(
        id_='https://acplt.org/Simple_Submodel',
        id_short="exampleSubmodel"
    )
    example_grandchild = generate_example_referable_with_namespace("exampleGrandchild")
    example_child = generate_example_referable_with_namespace("exampleChild", example_grandchild)
    example_referable = generate_example_referable_with_namespace("exampleReferable", example_child)
    example_parent = generate_example_referable_with_namespace("exampleParent", example_referable)
    example_grandparent = generate_example_referable_with_namespace("exampleGrandparent", example_parent)
    assert(isinstance(example_grandparent, model.SubmodelElement))
    example_submodel.submodel_element.add(example_grandparent)

    example_grandchild.source = "mockScheme:exampleGrandchild"
    example_grandparent.source = "mockScheme:exampleGrandparent"
    example_submodel.source = "mockScheme:exampleSubmodel"

    return example_referable


class ProvidersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.aas1 = model.AssetAdministrationShell(
            model.AssetInformation(global_asset_id="http://acplt.org/TestAsset1/"), "urn:x-test:aas1")
        self.aas2 = model.AssetAdministrationShell(
            model.AssetInformation(global_asset_id="http://acplt.org/TestAsset2/"), "urn:x-test:aas2")
        self.submodel1 = model.Submodel("urn:x-test:submodel1")
        self.submodel2 = model.Submodel("urn:x-test:submodel2")

    def test_store_retrieve(self) -> None:
        object_store: model.DictObjectStore[model.AssetAdministrationShell] = model.DictObjectStore()
        object_store.add(self.aas1)
        object_store.add(self.aas2)
        self.assertIn(self.aas1, object_store)
        property = model.Property('test', model.datatypes.String)
        self.assertFalse(property in object_store)
        aas3 = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="http://acplt.org/TestAsset/"),
                                              "urn:x-test:aas1")
        with self.assertRaises(KeyError) as cm:
            object_store.add(aas3)
        self.assertEqual("'Identifiable object with same id urn:x-test:aas1 is already "
                         "stored in this store'", str(cm.exception))
        self.assertEqual(2, len(object_store))
        self.assertIs(self.aas1,
                      object_store.get_identifiable("urn:x-test:aas1"))
        self.assertIs(self.aas1,
                      object_store.get("urn:x-test:aas1"))
        object_store.discard(self.aas1)
        object_store.discard(self.aas1)
        with self.assertRaises(KeyError) as cm:
            object_store.get_identifiable("urn:x-test:aas1")
        self.assertIsNone(object_store.get("urn:x-test:aas1"))
        self.assertEqual("'urn:x-test:aas1'", str(cm.exception))
        self.assertIs(self.aas2, object_store.pop())
        self.assertEqual(0, len(object_store))

    def test_store_update(self) -> None:
        object_store1: model.DictObjectStore[model.AssetAdministrationShell] = model.DictObjectStore()
        object_store1.add(self.aas1)
        object_store2: model.DictObjectStore[model.AssetAdministrationShell] = model.DictObjectStore()
        object_store2.add(self.aas2)
        object_store1.add_from(object_store2)
        self.assertIsInstance(object_store1, model.DictObjectStore)
        self.assertIn(self.aas2, object_store1)

    def test_provider_multiplexer(self) -> None:
        aas_object_store: model.DictObjectStore[model.AssetAdministrationShell] = model.DictObjectStore()
        aas_object_store.add(self.aas1)
        aas_object_store.add(self.aas2)
        submodel_object_store: model.DictObjectStore[model.Submodel] = model.DictObjectStore()
        submodel_object_store.add(self.submodel1)
        submodel_object_store.add(self.submodel2)

        multiplexer = model.ObjectProviderMultiplexer([aas_object_store, submodel_object_store])
        self.assertIs(self.aas1, multiplexer.get_identifiable("urn:x-test:aas1"))
        self.assertIs(self.submodel1, multiplexer.get_identifiable("urn:x-test:submodel1"))
        with self.assertRaises(KeyError) as cm:
            multiplexer.get_identifiable("urn:x-test:submodel3")
        self.assertEqual("'Identifier could not be found in any of the 2 consulted registries.'", str(cm.exception))

    def test_update(self):
        backends.register_backend(Protocol.MOCK, MockBackend)
        example_referable = generate_example_referable_tree()
        example_grandparent = example_referable.parent.parent
        example_grandchild = example_referable.get_referable("exampleChild").get_referable("exampleGrandchild")
        example_submodel = example_grandparent.parent

        obj_store: model.DictObjectStore = model.DictObjectStore()
        obj_store.add_source(example_grandparent, Protocol.MOCK, example_grandparent.source)
        obj_store.add_source(example_grandchild, Protocol.MOCK, example_grandchild.source)

        # Test update with parameter "recursive=False"
        obj_store.update_identifiable(example_referable, recursive=False, protocol=Protocol.MOCK)
        MockBackend.update_object.assert_called_once_with(
            updated_object=example_referable,
            store_object=example_grandparent,
            relative_path=["exampleGrandparent", "exampleParent", "exampleReferable"],
            source="mockScheme:exampleGrandparent"
        )
        MockBackend.update_object.reset_mock()

        # Test update with parameter "recursive=True"
        obj_store.update_identifiable(example_referable, protocol=Protocol.MOCK)
        self.assertEqual(MockBackend.update_object.call_count, 2)
        MockBackend.update_object.assert_has_calls([
            mock.call(updated_object=example_referable,
                      store_object=example_grandparent,
                      relative_path=["exampleGrandparent", "exampleParent", "exampleReferable"],
                      source="mockScheme:exampleGrandparent"),
            mock.call(updated_object=example_grandchild,
                      store_object=example_grandchild,
                      relative_path=[],
                      source="mockScheme:exampleGrandchild")
        ])
        MockBackend.update_object.reset_mock()

        # Test update with source != "" in example_referable
        example_referable.source = "mockScheme:exampleReferable"
        obj_store.add_source(example_referable, Protocol.MOCK, example_referable.source)
        obj_store.update_identifiable(example_referable, recursive=False, protocol=Protocol.MOCK)
        MockBackend.update_object.assert_called_once_with(
            updated_object=example_referable,
            store_object=example_referable,
            relative_path=[],
            source="mockScheme:exampleReferable"
        )
        MockBackend.update_object.reset_mock()

        # Test update with no source available
        example_grandparent.source = None
        example_referable.source = None
        obj_store.add_source(example_grandparent, Protocol.MOCK, example_grandparent.source)
        obj_store.add_source(example_referable, Protocol.MOCK, example_referable.source)
        obj_store.update_identifiable(example_referable, recursive=False, protocol=Protocol.MOCK)
        MockBackend.update_object.assert_not_called()

    def test_commit(self):
        backends.register_backend(Protocol.MOCK, MockBackend)
        example_referable = generate_example_referable_tree()
        example_grandparent = example_referable.parent.parent
        example_grandchild = example_referable.get_referable("exampleChild").get_referable("exampleGrandchild")
        example_submodel = example_grandparent.parent

        obj_store: model.DictObjectStore = model.DictObjectStore()
        obj_store.add_source(example_grandparent, Protocol.MOCK, example_grandparent.source)
        obj_store.add_source(example_grandchild, Protocol.MOCK, example_grandchild.source)
        obj_store.add_source(example_submodel, Protocol.MOCK, example_submodel.source)

        # Test commit starting from example_referable
        obj_store.commit_identifiable(example_referable, protocol=Protocol.MOCK)
        self.assertEqual(MockBackend.commit_object.call_count, 3)
        MockBackend.commit_object.assert_has_calls([
            mock.call(committed_object=example_referable,
                      store_object=example_grandparent,
                      relative_path=["exampleParent", "exampleReferable"],
                      source="mockScheme:exampleGrandparent"),
            mock.call(committed_object=example_referable,
                      store_object=example_submodel,
                      relative_path=["exampleGrandparent", "exampleParent", "exampleReferable"],
                      source="mockScheme:exampleSubmodel"),
            mock.call(committed_object=example_grandchild,
                      store_object=example_grandchild,
                      relative_path=[],
                      source="mockScheme:exampleGrandchild")
        ])
        MockBackend.commit_object.reset_mock()

        # Test commit starting from example_grandchild
        obj_store.commit_identifiable(example_grandchild, protocol=Protocol.MOCK)
        self.assertEqual(MockBackend.commit_object.call_count, 3)
        MockBackend.commit_object.assert_has_calls([
            mock.call(committed_object=example_grandchild,
                      store_object=example_grandparent,
                      relative_path=["exampleParent", "exampleReferable", "exampleChild", "exampleGrandchild"],
                      source="mockScheme:exampleGrandparent"),
            mock.call(committed_object=example_grandchild,
                      store_object=example_submodel,
                      relative_path=["exampleGrandparent", "exampleParent", "exampleReferable", "exampleChild",
                                     "exampleGrandchild"],
                      source="mockScheme:exampleSubmodel"),
            mock.call(committed_object=example_grandchild,
                      store_object=example_grandchild,
                      relative_path=[],
                      source="mockScheme:exampleGrandchild")
        ])
        MockBackend.commit_object.reset_mock()

        # Test commit starting from example_grandchild after adding a source to example_referable
        example_referable.source = "mockScheme:exampleReferable"
        obj_store.add_source(example_referable, Protocol.MOCK, example_referable.source)
        obj_store.commit_identifiable(example_grandchild, protocol=Protocol.MOCK)
        self.assertEqual(MockBackend.commit_object.call_count, 4)
        MockBackend.commit_object.assert_has_calls([
            mock.call(committed_object=example_grandchild,
                      store_object=example_referable,
                      relative_path=["exampleChild", "exampleGrandchild"],
                      source="mockScheme:exampleReferable"),
            mock.call(committed_object=example_grandchild,
                      store_object=example_grandparent,
                      relative_path=["exampleParent", "exampleReferable", "exampleChild", "exampleGrandchild"],
                      source="mockScheme:exampleGrandparent"),
            mock.call(committed_object=example_grandchild,
                      store_object=example_submodel,
                      relative_path=["exampleGrandparent", "exampleParent", "exampleReferable", "exampleChild",
                                     "exampleGrandchild"],
                      source="mockScheme:exampleSubmodel"),
            mock.call(committed_object=example_grandchild,
                      store_object=example_grandchild,
                      relative_path=[],
                      source="mockScheme:exampleGrandchild")
        ])
