# Authentication Migration

## Purpose

`oldap-tools` is a trusted administrative CLI that connects directly to
GraphDB through `oldaplib`. It does not call `oldap-api` and therefore does not
participate in the browser-oriented access/refresh-token lifecycle.

## Migration plan

1. Add an explicit `oldaplib.Connection` mode that authenticates credentials
   and builds the authorization context without issuing an access JWT.
2. Centralize all `oldap-tools` connection construction and select that mode.
3. Upgrade `oldap-tools` to the compatible `oldaplib` release while preserving
   the existing OLDAP and GraphDB credential options.
4. Verify credential failures, connection option forwarding, and representative
   read/write commands without requiring JWT signing secrets.

## Security boundary

The CLI must not receive `OLDAP_ACCESS_JWT_SECRET`,
`OLDAP_REFRESH_JWT_SECRET`, or `OLDAP_MEDIA_JWT_SECRET`. Those signing secrets
belong to the services that issue the corresponding tokens. A direct CLI
connection may authorize GraphDB operations but must not create tokens for
other services.
