# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import io
import unittest
import json

from basyx.aas import model
from basyx.aas.adapter.json import write_aas_json_file, JSON_SCHEMA_FILE, jsonization
from jsonschema import validate  # type: ignore
from typing import Set, Union

from basyx.aas.examples.data import example_aas_missing_attributes, example_aas, \
    example_aas_mandatory_attributes, example_submodel_template, create_example


class JsonSerializationTest(unittest.TestCase):
    def test_serialize_object(self) -> None:
        test_object = model.Property("test_id_short", model.datatypes.String, category="PARAMETER",
                                     description=model.MultiLanguageTextType({"en-US": "Germany", "de": "Deutschland"}))
        json_data = jsonization.to_jsonable(test_object)

    def test_random_object_serialization(self) -> None:
        aas_identifier = "AAS1"
        submodel_key = (model.Key(model.KeyTypes.SUBMODEL, "SM1"),)
        submodel_identifier = submodel_key[0].get_identifier()
        assert submodel_identifier is not None
        submodel_reference = model.ModelReference(submodel_key, model.Submodel)
        submodel = model.Submodel(submodel_identifier)
        test_aas = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="test"),
                                                  aas_identifier, submodel={submodel_reference})

        # serialize object to json
        json_data = json.dumps({
                'assetAdministrationShells': [jsonization.to_jsonable(test_aas)],
                'submodels': [jsonization.to_jsonable(submodel)],
                'assets': [],
                'conceptDescriptions': [],
            })
        json_data_new = json.loads(json_data)


class JsonSerializationSchemaTest(unittest.TestCase):
    def test_random_object_serialization(self) -> None:
        aas_identifier = "AAS1"
        submodel_key = (model.Key(model.KeyTypes.SUBMODEL, "SM1"),)
        submodel_identifier = submodel_key[0].get_identifier()
        assert submodel_identifier is not None
        submodel_reference = model.ModelReference(submodel_key, model.Submodel)
        # The JSONSchema expects every object with HasSemnatics (like Submodels) to have a `semanticId` Reference, which
        # must be a Reference. (This seems to be a bug in the JSONSchema.)
        submodel = model.Submodel(submodel_identifier,
                                  semantic_id=model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE,
                                                                       "http://acplt.org/TestSemanticId"),)))
        test_aas = model.AssetAdministrationShell(model.AssetInformation(global_asset_id="test"),
                                                  aas_identifier, submodel={submodel_reference})

        # serialize object to json
        json_data = json.dumps({
                'assetAdministrationShells': [jsonization.to_jsonable(test_aas)],
                'submodels': [jsonization.to_jsonable(submodel)]
            })
        json_data_new = json.loads(json_data)

        # load schema
        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_schema = json.load(json_file)

        # validate serialization against schema
        validate(instance=json_data_new, schema=aas_schema)

    def test_aas_example_serialization(self) -> None:
        data = example_aas.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_submodel_template_serialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_submodel_template.create_example_submodel_template())
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_full_empty_example_serialization(self) -> None:
        data = example_aas_mandatory_attributes.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_missing_serialization(self) -> None:
        data = example_aas_missing_attributes.create_full_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_concept_description_serialization(self) -> None:
        data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        data.add(example_aas.create_example_concept_description())
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)

    def test_full_example_serialization(self) -> None:
        data = create_example()
        file = io.StringIO()
        write_aas_json_file(file=file, data=data)

        with open(JSON_SCHEMA_FILE, 'r') as json_file:
            aas_json_schema = json.load(json_file)

        file.seek(0)
        json_data = json.load(file)

        # validate serialization against schema
        validate(instance=json_data, schema=aas_json_schema)
