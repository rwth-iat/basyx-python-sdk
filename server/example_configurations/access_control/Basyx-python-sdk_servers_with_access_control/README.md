# Secured BaSyx Python Server Stack

This example runs the Python repository, registry and discovery servers together with the BaSyx AAS Web UI behind the access-control concept from `access_control_general`.

Envoy is the public API gateway. The Python servers are only reachable inside the Docker network. Envoy validates JWTs issued by Keycloak and asks OPA whether the request is allowed before forwarding it to a server.

## Components

- `envoy`: Public gateway on http://localhost:10000.
- `repository`: Python AAS/Submodel repository server.
- `registry`: Python AAS/Submodel registry server.
- `discovery`: Python AAS discovery server.
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

## Gateway Routes

| Public route | Backend service | Backend base path |
|--------------|-----------------|-------------------|
| `/ui` | `aas-web-ui:3000` | `/ui` |
| `/repository/api/v3.0/` | `repository:80` | `/repository/api/v3.0/` |
| `/registry/api/v3.1.1/` | `registry:80` | `/registry/api/v3.1.1/` |
| `/discovery/api/v3.1.1/` | `discovery:80` | `/discovery/api/v3.1.1/` |

The server containers are configured with matching `API_BASE_PATH` values, so Envoy does not rewrite API paths.

## Policy

OPA policy data is in `policies/data.json`.

The default rules are intentionally conservative:

- UI paths are public.
- `GET` on server APIs is allowed for `viewer`, `editor` and `admin`.
- `POST` and `PUT` are allowed for `editor` and `admin`.
- `DELETE` is allowed only for `admin`.

Change the policy data when repository, registry and discovery need different role models.

## UI Configuration

The UI infrastructure configuration is mounted from `basyx-infra.yml` and locked with:

```yaml
ENDPOINT_CONFIG_AVAILABLE: "false"
```

This avoids users accidentally bypassing the gateway by entering direct backend URLs.

## Notes

- Do not expose the repository, registry or discovery ports in production.
- Replace demo users, passwords and client settings before real use.
- Use HTTPS for Envoy and Keycloak outside local development.
- Keep the API paths in `envoy.yaml`, `basyx-infra.yml`, server `API_BASE_PATH` values and `policies/data.json` aligned.
