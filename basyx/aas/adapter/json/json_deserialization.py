# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.json.json_deserialization:

Module for deserializing Asset Administration Shell data from the official JSON format

The module provides custom JSONDecoder classes :class:`~.AASFromJsonDecoder` and :class:`~.StrictAASFromJsonDecoder` to
be used with the Python standard :mod:`json` module.

Furthermore it provides two classes :class:`~basyx.aas.adapter.json.json_deserialization.StrippedAASFromJsonDecoder` and
:class:`~basyx.aas.adapter.json.json_deserialization.StrictStrippedAASFromJsonDecoder` for parsing stripped
JSON objects, which are used in the http adapter (see https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91).
The classes contain a custom :meth:`~basyx.aas.adapter.json.json_deserialization.AASFromJsonDecoder.object_hook`
function to detect encoded AAS objects within the JSON data and convert them to BaSyx Python SDK objects while parsing.
Additionally, there's the :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into` function, that
takes a complete AAS JSON file, reads its contents and stores the objects in the provided
:class:`~basyx.aas.model.provider.AbstractObjectStore`. :meth:`read_aas_json_file` is a wrapper for this function.
Instead of storing the objects in a given :class:`~basyx.aas.model.provider.AbstractObjectStore`,
it returns a :class:`~basyx.aas.model.provider.DictObjectStore` containing parsed objects.

The deserialization is performed in a bottom-up approach: The ``object_hook()`` method gets called for every parsed JSON
object (as dict) and checks for existence of the ``modelType`` attribute. If it is present, the ``AAS_CLASS_PARSERS``
dict defines, which of the constructor methods of the class is to be used for converting the dict into an object.
Embedded objects that should have a ``modelType`` themselves are expected to be converted already.
Other embedded objects are converted using a number of helper constructor methods.
"""
import logging
from typing import IO, Optional, Set

from basyx.aas import model
from . import jsonization

logger = logging.getLogger(__name__)


def read_aas_json_file_into(object_store: model.AbstractObjectStore, file: IO, replace_existing: bool = False,
                            ignore_existing: bool = False, failsafe: bool = False, stripped: bool = False,
                            decoder: Optional = None) -> Set[model.Identifier]:
    """
    Read an Asset Administration Shell JSON file according to 'Details of the Asset Administration Shell', chapter 5.5
    into a given object store.

    :param object_store: The :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` in which the
                         identifiable objects should be stored
    :param file: A file-like object to read the JSON-serialized data from
    :param replace_existing: Whether to replace existing objects with the same identifier in the object store or not
    :param ignore_existing: Whether to ignore existing objects (e.g. log a message) or raise an error.
                            This parameter is ignored if replace_existing is ``True``.
    :param failsafe: If ``True``, the document is parsed in a failsafe way: Missing attributes and elements are logged
                     instead of causing exceptions. Defect objects are skipped.
                     This parameter is ignored if a decoder class is specified.
    :param stripped: If ``True``, stripped JSON objects are parsed.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if a decoder class is specified.
    :param decoder: The decoder class used to decode the JSON objects
    :return: A set of :class:`Identifiers <basyx.aas.model.base.Identifier>` that were added to object_store
    """
    environment = jsonization.environment_from_jsonable(file.read())
    identifiables = environment.asset_administration_shells + environment.submodels + environment.concept_descriptions
    object_store.update(identifiables)

    ret: Set[model.Identifier] = set()
    ret.update([i.id for i in identifiables])

    return ret


def read_aas_json_file(file: IO, **kwargs) -> model.DictObjectStore[model.Identifiable]:
    """
    A wrapper of :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into`, that reads all objects
    in an empty :class:`~basyx.aas.model.provider.DictObjectStore`. This function supports the same keyword arguments as
    :meth:`~basyx.aas.adapter.json.json_deserialization.read_aas_json_file_into`.

    :param file: A filename or file-like object to read the JSON-serialized data from
    :param kwargs: Keyword arguments passed to :meth:`read_aas_json_file_into`
    :return: A :class:`~basyx.aas.model.provider.DictObjectStore` containing all AAS objects from the JSON file
    """
    object_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    read_aas_json_file_into(object_store, file, **kwargs)
    return object_store
