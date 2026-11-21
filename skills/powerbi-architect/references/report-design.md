# Report design — think like a product designer

## Contents
0. Visual standard · 1. Mindset · 2. From question to page · 3. Layout system · 4. Page archetypes · 5. Typography ·
6. Color · 7. Visual craft · 8. Interaction · 9. Accessibility · 10. Mobile · 11. Review ritual

## 0. The visual standard (non-negotiable)

Reports must look like a product designed for that company — never generic, never the default Power BI
look (default palette, grey canvas, axis titles, gridlines, right-side legends, DIN everywhere).
Everything below uses the company identity tokens (colors, ramp, fonts, logo).

**App shell, identical on every page (1280×720):**
- Sidebar 200 px, `sidebar` color: company logo or name (top), section label RELATÓRIO + page navigator
  (vertical, active page with `sidebar_active` background, inactive in `sidebar_muted`), section APOIO +
  Documentation/Manual page. Optional bottom callout card (e.g. "Customers at risk" + button to that page).
- Top bar 52 px, white, hairline bottom border: breadcrumb `Report › Page` (left); right: period slicer
  (dropdown) and a "Filters" button that opens the filter pane (bookmark/button). Nothing else.
- Content area x ≥ 220, y ≥ 72, 20‑px margin, 16‑px gutters, `canvas` background.
- Optional hero on the home page: 112 px image band (brand photo) with greeting and "Updated at".

**Components:**
- KPI card: label 10 pt muted · value 24 pt semibold · hairline · variation chip (arrow in a small
  square + % + "vs. previous month"), green/red by the metric's good direction. 4 per row.
- Chart card: title left (what is shown), legend top‑left under the title, optional segmented toggle
  top‑right (field parameter: "Revenue | Subscribers"), data labels instead of axes, no gridlines.
- Color: brand `ramp` dark → light; the focus series darkest, context lighter; comparisons in neutral
  grey; red/green only for good/bad; target lines dashed grey with a label ("Target: 3.5%").
- Rankings sorted desc with the leader in the darkest tone; matrices as heatmaps with the ramp and white
  text on dark cells; tracking tables with colored status text and no vertical grid.

The Power BI Workspaces prototype (`pbw prototipo`) already draws the shell; standalone, build the same
frame with shapes/text boxes and a page navigator.

## 1. Mindset
Great products start from the experience of the person using them and work backwards to the technology.
Apply that to every page:

- **Start from the decision.** Who opens this page, on which day, to decide what? Write it down.
  If two pages answer the same decision, merge them. If one page answers three decisions, split it.
- **Focus means saying no.** The quality of a report is measured by what you removed: the extra
  visual, the redundant KPI, the legend, the gridlines, the 7th color, the "just in case" slicer.
- **Simplicity is the hard part.** A page that looks obvious took the most decisions. Spend the effort
  on hierarchy and wording, not on effects.
- **Care about what nobody asked for.** Aligned edges, consistent number formats, a title that is a
  sentence, tooltips that explain, an empty state that says "no data for this filter". Users feel
  the craft even when they can't name it.
- **The first three seconds.** The user must know the answer to the page's question in 3 s
  (headline + KPIs), the "why" in 30 s (trend + breakdown), and find the detail in 3 min (table/drill).

## 2. From question to page
For each page, fill this before placing any visual:

| Field | Example |
|---|---|
| Decision | "Which customers do we call today?" |
| Question (subtitle) | "Where is our overdue balance concentrated?" |
| Headline measure (dynamic title) | "Overdue: R$ 4.2 mi (18% of open balance)" |
| KPIs (≤ 4) | Open balance · Overdue · % Overdue · Avg days late |
| Explanation visuals (≤ 3) | Overdue by aging bucket · Top customers · Balance by due month |
| Detail | Table on drill‑through page |
| Filters (≤ 2 on page) | Regional · Period |

## 3. Layout system
- Canvas **1280×720** (16:9). Grid **8 px**. Outer margin **24 px**. Gutter **16 px**.
- **Z‑pattern**: top‑left = most important (headline), top‑right = context (updated at, filters),
  middle = explanation, bottom = detail.
- Rows with consistent heights: header 80 · KPI row 104 · main row 232 · bottom row 232
  (adds up to 720 with margins/gutters).
- Equal widths within a row; align left edges of everything in a column.
- Whitespace is a feature: never fill empty space with another visual.

```
┌ 24 ───────────────────────────────────────────────────────────── 24 ┐
│ Headline (conclusion)                          [filter] [updated at] │ 80
│ Subtitle (question)                                                  │
├──────────────┬──────────────┬──────────────┬─────────────────────────┤
│ KPI          │ KPI          │ KPI          │ KPI                     │ 104
├──────────────┴──────────────┼──────────────┴─────────────────────────┤
│ Explanation 1               │ Explanation 2                          │ 232
├─────────────────────────────┴────────────────────────────────────────┤
│ Trend / detail                                                       │ 232
└──────────────────────────────────────────────────────────────────────┘
```

## 4. Page archetypes
| Archetype | Use | Structure |
|---|---|---|
| **Overview** | executive, recurring meeting | headline + 4 KPIs + 2 explanations + trend |
| **Diagnostic** | "why did it change?" | KPI with variance + decomposition/waterfall + breakdowns |
| **Operational list** | daily action | filters + prioritized table with conditional formatting |
| **Drill‑through detail** | one entity (customer, product) | entity header + KPIs + history + transactions |
| **Tooltip page** | context on hover | 320×240, 1–2 tiny visuals |
| **Documentation** | trust | metrics catalog + loads + last refresh (mandatory) |

Navigation: page tabs are enough for ≤ 6 pages. Use buttons/bookmarks only when they reduce clicks.

## 5. Typography
- One family (theme), two weights. Sizes: headline 20, KPI value 28, visual title 12, labels 10–11.
- Titles are **sentences in business language**, sentence case. Never "Sum of Valor by Mês".
- Numbers: thousands separators, sensible precision (R$ 4,2 mi in KPIs; full value in tables),
  units in titles or labels, never both.

## 6. Color
- **Primary** = the thing to look at. **Grey** = context/comparison. **Green/red** only for good/bad
  status and only when the business agrees on what "good" is. **Never** decorative color per category.
- ≤ 6 categorical colors; beyond that, group into "Others" or use small multiples.
- Same meaning, same color across all pages (e.g., "Online" is always the 2nd palette color).
- Backgrounds: light canvas, white cards, 1‑px border, radius from brand. No gradients, glow, shadows, 3D.
- Contrast ≥ 4.5:1 for text, ≥ 3:1 for graphical objects. Don't rely on color alone — add labels/icons.
- No brand theme yet? Start from [templates/theme/powerbi-architect-acessivel.json](../templates/theme/powerbi-architect-acessivel.json):
  6 categorical colors, all ≥ 4.8:1 on white, status colors, one font, no gridlines/axis titles/shadows.
  Register it as `customTheme` (see [pbir.md](pbir.md) › Theme registration) and replace colors with the
  brand's, keeping the contrast.

## 7. Visual craft
- **Bars**: start at zero; sort by value (except time/ordinal); data labels on, value axis off;
  horizontal bars for long category names.
- **Lines**: time on X; ≤ 4 series; label the last point; no markers unless sparse data.
- **Cards**: one number + short label; show variance as a second line (`▲ 4,2% vs AA`) via measure.
- **Tables**: right‑align numbers; conditional formatting on one column max; totals intentional;
  column widths fit content; ≤ 7 columns visible.
- **Matrix**: subtotals only where they mean something; stepped layout; collapse by default.
- **Pies/donuts**: only for 2–3 parts of a whole that sum to 100 %.
- **Maps**: only when location *is* the insight.
- Remove: gridlines, axis titles that repeat the title, legends for single series, borders inside
  cards, default "Sum of" names.

## 8. Interaction
- Default cross‑filtering is fine; disable interactions that produce nonsense (e.g., a KPI filtering a trend).
- Slicers: ≤ 2 on the page (others in the filter pane), dropdown style, with "All" meaning.
- Tooltips: add the "why" (variance, share, last date) — use tooltip pages for rich context.
- Drill‑through to detail instead of giant tables on the overview.
- Empty states: measures returning a friendly text when no data (`"Sem dados para o filtro"`).
- Bookmarks only for real views (e.g., "Absolute / %"), not for decoration.

## 9. Accessibility (always)
- Alt text on every data visual (what it shows + the key takeaway measure).
- Tab order follows reading order; decorative shapes excluded.
- Font ≥ 10 pt; contrast checked; color never the only signal.
- Test with high‑contrast mode and keyboard (Ctrl+F6, Tab, arrows).
- Titles and subtitles meaningful for screen readers.

## 10. Mobile
If users open it on phones, create the mobile layout: headline, 2–4 KPIs stacked, one trend,
filters at the top. Don't shrink the desktop page.

## 11. Review ritual (before Gate 2)
1. Squint test: does the eye land on the headline first?
2. Read only titles, top to bottom: do they tell the story?
3. Remove one visual. Did anything important get lost? If not, keep it removed.
4. Check every number format and every alignment.
5. Click every slicer/visual: any interaction that misleads?
6. Keyboard + high contrast pass.
