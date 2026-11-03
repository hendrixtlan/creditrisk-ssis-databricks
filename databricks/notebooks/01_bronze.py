# Databricks notebook source
"""Incrementally ingest immutable ADF CSV landing files into UC Bronze."""
import re
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, LongType, StringType, DecimalType, DateType, TimestampType

dbutils.widgets.text("catalog", "creditrisk_dev")
dbutils.widgets.text("as_of_date", "2026-10-31")
catalog = dbutils.widgets.get("catalog")
assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", catalog)

schemas = {
    "customers": StructType([
        StructField("customer_id", LongType()), StructField("region", StringType()),
        StructField("risk_band", StringType()), StructField("updated_at", TimestampType()),
    ]),
    "loans": StructType([
        StructField("loan_id", LongType()), StructField("customer_id", LongType()),
        StructField("principal_amount", DecimalType(18, 2)),
        StructField("outstanding_balance", DecimalType(18, 2)),
        StructField("due_date", DateType()), StructField("updated_at", TimestampType()),
    ]),
    "payments": StructType([
        StructField("payment_id", LongType()), StructField("loan_id", LongType()),
        StructField("payment_amount", DecimalType(18, 2)),
        StructField("payment_date", DateType()), StructField("updated_at", TimestampType()),
    ]),
}
for entity, source_schema in schemas.items():
    source = f"/Volumes/{catalog}/ingest/landing/{entity}/"
    state = f"/Volumes/{catalog}/ops/state/{entity}"
    stream = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.schemaLocation", f"{state}/schema")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("rescuedDataColumn", "_rescued_data")
        .schema(source_schema).load(source)
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .withColumn("_ingested_at", F.current_timestamp())
    )
    query = (
        stream.writeStream.format("delta")
        .option("checkpointLocation", f"{state}/checkpoint")
        .trigger(availableNow=True)
        .toTable(f"{catalog}.bronze.{entity}")
    )
    query.awaitTermination()
    print(f"Bronze completed for {entity}")

dbutils.notebook.exit("BRONZE_COMPLETE")
