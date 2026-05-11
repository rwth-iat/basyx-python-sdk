# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module provides the WSGI entry point for the Asset Administration Shell Repository Server.
"""

import logging
import os
from typing import Tuple, Union

from basyx.aas.adapter import load_directory
from basyx.aas.adapter.aasx import DictSupplementaryFileContainer
from basyx.aas.backend.local_file import LocalFileIdentifiableStore
from basyx.aas.model import AbstractObjectStore
from basyx.aas.model.provider import DictIdentifiableStore

from app.interfaces.repository import WSGIApp

# -------- Helper methods --------


def setup_logger() -> logging.Logger:
    """
    Configure a custom :class:`~logging.Logger` for the start-up sequence of the server.

    :return: Configured :class:`~logging.Logger`
    """

    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(levelname)s [Server Start-up] %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def build_storage(
    env_input: str, env_storage: str, env_storage_persistency: bool, env_storage_overwrite: bool, logger: logging.Logger
) -> Tuple[AbstractObjectStore, DictSupplementaryFileContainer]:
    """
    Configure the server's storage according to the given start-up settings.

    :param env_input: ``str`` pointing to the input directory of the server
    :param env_storage: ``str`` pointing to the :class:`~basyx.aas.backend.local_file.LocalFileIdentifiableStore`
        storage directory of the server if persistent storage is enabled
    :param env_storage_persistency: Flag to enable persistent storage
    :param env_storage_overwrite: Flag to overwrite existing :class:`Identifiables <basyx.aas.model.base.Identifiable>`
        in the :class:`~basyx.aas.backend.local_file.LocalFileIdentifiableStore` if persistent storage is enabled
    :param logger: :class:`~logging.Logger` used for start-up diagnostics
    :return: Tuple consisting of a storage backend and a
        :class:`~basyx.aas.adapter.aasx.DictSupplementaryFileContainer` for :class:`~interfaces.repository.WSGIApp`
    """

    env_storage_backend = os.getenv("STORAGE_BACKEND", "memory").lower()

    if env_storage_backend == "neo4j":
        from app.backend.neo4j import build_neo4j_object_store
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        logger.info('Using Neo4j backend at "%s" (user=%s)', neo4j_uri, neo4j_user)
        store = build_neo4j_object_store(neo4j_uri, neo4j_user, neo4j_password)
        if os.path.isdir(env_input):
            input_objects, input_supp_files = load_directory(env_input)
            loaded, skipped = 0, 0
            for obj in input_objects:
                try:
                    store.add(obj)
                    loaded += 1
                except KeyError:
                    skipped += 1
            logger.info(
                'Loaded %d identifiable(s) from "%s" into Neo4j (%d skipped, already existed)',
                loaded, env_input, skipped,
            )
            return store, input_supp_files
        else:
            logger.warning('INPUT directory "%s" not found, starting empty Neo4j store', env_input)
            return store, DictSupplementaryFileContainer()

    if env_storage_persistency:
        storage_files = LocalFileIdentifiableStore(env_storage)
        storage_files.check_directory(create=True)
        if os.path.isdir(env_input):
            input_files, input_supp_files = load_directory(env_input)
            added, overwritten, skipped = storage_files.sync(input_files, env_storage_overwrite)
            logger.info(
                'Loaded %d identifiable(s) and %d supplementary file(s) from "%s"',
                len(input_files),
                len(input_supp_files),
                env_input,
            )
            logger.info(
                "Synced INPUT to STORAGE with %d added and %d %s",
                added,
                overwritten if env_storage_overwrite else skipped,
                "overwritten" if env_storage_overwrite else "skipped",
            )
            return storage_files, input_supp_files
        else:
            logger.warning('INPUT directory "%s" not found, starting empty', env_input)
            return storage_files, DictSupplementaryFileContainer()

    if os.path.isdir(env_input):
        input_files, input_supp_files = load_directory(env_input)
        logger.info(
            'Loaded %d identifiable(s) and %d supplementary file(s) from "%s"',
            len(input_files),
            len(input_supp_files),
            env_input,
        )
        return input_files, input_supp_files
    else:
        logger.warning('INPUT directory "%s" not found, starting empty', env_input)
        return DictIdentifiableStore(), DictSupplementaryFileContainer()


# -------- WSGI entrypoint --------

logger = setup_logger()

env_input = os.getenv("INPUT", "/input")
env_storage = os.getenv("STORAGE", "/storage")
env_storage_persistency = os.getenv("STORAGE_PERSISTENCY", "false").lower() in {"1", "true", "yes"}
env_storage_overwrite = os.getenv("STORAGE_OVERWRITE", "false").lower() in {"1", "true", "yes"}
env_api_base_path = os.getenv("API_BASE_PATH")

wsgi_optparams = {"base_path": env_api_base_path} if env_api_base_path else {}

logger.info(
    'Loaded settings API_BASE_PATH="%s", STORAGE_BACKEND="%s", INPUT="%s", STORAGE="%s", PERSISTENCY=%s, OVERWRITE=%s',
    env_api_base_path or "",
    os.getenv("STORAGE_BACKEND", "memory"),
    env_input,
    env_storage,
    env_storage_persistency,
    env_storage_overwrite,
)

storage_files, supp_files = build_storage(
    env_input, env_storage, env_storage_persistency, env_storage_overwrite, logger
)

application = WSGIApp(storage_files, supp_files, **wsgi_optparams)

if __name__ == "__main__":
    logger.info("WSGI entrypoint created. Serve this module with uWSGI/Gunicorn/etc.")
