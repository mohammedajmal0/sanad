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
