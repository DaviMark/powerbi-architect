# E07 fixture: metadata extracted from `Vendas_Legado.pbit`

## Power Query: query `Vendas` (14 steps)
```m
let
    Source = Sql.Database("srv-prod-01", "ERP"),
    dbo_PedidoItem = Source{[Schema="dbo",Item="PedidoItem"]}[Data],
    #"Removed Columns" = Table.RemoveColumns(dbo_PedidoItem,{"obs", "usuario", "dt_alteracao"}),
    #"Filtered Rows" = Table.SelectRows(#"Removed Columns", each [status] <> "C"),
    #"Merged Queries" = Table.NestedJoin(#"Filtered Rows", {"id_produto"}, Produto, {"id"}, "Produto", JoinKind.LeftOuter),
    #"Expanded Produto" = Table.ExpandTableColumn(#"Merged Queries", "Produto", {"categoria", "marca"}),
    #"Added Custom" = Table.AddColumn(#"Expanded Produto", "Receita", each [qtd] * [preco_unit] - [desconto]),
    #"Changed Type" = Table.TransformColumnTypes(#"Added Custom",{{"Receita", type number}, {"dt_pedido", type date}}),
    #"Renamed Columns" = Table.RenameColumns(#"Changed Type",{{"dt_pedido", "Data Pedido"}, {"qtd", "Quantidade"}}),
    #"Replaced Value" = Table.ReplaceValue(#"Renamed Columns", null, "Sem marca", Replacer.ReplaceValue, {"marca"}),
    #"Trimmed Text" = Table.TransformColumns(#"Replaced Value",{{"categoria", Text.Trim, type text}}),
    #"Capitalized" = Table.TransformColumns(#"Trimmed Text",{{"categoria", Text.Proper, type text}}),
    #"Removed Duplicates" = Table.Distinct(#"Capitalized", {"id_item"}),
    #"Sorted Rows" = Table.Sort(#"Removed Duplicates",{{"Data Pedido", Order.Descending}})
in
    #"Sorted Rows"
```

## Model
- Tables: `Vendas` (fact, 31 columns imported), `Produto`, `Cliente`, `LocalDateTable_*` (auto date/time, 6 hidden tables).
- Relationship `Vendas[id_cliente]` → `Cliente[id]`, many-to-one, **cross filter: both**.
- Calculated column `Vendas[Ano]` = `YEAR(Vendas[Data Pedido])`.

## Measures (no descriptions, no format strings, no display folders)
```dax
Total Vendas = SUM(Vendas[Receita])
Margem % = (SUM(Vendas[Receita]) - SUM(Vendas[custo])) / SUM(Vendas[Receita])
Vendas AA = CALCULATE([Total Vendas], SAMEPERIODLASTYEAR(Vendas[Data Pedido].[Date]))
```

## Report
3 pages, 41 visuals in total; page 1 has a 12-slice pie chart and 9 slicers.

## Prompt
"Refactor this legacy report to our standard."
