# PBIR page templates

**Prefer the layout engine.** Describe the pages in a short JSON spec and let
[`scripts/pbir_layout.py`](../../scripts/pbir_layout.py) write the PBIR: every position lands on the 4 px
grid, the app shell of [report-design.md](../../references/report-design.md) §0 is added to every page,
and drill-through, tooltip and phone layouts come for free. [`layout-example.json`](layout-example.json)
is the spec of the example report; copy it and change the fields.

```bash
python <skill>/scripts/pbir_layout.py layout.json <Name>.Report --theme <skill>/templates/theme/powerbi-architect-acessivel.json
python <skill>/scripts/preview_pbir.py <Name>.Report --out preview.html     # then look at every page
```

The folders below are the pages the engine writes for that spec, validated against Microsoft's JSON
schemas (`page/1.1.0`, `visualContainer/1.1.0`, `visualContainerMobileState/1.0.0`). Read them to see
the JSON of each archetype, or copy one by hand when you cannot run Python.

| Folder | Archetype | Content area (1024×616) |
|---|---|---|
| `overview-kpis/` | Overview | 4 `kpiCard` (244×104) · `trend` with last year (608×228) · `ring` of the aging buckets (400×228) · top-3 `list` (608×252) · `list` by region with a tooltip page (400×252) |
| `diagnostic/` | Diagnostic | waterfall of the parts (672×300) · breakdown (336×300) · table with one conditional colour (1024×300) |
| `operational-list/` | Operational list | one sorted table (1024×616), one column coloured by a measure, drill-through by right click |
| `drillthrough-detail/` | Drill-through detail | back arrow + breadcrumb · 4 KPIs · history (504×512) · breakdown (504×512); hidden from navigation |
| `tooltip/` | Tooltip page | 320×240, one visual; bound to visuals through `visualTooltip` |
| `documentation/` | Documentation | measures catalog (608×616) + loads (400×616); needs `_Documentacao` and `_Cargas` ([documentation.md](../../references/documentation.md)) |

Every page also has the shell: white sidebar (app mark and subtitle, sections, one row per page with a
16 px icon from [`templates/icons/`](../icons/README.md) and an optional count, a foot panel with the load
date and source), a header (report name above the page name; at the right the period tabs, the date range,
≤ 2 slicers of 176×40 and an action button) and a `mobile.json` next to each content visual (phone layout,
stacked).
