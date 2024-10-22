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
    Iterable, Dict, Iterator, Tuple, Any, TYPE_CHECKING, Union

from basyx.aas.backend import backends
from basyx.aas.model import Submodel, ModelReference, SubmodelElementList, ModelReference
from basyx.aas.model.base import Referable, Identifiable, Identifier, UniqueIdShortNamespace, NameType
from basyx.aas.model.protocols import Protocol, ProtocolExtractor

if TYPE_CHECKING:
    from basyx.aas import model


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
        self._mapping: Dict[str, Dict[Union[Protocol, str], Any]] = {}

    def add_from(self, other: Iterable[_IT]) -> None:
        for x in other:
            self.add(x)

    def load_referable(self,
                       referable: "model.Referable",
                       protocol: Optional[Union[Protocol, str]] = None,
                       max_age: float = 0,
                       recursive: bool = True,
                       _indirect_source: bool = True) -> None:
        """
        Update the local Referable object from any underlying external data source, using an appropriate backend

        If there is no source given, it will find its next ancestor with a source and update from this source.
        If there is no source in any ancestor, this function will do nothing

        :param referable: The object to update
        :param protocol: The protocol to use for updating. If None, the first available protocol will be used.
        :param max_age: Maximum age of the local data in seconds. This method may return early, if the previous update
            of the object has been performed less than ``max_age`` seconds ago.
        :param recursive: Also call update on all children of this object. Default is True
        :param _indirect_source: Internal parameter to avoid duplicate updating.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        if protocol is None:
            protocol = self._get_first_available_protocol(referable)
            if protocol is None:
                print(f"No available protocol found for referable {referable.id_short}")
                return

        source = self.get_source(referable, protocol)

        if not _indirect_source:
            # Update was already called on an ancestor of this Referable. Only update it, if it has its own source
            if source:
                backends.get_object_backend(protocol).update_object(
                    updated_object=referable,
                    store_object=referable,
                    relative_path=[],
                    source=source)

        else:
            # Try to find a valid source for this Referable
            if source:
                backends.get_object_backend(protocol).update_object(
                    updated_object=referable,
                    store_object=referable,
                    relative_path=[],
                    source=source)
            else:
                store_object, relative_path = self.find_source(referable, protocol)
                if store_object and relative_path is not None:
                    source = self.get_source(store_object, protocol)
                    backends.get_object_backend(protocol).update_object(
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
                        self.load_referable(referable, protocol, max_age,
                                            recursive=True,
                                            _indirect_source=False)

    def store_referable(self, referable: "model.Referable", protocol: Optional[Union[Protocol, str]] = None) \
            -> None:
        """
        Transfer local changes on this object to all underlying external data sources.

        This function commits the current state of this object to its own and each external data source of its
        ancestors. If there is no source, this function will do nothing.

        :param referable: The Referable object to commit
        :param protocol: The protocol to use for committing. If None, the first available protocol will be used.
        """
        if protocol is None:
            protocol = self._get_first_available_protocol(referable)
            if protocol is None:
                print(f"No available protocol found for referable {referable.id_short}")
                return

        current_ancestor = referable.parent
        relative_path: List[NameType] = [referable.id_short]
        # Commit to all ancestors with sources
        while current_ancestor:
            assert isinstance(current_ancestor, Referable)
            source = self.get_source(current_ancestor, protocol)
            if source:
                backends.get_object_backend(protocol).commit_object(
                    committed_object=referable,
                    store_object=current_ancestor,
                    relative_path=list(relative_path),
                    source=source)
            relative_path.insert(0, current_ancestor.id_short)
            current_ancestor = current_ancestor.parent
        # Commit to own source and check if there are children with sources to commit to
        self._direct_source_commit(referable, protocol)

    def _direct_source_commit(self, referable: "model.Referable", protocol: Union[Protocol, str]) -> None:
        """
        Commits children of an ancestor recursively, if they have a specific source given
        """
        source = self.get_source(referable, protocol)
        if source:
            backends.get_object_backend(protocol).commit_object(
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

    def get_source(self, referable: "model.Referable", protocol: Union[Protocol, str]) -> Optional[Any]:
        """
        Find the source for the given Referable and protocol type in the mapping table.
        """
        model_ref = ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)
        if hash_value not in self._mapping:
            return None

        if protocol not in self._mapping[hash_value]:
            print(f"Source for protocol {protocol} is not available")
            return None
        return self._mapping[hash_value][protocol]

    def _get_first_available_protocol(self, referable: "model.Referable") -> Optional[Union[Protocol, str]]:
        """
        Extract the first available protocol for the given referable.

        :param referable: The Referable object to check for available protocols
        :return: The first available Protocol, or None if no protocols are available
        """
        model_ref = ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)

        if hash_value in self._mapping:
            available_protocols = list(self._mapping[hash_value].keys())
            if available_protocols:
                return available_protocols[0]

        return None

    def find_source(self, obj, protocol) -> Tuple[Optional["model.Referable"], Optional[List[str]]]:  # type: ignore
        """
        Finds the closest source in this object's ancestors. If there is no source, returns None

        :return: Tuple with the closest ancestor with a defined source and the relative path of id_shorts to that
                 ancestor
        """
        referable: "model.Referable" = obj
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

    @staticmethod
    def generate_model_reference_hash(model_ref: "model.Reference") -> str:
        """
        Generate a hash value for the ModelReference using SHA-256.
        Convert the key to a string and use it as input for the hash function.

        :param model_ref: ModelReference
        :return: generated hash value of the ModelReference
        """
        key_str = "|".join(f"{k.type},{k.value}" for k in model_ref.key)

        return hashlib.sha256(key_str.encode()).hexdigest()

    def add_source(self, referable: "model.Referable", protocol: Union[Protocol, str], source: Any) -> None:
        """
        Add a corresponding source to the mapping table. The input is extracted either from the AID or custom input.
        TODO: adapt the source dict to a source class
        """
        model_ref = ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)
        if hash_value not in self._mapping:
            self._mapping[hash_value] = {}

        self._mapping[hash_value][protocol] = source


class DictObjectStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a dict, mapping
    :class:`~basyx.aas.model.base.Identifier` → :class:`~basyx.aas.model.base.Identifiable`
    TODO: Add annotation
    """

    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        super().__init__()
        self._backend: Dict[Identifier, _IT] = {}
        for x in objects:
            self.add(x)

    def get_identifiable(self, identifier: Identifier) -> _IT:
        return self._backend[identifier]

    def add(self, x: _IT) -> None:
        if x.id in self._backend and self._backend.get(x.id) is not x:
            raise KeyError(
                "Identifiable object with same id {} is already stored in this store"
                .format(x.id))
        self._backend[x.id] = x

        # Check if the added object is AssetInterfacesMappingConfiguration
        if isinstance(x, Submodel):
            if self._is_aimc(x):
                self.add_source_from_AIMC(x)

    @staticmethod
    def _is_aimc(submodel: "model.Submodel") -> bool:
        """
        Non-public function to check if the submodel is an AssetInterfacesMappingConfiguration (AIMC).

        We assume that the Submodel is an AIMC if it contains a corresponding Identifier.
        """
        return ProtocolExtractor().check_identifier(submodel, "AssetInterfacesMappingConfiguration")

    def add_source_from_AIMC(self, aimc: "model.Submodel") -> None:
        """
        Process AssetInterfacesMappingConfiguration and update the mapping table "_mapping".

        The SubmodelElementCollections in the "MappingConfigurations" (SubmodelElementList) are processed.
        The related AID elements are extracted from the AIMC Submodel and added to the mapping table.
        """
        mapping_configurations = next((sme for sme in aimc.submodel_element if ProtocolExtractor().check_identifier(
            sme, "MappingConfigurations")), None)
        if mapping_configurations:
            if hasattr(mapping_configurations, 'value'):
                for config in mapping_configurations.value:
                    self._process_configuration(config)

    def _process_configuration(self, config: "model.SubmodelElementCollection") -> None:
        """
        Process a single Configuration in the MappingConfiguration.
        """
        protocol = None
        interface_reference = config.get_referable('InterfaceReference')
        if hasattr(interface_reference, 'value') and interface_reference.value:
            if isinstance(interface_reference.value, ModelReference):
                interface_element = interface_reference.value.resolve(self)
                protocol = ProtocolExtractor().determine_protocol(interface_element)

        if protocol is not None:
            mapping_relations = next((sme for sme in config.value if sme.id_short ==
                                      "MappingSourceSinkRelations"), None)
            if mapping_relations:
                if hasattr(mapping_relations, 'value'):
                    for relation in mapping_relations.value:
                        self._process_relationship_element(relation, protocol)
            else:
                print("MappingSourceSinkRelations not found or not of type SubmodelElementList")

    def _process_relationship_element(self, relation: "model.RelationshipElement",
                                      protocol: Union[Protocol, str]) -> None:
        """
        Process a single RelationshipElement in a Configuration and update _mapping.
        """
        if relation.second:
            second_hash = self.generate_model_reference_hash(relation.second)
            if second_hash not in self._mapping:
                self._mapping[second_hash] = {}

            if isinstance(relation.first, ModelReference):
                try:
                    aid_property = relation.first.resolve(self)
                except Exception as e:
                    print(f"Error resolving AID element: {e}")
                    return

            aid_parameters = self.extract_aid_parameters(aid_property, protocol)
            if aid_parameters:
                if protocol:
                    self._mapping[second_hash][protocol] = aid_parameters
                else:
                    print(f"Unable to determine protocol for relationship: {relation.id_short}")
            else:
                print(f"Failed to extract AID parameters for relationship: {relation.id_short}")

    @staticmethod
    def extract_aid_parameters(aid_property: "model.SubmodelElementCollection",
                               protocol: Optional[Union[Protocol, str]] = None) -> Dict[str, Any]:
        if protocol is None:
            # Find the parent SubmodelElementCollection (interface_element)
            interface_element = ProtocolExtractor().traverse_to_aid_interface(aid_property)
            protocol = ProtocolExtractor().determine_protocol(interface_element)
        assert protocol is not None
        parameters = ProtocolExtractor().extract_protocol_parameters(aid_property, protocol)
        # Add protocol to the parameters. This is necessary for the backend to determine the correct protocol
        parameters['protocol'] = protocol
        return parameters

    def discard(self, x: _IT) -> None:
        if self._backend.get(x.id) is x:
            del self._backend[x.id]

            # If the discarded object is an AIMC Submodel, clean up related mappings
            if isinstance(x, Submodel) and self._is_aimc(x):
                self._remove_mapping_for_aimc(x)

    def _remove_mapping_for_aimc(self, aimc: "model.Submodel") -> None:
        """
        Remove all mappings related to the AIMC from the mapping table.
        """
        mapping_configurations = next((sme for sme in aimc.submodel_element if sme.id_short == "MappingConfigurations"),
                                      None)
        if mapping_configurations:
            if hasattr(mapping_configurations, 'value'):
                for config in mapping_configurations.value:
                    self._remove_mapping_for_configuration(config)

    def _remove_mapping_for_configuration(self, config: "model.SubmodelElementCollection") -> None:
        """
        Remove mappings for a single Configuration in the MappingConfiguration.

        We assume the integration source is either described with AID or only with a custom protocol.
        If a Referable has mixed sources, the whole configuration will be removed.
        """
        # TODO: check if only should remove the configuration of related protocols
        mapping_relations = next((sme for sme in config.value if sme.id_short == "MappingSourceSinkRelations"), None)
        if mapping_relations and isinstance(mapping_relations, SubmodelElementList):
            for relation in mapping_relations.value:
                if relation.second:
                    second_hash = self.generate_model_reference_hash(relation.second)
                    if second_hash in self._mapping:
                        del self._mapping[second_hash]

    def update_referable_value(self,
                               referable: "model.Referable",
                               protocol: Optional[Union[Protocol, str]] = None) -> None:
        """
        Update the value of a Referable object from the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to update
        :param protocol: The protocol to use for updating. If None, the first available protocol will be used.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        if protocol is None:
            protocol = self._get_first_available_protocol(referable)
            if protocol is None:
                print(f"No available protocol found for referable {referable.id_short}")
                return

        source = self.get_source(referable, protocol)
        if source:
            backends.get_value_backend(protocol).update_value(
                updated_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

    def commit_referable_value(self,
                               referable: "model.Referable",
                               protocol: Optional[Union[Protocol, str]] = None) -> None:
        """
        Commit the value of a Referable object to the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to commit
        :param protocol: The protocol to use for committing. If None, the first available protocol will be used.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        if protocol is None:
            protocol = self._get_first_available_protocol(referable)
            if protocol is None:
                print(f"No available protocol found for referable {referable.id_short}")
                return

        source = self.get_source(referable, protocol)
        if source:
            backends.get_value_backend(protocol).commit_value(
                committed_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

    def subscribe_referable_value(self,
                                  referable: "model.Referable",
                                  protocol: Optional[Union[Protocol, str]] = None) -> None:
        """
        Subscribe the value of a Referable object from the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to update
        :param protocol: The protocol to use for updating
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        if protocol is None:
            protocol = self._get_first_available_protocol(referable)
            if protocol is None:
                print(f"No available protocol found for referable {referable.id_short}")
                return

        source = self.get_source(referable, protocol)
        if source:
            backends.get_value_backend(protocol).update_value(
                updated_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

    def publish_referable_value(self,
                                referable: "model.Referable",
                                protocol: Optional[Union[Protocol, str]] = None) -> None:
        """
        Publish the value of a Referable object to the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to commit
        :param protocol: The protocol to use for committing
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        if protocol is None:
            protocol = self._get_first_available_protocol(referable)
            if protocol is None:
                print(f"No available protocol found for referable {referable.id_short}")
                return

        source = self.get_source(referable, protocol)
        if source:
            backends.get_value_backend(protocol).commit_value(
                committed_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

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
