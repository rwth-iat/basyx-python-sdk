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
    def __init__(self,
                 endpointAddress: str = "",
                 endpointProtocol: Optional[str] = None,
                 endpointProtocolVersion: Optional[str] = None,
                 securityAttributes: Optional[str] = None,
                 subProtocol: Optional[str] = None,
                 subProtocolBody: Optional[str] = None,
                 subProtocolBodyEncoding: Optional[str] = None):
        self.endpointAddress: str = endpointAddress
        self.endpointProtocol: Optional[str] = endpointProtocol
        self.endpointProtocolVersion: Optional[str] = endpointProtocolVersion
        self.securityAttributes: Optional[str] = securityAttributes
        self.subProtocol: Optional[str] = subProtocol
        self.subProtocolBody: Optional[str] = subProtocolBody
        self.subProtocolBodyEncoding: Optional[str] = subProtocolBodyEncoding

    def __repr__(self) -> str:
        return "{}[{}]{}{}{}{}{}{}".format(
            self.__class__.__name__, self.endpointAddress, self.endpointProtocol, self.endpointProtocolVersion,
            self.securityAttributes, self.subProtocol, self.subProtocolBody, self.subProtocolBodyEncoding)
