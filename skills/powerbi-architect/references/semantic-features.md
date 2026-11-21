# Semantic model features: calculation groups, field parameters, visual calculations, DAX functions

Use these to **remove duplication**, never to show off. Each one has a cost (discoverability, tooling
support, performance); record the choice in the design doc when it changes how users read numbers.

| Need | Use | Not |
|---|---|---|
| Same time variants (YTD, PY, YoY %) for many measures | Calculation group | N × M copied measures |
| User switches the metric or dimension of one visual | Field parameter | Bookmarks + duplicated visuals |
| Running total, moving average, % of parent that only one visual needs | Visual calculation | A model measure nobody else uses |
| The same DAX logic repeated with different columns/measures | User-defined DAX function (preview) | Copy-pasted expressions |

Before using a feature, check the user's Power BI Desktop version and tenant: several of these became
generally available only recently, and some are still preview.

## 1. Calculation groups

When: ≥ 3 measures need the same set of variants. TMDL syntax: [tmdl.md](tmdl.md) › Calculation group.

Rules:
- The model must have `discourageImplicitMeasures` (calculation groups do not apply to implicit measures).
- Every item uses `SELECTEDMEASURE ()`; time items go through the marked date table.
- Percentage items set `formatStringDefinition` so `0.0%` does not inherit the base measure's currency.
- Exclude measures that must not be shifted (counts of "today", targets) with
  `ISSELECTEDMEASURE ( [Meta] )` guards, or keep them out of the visuals that use the group.
- One group per concern (time, currency, scenario). With several groups, set `precedence` explicitly and
  test the combinations.
- Name the column the user sees (`Item` → `Período`) and sort items with an ordinal column.
- Describe the group and every item with `///` so the Documentation page explains them.

```dax
-- calculation item YoY % with a guard for measures that must not be compared
VAR _cur = SELECTEDMEASURE ()
VAR _py = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dm_calendario[Data] ) )
RETURN IF ( ISSELECTEDMEASURE ( [Meta] ), BLANK (), DIVIDE ( _cur - _py, _py ) )
```

## 2. Field parameters

When: one visual must switch between 2–8 measures (or dimensions) chosen by the user.
Create them in Desktop (**Modeling › New parameter › Fields**): the generated calculated table carries a
hidden metadata column that marks it as a field parameter. The table expression is plain DAX:

```dax
{
    ( "Receita", NAMEOF ( '_Medidas'[Receita] ), 0 ),
    ( "Margem %", NAMEOF ( '_Medidas'[% Margem] ), 1 ),
    ( "Ticket Médio", NAMEOF ( '_Medidas'[Ticket Médio] ), 2 )
}
```

Rules:
- Edit the list in the table expression (TMDL partition) after Desktop created it; do not hand-write the
  metadata column.
- Measures in one parameter share a format family or the axis becomes unreadable; mixing currency and
  percentage → two visuals instead.
- Use the parameter column as a single-select slicer (or buttons), placed top-right of the visual it
  drives; the visual title is a measure that shows the selected name (`SELECTEDVALUE`).
- The audit and the graph see the parameter's measures through `NAMEOF`; keep the referenced measures
  documented like any other.

## 3. Visual calculations

DAX written on a visual, evaluated over the visual's own matrix (rows/columns), not over the model.
Functions designed for them include `RUNNINGSUM`, `MOVINGAVERAGE`, `PREVIOUS`, `NEXT`, `FIRST`, `LAST`,
`COLLAPSE`, `EXPAND` and `RANK`. Create them in Desktop (**New visual calculation**) and save; do not
hand-write them in `visual.json`.

```dax
Média móvel 3m = MOVINGAVERAGE ( [Receita], 3 )
% do total = DIVIDE ( [Receita], COLLAPSE ( [Receita], ROWS ) )
```

Rules:
- Only for logic that belongs to **one** visual. Anything shown in two places, used in a KPI or needed in
  the Documentation page → model measure.
- They depend on the visual's fields and order: changing the axis changes the result. Say so in the
  visual title or tooltip ("média móvel de 3 meses").
- Hide helper fields used only by the calculation, so the visual shows only what answers the question.

## 4. User-defined DAX functions (preview)

Reusable DAX functions defined once in the model and called from measures, calculated columns and
other functions. Preview feature: confirm it is enabled in the user's Desktop (**Options › Preview
features**) and supported where the model will be published before relying on it.

```dax
DEFINE
    FUNCTION MargemPct = ( receita : NUMERIC, custo : NUMERIC ) => DIVIDE ( receita - custo, receita )
EVALUATE
    { MargemPct ( 120, 90 ) }
```

Rules:
- Prototype in DAX query view with `DEFINE FUNCTION … EVALUATE …`, then add the function to the model from
  Desktop and commit the TMDL Desktop writes. Do not invent TMDL syntax for functions.
- Name functions by business meaning, describe them, and keep them small and pure (inputs → result).
- Measures still own the business definitions and the descriptions shown to users; a function is an
  implementation detail behind them.
- Until the feature is generally available, keep a fallback: the same logic inline in the measures.

## 5. Checklist

- [ ] The feature removes duplication that exists today (count the measures/visuals it replaces).
- [ ] The user's Desktop version supports it; preview features are flagged to the user.
- [ ] Descriptions exist for groups, items, parameters and functions.
- [ ] Numbers checked with and without the feature (same totals for the base case).
