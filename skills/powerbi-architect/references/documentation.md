# Documentation — the report explains itself

Three readers, one source of truth (the model's `///` descriptions):

| Reader | Where | Generated from |
|---|---|---|
| Business user | **Documentation page** inside the report | `INFO.VIEW.MEASURES/TABLES` calculated tables |
| Analyst / reviewer | `README.md` next to the project | written by you, kept current |
| Developer | `trabalho-da-ia/dicionario.md` (data dictionary) | generated from TMDL (`pbw documentar` in Power BI Workspaces) |

## 1. Documentation page (mandatory)
Two calculated tables, recalculated on every refresh:

```dax
-- _Documentacao : catalog of visible measures
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.MEASURES (), NOT [IsHidden] ),
    "Tabela", [Table],
    "Pasta", [DisplayFolder],
    "Medida", [Name],
    "Descrição", [Description],
    "Expressão DAX", [Expression],
    "Formato", [FormatString]
)
```
```dax
-- _Cargas : tables loaded from sources + last refresh
VAR _carga = MAX ( '_Medidas'[Data Carga] )          -- ROW("Data Carga", UTCNOW() + offset/24)
RETURN
    ADDCOLUMNS (
        SELECTCOLUMNS (
            FILTER ( INFO.VIEW.TABLES (), ISBLANK ( [Expression] ) && LEFT ( [Name], 1 ) <> "_" ),
            "Tabela", [Name], "Descrição", [Description], "Armazenamento", [StorageMode]
        ),
        "Última Carga", _carga
    )
```
Page layout: title "Documentação · <report>", subtitle, left table (Pasta, Medida, Descrição,
Expressão DAX), right table (Tabela, Descrição, Armazenamento, Última Carga). Hide the helper tables
from the field list only if report authors don't need them.

Notes: `INFO.VIEW.*` work in calculated tables of Power BI semantic models and refresh with the model;
`Expression` values require write permission at refresh time (the service refresh has it). In
calculated tables some data types may come back blank — keep text columns.

## 2. Description style (`///`)
- **Measures:** one business sentence + exclusions. *"Saldo em aberto com vencimento anterior à data
  da carga. Exclui títulos cancelados."* Not: *"CALCULATE of SUM with filter"*.
- **Tables:** content · grain · source file · connection. *"Parcelas de títulos a receber. Grão: 1
  linha por parcela · Fonte: trabalho-da-ia/sql/Fato Titulos.sql · Conexão: erp"*.
- **Columns:** only when the name is not self‑explanatory (codes, buckets, flags).

## 3. README sections (in the project language)
1. **O que é** — decision supported, audience, frequency; list of business questions.
2. **Como usar** — pages, key filters, drill‑throughs, where the Documentation page is.
3. **Cargas** — table: table · type · grain · SQL file · connection · mode; refresh schedule.
4. **Métricas** — table: metric · business definition (link to catalog and dictionary).
5. **Como foi construído** — model, Power Query policy, measures count/folders, decisions, validation.
6. **Segurança e privacidade** — classification, personal data, RLS.
7. **Histórico** — link to CHANGELOG.

## 4. CHANGELOG
Keep a Changelog sections (Adicionado / Alterado / Corrigido / Removido) and SemVer:
MAJOR = page/metric removed or redefined · MINOR = new analysis · PATCH = fix/formatting.

## 5. Design documents
`trabalho-da-ia/desenho.md` (Modelo, Métricas, Páginas, Decisões) is part of the documentation:
keep them current when the implementation changes (they are reviewed in PRs).
