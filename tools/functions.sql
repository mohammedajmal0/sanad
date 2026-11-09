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
COMMENT 'List one customer''s invoices (up to 50), flagged ones first, then newest first: invoice_id, order_id, invoice_date, amount in SAR, and issue_type. issue_type is "duplicate" (another invoice bills the same order_id), "non_positive_amount", "future_dated", or "none". Use it for billing questions such as being invoiced twice. Needs an account_id from get_customer_summary.'
RETURN
  SELECT i.invoice_id, i.order_id, i.invoice_date, i.amount_sar,
         coalesce(x.issue_type, 'none'),
         count(*) OVER (PARTITION BY i.order_id)
  FROM sanad.silver.invoices i
  LEFT JOIN sanad.gold.invoice_issues x ON x.invoice_id = i.invoice_id
  WHERE i.account_id = get_invoices.account_id
    AND i.account_id IN (SELECT c.account_id FROM sanad.gold.customer_360 c)  -- the region guard
  -- flagged invoices first: the model once copied the wrong id out of a long list
  ORDER BY x.issue_type IS NULL, i.invoice_date DESC
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

-- 4. Question -> policy and KB passages, with the document to cite.
--    AI Search has no row security, so the audience filter lives here, set from the
--    caller's groups, never from the model: policies ('all') for everyone, KB articles
--    for the caller's departments. No group means policies only.
--    vector_search() has no filter argument (checked 2026-11-08), so it fetches the top 100
--    of the whole index (all three strategies) and filters after; ADR 0003 picked 'whole'.
CREATE OR REPLACE FUNCTION sanad.ai.search_policies(
  question STRING COMMENT 'The question in plain words, e.g. "How soon must we tell a customer about a duplicate invoice?"'
)
RETURNS TABLE (
  doc_id STRING, title STRING, doc_type STRING, department STRING, effective_date STRING,
  text STRING
)
COMMENT 'Search Najm''s policies and knowledge-base articles. Returns up to 5 whole documents, best match first: doc_id and title (cite them in the answer), doc_type (policy or kb), department, effective_date, and the full text. Use it for any question about rules, deadlines, approvals, refunds, procedures or how-to steps. Only state rules that appear in the returned text.'
RETURN
  SELECT doc_id, title, doc_type, department, CAST(effective_date AS STRING), chunk_to_retrieve
  FROM vector_search(index => 'sanad.ai.chunks_index', query_text => question,
                     query_type => 'HYBRID', num_results => 100)
  WHERE strategy = 'whole'
    AND (audience = 'all'
      OR (audience IN ('customer_service', 'finance', 'logistics')
          AND is_account_group_member('account_managers'))
      OR (audience = 'logistics' AND is_account_group_member('ops_managers'))
      OR (audience = 'it' AND is_account_group_member('it_support')))
  ORDER BY search_score DESC
  LIMIT 5;

-- 5. Grants: the data tools to the Customer Service agent's users only. No table grants are added:
--    account managers still can't SELECT silver or gold.invoice_issues directly.
GRANT USE SCHEMA ON SCHEMA sanad.ai TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.get_customer_summary TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.get_invoices         TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.get_shipment_status  TO `account_managers`;
-- Policy search: vector_search() calls AI Search with the CALLER's identity (tested 2026-11-08:
-- 403 without SELECT on the index), unlike the table reads above, which use the owner's rights.
-- So each group needs SELECT on the index (chosen by me on 2026-11-08). The audience filter
-- then picks relevant documents; it is not a security boundary. Confidential documents
-- would go in a separate index with its own grants.
GRANT SELECT ON TABLE sanad.ai.chunks_index TO `account_managers`;
GRANT SELECT ON TABLE sanad.ai.chunks_index TO `ops_managers`;
GRANT SELECT ON TABLE sanad.ai.chunks_index TO `it_support`;
GRANT USE SCHEMA ON SCHEMA sanad.ai TO `ops_managers`;
GRANT USE SCHEMA ON SCHEMA sanad.ai TO `it_support`;
GRANT EXECUTE ON FUNCTION sanad.ai.search_policies TO `account_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.search_policies TO `ops_managers`;
GRANT EXECUTE ON FUNCTION sanad.ai.search_policies TO `it_support`;

-- 6. Checks (as an admin or ops manager, who sees every region):
--    expect 1 row, ACC-00001 Al-Faris Trading, Abha, flagged_invoices = 2
SELECT * FROM sanad.ai.get_customer_summary('al-faris');
--    expect 2 rows: INV-027711 and INV-050001, both ORD-027711, 1440.71
SELECT * FROM sanad.ai.get_invoices('ACC-00001') WHERE issue_type = 'duplicate';
--    expect 1 row for ORD-027711 with a status and days_late
SELECT * FROM sanad.ai.get_shipment_status('ORD-027711');
--    expect fin-duplicate-invoices in the top 5 (rank 4 on 2026-11-08)
SELECT doc_id, title FROM sanad.ai.search_policies('We billed a customer twice. How soon must we tell them?');

-- 7. Service Desk (2026-11-09): one IT category -> its busiest recent days, next to the category's
--    typical day. Several days far above typical mean an incident many users share. Tickets carry
--    no PII and no region, so there is no guard; only it_support gets EXECUTE. The window is
--    relative to today, like "last quarter" in the Genie agent. Written by Claude at my request.
CREATE OR REPLACE FUNCTION sanad.ai.get_ticket_trend(
  category_name STRING COMMENT 'One IT ticket category: "VPN", "Email", "Laptop", "Password reset", "ERP access" or "Printer"'
)
RETURNS TABLE (
  created_date DATE, tickets BIGINT, high_priority BIGINT, open_tickets BIGINT,
  typical_per_day DOUBLE, example_ticket_id STRING
)
COMMENT 'Busiest days of the last 60 days for one IT ticket category, busiest first (up to 15 days): created_date, tickets, high_priority, open_tickets, typical_per_day (the category''s average day over the 90 days before that) and an example_ticket_id to cite. Several days far above typical_per_day mean an incident that many users share. Use it when someone reports an IT problem, to see whether it is part of an incident, then call search_policies for the knowledge-base fix.'
RETURN
  WITH t AS (
    SELECT * FROM sanad.silver.tickets
    WHERE lower(category) = lower(get_ticket_trend.category_name)
  ),
  typical AS (
    SELECT count(*) / 90.0 AS per_day FROM t
    WHERE created_at >= date_sub(current_date(), 150) AND created_at < date_sub(current_date(), 60)
  )
  SELECT to_date(t.created_at), count(*), count_if(t.priority = 'high'),
         count_if(t.status = 'open'), round(any_value(typical.per_day), 1), min(t.ticket_id)
  FROM t CROSS JOIN typical
  WHERE t.created_at >= date_sub(current_date(), 60)
  GROUP BY to_date(t.created_at)
  ORDER BY count(*) DESC, to_date(t.created_at) DESC
  LIMIT 15;

GRANT EXECUTE ON FUNCTION sanad.ai.get_ticket_trend TO `it_support`;

--    expect the VPN incident first: 2026-10-19 with 30 tickets, typical_per_day about 2
SELECT * FROM sanad.ai.get_ticket_trend('vpn');
