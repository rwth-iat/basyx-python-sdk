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
    Iterable, Dict, Iterator, Tuple, Union, Any, TYPE_CHECKING

from basyx.aas.model.base import Referable, Identifiable, Identifier, UniqueIdShortNamespace, NameType, NamespaceSet
from basyx.aas.model import Submodel, ModelReference
from basyx.aas.backend import backends
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
        self._mapping: Dict[str, Dict[Protocol, Union[str, dict]]] = {}

    def get_identifiable(self, identifier: Identifier) -> _IT:
        return self._backend[identifier]

    def add(self, x: _IT, is_aimc: bool = False) -> None:
        if x.id in self._backend and self._backend.get(x.id) is not x:
            raise KeyError(
                "Identifiable object with same id {} is already stored in this store"
                .format(x.id))
        self._backend[x.id] = x

        # Check if the added object is AssetInterfacesMappingConfiguration
        if is_aimc or (isinstance(x, Submodel) and self._is_aimc(x)):
            self.add_source_from_AIMC(x)

    @staticmethod
    def _is_aimc(submodel: "model.Submodel") -> bool:
        """
        Check if the submodel is an AssetInterfacesMappingConfiguration.
        """
        return ProtocolExtractor().check_identifier(submodel, "AssetInterfacesMappingConfiguration")

    def add_source_from_AIMC(self, aimc: "model.Submodel") -> None:
        """
        Process AssetInterfacesMappingConfiguration and update _mapping.
        """
        mapping_configurations = next((sme for sme in aimc.submodel_element if ProtocolExtractor().check_identifier(
            sme, "MappingConfigurations")), None)
        if mapping_configurations:
            for config in mapping_configurations.value:
                self._process_mapping_configuration(config)

    def _process_mapping_configuration(self, config: "model.SubmodelElementCollection") -> None:
        """
        Process a single MappingConfiguration.
        """

        mapping_relations = next((sme for sme in config.value if sme.id_short == "MappingSourceSinkRelations"), None)
        if mapping_relations:
            for relation in mapping_relations.value:
                self._process_relationship_element(relation)
        else:
            print("MappingSourceSinkRelations not found or not of type SubmodelElementList")

    def _process_relationship_element(self, relation: "model.RelationshipElement") -> None:
        """
        Process a single RelationshipElement and update _mapping.
        """
        if relation.second:
            second_hash = self.generate_model_reference_hash(relation.second)
            if second_hash not in self._mapping:
                self._mapping[second_hash] = {}

            try:
                aid_element = relation.first.resolve(self)
            except Exception as e:
                print(f"Error resolving AID element: {e}")
                return

            aid_parameters = self.extract_aid_parameters(aid_element)
            if aid_parameters:
                protocol = aid_parameters.get('protocol')
                if protocol:
                    self._mapping[second_hash][protocol] = aid_parameters
                else:
                    print(f"Unable to determine protocol for relationship: {relation.id_short}")
            else:
                print(f"Failed to extract AID parameters for relationship: {relation.id_short}")

    @staticmethod
    def extract_aid_parameters(aid_element: "model.SubmodelElement") -> Dict[str, Any]:
        extractor = ProtocolExtractor()

        # Find the parent SubmodelElementCollection (interface_element)
        interface_element = aid_element.parent.parent.parent

        protocol = extractor.determine_protocol(interface_element)
        if not protocol:
            print(f"Unable to determine protocol for interface: {interface_element.id_short}")
            return {}

        parameters = extractor.extract_protocol_parameters(aid_element, protocol)
        parameters['protocol'] = protocol  # Add protocol to the parameters
        return parameters

    def discard(self, x: _IT) -> None:
        if self._backend.get(x.id) is x:
            del self._backend[x.id]

            # If the discarded object is an AIMC Submodel, clean up related mappings
            if isinstance(x, Submodel) and self._is_aimc(x):
                self._remove_mapping_for_aimc(x)

    def _remove_mapping_for_aimc(self, aimc: "model.Submodel") -> None:
        """
        Remove all mappings related to the AIMC.
        """
        mapping_configurations = next((sme for sme in aimc.submodel_element if sme.id_short == "MappingConfigurations"),
                                      None)
        if mapping_configurations:
            for config in mapping_configurations.value:
                self._remove_mapping_for_configuration(config)

    def _remove_mapping_for_configuration(self, config: "model.SubmodelElementCollection") -> None:
        """
        Remove mappings for a single MappingConfiguration.
        """
        # TODO: check if only should remove the configuration of related protocols
        mapping_relations = next((sme for sme in config.value if sme.id_short == "MappingSourceSinkRelations"), None)
        if mapping_relations and isinstance(mapping_relations, model.SubmodelElementList):
            for relation in mapping_relations.value:
                if relation.second:
                    second_hash = self.generate_model_reference_hash(relation.second)
                    if second_hash in self._mapping:
                        del self._mapping[second_hash]

    @staticmethod
    def generate_model_reference_hash(model_ref: "model.ModelReference") -> str:
        """
        Generate a hash value for the ModelReference using SHA-256.
        Convert the key to a string and use it as input for the hash function.

        :param model_ref: ModelReference
        :return: generated hash value of the ModelReference
        """
        key_str = "|".join(f"{k.type},{k.value}" for k in model_ref.key)

        return hashlib.sha256(key_str.encode()).hexdigest()

    def add_source(self, referable: "model.Referable", protocol: Protocol, source: Union[str, dict]):
        """
        Add a corresponding source to the mapping table. The input is extracted either from the AID or custom input.
        TODO: adapt the source dict to a source class
        """
        model_ref = ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)
        if hash_value not in self._mapping:
            self._mapping[hash_value] = {}

        self._mapping[hash_value][protocol] = source

    def get_source(self, referable: "model.Referable", protocol: Protocol) -> Optional[Union[str, dict]]:
        """
        find the source for the given referable and protocol
        """
        model_ref = ModelReference.from_referable(referable)
        hash_value = self.generate_model_reference_hash(model_ref)
        if hash_value not in self._mapping:
            print("Source is not available")
            return None

        if protocol not in self._mapping[hash_value]:
            print(f"Source for protocol {protocol.value} is not available")
            return None
        return self._mapping[hash_value][protocol]

    def update_identifiable(self,
                            referable: "model.Referable",
                            protocol: Protocol,
                            max_age: float = 0,
                            recursive: bool = True,
                            _indirect_source: bool = True) -> None:
        """
        Update the local Referable object from any underlying external data source, using an appropriate backend

        If there is no source given, it will find its next ancestor with a source and update from this source.
        If there is no source in any ancestor, this function will do nothing

        :param referable: The object to update
        :param protocol: The protocol to use for updating
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
                        self.update_identifiable(referable, protocol, max_age,
                                                 recursive=True,
                                                 _indirect_source=False)

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
    def update_from(obj, other: "model.Referable",
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
                vars(obj)[name] = var  # that variable is not a NameSpaceSet, so it isn't Referable

    def commit_identifiable(self, referable: "model.Referable", protocol) -> None:
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
                    relative_path=list(relative_path),
                    source=source)
            relative_path.insert(0, current_ancestor.id_short)
            current_ancestor = current_ancestor.parent
        # Commit to own source and check if there are children with sources to commit to
        self._direct_source_commit(referable, protocol)

    def _direct_source_commit(self, referable: "model.Referable", protocol):
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

    def update_referable_value(self,
                               referable: "model.Referable",
                               protocol: Protocol) -> None:
        """
        Update the value of a Referable object from the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to update
        :param protocol: The protocol to use for updating
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        source = self.get_source(referable, protocol)
        if source:
            backends.get_backend(protocol).update_value(
                updated_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

    def commit_referable_value(self,
                               referable: "model.Referable",
                               protocol: Protocol) -> None:
        """
        Commit the value of a Referable object to the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to commit
        :param protocol: The protocol to use for committing
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        source = self.get_source(referable, protocol)
        if source:
            backends.get_backend(protocol).commit_value(
                committed_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

    def subscribe_referable_value(self,
                                  referable: "model.Referable",
                                  protocol: Protocol) -> None:
        """
        Subscribe the value of a Referable object from the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to update
        :param protocol: The protocol to use for updating
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        source = self.get_source(referable, protocol)
        if source:
            backends.get_backend(protocol).update_value(
                updated_object=referable,
                source=source)
        else:
            print(f"No source found for referable {referable.id_short} with protocol {protocol}")

    def publish_referable_value(self,
                                referable: "model.Referable",
                                protocol: Protocol) -> None:
        """
        Publish the value of a Referable object to the external data source,
        using an appropriate backend.

        :param referable: The Referable object whose value to commit
        :param protocol: The protocol to use for committing
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        source = self.get_source(referable, protocol)
        if source:
            backends.get_backend(protocol).commit_value(
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
