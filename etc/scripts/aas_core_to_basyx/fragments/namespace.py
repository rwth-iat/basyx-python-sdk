import abc
import itertools
from typing import List, Type, Iterator, MutableSet, Generic, Union, Tuple, Iterable, Optional, Callable, Dict, \
    MutableSequence, overload, TypeVar

ATTRIBUTE_TYPES = Union[NameType, Reference, QualifierType]

ATTRIBUTES_CONSTRAINT_IDS = {
    "id_short": 22,  # Referable,
    "type": 21,  # Qualifier,
    "name": 77,  # Extension,
    # "id_short": 134, # model.OperationVariable
}

_NSO = TypeVar('_NSO', bound=Union["Referable", "Qualifier", "HasSemantics", "Extension"])

class Namespace(metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold  objects and resolve them by their
    specific attribute.

    <<abstract>>

    :ivar namespace_element_sets: List of :class:`NamespaceSets <basyx.aas.model.base.NamespaceSet>`
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []

    def _get_object(self, object_type: Type[_NSO], attribute_name: str, attribute) -> _NSO:
        """
        Find an :class:`~._NSO` in this namespace by its attribute

        :raises KeyError: If no such :class:`~._NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            try:
                return ns_set.get_object_by_attribute(attribute_name, attribute)
            except KeyError:
                continue
        raise KeyError(f"{object_type.__name__} with {attribute_name} {attribute} not found in this namespace")

    def _add_object(self, attribute_name: str, obj: _NSO) -> None:
        """
        Add an :class:`~._NSO` to this namespace by its attribute

        :raises KeyError: If no such :class:`~._NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            if attribute_name not in ns_set.get_attribute_name_list():
                continue
            ns_set.add(obj)
            return
        raise ValueError(f"{obj!r} can't be added to this namespace")

    def _remove_object(self, object_type: type, attribute_name: str, attribute) -> None:
        """
        Remove an :class:`~.NSO` from this namespace by its attribute

        :raises KeyError: If no such :class:`~.NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            if attribute_name in ns_set.get_attribute_name_list():
                try:
                    ns_set.remove_by_id(attribute_name, attribute)
                    return
                except KeyError:
                    continue
        raise KeyError(f"{object_type.__name__} with {attribute_name} {attribute} not found in this namespace")


class UniqueIdShortNamespace(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold :class:`~.Referable` objects and resolve them by
    their id_short.

    A Namespace can contain multiple :class:`NamespaceSets <NamespaceSet>`, which contain :class:`~.Referable` objects
    of different types. However, the id_short of each object must be unique across all NamespaceSets of one Namespace.



    :ivar namespace_element_sets: A list of all :class:`NamespaceSets <.NamespaceSet>` of this Namespace
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []

    def get_referable(self, id_short: NameType) -> Referable:
        """
        Find a :class:`~.Referable` in this Namespace by its id_short

        :param id_short: id_short
        :returns: :class:`~.Referable`
        :raises KeyError: If no such :class:`~.Referable` can be found
        """
        return super()._get_object(Referable, "id_short", id_short)  # type: ignore

    def add_referable(self, referable: Referable) -> None:
        """
        Add a :class:`~.Referable` to this Namespace

        :param referable: The :class:`~.Referable` to add
        :raises KeyError: If a :class:`~.Referable` with the same name is already present in this namespace
        :raises ValueError: If the given :class:`~.Referable` already has a parent namespace
        """
        return super()._add_object("id_short", referable)

    def remove_referable(self, id_short: NameType) -> None:
        """
        Remove a :class:`~.Referable` from this Namespace by its ``id_short``

        :param id_short: id_short
        :raises KeyError: If no such :class:`~.Referable` can be found
        """
        return super()._remove_object(Referable, "id_short", id_short)

    def __iter__(self) -> Iterator[Referable]:
        namespace_set_list: List[NamespaceSet] = []
        for namespace_set in self.namespace_element_sets:
            if len(namespace_set) == 0:
                namespace_set_list.append(namespace_set)
                continue
            if "id_short" in namespace_set.get_attribute_name_list():
                namespace_set_list.append(namespace_set)
        return itertools.chain.from_iterable(namespace_set_list)


class UniqueSemanticIdNamespace(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold HasSemantics objects and resolve them by their
    their semantic_id.

    A Namespace can contain multiple NamespaceSets, which contain HasSemantics objects of different types. However, the
    the semantic_id of each object must be unique across all NamespaceSets of one Namespace.

    :ivar namespace_element_sets: A list of all NamespaceSets of this Namespace
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []

    def get_object_by_semantic_id(self, semantic_id: Reference) -> HasSemantics:
        """
        Find an HasSemantics in this Namespaces by its semantic_id

        :raises KeyError: If no such HasSemantics can be found
        """
        return super()._get_object(HasSemantics, "semantic_id", semantic_id)  # type: ignore

    def remove_object_by_semantic_id(self, semantic_id: Reference) -> None:
        """
        Remove an HasSemantics from this Namespace by its semantic_id

        :raises KeyError: If no such HasSemantics can be found
        """
        return super()._remove_object(HasSemantics, "semantic_id", semantic_id)




class NamespaceSet(MutableSet[_NSO], Generic[_NSO]):
    """
    Helper class for storing AAS objects of a given type in a Namespace and find them by their unique attribute.

    This class behaves much like a set of AAS objects of a defined type, but uses dicts internally to rapidly
    find those objects by their unique attribute. Additionally, it manages the ``parent`` attribute of the stored
    AAS objects and ensures the uniqueness of their attribute within the Namespace.

    Use ``add()``, ``remove()``, ``pop()``, ``discard()``, ``clear()``, ``len()``, ``x in`` checks and iteration  just
    like on a normal set of AAS objects. To get an AAS object by its attribute, use ``get_object()`` or ``get()``
    (the latter one allows a default argument and returns None instead of raising a KeyError). As a bonus, the ``x in``
    check supports checking for existence of attribute *or* a concrete AAS object.

    :ivar parent: The Namespace this set belongs to

    To initialize, use the following parameters:

    :param parent: The Namespace this set belongs to
    :param attribute_names: List of attribute names, for which objects should be unique in the set. The bool flag
        indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
    :param items: A given list of AAS items to be added to the set

    :raises KeyError: When ``items`` contains multiple objects with same unique attribute
    """
    def __init__(self, parent: Union[UniqueIdShortNamespace, UniqueSemanticIdNamespace, Qualifiable, HasExtension],
                 attribute_names: List[Tuple[str, bool]], items: Iterable[_NSO] = (),
                 item_add_hook: Optional[Callable[[_NSO, Iterable[_NSO]], None]] = None,
                 item_id_set_hook: Optional[Callable[[_NSO], None]] = None,
                 item_id_del_hook: Optional[Callable[[_NSO], None]] = None) -> None:
        """
        Initialize a new NamespaceSet.

        This initializer automatically takes care of adding this set to the ``namespace_element_sets`` list of the
        Namespace.

        :param parent: The Namespace this set belongs to
        :attribute_names: List of attribute names, for which objects should be unique in the set. The bool flag
                          indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
        :param items: A given list of AAS items to be added to the set
        :param item_add_hook: A function that is called for each item that is added to this NamespaceSet, even when
                              it is initialized. The first parameter is the item that is added while the second is
                              an iterator over all currently contained items. Useful for constraint checking.
        :param item_id_set_hook: A function called to calculate the identifying attribute (e.g. id_short) of an object
                                 on-the-fly when it is added. Used for the SubmodelElementList implementation.
        :param item_id_del_hook: A function that is called for each item removed from this NamespaceSet. Used in
                                 SubmodelElementList to unset id_shorts on removal. Should not be used for
                                 constraint checking, as the hook is called after removal.
        :raises AASConstraintViolation: When ``items`` contains multiple objects with same unique attribute or when an
                                        item doesn't has an identifying attribute
        """
        self.parent = parent
        parent.namespace_element_sets.append(self)
        self._backend: Dict[str, Tuple[Dict[ATTRIBUTE_TYPES, _NSO], bool]] = {}
        self._item_add_hook: Optional[Callable[[_NSO, Iterable[_NSO]], None]] = item_add_hook
        self._item_id_set_hook: Optional[Callable[[_NSO], None]] = item_id_set_hook
        self._item_id_del_hook: Optional[Callable[[_NSO], None]] = item_id_del_hook
        for name, case_sensitive in attribute_names:
            self._backend[name] = ({}, case_sensitive)
        try:
            for i in items:
                self.add(i)
        except Exception:
            # Do a rollback, when an exception occurs while adding items
            self.clear()
            raise

    @staticmethod
    def _get_attribute(x: object, attr_name: str, case_sensitive: bool):
        attr_value = getattr(x, attr_name)
        return attr_value if case_sensitive or not isinstance(attr_value, str) else attr_value.upper()

    def get_attribute_name_list(self) -> List[str]:
        return list(self._backend.keys())

    def contains_id(self, attribute_name: str, identifier: ATTRIBUTE_TYPES) -> bool:
        try:
            backend, case_sensitive = self._backend[attribute_name]
        except KeyError:
            return False
        # if the identifier is not a string we ignore the case sensitivity
        if case_sensitive or not isinstance(identifier, str):
            return identifier in backend
        return identifier.upper() in backend

    def __contains__(self, obj: object) -> bool:
        attr_name = next(iter(self._backend))
        try:
            attr_value = self._get_attribute(obj, attr_name, self._backend[attr_name][1])
        except AttributeError:
            return False
        return self._backend[attr_name][0].get(attr_value) is obj

    def __len__(self) -> int:
        return len(next(iter(self._backend.values()))[0])

    def __iter__(self) -> Iterator[_NSO]:
        return iter(next(iter(self._backend.values()))[0].values())

    def add(self, element: _NSO):
        if element.parent is not None and element.parent is not self.parent:
            raise ValueError("Object has already a parent; it cannot belong to two namespaces.")
            # TODO remove from current parent instead (allow moving)?

        self._execute_item_id_set_hook(element)
        self._validate_namespace_constraints(element)
        self._execute_item_add_hook(element)

        element.parent = self.parent
        for key_attr_name, (backend, case_sensitive) in self._backend.items():
            backend[self._get_attribute(element, key_attr_name, case_sensitive)] = element

    def _validate_namespace_constraints(self, element: _NSO):
        for set_ in self.parent.namespace_element_sets:
            for key_attr_name, (backend_dict, case_sensitive) in set_._backend.items():
                if hasattr(element, key_attr_name):
                    key_attr_value = self._get_attribute(element, key_attr_name, case_sensitive)
                    self._check_attr_is_not_none(element, key_attr_name, key_attr_value)
                    self._check_value_is_not_in_backend(element, key_attr_name, key_attr_value, backend_dict, set_)

    def _check_attr_is_not_none(self, element: _NSO, attr_name: str, attr):
        if attr is None:
            if attr_name == "id_short":
                raise AASConstraintViolation(117, f"{element!r} has attribute {attr_name}=None, "
                                                  f"which is not allowed within a {self.parent.__class__.__name__}!")
            else:
                raise ValueError(f"{element!r} has attribute {attr_name}=None, which is not allowed!")

    def _check_value_is_not_in_backend(self, element: _NSO, attr_name: str, attr,
                                       backend_dict: Dict[ATTRIBUTE_TYPES, _NSO], set_: "NamespaceSet"):
        if attr in backend_dict:
            if set_ is self:
                text = f"Object with attribute (name='{attr_name}', value='{getattr(element, attr_name)}') " \
                       f"is already present in this set of objects"
            else:
                text = f"Object with attribute (name='{attr_name}', value='{getattr(element, attr_name)}') " \
                       f"is already present in another set in the same namespace"
            raise AASConstraintViolation(ATTRIBUTES_CONSTRAINT_IDS.get(attr_name, 0), text)

    def _execute_item_id_set_hook(self, element: _NSO):
        if self._item_id_set_hook is not None:
            self._item_id_set_hook(element)

    def _execute_item_add_hook(self, element: _NSO):
        if self._item_add_hook is not None:
            try:
                self._item_add_hook(element, self.__iter__())
            except Exception as e:
                self._execute_item_del_hook(element)
                raise

    def _execute_item_del_hook(self, element: _NSO):
        # parent needs to be unset first, otherwise generated id_shorts cannot be unset
        # see SubmodelElementList
        if hasattr(element, "parent"):
            element.parent = None
        if self._item_id_del_hook is not None:
            self._item_id_del_hook(element)

    def remove_by_id(self, attribute_name: str, identifier: ATTRIBUTE_TYPES) -> None:
        item = self.get_object_by_attribute(attribute_name, identifier)
        self.remove(item)

    def remove(self, item: _NSO) -> None:
        item_found = False
        for key_attr_name, (backend_dict, case_sensitive) in self._backend.items():
            key_attr_value = self._get_attribute(item, key_attr_name, case_sensitive)
            if backend_dict[key_attr_value] is item:
                # item has to be removed from backend before _item_del_hook() is called,
                # as the hook may unset the id_short, as in SubmodelElementLists
                del backend_dict[key_attr_value]
                item_found = True
        if not item_found:
            raise KeyError("Object not found in NamespaceDict")
        self._execute_item_del_hook(item)

    def discard(self, x: _NSO) -> None:
        if x not in self:
            return
        self.remove(x)

    def pop(self) -> _NSO:
        _, value = next(iter(self._backend.values()))[0].popitem()
        self._execute_item_del_hook(value)
        value.parent = None
        return value

    def clear(self) -> None:
        for attr_name, (backend, case_sensitive) in self._backend.items():
            for value in backend.values():
                self._execute_item_del_hook(value)
        for attr_name, (backend, case_sensitive) in self._backend.items():
            backend.clear()

    def get_object_by_attribute(self, attribute_name: str, attribute_value: ATTRIBUTE_TYPES) -> _NSO:
        """
        Find an object in this set by its unique attribute

        :raises KeyError: If no such object can be found
        """
        backend, case_sensitive = self._backend[attribute_name]
        return backend[attribute_value if case_sensitive else attribute_value.upper()]  # type: ignore

    def get(self, attribute_name: str, attribute_value: str, default: Optional[_NSO] = None) -> Optional[_NSO]:
        """
        Find an object in this set by its attribute, with fallback parameter

        :param attribute_name: name of the attribute to search for
        :param attribute_value: value of the attribute to search for
        :param default: An object to be returned, if no object with the given attribute is found
        :return: The AAS object with the given attribute in the set. Otherwise the ``default`` object or None, if
                 none is given.
        """
        backend, case_sensitive = self._backend[attribute_name]
        return backend.get(attribute_value if case_sensitive else attribute_value.upper(), default)

    # Todo: Implement function including tests
    def update_nss_from(self, other: "NamespaceSet"):
        """
        Update a NamespaceSet from a given NamespaceSet.

        WARNING: By updating, the "other" NamespaceSet gets destroyed.

        :param other: The NamespaceSet to update from
        """
        objects_to_add: List[_NSO] = []  # objects from the other nss to add to self
        objects_to_remove: List[_NSO] = []  # objects to remove from self
        for other_object in other:
            try:
                if isinstance(other_object, Referable):
                    backend, case_sensitive = self._backend["id_short"]
                    referable = backend[other_object.id_short if case_sensitive else other_object.id_short.upper()]
                    referable.update_from(other_object, update_source=True)  # type: ignore
                elif isinstance(other_object, Qualifier):
                    backend, case_sensitive = self._backend["type"]
                    qualifier = backend[other_object.type if case_sensitive else other_object.type.upper()]
                    # qualifier.update_from(other_object, update_source=True) # TODO: What should happend here?
                elif isinstance(other_object, Extension):
                    backend, case_sensitive = self._backend["name"]
                    extension = backend[other_object.name if case_sensitive else other_object.name.upper()]
                    # extension.update_from(other_object, update_source=True) # TODO: What should happend here?
                else:
                    raise TypeError("Type not implemented")
            except KeyError:
                # other object is not in NamespaceSet
                objects_to_add.append(other_object)
        for attr_name, (backend, case_sensitive) in self._backend.items():
            for attr_name_other, (backend_other, case_sensitive_other) in other._backend.items():
                if attr_name is attr_name_other:
                    for item in backend.values():
                        if not backend_other.get(self._get_attribute(item, attr_name, case_sensitive)):
                            # referable does not exist in the other NamespaceSet
                            objects_to_remove.append(item)
        for object_to_add in objects_to_add:
            other.remove(object_to_add)
            self.add(object_to_add)  # type: ignore
        for object_to_remove in objects_to_remove:
            self.remove(object_to_remove)  # type: ignore


class OrderedNamespaceSet(NamespaceSet[_NSO], MutableSequence[_NSO], Generic[_NSO]):
    """
    A specialized version of :class:`~.NamespaceSet`, that keeps track of the order of the stored
    :class:`~.Referable` objects.

    Additionally to the MutableSet interface of :class:`~.NamespaceSet`, this class provides a set-like interface
    (actually it is derived from MutableSequence). However, we don't permit duplicate entries in the ordered list of
    objects.
    """
    def __init__(self, parent: Union[UniqueIdShortNamespace, UniqueSemanticIdNamespace, Qualifiable, HasExtension],
                 attribute_names: List[Tuple[str, bool]], items: Iterable[_NSO] = (),
                 item_add_hook: Optional[Callable[[_NSO, Iterable[_NSO]], None]] = None,
                 item_id_set_hook: Optional[Callable[[_NSO], None]] = None,
                 item_id_del_hook: Optional[Callable[[_NSO], None]] = None) -> None:
        """
        Initialize a new OrderedNamespaceSet.

        This initializer automatically takes care of adding this set to the ``namespace_element_sets`` list of the
        Namespace.

        :param parent: The Namespace this set belongs to
        :attribute_names: Dict of attribute names, for which objects should be unique in the set. The bool flag
                          indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
        :param items: A given list of Referable items to be added to the set
        :param item_add_hook: A function that is called for each item that is added to this NamespaceSet, even when
                              it is initialized. The first parameter is the item that is added while the second is
                              an iterator over all currently contained items. Useful for constraint checking.
        :param item_id_set_hook: A function called to calculate the identifying attribute (e.g. id_short) of an object
                                 on-the-fly when it is added. Used for the SubmodelElementList implementation.
        :param item_id_del_hook: A function that is called for each item removed from this NamespaceSet. Used in
                                 SubmodelElementList to unset id_shorts on removal. Should not be used for
                                 constraint checking, as the hook is called after removal.
        :raises AASConstraintViolation: When ``items`` contains multiple objects with same unique attribute or when an
                                        item doesn't has an identifying attribute
        """
        self._order: List[_NSO] = []
        super().__init__(parent, attribute_names, items, item_add_hook, item_id_set_hook, item_id_del_hook)

    def __iter__(self) -> Iterator[_NSO]:
        return iter(self._order)

    def add(self, element: _NSO):
        super().add(element)
        self._order.append(element)

    def remove(self, item: Union[Tuple[str, ATTRIBUTE_TYPES], _NSO]):
        if isinstance(item, tuple):
            item = self.get_object_by_attribute(item[0], item[1])
        super().remove(item)
        self._order.remove(item)

    def pop(self, i: Optional[int] = None) -> _NSO:
        if i is None:
            value = super().pop()
            self._order.remove(value)
        else:
            value = self._order.pop(i)
            super().remove(value)
        return value

    def clear(self) -> None:
        super().clear()
        self._order.clear()

    def insert(self, index: int, object_: _NSO) -> None:
        super().add(object_)
        self._order.insert(index, object_)

    @overload
    def __getitem__(self, i: int) -> _NSO: ...

    @overload
    def __getitem__(self, s: slice) -> MutableSequence[_NSO]: ...

    def __getitem__(self, s: Union[int, slice]) -> Union[_NSO, MutableSequence[_NSO]]:
        return self._order[s]

    @overload
    def __setitem__(self, i: int, o: _NSO) -> None: ...

    @overload
    def __setitem__(self, s: slice, o: Iterable[_NSO]) -> None: ...

    def __setitem__(self, s, o) -> None:
        if isinstance(s, int):
            deleted_items = [self._order[s]]
            super().add(o)
            self._order[s] = o
        else:
            deleted_items = self._order[s]
            new_items = itertools.islice(o, len(deleted_items))
            successful_new_items = []
            try:
                for i in new_items:
                    super().add(i)
                    successful_new_items.append(i)
            except Exception:
                # Do a rollback, when an exception occurs while adding items
                for i in successful_new_items:
                    super().remove(i)
                raise
            self._order[s] = new_items
        for i in deleted_items:
            super().remove(i)

    @overload
    def __delitem__(self, i: int) -> None: ...

    @overload
    def __delitem__(self, i: slice) -> None: ...

    def __delitem__(self, i: Union[int, slice]) -> None:
        if isinstance(i, int):
            i = slice(i, i+1)
        for o in self._order[i]:
            super().remove(o)
        del self._order[i]
