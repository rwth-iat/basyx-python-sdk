# Secured BaSyx Python Server Stack

This example runs the Basyx Python repository, registry and discovery servers together with the BaSyx AAS Web UI behind the access-control concept from [`general`](../general).

## Components

- `envoy`: Public gateway on http://localhost:10000.
- `repository`: Basyx Python AAS/Submodel repository server.
- `registry`: Basyx Python AAS/Submodel registry server.
- `discovery`: Basyx Python AAS discovery server.
- `aas-web-ui`: BaSyx AAS Web UI served under http://localhost:10000/ui.
- `keycloak`: Demo identity provider on http://localhost:8080.
- `opa-envoy`: OPA external authorization service for Envoy.

The BaSyx UI is not used as the authorization authority. It is preconfigured with the same Keycloak issuer only so browser clients can obtain a bearer token and send it to Envoy. The final access decision is made by OPA.

## Run

Start the stack from this directory:

```bash
docker compose up
```

The BaSyx servers run as the published images (`eclipsebasyx/basyx-python-*`), so nothing is built. Server data is
kept in Docker volumes; `docker compose down -v` resets the stack to the example data.

Open:

- BaSyx UI: http://localhost:10000/ui
- Keycloak: http://localhost:8080
- Envoy admin: http://localhost:8001 (only from this machine)

OPA has no published ports: only Envoy talks to it over the internal network.

Demo users:

| User | Password | Role |
|------|----------|------|
| `viewer` | `viewer` | `viewer` |
| `editor` | `editor` | `editor` |
| `admin` | `admin` | `admin` |

## Policy

OPA policy data is in `policies/data.json`.
The policy has two layers:
1. Server-level rules decide whether a role may call broad server areas such as `/repository`, `/registry` or `/discovery` with a given HTTP method.
2. Resource-level rules decide whether a role may access a concrete resource URL when the resource id is present in the request path.

- UI paths are public.
- `GET` and `HEAD` on broad server APIs are allowed for `editor` and `admin`.
- `POST` and `PUT` are allowed for `editor` and `admin`, `PATCH` additionally on the repository.
- `DELETE` is allowed only for `admin`.
- `viewer` does not receive broad repository, registry or discovery access. It may only read the example shell
  `https://example.org/Test_AssetAdministrationShell` and two of its submodels (`Identification` and
  `Test_Submodel`), but not its `BillOfMaterial` submodel.
- Roles are read only from the token's `realm_access.roles` claim; scopes and groups are not roles.
- Requests whose path is not canonical (`..`, `.`, `//`, encoded `.`, `/`, `\` or `%`) are denied. Envoy normalizes
  paths before asking OPA (`normalize_path`, `merge_slashes`); the policy check is a second line of defense.

`GET all` requests are not supported for resource-level filtering in this version.

## Example Data

`example_data/example_aas.json` is the SDK's full example (`basyx.aas.examples.data.example_aas.create_full_example()`)
serialized to JSON. The repository loads it on start-up; the identifiers in `policies/data.json` refer to it.

## UI Configuration

The UI infrastructure configuration is mounted from `basyx-infra.yml` and locked with:

```yaml
ENDPOINT_CONFIG_AVAILABLE: "false"
```

This avoids users accidentally bypassing the gateway by entering direct backend URLs.

## Test resource level access

The viewer can read the listed example shell:

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/realms/basyx-secured-stack/protocol/openid-connect/token \
  -d grant_type=password -d client_id=basyx-web-ui -d username=viewer -d password=viewer \
  | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:10000/repository/api/v3.1/shells/aHR0cHM6Ly9leGFtcGxlLm9yZy9UZXN0X0Fzc2V0QWRtaW5pc3RyYXRpb25TaGVsbA
```

The same in PowerShell:

```powershell
$token = (Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8080/realms/basyx-secured-stack/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{
    grant_type = "password"
    client_id = "basyx-web-ui"
    username = "viewer"
    password = "viewer"
  }).access_token

Invoke-WebRequest `
  -Method Get `
  -Uri "http://localhost:10000/repository/api/v3.1/shells/aHR0cHM6Ly9leGFtcGxlLm9yZy9UZXN0X0Fzc2V0QWRtaW5pc3RyYXRpb25TaGVsbA" `
  -Headers @{ Authorization = "Bearer $token" } |
  ConvertTo-Json -Depth 50
```

## Tests

Policy unit tests (no running stack needed), from this directory:

```bash
docker run --rm -v "$PWD/policies:/policies:ro" openpolicyagent/opa:1.21.2-envoy-static test /policies -v
```

End-to-end tests against the running stack (Python 3.11+, no extra packages):

```bash
python -m unittest e2e_test -v
```

The end-to-end tests only read data or send requests that must be denied.


## Notes

- Do not expose the repository, registry or discovery ports in production.
- Replace demo users, passwords and client settings before real use.
- Use HTTPS for Envoy and Keycloak outside local development.
- Keep the API paths in `envoy.yaml`, `basyx-infra.yml`, server `API_BASE_PATH` values and `policies/data.json` aligned.
