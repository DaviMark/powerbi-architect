# Report design — think like a product designer

## Contents
0. Visual standard and app shell · 1. Mindset · 2. From question to page · 3. Layout system · 4. Page archetypes ·
5. Typography · 6. Color · 7. Visual craft · 8. Interaction · 9. Accessibility · 10. Mobile · 11. Harmony ·
12. Review ritual

## 0. The visual standard (non-negotiable)

Every report must look like a calm, precise product, never like a default Power BI page (default
palette, axis titles, gridlines, right-side legends, DIN, oversized slicers, five font sizes). The
reference is the interface of Twenty, the open-source CRM: neutral greys, one accent colour, a quiet
sidebar, a thin top bar, white panels with hairline borders, small type and generous, consistent space.
Brand identity (logo, accent colour, fonts) goes on top of this structure, never instead of it.

**App shell** (every page that has more than one sibling page; a single-page report can skip the
sidebar and keep the panel and top bar). Canvas 1280×720, positions in px:

| Piece | Position (x, y, w, h) | Spec |
|---|---|---|
| Canvas | 0, 0, 1280, 720 | page background `#F1F1F1` (theme `page.background`) |
| Sidebar | 0 – 220 | no shape: sits on the grey canvas, 8 px inner padding |
| App mark | 16, 20, 16, 16 | rounded square in the accent colour, or the 16 px logo |
| App name | 40, 16, 172, 24 | text box, 10 pt Segoe UI Semibold, `#333333` |
| Section label | 8, 52, 204, 24 | text box, 9 pt, `#757575` ("Páginas", "Apoio") |
| Page navigator | 8, 76, 204, 32·n | vertical, 32 px items, radius 8, text 10 pt left-aligned with a 32 px margin; default `#666666` on transparent, hover `#EBEBEB`, selected `#E3E3E3` + `#333333` semibold. Only visible pages (drill-through and tooltip pages are hidden) |
| Page icons | 16, 84 + 32·i, 16, 16 | one 16 px Tabler icon per visible page, grey, centred on its navigator item ([templates/icons](../templates/icons/README.md)) |
| Panel | 220, 12, 1048, 696 | shape with container background `#FFFFFF`, border 1 px `#EBEBEB`, radius 8 |
| Breadcrumb | 232, 28, ≤ 520, 24 | text box: `<Report>  /  ` 12 pt `#757575` + page name 12 pt semibold `#333333`; on drill-through pages a 24 px back arrow at 232 and the breadcrumb at 264 (`<Report> / <Parent> / <Page>`) |
| Top bar right | right edge 1256, y 20–28 | "Updated at" text (9 pt `#757575`, card without chrome) and ≤ 2 compact slicers (176×40) |
| Hairline | 220, 68, 1048, 1 | shape fill `#EBEBEB` |
| Content | 232, 80, 1024, 616 | everything else lives here, 16 px gutters |

`scripts/pbir_layout.py` writes all of this from a layout spec. The theme in [templates/theme/](../templates/theme/powerbi-architect-acessivel.json) already styles the
navigator, cards, tables, slicers, text boxes and shapes this way; the example
[examples/contas-a-receber](../../../examples/contas-a-receber) and the page templates in
[templates/pbir-pages/](../templates/pbir-pages/README.md) implement the shell. Copy them, do not redraw it.

**Components inside the content area:**
- KPI card: white, hairline border, radius 8; label 9 pt `#666666` (container title); value 20 pt
  semibold `#333333`; one 9 pt line at the bottom (12 px in, 20 px high): context ("R$ 14,4 mi ainda a
  vencer", grey) or distance to target / previous period with ▲/▼ coloured by a measure that knows
  whether up is good ([dax.md](dax.md) › KPI lines). Height 88, 4 per row.
- Chart card: title 10 pt semibold, sentence case, left; data labels instead of axes; no gridlines,
  no axis titles, legend only with 2+ series (top-left, 9 pt).
- Table: header 9 pt semibold `#666666`, values 9 pt `#333333`, horizontal hairlines `#F1F1F1` only,
  numbers right-aligned, no zebra stripes, no vertical grid.
- Colour: one accent for the focus series, greys for context, green/red only for good/bad.

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
- Canvas **1280×720** (16:9). **4 px grid**: every x, y, width and height is a multiple of 4 (audit
  `PBI048`); 1 px hairlines are the only exception.
- Spacing scale (Twenty's): 4 · 8 · 12 · 16 · 24 · 32. Gutter between cards **16**; panel padding
  **12**; never mix two gutters on one page.
- **Z‑pattern**: top‑left = most important (breadcrumb + headline KPI), top‑right = context (updated
  at, filters), middle = explanation, bottom = detail.
- Rows inside the content area (y 80 → 696): KPI row **88** · main row **248** · bottom row **248**
  (88 + 16 + 248 + 16 + 248 = 616). Two-column rows split 2:1 (672 + 16 + 336) or 1:1 (504 + 16 + 504).
- Equal widths within a row; left edges of everything in a column aligned; equal heights in a row.
- Whitespace is a feature: never fill empty space with another visual.

```
┌ sidebar 220 ┬─ panel (white, radius 8) ────────────────────────────────────────┐
│ ■ App name  │ Report / Page                     Updated at …   [Segment ▾]   │ 56
│ Páginas     ├──────────────────────────────────────────────────────────────────┤
│ ▌Overview   │ KPI 244×88   │ KPI 244×88   │ KPI 244×88   │ KPI 244×88         │
│  Customers  │ Explanation 672×248                    │ Breakdown 336×248     │
│  Docs       │ Detail / ranking 1024×248                                       │
└─────────────┴──────────────────────────────────────────────────────────────────┘
```

## 4. Page archetypes
Ready as layout spec rows and as PBIR in [templates/pbir-pages/](../templates/pbir-pages/README.md):

| Archetype | Use | Rows in the content area |
|---|---|---|
| **Overview** | executive, recurring meeting | 4 KPIs (88) · trend 2/3 + buckets 1/3 (248) · ranking with tooltip page (248) |
| **Diagnostic** | "where / why?" | waterfall of the parts 2/3 + breakdown 1/3 (300) · table with one conditional colour (300) |
| **Operational list** | daily action | one prioritized table (616), one column coloured by a measure, drill-through by right click |
| **Drill‑through detail** | one entity (customer, product) | back arrow + breadcrumb · 4 KPIs (88) · history 1/2 + breakdown 1/2 (512); hidden page |
| **Tooltip page** | context on hover | 320×240, one small visual, white background; hidden page |
| **Documentation** | trust | metrics catalog 3/5 + loads 2/5 (616) (mandatory) |

Navigation: page tabs are enough for ≤ 6 pages. Use buttons/bookmarks only when they reduce clicks.

## 5. Typography
**Font.** One family, two weights. Without a brand font, use **Segoe UI** (regular) and **Segoe UI
Semibold**: it renders on every Power BI surface, is neutral like Inter (Twenty's font), and keeps
numbers aligned. Use a brand font only if it is in Power BI's supported font list; fonts that are not
(Inter, Montserrat, Poppins…) fall back to something else in the service, so map them to Segoe UI and
say why. Never DIN (the Power BI default look), Comic Sans, Impact, Arial Black or decorative scripts
(audit `PBI051`).

**Scale (pt).** Small and calm; size never carries hierarchy alone, weight and colour do:

| Use | Size | Weight · colour |
|---|---|---|
| Page title / breadcrumb current page | 12 | semibold · `#333333` |
| Visual title, app name, navigator item | 10 | semibold (title, app) or regular · `#333333`/`#666666` |
| Body: table values, slicer items, data labels, axis labels, KPI label | 9 | regular · `#333333`/`#666666` |
| Secondary: updated at, section labels, breadcrumb parent, legend | 9 | regular · `#757575` |
| KPI value | 20 (max 24) | semibold · `#333333` |

Limits enforced by the audit (`PBI047`): text boxes ≤ 14 pt, KPI values ≤ 24 pt, everything else
≤ 12 pt. Minimum 9 pt anywhere.

- Titles are **sentences in business language**, sentence case. Never "Sum of Valor by Mês".
- Numbers: thousands separators, sensible precision (R$ 4,2 mi in KPIs; full value in tables),
  units in titles or labels, never both.

## 6. Color
- **Primary** = the thing to look at. **Grey** = context/comparison. **Green/red** only for good/bad
  status and only when the business agrees on what "good" is. **Never** decorative color per category.
- ≤ 6 categorical colors; beyond that, group into "Others" or use small multiples.
- Same meaning, same color across all pages (e.g., "Online" is always the 2nd palette color).
- Neutrals (Twenty's): canvas `#F1F1F1`, panels and cards `#FFFFFF`, borders `#EBEBEB` (strong
  `#D6D6D6`), text `#333333` / `#666666` / `#757575` (Twenty uses `#999999` for tertiary text; it fails
  4.5:1, so this skill darkens it). One accent (`#3E63DD` by default, or the brand's) for focus and
  selection. No gradients, glow, shadows, 3D.
- Contrast ≥ 4.5:1 for text, ≥ 3:1 for graphical objects. Don't rely on color alone — add labels/icons.
- No brand theme yet? Start from [templates/theme/powerbi-architect-acessivel.json](../templates/theme/powerbi-architect-acessivel.json):
  Twenty-inspired neutrals, 6 categorical colors (all ≥ 4.3:1 on white), status colors, Segoe UI, the
  type scale above, styled navigator, cards, tables and slicers, no gridlines/axis titles/shadows.
  Register it as `customTheme` (see [pbir.md](pbir.md) › Theme registration) and replace colors with the
  brand's, keeping the contrast.

## 7. Visual craft
The theme sets these defaults; only override per visual with a reason.
- **Bars**: start at zero; sort by value (except time/ordinal); data labels on, value axis off;
  horizontal bars for long category names.
- **Lines**: time on X; ≤ 4 series; 2 px stroke, no markers (theme); label the last point; title from a
  measure that states the current value.
- **Waterfall**: parts that add up to a total (aging buckets, variance by driver); sentiment colours
  follow the metric (more overdue = red: set `increase` red); total in grey.
- **Cards**: one number + short label; show variance as a second line (`▲ 4,2% vs AA`) via measure.
- **Tables**: right‑align numbers; one column coloured by a measure at most (`highlight` in the layout
  spec), the colour measure returns a hex that passes 4.5:1; horizontal hairlines only; totals
  intentional; column widths fit content; ≤ 7 columns visible.
- **Matrix** (`matrix` in the spec: `rows`, `columns`, `values`): subtotals only where they mean
  something; stepped layout; collapse by default; ≤ 6 columns across.
- **Combo** (`combo`: `values` as columns, `lineValues` as the line): only when the line is a different
  measure on the same scale story (volume and average, actual and target); never two unrelated units.
- **Scatter** (`scatter`: `details`, `x`, `y`, optional `size`): to show which items are outliers on two
  measures at once; title says what the corners mean ("Clientes com muito saldo e muito atraso no canto
  superior direito").
- **KPI with trend** (`kpiTrend`: `measure`, `trend` date field, optional `goal`): when the history
  matters more than the variation line; same height as the cards of its row (88 or 120), label 9 pt.
- **Pies/donuts**: only for 2–3 parts of a whole that sum to 100 %.
- **Maps**: only when location *is* the insight.
- Remove: gridlines, axis titles that repeat the title, legends for single series, borders inside
  cards, default "Sum of" names.

## 8. Interaction
- Default cross‑filtering is fine; disable interactions that produce nonsense (e.g., a KPI filtering a trend).
- Slicers: ≤ 2 on the page (audit `PBI050`), the rest in the filter pane. Dropdown style, **176×40 px**
  in the top bar (never wider than 240 or taller than 48: audit `PBI046`), header 9 pt, items 9 pt,
  "All" meaning everything. A slicer is a supporting control: it must never be the largest or boldest
  thing on the page.
- Tooltips: add the "why" (variance, share, last date) — use tooltip pages for rich context.
- Drill‑through to detail instead of giant tables on the overview.
- Empty states: measures returning a friendly text when no data (`"Sem dados para o filtro"`).
- Bookmarks only for real views (e.g., "Absolute / %"), not for decoration.

## 9. Accessibility (always)
- Alt text on every data visual (what it shows + the key takeaway measure).
- Tab order follows reading order; decorative shapes excluded.
- Font ≥ 9 pt; text contrast ≥ 4.5:1 (that is why tertiary text is `#757575`); color never the only signal.
- Test with high‑contrast mode and keyboard (Ctrl+F6, Tab, arrows).
- Titles and subtitles meaningful for screen readers.

## 10. Mobile
If users open it on phones, give every page a phone layout (`mobile.json` next to each visual). The
layout engine writes it: slicers on top, then each KPI full width (88), then the charts and tables full
width (≤ 240 high), on a 320 px wide canvas with 8 px margins; the sidebar, panel and top-bar chrome are
left out. Check it with `preview_pbir.py --mobile`, and once in Desktop's mobile layout view (the phone
canvas size has not been verified against Desktop yet). Never shrink the desktop page.

## 11. Harmony: the pass before you show anyone
**Look before you judge.** Render every page with `scripts/preview_pbir.py` (with a `--sample` file so
labels have real length) and look at the images: what does the eye land on first, is anything cramped,
truncated, floating or louder than it should be? An agent that has not looked at the page has not
reviewed it. Then go through the list:

Design it as if the most demanding product designer you can imagine will review it: everything has a
reason, nothing is louder than it needs to be, and the page feels inevitable.

1. **One of everything.** One font family, one accent colour, one gutter, one corner radius (8), one
   border colour. Count them.
2. **Edges.** Every left edge in a column and every top edge in a row lines up to the pixel; nothing is
   off the 4 px grid; nothing leaves the page.
3. **Proportion.** Visual sizes come from the row system in §3, not from dragging. Filters, logos and
   titles stay small; the data is the largest thing on the page.
4. **Type.** Only the sizes in §5. If you need emphasis, use weight or colour before size.
5. **Quiet chrome.** Hairline borders, no shadows, no backgrounds behind text boxes, no icons that
   carry no meaning, no duplicated labels.
6. **Consistency across pages.** Same shell, same positions for the same things (filters always in the
   top bar, updated-at always top-right), same colours for the same meaning.
7. **Words.** Titles, labels, measure names and empty states follow [copywriting.md](copywriting.md).
8. **Run the audit** with `--min-harmony 90`: `PBI046`–`PBI058` catch oversized slicers, large fonts,
   off-grid visuals, extra slicers, mixed fonts, visuals outside the page, wrong tab order, low-contrast
   text, generic or missing titles, axis titles and too many colours. Each page gets a harmony score
   (100 minus 20 per blocker, 10 per important finding, 4 per suggestion); deliver at 90 or more.

## 12. Review ritual (before Gate 2)
1. Squint test: does the eye land on the headline first?
2. Read only titles, top to bottom: do they tell the story?
3. Remove one visual. Did anything important get lost? If not, keep it removed.
4. Check every number format and every alignment.
5. Click every slicer/visual: any interaction that misleads?
6. Keyboard + high contrast pass.
