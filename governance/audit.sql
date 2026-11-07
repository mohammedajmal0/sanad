-- Who read a PII table in the last 7 days, how, and when.
-- PII tables are found through the `pii` column tag (governance/setup.sql, step 5),
-- so a newly tagged table is audited without changing this query.
--
-- Source: system.access.table_lineage, one row per read under the public table name.
-- Not system.access.audit: a read of a pipeline table is logged there under an
-- internal __materialization_ name, and a reused storage credential logs no new
-- event, so many reads never show up. Both system tables run minutes behind.
WITH pii_tables AS (
  SELECT DISTINCT concat_ws('.', catalog_name, schema_name, table_name) AS table_name
  FROM sanad.information_schema.column_tags
  WHERE tag_name = 'pii'
)
SELECT
  l.created_by AS who,
  l.source_table_full_name AS pii_table,
  coalesce(l.entity_type, 'SQL query') AS how,  -- PIPELINE, NOTEBOOK, DASHBOARD, JOB...
  l.target_table_full_name AS copied_into,      -- set when the read fed another table
  count(*) AS reads,
  min(l.event_time) AS first_read,
  max(l.event_time) AS last_read
FROM system.access.table_lineage AS l
JOIN pii_tables AS p ON l.source_table_full_name = p.table_name
WHERE l.event_date >= date_sub(current_date(), 7)
GROUP BY ALL
ORDER BY last_read DESC;
