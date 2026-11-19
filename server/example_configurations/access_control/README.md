# Access Control for AAS Servers

This folder contains an access-control layer for the [BaSyx Python SDK HTTP servers](../../README.md). It runs in
front of the servers and does not change them, so it can also protect other AAS servers (AAS Part 2 API).

## Why a separate layer

- Every operator has different infrastructure (Keycloak, Microsoft Entra ID, a company proxy); security built into the
  server rarely fits.
- The AAS specification separates the API (Part 2) from security (Part 4).
- One layer protects any server behind it, and it can be reviewed, updated and released on its own.
- Proven components (Envoy, OPA, an OpenID Connect provider) instead of custom security code.

## How it works

| Component | Role | Question it answers |
| --- | --- | --- |
| OpenID Connect provider (Keycloak in the example) | Authenticates users and issues signed JWTs with their roles | Who are you? |
| [Envoy](https://www.envoyproxy.io/) | The only public entry point; verifies the JWT (signature, issuer, audience, expiry), normalizes the path, asks OPA, routes the request | Is your token valid? |
| [OPA](https://www.openpolicyagent.org/) | Evaluates [`policy/policy.rego`](policy/policy.rego) against method, path and token roles | May you do this? |
| [Response filter](filter_server/README.md) | Between Envoy and the AAS servers for `GET`; removes from responses what OPA says the caller may not see | What of this may you see? |
| AAS servers | Unchanged; only reachable through Envoy | |

A request without a valid token gets `401`; a valid token without the required rights gets `403`. Envoy only sees the
request, never the response. Therefore `GET` requests pass through the response filter, which asks OPA which entries
of a list (and which submodel references in a shell) the caller may see and removes the others. The filter makes no
decisions of its own.

## Layout

```
access_control/
├── policy/              generic Rego policy and its unit tests
├── render-config.sh     fills .env values into configuration templates (Envoy cannot read environment variables)
├── examples/
│   └── basyx/           BaSyx Python repository, registry and discovery plus the AAS Web UI
└── filter_server/       response filter for GET responses (used by examples/basyx)
```

The example consists of `.env` (all settings), `compose.yaml`, `envoy.yaml.tmpl`, `keycloak/realm.json` and
`policy_data/` (its rules and tests for them).

## Configuration

The example is configured only through its `.env` file, which Docker Compose reads automatically. It contains the
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

The policy contains no application-specific values. The example describes its rules in `policy_data/data.json`
under `access_control`:

| Key | Meaning |
| --- | --- |
| `public_paths`, `public_path_prefixes` | Paths that need no token (e.g. the Web UI) |
| `rules` | Server-level rules: `path_prefix`, `methods`, `roles`. As in AAS Part 4, rules only allow: any matching rule grants the request. |
| `routes` | Path templates that identify resources, e.g. `/repository/api/{api_version}/shells/{aas}`. A placeholder names the resource type; the template also covers everything below it. |
| `resource_rules` | Resource-level rules: `resource` (type), `ids`, `id_prefixes` or `"*"`, `methods`, `roles`. Identifiers are readable (`https://example.org/...`); the policy decodes the base64url identifiers in the path itself. |
| `collections` | List endpoints (`path`, exact match) and the `resource` type of their entries. A caller with a resource rule for that type may read them, but only through the response filter (Envoy marks those routes with the context extension `response_filter=true`; without it the rule does not apply). |
| `api_base_paths` | Base paths below which the AAS API is served, e.g. `/repository/api/{api_version}`; they must not overlap. See [Rights](#rights). |
| `additional_operations` | Operations of the servers beyond the specification, in the shape of the table in [`policy/rights.rego`](policy/rights.rego) (`name`, `method`, `path`, `rights`) |
| `api_version`, `role_claim` | Defaults, overridable through OPA's environment (see above) |

A request is allowed if its path is canonical and it is public, or a server-level rule grants it, or every resource in
its path is granted by a resource rule, or it reads a collection through the response filter. For the filter, the
policy additionally answers `response_filter`: whether a response may pass unchanged, and which resources are visible. Paths with `..`, `.`, `//`, backslashes or encoded `.`, `/`, `\`, `%` are always
denied (Envoy already normalizes paths; this is a second line of defense). Roles come only from the configured role
claim, never from scopes or groups.

## Rights

Every request is mapped to the AAS API operation it calls, and the operation to the rights of the AAS Access Rule
Model (IDTA-01004) that an access rule has to grant (`required_rights` in [`policy/rights.rego`](policy/rights.rego)).
The table is the normative
[Operation to RIGHT Mapping](https://industrialdigitaltwin.io/aas-specifications/IDTA-01002/v3.2/annex/operation-to-right-mapping.html)
of IDTA-01002 v3.2, taken over unchanged. In short:

| Request | Right |
| --- | --- |
| `GET` on the repository, e.g. `/shells`, `/submodels/{id}`, `$metadata`, `$value`, `/description`, and `POST /query/shells`, `/query/submodels`, `/query/concept-descriptions` | `READ` |
| `GET` on `$reference`, `$path` and `/shells/{id}/submodel-refs`, and reading descriptors and asset links (registry, discovery) | `VIEW` |
| `POST` that adds a resource | `CREATE` |
| `PUT` on a resource that the client addresses by its identifier or path, e.g. `/shells/{id}`, `/submodels/{id}/submodel-elements/{idShortPath}`, `/shell-descriptors/{id}`, and `POST /lookup/shells/{id}` | `CREATE` or `UPDATE` |
| `PUT` on a part of a resource (`asset-information`, `attachment`, `thumbnail`), `PATCH` | `UPDATE` |
| `DELETE` | `DELETE` |
| `invoke`, `invoke-async`, `operation-status`, `operation-results` | `EXECUTE` |
| `POST /lookup/shellsByAssetLink`, `POST /query/shell-descriptors`, `POST /query/submodel-descriptors` | `VIEW` |

`CREATE` or `UPDATE` means that the right depends on whether the resource already exists. `HEAD` requires the rights
of `GET`. A trailing slash addresses the same operation. A request that matches no operation, e.g. an unknown path or
method, has no rights. The BaSyx servers additionally offer qualifier routes, which the example adds through
`additional_operations` with the rights of the corresponding submodel element operations.

The servers implement IDTA-01002 v3.1.1, which has no such mapping. Every operation of v3.1.1 is listed in the v3.2
table with the same method and path, except for the misspelled `invoke-asnyc` route of the single AAS interface, which
v3.2 corrects and the BaSyx servers do not offer.

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
- Demo users and passwords, no TLS: suitable for local use only.
