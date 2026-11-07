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
| `ai.chunks` | Phase 3 | Phase 3 | Phase 3 |
| `ai.*` functions (agent tools) | Phase 4 | Phase 4 | Phase 4 |
| `ops.*` | none | none | none |

Why:

- **Bronze and silver: nobody in the business.** They are raw or half-cleaned, and silver still has every region and the contacts' PII. Only the pipeline (running as its owner) and the data engineers read them. Business users read gold.
- **Account managers see their own customers only.** `customer_360` gets a row filter. `invoice_issues` is not granted to them at all, because it lists account names for every region and has no row filter (see the next section for why).
- **Delivery SLA is shared with account managers.** It has no customer names, only rates per region and carrier, and a manager in Jeddah needs to compare their region with the others.
- **IT support sees tickets only.** They have no business reason to see customers or invoices.
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

- The agent's service principal: a row for it is added in Phase 4, when it exists.
- Warehouse access (`CAN USE` on the SQL warehouse) is a workspace permission, not a UC grant. It is set in Phase 7 together with the app.
