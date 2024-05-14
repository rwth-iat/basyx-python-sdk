# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.json.json_deserialization:

This module facilitates deserialization of Asset Administration Shell (AAS) data from its official JSON representation.

Key Functions:
- `read_aas_json_file_into`: This function directly reads an AAS JSON file, and then populates an existing object store
with the deserialized objects.
- `read_aas_json_file`: Serving as a more straightforward approach, this function reads an AAS JSON file and returns
a new `DictObjectStore` containing the deserialized AAS objects.
"""


import logging
from typing import IO, Set

from basyx.aas import model
from . import jsonization

logger = logging.getLogger(__name__)


def read_aas_json_file_into(object_store: model.AbstractObjectStore, file: IO) -> Set[str]:
    """
    Read an Asset Administration Shell JSON file into a given object store.

    :param object_store: The :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` in which the
                         identifiable objects should be stored
    :param file: A file-like object to read the JSON-serialized data from
    :return: A set of identifiers that were added to object_store
    """
    environment = jsonization.environment_from_jsonable(file.read())
    identifiables = environment.asset_administration_shells + environment.submodels + environment.concept_descriptions
    object_store.update(identifiables)

    ret: Set[str] = set()
    ret.update([i.id for i in identifiables])

    return ret


def read_aas_json_file(file: IO) -> model.DictObjectStore[model.Identifiable]:
    """
    A wrapper of :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into`, that reads all objects
    in an empty :class:`~basyx.aas.model.provider.DictObjectStore`. This function supports the same keyword arguments as
    :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into`.

    :param file: A filename or file-like object to read the JSON-serialized data from
    :return: A :class:`~basyx.aas.model.provider.DictObjectStore` containing all AAS objects from the JSON file
    """
    object_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    read_aas_json_file_into(object_store, file)
    return object_store
