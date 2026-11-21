# Visual selection — native first

## Question → visual

| The question is about… | Best native choice | Avoid |
|---|---|---|
| A single number now | Card / new card (`cardVisual`) | Gauge (unless a range matters) |
| A number vs target | KPI visual, card + variance measure, bullet via bar + target line | Speedometers |
| Ranking (which is biggest) | Horizontal bar, sorted desc | Pie, treemap for precise comparison |
| Change over time (many points) | Line | Columns with 50+ bars |
| Change over time (≤ 12 periods) | Column | Area with many series |
| Ordered buckets (aging, ranges) | Column, ordered by bucket | Pie |
| Part‑to‑whole (2–3 parts) | Donut / 100 % stacked bar | Pie with 8 slices |
| Part‑to‑whole (many parts / hierarchy) | Treemap, stacked bar with "Others" | Pie |
| Composition over time | Stacked column (≤ 4 series) or small multiples | Stacked area with 10 series |
| From A to B (bridge) | Waterfall | Stacked bars |
| Two measures with different scales | Line and clustered column combo | Dual axes on lines |
| Correlation | Scatter (+ size) | Two separate charts |
| Distribution | Column histogram (bins at source/DAX) or box via scatter | Averages only |
| Drivers of a change | Decomposition tree, key influencers | Many filtered copies of one chart |
| Many categories × periods | Matrix with conditional formatting (heatmap) | Dozens of lines |
| Geography | Filled map / Azure Maps (only if location is the insight) | Map just because there is a "state" column |
| Detail / action list | Table with conditional formatting, drill‑through | Huge matrix on overview |
| Same chart per segment | Small multiples (native in bar/column/line) | Copy‑pasting 6 visuals |
| Let user switch metric/dimension | Field parameters | Bookmarks + duplicated visuals |
| Running totals / moving average in one visual | Visual calculations | Extra model measures used once |

## Before declaring "no native visual fits"
Try, in order:
1. Formatting: conditional formatting, data labels, error bars, reference/constant lines, analytics pane.
2. Combination: card + bar for bullet charts; matrix + icons for status boards; line + column combo.
3. Small multiples, field parameters, visual calculations, tooltip pages, drill‑through.
4. SVG measures in a table/matrix image column (`data:image/svg+xml;utf8,…` with `dataCategory: ImageUrl`)
   for sparklines/progress bars — tiny, native, themable.
5. Certified AppSource visual allowed by the tenant (check admin portal policy).

Only then: `custom-visuals.md`. Record the comparison in an ADR:

```markdown
## ADR-00X — Custom visual: <name>
- Question it answers: …
- Native options tried: bar+target (fails because …), matrix heatmap (fails because …), SVG measure (…)
- AppSource: <visual> rejected because (not certified / not allowed / license)
- Decision: build `<name>.pbiviz` (API 5.x), no network access, accessibility checklist passed
- Cost: maintenance owner = …, upgrade on API changes
```
