# Proving the numbers

A report with one wrong number is worse than no report: people stop trusting all of it. Nothing here is
optional before Gate 2. The audit catches the patterns it can see (`PBI032`, `PBI070`–`PBI077`); this file
covers the rest and the proof.

## Contents
1. The proof: reconcile against the source
2. DAX that returns the wrong number without an error
3. SQL that changes the numbers silently
4. Power Query and types
5. Python for checks
6. What to report to the user

## 1. The proof: reconcile against the source

1. **Pick the grain the business checks**: month × the main dimension (regional, product category),
   plus the grand total. Add the top 10 entities of the most important dimension.
2. **Write the source query** on the warehouse, from the fact columns, with the same filters and rules the
   measures apply (status, dates, sign). Do not query the views the model loads: query their sources, so
   the view itself is checked.
3. **Export the model's numbers** at the same grain: `python scripts/reconcile.py --dax "<measures>" --by
   "<Table[Column],…>"` prints the DAX query; run it through the Power BI Modeling MCP, DAX Studio or
   Desktop's DAX query view and save it as CSV.
4. **Compare**: `python scripts/reconcile.py source.csv report.csv --keys "<columns>" [--abs 0.01]
   [--rel 0.0001]`. It lists keys present on only one side, every value beyond tolerance (largest first)
   and the totals. Exit code 1 means stop.
5. **Explain every difference** before touching anything: which rows, which rule. Fix the cause (join,
   filter, sign, date), never the number.
6. **Row counts and distinct keys**: `COUNT(*)` and `COUNT(DISTINCT key)` of each fact in SQL against
   `COUNTROWS` and `DISTINCTCOUNT` in DAX. A fan-out shows here before it shows anywhere else.

Tolerance: money ±0.01 per row (cents), ratios ±0.0001; anything wider must be agreed with the user and
written in the README.

## 2. DAX that returns the wrong number without an error

| Pattern | What goes wrong | Right form |
|---|---|---|
| `AVERAGE ( t[%Col] )`, `AVERAGEX ( …, [% Measure] )` (`PBI070`) | average of ratios ≠ ratio of totals | `DIVIDE ( SUM ( num ), SUM ( den ) )` |
| `SUM` of a balance in a snapshot fact (`PBI071`) | a month adds 30 daily positions | `CALCULATE ( SUM ( … ), LASTNONBLANK ( dm_calendario[Data], CALCULATE ( COUNTROWS ( fact ) ) ) )` |
| `a / b` (`PBI032`) | error or infinity when b is 0 or blank | `DIVIDE ( a, b )` |
| `IFERROR` (`PBI033`) | hides the real error and is slow | handle the case: `IF ( ISBLANK ( … ), … )` |
| Totals of `IF ( HASONEVALUE … )` measures | the total row shows something different from the sum of rows | decide what the total means; compute it explicitly with `SUMX ( VALUES ( dim[key] ), [measure] )` |
| `CALCULATE ( [m], ALL ( fact ) )` for a share | removes the user's filters too (slicer on region) | `ALLSELECTED` or `REMOVEFILTERS ( dim[column] )` on the one column |
| `FILTER ( ALL ( dim ), … )` inside `CALCULATE` | overrides filters on that table silently | column predicate: `CALCULATE ( [m], dim[col] = "x" )` (adds to the filter context) |
| Time intelligence on an unmarked or gappy date table (`PBI011`) | `SAMEPERIODLASTYEAR` returns blanks or wrong periods | one marked date table, contiguous days, full years covering the fact |
| Many-to-many or bidirectional relationships (`PBI015`, `PBI016`) | double counting through the bridge | single direction; a bridge only by design, with `TREATAS` or `CROSSFILTER` in the measure |
| `COUNT ( fact[col] )` for "how many customers" | counts rows, not customers | `DISTINCTCOUNT ( fact[id_cliente] )` |
| Blank vs zero | `0 + BLANK ()` turns "no data" into 0 and shows every empty month | return `BLANK ()` when there is no data; `0` only when zero is a real value |
| Sign conventions | expenses negative in the source, positive in the measure, both summed | one rule, written in the measure description |
| Rounding before aggregating | `ROUND` in a row-level column, then summed | aggregate first, round only in the format string |
| Currency or unit mix | summing BRL and USD rows | convert at the row's date rate in SQL; one currency per measure |

Test every non-trivial measure with a tiny hand-made case: three rows you can add up on paper.

## 3. SQL that changes the numbers silently

| Pattern | What goes wrong | Right form |
|---|---|---|
| Join to a table that is not unique on the key | **fan-out**: each fact row repeats | check `COUNT(*) = COUNT(DISTINCT key)` on the dimension; join on the full key |
| `FROM a, b` or `JOIN` without `ON` (`PBI073`) | every row meets every row | `JOIN … ON` with the key |
| `LEFT JOIN d … WHERE d.col = 'x'` | turns into an inner join and drops facts without a match | put the condition in `ON`, or decide that an inner join is intended |
| `NOT IN (subquery)` with a NULL in it | returns no rows at all | `NOT EXISTS` |
| `BETWEEN '2025-01-01' AND '2025-01-31'` on datetime | misses everything after midnight of the 31st | `>= '2025-01-01' AND < '2025-02-01'` |
| `SELECT DISTINCT` in a fact (`PBI075`) | hides a fan-out, deletes legitimate equal rows | fix the join or the grain |
| `NOLOCK` (`PBI074`) | reads rows being written | normal isolation, or a snapshot |
| `SELECT *` (`PBI076`) | new columns load silently | explicit column list |
| Function on a column in `WHERE` (`PBI077`) | slow, scans the table | compare the raw column with a range |
| Time zone | UTC timestamps grouped by local day move sales across midnight | convert to the business time zone before taking the date |
| Late-arriving or soft-deleted rows | the report counts cancelled orders | filter on the status the business uses, written in the table description |
| Integer division (`SELECT 1/2` = 0 in SQL Server) | ratios computed in SQL come out 0 | cast to decimal, or compute ratios in DAX |

Every fact query states its grain in a comment and is tested once with `GROUP BY <grain> HAVING COUNT(*) > 1`
(must return nothing).

## 4. Power Query and types

- One step, native SQL (law 4). Types come from SQL: `decimal(18,2)` for money (never float), `date` for
  dates without time, integers for keys.
- `Decimal Number` (double) for money accumulates errors in totals (`PBI035`): use fixed decimal.
- Locale: the model's `culture` decides how text dates parse; keep dates typed in SQL so it never matters.

## 5. Python for checks

Python belongs to the checks around the model, not inside it (no Python visuals or Python steps in Power
Query: they break refresh in the service). Good uses:

- Reconciliation beyond CSV: query both sides with `pyodbc`/`sqlalchemy` and the DAX results exported, then
  compare with `pandas.merge(..., how="outer", indicator=True)`; same rules as `reconcile.py`.
- Data tests in CI on the warehouse (uniqueness of keys, no nulls in foreign keys, row counts per day).
- Generating or editing PBIP files: standard library, deterministic output, UTF-8 with LF, one function
  per file type, tested; the scripts of this skill are the house style.

```python
import pandas as pd
src = pd.read_csv("source.csv", sep=";", decimal=",", thousands=".")
rep = pd.read_csv("report.csv")
both = src.merge(rep, on=["Ano-Mês", "Regional"], how="outer", suffixes=("_src", "_rep"), indicator=True)
diff = both[(both["_merge"] != "both") | ((both["Valor Vencido_src"] - both["Valor Vencido_rep"]).abs() > 0.01)]
assert diff.empty, diff
```

## 6. What to report to the user

At Gate 2, in their language: the grain checked, the source used, how many keys and values matched,
every difference with its cause and fix, and what was not checked (no source access, a measure without
a reference). Never write "the numbers are correct" without the reconciliation output behind it.
