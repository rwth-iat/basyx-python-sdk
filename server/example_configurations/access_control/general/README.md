# General Access Control with [Envoy](https://github.com/envoyproxy/envoy) and [OPA (Open policy Agent)](https://github.com/open-policy-agent/OPA)

This example shows how to put access control in front of any HTTP application without adding authorization code to the application itself.

## Overview
This example uses:
1. **Keycloak** for user authentication.
2. **Envoy reverse proxy** to act as an intermediary, enforcing authentication and authorization. It validates JWTs and calls OPA for authorization.
3. **Open Policy Agent (OPA)** for access control.
4. **app**: A replaceable demo application. In real deployments this is the service you want to protect.

The application only receives requests after:

1. Envoy has verified the incoming bearer token against an OpenID Connect issuer.
2. Envoy has asked OPA whether the verified request is allowed.
3. OPA has matched the request method, path and token roles against the configured policy data.

![Workflow](img.png)

## Adapting It to Any Application
The demo Keycloak realm is imported automatically. 

1. Replace the `app` service in `compose.yaml` with your application, or update the `app` cluster in `envoy.yaml` to point to an existing host and port.
2. Update the OIDC settings in `envoy.yaml`:
   - `issuer`
   - `audiences`
   - `remote_jwks.http_uri.uri`
   - the `keycloak` cluster if your JWKS endpoint is not the demo Keycloak service
3. Update `keycloak/realm.json` only for the local demo identity provider, or replace Keycloak with your real identity provider.
4. Edit `policies/data.json` to describe the application's protected path prefixes, methods and required roles.

The Rego policy in `policies/policy.rego` is intentionally generic. Most application-specific changes should be made in `policies/data.json`.
