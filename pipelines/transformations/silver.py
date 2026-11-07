"""Silver: cleaned, typed copies of bronze, one table per business entity.

TRY_CAST turns text into real types (dates, money). On a bad value like "abc"
it returns NULL instead of crashing the run, and the expectations then decide
what happens to that row: warn (keep it, count it), drop (remove it) or fail
(stop the whole run).

Business duplicates (two invoices for one order) are NOT removed here: finding
them is the agents' job, through gold.invoice_issues.
"""

from pyspark import pipelines as dp

LINEAGE = ["source_file", "ingested_at"]  # carried through from bronze


def from_bronze(table: str, *columns: str):
    """Stream new rows from a bronze table, keeping only the listed columns."""
    return spark.readStream.table(f"bronze.{table}").selectExpr(*columns, *LINEAGE)


# ponytail: append-only streaming. If the CRM ever re-sends full snapshots,
# switch accounts and contacts to AUTO CDC keyed on their IDs (keeps latest row).
@dp.table(name="silver.accounts", comment="One row per customer account")
@dp.expect_or_drop("has_account_id", "account_id IS NOT NULL")
def accounts():
    return from_bronze("crm_accounts", "account_id", "account_name", "region", "segment",
                       "TRY_CAST(created_date AS DATE) AS created_date")


@dp.table(
    name="silver.contacts",
    comment="Customer contacts; email and phone are PII",
    # The mask lives here, not in an ALTER TABLE: the pipeline owns this table's definition.
    # It is on silver, not bronze: a mask on bronze would save *** into silver for good.
    # The function is created by governance/setup.sql, which must run before this pipeline.
    schema="""contact_id STRING, account_id STRING, full_name STRING,
              email STRING MASK sanad.ops.mask_pii, phone STRING MASK sanad.ops.mask_pii,
              title STRING, source_file STRING, ingested_at TIMESTAMP""",
)
@dp.expect_or_drop("has_contact_id", "contact_id IS NOT NULL")
def contacts():
    return from_bronze("crm_contacts", "contact_id", "account_id", "full_name", "email",
                       "phone", "title")


@dp.table(name="silver.orders", comment="One row per ERP order")
@dp.expect_or_drop("has_order_id", "order_id IS NOT NULL")
def orders():
    return from_bronze("erp_orders", "order_id", "account_id",
                       "TRY_CAST(order_date AS DATE) AS order_date",
                       "TRY_CAST(amount_sar AS DECIMAL(12, 2)) AS amount_sar")


@dp.table(name="silver.invoices", comment="One row per invoice; business duplicates kept")
@dp.expect_or_drop("has_invoice_id", "invoice_id IS NOT NULL")
# DROP: an amount or date we can't read makes the row useless, and keeping it
# would silently make gold totals wrong. Dropped rows stay in bronze for repair.
@dp.expect_or_drop("readable_amount", "amount_sar IS NOT NULL")
@dp.expect_or_drop("readable_date", "invoice_date IS NOT NULL")
# WARN: a negative amount may be a real credit note, and an invoice dated in the
# future may be a typo. Keep the row so finance can see it, but count it.
@dp.expect("positive_amount", "amount_sar > 0")
@dp.expect("not_in_future", "invoice_date <= current_date()")
# No FAIL rule: one bad invoice shouldn't stop every table from updating.
# Use expect_or_fail only when a violation means the whole load is broken.
def invoices():
    return from_bronze("erp_invoices", "invoice_id", "order_id", "account_id",
                       "TRY_CAST(invoice_date AS DATE) AS invoice_date",
                       "TRY_CAST(amount_sar AS DECIMAL(12, 2)) AS amount_sar")


@dp.table(name="silver.shipments", comment="One row per shipment; delivered_date NULL = in transit")
@dp.expect_or_drop("has_shipment_id", "shipment_id IS NOT NULL")
def shipments():
    return from_bronze("erp_shipments", "shipment_id", "order_id", "carrier",
                       "TRY_CAST(ship_date AS DATE) AS ship_date",
                       "TRY_CAST(promised_date AS DATE) AS promised_date",
                       "TRY_CAST(delivered_date AS DATE) AS delivered_date")


@dp.table(name="silver.tickets", comment="One row per IT service-desk ticket")
@dp.expect_or_drop("has_ticket_id", "ticket_id IS NOT NULL")
def tickets():
    return from_bronze("itsm_tickets", "ticket_id",
                       "TRY_CAST(created_at AS TIMESTAMP) AS created_at",
                       "category", "priority", "summary", "status")
