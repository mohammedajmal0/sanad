# governance

Grants, row filters, column masks and tags, all kept as SQL. The agent inherits everything here.

**Phase:** 2

## What goes here

- Groups `account_managers`, `ops_managers`, `it_support`, and their grants.
- A column mask on contact email and phone.
- A row filter so account managers see only their region.
- `pii` and `confidential` tags.
- Audit queries on system tables showing who read PII this week.

## You write

- TODO(human): the access matrix in [docs/access-matrix.md](../docs/access-matrix.md), then the grants and masks that implement it.

## Done when

The same query returns different rows for two users, and the audit query shows both.
