# The skill's custom visuals

Three Power BI custom visuals for what native visuals cannot draw at product quality. The layout engine
places them (`kpiCard`, `trend`, `list` in the layout spec) and packs them inside the report
(`<Report>/CustomVisuals/`), so the report opens with them on any machine.

| Visual | Spec type | What it draws | Data roles |
|---|---|---|---|
| Architect KPI | `kpiCard` | label, value, a pill with the variation (green or red by `higherIsBetter`), a note, a small trend | Value · Period (trend) · Reference (target) · Note (text measure) · Tooltips |
| Architect Trend | `trend` | title, the latest value with its variation, legend, dense columns with the latest period in focus | Period · Value · Comparison (last year, plan) · Tooltips |
| Architect List | `list` | avatar and name with a second line, status as a soft chip, numbers, progress bar | Item · Second line · Status (column or text measure) · Values (≤ 4) · Progress (0 to 1) · Tooltips |

With a Period, the KPI shows the **latest period** and compares it with the one before (or with the
Reference), like Power BI's native KPI visual.

## The company's identity

The drawing is the same for every company; the identity comes from the report theme. Each visual has a
**brand** card in the format pane (accent, text, secondary text, context colour, font) and
`scripts/make_theme.py --primary "#RRGGBB" --font "<font>"` fills it through `visualStyles`. Without a
brand, they use ink `#18181B` and zinc greys. Status colours (green, amber, red, blue) keep their
meaning for every brand.

When the company does not allow custom visuals, use the native types instead: `kpi` (with `trend`),
`lineChart` or `combo`, `tableEx` with a `highlight`.

## Layout

```
templates/visuals/
├── core/              drawing code shared by Power BI and the preview (plain DOM, no libraries)
├── architect-kpi/     one pbiviz project per visual: capabilities, src/visual.ts (data, format, events)
├── architect-list/
├── architect-trend/
└── dist/              the packaged .pbiviz files the layout engine puts in the report
```

`python tools/build_visuals.py` compiles `core/` into `scripts/visuals.js` (the preview draws with the
same code) and packages the three visuals with the official tools (ESLint config of
`eslint-plugin-powerbi-visuals`, `pbiviz package`). CI builds them on every change.

Each visual: rendering events, landing page, tooltips, selection and multi-selection (trend, list),
context menu, keyboard focus, high contrast, `allowInteractions`, highlight (KPI, trend), localization
(en-US, pt-BR), formatting model, `privileges: []`, no network, no `innerHTML`. The list has no highlight
support: Power BI highlights categorical data, not table rows.

**Not yet verified in Power BI Desktop**: the visuals compile, lint and package with Microsoft's tools,
and the report passes Microsoft's JSON schemas, but opening the example in Desktop is the check that
remains.
