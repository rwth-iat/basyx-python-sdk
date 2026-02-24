"""
Persistent Storage for BaSyx Registry API
Supports AssetAdministrationShellDescriptors and SubmodelDescriptors
"""
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set
from abc import ABC, abstractmethod
import logging

from basyx.aas import model
import server.app.model as server_model

logger = logging.getLogger(__name__)


class RegistryStorageInterface(ABC):
    """Abstract interface for registry storage implementations"""

    @abstractmethod
    def save_aas_descriptor(self, descriptor: server_model.AssetAdministrationShellDescriptor) -> None:
        """Save or update an AAS descriptor"""
        pass

    @abstractmethod
    def get_aas_descriptor(self, aas_id: str) -> Optional[server_model.AssetAdministrationShellDescriptor]:
        """Retrieve an AAS descriptor by ID"""
        pass

    @abstractmethod
    def delete_aas_descriptor(self, aas_id: str) -> bool:
        """Delete an AAS descriptor. Returns True if deleted, False if not found"""
        pass

    @abstractmethod
    def list_aas_descriptors(self) -> List[server_model.AssetAdministrationShellDescriptor]:
        """List all AAS descriptors"""
        pass

    @abstractmethod
    def save_submodel_descriptor(self, descriptor: server_model.SubmodelDescriptor) -> None:
        """Save or update a Submodel descriptor"""
        pass

    @abstractmethod
    def get_submodel_descriptor(self, submodel_id: str) -> Optional[server_model.SubmodelDescriptor]:
        """Retrieve a Submodel descriptor by ID"""
        pass

    @abstractmethod
    def delete_submodel_descriptor(self, submodel_id: str) -> bool:
        """Delete a Submodel descriptor. Returns True if deleted, False if not found"""
        pass

    @abstractmethod
    def list_submodel_descriptors(self) -> List[server_model.SubmodelDescriptor]:
        """List all Submodel descriptors"""
        pass


class JsonFileStorage(RegistryStorageInterface):
    """
    File-based persistent storage using JSON.
    Thread-safe with automatic saving.
    """

    def __init__(self, storage_path: str = "registry_storage.json"):
        self.storage_path = Path(storage_path)
        self.lock = threading.RLock()
        self.data = {
            "aas_descriptors": {},
            "submodel_descriptors": {}
        }
        self._load()

    def _load(self) -> None:
        """Load data from file"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.data = loaded_data
                    logger.info(f"Loaded registry data from {self.storage_path}")
            except Exception as e:
                logger.error(f"Failed to load registry data: {e}")
                # Keep empty data structure on error

    def _save(self) -> None:
        """Save data to file"""
        try:
            # Write to temporary file first, then rename (atomic operation)
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.storage_path)
            logger.debug(f"Saved registry data to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save registry data: {e}")

    def save_aas_descriptor(self, descriptor: server_model.AssetAdministrationShellDescriptor) -> None:
        with self.lock:
            # Convert descriptor to dict for JSON serialization
            descriptor_dict = self._serialize_descriptor(descriptor)
            aas_id = self._get_identifier(descriptor)
            self.data["aas_descriptors"][aas_id] = descriptor_dict
            self._save()

    def get_aas_descriptor(self, aas_id: str) -> Optional[server_model.AssetAdministrationShellDescriptor]:
        with self.lock:
            descriptor_dict = self.data["aas_descriptors"].get(aas_id)
            if descriptor_dict:
                return self._deserialize_descriptor(descriptor_dict, server_model.AssetAdministrationShellDescriptor)
            return None

    def delete_aas_descriptor(self, aas_id: str) -> bool:
        with self.lock:
            if aas_id in self.data["aas_descriptors"]:
                del self.data["aas_descriptors"][aas_id]
                self._save()
                return True
            return False

    def list_aas_descriptors(self) -> List[server_model.AssetAdministrationShellDescriptor]:
        with self.lock:
            return [
                self._deserialize_descriptor(desc_dict, server_model.AssetAdministrationShellDescriptor)
                for desc_dict in self.data["aas_descriptors"].values()
            ]

    def save_submodel_descriptor(self, descriptor: server_model.SubmodelDescriptor) -> None:
        with self.lock:
            descriptor_dict = self._serialize_descriptor(descriptor)
            submodel_id = self._get_identifier(descriptor)
            self.data["submodel_descriptors"][submodel_id] = descriptor_dict
            self._save()

    def get_submodel_descriptor(self, submodel_id: str) -> Optional[server_model.SubmodelDescriptor]:
        with self.lock:
            descriptor_dict = self.data["submodel_descriptors"].get(submodel_id)
            if descriptor_dict:
                return self._deserialize_descriptor(descriptor_dict, server_model.SubmodelDescriptor)
            return None

    def delete_submodel_descriptor(self, submodel_id: str) -> bool:
        with self.lock:
            if submodel_id in self.data["submodel_descriptors"]:
                del self.data["submodel_descriptors"][submodel_id]
                self._save()
                return True
            return False

    def list_submodel_descriptors(self) -> List[server_model.SubmodelDescriptor]:
        with self.lock:
            return [
                self._deserialize_descriptor(desc_dict, server_model.SubmodelDescriptor)
                for desc_dict in self.data["submodel_descriptors"].values()
            ]

    def _serialize_descriptor(self, descriptor) -> dict:
        """Convert descriptor object to JSON-serializable dict"""
        # Use your ServerAASToJsonEncoder here
        from server.app.adapter.jsonization import ServerAASToJsonEncoder
        return json.loads(json.dumps(descriptor, cls=ServerAASToJsonEncoder))

    def _deserialize_descriptor(self, descriptor_dict: dict, descriptor_class):
        """Convert dict back to descriptor object"""
        # Use your JSON deserialization logic here
        from server.app.adapter.jsonization import AASFromJsonDecoder
        # You'll need to adapt this based on your actual deserialization approach
        return descriptor_class(**descriptor_dict)

    def _get_identifier(self, descriptor) -> str:
        """Extract identifier from descriptor"""
        if hasattr(descriptor, 'id'):
            return str(descriptor.id)
        elif hasattr(descriptor, 'identification'):
            return str(descriptor.identification.id)
        else:
            raise ValueError(f"Cannot extract identifier from descriptor: {descriptor}")


class InMemoryStorage(RegistryStorageInterface):
    """
    In-memory storage (no persistence).
    Useful for testing and development.
    """

    def __init__(self):
        self.aas_descriptors: Dict[str, server_model.AssetAdministrationShellDescriptor] = {}
        self.submodel_descriptors: Dict[str, server_model.SubmodelDescriptor] = {}
        self.lock = threading.RLock()

    def save_aas_descriptor(self, descriptor: server_model.AssetAdministrationShellDescriptor) -> None:
        with self.lock:
            aas_id = self._get_identifier(descriptor)
            self.aas_descriptors[aas_id] = descriptor

    def get_aas_descriptor(self, aas_id: str) -> Optional[server_model.AssetAdministrationShellDescriptor]:
        with self.lock:
            return self.aas_descriptors.get(aas_id)

    def delete_aas_descriptor(self, aas_id: str) -> bool:
        with self.lock:
            if aas_id in self.aas_descriptors:
                del self.aas_descriptors[aas_id]
                return True
            return False

    def list_aas_descriptors(self) -> List[server_model.AssetAdministrationShellDescriptor]:
        with self.lock:
            return list(self.aas_descriptors.values())

    def save_submodel_descriptor(self, descriptor: server_model.SubmodelDescriptor) -> None:
        with self.lock:
            submodel_id = self._get_identifier(descriptor)
            self.submodel_descriptors[submodel_id] = descriptor

    def get_submodel_descriptor(self, submodel_id: str) -> Optional[server_model.SubmodelDescriptor]:
        with self.lock:
            return self.submodel_descriptors.get(submodel_id)

    def delete_submodel_descriptor(self, submodel_id: str) -> bool:
        with self.lock:
            if submodel_id in self.submodel_descriptors:
                del self.submodel_descriptors[submodel_id]
                return True
            return False

    def list_submodel_descriptors(self) -> List[server_model.SubmodelDescriptor]:
        with self.lock:
            return list(self.submodel_descriptors.values())

    def _get_identifier(self, descriptor) -> str:
        """Extract identifier from descriptor"""
        if hasattr(descriptor, 'id'):
            return str(descriptor.id)
        elif hasattr(descriptor, 'identification'):
            return str(descriptor.identification.id)
        else:
            raise ValueError(f"Cannot extract identifier from descriptor: {descriptor}")
