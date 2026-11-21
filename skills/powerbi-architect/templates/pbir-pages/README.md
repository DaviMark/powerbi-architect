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
| `overview-kpis/` | Overview | 4 KPI cards with a context or target line (244×88) · trend with dynamic title (672×248) · buckets (336×248) · ranking with a tooltip page (1024×248) |
| `diagnostic/` | Diagnostic | waterfall of the parts (672×300) · breakdown (336×300) · table with one conditional colour (1024×300) |
| `operational-list/` | Operational list | one sorted table (1024×616), one column coloured by a measure, drill-through by right click |
| `drillthrough-detail/` | Drill-through detail | back arrow + breadcrumb · 4 KPIs · history (504×512) · breakdown (504×512); hidden from navigation |
| `tooltip/` | Tooltip page | 320×240, one visual; bound to visuals through `visualTooltip` |
| `documentation/` | Documentation | measures catalog (608×616) + loads (400×616); needs `_Documentacao` and `_Cargas` ([documentation.md](../../references/documentation.md)) |

Every page also has the shell: sidebar (app mark, section label, page navigator, one 16 px icon per page
from [`templates/icons/`](../icons/README.md)), white panel, top bar (breadcrumb, "updated at",
≤ 2 slicers of 176×40) and a `mobile.json` next to each content visual (phone layout, stacked).

## Copying a page by hand

1. Copy the folder into `<Name>.Report/definition/pages/`, give it a new 20-hex-character id (folder name
   = `page.json › name`) and add it to `pages.json › pageOrder`.
2. Give every visual folder a new 20-hex id and set it in its `visual.json › name`.
3. Replace every field reference (`"Entity"`, `"Property"`, `queryRef`, `nativeQueryRef`) with fields of
   **your** model; remove a visual rather than leaving a reference to a field that does not exist.
4. Rewrite the texts: app name, breadcrumb, titles and every `altText`. Register the icons and the theme
   in `report.json › resourcePackages` (the engine does this for you).
5. Keep the `$schema` versions of the report you are editing ([pbir.md](../../references/pbir.md), rule 1).
6. Run `scripts/audit_pbip.py --min-harmony 90` and `scripts/preview_pbir.py`, then open in Desktop.
