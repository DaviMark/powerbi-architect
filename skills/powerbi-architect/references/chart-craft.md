# Chart craft: every visual, finished to the last detail

Read this when you place or review a visual. [visual-selection.md](visual-selection.md) says *which*
chart answers the question; this file says *how to finish it* so it looks designed, not defaulted. The
theme already sets most of it; the spec keys are those of `scripts/pbir_layout.py`.

## Contents
1. The rules every visual follows
2. Recipes: KPI card · KPI with trend · line · column · bar · combo · waterfall · scatter · table · matrix · slicer · map · pie
3. Numbers
4. Techniques in DAX (last point, top N + Others, empty states, highlight the current period)
5. The three-second review

## 1. The rules every visual follows

| Detail | Rule |
|---|---|
| Title | A conclusion or a question in sentence case, ≤ 60 characters, that fits the width (`PBI059`). When the number matters, make it a measure: "Vencido: R$ 4,2 mi (22,6% do saldo)". A dynamic title must be about the same measure as the visual (`PBI061`). |
| Data labels | On for bars, columns and waterfalls; 9 pt, `#666666`, display units automatic, ≤ 1 decimal. Off for lines with more than 12 points (label the last point instead, §4). |
| Axes | No axis titles (`PBI057`). Value axis hidden when every bar has a label. Category axis 9 pt `#757575`. |
| Gridlines | None. A line chart without labels may keep faint horizontal gridlines (`#F1F1F1`). |
| Legend | Only with 2+ series; top-left, 9 pt. With 2 series, prefer naming them in the title ("Receita em azul, meta tracejada"). |
| Colour | Accent for the focus series, grey (`#999999`) for context and targets, red/green only for bad/good through a colour measure (`colorMeasure`). Never a rainbow per category. |
| Sorting | By value, largest first, except time (chronological) and ordinal buckets (in their natural order, via `sortByColumn`). |
| Size | At least 200 × 140 px (`PBI064`); bars need 32 px per category (`"height": "auto"` with `"items"`). |
| Alt text | "<chart> of <measure> by <dimension>, <what to notice>": "Barras do vencido por regional; Sudeste concentra 38%". |
| Tooltip | Default tooltip shows the formatted value; for detail on hover, a tooltip page (`tooltipPage`), 320 × 240, one visual. |
| Interactions | Cross-filtering on; turn off interactions that produce nonsense (a KPI filtering a trend, a slicer filtering the "updated at" line). |
| Empty state | Measures return BLANK, not 0, when there is nothing to show; titles say "Sem dados para o filtro" (§4). |

## 2. Recipes

### KPI card (`kpi`)
- **When:** the headline numbers of a page, 3–4 per row (never more than 5, each ≥ 176 px: `PBI063`).
- **Anatomy:** label 9 pt `#666666` (container title) · value 20 pt semibold · one 9 pt line at the bottom.
- **The line:** context ("R$ 14,4 mi ainda a vencer") or distance to target/previous period with ▲/▼,
  coloured by a measure that knows the good direction (`variation`, `variationColor`; DAX in [dax.md](dax.md) › KPI lines).
  Every card in a row has a line, or none does: the rhythm matters more than the extra fact.
- **Label:** the business name, not the measure name: "Saldo em aberto", not "Valor Aberto".
- **Pitfalls:** units in the label *and* the value ("R$ (mi)" + "R$ 4,2 mi"); 3+ decimals; a card for a
  number nobody acts on.

### KPI with trend (`kpiTrend`)
- **When:** the history matters as much as the value (headcount, cash position). Height 120.
- `goal` adds the distance to target; the trend axis is the month column, not the date.

### Line (`lineChart`)
- **When:** change over time, ≥ 6 points. Time on X, oldest left.
- **Series:** 1 focus series in accent; up to 3 more in grey or the next palette colours; never > 4.
- **Target:** `"target": "Meta …"` draws it thin, grey and dashed, without labels. Say it in the title:
  "Entregas no prazo por mês, contra a meta de 95%".
- **Labels:** off; label the last point (§4) so the reader sees "now" without hunting.
- **Axis:** auto range is fine for rates; for amounts that people compare to zero, start at 0.
- **Pitfalls:** a line over categories that are not time; markers on every point; 24 months of daily data.

### Column (`clusteredColumnChart`)
- **When:** few periods (≤ 12) or ordinal buckets (aging 1-30, 31-60…). Sort by the bucket order.
- **Highlight:** colour the current period or the buckets above target with `colorMeasure`.
- **Pitfalls:** long category names (use bars); more than 12 columns (use a line).

### Bar (`clusteredBarChart`)
- **When:** ranking or comparing categories with names. Sort descending. Never time on the vertical axis (`PBI062`).
- **How many:** ≤ 10 bars; more → top N + "Outros" (§4), with the full list in a table page.
- **Height:** `"height": "auto"` and `"items": n` gives 32 px per bar; bars stay 20–28 px thick.
- **Colour:** one accent, or red for the bars below target via `colorMeasure` ("Margem por segmento:
  vermelho abaixo da meta de 30%").
- **Pitfalls:** truncated labels (widen the card or abbreviate in the dimension); sorted alphabetically.

### Combo (`combo`: columns + line)
- **When:** a volume and a related rate or target on the same time axis (deliveries and on-time rate;
  revenue and last year's revenue). `lineValues` for the line, `target` for a dashed target.
- **Units:** if the line is a different unit, Power BI adds a secondary axis; keep it, label the series in
  the title, and never combine more than one bar series with one line.
- **Pitfalls:** two unrelated stories in one chart — split them.

### Waterfall (`waterfallChart`)
- **When:** parts that add up to a total (DRE from revenue to EBITDA, variance by driver, aging buckets).
- **Colour:** `sentiment` by what is *good*: more overdue = red increase; revenue up = green increase;
  total grey. Order by the logic of the story (`sortByColumn` on an order column), not by value.

### Scatter (`scatter`)
- **When:** finding outliers on two measures at once (customers by revenue × margin; carriers by cost ×
  on-time). `size` only if a third measure really matters.
- **Title:** tell where to look: "Clientes com muita receita e pouca margem ficam embaixo à direita".
- **Detail:** add average lines on both axes in Desktop (Analytics › Average line) to make quadrants;
  label only the top outliers (a label measure that returns the name for the top 5, BLANK otherwise).

### Table (`tableEx`)
- **When:** people need exact values or will act on rows (a collection list, a reorder list).
- **Columns:** entity first, then ≤ 6 measures, ≥ 80 px each (`PBI060`); numbers right-aligned.
- **One highlight:** colour one measure column by a colour measure (`highlight`); everything else ink.
- **Sorting:** by the measure that decides the action (`sortBy`), and the title says so: "Clientes que
  concentram o valor vencido".
- **Extras worth adding in Desktop:** data bars on the main measure; sparklines per row when the trend
  of each row matters. Totals only when the sum means something (not for percentages).

### Matrix (`matrix`)
- **When:** two dimensions crossed (category × region) or a statement (DRE lines × accounts).
- Rows collapsed to the first level; ≤ 6 columns across; subtotals only where they mean something.
- Heat: background colour by a measure (Desktop › conditional formatting) on one value, light ramp
  (`#EEF2FD` → `#3E63DD`), never full saturation behind text.

### Slicer (`slicer`, top bar)
- Dropdown, 176 × 40, ≤ 2 per page in the top bar (`PBI046`, `PBI050`); everything else in the filter pane.
- Date: a "Between" slicer or a relative date filter in the filter pane, not a list of days.
- Sync the same slicer across pages (View › Sync slicers) so the user does not reset it page by page.

### Map
- Only when location *is* the insight (coverage, routing). Filled map with one sequential ramp; no
  bubbles over each other; always paired with a ranked bar for the exact numbers.

### Pie and donut
- 2–3 slices of one whole (`PBI040`), labels on slices, no legend. Anything else is a sorted bar.

## 3. Numbers

| Kind | Format | Example |
|---|---|---|
| Money in cards | display units auto, 1 decimal | R$ 4,2 mi |
| Money in tables | `\R\$ #,0` | R$ 4.218.300 |
| Percentages | `0.0%` | 22,6% |
| Difference of percentages | p.p. in a text measure | ▲ 1,4 p.p. |
| Counts | `#,0` | 8.412 |
| Days, rates per unit | `#,0` or `#,0.0` with the unit in the label | 2,7 dias |
| Variance | `+0.0%;-0.0%;0.0%` | +8,2% |

Same measure, same format everywhere. Never more than 1 decimal in a card or 2 in a table.

## 4. Techniques in DAX

**Label only the last point** (line charts): a second series with data labels on and the line hidden.

```dax
Último Ponto =
VAR _ultimo = CALCULATE ( MAX ( dm_calendario[Data] ), ALLSELECTED ( dm_calendario ) )
RETURN IF ( MAX ( dm_calendario[Data] ) = _ultimo, [Receita] )
```

**Top N + Outros** (bars): a disconnected table with the category names plus "Outros", and a measure that
returns the value for the top N and the sum of the rest on "Outros".

```dax
Receita Top 8 =
VAR _n = 8
VAR _cat = SELECTEDVALUE ( 'Categoria Top'[Categoria] )
VAR _top = TOPN ( _n, ALLSELECTED ( dm_produto[Categoria] ), [Receita] )
RETURN
    IF (
        _cat = "Outros",
        [Receita] - CALCULATE ( [Receita], KEEPFILTERS ( _top ) ),
        IF ( _cat IN SELECTCOLUMNS ( _top, "c", dm_produto[Categoria] ),
             CALCULATE ( [Receita], dm_produto[Categoria] = _cat ) )
    )
```

**Empty states:** titles that know when there is nothing to show.

```dax
Titulo Vencido =
IF (
    ISBLANK ( [Valor Vencido] ),
    "Sem títulos vencidos para o filtro escolhido",
    "Vencido: " & FORMAT ( [Valor Vencido], "R$ #,0" )
)
```

**Highlight the current period** (columns): a colour measure for `colorMeasure`.

```dax
Cor Mês Atual =
IF ( MAX ( dm_calendario[Data] ) >= EOMONTH ( TODAY (), -1 ) + 1, "#3E63DD", "#BBBBBB" )
```

## 5. The three-second review

Look at each visual in the preview PNG and answer, in order. Fix the first "no" before moving on.

1. Does the title say what to conclude, and does it fit?
2. Is the eye drawn to one thing first (the accent), with everything else quieter?
3. Can the exact number be read without hovering (labels or a card)?
4. Is the order meaningful (value, time or the natural order)?
5. Is every colour doing a job (focus, status, target)?
6. Would it still work for someone who cannot tell red from green (labels, ▲/▼, position)?
7. Does it line up with its neighbours (same top, same height in the row, 16 px gutters)?
8. Is there anything left to remove?
