# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Reads config.yaml  once and exposes the entries as module-level constants.
Consumers should import the constants directly rather than reading the file.
"""
from functools import cache
from importlib.resources import files
from typing import Any

import yaml


@cache
def _cfg() -> dict[str, Any]:
    return yaml.safe_load(files(__package__).joinpath("config.yaml").read_text())


API_BASE_PATH: str = _cfg()["api_base_path"]
