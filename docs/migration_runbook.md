# Migration runbook and portfolio demonstration

## 1. SSIS assessment

Inspect real `.dtsx`/`.ispac` assets in SSDT/SSISDB. Inventory data flow transforms, data types, expressions, SQL Agent triggers, OLE DB connection managers, credentials, third-party components, retry behaviors, and implicit ordering. Inventory blockers (UNC paths, custom scripts, locale and time-zone dependencies). The specifications in this repo are illustrative, not an exported executable SSIS project.

## 2. Provision Azure services

Minimum resources: Azure resource group, ADLS Gen2 storage account with hierarchical namespace and a `landing` filesystem, Data Factory, Databricks Premium workspace with Unity Catalog, Access Connector with managed identity. Optionally use `infra/` Terraform as a basic infrastructure starter (does not solve VNet/identity/UC setup). Install ADF Self-hosted Integration Runtime on a dedicated Windows VM/host able to reach source SQL Server. Secure firewall and DNS connectivity.

**Security:** assign the ADF identity write access to landing, the Databricks Access Connector managed identity the required storage rights, and runtime principals appropriate Unity Catalog permissions. Prefer private endpoints, customer-managed keys where required, Key Vault, federated auth/managed identities and separate dev/prod subscriptions. Do not store SQL passwords, PATs, ADLS keys, or live borrower data in Git. For synthetic demo the user can use temporary lower-cost resources with documented limitations.

## 3. Set up Unity Catalog

In the Databricks Catalog Explorer, register the Access Connector-based managed-identity storage credential, and an external location that covers `abfss://landing@<storage>.dfs.core.windows.net/`. Then execute `databricks/sql/00_bootstrap_uc.sql` (replace storage account first). UC `ingest.landing` is an **external volume** reading ADF files. UC `ops.state` is a **managed volume** used for Auto Loader schema/checkpoint state, separate from the source and table data. Grant the runtime principal `READ VOLUME` on landing, `READ VOLUME` and `WRITE VOLUME` on state, and table create/modify privileges on Bronze/Silver/Gold and Ops as necessary. Grant analysts read access only on Gold.

## 4. Build ADF linked services and import artifacts

- `LS_SQLSERVER`: SQL Server connector, on-premises Self-hosted IR, secure credentials. Azure SQL is a different source and may use Azure IR.
- `LS_ADLS`: ADLS Gen2 linked service, managed identity, `landing` filesystem.
- `LS_DATABRICKS`: Azure Databricks linked service with managed identity or another governed supported auth method; configure a UC-compatible job cluster/compute and workspace principal.

Import both ADF datasets, then the pipeline. The SQL dataset's `dbo.Customers` table is source metadata; each Copy activity overrides with its own SQL query. The pipeline copies three sources **in parallel** and starts the Databricks notebook **only after all three succeed**. Each Copy writes to `landing/<entity>/<RunId>/<entity>_<RunId>.csv`. Keep the output immutable; do not overwrite an existing landing file or destroy a running checkpoint. Databricks processes all currently undiscovered files under each entity root, not only a single ADF RunId.

For a full backfill, set `window_start` earlier than the oldest source `updated_at`; use an exclusive upper bound for `window_end`. Keep all timestamps UTC and treat the values as UTC by convention; source SQL Server `datetime2` lacks a time-zone offset. Validate the time standard in a real enterprise implementation. In production, a control table and a committed watermark per entity should replace manually supplied windows. Failed ADF runs should not advance committed watermarks.

## 5. Import and run Databricks notebooks

Import `databricks/notebooks/*.py` into `/Shared/creditrisk-migration` as notebooks named `00_run_pipeline`, `01_bronze`, etc., without `.py` extensions. Run `00_run_pipeline` with `catalog=creditrisk_dev`, `as_of_date=2026-10-31` (adjust as needed). The Bronze job creates three managed tables by streaming from the external landing volume. The Silver job reads Bronze, rejects invalid rows to current reject tables in Ops, deduplicates by source key and `updated_at`, and performs Delta `MERGE`. Gold computes the risk metrics. Validate runs at the end.

**Restart behavior:** a stable Auto Loader checkpoint per entity avoids processing already-seen file paths again, including after a failed later stage. Silver upserts and Gold `replaceWhere` make repeat runs of an unchanged dataset idempotent. New corrected source versions must arrive at new immutable file paths with later `updated_at`. Avoid replaying the same exact file path with different contents.

**Data-quality treatment:** invalid records are excluded from Silver and put in `ops.*_rejects_current` tables. This sample does **not** enforce an absolute reject-rate SLO and does not keep a historical immutable quarantine; add them before production. Foreign-key orphans fail Gold/validation instead of being silently omitted.

## 6. Reconcile legacy and modern outputs

For equivalent inputs and as-of date, run the SQL baseline script (`legacy/sql/02_legacy_risk_mart.sql`) against source SQL Server and export results to CSV. Export the Databricks Gold `SELECT * FROM creditrisk_dev.gold.portfolio_risk_daily WHERE as_of_date = DATE '2026-10-31'` to a single CSV of the same column structure. Execute:

```shell
python demo/reconcile_gold.py --expected legacy_mart.csv --actual databricks_gold_export.csv --tolerance 0.01
```

Acceptance threshold: exact grouping keys and loan counts, maximum absolute monetary or percentage difference of 0.01 per group. Additionally compare counts at each Bronze and Silver entity, invalid/reject rows, and Spark/ADF run telemetry. Currency is generic in this demo; a real loan system must explicitly define currency conversion and rounding rules.

## 7. Parallel run, production cutover and rollback

1. Baseline: capture SSIS package durations, row counts, key financial measures, failed runs, resource use, lineage and recovery time.
2. Historical backfill: split large source history into bounded windows; run ADF and reconcile after each coherent data cut. Ensure dependent entities are loaded before Gold calculation.
3. Dual-run: operate SSIS and the modern pipeline for an agreed acceptance period, comparing the same source snapshot/time window and KPI definitions.
4. Cutover gate: certify accuracy, data freshness, security roles, recovery and SLAs; switch downstream consumers to the governed Gold mart.
5. Rollback: preserve the original SSIS/SQL reporting path until cutover sign-off; if quality or performance degrades, route dashboards back to the legacy mart.
6. Retire: disable old SQL Agent schedules and package infrastructure only after retention/audit requirements are met.

## 8. Failure injection exercises for screenshots

- ADF Copy to an unavailable SQL Server: verify retry and no notebook execution.
- Invalid loan row with negative outstanding balance: verify Ops reject, no bad Silver insertion.
- Missing customer referenced by a loan: confirm Gold fails with an orphan exception.
- Duplicate loan key with later `updated_at`: confirm Silver `MERGE` resolves to the latest value.
- Re-run same pipeline with no new landing file paths: confirm Bronze counts unchanged and Gold totals unchanged.
- Rename/remove checkpoint in a **disposable** environment only: observe reprocessing, restore from backup/recreate safely; do not perform in a real managed environment.

## 9. Screenshots and portfolio evidence to collect

ADF copy activity graph, ADLS folder layout, Databricks job runs, Bronze/Silver/Gold table lineage, Unity Catalog access permissions, quality rejection example, reconciliation PASS output, before-vs-after runtime and compute cost. Never invent measurements: show observed numbers from your actual execution.

## 10. What to improve for a production-grade portfolio v2

SQL Server CDC and delete handling; metadata-driven extraction; persistent source watermarks with atomic commit; monitoring with Azure Monitor / Log Analytics; pipeline SLAs and alerting; incremental Silver based on Change Data Feed; data contracts/expectations; Delta table clustering/optimization; performance and cost benchmark; IaC coverage of identity/network/databricks/ADF connections; CI/CD and approval gates. Consider Lakeflow Spark Declarative Pipelines for a newer approach while keeping this version directly comparable to SSIS transforms.
