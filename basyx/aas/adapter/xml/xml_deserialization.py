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

These functions take a decoder class as keyword argument, which allows parsing in failsafe (default) or non-failsafe
mode. Parsing stripped elements - used in the HTTP adapter - is also possible. It is also possible to subclass the
default decoder class and provide an own decoder.

In failsafe mode errors regarding missing attributes and elements or invalid values are caught and logged.
In non-failsafe mode any error would abort parsing.
Error handling is done only by ``_failsafe_construct()`` in this module. Nearly all constructor functions are called
by other constructor functions via ``_failsafe_construct()``, so an error chain is constructed in the error case,
which allows printing stacktrace-like error messages like the following in the error case (in failsafe mode of course):


.. code-block::

    KeyError: aas:id on line 252 has no attribute with name idType!
        -> Failed to construct aas:id on line 252 using construct_identifier!
        -> Failed to construct aas:conceptDescription on line 247 using construct_concept_description!


Unlike the JSON deserialization, parsing is done top-down. Elements with a specific tag are searched on the level
directly below the level of the current xml element (in terms of parent and child relation) and parsed when
found. Constructor functions of these elements will then again search for mandatory and optional child elements
and construct them if available, and so on.
"""
from . import xmlization
from ... import model
from lxml import etree  # type: ignore
import logging

from typing import Any, IO, Optional, Set

logger = logging.getLogger(__name__)

def read_aas_xml_file_into(object_store: model.AbstractObjectStore[model.Identifiable], file: IO,
                           replace_existing: bool = False, ignore_existing: bool = False, failsafe: bool = True,
                           stripped: bool = False, decoder: Optional = None,
                           **parser_kwargs: Any) -> Set[model.Identifier]:
    """
    Read an Asset Administration Shell XML file according to 'Details of the Asset Administration Shell', chapter 5.4
    into a given :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>`.

    :param object_store: The :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` in which the
                         :class:`~basyx.aas.model.base.Identifiable` objects should be stored
    :param file: A filename or file-like object to read the XML-serialized data from
    :param replace_existing: Whether to replace existing objects with the same identifier in the object store or not
    :param ignore_existing: Whether to ignore existing objects (e.g. log a message) or raise an error.
                            This parameter is ignored if replace_existing is True.
    :param failsafe: If ``True``, the document is parsed in a failsafe way: missing attributes and elements are logged
                     instead of causing exceptions. Defect objects are skipped.
                     This parameter is ignored if a decoder class is specified.
    :param stripped: If ``True``, stripped XML elements are parsed.
                     See https://git.rwth-aachen.de/acplt/pyi40aas/-/issues/91
                     This parameter is ignored if a decoder class is specified.
    :param decoder: The decoder class used to decode the XML elements
    :param parser_kwargs: Keyword arguments passed to the XMLParser constructor
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


def read_aas_xml_file(file: IO, **kwargs: Any) -> model.DictObjectStore[model.Identifiable]:
    """
    A wrapper of :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`, that reads all objects in an
    empty :class:`~basyx.aas.model.provider.DictObjectStore`. This function supports
    the same keyword arguments as :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`.

    :param file: A filename or file-like object to read the XML-serialized data from
    :param kwargs: Keyword arguments passed to :meth:`~basyx.aas.adapter.xml.xml_deserialization.read_aas_xml_file_into`
    :return: A :class:`~basyx.aas.model.provider.DictObjectStore` containing all AAS objects from the XML file
    """
    object_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
    read_aas_xml_file_into(object_store, file, **kwargs)
    return object_store
