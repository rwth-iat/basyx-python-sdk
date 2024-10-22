# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Union
import json
from . import backends
from basyx.aas import model
from basyx.aas.model.protocols import ProtocolExtractor, Protocol


class HTTPBackend(backends.ValueBackend):
    @classmethod
    def _parse_source(cls, source: Any) -> Dict[str, Any]:
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

        request_params['headers'] = headers  # type: ignore
        return request_params

    @classmethod
    def update_value(cls,
                     updated_object: model.Referable,
                     source: Any) -> None:
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
            cls._set_object_value(updated_object, data)
        except json.JSONDecodeError:
            print("Failed to decode JSON response")

    @classmethod
    def commit_value(cls,
                     committed_object: model.Referable,
                     source: Any) -> None:
        """
        Commits an object to the HTTP server.
        """
        params = cls._parse_source(source)
        url = f"{params['base']}{params['href']}"
        method = params.get('method', 'PUT')
        request_params = cls._prepare_request_params(params)

        if method not in ['POST', 'PUT']:
            print(f"Warning: HTTP method '{method}' may not be appropriate for committing data")

        data = cls._get_object_value(committed_object)
        request_params['json'] = data

        try:
            response = requests.request(method, url, **request_params)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to commit the object to the server: {e}")

    @staticmethod
    def _set_object_value(obj: model.Referable, data: Any) -> None:
        """
        Sets the value of an object, handling cases where 'value' attribute might not exist.
        """
        if isinstance(data, dict) and 'value' in data:
            value_to_set = data['value']
        else:
            value_to_set = data

        if hasattr(obj, 'value'):
            obj.value = value_to_set
        else:
            print(f"Warning: Object of type {type(obj).__name__} does not have a 'value' attribute.")

    @staticmethod
    def _get_object_value(obj: model.Referable) -> Dict[str, Any]:
        """
        Gets the value of an object, handling cases where 'value' attribute might not exist.
        """
        if hasattr(obj, 'value'):
            return {"value": obj.value}
        else:
            print(f"Warning: Object of type {type(obj).__name__} does not have a 'value' attribute.")
            return {}


backends.register_backend(Protocol.HTTP, HTTPBackend)
