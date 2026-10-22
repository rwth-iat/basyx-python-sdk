# Access Control for AAS Servers

This folder contains an access-control layer for the [BaSyx Python SDK HTTP servers](../server/README.md). It runs in
front of the servers and does not change them, so it is not limited to the BaSyx Python SDK servers: it can also
protect other AAS servers (AAS Part 2 API) or any other HTTP application.

## Why a separate layer

- Every operator has different infrastructure (Keycloak, Microsoft Entra ID, a company proxy); security built into the
  server rarely fits.
- The AAS specification separates the API (Part 2) from security (Part 4).
- One layer protects any server behind it, and it can be reviewed, updated and released on its own.
- Proven components (Envoy, OPA, an OpenID Connect provider) instead of custom security code.

## How it works

| Component | Role | Question it answers |
| --- | --- | --- |
| OpenID Connect provider (Keycloak in the examples) | Authenticates users and issues signed JWTs with their roles | Who are you? |
| [Envoy](https://www.envoyproxy.io/) | The only public entry point; verifies the JWT (signature, issuer, audience, expiry), normalizes the path, asks OPA, routes the request | Is your token valid? |
| [OPA](https://www.openpolicyagent.org/) | Evaluates [`policy/policy.rego`](policy/policy.rego) against method, path and token roles | May you do this? |
| [Response filter](filter_server/README.md) | Between Envoy and the AAS servers for `GET`; removes from responses what OPA says the caller may not see | What of this may you see? |
| AAS servers | Unchanged; only reachable through Envoy | |

A request without a valid token gets `401`; a valid token without the required rights gets `403`. Envoy only sees the
request, never the response. Therefore `GET` requests pass through the response filter, which asks OPA which entries
of a list (and which submodel references in a shell) the caller may see and removes the others. The filter makes no
decisions of its own. See the [sequence diagram](examples/general/img.png) for the request path without the filter.

## Layout

```
access_control/
├── policy/              generic Rego policy and its unit tests, shared by all examples
├── render-config.sh     fills .env values into configuration templates (Envoy cannot read environment variables)
├── examples/
│   ├── general/         the pattern in front of a placeholder application (nginx)
│   └── basyx/           BaSyx Python repository, registry and discovery plus the AAS Web UI
└── filter_server/       response filter for GET responses (used by examples/basyx)
```

Each example has the same structure: `.env` (all settings), `compose.yaml`, `envoy.yaml.tmpl`, `keycloak/realm.json`
and `policy_data/` (its rules and tests for them).

## Configuration

Each example is configured only through its `.env` file, which Docker Compose reads automatically. It contains the
public URLs and ports, the OpenID Connect issuer, client and key location, the role claim, the backend addresses, demo
credentials and the pinned image versions. The values reach the components as follows:

| Component | How it gets the values |
| --- | --- |
| Envoy, Web UI | `config-renderer` service renders `*.tmpl` with `envsubst` before they start |
| Keycloak | resolves `${...}` placeholders in `keycloak/realm.json` during the import |
| OPA | `ACCESS_CONTROL_API_VERSION` and `ACCESS_CONTROL_ROLE_CLAIM` override `policy_data/data.json` |
| BaSyx servers | `API_BASE_PATH` |
| `e2e_test.py` | reads the same `.env` |

A missing value stops the stack with an error instead of producing a broken configuration.
Requires Docker Engine 26 or newer and Docker Compose 2.27 or newer (volume `subpath` mounts).

## Policy data

The policy contains no application-specific values. Each example describes its rules in `policy_data/data.json`
under `access_control`:

| Key | Meaning |
| --- | --- |
| `public_paths`, `public_path_prefixes` | Paths that need no token (e.g. the Web UI) |
| `rules` | Server-level rules: `path_prefix`, `methods`, `roles`. For a request, only the rules with the longest matching prefix count, so `/admin` can override `/`. |
| `routes` | Path templates that identify resources, e.g. `/repository/api/{api_version}/shells/{aas}`. A placeholder names the resource type; the template also covers everything below it. |
| `resource_rules` | Resource-level rules: `resource` (type), `ids`, `id_prefixes` or `"*"`, `methods`, `roles`. Identifiers are readable (`https://example.org/...`); the policy decodes the base64url identifiers in the path itself. |
| `collections` | List endpoints (`path`, exact match) and the `resource` type of their entries. A caller with a resource rule for that type may read them, but only through the response filter (Envoy marks those routes with the context extension `response_filter=true`; without it the rule does not apply). |
| `api_version`, `role_claim` | Defaults, overridable through OPA's environment (see above) |

A request is allowed if its path is canonical and it is public, or a server-level rule grants it, or every resource in
its path is granted by a resource rule, or it reads a collection through the response filter. For the filter, the
policy additionally answers `response_filter`: whether a response may pass unchanged, and which resources are visible. Paths with `..`, `.`, `//`, backslashes or encoded `.`, `/`, `\`, `%` are always
denied (Envoy already normalizes paths; this is a second line of defense). Roles come only from the configured role
claim, never from scopes or groups.

## Tests

| What | Command (from `access_control/`) | CI job |
| --- | --- | --- |
| Policy logic | `docker run --rm -v "$PWD:/ac:ro" openpolicyagent/opa:1.21.2-envoy-static test /ac/policy -v` | `access-control-policy-test` |
| An example's rules | `docker run --rm -v "$PWD:/ac:ro" openpolicyagent/opa:1.21.2-envoy-static test /ac/policy /ac/examples/basyx/policy_data -v` | `access-control-policy-test` |
| BaSyx stack end to end | in `examples/basyx`: `docker compose up -d`, then `python -m unittest e2e_test -v` | `access-control-e2e` |
| Response filter | in `filter_server`: `python -m unittest discover -v` | `access-control-static-analysis` |
| Python code style and types | `ruff check` and `mypy` | `access-control-static-analysis` |

## Limitations

- For callers who only see part of a collection, the response filter reads the whole collection from the server
  before filtering (up to `FILTER_MAX_ITEMS`, default 10000). This gets slow for large data sets; filtering in the
  server, e.g. through the AAS query language, would scale better but would couple the layer to the server.
- The general example has no response filter: its placeholder application has no AAS responses to filter.
- Demo users and passwords, no TLS: suitable for local use only.
