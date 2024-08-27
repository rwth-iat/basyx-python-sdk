# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import requests
from typing import List, Dict, Any
import json
from . import backends
from basyx.aas import model
from basyx.aas.model.protocols import Protocol


class HTTPBackend(backends.Backend):
    @classmethod
    def _parse_source(cls, source: Dict[str, Any]) -> str:
        """
        Parses the source dictionary to extract the URL for HTTP requests.
        """
        base = source.get('base')
        href = source.get('href')
        if not base or not href:
            raise ValueError("Invalid source format. 'base' and 'href' must be provided.")
        return f"{base}{href}"

    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Dict[str, Any]) -> None:
        """
        Updates an object by fetching the latest state from the HTTP server.
        """
        url = cls._parse_source(source)
        method = source.get('method', 'GET')

        if method != 'GET':
            print(f"Warning: HTTP method '{method}' may not be appropriate for fetching data. GET is recommended.")

        try:
            response = requests.request(method, url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to fetch the current object state from server: {e}")
            return

        try:
            data = response.json()
            if isinstance(data, dict) and 'value' in data:
                updated_object.value = data['value']
            else:
                print("Unexpected data format received from server")
                updated_object.value = data  # Fallback to using the entire response
        except json.JSONDecodeError:
            print("Failed to decode JSON response")

    @classmethod
    def commit_object(cls,
                      committed_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Dict[str, Any]) -> None:
        """
        Commits an object to the HTTP server.
        """
        url = cls._parse_source(source)
        method = source.get('method', 'POST')

        if method not in ['POST', 'PUT']:
            print(f"Warning: HTTP method '{method}' may not be appropriate for committing data")

        headers = {'Content-Type': 'application/json'}

        data = {"value": committed_object.value}

        try:
            response = requests.request(method, url, headers=headers, json=data)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to commit the object to the server: {e}")


backends.register_backend(Protocol.HTTP, HTTPBackend)
