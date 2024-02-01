# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import io
import logging
import unittest

from basyx.aas import model
from basyx.aas.adapter.xml import read_aas_xml_file, read_aas_xml_file_into, xmlization
from basyx.aas.adapter._generic import XML_NS_MAP
from lxml import etree  # type: ignore
from typing import Iterable, Type, Union


def _xml_wrap(xml: str) -> str:
    return \
        """<?xml version="1.0" encoding="utf-8" ?>""" \
        """<aas:aasenv xmlns:aas="https://admin-shell.io/aas/3/0"> """ \
        + xml + """</aas:aasenv>"""


def _root_cause(exception: BaseException) -> BaseException:
    while exception.__cause__ is not None:
        exception = exception.__cause__
    return exception


class XmlDeserializationTest(unittest.TestCase):
    def _assertInExceptionAndLog(self, xml: str, strings: Union[Iterable[str], str], error_type: Type[BaseException],
                                 log_level: int) -> None:
        """
        Runs read_xml_aas_file in failsafe mode and checks if each string is contained in the first message logged.
        Then runs it in non-failsafe mode and checks if each string is contained in the first error raised.

        :param xml: The xml document to parse.
        :param strings: One or more strings to match.
        :param error_type: The expected error type.
        :param log_level: The log level on which the string is expected.
        """
        if isinstance(strings, str):
            strings = [strings]
        bytes_io = io.BytesIO(xml.encode("utf-8"))
        with self.assertRaises(error_type) as err_ctx:
            read_aas_xml_file(bytes_io)
        cause = _root_cause(err_ctx.exception)
        for s in strings:
            self.assertIn(s, str(cause))

    def test_malformed_xml(self) -> None:
        xml = (
            "invalid xml",
            _xml_wrap("<<>>><<<<<"),
            _xml_wrap("<aas:submodels><aas:submodel/>")
        )
        for s in xml:
            self._assertInExceptionAndLog(s, [], etree.XMLSyntaxError, logging.ERROR)

    def test_invalid_list_name(self) -> None:
        xml = _xml_wrap("<aas:invalidList></aas:invalidList>")
        self._assertInExceptionAndLog(xml, "aas:invalidList", TypeError, logging.WARNING)

    def test_invalid_element_in_list(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:invalidElement/>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, ["aas:invalidElement", "aas:submodels"], KeyError, logging.WARNING)

    def test_missing_asset_kind(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        self._assertInExceptionAndLog(xml, "aas:assetKind", KeyError, logging.ERROR)

    def test_missing_asset_kind_text(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind></aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        self._assertInExceptionAndLog(xml, "aas:assetKind", KeyError, logging.ERROR)

    def test_invalid_asset_kind_text(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind>invalidKind</aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        self._assertInExceptionAndLog(xml, ["aas:assetKind", "invalidKind"], ValueError, logging.ERROR)

    def test_invalid_boolean(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:submodelElementList>
                        <aas:orderRelevant>False</aas:orderRelevant>
                        <aas:idShort>collection</aas:idShort>
                        <aas:typeValueListElement>Capability</aas:typeValueListElement>
                    </aas:submodelElementList>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, "False", ValueError, logging.ERROR)

    def test_no_modelling_kind(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
            </aas:submodel>
        </aas:submodels>
        """)
        # should get parsed successfully
        object_store = read_aas_xml_file(io.BytesIO(xml.encode("utf-8")))
        # modelling kind should default to INSTANCE
        submodel = object_store.pop()
        self.assertIsInstance(submodel, model.Submodel)
        assert isinstance(submodel, model.Submodel)  # to make mypy happy
        self.assertEqual(submodel.kind, model.ModellingKind.INSTANCE)

    def test_reference_kind_mismatch(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind>Instance</aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
                <aas:derivedFrom>
                    <aas:type>ModelReference</aas:type>
                    <aas:keys>
                        <aas:key>
                            <aas:type>Submodel</aas:type>
                            <aas:value>http://acplt.org/test_ref</aas:value>
                        </aas:key>
                    </aas:keys>
                </aas:derivedFrom>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        """)
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as context:
            read_aas_xml_file(io.BytesIO(xml.encode("utf-8")))
        for s in ("SUBMODEL", "http://acplt.org/test_ref", "AssetAdministrationShell"):
            self.assertIn(s, context.output[0])

    def test_invalid_submodel_element(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:invalidSubmodelElement/>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, "aas:invalidSubmodelElement", KeyError, logging.ERROR)

    def test_empty_qualifier(self) -> None:
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:qualifiers>
                    <aas:qualifier/>
                </aas:qualifiers>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, ["aas:qualifier", "has no child aas:type"], KeyError, logging.ERROR)

    def test_operation_variable_no_submodel_element(self) -> None:
        # TODO: simplify this should our suggestion regarding the XML schema get accepted
        # https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/57
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:operation>
                        <aas:idShort>test_operation</aas:idShort>
                        <aas:outputVariables>
                            <aas:operationVariable>
                                <aas:value/>
                            </aas:operationVariable>
                        </aas:outputVariables>
                    </aas:operation>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, ["aas:value", "has no submodel element"], KeyError, logging.ERROR)

    def test_operation_variable_too_many_submodel_elements(self) -> None:
        # TODO: simplify this should our suggestion regarding the XML schema get accepted
        # https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/57
        xml = _xml_wrap("""
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_submodel</aas:id>
                <aas:submodelElements>
                    <aas:operation>
                        <aas:idShort>test_operation</aas:idShort>
                        <aas:outputVariables>
                            <aas:operationVariable>
                                <aas:value>
                                    <aas:file>
                                        <aas:kind>Template</aas:kind>
                                        <aas:idShort>test_file</aas:idShort>
                                        <aas:contentType>application/problem+xml</aas:contentType>
                                    </aas:file>
                                    <aas:file>
                                        <aas:idShort>test_file2</aas:idShort>
                                        <aas:contentType>application/problem+xml</aas:contentType>
                                    </aas:file>
                                </aas:value>
                            </aas:operationVariable>
                        </aas:outputVariables>
                    </aas:operation>
                </aas:submodelElements>
            </aas:submodel>
        </aas:submodels>
        """)
        with self.assertLogs(logging.getLogger(), level=logging.WARNING) as context:
            read_aas_xml_file(io.BytesIO(xml.encode("utf-8")))
        self.assertIn("aas:value", context.output[0])
        self.assertIn("more than one submodel element", context.output[0])

    def test_duplicate_identifier(self) -> None:
        xml = _xml_wrap("""
        <aas:assetAdministrationShells>
            <aas:assetAdministrationShell>
                <aas:id>http://acplt.org/test_aas</aas:id>
                <aas:assetInformation>
                    <aas:assetKind>Instance</aas:assetKind>
                    <aas:globalAssetId>http://acplt.org/TestAsset/</aas:globalAssetId>
                </aas:assetInformation>
            </aas:assetAdministrationShell>
        </aas:assetAdministrationShells>
        <aas:submodels>
            <aas:submodel>
                <aas:id>http://acplt.org/test_aas</aas:id>
            </aas:submodel>
        </aas:submodels>
        """)
        self._assertInExceptionAndLog(xml, "duplicate identifier", KeyError, logging.ERROR)

    def test_read_aas_xml_element(self) -> None:
        xml = f"""
        <aas:submodel xmlns:aas="https://admin-shell.io/aas/3/0">
            <aas:id>http://acplt.org/test_submodel</aas:id>
        </aas:submodel>
        """
        bytes_io = io.BytesIO(xml.encode("utf-8"))

        submodel = xmlization.referable_from_str(bytes_io.read().decode("utf-8"))
        self.assertIsInstance(submodel, model.Submodel)
