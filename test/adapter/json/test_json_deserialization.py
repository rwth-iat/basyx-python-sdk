# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Additional tests for the adapter.json.json_deserialization module.

Deserialization is also somehow tested in the serialization tests -- at least, we get to know if exceptions are raised
when trying to reconstruct the serialized data structure. This module additionally tests error behaviour and verifies
deserialization results.
"""
import io
import logging
import unittest
from basyx.aas.adapter.json import read_aas_json_file, read_aas_json_file_into, jsonization
from basyx.aas import model


class JsonDeserializationTest(unittest.TestCase):
    def test_file_format_wrong_list(self) -> None:
        data = """
            {
                "assetAdministrationShells": [],
                "conceptDescriptions": [],
                "submodels": [
                    {
                        "modelType": "AssetAdministrationShell",
                        "id": "https://acplt.org/Test_Asset",
                        "assetInformation": {
                            "assetKind": "Instance",
                            "globalAssetId": "https://acplt.org/Test_AssetId"
                        }
                    }
                ]
            }"""
        with self.assertRaisesRegex(TypeError, r"submodels.*AssetAdministrationShell"):
            read_aas_json_file(io.StringIO(data), failsafe=False)
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as cm:
            read_aas_json_file(io.StringIO(data), failsafe=True)
        self.assertIn("submodels", cm.output[0])  # type: ignore
        self.assertIn("AssetAdministrationShell", cm.output[0])  # type: ignore

    def test_file_format_unknown_object(self) -> None:
        data = """
            {
                "assetAdministrationShells": [],
                "assets": [],
                "conceptDescriptions": [],
                "submodels": [
                    { "x": "foo" }
                ]
            }"""
        with self.assertRaisesRegex(TypeError, r"submodels.*'foo'"):
            read_aas_json_file(io.StringIO(data), failsafe=False)
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as cm:
            read_aas_json_file(io.StringIO(data), failsafe=True)
        self.assertIn("submodels", cm.output[0])  # type: ignore
        self.assertIn("'foo'", cm.output[0])  # type: ignore

    def test_broken_submodel(self) -> None:
        data = """
            [
                {
                    "modelType": "Submodel"
                },
                {
                    "modelType": "Submodel",
                    "id": ["https://acplt.org/Test_Submodel_broken_id", "IRI"]
                },
                {
                    "modelType": "Submodel",
                    "id": "https://acplt.org/Test_Submodel"
                }
            ]"""
        # In strict mode, we should catch an exception
        with self.assertRaisesRegex(KeyError, r"id"):
            environment = jsonization.environment_from_jsonable(data)


    def test_wrong_submodel_element_type(self) -> None:
        data = """
            [
                {
                    "modelType": "Submodel",
                    "id": "http://acplt.org/Submodels/Assets/TestAsset/Identification",
                    "submodelElements": [
                        {
                            "modelType": "Submodel",
                            "id": "https://acplt.org/Test_Submodel"
                        },
                        {
                            "modelType": {
                                "name": "Broken modelType"
                            }
                        },
                        {
                            "modelType": "Capability",
                            "idShort": "TestCapability"
                        }
                    ]
                }
            ]"""
        # In strict mode, we should catch an exception for the unexpected Submodel within the Submodel
        # The broken object should not raise an exception, but log a warning, even in strict mode.
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as cm:
            with self.assertRaisesRegex(TypeError, r"SubmodelElement.*Submodel"):
                environment = jsonization.environment_from_jsonable(data)
        self.assertIn("modelType", cm.output[0])  # type: ignore

        # In failsafe mode, we should get a log entries for the broken object and the wrong type of the first two
        #   submodelElements
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as cm:
            environment = jsonization.environment_from_jsonable(data)
            parsed_data = environment.submodels
        self.assertGreaterEqual(len(cm.output), 3)  # type: ignore
        self.assertIn("SubmodelElement", cm.output[1])  # type: ignore
        self.assertIn("SubmodelElement", cm.output[2])  # type: ignore

        self.assertIsInstance(parsed_data[0], model.Submodel)
        self.assertEqual(1, len(parsed_data[0].submodel_element))
        cap = parsed_data[0].submodel_element.pop()
        self.assertIsInstance(cap, model.Capability)
        self.assertEqual("TestCapability", cap.id_short)

    def test_duplicate_identifier(self) -> None:
        data = """
            {
                "assetAdministrationShells": [{
                    "modelType": "AssetAdministrationShell",
                    "id": "http://acplt.org/test_aas",
                    "assetInformation": {
                        "assetKind": "Instance",
                        "globalAssetId": "https://acplt.org/Test_AssetId"
                    }
                }],
                "submodels": [{
                    "modelType": "Submodel",
                    "id": "http://acplt.org/test_aas"
                }],
                "conceptDescriptions": []
            }"""
        string_io = io.StringIO(data)
        with self.assertLogs(logging.getLogger(), level=logging.ERROR) as cm:
            read_aas_json_file(string_io, failsafe=True)
        self.assertIn("duplicate identifier", cm.output[0])  # type: ignore
        string_io.seek(0)
        with self.assertRaisesRegex(KeyError, r"duplicate identifier"):
            read_aas_json_file(string_io, failsafe=False)

    def test_duplicate_identifier_object_store(self) -> None:
        sm_id = "http://acplt.org/test_submodel"

        def get_clean_store() -> model.DictObjectStore:
            store: model.DictObjectStore = model.DictObjectStore()
            submodel_ = model.Submodel(sm_id, id_short="test123")
            store.add(submodel_)
            return store

        data = """
            {
                "submodels": [{
                    "modelType": "Submodel",
                    "id": "http://acplt.org/test_submodel",
                    "idShort": "test456"
                }],
                "assetAdministrationShells": [],
                "conceptDescriptions": []
            }"""

        string_io = io.StringIO(data)

        object_store = get_clean_store()
        identifiers = read_aas_json_file_into(object_store, string_io, replace_existing=True, ignore_existing=False)
        self.assertEqual(identifiers.pop(), sm_id)
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        self.assertEqual(submodel.id_short, "test456")

        string_io.seek(0)

        object_store = get_clean_store()
        with self.assertLogs(logging.getLogger(), level=logging.INFO) as log_ctx:
            identifiers = read_aas_json_file_into(object_store, string_io, replace_existing=False, ignore_existing=True)
        self.assertEqual(len(identifiers), 0)
        self.assertIn("already exists in the object store", log_ctx.output[0])  # type: ignore
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        self.assertEqual(submodel.id_short, "test123")

        string_io.seek(0)

        object_store = get_clean_store()
        with self.assertRaisesRegex(KeyError, r"already exists in the object store"):
            identifiers = read_aas_json_file_into(object_store, string_io, replace_existing=False,
                                                  ignore_existing=False)
        self.assertEqual(len(identifiers), 0)
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        self.assertEqual(submodel.id_short, "test123")


class JsonDeserializationDerivingTest(unittest.TestCase):
    def test_asset_constructor_overriding(self) -> None:
        class EnhancedSubmodel(model.Submodel):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.enhanced_attribute = "fancy!"
