"""Bronze: raw copies of every source file, exactly as received.

Auto Loader (format "cloudFiles") remembers which files it has already read,
so each pipeline run ingests only new files. Nothing is cleaned or typed here:
every column stays a string. If a silver rule turns out wrong, we can rebuild
silver from this untouched copy.
"""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

LANDING = "/Volumes/sanad/bronze/landing"
SOURCES = {  # table name: (folder under LANDING, file format)
    "crm_accounts": ("crm/accounts", "csv"),
    "crm_contacts": ("crm/contacts", "csv"),
    "erp_orders": ("erp/orders", "csv"),
    "erp_invoices": ("erp/invoices", "csv"),
    "erp_shipments": ("erp/shipments", "csv"),
    "itsm_tickets": ("itsm/tickets", "json"),
}


def bronze_table(name: str, folder: str, fmt: str) -> None:
    @dp.table(name=f"bronze.{name}", comment=f"Raw {folder} files, as received")
    def ingest():
        return (
            spark.readStream.format("cloudFiles")  # Auto Loader
            .option("cloudFiles.format", fmt)
            .option("header", "true")  # first CSV line holds column names; JSON ignores it
            .load(f"{LANDING}/{folder}")
            .select(
                "*",
                F.col("_metadata.file_path").alias("source_file"),  # lineage: which file
                F.current_timestamp().alias("ingested_at"),  # lineage: when we loaded it
            )
        )


for name, (folder, fmt) in SOURCES.items():
    bronze_table(name, folder, fmt)
