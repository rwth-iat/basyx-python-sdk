# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.json.json_serialization:

This module provides the following functions for serializing Asset Administration Shell objects
to the official JSON format:

- :func:`write_aas_json_file` serializes a given :class:`~basyx.aas.model.provider.AbstractObjectStore`
- :func:`object_store_to_json` serializes the object store to a string and returns it.

"""
from typing import IO, Optional, Type
import json

from basyx.aas import model
from . import jsonization

def object_store_to_json(data: model.AbstractObjectStore, **kwargs) -> str:
    """
    Create a json serialization of a set of AAS objects

    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS meta model which should be serialized to a JSON file
    :param kwargs: Additional keyword arguments to be passed to :func:`json.dumps`
    """
    environment = data.get_environment()
    # Serialize to a JSON-able mapping
    jsonable = jsonization.to_jsonable(environment)

    # serialize object to json
    return json.dumps(jsonable, **kwargs)


def write_aas_json_file(file: IO, data: model.AbstractObjectStore, **kwargs) -> None:
    """
    Write a set of AAS objects to an Asset Administration Shell JSON file

    :param file: A file-like object to write the JSON-serialized data to
    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS meta model which should be serialized to a JSON file
    :param kwargs: Additional keyword arguments to be passed to `json.dump()`
    """
    environment = data.get_environment()
    # Serialize to a JSON-able mapping
    jsonable = jsonization.to_jsonable(environment)

    json.dump(jsonable, file, **kwargs)

