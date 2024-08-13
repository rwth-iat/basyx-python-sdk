# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module implements Registries for the AAS, in order to enable resolving global
:class:`Identifiers <basyx.aas.model.base.Identifier>`; and mapping
:class:`Identifiers <basyx.aas.model.base.Identifier>` to :class:`~basyx.aas.model.base.Identifiable` objects.
"""

import abc
import hashlib
from typing import List, Optional, TypeVar, MutableSet, Generic, \
    Iterable, Dict, Iterator, Tuple, Union, Any

from .base import Referable, Identifiable, Identifier, \
    UniqueIdShortNamespace, NameType, NamespaceSet, Qualifier, Extension
from ..backend import backends
from basyx.aas import model

from basyx.aas.model.protocols import Protocol


class AbstractObjectProvider(metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects, that allow to retrieve :class:`~basyx.aas.model.base.Identifiable` objects
    (resp. proxy objects for remote :class:`~basyx.aas.model.base.Identifiable` objects) by their
    :class:`~basyx.aas.model.base.Identifier`.

    This includes local object stores, database clients and AAS API clients.
    """

    @abc.abstractmethod
    def get_identifiable(self, identifier: Identifier) -> Identifiable:
        """
        Find an :class:`~basyx.aas.model.base.Identifiable` by its :class:`~basyx.aas.model.base.Identifier`

        This may include looking up the object's endpoint in a registry and fetching it from an HTTP server or a
        database.

        :param identifier: :class:`~basyx.aas.model.base.Identifier` of the object to return
        :return: The :class:`~basyx.aas.model.base.Identifiable` object (or a proxy object for a remote
                 :class:`~basyx.aas.model.base.Identifiable` object)
        :raises KeyError: If no such :class:`~.basyx.aas.model.base.Identifiable` can be found
        """
        pass

    def get(self, identifier: Identifier,
            default: Optional[Identifiable] = None) -> Optional[Identifiable]:
        """
        Find an object in this set by its :class:`id <basyx.aas.model.base.Identifier>`, with fallback parameter

        :param identifier: :class:`~basyx.aas.model.base.Identifier` of the object to return
        :param default: An object to be returned, if no object with the given
                        :class:`id <basyx.aas.model.base.Identifier>` is found
        :return: The :class:`~basyx.aas.model.base.Identifiable` object with the given
                 :class:`id <basyx.aas.model.base.Identifier>` in the provider. Otherwise the ``default`` object
                 or None, if none is given.
        """
        try:
            return self.get_identifiable(identifier)
        except KeyError:
            return default


_IT = TypeVar('_IT', bound=Identifiable)


class AbstractObjectStore(AbstractObjectProvider, MutableSet[_IT],
                          Generic[_IT], metaclass=abc.ABCMeta):
    """
    Abstract baseclass of for container-like objects for storage of :class:`~basyx.aas.model.base.Identifiable` objects.

    ObjectStores are special ObjectProvides that – in addition to retrieving objects by
    :class:`~basyx.aas.model.base.Identifier` – allow to add and delete objects (i.e. behave like a Python set).
    This includes local object stores (like :class:`~.DictObjectStore`) and database
    :class:`Backends <basyx.aas.backend.backends.Backend>`.

    The AbstractObjectStore inherits from the :class:`~collections.abc.MutableSet` abstract collections class and
    therefore implements all the functions of this class.
    """

    @abc.abstractmethod
    def __init__(self):
        pass

    def add_from(self, other: Iterable[_IT]) -> None:
        for x in other:
            self.add(x)


class DictObjectStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a dict, mapping
    :class:`~basyx.aas.model.base.Identifier` → :class:`~basyx.aas.model.base.Identifiable`
    TODO: Add annotation
    """

    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        self._backend: Dict[Identifier, _IT] = {}
        for x in objects:
            self.add(x)
        self._mapping: Dict[str, Dict[Protocol, str]] = {}

    def get_identifiable(self, identifier: Identifier) -> _IT:
        return self._backend[identifier]

    def add(self, x: _IT, is_aimc: bool = False) -> None:
        if x.id in self._backend and self._backend.get(x.id) is not x:
            raise KeyError(
                "Identifiable object with same id {} is already stored in this store"
                .format(x.id))
        self._backend[x.id] = x

        # Check if the added object is AssetInterfacesMappingConfiguration
        if is_aimc or (isinstance(x, model.Submodel) and self._is_aimc(x)):
            self._add_source_from_AIMC(x)

    def _is_aimc(self, submodel: model.Submodel) -> bool:
        """
        Check if the submodel is an AssetInterfacesMappingConfiguration.
        """
        # Check by idShort
        if submodel.id_short == "AssetInterfacesMappingConfiguration":
            return True

        # Check by semanticId
        if submodel.semantic_id:
            if isinstance(submodel.semantic_id, model.ExternalReference):
                # Check each key in the ExternalReference
                for key in submodel.semantic_id.key:
                    if "assetinterfacesmappingconfiguration" in key.value.lower():
                        return True

        return False

    def _add_source_from_AIMC(self, aimc: model.Submodel) -> None:
        """
        Process AssetInterfacesMappingConfiguration and update _mapping.
        """
        # TODO: Add checking with semanticID
        mapping_configurations = next((sme for sme in aimc.submodel_element if sme.id_short == "MappingConfigurations"),
                                      None)
        if mapping_configurations and isinstance(mapping_configurations, model.SubmodelElementList):
            for config in mapping_configurations.value:
                self._process_mapping_configuration(config)

    def _process_mapping_configuration(self, config: model.SubmodelElementCollection) -> None:
        """
        Process a single MappingConfiguration.
        """
        interface_reference = next((sme for sme in config.value if sme.id_short == "InterfaceReference"), None)
        if not interface_reference or not isinstance(interface_reference, model.ReferenceElement):
            print("InterfaceReference not found or not of type ReferenceElement")
            return

        protocol = self._extract_protocol_from_interface_reference(interface_reference.value)
        if not protocol:
            print(f"Unable to determine protocol for interface reference: {interface_reference.value}")
            return

        # Extract AID parameters
        aid_parameters = self._extract_aid_parameters(interface_reference.value, protocol)

        mapping_relations = next((sme for sme in config.value if sme.id_short == "MappingSourceSinkRelations"), None)
        if mapping_relations and isinstance(mapping_relations, model.SubmodelElementList):
            for relation in mapping_relations.value:
                if isinstance(relation, model.RelationshipElement):
                    self._process_relationship_element(relation, protocol, aid_parameters)
        else:
            print("MappingSourceSinkRelations not found or not of type SubmodelElementList")

    def _process_relationship_element(self, relation: model.RelationshipElement, protocol: Protocol,
                                      aid_parameters: Dict[str, Any]) -> None:
        """
        Process a single RelationshipElement and update _mapping.
        """
        if relation.second:
            second_hash = self.generate_model_reference_hash(relation.second)
            if second_hash not in self._mapping:
                self._mapping[second_hash] = {}

            # Combine AID parameters with the protocol
            self._mapping[second_hash][protocol] = aid_parameters

    def _extract_aid_parameters(self, aid_reference: model.ModelReference, protocol: Protocol) -> Dict[str, Any]:
        """
        Extract parameters from the AID element referenced by aid_reference

        :param aid_reference: ModelReference to the AID element
        :param protocol: Protocol type
        :return: Dictionary containing extracted parameters
        """
        try:
            aid_element = aid_reference.resolve(self)
        except Exception as e:
            print(f"Error resolving AID element for reference: {aid_reference}. Error: {e}")
            return {}

        if not isinstance(aid_element, model.SubmodelElementCollection):
            print(f"AID element is not a SubmodelElementCollection: {type(aid_element)}")
            return {}

        if protocol == Protocol.HTTP:
            return self._extract_http_parameters(aid_element)
        elif protocol == Protocol.MQTT:
            return self._extract_mqtt_parameters(aid_element)
        elif protocol == Protocol.MODBUS:
            return self._extract_modbus_parameters(aid_element)
        else:
            print(f"Unsupported protocol: {protocol}")
            return {}

    def _extract_http_parameters(self, aid_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        parameters = {}
        for element in aid_element.value:
            if element.id_short == "EndpointMetadata":
                for endpoint_element in element.value:
                    if endpoint_element.id_short == "base":
                        parameters["base"] = endpoint_element.value
            elif element.id_short == "InterfaceMetadata":
                for interface_element in element.value:
                    if interface_element.id_short == "Properties":
                        for property_element in interface_element.value:
                            if isinstance(property_element, model.SubmodelElementCollection):
                                property_params = self._extract_property_parameters(property_element)
                                parameters[property_element.id_short] = property_params
        return parameters

    def _extract_mqtt_parameters(self, aid_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        parameters = {}
        for element in aid_element.value:
            if element.id_short == "EndpointMetadata":
                for endpoint_element in element.value:
                    if endpoint_element.id_short == "base":
                        parameters["base"] = endpoint_element.value
            elif element.id_short == "InterfaceMetadata":
                for interface_element in element.value:
                    if interface_element.id_short == "Properties":
                        for property_element in interface_element.value:
                            if isinstance(property_element, model.SubmodelElementCollection):
                                property_params = self._extract_property_parameters(property_element)
                                parameters[property_element.id_short] = property_params
        return parameters

    def _extract_modbus_parameters(self, aid_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        parameters = {}
        for element in aid_element.value:
            if element.id_short == "EndpointMetadata":
                for endpoint_element in element.value:
                    if endpoint_element.id_short == "base":
                        parameters["base"] = endpoint_element.value
            elif element.id_short == "InterfaceMetadata":
                for interface_element in element.value:
                    if interface_element.id_short == "Properties":
                        for property_element in interface_element.value:
                            if isinstance(property_element, model.SubmodelElementCollection):
                                property_params = self._extract_property_parameters(property_element)
                                parameters[property_element.id_short] = property_params
        return parameters

    def _extract_property_parameters(self, property_element: model.SubmodelElementCollection) -> Dict[str, Any]:
        property_params = {}
        for element in property_element.value:
            if element.id_short in ["type", "valueType", "unit"]:
                property_params[element.id_short] = element.value
            elif element.id_short == "forms":
                for form_element in element.value:
                    if form_element.id_short == "href":
                        property_params["href"] = form_element.value
                    elif form_element.id_short.startswith("modv_") or form_element.id_short.startswith(
                            "htv_") or form_element.id_short.startswith("mqv_"):
                        property_params[form_element.id_short] = form_element.value
        return property_params

    def _extract_protocol_from_interface_reference(self, interface_ref: model.ModelReference) -> Optional[Protocol]:
        """
        Extract Protocol information from InterfaceReference.
        """
        try:
            interface_element = interface_ref.resolve(self)
        except Exception as e:
            print(f"Error resolving InterfaceReference: {e}")
            return None

        if not isinstance(interface_element, model.SubmodelElementCollection):
            print(f"Unexpected type for interface element: {type(interface_element)}")
            return None

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

        print(f"Unable to determine protocol for interface: {interface_element.id_short}")
        return None

    def discard(self, x: _IT) -> None:
        if self._backend.get(x.id) is x:
            del self._backend[x.id]

    def generate_model_reference_hash(self, model_ref: model.ModelReference) -> str:
        """
        Generate a hash value for the ModelReference using SHA-256.
        Convert the key to a string and use it as input for the hash function.

        :param model_ref: ModelReference
        :return: generated hash value of the ModelReference
        """
        key_str = "|".join(f"{k.type},{k.value}" for k in model_ref.key)

        return hashlib.sha256(key_str.encode()).hexdigest()

    def add_source(self, referable: model.Referable, protocol: Protocol, source: Union[str, dict]):
        """
        Add a corresponding source to the mapping table. The input is extracted either from the AID or custom input.
        TODO: adapt the source dict to a source class
        """
        model_ref = model.ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)
        if hash_value not in self._mapping:
            self._mapping[hash_value] = {}

        self._mapping[hash_value][protocol] = source

    def get_source(self, referable: model.Referable, protocol: Protocol) -> Optional[Union[str, dict]]:
        """
        find the source for the given referable and protocol
        """
        model_ref = model.ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)
        if hash_value not in self._mapping:
            print("Source is not available")
            return None

        if protocol not in self._mapping[hash_value]:
            print(f"Source for protocol {protocol.value} is not available")
            return None
        return self._mapping[hash_value][protocol]

    def update_referable(self,
                         referable: Referable,
                         protocol: Protocol,
                         max_age: float = 0,
                         recursive: bool = True,
                         _indirect_source: bool = True) -> None:
        """
        Update the local Referable object from any underlying external data source, using an appropriate backend

        If there is no source given, it will find its next ancestor with a source and update from this source.
        If there is no source in any ancestor, this function will do nothing

        :param referable: The object to update
        :param max_age: Maximum age of the local data in seconds. This method may return early, if the previous update
            of the object has been performed less than ``max_age`` seconds ago.
        :param recursive: Also call update on all children of this object. Default is True
        :param _indirect_source: Internal parameter to avoid duplicate updating.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        source = self.get_source(referable, protocol)

        if not _indirect_source:
            # Update was already called on an ancestor of this Referable. Only update it, if it has its own source
            if source:
                backends.get_backend(protocol).update_object(
                    updated_object=referable,
                    store_object=referable,
                    relative_path=[],
                    source=source)

        else:
            # Try to find a valid source for this Referable
            if source:
                backends.get_backend(protocol).update_object(
                    updated_object=referable,
                    store_object=referable,
                    relative_path=[],
                    source=source)
            else:
                store_object, relative_path = self.find_source(referable, protocol)
                if store_object and relative_path is not None:
                    source = self.get_source(store_object, protocol)
                    backends.get_backend(protocol).update_object(
                        updated_object=referable,
                        store_object=store_object,
                        relative_path=list(relative_path),
                        source=source)

        if recursive:
            # update all the children who have their own source
            if isinstance(referable, UniqueIdShortNamespace):
                for namespace_set in referable.namespace_element_sets:
                    if "id_short" not in namespace_set.get_attribute_name_list():
                        continue
                    for referable in namespace_set:
                        self.update_referable(referable, protocol, max_age,
                                              recursive=True,
                                              _indirect_source=False)

    def find_source(self, obj, protocol) -> Tuple[Optional["Referable"], Optional[List[str]]]:  # type: ignore
        """
        Finds the closest source in this objects ancestors. If there is no source, returns None

        :return: Tuple with the closest ancestor with a defined source and the relative path of id_shorts to that
                 ancestor
        """
        # TODO: adapt the function to use get_source function
        referable: Referable = obj
        relative_path: List[NameType] = [obj.id_short]
        while referable is not None:
            source = self.get_source(referable, protocol)
            if source is not None:
                relative_path.reverse()
                return referable, relative_path
            if referable.parent:
                assert isinstance(referable.parent, Referable)
                referable = referable.parent
                relative_path.append(referable.id_short)
                continue
            break
        return None, None

    def update_from(self, obj, other: "Referable",
                    update_source: bool = False):  # type: ignore
        """
        Internal function to updates the object's attributes from another object of a similar type.

        This function should not be used directly. It is typically used by backend implementations (database adapters,
        protocol clients, etc.) to update the object's data,
        after ``update()_referable`` has been called.

        :param obj: The object to update
        :param other: The object to update from
        :param update_source: Update the source attribute with the other's source attribute. This is not propagated
                              recursively
        """
        for name, var in vars(other).items():
            # do not update the parent, namespace_element_sets or source (depending on update_source parameter)
            if name in ("parent",
                        "namespace_element_sets") or name == "source" and not update_source:
                continue
            if isinstance(var, NamespaceSet):
                # update the elements of the NameSpaceSet
                vars(obj)[name].update_nss_from(var)
            else:
                vars(obj)[
                    name] = var  # that variable is not a NameSpaceSet, so it isn't Referable

    def commit_referable(self, referable: "Referable", protocol) -> None:
        """
        Transfer local changes on this object to all underlying external data sources.

        This function commits the current state of this object to its own and each external data source of its
        ancestors. If there is no source, this function will do nothing.
        """
        current_ancestor = referable.parent
        relative_path: List[NameType] = [referable.id_short]
        # Commit to all ancestors with sources
        while current_ancestor:
            assert isinstance(current_ancestor, Referable)
            source = self.get_source(referable, protocol)
            if source:
                backends.get_backend(protocol).commit_object(
                    committed_object=referable,
                    store_object=current_ancestor,
                    relative_path=list(relative_path))
            relative_path.insert(0, current_ancestor.id_short)
            current_ancestor = current_ancestor.parent
        # Commit to own source and check if there are children with sources to commit to
        self._direct_source_commit(referable, protocol)

    def _direct_source_commit(self, referable: "Referable", protocol):
        """
        Commits children of an ancestor recursively, if they have a specific source given
        """
        source = self.get_source(referable, protocol)
        if source:
            backends.get_backend(protocol).commit_object(
                committed_object=referable,
                store_object=referable,
                relative_path=[],
                source=source)

        if isinstance(referable, UniqueIdShortNamespace):
            for namespace_set in referable.namespace_element_sets:
                if "id_short" not in namespace_set.get_attribute_name_list():
                    continue
                for referable in namespace_set:
                    self._direct_source_commit(referable, protocol)

    def __contains__(self, x: object) -> bool:
        if isinstance(x, Identifier):
            return x in self._backend
        if not isinstance(x, Identifiable):
            return False
        return self._backend.get(x.id) is x

    def __len__(self) -> int:
        return len(self._backend)

    def __iter__(self) -> Iterator[_IT]:
        return iter(self._backend.values())


class ObjectProviderMultiplexer(AbstractObjectProvider):
    """
    A multiplexer for Providers of :class:`~basyx.aas.model.base.Identifiable` objects.

    This class combines multiple registries of :class:`~basyx.aas.model.base.Identifiable` objects into a single one
    to allow retrieving :class:`~basyx.aas.model.base.Identifiable` objects from different sources.
    It implements the :class:`~.AbstractObjectProvider` interface to be used as registry itself.

    :ivar registries: A list of :class:`AbstractObjectProviders <.AbstractObjectProvider>` to query when looking up an
                      object
    """

    def __init__(self, registries: Optional[List[AbstractObjectProvider]] = None):
        self.providers: List[
            AbstractObjectProvider] = registries if registries is not None else []

    def get_identifiable(self, identifier: Identifier) -> Identifiable:
        for provider in self.providers:
            try:
                return provider.get_identifiable(identifier)
            except KeyError:
                pass
        raise KeyError(
            "Identifier could not be found in any of the {} consulted registries."
            .format(len(self.providers)))
