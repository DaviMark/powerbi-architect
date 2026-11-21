# PBIR page templates

Three page archetypes in PBIR, validated against Microsoft's JSON schemas (`page/1.1.0`,
`visualContainer/1.1.0`). They come from [`examples/contas-a-receber`](../../../../examples/contas-a-receber)
and implement the app shell of [report-design.md](../../references/report-design.md) §0: grey canvas,
220 px sidebar with app mark, section label and page navigator; white panel (220, 12, 1048, 696) with
radius 8 and hairline border; 56 px top bar with breadcrumb, "updated at" and a 176×40 dropdown slicer;
content area (232, 80, 1024, 616) on a 4 px grid with 16 px gutters. Styling comes from the theme in
[templates/theme/](../theme/powerbi-architect-acessivel.json), so register it in the report.

| Folder | Archetype | Content area |
|---|---|---|
| `overview-kpis/` | Overview | 4 KPI cards (244×88) · trend (672×248) with dynamic title · buckets (336×248) · ranking (1024×248) |
| `detail-table/` | Detail | one sorted table (1024×616) |
| `documentation/` | Documentation page | measures catalog (608×616) + loads (400×616); needs `_Documentacao` and `_Cargas`, see [documentation.md](../../references/documentation.md) |

Shell visuals (sidebar, panel, breadcrumb, hairline, updated at, slicer) are the same on every page;
keep their positions when you copy a page so navigation feels like one product.

## How to use a template

1. Copy the folder into `<Name>.Report/definition/pages/` and rename it to a new 20-hex-character id.
   Set the same id in `page.json › name` and add it to `pages.json › pageOrder`.
2. Give every visual folder a new 20-hex id and set it in its `visual.json › name`.
3. Replace every field reference (`"Entity"`, `"Property"`, `queryRef`, `nativeQueryRef`) with fields of
   **your** model. Measures stay under `"Measure"`, columns under `"Column"`. Remove a visual rather than
   leaving a reference to a field that does not exist.
4. Rewrite the texts: app name, breadcrumb (report name and page name), visual titles and every
   `altText`. The "updated at" card needs a text measure such as
   `"Atualizado em " & FORMAT ( MAX ( '_Medidas'[Data Carga] ), "dd/mm/yyyy hh:nn" )`.
5. Keep the `$schema` versions of the report you are editing (see [pbir.md](../../references/pbir.md),
   golden rule 1). If the report uses newer versions, change the template's `$schema` to match.
6. Run `scripts/audit_pbip.py` (alt text, visual count, grid, font sizes, slicer size, page names) and
   open the report in Desktop.
