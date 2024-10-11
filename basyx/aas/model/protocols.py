# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
from enum import Enum
from typing import Dict, Any, Optional
from urllib.parse import parse_qs
from basyx.aas import model


class Protocol(Enum):
    HTTP = "HTTP"
    MQTT = "MQTT"
    MODBUS = "MODBUS"
    COUCHDB = "COUCHDB"
    FILE = "Local File"
    MOCK = "Mock"


class ProtocolExtractorError(Exception):
    pass


def _parse_address(href: str, protocol: Protocol) -> Dict[str, Any]:
    if protocol == Protocol.MODBUS:
        parts = href.split('?')
        address = int(parts[0])
        params = {'address': address}
        if len(parts) > 1:
            query_params = parse_qs(parts[1])
            if 'quantity' in query_params:
                params['quantity'] = int(query_params['quantity'][0])
        return params
    else:
        return {'href': href}


class ProtocolExtractor:
    def extract_protocol_parameters(self, aid_element: model.SubmodelElement, protocol: Protocol) -> Dict[str, Any]:
        # Get EndpointMetadata
        endpoint_metadata = self._get_endpoint_metadata(aid_element)
        if not endpoint_metadata:
            raise ProtocolExtractorError("EndpointMetadata not found")

        parameters = {}

        # Extract common parameters
        parameters.update(self._extract_common_parameters(endpoint_metadata))

        # Extract protocol-specific parameters
        forms = aid_element.get_referable('forms')
        if not forms or not isinstance(forms, model.SubmodelElementCollection):
            raise ProtocolExtractorError("Forms element not found or not of correct type")

        if protocol == Protocol.HTTP:
            parameters.update(self._extract_http_parameters(forms))
        elif protocol == Protocol.MQTT:
            parameters.update(self._extract_mqtt_parameters(forms))
        elif protocol == Protocol.MODBUS:
            parameters.update(self._extract_modbus_parameters(forms))

        return parameters

    def determine_protocol(self, interface_element: model.SubmodelElementCollection) -> Optional[Protocol]:
        if interface_element.id_short and self.check_identifier(interface_element, "http"):
            return Protocol.HTTP
        elif interface_element.id_short and self.check_identifier(interface_element, "mqtt"):
            return Protocol.MQTT
        elif interface_element.id_short and self.check_identifier(interface_element, "modbus"):
            return Protocol.MODBUS
        return None

    @staticmethod
    def check_identifier(element: model.Referable, identifier: str) -> bool:
        # Check if identifier is None or empty
        if not identifier:
            return False

        identifier = identifier.lower()

        # Check idShort
        if element.id_short and identifier in element.id_short.lower():
            return True

        # Check semanticId
        if element.semantic_id and isinstance(element.semantic_id, model.ExternalReference):
            for key in element.semantic_id.key:
                if key.value and identifier in key.value.lower():
                    return True

        # Check supplemental_semantic_ids
        # TODO: If required, only use semantic_id for identification
        if element.supplemental_semantic_id:
            for semantic_id in element.supplemental_semantic_id:
                if isinstance(semantic_id, model.ExternalReference):
                    for key in semantic_id.key:
                        if key.value and identifier in key.value.lower():
                            return True

        return False

    def _get_endpoint_metadata(self, aid_element: model.SubmodelElement) -> Optional[model.SubmodelElementCollection]:
        try:
            return aid_element.parent.parent.parent.get_referable('EndpointMetadata')
        except AttributeError:
            return self._find_parent_by_id_short(aid_element, 'EndpointMetadata')

    def _extract_common_parameters(self, endpoint_metadata: model.SubmodelElementCollection) -> Dict[str, Any]:
        params = {}
        base = endpoint_metadata.get_referable('base')
        if base and isinstance(base, model.Property):
            params['base'] = base.value
        else:
            raise ProtocolExtractorError("Base URL not found in EndpointMetadata")

        content_type = endpoint_metadata.get_referable('contentType')
        if content_type and isinstance(content_type, model.Property):
            params['contentType'] = content_type.value
        else:
            raise ProtocolExtractorError("Content Type not found in EndpointMetadata")

        params['security'] = self._extract_security_parameters(endpoint_metadata)
        return params

    @staticmethod
    def _extract_security_parameters(endpoint_metadata: model.SubmodelElementCollection) -> Dict[str, Any]:
        security_defs = endpoint_metadata.get_referable('securityDefinitions')
        if not security_defs or not isinstance(security_defs, model.SubmodelElementCollection):
            raise ProtocolExtractorError("Security Definitions not found in EndpointMetadata")

        security_params = {}
        for scheme in security_defs.value:
            if isinstance(scheme, model.SubmodelElementCollection):
                scheme_type = scheme.get_referable('scheme')
                if scheme_type and isinstance(scheme_type, model.Property):
                    security_params[scheme.id_short] = scheme_type.value

        return security_params

    @staticmethod
    def _extract_http_parameters(forms_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        params = {}
        href = forms_element.get_referable('href')
        if href and isinstance(href, model.Property):
            params['href'] = href.value
        else:
            raise ProtocolExtractorError("HTTP href not found in forms")

        method = forms_element.get_referable('htv_methodName')
        if method and isinstance(method, model.Property):
            params['method'] = method.value
        else:
            raise ProtocolExtractorError("HTTP method not found in forms")

        content_type = forms_element.get_referable('contentType')
        if content_type and isinstance(content_type, model.Property):
            params['contentType'] = content_type.value

        return params

    @staticmethod
    def _extract_mqtt_parameters(forms_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        params = {}
        href = forms_element.get_referable('href')
        if href and isinstance(href, model.Property):
            params['topic'] = href.value
        else:
            raise ProtocolExtractorError("MQTT topic not found in forms")

        control_packet = forms_element.get_referable('mqv_controlPacket')
        if control_packet and isinstance(control_packet, model.Property):
            params['controlPacket'] = control_packet.value
        else:
            raise ProtocolExtractorError("MQTT control packet not found in forms")

        content_type = forms_element.get_referable('contentType')
        if content_type and isinstance(content_type, model.Property):
            params['contentType'] = content_type.value

        return params

    @staticmethod
    def _extract_modbus_parameters(forms_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        params = {}
        href = forms_element.get_referable('href')
        if href and isinstance(href, model.Property):
            address_info = _parse_address(href.value, Protocol.MODBUS)
            params.update(address_info)
        else:
            raise ProtocolExtractorError("Modbus address not found in forms")

        function = forms_element.get_referable('modv_function')
        if function and isinstance(function, model.Property):
            params['function'] = function.value
        else:
            raise ProtocolExtractorError("Modbus function not found in forms")

        data_type = forms_element.get_referable('modv_type')
        if data_type and isinstance(data_type, model.Property):
            params['dataType'] = data_type.value

        return params

    @staticmethod
    def _find_parent_by_id_short(element: model.SubmodelElement, id_short: str) \
            -> Optional[model.SubmodelElementCollection]:
        current = element
        while current.parent:
            if current.parent.id_short.lower() == id_short.lower():
                return current.parent
            current = current.parent
        return None
