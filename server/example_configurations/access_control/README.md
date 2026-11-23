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
| [OPA](https://www.openpolicyagent.org/) | Evaluates [`policy/policy.rego`](policy/policy.rego): which rights the request requires, and whether the [access rules](#access-rules) grant them to the caller | May you do this? |
| [Response filter](filter_server/README.md) | Between Envoy and the AAS servers for `GET`; removes from responses what OPA says the caller may not see | What of this may you see? |
| AAS servers | Unchanged; only reachable through Envoy | |

A token is optional: rules for `ANONYMOUS` can grant access without one. A token that is sent must be valid, otherwise
Envoy answers `401`. A denied request gets `401` with `WWW-Authenticate: Bearer` if it has no token, so the client
knows that logging in may help, and `403` if it has one. Envoy only sees the request, never the response. Therefore `GET` requests pass through the response filter, which asks OPA which entries
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
`policy_data/` (its access rules, server paths and tests for them).

## Configuration

The example is configured only through its `.env` file, which Docker Compose reads automatically. It contains the
public URLs and ports, the OpenID Connect issuer, client and key location, the backend addresses, demo credentials and
the pinned image versions. The values reach the components as follows:

| Component | How it gets the values |
| --- | --- |
| Envoy, Web UI | `config-renderer` service renders `*.tmpl` with `envsubst` before they start |
| Keycloak | resolves `${...}` placeholders in `keycloak/realm.json` during the import |
| OPA | `ACCESS_CONTROL_API_VERSION` overrides `api_version` in `policy_data/data.json` |
| BaSyx servers | `API_BASE_PATH` |
| `e2e_test.py` | reads the same `.env` |

A missing value stops the stack with an error instead of producing a broken configuration.
Requires Docker Engine 26 or newer and Docker Compose 2.27 or newer (volume `subpath` mounts).

## Access rules

Who may do what is set by access rules in the JSON serialization of the
[AAS Access Rule Model](https://industrialdigitaltwin.io/aas-specifications/IDTA-01004/v3.1/access-rule-model.html)
(IDTA-01004 v3.1), e.g. the example's [`policy_data/access_rules.json`](examples/basyx/policy_data/access_rules.json).
The file is a document `{"AllAccessPermissionRules": ...}` that validates against the specification's JSON schema; OPA
loads it next to `data.json`, and [`policy/access_rules.rego`](policy/access_rules.rego) evaluates it.

A rule applies to a request if its ACL has `ACCESS` `ALLOW`, its `ATTRIBUTES` fit the caller and its `FORMULA` is
true. It then grants its `RIGHTS` on its `OBJECTS`; rules only allow, and what no rule grants is denied. The
specification leaves some points open; the policy handles them as follows:

| Point | Handling |
| --- | --- |
| `ATTRIBUTES` | Every `CLAIM` must be in the token. A rule needs a `CLAIM` or `GLOBAL` `ANONYMOUS`. A rule for `ANONYMOUS` grants public access: it applies to callers without a token and to callers with one. |
| `CLAIM` | Names a top-level claim of the token, e.g. `roles`. A list-valued claim stands for each of its values: `$eq` holds if any value is equal, `$ne` if none is, and the other comparisons if they hold for any value. Roles are compared as `{"$eq": [{"$attribute": {"CLAIM": "roles"}}, {"$strVal": "admin"}]}`. |
| `ROUTE` | The path of an API operation below the API base path (`api_base_paths`), e.g. `/shells`, as in the examples of the specification. Without `*` it matches exactly; ending in `*` it matches every path that starts with the part before the `*`; `*` alone matches the whole API. A `ROUTE` applies to every server whose API has that path (e.g. `/description`). |
| `IDENTIFIABLE`, `DESCRIPTOR` | `$aas`, `$sm`, `$cd`, `$aasdesc` and `$smdesc` with an identifier or `"*"`. They cover the requests that address the object by its identifier (see `routes` below), and its entries in lists (see `collections`). |
| `PUT` and other create-or-replace operations | Require `CREATE` and `UPDATE` until the policy checks whether the resource exists. |

Supported are `DEFATTRIBUTES`, `DEFACLS`, `DEFOBJECTS` and `DEFFORMULAS`; the objects `ROUTE`, `IDENTIFIABLE` and
`DESCRIPTOR`; and formulas with `$and`, `$or`, `$not`, `$boolean` and the comparisons `$eq`, `$ne`, `$gt`, `$ge`,
`$lt`, `$le`, `$contains`, `$starts-with`, `$ends-with` and `$regex` of `$strVal`, `$numVal`, `$boolean` and `CLAIM`
values, with up to six nested logical operators. A rule that uses anything else never applies: `REFERABLE` and
`FRAGMENT` objects, conditions on the content of objects (`$field`), casts, time attributes as values, and rules with
`FILTER` or `FILTERLIST`, which would grant more than intended without their filter. A formula that is invalid (e.g. it
compares values of different types or refers to a claim the token lacks) does not hold, as the specification requires.

## Policy data

The policy contains no application-specific values. Besides its access rules, the example describes its servers in
`policy_data/data.json` under `access_control`:

| Key | Meaning |
| --- | --- |
| `public_paths`, `public_path_prefixes` | Paths outside the AAS API that need no token (e.g. the Web UI) |
| `api_base_paths` | Base paths below which the AAS API is served, e.g. `/repository/api/{api_version}`; they must not overlap. See [Rights](#rights). |
| `additional_operations` | Operations of the servers beyond the specification, in the shape of the table in [`policy/rights.rego`](policy/rights.rego) (`name`, `method`, `path`, `rights`) |
| `routes` | Path templates that identify objects, e.g. `/repository/api/{api_version}/shells/{$aas}`. A placeholder names the object type as in `IDENTIFIABLE` and `DESCRIPTOR` objects; the template also covers everything below it. Identifiers in the path are base64url-encoded and compared in decoded form, so the rules contain readable identifiers. |
| `collections` | List endpoints (`path`, exact match) and the object type of their entries (`resource`). A caller whose rules grant the required rights on objects of that type may read them, but only through the response filter (Envoy marks those routes with the context extension `response_filter=true`; without it this does not apply). |
| `api_version` | Default, overridable through OPA's environment (see above) |

A request is allowed if its path is canonical and it is public, or rules with a matching `ROUTE` grant the rights it
requires (see [Rights](#rights)), or rules with matching `IDENTIFIABLE` or `DESCRIPTOR` objects grant them for every
object in its path, or it reads a collection through the response filter. For the filter, the policy additionally
answers `response_filter`: whether a response may pass unchanged, and which objects are visible. Paths with `..`, `.`,
`//`, backslashes or encoded `.`, `/`, `\`, `%` are always denied (Envoy already normalizes paths; this is a second
line of defense).

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

`CREATE` or `UPDATE` means that the right depends on whether the resource already exists. The policy does not check
this yet and requires both. `HEAD` requires the rights of `GET`. A trailing slash addresses the same operation. A request that matches no operation, e.g. an unknown path or
method, has no rights and is denied; so are bulk results (`/bulk/status`, `/bulk/result`), which take the rights of
the request that started them. The BaSyx servers additionally offer qualifier routes, which the example adds through
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
- Responses that need filtering are only available as JSON; a caller who accepts only XML gets `406`.
- Demo users and passwords, no TLS: suitable for local use only.
