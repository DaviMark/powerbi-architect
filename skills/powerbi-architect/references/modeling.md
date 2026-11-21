# Semantic modeling

## Contents
1. Principles · 2. Grain · 3. Facts & dimensions · 4. Keys & relationships · 5. Date dimension ·
6. Minimal import · 7. Storage modes · 8. Large models · 9. Naming · 10. Anti‑patterns

## 1. Principles
- The model is a **product** for report authors and analysts: obvious names, hidden plumbing,
  every measure documented. If someone needs you to explain the model, the model is wrong.
- VertiPaq compresses **columns**. Cost ≈ number of columns × cardinality. Rows are cheap, unique
  values are expensive.
- Star schema is not dogma; it is the shape that makes filters flow one way, DAX simple and
  compression good. Snowflakes and flat tables are the exceptions you justify.

## 2. Grain
Write the grain as a sentence **before** choosing columns: "1 row per invoice line per day".
- Mixed grains in one table (headers + lines, budget monthly + actuals daily) → split into facts.
- Need to compare facts at different grains (budget vs actual)? Share dimensions at the coarser level
  (e.g. a `Month` key in `dm_calendario`) and relate each fact at its own grain.

## 3. Facts & dimensions
| Fact | Dimension |
|---|---|
| events/snapshots with numbers to aggregate | entities to filter/group by |
| narrow: keys + measures + few degenerate attributes | wide is fine: descriptive attributes |
| many rows | fewer rows |

- **Transaction facts** (one row per event), **periodic snapshots** (balance per day/month),
  **accumulating snapshots** (one row per process with milestone dates). Name the type in the description.
- **Degenerate dimensions**: low‑cardinality attributes with no other use (status, bucket) may stay
  in the fact. Order numbers used only for drill‑through also stay (hidden unless needed).
- **Junk dimensions** for many small flags instead of 10 flag columns in the fact.
- **SCD2** dimensions: relate on the surrogate key; expose "current" attributes separately if needed.

## 4. Keys & relationships
- Integer surrogate keys (generated at the source). Text keys only if unavoidable.
- `fromColumn` = fact (many), `toColumn` = dimension (one). Single direction.
- **Bidirectional:** avoid. Use it only for a designed pattern (e.g. bridge for M:M) and record an ADR.
  Prefer `CROSSFILTER` inside a specific measure.
- **Many‑to‑many cardinality**: avoid; it signals a grain problem. Use a bridge table when the business
  relationship is truly M:M (e.g. customer ↔ account), with an ADR.
- Inactive relationships for secondary dates; activate in measures with `USERELATIONSHIP`.
- Every fact row should find its dimension row. Add an "Unknown" member (key `-1`) at the source
  instead of blank rows.

## 5. Date dimension
- One date table, marked as date table (`dataCategory: Time`, `isKey` on the date column), contiguous
  days covering the fact range (full years). **Auto date/time off** (model annotation
  `__PBI_TimeIntelligenceEnabled = 0`).
- Prefer a corporate date dimension from the source (fiscal calendars, holidays). Otherwise a DAX
  calculated table (no Power Query) bounded by the fact:

```dax
VAR _inicio = DATE ( YEAR ( MIN ( ft_vendas[Data] ) ), 1, 1 )
VAR _fim    = DATE ( YEAR ( MAX ( ft_vendas[Data] ) ), 12, 31 )
RETURN
    ADDCOLUMNS (
        SELECTCOLUMNS ( CALENDAR ( _inicio, _fim ), "Data", [Date] ),
        "Ano", YEAR ( [Data] ),
        "Mês Nº", MONTH ( [Data] ),
        "Mês", FORMAT ( [Data], "mmm" ),
        "Ano-Mês", FORMAT ( [Data], "yyyy-mm" ),
        "Trimestre", "T" & QUARTER ( [Data] ),
        "Dia da Semana Nº", WEEKDAY ( [Data], 2 ),
        "Dia da Semana", FORMAT ( [Data], "ddd" )
    )
```
- Sort `Mês` by `Mês Nº`, `Dia da Semana` by `Dia da Semana Nº`. Add fiscal columns if the business uses them.
- Datetime facts: split into date (relationship) and, only if needed, time (separate dim or column).

## 6. Minimal import — the column audit
For every candidate column ask: *is it used by a measure, a visual, a relationship, a sort, a filter
the user asked for, or RLS?* If not, don't import it. Typical cuts:
- audit columns (`created_by`, `updated_at`), technical GUIDs, row versions
- free‑text comments/descriptions (unless the report shows them)
- columns derivable from others at query time (`year`, `month` already in dm_calendario)
- duplicated names in facts when the dimension already has them
- high‑precision decimals → round at the source; datetime → date

Document the cut list in `trabalho-da-ia/desenho.md › Modelo › "O que NÃO vamos importar"`.

## 7. Storage modes
| Mode | Use when | Watch out |
|---|---|---|
| **Import** (default) | almost always | refresh window, model size |
| **DirectQuery** | near real‑time or data too big to import | every visual = source query; design aggregations; limited DAX performance |
| **Composite** | big detail fact in DQ + imported dims/aggregations | relationship limitations, dual mode on dims |
| **Direct Lake** | source is a Fabric lakehouse/warehouse (Delta) | framing, fallback to DQ, V‑Order at the source |

Record the choice as an ADR when not Import.

## 8. Large models
- **Incremental refresh**: `RangeStart`/`RangeEnd` parameters filtering the date in the **SQL WHERE**
  (folding is mandatory). Policy defined in the model; requires Premium/PPU/Fabric for some features.
- **Aggregations**: imported summary table at a coarser grain mapped to the DQ detail.
- **Pre‑aggregate at the source** when the report never needs the detail.

## 9. Naming (mandatory)
- **Tables:** lowercase snake case with a role prefix, in the project language.
  - Facts: `ft_<subject>` (`ft_vendas`, `ft_titulos`, `ft_saldos_diarios`).
  - Dimensions: `dm_<entity>` (`dm_cliente`, `dm_produto`, `dm_regional`); the date dimension is
    `dm_calendario` (`dm_date` in English projects).
  - Bridges (only by design, ADR): `ft_` if they carry measures, otherwise `dm_<a>_<b>`.
  - Helpers that are not part of the star: `_` prefix (`_Medidas`, `_Documentacao`, `_Cargas`).
  - The SQL file of a table has the same name: `sql/ft_vendas.sql`.
  Users never read table names in a well-built report: they see measures, display folders and friendly
  column names, so the prefixes cost nothing and make every model readable at a glance. The audit
  enforces them (rule `PBI049`).
- **Columns and measures:** business language, Title Case, units in the name when ambiguous
  (`Prazo Médio (dias)`), `%` prefix for ratios (`% Vencido`). No technical prefixes on what users see
  (`vl_`, `qt_`, `dt_`).
- **Keys:** `id_<entity>`, hidden.

## 10. Anti‑patterns (and the fix)
| Smell | Fix |
|---|---|
| One huge flat table | split into fact + dimensions |
| Snowflake chains (Product → Subcategory → Category) | flatten into one dimension at the source |
| Calculated columns in facts | compute in SQL |
| Bidirectional everywhere | single direction + specific measures |
| Auto date/time hidden tables | turn off; one date table |
| Same dimension imported twice | one conformed dimension |
| Measures scattered in many tables | one measure table with folders |
| Implicit measures (dragging numeric columns) | `discourageImplicitMeasures` + explicit measures |
