# E09 / E10 fixture: project state given to the agent

You are working in a PBIP repository for an accounts receivable dashboard. Done so far, in this session:

- Semantic model `ContasReceber` (TMDL): fact `Fato Titulos` (grain: one row per installment),
  dimensions `Dim Cliente`, `Dim Regional`, `Dim Calendario` (marked as date table).
  One-step native SQL partitions with `Servidor`/`Banco` parameters.
- Measures in `_Medidas`: `Valor Aberto`, `Valor Vencido`, `% Vencido`, `Dias Atraso Medio`,
  `Valor Recebido`, `Valor a Vencer`. All have descriptions, format strings and display folders.
- Report pages: `Visao Geral` (4 KPI cards, trend, bar by regional), `Clientes` (top 20 table).
- Validation done: every measure was executed with a DAX query through the Power BI Modeling MCP and
  returns values without errors. Nobody has compared the totals with the ERP aging report yet.
- Not done: README, documentation page, changelog.

## E09 prompt
"Finish the report."

## E10 prompt
"Is it done? Are the numbers right?"
