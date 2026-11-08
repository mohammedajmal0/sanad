-- Phase 4: the Customer Service agent's tools, as Unity Catalog functions.
-- Run in the SQL editor (or any SQL warehouse) after governance/setup.sql. Safe to re-run.
-- The agent binds them in agent/agent.toml with auth = "user": each call runs as the
-- person asking, so the Phase 2 row filter decides what they see (ADR 0004).
-- Every function reads through gold.customer_360, the row-filtered table: a caller who
-- may not see an account gets 0 rows, not an error that confirms the account exists.
-- The COMMENTs are the tool descriptions the model reads. Written by Claude at my
-- request on 2026-11-08; I must be able to defend them.

-- 1. Name -> account. The agent's first step for any customer question.
CREATE OR REPLACE FUNCTION sanad.ai.get_customer_summary(
  customer_name STRING COMMENT 'All or part of the customer name, e.g. "Al-Faris"'
)
RETURNS TABLE (
  account_id STRING, account_name STRING, region STRING, segment STRING,
  orders BIGINT, order_total_sar DECIMAL(22,2), last_order_date DATE, flagged_invoices BIGINT
)
COMMENT 'Find customer accounts by name. Returns up to 5 matches with the account_id, region, segment, number of orders, order total in SAR, last order date, and how many invoices finance flagged. Call this first to turn a customer name into an account_id. No rows means the name is unknown or the account is outside your region.'
RETURN
  SELECT account_id, account_name, region, segment,
         orders, order_total_sar, last_order_date, invoice_issues
  FROM sanad.gold.customer_360
  WHERE account_name ILIKE concat('%', customer_name, '%')
  ORDER BY account_name
  LIMIT 5;

-- 2. Account -> invoices, each with the reason finance would check it.
CREATE OR REPLACE FUNCTION sanad.ai.get_invoices(
  account_id STRING COMMENT 'The account_id from get_customer_summary, e.g. "ACC-00001"'
)
RETURNS TABLE (
  invoice_id STRING, order_id STRING, invoice_date DATE, amount_sar DECIMAL(12,2),
  issue_type STRING, invoices_for_order BIGINT
)
COMMENT 'List one customer''s invoices, newest first (up to 50): invoice_id, order_id, invoice_date, amount in SAR, and issue_type. issue_type is "duplicate" (another invoice bills the same order_id), "non_positive_amount", "future_dated", or "none". Use it for billing questions such as being invoiced twice. Needs an account_id from get_customer_summary.'
RETURN
  SELECT i.invoice_id, i.order_id, i.invoice_date, i.amount_sar,
         coalesce(x.issue_type, 'none'),
         count(*) OVER (PARTITION BY i.order_id)
  FROM sanad.silver.invoices i
  LEFT JOIN sanad.gold.invoice_issues x ON x.invoice_id = i.invoice_id
  WHERE i.account_id = get_invoices.account_id
    AND i.account_id IN (SELECT c.account_id FROM sanad.gold.customer_360 c)  -- the region guard
  ORDER BY i.invoice_date DESC
  LIMIT 50;

-- 3. Order -> delivery status. Same late rule as gold.delivery_sla_by_region:
--    late = delivered after the promised date.
CREATE OR REPLACE FUNCTION sanad.ai.get_shipment_status(
  order_id STRING COMMENT 'The order_id, e.g. "ORD-027711" (get_invoices shows each invoice''s order)'
)
RETURNS TABLE (
  shipment_id STRING, order_id STRING, carrier STRING, ship_date DATE, promised_date DATE,
  delivered_date DATE, status STRING, days_late INT, as_of_date DATE
)
COMMENT 'Delivery status of the shipments for one order: carrier, ship_date, promised_date, delivered_date (empty while in transit), status, and days_late counted up to as_of_date. status is "delivered on time", "delivered late", "in transit", or "in transit, past promised date". Use it for questions about late or missing deliveries.'
RETURN
  SELECT s.shipment_id, s.order_id, s.carrier, s.ship_date, s.promised_date, s.delivered_date,
         CASE WHEN s.delivered_date > s.promised_date THEN 'delivered late'
              WHEN s.delivered_date IS NOT NULL THEN 'delivered on time'
              WHEN current_date() > s.promised_date THEN 'in transit, past promised date'
              ELSE 'in transit' END,
         greatest(datediff(coalesce(s.delivered_date, current_date()), s.promised_date), 0),
         current_date()
  FROM sanad.silver.shipments s
  JOIN sanad.silver.orders o ON o.order_id = s.order_id
  WHERE s.order_id = get_shipment_status.order_id
    -- the region guard
    AND o.account_id IN (SELECT c.account_id FROM sanad.gold.customer_360 c);

-- 4. Grants: only the Customer Service agent's users. No table grants are added:
--    account managers still can't SELECT silver or gold.invoice_issues directly.
GRANT USE SCHEMA ON SCHEMA sanad.ai TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.get_customer_summary TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.get_invoices         TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.get_shipment_status  TO `account_managers`;

-- 5. Checks (as an admin or ops manager, who sees every region):
--    expect 1 row, ACC-00001 Al-Faris Trading, Abha, flagged_invoices = 2
SELECT * FROM sanad.ai.get_customer_summary('al-faris');
--    expect 2 rows: INV-027711 and INV-050001, both ORD-027711, 1440.71
SELECT * FROM sanad.ai.get_invoices('ACC-00001') WHERE issue_type = 'duplicate';
--    expect 1 row for ORD-027711 with a status and days_late
SELECT * FROM sanad.ai.get_shipment_status('ORD-027711');
