# Copyright (c) 2025 the Eclipse BaSyx Authors
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
import warnings
from typing import MutableSet, Iterator, Generic, TypeVar, Dict, List, Optional, Iterable, Set, Tuple

from .base import Identifier, Identifiable


class AbstractObjectProvider(metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects, that allow to retrieve :class:`~basyx.aas.model.base.Identifiable` objects
    (resp. proxy objects for remote :class:`~basyx.aas.model.base.Identifiable` objects) by their
    :class:`~basyx.aas.model.base.Identifier`.

    This includes local object stores, database clients and AAS API clients.
    """
    @abc.abstractmethod
    def get_object(self, identifier: Identifier) -> object:
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

    def fetch(self, identifier: Identifier, default: Optional[object] = None) -> Optional[object]:
        """
        Find an object in this set by its :class:`id <basyx.aas.model.base.Identifier>`, with fallback parameter

        :param identifier: :class:`~basyx.aas.model.base.Identifier` of the object to return
        :param default: An object to be returned, if no object with the given
                        :class:`id <basyx.aas.model.base.Identifier>` is found
        :return: The :class:`~basyx.aas.model.base.Identifiable` object with the given
                 :class:`id <basyx.aas.model.base.Identifier>` in the provider. Otherwise, the ``default`` object
                 or None, if none is given.
        """
        try:
            return self.get_object(identifier)
        except KeyError:
            return default

    def get_identifiable(self, identifier: Identifier) -> Identifiable:
        warnings.warn(
            "`get_identifiable()` is deprecated and will be removed in a future release. Use `get_object()`"
            "instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        obj = self.get_object(identifier)
        if not isinstance(obj, Identifiable):
            raise TypeError(
                f"Object with identifier {identifier} is not an Identifiable (got {type(obj).__name__})."
            )
        return obj

    def get(self, identifier: Identifier, default: Optional[Identifiable] = None) -> Optional[Identifiable]:
        warnings.warn(
            "`get()` is deprecated and will be removed in a future release. Use `fetch()` instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        obj = self.fetch(identifier, default)
        if not (isinstance(obj, Identifiable) or obj is None):
            if not isinstance(obj, Identifiable):
                raise TypeError(
                    f"Object with identifier {identifier} is not an Identifiable or NoneType (got {type(obj).__name__})"
                    f"."
                )
        return obj


_OBJ = TypeVar('_OBJ', bound=object)
_IT = TypeVar('_IT', bound=Identifiable)


class AbstractObjectStore(AbstractObjectProvider, MutableSet[_OBJ], Generic[_OBJ], metaclass=abc.ABCMeta):
    """
    Abstract baseclass of for container-like objects for storage of :class:`~basyx.aas.model.base.Identifiable` objects.

    ObjectStores are special ObjectProvides that – in addition to retrieving objects by
    :class:`~basyx.aas.model.base.Identifier` – allow to add and delete objects (i.e. behave like a Python set).
    This includes local object stores (like :class:`~.DictObjectStore`) and specific object stores
    (like :class:`~basyx.aas.backend.couchdb.CouchDBObjectStore` and
    :class:`~basyx.aas.backend.local_file.LocalFileObjectStore`).

    The AbstractObjectStore inherits from the :class:`~collections.abc.MutableSet` abstract collections class and
    therefore implements all the functions of this class.
    """
    @abc.abstractmethod
    def __init__(self):
        pass


class DictIdentifiableStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a dict, mapping
    :class:`~basyx.aas.model.base.Identifier` → :class:`~basyx.aas.model.base.Identifiable`

    .. note::
        The `DictObjectStore` provides efficient retrieval of objects by their :class:`~basyx.aas.model.base.Identifier`
        However, since object stores are not referenced via the parent attribute, the mapping is not updated
        if the :class:`~basyx.aas.model.base.Identifier` of an :class:`~basyx.aas.model.base.Identifiable` changes.
        For more details, see [issue #216](https://github.com/eclipse-basyx/basyx-python-sdk/issues/216).
        As a result, the `DictObjectStore` is unsuitable for storing objects whose
        :class:`~basyx.aas.model.base.Identifier` may change.
        In such cases, consider using a :class:`~.SetObjectStore` instead.
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        self._backend: Dict[Identifier, _IT] = {}
        for x in objects:
            self.add(x)

    def get_object(self, identifier: Identifier) -> _IT:
        return self._backend[identifier]

    def add(self, x: _IT) -> None:
        if x.id in self._backend and self._backend.get(x.id) is not x:
            raise KeyError("Identifiable object with same id {} is already stored in this store"
                           .format(x.id))
        self._backend[x.id] = x

    def discard(self, x: _IT) -> None:
        if self._backend.get(x.id) is x:
            del self._backend[x.id]

    def update(self, other: Iterable[_IT]) -> None:
        for x in other:
            self.add(x)

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


class DictObjectStore(DictIdentifiableStore[_IT], Generic[_IT]):
    """
    `DictObjectStore` has been renamed to :class:`~.DictIdentifiableStore` and will be removed in a future release.
    Please migrate to :class:`~.DictIdentifiableStore`.
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        warnings.warn(
            "`DictObjectStore` is deprecated and will be removed in a future release. Use "
            "`DictIdentifiableStore` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(objects)


class SetIdentifiableStore(AbstractObjectStore[_IT], Generic[_IT]):
    """
    A local in-memory object store for :class:`~basyx.aas.model.base.Identifiable` objects, backed by a set

    .. note::
        The `SetObjectStore` is slower than the `DictObjectStore` for retrieval of objects, because it has to iterate
        over all objects to find the one with the correct :class:`~basyx.aas.model.base.Identifier`.
        On the other hand, the `SetObjectStore` is more secure, because it is less affected by changes in the
        :class:`~basyx.aas.model.base.Identifier` of an :class:`~basyx.aas.model.base.Identifiable` object.
        Therefore, the `SetObjectStore` is suitable for storing objects whose :class:`~basyx.aas.model.base.Identifier`
        may change.
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        self._backend: Set[_IT] = set()
        for x in objects:
            self.add(x)

    def get_object(self, identifier: Identifier) -> _IT:
        for x in self._backend:
            if x.id == identifier:
                return x
        raise KeyError(identifier)

    def add(self, x: _IT) -> None:
        if x in self:
            # Object is already in store
            return
        try:
            self.get_object(x.id)
        except KeyError:
            self._backend.add(x)
        else:
            raise KeyError(f"Identifiable object with same id {x.id} is already stored in this store")

    def discard(self, x: _IT) -> None:
        self._backend.discard(x)

    def remove(self, x: _IT) -> None:
        self._backend.remove(x)

    def __contains__(self, x: object) -> bool:
        if isinstance(x, Identifier):
            try:
                self.get_object(x)
                return True
            except KeyError:
                return False
        if not isinstance(x, Identifiable):
            return False
        return x in self._backend

    def __len__(self) -> int:
        return len(self._backend)

    def __iter__(self) -> Iterator[_IT]:
        return iter(self._backend)


class SetObjectStore(SetIdentifiableStore[_IT], Generic[_IT]):
    """
    `SetObjectStore` has been renamed to :class:`~.SetIdentifiableStore` and will be removed in a future release.
    Please migrate to :class:`~.SetIdentifiableStore`.
    """
    def __init__(self, objects: Iterable[_IT] = ()) -> None:
        warnings.warn(
            "`SetObjectStore` is deprecated and will be removed in a future release. Use `SetIdentifiableStore`"
            "instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(objects)


class ObjectProviderMultiplexer(AbstractObjectProvider):
    """
    A multiplexer for Providers of :class:`~basyx.aas.model.base.Identifiable` objects.

    This class combines multiple registries of :class:`~basyx.aas.model.base.Identifiable` objects into a single one
    to allow retrieving :class:`~basyx.aas.model.base.Identifiable` objects from different sources.
    It implements the :class:`~.AbstractObjectProvider` interface to be used as registry itself.

    :param registries: A list of :class:`AbstractObjectProviders <.AbstractObjectProvider>` to query when looking up an
                      object
    """
    def __init__(self, registries: Optional[List[AbstractObjectProvider]] = None):
        self.providers: List[AbstractObjectProvider] = registries if registries is not None else []

    def get_object(self, identifier: Identifier) -> object:
        for provider in self.providers:
            try:
                return provider.get_object(identifier)
            except KeyError:
                pass
        raise KeyError("Identifier could not be found in any of the {} consulted registries."
                       .format(len(self.providers)))
