from enum import Enum
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from basyx.aas import model

class Protocol(Enum):
    HTTP = "HTTP"
    MQTT = "MQTT"
    MODBUS = "MODBUS"
    COUCHDB = "COUCHDB"


class ProtocolExtractor:
    def extract_parameters(self, aid_element: model.SubmodelElement, protocol: Protocol) -> Dict[str, Any]:
        parameters = {}

        # Get EndpointMetadata
        endpoint_metadata = self._get_endpoint_metadata(aid_element)
        if endpoint_metadata:
            base = endpoint_metadata.get_referable('base')
            if base and isinstance(base, model.Property):
                parameters['base'] = base.value

        if isinstance(aid_element, model.SubmodelElementCollection):
            forms = aid_element.get_referable('forms')
            if forms:
                protocol_params = self._extract_protocol_forms_parameters(forms, protocol)
                parameters.update(protocol_params)

        return parameters

    def determine_protocol(self, interface_element: model.SubmodelElementCollection) -> Optional[Protocol]:
        # Check idShort
        id_short = interface_element.id_short.lower()
        if "http" in id_short:
            return Protocol.HTTP
        elif "mqtt" in id_short:
            return Protocol.MQTT
        elif "modbus" in id_short:
            return Protocol.MODBUS

        # Check Supplemental Semantic IDs
        if interface_element._supplemental_semantic_ids:
            for semantic_id in interface_element._supplemental_semantic_ids:
                if isinstance(semantic_id, model.ExternalReference):
                    for key in semantic_id.key:
                        key_value = key.value.lower()
                        if "http" in key_value:
                            return Protocol.HTTP
                        elif "mqtt" in key_value:
                            return Protocol.MQTT
                        elif "modbus" in key_value:
                            return Protocol.MODBUS

        return None

    def _get_endpoint_metadata(self, aid_element: model.SubmodelElement) -> Optional[model.SubmodelElementCollection]:
        # Step 1: Try to find EndpointMetadata directly
        try:
            return aid_element.parent.parent.parent.get_referable('EndpointMetadata')
        except AttributeError:
            pass

        # Step 2: Try to find EndpointMetadata by id_short
        return self._find_parent_by_id_short(aid_element, 'EndpointMetadata')

    def _find_parent_by_id_short(self, element: model.SubmodelElement, id_short: str) -> Optional[
        model.SubmodelElementCollection]:
        current = element
        while current.parent:
            if current.parent.id_short == id_short:
                return current.parent
            current = current.parent
        return None

    def _extract_protocol_forms_parameters(self, forms_element: model.SubmodelElementCollection, protocol: Protocol) -> \
    Dict[str, Any]:
        params = {}
        href = forms_element.get_referable('href')
        if href and isinstance(href, model.Property):
            params['address'] = self._parse_address(href.value, protocol)

        if protocol == Protocol.MODBUS:
            modv_function = forms_element.get_referable('modv_function')
            modv_type = forms_element.get_referable('modv_type')
        elif protocol == Protocol.MQTT:
            modv_function = forms_element.get_referable('mqv_controlPacket')
            modv_type = forms_element.get_referable('mqv_qos')
        elif protocol == Protocol.HTTP:
            modv_function = forms_element.get_referable('htv_methodName')
            modv_type = None
        else:
            return params

        if modv_function and isinstance(modv_function, model.Property):
            params['function'] = modv_function.value
        if modv_type and isinstance(modv_type, model.Property):
            params['data_type'] = modv_type.value

        return params

    def _parse_address(self, href: str, protocol: Protocol) -> Any:
        if protocol == Protocol.MODBUS:
            address_str = href.split('?')[0]
            return int(address_str)
        elif protocol == Protocol.MQTT:
            return href
        elif protocol == Protocol.HTTP:
            return href
        else:
            return href