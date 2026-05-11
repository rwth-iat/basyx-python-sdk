# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

from aas_mapping.aas_neo4j_adapter.aas_neo4j_client import AASNeo4JClient, AAS_NEO4J_MODEL_CONFIG
from aas_mapping.aas_neo4j_adapter.neo_aas_object_store import Neo4jObjectStore


def build_neo4j_object_store(uri: str, user: str, password: str) -> Neo4jObjectStore:
    client = AASNeo4JClient(uri=uri, user=user, password=password, model_config=AAS_NEO4J_MODEL_CONFIG)
    return Neo4jObjectStore(client=client)
