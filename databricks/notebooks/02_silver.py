# Databricks notebook source
"""Validate, deduplicate and upsert source entities; retain rejected rows."""
import re
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable

dbutils.widgets.text("catalog", "creditrisk_dev")
dbutils.widgets.text("as_of_date", "2026-10-31")
catalog = dbutils.widgets.get("catalog")
assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", catalog)

configs = {
    "customers": {"key": "customer_id", "columns": ["customer_id", "region", "risk_band", "updated_at"]},
    "loans": {"key": "loan_id", "columns": ["loan_id", "customer_id", "principal_amount", "outstanding_balance", "due_date", "updated_at"]},
    "payments": {"key": "payment_id", "columns": ["payment_id", "loan_id", "payment_amount", "payment_date", "updated_at"]},
}
for entity, config in configs.items():
    key = config["key"]
    source = spark.table(f"{catalog}.bronze.{entity}")
    valid_rule = F.col(key).isNotNull() & F.col("updated_at").isNotNull() & F.col("_rescued_data").isNull()
    if entity == "customers":
        valid_rule = valid_rule & F.col("region").isNotNull() & F.col("risk_band").isNotNull()
    elif entity == "loans":
        valid_rule = (valid_rule & F.col("customer_id").isNotNull()
            & F.col("principal_amount").isNotNull() & (F.col("principal_amount") >= 0)
            & F.col("outstanding_balance").isNotNull() & (F.col("outstanding_balance") >= 0)
            & F.col("due_date").isNotNull())
    elif entity == "payments":
        valid_rule = (valid_rule & F.col("loan_id").isNotNull()
            & F.col("payment_amount").isNotNull() & (F.col("payment_amount") >= 0)
            & F.col("payment_date").isNotNull())

    # Current reject view for inspection; not a durable historical audit trail.
    source.filter(~valid_rule).write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        f"{catalog}.ops.{entity}_rejects_current")
    window = Window.partitionBy(key).orderBy(F.col("updated_at").desc(), F.col("_ingested_at").desc(), F.col("_source_file").desc())
    updates = (source.filter(valid_rule)
        .withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1).select(*config["columns"]))
    destination = f"{catalog}.silver.{entity}"
    if not spark.catalog.tableExists(destination):
        updates.write.format("delta").saveAsTable(destination)
    else:
        (DeltaTable.forName(spark, destination).alias("t")
         .merge(updates.alias("s"), f"t.{key} = s.{key}")
         .whenMatchedUpdateAll(condition="s.updated_at >= t.updated_at")
         .whenNotMatchedInsertAll().execute())
    print(f"Silver complete: {destination}")

dbutils.notebook.exit("SILVER_COMPLETE")
