# 0004: Run tool calls as the person asking, not as the agent

- **Status:** Accepted
- **Date:** 2026-11-08
- **Phase:** 4

## Context

The Customer Service agent reads customers, invoices and shipments through three Unity Catalog functions ([tools/functions.sql](../../tools/functions.sql)). Agent Bricks reaches them through Databricks' managed MCP servers (a Public Preview, switched on for this workspace on 2026-11-08). Each `[[tools]]` binding in `agent.toml` runs as one of two identities:
- `auth = "user"`: the signed-in person, through their forwarded token;
- `auth = "app"`: the app's service principal.

Phase 2's protections key on the caller:
- the region row filter on `gold.customer_360` checks `is_account_group_member()` and `current_user()`;
- the PII mask checks group membership;
- the [access matrix](../access-matrix.md) promises that the agent shows each user only what they could see themselves.

Constraints:
- Free Edition has one human user, so the service principal is the only second identity for testing.
- The docs don't say whether a SQL function reads its tables with the owner's rights or the caller's, or whom the row filter checks inside a function.

## Options

1. **The person asking (`auth = "user"`), with functions that filter through `customer_360`.** Won; see Decision.
2. **The app's service principal (`auth = "app"`).** Lost. The service principal is in no group, so the row filter shows it nothing. Making it work would mean one of two bad choices:
   - put it in `ops_managers`, and every user would see every region through the agent;
   - pass the user's region as a parameter, and the model, which fills parameters, could claim any region.
3. **Python tools that query tables over a SQL warehouse with their own filtering.** Lost. It copies the governance rules into app code, where they can drift from Phase 2's, and it needs the service principal to have `SELECT` on silver.

## Decision

Option 1. The three functions are bound with `auth = "user"`, and each keeps only accounts the caller can see in `gold.customer_360`.

Evidence, 2026-11-08:

| Test | Result |
|---|---|
| Service principal with `EXECUTE` on the functions but no table grants: direct `SELECT` on `customer_360` or `silver.invoices` | `INSUFFICIENT_PERMISSIONS` |
| Same service principal, no group, no region: `get_invoices('ACC-00001')` and the other two | 0 rows, no error |
| Owner (ops manager): `get_invoices('ACC-00001')` | Al-Faris's invoices, with the two duplicates of `ORD-027711` |
| Deployed agent, asked by me: "Why was Al-Faris Trading invoiced twice in September?" | Called all three tools and named `INV-027711` and `INV-050001` |

The service principal still held its test grants during the deployed run. Had the tools run as the service principal, the deployed run would have returned 0 rows, so they ran as me.

What the tests show: a function reads its tables with its owner's rights, but the row filter inside it checks the caller. So `EXECUTE` alone gives an account manager invoice details for their own region and nothing else.

Restated by Claude at my request: the agent should never see more than the person talking to it. If the agent used its own identity, it would either see nothing or see everything, and we would need a second permission system to cut it back down. Running each tool as the person asking means Phase 2's filter does the cutting, the same way it does in the SQL editor. The functions add one thing: they can read the detailed tables for you, but only for accounts you are already allowed to see.

## Consequences

- One permission system. A new tool is a new function that filters through `customer_360`, plus an `EXECUTE` grant. No table grants change.
- A customer outside your region looks like "no match". The system prompt must word that honestly: "not found, or not in your region".
- It depends on two previews:
  - managed MCP servers (a workspace preview);
  - Apps user authorization, with the `mcp.functions` scope, which `agentbricks deploy --allow-user-scope-update` added.
  After a scope change, users may need to sign in and consent again.
- Work done on a user's behalf can't be resumed automatically after a crash, because no new user token arrives (`MCP_USER_AUTH_RECOVERY_UNSUPPORTED` in the Agent Bricks contract). An approval must be resumed by the same user.
- **The functions run with their owner's rights, so the owner's access is their ceiling.** Today the owner is my personal account. Before production (Phase 7), give the functions to a group or a deployment service principal that has only the tables they read.
- **Exception: `vector_search()` runs as the caller even inside a function** (`403` for the service principal without `SELECT` on the index, 2026-11-08). So `search_policies` needs index `SELECT` for every business group, and its `audience` filter is for relevance, not security ([access matrix](../access-matrix.md)). Confidential documents would need their own index.
- Not tested: the positive case for an account manager. The service principal as an Abha account manager should get 2 rows, and as a Riyadh one 0. Adding it to `account_managers` was blocked as a permission grant; run it when a second human user exists.
