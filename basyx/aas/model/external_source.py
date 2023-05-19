# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module includes the abstract classes needed for the higher level classes to inherit from which are part
of the implementation of the basic structures of the AAS metamodel.

"""

import abc
from typing import Optional


class EndPointDefinition(metaclass=abc.ABCMeta):
    """
    Defines minimal attributes and functions which each specific endpoint definition requires.

    <<abstract>>

    :ivar endpointAddress: Is an address associated with endpoint, which is used to locate and identify the endpoint.
    :ivar endpointProtocol: Specifies a protocol that is used to make a connection with the endpoint.
    :ivar endpointProtocolVersion: Version of the endpoint protocol.
    :ivar securityAttributes: Security features associated with the endpoint security.
    :ivar subProtocol: Secondary protocol associated with the endpoint.
    :ivar subProtocolBody: The body for sub protocol.
    :ivar subProtocolBodyEncoding: Body Encoding associated with sub protocol.

    """

    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        self.endpointAddress: str = ""
        self.endpointProtocol: Optional[str] = None
        self.endpointProtocolVersion: Optional[str] = None
        self.securityAttributes: Optional[str] = None
        self.subProtocol: Optional[str] = None
        self.subProtocolBody: Optional[str] = None
        self.subProtocolBodyEncoding: Optional[str] = None

    def __repr__(self) -> str:
        return "{}[{}]{}{}{}{}{}{}".format(
            self.__class__.__name__, self.endpointAddress, self.endpointProtocol, self.endpointProtocolVersion,
            self.securityAttributes, self.subProtocol, self.subProtocolBody, self.subProtocolBodyEncoding)
