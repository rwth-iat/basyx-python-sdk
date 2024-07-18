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
from typing import List, Optional, TypeVar, MutableSet, Generic, \
    Iterable, Dict, Iterator, Tuple

from .base import Referable, Identifiable, Identifier, \
    UniqueIdShortNamespace, NameType, NamespaceSet, Qualifier, Extension
from ..backend import backends


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

    def get(self, identifier: Identifier, default: Optional[Identifiable] = None) -> Optional[Identifiable]:
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


class AbstractObjectStore(AbstractObjectProvider, MutableSet[_IT], Generic[_IT], metaclass=abc.ABCMeta):
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

    def update(self, other: Iterable[_IT]) -> None:
        for x in other:
            self.add(x)


class DictObjectStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a dict, mapping
    :class:`~basyx.aas.model.base.Identifier` → :class:`~basyx.aas.model.base.Identifiable`
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        self._backend: Dict[Identifier, _IT] = {}
        for x in objects:
            self.add(x)

    def get_identifiable(self, identifier: Identifier) -> _IT:
        return self._backend[identifier]

    def add(self, x: _IT) -> None:
        if x.id in self._backend and self._backend.get(x.id) is not x:
            raise KeyError("Identifiable object with same id {} is already stored in this store"
                           .format(x.id))
        self._backend[x.id] = x

    def discard(self, x: _IT) -> None:
        if self._backend.get(x.id) is x:
            del self._backend[x.id]

    def update(self,
               obj: Referable,
               max_age: float = 0,
               recursive: bool = False,
               _indirect_source: bool = True) -> None:
        # TODO: discuss the method name and signature used here
        """
        Update the local Referable object from any underlying external data source, using an appropriate backend

        If there is no source given, it will find its next ancestor with a source and update from this source.
        If there is no source in any ancestor, this function will do nothing

        :param identifier: :class:`~basyx.aas.model.base.Identifier`
        of the object to update
        :param max_age: Maximum age of the local data in seconds. This method may return early, if the previous update
                        of the object has been performed less than ``max_age`` seconds ago.
        :param recursive: Also call update on all children of this object. Default is True
        :param _indirect_source: Internal parameter to avoid duplicate updating.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        if not _indirect_source:
            # Update was already called on an ancestor of this Referable. Only update it, if it has its own source
            if obj.source != "":
                backends.get_backend(obj.source).update_object(updated_object=obj,
                                                               store_object=obj,
                                                               relative_path=[])

        else:
            # Try to find a valid source for this Referable
            if obj.source != "":
                backends.get_backend(obj.source).update_object(updated_object=obj,
                                                               store_object=obj,
                                                               relative_path=[])
            else:
                store_object, relative_path = self.find_source(obj)
                if store_object and relative_path is not None:
                    backends.get_backend(store_object.source).update_object(updated_object=obj,
                                                                            store_object=store_object,
                                                                            relative_path=list(relative_path))

        if recursive:
            # update all the children who have their own source
            if isinstance(obj, UniqueIdShortNamespace):
                for namespace_set in obj.namespace_element_sets:
                    if "id_short" not in namespace_set.get_attribute_name_list():
                        continue
                    for referable in namespace_set:
                        referable.update(max_age, recursive=True, _indirect_source=False)

    def find_source(self, obj) -> Tuple[Optional["Referable"], Optional[List[str]]]:  # type: ignore
        """
        Finds the closest source in this objects ancestors. If there is no source, returns None

        :return: Tuple with the closest ancestor with a defined source and the relative path of id_shorts to that
                 ancestor
        """
        referable: Referable = obj
        relative_path: List[NameType] = [obj.id_short]
        while referable is not None:
            if referable.source != "":
                relative_path.reverse()
                return referable, relative_path
            if referable.parent:
                assert isinstance(referable.parent, Referable)
                referable = referable.parent
                relative_path.append(referable.id_short)
                continue
            break
        return None, None

    def update_from(self, obj, other: "Referable", update_source: bool = False):
        """
        Internal function to updates the object's attributes from another object of a similar type.

        This function should not be used directly. It is typically used by backend implementations (database adapters,
        protocol clients, etc.) to update the object's data, after ``update()`` has been called.

        :param other: The object to update from
        :param update_source: Update the source attribute with the other's source attribute. This is not propagated
                              recursively
        """
        for name, var in vars(other).items():
            # do not update the parent, namespace_element_sets or source (depending on update_source parameter)
            if name in ("parent", "namespace_element_sets") or name == "source" and not update_source:
                continue
            if isinstance(var, NamespaceSet):
                # update the elements of the NameSpaceSet
                self.update_nss_from(vars(obj)[name], var)
            else:
                vars(obj)[name] = var  # that variable is not a NameSpaceSet, so it isn't Referable

        # Todo: Implement function including tests
    def update_nss_from(self, obj, other: "NamespaceSet"):
        """
        Update a NamespaceSet from a given NamespaceSet.

        WARNING: By updating, the "other" NamespaceSet gets destroyed.

        :param other: The NamespaceSet to update from
        """
        objects_to_add: List[
            _NSO] = []  # objects from the other nss to add to self
        objects_to_remove: List[
            _NSO] = []  # objects to remove from obj
        for other_object in other:
            try:
                if isinstance(other_object, Referable):
                    backend, case_sensitive = obj._backend[
                        "id_short"]
                    referable = backend[
                        other_object.id_short if case_sensitive else other_object.id_short.upper()]
                    self.update_from(referable, other_object,
                                     update_source=True)  # type: ignore
                elif isinstance(other_object, Qualifier):
                    backend, case_sensitive = obj._backend["type"]
                    qualifier = backend[
                        other_object.type if case_sensitive else other_object.type.upper()]
                    # qualifier.update_from(other_object, update_source=True) # TODO: What should happend here?
                elif isinstance(other_object, Extension):
                    backend, case_sensitive = obj._backend["name"]
                    extension = backend[
                        other_object.name if case_sensitive else other_object.name.upper()]
                    # extension.update_from(other_object, update_source=True) # TODO: What should happend here?
                else:
                    raise TypeError("Type not implemented")
            except KeyError:
                # other object is not in NamespaceSet
                objects_to_add.append(other_object)
        for attr_name, (backend, case_sensitive) in obj._backend.items():
            for attr_name_other, (backend_other,
                                  case_sensitive_other) in other._backend.items():
                if attr_name is attr_name_other:
                    for item in backend.values():
                        if not backend_other.get(
                                obj._get_attribute(item, attr_name,
                                                   case_sensitive)):
                            # referable does not exist in the other NamespaceSet
                            objects_to_remove.append(item)
        for object_to_add in objects_to_add:
            other.remove(object_to_add)
            obj.add(object_to_add)  # type: ignore
        for object_to_remove in objects_to_remove:
            obj.remove(object_to_remove)  # type: ignore

    def commit(self, obj) -> None:
        """
        Transfer local changes on this object to all underlying external data sources.

        This function commits the current state of this object to its own and each external data source of its
        ancestors. If there is no source, this function will do nothing.
        """
        current_ancestor = obj.parent
        relative_path: List[NameType] = [obj.id_short]
        # Commit to all ancestors with sources
        while current_ancestor:
            assert isinstance(current_ancestor, Referable)
            if current_ancestor.source != "":
                backends.get_backend(current_ancestor.source).commit_object(committed_object=obj,
                                                                            store_object=current_ancestor,
                                                                            relative_path=list(relative_path))
            relative_path.insert(0, current_ancestor.id_short)
            current_ancestor = current_ancestor.parent
        # Commit to own source and check if there are children with sources to commit to
        self._direct_source_commit(obj)

    def _direct_source_commit(self, obj):
        """
        Commits children of an ancestor recursively, if they have a specific source given
        """
        if obj.source != "":
            backends.get_backend(obj.source).commit_object(committed_object=obj,
                                                           store_object=obj,
                                                           relative_path=[])

        if isinstance(obj, UniqueIdShortNamespace):
            for namespace_set in obj.namespace_element_sets:
                if "id_short" not in namespace_set.get_attribute_name_list():
                    continue
                for referable in namespace_set:
                    self._direct_source_commit(referable)

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
        self.providers: List[AbstractObjectProvider] = registries if registries is not None else []

    def get_identifiable(self, identifier: Identifier) -> Identifiable:
        for provider in self.providers:
            try:
                return provider.get_identifiable(identifier)
            except KeyError:
                pass
        raise KeyError("Identifier could not be found in any of the {} consulted registries."
                       .format(len(self.providers)))
