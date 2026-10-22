#!/bin/sh
# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
#
# Renders every /templates/*.tmpl to /rendered/<name> by replacing ${VARIABLE} with the value of that environment
# variable. Only the variables named in RENDER_VARIABLES are replaced, so any other "$" stays untouched. Fails if one of
# them is empty, so a missing value in .env stops the stack instead of producing a broken configuration.
set -eu

: "${RENDER_VARIABLES:?RENDER_VARIABLES must list the variables to substitute}"

substitutions=""
for name in $RENDER_VARIABLES; do
    value=$(printenv "$name" || true)
    if [ -z "$value" ]; then
        echo "render-config: $name is not set (see .env)" >&2
        exit 1
    fi
    substitutions="$substitutions \${$name}"
done

for template in /templates/*.tmpl; do
    target="/rendered/$(basename "$template" .tmpl)"
    envsubst "$substitutions" < "$template" > "$target"
    echo "render-config: rendered $target"
done
