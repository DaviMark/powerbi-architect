# PBIR reference (PBIP report, enhanced report format)

Folder: `<Name>.Report/`

```
definition.pbir                     {"version":"4.0","datasetReference":{"byPath":{"path":"../<Name>.SemanticModel"}}}
.platform                           Fabric Git metadata (type Report, displayName, logicalId)
definition/
  version.json                      {"version":"2.0.0"}
  report.json                       theme collection, report settings, report-level filters
  pages/pages.json                  pageOrder + activePageName
  pages/<pageId>/page.json          displayName, size, page filters
  pages/<pageId>/visuals/<visualId>/visual.json
StaticResources/SharedResources/BaseThemes/*.json     base theme (don't edit)
StaticResources/RegisteredResources/*                 custom theme, images
```

Ready pages: [templates/pbir-pages/](../templates/pbir-pages/README.md) (overview with KPIs, detail
table, documentation), schema-validated. Accessible theme: [templates/theme/](../templates/theme/powerbi-architect-acessivel.json).

## Golden rules
1. **Keep the `$schema` versions already used** in the report you are editing. Power BI Desktop
   rejects files whose schema version is newer than it knows, and upgrades older ones when saving.
   New files: copy the `$schema` from a sibling file of the same kind.
2. `name` of a page/visual = its folder name = unique id (20 hex chars is the Desktop convention).
3. Field references must match the model **exactly**: `Entity` = table name, `Property` = column or
   measure name. Measures use `"Measure"`, columns use `"Column"`. `queryRef` = `"Table.Field"`,
   `nativeQueryRef` = field name.
4. Add every new page to `pages.json › pageOrder`.
5. Positions in pixels on the page canvas; `z` and `tabOrder` define stacking and keyboard order.
6. Literal values in expressions: strings `'text'` (single quotes inside JSON strings), numbers `12D`,
   integers `1L`, booleans `true`/`false`.
7. Validate JSON after every edit; then open in Desktop (or let the validator run).

## page.json
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.1.0/schema.json",
  "name": "a1b2c3d4e5f6a7b8c9d0",
  "displayName": "Visão Geral",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```
Tooltip page: add `"type": "Tooltip"`, size 320×240, and `"visibility": "HiddenInViewMode"`.
Drill‑through: `pageBinding` with the drill field — create it in Desktop once and copy the shape.

## Visual container skeleton
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.1.0/schema.json",
  "name": "0f1e2d3c4b5a69788796",
  "position": { "x": 24, "y": 96, "z": 1000, "width": 296, "height": 104, "tabOrder": 1000 },
  "visual": {
    "visualType": "card",
    "query": { "queryState": { "Values": { "projections": [
      { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Receita" } },
        "queryRef": "_Medidas.Receita", "nativeQueryRef": "Receita" }
    ] } } },
    "visualContainerObjects": {
      "title": [ { "properties": {
        "show": { "expr": { "Literal": { "Value": "true" } } },
        "text": { "expr": { "Literal": { "Value": "'Receita'" } } } } } ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

## Query roles by visual type

| visualType | Roles (queryState keys) | Typical use |
|---|---|---|
| `card` | `Values` (1 measure) | single KPI |
| `cardVisual` | `Data` (measures), `Categories` (optional) | new multi‑KPI card (check Desktop version) |
| `multiRowCard` | `Values` | several KPIs, compact |
| `kpi` | `Indicator`, `TrendLine`, `Goal` | KPI vs target with trend |
| `gauge` | `Y`, `MinValue`, `MaxValue`, `TargetValue` | single value vs range (use sparingly) |
| `clusteredBarChart` | `Category`, `Y`, `Series` | ranking with long labels |
| `clusteredColumnChart` | `Category`, `Y`, `Series` | time (few periods) / ordered buckets |
| `stackedBarChart` / `stackedColumnChart` | `Category`, `Y`, `Series` | composition (≤ 4 series) |
| `lineChart` | `Category`, `Y`, `Series` | trend over time |
| `lineClusteredColumnComboChart` | `Category`, `ColumnY`, `LineY` | volume + rate |
| `areaChart` | `Category`, `Y`, `Series` | cumulative / composition over time |
| `waterfallChart` | `Category`, `Y`, `Breakdown` | bridge between two totals |
| `scatterChart` | `Category`, `X`, `Y`, `Size`, `Series` | correlation |
| `donutChart` / `pieChart` | `Category`, `Y` | part‑to‑whole, ≤ 3 slices |
| `treemap` | `Group`, `Values` | many parts (hierarchy) |
| `tableEx` | `Values` | detail list |
| `pivotTable` (matrix) | `Rows`, `Columns`, `Values` | cross‑tab, hierarchy |
| `slicer` | `Values` | filter (mode via `objects.data.mode`: `'Basic'`, `'Dropdown'`, `'Between'`) |
| `textbox` | — (`objects.general.paragraphs`) | static titles/notes |
| `shape`, `image`, `actionButton` | — | layout/navigation |
| `filledMap` / `azureMap` | `Category`/`Location`, `Size`… | geography (only when location matters) |
| `decompositionTreeVisual`, `keyDriversVisual` | analysis | exploratory pages |

If unsure about role names for a visual, create it once in Desktop, save, and copy the JSON.

## Sorting
```json
"query": {
  "queryState": { "...": "..." },
  "sortDefinition": {
    "sort": [ { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Receita" } },
                "direction": "Descending" } ],
    "isDefaultSort": true
  }
}
```
Ordered categories (buckets, months): sort by the category column (its `sortByColumn` in the model
decides the order) with `"direction": "Ascending"`.

## Common formatting objects (`visual.objects`)
```json
"objects": {
  "labels":      [ { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } } ],
  "valueAxis":   [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ],
  "categoryAxis":[ { "properties": { "showAxisTitle": { "expr": { "Literal": { "Value": "false" } } } } } ],
  "legend":      [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ]
}
```
Prefer theme‑level styling (brand theme) over per‑visual formatting; per‑visual only for exceptions.

## Alt text (accessibility)
```json
"visualContainerObjects": {
  "general": [ { "properties": { "altText": { "expr": { "Literal": { "Value": "'Valor vencido por faixa de atraso, em reais'" } } } } } ]
}
```

## Dynamic title from a measure
```json
"title": [ { "properties": {
  "show": { "expr": { "Literal": { "Value": "true" } } },
  "text": { "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Título Página" } } }
} } ]
```

## Conditional color from a measure (field value)
```json
"dataPoint": [ { "properties": { "fill": { "solid": { "color": { "expr": {
  "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Cor Variação" } } } } } } } ]
```

## Visual‑level filter (Top N example) — easiest path
Create the filter once in Desktop and copy the `filterConfig` block; Top N filter JSON is verbose and
version‑sensitive. Alternative without filters: rank measure + `IF ( [Ranking] <= 10, [Valor] )`.

## Theme registration (report.json)
```json
"themeCollection": {
  "baseTheme":   { "name": "CY24SU06", "reportVersionAtImport": "5.56", "type": "SharedResources" },
  "customTheme": { "name": "acme-theme.json", "reportVersionAtImport": "5.56", "type": "RegisteredResources" }
},
"resourcePackages": [
  { "name": "SharedResources", "type": "SharedResources",
    "items": [ { "name": "CY24SU06", "path": "BaseThemes/CY24SU06.json", "type": "BaseTheme" } ] },
  { "name": "RegisteredResources", "type": "RegisteredResources",
    "items": [ { "name": "acme-theme.json", "path": "acme-theme.json", "type": "CustomTheme" } ] }
]
```
(Schema shape for `report/1.x`. Newer report schemas use an object for `reportVersionAtImport`;
follow what the file already has.)

## Custom visual registration
Custom visual from a `.pbiviz` imported in Desktop appears in `report.json › publicCustomVisuals`
(AppSource) or as a resource package (`CustomVisual…` item types). Import the `.pbiviz` through Desktop
once, then the JSON can reference `visualType` = the visual's GUID name.
