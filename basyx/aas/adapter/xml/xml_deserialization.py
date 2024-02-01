# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.xml.xml_deserialization:

Module for deserializing Asset Administration Shell data from the official XML format

This module provides the following functions for parsing XML documents:

- :func:`read_aas_xml_element` constructs a single object from an XML document containing a single element
- :func:`read_aas_xml_file_into` constructs all elements of an XML document and stores them in a given
  :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>`
- :func:`read_aas_xml_file` constructs all elements of an XML document and returns them in a
  :class:`~basyx.aas.model.provider.DictObjectStore`
"""
from . import xmlization
from ... import model
import logging

from typing import IO, Set

logger = logging.getLogger(__name__)


def read_aas_xml_file_into(object_store: model.AbstractObjectStore[model.Identifiable],
                           file: IO) -> Set[model.Identifier]:
    """
    Read an Asset Administration Shell XML file according to 'Details of the Asset Administration Shell', chapter 5.4
    into a given :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>`.

    :param object_store: The :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` in which the
                         :class:`~basyx.aas.model.base.Identifiable` objects should be stored
    :param file: A filename or file-like object to read the XML-serialized data from
    :return: A set of :class:`Identifiers <basyx.aas.model.base.Identifier>` that were added to object_store
    """
    environment = xmlization.environment_from_str(file.read())
    identifiables = environment.asset_administration_shells + environment.submodels + environment.concept_descriptions
    object_store.update(identifiables)

    ret: Set[model.Identifier] = set()
    ret.update([i.id for i in identifiables])

    return ret


def read_aas_xml_file_into(object_store: model.AbstractObjectStore[model.Identifiable], file: IO):
    environment = xmlization.environment_from_str(file.read())
    identifiables = environment.asset_administration_shells + environment.submodels + environment.concept_descriptions
    object_store.update(identifiables)

    ret: Set[model.Identifier] = set()
    ret.update([i.id for i in identifiables])

    return ret


def read_aas_xml_file(file: IO) -> model.DictObjectStore[model.Identifiable]:
    """
    A wrapper of :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`, that reads all objects in an
    empty :class:`~basyx.aas.model.provider.DictObjectStore`. This function supports
    the same keyword arguments as :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`.

    :param file: A filename or file-like object to read the XML-serialized data from
    :return: A :class:`~basyx.aas.model.provider.DictObjectStore` containing all AAS objects from the XML file
    """
    object_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    read_aas_xml_file_into(object_store, file)
    return object_store
