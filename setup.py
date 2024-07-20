#!/usr/bin/env python3
# Copyright (c) 2019-2024 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import setuptools

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name="basyx-python-sdk",
    # version is managed by pyproject.toml
    author="The Eclipse BaSyx Authors",
    description="The Eclipse BaSyx Python SDK, an implementation of the Asset Administration Shell for Industry 4.0 "
                "systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eclipse-basyx/basyx-python-sdk",
    packages=setuptools.find_packages(exclude=["test", "test.*"]),
    zip_safe=False,
    package_data={
        "basyx": ["py.typed"],
        "basyx.aas.examples.data": ["TestFile.pdf"],
    },
)