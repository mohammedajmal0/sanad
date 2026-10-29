# Access matrix

Who can do what on which object in the `sanad` catalog. The agent inherits these permissions, so this table defines what the agent can show each user. The grants themselves live as SQL in [governance/](../governance/). Built in Phase 2.

Privileges to choose from: `USE CATALOG`, `USE SCHEMA`, `SELECT`, `MODIFY`, `EXECUTE` (functions), `READ VOLUME`, `WRITE VOLUME`. Write `none` where a group has no access.

TODO(human): fill every cell. Then add a row for the agent's service principal and any other objects you create.

| Object | `account_managers` | `ops_managers` | `it_support` |
|---|---|---|---|
| `bronze.*` | | | |
| `silver.*` | | | |
| `gold.customer_360` | | | |
| `gold.invoice_issues` | | | |
| `gold.delivery_sla_by_region` | | | |
| `gold.ticket_trends` | | | |
| `ai.chunks` | | | |
| `ai.*` functions (agent tools) | | | |
| `ops.*` | | | |

## Row filters and column masks

| Object | Rule | Applies to | Exempt groups |
|---|---|---|---|
| CRM contact `email`, `phone` | Column mask | TODO(human) | TODO(human) |
| `gold.customer_360` | Row filter: account managers see only their region | `account_managers` | TODO(human) |

## Tags

| Tag | Applied to |
|---|---|
| `pii` | TODO(human) |
| `confidential` | TODO(human) |
