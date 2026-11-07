# governance

Grants, row filters, column masks and tags, all kept as SQL. The agent inherits everything here.

**Phase:** 2

## What goes here

- [setup.sql](setup.sql): `ops.user_regions`, the `ops.mask_pii` column mask, the `ops.region_filter` row filter, the grants and the tags. It implements [docs/access-matrix.md](../docs/access-matrix.md).
- [audit.sql](audit.sql): who read a `pii`-tagged table in the last 7 days, and how (SQL query or pipeline), from `system.access.table_lineage`.
- The mask and the filter are *attached* in the pipeline code, not here: `silver.contacts` in [silver.py](../pipelines/transformations/silver.py) and `gold.customer_360` in [gold.py](../pipelines/transformations/gold.py). The pipeline owns those tables' definitions.

## Run order

1. Create the groups `account_managers`, `ops_managers` and `it_support`. They must be **account** groups: UC grants and `is_account_group_member()` ignore workspace-local groups. `databricks groups create` and `groups-v2 create` both make workspace-local groups (`resourceType: WorkspaceGroup`, and `GRANT` fails with `PRINCIPAL_DOES_NOT_EXIST`). This one makes account groups from the workspace (Beta):
   ```bash
   databricks workspace-iam-v2 create-group-proxy --group-name account_managers --profile sanad
   databricks workspace-iam-v2 create-direct-group-member-proxy <group_id> <your user id> --profile sanad  # add a member
   ```
2. Run [setup.sql](setup.sql) in the SQL editor.
3. `databricks bundle deploy --profile sanad`, then `databricks bundle run sanad_medallion --profile sanad`. If `silver.contacts` refuses the new schema, run once with `--full-refresh silver.contacts` (bronze keeps every row, so nothing is lost).
4. Prove it (below), then run [audit.sql](audit.sql) a few minutes later.

## Proof

Free Edition has one user, so "two users" is one user in two roles. The agent's service principal becomes a real second identity in Phase 4.

```sql
SELECT region, count(*) FROM sanad.gold.customer_360 GROUP BY region;  -- query A
SELECT email, phone FROM sanad.silver.contacts LIMIT 3;                -- query B
```

Result on 2026-11-07 (the same two queries, the same workspace admin):

| You are in | Query A | Query B |
|---|---|---|
| no group | 0 rows | `***` |
| `account_managers` | Jeddah only (421) | real values |
| `account_managers` + `ops_managers` | all 5 regions (2,000) | real values |

A new membership took about 3.5 minutes to reach `is_account_group_member()`. Being a workspace admin exempts you from nothing.

## Done when

The same query returns different rows for two roles, and the audit query shows the reads.
