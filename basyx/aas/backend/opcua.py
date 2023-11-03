# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module contains the OPC UA backend implementation.
"""
import threading
import weakref
import urllib.parse
import logging
import json

import urllib3  # type: ignore

from ..adapter.json import json_serialization, json_deserialization
from basyx.aas import model
from ..model import OpcUaEndPointDefinition
from typing import Type

from typing import List, Dict, Any, Optional, Iterator, Iterable, Union, Tuple
from abc import ABC
from . import backends
from opcua import Client

class OpcUaBackend(backends.Backend):
    # @classmethod
    # def __init__(self, endpoint.client, endpoint.node_id):
    #     self.client = Client(endpoint.client)
    #     self.client.connect()
    #     self.node = self.client.get_node(endpoint.node_id)
    @classmethod
    def update_object(cls,
                      updated_object: "Referable",
                      store_object: "Referable",
                      relative_path: List[str],
                      specific_attribute: str = None,
                      endpoint: Type[OpcUaEndPointDefinition] = None) -> None:

        if endpoint is not None:
            try:
                requested_object = endpoint.node.get_value()
            except Exception as e:
                print("Error update from OPC UA server:", e)
                return None

        if specific_attribute is None:
            # TODO: Update Submodel or AAS from OPC UA server
            print("Current backend can only update specific attribute")
        else:
            # Update only the specific attribute with requested data
            for name, var in vars(updated_object).items():
                if name.replace('_', '').lower() == specific_attribute.replace('_', '').lower():
                    vars(updated_object)[name] = requested_object

backends.register_backend(OpcUaEndPointDefinition, OpcUaBackend)