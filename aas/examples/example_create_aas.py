# Copyright 2019 PyI40AAS Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""
Module for the creation of an example asset administration shell and related asset

The module has seven functions:
create_example_asset_identification_submodel: This function creates a submodel for the identification of the example
                                              asset containing two property elements according to 'Verwaltungssschale
                                              in der Praxis'
create_example_asset: This function creates an example asset with an reference to the above created submodel
create_example_submodel: This function creates an example submodel containing all kind of submodel element objects
create_example_concept_description: This function creates one example concept description
create_example_concept_dictionary: This function creates a concept dictionary with an reference with an reference to
                                   the above created concept description
create_example_asset_administration_shell: This function creates an asset administration shell with references to
                                           the above created asset and submodel and includes a concept description
create_full_example: This function creates an object store which is filled with an example asset, submodel, concept
                     description and asset administration shell using the function above
"""
from aas import model


def create_full_example() -> model.DictObjectStore:
    """
    creates an object store containing an example asset identification submodel, an example asset, an example submodel,
    an example concept description and an example asset administration shell

    :return: object store
    """
    obj_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    obj_store.add(create_example_asset_identification_submodel())
    obj_store.add(create_example_asset())
    obj_store.add(create_example_submodel())
    obj_store.add(create_example_concept_description())
    obj_store.add(create_example_asset_administration_shell(create_example_concept_dictionary()))
    return obj_store


def create_example_asset_identification_submodel() -> model.Submodel:
    """
    creates an example asset identification submodel which contains properties according to 'Verwaltungssschale in der
    Praxis'
    https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/2019-verwaltungsschale-in-der-praxis.html

    :return: example asset identification submodel
    """
    qualifier = model.Qualifier(
        type_='http://acplt.org/Qualifier/ExampleQualifier',
        value_type='string',
        value='100')

    formula = model.Formula(depends_on={model.Reference([model.Key(type_=model.KeyElements.ASSET,
                                                                   local=False,
                                                                   value='http://acplt.org/Formula/ExampleFormula',
                                                                   id_type=model.KeyType.IRDI)])})

    # Property-Element conform to 'Verwaltungssschale in der Praxis' page 41 ManufacturerName:
    # https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/2019-verwaltungsschale-in-der-praxis.html
    identification_submodel_element_manufacturer_name = model.Property(
        id_short='ManufacturerName',
        value_type='string',
        value='ACPLT',
        value_id=None,  # TODO
        category=None,
        description={'en-us': 'Legally valid designation of the natural or judicial person which is directly '
                              'responsible for the design, production, packaging and labeling of a product in '
                              'respect to its being brought into circulation.',
                     'de': 'Bezeichnung für eine natürliche oder juristische Person, die für die Auslegung, '
                           'Herstellung und Verpackung sowie die Etikettierung eines Produkts im Hinblick auf das '
                           '\'Inverkehrbringen\' im eigenen Namen verantwortlich ist'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='0173-1#02-AAO677#002',
                                               id_type=model.KeyType.IRDI)]),
        qualifier={qualifier},
        kind=model.ModelingKind.INSTANCE)

    # Property-Element conform to 'Verwaltungssschale in der Praxis' page 44 InstanceId:
    # https://www.plattform-i40.de/PI40/Redaktion/DE/Downloads/Publikation/2019-verwaltungsschale-in-der-praxis.html
    identification_submodel_element_instance_id = model.Property(
        id_short='InstanceId',
        value_type='string',
        value='978-8234-234-342',
        value_id=None,  # TODO
        category=None,
        description={'en-us': 'Legally valid designation of the natural or judicial person which is directly '
                              'responsible for the design, production, packaging and labeling of a product in '
                              'respect to its being brought into circulation.',
                     'de': 'Bezeichnung für eine natürliche oder juristische Person, die für die Auslegung, '
                           'Herstellung und Verpackung sowie die Etikettierung eines Produkts im Hinblick auf das '
                           '\'Inverkehrbringen\' im eigenen Namen verantwortlich ist'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://opcfoundation.org/UA/DI/1.1/DeviceType/Serialnumber',
                                               id_type=model.KeyType.IRI)]),
        qualifier={formula},
        kind=model.ModelingKind.INSTANCE)

    # asset identification submodel which will be included in the asset object
    identification_submodel = model.Submodel(
        identification=model.Identifier(id_='http://acplt.org/Submodels/Assets/TestAsset/Identification',
                                        id_type=model.IdentifierType.IRI),
        submodel_element=(identification_submodel_element_manufacturer_name,
                          identification_submodel_element_instance_id),
        id_short='Identification',
        category=None,
        description={'en-us': 'An example asset identification submodel for the test application',
                     'de': 'Ein Beispiel-Identifikations-Submodel für eine Test-Anwendung'},
        parent=None,
        administration=model.AdministrativeInformation(version='0.9',
                                                       revision='0'),
        data_specification={model.Reference([model.Key(type_=model.KeyElements.ASSET,
                                                       local=False,
                                                       value='http://acplt.org/DataSpecifications/Submodels/'
                                                             'AssetIdentification',
                                                       id_type=model.KeyType.IRDI)])},
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.SUBMODEL,
                                               local=False,
                                               value='http://acplt.org/SubmodelTemplates/AssetIdentification',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)
    return identification_submodel


def create_example_asset() -> model.Asset:
    """
    creates an example asset which holds references to the example asset identification submodel

    :return: example asset
    """
    asset = model.Asset(
        kind=model.AssetKind.INSTANCE,
        identification=model.Identifier(id_='https://acplt.org/Test_Asset',
                                        id_type=model.IdentifierType.IRI),
        id_short='Test_Asset',
        category=None,
        description={'en-us': 'An example asset for the test application',
                     'de': 'Ein Beispiel-Asset für eine Test-Anwendung'},
        parent=None,
        administration=model.AdministrativeInformation(version='0.9',
                                                       revision='0'),
        data_specification={model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                                       local=False,
                                                       value='http://acplt.org/DataSpecifications/AssetTypes/'
                                                             'TestAsset',
                                                       id_type=model.KeyType.IRDI)])},
        asset_identification_model=model.AASReference([model.Key(type_=model.KeyElements.SUBMODEL,
                                                                 local=False,
                                                                 value='http://acplt.org/Submodels/Assets/'
                                                                       'TestAsset/Identification',
                                                                 id_type=model.KeyType.IRDI)],
                                                      model.Submodel),
        bill_of_material=None)
    # TODO add billofMaterial-Submodel for the use of SubmodelElement: Entity
    return asset


def create_example_submodel() -> model.Submodel:
    """
    creates an example submodel containing all kind of SubmodelElement objects

    :return: example submodel
    """
    submodel_element_property = model.Property(
        id_short='ExampleProperty',
        value_type='string',
        value='exampleValue',
        value_id=None,  # TODO
        category='CONSTANT',
        description={'en-us': 'Example Property object',
                     'de': 'Beispiel Property Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Properties/ExampleProperty',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_multi_language_property = model.MultiLanguageProperty(
        id_short='ExampleMultiLanguageProperty',
        value={'en-us': 'Example value of a MultiLanguageProperty element',
               'de': 'Beispielswert für ein MulitLanguageProperty-Element'},
        value_id=None,  # TODO
        category='CONSTANT',
        description={'en-us': 'Example MultiLanguageProperty object',
                     'de': 'Beispiel MulitLanguageProperty Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/MultiLanguageProperties/'
                                                     'ExampleMultiLanguageProperty',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_range = model.Range(
        id_short='ExampleRange',
        value_type='int',
        min_='0',
        max_='100',
        category='PARAMETER',
        description={'en-us': 'Example Range object',
                     'de': 'Beispiel Range Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Ranges/ExampleRange',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_blob = model.Blob(
        id_short='ExampleBlob',
        mime_type='application/pdf',
        value=bytearray(b'\x01\x02\x03\x04\x05'),
        category='PARAMETER',
        description={'en-us': 'Example Blob object',
                     'de': 'Beispiel Blob Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Blobs/ExampleBlob',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_file = model.File(
        id_short='ExampleFile',
        mime_type='application/pdf',
        value='/TestFile.pdf',
        category='PARAMETER',
        description={'en-us': 'Example File object',
                     'de': 'Beispiel File Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Files/ExampleFile',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_reference_element = model.ReferenceElement(
        id_short='ExampleReferenceElement',
        value=model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                            local=True,
                                            value='ExampleProperty',
                                            id_type=model.KeyType.IDSHORT)],
                                 model.Property),
        category='PARAMETER',
        description={'en-us': 'Example Reference Element object',
                     'de': 'Beispiel Reference Element Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/ReferenceElements/ExampleReferenceElement',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_relationship_element = model.RelationshipElement(
        id_short='ExampleRelationshipElement',
        first=model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                            local=True,
                                            value='ExampleProperty',
                                            id_type=model.KeyType.IDSHORT)],
                                 model.Property),
        second=model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                             local=True,
                                             value='ExampleProperty',
                                             id_type=model.KeyType.IDSHORT)],
                                  model.Property),
        category='PARAMETER',
        description={'en-us': 'Example RelationshipElement object',
                     'de': 'Beispiel RelationshipElement Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/RelationshipElements/'
                                                     'ExampleRelationshipElement',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_annotated_relationship_element = model.AnnotatedRelationshipElement(
        id_short='ExampleAnnotatedRelationshipElement',
        first=model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                            local=True,
                                            value='ExampleProperty',
                                            id_type=model.KeyType.IDSHORT)],
                                 model.Property),
        second=model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                             local=True,
                                             value='ExampleProperty',
                                             id_type=model.KeyType.IDSHORT)],
                                  model.Property),
        annotation={model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                                  local=True,
                                                  value='ExampleProperty',
                                                  id_type=model.KeyType.IDSHORT)],
                                       model.Property)},
        category='PARAMETER',
        description={'en-us': 'Example AnnotatedRelationshipElement object',
                     'de': 'Beispiel AnnotatedRelationshipElement Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/RelationshipElements/'
                                                     'ExampleAnnotatedRelationshipElement',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_operation_variable_input = model.OperationVariable(
        id_short='ExampleInputOperationVariable',
        value=submodel_element_property,
        category='PARAMETER',
        description={'en-us': 'Example ExampleInputOperationVariable object',
                     'de': 'Beispiel ExampleInputOperationVariable Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Operations/'
                                                     'ExampleInputOperationVariable',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_operation_variable_output = model.OperationVariable(
        id_short='ExampleOutputOperationVariable',
        value=submodel_element_property,
        category='PARAMETER',
        description={'en-us': 'Example OutputOperationVariable object',
                     'de': 'Beispiel OutputOperationVariable Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Operations/'
                                                     'ExampleOutputOperationVariable',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_operation_variable_in_output = model.OperationVariable(
        id_short='ExampleInOutputOperationVariable',
        value=submodel_element_property,
        category='PARAMETER',
        description={'en-us': 'Example InOutputOperationVariable object',
                     'de': 'Beispiel InOutputOperationVariable Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Operations/'
                                                     'ExampleInOutputOperationVariable',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_operation = model.Operation(
        id_short='ExampleOperation',
        input_variable={submodel_element_operation_variable_input},
        output_variable={submodel_element_operation_variable_output},
        in_output_variable={submodel_element_operation_variable_in_output},
        category='PARAMETER',
        description={'en-us': 'Example Operation object',
                     'de': 'Beispiel Operation Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Operations/'
                                                     'ExampleOperation',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_capability = model.Capability(
        id_short='ExampleCapability',
        category='PARAMETER',
        description={'en-us': 'Example Capability object',
                     'de': 'Beispiel Capability Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Capabilities/'
                                                     'ExampleCapability',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_basic_event = model.BasicEvent(
        id_short='ExampleBasicEvent',
        observed=model.AASReference([model.Key(type_=model.KeyElements.PROPERTY,
                                               local=True,
                                               value='ExampleProperty',
                                               id_type=model.KeyType.IDSHORT)],
                                    model.Property),
        category='PARAMETER',
        description={'en-us': 'Example BasicEvent object',
                     'de': 'Beispiel BasicEvent Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/Events/'
                                                     'ExampleBasicEvent',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_submodel_element_collection_ordered = model.SubmodelElementCollectionOrdered(
        id_short='ExampleSubmodelCollectionOrdered',
        value=(submodel_element_property,
               submodel_element_multi_language_property,
               submodel_element_range),
        category='PARAMETER',
        description={'en-us': 'Example SubmodelElementCollectionOrdered object',
                     'de': 'Beispiel SubmodelElementCollectionOrdered Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/SubmodelElementCollections/'
                                                     'ExampleSubmodelElementCollectionOrdered',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel_element_submodel_element_collection_unordered = model.SubmodelElementCollectionUnordered(
        id_short='ExampleSubmodelCollectionUnordered',
        value=(submodel_element_blob,
               submodel_element_file,
               submodel_element_reference_element),
        category='PARAMETER',
        description={'en-us': 'Example SubmodelElementCollectionUnordered object',
                     'de': 'Beispiel SubmodelElementCollectionUnordered Element'},
        parent=None,
        data_specification=None,
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/SubmodelElementCollections/'
                                                     'ExampleSubmodelElementCollectionUnordered',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)

    submodel = model.Submodel(
        identification=model.Identifier(id_='https://acplt.org/Test_Submodel',
                                        id_type=model.IdentifierType.IRI),
        submodel_element=(submodel_element_relationship_element,
                          submodel_element_annotated_relationship_element,
                          submodel_element_operation,
                          submodel_element_capability,
                          submodel_element_basic_event,
                          submodel_element_submodel_element_collection_ordered,
                          submodel_element_submodel_element_collection_unordered),
        id_short='TestSubmodel',
        category=None,
        description={'en-us': 'An example submodel for the test application',
                     'de': 'Ein Beispiel-Teilmodell für eine Test-Anwendung'},
        parent=None,
        administration=model.AdministrativeInformation(version='0.9',
                                                       revision='0'),
        data_specification={model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                                       local=False,
                                                       value='http://acplt.org/DataSpecifications/AssetTypes/'
                                                             'TestAsset',
                                                       id_type=model.KeyType.IRDI)])},
        semantic_id=model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                               local=False,
                                               value='http://acplt.org/SubmodelTemplates/'
                                                     'ExampleSubmodel',
                                               id_type=model.KeyType.IRDI)]),
        qualifier=None,
        kind=model.ModelingKind.INSTANCE)
    return submodel


def create_example_concept_description() -> model.ConceptDescription:
    """
    creates an example concept description

    :return: example concept description
    """
    concept_description = model.ConceptDescription(
        identification=model.Identifier(id_='https://acplt.org/Test_ConceptDescription',
                                        id_type=model.IdentifierType.IRI),
        is_case_of=None,
        id_short='TestConceptDescription',
        category=None,
        description={'en-us': 'An example concept description  for the test application',
                     'de': 'Ein Beispiel-ConceptDescription für eine Test-Anwendung'},
        parent=None,
        administration=model.AdministrativeInformation(version='0.9',
                                                       revision='0'),
        data_specification={model.Reference([model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                                       local=False,
                                                       value='http://acplt.org/DataSpecifications/'
                                                             'ConceptDescriptions/TestConceptDescription',
                                                       id_type=model.KeyType.IRDI)])})
    return concept_description


def create_example_concept_dictionary() -> model.ConceptDictionary:
    """
    creates an example concept dictionary containing an reference to the example concept description

    :return: example concept dictionary
    """
    concept_dictionary = model.ConceptDictionary(
        id_short='TestConceptDictionary',
        category=None,
        description={'en-us': 'An example concept dictionary for the test application',
                     'de': 'Ein Beispiel-ConceptDictionary für eine Test-Anwendung'},
        parent=None,
        concept_description={model.AASReference([model.Key(type_=model.KeyElements.CONCEPT_DESCRIPTION,
                                                           local=False,
                                                           value='https://acplt.org/Test_ConceptDescription',
                                                           id_type=model.KeyType.IRDI)],
                                                model.ConceptDescription)})
    return concept_dictionary


def create_example_asset_administration_shell(concept_dictionary: model.ConceptDictionary) -> \
        model.AssetAdministrationShell:
    """
    creates an example asset administration shell containing references to the example asset and example submodel

    :return: example asset administration shell
    """
    asset_administration_shell = model.AssetAdministrationShell(
        asset=model.AASReference([model.Key(type_=model.KeyElements.ASSET,
                                            local=False,
                                            value='https://acplt.org/Test_Asset',
                                            id_type=model.KeyType.IRDI)],
                                 model.Asset),
        identification=model.Identifier(id_='https://acplt.org/Test_AssetAdministrationShell',
                                        id_type=model.IdentifierType.IRI),
        id_short='TestAssetAdministrationShell',
        category=None,
        description={'en-us': 'An Example Asset Administration Shell for the test application',
                     'de': 'Ein Beispiel-Verwaltungsschale für eine Test-Anwendung'},
        parent=None,
        administration=model.AdministrativeInformation(version='0.9',
                                                       revision='0'),
        data_specification=None,
        security_=None,
        submodel_={model.AASReference([model.Key(type_=model.KeyElements.SUBMODEL,
                                                 local=False,
                                                 value='https://acplt.org/Test_Submodel',
                                                 id_type=model.KeyType.IRDI)],
                                      model.Submodel)},
        concept_dictionary=[concept_dictionary],
        view=[],
        derived_from=None)
    return asset_administration_shell
