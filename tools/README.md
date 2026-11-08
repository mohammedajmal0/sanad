# tools

Unity Catalog functions the agents call as tools. They run under UC permissions, so the agent never touches tables directly.

**Phase:** 4

## Run

1. Run [functions.sql](functions.sql) in the SQL editor, after [governance/setup.sql](../governance/setup.sql). It creates the functions, grants `EXECUTE` to `account_managers`, and ends with three checks.
2. The agent binds them in [agent/agent.toml](../agent/agent.toml) with `auth = "user"`: `agentbricks tools add uc-function sanad.ai.<name> --auth user`.
3. The workspace needs the **managed MCP servers** preview switched on (profile menu → Previews). Agent Bricks reaches UC functions through Databricks' managed MCP endpoint (`/api/2.0/mcp/functions/<catalog>/<schema>/<function>`). Without the preview, every request fails with "Could not discover configured MCP tools".

## The Customer Service tools

| Function (`sanad.ai.`) | Input | Returns | Reads |
|---|---|---|---|
| `get_customer_summary` | part of a customer name | up to 5 accounts: id, region, segment, orders, order total (SAR), last order date, flagged invoices | `gold.customer_360` |
| `get_invoices` | `account_id` | up to 50 invoices, flagged first, then newest, each with `issue_type` (`duplicate`, `non_positive_amount`, `future_dated`, `none`) | `silver.invoices`, `gold.invoice_issues` |
| `get_shipment_status` | `order_id` | shipments with dates, `status` and `days_late` as of `as_of_date` | `silver.shipments`, `silver.orders` |
| `search_policies` | the question | up to 5 whole documents (`doc_id`, `title`, type, department, effective date, text) for the caller's audience | `ai.chunks_index` through `vector_search()` |

- **The function and parameter `COMMENT`s are the tool descriptions the model reads.** Written by Claude at my request; I must be able to defend them.
- **Every data function filters its accounts through `gold.customer_360`,** the row-filtered table, so the Phase 2 region filter guards all three data tools.
- **`search_policies` runs the ADR 0003 query.** It takes `whole` cards from a hybrid search. `vector_search()` has no filter argument, so the function fetches the top 100 and filters afterwards. The 40 eval questions, run through the function on 2026-11-08 as a non-IT user: all 29 visible questions hit the top 5 (recall@5 1.00, MRR 0.90), and the 11 IT-only questions returned nothing, as intended.
- **`get_invoices` lists flagged invoices first.** With newest-first ordering, the model once copied the wrong invoice id out of a 24-row list.
- **Every output carries its unit:** `_sar`, dates, `as_of_date`.

## Proof: whose rights does a tool run with?

Tested on 2026-11-08 as the agent's service principal. It had `USE CATALOG`, `USE SCHEMA` on `sanad.ai` and `EXECUTE` on the three functions, but no `SELECT` on any table, no group and no region. That is an account manager's access minus the region.

| Query | Result |
|---|---|
| `SELECT … FROM gold.customer_360` / `silver.invoices` | `INSUFFICIENT_PERMISSIONS` |
| `get_customer_summary('al-faris')`, `get_invoices('ACC-00001')`, `get_shipment_status('ORD-027711')` | 0 rows, no error |

What this shows:
- **A function reads its tables with its owner's rights.** The caller needs only `EXECUTE`, so account managers get invoice details without `SELECT` on `silver` or `invoice_issues`.
- **The row filter inside the function still checks the caller.** Run as the owner (an ops manager), the same calls return Al-Faris and its two duplicates.
- **A caller who may not see an account gets 0 rows,** exactly as if the account didn't exist.

**`vector_search()` is the exception:** it calls AI Search as the caller, so the service principal got `403` from `search_policies` even inside the function. That is why every business group has `SELECT` on the index (see the [access matrix](../docs/access-matrix.md)).

The positive case wasn't run. It would add the service principal to `account_managers` with region Abha (expect 2 rows), and auto mode blocked that grant.

## Done when

Gate A: the agent finds the seeded duplicate invoice, cites the refund policy, and the trace shows every tool call.
