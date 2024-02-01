# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
.. _adapter.xml.xml_serialization:

Module for serializing Asset Administration Shell data to the official XML format

How to use:

- For generating an XML-File from a :class:`~basyx.aas.model.provider.AbstractObjectStore`, check out the function
  :func:`write_aas_xml_file`.
- For serializing any object to an XML fragment, that fits the XML specification from 'Details of the
  Asset Administration Shell', chapter 5.4, check out ``<class_name>_to_xml()``. These functions return
  an :class:`~lxml.etree.Element` object to be serialized into XML.
"""

from lxml import etree  # type: ignore
from typing import IO

from basyx.aas import model
from . import xmlization


def write_aas_xml_file(file: IO,
                       data: model.AbstractObjectStore,
                       **kwargs) -> None:
    """
    Write a set of AAS objects to an Asset Administration Shell XML file according to 'Details of the Asset
    Administration Shell', chapter 5.4

    :param file: A file-like object to write the XML-serialized data to
    :param data: :class:`ObjectStore <basyx.aas.model.provider.AbstractObjectStore>` which contains different objects of
                 the AAS meta model which should be serialized to an XML file
    :param kwargs: Additional keyword arguments to be passed to :meth:`~lxml.etree.ElementTree.write`
    """

    file.write(xmlization.to_str(data.get_environment()))
