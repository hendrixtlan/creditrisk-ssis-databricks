# Databricks notebook source
"""Hard-fail on key uniqueness, orphan records and aggregate parity."""
import re
from datetime import date
from decimal import Decimal
from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "creditrisk_dev")
dbutils.widgets.text("as_of_date", "2026-10-31")
catalog = dbutils.widgets.get("catalog")
as_of_date = dbutils.widgets.get("as_of_date")
assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", catalog)
cutoff = date.fromisoformat(as_of_date)
for entity, key in (("customers", "customer_id"), ("loans", "loan_id"), ("payments", "payment_id")):
    table = spark.table(f"{catalog}.silver.{entity}")
    assert table.filter(F.col(key).isNull()).count() == 0, f"Null key in {entity}"
    assert table.count() == table.select(key).distinct().count(), f"Duplicate keys in {entity}"

loans = spark.table(f"{catalog}.silver.loans")
customers = spark.table(f"{catalog}.silver.customers")
payments = spark.table(f"{catalog}.silver.payments")
assert loans.join(customers, "customer_id", "left_anti").count() == 0, "Orphan loans"
assert payments.join(loans, "loan_id", "left_anti").count() == 0, "Orphan payments"
gold = spark.table(f"{catalog}.gold.portfolio_risk_daily").filter(F.col("as_of_date") == F.lit(cutoff))
assert gold.count() > 0, "Gold is empty"
loan_total = loans.agg(F.sum("outstanding_balance")).first()[0] or Decimal(0)
gold_total = gold.agg(F.sum("outstanding_exposure")).first()[0] or Decimal(0)
assert abs(loan_total - gold_total) <= Decimal("0.01"), f"Outstanding mismatch: {loan_total} vs {gold_total}"
assert gold.filter((F.col("past_due_pct") < 0) | (F.col("past_due_pct") > 100)).count() == 0, "Invalid overdue percentage"
print(f"Integrity checks passed for {as_of_date}; loans outstanding={loan_total}")
dbutils.notebook.exit("VALIDATION_PASSED")
