-- Phase 2 governance: docs/access-matrix.md as SQL. Run it in the SQL editor
-- AFTER the three groups exist (governance/README.md, step 1), and BEFORE the
-- pipeline update that attaches the mask and the row filter (they must exist first).
-- Safe to re-run: CREATE OR REPLACE, and GRANT / SET TAG do nothing if already set.
-- Drafted by Claude at my request on 2026-11-07.

-- 1. Who manages which region. Seeds whoever runs this script as the Jeddah
--    account manager, so no email address is written into git.
--    In a real company this is loaded from the CRM's account-owner data.
CREATE OR REPLACE TABLE sanad.ops.user_regions (
  user_email STRING NOT NULL COMMENT 'current_user() of the account manager',
  region     STRING NOT NULL
) COMMENT 'Which regions each account manager may see (read by ops.region_filter)';

INSERT INTO sanad.ops.user_regions SELECT current_user(), 'Jeddah';

-- 2. Column mask for PII. Runs on every read of a masked column: the reader gets
--    the real value or ***. Attached in pipelines/transformations/silver.py.
CREATE OR REPLACE FUNCTION sanad.ops.mask_pii(value STRING)
RETURNS STRING
COMMENT 'Column mask: the real value for account managers, *** for everyone else'
RETURN CASE WHEN is_account_group_member('account_managers') THEN value ELSE '***' END;

-- 3. Row filter by region. Runs on every row: TRUE keeps it, FALSE hides it.
--    Attached in pipelines/transformations/gold.py (customer_360 only).
--    The parameter is row_region, not region: inside the subquery an unqualified
--    `region` would mean u.region, and `u.region = region` would always be true.
CREATE OR REPLACE FUNCTION sanad.ops.region_filter(row_region STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: ops managers see every region, account managers only their own'
RETURN is_account_group_member('ops_managers')
    OR (is_account_group_member('account_managers')
        AND EXISTS (SELECT 1 FROM sanad.ops.user_regions u
                    WHERE u.user_email = current_user() AND u.region = row_region));

-- 4. Grants: the doors (catalog, schema), then the tables. Nothing on bronze, silver or ops.
GRANT USE CATALOG ON CATALOG sanad TO `account_managers`;
GRANT USE CATALOG ON CATALOG sanad TO `ops_managers`;
GRANT USE CATALOG ON CATALOG sanad TO `it_support`;
GRANT USE SCHEMA ON SCHEMA sanad.gold TO `account_managers`;
GRANT USE SCHEMA ON SCHEMA sanad.gold TO `ops_managers`;
GRANT USE SCHEMA ON SCHEMA sanad.gold TO `it_support`;

GRANT SELECT ON TABLE sanad.gold.customer_360          TO `account_managers`;
GRANT SELECT ON TABLE sanad.gold.delivery_sla_by_region TO `account_managers`;

GRANT SELECT ON TABLE sanad.gold.customer_360          TO `ops_managers`;
GRANT SELECT ON TABLE sanad.gold.invoice_issues        TO `ops_managers`;
GRANT SELECT ON TABLE sanad.gold.delivery_sla_by_region TO `ops_managers`;
GRANT SELECT ON TABLE sanad.gold.ticket_trends         TO `ops_managers`;

GRANT SELECT ON TABLE sanad.gold.ticket_trends         TO `it_support`;

-- 5. Tags: labels that say what kind of data a column or table holds.
--    governance/audit.sql finds PII tables through the pii tag.
SET TAG ON COLUMN sanad.bronze.crm_contacts.full_name pii;
SET TAG ON COLUMN sanad.bronze.crm_contacts.email     pii;
SET TAG ON COLUMN sanad.bronze.crm_contacts.phone     pii;
SET TAG ON COLUMN sanad.silver.contacts.full_name     pii;
SET TAG ON COLUMN sanad.silver.contacts.email         pii;
SET TAG ON COLUMN sanad.silver.contacts.phone         pii;

SET TAG ON TABLE sanad.silver.invoices     confidential;
SET TAG ON TABLE sanad.gold.invoice_issues confidential;
SET TAG ON TABLE sanad.gold.customer_360   confidential;
