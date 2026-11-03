# Databricks notebook source
"""Deterministic risk snapshot based on latest source rows + payment date cutoff."""
import re
from datetime import date
from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "creditrisk_dev")
dbutils.widgets.text("as_of_date", "2026-10-31")
catalog = dbutils.widgets.get("catalog")
as_of_date = dbutils.widgets.get("as_of_date")
assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", catalog)
cutoff = date.fromisoformat(as_of_date)

c = spark.table(f"{catalog}.silver.customers").alias("c")
l = spark.table(f"{catalog}.silver.loans").alias("l")
p = spark.table(f"{catalog}.silver.payments")
orphans = l.join(c, F.col("l.customer_id") == F.col("c.customer_id"), "left_anti").count()
assert orphans == 0, f"Found {orphans} loans with no customer; resolve dependencies first"
payment_totals = (p.filter(F.col("payment_date") <= F.lit(cutoff))
                  .groupBy("loan_id")
                  .agg(F.sum("payment_amount").alias("collected"))).alias("p")
portfolio = (l.join(c, F.col("l.customer_id") == F.col("c.customer_id"))
             .join(payment_totals, F.col("l.loan_id") == F.col("p.loan_id"), "left")
             .select(F.col("l.loan_id"), F.col("c.region"), F.col("c.risk_band"),
                     F.col("l.principal_amount"), F.col("l.outstanding_balance"),
                     F.col("l.due_date"), F.coalesce(F.col("p.collected"), F.lit(0)).alias("collected")))
summary = (portfolio.groupBy("region", "risk_band")
    .agg(F.count("loan_id").alias("loan_count"),
         F.sum("principal_amount").alias("total_principal"),
         F.sum("outstanding_balance").alias("outstanding_exposure"),
         F.sum(F.when((F.col("due_date") < F.lit(cutoff)) & (F.col("outstanding_balance") > 0),
                      F.col("outstanding_balance")).otherwise(F.lit(0))).alias("past_due_exposure"),
         F.sum("collected").alias("total_collected"))
    .withColumn("past_due_pct", F.when(F.col("outstanding_exposure") == 0, F.lit(0.0))
                .otherwise(F.lit(100.0) * F.col("past_due_exposure") / F.col("outstanding_exposure"))
                .cast("decimal(12,4)"))
    .withColumn("as_of_date", F.lit(cutoff).cast("date"))
    .select("as_of_date", "region", "risk_band", "loan_count", "total_principal",
            "outstanding_exposure", "past_due_exposure", "total_collected", "past_due_pct"))

target = f"{catalog}.gold.portfolio_risk_daily"
spark.sql(f"""CREATE TABLE IF NOT EXISTS {target} (
  as_of_date DATE, region STRING, risk_band STRING, loan_count BIGINT,
  total_principal DECIMAL(28,2), outstanding_exposure DECIMAL(28,2),
  past_due_exposure DECIMAL(28,2), total_collected DECIMAL(28,2),
  past_due_pct DECIMAL(12,4)) USING DELTA PARTITIONED BY (as_of_date)""")
(summary.write.format("delta").mode("overwrite")
 .option("replaceWhere", f"as_of_date = DATE '{as_of_date}'")
 .saveAsTable(target))
print(f"Published {target} as of {as_of_date}")
dbutils.notebook.exit("GOLD_COMPLETE")
