# Power Query — the one‑step policy

**Every source table has exactly one step:** `Fonte` (or `Source`) = connector + native SQL, using
parameters for server/database. No renames, no type changes, no filters, no merges in M.

Why: transformations in M are invisible in code review, slow to refresh, hard to fold and duplicated
across reports. SQL at the source is reviewed, reused, indexed and testable.

## Parameters
Defined in `expressions.tmdl` (in Power BI Workspaces they are generated — never edit by hand):

```tmdl
expression Erp_Server = "sql-erp.company.local" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	queryGroup: Parametros

	annotation PBI_ResultType = Text
```

## Partition template

```tmdl
	partition 'Fato Vendas' = m
		mode: import
		source =
				let
				    Fonte = Value.NativeQuery(Sql.Database(Erp_Server, Erp_Database), "SELECT ...", null, [EnableFolding = true])
				in
				    Fonte
```

The SQL is a single‑line M text literal: `"` → `""`, line breaks → `#(lf)`. Keep the readable SQL in
`sql/<Table>.sql` (source of truth) and regenerate the partition (`pbw sincronizar-sql` does this).

## Connector patterns (one step each)

| Source | M expression |
|---|---|
| SQL Server · Azure SQL · Fabric Warehouse/SQL endpoint · Synapse | `Value.NativeQuery(Sql.Database(S, D), q, null, [EnableFolding = true])` |
| SAP HANA | `SapHana.Database(S, [Implementation = "2.0", Query = q])` |
| Google BigQuery | `Value.NativeQuery(GoogleBigQuery.Database([BillingProject = P]){[Name = P]}[Data], q, null, [EnableFolding = true])` |
| PostgreSQL | `Value.NativeQuery(PostgreSQL.Database(S, D), q, null, [EnableFolding = true])` |
| Snowflake | `Value.NativeQuery(Snowflake.Databases(S, W){[Name = D, Kind = "Database"]}[Data], q, null, [EnableFolding = true])` |
| Databricks | `Value.NativeQuery(Databricks.Catalogs(H, Path, [Catalog = null, Database = null, EnableAutomaticProxyDiscovery = null]){[Name = C, Kind = "Database"]}[Data], q, null, [EnableFolding = true])` |
| Oracle | `Oracle.Database(S, [HierarchicalNavigation = true, Query = q])` |
| MySQL | `MySQL.Database(S, D, [ReturnSingleDatabase = true, Query = q])` |

`EnableFolding = true` lets Power BI fold incremental‑refresh filters and DirectQuery on top of the
native query (supported connectors). On first refresh Desktop asks to approve the native query — expected.

## SQL dialect notes
| Topic | T‑SQL | HANA | BigQuery | PostgreSQL | Snowflake |
|---|---|---|---|---|---|
| Today | `CAST(GETDATE() AS date)` | `CURRENT_DATE` | `CURRENT_DATE()` | `CURRENT_DATE` | `CURRENT_DATE()` |
| Date diff (days) | `DATEDIFF(day, a, b)` | `DAYS_BETWEEN(a, b)` | `DATE_DIFF(b, a, DAY)` | `b - a` | `DATEDIFF(day, a, b)` |
| Alias with spaces | `[Data Venc]` | `"Data Venc"` | `` `Data Venc` `` | `"Data Venc"` | `"Data Venc"` |
| Decimal | `DECIMAL(18,2)` | `DECIMAL(18,2)` | `NUMERIC` | `NUMERIC(18,2)` | `NUMBER(18,2)` |
| Table name | `schema.table` | `"SCHEMA"."TABLE"` | `` `project.dataset.table` `` | `schema.table` | `DB.SCHEMA.TABLE` |

## Incremental refresh
Add `RangeStart`/`RangeEnd` (DateTime parameters) and filter **inside** the SQL by building the query
text with them, keeping folding:

```m
Fonte = Value.NativeQuery(
    Sql.Database(Erp_Server, Erp_Database),
    "SELECT ... FROM bi.vendas WHERE data >= @ini AND data < @fim",
    [ini = RangeStart, fim = RangeEnd],
    [EnableFolding = true])
```
(Parameter binding support varies by connector — validate in Desktop and record an ADR.)

## Allowed exceptions (record an ADR)
- Sources without SQL (SharePoint/Excel/API): prefer landing them in a database/lakehouse. If impossible,
  keep the M minimal and isolated, and flag the dashboard as technical debt.
- Parameter tables or field parameters (DAX), not M.
- "Enter data" tables: never for business data; ok for tiny static lists (or use DAX `DATATABLE`).
