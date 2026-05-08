# Secured BaSyx Python Server Stack

This example runs the Basyx Python repository, registry and discovery servers together with the BaSyx AAS Web UI behind the access-control concept from `access_control_general`.

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
docker compose up --build
```

Open:

- BaSyx UI: http://localhost:10000/ui
- Keycloak: http://localhost:8080
- Envoy admin: http://localhost:8001

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
- `GET` on broad server APIs is allowed for `editor` and `admin`.
- `POST` and `PUT` are allowed for `editor` and `admin`.
- `DELETE` is allowed only for `admin`.
- `viewer` does not receive broad repository, registry or discovery access

`GET all` requests are not supported for resource-level filtering in this version.

## UI Configuration

The UI infrastructure configuration is mounted from `basyx-infra.yml` and locked with:

```yaml
ENDPOINT_CONFIG_AVAILABLE: "false"
```

This avoids users accidentally bypassing the gateway by entering direct backend URLs.

## Test resource level access

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
  -Uri "http://localhost:10000/repository/api/v3.0/shells/aHR0cHM6Ly9hY3BsdC5vcmcvVGVzdF9Bc3NldEFkbWluaXN0cmF0aW9uU2hlbGw" `
  -Headers @{ Authorization = "Bearer $token" } |
  ConvertTo-Json -Depth 50
```


## Notes

- Do not expose the repository, registry or discovery ports in production.
- Replace demo users, passwords and client settings before real use.
- Use HTTPS for Envoy and Keycloak outside local development.
- Keep the API paths in `envoy.yaml`, `basyx-infra.yml`, server `API_BASE_PATH` values and `policies/data.json` aligned.
