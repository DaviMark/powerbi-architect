# PBIR page templates

Three page archetypes in PBIR, validated against Microsoft's JSON schemas (`page/1.1.0`,
`visualContainer/1.1.0`). They come from [`examples/contas-a-receber`](../../../../examples/contas-a-receber)
and follow [report-design.md](../../references/report-design.md): 1280×720 canvas, 8 px grid, 24 px
margin, 16 px gutter, alt text on every data visual, sentence-case titles.

| Folder | Archetype | Visuals |
|---|---|---|
| `overview-kpis/` | Overview: headline, 4 KPI cards, trend (dynamic title), segment slicer, buckets, ranking | 9 |
| `detail-table/` | Detail: headline + one sorted table | 2 |
| `documentation/` | Documentation page: measures catalog + loads (needs `_Documentacao` and `_Cargas`, see [documentation.md](../../references/documentation.md)) | 3 |

## How to use a template

1. Copy the folder into `<Name>.Report/definition/pages/` and rename it to a new 20-hex-character id.
   Set the same id in `page.json › name` and add it to `pages.json › pageOrder`.
2. Give every visual folder a new 20-hex id and set it in its `visual.json › name`.
3. Replace every field reference (`"Entity"`, `"Property"`, `queryRef`, `nativeQueryRef`) with fields of
   **your** model. Measures stay under `"Measure"`, columns under `"Column"`. Remove a visual rather than
   leaving a reference to a field that does not exist.
4. Rewrite the texts for your question: headline textbox, visual titles and every `altText`.
5. Keep the `$schema` versions of the report you are editing (see [pbir.md](../../references/pbir.md),
   golden rule 1). If the report uses newer versions, change the template's `$schema` to match.
6. Run `scripts/audit_pbip.py` (alt text, visual count, generic page names) and open the report in
   Desktop.
