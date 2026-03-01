import os
from typing import MutableSet, Type, Iterator, Iterable, Dict, Optional, Any

from basyx.aas import model
import json




class DescriptorStore(MutableSet[object]):
    """A simple in‑memory store for descriptor objects.

    The store uses a dictionary keyed by the descriptor's ``id`` attribute.
    It enforces that at most one descriptor with a given identifier is
    present.  Membership checks can be performed either by descriptor
    instance or by identifier string.  Objects added to this store must
    expose an ``id`` attribute.
    """

    def __init__(self, objects: Iterable[object] = ()) -> None:
        self._backend: Dict[str, object] = {}
        for obj in objects:
            self.add(obj)

    def add(self, obj: object) -> None:
        """Add a descriptor to the store.

        :param obj: The descriptor object to add.  The object must have
            an ``id`` attribute.  If another descriptor with the same
            identifier already exists, a :class:`KeyError` is raised.
        """
        if not hasattr(obj, "id"):
            raise TypeError("Objects stored in DescriptorStore must have an 'id' attribute")
        identifier: model.Identifier = getattr(obj, "id")
        if identifier in self._backend and self._backend[identifier] is not obj:
            raise KeyError(f"Descriptor object with same id {identifier!r} is already stored")
        self._backend[identifier] = obj

    def discard(self, obj: object) -> None:
        """Remove a descriptor from the store if present.

        :param obj: The descriptor object to remove.  If the object is not
            present in the store, this method does nothing.
        """
        if not hasattr(obj, "id"):
            return
        identifier: model.Identifier = getattr(obj, "id")  # type: ignore[assignment]
        if self._backend.get(identifier) is obj:
            del self._backend[identifier]

    def __contains__(self, obj: object) -> bool:  # type: ignore[override]
        """Check whether a descriptor or identifier is contained in the store.

        :param obj: Either a descriptor instance or an identifier string.
        :return: ``True`` if the object or identifier is present in the store.
        """
        # Allow lookup by id string directly
        if isinstance(obj, str):
            return obj in self._backend
        # Otherwise, ensure it's a descriptor and compare by identity
        if not hasattr(obj, "id"):
            return False
        identifier: model.Identifier = getattr(obj, "id")  # type: ignore[assignment]
        return self._backend.get(identifier) is obj

    def __len__(self) -> int:  # type: ignore[override]
        return len(self._backend)

    def __iter__(self) -> Iterator[object]:  # type: ignore[override]
        return iter(self._backend.values())

    # Additional helper methods
    def get_descriptor(self, identifier: model.Identifier) -> object:
        """Retrieve a descriptor by its identifier.

        :param identifier: The descriptor's identifier.
        :return: The descriptor instance stored under the given identifier.
        :raises KeyError: If no descriptor with the given identifier exists.
        """
        return self._backend[identifier]

    def get(self, identifier: model.Identifier, default: Optional[object] = None) -> Optional[object]:
        """Retrieve a descriptor by its identifier, returning a default if not found.

        :param identifier: The descriptor's identifier.
        :param default: The value to return if the identifier is not present.
        :return: The descriptor instance or ``default``.
        """
        return self._backend.get(identifier, default)


class PersistentDescriptorStore(DescriptorStore):
    """A descriptor store that persists its contents to a JSON file.

    The store writes out the entire collection of descriptors whenever
    it is modified.  At initialization time it attempts to read
    existing descriptor data from the given file.  The file on disk
    will be created automatically if it does not exist.
    """

    def __init__(self, file_path: str, objects: Iterable[object] = ()) -> None:
        #: Path to the backing JSON file.
        self._file_path = file_path
        # If a file exists, prepopulate the backend from it; otherwise start
        # with an empty store.  We intentionally bypass the DescriptorStore
        # constructor here because we want to load from disk before adding
        # any objects passed in via the ``objects`` iterable.
        if os.path.isfile(self._file_path):
            self._backend = self._load_from_file()
        else:
            self._backend = {}
        # Add initial objects, if any; they will overwrite duplicates.
        for obj in objects:
            self.add(obj)
        # Ensure the file exists and reflects the current state.
        self._save_to_file()

    # -- Serialization helpers ------------------------------------------------

    def _descriptor_to_dict(self, obj: object) -> Dict[str, Any]:
        """Serialize a descriptor object into a JSON‑friendly dictionary.

        The default implementation uses ``vars(obj)`` (i.e., the object's
        ``__dict__``) and filters out callables and private attributes.
        Override this method if your descriptor classes require custom
        serialization.
        """
        return {k: v for k, v in vars(obj).items() if not callable(v) and not k.startswith("_")}

    def _dict_to_descriptor(self, data: Dict[str, Any]) -> object:
        """Deserialize a JSON dictionary back into a descriptor object.

        This method instantiates either an
        ``AssetAdministrationShellDescriptor`` or a ``SubmodelDescriptor``
        based on the presence of characteristic fields.  It passes
        all attributes except ``id`` to the descriptor constructor.
        Override this method if your descriptor types or construction
        signatures differ.
        """
        # Lazy import to avoid heavy dependencies at module load time
        from app.model.descriptor import (
            AssetAdministrationShellDescriptor,
            SubmodelDescriptor,
        )
        kwargs = {k: v for k, v in data.items() if k != "id"}
        if "endpoints" in data and "asset_kind" in data:
            return AssetAdministrationShellDescriptor(id_=data["id"], **kwargs)
        else:
            return SubmodelDescriptor(id_=data["id"], **kwargs)

    def _load_from_file(self) -> Dict[str, object]:
        """Read descriptor data from the backing JSON file."""
        with open(self._file_path, "r", encoding="utf-8") as f:
            raw_data: Dict[str, Dict[str, Any]] = json.load(f)
        return {identifier: self._dict_to_descriptor(d) for identifier, d in raw_data.items()}

    def _save_to_file(self) -> None:
        """Write the current collection of descriptors to the backing file."""
        raw_data: Dict[str, Dict[str, Any]] = {
            identifier: self._descriptor_to_dict(obj) for identifier, obj in self._backend.items()
        }
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2)

    # -- Overrides of DescriptorStore methods ---------------------------------

    def add(self, obj: object) -> None:
        """Add a descriptor and persist the updated store."""
        super().add(obj)
        self._save_to_file()

    def discard(self, obj: object) -> None:
        """Remove a descriptor, if present, and persist the updated store."""
        super().discard(obj)
        self._save_to_file()
