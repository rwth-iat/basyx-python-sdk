# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.json.json_serialization:

Module for serializing Asset Administration Shell objects to the official JSON format

The module provides an custom JSONEncoder classes :class:`AASToJsonEncoder`
to be used with the Python standard :mod:`json` module. While the former serializes objects as defined in the
specification, the latter serializes stripped objects, excluding some attributes
(see https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91).
Each class contains a custom :meth:`~.AASToJsonEncoder.default` function which converts BaSyx Python SDK objects to
simple python types for an automatic JSON serialization.
To simplify the usage of this module, the :meth:`write_aas_json_file` and :meth:`object_store_to_json` are provided.
The former is used to serialize a given :class:`~basyx.aas.model.provider.AbstractObjectStore` to a file, while the
latter serializes the object store to a string and returns it.

The serialization is performed in an iterative approach: The :meth:`~.AASToJsonEncoder.default` function gets called for
every object and checks if an object is an BaSyx Python SDK object. In this case, it calls a special function for the
respective BaSyx Python SDK class which converts the object (but not the contained objects) into a simple Python dict,
which is serializable. Any contained  BaSyx Python SDK objects are included into the dict as they are to be converted
later on. The special helper function ``_abstract_classes_to_json`` is called by most of the
conversion functions to handle all the attributes of abstract base classes.
"""
from typing import IO, Optional, Type
import json

from basyx.aas import model
from . import jsonization

def object_store_to_json(data: model.AbstractObjectStore, stripped: bool = False,
                         encoder: Optional = None, **kwargs) -> str:
    """
    Create a json serialization of a set of AAS objects according to 'Details of the Asset Administration Shell',
    chapter 5.5

    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS meta model which should be serialized to a JSON file
    :param stripped: If true, objects are serialized to stripped json objects.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if an encoder class is specified.
    :param encoder: The encoder class used to encode the JSON objects
    :param kwargs: Additional keyword arguments to be passed to :func:`json.dumps`
    """
    environment = data.get_environment()
    # Serialize to a JSON-able mapping
    jsonable = jsonization.to_jsonable(environment)

    # serialize object to json
    return json.dumps(jsonable, **kwargs)


def write_aas_json_file(file: IO, data: model.AbstractObjectStore, stripped: bool = False,
                        encoder: Optional = None, **kwargs) -> None:
    """
    Write a set of AAS objects to an Asset Administration Shell JSON file according to 'Details of the Asset
    Administration Shell', chapter 5.5

    :param file: A file-like object to write the JSON-serialized data to
    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS meta model which should be serialized to a JSON file
    :param stripped: If `True`, objects are serialized to stripped json objects.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if an encoder class is specified.
    :param encoder: The encoder class used to encode the JSON objects
    :param kwargs: Additional keyword arguments to be passed to `json.dump()`
    """
    environment = data.get_environment()
    # Serialize to a JSON-able mapping
    jsonable = jsonization.to_jsonable(environment)

    json.dump(jsonable, file, **kwargs)

