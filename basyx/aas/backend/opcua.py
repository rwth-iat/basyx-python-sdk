# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module contains the OPC UA backend implementation.
"""

import urllib3  # type: ignore

from basyx.aas import model
from ..model import OpcUaEndPointDefinition
from typing import Type

from typing import List, Dict, Any, Optional, Iterator, Iterable, Union, Tuple
from . import backends
from opcua import Client

class OpcUaBackend(backends.Backend):
    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      specific_attribute: str = None,
                      endpoint: Type[OpcUaEndPointDefinition] = None) -> None:

        if endpoint is not None:
            client = Client(endpoint.endpointAddress)
            client.connect()
            node_id = f"ns={endpoint.namespaceIndex};i={endpoint.identifier}"
            node = client.get_node(node_id)
            try:
                requested_object = node.get_value()
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

    @classmethod
    def commit_object(cls,
                      committed_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      specific_attribute: str = None,
                      endpoint: Type[OpcUaEndPointDefinition] = None) -> None:

        if endpoint is not None:
            client = Client(endpoint.endpointAddress)
            client.connect()
            node_id = f"ns={endpoint.namespaceIndex};i={endpoint.identifier}"
            node = client.get_node(node_id)

            if specific_attribute is None:
                # TODO: Update Submodel or AAS from OPC UA server
                print("Current backend can only commit specific attribute")
            else:
                # Update only the specific attribute with requested data
                for name, var in vars(committed_object).items():
                    if name.replace('_', '').lower() == specific_attribute.replace('_', '').lower():
                        data = vars(committed_object)[name]
                        node.set_value(data)

backends.register_backend(OpcUaEndPointDefinition, OpcUaBackend)