# Performance

## Model size (VertiPaq)
- Remove unused columns first — the biggest win, always.
- Reduce cardinality: datetime → date; round decimals to business precision; split high‑cardinality
  text (e.g. "code – name") into key + attribute in a dimension; avoid unique IDs in facts unless needed.
- Integer keys; `int64` and `decimal` over `string`.
- No calculated columns in big facts; no auto date/time.
- Measure size with VertiPaq Analyzer (DAX Studio / Tabular Editor) or `INFO.STORAGETABLECOLUMNS()`
  in DAX query view; check the biggest columns and dictionary sizes.

## Refresh
- One step per table with native SQL and folding; indexes/partitions at the source for the WHERE.
- Incremental refresh for large facts (date filter folded into SQL).
- Avoid many small tables hitting the same source sequentially — prefer one well‑designed view.

## DAX
- See `dax.md › Performance`. Use DAX query view + Performance Analyzer: find the slowest visual, copy
  its query, test the measure variants.
- Typical fixes: column predicates instead of `FILTER(table)`, variables, avoid `DISTINCTCOUNT` on huge
  columns (pre‑aggregate), avoid converting blanks to zero, simplify iterators.

## Report
- ≤ 8 visuals per page (each visual = at least one query). Combine KPIs in one card visual when possible.
- Slicers are queries too — use the filter pane for secondary filters.
- Tables/matrices with thousands of rows → drill‑through or Top N.
- Avoid high‑cardinality axes (e.g., 5 000 customers on a bar chart).
- Custom visuals must cap data and draw efficiently (see `custom-visuals.md`).

## DirectQuery specifics
- Every interaction queries the source: aggregations, dual storage for dimensions, limit visuals,
  "Apply" buttons on slicers (query reduction), source‑side indexes/materialized views.
