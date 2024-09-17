# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any
import json
from . import backends
from basyx.aas import model
from basyx.aas.model.protocols import ProtocolExtractor, Protocol


class HTTPBackend(backends.Backend):
    @classmethod
    def _parse_source(cls, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the source dictionary to extract all parameters needed for HTTP requests.
        """
        if not isinstance(source.get('protocol'), Protocol) or source['protocol'] != Protocol.HTTP:
            raise ValueError("Invalid protocol. Must be HTTP protocol.")
        
        return source

    @classmethod
    def _prepare_request_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepares request parameters including security settings.
        """
        request_params = {}
        headers = {'Content-Type': params.get('contentType', 'application/json')}
        
        security = params.get('security', {})
        if 'nosec_sc' in security:
            # No security required
            pass
        elif 'basic_sc' in security:
            # Basic authentication
            auth = HTTPBasicAuth(params.get('username'), params.get('password'))
            request_params['auth'] = auth
        elif 'bearer_sc' in security:
            # Bearer token authentication
            headers['Authorization'] = f"Bearer {params.get('token')}"
        
        request_params['headers'] = headers
        return request_params

    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Dict[str, Any]) -> None:
        """
        Updates an object by fetching the latest state from the HTTP server.
        """
        params = cls._parse_source(source)
        url = f"{params['base']}{params['href']}"
        method = params.get('method', 'GET')
        request_params = cls._prepare_request_params(params)

        if method != 'GET':
            print(f"Warning: HTTP method '{method}' may not be appropriate for fetching data. GET is recommended.")

        try:
            response = requests.request(method, url, **request_params)
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
        params = cls._parse_source(source)
        url = f"{params['base']}{params['href']}"
        method = params.get('method', 'POST')
        request_params = cls._prepare_request_params(params)

        if method not in ['POST', 'PUT']:
            print(f"Warning: HTTP method '{method}' may not be appropriate for committing data")

        data = {"value": committed_object.value}
        request_params['json'] = data

        try:
            response = requests.request(method, url, **request_params)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to commit the object to the server: {e}")


backends.register_backend(Protocol.HTTP, HTTPBackend)
