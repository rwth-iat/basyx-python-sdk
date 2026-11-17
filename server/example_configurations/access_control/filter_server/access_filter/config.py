# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""Settings of the response filter, read from environment variables."""
import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    #: Path prefix (e.g. ``/repository``) to base URL of the server behind it (e.g. ``http://repository:80``)
    upstreams: dict[str, str]
    #: URL of the OPA decision that tells the filter what to show
    opa_url: str
    #: Header in which Envoy passes the verified JWT payload (base64url-encoded JSON)
    claims_header: str = "x-jwt-payload"
    #: Upper limit of items a filtered collection may have; larger collections are refused instead of truncated
    max_items: int = 10000
    #: Page size used when reading a collection from a server
    upstream_page_size: int = 500
    #: Timeout in seconds for calls to servers and OPA
    timeout: float = 10.0

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] = os.environ) -> "Settings":
        """
        Read the settings from ``FILTER_UPSTREAMS`` (space-separated ``prefix=url`` pairs), ``FILTER_OPA_URL`` and the
        optional ``FILTER_CLAIMS_HEADER``, ``FILTER_MAX_ITEMS``, ``FILTER_UPSTREAM_PAGE_SIZE`` and ``FILTER_TIMEOUT``.
        """
        upstreams: dict[str, str] = {}
        for pair in environ.get("FILTER_UPSTREAMS", "").split():
            prefix, separator, url = pair.partition("=")
            if not separator or not prefix.startswith("/") or not url:
                raise ValueError(f"FILTER_UPSTREAMS: expected '/prefix=url', got {pair!r}")
            upstreams["/" + prefix.strip("/")] = url.rstrip("/")
        if not upstreams:
            raise ValueError("FILTER_UPSTREAMS must name at least one server")
        opa_url = environ.get("FILTER_OPA_URL", "")
        if not opa_url:
            raise ValueError("FILTER_OPA_URL must be set")
        return cls(
            upstreams=upstreams,
            opa_url=opa_url,
            claims_header=environ.get("FILTER_CLAIMS_HEADER", cls.claims_header),
            max_items=int(environ.get("FILTER_MAX_ITEMS", cls.max_items)),
            upstream_page_size=int(environ.get("FILTER_UPSTREAM_PAGE_SIZE", cls.upstream_page_size)),
            timeout=float(environ.get("FILTER_TIMEOUT", cls.timeout)),
        )
