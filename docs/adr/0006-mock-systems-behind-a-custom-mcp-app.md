# 0006: Najm's mock systems behind a custom MCP server on Databricks Apps

- **Status:** Accepted
- **Date:** 2026-11-09
- **Phase:** 5

## Context

Phase 5 is done when the agent reads the mock CRM, ERP and ITSM and posts to a mock Teams channel through a custom MCP server, with retries and a fallback on failure. The writes stay behind approval (Phase 4).

Constraints:
- Free Edition allows three Databricks Apps, and the agent already uses one.
- A deployed MCP server must be reachable from the deployed agent, so a laptop's Docker isn't enough.
- No workspace token may go to a server outside Databricks.

## Options

1. **A custom MCP server on Databricks Apps,** added in `agent/agent/mcps.py`. Won; see Decision.
2. **A Unity Catalog MCP service:** a UC securable backed by a UC HTTP connection to the server. Lost for now.
   - It's the governed route: per-group `EXECUTE` grants, audit, and binding with `agentbricks tools add mcp <catalog.schema.service>`.
   - But the connection needs the server's credentials as a service-principal OAuth secret, and that's more moving parts than a mock needs. It's the upgrade path in Phase 7.
3. **The REST API and the MCP server as two apps.** Lost: it would use the last free app slot for something one process can do.
4. **MCP tools that call the API's functions in-process,** with no HTTP. Lost: the retries, timeouts and idempotency keys would then have nothing to protect against, and those are the point of Phase 5.

## Decision

- **One app,** `sanad-mock-systems`, declared in `databricks.yml`. `mock_systems/app.py` serves the REST API and mounts the MCP server at `/mcp` in one process.
- **The MCP tools call the API over HTTP** on the same port, with a 5 s timeout, up to 3 attempts, and one idempotency key per create.
- **Who calls it:**
  - The deployed agent finds the app by name (`MOCK_MCP_APP`) and calls it with Databricks OAuth as its own service principal, which has `CAN_USE` on the app.
  - Locally, `MOCK_MCP_URL` points at a plain MCP server, which receives no Databricks token.
- **Approvals are default deny:** every tool except `get_*` reads pauses for approval.

Evidence, 2026-11-09:

| Test | Result |
|---|---|
| Local agent against the local mock | Credit note `CN-000002` drafted after approval, read back without approval, and a Teams post landed |
| Mock API stopped / MCP server stopped | HTTP 200 and a clear answer in both cases; the write was not tried again |
| The combined app run locally, with sync tools | Deadlock: 16.5 s, then "unavailable (ReadTimeout after 3 attempts)" |
| The same with async tools | Create in 0.04 s |
| Deployed app called over MCP with my Databricks token | 7 tools listed; the post returned `MSG-000001` |

## Consequences

- **The MCP tools must be async.** FastMCP runs a sync tool on the event loop, and in one process the tool's HTTP call to the API then waits on the loop it is blocking.
- **DNS-rebinding protection is off on Databricks Apps only.**
  - FastMCP accepts only `localhost` Host headers by default, and on Apps every request arrives through Databricks' authenticating proxy with the app's own host name.
  - The attack it guards against (a browser tricked into calling a local server) doesn't apply there. It stays on locally.
- **The mock's state is in memory,** so an app restart empties the ERP, ITSM, CRM and Teams.
- **The agent calls the mock as its service principal, not as the user.**
  - The mock can't tell who asked; approval is the human check.
  - The UC MCP-service route (option 2) could carry the user's identity, and that's the Phase 7 upgrade.
- **The idempotency key is per tool call.** A whole tool call replayed after a crash would get a new key; deriving the key from the agent's `tool_call_id` would close that gap.
