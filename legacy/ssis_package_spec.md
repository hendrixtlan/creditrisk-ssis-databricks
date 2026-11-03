# Legacy SSIS package inventory — designed migration source

These are **package specifications**, not compiled/deployable `.dtsx` binaries. Recreate in SSDT if a live legacy demo is required. A genuine corporate migration would start from exported SSISDB `.ispac`/`.dtsx` assets.

| Package | Control/Data Flow | Dependencies | Refactored replacement |
|---|---|---|---|
| `PKG_Extract_Customers.dtsx` | OLE DB Source → Data Conversion → Flat File Destination; SQL Agent daily schedule | `dbo.Customers` | ADF Copy to ADLS/landing/customers |
| `PKG_Extract_Loans.dtsx` | OLE DB Source → Derived Column → Conditional Split → Flat File Destination | `dbo.Loans` | ADF Copy + PySpark validations |
| `PKG_Extract_Payments.dtsx` | OLE DB Source → Lookup loan ID → Aggregate → OLE DB Destination | `dbo.Payments`, `dbo.Loans` | ADF Copy + PySpark Silver + Gold |
| `PKG_Build_Risk_Mart.dtsx` | Execute SQL Task → Lookup → Aggregate → OLE DB Destination | all three entities | Databricks Gold notebook + SQL baseline |

## Migration assessment worksheet

For every real legacy package collect version, data flow source/sink, connection managers, parameter/environment bindings, SQL Agent dependency, third-party components, custom scripts, row volumes, SLA, transaction handling, restart behavior, sensitive settings, and destination business logic. Classify each package as **retire**, **refactor**, **retain temporarily**, or **lift-and-shift**. During dual run, record old and new counts and monetary sums by batch/date.
