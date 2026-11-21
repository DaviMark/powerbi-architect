# DAX — patterns that read in one pass

## Contents
1. Measure contract · 2. Layering · 3. Core patterns · 4. Time intelligence · 5. Text & UX measures ·
6. Calculation groups, field parameters, visual calculations · 7. Performance · 8. Anti‑patterns · 9. Testing

## 1. Measure contract
Every measure has:
- **Name** in business language (`Valor Vencido`, `% Vencido`, `Ticket Médio`).
- **Description** (`///` in TMDL) — the business definition in one sentence, including exclusions.
  This text appears in the Documentation page; write it for a manager, not for a developer.
- **formatString** — currency `\R\$ #,0` (or `\$#,0`), integers `#,0`, ratios `0.0%`, days `0`.
- **displayFolder** — `Valores`, `Indicadores`, `Contagens`, `Tempo`, `Textos`, `_Sistema`.
- Lives in the measure table.

## 2. Layering
1. **Base** — one aggregation over one column: `SUM`, `COUNTROWS`, `DISTINCTCOUNT`, `MIN/MAX`.
2. **Filtered** — base + `CALCULATE` with column predicates.
3. **Derived** — ratios, differences, rankings built only from other measures.
4. **Presentation** — dynamic titles, labels, colors (folder `Textos`/`Formatação`).

Never repeat a base aggregation inside another measure; reference the base measure.

## 3. Core patterns

```dax
-- Base
Receita = SUM ( ft_vendas[Valor] )
Pedidos = DISTINCTCOUNT ( ft_vendas[id_pedido] )

-- Filtered (column predicate, not FILTER over the table)
Receita Online = CALCULATE ( [Receita], dm_canal[Canal] = "Online" )

-- Ratio
Ticket Médio = DIVIDE ( [Receita], [Pedidos] )
% Online = DIVIDE ( [Receita Online], [Receita] )

-- Share of total (respecting slicers on other dimensions)
% do Total Clientes = DIVIDE ( [Receita], CALCULATE ( [Receita], ALLSELECTED ( dm_cliente ) ) )

-- Ranking
Ranking Cliente =
IF (
    ISINSCOPE ( dm_cliente[Cliente] ),
    RANKX ( ALLSELECTED ( dm_cliente[Cliente] ), [Receita], , DESC, DENSE )
)

-- Weighted average
Prazo Médio (dias) =
DIVIDE (
    SUMX ( ft_titulos, ft_titulos[Saldo] * ft_titulos[Dias] ),
    SUM ( ft_titulos[Saldo] )
)

-- Distinct with condition
Clientes Ativos = CALCULATE ( DISTINCTCOUNT ( ft_vendas[id_cliente] ), KEEPFILTERS ( ft_vendas[Valor] > 0 ) )

-- Semi‑additive (balance = last date with data)
Saldo Final =
VAR _ultima = LASTNONBLANK ( dm_calendario[Data], CALCULATE ( COUNTROWS ( ft_saldos ) ) )
RETURN CALCULATE ( SUM ( ft_saldos[Saldo] ), _ultima )

-- Target vs actual
% Atingimento = DIVIDE ( [Receita], [Meta] )
Desvio Meta = [Receita] - [Meta]
```

## 4. Time intelligence (requires a marked date table)

```dax
Receita AA     = CALCULATE ( [Receita], SAMEPERIODLASTYEAR ( dm_calendario[Data] ) )
Receita YTD    = TOTALYTD ( [Receita], dm_calendario[Data] )
Var % AA       = DIVIDE ( [Receita] - [Receita AA], [Receita AA] )
Receita 12M    = CALCULATE ( [Receita], DATESINPERIOD ( dm_calendario[Data], MAX ( dm_calendario[Data] ), -12, MONTH ) )
Receita Mês Anterior = CALCULATE ( [Receita], DATEADD ( dm_calendario[Data], -1, MONTH ) )
```

- Avoid showing future periods: guard with
  `IF ( MIN ( dm_calendario[Data] ) <= [Última Data com Dados], <expr> )` where
  `Última Data com Dados = CALCULATE ( MAX ( ft_vendas[Data] ), REMOVEFILTERS () )`.
- Secondary dates: `CALCULATE ( [Receita], USERELATIONSHIP ( ft_vendas[Data Entrega], dm_calendario[Data] ) )`.
- Fiscal years: `TOTALYTD ( [Receita], dm_calendario[Data], "06-30" )`.
- Many time variants of many measures → a **calculation group** (see §6) instead of N×M measures.

## 5. Text & UX measures
```dax
Título Página =
"Receita de " & FORMAT ( [Receita], "R$ #,0" ) & " · " &
FORMAT ( [Var % AA], "+0.0%;-0.0%" ) & " vs ano anterior"

Seleção Atual = IF ( ISFILTERED ( dm_filial[Regional] ), SELECTEDVALUE ( dm_filial[Regional], "Várias regionais" ), "Todas as regionais" )

Cor Variação = IF ( [Var % AA] >= 0, "#1E8E3E", "#D93025" )   -- use in conditional formatting (field value)
```
Text measures have no formatString; put them in folder `Textos`.

## 6. Calculation groups, field parameters, visual calculations
Full rules and examples: [semantic-features.md](semantic-features.md).
- **Calculation groups** — time intelligence or currency conversion applied to any measure.
  Use `SELECTEDMEASURE()`; set `formatStringDefinition` for % items. Document the precedence.
- **Field parameters** — let users switch measure/dimension in one visual instead of duplicating
  visuals (fewer pages, fewer visuals).
- **Visual calculations** — running totals, moving averages, % of parent that belong only to one visual;
  keeps the model clean. Still document them in the wireframe.
- **DAX user‑defined functions** (where available in the user's Desktop/Service) — for repeated logic;
  confirm support before using.

## 7. Performance
- Column predicates inside `CALCULATE` instead of `FILTER ( 'Fact', … )`. Use `KEEPFILTERS` to intersect.
- Variables evaluate once; reuse them.
- Avoid iterating large facts with complex row expressions; precompute at the source.
- `DISTINCTCOUNT` on high‑cardinality columns is expensive — consider pre‑aggregation.
- `IF` on measures in matrices with many cells: prefer `DIVIDE` / blank propagation.
- Don't convert blanks to zero by default (`+ 0`, `COALESCE`) — it densifies visuals and kills performance.
  Do it only when the business explicitly wants zeros.

## 8. Anti‑patterns
| Don't | Do |
|---|---|
| `IFERROR`, `ISERROR` | `DIVIDE`, guard conditions |
| `FILTER ( ALL ( 'Fact' ), … )` for a simple condition | `CALCULATE ( …, 'Fact'[Col] = x )` |
| `SUMX ( 'Fact', 'Fact'[Valor] )` | `SUM ( 'Fact'[Valor] )` |
| Calculated columns for things a measure does | measures |
| Hard‑coded dates/years | relative to `TODAY()` or the data's last date |
| Measures with the same logic duplicated per segment | one measure + slicer / field parameter |
| `ALL` everywhere to "fix" totals | understand filter context; `REMOVEFILTERS`/`ALLSELECTED` deliberately |
| Formatting numbers with `FORMAT` in value measures | `formatString` (FORMAT returns text → breaks sorting/aggregation) |

## 9. Testing
Write the DAX checks (in `trabalho-da-ia/conferencia.md`) with:
- **Control totals**: `EVALUATE ROW ( "Receita", [Receita], "Pedidos", [Pedidos] )` → compare with SQL.
- **Identities**: parts sum to the whole (`[A] + [B] = [Total]`), shares sum to 100 %.
- **Edge filters**: empty period, single customer, future dates.
Run them with the MCP (`dax_query_operations`) or ask the user to run in DAX query view.
