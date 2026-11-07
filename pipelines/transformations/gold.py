"""Gold: business-ready answer tables for the agents, Genie and dashboards.

Materialized views, not streaming tables: each one batch-reads silver
(spark.read, all rows) and is recomputed on every pipeline update, so counts,
rates and duplicate checks always match the current data. A streaming table
sees each new row once and can never revisit an answer it already wrote.
"""

from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F


def silver(table: str):
    """Batch-read a whole silver table: every row, not just the new ones."""
    return spark.read.table(f"silver.{table}")


@dp.materialized_view(name="gold.invoice_issues",
                      comment="One row per invoice finance should check, with the reason")
def invoice_issues():
    invoices = silver("invoices").withColumn(
        "invoices_for_order", F.count("*").over(Window.partitionBy("order_id")))

    # Business rule: an order should be billed exactly once, so every invoice of an
    # order with 2+ invoices is a duplicate. Both are flagged: the pair is the evidence
    # the agent shows ("INV-027711 and INV-050001 both bill ORD-027711").
    is_duplicate = F.col("invoices_for_order") > 1

    issue_type = (  # first matching reason wins
        F.when(is_duplicate, "duplicate")
        # The same checks as silver's WARN rules: those rows were kept so finance sees them here.
        .when(F.col("amount_sar") <= 0, "non_positive_amount")
        .when(F.col("invoice_date") > F.current_date(), "future_dated")
    )
    accounts = silver("accounts").select("account_id", "account_name", "region")
    return (
        invoices.withColumn("issue_type", issue_type)
        .where(F.col("issue_type").isNotNull())
        .join(accounts, "account_id", "left")  # left: keep an issue even if its account is unknown
        .select("invoice_id", "order_id", "account_id", "account_name", "region",
                "invoice_date", "amount_sar", "invoices_for_order", "issue_type")
    )


@dp.materialized_view(name="gold.delivery_sla_by_region",
                      comment="Late-delivery rate per customer region, carrier and ship month")
def delivery_sla_by_region():
    # Business rule: late = delivered after the promised date. A shipment still in
    # transit is not counted yet (its outcome is unknown), so the rate is late / delivered.
    is_late = F.col("delivered_date") > F.col("promised_date")

    region = silver("orders").join(silver("accounts"), "account_id").select("order_id", "region")
    return (
        silver("shipments")
        .join(region, "order_id")
        .groupBy("region", "carrier", F.date_trunc("MONTH", "ship_date").cast("date")
                 .alias("ship_month"))
        .agg(F.count("*").alias("shipments"),
             F.count("delivered_date").alias("delivered"),  # count(col) skips NULLs
             F.count_if(is_late).alias("late"))
        .withColumn("late_rate", F.round(F.col("late") / F.col("delivered"), 4))
    )


@dp.materialized_view(name="gold.ticket_trends",
                      comment="Daily ticket counts per category; a spike means an incident")
def ticket_trends():
    return (
        silver("tickets")
        .groupBy(F.to_date("created_at").alias("created_date"), "category")
        .agg(F.count("*").alias("tickets"),
             F.count_if(F.col("priority") == "high").alias("high_priority"),
             F.count_if(F.col("status") == "open").alias("open_tickets"))
    )


@dp.materialized_view(name="gold.customer_360",
                      comment="One row per account: profile, order history, invoice issues")
def customer_360():
    # Aggregate each table per account BEFORE joining. Joining orders to contacts
    # first would repeat every order once per contact and inflate the totals (fan-out).
    contacts = silver("contacts").groupBy("account_id").agg(F.count("*").alias("contacts"))
    orders = silver("orders").groupBy("account_id").agg(
        F.count("*").alias("orders"),
        F.sum("amount_sar").alias("order_total_sar"),
        F.max("order_date").alias("last_order_date"))
    issues = (spark.read.table("gold.invoice_issues")
              .groupBy("account_id").agg(F.count("*").alias("invoice_issues")))
    return (
        silver("accounts")
        .select("account_id", "account_name", "region", "segment", "created_date")
        .join(contacts, "account_id", "left")
        .join(orders, "account_id", "left")
        .join(issues, "account_id", "left")
        .fillna(0, ["contacts", "orders", "invoice_issues"])  # no rows means 0, not unknown
    )
