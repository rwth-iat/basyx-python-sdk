# Response Filter

Envoy can allow or deny a request, but it never sees the response. A caller who may see only some shells could
therefore not list any. The response filter sits between Envoy and the AAS servers for `GET` requests and removes
what the caller may not see:

- entries of collections (`/shells`, `/submodels`, `/shells/{id}/submodel-refs`, `/shell-descriptors`,
  `/submodel-descriptors`, `/shell-descriptors/{id}/submodel-descriptors`, `/lookup/shells`),
- references to submodels in a shell (`submodels`) and nested submodel descriptors in a shell descriptor.

It makes **no access decisions** itself. For every request it asks OPA for the `response_filter` decision of the
shared policy ([`policy.rego`](../policy/policy.rego)), with the original request and the resources found in the
response:

- `"unfiltered": true` (a server-level rule grants the request, e.g. for editors): the response passes unchanged.
- otherwise only the resources in `"visible"` remain. If `"collection"` is true (the path is one of the policy's
  `collections`), the response is a list: it is read completely from the server, filtered and paginated by the filter
  itself (its own `cursor`). Only the policy decides what is a collection, so that, e.g., an element with the idShort
  `shells` is not mistaken for one.

The caller's roles come from the JWT payload that Envoy has verified and forwards in a header (`x-jwt-payload`); the
filter never decodes the bearer token itself. It must only be reachable through Envoy, and Envoy must remove this
header from incoming requests, so that a request without a token cannot bring its own (Envoy's `jwt_authn` does so on
every route that lists the provider, also with `allow_missing`).

The filter can only read JSON. For responses it has to filter, it therefore always asks the server for JSON, and a
caller who accepts no JSON (e.g. only `application/xml`) gets `406`; otherwise the XML response would show what JSON
hides. Callers whose response passes unchanged still get XML. Responses that are not JSON anyway (e.g. files) and error
responses pass unchanged. If OPA is unavailable or returns no complete decision, the filter answers `503`; if a collection has more than `FILTER_MAX_ITEMS` entries, `502` (filtering it after the fact would be too
expensive, see Limitations in the [overview](../README.md)).

## Code

| Module | Contents |
| --- | --- |
| `access_filter/config.py` | settings from environment variables |
| `access_filter/resources.py` | where resources appear in AAS API responses (AAS Part 2), no access rules |
| `access_filter/app.py` | the WSGI application: asks OPA, reads from the server, filters, paginates |

Runtime dependencies are pinned in `requirements.txt` (Werkzeug and urllib3 like the BaSyx server, gunicorn as WSGI
server).

## Configuration

| Variable | Meaning | Default |
| --- | --- | --- |
| `FILTER_UPSTREAMS` | space-separated `prefix=url` pairs, e.g. `/repository=http://repository:80` | required |
| `FILTER_OPA_URL` | URL of the decision, e.g. `http://opa-envoy:8181/v1/data/envoy/authz/response_filter` | required |
| `FILTER_CLAIMS_HEADER` | header with the verified JWT payload | `x-jwt-payload` |
| `FILTER_MAX_ITEMS` | largest collection that is filtered | `10000` |
| `FILTER_UPSTREAM_PAGE_SIZE` | page size when reading collections from a server | `500` |
| `FILTER_TIMEOUT` | timeout for calls to servers and OPA, in seconds | `10` |

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover -v
```
