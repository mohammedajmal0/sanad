# Access matrix

Who can do what on which object in the `sanad` catalog. The agent inherits these permissions, so this table defines what the agent can show each user. The grants themselves live as SQL in [governance/setup.sql](../governance/setup.sql). Built in Phase 2; drafted by Claude at my request on 2026-11-07, and I must be able to defend every cell.

Every group also gets `USE CATALOG` on `sanad` and `USE SCHEMA` on `gold`: the two "doors" before any table. `none` means no grant at all.

| Object | `account_managers` | `ops_managers` | `it_support` |
|---|---|---|---|
| `bronze.*` | none | none | none |
| `silver.*` | none | none | none |
| `gold.customer_360` | `SELECT` (own region only, row filter) | `SELECT` (all regions) | none |
| `gold.invoice_issues` | none (the count per account is in `customer_360`) | `SELECT` | none |
| `gold.delivery_sla_by_region` | `SELECT` | `SELECT` | none |
| `gold.ticket_trends` | none | `SELECT` | `SELECT` |
| `ai.chunks` | none | none | none |
| `ai.chunks_index` | `SELECT` (needed by `search_policies`) | `SELECT` | `SELECT` |
| `ai.get_customer_summary`, `ai.get_invoices`, `ai.get_shipment_status` (agent tools) | `EXECUTE` (own region only, through `customer_360`) | none (their specialist comes later in Phase 4) | none |
| `ai.search_policies` (agent tool) | `EXECUTE` | `EXECUTE` | `EXECUTE` |
| `ai.get_ticket_trend` (Service Desk tool) | none | none | `EXECUTE` (tickets have no PII and no region) |
| `ops.*` | none | none | none |
| `prompts.*` (MLflow Prompt Registry) | none | none | none |
| Genie agent *Sanad Ops Analytics* (workspace object, in [databricks.yml](../databricks.yml)) | none | `CAN_RUN` | none |

Why:

- **Bronze and silver: nobody in the business.** They are raw or half-cleaned, and silver still has every region and the contacts' PII. Only the pipeline (running as its owner) and the data engineers read them. Business users read gold.
- **Account managers see their own customers only.** `customer_360` gets a row filter. `invoice_issues` is not granted to them at all, because it lists account names for every region and has no row filter (see the next section for why).
- **Delivery SLA is shared with account managers.** It has no customer names, only rates per region and carrier, and a manager in Jeddah needs to compare their region with the others.
- **The Genie agent is for ops managers only (2026-11-09).** `CAN_RUN` only lets someone ask. Genie runs the SQL as the person asking, so their table grants still decide which rows they see. Account managers could read the table, but the Ops Analytics specialist is for ops managers; the supervisor task revisits who can reach which specialist. They will also need `CAN USE` on the warehouse (Phase 7, see below). Drafted by Claude at my request.
- **IT support sees tickets only.** They have no business reason to see customers or invoices.
- **Every business group can search the documents.** The agent's `search_policies` uses `vector_search()`, which calls AI Search with the **caller's** identity (`403` without `SELECT` on the index, tested 2026-11-08). The other tools read tables with their owner's rights; this one doesn't. So the three groups get `SELECT` on the index (chosen by me on 2026-11-08), and a user could also query it directly. The `audience` filter inside the function still gives each person all policies plus their own departments' KB articles (`account_managers`: customer service, finance, logistics; `ops_managers`: logistics; `it_support`: IT; anyone else: policies only). That filter is for relevance, not security. Acceptable here because the corpus is internal policies and how-tos with no customer data or PII. **Rule: confidential documents go in a separate index with its own grants.** A filter is not a security boundary. The `audience` mapping was drafted by Claude at my request.
- **Account managers read invoices and shipments only through the agent's tools.** The three functions read `silver` and `gold.invoice_issues` with their owner's rights, so `EXECUTE` is enough, and no table grant is added. Each function keeps only accounts the caller can see in `customer_360`, so the region filter still applies. The agent calls them as the person asking (`auth = "user"`, [ADR 0004](adr/0004-run-tools-as-the-asking-user.md)). Proof in [tools/README.md](../tools/README.md). Drafted by Claude at my request on 2026-11-08.
- **`ops.*` holds the access rules themselves** (`user_regions`, the mask and filter functions). Nobody needs to query them: a row filter or mask runs with its owner's rights, so readers don't need `SELECT` on `user_regions` or `EXECUTE` on the functions.

## Row filters and column masks

| Object | Rule | Applies to | Exempt groups |
|---|---|---|---|
| `silver.contacts` `email`, `phone` | Column mask `ops.mask_pii`: the real value or `***` | everyone, data engineers included | `account_managers` (they own the customer relationship) |
| `gold.customer_360` | Row filter `ops.region_filter`: only the region(s) in `ops.user_regions` for the reader | `account_managers`; everyone else sees no rows | `ops_managers` (see all regions) |

**Rule: never put a filter or mask on a table the pipeline reads further downstream.** The pipeline reads its tables as its owner, so a filter there would quietly decide what gold contains, depending on who runs the pipeline. A mask on `bronze.crm_contacts` would save `***` into silver for good. So:

- `bronze.*` holds raw PII and is protected by grants only (nobody in the business can open it).
- `gold.invoice_issues` is read by `customer_360`, so it gets no row filter; account managers simply don't get it.
- The mask is on `silver.contacts`. `customer_360` only counts contacts, so a masked email doesn't change any number.

## Tags

| Tag | Applied to |
|---|---|
| `pii` | `full_name`, `email` and `phone` in `bronze.crm_contacts` and `silver.contacts` |
| `confidential` | `silver.invoices`, `gold.invoice_issues`, `gold.customer_360` (money and customer details) |

The audit query in [governance/audit.sql](../governance/audit.sql) finds PII tables through the `pii` tag, so a newly tagged table is audited without changing the query.

## Not yet covered

- **Memory and sessions (2026-11-09):**
  - Deploy gives the app's service principal access to the `sanad-memory` and `sanad-sessions` stores. These are Agent Bricks stores, not Unity Catalog objects, so row filters and masks don't apply to them.
  - The actor partitions inside a store are not a security boundary: the app can read every user's memories.
  - So the supervisor prompt keeps memory to the user's own preferences and context, never customer, invoice, ticket or delivery data (tested: it refused to store an invoice id and amount).
  - Drafted by Claude at my request.
- **The agent's service principal (`agent-bricks-sanad-cs`) has rights only in `sanad.prompts`.** `agentbricks deploy` gives it `USE CATALOG` on `sanad`, plus `USE SCHEMA`, `EXECUTE`, `CREATE FUNCTION` and `MANAGE` on `sanad.prompts`, so it can load the system prompt. That is why prompts get their own schema: `MANAGE` on `sanad.ai` would let the agent change grants on the index and the tools. All tools, including policy search, run as the signed-in user, so it has nothing in `sanad.ai`. It was used once as a test identity on 2026-11-08, and its test grants were revoked; a leftover `CAN USE` on the warehouse gives it no data.
- Warehouse access (`CAN USE` on the SQL warehouse) is a workspace permission, not a UC grant. It is set in Phase 7 together with the app.
