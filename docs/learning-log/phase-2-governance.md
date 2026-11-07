# Phase 2: Governance: masks, row filters, tags, lineage, audit

**Goal:** control who sees what, and prove it.

**Done when:** PII columns are masked for non-admins, a row filter limits a regional user to their region, tables are tagged, and an audit query on system tables shows who read what.

## Read first

- [Row filters and column masks](https://docs.databricks.com/aws/en/tables/row-and-column-filters)
- [Audit log system table](https://docs.databricks.com/aws/en/admin/system-tables/audit-logs)

## Concepts to learn

- Grant (which tables you can open) versus row filter (which rows) versus column mask (what a cell shows).
- Account groups versus workspace-local groups.
- Why a filter or mask on an upstream table changes what the pipeline writes downstream.
- Tags as labels that drive audits and policies.

## Entries

### 2026-11-07: Access matrix, groups, PII mask, region row filter, tags, audit

**What we built:** the [access matrix](../access-matrix.md); [governance/setup.sql](../../governance/setup.sql) with `ops.user_regions`, the `ops.mask_pii` column mask, the `ops.region_filter` row filter, 13 grants and 9 tags; [governance/audit.sql](../../governance/audit.sql). The mask is attached to `silver.contacts` in [silver.py](../../pipelines/transformations/silver.py), and the row filter to `gold.customer_360` in [gold.py](../../pipelines/transformations/gold.py). Three account groups: `account_managers`, `ops_managers`, `it_support`. Proof with one user in three roles: no group → 0 rows and `***`; `account_managers` → Jeddah only (421 accounts) and real emails; plus `ops_managers` → all 5 regions (2,000). The audit query showed my SQL read of `silver.contacts` and the pipeline copying it into `customer_360`. The access matrix, `mask_pii` and `region_filter` were drafted by Claude at my request; I must be able to defend them.

**Key concepts:**
- Three locks: a grant is the door to a table, a row filter decides which rows, a mask decides what a cell shows. A row filter protects only the table it's attached to.
- A pipeline owns its tables' definitions, so masks and filters are declared in the pipeline code (`schema="... MASK fn"`, `row_filter="ROW FILTER fn ON (col)"`), not with `ALTER TABLE`.
- Never filter or mask a table that the pipeline reads further downstream: the pipeline reads as its owner, so the rule would change what gets written. Bronze PII is protected by grants only.
- Account groups vs workspace-local groups: UC grants and `is_account_group_member()` only see account groups. `databricks groups create` and `groups-v2 create` made workspace-local ones; `workspace-iam-v2 create-group-proxy` makes account groups from the workspace.
- Filter and mask functions run with their owner's rights, but `current_user()` and `is_account_group_member()` check the reader. That's why readers need no access to `ops.user_regions`.
- Being a workspace admin exempts you from nothing: I saw 0 rows until I joined a group. A new membership took about 3.5 minutes to apply.
- In a SQL function, a parameter with the same name as a column in a subquery loses: `u.region = region` compares the column with itself. Hence the name `row_region`.
- Tags drive the audit: the query finds PII tables through the `pii` tag instead of a hard-coded list.
- Audit source: `system.access.table_lineage` logs one row per read under the public table name. `system.access.audit` logs pipeline-table reads under internal `__materialization_` names and skips reads that reuse a credential.

**Mistakes:**
- My check answer said "it depends on access" but didn't say *where* the leak is: `silver.accounts` and `gold.invoice_issues` show every region. That's why account managers get no silver and no `invoice_issues`.
- Claude assumed `groups-v2 create` made account groups. Testing one `GRANT` (`PRINCIPAL_DOES_NOT_EXIST`) before building on it caught this; the groups were deleted and recreated as account groups.
- The first audit query used `system.access.audit` and missed my own reads of pipeline tables. Switched to `table_lineage`.

**Interview questions:**
1. A row filter limits an account manager to their region in one table. Name two other ways they could still see other regions' data, and how you close each.
2. Why would you not put a column mask on the bronze table that holds the raw PII, and what protects it instead?
3. Your PII audit report shows nobody read a table this week, but you know someone did. What could explain it?
