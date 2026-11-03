# Databricks notebook source
"""ADF entrypoint. Requires imported notebooks in the same workspace folder."""
import re
from datetime import date

dbutils.widgets.text("catalog", "creditrisk_dev")
dbutils.widgets.text("as_of_date", "2026-10-31")
dbutils.widgets.text("base_path", "/Shared/creditrisk-migration")
catalog = dbutils.widgets.get("catalog")
as_of_date = dbutils.widgets.get("as_of_date")
base_path = dbutils.widgets.get("base_path").rstrip("/")
assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", catalog), "Invalid UC catalog"
date.fromisoformat(as_of_date)

for notebook in ("01_bronze", "02_silver", "03_gold", "04_validate"):
    print(f"Running {notebook} for {as_of_date}")
    result = dbutils.notebook.run(
        f"{base_path}/{notebook}",
        timeout_seconds=3600,
        arguments={"catalog": catalog, "as_of_date": as_of_date},
    )
    print(f"{notebook}: {result}")

dbutils.notebook.exit("SUCCESS")
