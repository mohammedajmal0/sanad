# pipelines

Lakeflow Spark Declarative Pipelines (formerly DLT): Auto Loader bronze, cleaned silver, business gold.

**Phase:** 1

## What goes here

- Bronze: Auto Loader ingestion of CRM and ERP batches and the ITSM ticket stream.
- Silver: cleaned, conformed tables with expectations that warn, drop or fail.
- Gold: `customer_360`, `invoice_issues`, `delivery_sla_by_region`, `ticket_trends`.
- A job, `sanad_ingest`, that runs the pipeline when new files land in the volume (file-arrival trigger, [ADR 0002](../docs/adr/0002-trigger-pipeline-on-file-arrival.md)), and one AI/BI dashboard on gold.

## You write

- Done: the expectations and whether each warns, drops or fails, in [silver.py](transformations/silver.py).
- Done: the business definitions in [gold.py](transformations/gold.py): duplicate = an order with 2 or more invoices (all flagged); late = delivered after the promised date, counting delivered shipments only.

## Done when

The pipeline graph is green, expectation metrics are visible, and the seeded duplicate invoice appears in `gold.invoice_issues`.

## AI/BI dashboard on gold

Built on 2026-11-07 from [dashboards/sanad_gold.lvdash.json](../dashboards/sanad_gold.lvdash.json); `databricks bundle deploy` creates it as "[dev you] Najm operations (gold)". Design:

- **Deploy with the bundle**, not by hand: `resources.dashboards.sanad_gold` in [databricks.yml](../databricks.yml), `file_path: dashboards/sanad_gold.lvdash.json`, `dataset_catalog: sanad`, `dataset_schema: gold`. Get `warehouse_id` from a bundle variable with `lookup: warehouse: "Serverless Starter Warehouse"`, so no ID is hard-coded. Dataset queries use bare table names (`FROM invoice_issues`).
- **One page:** 3 KPIs (duplicate invoices; late rate of delivered shipments; VPN tickets on the worst day), late rate by month per region (Jeddah's Q3 spike), late rate by carrier (Red Sea Cargo), VPN tickets per day, the `invoice_issues` table, and one region filter.
- **Late rate** is a dataset measure `try_divide(SUM(late), SUM(delivered))`, never `AVG(late_rate)`. `try_divide` because the current month has shipments but no deliveries yet, and plain `/` by zero is an error in ANSI SQL.
- **Test every dataset query** with `databricks experimental aitools tools query` before deploying (the `databricks-aibi-dashboards` skill).
