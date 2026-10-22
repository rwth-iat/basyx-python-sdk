# Secured BaSyx Python Server Stack

This example runs the BaSyx Python repository, registry and discovery servers together with the BaSyx AAS Web UI
behind the access-control layer described in the [overview](../../README.md).

## Components

- `envoy`: public gateway on http://localhost:10000.
- `repository`, `registry`, `discovery`: the published, unmodified BaSyx Python server images.
- `aas-web-ui`: BaSyx AAS Web UI, served under http://localhost:10000/ui.
- `keycloak`: demo identity provider on http://localhost:8080.
- `opa-envoy`: OPA, asked by Envoy for every request.
- `config-renderer`: fills the values of `.env` into `envoy.yaml.tmpl` and `basyx-infra.yml.tmpl`, then exits.

The Web UI is not the authorization authority. It uses the same Keycloak issuer only so that browsers can obtain a
token and send it to Envoy. The access decision is made by OPA.

## Run

```bash
docker compose up
```

Then open http://localhost:10000/ui and log in with one of the demo users. `docker compose down -v` resets the stack
to the example data. The Envoy admin interface is on http://localhost:8001 (only from this machine); OPA has no
published ports.

| User | Password | Role |
|------|----------|------|
| `viewer` | `viewer` | `viewer` |
| `editor` | `editor` | `editor` |
| `admin` | `admin` | `admin` |

## Configuration

Everything is set in [`.env`](.env): API version, public URLs and ports, Keycloak realm and client, role claim, the
addresses of the AAS servers behind the gateway, demo credentials and image versions. To protect other AAS servers,
e.g. BaSyx Java, point `REPOSITORY_HOST`/`REPOSITORY_PORT` etc. to them.

The UI is locked to the gateway with `ENDPOINT_CONFIG_AVAILABLE: "false"`, so users cannot bypass it by entering backend
URLs.

## Rules

The rules are in [`policy_data/data.json`](policy_data/data.json); the policy itself is shared by all examples
([`policy.rego`](../../policy/policy.rego)).

- UI paths are public.
- `editor` and `admin` may read (`GET`, `HEAD`) and change (`POST`, `PUT`, and `PATCH` on the repository) everything.
- Only `admin` may `DELETE`.
- `viewer` gets no general access. It may only read the example shell `https://example.org/Test_AssetAdministrationShell`
  (in repository, registry and discovery) and two of its submodels, `Identification` and `Test_Submodel`, but not
  `BillOfMaterial`.
- Roles are read only from the token's `realm_access.roles` claim.

## Example Data

`example_data/example_aas.json` is the SDK's full example (`basyx.aas.examples.data.example_aas.create_full_example()`)
serialized to JSON. The repository loads it on start-up; the identifiers in `policy_data/data.json` refer to it.

## Try it

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

These commands use the default values of `.env`.

## Tests

Rules of this example, no running stack needed:

```bash
docker run --rm -v "$PWD/../..:/ac:ro" openpolicyagent/opa:1.21.2-envoy-static test /ac/policy /ac/examples/basyx/policy_data -v
```

End-to-end tests against the running stack (Python 3.11+, no extra packages; endpoints are read from `.env`):

```bash
python -m unittest e2e_test -v
```

The end-to-end tests only read data or send requests that must be denied.

## Notes

- Do not publish the ports of the repository, registry or discovery servers in production.
- Replace demo users, passwords and client settings before real use.
- Use HTTPS for Envoy and Keycloak outside local development.
