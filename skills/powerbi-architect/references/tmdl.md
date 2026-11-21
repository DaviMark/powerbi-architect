# TMDL reference (PBIP semantic model)

Folder: `<Name>.SemanticModel/definition/`

```
database.tmdl          compatibility level
model.tmdl             model properties, query groups, annotations
expressions.tmdl       Power Query parameters / shared expressions
relationships.tmdl     all relationships
tables/<Table>.tmdl    one file per table: columns, measures, hierarchies, partitions
roles/<Role>.tmdl      RLS
cultures/<xx-XX>.tmdl  linguistic metadata / translations
```
Plus `definition.pbism` (`"version": "4.0"` or higher = TMDL) and `.platform` (Fabric Git).

## Syntax rules
- **Indentation = hierarchy, with tabs.** Object at level n, its properties at n+1.
- Names with spaces or special characters in **single quotes**: `'Valor Vencido'`, `'% Vencido'`.
  Table names follow `ft_`/`dm_` snake case ([modeling.md](modeling.md) › Naming) and need no quotes.
  Escape a quote by doubling it: `'Customer''s Name'`.
- Object declaration with expression: `measure Name = <expr>`; multi‑line expressions start on the next
  line, indented **two levels deeper** than the object (or fenced with ```` ``` ````).
- Descriptions: `///` lines immediately above the object.
- Boolean properties are bare words: `isHidden`, `isKey`, `discourageImplicitMeasures`.
- Don't invent `lineageTag`s; Desktop creates them. Keep existing ones.
- Model‑level `annotation` lines sit at column 0 in `model.tmdl` (as Desktop writes them).

## model.tmdl
```tmdl
model Model
	culture: pt-BR
	defaultPowerBIDataSourceVersion: powerBI_V3
	discourageImplicitMeasures
	sourceQueryCulture: pt-BR
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

queryGroup Parametros

	annotation PBI_QueryGroupOrder = 0

annotation __PBI_TimeIntelligenceEnabled = 0
```

## Source table
```tmdl
/// Itens de nota fiscal faturados, sem devoluções.
/// Grão: 1 linha por item · Fonte: trabalho-da-ia/sql/ft_vendas.sql · Conexão: erp
table ft_vendas

	column id_cliente
		dataType: int64
		isHidden
		summarizeBy: none
		sourceColumn: id_cliente

	column Data
		dataType: dateTime
		formatString: dd/mm/yyyy
		summarizeBy: none
		sourceColumn: Data

	column Valor
		dataType: decimal
		isHidden
		formatString: \R\$ #,0.00
		summarizeBy: none
		sourceColumn: Valor

	partition ft_vendas = m
		mode: import
		source =
				let
				    Fonte = Value.NativeQuery(Sql.Database(Erp_Server, Erp_Database), "SELECT ...", null, [EnableFolding = true])
				in
				    Fonte
```
`dataType`: `string`, `int64`, `decimal` (fixed decimal, money), `double`, `dateTime`, `boolean`.

## Measure table
```tmdl
table _Medidas

	/// Receita líquida faturada (sem devoluções e cancelamentos).
	measure Receita = SUM ( ft_vendas[Valor] )
		formatString: \R\$ #,0
		displayFolder: Valores

	/// Variação da receita contra o mesmo período do ano anterior.
	measure 'Var % AA' =
			VAR _aa = [Receita AA]
			RETURN DIVIDE ( [Receita] - _aa, _aa )
		formatString: +0.0%;-0.0%;0.0%
		displayFolder: Indicadores

	column 'Data Carga'
		dataType: dateTime
		isHidden
		summarizeBy: none
		isNameInferred
		isDataTypeInferred
		sourceColumn: [Data Carga]

	partition _Medidas = calculated
		mode: import
		source = ROW ( "Data Carga", UTCNOW () )
```

## Calculated table / columns
Calculated table columns use `isNameInferred`, `isDataTypeInferred` and `sourceColumn: [Name]`
(bracketed). Calculated **column** in a table: `column 'Margem %' = DIVIDE ( … )` + `dataType` —
avoid in facts (push to SQL).

## Date table
```tmdl
table dm_calendario
	dataCategory: Time

	column Data
		dataType: dateTime
		isKey
		formatString: dd/mm/yyyy
		summarizeBy: none
		isNameInferred
		isDataTypeInferred
		sourceColumn: [Data]

	column Mês
		dataType: string
		summarizeBy: none
		isNameInferred
		isDataTypeInferred
		sourceColumn: [Mês]
		sortByColumn: 'Mês Nº'
```

## Relationships
```tmdl
relationship 5f8a6a3e-1c2d-4c1e-9a0b-0a1b2c3d4e5f
	fromColumn: ft_vendas.id_cliente
	toColumn: dm_cliente.id_cliente

relationship 7b1c2d3e-4f5a-4b6c-8d7e-9f0a1b2c3d4e
	isActive: false
	fromColumn: ft_vendas.'Data Entrega'
	toColumn: dm_calendario.Data
```
Optional: `crossFilteringBehavior: bothDirections` (avoid), `toCardinality: many` (avoid).
Relationship names: any unique id (Desktop uses GUIDs).

## Hierarchy
```tmdl
	hierarchy 'Ano > Mês'

		level Ano
			column: Ano

		level Mês
			column: Mês
```

## RLS role (roles/Gestor Filial.tmdl)
```tmdl
role 'Gestor Filial'
	modelPermission: read

	tablePermission dm_filial = dm_filial[email_gestor] = USERPRINCIPALNAME ()
```

## Calculation group
```tmdl
table 'Inteligência de Tempo'

	calculationGroup
		precedence: 10

		calculationItem Atual = SELECTEDMEASURE ()

		calculationItem AA = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dm_calendario[Data] ) )

		calculationItem 'Var %' =
				VAR _aa = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dm_calendario[Data] ) )
				RETURN DIVIDE ( SELECTEDMEASURE () - _aa, _aa )
			formatStringDefinition = "0.0%"

	column Item
		dataType: string
		summarizeBy: none
		sourceColumn: Name
```
Creating calculation groups requires `discourageImplicitMeasures` on the model.

## Editing tips
- After structural edits, reopen in Desktop (or use the MCP) to validate; Desktop rewrites files in
  canonical form — commit that version.
- Never edit `.pbi/cache.abf`; it is local data and git‑ignored.
- TMDL view in Desktop and the "TMDL" VS Code extension give syntax highlighting and diagnostics.
