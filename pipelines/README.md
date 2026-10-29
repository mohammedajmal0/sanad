# pipelines

Lakeflow Spark Declarative Pipelines (formerly DLT): Auto Loader bronze, cleaned silver, business gold.

**Phase:** 1

## What goes here

- Bronze: Auto Loader ingestion of CRM and ERP batches and the ITSM ticket stream.
- Silver: cleaned, conformed tables with expectations that warn, drop or fail.
- Gold: `customer_360`, `invoice_issues`, `delivery_sla_by_region`, `ticket_trends`.
- A job that runs the generator and the pipeline, and one AI/BI dashboard on gold.

## You write

- TODO(human): the expectations, and for each one whether it warns, drops or fails.
- TODO(human): the business definitions, such as what counts as "late".

## Done when

The pipeline graph is green, expectation metrics are visible, and the seeded duplicate invoice appears in `gold.invoice_issues`.
